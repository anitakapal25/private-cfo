"""Minimized boundary for automatic external explanation models."""

from dataclasses import dataclass
import json
import re
from typing import Protocol

import httpx


MODEL_POLICY_BUNDLE_VERSION = "cloud-explanation-v1"
NUMERIC_CONTENT = re.compile(r"\d")


@dataclass(frozen=True)
class ModelRequest:
    sanitized_question: str
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
    """Responses API adapter for sanitized questions and verified financial evidence only."""

    def __init__(self, api_key: str, model: str = "gpt-5-mini"):
        self.api_key = api_key
        self.model = model

    async def compose(self, request: ModelRequest) -> str:
        payload = {
            "model": self.model,
            "store": False,
            "instructions": (
                "Answer the sanitized question in plain language using only the supplied verified context and "
                "deterministic evidence. Do not provide personalized investment, insurance, tax, or product advice; "
                "do not rank products, create a shortlist, or issue buy/sell instructions. Do not introduce numbers, "
                "dates, rates, names, or facts. Refer to the evidence card for exact values."
            ),
            "input": json.dumps(
                {
                    "sanitized_question": request.sanitized_question,
                    "intent": request.intent,
                    "verified_context": request.redacted_context,
                    "deterministic_evidence": request.tool_results,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
        }
        timeout = httpx.Timeout(connect=3.0, read=8.0, write=8.0, pool=3.0)
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        response.raise_for_status()
        # output_text is an SDK convenience property, not a raw REST field.
        body = response.json()
        if not isinstance(body, dict) or body.get("status") != "completed":
            raise ModelSafetyError("Model explanation did not complete")
        parts = []
        for item in body.get("output", []):
            if item.get("type") != "message" or item.get("role") != "assistant":
                continue
            if item.get("status") != "completed":
                raise ModelSafetyError("Model explanation did not complete")
            for content in item.get("content", []):
                if content.get("type") == "refusal":
                    raise ModelSafetyError("Model explanation was refused")
                if content.get("type") == "output_text":
                    parts.append(content["text"])
        text = "\n".join(parts).strip()
        if not text or NUMERIC_CONTENT.search(text):
            raise ModelSafetyError("Model explanation was empty or introduced untraceable numeric content")
        return text
