"""Report and fail on expired versioned financial/regulatory assumptions."""

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.guardrails import catalog  # noqa: E402
from app.guardrails.assumption_freshness import VersionedAssumption  # noqa: E402


def main() -> int:
    assumptions = [
        value
        for value in vars(catalog).values()
        if isinstance(value, VersionedAssumption)
    ]
    expired = [item for item in assumptions if date.today() > item.review_by]
    for item in assumptions:
        state = "EXPIRED" if item in expired else "current"
        print(f"{item.identifier}: {state}; review by {item.review_by}; {item.source_url}")
    return 1 if expired else 0


if __name__ == "__main__":
    sys.exit(main())
