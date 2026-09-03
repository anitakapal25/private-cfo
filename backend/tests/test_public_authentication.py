"""Unit coverage for public-account security primitives and route surface."""

from types import SimpleNamespace
from email.message import EmailMessage

import pytest
from fastapi.routing import APIRoute

from app.auth.manager import generate_totp_secret, get_password_hash, password_is_strong, totp_code, totp_step, verify_password, verify_totp
from app.core.config import Settings
from app.main import app
from app.models.auth import AuthChallenge, AuthRateLimitEvent, AuthSession, MfaCredential
from app.services.email_delivery import SmtpEmailDelivery


def test_new_passwords_use_argon2id_and_reject_weak_values():
    candidate = "LongerSecurePassword123"
    encoded = get_password_hash(candidate)

    assert encoded.startswith("$argon2id$")
    assert verify_password(candidate, encoded)
    assert not verify_password("incorrect-password", encoded)
    assert not password_is_strong("short")
    with pytest.raises(ValueError, match="12 characters"):
        get_password_hash("alllowercasepassword")


def test_totp_accepts_a_current_code_once_only():
    secret = generate_totp_secret()
    step = totp_step()
    code = totp_code(secret, step)

    assert verify_totp(secret, code) == step
    assert verify_totp(secret, code, last_used_step=step) is None
    assert verify_totp(secret, "not-a-code") is None


def test_public_registration_requires_configured_smtp_delivery():
    with pytest.raises(ValueError, match="Public registration requires SMTP"):
        Settings(
            _env_file=None,
            environment="test",
            jwt_secret="test-secret",
            enable_public_registration=True,
        )


def test_smtp_delivery_uses_starttls_for_postmark_compatible_configuration(monkeypatch):
    calls: list[str] = []

    class FakeSmtpClient:
        def __init__(self, *args, **kwargs):
            calls.append("connect")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def ehlo(self):
            calls.append("ehlo")

        def starttls(self, **kwargs):
            calls.append("starttls")

        def login(self, username, password):
            assert username == "postmark-access-key"
            assert password == "postmark-secret-key"
            calls.append("login")

        def send_message(self, message):
            assert message["From"] == "no-reply@example.com"
            calls.append("send")

    monkeypatch.setattr("app.services.email_delivery.smtplib.SMTP", FakeSmtpClient)
    settings = SimpleNamespace(
        public_app_url="https://app.example.com",
        email_from_address="no-reply@example.com",
        smtp_host="smtp.postmarkapp.com",
        smtp_port=587,
        smtp_security="starttls",
        smtp_username="postmark-access-key",
        smtp_password="postmark-secret-key",
    )

    message = EmailMessage()
    message["From"] = "no-reply@example.com"
    SmtpEmailDelivery(settings)._deliver(message)

    assert calls == ["connect", "ehlo", "starttls", "ehlo", "login", "send"]


def test_authentication_tables_keep_only_hashed_or_encrypted_secrets():
    assert "refresh_token_hash" in AuthSession.__table__.columns
    assert "secret_hash" in AuthChallenge.__table__.columns
    assert "encrypted_totp_secret" in MfaCredential.__table__.columns
    assert "subject_hash" in AuthRateLimitEvent.__table__.columns
    for table in (AuthSession.__table__, AuthChallenge.__table__, AuthRateLimitEvent.__table__):
        assert "refresh_token" not in table.columns
        assert "token" not in table.columns
        assert "email" not in table.columns
        assert "ip_address" not in table.columns


def test_public_auth_routes_include_verification_mfa_refresh_and_revocation():
    paths = {route.path for route in app.routes if isinstance(route, APIRoute)}
    expected = {
        "/api/auth/register", "/api/auth/verify-email", "/api/auth/password-reset",
        "/api/auth/password-reset/confirm", "/api/auth/mfa/enrollment",
        "/api/auth/mfa/enrollment/confirm", "/api/auth/mfa/verify",
        "/api/auth/refresh", "/api/auth/logout",
    }
    assert expected <= paths
