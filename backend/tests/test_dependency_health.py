"""The dependency gate should identify deprecated application APIs precisely."""

import importlib.util
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "dependency_health",
    Path(__file__).resolve().parents[2] / "scripts/check_dependency_health.py",
)
dependency_health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dependency_health)


def test_deprecated_api_findings_cover_supported_cleanup_rules():
    source = """
from sqlalchemy.ext.declarative import declarative_base

class Example:
    class Config:
        from_attributes = True

value = datetime.utcnow()
payload = request.dict(exclude_unset=True)
"""

    messages = [message for _, message in dependency_health.deprecated_api_findings(source)]

    assert len(messages) == 4
    assert any("Pydantic class Config" in message for message in messages)
    assert any("utcnow" in message for message in messages)
    assert any("model_dump" in message for message in messages)
    assert any("sqlalchemy.orm" in message for message in messages)


def test_deprecated_api_findings_ignore_unrelated_dict_calls_and_comments():
    source = """
# datetime.utcnow() and request.dict(exclude_unset=True) are documentation examples.
payload = ordinary_mapping.dict()
"""

    assert dependency_health.deprecated_api_findings(source) == []
