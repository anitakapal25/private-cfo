from pathlib import Path

import pytest

from app.services import document_security
from app.services.document_security import DocumentSecurityError, scan_and_store, validate_document


def test_document_signature_must_match_allowlisted_type():
    with pytest.raises(DocumentSecurityError, match="signature"):
        validate_document("statement.pdf", b"not-a-pdf")


def test_document_size_and_empty_input_fail_closed():
    with pytest.raises(DocumentSecurityError):
        validate_document("statement.pdf", b"")


def scanner(tmp_path: Path, exit_code: int) -> Path:
    path = tmp_path / f"scanner-{exit_code}"
    path.write_text(f"#!/bin/sh\nexit {exit_code}\n", encoding="utf-8")
    path.chmod(0o700)
    return path


def test_clean_scan_encrypts_storage_and_removes_quarantine(tmp_path, monkeypatch):
    monkeypatch.setattr(document_security, "encrypt_bytes", lambda value: b"encrypted:" + value)
    result = scan_and_store(
        filename="statement.pdf", content=b"%PDF-safe-test",
        upload_dir=tmp_path / "uploads", scanner_path=scanner(tmp_path, 0),
    )
    assert Path(result.storage_path).read_bytes() == b"encrypted:%PDF-safe-test"
    assert list((tmp_path / "uploads" / "quarantine").iterdir()) == []


@pytest.mark.parametrize("exit_code,message", [(1, "failed malware"), (2, "failed closed")])
def test_infected_or_failed_scanner_never_stores_document(tmp_path, monkeypatch, exit_code, message):
    monkeypatch.setattr(document_security, "encrypt_bytes", lambda value: value)
    with pytest.raises(DocumentSecurityError, match=message):
        scan_and_store(
            filename="statement.pdf", content=b"%PDF-test",
            upload_dir=tmp_path / "uploads", scanner_path=scanner(tmp_path, exit_code),
        )
    encrypted = tmp_path / "uploads" / "encrypted"
    assert not encrypted.exists() or list(encrypted.iterdir()) == []
