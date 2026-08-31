"""Typed, authenticated API for the financial-freedom agent."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.auth.manager import get_current_active_user
from app.core.config import Settings, get_db, get_settings
from app.models.agent import ActionPlan, AgentRun, AuditEvent, Confirmation, Conversation, ConversationMessage, FinancialFact, PlannedAction, ProactiveReview
from app.models.user import User
from app.services.agent_orchestrator import AgentOrchestrator, audit_agent_run
from app.services.financial_freedom import FreedomProjectionInputs
from app.services.ecosystem_capabilities import get_ecosystem_capabilities
from app.services.financial_context import ALLOWED_FACT_TYPES, FinancialContextService
from app.services.recommendation_planner import CandidateAction, rank_actions
from app.services.proactive_reviews import persist_reviews

router = APIRouter()


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
    annual_inflation_rate: Decimal = Field(ge=0, le=Decimal("0.20"), max_digits=5, decimal_places=4)
    annual_return_rate: Decimal = Field(ge=Decimal("-0.50"), le=Decimal("0.50"), max_digits=5, decimal_places=4)
    withdrawal_rate: Decimal = Field(ge=Decimal("0.01"), le=Decimal("0.10"), max_digits=5, decimal_places=4)

    @model_validator(mode="after")
    def validate_age_order(self):
        if self.target_age <= self.current_age:
            raise ValueError("target_age must be greater than current_age")
        return self


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    client_request_id: UUID | None = None
    freedom_scenario: FreedomScenarioRequest | None = None
    user_selected_coverage_target: Decimal | None = Field(
        default=None, ge=0, max_digits=18, decimal_places=2
    )


class MessageResponse(BaseModel):
    message_id: UUID
    run_id: UUID
    role: Literal["assistant"] = "assistant"
    content: str
    blocks: list[dict[str, Any]]
    created_at: datetime


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
    observed_at: datetime
    verified_at: datetime | None
    supersedes_fact_id: UUID | None


class FactDecisionRequest(BaseModel):
    decision: Literal["confirm", "reject"]


class CandidateActionRequest(BaseModel):
    action_type: Literal["reduce_monthly_expenses", "increase_monthly_savings", "increase_debt_payment"]
    monthly_amount: Decimal = Field(gt=0, max_digits=20, decimal_places=2)
    feasibility: Decimal = Field(ge=0, le=1, max_digits=5, decimal_places=4)
    user_priority: Decimal = Field(ge=0, le=1, max_digits=5, decimal_places=4)


class RankActionsRequest(BaseModel):
    actions: list[CandidateActionRequest] = Field(min_length=1, max_length=10)


class CreateActionPlanRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    actions: list[CandidateActionRequest] = Field(min_length=1, max_length=10)
    confirmation_id: UUID


class ConvertReviewRequest(BaseModel):
    plan_id: UUID


@router.post("/planning/candidates")
def compare_planning_actions(
    payload: RankActionsRequest,
    current_user: User = Depends(get_current_active_user),
):
    del current_user
    actions = [CandidateAction(**item.model_dump()) for item in payload.actions]
    return {"actions": rank_actions(actions)}


@router.get("/planning/plans")
def list_action_plans(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    plans = db.query(ActionPlan).filter(ActionPlan.user_id == current_user.user_id).order_by(ActionPlan.created_at.desc()).all()
    return [{
        "plan_id": plan.plan_id, "title": plan.title, "status": plan.status,
        "created_at": plan.created_at,
        "actions": [{"action_id": action.action_id, "action_type": action.action_type, "monthly_amount": str(action.monthly_amount), "currency": action.currency, "rank": str(action.rank), "rationale": action.rationale, "impact": action.impact, "status": action.status} for action in plan.actions],
    } for plan in plans]


@router.post("/planning/plans", status_code=201)
def create_action_plan(
    payload: CreateActionPlanRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    action_payload = {"title": payload.title, "actions": [item.model_dump(mode="json") for item in payload.actions]}
    canonical = json.dumps(action_payload, sort_keys=True, separators=(",", ":"))
    expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    confirmation = db.query(Confirmation).filter(
        Confirmation.confirmation_id == payload.confirmation_id,
        Confirmation.user_id == current_user.user_id,
        Confirmation.action_type == "create_action_plan",
        Confirmation.status == "confirmed",
        Confirmation.consumed_at.is_(None),
    ).with_for_update().first()
    now = datetime.now(timezone.utc)
    if confirmation is None or confirmation.expires_at < now or confirmation.action_payload_hash != expected_hash:
        raise HTTPException(status_code=409, detail="A current payload-matched confirmation is required")
    ranked = rank_actions([CandidateAction(**item.model_dump()) for item in payload.actions])
    plan = ActionPlan(user_id=current_user.user_id, title=payload.title)
    db.add(plan)
    db.flush()
    for position, item in enumerate(ranked, start=1):
        db.add(PlannedAction(
            plan_id=plan.plan_id, action_type=item["action_type"],
            monthly_amount=Decimal(item["monthly_amount"]), rank=Decimal(item["score"]),
            rationale=item["rationale"], impact=item["impact"], status="planned",
        ))
    confirmation.consumed_at = now
    confirmation.status = "consumed"
    db.add(AuditEvent(user_id=current_user.user_id, event_type="action_plan_created", target_type="action_plan", target_id=str(plan.plan_id), outcome="success", metadata_json={"action_count": len(ranked), "planner_version": "planning-actions-v1"}))
    db.commit()
    db.refresh(plan)
    return {"plan_id": plan.plan_id, "title": plan.title, "status": plan.status, "action_count": len(ranked)}


@router.get("/financial-facts", response_model=list[FinancialFactResponse])
def list_financial_facts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return db.query(FinancialFact).filter(
        FinancialFact.user_id == current_user.user_id
    ).order_by(FinancialFact.created_at.desc()).all()


@router.post("/financial-facts", response_model=FinancialFactResponse, status_code=201)
def create_financial_fact_candidate(
    payload: CreateFinancialFactRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    fact = FinancialContextService(db, current_user.user_id).create_candidate(**payload.model_dump())
    db.commit()
    db.refresh(fact)
    return fact


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
    return {
        "conversation": ConversationResponse.model_validate(conversation),
        "messages": [
            {"message_id": row.message_id, "role": row.role, "content": row.content,
             "blocks": row.structured_content.get("blocks", []), "created_at": row.created_at}
            for row in sorted(conversation.messages, key=lambda item: item.created_at)
        ],
    }


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
def send_message(
    conversation_id: UUID,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    conversation = owned_conversation(db, conversation_id, current_user.user_id)
    user_message = ConversationMessage(
        message_id=uuid4(), conversation_id=conversation.conversation_id,
        role="user", content=payload.content, structured_content={},
    )
    db.add(user_message)
    freedom_inputs = (
        FreedomProjectionInputs(**payload.freedom_scenario.model_dump())
        if payload.freedom_scenario else None
    )
    answer = AgentOrchestrator(db, current_user.user_id).answer(
        payload.content, freedom_inputs, payload.user_selected_coverage_target
    )
    assistant_message = ConversationMessage(
        message_id=uuid4(), conversation_id=conversation.conversation_id,
        role="assistant", content=answer.narrative, structured_content={"blocks": answer.blocks},
        client_request_id=payload.client_request_id,
    )
    db.add(assistant_message)
    db.flush()
    run = audit_agent_run(db, current_user.user_id, assistant_message, answer)
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
