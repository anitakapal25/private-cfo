#!/usr/bin/env python3
"""Stage approved public source changes. Never edits approved education or rules."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.finance_knowledge import CATALOGUE
from app.services.source_refresh import fetch_approved

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic", choices=sorted({e.topic for e in CATALOGUE}))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    entry = next(e for e in CATALOGUE if e.topic == args.topic)
    try:
        metadata, data = fetch_approved(entry.url)
    except Exception:
        print("Source refresh failed; approved content was not changed", file=sys.stderr)
        return 1
    args.output.mkdir(parents=True, exist_ok=True)
    metadata.update(topic=args.topic, fetched_at=datetime.now(timezone.utc).isoformat(), previous_version=entry.version)
    # Binary staging is deliberately never read by the agent; reviewer opens official URL.
    (args.output / f"{args.topic}-{metadata['sha256']}.source").write_bytes(data)
    (args.output / f"{args.topic}-{metadata['sha256']}.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print("Public source staged for review; no runtime content or rules changed")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
