"""Unit tests for Field Sales Mapping Connectors, Budget Controller, Optimizer, and Recovery Engine."""
import pytest
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base, Tenant, User
from app.models.real_estate import RealEstateProject, RealEstateUnit, RealEstateSiteVisit
from app.models.field_sales import SalespersonFieldStatus, FieldScheduleRecoveryProposal, ConnectorUsageAudit
from app.models.verticals import Lead
from app.services.sales_os.field_sales.connectors.local_fallback import LocalRoadsFallbackConnector
from app.services.sales_os.field_sales.connectors.budget_controller import ConnectorBudgetController
from app.services.sales_os.field_sales.engine.optimizer import ScheduleOptimizer
from app.services.sales_os.field_sales.engine.recovery import ScheduleRecoveryEngine
from app.services.sales_os.field_sales.engine.nlp_agent import NaturalLanguageDispatchAgent


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    # Seed Tenant & User
    tenant = Tenant(id="tenant_fs", name="Skyline Real Estate")
    user = User(
        id="user_agent_1",
        tenant_id="tenant_fs",
        email="agent1@skyline.com",
        name="John Agent",
        hashed_password="pw",
    )
    user2 = User(
        id="user_agent_2",
        tenant_id="tenant_fs",
        email="agent2@skyline.com",
        name="Sarah Specialist",
        hashed_password="pw",
    )
    project = RealEstateProject(
        id="proj_1",
        tenant_id="tenant_fs",
        name="Skyline Horizon Towers",
        location="Whitefield, Bangalore",
        latitude=12.9698,
        longitude=77.7500,
    )
    lead = Lead(
        id="lead_1",
        tenant_id="tenant_fs",
        name="Amit Sharma",
        phone="+919876543210",
        email="amit.sharma@example.com",
        company="Self",
        source="Portal",
        status="qualified",
        score=85,
        need_of_what="3BHK Luxury ₹2.2Cr",
    )
    session.add_all([tenant, user, user2, project, lead])
    session.commit()

    yield session
    session.close()


@pytest.mark.asyncio
async def test_local_fallback_connector_curvature_and_speed():
    connector = LocalRoadsFallbackConnector()
    # Test route between two Bangalore points ~10km apart
    origin = (12.9716, 77.5946)
    dest = (12.9698, 77.7500)

    route = await connector.calculate_route(origin[0], origin[1], dest[0], dest[1])
    assert route["status"] == "ESTIMATED_OFFLINE"
    assert route["distance_meters"] > 10000  # Road curvature factor 1.35 applied
    assert route["duration_seconds"] > 600   # Realistic urban driving time >10 mins
    assert "km" in route["distance_text"]
    assert "mins" in route["duration_text"]


@pytest.mark.asyncio
async def test_connector_budget_controller_caching_and_audit(test_db):
    ctrl = ConnectorBudgetController(test_db, "tenant_fs")

    # Geocode call 1 (miss)
    res1 = await ctrl.geocode("Skyline Horizon Towers, Whitefield")
    assert res1["latitude"] is not None
    assert res1.get("cached") is not True

    # Geocode call 2 (hit)
    res2 = await ctrl.geocode("Skyline Horizon Towers, Whitefield")
    assert res2.get("cached") is True

    # Verify audit records in DB
    stats = ctrl.get_budget_stats()
    assert stats["daily_quota"] == 500
    assert stats["calls_used"] == 1
    assert stats["cache_hits"] == 1
    assert stats["status"] == "HEALTHY"


@pytest.mark.asyncio
async def test_schedule_optimizer_orders_visits_with_transit_buffers(test_db):
    # Schedule two visits for today
    today = date.today()
    now_dt = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc).replace(hour=10)

    visit1 = RealEstateSiteVisit(
        id="v1",
        tenant_id="tenant_fs",
        lead_id="lead_1",
        project_id="proj_1",
        scheduled_at=now_dt,
        assigned_agent="user_agent_1",
        duration_minutes=45,
    )
    visit2 = RealEstateSiteVisit(
        id="v2",
        tenant_id="tenant_fs",
        lead_id="lead_1",
        project_id="proj_1",
        scheduled_at=now_dt + timedelta(hours=2),
        assigned_agent="user_agent_1",
        duration_minutes=45,
    )
    test_db.add_all([visit1, visit2])
    test_db.commit()

    optimizer = ScheduleOptimizer(test_db, "tenant_fs")
    res = await optimizer.optimize_day_schedule(today, agent_id="user_agent_1")

    assert res["status"] == "SUCCESS"
    assert res["visits_count"] == 2
    assert len(res["optimized_routes"]) == 1
    route = res["optimized_routes"][0]
    assert route["agent_id"] == "user_agent_1"
    assert route["visits"][0]["sequence"] == 1
    assert route["visits"][1]["sequence"] == 2
    assert route["visits"][1]["travel_minutes"] >= 5


def test_schedule_recovery_engine_cascades_and_applies(test_db):
    now_dt = datetime.now(timezone.utc)
    v1 = RealEstateSiteVisit(
        id="v_delayed",
        tenant_id="tenant_fs",
        lead_id="lead_1",
        project_id="proj_1",
        scheduled_at=now_dt,
        assigned_agent="user_agent_1",
    )
    v2 = RealEstateSiteVisit(
        id="v_subsequent",
        tenant_id="tenant_fs",
        lead_id="lead_1",
        project_id="proj_1",
        scheduled_at=now_dt + timedelta(minutes=40),
        assigned_agent="user_agent_1",
    )
    test_db.add_all([v1, v2])
    test_db.commit()

    recovery = ScheduleRecoveryEngine(test_db, "tenant_fs")
    proposal_res = recovery.detect_and_propose_recovery(
        delayed_visit_id="v_delayed",
        delay_minutes=35,
        delay_reason="Client requested inspecting second penthouse",
    )

    assert proposal_res["status"] == "pending_review"
    assert proposal_res["affected_visits_count"] == 1
    diff = proposal_res["proposed_changes"][0]
    assert diff["visit_id"] == "v_subsequent"
    assert diff["action"] == "time_adjusted"
    assert "Proposed" in diff["rationale"] or "Adjusted" in diff["rationale"]

    # Apply proposal
    apply_res = recovery.apply_proposal(proposal_res["proposal_id"], "dispatcher_user")
    assert apply_res["status"] == "applied"

    test_db.refresh(v2)
    v2_dt = v2.scheduled_at if v2.scheduled_at.tzinfo else v2.scheduled_at.replace(tzinfo=timezone.utc)
    assert v2_dt > now_dt + timedelta(minutes=40)


@pytest.mark.asyncio
async def test_nlp_dispatch_agent_intent_recognition(test_db):
    agent = NaturalLanguageDispatchAgent(test_db, "tenant_fs")

    # Command: Plan tomorrow
    res1 = await agent.execute_command("Plan tomorrow's property visits for all available salespeople", "admin_user")
    assert res1["intent"] == "PLAN_TOMORROW"
    assert "Tomorrow" in res1["suggested_actions"][0]

    # Command: Nearby high-priority
    res2 = await agent.execute_command("Find high-priority families near the next visit who can tour today", "admin_user")
    assert res2["intent"] == "FIND_NEARBY_PRIORITY"
    assert len(res2["data"]["leads"]) >= 1
    assert res2["data"]["leads"][0]["name"] == "Amit Sharma"
