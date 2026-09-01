from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.config import get_db
from app.models.user import User
from app.models.wellness_program import EmployerWellnessProgram, UserWellnessParticipation
from app.auth.manager import get_current_active_user
from pydantic import BaseModel, ConfigDict
from datetime import datetime
import uuid
from uuid import UUID

router = APIRouter(tags=["wellness_program"])

# Pydantic models for request/response
class EmployerWellnessProgramBase(BaseModel):
    employer_name: str
    program_name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    brand_color: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_participants: Optional[int] = None

class EmployerWellnessProgramCreate(EmployerWellnessProgramBase):
    pass

class EmployerWellnessProgramResponse(EmployerWellnessProgramBase):
    model_config = ConfigDict(from_attributes=True)

    program_id: UUID
    is_active: bool
    current_participants: int
    created_at: datetime
    updated_at: datetime

class UserWellnessParticipationBase(BaseModel):
    program_id: str
    progress_percentage: Optional[int] = 0
    status: Optional[str] = 'active'

class UserWellnessParticipationCreate(UserWellnessParticipationBase):
    pass

class UserWellnessParticipationResponse(UserWellnessParticipationBase):
    model_config = ConfigDict(from_attributes=True)

    participation_id: UUID
    user_id: UUID
    enrollment_date: datetime
    completion_date: Optional[datetime]
    points_earned: int
    rewards_redeemed: int
    created_at: datetime
    updated_at: datetime

@router.post("/programs", response_model=EmployerWellnessProgramResponse)
async def create_wellness_program(
    program: EmployerWellnessProgramCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new employer wellness program.
    Only admins can create wellness programs.
    """
    # Check if current user is an admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create wellness programs"
        )

    db_program = EmployerWellnessProgram(
        employer_name=program.employer_name,
        program_name=program.program_name,
        description=program.description,
        logo_url=program.logo_url,
        brand_color=program.brand_color,
        start_date=program.start_date,
        end_date=program.end_date,
        max_participants=program.max_participants
    )
    db.add(db_program)
    db.commit()
    db.refresh(db_program)
    return db_program

@router.get("/programs", response_model=List[EmployerWellnessProgramResponse])
async def get_wellness_programs(
    active_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all wellness programs.
    """
    query = db.query(EmployerWellnessProgram)
    if active_only:
        query = query.filter(EmployerWellnessProgram.is_active == True)
    programs = query.all()
    return programs

@router.get("/programs/{program_id}", response_model=EmployerWellnessProgramResponse)
async def get_wellness_program(
    program_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific wellness program by ID.
    """
    program = db.query(EmployerWellnessProgram).filter(
        EmployerWellnessProgram.program_id == program_id
    ).first()
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wellness program not found"
        )
    return program

@router.put("/programs/{program_id}", response_model=EmployerWellnessProgramResponse)
async def update_wellness_program(
    program_id: str,
    program_update: EmployerWellnessProgramBase,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing wellness program.
    Only admins can update wellness programs.
    """
    # Check if current user is an admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update wellness programs"
        )

    program = db.query(EmployerWellnessProgram).filter(
        EmployerWellnessProgram.program_id == program_id
    ).first()
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wellness program not found"
        )

    # Update fields
    update_data = program_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(program, key, value)

    db.commit()
    db.refresh(program)
    return program

@router.delete("/programs/{program_id}")
async def delete_wellness_program(
    program_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a wellness program.
    Only admins can delete wellness programs.
    """
    # Check if current user is an admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete wellness programs"
        )

    program = db.query(EmployerWellnessProgram).filter(
        EmployerWellnessProgram.program_id == program_id
    ).first()
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wellness program not found"
        )

    db.delete(program)
    db.commit()
    return {"message": "Wellness program deleted successfully"}

@router.post("/programs/{program_id}/join", response_model=UserWellnessParticipationResponse)
async def join_wellness_program(
    program_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Join a wellness program as a user.
    """
    # Check if program exists and is active
    program = db.query(EmployerWellnessProgram).filter(
        EmployerWellnessProgram.program_id == program_id,
        EmployerWellnessProgram.is_active == True
    ).first()
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wellness program not found or not active"
        )

    # Check if user is already participating
    existing_participation = db.query(UserWellnessParticipation).filter(
        UserWellnessParticipation.user_id == current_user.user_id,
        UserWellnessParticipation.program_id == program_id,
        UserWellnessParticipation.is_active == True
    ).first()
    if existing_participation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already participating in this wellness program"
        )

    # Check if program has reached max participants
    if program.max_participants and program.current_participants >= program.max_participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wellness program has reached maximum participants"
        )

    # Create participation record
    participation = UserWellnessParticipation(
        user_id=current_user.user_id,
        program_id=program_id
    )
    db.add(participation)

    # Update participant count
    program.current_participants += 1

    db.commit()
    db.refresh(participation)
    return participation

@router.put("/participations/{participation_id}", response_model=UserWellnessParticipationResponse)
async def update_wellness_participation(
    participation_id: str,
    participation_update: UserWellnessParticipationBase,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a user's wellness participation.
    """
    participation = db.query(UserWellnessParticipation).filter(
        UserWellnessParticipation.participation_id == participation_id,
        UserWellnessParticipation.user_id == current_user.user_id
    ).first()
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participation not found"
        )

    # Update fields
    update_data = participation_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(participation, key, value)

    db.commit()
    db.refresh(participation)
    return participation

@router.delete("/participations/{participation_id}")
async def leave_wellness_program(
    participation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Leave a wellness program.
    """
    participation = db.query(UserWellnessParticipation).filter(
        UserWellnessParticipation.participation_id == participation_id,
        UserWellnessParticipation.user_id == current_user.user_id
    ).first()
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participation not found"
        )

    # Update program participant count
    program = db.query(EmployerWellnessProgram).filter(
        EmployerWellnessProgram.program_id == participation.program_id
    ).first()
    if program and program.current_participants > 0:
        program.current_participants -= 1

    # Mark participation as inactive
    participation.is_active = False
    participation.status = 'withdrawn'

    db.commit()
    return {"message": "Successfully left wellness program"}

@router.get("/my-participations", response_model=List[UserWellnessParticipationResponse])
async def get_my_wellness_participations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all wellness program participations for the current user.
    """
    participations = db.query(UserWellnessParticipation).filter(
        UserWellnessParticipation.user_id == current_user.user_id
    ).all()
    return participations
