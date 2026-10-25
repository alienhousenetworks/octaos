"""Tests for tenant-scoped Sales outbound authorization settings."""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.endpoints.leads import (
    generate_outreach,
    get_sales_settings,
    save_sales_settings,
    schedule_meeting,
    send_outreach_smart,
    update_whatsapp_opt_in,
    WhatsAppOptInRequest,
)
from app.models.base import Base, Tenant
from app.models.verticals import Lead


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Tenant(id="sales-settings-tenant", name="Sales Settings Tenant"))
    session.commit()
    yield session
    session.close()


def test_sales_settings_default_to_no_automatic_outbound(db_session):
    settings = get_sales_settings(db_session, "sales-settings-tenant", None)
    assert settings["sales_ai_auto_send_enabled"] is False
    assert settings["outbound_permission_state"] == "unknown"
    assert settings["whatsapp_permission_state"] == "unknown"


def test_sales_settings_persist_explicit_channel_authorization(db_session):
    result = save_sales_settings(
        {
            "reply_mode": "review_first",
            "sales_ai_auto_send_enabled": True,
            "outbound_permission_state": "granted",
            "whatsapp_permission_state": "granted",
        },
        db_session,
        "sales-settings-tenant",
        None,
    )
    assert result["status"] == "success"
    settings = get_sales_settings(db_session, "sales-settings-tenant", None)
    assert settings["sales_ai_auto_send_enabled"] is True
    assert settings["outbound_permission_state"] == "granted"
    assert settings["whatsapp_permission_state"] == "granted"


def test_sales_settings_reject_invalid_permission_state(db_session):
    with pytest.raises(HTTPException) as exc:
        save_sales_settings(
            {"outbound_permission_state": "sure"},
            db_session,
            "sales-settings-tenant",
            None,
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_generate_outreach_stores_draft_without_claiming_delivery(db_session, monkeypatch):
    lead = Lead(
        tenant_id="sales-settings-tenant",
        name="Taylor Example",
        email="taylor@example.com",
        company="Example Co",
        status="qualified",
        data={},
    )
    db_session.add(lead)
    db_session.commit()

    async def draft_only(self, lead_id, instructions=""):
        return "Hello Taylor, would a short discussion about your team's goals be useful?"

    monkeypatch.setattr("app.api.v1.endpoints.leads.SalesService.generate_outreach", draft_only)
    result = await generate_outreach(lead.id, db_session, "sales-settings-tenant")

    db_session.refresh(lead)
    assert result["status"] == "draft_ready"
    assert result["sent"] is False
    assert lead.status == "qualified"
    assert lead.data["outreach_draft"]["status"] == "draft"
    assert "outreach_sent_at" not in lead.data
    assert "conversation" not in lead.data


@pytest.mark.asyncio
async def test_schedule_meeting_does_not_invent_time_or_meet_link(db_session):
    lead = Lead(
        tenant_id="sales-settings-tenant",
        name="Taylor Example",
        email="taylor@example.com",
        company="Example Co",
        status="replied",
        data={"prospect_interested": True},
    )
    db_session.add(lead)
    db_session.commit()

    result = await schedule_meeting(
        lead_id=lead.id,
        payload=None,
        db=db_session,
        tenant_id="sales-settings-tenant",
    )
    db_session.refresh(lead)

    assert result["status"] == "needs_time_confirmation"
    assert result["booked"] is False
    assert lead.status == "replied"
    assert "meeting_link" not in (lead.data or {})


def test_whatsapp_consent_is_recipient_scoped_and_opt_out_suppresses(db_session):
    lead = Lead(
        tenant_id="sales-settings-tenant",
        name="Taylor Example",
        phone="+1 555 010 1000",
        company="Example Co",
        status="captured",
        data={},
    )
    db_session.add(lead)
    db_session.commit()

    opted_in = update_whatsapp_opt_in(
        lead.id,
        WhatsAppOptInRequest(opted_in=True, source="signed_consent_form"),
        db_session,
        "sales-settings-tenant",
    )
    db_session.refresh(lead)
    assert opted_in["opted_in"] is True
    assert lead.data["whatsapp_opt_in"] is True
    assert lead.data["whatsapp_opt_in_source"] == "signed_consent_form"
    assert lead.data["whatsapp_opt_in_at"]

    opted_out = update_whatsapp_opt_in(
        lead.id,
        WhatsAppOptInRequest(opted_in=False, source="recipient_opt_out", notes="Recipient requested no WhatsApp"),
        db_session,
        "sales-settings-tenant",
    )
    db_session.refresh(lead)
    assert opted_out["opted_in"] is False
    assert lead.data["whatsapp_opt_in"] is False

    from app.services.sales_os.governance.suppression import SuppressionService
    assert SuppressionService(db_session, "sales-settings-tenant").is_suppressed(
        phone=lead.phone, channel="whatsapp"
    )


def test_whatsapp_consent_cannot_override_existing_suppression(db_session):
    lead = Lead(
        tenant_id="sales-settings-tenant",
        name="Taylor Example",
        phone="+1 555 010 2000",
        company="Example Co",
        status="captured",
        data={},
    )
    db_session.add(lead)
    db_session.commit()

    update_whatsapp_opt_in(
        lead.id,
        WhatsAppOptInRequest(opted_in=False, source="recipient_opt_out"),
        db_session,
        "sales-settings-tenant",
    )
    with pytest.raises(HTTPException) as exc:
        update_whatsapp_opt_in(
            lead.id,
            WhatsAppOptInRequest(opted_in=True, source="signed_consent_form"),
            db_session,
            "sales-settings-tenant",
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_smart_outreach_endpoint_cannot_bypass_permission_gate(db_session):
    lead = Lead(
        tenant_id="sales-settings-tenant",
        name="Taylor Example",
        email="taylor@example.com",
        company="Example Co",
        status="qualified",
        data={
            "contact_status": "READY",
            "contact": {"name": "Taylor Example", "title": "VP Sales"},
            "evidence_url": "https://example.com/news/expansion",
            "evidence_quote": "Example Co announced a new regional sales team.",
            "buying_signal": "Regional expansion",
        },
    )
    db_session.add(lead)
    db_session.commit()

    result = await send_outreach_smart(
        lead_id=lead.id,
        payload={
            "subject": "A question about your expansion",
            "body": "Hi Taylor, I saw your expansion announcement and wanted to ask about your team's plans. Would a short discussion be useful?",
        },
        db=db_session,
        tenant_id="sales-settings-tenant",
    )
    db_session.refresh(lead)

    assert result["sent"] is False
    assert result["status"] == "blocked"
    assert "outbound_permission_not_granted" in result["blockers"]
    assert lead.status == "qualified"
    assert "outreach_sent_at" not in (lead.data or {})
