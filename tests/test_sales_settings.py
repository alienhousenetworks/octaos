"""Tests for tenant-scoped Sales outbound authorization settings."""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.endpoints.leads import get_sales_settings, save_sales_settings
from app.models.base import Base, Tenant


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
