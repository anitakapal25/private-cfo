from app.tools.base import BaseTool
from app.models.user import User
from app.models.financial import Asset, Liability, Goal, FinancialFreedomTarget
from app.core.config import get_db
from typing import Dict, Any
import uuid
from decimal import Decimal
from datetime import date

class InvestmentPortfolioAnalysisTool(BaseTool):
    """Analyze investment portfolio and provide optimization recommendations.

    This tool uses the deterministic calculation engine and returns
    an auditable result with assumptions and inputs documented.
    Never performs calculations based on LLM-generated arithmetic.
    """

    def get_description(self) -> str:
        return "Analyze investment portfolio allocation, risk profile, and provide optimization recommendations based on financial goals and risk tolerance."

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze investment portfolio.

        This is a deterministic calculation based on user's assets, goals, and financial freedom target.
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
            # Get user details
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                return {"error": "User not found"}

            # Get user's assets (only active assets)
            assets = db.query(Asset).filter(
                Asset.user_id == user_id,
                Asset.is_active == True
            ).all()

            # Get user's goals
            goals = db.query(Goal).filter(
                Goal.user_id == user_id,
                Goal.is_active == True
            ).all()

            # Get financial freedom target
            ff_target = db.query(FinancialFreedomTarget).filter(
                FinancialFreedomTarget.user_id == user_id
            ).first()

            # Calculate current date for age calculations
            today = date.today()
            current_age = today.year - user.date_of_birth.year - ((today.month, today.day) < (user.date_of_birth.month, user.date_of_birth.day))

            # --- Asset Allocation Analysis ---
            # Group assets by type and calculate totals
            assets_by_type = {}
            total_assets_value = Decimal('0')
            investment_assets = Decimal('0')  # Assets that are investments (exclude personal use items)

            for asset in assets:
                asset_type = asset.asset_type
                if asset_type not in assets_by_type:
                    assets_by_type[asset_type] = Decimal('0')
                assets_by_type[asset_type] += asset.current_value
                total_assets_value += asset.current_value

                # Consider certain asset types as investments for portfolio analysis
                if asset_type in ['mutual_funds', 'stocks', 'bonds', 'etf', 'epf', 'ppf', 'nps', 'gold', 'real_estate_investment']:
                    investment_assets += asset.current_value

            # Calculate allocation percentages
            allocation_by_type = {}
            for asset_type, value in assets_by_type.items():
                if total_assets_value > 0:
                    allocation_by_type[asset_type] = (value / total_assets_value) * 100
                else:
                    allocation_by_type[asset_type] = Decimal('0')

            # --- Risk Profiling ---
            # Simple risk score based on asset allocation
            # Higher allocation to volatile assets = higher risk
            risk_weights = {
                'cash': 0.1,
                'savings_account': 0.1,
                'fixed_deposit': 0.2,
                'epf': 0.3,
                'ppf': 0.3,
                'nps': 0.4,
                'mutual_funds': 0.6,
                'etf': 0.6,
                'stocks': 0.8,
                'bonds': 0.4,
                'gold': 0.5,
                'real_estate': 0.5,
                'real_estate_investment': 0.6,
                'property': 0.3  # Primary residence is less risky
            }

            weighted_risk_score = Decimal('0')
            total_weighted_value = Decimal('0')

            for asset_type, value in assets_by_type.items():
                weight = risk_weights.get(asset_type, 0.5)  # Default medium risk
                weighted_risk_score += value * Decimal(str(weight))
                total_weighted_value += value

            risk_score = Decimal('0')
            if total_weighted_value > 0:
                risk_score = weighted_risk_score / total_weighted_value

            # Convert to risk category (0-1 scale)
            if risk_score <= 0.3:
                risk_category = "Conservative"
            elif risk_score <= 0.6:
                risk_category = "Moderate"
            else:
                risk_category = "Aggressive"

            # --- Goal-Based Analysis ---
            total_goal_amount = Decimal('0')
            goals_by_type = {}
            monthly_goal_contribution = Decimal('0')

            for goal in goals:
                goal_type = goal.goal_type
                if goal_type not in goals_by_type:
                    goals_by_type[goal_type] = []
                goals_by_type[goal_type].append({
                    'goal_name': goal.goal_name,
                    'target_amount': goal.target_amount,
                    'current_amount': goal.current_amount,
                    'target_date': goal.target_date.isoformat() if goal.target_date else None,
                    'monthly_contribution': goal.monthly_contribution,
                    'priority': goal.priority
                })
                total_goal_amount += goal.target_amount
                monthly_goal_contribution += goal.monthly_contribution

            # --- Financial Freedom Progress ---
            ff_progress = {}
            if ff_target:
                years_to_target = max(0, ff_target.target_age - current_age)
                ff_progress = {
                    'target_age': ff_target.target_age,
                    'current_age': current_age,
                    'years_to_target': years_to_target,
                    'target_lifestyle_expenses': float(ff_target.target_lifestyle_expenses),
                    'required_corpus': float(ff_target.required_corpus) if ff_target.required_corpus else None,
                    'current_projected_corpus': float(ff_target.current_projected_corpus) if ff_target.current_projected_corpus else None,
                    'freedom_gap': float(ff_target.freedom_gap) if ff_target.freedom_gap else None
                }

            # --- Optimization Recommendations ---
            recommendations = []

            # Asset allocation recommendations based on risk profile and goals
            if risk_category == "Conservative":
                # Suggest increasing growth assets slightly for long-term goals
                if total_goal_amount > investment_assets * 2:  # Goals much larger than current investments
                    recommendations.append({
                        'type': 'allocation',
                        'priority': 'medium',
                        'suggestion': 'Consider increasing allocation to growth assets (mutual funds, stocks) for long-term goal funding',
                        'current_allocation': {
                            'mutual_funds': float(allocation_by_type.get('mutual_funds', 0)),
                            'stocks': float(allocation_by_type.get('stocks', 0)),
                            'etf': float(allocation_by_type.get('etf', 0))
                        },
                        'suggested_range': {
                            'mutual_funds': '20-35%',
                            'stocks': '10-25%',
                            'etf': '5-15%'
                        }
                    })
            elif risk_category == "Aggressive":
                # Suggest adding stability for capital preservation
                recommendations.append({
                    'type': 'allocation',
                    'priority': 'medium',
                    'suggestion': 'Consider adding stable assets (fixed deposits, bonds) for capital preservation',
                    'current_allocation': {
                        'fixed_deposit': float(allocation_by_type.get('fixed_deposit', 0)),
                        'bonds': float(allocation_by_type.get('bonds', 0)),
                        'epf': float(allocation_by_type.get('epf', 0)),
                        'ppf': float(allocation_by_type.get('ppf', 0))
                    },
                    'suggested_range': {
                        'fixed_deposit': '10-20%',
                        'bonds': '10-20%',
                        'epf': '10-15%' if user.employment_status == 'employed' else '0-5%',
                        'ppf': '5-15%'
                    }
                })

            # Rebalancing recommendations
            # Define target allocations based on risk profile
            target_allocations = {
                'Conservative': {
                    'fixed_deposit': 30,
                    'epf': 15,
                    'ppf': 15,
                    'mutual_funds': 25,
                    'stocks': 10,
                    'bonds': 5,
                    'gold': 5,
                    'real_estate': 0,
                    'cash': 0,
                    'savings_account': 0,
                    'nps': 0,
                    'etf': 0,
                    'real_estate_investment': 0,
                    'property': 0
                },
                'Moderate': {
                    'fixed_deposit': 20,
                    'epf': 10,
                    'ppf': 10,
                    'mutual_funds': 30,
                    'stocks': 20,
                    'bonds': 10,
                    'gold': 5,
                    'real_estate': 0,
                    'cash': 0,
                    'savings_account': 0,
                    'nps': 0,
                    'etf': 0,
                    'real_estate_investment': 0,
                    'property': 0
                },
                'Aggressive': {
                    'fixed_deposit': 10,
                    'epf': 5,
                    'ppf': 5,
                    'mutual_funds': 35,
                    'stocks': 30,
                    'bonds': 5,
                    'gold': 5,
                    'real_estate': 0,
                    'cash': 0,
                    'savings_account': 0,
                    'nps': 0,
                    'etf': 0,
                    'real_estate_investment': 0,
                    'property': 0
                }
            }

            user_target_allocation = target_allocations.get(risk_category, target_allocations['Moderate'])

            # Calculate rebalancing needs
            rebalancing_needs = []
            for asset_type, target_pct in user_target_allocation.items():
                current_pct = float(allocation_by_type.get(asset_type, 0))
                if asset_type in ['property', 'real_estate'] and current_pct > 0:
                    # Skip rebalancing primary residence
                    continue
                diff = current_pct - target_pct
                if abs(diff) >= 5:  # Significant deviation
                    rebalancing_needs.append({
                        'asset_type': asset_type,
                        'current_allocation': current_pct,
                        'target_allocation': target_pct,
                        'difference': diff,
                        'action': 'reduce' if diff > 0 else 'increase',
                        'amount_to_adjust': float(abs(diff) * float(total_assets_value) / 100)
                    })

            if rebalancing_needs:
                recommendations.append({
                    'type': 'rebalancing',
                    'priority': 'high',
                    'suggestion': 'Portfolio rebalancing recommended to align with risk profile',
                    'details': rebalancing_needs
                })

            # Emergency fund recommendation
            # Calculate monthly expenses from Financial Freedom Target or estimate
            monthly_expenses = Decimal('0')
            if ff_target and ff_target.target_lifestyle_expenses:
                monthly_expenses = ff_target.target_lifestyle_expenses / 12
            else:
                # Rough estimate: 50% of income if we had income data
                # For now, we'll skip this recommendation without expense data
                pass

            liquid_assets = assets_by_type.get('savings_account', Decimal('0')) + assets_by_type.get('fixed_deposit', Decimal('0'))
            if monthly_expenses > 0 and liquid_assets < monthly_expenses * 6:  # Less than 6 months expenses
                recommendations.append({
                    'type': 'emergency_fund',
                    'priority': 'high',
                    'suggestion': 'Build emergency fund to cover 6 months of essential expenses',
                    'current_liquid_assets': float(liquid_assets),
                    'recommended_emergency_fund': float(monthly_expenses * 6),
                    'shortfall': float(max(monthly_expenses * 6 - liquid_assets, 0))
                })

            return {
                "portfolio_analysis": {
                    "total_assets_value": float(total_assets_value),
                    "investment_assets_value": float(investment_assets),
                    "asset_allocation": {k: float(v) for k, v in allocation_by_type.items()},
                    "risk_profile": {
                        "risk_score": float(risk_score),
                        "risk_category": risk_category,
                        "description": f"{risk_category} risk profile based on current asset allocation"
                    },
                    "goals_analysis": {
                        "total_goal_amount": float(total_goal_amount),
                        "goals_by_type": goals_by_type,
                        "monthly_goal_contribution": float(monthly_goal_contribution)
                    },
                    "financial_freedom_progress": ff_progress
                },
                "recommendations": recommendations,
                "calculation_details": {
                    "user_profile": {
                        "age": current_age,
                        "employment_status": user.employment_status,
                        "primary_occupation": user.primary_occupation
                    },
                    "asset_breakdown": [
                        {"type": asset_type, "amount": float(value), "percentage": float(allocation_by_type.get(asset_type, 0))}
                        for asset_type, value in assets_by_type.items()
                    ]
                },
                "assumptions": {
                    "risk_weights": risk_weights,
                    "target_allocations": target_allocations,
                    "emergency_fund_months": 6,
                    "rebalancing_threshold": "5% deviation from target allocation",
                    "currency": "INR",
                    "date": "2026-08-28",
                    "note": "This is a simplified portfolio analysis. Actual investment advice should consider individual circumstances, tax implications, and market conditions."
                },
                "calculation_id": f"calc-investment-{user_id_str}-{int(__import__('time').time())}",
                "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z"
            }
        finally:
            db.close()