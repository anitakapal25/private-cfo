"""Local, network-isolated PDF extraction with deterministic candidate parsing."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import subprocess
import tempfile

from app.core.crypto import decrypt_bytes

MAX_EXTRACTED_TEXT_BYTES = 2 * 1024 * 1024
EXTRACTION_TIMEOUT_SECONDS = 20
EXTRACTOR_VERSION = "local-pdf-v1"


class DocumentExtractionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExtractedCandidateValue:
    fact_type: str
    value: Decimal
    unit: str
    confidence: Decimal
    source_location: str


# Only labels whose meaning maps directly to an existing financial fact are
# accepted. Statement balances and annual figures are intentionally excluded:
# a single account is not total liquid assets and annual/monthly conversion
# requires period semantics that generic text extraction cannot prove.
FIELD_PATTERNS: dict[str, tuple[tuple[str, str], ...]] = {
    "salary_slip": (
        ("monthly_income", r"(?im)^\s*(?:net\s+pay|net\s+salary|take[ -]?home\s+(?:pay|salary))\s*[:\-]?\s*(?:₹|rs\.?|inr)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)\s*$"),
    ),
    "insurance_policy": (
        ("insurance_coverage", r"(?im)^\s*(?:sum\s+assured|coverage\s+amount)\s*[:\-]?\s*(?:₹|rs\.?|inr)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)\s*$"),
    ),
}


def parse_candidate_values(document_type: str, text: str) -> list[ExtractedCandidateValue]:
    """Parse allowlisted labels without inferring, aggregating, or converting values."""
    results: list[ExtractedCandidateValue] = []
    for fact_type, pattern in FIELD_PATTERNS.get(document_type, ()):
        matches = list(re.finditer(pattern, text))
        if len(matches) != 1:
            continue
        match = matches[0]
        try:
            value = Decimal(match.group(1).replace(",", ""))
        except InvalidOperation:
            continue
        if value < 0:
            continue
        line_number = text.count("\n", 0, match.start()) + 1
        results.append(ExtractedCandidateValue(
            fact_type=fact_type,
            value=value.quantize(Decimal("0.01")),
            unit="INR",
            confidence=Decimal("0.9000"),
            source_location=f"extracted text line {line_number}",
        ))
    return results


def extract_pdf_text_sandboxed(
    *, encrypted_path: Path, quarantine_dir: Path, sandbox_path: Path,
    pdf_text_path: Path,
) -> str:
    """Decrypt temporarily and execute pdftotext inside a no-network bwrap sandbox."""
    sandbox = sandbox_path.resolve()
    extractor = pdf_text_path.resolve()
    if not sandbox.is_file() or not extractor.is_file():
        raise DocumentExtractionError("Configured local extraction tools are unavailable")
    quarantine_dir = quarantine_dir.resolve()
    quarantine_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    decrypted_path: Path | None = None
    output_path: Path | None = None
    try:
        content = decrypt_bytes(encrypted_path.read_bytes())
        if not content.startswith(b"%PDF-"):
            raise DocumentExtractionError("Only validated PDF documents can be extracted")
        with tempfile.NamedTemporaryFile(dir=quarantine_dir, suffix=".pdf", delete=False) as handle:
            handle.write(content)
            decrypted_path = Path(handle.name)
        decrypted_path.chmod(0o600)
        with tempfile.NamedTemporaryFile(dir=quarantine_dir, suffix=".txt", delete=False) as handle:
            output_path = Path(handle.name)
        output_path.chmod(0o600)
        command = [
            str(sandbox), "--unshare-all", "--die-with-parent", "--new-session",
            "--clearenv", "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
            "--ro-bind", "/lib64", "/lib64",
            "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
            "--ro-bind", str(decrypted_path), "/document.pdf",
            "--setenv", "HOME", "/tmp", "--setenv", "PATH", "/usr/bin:/bin",
            "--", "/usr/bin/prlimit", f"--as={256 * 1024 * 1024}", "--cpu=10",
            f"--fsize={MAX_EXTRACTED_TEXT_BYTES}", "--nofile=64", "--",
            str(extractor), "-layout", "/document.pdf", "-",
        ]
        with output_path.open("wb") as output:
            completed = subprocess.run(
                command, stdin=subprocess.DEVNULL, stdout=output,
                stderr=subprocess.DEVNULL, timeout=EXTRACTION_TIMEOUT_SECONDS,
                check=False,
            )
        if completed.returncode != 0:
            raise DocumentExtractionError("Sandboxed document extraction failed closed")
        if output_path.stat().st_size > MAX_EXTRACTED_TEXT_BYTES:
            raise DocumentExtractionError("Extracted document text exceeded the safety limit")
        return output_path.read_text(encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired as exc:
        raise DocumentExtractionError("Sandboxed document extraction timed out") from exc
    finally:
        for path in (decrypted_path, output_path):
            if path is not None and path.exists():
                path.unlink()
