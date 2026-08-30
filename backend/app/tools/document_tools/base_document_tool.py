from app.tools.base import BaseTool
from app.models.document import DocumentStorage, ExtractedField
from app.core.config import get_db
from typing import Dict, Any, Optional
import uuid
import json
from datetime import datetime
import hashlib
import os
from pathlib import Path

from app.core.config import get_settings
from app.core.crypto import encrypt_bytes

class BaseDocumentTool(BaseTool):
    """Base class for document processing tools"""

    def __init__(self):
        super().__init__()
        self.upload_dir = get_settings().upload_dir.resolve()
        # Ensure upload directory exists
        self.upload_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    def get_description(self) -> str:
        """Get a human-readable description of what this tool does.

        Returns:
            String description of the tool's purpose and functionality
        """
        return self.description if hasattr(self, 'description') else "Document processing tool"

    def _save_uploaded_file(self, file_content: bytes, original_filename: str, user_id: str) -> Dict[str, Any]:
        """Save uploaded file and return storage info"""
        # Generate unique filename
        file_id = uuid.uuid4()
        file_extension = Path(original_filename).suffix.lower()
        stored_filename = f"{file_id}{file_extension}.enc"
        storage_path = self.upload_dir / stored_filename

        # Save file
        storage_path.write_bytes(encrypt_bytes(file_content))
        storage_path.chmod(0o600)

        # Calculate checksum
        checksum_sha256 = hashlib.sha256(file_content).hexdigest()

        # Get file size
        file_size_bytes = len(file_content)

        # Determine MIME type (simplified)
        mime_type = self._get_mime_type(original_filename)

        return {
            "document_id": str(file_id),
            "storage_path": str(storage_path),
            "stored_filename": stored_filename,
            "file_size_bytes": file_size_bytes,
            "checksum_sha256": checksum_sha256,
            "mime_type": mime_type
        }

    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type based on file extension"""
        extension = os.path.splitext(filename)[1].lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.txt': 'text/plain'
        }
        return mime_types.get(extension, 'application/octet-stream')

    def _create_document_record(self, user_id: str, document_type: str, file_info: Dict[str, Any]) -> str:
        """Create document storage record in database"""
        db = next(get_db())
        try:
            document = DocumentStorage(
                user_id=uuid.UUID(user_id),
                document_type=document_type,
                original_filename=file_info["original_filename"],
                storage_path=file_info["storage_path"],
                file_size_bytes=file_info["file_size_bytes"],
                mime_type=file_info["mime_type"],
                checksum_sha256=file_info["checksum_sha256"],
                upload_timestamp=datetime.utcnow(),
                extraction_status="pending",
                extraction_confidence=0,
                verification_status="unverified",
                is_encrypted=True  # In production, this would use proper encryption
            )
            db.add(document)
            db.commit()
            db.refresh(document)
            return str(document.document_id)
        finally:
            db.close()

    def _update_extraction_status(self, document_id: str, status: str, confidence: Optional[int] = None, extracted_data: Optional[Dict] = None):
        """Update document extraction status"""
        db = next(get_db())
        try:
            document = db.query(DocumentStorage).filter(
                DocumentStorage.document_id == uuid.UUID(document_id)
            ).first()
            if document:
                document.extraction_status = status
                if confidence is not None:
                    document.extraction_confidence = confidence
                if extracted_data is not None:
                    document.extracted_data = extracted_data
                document.verification_status = "needs_review" if status == "completed" else "unverified"
                db.commit()
        finally:
            db.close()
