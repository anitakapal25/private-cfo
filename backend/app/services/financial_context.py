"""Verified financial memory with provenance and explicit conflict handling."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.agent import AuditEvent, EvidenceSource, FinancialFact

ALLOWED_FACT_TYPES = frozenset({
    "monthly_income", "monthly_expenses", "total_assets", "total_liabilities",
    "liquid_assets", "monthly_debt_payments", "debt_outstanding",
    "goal_target", "goal_current", "insurance_coverage",
})
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
    """Select the latest confirmed fact per field without automatic trust precedence."""
    eligible = [
        row for row in rows
        if row.fact_type in required
        and row.verification_status == "verified"
        and row.observed_at <= as_of
    ]
    eligible.sort(key=lambda row: (row.observed_at, row.created_at or row.observed_at), reverse=True)
    selected: dict[str, FinancialFact] = {}
    for row in eligible:
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

    @property
    def provenance(self) -> list[dict[str, str | None]]:
        return [{
            "fact_id": str(fact.fact_id), "fact_type": fact.fact_type,
            "source_type": fact.source_type, "source_id": fact.source_id,
            "observed_at": fact.observed_at.isoformat(),
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
        return ContextPacket(scope=scope, facts=selected, missing=missing, as_of=timestamp)

    def create_candidate(
        self, *, fact_type: str, value: Decimal, unit: str, source_type: str,
        source_id: str | None, observed_at: datetime, confidence: Decimal | None,
    ) -> FinancialFact:
        if fact_type not in ALLOWED_FACT_TYPES:
            raise ValueError("Unsupported financial fact type")
        if value < 0:
            raise ValueError("Financial fact value cannot be negative")
        existing = self.db.query(FinancialFact).filter(
            FinancialFact.user_id == self.user_id,
            FinancialFact.fact_type == fact_type,
            FinancialFact.verification_status == "verified",
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
            current_rows = self.db.query(FinancialFact).filter(
                FinancialFact.user_id == self.user_id,
                FinancialFact.fact_type == fact.fact_type,
                FinancialFact.verification_status == "verified",
                FinancialFact.fact_id != fact.fact_id,
            ).with_for_update().all()
            current = current_rows[0] if current_rows else None
            for previous in current_rows:
                previous.verification_status = "superseded"
        apply_fact_decision(fact, decision, current, datetime.now(timezone.utc))
        self._audit("financial_fact_decided", fact, {"decision": decision})
        return fact

    def _audit(self, event_type: str, fact: FinancialFact, metadata: dict) -> None:
        self.db.add(AuditEvent(
            user_id=self.user_id, event_type=event_type, target_type="financial_fact",
            target_id=str(fact.fact_id), outcome="success",
            metadata_json={"fact_type": fact.fact_type, **metadata},
        ))
