"""Unit & Integration tests for Multi-Channel Sales Cadence Automation.
Verifies real delivery logic for Email, WhatsApp, and LinkedIn touches.
Ensures zero mocked/faked progression.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, Tenant, APICredential
from app.models.enterprise import ApprovalRequest
from app.models.verticals import Lead
from app.models.deal_room import SalesOutboxItem
from app.services.sales.touch_dispatcher import (
    dispatch_sales_touch,
    send_whatsapp_with_status,
    dispatch_linkedin_touch,
    extract_lead_phone,
    extract_lead_linkedin_url,
)
from app.services.sales.outbox_service import SalesOutboxService
from app.services.sales_os.governance.suppression import SuppressionService
from app.core.security import encrypt_api_key


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create test tenant
    tenant = Tenant(id="test_tenant_cadence", name="Cadence Tenant")
    session.add(tenant)
    session.commit()

    yield session
    session.close()


def authorize_outbound(db_session):
    db_session.add(APICredential(
        tenant_id="test_tenant_cadence",
        provider="sales",
        encrypted_key=encrypt_api_key("test-sales-key"),
        settings={
            "sales_ai_auto_send_enabled": True,
            "outbound_permission_state": "granted",
            "whatsapp_permission_state": "granted",
            "whatsapp_opt_in": True,
        },
    ))
    db_session.commit()


def test_extract_phone_and_linkedin(db_session):
    lead = Lead(
        tenant_id="test_tenant_cadence",
        name="Sarah Connor",
        email="sarah@skynet.com",
        phone="+1 (555) 019-2834",
        company="Cyberdyne",
        data={
            "contact": {
                "linkedin_url": "https://www.linkedin.com/in/sarah-connor",
            }
        }
    )
    db_session.add(lead)
    db_session.commit()

    phone = extract_lead_phone(lead)
    assert phone == "15550192834"

    url = extract_lead_linkedin_url(lead)
    assert url == "https://www.linkedin.com/in/sarah-connor"


def test_whatsapp_dispatch_unconfigured(db_session):
    authorize_outbound(db_session)
    lead = Lead(
        tenant_id="test_tenant_cadence",
        name="Alex Smith",
        email="alex@example.com",
        phone="+1 555 123 4567",
        company="Acme Corp",
        data={
            "contact_status": "READY",
            "evidence_url": "https://example.com/news/acme",
            "evidence_quote": "Acme Corp announced a new customer support initiative.",
            "buying_signal": "Customer support initiative",
            "whatsapp_opt_in": True,
            "whatsapp_opt_in_source": "test_fixture",
            "whatsapp_opt_in_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    db_session.add(lead)
    db_session.commit()

    # Meta credentials NOT configured
    res = dispatch_sales_touch(
        db_session,
        "test_tenant_cadence",
        lead,
        channel="whatsapp",
        body="Hi Alex, brief follow up on partnership.",
    )

    assert res["sent"] is False
    assert res["channel"] == "whatsapp"
    assert res["reason"] == "meta_whatsapp_not_configured"
    assert "not configured" in res["message"].lower()


def test_whatsapp_only_lead_can_be_staged_in_durable_outbox(db_session):
    lead = Lead(
        tenant_id="test_tenant_cadence",
        name="Phone Only Prospect",
        phone="+1 555 010 2020",
        company="Phone First Co",
    )
    db_session.add(lead)
    db_session.commit()

    staged = SalesOutboxService(db_session, "test_tenant_cadence").stage_sequence(
        lead,
        [{
            "day": 1,
            "channel": "whatsapp",
            "content": "Hello, would a short conversation be useful this week?",
        }],
    )

    assert len(staged) == 1
    assert staged[0].channel == "whatsapp"
    assert staged[0].recipient_email == "15550102020"


def test_dispatcher_blocks_suppressed_email_before_provider_call(db_session):
    authorize_outbound(db_session)
    lead = Lead(
        tenant_id="test_tenant_cadence",
        name="Opted Out",
        email="opted-out@example.com",
        company="Suppressed Co",
        data={
            "contact_status": "READY",
            "evidence_url": "https://example.com/news/suppressed-co",
            "evidence_quote": "Suppressed Co announced a new service line.",
            "buying_signal": "New service line",
        },
    )
    db_session.add(lead)
    db_session.commit()
    SuppressionService(db_session, "test_tenant_cadence").add_suppression(
        "email", lead.email, reason="unsubscribe"
    )

    with patch("app.services.sales.touch_dispatcher.send_email_with_status") as send:
        result = dispatch_sales_touch(
            db_session,
            "test_tenant_cadence",
            lead,
            channel="email",
            subject="A relevant conversation",
            body="Hello, I wanted to share a relevant idea for your team.",
        )

    assert result["sent"] is False
    assert result["reason"] == "suppressed"
    send.assert_not_called()


def test_whatsapp_dispatch_with_mocked_meta_api(db_session):
    authorize_outbound(db_session)
    lead = Lead(
        tenant_id="test_tenant_cadence",
        name="Jane Doe",
        email="jane@acme.com",
        phone="+91 98765 43210",
        company="Acme Corp",
        data={
            "whatsapp_opt_in": True,
            "whatsapp_opt_in_source": "test_fixture",
            "whatsapp_opt_in_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    # Add Meta APICredential
    cred = APICredential(
        tenant_id="test_tenant_cadence",
        provider="meta",
        encrypted_key=encrypt_api_key("valid_meta_token_123"),
        settings={"phone_number_id": "phone_id_99999"}
    )
    db_session.add(lead)
    db_session.add(cred)
    db_session.commit()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"messages": [{"id": "wamid_HBgM12345678"}]}

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        res = dispatch_sales_touch(
            db_session,
            "test_tenant_cadence",
            lead,
            channel="whatsapp",
            body="Hello Jane, touching base regarding our offer.",
        )

        assert res["sent"] is True
        assert res["channel"] == "whatsapp"
        assert res["message_id"] == "wamid_HBgM12345678"
        assert mock_post.called
        call_kwargs = mock_post.call_args
        assert "phone_id_99999" in call_kwargs[0][0]


def test_linkedin_dispatch_stages_approval_request(db_session):
    lead = Lead(
        tenant_id="test_tenant_cadence",
        name="Michael Scott",
        email="mscott@dundermifflin.com",
        company="Dunder Mifflin",
        data={
            "contact": {
                "linkedin_url": "https://www.linkedin.com/in/michael-scott-boss",
            }
        }
    )
    db_session.add(lead)
    db_session.commit()

    res = dispatch_sales_touch(
        db_session,
        "test_tenant_cadence",
        lead,
        channel="linkedin",
        body="Hi Michael, would love to connect about paper supply chain AI.",
        step_number=2,
    )

    assert res["sent"] is False
    assert res["requires_action"] is True
    assert res["channel"] == "linkedin"
    assert res["linkedin_url"] == "https://www.linkedin.com/in/michael-scott-boss"
    assert "approval_id" in res

    # Verify ApprovalRequest in DB
    approval = db_session.query(ApprovalRequest).filter_by(id=res["approval_id"]).first()
    assert approval is not None
    assert approval.action_type == "linkedin_outreach"
    assert approval.payload["linkedin_url"] == "https://www.linkedin.com/in/michael-scott-boss"
    assert approval.status == "pending"


def test_outbox_drain_handles_multichannel_without_mocks(db_session):
    authorize_outbound(db_session)
    lead = Lead(
        id="lead_drain_1",
        tenant_id="test_tenant_cadence",
        name="Dwight Schrute",
        email="dwight@beetfarm.com",
        phone="+1 555 444 3333",
        company="Schrute Farms",
        data={
            "contact": {
                "linkedin_url": "https://www.linkedin.com/in/dwight-schrute",
            },
            "whatsapp_opt_in": True,
            "whatsapp_opt_in_source": "test_fixture",
            "whatsapp_opt_in_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    db_session.add(lead)
    db_session.commit()

    # Stage a WhatsApp touch and a LinkedIn touch in SalesOutboxItem
    now = datetime.now(timezone.utc)
    outbox_wa = SalesOutboxItem(
        id="outbox_wa_1",
        tenant_id="test_tenant_cadence",
        lead_id=lead.id,
        channel="whatsapp",
        recipient_email="dwight@beetfarm.com",
        subject=None,
        body="Dwight, following up via WhatsApp.",
        status="scheduled",
        scheduled_for=now,
    )
    outbox_li = SalesOutboxItem(
        id="outbox_li_1",
        tenant_id="test_tenant_cadence",
        lead_id=lead.id,
        channel="linkedin",
        recipient_email="dwight@beetfarm.com",
        subject=None,
        body="Dwight, let's connect on LinkedIn.",
        status="scheduled",
        scheduled_for=now,
    )
    db_session.add(outbox_wa)
    db_session.add(outbox_li)
    db_session.commit()

    outbox_svc = SalesOutboxService(db_session, "test_tenant_cadence")
    result = outbox_svc.drain_due_items(limit=10, max_jitter_sec=0)

    # WhatsApp without meta credentials should legitimately fail (not falsely mark sent/logged)
    db_session.refresh(outbox_wa)
    assert outbox_wa.status == "failed"
    assert "meta whatsapp api credentials" in outbox_wa.error_message.lower()

    # LinkedIn should be staged for operator review (status == pending_review)
    db_session.refresh(outbox_li)
    assert outbox_li.status == "pending_review"
    assert "human-in-the-loop" in outbox_li.error_message.lower()


def test_approved_linkedin_touch_is_not_reported_sent_without_execution_receipt(db_session):
    lead = Lead(
        tenant_id="test_tenant_cadence",
        name="Michael Scott",
        email="mscott@dundermifflin.com",
        company="Dunder Mifflin",
        data={"contact": {"linkedin_url": "https://www.linkedin.com/in/michael-scott-boss"}},
    )
    db_session.add(lead)
    db_session.flush()
    approval = ApprovalRequest(
        tenant_id="test_tenant_cadence",
        action_type="linkedin_outreach",
        channel="linkedin",
        resource_type="lead",
        resource_id=f"{lead.id}_step_2",
        title="Approved LinkedIn touch",
        payload={"lead_id": lead.id},
        status="approved",
    )
    db_session.add(approval)
    db_session.commit()

    result = dispatch_sales_touch(
        db_session,
        "test_tenant_cadence",
        lead,
        channel="linkedin",
        body="Hi Michael, would a short discussion be useful this week?",
        step_number=2,
    )
    assert result["sent"] is False
    assert result["requires_action"] is True
    assert result["reason"] == "approved_waiting_for_execution"


def test_dispatcher_blocks_email_when_tenant_authorization_is_not_configured(db_session):
    lead = Lead(
        tenant_id="test_tenant_cadence",
        name="Taylor Example",
        email="taylor@example.com",
        company="Example Co",
    )
    db_session.add(lead)
    db_session.commit()

    with patch("app.services.sales.touch_dispatcher.send_email_with_status") as send:
        result = dispatch_sales_touch(
            db_session,
            "test_tenant_cadence",
            lead,
            channel="email",
            subject="A relevant question",
            body="Hello Taylor, would a short discussion about your team's goals be useful?",
        )

    assert result["sent"] is False
    assert result["reason"] == "outbound_authorization_blocked"
    send.assert_not_called()


def test_explicit_contact_opt_out_overrides_stale_top_level_opt_in(db_session):
    authorize_outbound(db_session)
    lead = Lead(
        tenant_id="test_tenant_cadence",
        name="Taylor Example",
        phone="+1 555 010 9999",
        company="Example Co",
        data={
            "whatsapp_opt_in": True,
            "whatsapp_opt_in_source": "old_form",
            "whatsapp_opt_in_at": "2026-01-01T00:00:00Z",
            "contact": {
                "whatsapp_opt_in": False,
                "whatsapp_opt_in_source": "recipient_opt_out",
                "whatsapp_opt_in_at": "2026-10-25T00:00:00Z",
            },
        },
    )
    db_session.add(lead)
    db_session.commit()

    result = dispatch_sales_touch(
        db_session,
        "test_tenant_cadence",
        lead,
        channel="whatsapp",
        body="A follow-up message",
    )
    assert result["sent"] is False
    assert result["reason"] == "outbound_authorization_blocked"
    assert "recipient_whatsapp_opt_in_missing" in result["blockers"]


def test_dispatcher_blocks_authorized_email_without_prospect_evidence(db_session):
    authorize_outbound(db_session)
    lead = Lead(
        tenant_id="test_tenant_cadence",
        name="Taylor Example",
        email="taylor@example.com",
        company="Example Co",
        data={"contact_status": "READY"},
    )
    db_session.add(lead)
    db_session.commit()

    with patch("app.services.sales.touch_dispatcher.send_email_with_status") as send:
        result = dispatch_sales_touch(
            db_session,
            "test_tenant_cadence",
            lead,
            channel="email",
            subject="A relevant question",
            body="Hello Taylor, would a short discussion be useful?",
        )

    assert result["sent"] is False
    assert result["reason"] == "outbound_authorization_blocked"
    assert "source_url_missing_or_invalid" in result["blockers"]
    assert "need_evidence_missing" in result["blockers"]
    send.assert_not_called()
