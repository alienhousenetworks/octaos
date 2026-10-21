"""Tests for OctaOS Omnichannel Connectors, Webhooks, and Governed MCP Adapter."""
import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.main import app
from app.api import deps
from app.models.base import Base, Tenant, APICredential
from app.models.verticals import Lead
from app.models.enterprise import OutcomeEvent
from app.services.security_service import SecretValidationService
from app.services.mcp_hub import mcp_hub
from app.services.mcp.execution.dispatcher import GovernedExecutionDispatcher
from app.services.mcp.connectors.base import ConnectorContext

TEST_SQLITE_URL = "sqlite:///:memory:"


@pytest.fixture
def test_setup():
    engine = create_engine(
        TEST_SQLITE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    tenant_id = f"test-tenant-{uuid.uuid4().hex[:6]}"
    tenant = Tenant(id=tenant_id, name="Connector Test Tenant")
    db.add(tenant)
    db.commit()

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[deps.get_db] = override_get_db
    mcp_hub.db_factory = TestingSession

    yield {"db": db, "tenant_id": tenant_id, "session_factory": TestingSession}

    app.dependency_overrides.clear()
    mcp_hub.db_factory = None
    db.close()


def test_secret_validation_rules():
    # SendGrid validation
    assert SecretValidationService.validate_api_key("sendgrid", "SG.mock_key_longer_than_fifteen_chars")
    assert not SecretValidationService.validate_api_key("sendgrid", "")

    # Twilio validation
    assert SecretValidationService.validate_api_key("twilio", "AC_mock_twilio_account_sid_valid")
    assert SecretValidationService.validate_api_key("twilio_sms", "SK_mock_twilio_api_key_valid")

    # Calendly, ZoomInfo, Google Forms, Zapier
    assert SecretValidationService.validate_api_key("calendly", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
    assert SecretValidationService.validate_api_key("zoominfo", "zi_enterprise_key_123")
    assert SecretValidationService.validate_api_key("google_forms", "webhook_secret_key")
    assert SecretValidationService.validate_api_key("zapier", "https://hooks.zapier.com/hooks/catch/123/abc")
    assert SecretValidationService.validate_api_key("landingi", "landingi_token_123")

    # Special markers
    assert SecretValidationService.validate_api_key("calendly", "webhook_active")
    assert SecretValidationService.validate_api_key("meta", "oauth_connected")


def test_mcp_hub_tool_discovery():
    tools = mcp_hub.discover_tools("marketing_integrations")
    tool_names = [t["name"] for t in tools]

    assert "mcp_sendgrid_send_campaign" in tool_names
    assert "mcp_calendly_get_slots" in tool_names
    assert "mcp_zoominfo_enrich" in tool_names
    assert "mcp_twilio_send_sms" in tool_names
    assert "mcp_zapier_emit_event" in tool_names
    assert "mcp_powerbi_push_kpis" in tool_names


@pytest.mark.asyncio
async def test_mcp_hub_tool_execution(test_setup):
    # Test ZoomInfo enrichment execution
    res = await mcp_hub.execute_tool("mcp_zoominfo_enrich", {"domain": "acme.corp"})
    assert res["status"] == "success"
    assert "company_name" in res["data"]
    assert res["data"]["domain"] == "acme.corp"

    # Test Calendly slots execution
    res_cal = await mcp_hub.execute_tool("mcp_calendly_get_slots", {})
    assert res_cal["status"] == "success"
    assert len(res_cal["events"]) > 0

    # Test SendGrid simulated delivery
    res_sg = await mcp_hub.execute_tool(
        "mcp_sendgrid_send_campaign",
        {"to_email": "prospect@example.com", "subject": "OctaOS Intro", "content": "Hello World"},
    )
    assert res_sg["status"] == "success"
    assert res_sg["result"]["status"] in ("delivered", "simulated")


@pytest.mark.asyncio
async def test_governed_mcp_marketing_adapter(test_setup):
    session_factory = test_setup["session_factory"]
    tenant_id = test_setup["tenant_id"]

    dispatcher = GovernedExecutionDispatcher(db_factory=session_factory)
    adapter = dispatcher.get_adapter("marketing")
    ctx = ConnectorContext(tenant_id=tenant_id, connector_slug="marketing")

    objects = await adapter.discover_objects(ctx)
    obj_names = [o.object_name for o in objects]

    assert "email_campaign" in obj_names
    assert "scheduled_meeting" in obj_names
    assert "firmographic_enrichment" in obj_names
    assert "telephony_sms" in obj_names
    assert "ipaas_webhook" in obj_names

    # Test invoking action via adapter
    act_res = await adapter.invoke_action(
        ctx,
        "zoominfo_enrich_lead",
        {"domain": "stripe.com"},
    )
    assert "company_name" in act_res


def test_webhook_ingress_calendly(test_setup):
    db = test_setup["db"]
    tenant_id = test_setup["tenant_id"]
    client = TestClient(app)
    email = "calendly_invitee@enterprise.com"

    # Pre-create lead
    lead = Lead(tenant_id=tenant_id, email=email, name="John Invitee", status="captured")
    db.add(lead)
    db.commit()

    payload = {
        "event": "invitee.created",
        "payload": {
            "email": email,
            "name": "John Invitee",
            "event": "https://api.calendly.com/scheduled_events/evt_123",
            "tracking": {"utm_source": "linkedin_ad", "utm_campaign": "q4_enterprise"},
        },
    }

    resp = client.post(f"/api/v1/integrations/webhooks/calendly/{tenant_id}", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processed"
    assert data["result"]["lead_updated"] is True

    # Verify Lead status was upgraded to meeting_scheduled
    db.refresh(lead)
    assert lead.status == "meeting_scheduled"

    # Verify OutcomeEvent was recorded for learning loop attribution
    outcome = (
        db.query(OutcomeEvent)
        .filter(OutcomeEvent.tenant_id == tenant_id, OutcomeEvent.outcome_type == "meeting_booked")
        .first()
    )
    assert outcome is not None
    assert outcome.value == 100.0


def test_webhook_ingress_google_forms(test_setup):
    db = test_setup["db"]
    tenant_id = test_setup["tenant_id"]
    client = TestClient(app)
    email = "googleforms_lead@company.org"

    payload = {
        "email": email,
        "Full Name": "Alice Researcher",
        "Company": "Acme Biotech",
        "message": "Interested in deploying agentic HR workflows",
        "utm_source": "google_search",
    }

    resp = client.post(f"/api/v1/integrations/webhooks/google_forms/{tenant_id}", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processed"
    assert data["result"]["status"] == "success"
    assert data["result"]["is_new"] is True

    # Verify Lead was created in DB
    created_lead = (
        db.query(Lead)
        .filter(Lead.tenant_id == tenant_id, Lead.email == email)
        .first()
    )
    assert created_lead is not None
    assert created_lead.name == "Alice Researcher"
    assert created_lead.company == "Acme Biotech"
    assert created_lead.source == "form_google_forms"


def test_webhook_ingress_landingi(test_setup):
    tenant_id = test_setup["tenant_id"]
    client = TestClient(app)
    email = "landingi_lead@startup.io"

    payload = {
        "email": email,
        "name": "Bob Builder",
        "company": "Startup Labs",
        "utm_campaign": "black_friday_growth",
    }

    resp = client.post(f"/api/v1/integrations/webhooks/landingi/{tenant_id}", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processed"
    assert data["result"]["source"] == "landingi"


def test_webhook_ingress_zapier(test_setup):
    tenant_id = test_setup["tenant_id"]
    client = TestClient(app)
    email = "zapier_inbound@partner.com"

    payload = {
        "action": "create_lead",
        "data": {
            "email": email,
            "name": "Zapier Partner",
            "company": "Automation Inc",
            "notes": "Incoming lead via multi-step Zapier zap",
        },
    }

    resp = client.post(f"/api/v1/integrations/webhooks/zapier/{tenant_id}", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processed"
    assert data["result"]["status"] == "created"


def test_webhook_challenge():
    client = TestClient(app)
    resp = client.get("/api/v1/integrations/webhooks/meta/test_tenant?hub.challenge=123456789")
    assert resp.status_code == 200
    assert resp.text == "123456789"
