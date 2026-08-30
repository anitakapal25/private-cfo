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
        name="calculate_net_worth", version="financial-foundation-v1",
        allowed_intents=frozenset({"net_worth", "freedom_plan"}),
    ),
    "calculate_monthly_surplus": ToolSpec(
        name="calculate_monthly_surplus", version="financial-foundation-v1",
        allowed_intents=frozenset({"cash_flow", "freedom_plan"}),
    ),
}


def authorize_tool(tool_name: str, intent: str, *, confirmed: bool = False) -> ToolSpec:
    spec = TOOL_REGISTRY.get(tool_name)
    if spec is None or intent not in spec.allowed_intents:
        raise ToolAuthorizationError("Tool is not authorized for this intent")
    if spec.requires_confirmation and not confirmed:
        raise ToolAuthorizationError("Tool requires explicit user confirmation")
    return spec
