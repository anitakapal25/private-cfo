import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from fastapi.routing import APIRoute

from app.auth.manager import get_current_active_user
from app.core import crypto
from app.core.config import Settings
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
from app.services.ecosystem_capabilities import get_ecosystem_capabilities


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


def test_create_conversation_post_route_precedes_static_frontend():
    matching_routes = [
        route
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path == "/api/v1/agent/conversations"
        and "POST" in route.methods
    ]

    assert len(matching_routes) == 1
    assert app.routes.index(matching_routes[0]) < next(
        index for index, route in enumerate(app.routes) if route.path == ""
    )


def test_phase_3_routes_are_not_mounted_by_default():
    paths = {route.path for route in app.routes if isinstance(route, APIRoute)}
    blocked_prefixes = (
        "/api/advisor",
        "/api/investment-platform",
        "/api/account-aggregator",
        "/api/community",
        "/api/wellness-program",
        "/api/webhook",
        "/api/export",
    )
    assert not any(path.startswith(blocked_prefixes) for path in paths)


def test_financial_integrations_require_provider_and_approval():
    with pytest.raises(ValueError, match="approved provider"):
        Settings(
            _env_file=None,
            environment="test",
            jwt_secret="test-secret",
            enable_financial_integrations=True,
        )


def test_background_sync_cannot_run_without_financial_integrations():
    with pytest.raises(ValueError, match="ENABLE_FINANCIAL_INTEGRATIONS"):
        Settings(
            _env_file=None,
            environment="test",
            jwt_secret="test-secret",
            enable_background_sync=True,
            enable_financial_integrations=False,
        )


def test_phase_3_capability_report_is_fail_closed_and_non_sensitive():
    settings = Settings(
        _env_file=None,
        environment="test",
        jwt_secret="test-secret",
        financial_integration_provider="secret-provider-name",
        financial_integration_approval_reference="internal-approval",
    )

    report = get_ecosystem_capabilities(settings)

    assert all(item["status"] == "disabled" for item in report.values())
    assert "secret-provider-name" not in str(report)
    assert "internal-approval" not in str(report)


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
