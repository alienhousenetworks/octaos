import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone, timedelta

from app.models.base import Base, APICredential
from app.models.verticals import Lead, ContentPost, Ticket, Transaction, Candidate
from app.models.deal_room import DealRoom
from app.models.agents import ActivityLog
from app.services.agents.orchestrator import OrchestratorAgent
from app.schemas.orchestrator_briefing import BriefingResponse, MetricsPayload, MetricValue
from app.services.analytics.narrative_service import GroundingValidator


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.mark.asyncio
async def test_orchestrator_analytics_mode(db_session):
    tenant = "tenant-analytics-test"
    now = datetime.now(timezone.utc)

    # Seed 20 unassigned leads to trigger real operational bottleneck finding
    for i in range(20):
        db_session.add(Lead(
            id=f"lead-{i}",
            tenant_id=tenant,
            name=f"Founder {i}",
            status="captured",
            assigned_to=None,
            created_at=now,
        ))

    db_session.add(DealRoom(
        id="deal-1",
        tenant_id=tenant,
        company_name="Acme Corp",
        domain="acme.com",
        stage="proposal",
        annual_revenue_usd=75000.0,
        created_at=now,
    ))

    db_session.commit()

    agent = OrchestratorAgent(db_session, tenant)
    result = await agent.handle_prompt("Generate a full executive report on our current operations and weaknesses")

    assert result["mode"] == "analytics"
    assert "briefing" in result
    briefing = BriefingResponse.model_validate(result["briefing"])
    
    assert briefing.metrics.items["leads.total"].value == 20.0
    assert briefing.metrics.items["deals.pipeline_value"].value == 75000.0
    assert len(briefing.charts) == 5
    assert len(briefing.findings) >= 1
    assert len(briefing.improvement_plan) >= 1
    assert len(briefing.trace) == 10  # All 10 agents recorded
    assert all(t.agent_id in range(1, 11) for t in briefing.trace)


@pytest.mark.asyncio
async def test_orchestrator_clean_workspace_no_fake_findings(db_session):
    tenant = "tenant-clean-test"
    agent = OrchestratorAgent(db_session, tenant)
    result = await agent.handle_prompt("Generate a full executive report on our current operations and weaknesses")

    assert result["mode"] == "analytics"
    briefing = BriefingResponse.model_validate(result["briefing"])
    assert briefing.empty_state is True
    # Clean workspace must have 0 fake findings and 0 fake improvement items
    assert len(briefing.findings) == 0
    assert len(briefing.improvement_plan) == 0
    assert "No active leads" in briefing.briefing_text or "Clean state" in briefing.briefing_text or briefing.empty_state is True


@pytest.mark.asyncio
async def test_orchestrator_hybrid_mode(db_session):
    tenant = "tenant-hybrid-test"
    now = datetime.now(timezone.utc)

    # Seed stalled leads to trigger hybrid remediation
    for i in range(20):
        db_session.add(Lead(
            id=f"lead-h-{i}",
            tenant_id=tenant,
            name=f"Lead {i}",
            status="captured",
            assigned_to="unassigned",
            created_at=now,
        ))
    db_session.commit()

    agent = OrchestratorAgent(db_session, tenant)
    result = await agent.handle_prompt("Why is conversion low, and fix it")

    assert result["mode"] == "hybrid"
    assert "briefing" in result
    assert "plan" in result
    assert result["plan"]["status"] == "pending_approval"
    assert len(result["plan"]["actions"]) >= 1


def test_grounding_validator():
    metrics = MetricsPayload(
        tenant_id="t-val",
        harvested_at="2026-10-04T12:00:00Z",
        empty_state=False,
        items={
            "leads.total": MetricValue(
                metric_id="leads.total",
                name="Total Leads",
                value=150.0,
                formatted="150",
                unit="count",
                direction="up",
                category="sales",
            ),
            "leads.conversion_rate": MetricValue(
                metric_id="leads.conversion_rate",
                name="Conversion Rate",
                value=24.5,
                formatted="24.5%",
                unit="%",
                direction="up",
                category="sales",
            )
        }
    )

    valid_text = "Our operations encompass 150 leads with a 24.5% conversion rate."
    is_valid, unanchored = GroundingValidator.validate(valid_text, metrics)
    assert is_valid is True
    assert len(unanchored) == 0

    hallucinated_text = "We generated $9,999,999 revenue and closed 8,888 deals."
    is_valid, unanchored = GroundingValidator.validate(hallucinated_text, metrics)
    assert is_valid is False
    assert len(unanchored) >= 1
