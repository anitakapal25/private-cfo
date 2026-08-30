"""Fail CI for common repository secret and unsafe-route regressions."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", "node_modules", "dist", "uploads", "__pycache__"}
TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".json", ".md", ".yml", ".yaml", ".toml"}

PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "JWT token": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "hardcoded production-like secret": re.compile(
        r"(?i)(?:secret|password|api[_-]?key)\s*=\s*['\"][^'\"]{20,}['\"]"
    ),
}


def iter_text_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        yield path


def main() -> int:
    findings: list[str] = []
    for path in iter_text_files():
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                findings.append(f"{path.relative_to(ROOT)}: possible {label}")

    agent_router = (ROOT / "backend/app/routers/agent.py").read_text()
    if "Depends(get_current_active_user)" not in agent_router:
        findings.append("backend/app/routers/agent.py: authentication guard is missing")

    forbidden_tracked_roots = (ROOT / "uploads", ROOT / ".env")
    for path in forbidden_tracked_roots:
        if path.is_file():
            findings.append(f"{path.relative_to(ROOT)}: sensitive runtime file exists in repository")

    if findings:
        print("Repository guardrail failures:")
        print("\n".join(f"- {finding}" for finding in findings))
        return 1
    print("Repository guardrails passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

