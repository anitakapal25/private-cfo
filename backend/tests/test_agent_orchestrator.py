import asyncio

import pytest

from app.core.model_gateway import DisabledModelGateway, ModelDisabledError, ModelRequest
from app.services.agent_orchestrator import Intent, classify_intent
from app.services.agent_policy import ToolAuthorizationError, authorize_tool
from app.guardrails.regulatory_language import Decision, evaluate_financial_request


def test_agent_classifies_financial_freedom_intent():
    assert classify_intent("How can I achieve financial freedom earlier?") is Intent.FREEDOM_PLAN


def test_agent_classifies_cash_flow_intent():
    assert classify_intent("What is my monthly surplus?") is Intent.CASH_FLOW


def test_specific_product_request_is_blocked():
    decision = evaluate_financial_request("Which stock should I buy today?")
    assert decision.decision is Decision.BLOCK


def test_tool_registry_limits_tools_to_the_classified_intent():
    spec = authorize_tool("calculate_net_worth", "net_worth")
    assert spec.name == "calculate_net_worth"

    with pytest.raises(ToolAuthorizationError):
        authorize_tool("calculate_net_worth", "cash_flow")


def test_unknown_tool_fails_closed():
    with pytest.raises(ToolAuthorizationError):
        authorize_tool("query_any_database_table", "net_worth")


def test_external_model_gateway_is_disabled():
    request = ModelRequest(intent="general_education", redacted_context={}, tool_results=[])
    with pytest.raises(ModelDisabledError):
        asyncio.run(DisabledModelGateway().compose(request))
