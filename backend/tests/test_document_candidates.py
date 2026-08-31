from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.document_candidates import create_normalized_candidate


class FakeDb:
    def __init__(self): self.added = []
    def add(self, value): self.added.append(value)
    def flush(self): pass


def document(scan="clean", extraction="completed"):
    return SimpleNamespace(
        document_id=uuid4(), user_id=uuid4(), virus_scan_status=scan,
        extraction_status=extraction,
    )


def test_normalized_candidate_requires_clean_scanned_completed_extraction():
    with pytest.raises(ValueError, match="clean scan"):
        create_normalized_candidate(FakeDb(), document=document(scan="pending"), fact_type="monthly_income", value=Decimal("100"), unit="INR", confidence=Decimal("0.9"), source_location="page 1")
    with pytest.raises(ValueError, match="completed"):
        create_normalized_candidate(FakeDb(), document=document(extraction="blocked"), fact_type="monthly_income", value=Decimal("100"), unit="INR", confidence=Decimal("0.9"), source_location="page 1")


def test_normalized_candidate_remains_non_authoritative():
    db = FakeDb()
    candidate = create_normalized_candidate(db, document=document(), fact_type="monthly_income", value=Decimal("100"), unit="INR", confidence=Decimal("0.9"), source_location="page 1")
    assert candidate.status == "candidate"
    assert candidate.linked_fact_id is None
    assert db.added == [candidate]
