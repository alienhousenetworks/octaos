from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.tenancy.models import AuditLog


def record_audit(
    db: Session,
    *,
    tenant_id: str,
    user_id: Optional[str],
    action: str,
    resource: str,
    resource_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> AuditLog:
    entry = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        details=details or {},
    )
    db.add(entry)
    db.commit()
    return entry
