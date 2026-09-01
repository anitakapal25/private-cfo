"""Minimized, consent-gated boundary for external explanation models."""

from dataclasses import dataclass
import json
import re
from typing import Protocol

import httpx


MODEL_POLICY_BUNDLE_VERSION = "cloud-explanation-v1"
NUMERIC_CONTENT = re.compile(r"\d")


@dataclass(frozen=True)
class ModelRequest:
    intent: str
    redacted_context: dict
    tool_results: list[dict]


class ModelGateway(Protocol):
    async def compose(self, request: ModelRequest) -> str: ...


class ModelDisabledError(RuntimeError):
    pass


class ModelSafetyError(RuntimeError):
    pass


class DisabledModelGateway:
    async def compose(self, request: ModelRequest) -> str:
        del request
        raise ModelDisabledError(
            "External model use is disabled until privacy review and model safety evaluations pass"
        )


class OpenAIModelGateway:
    """Responses API adapter. It accepts no user prompts, IDs, or document content."""

    def __init__(self, api_key: str, model: str = "gpt-5-mini"):
        self.api_key = api_key
        self.model = model

    async def compose(self, request: ModelRequest) -> str:
        payload = {
            "model": self.model,
            "store": False,
            "instructions": (
                "Explain only the supplied deterministic financial evidence in plain language. "
                "Do not provide investment, insurance, tax, or product advice. Do not introduce "
                "numbers, dates, rates, names, or facts. Refer to the evidence card for exact values."
            ),
            "input": json.dumps(
                {
                    "intent": request.intent,
                    "verified_context": request.redacted_context,
                    "deterministic_evidence": request.tool_results,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        response.raise_for_status()
        text = response.json().get("output_text", "").strip()
        if not text or NUMERIC_CONTENT.search(text):
            raise ModelSafetyError("Model explanation was empty or introduced untraceable numeric content")
        return text
