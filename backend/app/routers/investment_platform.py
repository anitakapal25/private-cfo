from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.config import get_db, get_settings
from app.models.user import User
from app.models.investment_platform import InvestmentPlatformConnection
from app.auth.manager import get_current_active_user
from pydantic import BaseModel
from datetime import datetime
import uuid
from uuid import UUID

router = APIRouter(tags=["investment_platform"])


def require_financial_integrations() -> None:
    if not get_settings().enable_financial_integrations:
        raise HTTPException(status_code=503, detail="Financial integrations are disabled")

# Pydantic models for request/response
class InvestmentPlatformConnectionBase(BaseModel):
    platform_name: str
    platform_user_id: Optional[str] = None
    token_expires_at: Optional[datetime] = None

class InvestmentPlatformConnectionCreate(InvestmentPlatformConnectionBase):
    credentials: Optional[str] = None

class InvestmentPlatformConnectionUpdate(InvestmentPlatformConnectionBase):
    credentials: Optional[str] = None

class InvestmentPlatformConnectionResponse(InvestmentPlatformConnectionBase):
    connection_id: UUID
    user_id: UUID
    is_active: bool
    last_synced_at: Optional[datetime]
    sync_status: Optional[str]
    last_error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

@router.post("/connections", response_model=InvestmentPlatformConnectionResponse)
async def create_investment_platform_connection(
    connection: InvestmentPlatformConnectionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new investment platform connection for the current user.
    """
    require_financial_integrations()
    # Encrypt credentials before storing
    encrypted_credentials = None
    if connection.credentials:
        encrypted_credentials = InvestmentPlatformConnection.encrypt_credentials(connection.credentials)

    db_connection = InvestmentPlatformConnection(
        user_id=current_user.user_id,
        platform_name=connection.platform_name,
        platform_user_id=connection.platform_user_id,
        encrypted_credentials=encrypted_credentials,  # Now properly encrypted
        token_expires_at=connection.token_expires_at,
        is_active=True
    )
    db.add(db_connection)
    db.commit()
    db.refresh(db_connection)
    return db_connection

@router.get("/connections", response_model=List[InvestmentPlatformConnectionResponse])
async def get_investment_platform_connections(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all investment platform connections for the current user.
    """
    connections = db.query(InvestmentPlatformConnection).filter(
        InvestmentPlatformConnection.user_id == current_user.user_id
    ).all()
    return connections

@router.get("/connections/{connection_id}", response_model=InvestmentPlatformConnectionResponse)
async def get_investment_platform_connection(
    connection_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific investment platform connection by ID.
    """
    connection = db.query(InvestmentPlatformConnection).filter(
        InvestmentPlatformConnection.connection_id == connection_id,
        InvestmentPlatformConnection.user_id == current_user.user_id
    ).first()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    return connection

@router.put("/connections/{connection_id}", response_model=InvestmentPlatformConnectionResponse)
async def update_investment_platform_connection(
    connection_id: str,
    connection_update: InvestmentPlatformConnectionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing investment platform connection.
    """
    connection = db.query(InvestmentPlatformConnection).filter(
        InvestmentPlatformConnection.connection_id == connection_id,
        InvestmentPlatformConnection.user_id == current_user.user_id
    ).first()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    # Update fields
    update_data = connection_update.model_dump(exclude_unset=True)
    # Handle credentials encryption if provided
    credentials = update_data.pop('credentials', None)
    if credentials:
        update_data['encrypted_credentials'] = InvestmentPlatformConnection.encrypt_credentials(credentials)
    for key, value in update_data.items():
        setattr(connection, key, value)
    connection.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(connection)
    return connection

@router.delete("/connections/{connection_id}")
async def delete_investment_platform_connection(
    connection_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete an investment platform connection.
    """
    connection = db.query(InvestmentPlatformConnection).filter(
        InvestmentPlatformConnection.connection_id == connection_id,
        InvestmentPlatformConnection.user_id == current_user.user_id
    ).first()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    db.delete(connection)
    db.commit()
    return {"message": "Connection deleted successfully"}

@router.post("/connections/{connection_id}/sync")
async def sync_investment_platform_connection(
    connection_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Trigger a sync for the investment platform connection.
    In a real implementation, this would be a background task that fetches data from the platform.
    For MVP, we simulate a successful sync.
    """
    require_financial_integrations()
    connection = db.query(InvestmentPlatformConnection).filter(
        InvestmentPlatformConnection.connection_id == connection_id,
        InvestmentPlatformConnection.user_id == current_user.user_id
    ).first()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    # Simulate sync process
    connection.last_synced_at = datetime.utcnow()
    connection.sync_status = "success"
    connection.last_error_message = None
    # In a real implementation, we would update the user's financial data with the synced holdings
    db.commit()
    return {"message": "Sync initiated successfully", "last_synced_at": connection.last_synced_at}
