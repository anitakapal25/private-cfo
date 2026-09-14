"""Synthetic account journeys; ARTHA_TEST_DATABASE_URL must be disposable PostgreSQL."""
import os
from datetime import timedelta
from uuid import uuid4

import pytest
import asyncio
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import get_db, get_settings
from app.models.auth import AuthChallenge
from app.models.user import Profile
from app.auth.manager import now_utc, token_hash, totp_code, totp_step
from app.services.email_delivery import EmailDeliveryUnavailableError
from test_public_authentication import registration_settings


@pytest.fixture
def journey(monkeypatch):
    url = os.environ.get("ARTHA_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Disposable PostgreSQL URL not supplied")
    engine = create_engine(url)
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(connection, join_transaction_mode="create_savepoint")
    settings = registration_settings()
    monkeypatch.setattr("app.auth.manager.get_settings", lambda: settings)
    monkeypatch.setattr("app.core.crypto.get_settings", lambda: settings)
    class Mail:
        tokens = []
        fail = False
        async def send_verification(self, recipient, token):
            if self.fail:
                raise EmailDeliveryUnavailableError("Synthetic delivery failure")
            self.tokens.append(token)
        send_password_reset = send_verification
    mail = Mail()
    monkeypatch.setattr("app.auth.router.delivery_for", lambda settings: mail)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        class Client:
            def request(self, method, path, **kwargs):
                async def send():
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
                        return await client.request(method, path, **kwargs)
                return asyncio.run(send())
            def post(self, path, **kwargs):
                return self.request("POST", path, **kwargs)
            def get(self, path, **kwargs):
                return self.request("GET", path, **kwargs)
        yield Client(), db, mail
    finally:
        app.dependency_overrides.clear()
        db.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


def test_registration_verification_mfa_reset_logout(journey):
    client, db, mail = journey
    email = f"{uuid4()}@example.com"
    password = "Synthetic" + uuid4().hex + "123"
    register = lambda: client.post("/api/auth/register", json={"email": email, "password": password})
    login = lambda pw=password: client.post("/api/auth/token", data={"username": email, "password": pw})
    assert client.post("/api/auth/register", json={"email": email, "password": "weak"}).status_code == 422
    response = register()
    assert response.status_code == 202
    assert register().json() == response.json()
    assert login().json() == {"email_verification_required": True}
    first = mail.tokens[-1]
    assert client.post("/api/auth/verification/resend", json={"email": email}).status_code == 202
    second = mail.tokens[-1]
    assert first != second
    assert client.post("/api/auth/verify-email", json={"token": first}).status_code == 400
    assert client.post("/api/auth/verify-email", json={"token": second}).status_code == 200
    assert client.post("/api/auth/verify-email", json={"token": second}).status_code == 400
    start = login().json()
    assert start["mfa_enrollment_required"]
    assert "access_token" not in start
    challenge = {"challenge_token": start["mfa_challenge_token"]}
    setup = client.post("/api/auth/mfa/enrollment", json=challenge).json()
    step = totp_step()
    code = totp_code(setup["secret"], step)
    tokens = client.post("/api/auth/mfa/enrollment/confirm", json={**challenge, "code": code}).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    next_challenge = login().json()["mfa_challenge_token"]
    assert client.post("/api/auth/mfa/verify", json={"challenge_token": next_challenge, "code": code}).status_code == 401
    assert client.post("/api/auth/mfa/verify", json={"challenge_token": next_challenge, "code": totp_code(setup['secret'], step + 1)}).status_code == 200
    assert client.post("/api/auth/password-reset", json={"email": email}).status_code == 202
    reset = mail.tokens[-1]
    assert client.post("/api/auth/password-reset/confirm", json={"token": reset, "password": "NewSyntheticPassword123"}).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert login().status_code == 401
    start = login("NewSyntheticPassword123").json()
    assert start["mfa_required"]
    # Issue a fresh synthetic session to exercise logout independently of TOTP time.
    from app.auth.manager import issue_session
    profile = db.query(Profile).filter_by(email_address=email).one()
    tokens = issue_session(db, profile.user)
    db.commit()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_resend_expiry_delivery_rollback_and_limits(journey):
    client, db, mail = journey
    email = f"{uuid4()}@example.com"
    payload = {"email": email, "password": "SyntheticPassword123"}
    mail.fail = True
    assert client.post("/api/auth/register", json=payload).status_code == 503
    assert db.query(Profile).filter_by(email_address=email).first() is None
    mail.fail = False
    assert client.post("/api/auth/register", json=payload).status_code == 202
    token = mail.tokens[-1]
    mail.fail = True
    response = client.post("/api/auth/verification/resend", json={"email": email})
    assert response.status_code == 202
    assert db.query(AuthChallenge).filter_by(secret_hash=token_hash(token)).one().consumed_at is None
    assert client.post("/api/auth/verification/resend", json={"email": "unknown@example.com"}).json() == response.json()
    challenge = db.query(AuthChallenge).filter_by(secret_hash=token_hash(token)).one()
    challenge.expires_at = now_utc() - timedelta(seconds=1)
    db.commit()
    assert client.post("/api/auth/verify-email", json={"token": token}).status_code == 400
    mail.fail = False
    for _ in range(2):
        assert client.post("/api/auth/verification/resend", json={"email": email}).status_code == 202
    assert client.post("/api/auth/verification/resend", json={"email": email}).status_code == 429


def test_account_link_pages_and_desktop_cors(journey):
    client, _, _ = journey
    for path in ("/verify-email", "/reset-password"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["cache-control"] == "no-store"
    response = client.get("/api/auth/capabilities", headers={"Origin": "tauri://localhost"})
    assert response.headers["access-control-allow-origin"] == "tauri://localhost"
    response = client.get("/api/auth/capabilities", headers={"Origin": "https://untrusted.example"})
    assert "access-control-allow-origin" not in response.headers


def test_real_browser_and_desktop_registration(journey, tmp_path):
    """Opt-in Chrome journey against real API/DB with intercepted synthetic email only."""
    if os.environ.get("ARTHA_BROWSER_AUTH_TEST") != "1":
        pytest.skip("Set ARTHA_BROWSER_AUTH_TEST=1 after building frontend to run Chrome")
    import socket
    import subprocess
    import threading
    from pathlib import Path
    import uvicorn
    _, _, mail = journey
    capture = tmp_path / "synthetic-token.txt"
    original = mail.send_verification
    async def capture_mail(recipient, token):
        await original(recipient, token)
        capture.write_text(token)
    mail.send_verification = capture_mail
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False, lifespan="off"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        frontend = Path(__file__).resolve().parents[2] / "frontend"
        result = subprocess.run(
            ["node", "tests/integration/registration.mjs"], cwd=frontend,
            env={**os.environ, "ARTHA_BROWSER_URL": f"http://127.0.0.1:{port}", "ARTHA_TEST_MAIL_CAPTURE": str(capture)},
            capture_output=True, text=True, timeout=90,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
