"""Read-only, tenant-scoped compensation proposal listing for People Operations."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.models.base import User
from app.models.hr_core import HRCompensationChange
from app.services.rbac_service import user_has_perm

router = APIRouter()


@router.get("/proposals")
def list_compensation_proposals(
    status: str | None = None,
    limit: int = Query(100, ge=1, le=200),
    skip: int = Query(0, ge=0),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    """List compensation proposals only within the active tenant and permission scope."""
    privileged = (
        getattr(current_user, "is_system_admin", False)
        or getattr(current_user, "is_superuser", False)
        or (getattr(current_user, "role", "") or "").lower() in {"admin", "organization_admin", "super_admin"}
    )
    can_manage = privileged or user_has_perm(db, current_user, "hr.manage_compensation")
    can_view_people = privileged or user_has_perm(db, current_user, "hr.view_employees")
    query = db.query(HRCompensationChange).filter(HRCompensationChange.tenant_id == tenant_id)
    if not can_manage and not can_view_people:
        # Employees may only see proposals they personally requested.
        query = query.filter(HRCompensationChange.requested_by_user_id == current_user.id)
    if status:
        normalized = status.strip().lower()
        if normalized not in {"pending_approval", "approved", "rejected"}:
            raise HTTPException(status_code=422, detail="Invalid compensation proposal status.")
        query = query.filter(HRCompensationChange.status == normalized)
    rows = query.order_by(HRCompensationChange.created_at.desc()).offset(skip).limit(limit).all()
    return [{
        "id": row.id,
        "employee_id": row.employee_id,
        "requested_by_user_id": row.requested_by_user_id,
        "approver_user_id": row.approver_user_id,
        "currency": row.currency,
        "current_amount": str(row.current_amount) if row.current_amount is not None else None,
        "proposed_amount": str(row.proposed_amount),
        "reason": row.reason,
        "status": row.status,
        "decision_reason": row.decision_reason,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
        "payroll_applied": False,
    } for row in rows]
