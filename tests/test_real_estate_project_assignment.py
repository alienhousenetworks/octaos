"""
Comprehensive test suite for Real Estate Project & Employee Management,
AI Team Suggestions, Admin Team Implementation, and Lead-to-Specialist Dispatch.
"""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base, Tenant, User
from app.models.verticals import Lead
from app.models.field_sales import SalespersonFieldStatus
from app.models.real_estate import (
    RealEstateProject,
    RealEstateProjectAssignment,
    RealEstateSiteVisit,
    RealEstateUnit,
)
from app.services.sales_os.real_estate.inventory_service import InventoryService
from app.services.sales_os.real_estate.project_assignment_service import ProjectAssignmentService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    tenant = Tenant(id="tenant_re_test", name="Sobha Prestige Real Estate")
    session.add(tenant)

    # Admin user
    admin = User(
        id="user_admin_1",
        tenant_id="tenant_re_test",
        name="Vikram Mehta",
        email="admin@sobha.com",
        role="admin",
        hashed_password="hash",
        is_active=True,
    )
    session.add(admin)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


def test_admin_creates_and_updates_project(db_session):
    inv = InventoryService(db_session, "tenant_re_test")
    proj = inv.create_project(
        name="Sobha Royal Pavilion",
        code="SRP_EAST",
        location="Sarjapur Road",
        city="Bangalore",
        address="Sarjapur Main Rd, Hadosiddapura, Chikkakannalli, Bengaluru, Karnataka 560035",
        latitude=12.9081,
        longitude=77.6953,
        rera_number="PRM/KA/RERA/1251/308/PR/190204/002338",
        amenities=["Clubhouse", "Infinity Pool", "Tennis Court", "Cricket Pitch"],
        hold_duration_hours=72,
        status="active",
        total_units=120,
    )

    assert proj["name"] == "Sobha Royal Pavilion"
    assert proj["latitude"] == 12.9081
    assert proj["rera_number"] == "PRM/KA/RERA/1251/308/PR/190204/002338"

    # Fetch full dossier
    dossier = inv.get_project(proj["id"])
    assert dossier["assigned_team_count"] == 0
    assert "Infinity Pool" in dossier["amenities"]

    # Update project
    updated = inv.update_project(proj["id"], status="pre_launch", total_units=150)
    assert updated["status"] == "pre_launch"
    assert updated["total_units"] == 150


def test_admin_adds_sales_employees(db_session):
    svc = ProjectAssignmentService(db_session, "tenant_re_test")

    agent1 = svc.create_salesperson(
        name="Rahul Sharma",
        email="rahul.s@sobha.com",
        phone="+919876543210",
        designation="Senior Luxury Specialist",
        working_hours_start="09:00",
        working_hours_end="18:00",
        max_visits_per_day=5,
    )
    assert agent1["name"] == "Rahul Sharma"
    assert agent1["is_shift_active"] is True

    agent2 = svc.create_salesperson(
        name="Priya Verma",
        email="priya.v@sobha.com",
        phone="+919876543211",
        designation="Site Visit Executive",
        working_hours_start="10:00",
        working_hours_end="19:00",
        max_visits_per_day=6,
    )
    assert agent2["name"] == "Priya Verma"

    # List salespeople
    team = svc.list_salespeople()
    # At least admin + 2 salespeople
    emails = [m["email"] for m in team]
    assert "rahul.s@sobha.com" in emails
    assert "priya.v@sobha.com" in emails


def test_ai_suggests_project_team_and_admin_implements(db_session):
    inv = InventoryService(db_session, "tenant_re_test")
    svc = ProjectAssignmentService(db_session, "tenant_re_test")

    proj = inv.create_project(
        name="Prestige Golfshire",
        location="Nandi Hills",
        city="Bangalore",
        latitude=13.3702,
        longitude=77.6835,
        total_units=50,
    )
    # Add luxury villa unit
    inv.create_unit(proj["id"], "Villa-01", "Villa", 45000000.0)

    # Add 2 agents
    a1 = svc.create_salesperson(name="Amit Patel", email="amit@sobha.com", designation="Luxury Lead")
    a2 = svc.create_salesperson(name="Sunita Rao", email="sunita@sobha.com", designation="Associate")

    # Set GPS near project for Amit
    fs1 = db_session.query(SalespersonFieldStatus).filter_by(user_id=a1["user_id"]).first()
    fs1.last_latitude = 13.3750
    fs1.last_longitude = 77.6850
    db_session.commit()

    # AI Suggest Team
    suggestions = svc.suggest_salespeople_for_project(proj["id"])
    assert suggestions["project_id"] == proj["id"]
    assert len(suggestions["suggested_team"]) >= 2

    top_candidate = suggestions["suggested_team"][0]
    assert top_candidate["recommended_role"] == "primary_lead"
    assert top_candidate["match_score"] > 50

    # Admin implements the team
    team_to_assign = [
        {
            "user_id": top_candidate["user_id"],
            "role": top_candidate["recommended_role"],
            "ai_recommended": True,
            "match_score": top_candidate["match_score"],
            "reason": top_candidate["rationales"][0] if top_candidate["rationales"] else "AI Match",
        },
        {
            "user_id": a2["user_id"],
            "role": "site_specialist",
            "ai_recommended": False,
        },
    ]
    confirmed = svc.assign_team_to_project(proj["id"], team_to_assign, assigned_by_id="user_admin_1")
    assert confirmed["assigned_team_count"] == 2

    # Verify team
    current_team = svc.get_project_team(proj["id"])
    assert len(current_team) == 2
    assigned_roles = {m["role"] for m in current_team}
    assert "primary_lead" in assigned_roles
    assert "site_specialist" in assigned_roles


def test_intelligent_lead_auto_assign_to_available_specialist(db_session):
    inv = InventoryService(db_session, "tenant_re_test")
    svc = ProjectAssignmentService(db_session, "tenant_re_test")

    proj = inv.create_project(
        name="Sobha Dream Acres",
        location="Panathur",
        city="Bangalore",
        latitude=12.9352,
        longitude=77.7200,
    )
    inv.create_unit(proj["id"], "A-101", "2BHK", 8500000.0)

    # Add 2 agents
    agent_busy = svc.create_salesperson(name="Karan Oberoi", email="karan@sobha.com")
    agent_avail = svc.create_salesperson(name="Deepa Nair", email="deepa@sobha.com")

    # Assign both to the project
    svc.assign_team_to_project(
        proj["id"],
        [
            {"user_id": agent_busy["user_id"], "role": "primary_lead"},
            {"user_id": agent_avail["user_id"], "role": "site_specialist"},
        ],
    )

    # Set visit time tomorrow 2 PM
    showing_time = datetime.now(timezone.utc) + timedelta(days=1, hours=2)

    # Make agent_busy have a conflicting visit at showing_time
    busy_visit = RealEstateSiteVisit(
        tenant_id="tenant_re_test",
        lead_id="dummy_lead",
        project_id=proj["id"],
        scheduled_at=showing_time + timedelta(minutes=10),
        assigned_agent=agent_busy["user_id"],
        status="scheduled",
    )
    db_session.add(busy_visit)
    db_session.commit()

    # Create an inbound lead needing a showing
    lead = Lead(
        tenant_id="tenant_re_test",
        name="Rohan Varma",
        email="rohan@example.com",
        phone="+919988776655",
        company="Sobha Dream Acres",
        need_of_what="2BHK with balcony",
        how_much="85L - 90L",
        status="inquiry",
    )
    db_session.add(lead)
    db_session.commit()

    # Run auto-assignment
    result = svc.assign_lead_to_available_salesperson(
        lead_id=lead.id,
        project_id=proj["id"],
        scheduled_at=showing_time,
    )

    # Should select agent_avail (Deepa Nair) because Karan has a time conflict!
    assert result["assigned_specialist"]["user_id"] == agent_avail["user_id"]
    assert result["assignment_status"] == "ASSIGNED_AVAILABLE"
    assert "Deepa Nair" in result["decision_rationale"]

    # Verify 'Take Care' actions:
    # 1. Lead assigned_to updated
    db_session.refresh(lead)
    assert lead.assigned_to == "Deepa Nair"
    assert lead.status == "visit_scheduled"
    assert lead.data["project_id"] == proj["id"]
    assert len(lead.data["dispatch_history"]) >= 1

    # 2. Site visit booked
    visit = db_session.query(RealEstateSiteVisit).filter_by(lead_id=lead.id).first()
    assert visit is not None
    assert visit.assigned_agent == agent_avail["user_id"]
    assert visit.status == "scheduled"


def test_auto_assign_skips_agents_at_daily_capacity(db_session):
    inv = InventoryService(db_session, "tenant_re_test")
    svc = ProjectAssignmentService(db_session, "tenant_re_test")

    proj = inv.create_project(name="Brigade Cornerstone", location="Whitefield")
    agent_full = svc.create_salesperson(name="Maxed Agent", email="maxed@sobha.com", max_visits_per_day=2)
    agent_free = svc.create_salesperson(name="Free Agent", email="free@sobha.com", max_visits_per_day=5)

    svc.assign_team_to_project(
        proj["id"],
        [
            {"user_id": agent_full["user_id"], "role": "primary_lead"},
            {"user_id": agent_free["user_id"], "role": "site_specialist"},
        ],
    )

    # Put 2 visits today for agent_full to reach max capacity
    today = datetime.now(timezone.utc)
    v1 = RealEstateSiteVisit(tenant_id="tenant_re_test", lead_id="l1", project_id=proj["id"], scheduled_at=today, assigned_agent=agent_full["user_id"], status="completed")
    v2 = RealEstateSiteVisit(tenant_id="tenant_re_test", lead_id="l2", project_id=proj["id"], scheduled_at=today + timedelta(hours=1), assigned_agent=agent_full["user_id"], status="scheduled")
    db_session.add_all([v1, v2])
    db_session.commit()

    lead = Lead(tenant_id="tenant_re_test", name="New Buyer", email="buyer@test.com", company="Brigade Cornerstone")
    db_session.add(lead)
    db_session.commit()

    res = svc.assign_lead_to_available_salesperson(lead_id=lead.id, scheduled_at=today + timedelta(hours=3))
    # Must choose agent_free because agent_full is maxed out
    assert res["assigned_specialist"]["user_id"] == agent_free["user_id"]
    assert res["assignment_status"] == "ASSIGNED_AVAILABLE"
