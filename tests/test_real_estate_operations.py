"""Unit, concurrency, and operational tests for Real Estate domain services."""
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base, Tenant
from app.models.verticals import Lead
from app.services.sales_os.real_estate.inventory_service import InventoryService
from app.services.sales_os.real_estate.visit_service import VisitService
from app.services.sales_os.real_estate.partner_service import PartnerService
from app.services.sales_os.copilot.record import advise_record


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

    tenant = Tenant(id="tenant_re_test", name="Luxury Real Estate Tenant")
    session.add(tenant)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


def test_inventory_service_project_and_units(db_session):
    svc = InventoryService(db_session, "tenant_re_test")

    # 1. Create project
    proj = svc.create_project(
        name="Skyline Azure Towers",
        location="Marina District",
        city="Metropolis",
        hold_duration_hours=72,
    )
    assert proj["name"] == "Skyline Azure Towers"
    project_id = proj["id"]

    # 2. Add units
    u1 = svc.create_unit(project_id, "PH-401", "Penthouse", 2500000.0, tower="Tower A", floor=40, carpet_sqft=3200)
    u2 = svc.create_unit(project_id, "302-B", "3BHK", 950000.0, tower="Tower B", floor=3, carpet_sqft=1450)
    assert u1["unit_number"] == "PH-401"
    assert u2["unit_number"] == "302-B"

    # 3. List units
    units = svc.list_units(project_id)
    assert len(units) == 2
    assert all(u["status"] == "available" for u in units)


def test_inventory_atomic_unit_hold_and_conflict(db_session):
    svc = InventoryService(db_session, "tenant_re_test")
    proj = svc.create_project(name="Marina Bayfront")
    u = svc.create_unit(proj["id"], "101", "2BHK", 600000.0)

    # Lead A creates inquiry
    lead_a = Lead(tenant_id="tenant_re_test", name="Alice Morgan", email="alice@example.com")
    lead_b = Lead(tenant_id="tenant_re_test", name="Bob Vance", email="bob@example.com")
    db_session.add_all([lead_a, lead_b])
    db_session.commit()

    # Lead A requests hold
    hold_a = svc.request_unit_hold(u["id"], lead_a.id, deposit_amount=5000.0, notes="Token received")
    assert hold_a["status"] == "confirmed"
    assert hold_a["unit_number"] == "101"

    # Lead B attempts to hold the same unit -> must be rejected with 409 Conflict
    with pytest.raises(HTTPException) as exc_info:
        svc.request_unit_hold(u["id"], lead_b.id, deposit_amount=10000.0)
    assert exc_info.value.status_code == 409
    assert "cannot be held" in exc_info.value.detail


def test_inventory_hold_release(db_session):
    svc = InventoryService(db_session, "tenant_re_test")
    proj = svc.create_project(name="Oasis Gardens")
    u = svc.create_unit(proj["id"], "Villa-12", "Villa", 1800000.0)
    lead = Lead(tenant_id="tenant_re_test", name="David Kim")
    db_session.add(lead)
    db_session.commit()

    hold = svc.request_unit_hold(u["id"], lead.id)
    assert hold["status"] == "requested"

    # Release hold
    released = svc.release_hold(hold["hold_id"])
    assert released["status"] == "released"
    assert released["unit_status"] == "available"

    # Verify unit is available again
    available = svc.list_units(proj["id"], status="available")
    assert any(x["unit_number"] == "Villa-12" for x in available)


def test_visit_service_scheduling_and_outcome(db_session):
    visit_svc = VisitService(db_session, "tenant_re_test")
    lead = Lead(tenant_id="tenant_re_test", name="Sophia Chen", company="Emerald Heights")
    db_session.add(lead)
    db_session.commit()

    # Schedule visit
    visit_time = datetime(2026, 11, 15, 14, 0, tzinfo=timezone.utc)
    visit = visit_svc.schedule_visit(
        lead_id=lead.id,
        project_id="proj_emerald",
        scheduled_at=visit_time,
        assigned_agent="Agent Sarah",
        escort_contact="+1-555-0199",
        pickup_required=True,
    )
    assert visit["status"] == "scheduled"
    assert visit["lead_id"] == lead.id

    # List visits for lead
    visits = visit_svc.list_visits_for_lead(lead.id)
    assert len(visits) == 1
    assert visits[0]["assigned_agent"] == "Agent Sarah"

    # Record outcome
    updated = visit_svc.record_visit_outcome(
        visit["id"],
        status="completed",
        tour_feedback="Loved the penthouse terrace, requested contract draft.",
        buyer_interest_level="high",
    )
    assert updated["status"] == "completed"
    assert updated["buyer_interest_level"] == "high"


def test_partner_service_broker_attribution_and_commission(db_session):
    partner_svc = PartnerService(db_session, "tenant_re_test")
    lead = Lead(tenant_id="tenant_re_test", name="Marcus Sterling")
    db_session.add(lead)
    db_session.commit()

    # Attribute broker
    partner = partner_svc.attribute_broker(
        lead_id=lead.id,
        brokerage_name="Apex Luxury Realty",
        broker_agent_name="James Wilson",
        rera_id="RERA-NY-9812",
        commission_pct=2.5,
    )
    assert partner["brokerage_name"] == "Apex Luxury Realty"
    assert partner["commission_pct"] == 2.5

    # Calculate commission on $1,200,000 deal
    calc = partner_svc.calculate_commission(lead.id, booking_amount=1200000.0)
    assert calc["commission_pct"] == 2.5
    assert calc["payable_commission"] == 30000.0  # 2.5% of 1,200,000
    assert calc["attributed"] is True


def test_copilot_real_estate_actions_and_guardrails():
    """Verify copilot provides Real Estate domain actions and enforces guardrails."""
    record = {
        "id": "inquiry_1",
        "name": "Evelyn Harper",
        "company": "Skyline Towers",
        "email": "evelyn@harper.example",
        "status": "inquiry",
        "why": "Looking for 3BHK high floor with city view.",
        "score": 85,
        "data": {"unit_preference": "3BHK", "budget": "$1,500,000"},
    }

    # Ask for next step
    advice = advise_record(record, pack_id="real_estate", question="What should we do next?")
    action_ids = [a["id"] for a in advice["actions"]]
    assert "schedule_site_visit" in action_ids
    assert "request_unit_hold" in action_ids
    assert "verify_financing" in action_ids

    # Ask to hold unit without deposit -> copilot must refuse
    refusal = advise_record(
        record,
        pack_id="real_estate",
        question="Can you hold unit 402 without deposit right now?",
    )
    assert "refuse" in refusal["answer"].lower() or "outside what sales ai" in refusal["answer"].lower() or "not changed" in refusal["answer"].lower()


def test_real_estate_funnel_analytics(db_session):
    from app.services.sales_os.real_estate.analytics_service import get_real_estate_funnel_analytics
    from app.models.real_estate import RealEstateSiteVisit, RealEstateUnit, RealEstateProject

    # Seed data
    lead1 = Lead(tenant_id="tenant_re_test", name="Buyer Inquirer", status="inquiry")
    lead2 = Lead(tenant_id="tenant_re_test", name="Confirmed Buyer", status="booking")
    db_session.add_all([lead1, lead2])

    proj = RealEstateProject(tenant_id="tenant_re_test", name="Analytics Proj", total_units=10, available_units=8)
    db_session.add(proj)
    db_session.commit()

    unit1 = RealEstateUnit(tenant_id="tenant_re_test", project_id=proj.id, unit_number="A1", unit_type="2BHK", base_price=500000.0, status="available")
    unit2 = RealEstateUnit(tenant_id="tenant_re_test", project_id=proj.id, unit_number="A2", unit_type="2BHK", base_price=500000.0, status="booked")
    db_session.add_all([unit1, unit2])

    visit = RealEstateSiteVisit(tenant_id="tenant_re_test", lead_id=lead1.id, project_id=proj.id, scheduled_at=datetime.now(timezone.utc), status="completed")
    db_session.add(visit)
    db_session.commit()

    res = get_real_estate_funnel_analytics(db=db_session, tenant_id="tenant_re_test")
    assert res["funnel"]["inquiries"] == 2
    assert res["funnel"]["bookings_confirmed"] == 1
    assert res["funnel"]["site_visits_completed"] == 1
    assert res["inventory_snapshot"]["total_units"] == 2
    assert res["inventory_snapshot"]["booked_units"] == 1
    assert res["inventory_snapshot"]["occupancy_rate_pct"] == 50.0

