"""Unit tests for Enterprise Agent Runtime Kernel, ToolRegistry, and Canonical Reconciliation."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base, Tenant, User
from app.models.verticals import Lead
from app.models.deal_room import DealRoom, BuyingCommitteeMember
from app.models.sales_intelligence import SalesCompany, AccountContact, SalesOpportunity
from app.models.agent_runtime import AgentRun, AgentTask, ToolInvocation, AgentHandoff
from app.services.sales_os.runtime.tool_registry import tool_registry, ToolExecutionError
from app.services.sales_os.runtime.orchestrator import SalesOrchestrator
from app.services.sales_os.governance.suppression import SuppressionService
from app.services.sales.sync_bridge import SalesSyncBridge


@pytest.fixture
def runtime_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    tenant = Tenant(id="tenant_runtime", name="Runtime Enterprises", subdomain="runtime-ent", is_active=True)
    session.add(tenant)
    session.commit()

    yield session
    session.close()


@pytest.mark.asyncio
async def test_tool_registry_execution_and_verification(runtime_db):
    """Verifies that registered tools execute, enforce tenant checks, and verify DB side effects."""
    deal_room = DealRoom(
        tenant_id="tenant_runtime",
        company_name="Acme Corp",
        domain="acme.com",
        stage="discovered",
    )
    runtime_db.add(deal_room)
    runtime_db.commit()

    # Execute tool to add a buying committee member
    result = await tool_registry.execute(
        tool_name="upsert_buying_committee_member",
        tenant_id="tenant_runtime",
        parameters={
            "deal_room_id": deal_room.id,
            "name": "Jane Doe",
            "email": "jane@acme.com",
            "title": "Chief Technology Officer",
            "role_type": "economic_buyer",
        },
        db=runtime_db,
        agent_id="buying_committee_agent",
    )

    assert result["status"] == "success"
    assert result["verified"] is True
    assert "Verified BuyingCommitteeMember" in result["verification_details"]

    # Verify audit log in agent_tool_invocations
    invocations = runtime_db.query(ToolInvocation).filter_by(tenant_id="tenant_runtime").all()
    assert len(invocations) >= 1
    assert invocations[0].tool_name == "upsert_buying_committee_member"
    assert invocations[0].verified is True


@pytest.mark.asyncio
async def test_tool_registry_suppression_enforcement(runtime_db):
    """Verifies that external tools fail fast if the recipient is on the tenant suppression list."""
    suppression = SuppressionService(runtime_db, "tenant_runtime")
    suppression.add_suppression(
        identifier_type="email",
        identifier_value="blocked@competitor.com",
        reason="unsubscribed_dnc",
        origin="test",
    )

    @tool_registry.register(
        name="test_outreach_send",
        description="Test outbound dispatch tool",
        permission="outreach:dispatch",
        is_external=True,
    )
    def dummy_send(db, tenant_id, email, message):
        return {"sent": True}

    with pytest.raises(ToolExecutionError) as exc_info:
        await tool_registry.execute(
            tool_name="test_outreach_send",
            tenant_id="tenant_runtime",
            parameters={"email": "blocked@competitor.com", "message": "Hello"},
            db=runtime_db,
            agent_id="outreach_agent",
        )

    assert exc_info.value.code == "suppressed_email"


def test_sales_orchestrator_lifecycle_and_idempotency(runtime_db):
    """Verifies orchestrator durable run creation, idempotency, handoffs, and completion."""
    orchestrator = SalesOrchestrator(runtime_db, "tenant_runtime")

    run1 = orchestrator.start_run(
        goal="Discover buying committee for Skynet",
        idempotency_key="idemp_skynet_001",
    )
    assert run1.status == "running"

    # Second start with same idempotency key must return the same run
    run2 = orchestrator.start_run(
        goal="Discover buying committee for Skynet duplicate attempt",
        idempotency_key="idemp_skynet_001",
    )
    assert run1.id == run2.id

    # Test handoff
    handoff = orchestrator.execute_handoff(
        run_id=run1.id,
        from_agent="market_research_agent",
        to_agent="buying_committee_agent",
        objective="Map VP Engineering and CTO",
        payload={"domain": "skynet.com"},
    )
    assert handoff.status == "accepted"
    assert handoff.from_agent == "market_research_agent"

    # Complete run
    completed_run = orchestrator.complete_run(
        run_id=run1.id,
        output_payload={"identified_members": 2},
        tokens_used=450,
        cost_usd=0.003,
    )
    assert completed_run.status == "completed"
    assert completed_run.tokens_used == 450


def test_canonical_reconciliation_bridge(runtime_db):
    """Verifies that bulk reconciliation links unlinked leads to canonical SalesCompany and DealRoom."""
    bridge = SalesSyncBridge(runtime_db, "tenant_runtime")

    # Insert unlinked legacy leads
    lead1 = Lead(
        tenant_id="tenant_runtime",
        name="Alex Mercer",
        email="alex@gentek.com",
        company="Gentek Solutions",
        source="apollo",
        status="captured",
        score=82,
        data={"website": "https://gentek.com", "title": "VP Engineering"}
    )
    lead2 = Lead(
        tenant_id="tenant_runtime",
        name="Dana Mercer",
        email="dana@gentek.com",
        company="Gentek Solutions",
        source="apollo",
        status="captured",
        score=75,
        data={"website": "https://gentek.com", "title": "Chief Information Officer"}
    )
    runtime_db.add_all([lead1, lead2])
    runtime_db.commit()

    reconcile_result = bridge.reconcile_tenant_leads_to_canonical()

    assert reconcile_result["scanned"] == 2
    assert reconcile_result["promoted_to_canonical"] == 2
    assert len(reconcile_result["errors"]) == 0

    # Verify both leads resolve to the same canonical company domain
    company = runtime_db.query(SalesCompany).filter_by(tenant_id="tenant_runtime", canonical_domain="gentek.com").first()
    assert company is not None
    assert lead1.sales_company_id == company.id
    assert lead2.sales_company_id == company.id

    # Verify deal room is marked multi-threaded (2 members)
    deal_room = runtime_db.query(DealRoom).filter_by(tenant_id="tenant_runtime", domain="gentek.com").first()
    assert deal_room is not None
    assert deal_room.is_multi_threaded is True
