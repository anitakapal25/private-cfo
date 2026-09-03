"""Deterministic proactive financial review rules and persistence."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.agent import ActionPlan, AuditEvent, FinancialFact, PlannedAction, ProactiveReview

RULE_VERSION = "proactive-review-v1"
STALE_AFTER_DAYS = 90
INCOMPLETE_ACTION_DAYS = 30
DEDUP_WINDOW_DAYS = 30


def _latest_by_type(rows: list[FinancialFact], status: str) -> dict[str, FinancialFact]:
    selected: dict[str, FinancialFact] = {}
    for row in sorted(rows, key=lambda item: item.observed_at, reverse=True):
        if row.verification_status == status:
            selected.setdefault(row.fact_type, row)
    return selected


def generate_findings(
    facts: list[FinancialFact], actions: list[PlannedAction], now: datetime
) -> list[dict]:
    current = _latest_by_type(facts, "verified")
    previous = _latest_by_type(facts, "superseded")
    findings: list[dict] = []

    stale = [fact for fact in current.values() if fact.observed_at < now - timedelta(days=STALE_AFTER_DAYS)]
    if stale:
        findings.append({
            "finding_type": "stale_financial_data",
            "trigger_ids": sorted(str(item.fact_id) for item in stale),
            "evidence": {"fact_ids": sorted(str(item.fact_id) for item in stale), "threshold_days": STALE_AFTER_DAYS, "rule_version": RULE_VERSION, "as_of": now.isoformat()},
        })

    income, expenses = current.get("monthly_income"), current.get("monthly_expenses")
    if (
        income and expenses
        and income.period_start == expenses.period_start
        and Decimal(income.value) < Decimal(expenses.value)
    ):
        deficit = Decimal(expenses.value) - Decimal(income.value)
        findings.append({
            "finding_type": "negative_monthly_cash_flow",
            "trigger_ids": [str(income.fact_id), str(expenses.fact_id)],
            "evidence": {"fact_ids": [str(income.fact_id), str(expenses.fact_id)], "monthly_deficit": {"amount": str(deficit.quantize(Decimal("0.01"))), "currency": income.unit}, "calculation": "monthly_expenses - monthly_income", "rule_version": RULE_VERSION, "as_of": now.isoformat()},
        })

    for fact_type, finding_type in (("liquid_assets", "emergency_reserve_declined"), ("goal_current", "goal_balance_declined")):
        latest, prior = current.get(fact_type), previous.get(fact_type)
        if latest and prior and Decimal(latest.value) < Decimal(prior.value):
            findings.append({
                "finding_type": finding_type,
                "trigger_ids": [str(latest.fact_id), str(prior.fact_id)],
                "evidence": {"fact_ids": [str(latest.fact_id), str(prior.fact_id)], "change": str((Decimal(latest.value) - Decimal(prior.value)).quantize(Decimal("0.01"))), "unit": latest.unit, "rule_version": RULE_VERSION, "as_of": now.isoformat()},
            })

    overdue = [action for action in actions if action.status == "planned" and action.created_at and action.created_at < now - timedelta(days=INCOMPLETE_ACTION_DAYS)]
    if overdue:
        findings.append({
            "finding_type": "planned_actions_incomplete",
            "trigger_ids": sorted(str(item.action_id) for item in overdue),
            "evidence": {"action_ids": sorted(str(item.action_id) for item in overdue), "threshold_days": INCOMPLETE_ACTION_DAYS, "rule_version": RULE_VERSION, "as_of": now.isoformat()},
        })
    return findings


def persist_reviews(db: Session, user_id: UUID, now: datetime | None = None) -> list[ProactiveReview]:
    timestamp = now or datetime.now(timezone.utc)
    facts = db.query(FinancialFact).filter(FinancialFact.user_id == user_id).all()
    actions = db.query(PlannedAction).join(ActionPlan).filter(ActionPlan.user_id == user_id).all()
    existing = db.query(ProactiveReview).filter(
        ProactiveReview.user_id == user_id,
        ProactiveReview.created_at >= timestamp - timedelta(days=DEDUP_WINDOW_DAYS),
    ).all()
    existing_keys = {item.dedup_key for item in existing}
    created = []
    for finding in generate_findings(facts, actions, timestamp):
        material = f"{RULE_VERSION}:{finding['finding_type']}:{','.join(finding['trigger_ids'])}"
        key = hashlib.sha256(material.encode()).hexdigest()
        if key in existing_keys:
            continue
        review = ProactiveReview(
            user_id=user_id, finding_type=finding["finding_type"], status="open",
            evidence=finding["evidence"], rule_version=RULE_VERSION, dedup_key=key,
        )
        db.add(review)
        db.flush()
        db.add(AuditEvent(user_id=user_id, event_type="proactive_review_created", target_type="proactive_review", target_id=str(review.review_id), outcome="success", metadata_json={"finding_type": review.finding_type, "rule_version": RULE_VERSION}))
        created.append(review)
        existing_keys.add(key)
    return created
