from app.tools.base import BaseTool
from app.models.financial import IncomeSource, Expense, Asset, Liability, FinancialFreedomTarget
from app.core.config import get_db
from typing import Dict, Any
import uuid
from decimal import Decimal


def calculate_real_return(nominal_return: Decimal, inflation: Decimal) -> Decimal:
    """Convert nominal return and inflation assumptions to an exact real return."""
    if inflation <= Decimal('-1'):
        raise ValueError("Inflation must be greater than -100%")
    return (Decimal('1') + nominal_return) / (Decimal('1') + inflation) - Decimal('1')


class CalculateNetWorthTool(BaseTool):
    """Calculate user's net worth as total assets minus total liabilities.

    This tool uses the deterministic calculation engine and returns
    an auditable result with assumptions and inputs documented.
    Never performs calculations based on LLM-generated arithmetic.
    """

    def get_description(self) -> str:
        return "Calculate user's net worth by subtracting total liabilities from total assets. Provides detailed breakdown by asset and liability types with calculation ID for audit trail."

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate net worth from user's assets and liabilities in database.

        This is a deterministic calculation: Net Worth = Total Assets - Total Liabilities
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
            # Calculate total assets (only active assets)
            assets = db.query(Asset).filter(
                Asset.user_id == user_id,
                Asset.is_active == True
            ).all()

            total_assets = sum(asset.current_value for asset in assets)

            # Calculate total liabilities (only active liabilities)
            liabilities = db.query(Liability).filter(
                Liability.user_id == user_id,
                Liability.is_active == True
            ).all()

            total_liabilities = sum(liability.principal_outstanding for liability in liabilities)

            # Calculate net worth (deterministic formula)
            net_worth = total_assets - total_liabilities

            # Group assets by type for detailed breakdown
            assets_by_type = {}
            for asset in assets:
                asset_type = asset.asset_type
                if asset_type not in assets_by_type:
                    assets_by_type[asset_type] = Decimal('0')
                assets_by_type[asset_type] += asset.current_value

            # Group liabilities by type for detailed breakdown
            liabilities_by_type = {}
            for liability in liabilities:
                liability_type = liability.liability_type
                if liability_type not in liabilities_by_type:
                    liabilities_by_type[liability_type] = Decimal('0')
                liabilities_by_type[liability_type] += liability.principal_outstanding

            return {
                "net_worth": {
                    "amount": float(net_worth),
                    "currency": "INR"
                },
                "total_assets": {
                    "amount": float(total_assets),
                    "currency": "INR"
                },
                "total_liabilities": {
                    "amount": float(total_liabilities),
                    "currency": "INR"
                },
                "calculation_details": {
                    "assets_by_type": [
                        {"type": asset_type, "amount": float(amount)}
                        for asset_type, amount in assets_by_type.items()
                    ],
                    "liabilities_by_type": [
                        {"type": liability_type, "amount": float(amount)}
                        for liability_type, amount in liabilities_by_type.items()
                    ]
                },
                "assumptions": {
                    "valuation_method": "current_market_value",
                    "currency": "INR",
                    "date": "2026-08-26"  # In reality, this would be the calculation date
                },
                "calculation_id": f"calc-networth-{user_id_str}-{int(__import__('time').time())}",
                "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z"
            }
        finally:
            db.close()


class CalculateSavingsRateTool(BaseTool):
    """Calculate user's savings rate as (total income - total expenses) / total income.

    This tool uses the deterministic calculation engine and returns
    an auditable result with assumptions and inputs documented.
    Never performs calculations based on LLM-generated arithmetic.
    """

    def get_description(self) -> str:
        return "Calculate user's savings rate by determining the proportion of income that is saved. Returns rate as percentage and absolute monthly savings amount."

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate savings rate from user's income and expenses in database.

        This is a deterministic calculation: Savings Rate = (Total Income - Total Expenses) / Total Income
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
            # Calculate total monthly income (only active income sources)
            income_sources = db.query(IncomeSource).filter(
                IncomeSource.user_id == user_id,
                IncomeSource.is_active == True
            ).all()

            # Convert all income to monthly equivalent
            total_monthly_income = Decimal('0')
            for income in income_sources:
                monthly_amount = income.amount
                if income.frequency == 'quarterly':
                    monthly_amount = income.amount / 3
                elif income.frequency == 'annually':
                    monthly_amount = income.amount / 12
                # For one-time income, we don't include in regular monthly calculation
                elif income.frequency == 'one-time':
                    continue
                total_monthly_income += monthly_amount

            # Calculate total monthly expenses (only active expenses)
            expenses = db.query(Expense).filter(
                Expense.user_id == user_id,
                Expense.is_active == True
            ).all()

            # Convert all expenses to monthly equivalent
            total_monthly_expenses = Decimal('0')
            for expense in expenses:
                monthly_amount = expense.amount
                if expense.frequency == 'quarterly':
                    monthly_amount = expense.amount / 3
                elif expense.frequency == 'annually':
                    monthly_amount = expense.amount / 12
                # For one-time expenses, we don't include in regular monthly calculation
                elif expense.frequency == 'one-time':
                    continue
                total_monthly_expenses += monthly_amount

            # Calculate savings rate (deterministic formula)
            if total_monthly_income > 0:
                savings_rate = (total_monthly_income - total_monthly_expenses) / total_monthly_income
                savings_amount = total_monthly_income - total_monthly_expenses
            else:
                savings_rate = Decimal('0')
                savings_amount = Decimal('0')

            return {
                "savings_rate": {
                    "rate": float(savings_rate),  # As decimal (0.25 for 25%)
                    "percentage": float(savings_rate * 100)  # As percentage
                },
                "total_monthly_income": {
                    "amount": float(total_monthly_income),
                    "currency": "INR"
                },
                "total_monthly_expenses": {
                    "amount": float(total_monthly_expenses),
                    "currency": "INR"
                },
                "monthly_savings_amount": {
                    "amount": float(savings_amount),
                    "currency": "INR"
                },
                "calculation_details": {
                    "income_sources": [
                        {
                            "source_name": income.source_name,
                            "source_type": income.source_type,
                            "amount": float(income.amount),
                            "frequency": income.frequency,
                            "monthly_equivalent": float(
                                income.amount if income.frequency == 'monthly'
                                else income.amount / 3 if income.frequency == 'quarterly'
                                else income.amount / 12 if income.frequency == 'annually'
                                else 0
                            )
                        }
                        for income in income_sources if income.is_active and income.frequency != 'one-time'
                    ],
                    "expenses": [
                        {
                            "description": expense.description,
                            "category": expense.category,
                            "amount": float(expense.amount),
                            "frequency": expense.frequency,
                            "monthly_equivalent": float(
                                expense.amount if expense.frequency == 'monthly'
                                else expense.amount / 3 if expense.frequency == 'quarterly'
                                else expense.amount / 12 if expense.frequency == 'annually'
                                else 0
                            )
                        }
                        for expense in expenses if expense.is_active and expense.frequency != 'one-time'
                    ]
                },
                "assumptions": {
                    "calculation_basis": "monthly_equivalent",
                    "currency": "INR",
                    "date": "2026-08-26"
                },
                "calculation_id": f"calc-savingsrate-{user_id_str}-{int(__import__('time').time())}",
                "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z"
            }
        finally:
            db.close()


class CalculateFreedomNumberTool(BaseTool):
    """Calculate user's financial freedom number (required corpus) based on target lifestyle expenses.

    This tool uses the deterministic calculation engine and returns
    an auditable result with assumptions and inputs documented.
    Never performs calculations based on LLM-generated arithmetic.
    """

    def get_description(self) -> str:
        return "Calculate the financial freedom number (required corpus) needed to sustain target lifestyle expenses through passive income. Uses present value calculation with expected return rate and time horizon."

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate financial freedom number from user's financial freedom target.

        This is a deterministic calculation using present value formula:
        Freedom Number = (Annual Expenses × (1 - (1 + r)^-n)) / r
        Where r = real return rate, n = years in retirement
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
            # Get user's financial freedom target
            ff_target = db.query(FinancialFreedomTarget).filter(
                FinancialFreedomTarget.user_id == user_id
            ).first()

            if not ff_target:
                return {"error": "Financial freedom target not found. Please set your financial freedom target first."}

            # Extract parameters from target
            target_monthly_expenses = ff_target.target_lifestyle_expenses
            inflation_assumption = ff_target.inflation_assumption
            return_assumption = ff_target.return_assumption
            target_age = ff_target.target_age
            current_age = ff_target.current_age or 30  # Default if not calculated yet

            # Calculate annual lifestyle expenses
            annual_lifestyle_expenses = target_monthly_expenses * 12

            real_return_rate = calculate_real_return(return_assumption, inflation_assumption)

            # Calculate years in retirement (assuming lifespan of 85 years, or use target_age + 20 as default)
            years_in_retirement = max(20, 85 - target_age)  # At least 20 years, or until age 85

            # Calculate financial freedom number using present value formula
            # Handle edge case where real_return_rate is zero or very close to zero
            if abs(real_return_rate) < 0.0001:  # Essentially zero
                freedom_number = annual_lifestyle_expenses * years_in_retirement
            else:
                # Present value of annuity formula: PV = PMT × [1 - (1 + r)^-n] / r
                freedom_number = annual_lifestyle_expenses * (
                    (1 - (1 + real_return_rate) ** (-years_in_retirement)) / real_return_rate
                )

            # Ensure freedom number is not negative
            if freedom_number < 0:
                freedom_number = Decimal('0')

            return {
                "freedom_number": {
                    "amount": float(freedom_number),
                    "currency": "INR"
                },
                "calculation_details": {
                    "target_monthly_expenses": float(target_monthly_expenses),
                    "annual_lifestyle_expenses": float(annual_lifestyle_expenses),
                    "real_return_rate": float(real_return_rate),
                    "inflation_assumption": float(inflation_assumption),
                    "return_assumption": float(return_assumption),
                    "target_age": target_age,
                    "current_age": current_age,
                    "years_in_retirement": years_in_retirement
                },
                "assumptions": {
                    "calculation_method": "present_value_of_annuity",
                    "lifespan_assumption": "85 years",
                    "currency": "INR",
                    "date": "2026-08-26",
                    "note": "Financial freedom number represents the corpus needed to generate passive income covering target lifestyle expenses"
                },
                "calculation_id": f"calc-freedomnumber-{user_id_str}-{int(__import__('time').time())}",
                "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z"
            }
        finally:
            db.close()


class CalculateFreedomGapTool(BaseTool):
    """Calculate user's freedom gap (difference between required corpus and projected corpus).

    This tool uses the deterministic calculation engine and returns
    an auditable result with assumptions and inputs documented.
    Never performs calculations based on LLM-generated arithmetic.
    """

    def get_description(self) -> str:
        return "Calculate the freedom gap - the difference between the financial freedom number (required corpus) and the projected corpus at target age. A positive gap indicates a shortfall to be addressed, while a negative gap indicates surplus."

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate freedom gap by comparing required corpus with projected corpus.

        This is a deterministic calculation: Freedom Gap = Required Corpus - Projected Corpus
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
            # Get user's financial freedom target
            ff_target = db.query(FinancialFreedomTarget).filter(
                FinancialFreedomTarget.user_id == user_id
            ).first()

            if not ff_target:
                return {"error": "Financial freedom target not found. Please set your financial freedom target first."}

            # Calculate required corpus (financial freedom number)
            # We'll reuse the logic from CalculateFreedomNumberTool but return the raw value
            target_monthly_expenses = ff_target.target_lifestyle_expenses
            inflation_assumption = ff_target.inflation_assumption
            return_assumption = ff_target.return_assumption
            target_age = ff_target.target_age
            current_age = ff_target.current_age or 30  # Default if not calculated yet

            # Calculate annual lifestyle expenses
            annual_lifestyle_expenses = target_monthly_expenses * 12

            real_return_rate = calculate_real_return(return_assumption, inflation_assumption)

            # Calculate years in retirement (assuming lifespan of 85 years, or use target_age + 20 as default)
            years_in_retirement = max(20, 85 - target_age)  # At least 20 years, or until age 85

            # Calculate required corpus using present value formula
            if abs(real_return_rate) < 0.0001:  # Essentially zero
                required_corpus = annual_lifestyle_expenses * years_in_retirement
            else:
                # Present value of annuity formula: PV = PMT × [1 - (1 + r)^-n] / r
                required_corpus = annual_lifestyle_expenses * (
                    (1 - (1 + real_return_rate) ** (-years_in_retirement)) / real_return_rate
                )

            # Calculate projected corpus at target age
            # This requires calculating future value of current assets and future contributions
            # For simplicity in MVP, we'll use a simplified projection based on current net worth growth
            # In a full implementation, this would consider current assets, savings rate, investment returns, etc.

            # Get current net worth as baseline
            from app.models.financial import Asset, Liability

            # Calculate total assets (only active assets)
            assets = db.query(Asset).filter(
                Asset.user_id == user_id,
                Asset.is_active == True
            ).all()
            total_assets = sum(asset.current_value for asset in assets)

            # Calculate total liabilities (only active liabilities)
            liabilities = db.query(Liability).filter(
                Liability.user_id == user_id,
                Liability.is_active == True
            ).all()
            total_liabilities = sum(liability.principal_outstanding for liability in liabilities)

            # Current net worth
            current_net_worth = total_assets - total_liabilities

            # Years to target
            years_to_target = max(0, target_age - current_age)

            # Simplified projection: assume current net worth grows at return assumption rate
            # In reality, this would also factor in ongoing savings/contributions
            if years_to_target > 0 and return_assumption != 0:
                projected_corpus = current_net_worth * ((1 + return_assumption) ** years_to_target)
            else:
                projected_corpus = current_net_worth

            # Calculate freedom gap
            freedom_gap = required_corpus - projected_corpus

            return {
                "freedom_gap": {
                    "amount": float(freedom_gap),
                    "currency": "INR"
                },
                "required_corpus": {
                    "amount": float(required_corpus),
                    "currency": "INR"
                },
                "projected_corpus": {
                    "amount": float(projected_corpus),
                    "currency": "INR"
                },
                "calculation_details": {
                    "target_monthly_expenses": float(target_monthly_expenses),
                    "annual_lifestyle_expenses": float(annual_lifestyle_expenses),
                    "real_return_rate": float(real_return_rate),
                    "inflation_assumption": float(inflation_assumption),
                    "return_assumption": float(return_assumption),
                    "target_age": target_age,
                    "current_age": current_age,
                    "years_in_retirement": years_in_retirement,
                    "years_to_target": years_to_target,
                    "current_net_worth": float(current_net_worth),
                    "total_assets": float(total_assets),
                    "total_liabilities": float(total_liabilities)
                },
                "assumptions": {
                    "calculation_method": "present_value_vs_future_value",
                    "projection_method": "compound_growth_of_current_net_worth",
                    "note": "This is a simplified projection. A full implementation would include future contributions, changing asset allocation, and more sophisticated growth modeling.",
                    "currency": "INR",
                    "date": "2026-08-26"
                },
                "calculation_id": f"calc-freedomgap-{user_id_str}-{int(__import__('time').time())}",
                "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z"
            }
        finally:
            db.close()


class CalculateProjectedCorpusTool(BaseTool):
    """Calculate user's projected corpus at target age based on current financial trajectory.

    This tool uses the deterministic calculation engine and returns
    an auditable result with assumptions and inputs documented.
    Never performs calculations based on LLM-generated arithmetic.
    """

    def get_description(self) -> str:
        return "Calculate the projected corpus at target age based on current assets, liabilities, savings rate, and expected investment returns. Shows the future value of current financial trajectory."

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate projected corpus at target age from current financial data.

        This is a deterministic calculation that projects:
        1. Future value of current assets
        2. Future value of ongoing savings (based on savings rate)
        3. Future value of liabilities (typically decreasing)
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
            # Get user's financial freedom target for assumptions and target age
            ff_target = db.query(FinancialFreedomTarget).filter(
                FinancialFreedomTarget.user_id == user_id
            ).first()

            if not ff_target:
                return {"error": "Financial freedom target not found. Please set your financial freedom target first."}

            # Extract parameters
            target_age = ff_target.target_age
            current_age = ff_target.current_age or 30  # Default if not calculated yet
            return_assumption = ff_target.return_assumption  # Expected investment return
            inflation_assumption = ff_target.inflation_assumption  # For real return calculation if needed

            # Calculate years to target
            years_to_target = max(0, target_age - current_age)

            # Get current financial data
            from app.models.financial import Asset, Liability, IncomeSource, Expense

            # Calculate total assets (only active assets)
            assets = db.query(Asset).filter(
                Asset.user_id == user_id,
                Asset.is_active == True
            ).all()
            total_assets = sum(asset.current_value for asset in assets)

            # Calculate total liabilities (only active liabilities)
            liabilities = db.query(Liability).filter(
                Liability.user_id == user_id,
                Liability.is_active == True
            ).all()
            total_liabilities = sum(liability.principal_outstanding for liability in liabilities)

            # Calculate current net worth
            current_net_worth = total_assets - total_liabilities

            # Calculate monthly savings rate (for future contributions)
            # Get income sources
            income_sources = db.query(IncomeSource).filter(
                IncomeSource.user_id == user_id,
                IncomeSource.is_active == True
            ).all()

            # Convert all income to monthly equivalent
            total_monthly_income = Decimal('0')
            for income in income_sources:
                monthly_amount = income.amount
                if income.frequency == 'quarterly':
                    monthly_amount = income.amount / 3
                elif income.frequency == 'annually':
                    monthly_amount = income.amount / 12
                elif income.frequency == 'one-time':
                    continue
                total_monthly_income += monthly_amount

            # Get expenses
            expenses = db.query(Expense).filter(
                Expense.user_id == user_id,
                Expense.is_active == True
            ).all()

            # Convert all expenses to monthly equivalent
            total_monthly_expenses = Decimal('0')
            for expense in expenses:
                monthly_amount = expense.amount
                if expense.frequency == 'quarterly':
                    monthly_amount = expense.amount / 3
                elif expense.frequency == 'annually':
                    monthly_amount = expense.amount / 12
                elif expense.frequency == 'one-time':
                    continue
                total_monthly_expenses += monthly_amount

            # Calculate monthly savings
            if total_monthly_income > 0:
                monthly_savings = total_monthly_income - total_monthly_expenses
                savings_rate = monthly_savings / total_monthly_income
            else:
                monthly_savings = Decimal('0')
                savings_rate = Decimal('0')

            # Calculate projected corpus components
            # 1. Future value of current assets
            # Assume assets grow at return_assumption rate
            future_value_assets = total_assets * ((1 + return_assumption) ** years_to_target) if years_to_target > 0 else total_assets

            # 2. Future value of ongoing savings (monthly contributions)
            # Future value of ordinary annuity: FV = PMT × [((1 + r)^n - 1) / r]
            future_value_savings = Decimal('0')
            if monthly_savings > 0 and years_to_target > 0 and return_assumption != 0:
                future_value_savings = monthly_savings * (((1 + return_assumption) ** years_to_target - 1) / return_assumption)
            elif monthly_savings > 0 and years_to_target > 0:
                future_value_savings = monthly_savings * (years_to_target * 12)  # Simple sum if no growth

            # 3. Future value of liabilities (assuming they decrease over time as paid off)
            # For simplicity, we'll assume liabilities are paid off linearly over their remaining terms
            # A more sophisticated approach would analyze each liability's amortization schedule
            future_value_liabilities = total_liabilities  # Simplified: assume constant for now
            # In reality, this should be less than current liabilities as debts get paid down

            # Calculate projected corpus at target age
            projected_corpus = future_value_assets + future_value_savings - future_value_liabilities

            # Ensure projected corpus is not negative
            if projected_corpus < 0:
                projected_corpus = Decimal('0')

            return {
                "projected_corpus": {
                    "amount": float(projected_corpus),
                    "currency": "INR"
                },
                "calculation_details": {
                    "current_net_worth": float(current_net_worth),
                    "total_assets": float(total_assets),
                    "total_liabilities": float(total_liabilities),
                    "monthly_savings": float(monthly_savings),
                    "savings_rate": float(savings_rate),
                    "years_to_target": years_to_target,
                    "return_assumption": float(return_assumption),
                    "future_value_assets": float(future_value_assets),
                    "future_value_savings": float(future_value_savings),
                    "future_value_liabilities": float(future_value_liabilities)
                },
                "assumptions": {
                    "calculation_method": "future_value_of_assets_plus_savings_minus_liabilities",
                    "asset_growth_rate": "return_assumption",
                    "savings_growth_rate": "return_assumption",
                    "liability_assumption": "constant_simplified",
                    "currency": "INR",
                    "date": "2026-08-26",
                    "note": "This projection includes future value of current assets, future savings contributions, and simplified liability treatment."
                },
                "calculation_id": f"calc-projcorpus-{user_id_str}-{int(__import__('time').time())}",
                "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z"
            }
        finally:
            db.close()
