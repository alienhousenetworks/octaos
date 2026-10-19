import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone, timedelta

from app.models.base import Base, ProviderUsage
from app.models.verticals import Lead, ContentPost, Ticket, Transaction, Candidate
from app.models.deal_room import DealRoom
from app.models.agents import ActivityLog
from app.models.teams import AgentMetric
from app.models.flow_engine import FlowRun, UsageEvent, StepRun
from app.services.analytics.metrics_service import MetricsService
from app.services.analytics.chart_builders import build_all_charts
from app.services.analytics.detectors import detect_all_findings
from app.api.v1.endpoints.dashboard import get_dashboard_metrics


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    # We only create tables for the models needed in the test
    Base.metadata.create_all(engine, tables=[
        Lead.__table__,
        ContentPost.__table__,
        Ticket.__table__,
        DealRoom.__table__,
        Transaction.__table__,
        Candidate.__table__,
        ActivityLog.__table__,
        AgentMetric.__table__,
        FlowRun.__table__,
        StepRun.__table__,
        UsageEvent.__table__,
        ProviderUsage.__table__,
    ])
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_empty_tenant_metrics(in_memory_db):
    service = MetricsService(in_memory_db, "tenant-empty")
    payload = service.harvest()
    
    assert payload.empty_state is True
    assert payload.items["leads.total"].value == 0
    assert payload.items["deals.pipeline_value"].value == 0
    
    charts = build_all_charts(payload)
    assert len(charts) == 5
    for c in charts:
        assert "data" in c.spec
        assert "layout" in c.spec
        
    findings = detect_all_findings(payload)
    assert len(findings) == 0


def test_populated_tenant_metrics_and_detectors(in_memory_db):
    tenant = "tenant-struggling"
    now = datetime.now(timezone.utc)
    
    # Seed 30 leads (all captured, unassigned)
    for i in range(30):
        in_memory_db.add(Lead(
            id=f"lead-{i}",
            tenant_id=tenant,
            name=f"Lead {i}",
            status="captured",
            assigned_to="unassigned",
            created_at=now,
        ))
        
    # Seed 10 tickets (6 open for 72 hours -> stalled)
    for i in range(10):
        in_memory_db.add(Ticket(
            id=f"ticket-{i}",
            tenant_id=tenant,
            subject=f"Ticket {i}",
            status="open" if i < 6 else "resolved",
            created_at=now - timedelta(hours=72) if i < 6 else now,
        ))
        
    # Seed 3 deal rooms
    for i in range(3):
        in_memory_db.add(DealRoom(
            id=f"deal-{i}",
            tenant_id=tenant,
            company_name=f"Acme {i}",
            domain=f"acme{i}.com",
            stage="qualified",
            annual_revenue_usd=50000.0,
            created_at=now,
        ))
        
    in_memory_db.commit()
    
    service = MetricsService(in_memory_db, tenant)
    payload = service.harvest()
    
    assert payload.empty_state is False
    assert payload.items["leads.total"].value == 30
    assert payload.items["leads.unassigned_count"].value == 30
    assert payload.items["leads.uncontacted_count"].value == 30
    assert payload.items["deals.pipeline_value"].value == 150000.0
    assert payload.items["tickets.sla_breach_rate"].value == 60.0 # 6 out of 10 stalled
    
    # Verify chart builders
    charts = build_all_charts(payload)
    assert len(charts) == 5
    funnel = next(c for c in charts if c.chart_id == "funnel_chart")
    assert funnel.spec["data"][0]["type"] == "funnel"
    assert funnel.spec["data"][0]["x"][0] == 30 # captured
    
    # Verify rule-based detectors
    findings = detect_all_findings(payload)
    finding_ids = [f.id for f in findings]
    assert "W-LEADS-UNASSIGNED" in finding_ids
    assert "W-LEADS-STALLED" in finding_ids
    assert "W-SUPPORT-SLA" in finding_ids


def test_dashboard_endpoint_metrics(in_memory_db):
    tenant = "tenant-test-dashboard"
    now = datetime.now(timezone.utc)

    # 1. Add some leads
    in_memory_db.add(Lead(id="l1", tenant_id=tenant, name="Lead 1", status="captured", assigned_to="Sales AI", created_at=now))
    in_memory_db.add(Lead(id="l2", tenant_id=tenant, name="Lead 2", status="qualified", assigned_to="Sales AI", created_at=now))

    # 2. Add content post
    in_memory_db.add(ContentPost(id="p1", tenant_id=tenant, platform="linkedin", content="Post 1", status="published", impressions=1200.0, reach=800.0, engagement=60.0, engagement_rate=5.0, created_at=now))

    # 3. Add activity logs
    in_memory_db.add(ActivityLog(id="a1", tenant_id=tenant, agent_name="Marketing AI", action="Post", description="Published post", created_at=now))
    in_memory_db.add(ActivityLog(id="a2", tenant_id=tenant, agent_name="Sales AI", action="Enrich", description="Enriched lead", created_at=now))

    in_memory_db.commit()

    # Call get_dashboard_metrics
    result = get_dashboard_metrics(in_memory_db, tenant)

    # Assert backward-compatible keys exist
    assert "leads_generated" in result
    assert result["leads_generated"] == 2.0
    assert "posts_published" in result
    assert result["posts_published"] == 1.0
    assert "revenue_impact" in result
    assert "ai_cost" in result
    assert "daily_tasks" in result
    assert "totals" in result["daily_tasks"]

    # Assert new rich analytics keys exist
    assert "funnel" in result
    assert result["funnel"]["captured"] == 2
    assert "deal_stages" in result
    assert "channel_performance" in result
    assert len(result["channel_performance"]) == 1
    assert result["channel_performance"][0]["platform"] == "linkedin"
    assert result["channel_performance"][0]["impressions"] == 1200
    assert "ticket_analytics" in result
    assert "lead_metrics" in result
    assert result["lead_metrics"]["total"] == 2
    assert "marketing_metrics" in result
    assert result["marketing_metrics"]["total_posts"] == 1
    assert result["marketing_metrics"]["total_impressions"] == 1200.0
    assert "agent_fleet" in result
    assert result["agent_fleet"]["total_actions"] == 2
    assert "Marketing AI" in result["agent_fleet"]["agent_activity"]
    assert "flow_performance" in result

