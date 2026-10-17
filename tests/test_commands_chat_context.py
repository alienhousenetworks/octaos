import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, AsyncMock
import json
import uuid

from app.main import app
from app.models.base import Base, APICredential, User
from app.models.verticals import Candidate, Lead
from app.api.deps import get_db, get_current_tenant_id, get_current_user
from app.core.security import encrypt_api_key
from app.services.agents.intent_router import IntentRouter
from app.services.agents.orchestrator import OrchestratorAgent

import os

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_ctx.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

tenant_id_store = {"tenant_id": "test-tenant-ctx"}

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test_ctx.db"):
        try:
            os.remove("./test_ctx.db")
        except OSError:
            pass

@pytest.fixture(scope="function")
def test_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_current_tenant_id():
        return tenant_id_store["tenant_id"]

    def override_get_current_user():
        return User(
            id="test-user-id",
            email="test@example.com",
            name="Test User",
            tenant_id=tenant_id_store["tenant_id"],
            role="admin",
            is_verified=True,
            is_active=True,
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant_id] = override_get_current_tenant_id
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.services.llm_gateway.LLMGateway.complete")
async def test_commands_chat_context_single_turn_backward_compatibility(mock_complete, test_client, db_session):
    """Verifies that standard single-turn commands without messages continue to work unchanged."""
    tenant = tenant_id_store["tenant_id"]
    cred = APICredential(tenant_id=tenant, provider="anthropic", encrypted_key=encrypt_api_key("sk-ant-test"))
    db_session.add(cred)
    db_session.commit()

    mock_complete.return_value = json.dumps({
        "message": "I can help you source candidates.",
        "tasks": []
    })

    resp = test_client.post(
        "/api/v1/commands/execute",
        json={"prompt": "Find a Senior Engineer"}
    )
    if resp.status_code != 200:
        raise RuntimeError(f"STATUS {resp.status_code}: {resp.text}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["message"] == "I can help you source candidates."
    
    # Verify mock was called
    assert mock_complete.called
    kwargs = mock_complete.call_args.kwargs
    assert kwargs["prompt"] == "Find a Senior Engineer"


@pytest.mark.asyncio
@patch("app.services.llm_gateway.LLMGateway.complete")
async def test_commands_chat_context_multi_turn_history(mock_complete, test_client, db_session):
    """Verifies that multi-turn previous messages are sent and injected into the Orchestrator prompt."""
    tenant = tenant_id_store["tenant_id"]
    cred = APICredential(tenant_id=tenant, provider="anthropic", encrypted_key=encrypt_api_key("sk-ant-test"))
    db_session.add(cred)
    db_session.commit()

    # Turn 1 context
    turn1_user = "in hr how many resumes are ther can give me best fit for sales one tech saas"
    turn1_assistant = "I found 0 resumes in your database. However, I can help you source candidates for a Sales role in tech SaaS. To do this, please clarify experience and candidate count."

    # Turn 2 context
    turn2_user = "give me the one actually I am not sure with the exeorince it is a tech saas"
    turn2_assistant = "Got it! I will look for 1 Sales professional for a tech SaaS business."

    mock_complete.return_value = json.dumps({
        "message": "Understood! Sourcing 1 tech SaaS sales representative (candidate, not lead).",
        "tasks": []
    })

    # User sends Turn 3 with previous conversation history
    payload = {
        "prompt": "not lead sales person",
        "messages": [
            {"role": "user", "content": turn1_user},
            {"role": "assistant", "content": turn1_assistant},
            {"role": "user", "content": turn2_user},
            {"role": "assistant", "content": turn2_assistant},
        ]
    }

    resp = test_client.post("/api/v1/commands/execute", json=payload)
    assert resp.status_code == 200

    # Verify that the LLM gateway prompt contained the previous conversation history
    call_kwargs = mock_complete.call_args.kwargs
    prompt_sent = call_kwargs.get("prompt", "")
    assert "Previous Conversation History:" in prompt_sent
    assert f"User: {turn1_user}" in prompt_sent
    assert f"Orchestrator AI: {turn1_assistant}" in prompt_sent
    assert f"User: {turn2_user}" in prompt_sent
    assert f"Orchestrator AI: {turn2_assistant}" in prompt_sent
    assert "Current User Request:\nnot lead sales person" in prompt_sent

    # Verify system prompt mentions maintaining multi-turn context
    sys_prompt = call_kwargs.get("system_prompt", "")
    assert "Multi-turn conversation context" in sys_prompt


@pytest.mark.asyncio
@patch("app.services.llm_gateway.LLMGateway.complete")
async def test_orchestrator_operational_snapshot_grounding(mock_complete, test_client, db_session):
    """Verifies that live candidate counts in the DB are injected into the Orchestrator system prompt."""
    tenant = tenant_id_store["tenant_id"]
    cred = APICredential(tenant_id=tenant, provider="anthropic", encrypted_key=encrypt_api_key("sk-ant-test"))
    db_session.add(cred)

    # Seed 3 real candidates in DB
    for i in range(3):
        cand = Candidate(
            id=f"cand-{i}",
            tenant_id=tenant,
            name=f"Candidate {i}",
            email=f"cand{i}@example.com",
            role="Sales Rep",
            scorecard={"match_score": 85},
            status="sourced"
        )
        db_session.add(cand)
    db_session.commit()

    mock_complete.return_value = json.dumps({
        "message": "You currently have 3 candidate resumes on file.",
        "tasks": []
    })

    resp = test_client.post(
        "/api/v1/commands/execute",
        json={"prompt": "in hr how many resumes are ther"}
    )
    assert resp.status_code == 200

    # Verify system prompt has live candidate count
    call_kwargs = mock_complete.call_args.kwargs
    sys_prompt = call_kwargs.get("system_prompt", "")
    assert "3 Candidate(s)/Resume(s) currently on file" in sys_prompt


def test_intent_router_context_awareness():
    """Verifies IntentRouter uses recent messages for ambiguous follow-up prompts."""
    # When no history is given, ambiguous statement defaults to execution
    mode_alone, conf_alone = IntentRouter.classify("show me more breakdown")
    assert mode_alone == "analytics"

    # A short follow-up like "not lead sales person" with prior execution stays execution
    history_exec = [
        {"role": "user", "content": "source candidates for our tech saas"},
        {"role": "assistant", "content": "How many candidates do you need?"}
    ]
    mode_exec, _ = IntentRouter.classify("not lead sales person", messages=history_exec)
    assert mode_exec == "execution"

    # A short follow-up like "and what about last month" with prior analytics stays analytics
    history_analytics = [
        {"role": "user", "content": "give me a report on our churn rate"},
        {"role": "assistant", "content": "Here is the churn report..."}
    ]
    mode_ana, _ = IntentRouter.classify("and what about last month", messages=history_analytics)
    assert mode_ana == "analytics"
