"""Fail-closed validation, quarantine, malware scanning, and encrypted storage."""

from dataclasses import dataclass
import hashlib
from pathlib import Path
import subprocess
import tempfile
import uuid

from app.core.crypto import encrypt_bytes

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
SIGNATURES = {
    ".pdf": (b"%PDF-", "application/pdf"),
    ".jpg": (b"\xff\xd8\xff", "image/jpeg"),
    ".jpeg": (b"\xff\xd8\xff", "image/jpeg"),
    ".png": (b"\x89PNG\r\n\x1a\n", "image/png"),
}


class DocumentSecurityError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredDocument:
    storage_path: str
    checksum_sha256: str
    file_size_bytes: int
    mime_type: str


def validate_document(filename: str, content: bytes) -> tuple[str, str]:
    if not content or len(content) > MAX_DOCUMENT_BYTES:
        raise DocumentSecurityError("Document is empty or exceeds the 10 MB limit")
    suffix = Path(filename).suffix.lower()
    signature = SIGNATURES.get(suffix)
    if signature is None or not content.startswith(signature[0]):
        raise DocumentSecurityError("Document type or signature is not allowed")
    return suffix, signature[1]


def scan_and_store(
    *, filename: str, content: bytes, upload_dir: Path, scanner_path: Path,
) -> StoredDocument:
    suffix, mime_type = validate_document(filename, content)
    scanner = scanner_path.resolve()
    if not scanner.is_file():
        raise DocumentSecurityError("Configured malware scanner is unavailable")
    upload_dir = upload_dir.resolve()
    quarantine = upload_dir / "quarantine"
    stored = upload_dir / "encrypted"
    quarantine.mkdir(parents=True, exist_ok=True, mode=0o700)
    stored.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=quarantine, suffix=suffix, delete=False) as handle:
            handle.write(content)
            temporary_path = Path(handle.name)
        temporary_path.chmod(0o600)
        completed = subprocess.run(
            [str(scanner), str(temporary_path)], capture_output=True, text=True,
            timeout=30, check=False,
        )
        if completed.returncode == 1:
            raise DocumentSecurityError("Document failed malware scanning")
        if completed.returncode != 0:
            raise DocumentSecurityError("Malware scanner failed closed")
        destination = stored / f"{uuid.uuid4()}{suffix}.enc"
        destination.write_bytes(encrypt_bytes(content))
        destination.chmod(0o600)
        return StoredDocument(
            storage_path=str(destination), checksum_sha256=hashlib.sha256(content).hexdigest(),
            file_size_bytes=len(content), mime_type=mime_type,
        )
    except subprocess.TimeoutExpired as exc:
        raise DocumentSecurityError("Malware scanner timed out") from exc
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
