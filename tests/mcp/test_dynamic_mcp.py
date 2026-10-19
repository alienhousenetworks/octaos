"""Comprehensive Automated Test Suite for OctaOS Governed Dynamic MCP Platform."""
from __future__ import annotations

import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, Tenant, User
from app.models.mcp import SystemMCPCredential, DynamicConnector, DynamicObjectDefinition, CapabilityGrant
from app.models.verticals import Lead, Ticket
from app.services.mcp.auth.credentials import (
    generate_mcp_key,
    authenticate_mcp_key,
    create_credential_with_grants,
)
from app.services.mcp.auth.policy import PolicyKernel
from app.services.mcp.connectors.octaos_internal import OctaOSInternalAdapter
from app.services.mcp.registry.schema_discovery import SchemaDiscoveryService, compute_schema_fingerprint
from app.services.mcp.registry.schema_validation import validate_record_against_schema
from app.services.mcp.execution.query_engine import validate_query_dsl, QueryValidationError
from app.services.mcp.execution.dispatcher import GovernedExecutionDispatcher
from app.services.mcp.registry.capability_registry import CapabilityRegistry
from app.services.mcp.server import MCPServer

# In-memory SQLite for test isolation
TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture
def test_db():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    # Seed test tenant and user
    t1 = Tenant(id=str(uuid.uuid4()), name="Acme Corp", subdomain="acme")
    t2 = Tenant(id=str(uuid.uuid4()), name="Beta Corp", subdomain="beta")
    db.add_all([t1, t2])
    db.flush()

    u1 = User(id=str(uuid.uuid4()), tenant_id=t1.id, email="alice@acme.com", hashed_password="pw")
    db.add(u1)
    db.commit()

    yield db, TestingSessionLocal, t1, t2, u1

    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.mark.asyncio
async def test_key_generation_and_authentication(test_db):
    db, SessionLocal, t1, t2, u1 = test_db

    # 1. Generate key
    raw_key, key_hash, key_prefix = generate_mcp_key()
    assert raw_key.startswith("octa_mcp_")
    assert len(raw_key) > 40

    # 2. Create credential with grants
    cred, key = create_credential_with_grants(
        db=db,
        tenant_id=t1.id,
        name="Test Claude Desktop",
        user_id=u1.id,
        role="standard_operator",
    )
    assert cred.id is not None
    assert cred.key_prefix == key[:16]

    # 3. Authenticate valid key
    auth_cred = authenticate_mcp_key(db, key)
    assert auth_cred is not None
    assert auth_cred.id == cred.id
    assert auth_cred.last_used_at is not None

    # 4. Inactive key rejection
    auth_cred.is_active = False
    db.commit()
    assert authenticate_mcp_key(db, key) is None


@pytest.mark.asyncio
async def test_dynamic_schema_discovery(test_db):
    db, SessionLocal, t1, t2, u1 = test_db
    adapter = OctaOSInternalAdapter(db_factory=SessionLocal)

    conn = SchemaDiscoveryService.get_or_register_default_octaos_connector(db, t1.id)
    assert conn.slug == "octaos"

    synced = await SchemaDiscoveryService.sync_connector_schemas(db, t1.id, conn, adapter)
    assert len(synced) >= 5 # lead, ticket, content_post, candidate, workflow, etc.

    lead_def = next((o for o in synced if o.object_name == "lead"), None)
    assert lead_def is not None
    assert "email" in lead_def.schema_json["properties"]
    assert "name" in lead_def.schema_json["properties"]
    assert lead_def.schema_fingerprint is not None


@pytest.mark.asyncio
async def test_runtime_schema_validation():
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "score": {"type": "integer"},
            "is_vip": {"type": "boolean"},
        },
        "required": ["name"],
        "additionalProperties": False,
    }

    # Valid payload
    valid, errors = validate_record_against_schema({"name": "Acme Lead", "score": 85, "is_vip": True}, schema)
    assert valid is True
    assert len(errors) == 0

    # Missing required field
    valid, errors = validate_record_against_schema({"score": 85}, schema)
    assert valid is False
    assert any(e["field"] == "name" for e in errors)

    # Type mismatch (string instead of integer)
    valid, errors = validate_record_against_schema({"name": "Test", "score": "high"}, schema)
    assert valid is False
    assert any(e["field"] == "score" for e in errors)

    # Unexpected field when additionalProperties=False
    valid, errors = validate_record_against_schema({"name": "Test", "unrecognized": 123}, schema)
    assert valid is False
    assert any(e["field"] == "unrecognized" for e in errors)


@pytest.mark.asyncio
async def test_safe_typed_query_dsl():
    # Valid query
    valid = validate_query_dsl({
        "fields": ["name", "email", "status"],
        "filter": {
            "and": [
                {"field": "status", "operator": "eq", "value": "captured"},
                {"field": "score", "operator": "gte", "value": 50},
            ]
        },
        "sort": [{"field": "name", "direction": "asc"}],
        "limit": 25,
    }, max_allowed_limit=50)

    assert valid["limit"] == 25
    assert len(valid["fields"]) == 3

    # Reject dangerous SQL injection characters in field names
    with pytest.raises(QueryValidationError):
        validate_query_dsl({"fields": ["name; DROP TABLE leads;--"]})

    # Reject unsupported operators
    with pytest.raises(QueryValidationError):
        validate_query_dsl({"filter": {"field": "status", "operator": "EXEC_SQL", "value": "1"}})


@pytest.mark.asyncio
async def test_field_level_authorization_and_redaction(test_db):
    db, SessionLocal, t1, t2, u1 = test_db

    cred, key = create_credential_with_grants(
        db=db,
        tenant_id=t1.id,
        name="Restricted Agent",
        role="custom",
        grants=[
            {
                "connector_slug": "octaos",
                "object_name": "lead",
                "allowed_actions": ["read", "query", "create"],
                "permitted_fields": ["id", "name", "email", "company", "status"],
                "denied_fields": ["personal_email", "company_contact_no"],
            }
        ],
    )

    # 1. Authorize allowed create without sensitive fields
    decision = PolicyKernel.authorize_action(
        db=db,
        credential=cred,
        connector_slug="octaos",
        object_name="lead",
        action="create",
        payload_fields={"name", "email", "company"},
    )
    assert decision.allowed is True

    # 2. Deny create attempting to write denied sensitive field
    decision_denied = PolicyKernel.authorize_action(
        db=db,
        credential=cred,
        connector_slug="octaos",
        object_name="lead",
        action="create",
        payload_fields={"name", "personal_email"},
    )
    assert decision_denied.allowed is False
    assert "sensitive fields" in decision_denied.reason

    # 3. Deny action not granted (delete)
    decision_del = PolicyKernel.authorize_action(
        db=db,
        credential=cred,
        connector_slug="octaos",
        object_name="lead",
        action="delete",
    )
    assert decision_del.allowed is False
    assert "Permission Denied" in decision_del.reason

    # 4. Redaction test on output
    raw_record = {
        "id": "lead-1",
        "name": "Jane Doe",
        "email": "jane@corp.com",
        "personal_email": "jane.private@gmail.com",
        "password": "secret_password",
    }
    redacted = PolicyKernel.redact_record(
        raw_record,
        permitted_fields=decision.permitted_fields,
        denied_fields=decision.denied_fields,
    )
    assert "name" in redacted
    assert "email" in redacted
    assert "personal_email" not in redacted
    assert "password" not in redacted


@pytest.mark.asyncio
async def test_full_governed_crud_lifecycle(test_db):
    db, SessionLocal, t1, t2, u1 = test_db
    dispatcher = GovernedExecutionDispatcher(db_factory=SessionLocal)
    registry = CapabilityRegistry(dispatcher=dispatcher)

    # Create admin credential with full CRUD
    cred, key = create_credential_with_grants(
        db=db,
        tenant_id=t1.id,
        name="Admin Worker",
        role="admin",
    )

    # 1. Create record
    res_create = await registry.call_tool(
        credential=cred,
        tool_name="octaos_create_record",
        arguments={
            "source": "octaos",
            "object": "lead",
            "record": {
                "name": "Enterprise Buyer",
                "email": "buyer@enterprise.corp",
                "company": "Big Enterprise Inc",
                "status": "captured",
                "score": 90,
            },
        },
    )
    assert res_create.isError is False
    import json
    data = json.loads(res_create.content[0].text)
    lead_id = data["id"]
    assert data["name"] == "Enterprise Buyer"

    # 2. Query records
    res_query = await registry.call_tool(
        credential=cred,
        tool_name="octaos_query_records",
        arguments={
            "source": "octaos",
            "object": "lead",
            "filter": {"field": "status", "operator": "eq", "value": "captured"},
        },
    )
    assert res_query.isError is False
    query_data = json.loads(res_query.content[0].text)
    assert query_data["total_count"] >= 1
    assert any(r["id"] == lead_id for r in query_data["records"])

    # 3. Get record by ID
    res_get = await registry.call_tool(
        credential=cred,
        tool_name="octaos_get_record",
        arguments={"source": "octaos", "object": "lead", "id": lead_id},
    )
    assert res_get.isError is False
    get_data = json.loads(res_get.content[0].text)
    assert get_data["id"] == lead_id

    # 4. Update record
    res_update = await registry.call_tool(
        credential=cred,
        tool_name="octaos_update_record",
        arguments={
            "source": "octaos",
            "object": "lead",
            "id": lead_id,
            "record": {"status": "qualified", "score": 98},
        },
    )
    assert res_update.isError is False
    updated_data = json.loads(res_update.content[0].text)
    assert updated_data["status"] == "qualified"
    assert updated_data["score"] == 98

    # 5. Delete record
    res_del = await registry.call_tool(
        credential=cred,
        tool_name="octaos_delete_record",
        arguments={"source": "octaos", "object": "lead", "id": lead_id},
    )
    assert res_del.isError is False
    del_data = json.loads(res_del.content[0].text)
    assert del_data["deleted"] is True


@pytest.mark.asyncio
async def test_tenant_isolation_boundary(test_db):
    db, SessionLocal, t1, t2, u1 = test_db
    dispatcher = GovernedExecutionDispatcher(db_factory=SessionLocal)
    registry = CapabilityRegistry(dispatcher=dispatcher)

    # Insert a record in Tenant 2
    l2 = Lead(
        id=str(uuid.uuid4()),
        tenant_id=t2.id,
        name="Secret Tenant 2 Lead",
        email="secret@tenant2.com",
    )
    db.add(l2)
    db.commit()

    # Credential belongs to Tenant 1
    cred_t1, key_t1 = create_credential_with_grants(
        db=db,
        tenant_id=t1.id,
        name="Tenant 1 Caller",
        role="admin",
    )

    # Attempt to read Tenant 2 lead by ID
    res = await registry.call_tool(
        credential=cred_t1,
        tool_name="octaos_get_record",
        arguments={"source": "octaos", "object": "lead", "id": l2.id},
    )
    import json
    data = json.loads(res.content[0].text)
    # Must be None or empty - Tenant 1 cannot access Tenant 2 records
    assert data is None

    # Attempt to delete Tenant 2 lead by ID
    res_del = await registry.call_tool(
        credential=cred_t1,
        tool_name="octaos_delete_record",
        arguments={"source": "octaos", "object": "lead", "id": l2.id},
    )
    del_data = json.loads(res_del.content[0].text)
    assert del_data["deleted"] is False

    # Verify record still exists in Tenant 2
    check = db.query(Lead).filter(Lead.id == l2.id).first()
    assert check is not None


@pytest.mark.asyncio
async def test_mcp_server_protocol_flow(test_db):
    db, SessionLocal, t1, t2, u1 = test_db
    server = MCPServer(db_factory=SessionLocal)

    cred, key = create_credential_with_grants(
        db=db,
        tenant_id=t1.id,
        name="Protocol Test Client",
        role="standard_operator",
    )

    # 1. Initialize
    init_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05"},
    }
    resp = await server.handle_message(cred, init_msg)
    assert resp["id"] == 1
    assert resp["result"]["protocolVersion"] == "2024-11-05"
    assert "tools" in resp["result"]["capabilities"]

    # 2. Ping
    ping_msg = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
    resp_ping = await server.handle_message(cred, ping_msg)
    assert resp_ping["id"] == 2
    assert resp_ping["result"] == {}

    # 3. Tools List
    tools_msg = {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
    resp_tools = await server.handle_message(cred, tools_msg)
    assert resp_tools["id"] == 3
    tools = resp_tools["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "octaos_discover_sources" in tool_names
    assert "octaos_query_records" in tool_names
    assert "octaos_create_record" in tool_names
    # standard_operator lacks delete by default
    assert "octaos_delete_record" not in tool_names
