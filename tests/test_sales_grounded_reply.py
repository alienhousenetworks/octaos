import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from app.models.base import Base, Tenant, User
from app.models.verticals import Lead, BusinessProfile
from app.models.deal_room import CompanySalesContext
from app.models.agents import KnowledgeDocument
from app.services.sales.reply_handler import SalesReplyHandler
from app.services.sales.meeting_booking import book_meeting_for_lead


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    tenant = Tenant(id=str(uuid.uuid4()), name="Test Sales Co", subdomain="test-sales")
    session.add(tenant)
    session.commit()

    yield session, tenant.id
    session.close()


@pytest.mark.asyncio
async def test_inbound_query_unanswered_in_kb_triggers_escalation(test_db):
    db, tenant_id = test_db

    # Create lead
    lead = Lead(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name="Sarah Connor",
        company="Cyberdyne Systems",
        email="sconnor@cyberdyne.com",
        status="contacted",
        data={"outbound_body": "Would you be interested in our autonomous sales platform?"}
    )
    db.add(lead)
    db.commit()

    handler = SalesReplyHandler(db, tenant_id)

    # Mock classification to simulate unverified technical query
    mock_classification = {
        "intent": "question",
        "interested": False,
        "requires_human_clarification": True,
        "unanswered_question": "Do you support on-premise air-gapped deployment for HIPAA?",
        "confidence": 0.2,
        "suggested_reply": ""
    }

    with patch.object(handler, "_classify_reply", new_callable=AsyncMock) as mock_cls, \
         patch("app.services.sales.reply_handler.send_sales_telegram") as mock_tg:
        mock_cls.return_value = mock_classification

        result = await handler.process_inbound(
            lead_id=lead.id,
            channel="email",
            content="Do you support on-premise air-gapped deployment for HIPAA?",
            subject="Question regarding security"
        )

        assert result["status"] == "awaiting_user_clarification"
        assert result["lead_id"] == lead.id
        
        # Verify lead state
        db.refresh(lead)
        assert lead.data.get("awaiting_user_clarification") is True
        assert "air-gapped" in lead.data.get("pending_question")
        assert mock_tg.called


@pytest.mark.asyncio
async def test_submit_human_clarification_sends_and_trains_kb(test_db):
    db, tenant_id = test_db

    lead = Lead(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name="John Doe",
        company="Acme Corp",
        email="john@acme.com",
        status="contacted",
        data={
            "awaiting_user_clarification": True,
            "pending_question": "What is your data retention policy for EU clients?",
        }
    )
    db.add(lead)
    db.commit()

    handler = SalesReplyHandler(db, tenant_id)

    with patch.object(handler, "send_sales_reply", new_callable=AsyncMock) as mock_send:
        result = await handler.submit_human_clarification(
            lead_id=lead.id,
            answer="We retain EU data for 30 days post-termination and support zero-retention on request.",
            channel="email",
            add_to_kb=True,
            kb_title="EU Data Retention Policy"
        )

        assert result["status"] == "success"
        assert result["added_to_kb"] is True
        assert mock_send.called

        # Verify lead is cleared of awaiting status
        db.refresh(lead)
        assert lead.data.get("awaiting_user_clarification") is False
        assert lead.data.get("pending_question") is None

        # Verify KnowledgeDocument was created
        doc = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.tenant_id == tenant_id,
            KnowledgeDocument.department == "Sales"
        ).first()
        assert doc is not None
        assert doc.metadata_json.get("title") == "EU Data Retention Policy"
        assert "30 days" in doc.content


def test_meeting_booking_generates_pre_meeting_brief(test_db):
    db, tenant_id = test_db

    import json
    from app.models.base import APICredential
    from app.core.security import encrypt_api_key

    cred = APICredential(
        tenant_id=tenant_id,
        provider="google_calendar",
        encrypted_key=encrypt_api_key(json.dumps({"token": "mock_token"})),
        settings={}
    )
    db.add(cred)

    lead = Lead(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name="Alex Mercer",
        company="Gentech Inc",
        email="alex@gentech.com",
        status="contacted",
        target_context="Struggling with outbound email deliverability",
        why="High fit B2B tech company with 200 employees",
        data={}
    )
    db.add(lead)
    db.commit()

    with patch("app.services.sales.meeting_booking.create_google_calendar_event") as mock_cal, \
         patch("app.services.sales.meeting_booking.send_sales_telegram"):
        mock_cal.return_value = ("https://meet.google.com/xyz-abc-def", datetime.now(timezone.utc))

        booked = book_meeting_for_lead(db, tenant_id, lead)
        assert booked is True

        db.refresh(lead)
        assert lead.status == "meeting_scheduled"
        brief = lead.data.get("pre_meeting_brief")
        assert brief is not None
        assert brief["account_name"] == "Gentech Inc"
        assert brief["prospect_name"] == "Alex Mercer"
        assert "deliverability" in brief["pain_points"]
        assert len(brief["recommended_agenda"]) >= 3


@pytest.mark.asyncio
async def test_pending_clarifications_endpoint_and_resolution(test_db):
    db, tenant_id = test_db

    lead = Lead(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name="Elena Fisher",
        company="Uncharted Labs",
        email="elena@uncharted.com",
        status="contacted",
        data={
            "awaiting_user_clarification": True,
            "pending_question": "Does the platform support custom webhook integrations?",
            "conversation": [{"direction": "inbound", "content": "Does the platform support custom webhook integrations?"}]
        }
    )
    db.add(lead)
    db.commit()

    from app.api.v1.endpoints.leads import get_pending_clarifications, clarify_and_reply, ClarifyReplyRequest

    # 1. Test GET pending clarifications
    pending = get_pending_clarifications(db=db, tenant_id=tenant_id)
    assert len(pending) == 1
    assert pending[0]["lead_id"] == lead.id
    assert pending[0]["name"] == "Elena Fisher"
    assert "webhook" in pending[0]["pending_question"]

    # 2. Test POST clarify-reply
    req = ClarifyReplyRequest(
        answer="Yes, full bidirectional webhook support with HMAC-SHA256 signatures is included.",
        channel="email",
        add_to_kb=True,
        kb_title="Custom Webhook Integrations"
    )

    with patch("app.services.sales.reply_handler.SalesReplyHandler.send_sales_reply", new_callable=AsyncMock) as mock_send:
        res = await clarify_and_reply(lead_id=lead.id, payload=req, db=db, tenant_id=tenant_id)
        assert res["status"] == "success"
        assert res["added_to_kb"] is True
        assert mock_send.called

    # 3. Verify lead is no longer in pending list
    pending_after = get_pending_clarifications(db=db, tenant_id=tenant_id)
    assert len(pending_after) == 0

    # 4. Verify KnowledgeDocument was created and searchable
    doc = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.tenant_id == tenant_id,
        KnowledgeDocument.department == "Sales"
    ).first()
    assert doc is not None
    assert doc.metadata_json.get("title") == "Custom Webhook Integrations"
    assert "HMAC-SHA256" in doc.content

