"""Shared Outbound Message Delivery Service with Ownership Verification & Traceability."""

from __future__ import annotations
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
import httpx
from sqlalchemy.orm import Session

from app.models.base import APICredential
from app.models.verticals import Ticket, TicketMessage
from app.core.security import decrypt_api_key
from app.services.credentials import get_decrypted_credential


class SupportOutboundService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def send(
        self,
        ticket_id: str,
        channel: str,
        recipient: str,
        content: str,
        sender_type: str = "agent",
        is_ai_caller: bool = False,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validates conversation ownership and delivers outbound message."""
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.tenant_id == self.tenant_id).first()
        if not ticket:
            return {"status": "error", "reason": "Ticket not found"}

        # 1. Deterministic Ownership Enforcement
        if is_ai_caller:
            # AI is strictly locked from sending if human owns or handoff is pending
            if ticket.owner_type in ("human_handling", "pending_human", "escalated", "waiting_customer"):
                return {
                    "status": "blocked",
                    "reason": f"AI response suppressed. Ticket is owned by {ticket.owner_type}.",
                }

        provider_message_id = None
        delivery_status = "sent_to_provider"

        # 2. Channel Delivery Adapters
        if channel == "whatsapp":
            cred = self.db.query(APICredential).filter_by(tenant_id=self.tenant_id, provider="meta").first()
            token, _ = get_decrypted_credential(self.db, self.tenant_id, "meta")
            if not cred or not token or not cred.settings or not cred.settings.get("phone_number_id"):
                raise ValueError("WhatsApp Meta API credentials are not configured.")

            phone_number_id = cred.settings.get("phone_number_id")
            async with httpx.AsyncClient() as client:
                url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": recipient,
                    "type": "text",
                    "text": {"preview_url": False, "body": content},
                }
                resp = await client.post(url, json=payload, headers=headers, timeout=20.0)
                if resp.status_code not in (200, 201):
                    raise Exception(f"WhatsApp Meta API failed ({resp.status_code}): {resp.text}")
                res_json = resp.json()
                msgs = res_json.get("messages", [])
                if msgs:
                    provider_message_id = msgs[0].get("id")

        elif channel == "email":
            cred = self.db.query(APICredential).filter(
                APICredential.tenant_id == self.tenant_id,
                APICredential.provider == "smtp",
            ).first()
            if not cred or not cred.encrypted_key or not cred.settings or not cred.settings.get("smtp_server"):
                raise ValueError("SMTP credentials are not configured.")

            smtp_server = cred.settings.get("smtp_server")
            smtp_port = int(cred.settings.get("smtp_port", 587))
            smtp_user = cred.settings.get("smtp_username")
            smtp_pass = decrypt_api_key(cred.encrypted_key)
            from_email = cred.settings.get("from_email", smtp_user)

            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = recipient
            msg["Subject"] = f"Re: {ticket.subject or 'Customer Support Inquiry'}"

            # Thread preservation
            ticket_extra = ticket.extra_data or {}
            in_reply_to = ticket_extra.get("email_message_id")
            if in_reply_to:
                msg["In-Reply-To"] = in_reply_to
                msg["References"] = in_reply_to

            msg.attach(MIMEText(content, "plain"))

            def _send_smtp():
                if smtp_port == 465 or cred.settings.get("use_ssl", False):
                    server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=20.0)
                else:
                    server = smtplib.SMTP(smtp_server, smtp_port, timeout=20.0)
                    server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, recipient, msg.as_string())
                server.quit()

            await asyncio.to_thread(_send_smtp)
            delivery_status = "sent_to_provider"

        elif channel in ("widget", "chat"):
            delivery_status = "delivered"

        # 3. Record Outbound Message in Conversation Timeline
        ticket_msg = TicketMessage(
            ticket_id=ticket.id,
            sender=sender_type,
            content=content,
            direction="outbound",
            channel=channel,
            provider_message_id=provider_message_id,
            delivery_status=delivery_status,
            extra_data=extra_data or {},
        )
        self.db.add(ticket_msg)
        self.db.commit()
        self.db.refresh(ticket_msg)

        return {
            "status": "success",
            "message_id": ticket_msg.id,
            "provider_message_id": provider_message_id,
            "delivery_status": delivery_status,
        }
