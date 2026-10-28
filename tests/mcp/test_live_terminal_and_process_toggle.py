"""Tests for Live Terminal and Process ON/OFF Controls in OctaOS External AI Collaboration Gateway."""
from __future__ import annotations

import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

import app.models.mcp
import app.models.verticals
import app.models.enterprise
import app.models.agents
import app.models.collaborative_workforce
from app.main import app as fastapi_app
from app.api import deps
from app.models.base import Base, Tenant, User, SystemSetting
from app.services.collaboration.live_terminal import LiveTerminalManager
from app.services.mcp.auth.credentials import create_credential_with_grants
from app.services.mcp.server import mcp_server

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture
def terminal_setup():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    orig_server_db = mcp_server.db_factory
    orig_disp_db = mcp_server.dispatcher.db_factory
    orig_adapters_db = {}

    mcp_server.db_factory = TestingSession
    mcp_server.dispatcher.db_factory = TestingSession
    for slug, adapter in mcp_server.dispatcher._adapters.items():
        if hasattr(adapter, "db_factory"):
            orig_adapters_db[slug] = adapter.db_factory
            adapter.db_factory = TestingSession

    tenant_id = f"term-tenant-{uuid.uuid4().hex[:6]}"
    tenant = Tenant(id=tenant_id, name="Terminal Test Corp", subdomain="term-corp")
    db.add(tenant)

    user = User(id=str(uuid.uuid4()), tenant_id=tenant_id, email="terminal@octaos.ai", hashed_password="pw")
    db.add(user)
    db.commit()

    cred, raw_key = create_credential_with_grants(
        db=db,
        tenant_id=tenant_id,
        name="Terminal Connector AI",
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
        "raw_key": raw_key,
        "cred": cred,
        "Session": TestingSession,
    }

    mcp_server.db_factory = orig_server_db
    mcp_server.dispatcher.db_factory = orig_disp_db
    for slug, orig_db in orig_adapters_db.items():
        if slug in mcp_server.dispatcher._adapters:
            mcp_server.dispatcher._adapters[slug].db_factory = orig_db
    fastapi_app.dependency_overrides.clear()


def test_live_terminal_buffer_logging_and_filtering(terminal_setup):
    """Verifies that LiveTerminalManager buffers entries, filters by category, and enforces limits."""
    tenant_id = terminal_setup["tenant_id"]

    LiveTerminalManager.clear_logs(tenant_id)
    LiveTerminalManager.log_event(tenant_id, category="inbound", level="info", message="Inbound test 1")
    LiveTerminalManager.log_event(tenant_id, category="outbound", level="info", message="Outbound test 1")
    LiveTerminalManager.log_event(tenant_id, category="bridge", level="info", message="Bridge test 1")
    LiveTerminalManager.log_event(tenant_id, category="system", level="info", message="System test 1")

    all_logs = LiveTerminalManager.get_logs(tenant_id, limit=50)
    assert len(all_logs) >= 5 # 4 events + cleared event

    inbound_logs = LiveTerminalManager.get_logs(tenant_id, category="inbound")
    assert any("Inbound test 1" in e.message for e in inbound_logs)
    assert all(e.category == "inbound" for e in inbound_logs)

    bridge_logs = LiveTerminalManager.get_logs(tenant_id, category="bridge")
    assert any("Bridge test 1" in e.message for e in bridge_logs)


def test_process_toggle_on_off_and_rejection_of_incoming_traffic(terminal_setup):
    """
    Verifies that turning the external collaboration process OFF blocks incoming traffic
    with HTTP 503 and logs warning events, and turning it ON resumes normal processing.
    """
    client = terminal_setup["client"]
    raw_key = terminal_setup["raw_key"]
    tenant_id = terminal_setup["tenant_id"]
    db = terminal_setup["db"]

    # 1. Initially active
    status_resp = LiveTerminalManager.get_process_status(db, tenant_id)
    assert status_resp.is_active is True
    assert status_resp.status == "RUNNING"

    # 2. Toggle process OFF via API
    toggle_off_res = client.post(
        "/api/v1/plugin/collaboration/process/toggle",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={"active": False},
    )
    assert toggle_off_res.status_code == 200
    assert toggle_off_res.json()["status"] == "STOPPED"
    assert toggle_off_res.json()["is_active"] is False

    # 3. Verify incoming gateway execution is rejected with 503
    gw_res = client.post(
        "/api/v1/plugin/gateway/execute",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={"tool": "octaos_sales_capture_lead", "arguments": {"first_name": "Blocked"}},
    )
    assert gw_res.status_code == 503
    assert "currently STOPPED" in gw_res.json()["detail"]

    # 4. Verify workforce delegation is rejected with 503
    del_res = client.post(
        "/api/v1/plugin/workforce/delegate",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={"employee": "sales", "task_type": "lead_qualification", "parameters": {}},
    )
    assert del_res.status_code == 503
    assert "currently STOPPED" in del_res.json()["detail"]

    # 5. Verify direct action is rejected with 503
    act_res = client.post(
        "/api/v1/plugin/actions/octaos_sales_capture_lead",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={"first_name": "Direct"},
    )
    assert act_res.status_code == 503

    # 6. Verify collaboration task is rejected with 503
    task_res = client.post(
        "/api/v1/plugin/collaboration/tasks",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={"task_description": "Blocked async task", "async_execution": True},
    )
    assert task_res.status_code == 503

    # 7. Check that terminal logs recorded the rejection warnings
    logs_res = client.get(
        "/api/v1/plugin/collaboration/terminal/logs",
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert logs_res.status_code == 200
    logs_data = logs_res.json()
    assert logs_data["process"]["status"] == "STOPPED"
    assert any("REJECTED" in log["message"] for log in logs_data["logs"])

    # 8. Toggle process back ON
    toggle_on_res = client.post(
        "/api/v1/plugin/collaboration/process/toggle",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={"active": True},
    )
    assert toggle_on_res.status_code == 200
    assert toggle_on_res.json()["status"] == "RUNNING"
    assert toggle_on_res.json()["is_active"] is True

    # 9. Verify requests succeed again after turning back ON
    act_res_after = client.post(
        "/api/v1/plugin/actions/octaos_query_ai_workforce",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={},
    )
    assert act_res_after.status_code == 200


def test_terminal_clear_and_ping_endpoints(terminal_setup):
    """Verifies clearing the terminal log and sending diagnostic test pings."""
    client = terminal_setup["client"]
    raw_key = terminal_setup["raw_key"]

    # 1. Ping
    ping_res = client.post(
        "/api/v1/plugin/collaboration/terminal/ping",
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert ping_res.status_code == 200
    assert ping_res.json()["status"] == "pong"
    assert "operator_console" in ping_res.json()["entry"]["source"]

    # 2. Clear
    clear_res = client.post(
        "/api/v1/plugin/collaboration/terminal/clear",
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert clear_res.status_code == 200
    assert clear_res.json()["status"] == "cleared"

    # 3. Check logs after clear
    logs_res = client.get(
        "/api/v1/plugin/collaboration/terminal/logs",
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert logs_res.status_code == 200
    logs = logs_res.json()["logs"]
    assert len(logs) == 1
    assert "cleared by operator" in logs[0]["message"]
