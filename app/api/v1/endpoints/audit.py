from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from pydantic import BaseModel
from datetime import datetime

from app.api import deps
from app.core.rbac import require_permission, Resource, Action
from app.models.base import User
from app.models.verticals import AuditLog

router = APIRouter()

class AuditLogResponse(BaseModel):
    id: str
    tenant_id: str
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    action: str
    resource: Optional[str] = None
    resource_id: Optional[str] = None
    details: dict
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/", response_model=List[AuditLogResponse])
def get_audit_logs(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_permission(Resource.AUDIT_LOGS, Action.READ)),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action name"),
    resource: Optional[str] = Query(None, description="Filter by resource type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
) -> Any:
    """
    Retrieve audit logs for the current tenant.
    Access restricted to administrators/managers via RBAC.
    """
    query = db.query(AuditLog).filter(AuditLog.tenant_id == tenant_id)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource:
        query = query.filter(AuditLog.resource == resource)
        
    logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    return logs
