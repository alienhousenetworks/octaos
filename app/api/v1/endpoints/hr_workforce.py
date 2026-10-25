"""
HR Workforce & Compensation API Endpoints.
Covers Leave Management, Ledger Balances, Time & Attendance, and Shift Rosters.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.api import deps
from app.models.base import User
from app.models.hr_core import EmployeeProfile
from app.models.hr_workforce import (
    LeaveType, LeaveLedgerEntry, LeaveRequest, AttendanceRecord, AttendanceAuditEvent, ShiftRoster, ShiftAssignment
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


def _require_hr_role(user: User, approve: bool = False, permission: Optional[str] = None) -> None:
    # Permission codenames come from app.services.rbac_service.SYSTEM_PERMISSIONS.
    codename = permission or ("hr.manage_leave" if approve else "hr.view_employees")
    if not _has_hr_permission(user, codename):
        raise HTTPException(status_code=403, detail=f"Missing required permission: {codename}.")



def _require_self_or_hr(user: User, employee: EmployeeProfile) -> None:
    if getattr(user, "is_system_admin", False) or getattr(user, "is_superuser", False) or _role(user) in _HR_ROLES:
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

    if req.status == "approved":
        return {"status": "already_approved", "message": "Leave request is already approved."}
    if req.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending leave requests can be approved.")

    # Lock the request where supported and re-check state/ledger before writing.
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
    if not (getattr(current_user, "is_system_admin", False) or getattr(current_user, "is_superuser", False) or _role(current_user) in _HR_ROLES or (emp.user_id and str(emp.user_id) == str(current_user.id))):
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


@router.post("/rosters/optimize")
def optimize_roster(
    payload: RosterOptimizeRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    """Generate a draft shift proposal for authorized HR users."""
    _require_hr_role(current_user, permission="hr.manage_employees")
    roster = db.query(ShiftRoster).filter_by(id=payload.roster_id, tenant_id=tenant_id).first()
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found in this organization.")
    if roster.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft rosters can be changed by the optimizer.")
    if roster.end_date < roster.start_date:
        raise HTTPException(status_code=422, detail="Roster end date must be on or after its start date.")
    employees = db.query(EmployeeProfile).filter_by(tenant_id=tenant_id, status="active").all()
    # Honest baseline draft: no availability, skill, labor-rule, or demand model
    # exists here, so do not claim optimization or invent a score.
    shift_names = ["Morning (08:00 - 16:00)", "General (09:00 - 17:00)", "Evening (14:00 - 22:00)"]
    db.query(ShiftAssignment).filter_by(tenant_id=tenant_id, roster_id=roster.id).delete()
    created_assignments = 0
    for idx, emp in enumerate(employees):
        db.add(ShiftAssignment(tenant_id=tenant_id, roster_id=roster.id, employee_id=emp.id,
                               shift_name=shift_names[idx % len(shift_names)],
                               start_time=roster.start_date, end_time=roster.end_date, status="scheduled"))
        created_assignments += 1
    roster.is_optimized = False
    roster.optimization_score = None
    roster.constraint_violations = ["NOT_EVALUATED: availability, skills, coverage demand, and labor rules are not modeled."]
    db.commit()
    return {
        "roster_id": roster.id,
        "is_optimized": False,
        "score": None,
        "optimization_status": "baseline_draft_not_optimized",
        "assignments_created": created_assignments,
        "constraint_violations": roster.constraint_violations,
        "message": "Baseline roster draft created; validate staffing constraints before publishing."
    }
