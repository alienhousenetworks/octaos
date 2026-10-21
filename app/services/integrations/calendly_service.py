"""Calendly v2 connector service for meeting booking and SDR lifecycle handoffs."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session

from app.services.credentials import get_decrypted_credential
from app.services.audit_service import AuditService
from app.models.verticals import Lead
from app.models.enterprise import OutcomeEvent

logger = logging.getLogger(__name__)

CALENDLY_API_BASE = "https://api.calendly.com"


class CalendlyService:
    def __init__(self, db: Optional[Session], tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        if db:
            self.api_key, self.settings = get_decrypted_credential(db, tenant_id, "calendly")
        else:
            self.api_key, self.settings = None, {}

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5)

    async def list_event_types(self) -> List[Dict[str, Any]]:
        """List active booking event types for this organization."""
        if not self.is_configured():
            return [
                {
                    "uri": "https://api.calendly.com/event_types/mock-demo",
                    "name": "OctaOS Enterprise Demo",
                    "slug": "octaos-enterprise-demo",
                    "scheduling_url": "https://calendly.com/octaos-ai/demo",
                    "duration": 30,
                    "active": True,
                }
            ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{CALENDLY_API_BASE}/event_types",
                headers={"Authorization": f"Bearer {self.api_key}"},
                params={"count": 20},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("collection", [])
            logger.error(f"Calendly API error {resp.status_code}: {resp.text}")
            return []

    async def create_single_use_link(self, event_type_uri: str) -> Dict[str, Any]:
        """Generate a single-use booking link to embed in SDR outreach emails."""
        if not self.is_configured():
            return {
                "booking_url": f"https://calendly.com/octaos-demo/booked?ref={self.tenant_id}",
                "status": "simulated",
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{CALENDLY_API_BASE}/scheduling_links",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"max_event_count": 1, "owner": event_type_uri, "owner_type": "EventType"},
            )
            if resp.status_code == 201:
                return resp.json().get("resource", {})
            return {"status": "error", "code": resp.status_code, "detail": resp.text}

    def process_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Calendly webhook callbacks.
        Maps 'invitee.created' to an OutcomeEvent (meeting_booked) and updates Sales Lead status.
        """
        tracking = payload.get("tracking", {})
        invitee = payload.get("invitee", payload)
        email = invitee.get("email") or payload.get("email")
        name = invitee.get("name") or payload.get("name", "Prospect")

        logger.info(f"Processing Calendly webhook '{event_type}' for {email}")

        lead_updated = False
        if email:
            lead = (
                self.db.query(Lead)
                .filter(Lead.tenant_id == self.tenant_id, Lead.email == email)
                .first()
            )
            if lead:
                lead.status = "meeting_scheduled"
                lead_updated = True
                self.db.commit()

        if event_type in ("invitee.created", "calendly.meeting_booked"):
            # Record an outcome event for learning and attribution
            outcome = OutcomeEvent(
                tenant_id=self.tenant_id,
                outcome_type="meeting_booked",
                agent_name="calendly_connector",
                resource_type="lead",
                resource_id=lead.id if (lead_updated and lead) else None,
                value=100.0,  # Standard meeting booking attribution score
                metadata_json={
                    "email": email,
                    "name": name,
                    "event_type": event_type,
                    "calendly_event_uri": payload.get("event"),
                    "utm_source": tracking.get("utm_source"),
                    "utm_campaign": tracking.get("utm_campaign"),
                },
            )
            self.db.add(outcome)
            self.db.commit()

            AuditService.log_event(
                self.db,
                action="calendly.meeting.booked",
                tenant_id=self.tenant_id,
                resource="crm",
                details={"email": email, "lead_id": lead.id if lead_updated else None},
            )

        return {
            "status": "success",
            "event_type": event_type,
            "email": email,
            "lead_updated": lead_updated,
        }
