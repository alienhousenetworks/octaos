"""Unit tests verifying agent domain boundaries, department-aware ReAct synthesis, and agent.consult tool."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, Tenant
from app.models.flow_engine import AgentDefinition, AgentVersion
from app.services.agents.runtime import AgentRuntime
from app.services.agents.tools import tool_registry, ToolDefinition
from app.services.agents.seeder import seed_system_agents


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    tenant = Tenant(id="test_tenant_boundaries", name="Test Org", subdomain="test-org")
    session.add(tenant)
    session.commit()

    yield session
    session.close()


def test_agent_consult_tool_registered():
    """Verify agent.consult tool is registered in the global tool_registry."""
    tool = tool_registry.get("agent.consult")
    assert tool is not None
    assert "target_agent" in tool.input_schema["properties"]
    assert "task" in tool.input_schema["properties"]
    assert tool.risk_level == "LOW"
    assert tool.approval_required is False


@pytest.mark.asyncio
async def test_agent_consult_self_call_rejected(test_db):
    """Verify an agent cannot consult itself."""
    with pytest.raises(ValueError, match="cannot consult itself"):
        await tool_registry.execute_tool(
            name="agent.consult",
            payload={"target_agent": "marketing_ai", "task": "Brainstorm hooks"},
            db=test_db,
            tenant_id="test_tenant_boundaries",
            context={
                "agent_slug": "marketing_ai",
                "depth": 0,
                "granted_tools": ["agent.consult"],
                "request_tenant_id": "test_tenant_boundaries",
            },
        )


@pytest.mark.asyncio
async def test_agent_consult_recursion_depth_limit(test_db):
    """Verify recursion depth >= 2 raises error to prevent infinite loops."""
    with pytest.raises(ValueError, match="Maximum inter-agent consultation depth"):
        await tool_registry.execute_tool(
            name="agent.consult",
            payload={"target_agent": "sales_ai", "task": "Find target buyer persona"},
            db=test_db,
            tenant_id="test_tenant_boundaries",
            context={
                "agent_slug": "marketing_ai",
                "depth": 2,
                "granted_tools": ["agent.consult"],
                "request_tenant_id": "test_tenant_boundaries",
            },
        )


def test_department_aware_synthesis_prompts():
    """Verify _build_synthesis_prompt isolates marketing from sales leads."""
    runtime = AgentRuntime()
    sample_tools = [
        {
            "tool": "web_search",
            "args": {"query": "alienhouse brand diwali"},
            "result": {
                "results": [
                    {"company": "Alienhouse Living", "title": "Home Decor Lighting for Diwali"}
                ]
            },
        }
    ]

    # 1. Marketing AI
    marketing_agent = AgentDefinition(
        id="mkt_1", name="Marketing AI", slug="marketing_ai", department="marketing", role="Brand Strategist"
    )
    mkt_prompt = runtime._build_synthesis_prompt(
        marketing_agent, "create one spot for Diwali on alienhouse brand with caption Instagram post", sample_tools
    )
    assert "DEPARTMENT FOCUS (Marketing AI)" in mkt_prompt
    assert "DO NOT format output as sales leads" in mkt_prompt
    assert "CRITICAL BUYER VALIDATION & COUNT RULES" not in mkt_prompt
    assert "Website / Opportunity Gap" not in mkt_prompt

    # 2. Sales AI
    sales_agent = AgentDefinition(
        id="sales_1", name="Sales AI", slug="sales_ai", department="sales", role="Sales Specialist"
    )
    sales_prompt = runtime._build_synthesis_prompt(
        sales_agent, "find 10 clinics needing website redesign", sample_tools
    )
    assert "CRITICAL BUYER VALIDATION & COUNT RULES" in sales_prompt
    assert "Website / Opportunity Gap" in sales_prompt
    assert "Action Items / Pitch" in sales_prompt

    # 3. Support AI
    support_agent = AgentDefinition(
        id="sup_1", name="Support AI", slug="support_ai", department="support", role="Support Specialist"
    )
    sup_prompt = runtime._build_synthesis_prompt(
        support_agent, "how do I reset API credentials?", sample_tools
    )
    assert "DEPARTMENT FOCUS (Support AI)" in sup_prompt
    assert "troubleshooting" in sup_prompt
    assert "CRITICAL BUYER VALIDATION & COUNT RULES" not in sup_prompt

    # 4. HR AI
    hr_agent = AgentDefinition(
        id="hr_1", name="HR AI", slug="hr_ai", department="hr", role="HR Recruiter"
    )
    hr_prompt = runtime._build_synthesis_prompt(
        hr_agent, "evaluate senior backend candidates", sample_tools
    )
    assert "DEPARTMENT FOCUS (HR AI)" in hr_prompt
    assert "candidate competencies" in hr_prompt

    # 5. Finance AI
    finance_agent = AgentDefinition(
        id="fin_1", name="Finance AI", slug="finance_ai", department="finance", role="Finance Controller"
    )
    fin_prompt = runtime._build_synthesis_prompt(
        finance_agent, "audit Q3 cloud expenditures", sample_tools
    )
    assert "DEPARTMENT FOCUS (Finance AI)" in fin_prompt
    assert "audit findings" in fin_prompt


def test_system_prompt_role_boundaries():
    """Verify _build_system_prompt adds boundary directive and does not pollute marketing with sales defaults."""
    runtime = AgentRuntime()
    marketing_agent = AgentDefinition(
        id="mkt_1", name="Marketing AI", slug="marketing_ai", department="marketing", role="Brand Strategist"
    )
    mkt_version = AgentVersion(
        agent_id="mkt_1", version=1, system_prompt="You are Marketing AI, elite brand copywriter."
    )
    mkt_sys = runtime._build_system_prompt(marketing_agent, mkt_version, knowledge="", allowed_tools=[])

    assert "ROLE BOUNDARIES & NON-OVERLAP" in mkt_sys
    assert "Marketing AI must not generate B2B sales leads" in mkt_sys
    assert "Indian SMEs: manufacturing, healthcare clinics" not in mkt_sys

    sales_agent = AgentDefinition(
        id="sales_1", name="Sales AI", slug="sales_ai", department="sales", role="Sales Specialist"
    )
    sales_version = AgentVersion(
        agent_id="sales_1", version=1, system_prompt="You are Sales AI, sales intelligence specialist."
    )
    sales_sys = runtime._build_system_prompt(sales_agent, sales_version, knowledge="", allowed_tools=[])
    assert "ROLE BOUNDARIES & NON-OVERLAP" in sales_sys
    assert "Assume sensible defaults (e.g. for Indian SMEs: manufacturing" in sales_sys


def test_seeder_syncs_agent_consult_and_boundaries(test_db):
    """Verify seed_system_agents populates agent.consult tool and boundary prompts."""
    seed_system_agents(test_db)

    # Check Marketing AI
    mkt = test_db.query(AgentDefinition).filter_by(slug="marketing_ai").first()
    assert mkt is not None
    mkt_v = test_db.query(AgentVersion).filter_by(agent_id=mkt.id).order_by(AgentVersion.version.desc()).first()
    assert "agent.consult" in mkt_v.tool_grants
    assert "ROLE BOUNDARIES & COLLABORATION" in mkt_v.system_prompt
    assert "Do NOT generate B2B sales leads" in mkt_v.system_prompt

    # Check Sales AI
    sales = test_db.query(AgentDefinition).filter_by(slug="sales_ai").first()
    assert sales is not None
    sales_v = test_db.query(AgentVersion).filter_by(agent_id=sales.id).order_by(AgentVersion.version.desc()).first()
    assert "agent.consult" in sales_v.tool_grants
    assert "ROLE BOUNDARIES & COLLABORATION" in sales_v.system_prompt
    assert "Do NOT generate marketing content" in sales_v.system_prompt
