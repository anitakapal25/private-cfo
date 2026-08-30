from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.agent import FinancialFact
from app.services.financial_context import apply_fact_decision, select_verified_facts
from app.services.financial_engine import (
    calculate_cash_flow,
    calculate_debt_metrics,
    calculate_emergency_fund_coverage,
    calculate_goal_projection,
    calculate_net_worth,
)


NOW = datetime(2026, 8, 30, tzinfo=timezone.utc)


def fact(kind: str, value: str, status: str, observed_at: datetime) -> FinancialFact:
    return FinancialFact(
        fact_id=uuid4(), user_id=uuid4(), fact_type=kind, value=Decimal(value),
        unit="INR", source_type="user_statement", verification_status=status,
        observed_at=observed_at, created_at=observed_at,
    )


def test_context_uses_only_latest_confirmed_facts_for_requested_scope():
    old = fact("monthly_income", "100", "verified", NOW - timedelta(days=2))
    new = fact("monthly_income", "120", "verified", NOW - timedelta(days=1))
    candidate = fact("monthly_income", "999", "unverified", NOW)
    unrelated = fact("total_assets", "500", "verified", NOW)

    selected = select_verified_facts(
        [old, new, candidate, unrelated], ("monthly_income",), NOW
    )

    assert selected == {"monthly_income": new}


def test_confirming_conflict_supersedes_previous_fact_explicitly():
    current = fact("monthly_income", "100", "verified", NOW - timedelta(days=1))
    candidate = fact("monthly_income", "120", "conflict", NOW)

    apply_fact_decision(candidate, "confirm", current, NOW)

    assert current.verification_status == "superseded"
    assert candidate.verification_status == "verified"
    assert candidate.supersedes_fact_id == current.fact_id
    assert candidate.verified_at == NOW


def test_rejected_candidate_never_becomes_authoritative():
    candidate = fact("total_assets", "500", "unverified", NOW)
    apply_fact_decision(candidate, "reject", None, NOW)
    assert candidate.verification_status == "rejected"
    assert select_verified_facts([candidate], ("total_assets",), NOW) == {}


def test_fact_decision_cannot_be_replayed():
    candidate = fact("total_assets", "500", "unverified", NOW)
    apply_fact_decision(candidate, "confirm", None, NOW)
    with pytest.raises(ValueError, match="already been decided"):
        apply_fact_decision(candidate, "reject", None, NOW)


def test_financial_foundation_golden_examples():
    assert calculate_net_worth(Decimal("1000"), Decimal("400"))["net_worth"]["amount"] == "600.00"
    assert calculate_cash_flow(Decimal("100"), Decimal("60"))["savings_rate"] == "0.4000"
    assert calculate_emergency_fund_coverage(Decimal("300"), Decimal("100"))["coverage_months"] == "3.00"
    assert calculate_debt_metrics(Decimal("100"), Decimal("25"), Decimal("500"))["debt_to_income_ratio"] == "0.2500"
    assert calculate_goal_projection(Decimal("100"), Decimal("500"), Decimal("20"), 12, Decimal("0"))["projected_amount"]["amount"] == "340.00"


@pytest.mark.parametrize("function,args", [
    (calculate_net_worth, (Decimal("-1"), Decimal("0"))),
    (calculate_cash_flow, (Decimal("1"), Decimal("-1"))),
    (calculate_emergency_fund_coverage, (Decimal("-1"), Decimal("1"))),
    (calculate_debt_metrics, (Decimal("1"), Decimal("-1"), Decimal("0"))),
])
def test_financial_foundation_rejects_negative_inputs(function, args):
    with pytest.raises(ValueError):
        function(*args)
