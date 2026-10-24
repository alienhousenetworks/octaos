"""Outreach Service for Sales OS: Multichannel outreach, template synthesis, compliance checks, and dispatch."""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from sqlalchemy.orm import Session

from app.core.security import decrypt_api_key
from app.models.base import APICredential, User
from app.models.verticals import BusinessProfile, Lead
from app.services.email.sender import parse_smtp_credentials, send_gmail_email, send_smtp_email
from app.services.sales.utils import extract_json

logger = logging.getLogger(__name__)


class OutreachService:
    def __init__(self, db: Session, tenant_id: str, llm=None, log_activity: Optional[Callable] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.llm = llm
        self._log_activity = log_activity or (lambda *args, **kwargs: None)

    async def sales_outreach(self, params: dict) -> dict:
        """Personalize and send outreach messages across SMTP, Gmail, or WhatsApp."""
        channel = params.get("channel", "smtp")
        provider = params.get("provider")
        model = params.get("model")
        subject = params.get("subject", "Partnership opportunity")
        body_template = params.get("body_template", "Hello {name}, I noticed {company} has great potential...")

        # Fetch leads that need outreach
        leads = self.db.query(Lead).filter(
            Lead.tenant_id == self.tenant_id,
            Lead.status.in_(["captured", "scored"]),
        ).all()

        if not leads:
            self._log_activity("Sales Outreach", "No new leads found needing outreach.", "success")
            return {"status": "success", "sent_count": 0}

        self._log_activity("Sales Outreach", f"Initiating sales outreach via {channel} for {len(leads)} leads.")

        # Check SMTP/Gmail settings
        smtp_credentials = None
        gmail_credentials = None
        if channel == "smtp":
            cred = self.db.query(APICredential).filter_by(
                tenant_id=self.tenant_id, provider="smtp"
            ).first()
            if cred and cred.encrypted_key:
                smtp_credentials = parse_smtp_credentials(decrypt_api_key(cred.encrypted_key))
            if not smtp_credentials:
                raise ValueError("No SMTP credentials configured. Please configure SMTP credentials under Platform Setup -> API Settings.")
        elif channel == "gmail":
            cred = self.db.query(APICredential).filter_by(
                tenant_id=self.tenant_id, provider="gmail"
            ).first()
            if cred and cred.encrypted_key:
                try:
                    gmail_credentials = json.loads(decrypt_api_key(cred.encrypted_key))
                except Exception:
                    pass
            if not gmail_credentials:
                raise ValueError("No Gmail API credentials configured. Please connect Google Workspace under Platform Setup -> API Settings.")

        # Resolve company and employee sender context
        bp = self.db.query(BusinessProfile).filter_by(tenant_id=self.tenant_id).first()
        company_name = bp.company_name if (bp and bp.company_name) else "OctaOS"
        user = self.db.query(User).filter_by(tenant_id=self.tenant_id).order_by(User.is_superuser.desc(), User.id.asc()).first()
        employee_name = user.name.strip() if (user and user.name and user.name.strip()) else None

        if employee_name:
            sender_rule = f"Write on behalf of {employee_name} at {company_name}. Sign off with: Best regards, {employee_name}, {company_name}."
        else:
            sender_rule = f"Write on behalf of {company_name}. Do NOT invent any employee name. Sign off strictly with: Best regards, The {company_name} Team."

        sent_count = 0
        for lead in leads:
            prompt = f"""Write a personalized sales email/outreach message.
Lead Name: {lead.name}
Lead Company: {lead.company}
Lead Source: {lead.source}
Lead Intent/Need: {lead.need_of_what or 'N/A'}
Lead Pain Points (Why): {lead.why or 'N/A'}
Target Context: {lead.target_context or 'N/A'}
Base Template: {body_template}
Subject: {subject}
Sender Context: {sender_rule}
Do NOT use or invent any fake human personas.
Output a JSON object with keys 'subject' and 'body'. No other text."""

            if self.llm:
                response = await self.llm.complete(prompt, provider=provider, model=model)
            else:
                response = "{}"
            try:
                parsed = extract_json(response)
                outbound_subject = parsed.get("subject", subject)
                outbound_body = parsed.get("body", body_template.format(name=lead.name, company=lead.company))
            except Exception:
                outbound_subject = subject
                outbound_body = body_template.format(name=lead.name, company=lead.company)

            from app.services.sales_os.governance.gatekeeper import PreSendGatekeeper
            from app.services.sales_os.governance.suppression import SuppressionService

            is_suppressed, suppression_reason = SuppressionService(self.db, self.tenant_id).is_suppressed(
                email=lead.email,
                phone=lead.phone,
                channel="whatsapp" if channel == "whatsapp" else "email",
            )
            if is_suppressed:
                self._log_activity(
                    "Outreach Skipped",
                    f"Contact {lead.email or lead.phone} is suppressed: {suppression_reason}",
                    "pending",
                )
                continue

            gate = PreSendGatekeeper.evaluate(
                outbound_subject,
                outbound_body,
                step_number=1,
                min_words=8 if channel in ("smtp", "gmail", "email") else 3,
                require_subject=channel in ("smtp", "gmail", "email"),
            )
            if not gate.is_valid:
                self._log_activity(
                    "Outreach Blocked",
                    f"Could not send to {lead.email or lead.phone}: {'; '.join(gate.violations)}",
                    "failed",
                )
                continue

            # Send
            sent_successfully = False
            if channel == "smtp" and smtp_credentials:
                try:
                    sent_successfully = send_smtp_email(
                        smtp_credentials, lead.email, outbound_subject, outbound_body
                    )
                except Exception as e:
                    self._log_activity("SMTP Send Fail", f"SMTP error for {lead.email}: {str(e)}.", "failed")
            elif channel == "gmail" and gmail_credentials:
                try:
                    result = send_gmail_email(
                        gmail_credentials, lead.email, outbound_subject, outbound_body
                    )
                    sent_successfully = bool(result and result.get("ok"))
                    if result and result.get("thread_id"):
                        lead.data = {
                            **(lead.data or {}),
                            "gmail_thread_id": result.get("thread_id"),
                            "gmail_message_id": result.get("message_id"),
                        }
                except Exception as e:
                    self._log_activity("Gmail Send Fail", f"Gmail error for {lead.email}: {str(e)}.", "failed")
            elif channel == "whatsapp":
                from app.services.sales.touch_dispatcher import dispatch_sales_touch

                delivery = dispatch_sales_touch(
                    self.db,
                    self.tenant_id,
                    lead,
                    channel="whatsapp",
                    body=outbound_body,
                    subject=outbound_subject,
                    step_number=1,
                )
                sent_successfully = bool(delivery.get("sent"))
                if sent_successfully:
                    lead.data = {**(lead.data or {}), "whatsapp_from": lead.phone}

            if not sent_successfully:
                self._log_activity(
                    f"Outreach Failed ({channel.upper()})",
                    f"Failed to send to: {lead.name} ({lead.email}).",
                    "failed",
                )
                continue

            self._log_activity(
                f"Outreach Sent ({channel.upper()})",
                f"Message to: {lead.name} ({lead.email}). Subject: '{outbound_subject}'",
                "success",
            )

            lead.status = "contacted"
            conv = list((lead.data or {}).get("conversation") or [])
            conv.append(
                {
                    "direction": "outbound",
                    "channel": channel,
                    "content": outbound_body,
                    "subject": outbound_subject,
                    "author": "Sales AI Agent",
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )
            lead.data = {
                **(lead.data or {}),
                "outreach_channel": channel,
                "outbound_subject": outbound_subject,
                "outbound_body": outbound_body,
                "sent_actual": sent_successfully,
                "outreach_sent_at": datetime.now(timezone.utc).isoformat(),
                "conversation": conv[-50:],
            }
            sent_count += 1

        self.db.commit()
        return {"status": "success", "sent_count": sent_count}
