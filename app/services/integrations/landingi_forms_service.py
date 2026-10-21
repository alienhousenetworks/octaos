"""Inbound lead & form capture service for Landingi, Google Forms, and Formstack."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.models.verticals import Lead
from app.models.enterprise import OutcomeEvent
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class LandingiFormsService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def ingest_submission(self, source_platform: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingests webhooks from Landingi, Google Forms, or Formstack, normalizing
        form keys and upserting into the Sales OS Lead pipeline.
        """
        source_lower = source_platform.lower().replace(" ", "_")

        # Extract email and name across different form payload variations
        email = (
            payload.get("email")
            or payload.get("email_address")
            or payload.get("Email")
            or payload.get("Email Address")
            or payload.get("your-email")
        )
        if isinstance(email, str):
            email = email.strip().lower()

        if not email or "@" not in email:
            logger.warning(f"Inbound {source_platform} form submission missing valid email: {payload}")
            return {"status": "ignored", "reason": "No valid email found in submission"}

        name = (
            payload.get("name")
            or payload.get("full_name")
            or payload.get("Name")
            or payload.get("Full Name")
            or f"{payload.get('first_name', '')} {payload.get('last_name', '')}".strip()
            or email.split("@")[0].capitalize()
        )

        company = (
            payload.get("company")
            or payload.get("company_name")
            or payload.get("Company")
            or payload.get("organization")
            or email.split("@")[1].split(".")[0].capitalize()
        )

        phone = payload.get("phone") or payload.get("phone_number") or payload.get("Phone") or ""
        notes = payload.get("message") or payload.get("comments") or payload.get("notes") or ""

        # UTM and campaign attribution tags
        utm_source = payload.get("utm_source") or source_lower
        utm_campaign = payload.get("utm_campaign")
        utm_medium = payload.get("utm_medium")

        # Find or create Lead in Sales OS
        lead = (
            self.db.query(Lead)
            .filter(Lead.tenant_id == self.tenant_id, Lead.email == email)
            .first()
        )

        is_new = False
        submission_text = f"Submitted via {source_platform}. {notes}".strip()
        if not lead:
            lead = Lead(
                tenant_id=self.tenant_id,
                email=email,
                name=name,
                company=company,
                phone=phone,
                status="captured",
                source=f"form_{source_lower}",
                score=70,  # High intent baseline for inbound form submissions
                target_context=submission_text,
                data={"notes": notes, "raw_submission": payload},
            )
            self.db.add(lead)
            is_new = True
        else:
            if phone and not lead.phone:
                lead.phone = phone
            if company and (not lead.company or lead.company == "Unknown"):
                lead.company = company
            if notes:
                lead.target_context = f"{lead.target_context or ''}\n[{source_platform}] {notes}".strip()
                lead_data = dict(lead.data or {})
                lead_data["latest_submission"] = payload
                lead.data = lead_data

        self.db.commit()
        self.db.refresh(lead)

        # Log conversion outcome
        outcome = OutcomeEvent(
            tenant_id=self.tenant_id,
            outcome_type="conversion",
            agent_name=f"{source_lower}_connector",
            resource_type="lead",
            resource_id=lead.id,
            value=25.0,
            metadata_json={
                "source": source_lower,
                "email": email,
                "utm_source": utm_source,
                "utm_campaign": utm_campaign,
                "utm_medium": utm_medium,
            },
        )
        self.db.add(outcome)
        self.db.commit()

        AuditService.log_event(
            self.db,
            action=f"{source_lower}.form.submitted",
            tenant_id=self.tenant_id,
            resource="crm",
            details={"lead_id": lead.id, "email": email, "is_new": is_new},
        )

        return {
            "status": "success",
            "lead_id": lead.id,
            "email": email,
            "is_new": is_new,
            "source": source_lower,
        }
