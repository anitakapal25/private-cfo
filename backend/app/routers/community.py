from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.config import get_db
from app.models.user import User
from app.models.community import CommunityBenchmark
from app.auth.manager import get_current_active_user
from pydantic import BaseModel, ConfigDict
from datetime import datetime
import uuid
from uuid import UUID

router = APIRouter(tags=["community"])

# Pydantic models for request/response
class CommunityBenchmarkBase(BaseModel):
    age_group: str
    income_bracket: str
    metric_type: str
    metric_value: float
    value_type: str = "average"
    sample_size: int
    region: Optional[str] = None
    benchmark_metadata: Optional[dict] = None

class CommunityBenchmarkCreate(CommunityBenchmarkBase):
    pass

class CommunityBenchmarkResponse(CommunityBenchmarkBase):
    model_config = ConfigDict(from_attributes=True)

    benchmark_id: UUID
    calculated_at: datetime

@router.post("/benchmarks", response_model=CommunityBenchmarkResponse)
async def create_community_benchmark(
    benchmark: CommunityBenchmarkCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new community benchmark.
    Only admins can create community benchmarks.
    """
    # Check if current user is an admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create community benchmarks"
        )

    db_benchmark = CommunityBenchmark(
        age_group=benchmark.age_group,
        income_bracket=benchmark.income_bracket,
        metric_type=benchmark.metric_type,
        metric_value=benchmark.metric_value,
        value_type=benchmark.value_type,
        sample_size=benchmark.sample_size,
        region=benchmark.region,
        benchmark_metadata=benchmark.benchmark_metadata
    )
    db.add(db_benchmark)
    db.commit()
    db.refresh(db_benchmark)
    return db_benchmark

@router.get("/benchmarks", response_model=List[CommunityBenchmarkResponse])
async def get_community_benchmarks(
    age_group: Optional[str] = None,
    income_bracket: Optional[str] = None,
    metric_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get community benchmarks with optional filtering.
    """
    query = db.query(CommunityBenchmark)

    if age_group:
        query = query.filter(CommunityBenchmark.age_group == age_group)
    if income_bracket:
        query = query.filter(CommunityBenchmark.income_bracket == income_bracket)
    if metric_type:
        query = query.filter(CommunityBenchmark.metric_type == metric_type)

    benchmarks = query.all()
    return benchmarks

@router.get("/benchmarks/{benchmark_id}", response_model=CommunityBenchmarkResponse)
async def get_community_benchmark(
    benchmark_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific community benchmark by ID.
    """
    benchmark = db.query(CommunityBenchmark).filter(
        CommunityBenchmark.benchmark_id == benchmark_id
    ).first()
    if not benchmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benchmark not found"
        )
    return benchmark

@router.put("/benchmarks/{benchmark_id}", response_model=CommunityBenchmarkResponse)
async def update_community_benchmark(
    benchmark_id: str,
    benchmark_update: CommunityBenchmarkBase,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing community benchmark.
    Only admins can update community benchmarks.
    """
    # Check if current user is an admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update community benchmarks"
        )

    benchmark = db.query(CommunityBenchmark).filter(
        CommunityBenchmark.benchmark_id == benchmark_id
    ).first()
    if not benchmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benchmark not found"
        )

    # Update fields
    update_data = benchmark_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(benchmark, key, value)

    db.commit()
    db.refresh(benchmark)
    return benchmark

@router.delete("/benchmarks/{benchmark_id}")
async def delete_community_benchmark(
    benchmark_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a community benchmark.
    Only admins can delete community benchmarks.
    """
    # Check if current user is an admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete community benchmarks"
        )

    benchmark = db.query(CommunityBenchmark).filter(
        CommunityBenchmark.benchmark_id == benchmark_id
    ).first()
    if not benchmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benchmark not found"
        )

    db.delete(benchmark)
    db.commit()
    return {"message": "Benchmark deleted successfully"}

@router.get("/my-benchmark-comparison")
async def get_my_benchmark_comparison(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get benchmark comparisons for the current user's demographic group.
    This would compare the user's financial metrics against community benchmarks.
    """
    # Get user's profile to determine age group and income bracket
    profile = current_user.profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )

    # Calculate user's age from date_of_birth
    from datetime import date
    today = date.today()
    user_age = today.year - current_user.date_of_birth.year

    # Determine age group (simplified)
    if user_age < 25:
        age_group = "under-25"
    elif user_age < 35:
        age_group = "25-34"
    elif user_age < 45:
        age_group = "35-44"
    elif user_age < 55:
        age_group = "45-54"
    else:
        age_group = "55+"

    # Determine income bracket (simplified - would need to calculate from income sources)
    # For now, we'll use a placeholder
    income_bracket = "5-10L"  # This would be calculated from actual income

    # Get benchmarks for this demographic group
    benchmarks = db.query(CommunityBenchmark).filter(
        CommunityBenchmark.age_group == age_group,
        CommunityBenchmark.income_bracket == income_bracket
    ).all()

    # In a real implementation, we would calculate the user's actual metrics
    # and compare them to the benchmarks
    return {
        "user_demographics": {
            "age_group": age_group,
            "income_bracket": income_bracket,
            "age": user_age
        },
        "comparison": [
            {
                "metric_type": benchmark.metric_type,
                "benchmark_value": benchmark.metric_value,
                "value_type": benchmark.value_type,
                "sample_size": benchmark.sample_size,
                "region": benchmark.region,
                "calculated_at": benchmark.calculated_at
            }
            for benchmark in benchmarks
        ],
        "message": "In a full implementation, this would include the user's actual metrics and comparison analysis"
    }
