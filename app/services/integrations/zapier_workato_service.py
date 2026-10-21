"""Universal iPaaS connector service for Zapier and Workato."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session

from app.services.credentials import get_decrypted_credential
from app.services.audit_service import AuditService
from app.models.verticals import Lead

logger = logging.getLogger(__name__)


class ZapierWorkatoService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def get_webhook_url(self, platform: str = "zapier") -> Optional[str]:
        _, settings = get_decrypted_credential(self.db, self.tenant_id, platform)
        return settings.get("webhook_url") or settings.get("target_url")

    async def emit_event(self, event_name: str, payload: Dict[str, Any], platform: str = "zapier") -> Dict[str, Any]:
        """
        Emits an outbound event trigger to subscribed Zapier or Workato webhooks.
        """
        target_url = self.get_webhook_url(platform)
        if not target_url:
            logger.info(f"[{platform}] Simulated event emit: {event_name} (No webhook URL configured)")
            return {"status": "simulated", "event": event_name, "reason": "No webhook URL configured"}

        enriched_payload = {
            "event": event_name,
            "tenant_id": self.tenant_id,
            "data": payload,
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(target_url, json=enriched_payload)
                AuditService.log_event(
                    self.db,
                    action=f"{platform}.event.emitted",
                    tenant_id=self.tenant_id,
                    resource="ipaas",
                    details={"event": event_name, "status_code": resp.status_code},
                )
                return {"status": "dispatched", "status_code": resp.status_code}
        except Exception as e:
            logger.error(f"Failed to dispatch {platform} event: {e}")
            return {"status": "error", "error": str(e)}

    def execute_inbound_action(self, platform: str, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes actions triggered from an external Zapier zap or Workato recipe.
        """
        logger.info(f"Executing inbound {platform} action: {action}")
        if action in ("create_lead", "lead.create"):
            email = data.get("email")
            if not email:
                return {"status": "error", "message": "Email is required"}
            lead = (
                self.db.query(Lead)
                .filter(Lead.tenant_id == self.tenant_id, Lead.email == email)
                .first()
            )
            if not lead:
                lead = Lead(
                    tenant_id=self.tenant_id,
                    email=email,
                    name=data.get("name", "Zapier Lead"),
                    company=data.get("company", "Unknown"),
                    phone=data.get("phone", ""),
                    status="captured",
                    source=f"ipaas_{platform.lower()}",
                    target_context=data.get("notes", f"Created via {platform}"),
                    data={"notes": data.get("notes"), "source_data": data},
                )
                self.db.add(lead)
                self.db.commit()
                self.db.refresh(lead)
                return {"status": "created", "lead_id": lead.id, "email": email}
            return {"status": "existing", "lead_id": lead.id, "email": email}

        return {"status": "success", "platform": platform, "action": action, "echo": data}
