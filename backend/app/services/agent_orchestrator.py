"""Deterministic, auditable orchestration for the financial-freedom agent."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import uuid

from sqlalchemy.orm import Session

from app.guardrails.agent_input import evaluate_agent_input
from app.guardrails.regulatory_language import Decision, evaluate_financial_request
from app.models.agent import AgentRun, AuditEvent, CalculationRecord, ConversationMessage, ToolCall
from app.services.agent_policy import authorize_tool
from app.services.financial_context import FinancialContextService
from app.services.financial_engine import VERSION as FOUNDATION_VERSION
from app.services.financial_engine import calculate_cash_flow, calculate_debt_metrics as calculate_verified_debt_metrics, calculate_emergency_fund_coverage, calculate_net_worth
from app.services.financial_freedom import (
    PROJECTION_VERSION,
    FreedomProjectionInputs,
    calculate_freedom_projection,
)
from app.services.planning_metrics import (
    PLANNING_VERSION,
    calculate_coverage_gap,
    calculate_debt_metrics,
    calculate_goal_progress,
    forecast_flat_cash_flow,
)

CALCULATION_VERSION = FOUNDATION_VERSION
AGENT_POLICY_VERSION = "planning-policy-v1"


class Intent(str, Enum):
    NET_WORTH = "net_worth"
    CASH_FLOW = "cash_flow"
    FREEDOM_PLAN = "freedom_plan"
    GENERAL_EDUCATION = "general_education"
    DEBT_ANALYSIS = "debt_analysis"
    CASH_FLOW_FORECAST = "cash_flow_forecast"
    GOAL_PROGRESS = "goal_progress"
    INSURANCE_GAP = "insurance_gap"
    EMERGENCY_FUND = "emergency_fund"
    TAX = "tax"
    DOCUMENT = "document"


@dataclass(frozen=True)
class AgentAnswer:
    intent: Intent
    narrative: str
    blocks: list[dict]
    tool_name: str | None = None
    calculation_id: str | None = None
    policy_decision: str = "allow"


def classify_intent(message: str) -> Intent:
    normalized = " ".join(message.lower().split())
    if any(term in normalized for term in ("emergency fund", "emergency reserve")):
        return Intent.EMERGENCY_FUND
    if any(term in normalized for term in ("cash flow forecast", "forecast cash", "next 12 months")):
        return Intent.CASH_FLOW_FORECAST
    if any(term in normalized for term in ("debt", "loan", "emi")):
        return Intent.DEBT_ANALYSIS
    if any(term in normalized for term in ("goal progress", "my goals", "goal status")):
        return Intent.GOAL_PROGRESS
    if any(term in normalized for term in ("coverage gap", "current insurance", "insurance summary")):
        return Intent.INSURANCE_GAP
    if any(term in normalized for term in ("tax", "deduction", "tax regime")):
        return Intent.TAX
    if any(term in normalized for term in ("document", "form 16", "statement upload")):
        return Intent.DOCUMENT
    if any(term in normalized for term in ("net worth", "assets", "liabilities")):
        return Intent.NET_WORTH
    if any(term in normalized for term in ("cash flow", "surplus", "savings rate", "expenses")):
        return Intent.CASH_FLOW
    if any(term in normalized for term in ("financial freedom", "retire early", "freedom plan", "achieve freedom")):
        return Intent.FREEDOM_PLAN
    return Intent.GENERAL_EDUCATION


def _monthly(value: Decimal, frequency: str) -> Decimal:
    factors = {
        "monthly": Decimal("1"),
        "quarterly": Decimal("0.333333333333"),
        "annually": Decimal("0.083333333333"),
        "one-time": Decimal("0"),
    }
    return value * factors.get(frequency, Decimal("0"))


def _money(value: Decimal) -> dict[str, str]:
    return {"amount": str(value.quantize(Decimal("0.01"))), "currency": "INR"}


class AgentOrchestrator:
    """Routes user intent to deterministic data/calculation tools only."""

    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    def answer(
        self, message: str, freedom_inputs: FreedomProjectionInputs | None = None,
        coverage_target: Decimal | None = None,
    ) -> AgentAnswer:
        input_decision = evaluate_agent_input(message)
        if not input_decision.allowed:
            return AgentAnswer(
                intent=Intent.GENERAL_EDUCATION,
                narrative=(
                    "I cannot follow instructions that attempt to override safety controls, "
                    "expose protected instructions, or access another user's information."
                ),
                blocks=[{"type": "warning", "code": input_decision.reason}],
                policy_decision="block",
            )
        decision = evaluate_financial_request(message)
        if decision.decision is Decision.BLOCK:
            return AgentAnswer(
                intent=Intent.GENERAL_EDUCATION,
                narrative=decision.safe_response or "That request is outside my planning boundary.",
                blocks=[{"type": "warning", "code": decision.reason}],
                policy_decision="block",
            )

        intent = classify_intent(message)
        if intent is Intent.NET_WORTH:
            return self._net_worth()
        if intent is Intent.CASH_FLOW:
            return self._cash_flow()
        if intent is Intent.FREEDOM_PLAN:
            return self._freedom_plan(freedom_inputs)
        if intent is Intent.DEBT_ANALYSIS:
            return self._debt_analysis()
        if intent is Intent.CASH_FLOW_FORECAST:
            return self._cash_flow_forecast()
        if intent is Intent.GOAL_PROGRESS:
            return self._goal_progress()
        if intent is Intent.INSURANCE_GAP:
            return self._insurance_gap(coverage_target)
        if intent is Intent.EMERGENCY_FUND:
            return self._emergency_fund()
        if intent is Intent.TAX:
            return AgentAnswer(
                intent=intent,
                narrative="Current personalized tax calculations are unavailable because the reviewed tax rule catalogue is expired.",
                blocks=[{"type": "warning", "code": "STALE_ASSUMPTION"}],
                policy_decision="block",
            )
        if intent is Intent.DOCUMENT:
            return AgentAnswer(
                intent=intent,
                narrative="Document extraction is disabled until malware scanning and sandboxed processing pass the release gate.",
                blocks=[{"type": "warning", "code": "DOCUMENT_PIPELINE_BLOCKED"}],
                policy_decision="block",
            )
        return AgentAnswer(
            intent=intent,
            narrative=(
                "I can explain financial concepts and personalize planning once the relevant "
                "income, expenses, assets, liabilities, goals, and assumptions are verified. "
                "What outcome would you like to understand?"
            ),
            blocks=[{"type": "missing_data", "fields": ["financial question or planning goal"]}],
        )

    def _net_worth(self) -> AgentAnswer:
        authorize_tool("calculate_net_worth", Intent.NET_WORTH.value)
        context = FinancialContextService(self.db, self.user_id).assemble("net_worth")
        if context.missing:
            return self._missing(Intent.NET_WORTH, list(context.missing))
        result = calculate_net_worth(Decimal(context.facts["total_assets"].value), Decimal(context.facts["total_liabilities"].value))
        record = self._record_calculation("net_worth", result, context=context)
        return AgentAnswer(
            intent=Intent.NET_WORTH,
            narrative="Your verified records produce the net-worth calculation shown below.",
            blocks=[self._calculation_block(record, result)],
            tool_name="calculate_net_worth",
            calculation_id=str(record.calculation_id),
        )

    def _cash_flow(self) -> AgentAnswer:
        authorize_tool("calculate_monthly_surplus", Intent.CASH_FLOW.value)
        context = FinancialContextService(self.db, self.user_id).assemble("cash_flow")
        if context.missing:
            return self._missing(Intent.CASH_FLOW, list(context.missing))
        result = calculate_cash_flow(Decimal(context.facts["monthly_income"].value), Decimal(context.facts["monthly_expenses"].value))
        record = self._record_calculation("cash_flow", result, context=context)
        return AgentAnswer(
            intent=Intent.CASH_FLOW,
            narrative="Here is your monthly cash-flow position based only on active verified records.",
            blocks=[self._calculation_block(record, result)],
            tool_name="calculate_monthly_surplus",
            calculation_id=str(record.calculation_id),
        )

    def _freedom_plan(
        self, freedom_inputs: FreedomProjectionInputs | None
    ) -> AgentAnswer:
        if freedom_inputs is None:
            return AgentAnswer(
                intent=Intent.FREEDOM_PLAN,
                narrative=(
                    "I can build your financial-freedom baseline after the scenario inputs below "
                    "are explicitly confirmed. I will not infer rates or balances from chat text."
                ),
                blocks=[{"type": "missing_data", "fields": [
                    "current age", "target age", "current monthly lifestyle expenses",
                    "current investable corpus", "monthly contribution",
                    "user-selected inflation rate", "user-selected return rate",
                    "user-selected withdrawal rate",
                ]}],
            )
        authorize_tool("calculate_financial_freedom_projection", Intent.FREEDOM_PLAN.value)
        result = calculate_freedom_projection(freedom_inputs)
        input_record = {
            "current_age": freedom_inputs.current_age,
            "target_age": freedom_inputs.target_age,
            "current_monthly_lifestyle_expenses": str(freedom_inputs.current_monthly_lifestyle_expenses),
            "current_investable_corpus": str(freedom_inputs.current_investable_corpus),
            "monthly_contribution": str(freedom_inputs.monthly_contribution),
        }
        assumptions = {
            "annual_inflation_rate": str(freedom_inputs.annual_inflation_rate),
            "annual_return_rate": str(freedom_inputs.annual_return_rate),
            "withdrawal_rate": str(freedom_inputs.withdrawal_rate),
            "contribution_timing": "end_of_month",
            "monthly_rate_method": "nominal_annual_rate_divided_by_12",
            "source": "explicit_user_confirmed_scenario",
        }
        record = self._record_calculation(
            "financial_freedom_projection", result,
            ["explicit user-confirmed scenario inputs"],
            version=PROJECTION_VERSION, inputs=input_record, assumptions=assumptions,
        )
        return AgentAnswer(
            intent=Intent.FREEDOM_PLAN,
            narrative=(
                "This is your deterministic financial-freedom scenario based on the values and "
                "assumptions you explicitly confirmed. It is a planning projection, not a guarantee."
            ),
            blocks=[self._calculation_block(record, result)],
            tool_name="calculate_financial_freedom_projection",
            calculation_id=str(record.calculation_id),
        )

    def _missing(self, intent: Intent, fields: list[str]) -> AgentAnswer:
        return AgentAnswer(
            intent=intent,
            narrative="I do not have enough verified information to calculate this without inventing financial facts.",
            blocks=[{"type": "missing_data", "fields": fields}],
        )

    def _debt_analysis(self) -> AgentAnswer:
        authorize_tool("calculate_debt_metrics", Intent.DEBT_ANALYSIS.value)
        context = FinancialContextService(self.db, self.user_id).assemble("debt")
        if context.missing:
            return self._missing(Intent.DEBT_ANALYSIS, list(context.missing))
        result = calculate_verified_debt_metrics(*(Decimal(context.facts[key].value) for key in ("monthly_income", "monthly_debt_payments", "debt_outstanding")))
        return self._planning_answer(Intent.DEBT_ANALYSIS, "calculate_debt_metrics", "debt_metrics", result, "Here are your debt metrics based only on confirmed facts.", context=context)

    def _cash_flow_forecast(self) -> AgentAnswer:
        authorize_tool("forecast_cash_flow", Intent.CASH_FLOW_FORECAST.value)
        context = FinancialContextService(self.db, self.user_id).assemble("cash_flow")
        if context.missing:
            return self._missing(Intent.CASH_FLOW_FORECAST, list(context.missing))
        result = forecast_flat_cash_flow(Decimal(context.facts["monthly_income"].value), Decimal(context.facts["monthly_expenses"].value))
        return self._planning_answer(Intent.CASH_FLOW_FORECAST, "forecast_cash_flow", "cash_flow_forecast", result, "This 12-month cash-flow scenario holds confirmed monthly amounts constant.", context=context)

    def _goal_progress(self) -> AgentAnswer:
        authorize_tool("get_goal_progress", Intent.GOAL_PROGRESS.value)
        context = FinancialContextService(self.db, self.user_id).assemble("goal")
        if context.missing:
            return self._missing(Intent.GOAL_PROGRESS, list(context.missing))
        result = calculate_goal_progress(Decimal(context.facts["goal_current"].value), Decimal(context.facts["goal_target"].value))
        return self._planning_answer(Intent.GOAL_PROGRESS, "get_goal_progress", "goal_progress", result, "Here is the progress calculated from your confirmed goal facts.", context=context)

    def _insurance_gap(self, coverage_target: Decimal | None) -> AgentAnswer:
        if coverage_target is None:
            return self._missing(Intent.INSURANCE_GAP, ["explicit user-selected coverage target"])
        authorize_tool("calculate_coverage_gap", Intent.INSURANCE_GAP.value)
        context = FinancialContextService(self.db, self.user_id).assemble("insurance")
        if context.missing:
            return self._missing(Intent.INSURANCE_GAP, list(context.missing))
        result = calculate_coverage_gap(Decimal(context.facts["insurance_coverage"].value), coverage_target)
        return self._planning_answer(Intent.INSURANCE_GAP, "calculate_coverage_gap", "insurance_coverage_gap", result, "This compares confirmed coverage with the target you selected; it does not recommend a product or coverage level.", context=context)

    def _emergency_fund(self) -> AgentAnswer:
        authorize_tool("calculate_emergency_fund_coverage", Intent.EMERGENCY_FUND.value)
        context = FinancialContextService(self.db, self.user_id).assemble("emergency_fund")
        if context.missing:
            return self._missing(Intent.EMERGENCY_FUND, list(context.missing))
        result = calculate_emergency_fund_coverage(Decimal(context.facts["liquid_assets"].value), Decimal(context.facts["monthly_expenses"].value))
        return self._planning_answer(Intent.EMERGENCY_FUND, "calculate_emergency_fund_coverage", "emergency_fund_coverage", result, "This is your emergency-reserve coverage based on confirmed liquid assets and monthly expenses.", context=context)

    def _planning_answer(self, intent: Intent, tool_name: str, calculation_type: str, result: dict, narrative: str, *, context=None) -> AgentAnswer:
        record = self._record_calculation(calculation_type, result, version=PLANNING_VERSION, assumptions={"currency": "INR", "source": "verified_financial_facts", "no_product_recommendation": True}, context=context)
        return AgentAnswer(intent=intent, narrative=narrative, blocks=[self._calculation_block(record, result)], tool_name=tool_name, calculation_id=str(record.calculation_id))

    def _record_calculation(
        self, calculation_type: str, result: dict, sources: list[str] | None = None,
        *, version: str = CALCULATION_VERSION, inputs: dict | None = None,
        assumptions: dict | None = None, context=None,
    ) -> CalculationRecord:
        now = datetime.now(timezone.utc)
        provenance = context.provenance if context else []
        limitations = ["Only confirmed facts and explicit scenario inputs are included", "This is planning information, not a guaranteed outcome"]
        record = CalculationRecord(
            calculation_id=uuid.uuid4(),
            user_id=self.user_id,
            calculation_type=calculation_type,
            calculation_version=version,
            inputs=inputs or {"sources": sources or [], "fact_ids": [item["fact_id"] for item in provenance]},
            assumptions=assumptions or {"currency": "INR", "frequency_normalization": "monthly"},
            result=result,
            input_provenance=provenance,
            rule_versions={"calculation": version},
            limitations=limitations,
            as_of=context.as_of if context else now,
        )
        self.db.add(record)
        self.db.flush()
        return record

    @staticmethod
    def _calculation_block(record: CalculationRecord, result: dict) -> dict:
        return {
            "type": "calculation",
            "calculation_id": str(record.calculation_id),
            "version": record.calculation_version,
            "result": result,
            "assumptions": record.assumptions,
            "timestamp": record.as_of.isoformat(),
            "provenance": record.input_provenance,
            "rule_versions": record.rule_versions,
            "limitations": record.limitations,
        }


def audit_agent_run(db: Session, user_id: uuid.UUID, assistant_message: ConversationMessage, answer: AgentAnswer) -> AgentRun:
    run = AgentRun(
        run_id=uuid.uuid4(), user_id=user_id, message_id=assistant_message.message_id,
        intent=answer.intent.value, policy_decision=answer.policy_decision, model_used=False,
    )
    db.add(run)
    db.flush()
    if answer.tool_name:
        tool_spec = authorize_tool(answer.tool_name, answer.intent.value)
        db.add(ToolCall(
            run_id=run.run_id,
            tool_name=answer.tool_name,
            tool_version=tool_spec.version,
            sanitized_input_hash=hashlib.sha256(
                f"{user_id}:{answer.intent.value}:{AGENT_POLICY_VERSION}".encode("utf-8")
            ).hexdigest(),
            outcome="success",
            result_reference=answer.calculation_id,
        ))
    db.add(AuditEvent(
        user_id=user_id,
        event_type="agent_response_created",
        target_type="agent_run",
        target_id=str(run.run_id),
        outcome="success",
        metadata_json={"intent": answer.intent.value, "policy_version": AGENT_POLICY_VERSION},
    ))
    return run
