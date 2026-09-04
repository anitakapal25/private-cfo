"""Pure Decimal financial foundation calculations."""

from decimal import Decimal, ROUND_HALF_UP

VERSION = "financial-foundation-v2"
MONEY = Decimal("0.01")


def money(value: Decimal) -> dict[str, str]:
    return {"amount": str(value.quantize(MONEY, rounding=ROUND_HALF_UP)), "currency": "INR"}


def calculate_net_worth(assets: Decimal, liabilities: Decimal) -> dict:
    _nonnegative(assets, liabilities)
    return {"total_assets": money(assets), "total_liabilities": money(liabilities), "net_worth": money(assets-liabilities)}


def calculate_cash_flow(income: Decimal, expenses: Decimal) -> dict:
    _nonnegative(income, expenses)
    surplus = income - expenses
    rate = surplus / income if income else None
    return {"monthly_income": money(income), "monthly_expenses": money(expenses), "monthly_surplus": money(surplus), "savings_rate": str(rate.quantize(Decimal("0.0001"))) if rate is not None else None}


def calculate_monthly_money_left(
    income: Decimal, expenses: Decimal, debt_payments: Decimal,
) -> dict:
    """Return money remaining after confirmed same-month outflows."""
    _nonnegative(income, expenses, debt_payments)
    return {
        "monthly_income": money(income),
        "monthly_expenses": money(expenses),
        "monthly_debt_payments": money(debt_payments),
        "money_left": money(income - expenses - debt_payments),
    }


def calculate_emergency_fund_coverage(liquid_assets: Decimal, monthly_essential_expenses: Decimal) -> dict:
    _nonnegative(liquid_assets, monthly_essential_expenses)
    months = liquid_assets / monthly_essential_expenses if monthly_essential_expenses else None
    return {"liquid_assets": money(liquid_assets), "monthly_essential_expenses": money(monthly_essential_expenses), "coverage_months": str(months.quantize(Decimal("0.01"))) if months is not None else None}


def calculate_debt_metrics(income: Decimal, debt_payments: Decimal, outstanding: Decimal) -> dict:
    _nonnegative(income, debt_payments, outstanding)
    ratio = debt_payments / income if income else None
    return {"monthly_income": money(income), "monthly_debt_payments": money(debt_payments), "debt_outstanding": money(outstanding), "debt_to_income_ratio": str(ratio.quantize(Decimal("0.0001"))) if ratio is not None else None}


def calculate_goal_projection(
    current_amount: Decimal, target_amount: Decimal, monthly_contribution: Decimal,
    months: int, annual_return_rate: Decimal,
) -> dict:
    _nonnegative(current_amount, target_amount, monthly_contribution)
    if target_amount <= 0 or not 1 <= months <= 1200:
        raise ValueError("Goal target and horizon must be positive")
    if not Decimal("-0.50") <= annual_return_rate <= Decimal("0.50"):
        raise ValueError("annual_return_rate is outside the supported range")
    monthly_rate = annual_return_rate / Decimal("12")
    if monthly_rate == 0:
        projected = current_amount + monthly_contribution * months
    else:
        factor = (Decimal("1") + monthly_rate) ** months
        projected = current_amount * factor + monthly_contribution * (factor - Decimal("1")) / monthly_rate
    gap = target_amount - projected
    return {
        "projected_amount": money(projected), "target_amount": money(target_amount),
        "goal_gap": money(gap), "status": "on_track" if gap <= 0 else "shortfall",
        "months": months, "monthly_return_rate": str(monthly_rate.quantize(Decimal("0.000001"))),
    }


def _nonnegative(*values: Decimal) -> None:
    if any(value < 0 for value in values):
        raise ValueError("Financial inputs cannot be negative")
