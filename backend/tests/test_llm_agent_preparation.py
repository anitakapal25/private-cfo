"""Offline preparation evidence, not acceptance of a conversational LLM agent."""

import asyncio
from uuid import uuid4

import httpx
import pytest

from app.core.model_gateway import ModelRequest, ModelSafetyError, OpenAIModelGateway
from app.guardrails.regulatory_language import Decision, evaluate_financial_request
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.agent_policy import ToolAuthorizationError, authorize_tool


@pytest.mark.parametrize("question", [
    "How am I doing financially?",
    "Give me an overview of my finances",
    "How healthy are my finances?",
])
def test_overview_questions_execute_conversational_tools(question):
    from test_conversation_agent import run
    agent, answer, _, _ = run(question)
    assert answer.intent.value == "financial_overview"
    assert len(agent.executor.calls) == 5


@pytest.mark.parametrize("question", [
    "Which mutual fund or stock should I buy?",
    "Which stocks should I buy?",
    "Which fund would you pick for me?",
])
def test_product_selection_paraphrases_receive_boundary(question):
    assert evaluate_financial_request(question).decision is Decision.BLOCK


@pytest.mark.parametrize("tool,intent", [
    ("execute_sql", "net_worth"),
    ("calculate_net_worth", "general_education"),
])
def test_untrusted_tool_choices_are_rejected(tool, intent):
    with pytest.raises(ToolAuthorizationError):
        authorize_tool(tool, intent)


def test_mocked_model_cannot_introduce_a_financial_number(monkeypatch):
    def fake_provider(request):
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [{
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": "Your surplus is ₹999999."}],
                }],
            },
        )

    transport = httpx.MockTransport(fake_provider)
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        "app.core.model_gateway.httpx.AsyncClient",
        lambda **kwargs: real_client(transport=transport, **kwargs),
    )
    request = ModelRequest(
        sanitized_question="Explain my cash flow.",
        intent="cash_flow",
        redacted_context={},
        tool_results=[],
    )
    with pytest.raises(ModelSafetyError):
        asyncio.run(OpenAIModelGateway("synthetic-test-only").compose(request))
