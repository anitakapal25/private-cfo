from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services import document_extraction
from app.services.document_extraction import (
    DocumentExtractionError,
    extract_pdf_text_sandboxed,
    parse_candidate_values,
)


def test_parser_accepts_only_direct_allowlisted_monthly_label():
    values = parse_candidate_values(
        "salary_slip",
        "Employee: Test User\nNet Pay: INR 1,23,456.78\nAnnual gross: 2000000\n",
    )
    assert len(values) == 1
    assert values[0].fact_type == "monthly_income"
    assert values[0].value == Decimal("123456.78")
    assert values[0].confidence == Decimal("0.9000")


def test_parser_does_not_infer_bank_balance_or_ambiguous_duplicate():
    assert parse_candidate_values("bank_statement", "Closing balance: INR 50000") == []
    assert parse_candidate_values("salary_slip", "Net Pay: 100\nNet Salary: 200") == []


def test_sandboxed_extraction_uses_no_network_boundary_and_removes_plaintext(tmp_path, monkeypatch):
    encrypted = tmp_path / "document.pdf.enc"
    encrypted.write_bytes(b"encrypted")
    sandbox = tmp_path / "bwrap"
    extractor = tmp_path / "pdftotext"
    sandbox.write_bytes(b"")
    extractor.write_bytes(b"")
    monkeypatch.setattr(document_extraction, "decrypt_bytes", lambda _: b"%PDF-safe")
    observed = {}

    def run(command, **kwargs):
        observed["command"] = command
        kwargs["stdout"].write(b"Net Pay: INR 1000.00\n")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(document_extraction.subprocess, "run", run)
    quarantine = tmp_path / "quarantine"
    text = extract_pdf_text_sandboxed(
        encrypted_path=encrypted, quarantine_dir=quarantine,
        sandbox_path=sandbox, pdf_text_path=extractor,
    )
    assert text == "Net Pay: INR 1000.00\n"
    assert "--unshare-all" in observed["command"]
    assert "--clearenv" in observed["command"]
    assert list(quarantine.iterdir()) == []


def test_sandbox_failure_leaves_no_plaintext(tmp_path, monkeypatch):
    encrypted = tmp_path / "document.pdf.enc"
    encrypted.write_bytes(b"encrypted")
    sandbox = tmp_path / "bwrap"
    extractor = tmp_path / "pdftotext"
    sandbox.write_bytes(b"")
    extractor.write_bytes(b"")
    monkeypatch.setattr(document_extraction, "decrypt_bytes", lambda _: b"%PDF-safe")
    monkeypatch.setattr(
        document_extraction.subprocess, "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1),
    )
    quarantine = tmp_path / "quarantine"
    with pytest.raises(DocumentExtractionError, match="failed closed"):
        extract_pdf_text_sandboxed(
            encrypted_path=encrypted, quarantine_dir=quarantine,
            sandbox_path=sandbox, pdf_text_path=extractor,
        )
    assert list(quarantine.iterdir()) == []
