"""Verified financial memory with provenance and explicit conflict handling."""

from dataclasses import dataclass
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.agent import AuditEvent, EvidenceSource, FinancialFact

ALLOWED_FACT_TYPES = frozenset({
    "monthly_income", "monthly_expenses", "total_assets", "total_liabilities",
    "liquid_assets", "monthly_debt_payments", "debt_outstanding",
    "goal_target", "goal_current", "insurance_coverage",
    "annual_gross_income", "bank_account_balance", "epf_balance",
})
MONTHLY_FACT_TYPES = frozenset({"monthly_income", "monthly_expenses", "monthly_debt_payments"})
SNAPSHOT_FACT_TYPES = ALLOWED_FACT_TYPES - MONTHLY_FACT_TYPES
SCOPES = {
    "net_worth": ("total_assets", "total_liabilities"),
    "cash_flow": ("monthly_income", "monthly_expenses"),
    "debt": ("monthly_income", "monthly_debt_payments", "debt_outstanding"),
    "emergency_fund": ("liquid_assets", "monthly_expenses"),
    "goal": ("goal_current", "goal_target"),
    "insurance": ("insurance_coverage",),
}


def select_verified_facts(
    rows: list[FinancialFact], required: tuple[str, ...], as_of: datetime
) -> dict[str, FinancialFact]:
    """Select period-compatible confirmed facts without carrying monthly values forward."""
    local_calendar_cutoff = (as_of + timedelta(hours=14)).date()
    eligible = [
        row for row in rows
        if row.fact_type in required
        and row.verification_status == "verified"
        and row.observed_at <= as_of
        and (row.period_start is None or row.period_start <= local_calendar_cutoff)
    ]
    required_monthly = tuple(key for key in required if key in MONTHLY_FACT_TYPES)
    target_month = None
    if len(required_monthly) > 1:
        periods = [row.period_start for row in eligible if row.fact_type in required_monthly and row.period_start]
        target_month = max(periods) if periods else None
    target_month_end = date(target_month.year, target_month.month, monthrange(target_month.year, target_month.month)[1]) if target_month else None
    eligible.sort(key=lambda row: (row.period_start or row.observed_at.date(), row.observed_at, row.created_at or row.observed_at), reverse=True)
    selected: dict[str, FinancialFact] = {}
    for row in eligible:
        if row.fact_type in required_monthly and target_month and row.period_start != target_month:
            continue
        if row.fact_type in SNAPSHOT_FACT_TYPES and target_month_end and row.period_start and row.period_start > target_month_end:
            continue
        selected.setdefault(row.fact_type, row)
    return selected


def apply_fact_decision(
    fact: FinancialFact, decision: str, current: FinancialFact | None,
    decided_at: datetime,
) -> None:
    if fact.verification_status in {"verified", "rejected", "superseded"}:
        raise ValueError("Financial fact has already been decided")
    if decision == "reject":
        fact.verification_status = "rejected"
    elif decision == "confirm":
        if current:
            current.verification_status = "superseded"
            fact.supersedes_fact_id = current.fact_id
        fact.verification_status = "verified"
        fact.verified_at = decided_at
    else:
        raise ValueError("Decision must be confirm or reject")


@dataclass(frozen=True)
class ContextPacket:
    scope: str
    facts: dict[str, FinancialFact]
    missing: tuple[str, ...]
    as_of: datetime
    period_start: date | None = None

    @property
    def provenance(self) -> list[dict[str, str | None]]:
        return [{
            "fact_id": str(fact.fact_id), "fact_type": fact.fact_type,
            "source_type": fact.source_type, "source_id": fact.source_id,
            "observed_at": fact.observed_at.isoformat(),
            "period_kind": fact.period_kind,
            "period_start": fact.period_start.isoformat() if fact.period_start else None,
            "verified_at": fact.verified_at.isoformat() if fact.verified_at else None,
        } for fact in self.facts.values()]


class FinancialContextService:
    def __init__(self, db: Session, user_id: UUID):
        self.db = db
        self.user_id = user_id

    def assemble(self, scope: str, as_of: datetime | None = None) -> ContextPacket:
        if scope not in SCOPES:
            raise ValueError("Unsupported financial context scope")
        timestamp = as_of or datetime.now(timezone.utc)
        rows = self.db.query(FinancialFact).filter(
            FinancialFact.user_id == self.user_id,
            FinancialFact.fact_type.in_(SCOPES[scope]),
            FinancialFact.verification_status == "verified",
            FinancialFact.observed_at <= timestamp,
        ).order_by(FinancialFact.observed_at.desc(), FinancialFact.created_at.desc()).all()
        selected = select_verified_facts(rows, SCOPES[scope], timestamp)
        missing = tuple(key for key in SCOPES[scope] if key not in selected)
        selected_months = [fact.period_start for fact in selected.values() if fact.fact_type in MONTHLY_FACT_TYPES and fact.period_start]
        target_month = max(selected_months) if selected_months else None
        if missing:
            all_months = [row.period_start for row in rows if row.fact_type in MONTHLY_FACT_TYPES and row.period_start]
            target_month = max(all_months) if all_months else target_month
        return ContextPacket(scope=scope, facts=selected, missing=missing, as_of=timestamp, period_start=target_month)

    def create_candidate(
        self, *, fact_type: str, value: Decimal, unit: str, source_type: str,
        source_id: str | None, observed_at: datetime, confidence: Decimal | None,
        period_kind: str | None = None, period_start: date | None = None,
    ) -> FinancialFact:
        if fact_type not in ALLOWED_FACT_TYPES:
            raise ValueError("Unsupported financial fact type")
        if value < 0:
            raise ValueError("Financial fact value cannot be negative")
        expected_kind = "monthly" if fact_type in MONTHLY_FACT_TYPES else "as_of"
        actual_period = period_start or (observed_at.date().replace(day=1) if expected_kind == "monthly" else observed_at.date())
        if period_kind is not None and period_kind != expected_kind:
            raise ValueError(f"{fact_type} requires {expected_kind} period semantics")
        if expected_kind == "monthly" and actual_period.day != 1:
            raise ValueError("Monthly facts require the first day of the calendar month")
        local_date_tolerance = datetime.now(timezone.utc).date() + timedelta(days=1)
        if actual_period > (local_date_tolerance.replace(day=1) if expected_kind == "monthly" else local_date_tolerance):
            raise ValueError("Financial fact period cannot be in the future")
        existing = self.db.query(FinancialFact).filter(
            FinancialFact.user_id == self.user_id,
            FinancialFact.fact_type == fact_type,
            FinancialFact.verification_status == "verified",
            *([FinancialFact.period_start == actual_period] if expected_kind == "monthly" else []),
        ).first()
        evidence = EvidenceSource(
            user_id=self.user_id, source_type=source_type,
            source_reference=source_id, observed_at=observed_at,
        )
        self.db.add(evidence)
        self.db.flush()
        fact = FinancialFact(
            user_id=self.user_id, fact_type=fact_type, value=value, unit=unit,
            source_type=source_type, source_id=source_id,
            evidence_source_id=evidence.evidence_source_id,
            verification_status="conflict" if existing else "unverified",
            confidence=confidence, observed_at=observed_at,
            period_kind=expected_kind, period_start=actual_period,
        )
        self.db.add(fact)
        self.db.flush()
        self._audit("financial_fact_candidate_created", fact, {"has_conflict": existing is not None})
        return fact

    def decide(self, fact_id: UUID, decision: str) -> FinancialFact:
        fact = self.db.query(FinancialFact).filter(
            FinancialFact.fact_id == fact_id, FinancialFact.user_id == self.user_id,
        ).first()
        if fact is None:
            raise LookupError("Financial fact not found")
        current = None
        if decision == "confirm":
            filters = [
                FinancialFact.user_id == self.user_id,
                FinancialFact.fact_type == fact.fact_type,
                FinancialFact.verification_status == "verified",
                FinancialFact.fact_id != fact.fact_id,
            ]
            if fact.period_kind == "monthly":
                filters.append(FinancialFact.period_start == fact.period_start)
            current_rows = self.db.query(FinancialFact).filter(*filters).with_for_update().all()
            current = current_rows[0] if current_rows else None
            for previous in current_rows:
                previous.verification_status = "superseded"
        apply_fact_decision(fact, decision, current, datetime.now(timezone.utc))
        self._audit("financial_fact_decided", fact, {"decision": decision})
        return fact

    def decide_many(self, fact_ids: list[UUID], decision: str) -> list[FinancialFact]:
        if len(set(fact_ids)) != len(fact_ids):
            raise ValueError("Duplicate financial fact identifiers are not allowed")
        rows = self.db.query(FinancialFact).filter(
            FinancialFact.user_id == self.user_id,
            FinancialFact.fact_id.in_(fact_ids),
        ).with_for_update().all()
        if len(rows) != len(fact_ids):
            raise LookupError("One or more financial facts were not found")
        by_id = {row.fact_id: row for row in rows}
        return [self.decide(fact_id, decision) for fact_id in fact_ids if fact_id in by_id]

    def _audit(self, event_type: str, fact: FinancialFact, metadata: dict) -> None:
        self.db.add(AuditEvent(
            user_id=self.user_id, event_type=event_type, target_type="financial_fact",
            target_id=str(fact.fact_id), outcome="success",
            metadata_json={"fact_type": fact.fact_type, **metadata},
        ))
