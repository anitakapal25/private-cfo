"""Deterministic, auditable orchestration for the financial-freedom agent."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import uuid

from sqlalchemy.orm import Session

from app.guardrails.regulatory_language import Decision, evaluate_financial_request
from app.models.agent import AgentRun, AuditEvent, CalculationRecord, ConversationMessage, ToolCall
from app.models.financial import Asset, Expense, IncomeSource, Liability
from app.services.agent_policy import authorize_tool

CALCULATION_VERSION = "financial-foundation-v1"
AGENT_POLICY_VERSION = "planning-policy-v1"


class Intent(str, Enum):
    NET_WORTH = "net_worth"
    CASH_FLOW = "cash_flow"
    FREEDOM_PLAN = "freedom_plan"
    GENERAL_EDUCATION = "general_education"


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

    def answer(self, message: str) -> AgentAnswer:
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
            return self._freedom_plan()
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
        assets = self.db.query(Asset).filter(Asset.user_id == self.user_id, Asset.is_active.is_(True)).all()
        liabilities = self.db.query(Liability).filter(Liability.user_id == self.user_id, Liability.is_active.is_(True)).all()
        if not assets and not liabilities:
            return self._missing(Intent.NET_WORTH, ["assets", "liabilities"])
        total_assets = sum((Decimal(item.current_value) for item in assets), Decimal("0"))
        total_liabilities = sum((Decimal(item.principal_outstanding) for item in liabilities), Decimal("0"))
        result = {
            "net_worth": _money(total_assets - total_liabilities),
            "total_assets": _money(total_assets),
            "total_liabilities": _money(total_liabilities),
        }
        record = self._record_calculation("net_worth", result, ["active assets", "active liabilities"])
        return AgentAnswer(
            intent=Intent.NET_WORTH,
            narrative="Your verified records produce the net-worth calculation shown below.",
            blocks=[self._calculation_block(record, result)],
            tool_name="calculate_net_worth",
            calculation_id=str(record.calculation_id),
        )

    def _cash_flow(self) -> AgentAnswer:
        authorize_tool("calculate_monthly_surplus", Intent.CASH_FLOW.value)
        incomes = self.db.query(IncomeSource).filter(IncomeSource.user_id == self.user_id, IncomeSource.is_active.is_(True)).all()
        expenses = self.db.query(Expense).filter(Expense.user_id == self.user_id, Expense.is_active.is_(True)).all()
        if not incomes or not expenses:
            missing = [name for name, rows in (("income", incomes), ("expenses", expenses)) if not rows]
            return self._missing(Intent.CASH_FLOW, missing)
        monthly_income = sum((_monthly(Decimal(item.amount), item.frequency) for item in incomes), Decimal("0"))
        monthly_expenses = sum((_monthly(Decimal(item.amount), item.frequency) for item in expenses), Decimal("0"))
        surplus = monthly_income - monthly_expenses
        rate = (surplus / monthly_income * Decimal("100")) if monthly_income > 0 else Decimal("0")
        result = {
            "monthly_income": _money(monthly_income),
            "monthly_expenses": _money(monthly_expenses),
            "monthly_surplus": _money(surplus),
            "savings_rate_percent": str(rate.quantize(Decimal("0.01"))),
        }
        record = self._record_calculation("cash_flow", result, ["active recurring income", "active recurring expenses"])
        return AgentAnswer(
            intent=Intent.CASH_FLOW,
            narrative="Here is your monthly cash-flow position based only on active verified records.",
            blocks=[self._calculation_block(record, result)],
            tool_name="calculate_monthly_surplus",
            calculation_id=str(record.calculation_id),
        )

    def _freedom_plan(self) -> AgentAnswer:
        cash_flow = self._cash_flow()
        net_worth = self._net_worth()
        missing = []
        if cash_flow.tool_name is None:
            missing.extend(["income", "expenses"])
        if net_worth.tool_name is None:
            missing.extend(["assets", "liabilities"])
        # A target and approved assumptions are mandatory; never synthesize them.
        missing.extend(["target lifestyle expenses", "target date", "user-selected return and inflation assumptions"])
        return AgentAnswer(
            intent=Intent.FREEDOM_PLAN,
            narrative=(
                "I can build your financial-freedom baseline after the missing inputs below are confirmed. "
                "I will show scenario ranges rather than promise a date."
            ),
            blocks=[{"type": "missing_data", "fields": sorted(set(missing))}],
        )

    def _missing(self, intent: Intent, fields: list[str]) -> AgentAnswer:
        return AgentAnswer(
            intent=intent,
            narrative="I do not have enough verified information to calculate this without inventing financial facts.",
            blocks=[{"type": "missing_data", "fields": fields}],
        )

    def _record_calculation(self, calculation_type: str, result: dict, sources: list[str]) -> CalculationRecord:
        record = CalculationRecord(
            calculation_id=uuid.uuid4(),
            user_id=self.user_id,
            calculation_type=calculation_type,
            calculation_version=CALCULATION_VERSION,
            inputs={"sources": sources},
            assumptions={"currency": "INR", "frequency_normalization": "monthly"},
            result=result,
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "limitations": ["Only active stored records are included", "This is planning information, not a guaranteed outcome"],
        }


def audit_agent_run(db: Session, user_id: uuid.UUID, assistant_message: ConversationMessage, answer: AgentAnswer) -> AgentRun:
    run = AgentRun(
        run_id=uuid.uuid4(), user_id=user_id, message_id=assistant_message.message_id,
        intent=answer.intent.value, policy_decision=answer.policy_decision, model_used=False,
    )
    db.add(run)
    db.flush()
    if answer.tool_name:
        db.add(ToolCall(
            run_id=run.run_id,
            tool_name=answer.tool_name,
            tool_version=CALCULATION_VERSION,
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
