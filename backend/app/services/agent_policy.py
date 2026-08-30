"""Least-privilege tool catalogue and policy for agent orchestration."""

from dataclasses import dataclass


class ToolAuthorizationError(PermissionError):
    pass


@dataclass(frozen=True)
class ToolSpec:
    name: str
    version: str
    allowed_intents: frozenset[str]
    mutates_data: bool = False
    requires_confirmation: bool = False
    model_callable: bool = True


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "calculate_net_worth": ToolSpec(
        name="calculate_net_worth", version="financial-foundation-v2",
        allowed_intents=frozenset({"net_worth", "freedom_plan"}),
    ),
    "calculate_monthly_surplus": ToolSpec(
        name="calculate_monthly_surplus", version="financial-foundation-v2",
        allowed_intents=frozenset({"cash_flow", "freedom_plan"}),
    ),
    "calculate_financial_freedom_projection": ToolSpec(
        name="calculate_financial_freedom_projection", version="freedom-projection-v1",
        allowed_intents=frozenset({"freedom_plan"}),
    ),
    "calculate_debt_metrics": ToolSpec(
        name="calculate_debt_metrics", version="financial-foundation-v2",
        allowed_intents=frozenset({"debt_analysis"}),
    ),
    "forecast_cash_flow": ToolSpec(
        name="forecast_cash_flow", version="enhanced-planning-v1",
        allowed_intents=frozenset({"cash_flow_forecast"}),
    ),
    "get_goal_progress": ToolSpec(
        name="get_goal_progress", version="enhanced-planning-v1",
        allowed_intents=frozenset({"goal_progress"}),
    ),
    "calculate_coverage_gap": ToolSpec(
        name="calculate_coverage_gap", version="enhanced-planning-v1",
        allowed_intents=frozenset({"insurance_gap"}),
    ),
    "calculate_emergency_fund_coverage": ToolSpec(
        name="calculate_emergency_fund_coverage", version="financial-foundation-v2",
        allowed_intents=frozenset({"emergency_fund"}),
    ),
}


def authorize_tool(tool_name: str, intent: str, *, confirmed: bool = False) -> ToolSpec:
    spec = TOOL_REGISTRY.get(tool_name)
    if spec is None or intent not in spec.allowed_intents:
        raise ToolAuthorizationError("Tool is not authorized for this intent")
    if spec.requires_confirmation and not confirmed:
        raise ToolAuthorizationError("Tool requires explicit user confirmation")
    return spec
