"""Hermetic tests for Phase 3: Intent Signal Bus, Convergence, and Territory Route Planning."""
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base, Tenant, User
from app.models.sales_intelligence import SalesCompany, SalesSignal, SignalEvidence, SourceCost
from app.models.deal_room import DealRoom
from app.services.sales_os.signals.bus import IntentSignalBus
from app.services.sales_os.agents.territory_route import TerritoryRoutePlannerAgent
from app.services.sales_os.attribution.source_roi import summarize_roi


@pytest.fixture
def signal_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    tenant = Tenant(id="test_signal_tenant", name="Signal Tenant", is_active=True)
    session.add(tenant)

    company = SalesCompany(
        id="comp_datadog_101",
        tenant_id="test_signal_tenant",
        canonical_domain="datadog.com",
        display_name="Datadog Technologies",
        industry="Cloud Monitoring",
        intent_score=20.0,
    )
    session.add(company)
    session.commit()

    yield session, tenant, company
    session.close()


def test_intent_signal_ingestion_and_provenance(signal_db):
    session, tenant, company = signal_db
    bus = IntentSignalBus(session, tenant.id)

    res = bus.ingest_signal(
        company_id=company.id,
        signal_type="ats_hiring_surge",
        family="hiring",
        summary="Greenhouse ATS surge: 18 DevOps engineer openings added this week.",
        base_strength=80.0,
        source_confidence=0.95,
        half_life_days=30,
        source_key="greenhouse",
    )

    assert res["company_id"] == company.id
    assert res["signal_type"] == "ats_hiring_surge"
    assert res["family"] == "hiring"
    assert res["effective_intent_score"] is not None

    # Verify company intent_score was updated
    session.refresh(company)
    assert company.intent_score > 0.0

    # Verify immutable evidence was anchored
    ev = session.query(SignalEvidence).filter_by(company_id=company.id).first()
    assert ev is not None
    assert ev.source_key == "greenhouse"
    assert ev.confidence == 0.95


def test_multi_source_convergence_bonus(signal_db):
    session, tenant, company = signal_db
    bus = IntentSignalBus(session, tenant.id)

    # Ingest 3 distinct signal families: funding, hiring, and leadership
    bus.ingest_signal(
        company_id=company.id,
        signal_type="series_c_funding",
        family="funding",
        summary="Raised $50M Series C round led by Index Ventures.",
        base_strength=90.0,
        source_confidence=0.98,
        half_life_days=60,
        source_key="crunchbase",
    )

    bus.ingest_signal(
        company_id=company.id,
        signal_type="ats_hiring_surge",
        family="hiring",
        summary="Opened 12 enterprise sales positions.",
        base_strength=75.0,
        source_confidence=0.90,
        half_life_days=30,
        source_key="lever_ats",
    )

    res3 = bus.ingest_signal(
        company_id=company.id,
        signal_type="vp_sales_hire",
        family="leadership",
        summary="Appointed former Snowflake VP of Sales as new CRO.",
        base_strength=85.0,
        source_confidence=0.95,
        half_life_days=45,
        source_key="linkedin_talent",
    )

    # Convergence bonus should trigger for funding + hiring + leadership bundle (+15.0 bonus)
    conv = res3.get("convergence", {})
    assert conv.get("bonus", 0.0) >= 15.0
    assert "funding_hiring_leadership" in conv.get("reasons", [])

    # Verify company score reflects stacked convergence
    session.refresh(company)
    assert company.intent_score >= 80.0


@pytest.mark.asyncio
async def test_territory_route_planner_agent(signal_db):
    session, tenant, company = signal_db
    # Seed 2 deal rooms for territory clustering
    r1 = DealRoom(
        tenant_id=tenant.id,
        company_name="CloudScale AI",
        domain="cloudscale.ai",
        city="San Francisco",
        country="USA",
        stage="qualified",
        priority_index=0.92,
    )
    r2 = DealRoom(
        tenant_id=tenant.id,
        company_name="DataMesh Systems",
        domain="datamesh.io",
        city="San Francisco",
        country="USA",
        stage="in_cadence",
        priority_index=0.88,
    )
    session.add_all([r1, r2])
    session.commit()

    agent = TerritoryRoutePlannerAgent(session, tenant.id)
    result = await agent.execute(
        parameters={
            "rep_id": "rep_alex",
            "start_latitude": 37.7749,
            "start_longitude": -122.4194,
        }
    )

    assert result.data is not None
    plan = result.data
    assert plan.rep_id == "rep_alex"
    assert len(plan.stops) >= 1
    assert plan.total_travel_distance_km >= 0.0


def test_source_roi_attribution():
    costs = [
        {"provider_key": "apollo", "actual_amount": 200.0},
        {"provider_key": "apify_google_maps", "actual_amount": 50.0},
    ]
    outcomes = [
        {"provider_key": "apollo", "outcome_type": "meeting"},
        {"provider_key": "apollo", "outcome_type": "revenue", "amount": 25000.0, "touch_role": "first"},
        {"provider_key": "apify_google_maps", "outcome_type": "verified_lead"},
    ]

    roi = summarize_roi(costs, outcomes)
    assert roi["spend"] == 250.0
    assert roi["meetings"] == 1
    assert roi["revenue"] == 25000.0
    assert roi["cost_per_meeting"] == 250.0
    assert roi["revenue_per_dollar"] == 100.0
