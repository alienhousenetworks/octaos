"""Unit, concurrency, and CPQ calculation tests for Enterprise Real Estate."""
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base, Tenant
from app.models.verticals import Lead
from app.models.real_estate import RealEstateProject, RealEstateUnit, RealEstateCostSheet
from app.services.sales_os.real_estate.inventory_service import InventoryService
from app.services.sales_os.real_estate.booking_service import BookingService
from app.services.sales_os.real_estate.cost_sheet_service import CostSheetService
from app.services.sales_os.real_estate.concurrency import (
    acquire_inventory_lock,
    release_inventory_lock,
    inventory_unit_lock,
)


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

    tenant = Tenant(id="tenant_cpq_test", name="Enterprise Real Estate Dev Corp")
    session.add(tenant)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


def test_distributed_inventory_lock_lifecycle():
    unit_id = "test_unit_concurrency_01"

    # 1. First lock acquisition succeeds
    token1 = acquire_inventory_lock(unit_id, timeout_seconds=10)
    assert token1 is not None

    # 2. Concurrent second attempt fails while token1 is active
    token2 = acquire_inventory_lock(unit_id, timeout_seconds=10)
    assert token2 is None

    # 3. Release lock with token1
    released = release_inventory_lock(unit_id, token1)
    assert released is True

    # 4. Now a new lock can be acquired
    token3 = acquire_inventory_lock(unit_id, timeout_seconds=10)
    assert token3 is not None
    release_inventory_lock(unit_id, token3)


def test_inventory_unit_lock_context_manager():
    unit_id = "test_unit_concurrency_02"

    with inventory_unit_lock(unit_id, timeout_seconds=30) as token:
        assert token is not None
        # Within the lock, another acquisition attempt must fail
        with pytest.raises(HTTPException) as exc_info:
            with inventory_unit_lock(unit_id, timeout_seconds=30):
                pass
        assert exc_info.value.status_code == 409

    # Once exited, lock is released and can be acquired again
    with inventory_unit_lock(unit_id, timeout_seconds=30) as new_token:
        assert new_token is not None


def test_cost_sheet_calculation_and_milestones(db_session):
    inv_svc = InventoryService(db_session, "tenant_cpq_test")
    proj = inv_svc.create_project(name="Prestige Sky Towers", location="Whitefield")
    unit = inv_svc.create_unit(
        project_id=proj["id"],
        unit_number="A-802",
        unit_type="3BHK Luxury",
        base_price=20000000.0,
        floor=8,
        carpet_sqft=1850.0,
    )

    lead = Lead(
        id="lead_cpq_buyer_01",
        tenant_id="tenant_cpq_test",
        name="Vikram Malhotra",
        email="vikram@test.com",
    )
    db_session.add(lead)
    db_session.commit()

    cpq_svc = CostSheetService(db_session, "tenant_cpq_test")

    # Calculate CPQ with Floor Rise and PLC
    calc = cpq_svc.calculate_cost_sheet(
        unit_id=unit["id"],
        lead_id=lead.id,
        base_rate_per_sqft=10000.0,
        floor_rise_rate_per_sqft=50.0,
        plc_type="Corner Pool Facing",
        plc_rate_per_sqft=400.0,
        car_parking_slots=2,
        car_parking_charges_per_slot=350000.0,
        clubhouse_charges=250000.0,
        infrastructure_development_charges=150000.0,
        gst_rate_pct=5.0,
        stamp_duty_pct=5.6,
        payment_plan_type="construction_linked",
    )

    # 1. Base unit value: 1850 sqft * 10,000 = 18,500,000
    assert calc["base_unit_value"] == 18500000.0

    # 2. Floor rise: Floor 8 -> (8 - 3) = 5 floors * 50 * 1850 = 462,500
    assert calc["floor_rise_total"] == 462500.0

    # 3. PLC: 1850 * 400 = 740,000
    assert calc["plc_total"] == 740000.0

    # 4. Parking: 2 * 350,000 = 700,000
    assert calc["car_parking_charges"] == 700000.0

    # 5. Gross consideration = 18.5M + 462.5k + 740k + 250k + 150k + 700k = 20,802,500
    expected_gross = 18500000.0 + 462500.0 + 740000.0 + 250000.0 + 150000.0 + 700000.0
    assert calc["gross_consideration"] == expected_gross

    # 6. GST: 5% of gross
    assert calc["gst_amount"] == round(expected_gross * 0.05, 2)

    # 7. Milestone schedule generated
    assert len(calc["milestone_schedule"]) == 9
    total_pct = sum(m["percentage"] for m in calc["milestone_schedule"])
    assert total_pct == 100.0


def test_cost_sheet_persistence_and_superseding(db_session):
    inv_svc = InventoryService(db_session, "tenant_cpq_test")
    proj = inv_svc.create_project(name="Azure Heights")
    unit = inv_svc.create_unit(proj["id"], "101", "2BHK", 10000000.0, floor=1, carpet_sqft=1000.0)

    lead = Lead(id="lead_02", tenant_id="tenant_cpq_test", name="Priya")
    db_session.add(lead)
    db_session.commit()

    cpq_svc = CostSheetService(db_session, "tenant_cpq_test")

    # 1. Save first cost sheet (CLP)
    cs1 = cpq_svc.save_cost_sheet(
        unit_id=unit["id"],
        lead_id=lead.id,
        payment_plan_type="construction_linked",
        notes="First quote for buyer",
    )
    assert cs1["status"] == "active"
    cs1_id = cs1["id"]

    # 2. Save second revised cost sheet (Down Payment)
    cs2 = cpq_svc.save_cost_sheet(
        unit_id=unit["id"],
        lead_id=lead.id,
        payment_plan_type="down_payment",
        notes="Revised with 80% down payment",
    )
    assert cs2["status"] == "active"
    assert cs2["payment_plan_type"] == "down_payment"

    # 3. Verify cs1 was superseded
    fetched_cs1 = cpq_svc.get_cost_sheet(cs1_id)
    assert fetched_cs1["status"] == "superseded"

    # 4. Fetch latest active cost sheet for unit
    latest = cpq_svc.get_latest_cost_sheet_for_unit(unit["id"], lead_id=lead.id)
    assert latest is not None
    assert latest["id"] == cs2["id"]
    assert latest["payment_plan_type"] == "down_payment"


def test_booking_application_concurrency_lock(db_session):
    inv_svc = InventoryService(db_session, "tenant_cpq_test")
    proj = inv_svc.create_project(name="The Sovereign")
    unit = inv_svc.create_unit(proj["id"], "Villa-01", "Villa", 50000000.0, floor=1, carpet_sqft=4000.0)

    lead1 = Lead(id="lead_villa_1", tenant_id="tenant_cpq_test", name="Buyer A")
    lead2 = Lead(id="lead_villa_2", tenant_id="tenant_cpq_test", name="Buyer B")
    db_session.add_all([lead1, lead2])
    db_session.commit()

    booking_svc = BookingService(db_session, "tenant_cpq_test")

    # 1. First booking succeeds
    bk1 = booking_svc.create_booking_application(
        lead_id=lead1.id,
        unit_id=unit["id"],
        agreed_price=50000000.0,
        buyer_legal_name="Buyer A Full Legal",
        deposit_paid=5000000.0,
    )
    assert bk1["status"] == "payment_verified"
    assert bk1["balance_due"] == 45000000.0

    # 2. Immediate second booking attempt fails because unit is already booked
    with pytest.raises(HTTPException) as exc_info:
        booking_svc.create_booking_application(
            lead_id=lead2.id,
            unit_id=unit["id"],
            agreed_price=50000000.0,
            buyer_legal_name="Buyer B Full Legal",
        )
    assert exc_info.value.status_code == 409
