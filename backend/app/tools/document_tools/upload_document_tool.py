from app.tools.document_tools.base_document_tool import BaseDocumentTool
from typing import Dict, Any
from app.guardrails.data_redaction import redact_text
import base64
import logging

logger = logging.getLogger(__name__)

class UploadDocumentTool(BaseDocumentTool):
    """Tool for uploading and initially processing financial documents"""

    def __init__(self):
        super().__init__()
        self.name = "UploadDocumentTool"
        self.description = "Upload financial documents (salary slip, Form 16, bank statement, etc.) for data extraction"

    def get_description(self) -> str:
        """Get a human-readable description of what this tool does.

        Returns:
            String description of the tool's purpose and functionality
        """
        return self.description

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upload a financial document for processing

        Expected input:
        {
            "user_id": "uuid-string",
            "document_type": "salary_slip|form_16|bank_statement|epf_statement|insurance_policy",
            "file_content": "base64-encoded-file-content",
            "original_filename": "document.pdf"
        }
        """
        try:
            # Validate required fields
            user_id = input_data.get("user_id")
            document_type = input_data.get("document_type")
            file_content_b64 = input_data.get("file_content")
            original_filename = input_data.get("original_filename")

            if not all([user_id, document_type, file_content_b64, original_filename]):
                return {
                    "error": "Missing required fields: user_id, document_type, file_content, original_filename"
                }

            # Validate document type
            valid_types = ["salary_slip", "form_16", "bank_statement", "epf_statement", "insurance_policy"]
            if document_type not in valid_types:
                return {
                    "error": f"Invalid document type. Must be one of: {', '.join(valid_types)}"
                }

            # Decode base64 content
            try:
                file_content = base64.b64decode(file_content_b64, validate=True)
            except Exception as e:
                return {
                    "error": f"Invalid base64 file content: {str(e)}"
                }

            # Validate file size (max 10MB)
            if len(file_content) > 10 * 1024 * 1024:  # 10MB
                return {
                    "error": "File size too large. Maximum allowed size is 10MB."
                }

            if not file_content:
                return {"error": "Uploaded file is empty"}

            extension = __import__('pathlib').Path(original_filename).suffix.lower()
            allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.txt'}
            if extension not in allowed_extensions:
                return {"error": "Unsupported file extension"}

            signatures = {
                '.pdf': (b'%PDF-',),
                '.jpg': (b'\xff\xd8\xff',),
                '.jpeg': (b'\xff\xd8\xff',),
                '.png': (b'\x89PNG\r\n\x1a\n',),
            }
            if extension in signatures and not file_content.startswith(signatures[extension]):
                return {"error": "File content does not match its extension"}

            # Save the uploaded file encrypted at rest.
            file_info = self._save_uploaded_file(
                file_content=file_content,
                original_filename=original_filename,
                user_id=user_id
            )

            # Add original filename to file_info for database record
            file_info["original_filename"] = original_filename

            # Create database record
            document_id = self._create_document_record(
                user_id=user_id,
                document_type=document_type,
                file_info=file_info
            )

            # For now, return success with document ID
            # In a full implementation, this would trigger background processing
            return {
                "document_id": document_id,
                "message": f"Document '{original_filename}' uploaded successfully. Document ID: {document_id}",
                "status": "uploaded",
                "next_steps": "Use ExtractDocumentDataTool to extract data from this document.",
                "extraction_status": "pending"
            }

        except Exception as e:
            logger.error("Document upload failed: %s", redact_text(str(e)))
            return {
                "error": "Failed to upload document"
            }
