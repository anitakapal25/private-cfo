from app.tools.base import BaseTool
from app.models.financial import IncomeSource
from app.core.config import get_db
from typing import Dict, Any
import uuid
from decimal import Decimal
from app.guardrails.assumption_freshness import require_current_assumption, StaleAssumptionError
from app.guardrails.catalog import TAX_RULES_FY_2023_24

class TaxOptimizationTool(BaseTool):
    """Compare old and new tax regimes for India and recommend the better option.

    This tool uses the deterministic calculation engine and returns
    an auditable result with assumptions and inputs documented.
    Never performs calculations based on LLM-generated arithmetic.
    """

    def get_description(self) -> str:
        return "Compare old and new tax regimes for India based on user's income and suggest the regime that results in lower tax liability."

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate tax liability under old and new tax regimes.

        This is a deterministic calculation based on income tax slabs for FY 2023-24 (AY 2024-25).
        """
        try:
            require_current_assumption(TAX_RULES_FY_2023_24)
        except StaleAssumptionError as exc:
            return {
                "error": str(exc),
                "error_code": "STALE_ASSUMPTION",
                "source": TAX_RULES_FY_2023_24.source_url,
            }

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
            # Get all active income sources for the user
            income_sources = db.query(IncomeSource).filter(
                IncomeSource.user_id == user_id,
                IncomeSource.is_active == True
            ).all()

            if not income_sources:
                return {"error": "No income sources found for the user"}

            # Calculate annual gross total income
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
                    # For one-time income, we consider it as part of annual income in the year it occurs
                    annual_amount = income.amount
                annual_income += annual_amount

            # Define tax slabs for FY 2023-24 (AY 2024-25)
            # Old regime slabs (for individuals below 60 years)
            old_regime_slabs = [
                (Decimal('250000'), Decimal('0')),      # 0% up to 2.5L
                (Decimal('500000'), Decimal('0.05')),   # 5% from 2.5L to 5L
                (Decimal('1000000'), Decimal('0.20')),  # 20% from 5L to 10L
                (Decimal('Infinity'), Decimal('0.30'))  # 30% above 10L
            ]

            # New regime slabs (for FY 2023-24)
            new_regime_slabs = [
                (Decimal('300000'), Decimal('0')),      # 0% up to 3L
                (Decimal('600000'), Decimal('0.05')),   # 5% from 3L to 6L
                (Decimal('900000'), Decimal('0.10')),   # 10% from 6L to 9L
                (Decimal('1200000'), Decimal('0.15')),  # 15% from 9L to 12L
                (Decimal('1500000'), Decimal('0.20')),  # 20% from 12L to 15L
                (Decimal('Infinity'), Decimal('0.30'))  # 30% above 15L
            ]

            # Deductions for old regime (FY 2023-24)
            # Standard deduction: ₹50,000
            # Section 80C: ₹1,50,000 (assuming max investment)
            # Section 80D: ₹50,000 (assuming medical insurance for self/family and parents)
            old_regime_deductions = Decimal('50000') + Decimal('150000') + Decimal('50000')  # ₹2,50,000

            # Deductions for new regime (FY 2023-24): only standard deduction of ₹50,000
            new_regime_deductions = Decimal('50000')

            # Calculate taxable income for each regime
            old_taxable_income = max(Decimal('0'), annual_income - old_regime_deductions)
            new_taxable_income = max(Decimal('0'), annual_income - new_regime_deductions)

            # Function to calculate tax based on slabs
            def calculate_tax(income, slabs):
                tax = Decimal('0')
                prev_limit = Decimal('0')
                for limit, rate in slabs:
                    if income > prev_limit:
                        taxable_in_slab = min(income, limit) - prev_limit
                        tax += taxable_in_slab * rate
                        prev_limit = limit
                    if income <= limit:
                        break
                return tax

            # Calculate tax for each regime (before cess)
            old_tax = calculate_tax(old_taxable_income, old_regime_slabs)
            new_tax = calculate_tax(new_taxable_income, new_regime_slabs)

            # Add health and education cess @ 4%
            old_tax_with_cess = old_tax * Decimal('1.04')
            new_tax_with_cess = new_tax * Decimal('1.04')

            # Determine which regime is better
            if old_tax_with_cess < new_tax_with_cess:
                recommended_regime = 'old'
                tax_saving = new_tax_with_cess - old_tax_with_cess
            else:
                recommended_regime = 'new'
                tax_saving = old_tax_with_cess - new_tax_with_cess

            return {
                "tax_analysis": {
                    "annual_gross_income": float(annual_income),
                    "old_regime": {
                        "deductions": float(old_regime_deductions),
                        "taxable_income": float(old_taxable_income),
                        "tax_before_cess": float(old_tax),
                        "tax_after_cess": float(old_tax_with_cess)
                    },
                    "new_regime": {
                        "deductions": float(new_regime_deductions),
                        "taxable_income": float(new_taxable_income),
                        "tax_before_cess": float(new_tax),
                        "tax_after_cess": float(new_tax_with_cess)
                    },
                    "recommended_regime": recommended_regime,
                    "tax_saving": float(tax_saving),
                    "currency": "INR",
                    "assessment_year": "2024-25",
                    "financial_year": "2023-24"
                },
                "calculation_details": {
                    "income_sources": [
                        {
                            "source_name": income.source_name,
                            "source_type": income.source_type,
                            "amount": float(income.amount),
                            "frequency": income.frequency,
                            "annual_equivalent": float(
                                income.amount * 12 if income.frequency == 'monthly'
                                else income.amount * 4 if income.frequency == 'quarterly'
                                else income.amount if income.frequency == 'annually'
                                else income.amount  # one-time
                            )
                        }
                        for income in income_sources if income.is_active
                    ]
                },
                "assumptions": {
                    "tax_regime": "FY 2023-24 (AY 2024-25)",
                    "old_regime_deductions": {
                        "standard_deduction": 50000,
                        "section_80c": 150000,
                        "section_80d": 50000,
                        "total": 250000
                    },
                    "new_regime_deductions": {
                        "standard_deduction": 50000,
                        "total": 50000
                    },
                    "cess_rate": "4%",
                    "note": "This is a simplified tax calculation. Actual tax liability may vary based on additional deductions, exemptions, and specific circumstances."
                },
                "calculation_id": f"calc-taxopt-{user_id_str}-{int(__import__('time').time())}",
                "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z"
            }
        finally:
            db.close()
