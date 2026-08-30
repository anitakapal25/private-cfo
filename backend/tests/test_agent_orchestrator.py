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


@pytest.mark.parametrize(
    ("message", "intent"),
    [
        ("Show my 12-month cash flow forecast", Intent.CASH_FLOW_FORECAST),
        ("What are my debt and EMI metrics?", Intent.DEBT_ANALYSIS),
        ("Show my goal progress", Intent.GOAL_PROGRESS),
        ("Compare my current insurance coverage gap", Intent.INSURANCE_GAP),
        ("Help with my tax regime", Intent.TAX),
        ("Extract my Form 16 document", Intent.DOCUMENT),
        ("How many months does my emergency fund cover?", Intent.EMERGENCY_FUND),
    ],
)
def test_agent_classifies_phase_two_intents(message, intent):
    assert classify_intent(message) is intent


def test_specific_product_request_is_blocked():
    decision = evaluate_financial_request("Which stock should I buy today?")
    assert decision.decision is Decision.BLOCK


def test_tool_registry_limits_tools_to_the_classified_intent():
    spec = authorize_tool("calculate_net_worth", "net_worth")
    assert spec.name == "calculate_net_worth"

    with pytest.raises(ToolAuthorizationError):
        authorize_tool("calculate_net_worth", "cash_flow")

    projection = authorize_tool(
        "calculate_financial_freedom_projection", "freedom_plan"
    )
    assert projection.version == "freedom-projection-v1"


def test_unknown_tool_fails_closed():
    with pytest.raises(ToolAuthorizationError):
        authorize_tool("query_any_database_table", "net_worth")


def test_external_model_gateway_is_disabled():
    request = ModelRequest(intent="general_education", redacted_context={}, tool_results=[])
    with pytest.raises(ModelDisabledError):
        asyncio.run(DisabledModelGateway().compose(request))
