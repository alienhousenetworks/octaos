"""Comprehensive end-to-end unit and concurrency tests for Real Estate Operating System lifecycle."""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base, Tenant
from app.models.verticals import Lead
from app.models.real_estate import (
    RealEstateProject,
    RealEstateUnit,
    RealEstateUnitHold,
    RealEstateBooking,
    RealEstatePaymentTransaction,
    RealEstateCommissionLedger,
    RealEstateBrokerAttribution,
    RealEstateSiteVisit,
)
from app.services.sales_os.real_estate.inventory_service import InventoryService
from app.services.sales_os.real_estate.booking_service import BookingService
from app.services.sales_os.real_estate.payment_reconciliation_service import PaymentReconciliationService
from app.services.sales_os.real_estate.commission_ledger_service import CommissionLedgerService
from app.services.sales_os.real_estate.property_matching_service import PropertyMatchingService
from app.workers.real_estate_jobs import expire_stale_holds_job


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

    tenant = Tenant(id="tenant_re_enterprise", name="Apex Luxury Developments")
    session.add(tenant)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


def test_concurrent_unit_holds_prevent_double_booking(db_session):
    inv = InventoryService(db_session, "tenant_re_enterprise")
    proj = inv.create_project(name="Marina Crown", location="South Bay", city="Metropolis")

    unit = inv.create_unit(proj["id"], "1001", "3BHK", 1200000.0, tower="Tower A", floor=10)

    lead1 = Lead(tenant_id="tenant_re_enterprise", name="Buyer One", email="buyer1@example.com")
    lead2 = Lead(tenant_id="tenant_re_enterprise", name="Buyer Two", email="buyer2@example.com")
    db_session.add_all([lead1, lead2])
    db_session.commit()

    # Lead 1 requests hold
    hold1 = inv.request_unit_hold(unit["id"], lead1.id, deposit_amount=50000.0)
    assert hold1["status"] == "confirmed"
    assert hold1["unit_number"] == "1001"

    # Lead 2 attempts hold on the same unit -> HTTP 409 Conflict
    with pytest.raises(HTTPException) as exc:
        inv.request_unit_hold(unit["id"], lead2.id, deposit_amount=50000.0)
    assert exc.value.status_code == 409


def test_expired_hold_does_not_release_booked_unit(db_session):
    inv = InventoryService(db_session, "tenant_re_enterprise")
    book_svc = BookingService(db_session, "tenant_re_enterprise")

    proj = inv.create_project(name="Azure Heights")
    unit = inv.create_unit(proj["id"], "PH-01", "Penthouse", 3500000.0)
    lead = Lead(tenant_id="tenant_re_enterprise", name="Charles Xavier")
    db_session.add(lead)
    db_session.commit()

    # Hold unit
    hold = inv.request_unit_hold(unit["id"], lead.id)

    # Fast forward: unit is committed into a booking
    booking = book_svc.create_booking_application(
        lead_id=lead.id,
        unit_id=unit["id"],
        agreed_price=3500000.0,
        buyer_legal_name="Charles Xavier",
        hold_id=hold["hold_id"],
    )
    assert booking["status"] == "pending_payment"

    # Manually backdate hold expiration to simulate past expiration
    hold_record = db_session.query(RealEstateUnitHold).filter(RealEstateUnitHold.id == hold["hold_id"]).first()
    hold_record.expires_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db_session.commit()

    # Trigger reconciliation
    inv.reconcile_expired_holds(proj["id"])

    # Invariant: unit must remain booked, NEVER reverted to available!
    refreshed_unit = db_session.query(RealEstateUnit).filter(RealEstateUnit.id == unit["id"]).first()
    assert refreshed_unit.status == "booked"


def test_booking_application_creation_and_cancellation(db_session):
    inv = InventoryService(db_session, "tenant_re_enterprise")
    book_svc = BookingService(db_session, "tenant_re_enterprise")

    proj = inv.create_project(name="Palm Sanctuary")
    unit = inv.create_unit(proj["id"], "V-201", "Villa", 2000000.0)
    lead = Lead(tenant_id="tenant_re_enterprise", name="Diana Prince")
    db_session.add(lead)
    db_session.commit()

    # Create booking directly
    booking = book_svc.create_booking_application(
        lead_id=lead.id,
        unit_id=unit["id"],
        agreed_price=1950000.0,
        buyer_legal_name="Diana Prince",
        deposit_paid=100000.0,
    )
    assert booking["booking_reference"].startswith("BK-")
    assert booking["agreed_price"] == 1950000.0
    assert booking["deposit_paid"] == 100000.0
    assert booking["balance_due"] == 1850000.0
    assert booking["status"] == "payment_verified"

    # Verify unit is booked
    unit_rec = db_session.query(RealEstateUnit).filter(RealEstateUnit.id == unit["id"]).first()
    assert unit_rec.status == "booked"

    # Cancel booking
    cancel_res = book_svc.cancel_booking(booking["id"], reason="Buyer opted for relocation", refund_amount=100000.0)
    assert cancel_res["status"] == "cancelled"
    assert cancel_res["unit_status"] == "available"

    # Verify unit is back to available
    db_session.refresh(unit_rec)
    assert unit_rec.status == "available"


def test_payment_reconciliation_idempotency_and_deposit(db_session):
    inv = InventoryService(db_session, "tenant_re_enterprise")
    book_svc = BookingService(db_session, "tenant_re_enterprise")
    pay_svc = PaymentReconciliationService(db_session, "tenant_re_enterprise")

    proj = inv.create_project(name="Silver Crest")
    unit = inv.create_unit(proj["id"], "501", "2BHK", 800000.0)
    lead = Lead(tenant_id="tenant_re_enterprise", name="Edward Nygma")
    db_session.add(lead)
    db_session.commit()

    booking = book_svc.create_booking_application(
        lead_id=lead.id,
        unit_id=unit["id"],
        agreed_price=800000.0,
        buyer_legal_name="Edward Nygma",
        deposit_paid=0.0,
    )
    assert booking["status"] == "pending_payment"

    # 1. Record deposit via gateway webhook
    tx1 = pay_svc.record_payment_event(
        idempotency_key="tx_pay_001_unique",
        lead_id=lead.id,
        amount=50000.0,
        payment_method="gateway",
        payment_reference="pay_razor_998877",
        booking_id=booking["id"],
        auto_verify=True,
    )
    assert tx1["status"] == "verified"
    assert tx1["idempotent_duplicate"] is False

    # Check booking updated
    b_updated = book_svc.get_booking(booking["id"])
    assert b_updated["deposit_paid"] == 50000.0
    assert b_updated["balance_due"] == 750000.0
    assert b_updated["status"] == "payment_verified"

    # 2. Replay the exact same webhook event -> must be deduplicated
    tx2 = pay_svc.record_payment_event(
        idempotency_key="tx_pay_001_unique",
        lead_id=lead.id,
        amount=50000.0,
        payment_method="gateway",
        payment_reference="pay_razor_998877",
        booking_id=booking["id"],
        auto_verify=True,
    )
    assert tx2["idempotent_duplicate"] is True

    # Balance must NOT be doubled
    b_recheck = book_svc.get_booking(booking["id"])
    assert b_recheck["deposit_paid"] == 50000.0


def test_commission_ledger_milestones_and_reversals(db_session):
    inv = InventoryService(db_session, "tenant_re_enterprise")
    book_svc = BookingService(db_session, "tenant_re_enterprise")
    com_svc = CommissionLedgerService(db_session, "tenant_re_enterprise")

    proj = inv.create_project(name="Grand Residences")
    unit = inv.create_unit(proj["id"], "1204", "3BHK", 1000000.0)
    lead = Lead(tenant_id="tenant_re_enterprise", name="Fiona Gallagher")
    db_session.add(lead)
    db_session.commit()

    # Attribution
    attr = RealEstateBrokerAttribution(
        tenant_id="tenant_re_enterprise",
        lead_id=lead.id,

        brokerage_name="Knight & Frank Properties",
        commission_pct=2.0,
    )
    db_session.add(attr)
    db_session.commit()

    # Create Booking
    booking = book_svc.create_booking_application(
        lead_id=lead.id,
        unit_id=unit["id"],
        agreed_price=1000000.0,
        buyer_legal_name="Fiona Gallagher",
        deposit_paid=50000.0,
    )

    # Accrue commissions: 2% of 1,000,000 = 20,000 (M1: 5,000, M2: 15,000)
    ledgers = com_svc.accrue_booking_commissions(booking["id"])
    assert len(ledgers) == 2
    assert ledgers[0]["total_commission_amount"] == 20000.0
    assert ledgers[0]["payable_amount"] == 5000.0
    assert ledgers[1]["payable_amount"] == 15000.0

    # Pay Milestone 1
    payout = com_svc.record_payout(ledgers[0]["id"], payout_reference="NEFT_BNK_4455", approved_by_user_id="user_fin_01")
    assert payout["status"] == "paid"

    # Reverse remaining on deal cancellation
    reversed_count = com_svc.reverse_commissions_for_booking(booking["id"], reason="Cancelled before agreement")
    assert reversed_count == 1  # Only unpaid M2 reversed; M1 was already paid

    entries = com_svc.list_ledgers(booking_id=booking["id"])
    assert entries[0]["status"] == "paid"
    assert entries[1]["status"] == "reversed"


def test_property_matching_strictly_respects_available_inventory(db_session):
    inv = InventoryService(db_session, "tenant_re_enterprise")
    match_svc = PropertyMatchingService(db_session, "tenant_re_enterprise")

    proj1 = inv.create_project(name="Marina Crown", city="Metropolis")
    proj2 = inv.create_project(name="Suburban Greens", city="Outskirts")

    # Available units
    inv.create_unit(proj1["id"], "A-101", "2BHK", 750000.0, floor=5)
    inv.create_unit(proj1["id"], "A-102", "3BHK", 950000.0, floor=10)
    inv.create_unit(proj2["id"], "B-201", "3BHK", 600000.0, floor=2)

    # Booked unit (must NEVER be matched!)
    booked_u = inv.create_unit(proj1["id"], "A-103", "3BHK", 920000.0, floor=8)
    unit_obj = db_session.query(RealEstateUnit).filter(RealEstateUnit.id == booked_u["id"]).first()
    unit_obj.status = "booked"
    db_session.commit()

    # Lead looking for 3BHK up to 1.0M at Marina Crown
    lead = Lead(
        tenant_id="tenant_re_enterprise",
        name="George Miller",
        company="Marina Crown",
        need_of_what="3BHK with scenic view",
        how_much="700k - 1M",
    )
    db_session.add(lead)
    db_session.commit()

    res = match_svc.find_top_matches(lead.id)
    assert res["matched_count"] > 0
    top = res["top_matches"][0]

    # Best match must be A-102 (3BHK at Marina Crown, 950k)
    assert top["unit_number"] == "A-102"
    assert top["unit_type"] == "3BHK"
    assert top["match_score"] >= 80
    assert any("Matches desired configuration" in p for p in top["pros"])

    # Booked unit A-103 must not be returned
    assert all(m["unit_number"] != "A-103" for m in res["top_matches"])

    # Next-best action suggested
    assert res["next_best_action"]["action_code"] == "schedule_site_visit"
