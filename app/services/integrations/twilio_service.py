"""Twilio connector service for SMS outreach and voice automation."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import httpx
from sqlalchemy.orm import Session

from app.services.credentials import get_decrypted_credential
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"


class TwilioService:
    def __init__(self, db: Optional[Session], tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        if db:
            self.api_key, self.settings = get_decrypted_credential(db, tenant_id, "twilio")
        else:
            self.api_key, self.settings = None, {}
        self.account_sid = self.settings.get("account_sid") or self.settings.get("sid")
        if not self.account_sid and self.api_key and self.api_key.startswith("AC"):
            self.account_sid = self.api_key
        self.auth_token = self.settings.get("auth_token") or self.settings.get("token") or self.api_key
        self.from_number = self.settings.get("from_number") or "+15005550006"

    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and len(self.account_sid) >= 10)

    async def send_sms(self, to_phone: str, message: str) -> Dict[str, Any]:
        """Send an SMS notification or outreach text via Twilio."""
        if not self.is_configured():
            logger.info(f"[Twilio Simulated SMS] To: {to_phone} | Message: {message[:40]}...")
            if self.db:
                AuditService.log_event(
                    self.db,
                    action="sms.twilio.simulated",
                    tenant_id=self.tenant_id,
                    resource="crm",
                    details={"to_phone": to_phone, "preview": message[:30]},
                )
            return {"status": "simulated", "sid": f"SM_mock_{to_phone}", "to": to_phone}

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{TWILIO_API_BASE}/Accounts/{self.account_sid}/Messages.json",
                auth=(self.account_sid, self.auth_token),
                data={"To": to_phone, "From": self.from_number, "Body": message},
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                AuditService.log_event(
                    self.db,
                    action="sms.twilio.sent",
                    tenant_id=self.tenant_id,
                    resource="crm",
                    details={"to_phone": to_phone, "sid": data.get("sid")},
                )
                return {"status": "sent", "sid": data.get("sid"), "to": to_phone}
            return {"status": "error", "code": resp.status_code, "detail": resp.text}

    def handle_inbound_sms(self, from_phone: str, body: str) -> Dict[str, Any]:
        """Process inbound SMS reply."""
        logger.info(f"Inbound Twilio SMS from {from_phone}: {body}")
        AuditService.log_event(
            self.db,
            action="sms.twilio.received",
            tenant_id=self.tenant_id,
            resource="crm",
            details={"from_phone": from_phone, "body": body},
        )
        return {"status": "received", "from": from_phone, "body": body}
