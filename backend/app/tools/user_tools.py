from app.tools.base import BaseTool
from typing import Dict, Any
import uuid

class GetUserProfileTool(BaseTool):
    """Retrieve basic user profile information including age, income sources, and dependents.

    This tool returns non-sensitive profile data only. Sensitive identifiers like PAN,
    Aadhaar, and full account numbers are never returned.
    """

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get user profile from database with authorization check.

        In a real implementation, we would verify that the requesting user
        is authorized to access this profile data.
        """
        user_id_str = input_data.get("user_id")
        if not user_id_str:
            return {"error": "User ID is required"}

        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            return {"error": "Invalid user ID format"}

        # For now, return mock data since we don't have database connection
        # In a real implementation, this would query the database
        return {
            "user_id": str(user_id),
            "date_of_birth": "1990-01-01",
            "age": 34,
            "marital_status": "married",
            "dependents_count": 2,
            "residential_status": "resident_indian",
            "employment_status": "employed",
            "primary_occupation": "Software Engineer",
            "profile": {
                "full_name": "Test User",
                "email_verified": True,
                "phone_verified": True,
                "preferred_language": "en",
                "timezone": "Asia/Kolkata"
            }
        }

    def get_description(self) -> str:
        return "Retrieve basic user profile information including age, marital status, dependents, occupation, and contact verification status. Does not return sensitive identifiers like PAN or Aadhaar."