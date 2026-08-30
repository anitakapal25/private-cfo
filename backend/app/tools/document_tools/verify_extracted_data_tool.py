from app.tools.document_tools.base_document_tool import BaseDocumentTool
from typing import Dict, Any
from datetime import datetime
from app.core.config import get_db
from app.models.document import DocumentStorage, ExtractedField
from app.guardrails.data_redaction import redact_text
import logging
import uuid

logger = logging.getLogger(__name__)

class VerifyExtractedDataTool(BaseDocumentTool):
    """Tool for verifying and correcting extracted document data"""

    def __init__(self):
        super().__init__()
        self.name = "VerifyExtractedDataTool"
        self.description = "Verify and correct data extracted from financial documents"

    def get_description(self) -> str:
        """Get a human-readable description of what this tool does.

        Returns:
            String description of the tool's purpose and functionality
        """
        return self.description

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify or correct extracted data from a document

        Expected input:
        {
            "document_id": "uuid-string",
            "user_id": "uuid-string",
            "field_corrections": {  # Optional: field name -> corrected value
                "gross_salary": 1750000,
                "employee_name": "Test User Corrected"
            },
            "verified": true  # Whether to mark as verified
        }
        """
        try:
            document_id = input_data.get("document_id")
            user_id = input_data.get("user_id")
            field_corrections = input_data.get("field_corrections", {})
            verified = input_data.get("verified", False)

            if not document_id or not user_id:
                return {
                    "error": "Missing required fields: document_id, user_id"
                }

            # Get document from database
            db = next(get_db())
            try:
                document = db.query(DocumentStorage).filter(
                    DocumentStorage.document_id == uuid.UUID(document_id),
                    DocumentStorage.user_id == uuid.UUID(user_id)
                ).first()

                if not document:
                    return {
                        "error": "Document not found or access denied"
                    }

                if document.extraction_status != "completed":
                    return {
                        "error": f"Document extraction not completed. Current status: {document.extraction_status}"
                    }

                # Start with current extracted data
                extracted_data = document.extracted_data.copy() if document.extracted_data else {}

                # Apply field corrections if provided
                corrections_applied = {}
                if field_corrections:
                    # Flatten the extracted data for easier matching
                    def flatten_dict(d, parent_key='', sep='_'):
                        items = []
                        for k, v in d.items():
                            new_key = f"{parent_key}{sep}{k}" if parent_key else k
                            if isinstance(v, dict):
                                items.extend(flatten_dict(v, new_key, sep=sep).items())
                            else:
                                items.append((new_key, v))
                        return dict(items)

                    flat_extracted = flatten_dict(extracted_data)

                    for field_name, corrected_value in field_corrections.items():
                        # Try to find the field in flattened data
                        if field_name in flat_extracted:
                            # Update the value
                            old_value = flat_extracted[field_name]
                            flat_extracted[field_name] = corrected_value
                            corrections_applied[field_name] = {
                                "old": old_value,
                                "new": corrected_value
                            }
                        else:
                            # Try to find in nested structure (simplified)
                            found = False
                            for top_key, top_value in extracted_data.items():
                                if isinstance(top_value, dict) and field_name in top_value:
                                    old_value = top_value[field_name]
                                    top_value[field_name] = corrected_value
                                    corrections_applied[field_name] = {
                                        "old": old_value,
                                        "new": corrected_value
                                    }
                                    found = True
                                    break
                            if not found:
                                # Field not found, could be a new field or error
                                pass

                    # Reconstruct nested structure from flattened data (simplified approach)
                    # For this implementation, we'll update known fields directly
                    # In a production system, you'd have a more robust mapping

                    # Update specific known fields if they exist in corrections
                    known_fields = [
                        "gross_salary", "employee_name", "employee_pan",
                        "employer_name", "employer_tan", "assessment_year",
                        "financial_year", "standard_deduction", "epf_employee",
                        "ppf", "life_insurance", "elss", "home_loan_principal",
                        "total_tax_deducted", "net_taxable_income", "total_income"
                    ]

                    for field in known_fields:
                        if field in field_corrections:
                            extracted_data[field] = field_corrections[field]

                # Update document with verified/corrected data
                document.extracted_data = extracted_data
                if verified:
                    document.verification_status = "verified"
                else:
                    document.verification_status = "partially_verified" if corrections_applied else "needs_review"
                document.updated_at = datetime.utcnow()
                db.commit()

                # Update individual extracted field records
                self._update_extracted_field_records(db, document_id, field_corrections, verified)

                return {
                    "document_id": document_id,
                    "message": "Document data verification completed",
                    "verification_status": document.verification_status,
                    "extracted_data": extracted_data,
                    "corrections_applied": corrections_applied,
                    "verified": verified,
                    "note": "Data has been updated. You can now use this information in financial calculations."
                }

            finally:
                db.close()

        except Exception as e:
            logger.error("Document verification failed: %s", redact_text(str(e)))
            return {
                "error": "Failed to verify extracted data"
            }

    def _update_extracted_field_records(self, db, document_id: str, field_corrections: Dict[str, Any], verified: bool):
        """Update extracted field records with verification status"""
        from app.models.document import ExtractedField

        # Update verification status for fields
        for field_name, correction in field_corrections.items():
            # Find the field record (simplified - in reality would need better matching)
            field_record = db.query(ExtractedField).filter(
                ExtractedField.document_id == uuid.UUID(document_id),
                ExtractedField.field_name == field_name
            ).first()

            if field_record:
                field_record.verified_by_user = verified
                if "new" in correction:
                    field_record.extracted_value = str(correction["new"])
                    # Try to parse the new value
                    try:
                        if isinstance(correction["new"], (int, float)) and not isinstance(correction["new"], bool):
                            field_record.parsed_value = int(correction["new"])
                        field_record.parsed_text = str(correction["new"])
                    except:
                        pass
                field_record.verification_timestamp = datetime.utcnow() if verified else None

        # If marking as fully verified, update all fields
        if verified and not field_corrections:
            db.query(ExtractedField).filter(
                ExtractedField.document_id == uuid.UUID(document_id)
            ).update({ExtractedField.verified_by_user: True})

        db.commit()
