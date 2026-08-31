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
