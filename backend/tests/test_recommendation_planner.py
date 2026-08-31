from decimal import Decimal

import pytest

from app.services.recommendation_planner import CandidateAction, calculate_action_impact, rank_actions


def action(kind="increase_monthly_savings", amount="1000", feasibility="0.8", priority="0.9"):
    return CandidateAction(kind, Decimal(amount), Decimal(feasibility), Decimal(priority))


def test_action_impact_is_deterministic_and_annualizes_without_model_arithmetic():
    result = calculate_action_impact(action())
    assert result["monthly_cash_flow_change"]["amount"] == "1000.00"
    assert result["annualized_change"]["amount"] == "12000.00"
    assert result == calculate_action_impact(action())


def test_ranking_uses_user_priority_and_feasibility():
    ranked = rank_actions([
        action(amount="500", feasibility="0.2", priority="0.2"),
        action(kind="reduce_monthly_expenses", amount="300", feasibility="1", priority="1"),
    ])
    assert ranked[0]["action_type"] == "reduce_monthly_expenses"
    assert "planner_version" in ranked[0]


def test_product_specific_or_unknown_action_fails_closed():
    with pytest.raises(ValueError, match="Unsupported"):
        calculate_action_impact(action(kind="buy_named_mutual_fund"))


@pytest.mark.parametrize("amount,feasibility,priority", [("0", "1", "1"), ("1", "1.1", "1"), ("1", "1", "-0.1")])
def test_invalid_action_inputs_fail_closed(amount, feasibility, priority):
    with pytest.raises(ValueError):
        calculate_action_impact(action(amount=amount, feasibility=feasibility, priority=priority))
