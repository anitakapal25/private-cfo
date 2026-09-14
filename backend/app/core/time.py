"""UTC timestamps for persistence and existing legacy wire formats."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def legacy_utc_isoformat() -> str:
    """Preserve the timezone-less UTC strings used by legacy API payloads."""
    return utc_now().replace(tzinfo=None).isoformat()
