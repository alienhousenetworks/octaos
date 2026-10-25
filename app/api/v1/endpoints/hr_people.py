"""
HR People Management API Endpoints.
Covers Employee Directory, Organizational Chart, Policy Management, and Workforce Analytics.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid
from sqlalchemy.exc import IntegrityError

from app.api import deps
from app.models.base import User
from app.models.hr_core import EmployeeProfile, Department, CompanyPolicy
from app.models.hr_workforce import LeaveRequest, AttendanceRecord

router = APIRouter()

_HR_READ_ROLES = {"admin", "organization_admin", "super_admin", "hr_admin", "hr_manager", "hr_recruiter", "hr_hiring_manager", "manager"}
_HR_WRITE_ROLES = {"admin", "organization_admin", "super_admin", "hr_admin", "hr_manager"}

def _require_hr_access(user: User, *, write: bool = False) -> None:
    """Fail closed for HR endpoints; section visibility is not authorization."""
    if getattr(user, "is_system_admin", False) or getattr(user, "is_superuser", False):
        return
    role = (getattr(user, "role", None) or "").strip().lower().replace("-", "_").replace(" ", "_")
    if role not in (_HR_WRITE_ROLES if write else _HR_READ_ROLES):
        raise HTTPException(status_code=403, detail="You do not have permission to access this HR operation.")


class EmployeeCreateRequest(BaseModel):
    employee_number: Optional[str] = None
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    job_title: str
    department_name: Optional[str] = "Engineering"
    manager_id: Optional[str] = None
    employment_type: str = "full_time"
    work_location: str = "HQ"
    skills: List[str] = []


class PolicyCreateRequest(BaseModel):
    title: str
    category: str = "general"
    summary: Optional[str] = None
    content: str
    requires_acknowledgement: bool = False


class EmployeeStatusUpdateRequest(BaseModel):
    status: str
    reason: Optional[str] = None


@router.get("/employees")
def list_employees(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    department: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    current_user: User = Depends(deps.get_current_user),
):
    """List and search authorized employee profiles."""
    _require_hr_access(current_user)
    q = db.query(EmployeeProfile).filter(EmployeeProfile.tenant_id == tenant_id)
    if department:
        q = q.filter(EmployeeProfile.department_name.ilike(f"%{department}%"))
    if search:
        search_filter = f"%{search}%"
        q = q.filter(
            (EmployeeProfile.first_name.ilike(search_filter)) |
            (EmployeeProfile.last_name.ilike(search_filter)) |
            (EmployeeProfile.email.ilike(search_filter)) |
            (EmployeeProfile.job_title.ilike(search_filter)) |
            (EmployeeProfile.employee_number.ilike(search_filter))
        )

    total = q.count()
    employees = q.order_by(EmployeeProfile.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": emp.id,
                "employee_number": emp.employee_number,
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "full_name": emp.full_name,
                "email": emp.email,
                "phone": emp.phone,
                "job_title": emp.job_title,
                "department_name": emp.department_name,
                "work_location": emp.work_location,
                "employment_type": emp.employment_type,
                "status": emp.status,
                "skills": emp.skills or [],
                "hire_date": emp.hire_date.strftime("%Y-%m-%d") if emp.hire_date else None
            }
            for emp in employees
        ]
    }


@router.post("/employees")
def create_employee(
    payload: EmployeeCreateRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user)
):
    """Create an employee with tenant-safe validation and atomic persistence."""
    _require_hr_access(current_user, write=True)
    normalized_email = payload.email.strip().lower()
    if not normalized_email or "@" not in normalized_email:
        raise HTTPException(status_code=422, detail="A valid employee email is required.")
    existing = db.query(EmployeeProfile).filter_by(tenant_id=tenant_id, email=normalized_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An employee with this email already exists.")

    emp_number = (payload.employee_number or f"EMP-{uuid.uuid4().hex[:12].upper()}").strip()
    if not emp_number:
        raise HTTPException(status_code=422, detail="Employee number cannot be blank.")
    if payload.manager_id and not db.query(EmployeeProfile).filter_by(id=payload.manager_id, tenant_id=tenant_id).first():
        raise HTTPException(status_code=422, detail="Manager must be an employee in this organization.")

    # Resolve/create the department in the same transaction as the employee.
    dept = None
    department_name = payload.department_name.strip() if payload.department_name else None
    if department_name:
        dept = db.query(Department).filter_by(tenant_id=tenant_id, name=department_name).first()
        if not dept:
            dept = Department(tenant_id=tenant_id, name=department_name)
            db.add(dept)
            db.flush()

    emp = EmployeeProfile(
        tenant_id=tenant_id,
        employee_number=emp_number,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=normalized_email,
        phone=payload.phone,
        job_title=payload.job_title,
        department_id=dept.id if dept else None,
        department_name=department_name,
        manager_id=payload.manager_id,
        employment_type=payload.employment_type,
        work_location=payload.work_location,
        status="active",
        skills=payload.skills,
        hire_date=datetime.now(timezone.utc)
    )
    db.add(emp)
    try:
        db.commit()
        db.refresh(emp)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Employee number or email already exists in this organization.")

    return {
        "id": emp.id,
        "employee_number": emp.employee_number,
        "full_name": emp.full_name,
        "email": emp.email,
        "status": emp.status,
        "message": "Employee created successfully."
    }


@router.patch("/employees/{employee_id}/status")
def update_employee_status(
    employee_id: str,
    payload: EmployeeStatusUpdateRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    """Apply an explicit, tenant-scoped employment status transition."""
    _require_hr_access(current_user, write=True)
    allowed_statuses = {"onboarding", "active", "probation", "on_leave", "terminated"}
    new_status = payload.status.strip().lower()
    if new_status not in allowed_statuses:
        raise HTTPException(status_code=422, detail="Unsupported employment status.")
    employee = db.query(EmployeeProfile).filter_by(id=employee_id, tenant_id=tenant_id).with_for_update().first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")
    if employee.status == "terminated":
        raise HTTPException(status_code=409, detail="Terminated employees cannot be reactivated through this endpoint; use a reviewed rehire workflow.")
    if new_status == employee.status:
        return {"id": employee.id, "status": employee.status, "changed": False}
    if new_status == "terminated" and not (payload.reason and payload.reason.strip()):
        raise HTTPException(status_code=422, detail="A termination reason is required.")
    try:
        employee.status = new_status
        if new_status == "terminated":
            employee.termination_date = datetime.now(timezone.utc)
        db.commit()
        db.refresh(employee)
    except Exception:
        db.rollback()
        raise
    return {
        "id": employee.id,
        "employee_number": employee.employee_number,
        "status": employee.status,
        "termination_date": employee.termination_date.isoformat() if employee.termination_date else None,
        "changed": True,
        "reason_recorded": bool(payload.reason and payload.reason.strip()),
        "message": "Employment status updated. Termination reason is acknowledged by this API but is not yet stored in a dedicated audit record."
    }


@router.get("/org-chart")
def get_org_chart(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    """Generates the organizational hierarchy graph."""
    _require_hr_access(current_user)
    employees = db.query(EmployeeProfile).filter(
        EmployeeProfile.tenant_id == tenant_id,
        EmployeeProfile.status == "active"
    ).all()

    nodes = [
        {
            "id": e.id,
            "name": e.full_name,
            "title": e.job_title,
            "department": e.department_name or "General",
            "manager_id": e.manager_id,
            "email": e.email
        }
        for e in employees
    ]

    return {"nodes": nodes}


@router.get("/policies")
def list_policies(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    category: Optional[str] = None,
    current_user: User = Depends(deps.get_current_user),
):
    """Retrieve company policy documents."""
    _require_hr_access(current_user)
    q = db.query(CompanyPolicy).filter(
        CompanyPolicy.tenant_id == tenant_id,
        CompanyPolicy.is_active.is_(True)
    )
    if category:
        q = q.filter(CompanyPolicy.category == category.lower())

    policies = q.order_by(CompanyPolicy.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "category": p.category,
            "summary": p.summary,
            "version": p.version,
            "requires_acknowledgement": p.requires_acknowledgement,
            "effective_date": p.effective_date.strftime("%Y-%m-%d") if p.effective_date else None
        }
        for p in policies
    ]


@router.post("/policies")
def create_policy(
    payload: PolicyCreateRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    """Publish a new company policy for grounding RAG."""
    _require_hr_access(current_user, write=True)
    if not payload.title.strip() or not payload.content.strip():
        raise HTTPException(status_code=422, detail="Policy title and content are required.")
    policy = CompanyPolicy(
        tenant_id=tenant_id,
        title=payload.title,
        category=payload.category,
        summary=payload.summary,
        content=payload.content,
        requires_acknowledgement=payload.requires_acknowledgement
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return {"id": policy.id, "title": policy.title, "status": "published"}


@router.get("/analytics/summary")
def get_workforce_analytics(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    """Provides tenant-scoped workforce metrics without fabricated values."""
    _require_hr_access(current_user)
    total_employees = db.query(EmployeeProfile).filter_by(tenant_id=tenant_id, status="active").count()
    onboarding_count = db.query(EmployeeProfile).filter_by(tenant_id=tenant_id, status="onboarding").count()
    on_leave_count = db.query(EmployeeProfile).filter_by(tenant_id=tenant_id, status="on_leave").count()

    # Department breakdown
    departments = db.query(EmployeeProfile.department_name).filter_by(
        tenant_id=tenant_id, status="active"
    ).all()
    dept_counts: Dict[str, int] = {}
    for (dname,) in departments:
        name = dname or "Unassigned"
        dept_counts[name] = dept_counts.get(name, 0) + 1

    # Pending approvals
    pending_leaves = db.query(LeaveRequest).filter_by(
        tenant_id=tenant_id, status="pending"
    ).count()

    return {
        "headcount": {
            "total_active": total_employees,
            "onboarding": onboarding_count,
            "on_leave": on_leave_count
        },
        "department_distribution": dept_counts,
        "pending_leave_requests": pending_leaves,
        "retention_rate_pct": None,
        "retention_rate_status": "unavailable_without_historical_termination_and_headcount_data",
        "as_of": datetime.now().isoformat()
    }
