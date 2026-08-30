"""Typed, authenticated API for the financial-freedom agent."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth.manager import get_current_active_user
from app.core.config import get_db
from app.models.agent import AuditEvent, Confirmation, Conversation, ConversationMessage, ProactiveReview
from app.models.user import User
from app.services.agent_orchestrator import AgentOrchestrator, audit_agent_run

router = APIRouter()


class CreateConversationRequest(BaseModel):
    title: str = Field(default="Financial freedom conversation", min_length=1, max_length=160)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    conversation_id: UUID
    title: str
    status: str
    created_at: datetime


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


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
    created_at: datetime


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
    answer = AgentOrchestrator(db, current_user.user_id).answer(payload.content)
    assistant_message = ConversationMessage(
        message_id=uuid4(), conversation_id=conversation.conversation_id,
        role="assistant", content=answer.narrative, structured_content={"blocks": answer.blocks},
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
