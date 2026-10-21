"""Twilio SendGrid v3 connector service for transactional & marketing email."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session

from app.services.credentials import get_decrypted_credential
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

SENDGRID_API_BASE = "https://api.sendgrid.com/v3"


class SendGridService:
    def __init__(self, db: Optional[Session], tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        if db:
            self.api_key, self.settings = get_decrypted_credential(db, tenant_id, "sendgrid")
        else:
            self.api_key, self.settings = None, {}
        self.from_email = self.settings.get("from_email") or "outreach@octaos.ai"
        self.from_name = self.settings.get("from_name") or "OctaOS Agent"

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 10)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        is_html: bool = True,
        template_id: Optional[str] = None,
        dynamic_template_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a single email message via SendGrid Mail Send v3."""
        payload: Dict[str, Any] = {
            "personalizations": [
                {
                    "to": [{"email": to_email}],
                    "subject": subject,
                }
            ],
            "from": {"email": self.from_email, "name": self.from_name},
        }

        if template_id:
            payload["template_id"] = template_id
            if dynamic_template_data:
                payload["personalizations"][0]["dynamic_template_data"] = dynamic_template_data
        else:
            payload["content"] = [
                {
                    "type": "text/html" if is_html else "text/plain",
                    "value": content,
                }
            ]

        if not self.is_configured():
            logger.info(f"[SendGrid Mock] Sending email to {to_email} (API Key not configured)")
            if self.db:
                AuditService.log_event(
                    self.db,
                    action="email.sendgrid.simulated",
                    tenant_id=self.tenant_id,
                    resource="email",
                    details={"to_email": to_email, "subject": subject},
                )
            return {"status": "simulated", "message_id": f"mock_sg_{to_email}", "to": to_email}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{SENDGRID_API_BASE}/mail/send",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code in (200, 202):
                msg_id = resp.headers.get("X-Message-Id", "sg_sent")
                AuditService.log_event(
                    self.db,
                    action="email.sendgrid.sent",
                    tenant_id=self.tenant_id,
                    resource="email",
                    details={"to_email": to_email, "message_id": msg_id},
                )
                return {"status": "delivered", "message_id": msg_id, "to": to_email}
            else:
                logger.error(f"SendGrid API error {resp.status_code}: {resp.text}")
                return {"status": "error", "code": resp.status_code, "detail": resp.text}

    async def add_or_update_contacts(self, contacts: List[Dict[str, Any]], list_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Sync contacts to SendGrid Marketing Campaigns contact database."""
        if not self.is_configured():
            return {"status": "simulated", "contacts_synced": len(contacts)}

        payload: Dict[str, Any] = {"contacts": contacts}
        if list_ids:
            payload["list_ids"] = list_ids

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.put(
                f"{SENDGRID_API_BASE}/marketing/contacts",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code in (200, 202):
                return resp.json()
            return {"status": "error", "code": resp.status_code, "detail": resp.text}

    def process_webhook_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle SendGrid Event Webhook (opens, clicks, bounces, unsubscribes)."""
        processed = 0
        bounces = 0
        for ev in events:
            event_type = ev.get("event")
            email = ev.get("email")
            if event_type in ("bounce", "dropped"):
                bounces += 1
                logger.warning(f"SendGrid bounce event for {email}: {ev.get('reason')}")
            processed += 1

        AuditService.log_event(
            self.db,
            action="sendgrid.webhook.processed",
            tenant_id=self.tenant_id,
            resource="marketing",
            details={"total_events": processed, "bounces": bounces},
        )
        return {"processed": processed, "bounces": bounces}
