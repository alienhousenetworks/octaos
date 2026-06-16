import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.verticals import AuditLog
from app.models.base import tenant_context, org_context, bypass_tenant_isolation

logger = logging.getLogger(__name__)

class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        action: str,
        tenant_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """
        Creates an immutable audit log entry.
        Falls back to thread-local context vars for tenant_id and organization_id if not supplied.
        """
        # Resolve tenant & organization context if not passed directly
        resolved_tenant_id = tenant_id or tenant_context.get()
        resolved_org_id = organization_id or org_context.get()

        if not resolved_tenant_id:
            logger.warning(
                f"Attempting to write audit log without tenant context. Action: {action}"
            )
            # We still write it but flag it
            resolved_tenant_id = "system"

        try:
            # We bypass tenant isolation to ensure log writing/checking is unaffected by filters
            with bypass_tenant_isolation():
                audit_entry = AuditLog(
                    tenant_id=resolved_tenant_id,
                    organization_id=resolved_org_id,
                    user_id=user_id,
                    action=action,
                    resource=resource,
                    resource_id=resource_id,
                    details=details or {},
                    ip_address=ip_address
                )
                db.add(audit_entry)
                db.commit()
                db.refresh(audit_entry)
                
                logger.info(
                    f"Audit event logged: {action} on resource {resource} (ID: {resource_id}) "
                    f"by User: {user_id} in Tenant: {resolved_tenant_id}"
                )
                return audit_entry
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to write audit log entry: {e}")
            raise e
