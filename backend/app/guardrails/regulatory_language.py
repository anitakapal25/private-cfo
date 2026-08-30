"""Conservative language boundary for unlicensed personalized guidance."""

import re
from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"


@dataclass(frozen=True)
class GuardrailDecision:
    decision: Decision
    reason: str | None = None
    safe_response: str | None = None


PROHIBITED_PATTERNS = (
    r"\b(?:buy|sell|short|trade)\b.{0,50}\b(?:stock|share|fund|etf|bond|gold|crypto)\b",
    r"\bguaranteed\s+(?:return|profit|income)\b",
    r"\bwhich\s+(?:stock|share|mutual fund|etf|bond)\s+should\s+i\b",
)

PERSONALIZED_ADVICE_PATTERNS = (
    r"\b(?:investment|portfolio|rebalance|asset allocation|investment advice|portfolio recommendation)\b",
    r"\b(?:insurance needs|recommended insurance|coverage should i)\b",
    r"\brecommend(?:ed|ation)?\b.{0,40}\b(?:portfolio|investment|insurance|fund|stock)\b",
)


def evaluate_financial_request(text: str) -> GuardrailDecision:
    normalized = " ".join(text.lower().split())
    if any(re.search(pattern, normalized) for pattern in PROHIBITED_PATTERNS):
        return GuardrailDecision(
            Decision.BLOCK,
            "specific_product_or_guaranteed_outcome",
            "I can explain financial concepts and show calculations, but I cannot tell you to buy, sell, or expect a guaranteed outcome from a specific product.",
        )
    if any(re.search(pattern, normalized) for pattern in PERSONALIZED_ADVICE_PATTERNS):
        return GuardrailDecision(
            Decision.BLOCK,
            "personalized_regulated_guidance",
            "I can show your verified figures and explain general planning principles, but personalized investment or insurance recommendations require an appropriately licensed professional.",
        )
    return GuardrailDecision(Decision.ALLOW)
