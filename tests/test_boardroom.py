import os
os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, AsyncMock
import uuid

from app.main import app
from app.api.deps import get_db, get_current_tenant_id
from app.models.base import Base
from app.models.verticals import Ticket, Lead, AgentMeeting
from app.services.agents.boardroom import BoardroomService

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_boardroom.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

tenant_id_override_store = {"tenant_id": None}

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
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant_id] = override_get_current_tenant_id
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.mark.asyncio
@patch("app.services.llm_gateway.LLMGateway.complete")
async def test_boardroom_inquiry_classification(mock_complete, db):
    mock_complete.return_value = '{"needs_meeting": true, "title": "Enterprise Sales Escalation", "participants": ["CEO AI", "Support AI", "Sales AI"], "reason": "Customer inquiry regarding bulk pricing"}'
    
    tenant_id = "test-tenant-id"
    service = BoardroomService(db, tenant_id)
    
    # Create ticket
    ticket = Ticket(
        tenant_id=tenant_id,
        subject="Enterprise Inquiry",
        description="We want to buy 500 licenses, please send pricing info.",
        status="open",
        channel="whatsapp",
        customer_contact="+123456789",
        approval_status="pending"
    )
    db.add(ticket)
    db.commit()
    
    res = await service.classify_ticket_inquiry(ticket.id)
    assert res["needs_meeting"] is True
    assert res["title"] == "Enterprise Sales Escalation"
    assert "Sales AI" in res["participants"]

@pytest.mark.asyncio
@patch("app.services.llm_gateway.LLMGateway.complete")
@patch("app.services.agents.support.SupportAgent.send_message", new_callable=AsyncMock)
async def test_run_meeting_and_execute_actions(mock_send_message, mock_complete, db):
    # Mock LLM complete returns for different agents in the turn loop
    # Turn 1: Support AI intro
    # Turn 2: Sales AI recommendation
    # Turn 3: CEO AI decision + actions
    mock_complete.side_effect = [
        "Hey everyone, we got a customer asking for pricing options.", # Support AI
        "I suggest we create a lead and notify them we are preparing a quote.", # Sales AI
        "[MESSAGE]\nI approve creating the sales lead. Support AI will notify the customer.\n[ACTIONS]\n[\n  {\"assigned_to\": \"Sales AI\", \"description\": \"Create a lead record in the database\"},\n  {\"assigned_to\": \"Support AI\", \"description\": \"Send escalation response to ticket customer\"}\n]" # CEO AI
    ]
    
    tenant_id = "test-tenant-id"
    service = BoardroomService(db, tenant_id)
    
    ticket = Ticket(
        tenant_id=tenant_id,
        subject="Enterprise pricing quote",
        description="Hello, can we purchase an enterprise package?",
        status="open",
        channel="email",
        customer_contact="prospect@company.com",
        approval_status="pending"
    )
    db.add(ticket)
    
    from app.models.base import APICredential
    from app.core.security import encrypt_api_key
    cred_smtp = APICredential(tenant_id=tenant_id, provider="smtp", encrypted_key=encrypt_api_key("smtp://user:pass@host:25"), settings={"smtp_server": "localhost", "smtp_port": 25, "smtp_username": "user"})
    db.add(cred_smtp)
    
    db.commit()
    
    classification = {
        "needs_meeting": True,
        "title": "Escalated Lead: prospect@company.com",
        "participants": ["CEO AI", "Support AI", "Sales AI"]
    }
    
    meeting = await service.create_meeting_from_ticket(ticket.id, classification)
    assert meeting is not None
    assert meeting.status == "active"
    
    # Run meeting
    await service.run_meeting(meeting.id)
    
    # Refresh meeting from DB
    db.refresh(meeting)
    assert meeting.status == "completed"
    assert len(meeting.transcript) == 4
    assert meeting.transcript[0]["phase"] == "Decision Understanding / Board Assembly"
    assert meeting.transcript[3]["sender"] == "CEO AI"
    
    # Verify execution of action items
    assert len(meeting.action_items) == 2
    assert meeting.action_items[0]["status"] == "completed"
    assert meeting.action_items[1]["status"] == "completed"
    
    # Verify that a lead was indeed created
    lead = db.query(Lead).filter(Lead.tenant_id == tenant_id).first()
    assert lead is not None
    assert lead.email == "prospect@company.com"
    assert lead.source == "support_ticket"

def test_dynamic_boardroom_assembly_selects_relevant_experts(db):
    service = BoardroomService(db, "test-tenant-id")

    profile = service.build_decision_profile(
        title="Evaluate healthcare AI expansion",
        context=(
            "We need to decide whether to launch a clinical workflow SaaS product. "
            "Use HubSpot pipeline data, GA4 acquisition metrics, privacy constraints, "
            "ROI, and hiring capacity as success inputs."
        ),
    )
    participants = service.assemble_boardroom(profile)

    assert profile["industry"] == "healthcare"
    assert "Finance Expert" in participants
    assert "Risk Expert" in participants
    assert "Healthcare Operations Expert" in participants
    assert "Sales Intelligence Expert" in participants
    assert "Marketing Intelligence Expert" in participants
    assert "Legal & Compliance Expert" in participants
    assert "Human Resources Expert" in participants
