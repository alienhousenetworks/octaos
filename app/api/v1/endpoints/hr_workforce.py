"""
HR Workforce & Compensation API Endpoints.
Covers Leave Management, Ledger Balances, Time & Attendance, and Shift Rosters.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.api import deps
from app.models.base import User
from app.models.hr_core import EmployeeProfile
from app.models.hr_workforce import (
    LeaveType, LeaveLedgerEntry, LeaveRequest, AttendanceRecord, AttendanceAuditEvent, ShiftRoster, ShiftAssignment,
    EmployeeAvailability, ShiftDemand
)
from app.services.agents.hr.specialists.leave_impact import LeaveImpactSpecialist
from app.services.agents.hr.approval_bridge import HRApprovalBridge
from app.services.agents.hr.schemas import RiskTier

router = APIRouter()

def _role(user: User) -> str:
    return (getattr(user, "role", None) or "").strip().lower().replace("-", "_").replace(" ", "_")


def _has_hr_permission(user: User, codename: str) -> bool:
    if getattr(user, "is_system_admin", False) or getattr(user, "is_superuser", False):
        return True
    if _role(user) in {"admin", "organization_admin", "super_admin"}:
        return True
    effective = {getattr(permission, "codename", "") for permission in (getattr(user, "user_permissions", None) or [])}
    for group in (getattr(user, "groups", None) or []):
        effective.update(getattr(permission, "codename", "") for permission in (getattr(group, "permissions", None) or []))
    return codename in effective


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _require_hr_role(user: User, approve: bool = False, permission: Optional[str] = None) -> None:
    # Permission codenames come from app.services.rbac_service.SYSTEM_PERMISSIONS.
    codename = permission or ("hr.manage_leave" if approve else "hr.view_employees")
    if not _has_hr_permission(user, codename):
        raise HTTPException(status_code=403, detail=f"Missing required permission: {codename}.")



def _require_self_or_hr(user: User, employee: EmployeeProfile) -> None:
    if getattr(user, "is_system_admin", False) or getattr(user, "is_superuser", False) or _has_hr_permission(user, "hr.manage_leave") or _has_hr_permission(user, "hr.manage_employees"):
        return
    if employee.user_id and str(employee.user_id) == str(user.id):
        return
    raise HTTPException(status_code=403, detail="You may only access your own employee record.")

class LeaveSubmitRequest(BaseModel):
    employee_id: str
    leave_type_code: str = "ANNUAL"
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    days_requested: float
    reason: Optional[str] = None


class AttendancePunchRequest(BaseModel):
    employee_id: str
    punch_type: str = "clock_in"  # clock_in, clock_out
    work_date: Optional[str] = None
    timezone: str = "UTC"


class RosterOptimizeRequest(BaseModel):
    roster_id: str



class AvailabilityCreateRequest(BaseModel):
    employee_id: str
    starts_at: datetime
    ends_at: datetime
    status: str = "available"


class ShiftDemandCreateRequest(BaseModel):
    roster_id: str
    shift_name: str = Field(min_length=2, max_length=100)
    starts_at: datetime
    ends_at: datetime
    role_required: Optional[str] = None
    required_headcount: int = Field(default=1, ge=1, le=500)


@router.get("/leaves")
def list_leaves(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    status: Optional[str] = None,
    current_user: User = Depends(deps.get_current_user),
):
    """Retrieve leave requests with employee details and coverage scores."""
    _require_hr_role(current_user)
    q = db.query(LeaveRequest).filter(LeaveRequest.tenant_id == tenant_id)
    if status:
        q = q.filter(LeaveRequest.status == status.lower())

    requests = q.order_by(LeaveRequest.created_at.desc()).all()
    results = []
    for r in requests:
        emp = db.query(EmployeeProfile).filter_by(id=r.employee_id, tenant_id=tenant_id).first()
        ltype = db.query(LeaveType).filter_by(id=r.leave_type_id, tenant_id=tenant_id).first()
        results.append({
            "id": r.id,
            "employee_id": r.employee_id,
            "employee_name": emp.full_name if emp else "Unknown",
            "department": emp.department_name if emp else "General",
            "leave_type": ltype.name if ltype else "Leave",
            "start_date": r.start_date.strftime("%Y-%m-%d"),
            "end_date": r.end_date.strftime("%Y-%m-%d"),
            "days_requested": r.days_requested,
            "reason": r.reason,
            "status": r.status,
            "coverage_score": r.coverage_score,
            "ai_risk_level": r.ai_risk_level,
            "ai_coverage_notes": r.ai_coverage_notes,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else None
        })
    return results


@router.post("/leaves")
def submit_leave_request(
    payload: LeaveSubmitRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user)
):
    """Submit a leave request and evaluate staffing coverage."""
    if payload.days_requested <= 0:
        raise HTTPException(status_code=422, detail="Requested leave days must be greater than zero.")
    emp = db.query(EmployeeProfile).filter_by(id=payload.employee_id, tenant_id=tenant_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    _require_self_or_hr(current_user, emp)

    try:
        s_date = datetime.strptime(payload.start_date, "%Y-%m-%d")
        e_date = datetime.strptime(payload.end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")

    if e_date < s_date:
        raise HTTPException(status_code=422, detail="End date must be on or after start date.")
    ltype = db.query(LeaveType).filter_by(tenant_id=tenant_id, code=payload.leave_type_code.strip().upper(), is_active=True).first()
    if not ltype:
        raise HTTPException(status_code=422, detail="The requested leave type is not configured for this organization.")

    # Run AI Coverage Evaluation
    evaluator = LeaveImpactSpecialist(db, tenant_id)
    impact = evaluator.evaluate_leave_request(
        employee_id=emp.id,
        leave_type_code=payload.leave_type_code,
        start_date=s_date,
        end_date=e_date,
        days_requested=payload.days_requested
    )

    req = LeaveRequest(
        tenant_id=tenant_id,
        employee_id=emp.id,
        leave_type_id=ltype.id,
        start_date=s_date,
        end_date=e_date,
        days_requested=payload.days_requested,
        reason=payload.reason,
        status="pending",
        coverage_score=impact.coverage_score,
        conflict_count=impact.conflicting_leaves_count,
        ai_risk_level=impact.risk_tier.value.lower(),
        ai_coverage_notes=impact.explanation
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    return {
        "id": req.id,
        "status": req.status,
        "coverage_score": req.coverage_score,
        "ai_risk_level": req.ai_risk_level,
        "notes": req.ai_coverage_notes,
        "message": "Leave request submitted for review."
    }


@router.post("/leaves/{id}/impact-assessment")
def check_leave_impact(
    id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    """Re-runs the staffing coverage assessment for an existing leave request."""
    _require_hr_role(current_user)
    req = db.query(LeaveRequest).filter_by(id=id, tenant_id=tenant_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")

    ltype = db.query(LeaveType).filter_by(id=req.leave_type_id, tenant_id=tenant_id).first()
    evaluator = LeaveImpactSpecialist(db, tenant_id)
    impact = evaluator.evaluate_leave_request(
        employee_id=req.employee_id,
        leave_type_code=ltype.code if ltype else "ANNUAL",
        start_date=req.start_date,
        end_date=req.end_date,
        days_requested=req.days_requested
    )

    # Update persisted score
    req.coverage_score = impact.coverage_score
    req.conflict_count = impact.conflicting_leaves_count
    req.ai_coverage_notes = impact.explanation
    db.commit()

    return impact.dict()


@router.post("/leaves/{id}/approve")
def approve_leave(
    id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Approves a pending leave request and appends its ledger deduction.
    """
    _require_hr_role(current_user, approve=True)
    req = db.query(LeaveRequest).filter_by(id=id, tenant_id=tenant_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")

    # Lock the request and re-check both request state and ledger before writing.
    req = db.query(LeaveRequest).filter_by(id=id, tenant_id=tenant_id).with_for_update().first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    existing_entry = db.query(LeaveLedgerEntry).filter_by(
        tenant_id=tenant_id, transaction_type="deduction", reference_id=req.id
    ).first()
    if req.status == "approved" and existing_entry:
        return {"status": "already_approved", "message": "Leave request and ledger are already up to date."}
    if req.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending leave requests can be approved.")
    if existing_entry:
        raise HTTPException(status_code=409, detail="A leave deduction already exists; HR reconciliation is required.")

    try:
        req.status = "approved"
        req.approver_user_id = current_user.id
        req.approved_at = datetime.utcnow()
        db.add(LeaveLedgerEntry(
            tenant_id=tenant_id,
            employee_id=req.employee_id,
            leave_type_id=req.leave_type_id,
            transaction_type="deduction",
            amount_days=-abs(req.days_requested),
            reference_id=req.id,
            note=f"Approved leave from {req.start_date.strftime('%Y-%m-%d')} to {req.end_date.strftime('%Y-%m-%d')}",
            created_by_user_id=current_user.id
        ))
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "id": req.id,
        "status": "approved",
        "days_deducted": req.days_requested,
        "message": "Leave approved and deducted from employee ledger."
    }


@router.get("/leaves/balances/{employee_id}")
def get_leave_balances(
    employee_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    """Calculates tenant-scoped balance for all leave types from ledger entries."""
    emp = db.query(EmployeeProfile).filter_by(id=employee_id, tenant_id=tenant_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")
    if not (getattr(current_user, "is_system_admin", False) or getattr(current_user, "is_superuser", False) or _has_hr_permission(current_user, "hr.manage_workforce") or _has_hr_permission(current_user, "hr.manage_employees") or _has_hr_permission(current_user, "hr.manage_leave") or (emp.user_id and str(emp.user_id) == str(current_user.id))):
        raise HTTPException(status_code=403, detail="You may only view your own leave balance.")
    ltypes = db.query(LeaveType).filter_by(tenant_id=tenant_id, is_active=True).all()
    evaluator = LeaveImpactSpecialist(db, tenant_id)

    balances = []
    for lt in ltypes:
        bal = evaluator.get_employee_balance(employee_id, lt.id)
        balances.append({
            "leave_type_id": lt.id,
            "name": lt.name,
            "code": lt.code,
            "annual_allowance": lt.annual_allowance_days,
            "current_balance": bal
        })
    return balances


@router.get("/attendance")
def list_attendance(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    date: Optional[str] = None,
    current_user: User = Depends(deps.get_current_user),
):
    """Retrieve daily attendance records with anomaly indicators."""
    _require_hr_role(current_user)
    q = db.query(AttendanceRecord).filter(AttendanceRecord.tenant_id == tenant_id)
    records = q.order_by(AttendanceRecord.work_date.desc()).limit(100).all()

    results = []
    for r in records:
        emp = db.query(EmployeeProfile).filter_by(id=r.employee_id, tenant_id=tenant_id).first()
        results.append({
            "id": r.id,
            "employee_id": r.employee_id,
            "employee_name": emp.full_name if emp else "Unknown",
            "department": emp.department_name if emp else "General",
            "work_date": r.work_date.strftime("%Y-%m-%d"),
            "clock_in": r.clock_in.strftime("%H:%M") if r.clock_in else None,
            "clock_out": r.clock_out.strftime("%H:%M") if r.clock_out else None,
            "total_hours": r.total_hours,
            "status": r.status,
            "anomaly_detected": r.anomaly_detected,
            "anomaly_type": r.anomaly_type
        })
    return results


@router.post("/attendance/punch")
def punch_attendance(
    payload: AttendancePunchRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    """Record an attendance punch for an employee in this tenant."""
    if payload.punch_type not in {"clock_in", "clock_out"}:
        raise HTTPException(status_code=422, detail="punch_type must be clock_in or clock_out.")
    employee = db.query(EmployeeProfile).filter_by(id=payload.employee_id, tenant_id=tenant_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")
    if not (getattr(current_user, "is_system_admin", False) or getattr(current_user, "is_superuser", False) or _role(current_user) in _HR_ROLES or (employee.user_id and str(employee.user_id) == str(current_user.id))):
        raise HTTPException(status_code=403, detail="You may only record attendance for your own employee record.")
    try:
        employee_tz = ZoneInfo(payload.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(status_code=422, detail="timezone must be a valid IANA timezone, such as Asia/Kolkata.")
    now_utc = datetime.now(timezone.utc)
    local_now = now_utc.astimezone(employee_tz)
    local_day = local_now.date()
    local_midnight = datetime.combine(local_day, datetime.min.time(), tzinfo=employee_tz)
    work_date_utc = local_midnight.astimezone(timezone.utc)
    if payload.work_date and payload.work_date != local_day.isoformat():
        raise HTTPException(status_code=422, detail="Punches must use the current local work date; backdated corrections require a separate audited workflow.")

    rec = db.query(AttendanceRecord).filter_by(
        tenant_id=tenant_id, employee_id=payload.employee_id, work_date=work_date_utc
    ).with_for_update().first()

    now = now_utc
    before_state = {
        "clock_in": rec.clock_in.isoformat() if rec and rec.clock_in else None,
        "clock_out": rec.clock_out.isoformat() if rec and rec.clock_out else None,
        "status": rec.status if rec else None,
    }
    if not rec:
        if payload.punch_type == "clock_out":
            raise HTTPException(status_code=409, detail="Cannot clock out before clocking in.")
        rec = AttendanceRecord(tenant_id=tenant_id, employee_id=payload.employee_id, work_date=today_dt,
                               clock_in=now, status="present", total_hours=0.0)
        db.add(rec)
    elif payload.punch_type == "clock_in":
        if rec.clock_in:
            raise HTTPException(status_code=409, detail="Already clocked in for this workday.")
        if rec.clock_out:
            raise HTTPException(status_code=409, detail="Attendance is already closed for this workday.")
        rec.clock_in = now
        rec.status = "present"
    else:
        if not rec.clock_in:
            raise HTTPException(status_code=409, detail="Cannot clock out before clocking in.")
        if rec.clock_out:
            raise HTTPException(status_code=409, detail="Already clocked out for this workday.")
        clock_in_utc = rec.clock_in
        if clock_in_utc.tzinfo is None:
            clock_in_utc = clock_in_utc.replace(tzinfo=timezone.utc)
        if now < clock_in_utc:
            raise HTTPException(status_code=409, detail="Clock-out time cannot precede clock-in time.")
        rec.clock_out = now
        diff = (now - clock_in_utc).total_seconds() / 3600.0
        rec.total_hours = round(max(0.0, diff - (rec.break_minutes / 60.0)), 2)
    try:
        db.flush()
        db.add(AttendanceAuditEvent(
            tenant_id=tenant_id,
            attendance_record_id=rec.id,
            employee_id=rec.employee_id,
            actor_user_id=str(current_user.id),
            event_type=payload.punch_type,
            occurred_at_utc=now_utc,
            local_timezone=payload.timezone,
            local_work_date=local_day.isoformat(),
            before_state=before_state,
            after_state={
                "clock_in": rec.clock_in.isoformat() if rec.clock_in else None,
                "clock_out": rec.clock_out.isoformat() if rec.clock_out else None,
                "status": rec.status,
                "total_hours": rec.total_hours,
            },
            source="hr_admin" if _role(current_user) in _HR_ROLES else "self_service",
        ))
        db.commit()
        db.refresh(rec)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Attendance was updated concurrently; refresh and retry.")
    except Exception:
        db.rollback()
        raise

    return {
        "id": rec.id,
        "employee_id": rec.employee_id,
        "clock_in": rec.clock_in.strftime("%H:%M") if rec.clock_in else None,
        "clock_out": rec.clock_out.strftime("%H:%M") if rec.clock_out else None,
        "total_hours": rec.total_hours
    }


@router.get("/rosters")
def list_rosters(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    """Retrieve shift rosters and coverage scores."""
    _require_hr_role(current_user)
    rosters = db.query(ShiftRoster).filter_by(tenant_id=tenant_id).order_by(ShiftRoster.start_date.desc()).all()
    results = []
    for r in rosters:
        shifts = db.query(ShiftAssignment).filter_by(roster_id=r.id).all()
        results.append({
            "id": r.id,
            "name": r.name,
            "start_date": r.start_date.strftime("%Y-%m-%d"),
            "end_date": r.end_date.strftime("%Y-%m-%d"),
            "status": r.status,
            "is_optimized": r.is_optimized,
            "optimization_score": r.optimization_score,
            "assignments_count": len(shifts)
        })
    return results


@router.post("/availability")
def create_employee_availability(
    payload: AvailabilityCreateRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    employee = db.query(EmployeeProfile).filter_by(id=payload.employee_id, tenant_id=tenant_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")
    _require_hr_role(current_user, permission="hr.manage_workforce")
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=422, detail="Availability end must be after start.")
    if payload.status not in {"available", "unavailable", "leave"}:
        raise HTTPException(status_code=422, detail="Availability status must be available, unavailable, or leave.")
    row = EmployeeAvailability(tenant_id=tenant_id, employee_id=employee.id, starts_at=payload.starts_at,
                               ends_at=payload.ends_at, status=payload.status, source="hr_admin")
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "employee_id": row.employee_id, "status": row.status}


@router.post("/rosters/demand")
def create_shift_demand(
    payload: ShiftDemandCreateRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    _require_hr_role(current_user, permission="hr.manage_workforce")
    roster = db.query(ShiftRoster).filter_by(id=payload.roster_id, tenant_id=tenant_id).first()
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found in this organization.")
    if roster.status != "draft":
        raise HTTPException(status_code=409, detail="Staffing demand can only be changed on draft rosters.")
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=422, detail="Shift end must be after shift start.")
    if _as_utc(payload.starts_at) < _as_utc(roster.start_date) or _as_utc(payload.ends_at) > _as_utc(roster.end_date):
        raise HTTPException(status_code=422, detail="Demand slot must fit within the roster period.")
    demand = ShiftDemand(tenant_id=tenant_id, roster_id=roster.id, shift_name=payload.shift_name.strip(),
                         starts_at=payload.starts_at, ends_at=payload.ends_at,
                         role_required=payload.role_required.strip().lower() if payload.role_required else None,
                         required_headcount=payload.required_headcount)
    db.add(demand)
    try:
        db.commit()
        db.refresh(demand)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An equivalent demand slot already exists.")
    return {"id": demand.id, "roster_id": demand.roster_id, "required_headcount": demand.required_headcount}


@router.post("/rosters/optimize")
def optimize_roster(
    payload: RosterOptimizeRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    """Greedy constraint-based draft scheduler; only scores constraints that are modeled."""
    _require_hr_role(current_user, permission="hr.manage_workforce")
    roster = db.query(ShiftRoster).filter_by(id=payload.roster_id, tenant_id=tenant_id).with_for_update().first()
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found in this organization.")
    if roster.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft rosters can be optimized.")
    demands = db.query(ShiftDemand).filter_by(tenant_id=tenant_id, roster_id=roster.id).order_by(ShiftDemand.starts_at.asc()).all()
    if not demands:
        raise HTTPException(status_code=422, detail="Configure explicit staffing demand before optimization; demand is never invented.")
    employees = db.query(EmployeeProfile).filter_by(tenant_id=tenant_id, status="active").all()
    availability = db.query(EmployeeAvailability).filter_by(tenant_id=tenant_id, status="available").all()
    unavailable = db.query(EmployeeAvailability).filter_by(tenant_id=tenant_id).filter(EmployeeAvailability.status.in_(["unavailable", "leave"])).all()
    availability_by_employee = {}
    for window in availability:
        availability_by_employee.setdefault(window.employee_id, []).append(window)
    unavailable_by_employee = {}
    for window in unavailable:
        unavailable_by_employee.setdefault(window.employee_id, []).append(window)

    def overlaps(a_start, a_end, b_start, b_end):
        return _as_utc(a_start) < _as_utc(b_end) and _as_utc(b_start) < _as_utc(a_end)

    # Existing assignments from other rosters are respected; this optimizer never edits published rosters.
    other_assignments = db.query(ShiftAssignment).filter(
        ShiftAssignment.tenant_id == tenant_id,
        ShiftAssignment.roster_id != roster.id,
        ShiftAssignment.status.in_(["scheduled", "published"]),
    ).all()
    planned = []
    db.query(ShiftAssignment).filter_by(tenant_id=tenant_id, roster_id=roster.id).delete()
    violations = []
    required_total = sum(d.required_headcount for d in demands)
    assigned_total = 0
    for demand in demands:
        assigned_for_slot = 0
        for _ in range(demand.required_headcount):
            candidates = []
            for emp in employees:
                skills = {str(x).strip().lower() for x in (emp.skills or [])}
                skills.add((emp.job_title or "").strip().lower())
                if demand.role_required and demand.role_required not in skills:
                    continue
                windows = availability_by_employee.get(emp.id, [])
                if not any(_as_utc(w.starts_at) <= _as_utc(demand.starts_at) and _as_utc(w.ends_at) >= _as_utc(demand.ends_at) for w in windows):
                    continue
                if any(overlaps(demand.starts_at, demand.ends_at, w.starts_at, w.ends_at) for w in unavailable_by_employee.get(emp.id, [])):
                    continue
                if any(a.employee_id == emp.id and overlaps(demand.starts_at, demand.ends_at, a.start_time, a.end_time) for a in other_assignments):
                    continue
                if any(p["employee_id"] == emp.id and overlaps(demand.starts_at, demand.ends_at, p["start_time"], p["end_time"]) for p in planned):
                    continue
                # Prefer employees with fewer already-planned hours in this roster.
                hours = sum((_as_utc(p["end_time"]) - _as_utc(p["start_time"])).total_seconds() for p in planned if p["employee_id"] == emp.id)
                candidates.append((hours, emp.id, emp))
            if not candidates:
                violations.append({"demand_id": demand.id, "shift_name": demand.shift_name, "reason": "no_available_skill_matched_employee"})
                continue
            _, _, chosen = sorted(candidates, key=lambda item: (item[0], item[1]))[0]
            planned.append({"employee_id": chosen.id, "shift_name": demand.shift_name, "start_time": demand.starts_at,
                            "end_time": demand.ends_at, "role_required": demand.role_required, "demand_id": demand.id})
            assigned_for_slot += 1
            assigned_total += 1
        if assigned_for_slot < demand.required_headcount:
            pass

    for item in planned:
        db.add(ShiftAssignment(tenant_id=tenant_id, roster_id=roster.id, employee_id=item["employee_id"],
                               shift_name=item["shift_name"], start_time=item["start_time"], end_time=item["end_time"],
                               role_required=item["role_required"], status="scheduled"))
    score = round(assigned_total / required_total, 4) if required_total else None
    roster.is_optimized = bool(score == 1.0 and not violations)
    roster.optimization_score = score
    roster.constraint_violations = violations
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "roster_id": roster.id,
        "is_optimized": roster.is_optimized,
        "score": score,
        "optimization_status": "constraints_satisfied" if roster.is_optimized else "partial_coverage",
        "required_assignments": required_total,
        "assignments_created": assigned_total,
        "constraint_violations": violations,
        "constraints_checked": ["explicit_staffing_demand", "declared_availability", "unavailability_and_leave_windows",
                                "role_skill_match", "overlapping_assignments_in_other_rosters", "overlapping_assignments_in_this_roster"],
        "constraints_not_modeled": ["jurisdiction_specific_labor_law", "minimum_rest_period", "maximum_weekly_hours", "budget_cost"],
    }
