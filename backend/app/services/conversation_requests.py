"""Request reservation, serialized conversation state, and atomic evidence commits."""
from datetime import datetime, timezone
import hashlib
import hmac
import json
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from app.models.agent import Conversation, ConversationRequest, ConversationMessage, ToolCall, AuditEvent
from app.services.agent_orchestrator import audit_agent_run
from app.services.conversation_contracts import VERSION
from app.services.conversation_tools import ConversationToolExecutor
from app.services.agent_policy import TOOL_REGISTRY
from app.services.conversation_agent import ConversationAgent
from app.core.conversation_gateway import OpenAIConversationGateway

GATEWAY_FACTORY = OpenAIConversationGateway

def reserve_request(db, user_id, conversation_id, payload, secret):
    owned = db.query(Conversation).filter_by(user_id=user_id, conversation_id=conversation_id).first()
    if owned is None:
        raise HTTPException(404, "Conversation not found")
    client_id = payload.client_request_id or uuid4()
    # Keyed digest prevents simple offline guessing of financial message contents.
    digest = hmac.new(secret.encode(), json.dumps(payload.model_dump(mode="json", exclude={"client_request_id", "cloud_assistance"}), sort_keys=True).encode(), hashlib.sha256).hexdigest()
    def query():
        return db.query(ConversationRequest).filter_by(user_id=user_id, conversation_id=conversation_id, client_request_id=client_id)
    row = query().first()
    created = False
    if row is None:
        if db.query(ConversationMessage).filter_by(conversation_id=conversation_id, client_request_id=client_id).first() is not None:
            raise HTTPException(409, "This request predates conversational mode; use a new request ID")
        row = ConversationRequest(request_id=uuid4(), user_id=user_id, conversation_id=conversation_id, client_request_id=client_id, payload_hash=digest, status="pending")
        db.add(row)
        try:
            db.commit()
            created = True
        except IntegrityError:
            db.rollback()
            row = query().first()
    if row is None or not hmac.compare_digest(row.payload_hash, digest):
        raise HTTPException(409, "Request ID was already used for a different payload")
    if row.status == "complete":
        return row, row.response
    age = (datetime.now(timezone.utc) - (row.updated_at.replace(tzinfo=timezone.utc) if row.updated_at.tzinfo is None else row.updated_at.astimezone(timezone.utc))).total_seconds()
    if not created and row.status == "pending" and age < 45:
        raise HTTPException(409, "Request is in progress; retry with the same request ID", headers={"Retry-After": "2"})
    try:
        db.query(Conversation).filter_by(conversation_id=conversation_id, user_id=user_id).populate_existing().with_for_update(nowait=True).one()
        row = query().populate_existing().with_for_update(nowait=True).one()
    except OperationalError:
        db.rollback()
        raise HTTPException(409, "Conversation is busy; retry with the same request ID", headers={"Retry-After": "2"}) from None
    if row.status == "complete":
        return row, row.response
    row.status, row.updated_at = "pending", datetime.now(timezone.utc)
    return row, None

async def process_conversation(db, user_id, conversation, payload, settings, disconnected, *, freedom_inputs=None, assumption_metadata=None):
    row, cached = reserve_request(db, user_id, conversation.conversation_id, payload, settings.jwt_secret or "")
    if cached is not None:
        return cached
    try:
        if db.bind.dialect.name == "postgresql":
            db.execute(text("SET LOCAL statement_timeout = '2000ms'"))
            db.execute(text("SET LOCAL lock_timeout = '1000ms'"))
        executor = ConversationToolExecutor(db, user_id, freedom_inputs=freedom_inputs, assumption_metadata=assumption_metadata, coverage_target=payload.user_selected_coverage_target)
        gateway = GATEWAY_FACTORY(settings.openai_api_key, settings.conversational_model) if settings.automatic_model_enabled else None
        agent = ConversationAgent(executor, gateway, max_rounds=settings.conversation_max_rounds, max_tools=settings.conversation_max_tools, timeout=settings.conversation_timeout_seconds)
        answer, state, used = await agent.answer(payload.content, conversation.conversation_state, disconnected=disconnected)
        db.add(ConversationMessage(message_id=uuid4(), conversation_id=conversation.conversation_id, role="user", content=payload.content, structured_content={}))
        message = ConversationMessage(message_id=uuid4(), conversation_id=conversation.conversation_id, role="assistant", content=answer.narrative, structured_content={"blocks": answer.blocks}, client_request_id=row.client_request_id)
        db.add(message)
        db.flush()
        run = audit_agent_run(db, user_id, message, answer, model_used=used)
        for request, result in executor.calls:
            db.add(ToolCall(run_id=run.run_id, tool_name=request.name, tool_version=TOOL_REGISTRY[request.name].version if request.name in TOOL_REGISTRY else "education-2026-09-11",
                sanitized_input_hash=hashlib.sha256(request.model_dump_json().encode()).hexdigest(), outcome=result.status,
                result_reference=next((b["calculation_id"] for b in result.blocks if b["type"] == "calculation"), result.reference)))
        for request in executor.failures:
            db.add(ToolCall(run_id=run.run_id, tool_name=request.name,
                tool_version=TOOL_REGISTRY[request.name].version if request.name in TOOL_REGISTRY else "education-2026-09-11",
                sanitized_input_hash=hashlib.sha256(request.model_dump_json().encode()).hexdigest(),
                outcome="unavailable", result_reference=None))
        db.add(AuditEvent(user_id=user_id, event_type="conversation_execution", target_type="agent_run", target_id=str(run.run_id), outcome="fallback" if agent.metrics["fallback"] else "success", metadata_json={"version": VERSION, **agent.metrics}))
        conversation.conversation_state = state.model_dump(mode="json")
        response = {"message_id": str(message.message_id), "run_id": str(run.run_id), "role": "assistant", "content": answer.narrative, "blocks": answer.blocks, "model_used": used, "created_at": (message.created_at or datetime.now(timezone.utc)).isoformat()}
        row.response, row.status, row.updated_at = response, "complete", datetime.now(timezone.utc)
        db.commit()
        return response
    except BaseException:
        db.rollback()
        # Reservation remains pending for bounded lease recovery; no tool results committed.
        raise


def clear_owned_conversation_runtime(db, user_id, conversation_id):
    """Internal rights-workflow step, not a claim of complete account erasure."""
    conversation = db.query(Conversation).filter_by(user_id=user_id, conversation_id=conversation_id).with_for_update().first()
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    db.query(ConversationRequest).filter_by(user_id=user_id, conversation_id=conversation_id).delete(synchronize_session=False)
    conversation.conversation_state = {}
    db.add(AuditEvent(user_id=user_id, event_type="conversation_runtime_cleared", target_type="conversation", target_id=str(conversation_id), outcome="success", metadata_json={"version": VERSION}))
