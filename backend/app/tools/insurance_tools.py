from app.tools.base import BaseTool
from app.models.user import User, Profile
from app.models.financial import IncomeSource, Expense, Asset, Liability
from app.core.config import get_db
from typing import Dict, Any
import uuid
from decimal import Decimal

class InsurancePlanningTool(BaseTool):
    """Calculate insurance needs for life, health, and property.

    This tool uses the deterministic calculation engine and returns
    an auditable result with assumptions and inputs documented.
    Never performs calculations based on LLM-generated arithmetic.
    """

    def get_description(self) -> str:
        return "Calculate recommended insurance coverage for life, health, and property based on user's financial situation, family details, and existing assets."

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate insurance needs.

        This is a deterministic calculation based on user's income, expenses, assets, liabilities, and family details.
        """
        user_id_str = input_data.get("user_id")
        if not user_id_str:
            return {"error": "User ID is required"}

        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            return {"error": "Invalid user ID format"}

        # Get database session
        db = next(get_db())

        try:
            # Get user's profile and user details
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                return {"error": "User not found"}

            profile = db.query(Profile).filter(Profile.user_id == user_id).first()
            if not profile:
                return {"error": "Profile not found for the user"}

            # Get user's income sources
            income_sources = db.query(IncomeSource).filter(
                IncomeSource.user_id == user_id,
                IncomeSource.is_active == True
            ).all()

            # Get user's expenses
            expenses = db.query(Expense).filter(
                Expense.user_id == user_id,
                Expense.is_active == True
            ).all()

            # Get user's assets
            assets = db.query(Asset).filter(
                Asset.user_id == user_id,
                Asset.is_active == True
            ).all()

            # Get user's liabilities
            liabilities = db.query(Liability).filter(
                Liability.user_id == user_id,
                Liability.is_active == True
            ).all()

            # Extract user details from user and profile
            # Calculate age from date_of_birth
            from datetime import date
            today = date.today()
            age = today.year - user.date_of_birth.year - ((today.month, today.day) < (user.date_of_birth.month, user.date_of_birth.day))
            marital_status = user.marital_status or 'unmarried'
            dependents_count = user.dependents_count or 0
            annual_income = self._calculate_annual_income(income_sources)

            # Calculate total annual expenses
            annual_expenses = self._calculate_annual_expenses(expenses)

            # Calculate total assets value
            total_assets_value = sum(asset.current_value for asset in assets)

            # Calculate total liabilities outstanding
            total_liabilities_outstanding = sum(liability.principal_outstanding for liability in liabilities)

            # --- Life Insurance Calculation ---
            # Using Needs Analysis method
            # Assume retirement age 60
            retirement_age = 60
            years_to_retirement = max(0, retirement_age - age)

            # Future expenses to cover:
            # 1. Outstanding liabilities (to be paid off)
            # 2. Children's education (if any)
            # 3. Spouse's retirement expenses (if married)
            # 4. Annual living expenses for dependents for a certain period

            # We'll use a simplified model:
            # Life cover = (Outstanding liabilities) +
            #            (Annual living expenses * years of protection) +
            #            (Children's education fund) -
            #            (Current liquid assets)

            # Assumptions:
            # - Years of protection for income replacement: 10 years (can be adjusted)
            # - Annual living expenses for family: 80% of current annual expenses (assuming some expenses reduce)
            # - Children's education: ₹25,00,000 per child (for higher education in India)
            # - Existing life insurance: we don't have a model for existing policies, so assume 0 for now

            years_of_protection = 10
            annual_living_expenses_for_family = annual_expenses * Decimal('0.8')
            education_cost_per_child = Decimal('2500000')  # ₹25 lakhs per child
            total_education_cost = education_cost_per_child * dependents_count

            # Current liquid assets: we'll consider savings account and fixed deposits as liquid
            liquid_assets = Decimal('0')
            for asset in assets:
                if asset.asset_type in ['savings_account', 'fixed_deposit']:
                    liquid_assets += asset.current_value

            life_insurance_need = (
                total_liabilities_outstanding +
                (annual_living_expenses_for_family * years_of_protection) +
                total_education_cost -
                liquid_assets
            )
            # Ensure not negative
            if life_insurance_need < 0:
                life_insurance_need = Decimal('0')

            # --- Health Insurance Calculation ---
            # Based on family size and age
            # We'll suggest a coverage amount per person
            # Base coverage per adult: ₹10 lakhs
            # Base coverage per child: ₹5 lakhs
            # Additional for elderly parents (if applicable) - we don't have parent data, so skip
            base_coverage_per_adult = Decimal('1000000')  # ₹10 lakhs
            base_coverage_per_child = Decimal('500000')   # ₹5 lakhs

            # Number of adults: self + spouse (if married)
            num_adults = 1
            if marital_status == 'married':
                num_adults += 1  # assuming spouse

            health_insurance_need = (
                (num_adults * base_coverage_per_adult) +
                (dependents_count * base_coverage_per_child)
            )

            # --- Property Insurance Calculation ---
            # For home and contents
            # We'll look for assets that are property
            property_value = Decimal('0')
            contents_value = Decimal('0')
            for asset in assets:
                if asset.asset_type == 'property':
                    property_value += asset.current_value
                elif asset.asset_type in ['jewelry', 'electronics', 'furniture']:
                    contents_value += asset.current_value

            # Property insurance should cover reinstatement value of property and contents
            # We'll assume contents are 50% of property value if not specified separately
            if property_value > 0 and contents_value == 0:
                contents_value = property_value * Decimal('0.5')

            property_insurance_need = property_value + contents_value

            # If no property asset found, we might still need renters insurance for contents
            # But for simplicity, we'll only suggest if there's property or significant contents

            return {
                "insurance_needs": {
                    "life_insurance": {
                        "recommended_coverage": float(life_insurance_need),
                        "currency": "INR",
                        "breakdown": {
                            "outstanding_liabilities": float(total_liabilities_outstanding),
                            "income_protection": float(annual_living_expenses_for_family * years_of_protection),
                            "children_education": float(total_education_cost),
                            "less_liquid_assets": float(liquid_assets)
                        }
                    },
                    "health_insurance": {
                        "recommended_coverage": float(health_insurance_need),
                        "currency": "INR",
                        "breakdown": {
                            "adults_covered": num_adults,
                            "children_covered": dependents_count,
                            "coverage_per_adult": float(base_coverage_per_adult),
                            "coverage_per_child": float(base_coverage_per_child)
                        }
                    },
                    "property_insurance": {
                        "recommended_coverage": float(property_insurance_need),
                        "currency": "INR",
                        "breakdown": {
                            "property_value": float(property_value),
                            "contents_value": float(contents_value)
                        }
                    }
                },
                "calculation_details": {
                    "user_profile": {
                        "age": age,
                        "marital_status": marital_status,
                        "dependents_count": dependents_count,
                        "annual_income": float(annual_income),
                        "annual_expenses": float(annual_expenses)
                    },
                    "financial_snapshot": {
                        "total_assets": float(total_assets_value),
                        "total_liabilities": float(total_liabilities_outstanding),
                        "liquid_assets": float(liquid_assets)
                    }
                },
                "assumptions": {
                    "life_insurance": {
                        "retirement_age": 60,
                        "years_of_protection": 10,
                        "income_replacement_ratio": "80% of annual expenses",
                        "education_cost_per_child": "₹25,00,000",
                        "existing_life_insurance": "₹0 (not modeled)"
                    },
                    "health_insurance": {
                        "coverage_per_adult": "₹10,00,000",
                        "coverage_per_child": "₹5,00,000",
                        "note": "Based on average hospitalization costs in metro cities in India"
                    },
                    "property_insurance": {
                        "contents_assumption": "50% of property value if contents not separately specified",
                        "note": "Covers reinstatement value of property and contents"
                    },
                    "currency": "INR",
                    "date": "2026-08-27",
                    "note": "This is a simplified insurance needs analysis. Actual requirements may vary based on specific goals, existing policies, and risk tolerance."
                },
                "calculation_id": f"calc-insurance-{user_id_str}-{int(__import__('time').time())}",
                "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z"
            }
        finally:
            db.close()

    def _calculate_annual_income(self, income_sources):
        annual_income = Decimal('0')
        for income in income_sources:
            annual_amount = income.amount
            if income.frequency == 'monthly':
                annual_amount = income.amount * 12
            elif income.frequency == 'quarterly':
                annual_amount = income.amount * 4
            elif income.frequency == 'annually':
                annual_amount = income.amount
            elif income.frequency == 'one-time':
                # For one-time income, we don't annualize it for regular income calculation
                # but we can consider it as part of annual income in the year it occurs.
                # For insurance planning, we might want to consider it as it adds to net worth.
                # However, for protection planning, we focus on recurring income.
                # We'll skip one-time income for annual income calculation here.
                continue
            annual_income += annual_amount
        return annual_income

    def _calculate_annual_expenses(self, expenses):
        annual_expenses = Decimal('0')
        for expense in expenses:
            monthly_amount = expense.amount
            if expense.frequency == 'monthly':
                monthly_amount = expense.amount
            elif expense.frequency == 'quarterly':
                monthly_amount = expense.amount / 3
            elif expense.frequency == 'annually':
                monthly_amount = expense.amount / 12
            elif expense.frequency == 'one-time':
                # One-time expenses are not recurring, so skip for annual expenses
                continue
            annual_expenses += monthly_amount * 12
        return annual_expenses