from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.guardrails.assumption_freshness import StaleAssumptionError, VersionedAssumption
from app.routers.agent_v1 import FreedomScenarioRequest, resolve_freedom_scenario


def scenario_request(**overrides):
    values = {
        "current_age": 34,
        "target_age": 50,
        "current_monthly_lifestyle_expenses": Decimal("45000"),
        "current_investable_corpus": Decimal("850000"),
        "monthly_contribution": Decimal("15000"),
    }
    values.update(overrides)
    return FreedomScenarioRequest(**values)


def test_reviewed_catalogue_supplies_technical_rates():
    inputs, metadata = resolve_freedom_scenario(scenario_request())

    assert inputs.annual_inflation_rate == Decimal("0.0600")
    assert inputs.annual_return_rate == Decimal("0.0800")
    assert inputs.withdrawal_rate == Decimal("0.0350")
    assert metadata["source"] == "reviewed_assumption_catalogue"
    assert set(metadata["rates"]) == {
        "annual_inflation_rate", "annual_return_rate", "withdrawal_rate"
    }
    assert all(rate["version"] for rate in metadata["rates"].values())
    assert all(rate["reviewed_at"] for rate in metadata["rates"].values())


def test_legacy_custom_rates_remain_supported_and_distinguishable():
    inputs, metadata = resolve_freedom_scenario(scenario_request(
        annual_inflation_rate=Decimal("0.0500"),
        annual_return_rate=Decimal("0.0700"),
        withdrawal_rate=Decimal("0.0300"),
    ))

    assert inputs.annual_return_rate == Decimal("0.0700")
    assert metadata == {"source": "explicit_user_confirmed_scenario", "rates": {}}


def test_partial_custom_rates_are_rejected():
    with pytest.raises(ValidationError, match="custom scenario rates must be supplied together"):
        scenario_request(annual_inflation_rate=Decimal("0.0500"))


def test_expired_catalogue_assumption_fails_closed(monkeypatch):
    expired = VersionedAssumption(
        identifier="expired-planning-rate",
        value=Decimal("0.0500"),
        version="expired-v1",
        effective_from=date(2020, 1, 1),
        reviewed_at=date(2020, 1, 1),
        review_by=date(2020, 1, 2),
        source_url="https://example.invalid/expired",
        methodology="Expired test assumption",
    )
    monkeypatch.setitem(
        __import__("app.routers.agent_v1", fromlist=["FINANCIAL_FREEDOM_ASSUMPTIONS"]).FINANCIAL_FREEDOM_ASSUMPTIONS,
        "annual_inflation_rate",
        expired,
    )

    with pytest.raises(StaleAssumptionError, match="expired for review"):
        resolve_freedom_scenario(scenario_request())


def test_unreviewed_catalogue_assumption_fails_closed(monkeypatch):
    unreviewed = VersionedAssumption(
        identifier="unreviewed-planning-rate",
        value=Decimal("0.0500"),
        version=None,
        effective_from=date(2026, 1, 1),
        reviewed_at=None,
        review_by=date(2099, 1, 1),
        source_url="https://example.invalid/unreviewed",
        methodology="Unreviewed test assumption",
    )
    monkeypatch.setitem(
        __import__("app.routers.agent_v1", fromlist=["FINANCIAL_FREEDOM_ASSUMPTIONS"]).FINANCIAL_FREEDOM_ASSUMPTIONS,
        "annual_inflation_rate",
        unreviewed,
    )

    with pytest.raises(StaleAssumptionError, match="has not completed review"):
        resolve_freedom_scenario(scenario_request())
