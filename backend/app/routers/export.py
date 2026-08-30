from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.config import get_db
from app.models.user import User
from app.models.export import TaxExportTemplate, TaxExport, LoanApplicationExport
from app.models.financial import IncomeSource, Asset, Liability
from app.auth.manager import get_current_active_user
from pydantic import BaseModel
from datetime import datetime, timedelta
import uuid
from uuid import UUID
import json

router = APIRouter(tags=["export"])

# Pydantic models for TaxExportTemplate
class TaxExportTemplateBase(BaseModel):
    template_name: str
    assessment_year: str
    description: Optional[str] = None
    export_format: str = "PDF"  # PDF, XML, JSON, CSV
    is_active: bool = True

class TaxExportTemplateCreate(TaxExportTemplateBase):
    pass

class TaxExportTemplateResponse(TaxExportTemplateBase):
    template_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Pydantic models for TaxExport
class TaxExportBase(BaseModel):
    template_id: str
    # In a real implementation, we might have additional parameters for the export
    # For MVP, we'll just use the template and generate data based on user's financials

class TaxExportCreate(TaxExportBase):
    pass

class TaxExportResponse(TaxExportBase):
    export_id: UUID
    user_id: UUID
    export_data: str
    file_name: str
    file_size_bytes: int
    is_downloaded: bool
    download_count: int
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True

# Pydantic models for LoanApplicationExport
class LoanApplicationExportBase(BaseModel):
    loan_type: str  # home, personal, auto, education, business
    loan_amount_requested: int  # Amount in currency units (e.g., INR)

class LoanApplicationExportCreate(LoanApplicationExportBase):
    pass

class LoanApplicationExportResponse(LoanApplicationExportBase):
    export_id: UUID
    user_id: UUID
    export_data: str
    file_name: str
    file_size_bytes: int
    is_downloaded: bool
    download_count: int
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True

# Tax Export Template Endpoints (Admin only)
@router.post("/templates/tax", response_model=TaxExportTemplateResponse)
async def create_tax_export_template(
    template: TaxExportTemplateCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new tax export template.
    Only admins can create tax export templates.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create tax export templates"
        )

    db_template = TaxExportTemplate(
        template_name=template.template_name,
        assessment_year=template.assessment_year,
        description=template.description,
        export_format=template.export_format,
        is_active=template.is_active
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

@router.get("/templates/tax", response_model=List[TaxExportTemplateResponse])
async def get_tax_export_templates(
    active_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all tax export templates.
    """
    query = db.query(TaxExportTemplate)
    if active_only:
        query = query.filter(TaxExportTemplate.is_active == True)
    templates = query.all()
    return templates

@router.get("/templates/tax/{template_id}", response_model=TaxExportTemplateResponse)
async def get_tax_export_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific tax export template by ID.
    """
    template = db.query(TaxExportTemplate).filter(
        TaxExportTemplate.template_id == template_id
    ).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax export template not found"
        )
    return template

@router.put("/templates/tax/{template_id}", response_model=TaxExportTemplateResponse)
async def update_tax_export_template(
    template_id: str,
    template_update: TaxExportTemplateBase,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing tax export template.
    Only admins can update tax export templates.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update tax export templates"
        )

    template = db.query(TaxExportTemplate).filter(
        TaxExportTemplate.template_id == template_id
    ).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax export template not found"
        )

    # Update fields
    update_data = template_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)

    db.commit()
    db.refresh(template)
    return template

@router.delete("/templates/tax/{template_id}")
async def delete_tax_export_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a tax export template.
    Only admins can delete tax export templates.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete tax export templates"
        )

    template = db.query(TaxExportTemplate).filter(
        TaxExportTemplate.template_id == template_id
    ).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax export template not found"
        )

    db.delete(template)
    db.commit()
    return {"message": "Tax export template deleted successfully"}

# Tax Export Endpoints (Users can create exports for themselves)
@router.post("/exports/tax", response_model=TaxExportResponse)
async def create_tax_export(
    export_request: TaxExportCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a tax export for the current user.
    This generates the export data based on the user's financial data and the selected template.
    """
    # Verify the template exists and is active
    template = db.query(TaxExportTemplate).filter(
        TaxExportTemplate.template_id == export_request.template_id,
        TaxExportTemplate.is_active == True
    ).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax export template not found or not active"
        )

    # In a real implementation, we would generate the actual tax form data (XML, JSON, etc.)
    # For MVP, we'll create a JSON summary of the user's relevant financial data for tax purposes.

    # Gather user's financial data (simplified)
    user = current_user
    profile = user.profile

    # Calculate age
    from datetime import date
    today = date.today()
    user_age = today.year - user.date_of_birth.year if user.date_of_birth else 0

    # Get income sources
    income_sources = db.query(IncomeSource).filter(
        IncomeSource.user_id == user.user_id,
        IncomeSource.is_active == True
    ).all()
    total_annual_income = sum([float(source.amount) * (12 if source.frequency == 'monthly' else 1 if source.frequency == 'annually' else 4 if source.frequency == 'quarterly' else 1) for source in income_sources])

    # Get deductions (simplified - we don't have a separate deductions table, so we'll use some expenses and investments)
    # For now, we'll use a placeholder
    total_deductions = 50000.0  # Placeholder

    # Calculate taxable income
    taxable_income = max(0, total_annual_income - total_deductions)

    # Create export data (JSON)
    export_data = {
        "personal_info": {
            "name": profile.full_name if profile else "Unknown",
            "pan_last_four": user.pan_last_four,
            "aadhaar_last_four": user.aadhaar_last_four,
            "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
            "gender": user.gender,
            "email": profile.email_address if profile else None,
            "phone": profile.phone_number if profile else None
        },
        "financial_info": {
            "assessment_year": template.assessment_year,
            "total_annual_income": total_annual_income,
            "total_deductions": total_deductions,
            "taxable_income": taxable_income,
            "income_sources": [
                {
                    "source_type": source.source_type,
                    "source_name": source.source_name,
                    "amount": float(source.amount),
                    "frequency": source.frequency
                }
                for source in income_sources
            ]
        }
    }

    # Convert to JSON string for storage
    export_data_json = json.dumps(export_data, indent=2)

    # Determine file name and size
    file_name = f"tax_export_{user.user_id}_{template.assessment_year}.{template.export_format.lower()}"
    file_size_bytes = len(export_data_json.encode('utf-8'))

    # Create the export record
    db_export = TaxExport(
        user_id=user.user_id,
        template_id=template.template_id,
        export_data=export_data_json,
        file_name=file_name,
        file_size_bytes=file_size_bytes,
        is_downloaded=False,
        download_count=0,
        expires_at=datetime.utcnow() + timedelta(days=30)  # Expires in 30 days
    )
    db.add(db_export)
    db.commit()
    db.refresh(db_export)
    return db_export

@router.get("/exports/tax", response_model=List[TaxExportResponse])
async def get_my_tax_exports(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all tax exports for the current user.
    """
    exports = db.query(TaxExport).filter(
        TaxExport.user_id == current_user.user_id
    ).all()
    return exports

@router.get("/exports/tax/{export_id}", response_model=TaxExportResponse)
async def get_tax_export(
    export_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific tax export by ID.
    """
    export = db.query(TaxExport).filter(
        TaxExport.export_id == export_id,
        TaxExport.user_id == current_user.user_id
    ).first()
    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax export not found"
        )
    return export

@router.delete("/exports/tax/{export_id}")
async def delete_tax_export(
    export_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a tax export.
    """
    export = db.query(TaxExport).filter(
        TaxExport.export_id == export_id,
        TaxExport.user_id == current_user.user_id
    ).first()
    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax export not found"
        )

    db.delete(export)
    db.commit()
    return {"message": "Tax export deleted successfully"}

# Loan Application Export Endpoints
@router.post("/exports/loan", response_model=LoanApplicationExportResponse)
async def create_loan_application_export(
    export_request: LoanApplicationExportCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a loan application export for the current user.
    This generates the export data based on the user's financial data for loan application.
    """
    # Gather user's financial data (simplified)
    user = current_user
    profile = user.profile

    # Calculate age
    from datetime import date
    today = date.today()
    user_age = today.year - user.date_of_birth.year if user.date_of_birth else 0

    # Get income sources
    income_sources = db.query(IncomeSource).filter(
        IncomeSource.user_id == user.user_id,
        IncomeSource.is_active == True
    ).all()
    monthly_income = sum([float(source.amount) if source.frequency == 'monthly' else float(source.amount)/12 if source.frequency == 'annually' else float(source.amount)/3 if source.frequency == 'quarterly' else 0 for source in income_sources])

    # Get assets
    assets = db.query(app.models.financial.Asset).filter(
        app.models.financial.Asset.user_id == user.user_id,
        app.models.financial.Asset.is_active == True
    ).all()
    total_assets = sum([float(asset.current_value) for asset in assets])

    # Get liabilities
    liabilities = db.query(app.models.financial.Liability).filter(
        app.models.financial.Liability.user_id == user.user_id,
        app.models.financial.Liability.is_active == True
    ).all()
    total_liabilities = sum([float(liability.principal_outstanding) for liability in liabilities])

    # Calculate net worth
    net_worth = total_assets - total_liabilities

    # Create export data (JSON)
    export_data = {
        "personal_info": {
            "name": profile.full_name if profile else "Unknown",
            "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
            "gender": user.gender,
            "email": profile.email_address if profile else None,
            "phone": profile.phone_number if profile else None
        },
        "loan_application_info": {
            "loan_type": export_request.loan_type,
            "loan_amount_requested": export_request.loan_amount_requested,
            "application_date": datetime.utcnow().isoformat()
        },
        "financial_info": {
            "monthly_income": monthly_income,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "net_worth": net_worth,
            "assets": [
                {
                    "asset_type": asset.asset_type,
                    "account_name": asset.account_name,
                    "current_value": float(asset.current_value)
                }
                for asset in assets
            ],
            "liabilities": [
                {
                    "liability_type": liability.liability_type,
                    "lender_name": liability.lender_name,
                    "principal_outstanding": float(liability.principal_outstanding)
                }
                for liability in liabilities
            ]
        }
    }

    # Convert to JSON string for storage
    export_data_json = json.dumps(export_data, indent=2)

    # Determine file name and size
    file_name = f"loan_export_{user.user_id}_{export_request.loan_type}.json"
    file_size_bytes = len(export_data_json.encode('utf-8'))

    # Create the export record
    db_export = LoanApplicationExport(
        user_id=user.user_id,
        loan_type=export_request.loan_type,
        loan_amount_requested=export_request.loan_amount_requested,
        export_data=export_data_json,
        file_name=file_name,
        file_size_bytes=file_size_bytes,
        is_downloaded=False,
        download_count=0,
        expires_at=datetime.utcnow() + timedelta(days=30)  # Expires in 30 days
    )
    db.add(db_export)
    db.commit()
    db.refresh(db_export)
    return db_export

@router.get("/exports/loan", response_model=List[LoanApplicationExportResponse])
async def get_my_loan_exports(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all loan application exports for the current user.
    """
    exports = db.query(LoanApplicationExport).filter(
        LoanApplicationExport.user_id == current_user.user_id
    ).all()
    return exports

@router.get("/exports/loan/{export_id}", response_model=LoanApplicationExportResponse)
async def get_loan_export(
    export_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific loan application export by ID.
    """
    export = db.query(LoanApplicationExport).filter(
        LoanApplicationExport.export_id == export_id,
        LoanApplicationExport.user_id == current_user.user_id
    ).first()
    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan application export not found"
        )
    return export

@router.delete("/exports/loan/{export_id}")
async def delete_loan_export(
    export_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a loan application export.
    """
    export = db.query(LoanApplicationExport).filter(
        LoanApplicationExport.export_id == export_id,
        LoanApplicationExport.user_id == current_user.user_id
    ).first()
    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan application export not found"
        )

    db.delete(export)
    db.commit()
    return {"message": "Loan application export deleted successfully"}