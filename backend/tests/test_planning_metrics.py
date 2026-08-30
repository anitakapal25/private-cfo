from decimal import Decimal

import pytest

from app.services.planning_metrics import (
    calculate_coverage_gap,
    calculate_debt_metrics,
    calculate_goal_progress,
    forecast_flat_cash_flow,
)


def test_debt_metrics_golden_example():
    result = calculate_debt_metrics(Decimal("100000"), [
        {"principal_outstanding": Decimal("500000"), "emi_amount": Decimal("20000")},
        {"principal_outstanding": Decimal("100000"), "emi_amount": Decimal("5000")},
    ])
    assert result["total_outstanding"]["amount"] == "600000.00"
    assert result["monthly_emi"]["amount"] == "25000.00"
    assert result["debt_to_income_ratio"] == "0.2500"


def test_zero_income_reports_unknown_ratio_without_dividing():
    result = calculate_debt_metrics(Decimal("0"), [])
    assert result["debt_to_income_ratio"] is None


def test_flat_cash_flow_forecast_reconciles_cumulative_surplus():
    result = forecast_flat_cash_flow(Decimal("100"), Decimal("60"), months=12)
    assert result["months"][0]["surplus"]["amount"] == "40.00"
    assert result["months"][-1]["cumulative_surplus"]["amount"] == "480.00"


def test_forecast_rejects_unbounded_horizon():
    with pytest.raises(ValueError):
        forecast_flat_cash_flow(Decimal("100"), Decimal("60"), months=25)


def test_goal_progress_caps_remaining_but_discloses_overfunding_percentage():
    result = calculate_goal_progress(Decimal("120"), Decimal("100"))
    assert result["remaining_amount"]["amount"] == "0.00"
    assert result["progress_percent"] == "120.00"
    assert result["status"] == "funded"


def test_coverage_gap_uses_only_user_selected_target():
    result = calculate_coverage_gap(Decimal("500000"), Decimal("1000000"))
    assert result["coverage_gap"]["amount"] == "500000.00"
    assert result["target_source"] == "explicit_user_selected_scenario"
