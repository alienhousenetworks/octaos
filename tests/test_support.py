import os
os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, AsyncMock
import uuid
from datetime import datetime, timedelta

from app.main import app
from app.api.deps import get_db, get_current_tenant_id, get_current_user
from app.models.base import Base, APICredential, Tenant, User
from app.models.verticals import Ticket, TicketMessage
from app.services.agents.support import SupportAgent

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_support.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

tenant_id_override_store = {"tenant_id": None}
test_user_id = str(uuid.uuid4())

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    def override_get_current_tenant_id():
        return tenant_id_override_store["tenant_id"] or "test-tenant-id"

    def override_get_current_user():
        tid = tenant_id_override_store["tenant_id"] or "test-tenant-id"
        u = db.query(User).filter(User.tenant_id == tid).first()
        if not u:
            u = User(
                id=test_user_id,
                tenant_id=tid,
                email="admin@example.com",
                name="Admin User",
                hashed_password="pw",
                role="admin",
                is_active=True,
                is_verified=True,
            )
            db.add(u)
            db.commit()
            db.refresh(u)
        return u
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant_id] = override_get_current_tenant_id
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()



@pytest.mark.asyncio
async def test_incoming_webhook_missing_credentials(client, db):
    tenant_id = "test-tenant"
    tenant_id_override_store["tenant_id"] = tenant_id
    from app.models.base import Tenant
    if not db.query(Tenant).filter(Tenant.id == tenant_id).first():
        db.add(Tenant(id=tenant_id, name="Test Tenant", is_active=True))
        db.commit()
    
    # Webhook should fail because Meta credentials are not configured
    response = client.post(
        "/api/v1/support/email/webhook/test-tenant",
        json={
            "sender": "customer@example.com",
            "subject": "Missing keys test",
            "content": "Please help"
        }
    )
    assert response.status_code == 400
    assert "SMTP/Email credentials" in response.json()["detail"]

@pytest.mark.asyncio
@patch("app.core.celery_app.celery_app.send_task")
async def test_auto_reply_queued(mock_send_task, client, db):
    tenant_id = "test-tenant"
    tenant_id_override_store["tenant_id"] = tenant_id
    from app.models.base import Tenant
    if not db.query(Tenant).filter(Tenant.id == tenant_id).first():
        db.add(Tenant(id=tenant_id, name="Test Tenant", is_active=True))
        db.commit()
    
    # Add dummy credentials
    from app.models.base import APICredential
    from app.core.security import encrypt_api_key
    cred_whatsapp = APICredential(tenant_id=tenant_id, provider="meta", encrypted_key=encrypt_api_key("token123"), settings={"phone_number_id": "123"})
    cred_smtp = APICredential(tenant_id=tenant_id, provider="smtp", encrypted_key=encrypt_api_key("token123"), settings={"smtp_server": "localhost", "smtp_port": 25, "smtp_username": "user"})
    db.add_all([cred_whatsapp, cred_smtp])
    db.commit()
    
    agent = SupportAgent(db, tenant_id)
    
    # Test WhatsApp auto reply queuing
    await agent.handle_incoming_message("whatsapp", "+1234567890", "hi")
    auto_reply_calls = [c for c in mock_send_task.mock_calls if c[1] and c[1][0] == "auto_reply_task"]
    assert len(auto_reply_calls) == 1
    args = auto_reply_calls[0][1]
    kwargs = auto_reply_calls[0][2]
    assert args[0] == "auto_reply_task"
    assert kwargs.get("countdown") == 270
        
    mock_send_task.reset_mock()
    
    # Test Email auto reply queuing
    await agent.handle_incoming_message("email", "customer@example.com", "hi", "subject")
    auto_reply_calls = [c for c in mock_send_task.mock_calls if c[1] and c[1][0] == "auto_reply_task"]
    assert len(auto_reply_calls) == 1
    args = auto_reply_calls[0][1]
    kwargs = auto_reply_calls[0][2]
    assert args[0] == "auto_reply_task"
    assert kwargs.get("countdown") == 1200

@pytest.mark.asyncio
@patch("app.services.llm_gateway.LLMGateway.complete")
async def test_collision_prevention_agent_replied(mock_complete, client, db):
    tenant_id = "test-tenant-id"
    tenant_id_override_store["tenant_id"] = tenant_id
    
    # Add dummy credentials
    from app.models.base import APICredential
    from app.core.security import encrypt_api_key
    cred_whatsapp = APICredential(tenant_id=tenant_id, provider="meta", encrypted_key=encrypt_api_key("token123"), settings={"phone_number_id": "123"})
    db.add(cred_whatsapp)
    db.commit()
    agent = SupportAgent(db, tenant_id)
    
    # Customer sends message -> Creates ticket and queues auto-reply
    res = await agent.handle_incoming_message("whatsapp", "+1234567890", "First customer message")
    ticket_id = res["ticket_id"]
    trigger_msg_id = res["message_id"]
    
    # Simulate an agent replying manually in the meantime with a later created_at timestamp
    manual_reply_msg = TicketMessage(
        ticket_id=ticket_id,
        sender="agent",
        content="I am a human assisting you.",
        created_at=datetime.utcnow() + timedelta(seconds=5)
    )
    db.add(manual_reply_msg)
    db.commit()
    
    # Now run the Celery auto reply task process manually
    # It should detect the agent message and abort without calling LLM
    mock_complete.return_value = "AI reply"
    
    await agent.process_auto_reply(ticket_id, trigger_msg_id, "whatsapp")
    
    # Verify no LLM response was generated/sent
    mock_complete.assert_not_called()
    
    # Check messages in db - only should have customer message + manual agent reply (total 2)
    messages = db.query(TicketMessage).filter(TicketMessage.ticket_id == ticket_id).all()
    assert len(messages) == 2
    assert messages[0].sender == "customer"
    assert messages[1].sender == "agent"
    assert messages[1].content == "I am a human assisting you."


@pytest.mark.asyncio
@patch("app.services.llm_gateway.LLMGateway.complete")
async def test_ai_draft_and_triage_endpoints(mock_complete, client, db):
    tenant_id = "test-tenant-copilot"
    tenant_id_override_store["tenant_id"] = tenant_id

    from app.models.base import Tenant
    if not db.query(Tenant).filter(Tenant.id == tenant_id).first():
        db.add(Tenant(id=tenant_id, name="Copilot Tenant", is_active=True))
        db.commit()

    ticket = Ticket(
        tenant_id=tenant_id,
        subject="Payment failed on renewal",
        description="My card was charged twice but account says expired",
        status="open",
        channel="widget",
        customer_name="Alice",
        customer_contact="alice@example.com",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    msg = TicketMessage(
        ticket_id=ticket.id,
        sender="customer",
        content="Please help resolve my payment issue ASAP!",
    )
    db.add(msg)
    db.commit()

    # 1. Test AI Draft
    mock_complete.return_value = "Hello Alice, I see your double charge inquiry. We have reversed the duplicate transaction."
    draft_res = client.post(f"/api/v1/support/tickets/{ticket.id}/ai-draft")
    assert draft_res.status_code == 200
    draft_data = draft_res.json()
    assert draft_data["status"] == "success"
    assert "reversed the duplicate" in draft_data["draft"]

    # 2. Test AI Triage
    mock_complete.return_value = '{"sentiment": "urgent", "urgency": "P1", "category": "Billing & Payments", "summary": "Customer charged twice on renewal", "suggested_action": "Check Stripe charge and refund"}'
    triage_res = client.post(f"/api/v1/support/tickets/{ticket.id}/ai-triage")
    assert triage_res.status_code == 200
    triage_data = triage_res.json()
    assert triage_data["status"] == "success"
    assert triage_data["ai_insights"]["urgency"] == "P1"
    assert triage_data["ai_insights"]["category"] == "Billing & Payments"

    # 3. Test ticket list includes unassigned tickets in default room
    from app.models.rooms import SectionRoom
    room = SectionRoom(
        tenant_id=tenant_id,
        section="support",
        name="Default Support Queue",
        slug="default",
    )
    db.add(room)
    db.commit()

    list_res = client.get("/api/v1/support/tickets?room_slug=default")
    assert list_res.status_code == 200
    tickets_list = list_res.json()
    assert len(tickets_list) >= 1
    assert any(t["id"] == ticket.id for t in tickets_list)
    found = next(t for t in tickets_list if t["id"] == ticket.id)
    assert found["extra_data"]["ai_insights"]["urgency"] == "P1"
