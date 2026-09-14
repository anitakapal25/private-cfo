"""Fail when locked frontend packages are marked deprecated or requirements are unpinned."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_LOCK = ROOT / "frontend" / "package-lock.json"
BACKEND_REQUIREMENTS = ROOT / "backend" / "requirements.txt"


def check_frontend_lock() -> list[str]:
    try:
        lock = json.loads(FRONTEND_LOCK.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"frontend/package-lock.json cannot be read: {exc}"]

    packages = lock.get("packages")
    if not isinstance(packages, dict):
        return ["frontend/package-lock.json has no package metadata; regenerate it with npm install"]

    findings: list[str] = []
    for path, package in sorted(packages.items()):
        if not path.startswith("node_modules/") or not isinstance(package, dict):
            continue
        deprecation = package.get("deprecated")
        if isinstance(deprecation, str) and deprecation.strip():
            findings.append(
                f"frontend/{path} ({package.get('version', 'unknown version')}): {deprecation.strip()}"
            )
    return findings


def check_backend_requirements() -> list[str]:
    findings: list[str] = []
    for line_number, raw_line in enumerate(BACKEND_REQUIREMENTS.read_text(encoding="utf-8").splitlines(), start=1):
        requirement = raw_line.strip()
        if not requirement or requirement.startswith("#"):
            continue
        if "==" not in requirement:
            findings.append(
                f"backend/requirements.txt:{line_number}: dependencies must use exact versions ({requirement})"
            )
    return findings


def deprecated_api_findings(source: str) -> list[tuple[int, str]]:
    """Inspect syntax, ignoring comments and ordinary dictionary operations."""
    tree = ast.parse(source)
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Config":
            findings.append((node.lineno, "Pydantic class Config is deprecated; use model_config = ConfigDict(...)"))
        elif isinstance(node, ast.Attribute) and node.attr == "utcnow":
            findings.append((node.lineno, "utcnow is deprecated; use timezone-aware UTC timestamps"))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "dict" and any(k.arg == "exclude_unset" for k in node.keywords):
            findings.append((node.lineno, "Pydantic dict(exclude_unset=...) is deprecated; use model_dump"))
        elif isinstance(node, ast.ImportFrom) and node.module == "sqlalchemy.ext.declarative" and any(n.name == "declarative_base" for n in node.names):
            findings.append((node.lineno, "Use sqlalchemy.orm.declarative_base instead of sqlalchemy.ext.declarative"))
    return findings


def check_deprecated_python_apis() -> list[str]:
    findings: list[str] = []
    # Historical migrations and test fixtures are not application modernization targets.
    for path in sorted((ROOT / "backend" / "app").rglob("*.py")):
        for line, message in deprecated_api_findings(path.read_text(encoding="utf-8")):
            findings.append(f"{path.relative_to(ROOT)}:{line}: {message}")
    return findings


def main() -> int:
    findings = check_frontend_lock() + check_backend_requirements() + check_deprecated_python_apis()
    if findings:
        print("Dependency health checks failed:")
        print("\n".join(f"- {finding}" for finding in findings))
        return 1
    print("Dependency health checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
