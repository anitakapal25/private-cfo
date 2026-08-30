import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from fastapi.routing import APIRoute

from app.auth.manager import get_current_active_user
from app.core import crypto
from app.main import app
from app.routers.account_aggregator import AccountAggregatorConnectionResponse
from app.routers.investment_platform import InvestmentPlatformConnectionResponse
from app.routers.webhook import WebhookSubscriptionResponse
from app.tools.financial_tools import calculate_real_return
from app.guardrails.assumption_freshness import (
    StaleAssumptionError,
    VersionedAssumption,
    require_current_assumption,
)
from app.guardrails.authorization import bind_authenticated_user
from app.guardrails.data_redaction import redact_sensitive
from app.guardrails.financial_output import FinancialOutputError, execute_financial_tool
from app.guardrails.regulatory_language import Decision, evaluate_financial_request


def test_all_agent_routes_require_authenticated_user():
    agent_routes = [
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/api/agent/")
    ]
    assert agent_routes
    for route in agent_routes:
        dependency_calls = {dependency.call for dependency in route.dependant.dependencies}
        assert get_current_active_user in dependency_calls, route.path


def test_all_v1_agent_routes_require_authenticated_user():
    agent_routes = [
        route for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/api/v1/agent/")
    ]
    assert agent_routes
    for route in agent_routes:
        dependency_calls = {dependency.call for dependency in route.dependant.dependencies}
        assert get_current_active_user in dependency_calls, route.path


def test_sensitive_fields_are_not_in_response_schemas():
    assert "encrypted_credentials" not in AccountAggregatorConnectionResponse.model_fields
    assert "credentials" not in AccountAggregatorConnectionResponse.model_fields
    assert "encrypted_credentials" not in InvestmentPlatformConnectionResponse.model_fields
    assert "credentials" not in InvestmentPlatformConnectionResponse.model_fields
    assert "secret" not in WebhookSubscriptionResponse.model_fields


def test_secret_encryption_round_trip(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(crypto, "get_settings", lambda: SimpleNamespace(encryption_key=key))

    encrypted = crypto.encrypt_secret("sensitive-token")

    assert encrypted != "sensitive-token"
    assert crypto.decrypt_secret(encrypted) == "sensitive-token"


def test_encryption_fails_closed_without_key(monkeypatch):
    monkeypatch.setattr(crypto, "get_settings", lambda: SimpleNamespace(encryption_key=None))

    with pytest.raises(crypto.EncryptionConfigurationError):
        crypto.encrypt_secret("sensitive-token")


def test_real_return_uses_geometric_relationship():
    result = calculate_real_return(Decimal("0.10"), Decimal("0.06"))

    assert result == (Decimal("1.10") / Decimal("1.06")) - Decimal("1")
    assert result != Decimal("0.04")


def test_real_return_rejects_invalid_inflation():
    with pytest.raises(ValueError):
        calculate_real_return(Decimal("0.10"), Decimal("-1"))


def test_authorization_guard_rejects_conflicting_user_id():
    with pytest.raises(Exception) as exc_info:
        bind_authenticated_user({"user_id": "attacker"}, "authenticated-user")

    assert getattr(exc_info.value, "status_code", None) == 403


def test_regulatory_language_blocks_specific_product_instruction():
    decision = evaluate_financial_request("Which stock should I buy today?")

    assert decision.decision is Decision.BLOCK
    assert "buy" in decision.safe_response


def test_redaction_removes_sensitive_fields_and_identifiers():
    redacted = redact_sensitive({
        "password": "secret-value",
        "note": "PAN ABCDE1234F and Aadhaar 1234 5678 9012",
    })

    assert redacted["password"] == "[REDACTED]"
    assert "ABCDE1234F" not in redacted["note"]
    assert "1234 5678 9012" not in redacted["note"]


def test_expired_assumption_fails_closed():
    assumption = VersionedAssumption(
        identifier="expired",
        effective_from=date(2024, 1, 1),
        review_by=date(2024, 12, 31),
        source_url="https://example.invalid",
    )

    with pytest.raises(StaleAssumptionError):
        require_current_assumption(assumption, as_of=date(2025, 1, 1))


def test_financial_tool_output_requires_traceability_metadata():
    class IncompleteTool:
        async def execute(self, _):
            return {"amount": 100}

    with pytest.raises(FinancialOutputError):
        asyncio.run(execute_financial_tool(IncompleteTool(), {}))
