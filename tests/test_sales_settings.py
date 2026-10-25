"""Tests for tenant-scoped Sales outbound authorization settings."""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.endpoints.leads import generate_outreach, get_sales_settings, save_sales_settings
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
