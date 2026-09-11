import base64
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("start_demo", Path(__file__).resolve().parents[1] / "start_demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def test_demo_rejects_other_environments(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError):
        demo.configure_demo()


def test_demo_requires_generated_secrets(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "demo")
    monkeypatch.delenv("DEMO_PASSWORD", raising=False)
    with pytest.raises(RuntimeError):
        demo.configure_demo()


def test_demo_disables_external_services_and_keeps_mfa(monkeypatch):
    monkeypatch.setattr(demo.os, "environ", {
        "ENVIRONMENT": "demo", "JWT_SECRET": "j" * 40,
        "DEMO_ENCRYPTION_SEED": "e" * 40, "DEMO_PASSWORD": "p" * 40,
        "ENABLE_EXTERNAL_MODEL": "true", "ENABLE_PUBLIC_REGISTRATION": "true",
        "ENABLE_MFA": "false",
    })
    demo.configure_demo()
    assert demo.os.environ["ENABLE_EXTERNAL_MODEL"] == "false"
    assert demo.os.environ["ENABLE_PUBLIC_REGISTRATION"] == "false"
    assert demo.os.environ["ENABLE_MFA"] == "true"
    assert len(base64.urlsafe_b64decode(demo.os.environ["ENCRYPTION_KEY"])) == 32
