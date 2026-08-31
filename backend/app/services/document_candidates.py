"""Normalized document candidates and explicit promotion to verified memory."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.agent import AuditEvent
from app.models.document import DocumentCandidate, DocumentStorage
from app.services.financial_context import ALLOWED_FACT_TYPES, FinancialContextService


def create_normalized_candidate(
    db: Session, *, document: DocumentStorage, fact_type: str, value: Decimal,
    unit: str, confidence: Decimal, source_location: str | None,
) -> DocumentCandidate:
    if document.virus_scan_status != "clean" or document.extraction_status != "completed":
        raise ValueError("Candidates require clean scan and completed sandboxed extraction")
    if fact_type not in ALLOWED_FACT_TYPES or value < 0 or not Decimal("0") <= confidence <= Decimal("1"):
        raise ValueError("Invalid normalized document candidate")
    candidate = DocumentCandidate(
        document_id=document.document_id, user_id=document.user_id,
        fact_type=fact_type, value=value, unit=unit, confidence=confidence,
        source_location=source_location, status="candidate",
    )
    db.add(candidate)
    db.flush()
    return candidate


def decide_document_candidate(
    db: Session, *, user_id: UUID, candidate_id: UUID, decision: str,
) -> DocumentCandidate:
    candidate = db.query(DocumentCandidate).filter(
        DocumentCandidate.candidate_id == candidate_id,
        DocumentCandidate.user_id == user_id,
    ).with_for_update().first()
    if candidate is None:
        raise LookupError("Document candidate not found")
    if candidate.status != "candidate":
        raise ValueError("Document candidate has already been decided")
    now = datetime.now(timezone.utc)
    if decision == "reject":
        candidate.status = "rejected"
    elif decision == "confirm":
        document = db.query(DocumentStorage).filter(
            DocumentStorage.document_id == candidate.document_id,
            DocumentStorage.user_id == user_id,
            DocumentStorage.virus_scan_status == "clean",
        ).first()
        if document is None:
            raise ValueError("Document is not eligible for candidate confirmation")
        fact = FinancialContextService(db, user_id).create_candidate(
            fact_type=candidate.fact_type, value=Decimal(candidate.value), unit=candidate.unit,
            source_type="verified_document", source_id=str(candidate.document_id),
            observed_at=document.upload_timestamp, confidence=Decimal(candidate.confidence),
        )
        FinancialContextService(db, user_id).decide(fact.fact_id, "confirm")
        candidate.status = "confirmed"
        candidate.linked_fact_id = fact.fact_id
    else:
        raise ValueError("Decision must be confirm or reject")
    candidate.decided_at = now
    db.add(AuditEvent(user_id=user_id, event_type="document_candidate_decided", target_type="document_candidate", target_id=str(candidate.candidate_id), outcome="success", metadata_json={"decision": decision, "fact_type": candidate.fact_type}))
    return candidate
