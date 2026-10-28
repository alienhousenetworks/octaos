"""Automated Tests for OctaOS Universal AI Plugin & Gateway.
Verifies multi-protocol compatibility (Claude MCP, ChatGPT OpenAPI, Grok/DeepSeek Gateway),
polymorphic media quarantine, AI Employee delegation, and Instagram social publishing.
"""
from __future__ import annotations

import io
import json
import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from sqlalchemy.pool import StaticPool

import app.models.mcp
import app.models.verticals
import app.models.enterprise
import app.models.agents
from app.main import app as fastapi_app
from app.api import deps
from app.models.base import Base, Tenant, User
from app.services.mcp.auth.credentials import create_credential_with_grants
from app.services.media.storage import validate_and_quarantine_media
from app.services.mcp.server import mcp_server

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture
def test_setup():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    # Wire mcp_server to use test session
    orig_server_db = mcp_server.db_factory
    orig_disp_db = mcp_server.dispatcher.db_factory
    orig_mkt_db = mcp_server.dispatcher.get_adapter("marketing").db_factory

    mcp_server.db_factory = TestingSession
    mcp_server.dispatcher.db_factory = TestingSession
    mcp_server.dispatcher.get_adapter("marketing").db_factory = TestingSession

    tenant_id = f"test-tenant-{uuid.uuid4().hex[:6]}"
    tenant = Tenant(id=tenant_id, name="Universal AI Workforce Tenant", subdomain="workforce")
    db.add(tenant)
    db.commit()

    user = User(id=str(uuid.uuid4()), tenant_id=tenant_id, email="owner@workforce.com", hashed_password="pw")
    db.add(user)
    db.commit()

    # Create standard operator credential with universal access
    cred, raw_key = create_credential_with_grants(
        db=db,
        tenant_id=tenant_id,
        name="Frontier AI Model Gateway",
        user_id=user.id,
        client_type="generic",
        role="admin",
        grants=[
            {
                "connector_slug": "*",
                "object_name": "*",
                "allowed_actions": ["discover", "read", "query", "create", "update", "invoke"],
            }
        ],
    )

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    fastapi_app.dependency_overrides[deps.get_db] = override_get_db

    client = TestClient(fastapi_app)

    yield {
        "db": db,
        "client": client,
        "tenant": tenant,
        "user": user,
        "cred": cred,
        "raw_key": raw_key,
        "Session": TestingSession,
    }

    # Teardown
    mcp_server.db_factory = orig_server_db
    mcp_server.dispatcher.db_factory = orig_disp_db
    mcp_server.dispatcher.get_adapter("marketing").db_factory = orig_mkt_db
    fastapi_app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(bind=engine)


def test_ai_plugin_manifest(test_setup):
    """Verify ChatGPT Plugin Manifest is exposed at /.well-known/ai-plugin.json."""
    client = test_setup["client"]
    res = client.get("/.well-known/ai-plugin.json")
    assert res.status_code == 200
    data = res.json()
    assert data["schema_version"] == "v1"
    assert "OctaOS" in data["name_for_human"]
    assert data["auth"]["type"] == "user_http"
    assert "/api/v1/plugin/openapi.json" in data["api"]["url"]


def test_openapi_spec_generation(test_setup):
    """Verify dynamic OpenAPI 3.1 specification contains workforce tools."""
    client = test_setup["client"]
    raw_key = test_setup["raw_key"]

    res = client.get("/api/v1/plugin/openapi.json", headers={"Authorization": f"Bearer {raw_key}"})
    assert res.status_code == 200
    spec = res.json()
    assert spec["openapi"] == "3.1.0"
    paths = spec["paths"]

    # Verify our key AI Employee and Social capabilities exist in the OpenAPI paths
    assert "/api/v1/plugin/actions/octaos_delegate_ai_employee" in paths
    assert "/api/v1/plugin/actions/octaos_social_publish_post" in paths
    assert "/api/v1/plugin/actions/octaos_upload_media_or_document" in paths
    assert "/api/v1/plugin/actions/octaos_query_ai_workforce" in paths


def test_media_quarantine_validation():
    """Verify magic-byte inspection, size limits, and forbidden extensions."""
    # 1. Valid MP4 header (ftyp box)
    valid_mp4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42" + (b"\x00" * 50)
    ok, mime, err = validate_and_quarantine_media(valid_mp4, declared_mime="video/mp4", filename="video.mp4")
    assert ok is True
    assert mime == "video/mp4"

    # 2. Valid PNG header
    valid_png = b"\x89PNG\r\n\x1a\n" + (b"\x00" * 20)
    ok, mime, err = validate_and_quarantine_media(valid_png, declared_mime="image/png", filename="image.png")
    assert ok is True
    assert mime == "image/png"

    # 3. Forbidden executable extension rejected
    ok, mime, err = validate_and_quarantine_media(b"binary payload", filename="malicious.exe")
    assert ok is False
    assert "forbidden" in err.lower()

    # 4. Empty payload rejected
    ok, mime, err = validate_and_quarantine_media(b"")
    assert ok is False


def test_query_ai_workforce(test_setup):
    """Verify external model can query the active OctaOS AI Employee workforce."""
    client = test_setup["client"]
    raw_key = test_setup["raw_key"]

    res = client.post(
        "/api/v1/plugin/gateway/execute",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={
            "tool": "octaos_query_ai_workforce",
            "arguments": {},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "records" in data
    role_keys = [r["role_key"] for r in data["records"]]
    assert "marketing" in role_keys
    assert "sales" in role_keys
    assert "support" in role_keys


def test_delegate_ai_employee_marketing(test_setup):
    """Verify delegating a social media post to Marketing AI."""
    client = test_setup["client"]
    raw_key = test_setup["raw_key"]

    res = client.post(
        "/api/v1/plugin/gateway/execute",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={
            "tool": "octaos_delegate_ai_employee",
            "arguments": {
                "employee": "marketing",
                "task_type": "publish_social_content",
                "parameters": {
                    "platform": "instagram",
                    "caption_draft": "Announcing our breakthrough autonomous AI workforce! 🔥",
                    "post_mode": "draft",
                },
            },
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "Marketing" in data["employee"]
    assert "enhanced_caption" in data["result"]


def test_social_publish_post_instagram_flow(test_setup):
    """Verify octaos_social_publish_post accepts video payload and triggers publishing."""
    client = test_setup["client"]
    raw_key = test_setup["raw_key"]

    # Provide a base64 encoded mock MP4 header
    mock_mp4_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42" + (b"\x00" * 100)
    import base64
    b64_video = base64.b64encode(mock_mp4_bytes).decode("utf-8")

    res = client.post(
        "/api/v1/plugin/gateway/execute",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={
            "tool": "octaos_social_publish_post",
            "arguments": {
                "platform": "instagram",
                "content": "Check out our next-gen product in action! #AI #Innovation",
                "media_base64": b64_video,
                "media_type": "video",
                "auto_optimize_with_marketing_ai": True,
            },
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["platform"] == "instagram"
    assert "post_id" in data
    assert "media_url" in data
    # Note: Success or note depends on whether live Meta OAuth token is stored (gracefully reports status)
    assert "published_content" in data


def test_multipart_file_upload_gateway(test_setup):
    """Verify external systems can upload binary video/image files directly via multipart form."""
    client = test_setup["client"]
    raw_key = test_setup["raw_key"]

    mock_mp4_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42" + (b"\x00" * 100)
    file_obj = io.BytesIO(mock_mp4_bytes)

    res = client.post(
        "/api/v1/plugin/gateway/execute",
        headers={"Authorization": f"Bearer {raw_key}"},
        data={
            "tool": "octaos_social_publish_post",
            "platform": "instagram",
            "content": "Direct multipart upload test! 🎥",
            "auto_optimize_with_marketing_ai": "false",
        },
        files={
            "file": ("product_reel.mp4", file_obj, "video/mp4"),
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["platform"] == "instagram"
    assert "vid_" in data["media_url"]
    assert "post_id" in data


def test_unauthenticated_request_rejected(test_setup):
    """Verify gateway rejects unauthenticated requests with 401."""
    client = test_setup["client"]
    res = client.post(
        "/api/v1/plugin/gateway/execute",
        json={"tool": "octaos_query_ai_workforce", "arguments": {}},
    )
    assert res.status_code == 401


def test_collaboration_providers_accepts_workspace_login(test_setup):
    """The integrations screen calls this with the user session, not an MCP key."""
    from app.core.security import create_access_token

    setup = test_setup
    user = setup["user"]
    user.is_verified = True
    user.is_active = True
    setup["db"].commit()

    token = create_access_token(subject=user.id, tenant_id=user.tenant_id)
    client = setup["client"]
    logged_in = client.get(
        "/api/v1/plugin/collaboration/providers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logged_in.status_code == 200
    assert isinstance(logged_in.json(), list)

    with_mcp_key = client.get(
        "/api/v1/plugin/collaboration/providers",
        headers={"Authorization": f"Bearer {setup['raw_key']}"},
    )
    assert with_mcp_key.status_code == 200
    assert isinstance(with_mcp_key.json(), list)


def test_api_key_can_draft_outreach_without_sending(test_setup, monkeypatch):
    from app.models.verticals import Lead
    from app.services.verticals.sales import SalesService

    setup = test_setup
    lead = Lead(
        tenant_id=setup["tenant"].id,
        name="Harish Iyer",
        email="harish.iyer@interactiveavenues.com",
        company="Interactive Avenues",
        status="captured",
    )
    setup["db"].add(lead)
    setup["db"].commit()

    async def fake_outreach(self, lead_id, instructions=""):
        return "Hello Interactive Avenues.\nhttps://interactiveavenues.com"

    monkeypatch.setattr(SalesService, "generate_outreach", fake_outreach)
    res = setup["client"].post(
        f"/api/v1/leads/{lead.id}/outreach/draft",
        headers={"Authorization": f"Bearer {setup['raw_key']}"},
        json={"instructions": "Keep it specific"},
    )
    assert res.status_code == 200
    assert res.json()["body"] == "Hello Interactive Avenues.\nhttps://interactiveavenues.com"
    setup["db"].expire_all()
    saved = setup["db"].query(Lead).filter(Lead.id == lead.id).one()
    assert saved.data["draft_body"]
    assert saved.status == "captured"


@pytest.mark.asyncio
async def test_sales_delegate_does_not_invent_a_placeholder_lead(test_setup, monkeypatch):
    """A sales job uses a real CRM lead and drafts. It must not insert lead@example.com."""
    from app.models.verticals import Lead
    from app.services.sales.discovery_service import DiscoveryService
    from app.services.verticals.sales import SalesService

    setup = test_setup
    lead = Lead(
        tenant_id=setup["tenant"].id,
        name="Business Development",
        email="info@webenza.com",
        company="Webenza",
        status="captured",
        data={"tags": ["AHN ICP"]},
    )
    setup["db"].add(lead)
    setup["db"].commit()

    async def fake_outreach(self, lead_id, instructions=""):
        return "Hello Webenza.\nhttps://webenza.com"

    async def fail_research(self, params):
        raise AssertionError("web research should not run when a real lead is already on file")

    monkeypatch.setattr(SalesService, "generate_outreach", fake_outreach)
    monkeypatch.setattr(DiscoveryService, "generate_leads", fail_research)

    res = setup["client"].post(
        "/api/v1/plugin/workforce/delegate",
        headers={"Authorization": f"Bearer {setup['raw_key']}"},
        json={"employee": "sales", "task_type": "outreach_draft", "parameters": {}, "instructions": "Draft the AHN ICP emails"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["result"]["sent"] is False
    assert body["result"]["drafted_count"] == 1
    assert body["result"]["created_count"] == 0

    setup["db"].expire_all()
    emails = [row.email for row in setup["db"].query(Lead).all()]
    assert "lead@example.com" not in emails
    saved = setup["db"].query(Lead).filter(Lead.email == "info@webenza.com").one()
    assert "webenza.com" not in saved.data["draft_body"]


def test_api_key_can_read_mail_status_and_is_blocked_from_sending_without_a_mailbox(test_setup):
    setup = test_setup
    headers = {"Authorization": f"Bearer {setup['raw_key']}"}
    status_res = setup["client"].get("/api/v1/unified-mail/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["configured"] is False

    send_res = setup["client"].post(
        "/api/v1/unified-mail/send",
        headers=headers,
        json={"to_email": "info@webenza.com", "subject": "Hello", "body": "Draft only."},
    )
    assert send_res.status_code == 502
    assert send_res.json()["detail"]
    assert "sent" not in send_res.json() or send_res.json().get("sent") is not True


def test_read_only_api_key_cannot_send_mail(test_setup):
    from app.services.mcp.auth.credentials import create_credential_with_grants

    setup = test_setup
    _cred, raw_key = create_credential_with_grants(
        db=setup["db"],
        tenant_id=setup["tenant"].id,
        name="Read only",
        user_id=setup["user"].id,
        role="read_only",
    )
    res = setup["client"].post(
        "/api/v1/unified-mail/send",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={"to_email": "info@webenza.com", "subject": "Hello", "body": "Do not send."},
    )
    assert res.status_code == 403
