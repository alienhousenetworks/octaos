"""Unified Support Customer Identity Resolution & History Retrieval Service."""

from __future__ import annotations
import re
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.models.verticals import SupportCustomer, SupportCustomerIdentity, Ticket, TicketMessage


class SupportIdentityService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    @staticmethod
    def normalize_identifier(channel: str, raw_identifier: str) -> str:
        if not raw_identifier:
            return ""
        clean = raw_identifier.strip()
        if channel == "email":
            return clean.lower()
        if channel == "whatsapp":
            # Strip spaces, hyphens, parentheses; preserve '+' prefix if present
            digits = re.sub(r"[^\d+]", "", clean)
            return digits
        return clean

    def resolve_or_create_customer(
        self,
        channel: str,
        sender: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> SupportCustomer:
        norm_id = self.normalize_identifier(channel, sender)
        if not norm_id:
            norm_id = f"anon_{channel}"

        if channel == "email" and not email:
            email = norm_id
        if channel == "whatsapp" and not phone:
            phone = norm_id

        # 1. Lookup existing channel identity
        identity = (
            self.db.query(SupportCustomerIdentity)
            .filter(
                SupportCustomerIdentity.tenant_id == self.tenant_id,
                SupportCustomerIdentity.channel == channel,
                SupportCustomerIdentity.normalized_identifier == norm_id,
            )
            .first()
        )

        if identity and identity.customer:
            customer = identity.customer
            # Enrich existing profile if new metadata provided
            changed = False
            if name and not customer.display_name:
                customer.display_name = name
                changed = True
            if email and not customer.primary_email:
                customer.primary_email = email.strip().lower()
                changed = True
            if phone and not customer.primary_phone:
                customer.primary_phone = self.normalize_identifier("whatsapp", phone)
                changed = True
            if changed:
                self.db.commit()
                self.db.refresh(customer)
            return customer

        # 2. Check if verified secondary email or phone matches an existing customer in same tenant
        customer = None
        if email:
            norm_email = email.strip().lower()
            customer = (
                self.db.query(SupportCustomer)
                .filter(
                    SupportCustomer.tenant_id == self.tenant_id,
                    SupportCustomer.primary_email == norm_email,
                )
                .first()
            )
        if not customer and phone:
            norm_phone = self.normalize_identifier("whatsapp", phone)
            customer = (
                self.db.query(SupportCustomer)
                .filter(
                    SupportCustomer.tenant_id == self.tenant_id,
                    SupportCustomer.primary_phone == norm_phone,
                )
                .first()
            )

        if customer:
            changed = False
            if email and not customer.primary_email:
                customer.primary_email = email.strip().lower()
                changed = True
            if phone and not customer.primary_phone:
                customer.primary_phone = self.normalize_identifier("whatsapp", phone)
                changed = True
            if name and not customer.display_name:
                customer.display_name = name
                changed = True
            if changed:
                self.db.commit()
                self.db.refresh(customer)

        # 3. Create customer if not found
        if not customer:
            display = name or (f"WhatsApp ({norm_id})" if channel == "whatsapp" else norm_id)
            customer = SupportCustomer(
                tenant_id=self.tenant_id,
                display_name=display,
                primary_phone=norm_id if channel == "whatsapp" else (self.normalize_identifier("whatsapp", phone) if phone else None),
                primary_email=norm_id if channel == "email" else (email.strip().lower() if email else None),
                verified=False,
            )
            self.db.add(customer)
            self.db.commit()
            self.db.refresh(customer)

        # 4. Attach new channel identity to customer
        new_identity = SupportCustomerIdentity(
            tenant_id=self.tenant_id,
            customer_id=customer.id,
            channel=channel,
            normalized_identifier=norm_id,
            verified_at=func.now(),
        )
        self.db.add(new_identity)
        self.db.commit()

        return customer

    def get_customer_history(self, customer_id: str, exclude_ticket_id: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        query = (
            self.db.query(Ticket)
            .filter(
                Ticket.tenant_id == self.tenant_id,
                Ticket.customer_id == customer_id,
            )
        )
        if exclude_ticket_id:
            query = query.filter(Ticket.id != exclude_ticket_id)

        tickets = query.order_by(Ticket.created_at.desc()).limit(limit).all()
        history = []
        for t in tickets:
            last_msg = (
                self.db.query(TicketMessage)
                .filter(TicketMessage.ticket_id == t.id)
                .order_by(TicketMessage.created_at.desc())
                .first()
            )
            history.append({
                "ticket_id": t.id,
                "subject": t.subject,
                "status": t.status,
                "channel": t.channel,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
                "last_message": last_msg.content if last_msg else t.description,
            })
        return history
