from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.models.agent import FinancialFact, PlannedAction
from app.services.proactive_reviews import RULE_VERSION, generate_findings

NOW = datetime(2026, 8, 30, tzinfo=timezone.utc)


def fact(kind, value, status="verified", days_old=0):
    observed = NOW - timedelta(days=days_old)
    return FinancialFact(fact_id=uuid4(), user_id=uuid4(), fact_type=kind, value=Decimal(value), unit="INR", source_type="user_statement", verification_status=status, observed_at=observed, created_at=observed)


def test_review_detects_stale_data_and_negative_cash_flow_with_evidence():
    findings = generate_findings([
        fact("monthly_income", "100", days_old=100),
        fact("monthly_expenses", "125"),
    ], [], NOW)
    types = {item["finding_type"] for item in findings}
    assert types == {"stale_financial_data", "negative_monthly_cash_flow"}
    deficit = next(item for item in findings if item["finding_type"] == "negative_monthly_cash_flow")
    assert deficit["evidence"]["monthly_deficit"]["amount"] == "25.00"
    assert deficit["evidence"]["rule_version"] == RULE_VERSION


def test_review_detects_reserve_and_goal_decline_from_superseded_fact():
    findings = generate_findings([
        fact("liquid_assets", "80"), fact("liquid_assets", "100", "superseded", 10),
        fact("goal_current", "40"), fact("goal_current", "50", "superseded", 10),
    ], [], NOW)
    assert {item["finding_type"] for item in findings} == {"emergency_reserve_declined", "goal_balance_declined"}


def test_review_detects_only_overdue_planned_actions():
    overdue = PlannedAction(action_id=uuid4(), status="planned", created_at=NOW - timedelta(days=31))
    recent = PlannedAction(action_id=uuid4(), status="planned", created_at=NOW - timedelta(days=5))
    done = PlannedAction(action_id=uuid4(), status="completed", created_at=NOW - timedelta(days=60))
    findings = generate_findings([], [overdue, recent, done], NOW)
    assert len(findings) == 1
    assert findings[0]["evidence"]["action_ids"] == [str(overdue.action_id)]


def test_no_verified_data_produces_no_invented_finding():
    assert generate_findings([fact("monthly_income", "1", "unverified")], [], NOW) == []
