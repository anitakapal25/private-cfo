from decimal import Decimal
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.financial_freedom import (
    FreedomProjectionInputs,
    calculate_freedom_projection,
)
from app.services.agent_orchestrator import AgentOrchestrator


def scenario(**overrides):
    values = {
        "current_age": 30,
        "target_age": 40,
        "current_monthly_lifestyle_expenses": Decimal("50000"),
        "current_investable_corpus": Decimal("1000000"),
        "monthly_contribution": Decimal("25000"),
        "annual_inflation_rate": Decimal("0"),
        "annual_return_rate": Decimal("0"),
        "withdrawal_rate": Decimal("0.04"),
    }
    values.update(overrides)
    return FreedomProjectionInputs(**values)


def test_zero_growth_projection_is_independently_reconcilable():
    result = calculate_freedom_projection(scenario())

    assert result["target_monthly_expenses"]["amount"] == "50000.00"
    assert result["required_corpus"]["amount"] == "15000000.00"
    assert result["projected_corpus"]["amount"] == "4000000.00"
    assert result["freedom_gap"]["amount"] == "11000000.00"
    assert result["scenario_status"] == "shortfall"


def test_projection_is_deterministic_for_identical_inputs():
    inputs = scenario(
        annual_inflation_rate=Decimal("0.06"),
        annual_return_rate=Decimal("0.08"),
    )
    assert calculate_freedom_projection(inputs) == calculate_freedom_projection(inputs)


@pytest.mark.parametrize("current_corpus, expected_status", [
    ("1000000", "shortfall"),
    ("20000000", "on_track"),
])
def test_projection_reply_explains_result_with_tool_sourced_everyday_example(current_corpus, expected_status):
    agent = AgentOrchestrator(None, uuid4())
    calculation_id = uuid4()
    record = SimpleNamespace(
        calculation_id=calculation_id, calculation_version="freedom-projection-v1",
        assumptions={}, as_of=datetime.now(timezone.utc), input_provenance=[],
        rule_versions={}, limitations=[],
    )
    agent._record_calculation = lambda *args, **kwargs: record
    answer = agent._freedom_plan(scenario(current_investable_corpus=Decimal(current_corpus)))

    assert answer.blocks[0]["calculation_id"] == str(calculation_id)
    assert answer.blocks[0]["result"]["scenario_status"] == expected_status
    assert "₹50,000.00" in answer.narrative
    assert "rent, groceries and bills" in answer.narrative
    assert "corpus" not in answer.narrative
    if expected_status == "shortfall":
        assert "not yet on track" in answer.narrative
        assert "what later age" in answer.narrative
    else:
        assert "looks on track" in answer.narrative


def test_larger_monthly_contribution_cannot_reduce_projected_corpus():
    lower = calculate_freedom_projection(scenario(monthly_contribution=Decimal("10000")))
    higher = calculate_freedom_projection(scenario(monthly_contribution=Decimal("20000")))
    assert Decimal(higher["projected_corpus"]["amount"]) >= Decimal(lower["projected_corpus"]["amount"])


@pytest.mark.parametrize(
    "overrides",
    [
        {"target_age": 30},
        {"current_monthly_lifestyle_expenses": Decimal("0")},
        {"current_investable_corpus": Decimal("-1")},
        {"annual_inflation_rate": Decimal("0.21")},
        {"annual_return_rate": Decimal("0.51")},
        {"withdrawal_rate": Decimal("0.009")},
    ],
)
def test_invalid_scenario_inputs_fail_closed(overrides):
    with pytest.raises(ValueError):
        calculate_freedom_projection(scenario(**overrides))
