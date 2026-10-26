import asyncio

import pytest

from app.services.agent_runtime.protocol import AgentEvent, AgentEventType
from app.services.agents.tools import tool_registry
from app.services.runtime_governance.tool_policy import authorize_tool_call


def test_agent_contract_public_event_redacts_credentials_and_private_reasoning():
    event = AgentEvent(
        tenant_id="tenant-a",
        run_id="run-a",
        event_type=AgentEventType.PROGRESS,
        message="Working with api_key=super-secret",
        payload={
            "progress": "Found three records",
            "api_key": "super-secret",
            "chain_of_thought": "private reasoning",
            "count": 3,
        },
    )
    public = event.to_public_dict()
    assert "super-secret" not in str(public)
    assert "chain_of_thought" not in public["payload"]
    assert public["payload"]["count"] == 3


def test_tool_dispatch_fails_closed_without_server_authorization_context():
    async def run():
        with pytest.raises(PermissionError, match="TOOL_POLICY_CONTEXT_REQUIRED"):
            await tool_registry.execute_tool(
                name="web_search",
                payload={"query": "example"},
                db=object(),
                tenant_id="tenant-a",
            )
    asyncio.run(run())


def test_tool_dispatch_rejects_missing_grant_before_side_effect():
    async def run():
        with pytest.raises(PermissionError, match="TOOL_NOT_GRANTED"):
            await tool_registry.execute_tool(
                name="web_search",
                payload={"query": "example"},
                db=object(),
                tenant_id="tenant-a",
                context={"request_tenant_id": "tenant-a", "granted_tools": []},
            )
    asyncio.run(run())


def test_high_risk_tool_requires_execution_time_approval():
    decision = authorize_tool_call(
        tenant_id="tenant-a",
        request_tenant_id="tenant-a",
        tool_name="email.send",
        granted_tools=["email.send"],
        connection_active=True,
    )
    assert not decision.allowed
    assert decision.approval_required
    assert decision.reason == "APPROVAL_REQUIRED"


def test_tool_policy_rejects_tenant_mismatch():
    decision = authorize_tool_call(
        tenant_id="tenant-a",
        request_tenant_id="tenant-b",
        tool_name="web_search",
        granted_tools=["web_search"],
        connection_active=True,
    )
    assert not decision.allowed
    assert decision.reason == "TENANT_MISMATCH"
