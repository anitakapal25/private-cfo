"""Typed, authenticated API for the financial-freedom agent."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.auth.manager import get_current_active_user
from app.core.config import Settings, get_db, get_settings
from app.core.model_gateway import MODEL_POLICY_BUNDLE_VERSION, ModelRequest, OpenAIModelGateway
from app.models.agent import ActionCheckIn, ActionPlan, AgentRun, AuditEvent, CalculationRecord, Confirmation, Conversation, ConversationMessage, FinancialFact, ModelConsent, PlannedAction, ProactiveReview
from app.models.user import User
from app.services.agent_orchestrator import AgentOrchestrator, audit_agent_run
from app.services.financial_freedom import FreedomProjectionInputs
from app.services.ecosystem_capabilities import get_ecosystem_capabilities
from app.services.financial_context import ALLOWED_FACT_TYPES, MONTHLY_FACT_TYPES, FinancialContextService
from app.services.financial_engine import calculate_monthly_money_left
from app.services.recommendation_planner import ACTION_TRACKING_VERSION, CandidateAction, calculate_action_progress, calculate_action_target, rank_actions
from app.services.proactive_reviews import persist_reviews
from app.guardrails.data_redaction import redact_sensitive
from app.guardrails.assumption_freshness import StaleAssumptionError, require_current_assumption
from app.guardrails.catalog import FINANCIAL_FREEDOM_ASSUMPTIONS

router = APIRouter()
MEMORY_MONTHLY_SUMMARY_VERSION = "financial-memory-monthly-v1"

CLOUD_ASSISTANCE_CATEGORIES = (
    "agent_intent",
    "verified_financial_facts",
    "deterministic_calculation_evidence",
)
CLOUD_ASSISTANCE_PURPOSE = "Plain-language explanation of deterministic financial evidence"
CLOUD_ASSISTANCE_RETENTION_URL = "https://platform.openai.com/docs/models/default-usage-policies-by-endpoint"
CLOUD_ASSISTANCE_FACT_TYPES = {
    "net_worth": {"total_assets", "total_liabilities"},
    "cash_flow": {"monthly_income", "monthly_expenses"},
    "cash_flow_forecast": {"monthly_income", "monthly_expenses"},
    "debt_analysis": {"monthly_income", "monthly_debt_payments", "debt_outstanding"},
    "goal_progress": {"goal_current", "goal_target"},
    "insurance_gap": {"insurance_coverage"},
    "emergency_fund": {"liquid_assets", "monthly_expenses"},
}


@router.get("/capabilities")
def list_capabilities(
    current_user: User = Depends(get_current_active_user),
    settings: Settings = Depends(get_settings),
):
    """Expose release status without provider identifiers, secrets, or user data."""
    return {"phase": 3, "capabilities": get_ecosystem_capabilities(settings)}


class CreateConversationRequest(BaseModel):
    title: str = Field(default="Financial freedom conversation", min_length=1, max_length=160)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    conversation_id: UUID
    title: str
    status: str
    created_at: datetime


class FreedomScenarioRequest(BaseModel):
    current_age: int = Field(ge=18, lt=100)
    target_age: int = Field(gt=18, le=100)
    current_monthly_lifestyle_expenses: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    current_investable_corpus: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    monthly_contribution: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    annual_inflation_rate: Decimal | None = Field(default=None, ge=0, le=Decimal("0.20"), max_digits=5, decimal_places=4)
    annual_return_rate: Decimal | None = Field(default=None, ge=Decimal("-0.50"), le=Decimal("0.50"), max_digits=5, decimal_places=4)
    withdrawal_rate: Decimal | None = Field(default=None, ge=Decimal("0.01"), le=Decimal("0.10"), max_digits=5, decimal_places=4)

    @model_validator(mode="after")
    def validate_age_order(self):
        if self.target_age <= self.current_age:
            raise ValueError("target_age must be greater than current_age")
        supplied_rates = (
            self.annual_inflation_rate,
            self.annual_return_rate,
            self.withdrawal_rate,
        )
        if any(rate is not None for rate in supplied_rates) and not all(rate is not None for rate in supplied_rates):
            raise ValueError("custom scenario rates must be supplied together")
        return self


def resolve_freedom_scenario(payload: FreedomScenarioRequest) -> tuple[FreedomProjectionInputs, dict[str, Any]]:
    scenario = payload.model_dump()
    if payload.annual_inflation_rate is not None:
        return FreedomProjectionInputs(**scenario), {
            "source": "explicit_user_confirmed_scenario",
            "rates": {},
        }

    rates: dict[str, Any] = {}
    for field, assumption in FINANCIAL_FREEDOM_ASSUMPTIONS.items():
        require_current_assumption(assumption)
        if assumption.value is None or assumption.version is None or assumption.reviewed_at is None:
            raise StaleAssumptionError(f"Assumption {assumption.identifier} has not completed review")
        scenario[field] = assumption.value
        rates[field] = {
            "value": str(assumption.value),
            "identifier": assumption.identifier,
            "version": assumption.version,
            "source_url": assumption.source_url,
            "effective_from": assumption.effective_from.isoformat(),
            "reviewed_at": assumption.reviewed_at.isoformat(),
            "review_by": assumption.review_by.isoformat(),
            "methodology": assumption.methodology,
        }
    return FreedomProjectionInputs(**scenario), {
        "source": "reviewed_assumption_catalogue",
        "rates": rates,
    }


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    client_request_id: UUID | None = None
    freedom_scenario: FreedomScenarioRequest | None = None
    user_selected_coverage_target: Decimal | None = Field(
        default=None, ge=0, max_digits=18, decimal_places=2
    )
    cloud_assistance: bool = False


class MessageResponse(BaseModel):
    message_id: UUID
    run_id: UUID
    role: Literal["assistant"] = "assistant"
    content: str
    blocks: list[dict[str, Any]]
    created_at: datetime


class CloudAssistanceConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    consent_id: UUID | None = None
    status: Literal["active", "revoked", "not_granted"]
    provider: str = "OpenAI"
    purpose: str = CLOUD_ASSISTANCE_PURPOSE
    policy_bundle_version: str = MODEL_POLICY_BUNDLE_VERSION
    data_categories: list[str] = Field(default_factory=lambda: list(CLOUD_ASSISTANCE_CATEGORIES))
    excluded_categories: list[str] = Field(default_factory=lambda: [
        "original_documents", "document_text", "file_paths", "user_identifiers",
        "unverified_facts", "raw_user_message",
    ])
    retention_url: str = CLOUD_ASSISTANCE_RETENTION_URL
    granted_at: datetime | None = None
    revoked_at: datetime | None = None


class GrantCloudAssistanceConsentRequest(BaseModel):
    privacy_notice_version: str = Field(min_length=1, max_length=40)


def active_cloud_consent(db: Session, conversation_id: UUID, user_id: UUID) -> ModelConsent | None:
    return db.query(ModelConsent).filter(
        ModelConsent.conversation_id == conversation_id,
        ModelConsent.user_id == user_id,
        ModelConsent.status == "active",
    ).first()


def cloud_consent_response(consent: ModelConsent | None) -> CloudAssistanceConsentResponse:
    if consent is None:
        return CloudAssistanceConsentResponse(status="not_granted")
    return CloudAssistanceConsentResponse(
        consent_id=consent.consent_id,
        status=consent.status,
        provider="OpenAI",
        purpose=consent.purpose,
        policy_bundle_version=consent.policy_bundle_version,
        data_categories=list(consent.data_categories),
        granted_at=consent.granted_at,
        revoked_at=consent.revoked_at,
    )


def minimized_model_request(db: Session, user_id: UUID, intent: str, blocks: list[dict[str, Any]]) -> ModelRequest:
    allowed_fact_types = CLOUD_ASSISTANCE_FACT_TYPES.get(intent, set())
    facts = db.query(FinancialFact).filter(
        FinancialFact.user_id == user_id,
        FinancialFact.verification_status == "verified",
        FinancialFact.fact_type.in_(allowed_fact_types),
    ).order_by(FinancialFact.period_start.desc(), FinancialFact.observed_at.desc()).all()
    verified_context = {}
    for fact in facts:
        verified_context.setdefault(fact.fact_type, {
            "value": str(fact.value), "unit": fact.unit,
            "period_kind": fact.period_kind, "period_start": fact.period_start.isoformat(),
        })
    evidence = [
        {
            "type": block["type"],
            "calculation_id": block.get("calculation_id"),
            "version": block.get("version"),
            "result": block.get("result"),
            "assumptions": block.get("assumptions"),
            "limitations": block.get("limitations", []),
            "rule_versions": block.get("rule_versions", {}),
        }
        for block in blocks if block.get("type") == "calculation"
    ]
    return ModelRequest(
        intent=intent,
        redacted_context=redact_sensitive(verified_context),
        tool_results=redact_sensitive(evidence),
    )


class ConfirmationRequest(BaseModel):
    action_type: str = Field(min_length=1, max_length=60)
    action_payload: dict[str, Any]


class ConfirmationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    confirmation_id: UUID
    action_type: str
    status: str
    expires_at: datetime


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    review_id: UUID
    finding_type: str
    status: str
    evidence: dict[str, Any]
    rule_version: str
    created_at: datetime


class CreateFinancialFactRequest(BaseModel):
    fact_type: str
    value: Decimal = Field(ge=0, max_digits=20, decimal_places=4)
    unit: str = Field(default="INR", min_length=1, max_length=12)
    source_type: Literal["user_statement", "manual_record", "imported_record", "local_document_confirmation"] = "user_statement"
    source_id: str | None = Field(default=None, max_length=120)
    observed_at: datetime
    period_kind: Literal["monthly", "as_of"] | None = None
    period_start: date | None = None
    confidence: Decimal | None = Field(default=None, ge=0, le=1, max_digits=5, decimal_places=4)

    @model_validator(mode="after")
    def validate_fact_type(self):
        if self.fact_type not in ALLOWED_FACT_TYPES:
            raise ValueError("Unsupported financial fact type")
        if self.source_type == "local_document_confirmation":
            if not self.source_id:
                raise ValueError("Local document confirmation requires an opaque evidence reference")
            try:
                UUID(self.source_id)
            except ValueError as exc:
                raise ValueError("Local document confirmation requires a valid opaque evidence identifier") from exc
        expected_kind = "monthly" if self.fact_type in MONTHLY_FACT_TYPES else "as_of"
        if self.period_kind is not None and self.period_kind != expected_kind:
            raise ValueError(f"{self.fact_type} requires {expected_kind} period semantics")
        self.period_kind = expected_kind
        if self.period_start is None:
            observed_date = self.observed_at.date()
            self.period_start = observed_date.replace(day=1) if expected_kind == "monthly" else observed_date
        if expected_kind == "monthly" and self.period_start.day != 1:
            raise ValueError("Monthly periods must use the first day of the month")
        local_date_tolerance = datetime.now(timezone.utc).date() + timedelta(days=1)
        latest_allowed = local_date_tolerance.replace(day=1) if expected_kind == "monthly" else local_date_tolerance
        if self.period_start > latest_allowed:
            raise ValueError("Financial fact period cannot be in the future")
        return self


class FinancialFactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    fact_id: UUID
    fact_type: str
    value: Decimal
    unit: str
    source_type: str
    source_id: str | None
    verification_status: str
    confidence: Decimal | None
    period_kind: Literal["monthly", "as_of"]
    period_start: date
    observed_at: datetime
    verified_at: datetime | None
    supersedes_fact_id: UUID | None


class FactDecisionRequest(BaseModel):
    decision: Literal["confirm", "reject"]


class CreateFinancialFactBatchRequest(BaseModel):
    facts: list[CreateFinancialFactRequest] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def reject_duplicate_periods(self):
        keys = [(item.fact_type, item.period_start) for item in self.facts]
        if len(keys) != len(set(keys)):
            raise ValueError("A batch cannot contain duplicate field and period entries")
        return self


class FactBatchDecisionRequest(BaseModel):
    fact_ids: list[UUID] = Field(min_length=1, max_length=10)
    decision: Literal["confirm", "reject"]

    @model_validator(mode="after")
    def reject_duplicate_ids(self):
        if len(self.fact_ids) != len(set(self.fact_ids)):
            raise ValueError("Duplicate financial fact identifiers are not allowed")
        return self


class CandidateActionRequest(BaseModel):
    action_type: Literal["reduce_monthly_expenses", "increase_monthly_savings", "increase_debt_payment"]
    monthly_amount: Decimal = Field(gt=0, max_digits=20, decimal_places=2)
    feasibility: Decimal | None = Field(default=None, ge=0, le=1, max_digits=5, decimal_places=4)
    user_priority: Decimal | None = Field(default=None, ge=0, le=1, max_digits=5, decimal_places=4)
    priority_label: Literal["low", "medium", "high"] = "medium"
    difficulty_label: Literal["easy", "manageable", "difficult"] = "manageable"
    start_date: date | None = None
    target_date: date | None = None

    @model_validator(mode="after")
    def derive_scores_and_dates(self):
        priority_scores = {"low": Decimal("0.25"), "medium": Decimal("0.50"), "high": Decimal("0.75")}
        difficulty_scores = {"easy": Decimal("0.25"), "manageable": Decimal("0.50"), "difficult": Decimal("0.75")}
        self.user_priority = self.user_priority if self.user_priority is not None else priority_scores[self.priority_label]
        self.feasibility = self.feasibility if self.feasibility is not None else Decimal("1") - difficulty_scores[self.difficulty_label]
        self.start_date = self.start_date or date.today()
        self.target_date = self.target_date or self.start_date
        if self.target_date < self.start_date:
            raise ValueError("Target date must be on or after the start date")
        return self


class RankActionsRequest(BaseModel):
    actions: list[CandidateActionRequest] = Field(min_length=1, max_length=10)


class CreateActionPlanRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    actions: list[CandidateActionRequest] = Field(min_length=1, max_length=10)
    confirmation_id: UUID


class ConvertReviewRequest(BaseModel):
    plan_id: UUID


class UpdatePlannedActionRequest(BaseModel):
    monthly_amount: Decimal = Field(gt=0, max_digits=20, decimal_places=2)
    priority_label: Literal["low", "medium", "high"]
    difficulty_label: Literal["easy", "manageable", "difficult"]
    start_date: date
    target_date: date
    confirmation_id: UUID

    @model_validator(mode="after")
    def validate_dates(self):
        if self.target_date < self.start_date:
            raise ValueError("Target date must be on or after the start date")
        return self


class ActionCheckInRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=20, decimal_places=2)
    check_in_date: date
    note: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def reject_future_check_in(self):
        if self.check_in_date > date.today():
            raise ValueError("Check-in date cannot be in the future")
        return self


class ActionStatusRequest(BaseModel):
    status: Literal["active", "paused", "completed", "archived"]
    confirmation_id: UUID | None = None


@router.post("/planning/candidates")
def compare_planning_actions(
    payload: RankActionsRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    actions = [CandidateAction(action_type=item.action_type, monthly_amount=item.monthly_amount, feasibility=item.feasibility, user_priority=item.user_priority) for item in payload.actions]
    ranked = rank_actions(actions)
    now = datetime.now(timezone.utc)
    record = CalculationRecord(
        calculation_id=uuid4(), user_id=current_user.user_id, calculation_type="planning_action_candidates",
        calculation_version=ACTION_TRACKING_VERSION,
        inputs={"actions": [item.model_dump(mode="json") for item in payload.actions]},
        assumptions={"priority_mapping": "low=0.25, medium=0.50, high=0.75", "difficulty": "inverted into feasibility"},
        result={"actions": ranked}, input_provenance=[{"source": "user_input"}], rule_versions={},
        limitations=["Conditional planning impact only", "No product or guaranteed outcome is implied"], as_of=now,
    )
    db.add(record); db.commit()
    return {"actions": ranked, "calculation_id": record.calculation_id, "version": ACTION_TRACKING_VERSION, "timestamp": now, "assumptions": record.assumptions, "limitations": record.limitations}


def _action_progress(action: PlannedAction) -> dict[str, Any]:
    return calculate_action_progress([Decimal(item.amount) for item in action.check_ins], Decimal(action.target_amount))


def _action_response(action: PlannedAction, *, include_check_ins: bool = False) -> dict[str, Any]:
    result = {
        "action_id": action.action_id, "action_type": action.action_type,
        "monthly_amount": str(action.monthly_amount), "currency": action.currency,
        "rank": str(action.rank), "rationale": action.rationale, "impact": action.impact,
        "status": action.status, "start_date": action.start_date, "target_date": action.target_date,
        "target_amount": str(action.target_amount), "priority_label": action.priority_label,
        "difficulty_label": action.difficulty_label, "progress": _action_progress(action),
        "created_at": action.created_at, "updated_at": action.updated_at,
        "completed_at": action.completed_at, "archived_at": action.archived_at,
    }
    if include_check_ins:
        result["check_ins"] = [{"check_in_id": item.check_in_id, "amount": str(item.amount), "currency": item.currency, "check_in_date": item.check_in_date, "note": item.note, "created_at": item.created_at} for item in sorted(action.check_ins, key=lambda value: (value.check_in_date, value.created_at), reverse=True)]
    return result


def _owned_action(db: Session, action_id: UUID, user_id: UUID) -> PlannedAction:
    action = db.query(PlannedAction).join(ActionPlan).filter(PlannedAction.action_id == action_id, ActionPlan.user_id == user_id).first()
    if action is None:
        raise HTTPException(status_code=404, detail="Planning action not found")
    return action


def _consume_confirmation(db: Session, confirmation_id: UUID | None, user_id: UUID, action_type: str, action_payload: dict[str, Any]) -> Confirmation:
    canonical = json.dumps(action_payload, sort_keys=True, separators=(",", ":"))
    expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    confirmation = db.query(Confirmation).filter(
        Confirmation.confirmation_id == confirmation_id, Confirmation.user_id == user_id,
        Confirmation.action_type == action_type, Confirmation.status == "confirmed",
        Confirmation.consumed_at.is_(None),
    ).with_for_update().first()
    now = datetime.now(timezone.utc)
    if confirmation is None or confirmation.expires_at < now or confirmation.action_payload_hash != expected_hash:
        raise HTTPException(status_code=409, detail="A current payload-matched confirmation is required")
    confirmation.consumed_at = now; confirmation.status = "consumed"
    return confirmation


@router.get("/planning/plans")
def list_action_plans(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    plans = db.query(ActionPlan).filter(ActionPlan.user_id == current_user.user_id).order_by(ActionPlan.created_at.desc()).all()
    return [{
        "plan_id": plan.plan_id, "title": plan.title, "status": plan.status,
        "created_at": plan.created_at,
        "actions": [_action_response(action) for action in plan.actions],
    } for plan in plans]


@router.post("/planning/plans", status_code=201)
def create_action_plan(
    payload: CreateActionPlanRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    action_payload = {"title": payload.title, "actions": [item.model_dump(mode="json", exclude_unset=True) for item in payload.actions]}
    confirmation = _consume_confirmation(db, payload.confirmation_id, current_user.user_id, "create_action_plan", action_payload)
    ranked = [rank_actions([CandidateAction(action_type=item.action_type, monthly_amount=item.monthly_amount, feasibility=item.feasibility, user_priority=item.user_priority)])[0] for item in payload.actions]
    plan = db.query(ActionPlan).filter(ActionPlan.user_id == current_user.user_id, ActionPlan.status == "active").first()
    if plan is None:
        plan = ActionPlan(user_id=current_user.user_id, title=payload.title, status="active")
        db.add(plan); db.flush()
    calculation_ids = []
    for request_item, item in zip(payload.actions, ranked, strict=True):
        target = calculate_action_target(request_item.monthly_amount, request_item.start_date, request_item.target_date)
        action = PlannedAction(
            plan_id=plan.plan_id, action_type=item["action_type"],
            monthly_amount=Decimal(item["monthly_amount"]), rank=Decimal(item["score"]),
            rationale=item["rationale"], impact=item["impact"], status="active",
            start_date=request_item.start_date, target_date=request_item.target_date,
            target_amount=Decimal(target["target_amount"]), priority_label=request_item.priority_label,
            difficulty_label=request_item.difficulty_label,
        )
        db.add(action); db.flush()
        calculation = CalculationRecord(calculation_id=uuid4(), user_id=current_user.user_id, calculation_type="action_target", calculation_version=ACTION_TRACKING_VERSION, inputs={"action_id": str(action.action_id), "monthly_amount": str(request_item.monthly_amount), "start_date": request_item.start_date.isoformat(), "target_date": request_item.target_date.isoformat()}, assumptions={"month_count": "inclusive calendar months"}, result=target, input_provenance=[{"source": "confirmed_action"}], rule_versions={}, limitations=["Target assumes the same action amount each calendar month"], as_of=datetime.now(timezone.utc))
        db.add(calculation); calculation_ids.append(calculation.calculation_id)
    db.add(AuditEvent(user_id=current_user.user_id, event_type="action_plan_created", target_type="action_plan", target_id=str(plan.plan_id), outcome="success", metadata_json={"action_count": len(ranked), "planner_version": "planning-actions-v1"}))
    db.commit()
    db.refresh(plan)
    return {"plan_id": plan.plan_id, "title": plan.title, "status": plan.status, "action_count": len(ranked), "calculation_ids": calculation_ids, "version": ACTION_TRACKING_VERSION}


@router.get("/planning/plans/active")
def get_active_action_plan(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    plans = db.query(ActionPlan).filter(ActionPlan.user_id == current_user.user_id).order_by(ActionPlan.created_at.desc()).all()
    active_plan = next((plan for plan in plans if plan.status == "active"), None)
    actions = [action for plan in plans for action in plan.actions]
    active_actions = [action for action in (active_plan.actions if active_plan else []) if action.status in {"active", "paused"}]
    completed = [action for action in actions if action.status == "completed" and action.plan.status != "archived"]
    archived = [action for action in actions if action.status == "archived" or action.plan.status == "archived"]
    commitment = sum((Decimal(action.monthly_amount) for action in active_actions if action.status == "active" and action.action_type in {"increase_monthly_savings", "increase_debt_payment"}), Decimal("0"))
    now = datetime.now(timezone.utc)
    result = {
        "plan": {"plan_id": active_plan.plan_id, "title": active_plan.title, "created_at": active_plan.created_at} if active_plan else None,
        "summary": {"active_count": len(active_actions), "monthly_commitment": {"amount": str(commitment.quantize(Decimal('0.01'))), "currency": "INR"}, "completed_count": len(completed)},
        "active_actions": [_action_response(action) for action in active_actions],
        "completed_actions": [_action_response(action) for action in completed],
        "archived_actions": [_action_response(action) for action in archived],
    }
    record = CalculationRecord(calculation_id=uuid4(), user_id=current_user.user_id, calculation_type="action_plan_summary", calculation_version=ACTION_TRACKING_VERSION, inputs={"active_action_ids": [str(action.action_id) for action in active_actions]}, assumptions={"monthly_commitment": "active savings and extra debt-payment actions only", "progress": "manual check-ins only"}, result=result["summary"], input_provenance=[{"source": "confirmed_action_plan"}], rule_versions={}, limitations=["Expense-reduction actions are excluded from monthly commitment"], as_of=now)
    db.add(record); db.commit()
    return {**result, "calculation_id": record.calculation_id, "version": ACTION_TRACKING_VERSION, "timestamp": now, "assumptions": record.assumptions, "limitations": record.limitations}


@router.get("/planning/actions/{action_id}")
def get_planned_action(action_id: UUID, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    action = _owned_action(db, action_id, current_user.user_id)
    progress = _action_progress(action); now = datetime.now(timezone.utc)
    record = CalculationRecord(calculation_id=uuid4(), user_id=current_user.user_id, calculation_type="action_progress", calculation_version=ACTION_TRACKING_VERSION, inputs={"action_id": str(action.action_id), "check_in_ids": [str(item.check_in_id) for item in action.check_ins]}, assumptions={"progress": "sum of explicit manual check-ins capped at 100%"}, result=progress, input_provenance=[{"source": "user_check_in"}], rule_versions={}, limitations=["Progress is based only on user check-ins"], as_of=now)
    db.add(record); db.commit()
    return {**_action_response(action, include_check_ins=True), "calculation_id": record.calculation_id, "version": ACTION_TRACKING_VERSION, "timestamp": now, "assumptions": record.assumptions, "limitations": record.limitations}


@router.post("/planning/actions/{action_id}/check-ins", status_code=201)
def create_action_check_in(action_id: UUID, payload: ActionCheckInRequest, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    action = _owned_action(db, action_id, current_user.user_id)
    if action.status not in {"active", "paused"}:
        raise HTTPException(status_code=409, detail="Only active or paused actions accept check-ins")
    check_in = ActionCheckIn(action=action, amount=payload.amount, check_in_date=payload.check_in_date, note=payload.note)
    db.add(check_in); db.flush()
    progress = calculate_action_progress([Decimal(item.amount) for item in action.check_ins], Decimal(action.target_amount))
    now = datetime.now(timezone.utc)
    record = CalculationRecord(calculation_id=uuid4(), user_id=current_user.user_id, calculation_type="action_progress", calculation_version=ACTION_TRACKING_VERSION, inputs={"action_id": str(action.action_id), "check_in_ids": [str(item.check_in_id) for item in action.check_ins]}, assumptions={"progress": "sum of explicit manual check-ins capped at 100%"}, result=progress, input_provenance=[{"source": "user_check_in"}], rule_versions={}, limitations=["Progress is based only on user check-ins"], as_of=now)
    db.add(record); db.add(AuditEvent(user_id=current_user.user_id, event_type="action_check_in_created", target_type="planned_action", target_id=str(action.action_id), outcome="success", metadata_json={"calculation_id": str(record.calculation_id)})); db.commit(); db.refresh(check_in)
    return {"check_in_id": check_in.check_in_id, "progress": progress, "calculation_id": record.calculation_id, "version": ACTION_TRACKING_VERSION, "timestamp": now}


@router.patch("/planning/actions/{action_id}")
def update_planned_action(action_id: UUID, payload: UpdatePlannedActionRequest, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    action = _owned_action(db, action_id, current_user.user_id)
    if action.status == "archived":
        raise HTTPException(status_code=409, detail="Archived actions cannot be edited")
    action_payload = {"action_id": str(action_id), **payload.model_dump(mode="json", exclude={"confirmation_id"})}
    _consume_confirmation(db, payload.confirmation_id, current_user.user_id, "update_planned_action", action_payload)
    target = calculate_action_target(payload.monthly_amount, payload.start_date, payload.target_date)
    label_scores = {"low": Decimal("0.25"), "medium": Decimal("0.50"), "high": Decimal("0.75")}
    difficulty_scores = {"easy": Decimal("0.25"), "manageable": Decimal("0.50"), "difficult": Decimal("0.75")}
    ranked = rank_actions([CandidateAction(action_type=action.action_type, monthly_amount=payload.monthly_amount, feasibility=Decimal("1") - difficulty_scores[payload.difficulty_label], user_priority=label_scores[payload.priority_label])])[0]
    action.monthly_amount = payload.monthly_amount; action.start_date = payload.start_date; action.target_date = payload.target_date
    action.target_amount = Decimal(target["target_amount"]); action.priority_label = payload.priority_label; action.difficulty_label = payload.difficulty_label
    action.rank = Decimal(ranked["score"]); action.rationale = ranked["rationale"]; action.impact = ranked["impact"]
    action.updated_at = datetime.now(timezone.utc)
    calculation = CalculationRecord(calculation_id=uuid4(), user_id=current_user.user_id, calculation_type="action_target", calculation_version=ACTION_TRACKING_VERSION, inputs={"action_id": str(action.action_id), "monthly_amount": str(payload.monthly_amount), "start_date": payload.start_date.isoformat(), "target_date": payload.target_date.isoformat()}, assumptions={"month_count": "inclusive calendar months"}, result=target, input_provenance=[{"source": "confirmed_action_update"}], rule_versions={}, limitations=["Target assumes the same action amount each calendar month"], as_of=action.updated_at)
    db.add(calculation)
    db.add(AuditEvent(user_id=current_user.user_id, event_type="planned_action_updated", target_type="planned_action", target_id=str(action.action_id), outcome="success", metadata_json={"tracking_version": ACTION_TRACKING_VERSION})); db.commit(); db.refresh(action)
    return {**_action_response(action, include_check_ins=True), "calculation_id": calculation.calculation_id, "version": ACTION_TRACKING_VERSION, "timestamp": calculation.as_of, "assumptions": calculation.assumptions, "limitations": calculation.limitations}


@router.post("/planning/actions/{action_id}/status")
def change_planned_action_status(action_id: UUID, payload: ActionStatusRequest, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    action = _owned_action(db, action_id, current_user.user_id)
    allowed = {"active": {"paused", "completed", "archived"}, "paused": {"active", "completed", "archived"}, "completed": {"archived"}, "archived": set()}
    if payload.status not in allowed.get(action.status, set()):
        raise HTTPException(status_code=409, detail="Unsupported action status transition")
    if payload.status == "archived":
        _consume_confirmation(db, payload.confirmation_id, current_user.user_id, "archive_planned_action", {"action_id": str(action_id), "status": "archived"})
    now = datetime.now(timezone.utc); action.status = payload.status; action.updated_at = now
    action.completed_at = now if payload.status == "completed" else action.completed_at
    action.archived_at = now if payload.status == "archived" else action.archived_at
    db.add(AuditEvent(user_id=current_user.user_id, event_type=f"planned_action_{payload.status}", target_type="planned_action", target_id=str(action.action_id), outcome="success", metadata_json={})); db.commit(); db.refresh(action)
    return _action_response(action, include_check_ins=True)


@router.get("/financial-facts", response_model=list[FinancialFactResponse])
def list_financial_facts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return db.query(FinancialFact).filter(
        FinancialFact.user_id == current_user.user_id
    ).order_by(FinancialFact.period_start.desc(), FinancialFact.created_at.desc()).all()


@router.get("/financial-memory/monthly-summary")
def get_financial_memory_monthly_summary(
    month: str = Query(pattern=r"^\d{4}-(?:0[1-9]|1[0-2])$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    period_start = date.fromisoformat(f"{month}-01")
    required = ("monthly_income", "monthly_expenses", "monthly_debt_payments")
    rows = db.query(FinancialFact).filter(
        FinancialFact.user_id == current_user.user_id,
        FinancialFact.fact_type.in_(required),
        FinancialFact.period_kind == "monthly",
        FinancialFact.period_start == period_start,
        FinancialFact.verification_status == "verified",
    ).order_by(FinancialFact.created_at.desc()).all()
    selected = {}
    for row in rows:
        selected.setdefault(row.fact_type, row)
    missing = [fact_type for fact_type in required if fact_type not in selected]
    if missing:
        return {"status": "incomplete", "month": month, "missing": missing, "money_left": None}

    result = calculate_monthly_money_left(*(Decimal(selected[key].value) for key in required))
    now = datetime.now(timezone.utc)
    provenance = [{
        "fact_id": str(selected[key].fact_id), "fact_type": key,
        "source_type": selected[key].source_type, "source_id": selected[key].source_id,
        "observed_at": selected[key].observed_at.isoformat(),
        "period_kind": selected[key].period_kind,
        "period_start": selected[key].period_start.isoformat(),
        "verified_at": selected[key].verified_at.isoformat() if selected[key].verified_at else None,
    } for key in required]
    assumptions = {
        "currency": "INR", "period": month,
        "formula": "monthly_income - monthly_expenses - monthly_debt_payments",
        "inputs": "confirmed_same_month_facts_only",
    }
    record = CalculationRecord(
        calculation_id=uuid4(), user_id=current_user.user_id,
        calculation_type="financial_memory_monthly_money_left",
        calculation_version=MEMORY_MONTHLY_SUMMARY_VERSION,
        inputs={"fact_ids": [item["fact_id"] for item in provenance]},
        assumptions=assumptions, result=result, input_provenance=provenance,
        rule_versions={"calculation": MEMORY_MONTHLY_SUMMARY_VERSION},
        limitations=["Only confirmed facts for the selected calendar month are included"],
        as_of=now,
    )
    db.add(record)
    db.commit()
    return {
        "status": "complete", "month": month, "missing": [],
        "money_left": result["money_left"], "calculation_id": str(record.calculation_id),
        "version": record.calculation_version, "timestamp": now.isoformat(),
        "assumptions": assumptions, "provenance": provenance,
        "limitations": record.limitations,
    }


@router.post("/financial-facts", response_model=FinancialFactResponse, status_code=201)
def create_financial_fact_candidate(
    payload: CreateFinancialFactRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        fact = FinancialContextService(db, current_user.user_id).create_candidate(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    db.refresh(fact)
    return fact


@router.post("/financial-facts/batch", response_model=list[FinancialFactResponse], status_code=201)
def create_financial_fact_candidates_batch(
    payload: CreateFinancialFactBatchRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    service = FinancialContextService(db, current_user.user_id)
    try:
        facts = [service.create_candidate(**item.model_dump()) for item in payload.facts]
        db.commit()
        for fact in facts:
            db.refresh(fact)
        return facts
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/financial-facts/batch/decision", response_model=list[FinancialFactResponse])
def decide_financial_facts_batch(
    payload: FactBatchDecisionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        facts = FinancialContextService(db, current_user.user_id).decide_many(payload.fact_ids, payload.decision)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    for fact in facts:
        db.refresh(fact)
    return facts


@router.post("/financial-facts/{fact_id}/decision", response_model=FinancialFactResponse)
def decide_financial_fact(
    fact_id: UUID,
    payload: FactDecisionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        fact = FinancialContextService(db, current_user.user_id).decide(fact_id, payload.decision)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(fact)
    return fact


@router.get("/financial-context/{scope}")
def get_financial_context(
    scope: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        packet = FinancialContextService(db, current_user.user_id).assemble(scope)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "scope": scope,
        "as_of": packet.as_of,
        "facts": [{
            "fact_id": fact.fact_id, "fact_type": fact.fact_type,
            "value": str(fact.value), "unit": fact.unit,
            "source_type": fact.source_type, "verification_status": fact.verification_status,
            "observed_at": fact.observed_at,
        } for fact in packet.facts.values()],
        "missing": packet.missing,
    }


def owned_conversation(db: Session, conversation_id: UUID, user_id: UUID) -> Conversation:
    conversation = db.query(Conversation).filter(
        Conversation.conversation_id == conversation_id,
        Conversation.user_id == user_id,
    ).first()
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
def create_conversation(
    payload: CreateConversationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    conversation = Conversation(user_id=current_user.user_id, title=payload.title)
    db.add(conversation)
    db.flush()
    db.add(AuditEvent(
        user_id=current_user.user_id, event_type="conversation_created",
        target_type="conversation", target_id=str(conversation.conversation_id),
        outcome="success", metadata_json={},
    ))
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return db.query(Conversation).filter(Conversation.user_id == current_user.user_id).order_by(Conversation.updated_at.desc()).all()


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    conversation = owned_conversation(db, conversation_id, current_user.user_id)
    return {
        "conversation": ConversationResponse.model_validate(conversation),
        "messages": [
            {"message_id": row.message_id, "role": row.role, "content": row.content,
             "blocks": row.structured_content.get("blocks", []), "created_at": row.created_at}
            for row in sorted(conversation.messages, key=lambda item: item.created_at)
        ],
    }


@router.get(
    "/conversations/{conversation_id}/cloud-assistance",
    response_model=CloudAssistanceConsentResponse,
)
def get_cloud_assistance_consent(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    owned_conversation(db, conversation_id, current_user.user_id)
    consent = db.query(ModelConsent).filter(
        ModelConsent.conversation_id == conversation_id,
        ModelConsent.user_id == current_user.user_id,
    ).first()
    return cloud_consent_response(consent)


@router.post(
    "/conversations/{conversation_id}/cloud-assistance",
    response_model=CloudAssistanceConsentResponse,
    status_code=201,
)
def grant_cloud_assistance_consent(
    conversation_id: UUID,
    payload: GrantCloudAssistanceConsentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    owned_conversation(db, conversation_id, current_user.user_id)
    consent = db.query(ModelConsent).filter(
        ModelConsent.conversation_id == conversation_id,
        ModelConsent.user_id == current_user.user_id,
    ).with_for_update().first()
    now = datetime.now(timezone.utc)
    if consent is None:
        consent = ModelConsent(
            user_id=current_user.user_id,
            conversation_id=conversation_id,
            provider="openai",
            purpose=CLOUD_ASSISTANCE_PURPOSE,
            policy_bundle_version=MODEL_POLICY_BUNDLE_VERSION,
            data_categories=list(CLOUD_ASSISTANCE_CATEGORIES),
            status="active",
            granted_at=now,
        )
        db.add(consent)
    else:
        consent.status = "active"
        consent.policy_bundle_version = MODEL_POLICY_BUNDLE_VERSION
        consent.data_categories = list(CLOUD_ASSISTANCE_CATEGORIES)
        consent.granted_at = now
        consent.revoked_at = None
    db.add(AuditEvent(
        user_id=current_user.user_id,
        event_type="cloud_assistance_consent_granted",
        target_type="conversation",
        target_id=str(conversation_id),
        outcome="success",
        metadata_json={"notice_version": payload.privacy_notice_version, "policy_bundle_version": MODEL_POLICY_BUNDLE_VERSION},
    ))
    db.commit()
    db.refresh(consent)
    return cloud_consent_response(consent)


@router.delete(
    "/conversations/{conversation_id}/cloud-assistance",
    response_model=CloudAssistanceConsentResponse,
)
def revoke_cloud_assistance_consent(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    owned_conversation(db, conversation_id, current_user.user_id)
    consent = active_cloud_consent(db, conversation_id, current_user.user_id)
    if consent is None:
        return CloudAssistanceConsentResponse(status="not_granted")
    consent.status = "revoked"
    consent.revoked_at = datetime.now(timezone.utc)
    db.add(AuditEvent(
        user_id=current_user.user_id,
        event_type="cloud_assistance_consent_revoked",
        target_type="conversation",
        target_id=str(conversation_id),
        outcome="success",
        metadata_json={"policy_bundle_version": MODEL_POLICY_BUNDLE_VERSION},
    ))
    db.commit()
    db.refresh(consent)
    return cloud_consent_response(consent)


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: UUID,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    conversation = owned_conversation(db, conversation_id, current_user.user_id)
    if payload.client_request_id is not None:
        prior = db.query(ConversationMessage).filter(
            ConversationMessage.conversation_id == conversation.conversation_id,
            ConversationMessage.client_request_id == payload.client_request_id,
            ConversationMessage.role == "assistant",
        ).first()
        if prior is not None:
            prior_run = db.query(AgentRun).filter(AgentRun.message_id == prior.message_id).first()
            if prior_run is None:
                raise HTTPException(status_code=409, detail="Prior request is incomplete; retry later")
            return MessageResponse(
                message_id=prior.message_id, run_id=prior_run.run_id,
                content=prior.content, blocks=prior.structured_content.get("blocks", []),
                created_at=prior.created_at,
            )
    user_message = ConversationMessage(
        message_id=uuid4(), conversation_id=conversation.conversation_id,
        role="user", content=payload.content, structured_content={},
    )
    db.add(user_message)
    freedom_inputs = None
    freedom_assumption_metadata = None
    if payload.freedom_scenario:
        try:
            freedom_inputs, freedom_assumption_metadata = resolve_freedom_scenario(payload.freedom_scenario)
        except StaleAssumptionError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="This projection is temporarily unavailable while Artha’s planning assumptions are being reviewed.",
            ) from exc
    answer = AgentOrchestrator(db, current_user.user_id).answer(
        payload.content, freedom_inputs, payload.user_selected_coverage_target,
        freedom_assumption_metadata,
    )
    model_used = False
    if payload.cloud_assistance:
        settings = get_settings()
        if not settings.enable_external_model:
            raise HTTPException(status_code=503, detail="Cloud assistance is not enabled for this release")
        if active_cloud_consent(db, conversation_id, current_user.user_id) is None:
            raise HTTPException(status_code=409, detail="Cloud assistance requires active consent for this conversation")
        model_request = minimized_model_request(db, current_user.user_id, answer.intent.value, answer.blocks)
        try:
            explanation = await OpenAIModelGateway(settings.openai_api_key or "").compose(model_request)
            answer.blocks.append({
                "type": "cloud_explanation",
                "provider": "OpenAI",
                "policy_bundle_version": MODEL_POLICY_BUNDLE_VERSION,
                "content": explanation,
                "data_categories": list(CLOUD_ASSISTANCE_CATEGORIES),
            })
            model_used = True
        except Exception:
            answer.blocks.append({
                "type": "warning",
                "code": "CLOUD_EXPLANATION_UNAVAILABLE",
            })
    assistant_message = ConversationMessage(
        message_id=uuid4(), conversation_id=conversation.conversation_id,
        role="assistant", content=answer.narrative, structured_content={"blocks": answer.blocks},
        client_request_id=payload.client_request_id,
    )
    db.add(assistant_message)
    db.flush()
    run = audit_agent_run(db, current_user.user_id, assistant_message, answer, model_used=model_used)
    db.commit()
    return MessageResponse(
        message_id=assistant_message.message_id, run_id=run.run_id,
        content=assistant_message.content, blocks=answer.blocks,
        created_at=assistant_message.created_at or datetime.now(timezone.utc),
    )


@router.post(
    "/conversations/{conversation_id}/confirmations",
    response_model=ConfirmationResponse,
    status_code=201,
)
def create_confirmation(
    conversation_id: UUID,
    payload: ConfirmationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    owned_conversation(db, conversation_id, current_user.user_id)
    canonical_payload = json.dumps(payload.action_payload, sort_keys=True, separators=(",", ":"))
    confirmation = Confirmation(
        confirmation_id=uuid4(), user_id=current_user.user_id,
        conversation_id=conversation_id, action_type=payload.action_type,
        action_payload_hash=hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest(),
        status="confirmed", expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(confirmation)
    db.add(AuditEvent(
        user_id=current_user.user_id, event_type="action_confirmed",
        target_type="confirmation", target_id=str(confirmation.confirmation_id),
        outcome="success", metadata_json={"action_type": payload.action_type},
    ))
    db.commit()
    db.refresh(confirmation)
    return confirmation


@router.get("/messages/{message_id}/evidence")
def get_message_evidence(
    message_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    message = db.query(ConversationMessage).join(Conversation).filter(
        ConversationMessage.message_id == message_id,
        Conversation.user_id == current_user.user_id,
    ).first()
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message_id": message.message_id, "blocks": message.structured_content.get("blocks", [])}


@router.get("/reviews", response_model=list[ReviewResponse])
def list_reviews(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return db.query(ProactiveReview).filter(ProactiveReview.user_id == current_user.user_id).order_by(ProactiveReview.created_at.desc()).all()


@router.post("/reviews/run", response_model=list[ReviewResponse])
def run_reviews_now(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    reviews = persist_reviews(db, current_user.user_id)
    db.commit()
    for review in reviews:
        db.refresh(review)
    return reviews


@router.post("/reviews/{review_id}/acknowledge", response_model=ReviewResponse)
def acknowledge_review(
    review_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    review = db.query(ProactiveReview).filter(
        ProactiveReview.review_id == review_id,
        ProactiveReview.user_id == current_user.user_id,
    ).first()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    review.status = "acknowledged"
    review.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)
    return review


@router.post("/reviews/{review_id}/dismiss", response_model=ReviewResponse)
def dismiss_review(
    review_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    review = db.query(ProactiveReview).filter(
        ProactiveReview.review_id == review_id,
        ProactiveReview.user_id == current_user.user_id,
    ).first()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    review.status = "dismissed"
    review.dismissed_at = datetime.now(timezone.utc)
    db.add(AuditEvent(user_id=current_user.user_id, event_type="proactive_review_dismissed", target_type="proactive_review", target_id=str(review.review_id), outcome="success", metadata_json={"finding_type": review.finding_type, "rule_version": review.rule_version}))
    db.commit()
    db.refresh(review)
    return review


@router.post("/reviews/{review_id}/convert", response_model=ReviewResponse)
def convert_review_to_confirmed_plan(
    review_id: UUID,
    payload: ConvertReviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Link a finding to an already confirmed, user-owned action plan."""
    review = db.query(ProactiveReview).filter(
        ProactiveReview.review_id == review_id,
        ProactiveReview.user_id == current_user.user_id,
    ).first()
    plan = db.query(ActionPlan).filter(
        ActionPlan.plan_id == payload.plan_id,
        ActionPlan.user_id == current_user.user_id,
    ).first()
    if review is None or plan is None:
        raise HTTPException(status_code=404, detail="Review or confirmed plan not found")
    if review.status not in {"open", "acknowledged"}:
        raise HTTPException(status_code=409, detail="Only an open or acknowledged review can be converted")
    review.status = "converted"
    review.acknowledged_at = datetime.now(timezone.utc)
    db.add(AuditEvent(
        user_id=current_user.user_id,
        event_type="proactive_review_converted",
        target_type="proactive_review",
        target_id=str(review.review_id),
        outcome="success",
        metadata_json={"plan_id": str(plan.plan_id), "rule_version": review.rule_version},
    ))
    db.commit()
    db.refresh(review)
    return review
