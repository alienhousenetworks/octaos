"""Field Sales & Smart Visit Scheduling Endpoints."""
from __future__ import annotations
from datetime import datetime, date, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.models.base import User
from app.models.real_estate import RealEstateSiteVisit, RealEstateProject, RealEstateUnit
from app.models.field_sales import SalespersonFieldStatus, FieldScheduleRecoveryProposal
from app.models.verticals import Lead
from app.services.sales_os.real_estate.visit_service import VisitService
from app.services.sales_os.field_sales.connectors.budget_controller import ConnectorBudgetController
from app.services.sales_os.field_sales.engine.optimizer import ScheduleOptimizer
from app.services.sales_os.field_sales.engine.recovery import ScheduleRecoveryEngine
from app.services.sales_os.field_sales.engine.nlp_agent import NaturalLanguageDispatchAgent
from app.services.sales_os.field_sales.orchestrator_bridge import FieldSalesOrchestratorBridge

router = APIRouter()


class AgentLocationUpdate(BaseModel):
    latitude: float
    longitude: float
    accuracy: float = 10.0
    battery_level: int | None = None
    speed: float | None = None
    heading: float | None = None


class AgentShiftToggle(BaseModel):
    is_active: bool
    status: str = "available"


class VisitGPSCheckIn(BaseModel):
    latitude: float
    longitude: float
    accuracy: float = 10.0
    manual_exception_reason: str | None = None


class VisitOutcomeRecord(BaseModel):
    status: str  # completed, cancelled, no_show
    tour_feedback: str | None = None
    buyer_interest_level: str | None = None
    buyer_objections: list[str] = Field(default_factory=list)
    agreed_next_step: str | None = None


class AIPlanRequest(BaseModel):
    prompt: str = Field(..., min_length=2)


class AIRecoverRequest(BaseModel):
    visit_id: str
    delay_minutes: int = 30
    delay_reason: str = "Extended showing / transit traffic"


class ProposalDecision(BaseModel):
    reason: str = ""


class OfflineSyncBatch(BaseModel):
    events: list[dict[str, Any]] = Field(default_factory=list)


# --- Dashboard Overview ---
@router.get("/overview")
def get_field_sales_overview(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_visits = (
        db.query(RealEstateSiteVisit)
        .filter(
            RealEstateSiteVisit.tenant_id == tenant_id,
            RealEstateSiteVisit.scheduled_at >= today_start,
        )
        .all()
    )
    total_today = len(today_visits)
    completed = sum(1 for v in today_visits if v.status == "completed")
    delayed = sum(1 for v in today_visits if v.status == "delayed")
    no_shows = sum(1 for v in today_visits if v.status == "no_show")

    active_agents = (
        db.query(SalespersonFieldStatus)
        .filter(
            SalespersonFieldStatus.tenant_id == tenant_id,
            SalespersonFieldStatus.is_shift_active == True,
        )
        .count()
    )

    budget_ctrl = ConnectorBudgetController(db, tenant_id)
    budget_stats = budget_ctrl.get_budget_stats()

    return {
        "today_scheduled": total_today,
        "today_completed": completed,
        "today_delayed": delayed,
        "today_no_shows": no_shows,
        "completion_rate_pct": round((completed / max(1, total_today)) * 100, 1),
        "active_salespeople": active_agents,
        "connector_budget": budget_stats,
    }


# --- Live Dispatch Map ---
@router.get("/dispatch-map")
def get_dispatch_map_data(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    # Active/authorized salespeople
    agents = (
        db.query(SalespersonFieldStatus)
        .filter(SalespersonFieldStatus.tenant_id == tenant_id)
        .all()
    )
    salespeople = []
    for a in agents:
        user = db.query(User).filter(User.id == a.user_id).first()
        salespeople.append({
            "user_id": a.user_id,
            "name": user.name if user and user.name else (user.email if user else a.user_id),
            "email": user.email if user else None,
            "status": a.status,
            "is_shift_active": a.is_shift_active,
            "latitude": a.last_latitude,
            "longitude": a.last_longitude,
            "accuracy": a.last_accuracy,
            "battery_level": a.battery_level,
            "speed": a.speed,
            "last_updated": a.last_location_updated_at.isoformat() if a.last_location_updated_at else None,
        })

    # Today's project visit markers
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    visits = (
        db.query(RealEstateSiteVisit)
        .filter(
            RealEstateSiteVisit.tenant_id == tenant_id,
            RealEstateSiteVisit.scheduled_at >= today_start,
        )
        .all()
    )
    visit_pins = []
    for v in visits:
        project = db.query(RealEstateProject).filter(RealEstateProject.id == v.project_id).first()
        lead = db.query(Lead).filter(Lead.id == v.lead_id).first()
        visit_pins.append({
            "visit_id": v.id,
            "project_name": project.name if project else "Project Site",
            "project_location": project.location if project else None,
            "latitude": project.latitude if project and project.latitude else 12.9716,
            "longitude": project.longitude if project and project.longitude else 77.5946,
            "buyer_name": lead.name if lead else "Prospective Buyer",
            "buyer_phone": (lead.phone or lead.mobile_no) if lead else None,
            "scheduled_at": v.scheduled_at.isoformat(),
            "status": v.status,
            "assigned_agent": v.assigned_agent,
            "sequence_order": v.sequence_order,
            "estimated_travel_minutes": v.estimated_travel_minutes,
        })

    return {
        "salespeople": salespeople,
        "visits": visit_pins,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# --- Team Schedule Planner ---
@router.get("/schedule")
def get_team_schedule(
    target_date: str | None = Query(None),
    agent_id: str | None = Query(None),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    day = date.fromisoformat(target_date) if target_date else date.today()
    start_dt = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(day, datetime.max.time(), tzinfo=timezone.utc)

    query = db.query(RealEstateSiteVisit).filter(
        RealEstateSiteVisit.tenant_id == tenant_id,
        RealEstateSiteVisit.scheduled_at >= start_dt,
        RealEstateSiteVisit.scheduled_at <= end_dt,
    )
    if agent_id:
        query = query.filter(RealEstateSiteVisit.assigned_agent == agent_id)

    visits = query.order_by(RealEstateSiteVisit.scheduled_at.asc()).all()
    records = []
    for v in visits:
        project = db.query(RealEstateProject).filter(RealEstateProject.id == v.project_id).first()
        lead = db.query(Lead).filter(Lead.id == v.lead_id).first()
        records.append({
            "id": v.id,
            "lead_id": v.lead_id,
            "buyer_name": lead.name if lead else "Buyer",
            "buyer_phone": (lead.phone or lead.mobile_no) if lead else None,
            "project_id": v.project_id,
            "project_name": project.name if project else "Project",
            "project_location": project.location if project else None,
            "scheduled_at": v.scheduled_at.isoformat(),
            "estimated_arrival_at": v.estimated_arrival_at.isoformat() if v.estimated_arrival_at else None,
            "duration_minutes": v.duration_minutes,
            "sequence_order": v.sequence_order,
            "estimated_travel_minutes": v.estimated_travel_minutes,
            "status": v.status,
            "assigned_agent": v.assigned_agent,
            "check_in_verified": v.check_in_verified,
        })

    return {
        "date": day.isoformat(),
        "visits": records,
        "total_count": len(records),
    }


# --- Prioritized Leads for Site Visits ---
@router.get("/priority-leads")
def get_priority_leads_for_showings(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> list[dict[str, Any]]:
    leads = (
        db.query(Lead)
        .filter(Lead.tenant_id == tenant_id)
        .order_by(Lead.score.desc().nullslast())
        .limit(20)
        .all()
    )
    results = []
    for l in leads:
        # Check if already has visit
        visit_count = db.query(RealEstateSiteVisit).filter(RealEstateSiteVisit.lead_id == l.id).count()
        results.append({
            "id": l.id,
            "name": l.name,
            "email": l.email,
            "phone": l.phone or l.mobile_no,
            "score": l.score or 50,
            "status": l.status,
            "budget": l.need_of_what or "₹1.5Cr - ₹2.5Cr",
            "why": l.why or "High intent 3BHK search near Tech Corridor",
            "existing_visits_count": visit_count,
            "recommended_action": "Schedule Showing" if visit_count == 0 else "Follow-up After Visit",
        })
    return results


# --- Mobile Salesperson Endpoints ---
@router.post("/agent/location")
def update_agent_location(
    body: AgentLocationUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    status_row = (
        db.query(SalespersonFieldStatus)
        .filter(
            SalespersonFieldStatus.tenant_id == tenant_id,
            SalespersonFieldStatus.user_id == current_user.id,
        )
        .first()
    )
    if not status_row:
        status_row = SalespersonFieldStatus(
            tenant_id=tenant_id,
            user_id=current_user.id,
        )
        db.add(status_row)

    status_row.last_latitude = body.latitude
    status_row.last_longitude = body.longitude
    status_row.last_accuracy = body.accuracy
    status_row.last_location_updated_at = datetime.now(timezone.utc)
    if body.battery_level is not None:
        status_row.battery_level = body.battery_level
    if body.speed is not None:
        status_row.speed = body.speed
    if body.heading is not None:
        status_row.heading = body.heading

    db.commit()
    return {"status": "UPDATED", "user_id": current_user.id, "timestamp": status_row.last_location_updated_at.isoformat()}


@router.post("/agent/shift")
def toggle_agent_shift(
    body: AgentShiftToggle,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    status_row = (
        db.query(SalespersonFieldStatus)
        .filter(
            SalespersonFieldStatus.tenant_id == tenant_id,
            SalespersonFieldStatus.user_id == current_user.id,
        )
        .first()
    )
    if not status_row:
        status_row = SalespersonFieldStatus(
            tenant_id=tenant_id,
            user_id=current_user.id,
        )
        db.add(status_row)

    status_row.is_shift_active = body.is_active
    status_row.status = body.status if body.is_active else "off_duty"
    if body.is_active:
        status_row.shift_started_at = datetime.now(timezone.utc)
    else:
        status_row.shift_ended_at = datetime.now(timezone.utc)

    db.commit()
    return {
        "user_id": current_user.id,
        "is_shift_active": status_row.is_shift_active,
        "status": status_row.status,
    }


@router.get("/agent/my-day")
def get_agent_my_day(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59)

    visits = (
        db.query(RealEstateSiteVisit)
        .filter(
            RealEstateSiteVisit.tenant_id == tenant_id,
            RealEstateSiteVisit.assigned_agent == current_user.id,
            RealEstateSiteVisit.scheduled_at >= today_start,
            RealEstateSiteVisit.scheduled_at <= today_end,
        )
        .order_by(RealEstateSiteVisit.scheduled_at.asc())
        .all()
    )

    items = []
    for v in visits:
        proj = db.query(RealEstateProject).filter(RealEstateProject.id == v.project_id).first()
        lead = db.query(Lead).filter(Lead.id == v.lead_id).first()
        unit = db.query(RealEstateUnit).filter(RealEstateUnit.id == v.unit_id).first() if v.unit_id else None
        items.append({
            "id": v.id,
            "project_name": proj.name if proj else "Project",
            "project_address": (proj.address or proj.location) if proj else "Project Location",
            "latitude": proj.latitude if proj and proj.latitude else 12.9716,
            "longitude": proj.longitude if proj and proj.longitude else 77.5946,
            "buyer_name": lead.name if lead else "Buyer",
            "buyer_phone": (lead.phone or lead.mobile_no) if lead else "",
            "buyer_email": lead.email if lead else "",
            "unit_number": unit.unit_number if unit else None,
            "unit_type": unit.unit_type if unit else None,
            "scheduled_at": v.scheduled_at.isoformat(),
            "duration_minutes": v.duration_minutes,
            "sequence_order": v.sequence_order,
            "estimated_travel_minutes": v.estimated_travel_minutes,
            "status": v.status,
            "check_in_verified": v.check_in_verified,
            "recovery_notes": v.recovery_notes,
        })

    # Shift status
    shift = (
        db.query(SalespersonFieldStatus)
        .filter(
            SalespersonFieldStatus.tenant_id == tenant_id,
            SalespersonFieldStatus.user_id == current_user.id,
        )
        .first()
    )

    # Check for active recovery proposal
    proposal = (
        db.query(FieldScheduleRecoveryProposal)
        .filter(
            FieldScheduleRecoveryProposal.tenant_id == tenant_id,
            FieldScheduleRecoveryProposal.affected_user_id == current_user.id,
            FieldScheduleRecoveryProposal.status == "pending_review",
        )
        .order_by(FieldScheduleRecoveryProposal.created_at.desc())
        .first()
    )

    return {
        "user_id": current_user.id,
        "is_shift_active": shift.is_shift_active if shift else False,
        "agent_status": shift.status if shift else "off_duty",
        "visits": items,
        "total_visits_today": len(items),
        "pending_proposal": {
            "id": proposal.id,
            "rationale": proposal.rationale,
            "changes": proposal.proposed_changes,
        } if proposal else None,
    }


# --- Visit GPS Check-In & Outcomes ---
@router.post("/visits/{visit_id}/check-in")
def check_in_visit(
    visit_id: str,
    body: VisitGPSCheckIn,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    svc = VisitService(db, tenant_id)
    return svc.record_gps_check_in(
        visit_id=visit_id,
        latitude=body.latitude,
        longitude=body.longitude,
        accuracy=body.accuracy,
        manual_exception_reason=body.manual_exception_reason,
    )


@router.post("/visits/{visit_id}/outcome")
def record_visit_outcome(
    visit_id: str,
    body: VisitOutcomeRecord,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    svc = VisitService(db, tenant_id)
    return svc.record_visit_outcome(
        visit_id=visit_id,
        status=body.status,
        tour_feedback=body.tour_feedback,
        buyer_interest_level=body.buyer_interest_level,
        buyer_objections=body.buyer_objections,
        agreed_next_step=body.agreed_next_step,
    )


# --- AI Dispatch & Recovery Endpoints ---
@router.post("/ai/plan")
async def ai_plan_schedule(
    body: AIPlanRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    agent = NaturalLanguageDispatchAgent(db, tenant_id)
    return await agent.execute_command(body.prompt, current_user.id)


@router.post("/ai/recover")
def trigger_ai_recovery(
    body: AIRecoverRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    engine = ScheduleRecoveryEngine(db, tenant_id)
    return engine.detect_and_propose_recovery(
        delayed_visit_id=body.visit_id,
        delay_minutes=body.delay_minutes,
        delay_reason=body.delay_reason,
    )


@router.get("/ai/proposals")
def list_ai_proposals(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> list[dict[str, Any]]:
    proposals = (
        db.query(FieldScheduleRecoveryProposal)
        .filter(FieldScheduleRecoveryProposal.tenant_id == tenant_id)
        .order_by(FieldScheduleRecoveryProposal.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": p.id,
            "trigger_type": p.trigger_type,
            "status": p.status,
            "affected_user_id": p.affected_user_id,
            "rationale": p.rationale,
            "proposed_changes": p.proposed_changes,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
        }
        for p in proposals
    ]


@router.post("/ai/proposals/{proposal_id}/approve")
def approve_proposal(
    proposal_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    engine = ScheduleRecoveryEngine(db, tenant_id)
    return engine.apply_proposal(proposal_id, current_user.id)


@router.post("/ai/proposals/{proposal_id}/reject")
def reject_proposal(
    proposal_id: str,
    body: ProposalDecision,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    engine = ScheduleRecoveryEngine(db, tenant_id)
    return engine.reject_proposal(proposal_id, current_user.id, body.reason)


# --- Orchestrator Analysis Report Endpoint ---
@router.get("/analysis-report")
def get_field_sales_analysis_report(
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    bridge = FieldSalesOrchestratorBridge(db, tenant_id)
    return bridge.generate_analysis_report(period_days)


# --- Offline Batch Sync ---
@router.post("/sync/offline")
def sync_offline_events(
    body: OfflineSyncBatch,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    svc = VisitService(db, tenant_id)
    results = []
    for ev in body.events:
        ev_type = ev.get("type")
        v_id = ev.get("visit_id")
        try:
            if ev_type == "check_in" and v_id:
                res = svc.record_gps_check_in(
                    visit_id=v_id,
                    latitude=ev.get("latitude", 0.0),
                    longitude=ev.get("longitude", 0.0),
                    accuracy=ev.get("accuracy", 10.0),
                    manual_exception_reason=ev.get("manual_exception_reason"),
                )
                results.append({"event_id": ev.get("id"), "status": "SYNCED", "result": res})
            elif ev_type == "outcome" and v_id:
                res = svc.record_visit_outcome(
                    visit_id=v_id,
                    status=ev.get("status", "completed"),
                    tour_feedback=ev.get("tour_feedback"),
                    buyer_interest_level=ev.get("buyer_interest_level"),
                    buyer_objections=ev.get("buyer_objections", []),
                    agreed_next_step=ev.get("agreed_next_step"),
                )
                results.append({"event_id": ev.get("id"), "status": "SYNCED", "result": res})
            else:
                results.append({"event_id": ev.get("id"), "status": "SKIPPED", "reason": "Unknown event type"})
        except Exception as e:
            results.append({"event_id": ev.get("id"), "status": "FAILED", "error": str(e)})

    return {"synced_count": len([r for r in results if r["status"] == "SYNCED"]), "results": results}


# --- Connector Budget Stats ---
@router.get("/budget")
def get_connector_budget(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    ctrl = ConnectorBudgetController(db, tenant_id)
    return ctrl.get_budget_stats()
