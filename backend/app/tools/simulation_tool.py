from app.tools.base import BaseTool
from app.models.user import User
from app.models.financial import Asset, Liability, IncomeSource, Expense, FinancialFreedomTarget
from app.core.config import get_db
from typing import Dict, Any, List
import uuid
import random
import math
from datetime import date, datetime
from decimal import Decimal
import numpy as np


class SimulationTool(BaseTool):
    """Run Monte Carlo simulations for financial scenarios including market volatility,
    income variability, and expense fluctuations.

    This tool performs stochastic simulations to help users understand the range
    of possible financial outcomes based on probabilistic inputs.
    """

    def get_description(self) -> str:
        return "Run Monte Carlo simulations to model financial scenarios under uncertainty including market volatility, income changes, and expense fluctuations. Provides probabilistic outcomes for financial freedom timeline and corpus requirements."

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run Monte Carlo simulation for financial planning scenarios.

        Args:
            input_data: Dictionary containing user_id and simulation parameters

        Returns:
            Dictionary with simulation results including probability distributions
        """
        user_id_str = input_data.get("user_id")
        if not user_id_str:
            return {"error": "User ID is required"}

        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            return {"error": "Invalid user ID format"}

        # Get simulation parameters
        simulation_years = input_data.get("years", 10)
        num_simulations = input_data.get("simulations", 1000)
        include_income_var = input_data.get("include_income_variability", True)
        include_expense_var = input_data.get("include_expense_variability", True)
        include_market_var = input_data.get("include_market_volatility", True)

        # Get database session
        db = next(get_db())

        try:
            # Get user details
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                return {"error": "User not found"}

            # Get financial data
            assets = db.query(Asset).filter(Asset.user_id == user_id, Asset.is_active == True).all()
            liabilities = db.query(Liability).filter(Liability.user_id == user_id, Liability.is_active == True).all()
            income_sources = db.query(IncomeSource).filter(IncomeSource.user_id == user_id, IncomeSource.is_active == True).all()
            expenses = db.query(Expense).filter(Expense.user_id == user_id, Expense.is_active == True).all()

            # Get financial freedom target for context
            ff_target = db.query(FinancialFreedomTarget).filter(
                FinancialFreedomTarget.user_id == user_id
            ).first()

            # Calculate baseline financial metrics
            total_assets = sum(float(asset.current_value) for asset in assets)
            total_liabilities = sum(float(liability.principal_outstanding) for liability in liabilities)
            net_worth = total_assets - total_liabilities

            monthly_income = sum(float(income.amount) for income in income_sources if income.frequency == 'monthly')
            annual_income = monthly_income * 12

            monthly_expenses = sum(float(expense.amount) for expense in expenses if expense.frequency == 'monthly')
            annual_expenses = monthly_expenses * 12

            monthly_savings = monthly_income - monthly_expenses
            annual_savings = monthly_savings * 12

            # Set up simulation parameters
            simulation_results = []

            for sim in range(num_simulations):
                # Initialize simulation state
                current_net_worth = net_worth
                current_annual_income = annual_income
                current_annual_expenses = annual_expenses

                # Track yearly values
                yearly_net_worth = [current_net_worth]
                yearly_income = [current_annual_income]
                yearly_expenses = [current_annual_expenses]

                # Simulate each year
                for year in range(1, simulation_years + 1):
                    # Apply market volatility to investment assets
                    if include_market_var and assets:
                        # Assume 70% of assets are market-linked (simplification)
                        market_assets = total_assets * 0.7
                        non_market_assets = total_assets * 0.3

                        # Market return: normal distribution with mean 8%, volatility 15%
                        market_return = np.random.normal(0.08, 0.15)
                        market_assets *= (1 + market_return)

                        # Non-market assets grow at 4% (fixed deposits, etc.)
                        non_market_assets *= 1.04

                        total_assets = market_assets + non_market_assets
                    else:
                        # No market volatility - steady growth
                        total_assets *= 1.06  # 6% steady return

                    # Apply income variability
                    if include_income_var and income_sources:
                        # Income changes: normal distribution with mean 0%, volatility 10%
                        income_change = np.random.normal(0.0, 0.10)
                        current_annual_income *= (1 + income_change)

                        # Ensure income doesn't go negative
                        current_annual_income = max(current_annual_income, 0)
                    else:
                        # Steady income growth at 6%
                        current_annual_income *= 1.06

                    # Apply expense variability
                    if include_expense_var and expenses:
                        # Expense changes: normal distribution with mean 3% (inflation), volatility 5%
                        expense_change = np.random.normal(0.03, 0.05)
                        current_annual_expenses *= (1 + expense_change)

                        # Ensure expenses don't go negative
                        current_annual_expenses = max(current_annual_expenses, 0)
                    else:
                        # Steady expense growth at 6% inflation
                        current_annual_expenses *= 1.06

                    # Calculate savings and update net worth
                    annual_savings = current_annual_income - current_annual_expenses
                    current_net_worth += annual_savings

                    # Track yearly values
                    yearly_net_worth.append(current_net_worth)
                    yearly_income.append(current_annual_income)
                    yearly_expenses.append(current_annual_expenses)

                # Store simulation results
                simulation_results.append({
                    'final_net_worth': yearly_net_worth[-1],
                    'peak_net_worth': max(yearly_net_worth),
                    'final_income': yearly_income[-1],
                    'final_expenses': yearly_expenses[-1],
                    'yearly_net_worth': yearly_net_worth,
                    'yearly_income': yearly_income,
                    'yearly_expenses': yearly_expenses
                })

            # Analyze results
            final_net_worths = [result['final_net_worth'] for result in simulation_results]

            # Calculate statistics
            mean_final_nw = np.mean(final_net_worths)
            median_final_nw = np.median(final_net_worths)
            std_final_nw = np.std(final_net_worths)
            percentile_5 = np.percentile(final_net_worths, 5)
            percentile_25 = np.percentile(final_net_worths, 25)
            percentile_75 = np.percentile(final_net_worths, 75)
            percentile_95 = np.percentile(final_net_worths, 95)

            # Probability of achieving financial freedom target
            if ff_target and ff_target.required_corpus:
                target_corpus = float(ff_target.required_corpus)
                success_count = sum(1 for nw in final_net_worths if nw >= target_corpus)
                probability_success = (success_count / num_simulations) * 100
            else:
                # Use a default target based on current expenses * 25 (4% rule)
                target_corpus = annual_expenses * 25
                success_count = sum(1 for nw in final_net_worths if nw >= target_corpus)
                probability_success = (success_count / num_simulations) * 100

            # Calculate years to financial freedom for each simulation
            years_to_ff = []
            for result in simulation_results:
                yearly_nw = result['yearly_net_worth']
                yearly_exp = result['yearly_expenses']

                # Find first year where net worth >= 25 * annual expenses (4% rule)
                ff_year = None
                for year, (nw, exp) in enumerate(zip(yearly_nw, yearly_exp)):
                    if exp > 0 and nw >= (exp * 25):
                        ff_year = year
                        break

                if ff_year is not None:
                    years_to_ff.append(ff_year)
                else:
                    years_to_ff.append(simulation_years)  # Didn't achieve FF in simulation period

            mean_years_to_ff = np.mean(years_to_ff) if years_to_ff else simulation_years
            median_years_to_ff = np.median(years_to_ff) if years_to_ff else simulation_years

            # Format response
            response_parts = [
                f"Monte Carlo Simulation Results ({num_simulations} simulations over {simulation_years} years):",
                f"",
                f"Starting Financial Position:",
                f"• Net Worth: ₹{net_worth:,.0f}",
                f"• Annual Income: ₹{annual_income:,.0f}",
                f"• Annual Expenses: ₹{annual_expenses:,.0f}",
                f"• Annual Savings: ₹{annual_savings:,.0f}",
                f"",
                f"Projected Outcomes After {simulation_years} Years:",
                f"• Median Net Worth: ₹{median_final_nw:,.0f}",
                f"• Average Net Worth: ₹{mean_final_nw:,.0f}",
                f"• Range (5th-95th percentile): ₹{percentile_5:,.0f} - ₹{percentile_95:,.0f}",
                f"• Standard Deviation: ₹{std_final_nw:,.0f}",
                f"",
                f"Financial Freedom Analysis:",
                f"• Probability of achieving financial freedom: {probability_success:.1f}%",
                f"• Median years to financial freedom: {median_years_to_ff:.1f} years",
                f"• Average years to financial freedom: {mean_years_to_ff:.1f} years",
                f"",
                f"Key Insights:",
            ]

            # Add insights based on simulation
            if probability_success >= 70:
                response_parts.append("• Strong likelihood of achieving financial freedom goals")
            elif probability_success >= 40:
                response_parts.append("• Moderate chance of achieving financial freedom - consider increasing savings rate or reducing risk")
            else:
                response_parts.append("• Lower probability of achieving financial freedom - significant changes to savings/investment strategy may be needed")

            if std_final_nw > mean_final_nw * 0.5:
                response_parts.append("• High outcome variability suggests significant sensitivity to market conditions")
            else:
                response_parts.append("• Relatively stable outcomes across different market scenarios")

            if include_income_var:
                income_volatility = np.std([result['final_income'] for result in simulation_results]) / np.mean([result['final_income'] for result in simulation_results])
                if income_volatility > 0.3:
                    response_parts.append("• Income shows high variability - consider building emergency fund and developing multiple income streams")

            response_parts.append(f"• Simulation assumptions: {'Market volatility ' if include_market_var else ''}{'Income variability ' if include_income_var else ''}{'Expense variability ' if include_expense_var else ''}".strip())

            return {
                "simulation_results": {
                    "parameters": {
                        "simulation_years": simulation_years,
                        "num_simulations": num_simulations,
                        "include_market_volatility": include_market_var,
                        "include_income_variability": include_income_var,
                        "include_expense_variability": include_expense_var
                    },
                    "starting_position": {
                        "net_worth": net_worth,
                        "annual_income": annual_income,
                        "annual_expenses": annual_expenses,
                        "annual_savings": annual_savings
                    },
                    "projected_outcomes": {
                        "median_net_worth": median_final_nw,
                        "mean_net_worth": mean_final_nw,
                        "std_net_worth": std_final_nw,
                        "percentile_5": percentile_5,
                        "percentile_25": percentile_25,
                        "percentile_75": percentile_75,
                        "percentile_95": percentile_95
                    },
                    "financial_freedom_analysis": {
                        "target_corpus": target_corpus,
                        "probability_success": probability_success,
                        "median_years_to_ff": median_years_to_ff,
                        "mean_years_to_ff": mean_years_to_ff,
                        "years_to_ff_distribution": {
                            "min": (min(years_to_ff) if years_to_ff else simulation_years),
                            "max": (max(years_to_ff) if years_to_ff else simulation_years)
                        }
                    }
                },
                "calculation_details": {
                    "assumptions": {
                        "market_return_mean": "8% annual",
                        "market_return_volatility": "15% annual",
                        "income_change_volatility": "10% annual" if include_income_var else "0% (steady)",
                        "expense_change_volatility": "5% annual" if include_expense_var else "0% (steady inflation only)",
                        "base_income_growth": "6% annually" if not include_income_var else "Variable",
                        "base_expense_growth": "6% annually (inflation)" if not include_expense_var else "Variable",
                        "base_asset_growth": "6% annually" if not include_market_var else "Market-linked with 8% mean, 15% volatility",
                        "currency": "INR",
                        "simulation_date": date.today().isoformat()
                    },
                    "methodology": "Monte Carlo simulation with geometric Brownian motion for market returns and normal distributions for income/expense variations"
                },
                "calculation_id": f"calc-sim-{user_id_str}-{int(datetime.now().timestamp())}",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "response": ". ".join(response_parts)
            }

        finally:
            db.close()