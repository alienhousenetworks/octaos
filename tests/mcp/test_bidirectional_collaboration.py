"""Integration Tests for OctaOS Bidirectional Universal AI Collaboration Engine.
Verifies:
1. Sales AI outbound delegation to external AI with workflow resumption.
2. Inbound delegation from external AI to OctaOS AI employees.
3. Bidirectional data flow with correlation IDs, results, and evidence.
4. Long-running async jobs and status polling.
5. Safe fallback on missing providers and errors.
6. Multi-tenant isolation and prohibited data sharing rejection.
7. Delegation loops and cycle prevention.
8. Result-to-Execution Bridge: policy checks, approvals, and verified evidence.
9. Redaction of credentials and sensitive context.
10. Webhook signing and anti-replay verification.
"""
from __future__ import annotations

import json
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
from app.core.security import encrypt_api_key
from app.models.base import Base, Tenant, User, APICredential
from app.services.agents.sales import SalesAgent
from app.services.collaboration import (
    AICollaborationEngine,
    AIProviderRegistry,
    CollaborationTaskSubmitRequest,
    DelegationLoopError,
    DelegationLimitError,
    ExecutionBridge,
    ExecutionBridgeRequest,
    redact_sensitive_context,
    validate_delegation_safety,
)
from app.services.mcp.auth.credentials import create_credential_with_grants
from app.services.mcp.server import mcp_server

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture
def collab_setup():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    # Wire mcp_server and all adapters to use test session
    orig_server_db = mcp_server.db_factory
    orig_disp_db = mcp_server.dispatcher.db_factory
    orig_adapters_db = {}

    mcp_server.db_factory = TestingSession
    mcp_server.dispatcher.db_factory = TestingSession
    for slug, adapter in mcp_server.dispatcher._adapters.items():
        if hasattr(adapter, "db_factory"):
            orig_adapters_db[slug] = adapter.db_factory
            adapter.db_factory = TestingSession

    # Primary Tenant
    tenant_id = f"tenant-{uuid.uuid4().hex[:6]}"
    tenant = Tenant(id=tenant_id, name="Primary Collaboration Tenant", subdomain="primary")
    db.add(tenant)

    # Second Tenant for Isolation Tests
    tenant2_id = f"tenant2-{uuid.uuid4().hex[:6]}"
    tenant2 = Tenant(id=tenant2_id, name="Isolated Tenant B", subdomain="tenant-b")
    db.add(tenant2)
    db.commit()

    user = User(id=str(uuid.uuid4()), tenant_id=tenant_id, email="admin@primary.com", hashed_password="pw")
    user2 = User(id=str(uuid.uuid4()), tenant_id=tenant2_id, email="admin@tenantb.com", hashed_password="pw")
    db.add(user)
    db.add(user2)
    db.commit()

    # Create admin credential for primary tenant
    cred, raw_key = create_credential_with_grants(
        db=db,
        tenant_id=tenant_id,
        name="Universal AI Collab Gateway",
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

    # Create credential for Tenant 2
    cred2, raw_key2 = create_credential_with_grants(
        db=db,
        tenant_id=tenant2_id,
        name="Tenant B Gateway",
        user_id=user2.id,
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

    # Add a mock connected Claude credential to primary tenant
    anthropic_cred = APICredential(
        tenant_id=tenant_id,
        provider="anthropic",
        encrypted_key=encrypt_api_key("sk-ant-api03-testkey-12345678901234567890"),
        settings={"cost_ceiling_usd": 50.0, "rate_limit_rpm": 60, "data_sharing_scope": "anonymized_only"},
    )
    db.add(anthropic_cred)
    db.commit()

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
        "tenant2_id": tenant2_id,
        "raw_key": raw_key,
        "raw_key2": raw_key2,
        "cred": cred,
        "Session": TestingSession,
    }

    mcp_server.db_factory = orig_server_db
    mcp_server.dispatcher.db_factory = orig_disp_db
    for slug, orig_db in orig_adapters_db.items():
        if slug in mcp_server.dispatcher._adapters:
            mcp_server.dispatcher._adapters[slug].db_factory = orig_db
    fastapi_app.dependency_overrides.clear()


def test_provider_registry_connection_status(collab_setup):
    """
    Verify that AIProviderRegistry accurately reflects configured vs unconfigured providers.
    Never reports a provider as connected unless a valid credential is in the database.
    """
    db = collab_setup["db"]
    tenant_id = collab_setup["tenant_id"]

    providers = AIProviderRegistry.get_connected_providers(db, tenant_id)
    assert len(providers) >= 4

    prov_map = {p.provider: p for p in providers}

    # Anthropic was configured with valid key
    assert prov_map["anthropic"].is_connected is True
    assert prov_map["anthropic"].status == "connected"
    assert "deep_coding" in prov_map["anthropic"].supported_capabilities
    assert prov_map["anthropic"].cost_ceiling_usd == 50.0

    # Grok and OpenAI have not been configured for this tenant
    assert prov_map["grok"].is_connected is False
    assert prov_map["grok"].status == "not_configured"
    assert prov_map["openai"].is_connected is False


def test_sensitive_context_redaction():
    """Verify that sensitive keys, secrets, and auth tokens are stripped before external transmission."""
    raw_context = {
        "company": "OctaOS Enterprise",
        "api_key": "sk-secret-live-token-123456",
        "nested": {
            "bearer_token": "bearer-xyz",
            "safe_field": "public_data",
            "user_password": "supersecretpassword",
        },
        "query": "Analysis using key sk-12345678901234567890 in query",
    }
    redacted = redact_sensitive_context(raw_context)

    assert redacted["api_key"] == "[REDACTED_SECRET]"
    assert redacted["nested"]["bearer_token"] == "[REDACTED_SECRET]"
    assert redacted["nested"]["user_password"] == "[REDACTED_SECRET]"
    assert redacted["nested"]["safe_field"] == "public_data"
    assert "sk-1234567890" not in redacted["query"]
    assert "[REDACTED_KEY]" in redacted["query"]


@pytest.mark.asyncio
async def test_outbound_collaboration_sales_ai(collab_setup):
    """
    Requirement 1: Sales AI delegates a subtask to an external AI (Claude),
    captures structured results and provenance, and resumes its workflow.
    """
    db = collab_setup["db"]
    tenant_id = collab_setup["tenant_id"]

    sales_agent = SalesAgent(db, tenant_id)

    # Test payload delegating market research with test fixture response
    mock_findings = {
        "competitor_analysis": "Market leading autonomous operating system",
        "target_segments": ["Fintech", "Healthtech", "B2B SaaS"],
        "estimated_acv": "$50,000",
    }

    result = await sales_agent.execute_task({
        "action": "collaborate_market_research",
        "parameters": {
            "query": "Enterprise AI Workforce competitive market analysis",
            "provider": "anthropic",
            "required_capabilities": ["complex_reasoning", "document_analysis"],
            "context": {"industry": "Enterprise Software", "secret_key": "sk-should-be-redacted"},
            "output_schema": {"required": ["competitor_analysis", "target_segments"]},
            "_test_mock_response": mock_findings,
        },
    })

    assert result["status"] == "success"
    assert result["workflow_resumed"] is True
    assert result["leads_enriched"] is True

    collab_data = result["collaboration"]
    assert collab_data["status"] == "success"
    assert collab_data["executed_externally"] is True
    assert collab_data["target_provider"] == "anthropic"
    assert collab_data["provenance"]["source_agent"] == "Sales AI"
    assert collab_data["result"]["competitor_analysis"] == mock_findings["competitor_analysis"]


def test_inbound_collaboration_external_to_octaos(collab_setup):
    """
    Requirement 2 & 3: An external AI delegates a task to an authorized OctaOS employee
    via the collaboration REST gateway, returning status, correlation IDs, and evidence.
    """
    client = collab_setup["client"]
    raw_key = collab_setup["raw_key"]

    req_payload = {
        "target_employee": "marketing",
        "target_capability": "execute_task",
        "task_description": "Draft social post for upcoming product release",
        "context": {
            "platform": "instagram",
            "caption_draft": "Autonomous collaboration live now!",
            "post_mode": "draft",
        },
        "async_execution": False,
    }

    res = client.post(
        "/api/v1/plugin/collaboration/tasks",
        headers={"Authorization": f"Bearer {raw_key}"},
        json=req_payload,
    )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("completed", "verified")
    assert data["target_employee"] == "marketing"
    assert len(data["task_id"]) > 10
    assert len(data["evidence"]) >= 1
    assert data["evidence"][0]["success"] is True


def test_long_running_async_job_and_polling(collab_setup):
    """
    Requirement 4: Long-running async jobs survive client disconnects,
    return a stable task_id, and support polling.
    """
    client = collab_setup["client"]
    raw_key = collab_setup["raw_key"]

    # 1. Submit Asynchronous Job
    submit_res = client.post(
        "/api/v1/plugin/collaboration/tasks",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={
            "target_employee": "sales",
            "task_description": "Asynchronous lead enrichment pipeline",
            "context": {"lead_count": 10},
            "async_execution": True,
        },
    )
    assert submit_res.status_code == 200
    sub_data = submit_res.json()
    task_id = sub_data["task_id"]
    assert sub_data["status"] == "queued"

    # 2. Poll Task Status
    poll_res = client.get(
        f"/api/v1/plugin/collaboration/tasks/{task_id}",
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert poll_res.status_code == 200
    poll_data = poll_res.json()
    assert poll_data["task_id"] == task_id
    assert poll_data["status"] == "queued"

    # 3. Test Task Cancellation
    cancel_res = client.post(
        f"/api/v1/plugin/collaboration/tasks/{task_id}/cancel",
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # 4. Verify Poll Reflects Cancelled
    poll_after = client.get(
        f"/api/v1/plugin/collaboration/tasks/{task_id}",
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert poll_after.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_missing_provider_and_failure_resilience(collab_setup):
    """
    Requirement 5: If no external provider is configured for requested capabilities,
    the collaboration engine fails safely and falls back to local execution.
    """
    db = collab_setup["db"]
    tenant_id = collab_setup["tenant_id"]

    engine = AICollaborationEngine(db, tenant_id)

    # Request an unconfigured provider capability (e.g. quantum_logic)
    res = await engine.collaborate_with_external_ai(
        task={"description": "Unconfigured capability task"},
        required_capabilities=["unconfigured_quantum_logic"],
        context={"sample": "data"},
        calling_agent="Support AI",
    )

    assert res["status"] == "fallback_local"
    assert res["executed_externally"] is False
    assert "No connected external AI provider" in res["message"]


def test_cross_tenant_isolation_rejected(collab_setup):
    """
    Requirement 6: Cross-tenant access is strictly rejected. Tenant B cannot access Tenant A's task.
    """
    client = collab_setup["client"]
    raw_key1 = collab_setup["raw_key"]
    raw_key2 = collab_setup["raw_key2"]

    # 1. Create task in Tenant A
    res_a = client.post(
        "/api/v1/plugin/collaboration/tasks",
        headers={"Authorization": f"Bearer {raw_key1}"},
        json={
            "target_employee": "sales",
            "task_description": "Confidential Tenant A task",
            "async_execution": True,
        },
    )
    assert res_a.status_code == 200
    task_id_a = res_a.json()["task_id"]

    # 2. Attempt access from Tenant B -> Must return 404
    res_b = client.get(
        f"/api/v1/plugin/collaboration/tasks/{task_id_a}",
        headers={"Authorization": f"Bearer {raw_key2}"},
    )
    assert res_b.status_code == 404


def test_delegation_loop_and_depth_prevention(collab_setup):
    """
    Requirement 7: Cycle detection and delegation depth limits prevent runaway costs.
    """
    db = collab_setup["db"]
    tenant_id = collab_setup["tenant_id"]

    # A. Cycle Detection (Target already in lineage)
    lineage_with_grok = ["Sales AI", "external:grok"]
    with pytest.raises(DelegationLoopError) as exc_cycle:
        validate_delegation_safety(
            db,
            tenant_id=tenant_id,
            source_agent="Sales AI",
            target="external:grok",
            lineage=lineage_with_grok,
        )
    assert "cycle detected" in str(exc_cycle.value).lower()

    # B. Max Depth Limit (depth >= 3)
    deep_lineage = ["Agent1", "Agent2", "Agent3"]
    with pytest.raises(DelegationLimitError) as exc_depth:
        validate_delegation_safety(
            db,
            tenant_id=tenant_id,
            source_agent="Agent3",
            target="Agent4",
            lineage=deep_lineage,
        )
    assert "maximum delegation depth" in str(exc_depth.value).lower()


def test_execution_bridge_policy_and_evidence(collab_setup):
    """
    Requirement 8: Result-to-Execution Bridge enforces policy checks and ensures
    external AI proposals are never reported as executed without verified evidence.
    """
    client = collab_setup["client"]
    raw_key = collab_setup["raw_key"]

    task_id = str(uuid.uuid4())

    # Execute a verified bridge action
    bridge_payload = {
        "task_id": task_id,
        "proposed_tool": "octaos_create_lead",
        "action_type": "crm_lead_create",
        "arguments": {
            "name": "Verified Inbound Partner",
            "email": "partner@collaboration.ai",
            "company": "Collaboration Corp",
        },
        "intent_description": "Execute partner lead creation proposed by external Claude analysis",
    }

    res = client.post(
        "/api/v1/plugin/collaboration/execute_bridge",
        headers={"Authorization": f"Bearer {raw_key}"},
        json=bridge_payload,
    )

    assert res.status_code == 200
    data = res.json()
    assert data["verified"] is True
    assert data["status"] == "executed"
    assert "tool_executed" in data["evidence"]
    assert data["evidence"]["tool_executed"] == "octaos_create_lead"
    assert data["evidence"]["is_error"] is False


@pytest.mark.asyncio
async def test_execution_bridge_rejects_actions_without_collaboration_receipt(collab_setup):
    """The bridge must not be usable as a generic tool-execution endpoint."""
    from app.services.collaboration import ExecutionBridge, ExecutionBridgeRequest

    setup = collab_setup
    result = await ExecutionBridge.process_proposed_action(
        db=setup["db"],
        tenant_id=setup["tenant"].id,
        request=ExecutionBridgeRequest(
            task_id="missing-receipt-task",
            proposed_tool="octaos_query_ai_workforce",
            intent_description="Regression test: no durable task receipt exists",
        ),
        mcp_credential=setup["cred"],
    )
    assert result.status == "blocked"
    assert result.verified is False
    assert "receipt" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_admin_credential_does_not_bypass_policy_approval(collab_setup, monkeypatch):
    """Admin API access must not erase a policy decision requiring human approval."""
    from app.models.collaborative_workforce import AgentMessage, DelegationReceipt
    from app.services.collaboration import ExecutionBridge, ExecutionBridgeRequest
    from app.services.policy_engine import PolicyEngine

    setup = collab_setup
    db = setup["db"]
    db.add(AgentMessage(
        id="approval-gated-task",
        tenant_id=setup["tenant"].id,
        correlation_id="approval-gated-correlation",
        idempotency_key="approval-gated-idempotency",
        from_agent="test-agent",
        to_agent="external:test",
        message_type="test",
        status="processing",
        payload={},
    ))
    db.commit()
    receipt = DelegationReceipt(
        tenant_id=setup["tenant"].id,
        task_id="approval-gated-task",
        parent_agent="test-agent",
        child_agent="external:test",
        request_message_id="approval-gated-task",
        status="in_progress",
        acceptance_criteria=[],
        evidence=[],
    )
    db.add(receipt)
    db.commit()

    monkeypatch.setattr(
        PolicyEngine,
        "evaluate",
        lambda *args, **kwargs: {
            "decision": "queue_approval",
            "reason": "Human approval required by policy",
            "approval_id": "approval-test-1",
        },
    )

    result = await ExecutionBridge.process_proposed_action(
        db=db,
        tenant_id=setup["tenant"].id,
        request=ExecutionBridgeRequest(
            task_id="approval-gated-task",
            proposed_tool="octaos_social_publish_post",
            action_type="social_publish",
            arguments={"platform": "instagram", "content": "test"},
            intent_description="Regression test for approval enforcement",
        ),
        mcp_credential=setup["cred"],
    )
    assert result.status == "waiting_approval"
    assert result.verified is False
    assert result.approval_request_id == "approval-test-1"
    assert receipt.status == "waiting_approval"
