"""Pure Decimal financial-freedom projection used by agent tools.

All inputs are explicit user-confirmed scenario values. This module contains no
regulatory, tax, product-selection, or model-generated assumptions.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

MONEY_QUANTUM = Decimal("0.01")
RATE_QUANTUM = Decimal("0.000001")
PROJECTION_VERSION = "freedom-projection-v1"


@dataclass(frozen=True)
class FreedomProjectionInputs:
    current_age: int
    target_age: int
    current_monthly_lifestyle_expenses: Decimal
    current_investable_corpus: Decimal
    monthly_contribution: Decimal
    annual_inflation_rate: Decimal
    annual_return_rate: Decimal
    withdrawal_rate: Decimal

    def validate(self) -> None:
        if not 18 <= self.current_age < 100:
            raise ValueError("current_age must be between 18 and 99")
        if not self.current_age < self.target_age <= 100:
            raise ValueError("target_age must be greater than current_age and at most 100")
        if self.current_monthly_lifestyle_expenses <= 0:
            raise ValueError("current_monthly_lifestyle_expenses must be positive")
        if self.current_investable_corpus < 0 or self.monthly_contribution < 0:
            raise ValueError("corpus and contribution cannot be negative")
        if not Decimal("0") <= self.annual_inflation_rate <= Decimal("0.20"):
            raise ValueError("annual_inflation_rate must be between 0 and 0.20")
        if not Decimal("-0.50") <= self.annual_return_rate <= Decimal("0.50"):
            raise ValueError("annual_return_rate must be between -0.50 and 0.50")
        if not Decimal("0.01") <= self.withdrawal_rate <= Decimal("0.10"):
            raise ValueError("withdrawal_rate must be between 0.01 and 0.10")


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP))


def calculate_freedom_projection(inputs: FreedomProjectionInputs) -> dict:
    inputs.validate()
    years = inputs.target_age - inputs.current_age
    months = years * 12
    target_monthly_expenses = inputs.current_monthly_lifestyle_expenses * (
        Decimal("1") + inputs.annual_inflation_rate
    ) ** years
    required_corpus = target_monthly_expenses * Decimal("12") / inputs.withdrawal_rate

    monthly_return = inputs.annual_return_rate / Decimal("12")
    if monthly_return == 0:
        projected_corpus = inputs.current_investable_corpus + inputs.monthly_contribution * months
    else:
        growth_factor = (Decimal("1") + monthly_return) ** months
        projected_corpus = (
            inputs.current_investable_corpus * growth_factor
            + inputs.monthly_contribution * (growth_factor - Decimal("1")) / monthly_return
        )
    gap = required_corpus - projected_corpus
    return {
        "target_age": inputs.target_age,
        "years_to_target": years,
        "target_monthly_expenses": {"amount": _money(target_monthly_expenses), "currency": "INR"},
        "required_corpus": {"amount": _money(required_corpus), "currency": "INR"},
        "projected_corpus": {"amount": _money(projected_corpus), "currency": "INR"},
        "freedom_gap": {"amount": _money(gap), "currency": "INR"},
        "scenario_status": "on_track" if gap <= 0 else "shortfall",
        "monthly_return_rate": str(monthly_return.quantize(RATE_QUANTUM)),
    }
