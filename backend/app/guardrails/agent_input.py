"""Conservative input boundary for prompt-injection and data-exfiltration attempts."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class InputDecision:
    allowed: bool
    reason: str | None = None


BLOCKED_PATTERNS = (
    r"\bignore\b.{0,50}\b(?:system|developer|previous)\b.{0,30}\binstructions?\b",
    r"\b(?:reveal|print|show|return)\b.{0,60}\b(?:system prompt|developer message|secret|token|credentials?)\b",
    r"\b(?:another|other)\s+users?'?\b.{0,60}\b(?:data|finances|account|conversation|document)\b",
    r"\b(?:override|impersonate|switch)\b.{0,40}\buser(?:_id| id)?\b",
)


def evaluate_agent_input(text: str) -> InputDecision:
    normalized = " ".join(text.lower().split())
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, normalized):
            return InputDecision(False, "prompt_injection_or_data_exfiltration")
    return InputDecision(True)
