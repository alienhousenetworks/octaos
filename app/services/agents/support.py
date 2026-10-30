import os
import re
import difflib
import asyncio
import httpx
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any

from app.services.agents.base import BaseAgent
from app.models.verticals import Ticket, TicketMessage, SupportCustomer
from app.models.base import APICredential
from app.core.security import decrypt_api_key
from app.services.credentials import get_decrypted_credential
from app.core.celery_app import celery_app
from app.services.notifications.telegram import send_telegram_notification
from app.core.http_utils import with_retry
from app.services.support_identity_service import SupportIdentityService
from app.services.support_outbound_service import SupportOutboundService


class SupportAgent(BaseAgent):
    def __init__(self, db, tenant_id):
        super().__init__(db, tenant_id, "Support AI")

    async def execute_task(self, task: dict) -> dict:
        action = task.get("action")
        params = task.get("parameters", {})
        
        if action == "onboard_users":
            return await self._onboard_users(params)
        return {"status": "Unknown action"}

    async def _onboard_users(self, params: dict):
        count = params.get("count", 2)
        self.log_activity("Onboard Users", f"Drafting onboarding messages for {count} users.")
        
        for i in range(count):
            ticket = Ticket(
                tenant_id=self.tenant_id,
                subject=f"Welcome to our service User {i+1}",
                description="Auto-generated onboarding sequence.",
                status="open",
                customer_contact=f"user{i+1}@example.com",
                channel="email",
                approval_status="pending"
            )
            self.db.add(ticket)
        self.db.commit()
        return {"status": "success", "tickets_created": count}

    async def daily_routine(self):
        self.log_activity("Daily Routine", "Checking for new unhandled tickets.", status="success")

    def is_auto_reply_enabled(self, channel: str) -> bool:
        cred = self.db.query(APICredential).filter(
            APICredential.tenant_id == self.tenant_id,
            APICredential.provider == "support"
        ).first()
        if cred and cred.settings:
            if channel == "whatsapp":
                return cred.settings.get("whatsapp_auto_reply", True)
            elif channel == "email":
                return cred.settings.get("email_auto_reply", True)
            elif channel in ("widget", "chat"):
                return cred.settings.get("widget_auto_reply", True)
        return True

    def validate_credentials(self, channel: str):
        if channel == "whatsapp":
            cred = self.db.query(APICredential).filter(
                APICredential.tenant_id == self.tenant_id,
                APICredential.provider == "meta"
            ).first()
            if not cred or not cred.encrypted_key or not cred.settings or not cred.settings.get("phone_number_id"):
                raise ValueError("WhatsApp Meta API credentials (Access Token and Phone Number ID) are required but not configured.")
        elif channel == "email":
            cred = self.db.query(APICredential).filter(
                APICredential.tenant_id == self.tenant_id,
                APICredential.provider == "smtp"
            ).first()
            if not cred or not cred.encrypted_key or not cred.settings or not cred.settings.get("smtp_server"):
                raise ValueError("SMTP/Email credentials (Server, Port, Username, Password) are required but not configured.")

    def detect_human_handoff_intent(self, message: str) -> bool:
        """Detect explicit /human command or natural user requests to speak with a human."""
        if not message:
            return False
        clean = message.lower().strip()
        if clean in ("/human", "/agent", "human", "agent") or clean.startswith(("/human ", "/agent ")):
            return True
        patterns = [
            r"\b(talk|speak|connect|chat|transfer)\s+(me\s+)?(to|with)?\s*(a\s+)?(live\s+|real\s+)?(human|person|agent|representative|specialist|support|team)\b",
            r"\b(want|need|get)\s+(a\s+)?(human|real\s+person|support\s+agent|live\s+agent|live\s+representative|representative)\b",
            r"\b(live\s+(chat|agent|support|person|rep|representative))\b",
            r"\b(human\s+(please|agent|support|help|now))\b",
            r"\b(real\s+(person|human))\b",
            r"\b(customer\s+(service|care|support))\b",
            r"\b(hand\s*off|escalate\s+to\s+human)\b",
            r"\b(agent\s+please)\b",
        ]
        for p in patterns:
            if re.search(p, clean):
                return True
        return False

    def detect_loop(self, recent_messages: List[TicketMessage], current_message: str) -> bool:
        """Detect if conversation is looping, repeating, or user is expressing frustration."""
        clean = current_message.lower().strip()
        frustration_triggers = [
            "stuck", "in a loop", "looping", "you keep repeating", "you already said that",
            "already asked that", "not helpful", "not answering my question", "doesn't help",
            "repeat", "useless", "same answer", "don't understand"
        ]
        for trig in frustration_triggers:
            if trig in clean:
                return True

        if not recent_messages:
            return False

        user_msgs = [m.content.strip().lower() for m in recent_messages if m.sender == "customer" and m.content]
        if len(user_msgs) >= 2:
            for prev in user_msgs[-2:]:
                ratio = difflib.SequenceMatcher(None, clean, prev).ratio()
                if ratio > 0.85:
                    return True

        agent_msgs = [m.content.strip().lower() for m in recent_messages if m.sender == "agent" and m.content]
        if len(agent_msgs) >= 2:
            if difflib.SequenceMatcher(None, agent_msgs[-1], agent_msgs[-2]).ratio() > 0.8:
                return True

        return False

    def extract_customer_details(self, content: str) -> Dict[str, Optional[str]]:
        """Extract email, phone number, and probable name from customer message."""
        details: Dict[str, Optional[str]] = {"email": None, "phone": None, "name": None}
        if not content:
            return details
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", content)
        if email_match:
            details["email"] = email_match.group(0).lower()
        phone_match = re.search(r"(\+?\d[\d\s\-\(\)]{8,15}\d)", content)
        if phone_match:
            digits = re.sub(r"[^\d+]", "", phone_match.group(0))
            if len(digits) >= 9:
                details["phone"] = digits
        name_match = re.search(r"\b(?:my\s+name\s+is|name:?|i\s+am)\s+([A-Za-z\s]{2,30})\b", content, re.IGNORECASE)
        if name_match:
            details["name"] = name_match.group(1).strip().title()
        return details

    async def handle_incoming_message(
        self,
        channel: str,
        sender: str,
        content: str,
        subject: Optional[str] = None,
        external_id: Optional[str] = None,
    ) -> dict:
        # 0. Active sales lead? Route to Sales AI (real replies, booking, auto-reply)
        from app.services.sales.inbound_router import route_incoming_to_sales

        sales_route = await route_incoming_to_sales(
            self.db,
            self.tenant_id,
            channel,
            sender,
            content,
            subject=subject,
            external_id=external_id,
        )
        if sales_route.get("handled"):
            return {
                "status": "success",
                "routed_to": "sales",
                "lead_id": sales_route.get("lead_id"),
            }

        # 1. Validation check for credentials
        self.validate_credentials(channel)

        # 2. Unified Customer Identity Resolution
        id_svc = SupportIdentityService(self.db, self.tenant_id)
        customer = id_svc.resolve_or_create_customer(
            channel=channel,
            sender=sender,
            email=sender if channel == "email" else None,
            phone=sender if channel == "whatsapp" else None,
        )

        # 3. Look for existing active ticket for sender on this channel
        ticket = self.db.query(Ticket).filter(
            Ticket.tenant_id == self.tenant_id,
            Ticket.channel == channel,
            Ticket.customer_contact == sender,
            Ticket.status.in_(["open", "pending_human", "human_handling", "waiting_customer", "escalated"])
        ).order_by(Ticket.created_at.desc()).first()

        if not ticket:
            ticket = Ticket(
                tenant_id=self.tenant_id,
                customer_id=customer.id,
                subject=subject or f"New {channel.capitalize()} support request from {customer.display_name or sender}",
                description=content,
                status="open",
                priority="medium",
                channel=channel,
                customer_contact=sender,
                customer_name=customer.display_name,
                customer_email=customer.primary_email,
                customer_phone=customer.primary_phone,
                owner_type="ai",
                mode="ai",
                approval_status="pending",
                extra_data={"email_message_id": external_id} if external_id and channel == "email" else {}
            )
            self.db.add(ticket)
            self.db.commit()
            self.db.refresh(ticket)
            self.log_activity("Ticket Created", f"New ticket #{ticket.id[:8]} opened for {sender} via {channel}.")
            
            # Send Telegram Notification
            msg = f"🎫 *New Support Ticket*\nFrom: {sender}\nCustomer: {customer.display_name or 'N/A'}\nSubject: {ticket.subject}\nChannel: {channel}"
            asyncio.create_task(send_telegram_notification(self.db, self.tenant_id, msg))

            # Context Engineering Check
            try:
                celery_app.send_task("check_ticket_coordination_task", args=[self.tenant_id, ticket.id])
            except Exception as e:
                print(f"Failed to queue ticket check task: {e}")

        # 4. Ingest customer message to conversation transcript immediately
        message = TicketMessage(
            ticket_id=ticket.id,
            sender="customer",
            content=content,
            direction="inbound",
            channel=channel,
            provider_message_id=external_id,
            delivery_status="received"
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)

        # 5. Extract customer details if provided in message body
        extracted = self.extract_customer_details(content)
        changed_details = False
        if extracted.get("name") and not ticket.customer_name:
            ticket.customer_name = extracted["name"]
            customer.display_name = extracted["name"]
            changed_details = True
        if extracted.get("email") and not ticket.customer_email:
            ticket.customer_email = extracted["email"]
            if not customer.primary_email:
                customer.primary_email = extracted["email"]
            changed_details = True
        if extracted.get("phone") and not ticket.customer_phone:
            ticket.customer_phone = extracted["phone"]
            if not customer.primary_phone:
                customer.primary_phone = extracted["phone"]
            changed_details = True
        if changed_details:
            self.db.commit()

        # 6. Check for Explicit /human Command or Natural Human Handoff Intent
        is_handoff_requested = self.detect_human_handoff_intent(content)
        if is_handoff_requested:
            now = datetime.now(timezone.utc)
            ticket.status = "pending_human"
            ticket.owner_type = "pending_human"
            ticket.mode = "human"
            ticket.handoff_generation = (ticket.handoff_generation or 0) + 1
            ticket.handoff_started_at = now
            ticket.handoff_deadline_at = now + timedelta(seconds=300)
            self.db.commit()

            if channel == "whatsapp":
                ack_text = (
                    "Connecting you with our live support team now! A human representative has been notified "
                    "and will connect with you shortly. If an agent is not available within a few minutes, "
                    "we will register a priority ticket with your details."
                )
            elif channel == "email":
                ack_text = (
                    "Thank you for contacting support. Your request has been transferred to our human support team. "
                    "A representative will review your message and reply shortly."
                )
            else:
                ack_text = "Connecting you with our live support team now! An agent will be with you shortly."

            outbound = SupportOutboundService(self.db, self.tenant_id)
            try:
                await outbound.send(
                    ticket_id=ticket.id,
                    channel=channel,
                    recipient=ticket.customer_contact,
                    content=ack_text,
                    sender_type="system",
                    is_ai_caller=False,
                )
            except Exception as e:
                print(f"Failed to send handoff acknowledgment: {e}")

            alert_msg = (
                f"💬 *Live Human Handoff Requested*\n"
                f"Ticket: #{ticket.id[:8]}\n"
                f"Channel: {channel}\n"
                f"From: {sender}\n"
                f"Customer: {customer.display_name or 'N/A'}\n"
                f"Message: {content}\n"
                f"⏱ 5-Minute Claim SLA active."
            )
            asyncio.create_task(send_telegram_notification(self.db, self.tenant_id, alert_msg))

            try:
                celery_app.send_task(
                    "check_human_handoff_timeout_task",
                    args=[self.tenant_id, ticket.id, ticket.handoff_generation],
                    countdown=300,
                )
                self.log_activity("Handoff SLA Queued", f"Ticket #{ticket.id[:8]} scheduled for 300s escalation check.")
            except Exception as e:
                print(f"Failed to queue handoff timeout task: {e}")

            return {
                "status": "handoff_queued",
                "ticket_id": ticket.id,
                "message_id": message.id,
                "owner_type": "pending_human"
            }

        # 7. Check Ownership: Suppress AI if conversation is owned by a human or handoff queue
        if ticket.owner_type in ("human_handling", "pending_human", "waiting_customer", "escalated"):
            self.log_activity("AI Response Suppressed", f"Ticket #{ticket.id[:8]} is currently owned by {ticket.owner_type}.")
            msg_update = f"💬 *Customer reply on live ticket*\nTicket: #{ticket.id[:8]}\nChannel: {channel}\nFrom: {sender}\nMessage: {content}"
            asyncio.create_task(send_telegram_notification(self.db, self.tenant_id, msg_update))
            return {
                "status": "human_owned",
                "ticket_id": ticket.id,
                "message_id": message.id,
                "owner_type": ticket.owner_type
            }

        # 8. If auto-reply is enabled and AI owns the ticket, queue celery task with delay
        if self.is_auto_reply_enabled(channel):
            delay_seconds = 270 if channel == "whatsapp" else 1200 if channel == "email" else 180
            celery_app.send_task(
                "auto_reply_task",
                args=[self.tenant_id, ticket.id, message.id, channel],
                countdown=delay_seconds,
            )
            self.log_activity(
                "Auto-Reply Queued",
                f"Queued support response for ticket #{ticket.id[:8]} in {delay_seconds}s.",
            )

        return {
            "status": "success",
            "ticket_id": ticket.id,
            "message_id": message.id
        }

    async def process_auto_reply(self, ticket_id: str, trigger_msg_id: str, channel: str):
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return

        if ticket.status in ("resolved", "closed") or ticket.owner_type in ("human_handling", "pending_human", "escalated"):
            self.log_activity("Auto-Reply Cancelled", f"Ticket #{ticket.id[:8]} owner is {ticket.owner_type or ticket.status}.")
            return

        trigger_msg = self.db.query(TicketMessage).filter(TicketMessage.id == trigger_msg_id).first()
        if not trigger_msg:
            return

        # Check if an agent replied after trigger message
        later_agent_messages = self.db.query(TicketMessage).filter(
            TicketMessage.ticket_id == ticket_id,
            TicketMessage.sender == "agent",
            TicketMessage.created_at > trigger_msg.created_at
        ).count()

        if later_agent_messages > 0:
            self.log_activity("Auto-Reply Cancelled", f"A reply has already been sent by agent for ticket #{ticket.id[:8]}.")
            return

        # Fetch conversation history
        messages = self.db.query(TicketMessage).filter(
            TicketMessage.ticket_id == ticket_id
        ).order_by(TicketMessage.created_at.asc()).all()

        last_customer = trigger_msg.content or ""

        # Check for loop / frustration -> Trigger Human Handoff
        if self.detect_loop(messages[:-1], last_customer):
            self.log_activity("Loop Detected", f"AI stuck looping on ticket #{ticket.id[:8]}. Escalating to human.")
            await self._trigger_ai_escalation(
                ticket,
                channel,
                transfer_reason="loop_detected",
                customer_message="I'm having trouble resolving this for you. I am transferring your request to our human support team now. A representative will connect with you shortly."
            )
            return

        # KB-gated answer with citations / refuse mode
        from app.services.kb_rag import KnowledgeRAGService
        from app.services.policy_engine import PolicyEngine
        from app.services.subscription_service import SubscriptionService

        budget = SubscriptionService(self.db).check_action_allowed(self.tenant_id)
        if not budget.get("allowed"):
            self.log_activity("Auto-Reply Blocked", f"Budget/quota: {budget.get('reason')}")
            return

        kb = KnowledgeRAGService(self.db, self.tenant_id).answer_context(
            last_customer, department="Support"
        )
        if not kb.get("answer_allowed") or kb.get("mode") == "refuse":
            # Knowledge base cannot answer safely -> Escalate to human
            self.log_activity("KB Refusal", f"Ticket #{ticket.id[:8]} requires human escalation.")
            await self._trigger_ai_escalation(
                ticket,
                channel,
                transfer_reason="kb_refusal",
                customer_message="I don't have enough verified information in my knowledge base to answer this accurately. I am escalating your request to our human support team. A representative will connect with you shortly."
            )
            return

        knowledge = kb.get("context") or self.get_knowledge_context("Support")
        citations = kb.get("citations") or []

        history_str = ""
        for m in messages:
            history_str += f"{m.sender.upper()}: {m.content}\n"

        system_prompt = (
            "You are a helpful, professional, and empathetic customer support agent. "
            "Your replies should be concise, human-like, and natural. Do not mention that you are an AI or bot. "
            "Rely strictly on the provided Company Guidelines & Knowledge Base. "
            "If the information is not in the knowledge base, say you will escalate to a specialist. "
            "When you use knowledge, you may cite sources by their citation tags."
        )
        prompt = (
            f"Customer Conversation History:\n{history_str}\n"
            f"Knowledge Base (with citations):\n{knowledge}\n"
            "Draft the final response from the agent to the customer."
        )

        reply_content = await self.llm.complete(
            prompt=prompt,
            model=None,
            provider=None,
            system_prompt=system_prompt,
        )
        if citations:
            reply_content = f"{reply_content}\n\nSources: " + "; ".join(citations[:3])

        # Policy: support replies go through HITL unless auto_with_rules
        decision = PolicyEngine(self.db, self.tenant_id).evaluate(
            action_type="support_auto_reply",
            channel=channel,
            agent_name="Support AI",
            confidence=0.9 if kb.get("mode") == "grounded" else 0.5,
            brand_pass=True,
            title=f"Support reply ticket {ticket.id[:8]}",
            payload={"draft": reply_content, "ticket_id": ticket.id, "channel": channel},
            resource_type="ticket",
            resource_id=ticket.id,
            requested_by="Support AI",
        )
        if decision.get("decision") == "block":
            self.log_activity("Auto-Reply Blocked", decision.get("reason", "policy"))
            return
        if decision.get("decision") == "queue_approval":
            draft_msg = TicketMessage(
                ticket_id=ticket.id,
                sender="agent",
                direction="internal_note",
                content=f"[PENDING APPROVAL {decision.get('approval_id')}]\n{reply_content}",
            )
            self.db.add(draft_msg)
            self.db.commit()
            self.log_activity("Auto-Reply Queued for Approval", f"Ticket #{ticket.id[:8]}")
            return

        outbound = SupportOutboundService(self.db, self.tenant_id)
        await outbound.send(
            ticket_id=ticket.id,
            channel=channel,
            recipient=ticket.customer_contact,
            content=reply_content,
            sender_type="agent",
            is_ai_caller=True,
        )
        SubscriptionService(self.db).record_action(self.tenant_id, cost_usd=0.0, count=1)
        self.log_activity("Auto-Reply Sent", f"Auto-reply sent for ticket #{ticket.id[:8]} via {channel}.")

    async def _trigger_ai_escalation(self, ticket: Ticket, channel: str, transfer_reason: str, customer_message: str):
        now = datetime.now(timezone.utc)
        ticket.status = "pending_human"
        ticket.owner_type = "pending_human"
        ticket.mode = "human"
        ticket.handoff_generation = (ticket.handoff_generation or 0) + 1
        ticket.handoff_started_at = now
        ticket.handoff_deadline_at = now + timedelta(seconds=300)
        if not ticket.extra_data:
            ticket.extra_data = {}
        ticket.extra_data["handoff_reason"] = transfer_reason
        self.db.commit()

        outbound = SupportOutboundService(self.db, self.tenant_id)
        try:
            await outbound.send(
                ticket_id=ticket.id,
                channel=channel,
                recipient=ticket.customer_contact,
                content=customer_message,
                sender_type="system",
                is_ai_caller=False,
            )
        except Exception as e:
            print(f"Failed to dispatch escalation message: {e}")

        alert_msg = (
            f"⚠️ *Support AI Triggered Human Handoff*\n"
            f"Ticket: #{ticket.id[:8]}\n"
            f"Channel: {channel}\n"
            f"Reason: {transfer_reason}\n"
            f"Contact: {ticket.customer_contact}\n"
            f"⏱ 5-Minute Claim SLA active."
        )
        await send_telegram_notification(self.db, self.tenant_id, alert_msg)

        try:
            celery_app.send_task(
                "check_human_handoff_timeout_task",
                args=[self.tenant_id, ticket.id, ticket.handoff_generation],
                countdown=300,
            )
        except Exception as e:
            print(f"Failed to queue handoff timeout task: {e}")

    async def process_handoff_timeout(self, ticket_id: str, expected_generation: int):
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.tenant_id == self.tenant_id).first()
        if not ticket:
            return

        # Verify generation and state to avoid claim-versus-timeout races
        if ticket.owner_type == "pending_human" and ticket.claimed_by is None and ticket.handoff_generation == expected_generation:
            ticket.owner_type = "escalated"
            ticket.status = "escalated"
            ticket.priority = "high"
            if not ticket.extra_data:
                ticket.extra_data = {}
            ticket.extra_data["escalated_at"] = datetime.now(timezone.utc).isoformat()
            ticket.extra_data["escalation_reason"] = "sla_5min_timeout_unclaimed"
            self.db.commit()

            if ticket.channel == "whatsapp":
                fallback_text = (
                    f"Our live agents are currently assisting other customers. "
                    f"We have formally registered priority support ticket #{ticket.id[:8]} with your contact information. "
                    f"To help us resolve this faster, please reply with your Full Name and Email Address, or any additional details."
                )
            elif ticket.channel == "email":
                fallback_text = (
                    f"Our live support agents are currently assisting other customers. "
                    f"We have registered priority support ticket #{ticket.id[:8]} with your email address. "
                    f"A dedicated specialist has been assigned and will reply to this thread shortly."
                )
            else:
                fallback_text = f"Live agents are currently busy. Priority support ticket #{ticket.id[:8]} has been registered."

            outbound = SupportOutboundService(self.db, self.tenant_id)
            try:
                await outbound.send(
                    ticket_id=ticket.id,
                    channel=ticket.channel,
                    recipient=ticket.customer_contact,
                    content=fallback_text,
                    sender_type="system",
                    is_ai_caller=False,
                )
            except Exception as e:
                print(f"Failed to send timeout fallback message: {e}")

            msg = (
                f"🚨 *Support SLA Timeout*\n"
                f"No agent claimed ticket #{ticket.id[:8]} within 5 minutes.\n"
                f"Channel: {ticket.channel}\n"
                f"Contact: {ticket.customer_contact}\n"
                f"Status: ESCALATED HIGH PRIORITY"
            )
            await send_telegram_notification(self.db, self.tenant_id, msg)
            self.log_activity("Handoff Timeout: Priority Ticket Raised", f"Ticket #{ticket.id[:8]}")

    @with_retry
    async def send_message(self, channel: str, recipient: str, content: str):
        """Backward-compatible wrapper for direct message dispatch."""
        outbound = SupportOutboundService(self.db, self.tenant_id)
        # Note: ticket might not be provided in legacy callers
        ticket = self.db.query(Ticket).filter(
            Ticket.tenant_id == self.tenant_id,
            Ticket.customer_contact == recipient,
        ).order_by(Ticket.created_at.desc()).first()

        ticket_id = ticket.id if ticket else "temp"
        if not ticket:
            # Create a lightweight shell ticket for standalone outbound
            temp_ticket = Ticket(
                tenant_id=self.tenant_id,
                customer_contact=recipient,
                channel=channel,
                subject=f"Outbound {channel.capitalize()} message",
                description=content,
                status="open",
            )
            self.db.add(temp_ticket)
            self.db.commit()
            self.db.refresh(temp_ticket)
            ticket_id = temp_ticket.id

        await outbound.send(
            ticket_id=ticket_id,
            channel=channel,
            recipient=recipient,
            content=content,
            sender_type="agent",
            is_ai_caller=False,
        )
