"""
Unit tests for OctaOS Governed Agent & Tool Registry.
"""
import pytest
from app.core.tool_registry import (
    ToolRegistry,
    GovernedTool,
    ToolExecutionError,
    ApprovalRequiredError,
    RiskLevel,
)


@pytest.fixture
def registry():
    # Return singleton instance
    return ToolRegistry.get_instance()


def test_registry_has_default_department_tools(registry):
    tools = registry.list_tools()
    departments = {t.department for t in tools}
    assert "marketing" in departments
    assert "sales" in departments
    assert "hr" in departments
    assert "support" in departments
    assert "real_estate" in departments


def test_registry_filters_by_department(registry):
    sales_tools = registry.list_tools(department="sales")
    assert len(sales_tools) >= 2
    for tool in sales_tools:
        assert tool.department == "sales"


def test_llm_definitions_export(registry):
    definitions = registry.get_llm_definitions(departments=["sales", "real_estate"])
    tool_names = [d["function"]["name"] for d in definitions]
    assert any("sales__query_pipeline" in name or "sales.query_pipeline" in name for name in tool_names)
    assert any("real_estate" in name for name in tool_names)


@pytest.mark.asyncio
async def test_governed_tool_execution_informational(registry):
    result = await registry.execute(
        tool_id="sales.query_pipeline",
        tenant_id="tenant-123",
        inputs={"stage": "negotiation"},
        user_context={"role": "sales_rep", "permissions": ["sales:read"]},
    )
    assert result["success"] is True
    assert result["tool_id"] == "sales.query_pipeline"


@pytest.mark.asyncio
async def test_governed_tool_approval_gate_blocks_critical_action(registry):
    # sales.approve_booking_discount is marked requires_human_approval=True
    with pytest.raises(ApprovalRequiredError) as exc_info:
        await registry.execute(
            tool_id="sales.approve_booking_discount",
            tenant_id="tenant-123",
            inputs={"deal_id": "deal-456", "discount_pct": 5.0, "rationale": "CEO exception"},
            user_context={"role": "sales_rep", "pre_approved": False},
        )
    assert "Human approval required" in str(exc_info.value)
    assert exc_info.value.action_key == "sales.approve_booking_discount"


@pytest.mark.asyncio
async def test_governed_tool_succeeds_when_pre_approved(registry):
    result = await registry.execute(
        tool_id="sales.approve_booking_discount",
        tenant_id="tenant-123",
        inputs={"deal_id": "deal-456", "discount_pct": 5.0, "rationale": "CEO exception"},
        user_context={"role": "admin", "pre_approved": True, "is_superuser": True},
    )
    assert result["success"] is True


@pytest.mark.asyncio
async def test_governed_tool_permission_denial(registry):
    # Member without sales:read trying to access a tool requiring permission
    with pytest.raises(ToolExecutionError) as exc_info:
        await registry.execute(
            tool_id="marketing.generate_campaign_draft",
            tenant_id="tenant-123",
            inputs={"campaign_name": "Summer Launch", "target_audience": "Investors"},
            user_context={"role": "guest", "permissions": [], "is_superuser": False},
        )
    assert "lacks required permission" in str(exc_info.value)
