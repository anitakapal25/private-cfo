"""Executable read-only tool registry. Authentication is supplied only by the server."""
from dataclasses import dataclass
import hashlib
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.agent_policy import authorize_tool, ToolAuthorizationError
from app.services.conversation_contracts import ToolRequest, ToolEvidence
from app.services.finance_knowledge import lookup_topic
from app.guardrails.financial_output import validate_financial_output

@dataclass(frozen=True)
class Handler:
    intent: str
    method: str

HANDLERS = {
    "calculate_net_worth": Handler("net_worth", "_net_worth"),
    "calculate_monthly_surplus": Handler("cash_flow", "_cash_flow"),
    "calculate_debt_metrics": Handler("debt_analysis", "_debt_analysis"),
    "calculate_emergency_fund_coverage": Handler("emergency_fund", "_emergency_fund"),
    "get_goal_progress": Handler("goal_progress", "_goal_progress"),
    "forecast_cash_flow": Handler("cash_flow_forecast", "_cash_flow_forecast"),
    "calculate_coverage_gap": Handler("insurance_gap", "_insurance_gap"),
    "calculate_financial_freedom_projection": Handler("freedom_plan", "_freedom_plan"),
}

class ConversationToolExecutor:
    def __init__(self, db, user_id, *, freedom_inputs=None, assumption_metadata=None, coverage_target=None):
        self.db, self.user_id = db, user_id
        self.freedom_inputs, self.assumption_metadata, self.coverage_target = freedom_inputs, assumption_metadata, coverage_target
        self.calls = []
        self.failures = []

    def execute(self, request: ToolRequest, *, public_only=False) -> ToolEvidence:
        request = ToolRequest.model_validate(request)
        if public_only and request.name != "lookup_finance_topic":
            raise ToolAuthorizationError("Private tools unavailable for this request")
        if request.name == "lookup_finance_topic":
            if request.arguments.topic is None or request.arguments.period_start is not None:
                raise ValueError("Public lookup requires only a topic")
            block = lookup_topic(request.arguments.topic)
            blocks, narrative = [block], block["content"]
        else:
            if request.arguments.topic is not None:
                raise ValueError("Calculation arguments cannot contain a public topic")
            handler = HANDLERS[request.name]
            spec = authorize_tool(request.name, handler.intent)
            if spec.mutates_data or not spec.model_callable:
                raise ToolAuthorizationError("Tool is not available to the conversation planner")
            agent = AgentOrchestrator(self.db, self.user_id, request.arguments.period_start)
            method = getattr(agent, handler.method)
            if request.name == "calculate_coverage_gap":
                answer = method(self.coverage_target)
            elif request.name == "calculate_financial_freedom_projection":
                if request.arguments.period_start is not None:
                    raise ValueError("Confirmed freedom scenarios do not accept historical periods")
                answer = method(self.freedom_inputs, self.assumption_metadata)
            else:
                answer = method()
            blocks, narrative = answer.blocks, answer.narrative
            for block in blocks:
                if block["type"] == "calculation":
                    validate_financial_output(block)
                    block["period_start"] = request.arguments.period_start.isoformat() if request.arguments.period_start else next((p.get("period_start") for p in block.get("provenance", []) if p.get("period_kind") == "monthly"), None)
        reference = "e_" + hashlib.sha256(request.model_dump_json().encode()).hexdigest()[:20]
        status = "missing" if any(b["type"] == "missing_data" for b in blocks) else "unavailable" if any(b["type"] in {"warning", "unsupported_coverage"} for b in blocks) else "complete"
        result = ToolEvidence(reference=reference, tool_name=request.name, status=status, narrative=narrative, blocks=blocks)
        self.calls.append((request, result))
        return result
