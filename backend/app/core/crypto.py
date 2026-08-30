"""Fail-closed encryption helpers for secrets and uploaded documents."""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class EncryptionConfigurationError(RuntimeError):
    pass


def get_fernet() -> Fernet:
    key = get_settings().encryption_key
    if not key:
        raise EncryptionConfigurationError(
            "ENCRYPTION_KEY is required for sensitive data operations"
        )
    try:
        return Fernet(key.encode())
    except (TypeError, ValueError) as exc:
        raise EncryptionConfigurationError("ENCRYPTION_KEY is not a valid Fernet key") from exc


def encrypt_secret(value: str) -> str:
    return get_fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    try:
        return get_fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Encrypted value cannot be decrypted") from exc


def encrypt_bytes(value: bytes) -> bytes:
    return get_fernet().encrypt(value)


def decrypt_bytes(value: bytes) -> bytes:
    try:
        return get_fernet().decrypt(value)
    except InvalidToken as exc:
        raise ValueError("Encrypted document cannot be decrypted") from exc
