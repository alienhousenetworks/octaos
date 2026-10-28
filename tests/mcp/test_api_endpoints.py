"""Tests for the MCP FastAPI HTTP Endpoints and Streamable HTTP Transport with in-memory DB."""
import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.main import app
from app.api import deps
from app.models.base import Base, Tenant, User
from app.core.security import create_access_token
from app.services.mcp.auth.credentials import create_credential_with_grants

TEST_SQLITE_URL = "sqlite:///:memory:"


@pytest.fixture
def api_test_data():
    engine = create_engine(
        TEST_SQLITE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    t = Tenant(id=tenant_id, name="Test Endpoint Tenant", subdomain=f"test-{uuid.uuid4().hex[:6]}")
    u = User(id=user_id, tenant_id=tenant_id, email=f"user-{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw", is_active=True, is_verified=True, role="admin")
    db.add_all([t, u])
    db.commit()

    token = create_access_token(subject=u.id, tenant_id=t.id)

    # Create an MCP key
    mcp_cred, raw_key = create_credential_with_grants(
        db=db,
        tenant_id=t.id,
        name="Endpoint Test Key",
        user_id=u.id,
        role="admin",
    )

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[deps.get_db] = override_get_db

    yield {
        "db": db,
        "tenant": t,
        "user": u,
        "jwt_token": token,
        "mcp_cred": mcp_cred,
        "raw_mcp_key": raw_key,
    }

    app.dependency_overrides.pop(deps.get_db, None)
    db.close()
    Base.metadata.drop_all(bind=engine)


def test_mcp_catalog_endpoint(api_test_data):
    token = api_test_data["jwt_token"]
    with TestClient(app) as client:
        res = client.get("/api/v1/mcp/catalog", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert "universal_tools" in data
        assert "domain_wrappers" in data
        tool_names = [t["name"] for t in data["universal_tools"]]
        assert "octaos_query_records" in tool_names
        assert "octaos_create_record" in tool_names


def test_mcp_credentials_crud_endpoint(api_test_data):
    token = api_test_data["jwt_token"]
    with TestClient(app) as client:
        # 1. Create credential via API
        create_res = client.post(
            "/api/v1/mcp/credentials",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Integration Test Key",
                "client_type": "claude_desktop",
                "role": "standard_operator",
            },
        )
        assert create_res.status_code == 200
        new_cred = create_res.json()
        assert "raw_key" in new_cred
        assert new_cred["raw_key"].startswith("octa_mcp_")
        cred_id = new_cred["id"]

        # 2. List credentials
        list_res = client.get("/api/v1/mcp/credentials", headers={"Authorization": f"Bearer {token}"})
        assert list_res.status_code == 200
        creds = list_res.json()["credentials"]
        assert any(c["id"] == cred_id for c in creds)

        # 3. Test connection endpoint
        test_res = client.post(
            "/api/v1/mcp/test-connection",
            headers={"Authorization": f"Bearer {token}"},
            json={"raw_key": new_cred["raw_key"]},
        )
        assert test_res.status_code == 200
        assert test_res.json()["status"] == "success"

        # 4. Revoke credential
        del_res = client.delete(f"/api/v1/mcp/credentials/{cred_id}", headers={"Authorization": f"Bearer {token}"})
        assert del_res.status_code == 200


def test_external_mcp_server_registration_accepts_arbitrary_provider(api_test_data):
    token = api_test_data["jwt_token"]
    with TestClient(app) as client:
        add_res = client.post(
            "/api/v1/mcp/servers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Any Provider MCP",
                "slug": "any-provider",
                "transport": "streamable_http",
                "endpoint": "https://mcp.example.test/provider",
                "headers": {"Authorization": "Bearer secret"},
            },
        )
        assert add_res.status_code == 200
        server = add_res.json()
        assert server["slug"] == "any-provider"
        assert server["transport"] == "streamable_http"
        assert server["target"] == "https://mcp.example.test/provider"
        assert server["has_headers"] is True

        list_res = client.get("/api/v1/mcp/servers", headers={"Authorization": f"Bearer {token}"})
        assert list_res.status_code == 200
        assert any(item["id"] == server["id"] for item in list_res.json()["servers"])

        delete_res = client.delete(
            f"/api/v1/mcp/servers/{server['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete_res.status_code == 200


def test_mcp_streamable_http_transport(api_test_data):
    raw_key = api_test_data["raw_mcp_key"]
    with TestClient(app) as client:
        # Call initialize over Streamable HTTP
        init_res = client.post(
            "/api/v1/mcp/stream",
            headers={"Authorization": f"Bearer {raw_key}"},
            json={
                "jsonrpc": "2.0",
                "id": "req-1",
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
            },
        )
        assert init_res.status_code == 200
        init_data = init_res.json()
        assert init_data["id"] == "req-1"
        assert init_data["result"]["protocolVersion"] == "2024-11-05"

        # Call tools/list over Streamable HTTP
        tools_res = client.post(
            "/api/v1/mcp/stream",
            headers={"Authorization": f"Bearer {raw_key}"},
            json={
                "jsonrpc": "2.0",
                "id": "req-2",
                "method": "tools/list",
            },
        )
        assert tools_res.status_code == 200
        tools_data = tools_res.json()
        assert "tools" in tools_data["result"]


def test_canonical_mcp_endpoint_is_available(api_test_data):
    """Clients can use the conventional /mcp endpoint, not only the versioned alias."""
    raw_key = api_test_data["raw_mcp_key"]
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            headers={
                "Authorization": f"Bearer {raw_key}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            json={
                "jsonrpc": "2.0",
                "id": "canonical-init",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "interop-test", "version": "1.0.0"},
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["jsonrpc"] == "2.0"
        assert payload["id"] == "canonical-init"
        assert payload["result"]["protocolVersion"] == "2024-11-05"
        assert payload["result"]["serverInfo"]["name"] == "octaos-governed-mcp-platform"


def test_canonical_mcp_endpoint_rejects_non_json_content_type(api_test_data):
    raw_key = api_test_data["raw_mcp_key"]
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            headers={
                "Authorization": f"Bearer {raw_key}",
                "Content-Type": "text/plain",
                "Accept": "application/json",
            },
            content='{"jsonrpc":"2.0","id":1,"method":"ping"}',
        )
        assert response.status_code == 415


def test_mcp_server_rejects_invalid_jsonrpc_version(api_test_data):
    raw_key = api_test_data["raw_mcp_key"]
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            headers={
                "Authorization": f"Bearer {raw_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={"jsonrpc": "1.0", "id": "bad-version", "method": "ping"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["error"]["code"] == -32600
        assert payload["id"] == "bad-version"
