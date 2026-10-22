"""Real Estate domain endpoints for project catalog, units, holds, visits, team assignments, and broker attribution."""
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.models.base import User
from app.services.sales_os.real_estate.inventory_service import InventoryService
from app.services.sales_os.real_estate.visit_service import VisitService
from app.services.sales_os.real_estate.partner_service import PartnerService
from app.services.sales_os.real_estate.project_assignment_service import ProjectAssignmentService

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    code: str | None = None
    location: str | None = None
    city: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    rera_number: str | None = None
    amenities: list[str] = Field(default_factory=list)
    hold_duration_hours: int = 48
    status: str = "active"
    total_units: int = 0


class ProjectUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    location: str | None = None
    city: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    rera_number: str | None = None
    amenities: list[str] | None = None
    hold_duration_hours: int | None = None
    status: str | None = None
    total_units: int | None = None
    available_units: int | None = None


class SalespersonCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=3)
    phone: str | None = None
    designation: str = "Property Specialist"
    password: str | None = None
    working_hours_start: str = "09:00"
    working_hours_end: str = "18:00"
    max_visits_per_day: int = 6
    initial_project_ids: list[str] = Field(default_factory=list)


class SalespersonStatusUpdate(BaseModel):
    is_shift_active: bool | None = None
    status: str | None = None
    working_hours_start: str | None = None
    working_hours_end: str | None = None
    max_visits_per_day: int | None = None


class ProjectTeamAssignmentItem(BaseModel):
    user_id: str
    role: str = "site_specialist"
    ai_recommended: bool = False
    match_score: float | None = None
    reason: str | None = None


class ProjectTeamAssignmentRequest(BaseModel):
    assignments: list[ProjectTeamAssignmentItem] = Field(default_factory=list)


class LeadAutoAssignRequest(BaseModel):
    project_id: str | None = None
    scheduled_at: datetime | None = None
    unit_id: str | None = None
    visit_duration_minutes: int = 45


class UnitCreate(BaseModel):
    unit_number: str = Field(..., min_length=1, max_length=64)
    unit_type: str = Field(..., min_length=1, max_length=32)
    base_price: float = Field(..., gt=0)
    tower: str | None = None
    floor: int | None = None
    carpet_sqft: float | None = None


class HoldRequest(BaseModel):
    lead_id: str
    deposit_amount: float = 0.0
    notes: str | None = None


class VisitSchedule(BaseModel):
    project_id: str
    scheduled_at: datetime
    unit_id: str | None = None
    assigned_agent: str | None = None
    escort_contact: str | None = None
    pickup_required: bool = False


class VisitOutcome(BaseModel):
    status: str
    tour_feedback: str | None = None
    buyer_interest_level: str | None = None


class BrokerAttribution(BaseModel):
    brokerage_name: str
    broker_agent_name: str | None = None
    broker_email: str | None = None
    broker_phone: str | None = None
    rera_id: str | None = None
    commission_pct: float = 2.0
    agreement_doc_url: str | None = None


class CommissionCalc(BaseModel):
    booking_amount: float


class BookingCreate(BaseModel):
    lead_id: str
    unit_id: str
    agreed_price: float = Field(..., gt=0)
    buyer_legal_name: str = Field(..., min_length=2)
    buyer_id_number: str | None = None
    deposit_paid: float = 0.0
    hold_id: str | None = None
    sales_rep_id: str | None = None
    payment_plan: dict[str, Any] = Field(default_factory=dict)
    co_buyers: list[dict[str, Any]] = Field(default_factory=list)


class BookingCancel(BaseModel):
    reason: str = Field(..., min_length=3)
    refund_amount: float = 0.0


class PaymentEventCreate(BaseModel):
    idempotency_key: str = Field(..., min_length=6)
    lead_id: str
    amount: float = Field(..., gt=0)
    payment_method: str = "wire"  # wire, card, upi, cheque, gateway
    payment_reference: str | None = None
    transaction_type: str = "token_deposit"
    booking_id: str | None = None
    hold_id: str | None = None
    proof_document_url: str | None = None
    auto_verify: bool = False
    notes: str | None = None


class CommissionPayout(BaseModel):
    payout_reference: str = Field(..., min_length=3)



# --- Projects ---
@router.get("/projects")
def list_projects(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> list[dict[str, Any]]:
    svc = InventoryService(db, tenant_id)
    return svc.list_projects()


@router.post("/projects")
def create_project(
    body: ProjectCreate,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    svc = InventoryService(db, tenant_id)
    return svc.create_project(
        name=body.name,
        code=body.code,
        location=body.location,
        city=body.city,
        address=body.address,
        latitude=body.latitude,
        longitude=body.longitude,
        rera_number=body.rera_number,
        amenities=body.amenities,
        hold_duration_hours=body.hold_duration_hours,
        status=body.status,
        total_units=body.total_units,
    )


@router.get("/projects/{project_id}")
def get_project_details(
    project_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    svc = InventoryService(db, tenant_id)
    return svc.get_project(project_id)


@router.put("/projects/{project_id}")
def update_project_details(
    project_id: str,
    body: ProjectUpdate,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    svc = InventoryService(db, tenant_id)
    return svc.update_project(project_id, **body.model_dump(exclude_unset=True))


# --- Project Team Allocation & AI Suggestions ---
@router.get("/projects/{project_id}/ai-team-suggestions")
def get_ai_team_suggestions(
    project_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    """AI evaluates all sales employees and recommends optimal team assignments with match scores."""
    svc = ProjectAssignmentService(db, tenant_id)
    return svc.suggest_salespeople_for_project(project_id)


@router.get("/projects/{project_id}/team")
def get_project_assigned_team(
    project_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> list[dict[str, Any]]:
    svc = ProjectAssignmentService(db, tenant_id)
    return svc.get_project_team(project_id)


@router.post("/projects/{project_id}/team")
def assign_project_team(
    project_id: str,
    body: ProjectTeamAssignmentRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    """Admin or authorized member commits/implements sales team assignments for the project."""
    svc = ProjectAssignmentService(db, tenant_id)
    return svc.assign_team_to_project(
        project_id=project_id,
        assignments=[item.model_dump() for item in body.assignments],
        assigned_by_id=current_user.id,
    )


# --- Sales Employees & Roster Management ---
@router.get("/salespeople")
def list_salespeople_directory(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> list[dict[str, Any]]:
    """List sales agents with live shift status, daily capacity, and assigned projects."""
    svc = ProjectAssignmentService(db, tenant_id)
    return svc.list_salespeople()


@router.post("/salespeople")
def create_salesperson_profile(
    body: SalespersonCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    """Add a new sales employee/agent in the organization."""
    svc = ProjectAssignmentService(db, tenant_id)
    return svc.create_salesperson(
        name=body.name,
        email=body.email,
        phone=body.phone,
        designation=body.designation,
        password=body.password,
        working_hours_start=body.working_hours_start,
        working_hours_end=body.working_hours_end,
        max_visits_per_day=body.max_visits_per_day,
        initial_project_ids=body.initial_project_ids,
        assigned_by_id=current_user.id,
    )


@router.put("/salespeople/{user_id}/status")
def update_salesperson_shift_status(
    user_id: str,
    body: SalespersonStatusUpdate,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    svc = ProjectAssignmentService(db, tenant_id)
    return svc.update_salesperson_status(
        user_id=user_id,
        is_shift_active=body.is_shift_active,
        status=body.status,
        working_hours_start=body.working_hours_start,
        working_hours_end=body.working_hours_end,
        max_visits_per_day=body.max_visits_per_day,
    )


# --- Autonomous Lead & Visit Dispatch ---
@router.post("/leads/{lead_id}/auto-assign-visit")
def auto_assign_lead_to_project_specialist(
    lead_id: str,
    body: LeadAutoAssignRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    """
    Intelligently assigns a lead/visit to an available salesperson assigned to the matching project,
    books the showing, and records dispatch history.
    """
    svc = ProjectAssignmentService(db, tenant_id)
    return svc.assign_lead_to_available_salesperson(
        lead_id=lead_id,
        project_id=body.project_id,
        scheduled_at=body.scheduled_at,
        unit_id=body.unit_id,
        visit_duration_minutes=body.visit_duration_minutes,
    )


# --- Units & Inventory ---
@router.get("/projects/{project_id}/units")
def list_units(
    project_id: str,
    unit_type: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> list[dict[str, Any]]:
    svc = InventoryService(db, tenant_id)
    return svc.list_units(project_id, unit_type=unit_type, status=status)


@router.post("/projects/{project_id}/units")
def create_unit(
    project_id: str,
    body: UnitCreate,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    svc = InventoryService(db, tenant_id)
    return svc.create_unit(
        project_id=project_id,
        unit_number=body.unit_number,
        unit_type=body.unit_type,
        base_price=body.base_price,
        tower=body.tower,
        floor=body.floor,
        carpet_sqft=body.carpet_sqft,
    )


@router.post("/units/{unit_id}/hold")
def request_unit_hold(
    unit_id: str,
    body: HoldRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    svc = InventoryService(db, tenant_id)
    return svc.request_unit_hold(
        unit_id=unit_id,
        lead_id=body.lead_id,
        deposit_amount=body.deposit_amount,
        notes=body.notes,
    )


@router.post("/holds/{hold_id}/release")
def release_unit_hold(
    hold_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    svc = InventoryService(db, tenant_id)
    return svc.release_hold(hold_id)


# --- Site Visits ---
@router.get("/leads/{lead_id}/visits")
def list_lead_visits(
    lead_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> list[dict[str, Any]]:
    svc = VisitService(db, tenant_id)
    return svc.list_visits_for_lead(lead_id)


@router.post("/leads/{lead_id}/visits")
def schedule_lead_visit(
    lead_id: str,
    body: VisitSchedule,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    svc = VisitService(db, tenant_id)
    return svc.schedule_visit(
        lead_id=lead_id,
        project_id=body.project_id,
        scheduled_at=body.scheduled_at,
        unit_id=body.unit_id,
        assigned_agent=body.assigned_agent,
        escort_contact=body.escort_contact,
        pickup_required=body.pickup_required,
    )


@router.post("/visits/{visit_id}/outcome")
def update_visit_outcome(
    visit_id: str,
    body: VisitOutcome,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    svc = VisitService(db, tenant_id)
    return svc.record_visit_outcome(
        visit_id=visit_id,
        status=body.status,
        tour_feedback=body.tour_feedback,
        buyer_interest_level=body.buyer_interest_level,
    )


# --- Channel Partners ---
@router.get("/leads/{lead_id}/broker")
def get_lead_broker(
    lead_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any] | None:
    svc = PartnerService(db, tenant_id)
    return svc.get_attribution_for_lead(lead_id)


@router.post("/leads/{lead_id}/broker")
def attribute_lead_broker(
    lead_id: str,
    body: BrokerAttribution,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    svc = PartnerService(db, tenant_id)
    return svc.attribute_broker(
        lead_id=lead_id,
        brokerage_name=body.brokerage_name,
        broker_agent_name=body.broker_agent_name,
        broker_email=body.broker_email,
        broker_phone=body.broker_phone,
        rera_id=body.rera_id,
        commission_pct=body.commission_pct,
        agreement_doc_url=body.agreement_doc_url,
    )


@router.post("/leads/{lead_id}/commission")
def calculate_lead_commission(
    lead_id: str,
    body: CommissionCalc,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    svc = PartnerService(db, tenant_id)
    return svc.calculate_commission(lead_id, body.booking_amount)


# --- Funnel Analytics & Conversion Metrics ---
@router.get("/analytics/funnel")
def get_real_estate_funnel_analytics_endpoint(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    from app.services.sales_os.real_estate.analytics_service import get_real_estate_funnel_analytics
    return get_real_estate_funnel_analytics(db=db, tenant_id=tenant_id)


# --- AI Property Matching ---
@router.get("/inquiries/{lead_id}/matches")
def match_properties_for_inquiry(
    lead_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    from app.services.sales_os.real_estate.property_matching_service import PropertyMatchingService
    svc = PropertyMatchingService(db, tenant_id)
    return svc.find_top_matches(lead_id, limit=limit)


# --- Bookings Lifecycle ---
@router.get("/bookings")
def list_bookings(
    project_id: str | None = Query(None),
    lead_id: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> list[dict[str, Any]]:
    from app.services.sales_os.real_estate.booking_service import BookingService
    svc = BookingService(db, tenant_id)
    return svc.list_bookings(project_id=project_id, lead_id=lead_id, status=status)


@router.get("/bookings/{booking_id}")
def get_booking(
    booking_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    from app.services.sales_os.real_estate.booking_service import BookingService
    svc = BookingService(db, tenant_id)
    return svc.get_booking(booking_id)


@router.post("/bookings")
def create_booking(
    body: BookingCreate,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    from app.services.sales_os.real_estate.booking_service import BookingService
    from app.services.sales_os.real_estate.commission_ledger_service import CommissionLedgerService

    svc = BookingService(db, tenant_id)
    res = svc.create_booking_application(
        lead_id=body.lead_id,
        unit_id=body.unit_id,
        agreed_price=body.agreed_price,
        buyer_legal_name=body.buyer_legal_name,
        buyer_id_number=body.buyer_id_number,
        co_buyers=body.co_buyers,
        payment_plan=body.payment_plan,
        deposit_paid=body.deposit_paid,
        sales_rep_id=body.sales_rep_id,
        hold_id=body.hold_id,
    )

    # Automatically accrue commission ledger if broker attributed
    try:
        c_svc = CommissionLedgerService(db, tenant_id)
        c_svc.accrue_booking_commissions(res["id"])
    except Exception:
        pass

    return res


@router.post("/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: str,
    body: BookingCancel,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    from app.services.sales_os.real_estate.booking_service import BookingService
    from app.services.sales_os.real_estate.commission_ledger_service import CommissionLedgerService

    svc = BookingService(db, tenant_id)
    res = svc.cancel_booking(booking_id, reason=body.reason, refund_amount=body.refund_amount)

    # Reverse unpaid commissions
    try:
        c_svc = CommissionLedgerService(db, tenant_id)
        c_svc.reverse_commissions_for_booking(booking_id, reason=body.reason)
    except Exception:
        pass

    return res


# --- Payments & Reconciliation ---
@router.get("/payments")
def list_payments(
    booking_id: str | None = Query(None),
    lead_id: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> list[dict[str, Any]]:
    from app.services.sales_os.real_estate.payment_reconciliation_service import PaymentReconciliationService
    svc = PaymentReconciliationService(db, tenant_id)
    return svc.list_transactions(booking_id=booking_id, lead_id=lead_id, status=status)


@router.post("/payments/reconcile")
def record_payment_event(
    body: PaymentEventCreate,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    from app.services.sales_os.real_estate.payment_reconciliation_service import PaymentReconciliationService
    svc = PaymentReconciliationService(db, tenant_id)
    return svc.record_payment_event(
        idempotency_key=body.idempotency_key,
        lead_id=body.lead_id,
        amount=body.amount,
        payment_method=body.payment_method,
        payment_reference=body.payment_reference,
        transaction_type=body.transaction_type,
        booking_id=body.booking_id,
        hold_id=body.hold_id,
        proof_document_url=body.proof_document_url,
        auto_verify=body.auto_verify,
        notes=body.notes,
    )


@router.post("/payments/{transaction_id}/verify")
def verify_payment(
    transaction_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: Any = Depends(deps.get_current_user),
) -> dict[str, Any]:
    from app.services.sales_os.real_estate.payment_reconciliation_service import PaymentReconciliationService
    svc = PaymentReconciliationService(db, tenant_id)
    user_id = getattr(current_user, "id", "admin")
    return svc.verify_transaction(transaction_id, verified_by_user_id=user_id)


# --- Commission Ledgers ---
@router.get("/commissions/ledger")
def list_commission_ledgers(
    booking_id: str | None = Query(None),
    broker_attribution_id: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> list[dict[str, Any]]:
    from app.services.sales_os.real_estate.commission_ledger_service import CommissionLedgerService
    svc = CommissionLedgerService(db, tenant_id)
    return svc.list_ledgers(booking_id=booking_id, broker_attribution_id=broker_attribution_id, status=status)


@router.post("/commissions/{ledger_id}/payout")
def record_commission_payout(
    ledger_id: str,
    body: CommissionPayout,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: Any = Depends(deps.get_current_user),
) -> dict[str, Any]:
    from app.services.sales_os.real_estate.commission_ledger_service import CommissionLedgerService
    svc = CommissionLedgerService(db, tenant_id)
    user_id = getattr(current_user, "id", "finance_manager")
    return svc.record_payout(ledger_id, payout_reference=body.payout_reference, approved_by_user_id=user_id)


# --- Durable Jobs Trigger Endpoints ---
@router.post("/jobs/expire-holds")
def trigger_expire_holds_job(
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    from app.workers.real_estate_jobs import expire_stale_holds_job
    return expire_stale_holds_job(tenant_id=tenant_id)


@router.post("/jobs/dispatch-reminders")
def trigger_dispatch_reminders_job() -> dict[str, Any]:
    from app.workers.real_estate_jobs import dispatch_upcoming_visit_reminders_job
    return dispatch_upcoming_visit_reminders_job(window_minutes=120)


