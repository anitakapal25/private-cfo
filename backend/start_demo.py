"""Initialize an isolated synthetic Render demo, without printing credentials."""
import base64
import hashlib
import os
import subprocess
import sys


def configure_demo():
    if os.environ.get("ENVIRONMENT") != "demo":
        raise RuntimeError("Demo startup requires ENVIRONMENT=demo")
    for key in ("JWT_SECRET", "DEMO_ENCRYPTION_SEED", "DEMO_PASSWORD"):
        if len(os.environ.get(key, "")) < 32:
            raise RuntimeError("Demo requires generated secrets of at least 32 characters")
    # A separate stable random seed provides a valid Fernet key for MFA storage.
    os.environ["ENCRYPTION_KEY"] = base64.urlsafe_b64encode(
        hashlib.sha256(os.environ["DEMO_ENCRYPTION_SEED"].encode()).digest()
    ).decode()
    for key in (
        "ENABLE_EXTERNAL_MODEL", "ENABLE_PUBLIC_REGISTRATION",
        "ENABLE_FINANCIAL_INTEGRATIONS", "ENABLE_BACKGROUND_SYNC",
        "ENABLE_PROACTIVE_REVIEWS", "ENABLE_EXTERNAL_WEBHOOKS",
        "ENABLE_ADVISOR_ACCESS", "ENABLE_COMMUNITY_BENCHMARKS",
        "ENABLE_WELLNESS_PROGRAMS", "ENABLE_DATA_EXPORTS",
    ):
        os.environ[key] = "false"
    os.environ["EMAIL_DELIVERY_MODE"] = "disabled"
    os.environ["ENABLE_MFA"] = "true"


def main():
    configure_demo()
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    from app.core.config import SessionLocal
    from app.models.user import User, Profile
    from app.auth.manager import get_password_hash

    with SessionLocal() as db:
        if db.query(Profile).filter_by(email_address="demo@example.com").first() is None:
            user = User(hashed_password=get_password_hash(os.environ["DEMO_PASSWORD"]), role="user")
            db.add(user)
            db.flush()
            db.add(Profile(user_id=user.user_id, email_address="demo@example.com",
                           full_name="Synthetic Demo — do not enter real financial data",
                           email_verified=True))
            db.commit()
    os.execvp(sys.executable, [sys.executable, "-m", "uvicorn", "app.main:app",
                              "--host", "0.0.0.0", "--port", os.environ.get("PORT", "8000")])


if __name__ == "__main__":
    main()
