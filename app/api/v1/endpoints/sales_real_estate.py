"""Real Estate domain endpoints for project catalog, units, holds, visits, and broker attribution."""
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.services.sales_os.real_estate.inventory_service import InventoryService
from app.services.sales_os.real_estate.visit_service import VisitService
from app.services.sales_os.real_estate.partner_service import PartnerService

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    code: str | None = None
    location: str | None = None
    city: str | None = None
    hold_duration_hours: int = 48


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
        hold_duration_hours=body.hold_duration_hours,
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


# --- Funnel Analytics & Conversion Metrics (Phase 6) ---
@router.get("/analytics/funnel")
def get_real_estate_funnel_analytics_endpoint(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    from app.services.sales_os.real_estate.analytics_service import get_real_estate_funnel_analytics
    return get_real_estate_funnel_analytics(db=db, tenant_id=tenant_id)

