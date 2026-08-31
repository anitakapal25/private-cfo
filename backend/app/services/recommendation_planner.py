"""Deterministic, product-neutral planning action impact and ranking."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

PLANNER_VERSION = "planning-actions-v1"
ALLOWED_ACTIONS = {
    "reduce_monthly_expenses": {"risk": Decimal("1"), "liquidity": Decimal("1")},
    "increase_monthly_savings": {"risk": Decimal("1"), "liquidity": Decimal("2")},
    "increase_debt_payment": {"risk": Decimal("2"), "liquidity": Decimal("3")},
}


@dataclass(frozen=True)
class CandidateAction:
    action_type: str
    monthly_amount: Decimal
    feasibility: Decimal
    user_priority: Decimal


def calculate_action_impact(action: CandidateAction) -> dict:
    if action.action_type not in ALLOWED_ACTIONS:
        raise ValueError("Unsupported or product-specific planning action")
    if action.monthly_amount <= 0:
        raise ValueError("Action amount must be positive")
    if not Decimal("0") <= action.feasibility <= Decimal("1"):
        raise ValueError("Feasibility must be between zero and one")
    if not Decimal("0") <= action.user_priority <= Decimal("1"):
        raise ValueError("User priority must be between zero and one")
    annual = action.monthly_amount * Decimal("12")
    if action.action_type == "reduce_monthly_expenses":
        effect = "increases monthly surplus if the reduction is achieved"
    elif action.action_type == "increase_monthly_savings":
        effect = "increases planned annual contributions"
    else:
        effect = "increases debt payments; payoff timing requires verified loan terms"
    return {
        "monthly_cash_flow_change": {"amount": str(action.monthly_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)), "currency": "INR"},
        "annualized_change": {"amount": str(annual.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)), "currency": "INR"},
        "effect": effect,
        "limitations": ["This is a conditional planning scenario", "No product or guaranteed outcome is implied"],
    }


def rank_actions(actions: list[CandidateAction]) -> list[dict]:
    ranked = []
    for action in actions:
        impact = calculate_action_impact(action)
        policy = ALLOWED_ACTIONS[action.action_type]
        score = (
            action.feasibility * Decimal("0.45")
            + action.user_priority * Decimal("0.45")
            + (Decimal("1") / policy["risk"]) * Decimal("0.05")
            + (Decimal("1") / policy["liquidity"]) * Decimal("0.05")
        ).quantize(Decimal("0.0001"))
        ranked.append({
            "action_type": action.action_type,
            "monthly_amount": str(action.monthly_amount.quantize(Decimal("0.01"))),
            "score": str(score), "impact": impact,
            "rationale": "Ranked from user priority, feasibility, implementation risk, and liquidity impact.",
            "planner_version": PLANNER_VERSION,
        })
    return sorted(ranked, key=lambda item: (Decimal(item["score"]), Decimal(item["monthly_amount"])), reverse=True)
