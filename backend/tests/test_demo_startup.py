import base64
import importlib.util
import os
import subprocess
import sys
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


def test_demo_disables_external_services_and_preserves_explicit_auth_delivery(monkeypatch):
    monkeypatch.setattr(demo.os, "environ", {
        "ENVIRONMENT": "demo", "JWT_SECRET": "j" * 40,
        "DEMO_ENCRYPTION_SEED": "e" * 40, "DEMO_PASSWORD": "p" * 40,
        "ENABLE_EXTERNAL_MODEL": "true", "ENABLE_PUBLIC_REGISTRATION": "true",
        "EMAIL_DELIVERY_MODE": "smtp", "ENABLE_MFA": "false",
    })
    demo.configure_demo()
    assert demo.os.environ["ENABLE_EXTERNAL_MODEL"] == "false"
    assert demo.os.environ["ENABLE_PUBLIC_REGISTRATION"] == "true"
    assert demo.os.environ["EMAIL_DELIVERY_MODE"] == "smtp"
    assert demo.os.environ["ENABLE_MFA"] == "true"
    assert len(base64.urlsafe_b64decode(demo.os.environ["ENCRYPTION_KEY"])) == 32


def test_demo_startup_registers_models_in_fresh_process():
    # A fresh interpreter matters: other tests import financial models and can
    # hide missing relationship targets in the standalone deployment entrypoint.
    result = subprocess.run(
        [sys.executable, "-c", '''
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import configure_mappers
import start_demo
start_demo.configure_demo()

def session():
    configure_mappers()
    return MagicMock()

with patch("app.core.config.SessionLocal", side_effect=session), \
     patch("start_demo.subprocess.run") as migrate, \
     patch("start_demo.os.execvp") as launch:
    start_demo.main()
    migrate.assert_called_once()
    launch.assert_called_once()
'''],
        cwd=Path(__file__).resolve().parents[1],
        env={
            "PATH": os.environ.get("PATH", ""),
            "ENVIRONMENT": "demo", "DATABASE_URL": "sqlite://",
            "JWT_SECRET": "j" * 40, "DEMO_ENCRYPTION_SEED": "e" * 40,
            "DEMO_PASSWORD": "p" * 40,
            "ENABLE_PUBLIC_REGISTRATION": "false",
            "EMAIL_DELIVERY_MODE": "disabled",
        },
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
