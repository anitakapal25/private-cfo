import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from app.core import model_gateway
from app.core.model_gateway import ModelRequest, ModelSafetyError, OpenAIModelGateway
from app.routers import agent_v1
from app.routers.agent_v1 import MessageResponse, compose_automatic_explanation


def message(*parts):
    return {"type": "message", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": part} for part in parts]}


def compose(monkeypatch, body, status_code=200):
    real_client = httpx.AsyncClient

    def respond(request):
        return httpx.Response(status_code, json=body)

    monkeypatch.setattr(model_gateway.httpx, "AsyncClient", lambda **kwargs: real_client(
        transport=httpx.MockTransport(respond), **kwargs,
    ))
    return asyncio.run(OpenAIModelGateway("test-key").compose(
        ModelRequest(sanitized_question="What is my net worth?", intent="net_worth", redacted_context={}, tool_results=[]),
    ))


def test_reads_rest_output_after_reasoning_and_combines_text(monkeypatch):
    body = {"status": "completed", "output": [
        {"type": "reasoning", "summary": []},
        message("Your evidence shows your financial position.", "See the evidence card."),
    ]}
    assert compose(monkeypatch, body) == (
        "Your evidence shows your financial position.\nSee the evidence card."
    )


def test_sends_only_the_model_request_and_disables_response_storage(monkeypatch):
    real_client = httpx.AsyncClient
    captured = {}

    def respond(request):
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"status": "completed", "output": [
            message("Your verified evidence is available in the card."),
        ]})

    monkeypatch.setattr(model_gateway.httpx, "AsyncClient", lambda **kwargs: real_client(
        transport=httpx.MockTransport(respond), **kwargs,
    ))
    asyncio.run(OpenAIModelGateway("test-key").compose(ModelRequest(
        sanitized_question="Is my PAN [REDACTED_PAN] visible?",
        intent="net_worth",
        redacted_context={"total_assets": {"value": "100.00"}},
        tool_results=[],
    )))

    model_input = json.loads(captured["input"])
    assert captured["store"] is False
    assert model_input["sanitized_question"] == "Is my PAN [REDACTED_PAN] visible?"
    assert set(model_input) == {"sanitized_question", "intent", "verified_context", "deterministic_evidence"}


@pytest.mark.parametrize("model_used", [False, True])
def test_agent_response_exposes_whether_the_llm_was_used(model_used):
    response = MessageResponse(
        message_id="5d4a312c-e1e2-44f4-bb47-4fa8946eae0f",
        run_id="e405d3e3-fa0e-4b59-9b65-9bd4ce4caf32",
        content="Local answer.",
        blocks=[],
        model_used=model_used,
        created_at="2026-09-06T00:00:00Z",
    )
    assert response.model_used is model_used


def test_automatic_model_hook_invokes_gateway_when_enabled(monkeypatch):
    calls = []

    class FakeGateway:
        def __init__(self, api_key):
            calls.append(("init", api_key))

        async def compose(self, request):
            calls.append(("compose", request.sanitized_question))
            return "Plain-language explanation."

    monkeypatch.setattr(agent_v1, "MODEL_GATEWAY_FACTORY", FakeGateway)
    explanation = asyncio.run(compose_automatic_explanation(
        SimpleNamespace(automatic_model_enabled=True, openai_api_key="test-key"),
        ModelRequest(sanitized_question="What is an index fund?", intent="general_education", redacted_context={}, tool_results=[]),
    ))

    assert explanation == "Plain-language explanation."
    assert calls == [("init", "test-key"), ("compose", "What is an index fund?")]


def test_automatic_model_hook_skips_gateway_when_disabled(monkeypatch):
    monkeypatch.setattr(agent_v1, "MODEL_GATEWAY_FACTORY", lambda _key: pytest.fail("gateway called"))
    explanation = asyncio.run(compose_automatic_explanation(
        SimpleNamespace(automatic_model_enabled=False, openai_api_key="test-key"),
        ModelRequest(sanitized_question="What is an index fund?", intent="general_education", redacted_context={}, tool_results=[]),
    ))
    assert explanation is None


@pytest.mark.parametrize("body", [
    {"status": "completed", "output": []},
    {"status": "incomplete", "output": [message("Partial explanation.")]},
    {"status": "failed", "output": []},
    {"status": "completed", "output": [message("Your balance is 100.")]},
    {"status": "completed", "output": [message(" ")]},
    {"status": "completed", "output": [{
        "type": "message", "role": "assistant", "status": "completed",
        "content": [{"type": "refusal", "refusal": "Cannot answer."}],
    }]},
    {"output_text": "SDK convenience fields are not a REST response."},
])
def test_rejects_unusable_or_unsafe_output(monkeypatch, body):
    with pytest.raises(ModelSafetyError):
        compose(monkeypatch, body)


@pytest.mark.parametrize("status_code", [401, 429, 500])
def test_http_errors_remain_failures(monkeypatch, status_code):
    with pytest.raises(httpx.HTTPStatusError):
        compose(monkeypatch, {"error": {"message": "Simulated failure"}}, status_code)
