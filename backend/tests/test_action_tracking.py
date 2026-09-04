from datetime import date
from decimal import Decimal

import pytest

from app.services.recommendation_planner import calculate_action_progress, calculate_action_target, inclusive_months
from app.routers.agent_v1 import CandidateActionRequest


def test_target_uses_inclusive_calendar_months_across_years():
    assert inclusive_months(date(2026, 11, 20), date(2027, 2, 1)) == 4
    assert calculate_action_target(Decimal("5000"), date(2026, 11, 20), date(2027, 2, 1)) == {
        "months": 4, "target_amount": "20000.00", "currency": "INR",
    }


def test_target_rejects_reversed_dates_and_nonpositive_amounts():
    with pytest.raises(ValueError):
        calculate_action_target(Decimal("100"), date(2026, 2, 1), date(2026, 1, 1))
    with pytest.raises(ValueError):
        calculate_action_target(Decimal("0"), date(2026, 1, 1), date(2026, 1, 1))


def test_progress_is_decimal_deterministic_and_capped_at_one_hundred_percent():
    assert calculate_action_progress([], Decimal("1000"))["percentage"] == "0.00"
    assert calculate_action_progress([Decimal("333.33")], Decimal("1000"))["percentage"] == "33.33"
    result = calculate_action_progress([Decimal("700"), Decimal("500")], Decimal("1000"))
    assert result["progress_amount"] == "1200.00"
    assert result["percentage"] == "100"


def test_progress_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        calculate_action_progress([Decimal("0")], Decimal("100"))
    with pytest.raises(ValueError):
        calculate_action_progress([], Decimal("0"))


def test_human_labels_map_to_deterministic_scores():
    request = CandidateActionRequest(
        action_type="increase_monthly_savings", monthly_amount="5000",
        priority_label="high", difficulty_label="easy",
        start_date="2026-09-15", target_date="2027-01-02",
    )
    assert request.user_priority == Decimal("0.75")
    assert request.feasibility == Decimal("0.75")
    assert request.start_date == date(2026, 9, 15)


def test_action_request_rejects_reversed_dates():
    with pytest.raises(ValueError, match="Target date"):
        CandidateActionRequest(
            action_type="increase_monthly_savings", monthly_amount="5000",
            start_date="2026-10-01", target_date="2026-09-01",
        )
