"""Deterministic Phase 2 planning metrics with no embedded market assumptions."""

from decimal import Decimal, ROUND_HALF_UP

PLANNING_VERSION = "enhanced-planning-v1"
MONEY = Decimal("0.01")


def money(value: Decimal) -> dict[str, str]:
    return {"amount": str(value.quantize(MONEY, rounding=ROUND_HALF_UP)), "currency": "INR"}


def calculate_debt_metrics(
    monthly_gross_income: Decimal,
    liabilities: list[dict[str, Decimal | str]],
) -> dict:
    if monthly_gross_income < 0:
        raise ValueError("monthly_gross_income cannot be negative")
    total_outstanding = sum(
        (Decimal(str(item["principal_outstanding"])) for item in liabilities), Decimal("0")
    )
    monthly_emi = sum((Decimal(str(item["emi_amount"])) for item in liabilities), Decimal("0"))
    if total_outstanding < 0 or monthly_emi < 0:
        raise ValueError("liability values cannot be negative")
    ratio = monthly_emi / monthly_gross_income if monthly_gross_income > 0 else None
    return {
        "total_outstanding": money(total_outstanding),
        "monthly_emi": money(monthly_emi),
        "debt_to_income_ratio": (
            str(ratio.quantize(Decimal("0.0001"))) if ratio is not None else None
        ),
        "liability_count": len(liabilities),
    }


def forecast_flat_cash_flow(
    monthly_income: Decimal, monthly_expenses: Decimal, months: int = 12
) -> dict:
    if not 1 <= months <= 24:
        raise ValueError("months must be between 1 and 24")
    if monthly_income < 0 or monthly_expenses < 0:
        raise ValueError("income and expenses cannot be negative")
    monthly_surplus = monthly_income - monthly_expenses
    return {
        "months": [
            {
                "month_number": month,
                "income": money(monthly_income),
                "expenses": money(monthly_expenses),
                "surplus": money(monthly_surplus),
                "cumulative_surplus": money(monthly_surplus * month),
            }
            for month in range(1, months + 1)
        ],
        "assumption": "Active recurring amounts remain unchanged; one-time items are excluded",
    }


def calculate_goal_progress(current_amount: Decimal, target_amount: Decimal) -> dict:
    if target_amount <= 0 or current_amount < 0:
        raise ValueError("goal amounts must be non-negative and target must be positive")
    progress = current_amount / target_amount
    return {
        "current_amount": money(current_amount),
        "target_amount": money(target_amount),
        "remaining_amount": money(max(target_amount - current_amount, Decimal("0"))),
        "progress_percent": str((progress * Decimal("100")).quantize(Decimal("0.01"))),
        "status": "funded" if current_amount >= target_amount else "in_progress",
    }


def calculate_coverage_gap(current_coverage: Decimal, user_selected_target: Decimal) -> dict:
    if current_coverage < 0 or user_selected_target < 0:
        raise ValueError("coverage values cannot be negative")
    return {
        "current_coverage": money(current_coverage),
        "user_selected_target": money(user_selected_target),
        "coverage_gap": money(max(user_selected_target - current_coverage, Decimal("0"))),
        "target_source": "explicit_user_selected_scenario",
    }
