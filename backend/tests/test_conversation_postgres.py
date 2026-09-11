"""Real PostgreSQL acceptance. Set ARTHA_TEST_DATABASE_URL to a disposable database only."""
import asyncio
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
import os
import secrets
from uuid import uuid4
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.main import app  # registers all ORM relationships
from app.models.user import User
from app.models.agent import Conversation, FinancialFact, CalculationRecord, ConversationMessage, ConversationRequest, ToolCall
from app.services.conversation_requests import process_conversation, reserve_request
from app.services.conversation_tools import ConversationToolExecutor
from app.services.conversation_agent import ConversationAgent
from app.core.config import Settings
from app.routers.agent_v1 import SendMessageRequest, owned_conversation

@pytest.fixture
def db():
    url = os.environ.get("ARTHA_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Disposable PostgreSQL URL not supplied")
    engine = create_engine(url)
    with Session(engine) as session:
        yield session
        session.rollback()
    engine.dispose()

@pytest.fixture
def records(db):
    user = User(user_id=uuid4())
    other = User(user_id=uuid4())
    db.add_all([user, other]); db.flush()
    conversation = Conversation(conversation_id=uuid4(), user_id=user.user_id, title="Synthetic conversation")
    db.add(conversation)
    for month, income, expenses in [(7, "70000", "30000"), (8, "80000", "50000")]:
        for kind, value in [("monthly_income", income), ("monthly_expenses", expenses)]:
            db.add(FinancialFact(user_id=user.user_id, fact_type=kind, value=Decimal(value), unit="INR", source_type="manual_record", verification_status="verified", period_kind="monthly", period_start=date(2026,month,1), observed_at=datetime(2026,9,1,tzinfo=timezone.utc), verified_at=datetime(2026,9,1,tzinfo=timezone.utc)))
    db.commit()
    return user, other, conversation

TEST_SECRET = secrets.token_hex(32)

async def connected():
    return False

def settings():
    return Settings(_env_file=None, environment="test", jwt_secret=TEST_SECRET, enable_external_model=False, enable_conversational_agent=True)

def process(db, user, conversation, payload):
    return asyncio.run(process_conversation(db, user.user_id, conversation, payload, settings(), connected))

def test_real_period_followups_and_idempotency(db, records):
    user, _, conversation = records
    first = SendMessageRequest(content="Show my cash flow for August 2026", client_request_id=uuid4())
    a = process(db,user,conversation,first)
    b = process(db,user,conversation,first)
    assert a == b
    assert db.query(ConversationMessage).filter_by(conversation_id=conversation.conversation_id).count() == 2
    second = process(db,user,conversation,SendMessageRequest(content="What about July?", client_request_id=uuid4()))
    block = next(b for b in second["blocks"] if b["type"] == "calculation")
    assert block["period_start"] == "2026-07-01"
    assert block["result"]["monthly_surplus"]["amount"] == "40000.00"
    assert db.query(CalculationRecord).filter_by(user_id=user.user_id).count() == 2
    assert db.query(ToolCall).count() >= 2
    with pytest.raises(HTTPException) as error:
        process(db,user,conversation,first.model_copy(update={"content": "my net worth"}))
    assert error.value.status_code == 409


def test_cross_user_isolation_and_missing_month(db, records):
    user, other, conversation = records
    with pytest.raises(HTTPException) as error:
        owned_conversation(db, conversation.conversation_id, other.user_id)
    assert error.value.status_code == 404
    agent = ConversationAgent(ConversationToolExecutor(db, other.user_id))
    answer, _, _ = asyncio.run(agent.answer("my cash flow for July 2026"))
    assert not any(b["type"] == "calculation" for b in answer.blocks)
    result = process(db,user,conversation,SendMessageRequest(content="my cash flow for June 2026", client_request_id=uuid4()))
    assert not any(b["type"] == "calculation" for b in result["blocks"])


def test_unverified_expenses_never_calculated(db, records):
    user, _, conversation = records
    fact = db.query(FinancialFact).filter_by(user_id=user.user_id, fact_type="monthly_expenses", period_start=date(2026,8,1)).one()
    fact.verification_status = "unverified"; db.commit()
    result = process(db,user,conversation,SendMessageRequest(content="my cash flow for August 2026", client_request_id=uuid4()))
    block = next(b for b in result["blocks"] if b["type"] == "missing_data")
    assert block["fields"] == ["monthly_expenses"]


def test_concurrent_reservation_blocks_duplicate(db, records):
    user, _, conversation = records
    payload = SendMessageRequest(content="my cash flow", client_request_id=uuid4())
    row, cached = reserve_request(db,user.user_id,conversation.conversation_id,payload,settings().jwt_secret)
    assert cached is None
    with Session(db.bind) as other_session:
        with pytest.raises(HTTPException) as error:
            reserve_request(other_session,user.user_id,conversation.conversation_id,payload,settings().jwt_secret)
        assert error.value.status_code == 409
    db.rollback()
    row = db.query(ConversationRequest).filter_by(request_id=row.request_id).one()
    row.updated_at = datetime.now(timezone.utc) - timedelta(minutes=2); db.commit()
    result = process(db,user,conversation,payload)
    assert result["message_id"]
    assert db.query(ConversationMessage).filter_by(conversation_id=conversation.conversation_id).count() == 2


def test_partial_results_are_atomic_and_replayable(db, records):
    user, _, conversation = records
    payload = SendMessageRequest(content="How am I doing financially?", client_request_id=uuid4())
    result = process(db,user,conversation,payload)
    assert any(b["type"] == "calculation" for b in result["blocks"])
    assert any(b["type"] == "missing_data" for b in result["blocks"])
    assert process(db,user,conversation,payload) == result


def test_runtime_erasure_is_owned_and_clears_cached_evidence(db, records):
    from app.services.conversation_requests import clear_owned_conversation_runtime
    user, other, conversation = records
    process(db,user,conversation,SendMessageRequest(content="my cash flow", client_request_id=uuid4()))
    with pytest.raises(HTTPException):
        clear_owned_conversation_runtime(db,other.user_id,conversation.conversation_id)
    clear_owned_conversation_runtime(db,user.user_id,conversation.conversation_id)
    db.commit()
    assert conversation.conversation_state == {}
    assert db.query(ConversationRequest).filter_by(conversation_id=conversation.conversation_id).count() == 0
    # This internal step intentionally does not claim to erase the conversation itself.
    assert db.query(ConversationMessage).filter_by(conversation_id=conversation.conversation_id).count() == 2


def test_simultaneous_same_request_has_one_result_set(db, records):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    user, _, conversation = records
    user_id, conversation_id = user.user_id, conversation.conversation_id
    payload = SendMessageRequest(content="my cash flow", client_request_id=uuid4())
    barrier = Barrier(2)
    def invoke():
        with Session(db.bind) as session:
            owned = owned_conversation(session, conversation_id, user_id)
            barrier.wait(timeout=5)
            try:
                return asyncio.run(process_conversation(session,user_id,owned,payload,settings(),connected))
            except HTTPException as exc:
                assert exc.status_code == 409
                return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: invoke(), range(2)))
    assert any(replies)
    db.expire_all()
    assert db.query(ConversationMessage).filter_by(conversation_id=conversation_id).count() == 2
    assert db.query(CalculationRecord).filter_by(user_id=user_id).count() == 1
