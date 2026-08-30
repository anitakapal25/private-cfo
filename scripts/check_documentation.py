"""Validate documentation status markers and local Markdown links."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def main() -> int:
    findings: list[str] = []
    for path in DOCS.rglob("*.md"):
        content = path.read_text(encoding="utf-8")
        if "**Status:**" not in content:
            findings.append(f"{path.relative_to(ROOT)}: missing status marker")
        if "**Last reviewed:**" not in content:
            findings.append(f"{path.relative_to(ROOT)}: missing last-reviewed date")
        for target in LINK_PATTERN.findall(content):
            target = target.strip().split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                findings.append(f"{path.relative_to(ROOT)}: link escapes repository: {target}")
                continue
            if not resolved.exists():
                findings.append(f"{path.relative_to(ROOT)}: broken local link: {target}")

    if findings:
        print("Documentation checks failed:")
        print("\n".join(f"- {finding}" for finding in findings))
        return 1
    print("Documentation checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
