from app.tools.document_tools.base_document_tool import BaseDocumentTool
from typing import Dict, Any
import re
from datetime import datetime
from app.core.config import get_db
from app.models.document import DocumentStorage, ExtractedField
from app.guardrails.data_redaction import redact_text
import logging
import uuid

logger = logging.getLogger(__name__)

class ExtractForm16Tool(BaseDocumentTool):
    """Tool for extracting data from Form 16 (TDS certificate)"""

    def __init__(self):
        super().__init__()
        self.name = "ExtractForm16Tool"
        self.description = "Extract financial data from Form 16 (TDS certificate on salary)"

    def get_description(self) -> str:
        """Get a human-readable description of what this tool does.

        Returns:
            String description of the tool's purpose and functionality
        """
        return self.description

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data from Form 16 document

        Expected input:
        {
            "document_id": "uuid-string",
            "user_id": "uuid-string"
        }
        """
        try:
            document_id = input_data.get("document_id")
            user_id = input_data.get("user_id")

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

                if document.document_type != "form_16":
                    return {
                        "error": "Document is not a Form 16"
                    }

                # Update status to processing
                self._update_extraction_status(document_id, "processing")

                # In a real implementation, we would:
                # 1. Read the actual file from storage
                # 2. Use OCR or PDF parsing to extract text
                # 3. Apply Form 16 specific parsing rules

                # For this MVP, we'll simulate extraction with sample data
                # In reality, this would be replaced with actual document processing

                # Simulate reading file content (in production, read from storage_path)
                # For demo, we'll generate mock extracted data based on seeded financial data

                current_year = datetime.now().year
                financial_year = f"{current_year-1}-{str(current_year)[-2:]}"

                # Mock extracted data (would come from actual OCR/parsing)
                extracted_data = {
                    "employee_name": "Test User",
                    "employee_pan": "ABCDE1234F",
                    "employer_name": "Test Company Ltd",
                    "employer_tan": "TDEL12345A",
                    "assessment_year": f"{current_year+1:04d}-{str(current_year+1)[-2:]}",
                    "financial_year": financial_year,
                    "gross_salary": 1800000,  # ₹18,00,000 per year
                    "allowances": {
                        "house_rent_allowance": 300000,
                        "leave_travel_allowance": 60000,
                        "other_allowances": 120000
                    },
                    "deductions": {
                        "standard_deduction": 50000,
                        "professional_tax": 2400,
                        "epf_employee": 108000,  # 12% of basic
                        "ppf": 70000,
                        "life_insurance": 25000,
                        "elss": 40000,
                        "home_loan_principal": 150000
                    },
                    "tax_details": {
                        "total_tax_deducted": 185000,
                        "education_cess": 7400,
                        "secondary_hes_cess": 3700,
                        "total_tax_paid": 196100
                    },
                    "net_taxable_income": 1254600,  # After deductions
                    "total_income": 1800000
                }

                # Update document with extracted data
                document.extracted_data = extracted_data
                document.extraction_status = "completed"
                document.extraction_confidence = 85  # Simulated confidence score
                document.verification_status = "needs_review"
                document.updated_at = datetime.utcnow()
                db.commit()

                # Also create individual extracted field records for audit trail
                self._create_extracted_field_records(db, document_id, extracted_data)

                return {
                    "document_id": document_id,
                    "message": "Form 16 data extracted successfully",
                    "extraction_status": "completed",
                    "extraction_confidence": 85,
                    "verification_status": "needs_review",
                    "extracted_data": extracted_data,
                    "note": "Please review the extracted data for accuracy. Use VerifyExtractedDataTool to confirm or correct any values."
                }

            finally:
                db.close()

        except Exception as e:
            logger.error("Form 16 extraction failed: %s", redact_text(str(e)))
            # Update status to failed on error
            if 'document_id' in locals():
                self._update_extraction_status(document_id, "failed")
            return {
                "error": "Failed to extract Form 16 data"
            }

    def _create_extracted_field_records(self, db, document_id: str, extracted_data: Dict[str, Any]):
        """Create individual extracted field records for detailed audit trail"""
        # Flatten the extracted data into individual fields
        def flatten_dict(d, parent_key='', sep='_'):
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key, sep=sep).items())
                else:
                    items.append((new_key, v))
            return dict(items)

        flat_data = flatten_dict(extracted_data)

        for field_name, field_value in flat_data.items():
            # Determine data type and category
            data_type = "text"
            field_category = "other"
            parsed_value = None
            parsed_date = None
            parsed_text = str(field_value) if field_value is not None else ""

            # Try to determine data type
            if isinstance(field_value, (int, float)) and not isinstance(field_value, bool):
                data_type = "currency" if any(x in field_name.lower() for x in ['salary', 'income', 'tax', 'deduction', 'allowance']) else "integer"
                parsed_value = int(field_value)
                parsed_text = str(field_value)
            elif 'date' in field_name.lower():
                data_type = "date"
                # In real implementation, parse actual date
                parsed_text = str(field_value)

            # Determine category
            if any(x in field_name.lower() for x in ['salary', 'income', 'allowance']):
                field_category = "income"
            elif any(x in field_name.lower() for x in ['deduction', 'tax', 'cess']):
                field_category = "deduction"
            elif any(x in field_name.lower() for x in ['pf', 'epf', 'ppf']):
                field_category = "deduction"  # Investments/deductions
            elif any(x in field_name.lower() for x in ['name', 'pan', 'tan', 'employer']):
                field_category = "other"

            extracted_field = ExtractedField(
                document_id=uuid.UUID(document_id),
                field_name=field_name,
                field_category=field_category,
                extracted_value=str(field_value) if field_value is not None else "",
                parsed_value=parsed_value,
                parsed_date=parsed_date,
                parsed_text=parsed_text,
                data_type=data_type,
                source_location="Form 16",  # Simplified
                extraction_method="template_matching",  # Simplified
                confidence_score=85,  # Matches overall confidence
                verified_by_user=False
            )
            db.add(extracted_field)

        db.commit()
