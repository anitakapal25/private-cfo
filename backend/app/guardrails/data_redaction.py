"""Redaction utilities for logs, telemetry, and future model boundaries."""

import re
from typing import Any

SENSITIVE_KEYS = {
    "aadhaar",
    "aadhaar_number",
    "authorization",
    "content",
    "credentials",
    "document_text",
    "encrypted_credentials",
    "extracted_text",
    "file_content",
    "jwt",
    "pan",
    "password",
    "prompt",
    "raw_prompt",
    "secret",
    "token",
    "transaction_description",
}

TOKEN_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
AADHAAR_PATTERN = re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)")
PAN_PATTERN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE)


def redact_text(value: str) -> str:
    value = TOKEN_PATTERN.sub("[REDACTED_TOKEN]", value)
    value = AADHAAR_PATTERN.sub("[REDACTED_AADHAAR]", value)
    return PAN_PATTERN.sub("[REDACTED_PAN]", value)


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if str(key).lower() in SENSITIVE_KEYS else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    if isinstance(value, str):
        return redact_text(value)
    return value


# The conversational boundary never needs amounts from the current question:
# confirmed amounts come from tools. Years remain available for period resolution.
PRIVATE_TEXT = re.compile(
    r"(?:https?://|(?:[A-Za-z]:[\\/])|/|~/)[^\s]+"
    r"|\b(?:sk-|AKIA)[A-Za-z0-9_-]+"
    r"|\b(?:password|secret|api[_ -]?key|token|account(?: number| no\.?)?|iban|ifsc|upi)\s*(?:(?:is|equals)\s+|[:=]\s*)?\S+"
    r"|[\w.+-]+@[\w.-]+"
    r"|\b[A-Za-z]*\d{5,}[A-Za-z0-9]*\b",
    re.IGNORECASE,
)

def sanitize_question(value: str) -> str:
    value = PRIVATE_TEXT.sub("[REDACTED]", redact_text(value))
    # Preserve only standalone calendar years; all other numeric statements are unverified.
    value = re.sub(r"(?<!\w)(?:₹|rs\.?|inr|\$)?\s*\d[\d,.]*(?:\s*(?:lakh|crore|thousand|million|%))?",
                   lambda m: m.group(0) if re.fullmatch(r"\s*(?:19|20)\d{2}", m.group(0)) else " [UNVERIFIED_VALUE]", value, flags=re.I)
    value = re.sub(r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|lakh|crore|million|billion)\b(?:[ -]+(?:and[ -]+)?(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|lakh|crore|million|billion))?", "[UNVERIFIED_VALUE]", value, flags=re.I)
    return value[:4000]
