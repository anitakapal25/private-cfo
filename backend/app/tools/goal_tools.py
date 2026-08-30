from app.tools.base import BaseTool
from app.models.user import User
from app.models.financial import Goal, FinancialFreedomTarget
from app.core.config import get_db
from typing import Dict, Any
import uuid
from decimal import Decimal
from datetime import date

class GoalPlanningTool(BaseTool):
    """Analyze financial goals and provide planning recommendations.

    This tool uses the deterministic calculation engine and returns
    an auditable result with assumptions and inputs documented.
    Never performs calculations based on LLM-generated arithmetic.
    """

    def get_description(self) -> str:
        return "Analyze financial goals, track progress, and provide recommendations for goal funding and prioritization."

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze financial goals.

        This is a deterministic calculation based on user's goals, income, expenses, and financial freedom target.
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

            # Get user's goals
            goals = db.query(Goal).filter(
                Goal.user_id == user_id,
                Goal.is_active == True
            ).all()

            # Get financial freedom target (for context)
            ff_target = db.query(FinancialFreedomTarget).filter(
                FinancialFreedomTarget.user_id == user_id
            ).first()

            # Calculate current date for age calculations
            today = date.today()
            current_age = today.year - user.date_of_birth.year - ((today.month, today.day) < (user.date_of_birth.month, user.date_of_birth.day))

            # --- Goals Analysis ---
            goals_analysis = []
            total_monthly_contribution_required = Decimal('0')
            total_monthly_contribution_current = Decimal('0')
            goals_by_priority = {'high': [], 'medium': [], 'low': []}

            for goal in goals:
                # Calculate time to goal in years
                time_to_goal = 0  # Default if no target date
                if goal.target_date:
                    try:
                        time_to_goal = max(0, (goal.target_date - today).days / 365.25)
                    except Exception:
                        time_to_goal = 0

                # Calculate required monthly contribution to reach goal
                # Formula: FV = PV * (1 + r)^n + PMT * [((1 + r)^n - 1) / r]
                # We want to solve for PMT: PMT = (FV - PV * (1 + r)^n) / [((1 + r)^n - 1) / r]
                # Where:
                #   FV = target_amount
                #   PV = current_amount
                #   r = monthly expected return (expected_return / 12)
                #   n = number of months (time_to_goal * 12)
                #   PMT = monthly_contribution_required

                # Adjust for inflation if needed
                target_amount = goal.target_amount
                if goal.inflation_adjusted and goal.target_date:
                    # Inflation adjust the target amount from today to target date
                    # Use a default inflation rate of 5% since it's not stored in the Goal model
                    years_inflation = time_to_goal
                    inflation_factor = (1 + 0.05) ** years_inflation
                    target_amount = goal.target_amount * Decimal(str(inflation_factor))

                # Calculate required monthly contribution
                if time_to_goal > 0 and goal.expected_return is not None:
                    try:
                        # Safely convert all values to float - explicit conversion to avoid Decimal issues
                        expected_return_val = float(str(goal.expected_return)) if goal.expected_return is not None else 0.0
                        time_to_goal_val = float(str(time_to_goal)) if time_to_goal is not None else 0.0
                        current_amount_val = float(str(goal.current_amount)) if goal.current_amount is not None else 0.0
                        target_amount_val = float(str(target_amount)) if target_amount is not None else 0.0

                        # Calculate monthly return and months
                        monthly_return = expected_return_val / 12.0
                        months = time_to_goal_val * 12.0
                        months_int = int(months)  # Integer for exponentiation

                        # Future value of current amount: FV = PV * (1 + r)^n
                        if months_int > 0:
                            # Explicitly convert everything to float to avoid Decimal issues
                            one_plus_r = 1.0 + float(monthly_return)
                            one_plus_r_float = float(one_plus_r)
                            months_int_int = int(months_int)
                            # Use pow() with explicit float conversion
                            power_result = float(pow(one_plus_r_float, months_int_int))
                            fv_current = float(current_amount_val) * power_result
                        else:
                            fv_current = float(current_amount_val)

                        # If future value of current amount already exceeds target, no additional contribution needed
                        if fv_current >= target_amount_val:
                            monthly_contribution_required = Decimal('0')
                        else:
                            # Calculate required monthly contribution
                            # PMT = (FV - FV_current) / [((1 + r)^n - 1) / r]
                            if months_int > 0 and monthly_return != 0:
                                one_plus_r_float = float(1.0 + monthly_return)
                                months_int_int = int(months_int)
                                one_plus_r_pow_n = float(pow(one_plus_r_float, months_int_int))
                                numerator = float(target_amount_val - fv_current)
                                denominator = float((one_plus_r_pow_n - 1.0) / monthly_return)
                                if denominator > 0:
                                    monthly_contribution_required = Decimal(str(numerator / denominator))
                                else:
                                    monthly_contribution_required = Decimal('0')
                            else:
                                # Simple division if no return or no time
                                monthly_contribution_required = Decimal('0')
                    except (ValueError, TypeError, OverflowError, Exception) as e:
                        # Fallback to simple calculation if there are any issues
                        if time_to_goal > 0 and goal.expected_return is not None:
                            try:
                                months_simple = float(str(time_to_goal)) * 12.0
                                months_int_simple = int(months_simple)
                                if months_int_simple > 0:
                                    monthly_contribution_required = (target_amount - goal.current_amount) / months_int_simple
                                else:
                                    monthly_contribution_required = Decimal('0')
                            except (ValueError, TypeError, ZeroDivisionError):
                                monthly_contribution_required = Decimal('0')
                        else:
                            monthly_contribution_required = Decimal('0')
                else:
                    # If no time or no return assumption, simple division
                    if time_to_goal > 0:
                        try:
                            months_float = float(str(time_to_goal)) * 12.0
                            months_int = int(months_float)
                            if months_int > 0:
                                monthly_contribution_required = (target_amount - goal.current_amount) / months_int
                            else:
                                monthly_contribution_required = Decimal('0')
                        except (ValueError, TypeError, ZeroDivisionError):
                            monthly_contribution_required = Decimal('0')
                    else:
                        monthly_contribution_required = Decimal('0')

                # Ensure not negative
                if monthly_contribution_required < 0:
                    monthly_contribution_required = Decimal('0')

                # Current monthly contribution from goal
                monthly_contribution_current = goal.monthly_contribution

                # Calculate progress percentage
                if goal.target_amount > 0:
                    progress_percentage = (goal.current_amount / goal.target_amount) * 100
                else:
                    progress_percentage = Decimal('0')

                # Determine if on track
                on_track = monthly_contribution_current >= monthly_contribution_required

                goal_info = {
                    'goal_id': str(goal.goal_id),
                    'goal_name': goal.goal_name,
                    'goal_type': goal.goal_type,
                    'target_amount': float(goal.target_amount),
                    'current_amount': float(goal.current_amount),
                    'target_date': goal.target_date.isoformat() if goal.target_date else None,
                    'time_to_goal_years': round(time_to_goal, 1),
                    'expected_return': float(goal.expected_return) if goal.expected_return else None,
                    'inflation_adjusted': goal.inflation_adjusted,
                    'priority': goal.priority,
                    'monthly_contribution_required': float(monthly_contribution_required),
                    'monthly_contribution_current': float(monthly_contribution_current),
                    'monthly_contribution_gap': float(monthly_contribution_required - monthly_contribution_current),
                    'progress_percentage': float(progress_percentage),
                    'on_track': on_track
                }

                goals_analysis.append(goal_info)
                total_monthly_contribution_required += monthly_contribution_required
                total_monthly_contribution_current += monthly_contribution_current

                # Group by priority
                if goal.priority in goals_by_priority:
                    goals_by_priority[goal.priority].append(goal_info)

            # --- Financial Context ---
            # We don't have income/expense tools imported directly, but we can estimate
            # For now, we'll note that we need income data to assess funding capacity
            financial_context = {
                'note': 'To assess goal funding capacity, income and expense data would be required.'
            }

            # --- Recommendations ---
            recommendations = []

            # Check if total required contributions exceed a reasonable threshold
            # We would need income data to do this properly, so we'll skip for now
            # Instead, we'll focus on goal-specific recommendations

            for goal_info in goals_analysis:
                if not goal_info['on_track'] and goal_info['monthly_contribution_gap'] > 0:
                    recommendations.append({
                        'type': 'funding_gap',
                        'goal_name': goal_info['goal_name'],
                        'priority': 'high' if goal_info['priority'] == 'high' else 'medium',
                        'suggestion': f"Increase monthly contribution for '{goal_info['goal_name']}' by ₹{goal_info['monthly_contribution_gap']:,.2f} to stay on track",
                        'current_contribution': goal_info['monthly_contribution_current'],
                        'required_contribution': goal_info['monthly_contribution_required'],
                        'gap': goal_info['monthly_contribution_gap']
                    })

            # Prioritization recommendations
            # Check if there are high priority goals that are not on track
            high_priority_off_track = [g for g in goals_analysis if g['priority'] == 'high' and not g['on_track']]
            if high_priority_off_track:
                recommendations.append({
                    'type': 'prioritization',
                    'priority': 'high',
                    'suggestion': 'Focus on funding high priority goals first before lower priority ones',
                    'off_track_goals': [g['goal_name'] for g in high_priority_off_track]
                })

            # Suggest goal consolidation if too many goals
            if len(goals) > 5:
                recommendations.append({
                    'type': 'consolidation',
                    'priority': 'low',
                    'suggestion': 'Consider consolidating similar goals to simplify tracking',
                    'goal_count': len(goals)
                })

            return {
                "goals_analysis": {
                    "total_goals": len(goals),
                    "goals_by_priority": {
                        "high": len(goals_by_priority['high']),
                        "medium": len(goals_by_priority['medium']),
                        "low": len(goals_by_priority['low'])
                    },
                    "total_monthly_contribution_required": float(total_monthly_contribution_required),
                    "total_monthly_contribution_current": float(total_monthly_contribution_current),
                    "total_monthly_contribution_gap": float(total_monthly_contribution_required - total_monthly_contribution_current),
                    "goals": goals_analysis
                },
                "financial_context": financial_context,
                "recommendations": recommendations,
                "calculation_details": {
                    "user_profile": {
                        "age": current_age,
                        "employment_status": user.employment_status,
                        "primary_occupation": user.primary_occupation
                    },
                    "assumptions": {
                        "return_rates": "Individual goal expected return rates used",
                        "inflation_adjustment": "Applied when goal.inflation_adjusted is True",
                        "currency": "INR",
                        "date": "2026-08-29",
                        "note": "This is a simplified goal planning analysis. Actual financial planning should consider income, expenses, taxes, and changing circumstances."
                    }
                },
                "calculation_id": f"calc-goal-{user_id_str}-{int(__import__('time').time())}",
                "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z"
            }
        finally:
            db.close()