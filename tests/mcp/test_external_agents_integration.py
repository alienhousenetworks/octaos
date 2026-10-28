"""Comprehensive automated test suite for OctaOS Bidirectional External Agent Integration.
Verifies:
1. Universal Media & Safe File Quarantine (any safe format: audio, video, SVG, XLSX, PDF; blocking executables).
2. Strict Schema Validation & Placeholder Prevention (rejecting empty {} and dummy contacts).
3. Auth Unification (octa_mcp_... keys working transparently across product routes without 401 session expired).
4. Inbound Controller Replies & Activity Feed (correlation, attachments, and status updates).
5. Outbound Webhook Dispatcher, HMAC-SHA256 Signatures, and SSRF Protection.
6. Dashboard Agent Tool (external_agent.send_command).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

import app.models.external_agents
import app.models.mcp
import app.models.verticals
from app.api import deps
from app.main import app as fastapi_app
from app.models.base import Base, Tenant, User
from app.models.external_agents import (
    ActivityEvent,
    ControllerCommand,
    ExternalAgentConnection,
    WebhookSubscription,
)
from app.services.agents.tools import tool_registry, validate_outbound_url, SSRFProtectionError
from app.services.mcp.auth.credentials import create_credential_with_grants
from app.services.mcp.server import mcp_server
from app.services.media.storage import (
    validate_and_quarantine_media,
    store_media_bytes,
    get_media_asset,
    read_media_asset_bytes,
)
from app.services.webhooks.dispatcher import (
    generate_envelope,
    sign_webhook_headers,
    deliver_webhook,
    enqueue_webhook_event,
)

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture
def integration_env():
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
    orig_octaos_db = mcp_server.dispatcher.get_adapter("octaos").db_factory

    mcp_server.db_factory = TestingSession
    mcp_server.dispatcher.db_factory = TestingSession
    mcp_server.dispatcher.get_adapter("marketing").db_factory = TestingSession
    mcp_server.dispatcher.get_adapter("octaos").db_factory = TestingSession

    tenant_id = f"test-tenant-{uuid.uuid4().hex[:6]}"
    tenant = Tenant(id=tenant_id, name="External Agent Integration Test Tenant", subdomain="ext-agent")
    db.add(tenant)
    db.commit()

    user = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        email="controller_admin@octaos.io",
        hashed_password="pw",
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()

    cred, raw_mcp_key = create_credential_with_grants(
        db=db,
        tenant_id=tenant_id,
        name="External Controller Key",
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
        "tenant_id": tenant_id,
        "user": user,
        "mcp_key": raw_mcp_key,
        "TestingSession": TestingSession,
    }

    # Teardown
    mcp_server.db_factory = orig_server_db
    mcp_server.dispatcher.db_factory = orig_disp_db
    mcp_server.dispatcher.get_adapter("marketing").db_factory = orig_mkt_db
    mcp_server.dispatcher.get_adapter("octaos").db_factory = orig_octaos_db
    fastapi_app.dependency_overrides.clear()
    db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Universal Media Transfer & Binary Malware Quarantine
# ─────────────────────────────────────────────────────────────────────────────

def test_universal_media_transfer_formats():
    """Verify any safe MIME type (audio, video, SVG, PDF, XLSX, CSV, JSON) is accepted."""
    # Audio WAV
    wav_header = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
    ok, mime, err = validate_and_quarantine_media(wav_header, declared_mime="audio/wav", filename="sample.wav")
    assert ok
    assert mime == "audio/wav"

    # Audio MP3
    mp3_data = b"\xff\xfb\x90\x44" + b"\x00" * 100
    ok, mime, _ = validate_and_quarantine_media(mp3_data, declared_mime="audio/mpeg", filename="speech.mp3")
    assert ok
    assert mime == "audio/mpeg"

    # Vector SVG
    svg_data = b"<svg xmlns='http://www.w3.org/2000/svg'><circle r='10'/></svg>"
    ok, mime, _ = validate_and_quarantine_media(svg_data, declared_mime="image/svg+xml", filename="diagram.svg")
    assert ok
    assert mime == "image/svg+xml"

    # PDF Document
    pdf_data = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj"
    ok, mime, _ = validate_and_quarantine_media(pdf_data, declared_mime="application/pdf", filename="report.pdf")
    assert ok
    assert mime == "application/pdf"

    # Excel XLSX
    xlsx_data = b"PK\x03\x04\x14\x00\x06\x00" + b"\x00" * 50
    ok, mime, _ = validate_and_quarantine_media(
        xlsx_data,
        declared_mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="model.xlsx",
    )
    assert ok

    # Parquet Data
    parquet_data = b"PAR1" + b"\x00" * 30 + b"PAR1"
    ok, mime, _ = validate_and_quarantine_media(parquet_data, declared_mime="application/x-parquet", filename="data.parquet")
    assert ok


def test_malicious_executables_quarantine():
    """Verify dangerous executable formats (ELF, Windows PE MZ, Mach-O, shebangs) are quarantined."""
    # Linux ELF binary
    elf_data = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 50
    ok, mime, reason = validate_and_quarantine_media(elf_data, filename="agent_binary")
    assert not ok
    assert "quarantined" in reason.lower() or "malicious" in reason.lower()

    # Windows PE executable
    mz_data = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 60
    ok, mime, reason = validate_and_quarantine_media(mz_data, filename="installer.exe")
    assert not ok
    assert "forbidden" in reason.lower() or "quarantined" in reason.lower()

    # Mach-O executable
    macho_data = b"\xfe\xed\xfa\xce" + b"\x00" * 40
    ok, mime, reason = validate_and_quarantine_media(macho_data, filename="macho_bin")
    assert not ok

    # Script shebang
    sh_data = b"#!/bin/bash\nrm -rf /"
    ok, mime, reason = validate_and_quarantine_media(sh_data, filename="script.sh")
    assert not ok


def test_store_and_read_media_asset():
    """Verify store_media_bytes and read_media_asset_bytes roundtrip."""
    content = b"Universal AI Data Payload \x00\x01\x02"
    stored = store_media_bytes(content, filename="artifact.dat", declared_mime="application/octet-stream")
    assert stored["size_bytes"] == len(content)
    assert stored["sha256"] == hashlib.sha256(content).hexdigest()

    retrieved = get_media_asset(stored["url"])
    assert retrieved is not None
    assert stored["filename"] == "artifact.dat"
    assert retrieved["filename"].endswith(".dat")

    read_back, mime_type, total_size = read_media_asset_bytes(stored["url"])
    assert read_back == content
    assert total_size == len(content)



# ─────────────────────────────────────────────────────────────────────────────
# 2. Strict Schema Validation & Dummy Placeholder Prevention
# ─────────────────────────────────────────────────────────────────────────────

def test_reject_empty_payload_on_create(integration_env):
    """Verify dispatcher rejects empty argument payloads when schema has required fields."""
    client = integration_env["client"]
    mcp_key = integration_env["mcp_key"]

    resp = client.post(
        "/api/v1/plugin/gateway/execute",
        headers={"Authorization": f"Bearer {mcp_key}"},
        json={
            "tool": "octaos_create_lead",
            "arguments": {},
        },
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "required" in str(data).lower()


def test_reject_placeholder_dummy_lead(integration_env):
    """Verify dummy placeholder contacts (e.g. Inbound Lead, *@example.com) are rejected."""
    client = integration_env["client"]
    mcp_key = integration_env["mcp_key"]

    # Placeholder email @example.com
    resp = client.post(
        "/api/v1/plugin/gateway/execute",
        headers={"Authorization": f"Bearer {mcp_key}"},
        json={
            "tool": "octaos_create_lead",
            "arguments": {
                "name": "Jane Doe",
                "email": "test@example.com",
            },
        },
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "placeholder" in str(data).lower()

    # Placeholder dummy name "Inbound Lead"
    resp2 = client.post(
        "/api/v1/plugin/gateway/execute",
        headers={"Authorization": f"Bearer {mcp_key}"},
        json={
            "tool": "octaos_create_lead",
            "arguments": {
                "name": "Inbound Lead",
                "email": "jane@acmecorp.com",
            },
        },
    )
    assert resp2.status_code == 400
    data2 = resp2.json()
    assert "placeholder" in str(data2).lower()

    # Valid lead succeeds
    resp3 = client.post(
        "/api/v1/plugin/gateway/execute",
        headers={"Authorization": f"Bearer {mcp_key}"},
        json={
            "tool": "octaos_create_lead",
            "arguments": {
                "name": "Jane Doe",
                "email": "jane@acmecorp.com",
                "company": "Acme Corp",
            },
        },
    )
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["name"] == "Jane Doe"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Auth Unification (Eliminating false 401s on octa_mcp_... keys)
# ─────────────────────────────────────────────────────────────────────────────

def test_auth_unification_product_routes(integration_env):
    """Verify routes that require authentication accept octa_mcp_... keys without 401 session expired."""
    client = integration_env["client"]
    mcp_key = integration_env["mcp_key"]

    # Calling /api/v1/unified-mail/status with MCP key
    resp = client.get(
        "/api/v1/unified-mail/status",
        headers={"Authorization": f"Bearer {mcp_key}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "provider" in data or "configured" in data

    # Calling /api/v1/integrations/external-agents/connections with MCP key
    resp2 = client.get(
        "/api/v1/integrations/external-agents/connections",
        headers={"Authorization": f"Bearer {mcp_key}"},
    )
    assert resp2.status_code == 200
    assert isinstance(resp2.json(), list)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Inbound Controller Replies & Activity Feed
# ─────────────────────────────────────────────────────────────────────────────

def test_inbound_controller_replies_and_activity_feed(integration_env):
    """Verify external controllers report results and progress, correlating with commands."""
    client = integration_env["client"]
    mcp_key = integration_env["mcp_key"]

    # 1. Issue command first
    cmd_resp = client.post(
        "/api/v1/integrations/external-agents/commands",
        headers={"Authorization": f"Bearer {mcp_key}"},
        json={
            "command": "Run SEO audit for client portal",
            "correlation_id": "test-corr-456",
        },
    )
    assert cmd_resp.status_code == 201
    cmd_data = cmd_resp.json()
    assert cmd_data["status"] == "sent"

    # 2. External controller posts status reply with attachments
    reply_resp = client.post(
        "/api/v1/controller/replies",
        headers={"Authorization": f"Bearer {mcp_key}"},
        json={
            "correlation_id": "test-corr-456",
            "kind": "result",
            "title": "Audit Complete",
            "body": "Found 12 optimization opportunities. Detailed report attached.",
            "attachments": [
                {
                    "name": "Audit_Report.pdf",
                    "url": "https://storage.octaos.io/media/audit.pdf",
                    "mime_type": "application/pdf",
                    "size_bytes": 204800,
                }
            ],
            "data": {"score": 92},
        },
    )
    assert reply_resp.status_code == 201
    reply_data = reply_resp.json()
    assert reply_data["success"] is True

    # 3. Verify ControllerCommand is updated to completed
    commands_resp = client.get(
        "/api/v1/integrations/external-agents/commands",
        headers={"Authorization": f"Bearer {mcp_key}"},
    )
    assert commands_resp.status_code == 200
    items = commands_resp.json()["items"]
    matched = next((c for c in items if c["correlation_id"] == "test-corr-456"), None)
    assert matched is not None
    assert matched["status"] == "completed"
    assert "Audit Complete" in matched["reply_summary"]

    # 4. Verify Activity Feed endpoint returns the event with attachments
    act_resp = client.get(
        "/api/v1/dashboard/activity?correlation_id=test-corr-456",
        headers={"Authorization": f"Bearer {mcp_key}"},
    )
    assert act_resp.status_code == 200
    feed = act_resp.json()["items"]
    assert len(feed) >= 1
    assert feed[0]["title"] == "Audit Complete"
    assert len(feed[0]["attachments"]) == 1
    assert feed[0]["attachments"][0]["name"] == "Audit_Report.pdf"


def test_mcp_tool_octaos_post_status(integration_env):
    """Verify AI agents can post status and notes to activity feed via MCP tool."""
    client = integration_env["client"]
    mcp_key = integration_env["mcp_key"]

    resp = client.post(
        "/api/v1/plugin/gateway/execute",
        headers={"Authorization": f"Bearer {mcp_key}"},
        json={
            "tool": "octaos_post_status",
            "arguments": {
                "title": "Agent Milestone Reached",
                "body": "Completed background sync of external records.",
                "kind": "status",
                "correlation_id": "mcp-corr-789",
                "attachments": [
                    {
                        "name": "sync_summary.json",
                        "url": "https://storage.octaos.io/media/sync.json",
                        "mime_type": "application/json",
                    }
                ],
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["title"] == "Agent Milestone Reached"



# ─────────────────────────────────────────────────────────────────────────────
# 5. Outbound Webhook Dispatcher, HMAC Signatures, and SSRF
# ─────────────────────────────────────────────────────────────────────────────

def test_webhook_hmac_signature_generation():
    """Verify HMAC-SHA256 signature formatting and verification."""
    payload = {"event": "lead.created", "tenant_id": "tenant-1", "lead_id": "ld-100"}
    envelope_str = json.dumps(payload, separators=(",", ":"))
    secret = "shh_super_secret_webhook_key_42"

    headers = sign_webhook_headers(
        envelope_str=envelope_str,
        secret=secret,
        delivery_id="evt_12345",
        event_type="lead.created",
        auth_type="hmac",
    )

    sig_header = headers["X-OctaOS-Signature"]
    assert sig_header.startswith("t=") and ",v1=" in sig_header
    parts = dict(p.split("=", 1) for p in sig_header.split(","))
    t = parts["t"]
    v1 = parts["v1"]

    expected_sig = hmac.new(
        secret.encode("utf-8"),
        f"{t}.{envelope_str}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    assert hmac.compare_digest(v1, expected_sig)


def test_ssrf_protection_blocks_internal_ips():
    """Verify validate_outbound_url blocks localhost, loopback, and RFC-1918 private IPs."""
    with pytest.raises(SSRFProtectionError):
        validate_outbound_url("http://127.0.0.1:8000/webhook")

    with pytest.raises(SSRFProtectionError):
        validate_outbound_url("http://localhost:3000/api")

    with pytest.raises(SSRFProtectionError):
        validate_outbound_url("http://192.168.1.1/hook")

    with pytest.raises(SSRFProtectionError):
        validate_outbound_url("http://10.0.0.5/hook")

    with pytest.raises(SSRFProtectionError):
        validate_outbound_url("file:///etc/passwd")

    # Safe public URL passes
    assert validate_outbound_url("https://api.github.com/webhook") == "https://api.github.com/webhook"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Dashboard Agent Tool (external_agent.send_command)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_tool_external_agent_send_command(integration_env):
    """Verify workforce agents can dispatch commands to external agents via ToolRegistry."""
    db = integration_env["db"]
    tenant_id = integration_env["tenant_id"]

    res = await tool_registry.execute_tool(
        name="external_agent.send_command",
        payload={
            "command": "Perform automated CRO review on landing page",
            "correlation_id": "agent-cmd-111",
            "context": {"url": "https://octaos.io"},
        },
        db=db,
        tenant_id=tenant_id,
        context={
            "agent_name": "Senior CRO Auditor",
            "granted_tools": ["external_agent.send_command"],
            "request_tenant_id": tenant_id,
        },
    )

    assert res["success"] is True
    assert res["correlation_id"] == "agent-cmd-111"
    assert res["status"] == "sent"

    # Verify record in DB
    cmd = db.query(ControllerCommand).filter(ControllerCommand.correlation_id == "agent-cmd-111").first()
    assert cmd is not None
    assert cmd.command == "Perform automated CRO review on landing page"
    assert cmd.issued_by == "Senior CRO Auditor"
