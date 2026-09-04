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


def test_parser_extracts_each_supported_document_type():
    cases = (
        ("bank_statement", "Closing balance: INR 50,000", "bank_account_balance", Decimal("50000.00")),
        ("epf_statement", "Total EPF Balance: INR 5,34,500", "epf_balance", Decimal("534500.00")),
        ("form_16", "Gross Salary: INR 11,40,000", "annual_gross_income", Decimal("1140000.00")),
        ("insurance_policy", "Sum Assured: INR 50,00,000", "insurance_coverage", Decimal("5000000.00")),
    )
    for document_type, text, fact_type, amount in cases:
        values = parse_candidate_values(document_type, text)
        assert len(values) == 1
        assert values[0].fact_type == fact_type
        assert values[0].value == amount


def test_bank_statement_extracts_separate_monthly_totals_for_the_stated_month():
    values = parse_candidate_values(
        "bank_statement",
        "Statement Period: 01 August 2026 to 31 August 2026\n"
        "Total Income Credits: INR 87,600.00\n"
        "Total Living Expense Debits: INR 36,500.00\n"
        "Total EMI Debits: INR 12,000.00\nClosing Balance: INR 1,59,100.00\n",
    )
    monthly = {value.fact_type: value for value in values if value.fact_type.startswith("monthly_")}
    assert monthly["monthly_income"].value == Decimal("87600.00")
    assert monthly["monthly_expenses"].value == Decimal("36500.00")
    assert monthly["monthly_debt_payments"].value == Decimal("12000.00")
    assert {value.period_start for value in monthly.values()} == {"2026-08-01"}


def test_bank_statement_does_not_infer_expenses_without_a_direct_total():
    values = parse_candidate_values(
        "bank_statement",
        "Statement Period: 01 August 2026 to 31 August 2026\n"
        "05 August 2026 Rent payment INR 25,000.00\n"
        "25 August 2026 Home loan EMI INR 12,000.00\nClosing Balance: INR 50,000.00\n",
    )
    assert all(not value.fact_type.startswith("monthly_") for value in values)


def test_parser_rejects_ambiguous_duplicate():
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
