from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.config import get_db
from app.models.user import User, Profile
from app.models.advisor import AdvisorConsent
from app.auth.manager import get_current_active_user
from pydantic import BaseModel
from datetime import datetime
import uuid

router = APIRouter(tags=["advisor"])

# Pydantic models for request/response
class ConsentRequest(BaseModel):
    client_email: str
    scope: str = "read_only"

class ConsentResponse(BaseModel):
    consent_id: str
    advisor_id: str
    client_id: str
    granted_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    scope: str

class AdvisorClientInfo(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    consent_id: str

@router.post("/request-consent", response_model=ConsentResponse)
async def request_consent(
    consent_request: ConsentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Request consent to access a client's financial data.
    Only advisors can request consent.
    """
    # Check if current user is an advisor
    if current_user.role != "advisor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only financial advisors can request consent"
        )

    # Find the client by email
    client = db.query(User).join(Profile).filter(
        Profile.email_address == consent_request.client_email
    ).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    # Check if client is actually a user (not advisor/admin trying to get consent)
    if client.role != "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent can only be requested for regular users"
        )

    # Check if consent already exists
    existing_consent = db.query(AdvisorConsent).filter(
        AdvisorConsent.advisor_id == current_user.user_id,
        AdvisorConsent.client_id == client.user_id,
        AdvisorConsent.is_active == True
    ).first()

    if existing_consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active consent already exists for this client"
        )

    # Create new consent
    new_consent = AdvisorConsent(
        advisor_id=current_user.user_id,
        client_id=client.user_id,
        scope=consent_request.scope,
        is_active=True
    )

    db.add(new_consent)
    db.commit()
    db.refresh(new_consent)

    return ConsentResponse(
        consent_id=str(new_consent.consent_id),
        advisor_id=str(new_consent.advisor_id),
        client_id=str(new_consent.client_id),
        granted_at=new_consent.granted_at,
        expires_at=new_consent.expires_at,
        is_active=new_consent.is_active,
        scope=new_consent.scope
    )

@router.get("/clients", response_model=List[AdvisorClientInfo])
async def get_consented_clients(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get list of clients who have granted consent to the current advisor.
    """
    # Check if current user is an advisor
    if current_user.role != "advisor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only financial advisors can view their clients"
        )

    # Get all active consents where current user is the advisor
    consents = db.query(AdvisorConsent).filter(
        AdvisorConsent.advisor_id == current_user.user_id,
        AdvisorConsent.is_active == True
    ).all()

    # Get client information for each consent
    clients = []
    for consent in consents:
        client = db.query(User).join(User.profile).filter(
            User.user_id == consent.client_id
        ).first()

        if client:
            clients.append(AdvisorClientInfo(
                user_id=str(client.user_id),
                email=client.profile.email_address,
                full_name=client.profile.full_name,
                role=client.role,
                is_active=client.is_active,
                consent_id=str(consent.consent_id)
            ))

    return clients

@router.delete("/consent/{consent_id}")
async def revoke_consent(
    consent_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Revoke consent for a client.
    Only the advisor who granted the consent can revoke it.
    """
    # Find the consent
    consent = db.query(AdvisorConsent).filter(
        AdvisorConsent.consent_id == consent_id
    ).first()

    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent not found"
        )

    # Check if current user is the advisor who granted this consent
    if consent.advisor_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only revoke consents you granted"
        )

    # Revoke the consent
    consent.is_active = False
    db.commit()

    return {"message": "Consent revoked successfully"}

@router.get("/client-data/{client_id}")
async def get_client_financial_data(
    client_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get financial data for a client who has granted consent.
    """
    # Check if current user is an advisor
    if current_user.role != "advisor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only financial advisors can access client data"
        )

    # Check if consent exists and is active
    consent = db.query(AdvisorConsent).filter(
        AdvisorConsent.advisor_id == current_user.user_id,
        AdvisorConsent.client_id == client_id,
        AdvisorConsent.is_active == True
    ).first()

    if not consent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active consent found for this client"
        )

    # Get client information
    client = db.query(User).join(User.profile).filter(
        User.user_id == client_id
    ).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    # Return basic client profile information (in a real implementation,
    # this would return financial data based on the consent scope)
    return {
        "user_id": str(client.user_id),
        "email": client.profile.email_address,
        "full_name": client.profile.full_name,
        "role": client.role,
        "is_active": client.is_active,
        "consent_scope": consent.scope,
        "consent_granted_at": consent.granted_at,
        "message": "Financial data access would be implemented here based on consent scope"
    }