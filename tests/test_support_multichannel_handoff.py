import os
os.environ["TESTING"] = "1"

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone, timedelta

from app.models.base import Base, Tenant, APICredential, User
from app.models.agents import ActivityLog
from app.models.verticals import Ticket, TicketMessage, SupportCustomer, SupportCustomerIdentity, Lead
from app.services.agents.support import SupportAgent
from app.services.support_identity_service import SupportIdentityService
from app.core.security import encrypt_api_key

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_multichannel_handoff.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

test_tenant_id = "tenant-enterprise-support-999"


@pytest.fixture(scope="function")
def db():
    tables = [
        Tenant.__table__,
        APICredential.__table__,
        ActivityLog.__table__,
        Lead.__table__,
        SupportCustomer.__table__,
        SupportCustomerIdentity.__table__,
        Ticket.__table__,
        TicketMessage.__table__,
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    session = TestingSessionLocal()

    # Seed Tenant & API Credentials
    tenant = Tenant(id=test_tenant_id, name="Stripe Enterprise", subdomain="stripe", is_active=True)
    cred_meta = APICredential(
        tenant_id=test_tenant_id,
        provider="meta",
        encrypted_key=encrypt_api_key("meta_test_token"),
        settings={"phone_number_id": "phone_12345"},
    )
    cred_smtp = APICredential(
        tenant_id=test_tenant_id,
        provider="smtp",
        encrypted_key=encrypt_api_key("smtp_password"),
        settings={"smtp_server": "smtp.test.com", "smtp_port": 587, "smtp_username": "support@stripe.com"},
    )
    session.add_all([tenant, cred_meta, cred_smtp])
    session.commit()

    yield session
    session.close()
    Base.metadata.drop_all(bind=engine, tables=tables)


@pytest.mark.asyncio
@patch("app.core.celery_app.celery_app.send_task")
@patch("app.services.support_outbound_service.SupportOutboundService.send", new_callable=AsyncMock)
async def test_whatsapp_human_handoff(mock_outbound_send, mock_send_task, db):
    mock_outbound_send.return_value = {"status": "success", "message_id": "msg_ack"}
    agent = SupportAgent(db, test_tenant_id)

    # Customer sends /human on WhatsApp
    result = await agent.handle_incoming_message(
        channel="whatsapp",
        sender="+14155552671",
        content="/human I need help with an enterprise billing dispute",
    )

    assert result["status"] == "handoff_queued"
    assert result["owner_type"] == "pending_human"

    # Verify Ticket in DB
    ticket = db.query(Ticket).filter(Ticket.id == result["ticket_id"]).first()
    assert ticket is not None
    assert ticket.status == "pending_human"
    assert ticket.owner_type == "pending_human"
    assert ticket.mode == "human"
    assert ticket.handoff_generation == 1
    assert ticket.customer_contact == "+14155552671"

    # Verify Outbound Acknowledgment was sent to WhatsApp
    assert mock_outbound_send.called
    outbound_call = mock_outbound_send.call_args[1]
    assert outbound_call["channel"] == "whatsapp"
    assert "live support team" in outbound_call["content"]

    # Verify 5-Minute SLA task was queued with 300s countdown
    sla_task_calls = [c for c in mock_send_task.mock_calls if c[1] and c[1][0] == "check_human_handoff_timeout_task"]
    assert len(sla_task_calls) == 1
    assert sla_task_calls[0][2]["countdown"] == 300


@pytest.mark.asyncio
@patch("app.core.celery_app.celery_app.send_task")
@patch("app.services.support_outbound_service.SupportOutboundService.send", new_callable=AsyncMock)
async def test_email_human_handoff(mock_outbound_send, mock_send_task, db):
    mock_outbound_send.return_value = {"status": "success", "message_id": "msg_ack"}
    agent = SupportAgent(db, test_tenant_id)

    # Customer sends email requesting human agent
    result = await agent.handle_incoming_message(
        channel="email",
        sender="sarah@corp.com",
        content="Please connect me with a live representative immediately",
        subject="Urgent Escalation",
    )

    assert result["status"] == "handoff_queued"
    assert result["owner_type"] == "pending_human"

    ticket = db.query(Ticket).filter(Ticket.id == result["ticket_id"]).first()
    assert ticket.status == "pending_human"
    assert ticket.owner_type == "pending_human"
    assert ticket.customer_contact == "sarah@corp.com"

    # Verify email outbound acknowledgment
    assert mock_outbound_send.called
    outbound_call = mock_outbound_send.call_args[1]
    assert outbound_call["channel"] == "email"


@pytest.mark.asyncio
@patch("app.core.celery_app.celery_app.send_task")
async def test_human_ownership_suppresses_ai_replies(mock_send_task, db):
    agent = SupportAgent(db, test_tenant_id)

    # First message triggers handoff
    with patch("app.services.support_outbound_service.SupportOutboundService.send", new_callable=AsyncMock):
        h_res = await agent.handle_incoming_message(
            channel="whatsapp",
            sender="+14155559999",
            content="/human I need help",
        )
    ticket_id = h_res["ticket_id"]
    mock_send_task.reset_mock()

    # Second message arrives while ticket is pending human
    reply_res = await agent.handle_incoming_message(
        channel="whatsapp",
        sender="+14155559999",
        content="My account number is ACC-88219",
    )

    assert reply_res["status"] == "human_owned"
    # Auto-reply task MUST NOT be queued!
    auto_reply_calls = [c for c in mock_send_task.mock_calls if c[1] and c[1][0] == "auto_reply_task"]
    assert len(auto_reply_calls) == 0

    # Verify message was appended to transcript
    msgs = db.query(TicketMessage).filter(TicketMessage.ticket_id == ticket_id).all()
    contents = [m.content for m in msgs]
    assert "My account number is ACC-88219" in contents


@pytest.mark.asyncio
@patch("app.services.support_outbound_service.SupportOutboundService.send", new_callable=AsyncMock)
async def test_sla_5min_timeout_escalation(mock_outbound_send, db):
    mock_outbound_send.return_value = {"status": "success"}
    agent = SupportAgent(db, test_tenant_id)

    # Create ticket in pending_human state
    ticket = Ticket(
        tenant_id=test_tenant_id,
        subject="Test Ticket",
        description="Help needed",
        status="pending_human",
        owner_type="pending_human",
        mode="human",
        channel="whatsapp",
        customer_contact="+14155551122",
        handoff_generation=1,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # 5 minutes elapse without agent claim -> run timeout processor
    await agent.process_handoff_timeout(ticket.id, expected_generation=1)

    db.refresh(ticket)
    # Ticket must be escalated to high priority!
    assert ticket.status == "escalated"
    assert ticket.owner_type == "escalated"
    assert ticket.priority == "high"
    assert ticket.extra_data.get("escalation_reason") == "sla_5min_timeout_unclaimed"

    # Outbound fallback notification sent to customer
    assert mock_outbound_send.called
    outbound_call = mock_outbound_send.call_args[1]
    assert "priority support ticket" in outbound_call["content"].lower()


@pytest.mark.asyncio
@patch("app.services.support_outbound_service.SupportOutboundService.send", new_callable=AsyncMock)
async def test_agent_claim_cancels_timeout_escalation(mock_outbound_send, db):
    agent = SupportAgent(db, test_tenant_id)

    # Create ticket and simulate agent claiming it before 5 minutes
    ticket = Ticket(
        tenant_id=test_tenant_id,
        subject="Test Claim Ticket",
        description="Assistance",
        status="human_handling",
        owner_type="human_handling",
        mode="human",
        channel="whatsapp",
        customer_contact="+14155553344",
        claimed_by="agent-uuid-1",
        claimed_at=datetime.now(timezone.utc),
        handoff_generation=1,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Timeout job executes later
    await agent.process_handoff_timeout(ticket.id, expected_generation=1)

    db.refresh(ticket)
    # Status MUST remain human_handling, NOT overwritten to escalated!
    assert ticket.status == "human_handling"
    assert ticket.owner_type == "human_handling"
    assert ticket.claimed_by == "agent-uuid-1"
    assert not mock_outbound_send.called


def test_unified_identity_resolution(db):
    id_svc = SupportIdentityService(db, test_tenant_id)

    # 1. Customer contacts via WhatsApp
    c1 = id_svc.resolve_or_create_customer(
        channel="whatsapp",
        sender="+14155557788",
        name="Elena Rostova",
    )
    assert c1.id is not None
    assert c1.primary_phone == "+14155557788"

    # 2. Customer contacts via Email with matching email or enriched phone
    c2 = id_svc.resolve_or_create_customer(
        channel="email",
        sender="elena@rostova.com",
        phone="+14155557788",
    )
    # Must link to the same canonical customer!
    assert c2.id == c1.id
    assert c2.primary_email == "elena@rostova.com"

    # 3. Verify channel identities linked to this customer
    identities = db.query(SupportCustomerIdentity).filter(SupportCustomerIdentity.customer_id == c1.id).all()
    channels = [i.channel for i in identities]
    assert "whatsapp" in channels
    assert "email" in channels
