"""Authorization helpers that bind tool inputs to authenticated identity."""

from typing import Any, Mapping

from fastapi import HTTPException, status


def bind_authenticated_user(
    input_data: Mapping[str, Any], authenticated_user_id: str
) -> dict[str, Any]:
    """Return a copy bound to the authenticated user and reject identity conflicts."""
    supplied_user_id = input_data.get("user_id")
    if supplied_user_id is not None and str(supplied_user_id) != authenticated_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request identity does not match the authenticated user",
        )
    bound = dict(input_data)
    bound["user_id"] = authenticated_user_id
    return bound

