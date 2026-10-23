"""Process real prospect replies for active sales leads (email / WhatsApp)."""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.services.agents.base import BaseAgent
from app.models.verticals import Lead
from app.models.base import APICredential
from app.services.notifications.sales_alerts import send_sales_telegram
from app.services.sales.meeting_booking import book_meeting_for_lead



def _sales_settings(db: Session, tenant_id: str) -> dict:
    cred = (
        db.query(APICredential)
        .filter_by(tenant_id=tenant_id, provider="sales")
        .first()
    )
    base = {
        "sales_auto_reply": True,
        "reply_mode": "review_first",
        "auto_book_meetings": True,
    }
    if cred and cred.settings:
        base.update(cred.settings)
    return base


def sales_auto_reply_enabled(db: Session, tenant_id: str) -> bool:
    return bool(_sales_settings(db, tenant_id).get("sales_auto_reply", True))


def sales_reply_mode(db: Session, tenant_id: str) -> str:
    mode = str(_sales_settings(db, tenant_id).get("reply_mode") or "review_first").lower()
    return mode if mode in ("review_first", "auto_send") else "review_first"


def sales_auto_book_meetings(db: Session, tenant_id: str) -> bool:
    return bool(_sales_settings(db, tenant_id).get("auto_book_meetings", True))


class SalesReplyHandler(BaseAgent):
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, tenant_id, "Sales AI")

    def _append_conversation(
        self,
        lead: Lead,
        *,
        direction: str,
        channel: str,
        content: str,
        external_id: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> None:
        data = dict(lead.data or {})
        history = list(data.get("conversation") or [])
        history.append(
            {
                "direction": direction,
                "channel": channel,
                "content": content,
                "subject": subject,
                "external_id": external_id,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )
        data["conversation"] = history[-50:]
        lead.data = data

    def _already_processed(self, lead: Lead, external_id: Optional[str]) -> bool:
        if not external_id:
            return False
        processed = set((lead.data or {}).get("processed_inbound_ids") or [])
        return external_id in processed

    def _mark_processed(self, lead: Lead, external_id: Optional[str]) -> None:
        if not external_id:
            return
        data = dict(lead.data or {})
        processed = list(data.get("processed_inbound_ids") or [])
        if external_id not in processed:
            processed.append(external_id)
        data["processed_inbound_ids"] = processed[-200:]
        lead.data = data

    def register_inbound(
        self,
        lead: Lead,
        channel: str,
        content: str,
        *,
        subject: Optional[str] = None,
        external_id: Optional[str] = None,
    ) -> bool:
        """Store inbound message; return False if duplicate."""
        if self._already_processed(lead, external_id):
            return False
        self._append_conversation(
            lead,
            direction="inbound",
            channel=channel,
            content=content,
            external_id=external_id,
            subject=subject,
        )
        self._mark_processed(lead, external_id)
        data = dict(lead.data or {})
        data["last_inbound_at"] = datetime.now(timezone.utc).isoformat()
        data["last_inbound_channel"] = channel
        lead.data = data
        if lead.status in ("contacted", "enriched", "captured"):
            lead.status = "replied"
        self.db.commit()
        self.db.refresh(lead)

        # Atomic Stop-on-Reply: cancel all pending outbox touches for this prospect
        try:
            from app.services.sales.outbox_service import SalesOutboxService
            outbox = SalesOutboxService(self.db, self.tenant_id)
            outbox.cancel_pending_for_lead(lead_id=lead.id, recipient_email=lead.email, reason="prospect_replied")
        except Exception as e:
            self.logger.warning(f"Error cancelling outbox items for lead {lead.id}: {e}")

        return True

    async def process_inbound(
        self,
        lead_id: str,
        channel: str,
        content: str,
        *,
        subject: Optional[str] = None,
        external_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        lead = (
            self.db.query(Lead)
            .filter(Lead.id == lead_id, Lead.tenant_id == self.tenant_id)
            .first()
        )
        if not lead:
            return {"status": "error", "detail": "lead not found"}

        if not self.register_inbound(lead, channel, content, subject=subject, external_id=external_id):
            return {"status": "skipped", "reason": "duplicate"}

        # Telegram: new prospect reply
        preview = (content or "")[:280].replace("\n", " ")
        tg_msg = (
            f"Prospect replied ({channel})\n"
            f"{lead.name} — {lead.company}\n"
            f"{preview}"
        )
        send_sales_telegram(self.db, self.tenant_id, tg_msg)

        parsed = await self._classify_reply(lead, content, subject)
        data = dict(lead.data or {})
        data["prospect_reply"] = content
        data["prospect_interested"] = parsed.get("interested", False)
        data["reply_intent"] = parsed.get("intent", "neutral")
        data["reply_classification"] = parsed
        lead.data = data
        self.db.commit()

        # Unify state across Lead, DealRoom, and SalesOpportunity
        from app.services.sales.sync_bridge import SalesSyncBridge
        sync_bridge = SalesSyncBridge(self.db, self.tenant_id)
        sync_bridge.sync_reply_received(lead, parsed.get("intent", "neutral"), content, auto_commit=True)

        # Check if the prospect's query requires human clarification
        if parsed.get("requires_human_clarification"):
            data["awaiting_user_clarification"] = True
            data["pending_question"] = parsed.get("unanswered_question") or content
            data["clarification_requested_at"] = datetime.now(timezone.utc).isoformat()
            lead.data = data
            self.db.commit()

            alert_msg = (
                f"⚠️ AI Needs Your Help: Prospect Inquiry\n"
                f"Lead: {lead.name} ({lead.company})\n"
                f"Question: \"{content[:250]}\"\n\n"
                f"Status: Missing from Knowledge Base. Please clarify in Sales Dashboard to respond and train AI."
            )
            send_sales_telegram(self.db, self.tenant_id, alert_msg)
            self.log_activity(
                "Sales AI Clarification Needed",
                f"Prospect {lead.name} asked unverified question: '{content[:100]}'. Escalated to user.",
                "warning",
            )
            return {
                "status": "awaiting_user_clarification",
                "lead_id": lead.id,
                "intent": parsed.get("intent"),
                "question": content,
            }

        booked = False
        if (
            parsed.get("interested")
            and lead.status != "meeting_scheduled"
            and sales_auto_book_meetings(self.db, self.tenant_id)
        ):
            suggested_time = parsed.get("suggested_time")
            # Require explicit time proposal/agreement from prospect before booking
            has_agreed_time = bool(
                suggested_time and any(
                    tok in str(suggested_time).lower()
                    for tok in ("am", "pm", ":", "morning", "afternoon", "monday", "tuesday", "wednesday", "thursday", "friday", "tomorrow", "confirmed")
                )
            )
            if has_agreed_time:
                try:
                    booked = book_meeting_for_lead(
                        self.db,
                        self.tenant_id,
                        lead,
                        tool="google_calendar",
                        suggested_time=suggested_time,
                        log_activity=self.log_activity,
                    )
                    if booked:
                        sync_bridge.sync_meeting_booked(lead, auto_commit=True)
                except Exception as book_exc:
                    data["meeting_coordination_status"] = "needs_booking_details"
                    data["meeting_booking_error"] = str(book_exc)[:300]
                    lead.data = data
                    self.db.commit()
                    self.log_activity("Meeting Booking Deferred", f"Auto-booking deferred ({book_exc}); coordinating slots.", "warning")
            else:
                data["meeting_coordination_status"] = "coordinating_slots"
                lead.data = data
                self.db.commit()

        auto_reply = parsed.get("should_auto_reply", True)
        suggested = parsed.get("suggested_reply")
        if sales_auto_reply_enabled(self.db, self.tenant_id) and auto_reply and suggested:
            mode = sales_reply_mode(self.db, self.tenant_id)
            if mode == "review_first":
                # Human must approve draft before send
                from app.services.policy_engine import PolicyEngine
                decision = PolicyEngine(self.db, self.tenant_id).evaluate(
                    action_type="first_touch_email" if channel in ("email", "smtp", "gmail") else "sales_auto_reply",
                    channel=channel,
                    agent_name="Sales AI",
                    confidence=0.7,
                    brand_pass=True,
                    title=f"Sales reply to {lead.name} ({lead.company})",
                    payload={
                        "draft": suggested,
                        "lead_id": lead.id,
                        "channel": channel,
                        "intent": parsed.get("intent"),
                    },
                    resource_type="lead",
                    resource_id=lead.id,
                    requested_by="Sales AI",
                )
                data["pending_review_reply"] = suggested
                data["approval_id"] = decision.get("approval_id")
                lead.data = data
                self.db.commit()
                self.log_activity(
                    "Sales Reply Awaiting Review",
                    f"Draft for {lead.name} queued for human approval ({decision.get('decision')}).",
                    "success",
                )
            else:
                from app.core.celery_app import celery_app

                delay = 120 if channel == "email" else 60
                data["pending_auto_reply_for"] = external_id or data.get("last_inbound_at", "")
                lead.data = data
                self.db.commit()
                celery_app.send_task(
                    "sales_auto_reply_task",
                    args=[
                        self.tenant_id,
                        lead.id,
                        channel,
                        suggested,
                        external_id or data.get("pending_auto_reply_for", ""),
                    ],
                    countdown=delay,
                )
                self.log_activity(
                    "Sales Auto-Reply Queued",
                    f"Queued sales follow-up for {lead.name} in {delay}s.",
                    "success",
                )

        self.log_activity(
            "Prospect Reply Processed",
            f"{lead.name} ({lead.company}) — intent: {parsed.get('intent')}, meeting_booked: {booked}",
            "success",
        )
        return {
            "status": "success",
            "lead_id": lead.id,
            "intent": parsed.get("intent"),
            "meeting_booked": booked,
        }

    async def _classify_reply(
        self, lead: Lead, content: str, subject: Optional[str]
    ) -> Dict[str, Any]:
        from app.models.deal_room import CompanySalesContext
        from app.models.agents import KnowledgeDocument
        
        ctx = (
            self.db.query(CompanySalesContext)
            .filter(CompanySalesContext.tenant_id == self.tenant_id, CompanySalesContext.is_active == True)
            .first()
        )
        docs = (
            self.db.query(KnowledgeDocument)
            .filter(KnowledgeDocument.tenant_id == self.tenant_id, KnowledgeDocument.is_active == True)
            .limit(10)
            .all()
        )
        doc_snippets = "\n".join([f"- [{d.doc_type} / {d.title}]: {d.content[:400]}" for d in docs])

        outbound = (lead.data or {}).get("outbound_body", "")
        history = (lead.data or {}).get("conversation") or []
        history_text = ""
        for msg in history[-10:]:
            history_text += f"{msg.get('direction', '?').upper()} ({msg.get('channel')}): {msg.get('content', '')}\n"

        from app.services.sales_os.contracts.registry import render_prompts

        rendered = render_prompts(
            "sales.conversation",
            {
                "company_name": lead.company or "the prospect's company",
                "inbound_text": content or "",
            },
        )
        prompt = f"""Classify one real inbound sales reply using the contract below.

VERIFIED COMPANY CONTEXT:
Company overview: {ctx.company_overview if ctx else 'No verified company overview'}
Products catalog: {ctx.products_catalog if ctx else []}
Objection playbook: {ctx.objection_playbook if ctx else {}}
Knowledge documents:
{doc_snippets if doc_snippets else 'No extra knowledge documents available.'}

CONVERSATION CONTEXT:
Lead: {lead.name or 'Unknown'} at {lead.company or 'Unknown company'}
Our last outreach:
{outbound or 'No outbound message recorded.'}
History:
{history_text or 'No prior conversation.'}
Subject: {subject or 'No subject'}

CONTRACT TASK:
{rendered['task_prompt']}

Return only the JSON object required by the contract. Do not add facts, availability, pricing, or policy details that are not in the verified context.
"""
        response = await self.llm.complete(
            prompt=prompt,
            system_prompt=rendered["system_prompt"],
            provider=rendered.get("provider") or "anthropic",
            model=rendered.get("model_id") or "claude-3-haiku-20240307",
        )
        try:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:]).strip()
            parsed = json.loads(cleaned)
            if not isinstance(parsed, dict):
                raise ValueError("Reply classifier returned a non-object")

            allowed_intents = {
                "interested", "question", "objection", "decline", "unsubscribe",
                "wrong_person", "timing_later", "out_of_office", "needs_human_review",
            }
            intent = str(parsed.get("intent") or "needs_human_review").strip().lower()
            if intent not in allowed_intents:
                intent = "needs_human_review"
            requires_clarification = bool(parsed.get("requires_human_clarification"))
            interested = bool(parsed.get("interested")) and intent == "interested"
            if intent in {"decline", "unsubscribe", "wrong_person", "out_of_office", "timing_later"}:
                interested = False
            if intent == "needs_human_review":
                requires_clarification = True

            return {
                "intent": intent,
                "interested": interested,
                "requires_human_clarification": requires_clarification,
                "unanswered_question": parsed.get("unanswered_question"),
                "confidence": max(0.0, min(1.0, float(parsed.get("confidence", 0.0) or 0.0))),
                "suggested_time": parsed.get("suggested_time"),
                "summary": parsed.get("summary") or (content or "")[:120],
                "should_auto_reply": bool(parsed.get("should_auto_reply")) and not requires_clarification and intent not in {"decline", "unsubscribe"},
                "suggested_reply": str(parsed.get("suggested_reply") or ""),
            }
        except Exception:
            lower = content.lower()
            unsubscribe = any(w in lower for w in ("unsubscribe", "remove me", "stop emailing", "do not contact", "don't contact"))
            decline = any(w in lower for w in ("not interested", "no thanks", "not a fit", "please don't"))
            meeting_interest = any(w in lower for w in ("meet", "meeting", "call", "demo", "schedule", "calendar"))
            positive = any(w in lower for w in ("yes", "happy to", "sounds good", "interested", "let's"))
            interested = meeting_interest and positive and not unsubscribe and not decline
            is_question = "?" in content or any(w in lower for w in ("how", "what", "pricing", "can you", "integrate", "support"))
            if unsubscribe:
                intent = "unsubscribe"
            elif decline:
                intent = "decline"
            elif interested:
                intent = "interested"
            elif is_question:
                intent = "question"
            else:
                intent = "needs_human_review"
            # If docs exist and question is asked, check if covered
            return {
                "intent": intent,
                "interested": interested,
                "requires_human_clarification": intent == "needs_human_review" or (is_question and not bool(docs)),
                "unanswered_question": content if (is_question and not bool(docs)) else None,
                "confidence": 0.5,
                "suggested_time": None,
                "summary": content[:120],
                "should_auto_reply": not is_question and intent not in {"decline", "unsubscribe", "needs_human_review"},
                "suggested_reply": (
                    "Thanks for getting back to me — happy to find a time that works. "
                    "What does your calendar look like this week?"
                ) if interested else "",
            }

    async def send_sales_reply(self, lead: Lead, channel: str, content: str) -> None:
        from app.services.email.sender import send_email

        if channel == "email":
            subject = (lead.data or {}).get("outbound_subject", "Following up")
            if not subject.lower().startswith("re:"):
                subject = f"Re: {subject}"
            outreach_channel = (lead.data or {}).get("outreach_channel", "smtp")
            result = send_email(
                self.db,
                self.tenant_id,
                lead.email,
                subject,
                content,
                channel=outreach_channel,
            )
            sent = result.get("sent", False) if isinstance(result, dict) else bool(result)
            if sent:
                self._append_conversation(
                    lead, direction="outbound", channel=channel, content=content
                )
                self.db.commit()
                self.log_activity(
                    "Sales Reply Sent",
                    f"Email reply sent to {lead.email}.",
                    "success",
                )
            else:
                reason = result.get("reason", "unknown") if isinstance(result, dict) else "unknown"
                self.log_activity(
                    "Sales Reply Failed",
                    f"Could not send email to {lead.email}. Reason: {reason}",
                    "failed",
                )
        elif channel == "whatsapp":
            from app.services.sales.touch_dispatcher import extract_lead_phone, send_whatsapp_with_status

            phone = lead.phone or (lead.data or {}).get("whatsapp_from")
            if phone:
                result = send_whatsapp_with_status(self.db, self.tenant_id, extract_lead_phone(lead) or phone, content)
                if result.get("sent"):
                    self._append_conversation(
                        lead, direction="outbound", channel=channel, content=content
                    )
                    self.db.commit()
                    self.log_activity(
                        "Sales Reply Sent",
                        f"WhatsApp reply sent to {phone}.",
                        "success",
                    )
                else:
                    self.log_activity(
                        "Sales Reply Failed",
                        f"Could not send WhatsApp reply to {phone}. Reason: {result.get('reason')}",
                        "failed",
                    )
            else:
                self.log_activity(
                    "Sales Reply Failed",
                    f"Could not send WhatsApp reply to {lead.name}: no phone number.",
                    "failed",
                )

    async def submit_human_clarification(
        self,
        lead_id: str,
        answer: str,
        *,
        channel: str = "email",
        add_to_kb: bool = True,
        kb_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        lead = (
            self.db.query(Lead)
            .filter(Lead.id == lead_id, Lead.tenant_id == self.tenant_id)
            .first()
        )
        if not lead:
            return {"status": "error", "message": "Lead not found"}

        data = dict(lead.data or {})
        pending_question = data.get("pending_question") or "Prospect inquiry"

        # 1. Dispatch the clarified reply to the prospect
        await self.send_sales_reply(lead, channel, answer)

        # 2. Ingest into Knowledge Base so the AI permanently learns this answer
        if add_to_kb:
            from app.models.agents import KnowledgeDocument
            from app.services.sales_os.context_materializer import SalesContextMaterializer

            title = kb_title or f"Q&A: {pending_question[:50]}"
            new_doc = KnowledgeDocument(
                tenant_id=self.tenant_id,
                department="Sales",
                doc_type="Product Q&A",
                content=f"Prospect Question:\n{pending_question}\n\nVerified Answer:\n{answer}",
                source_type="text",
                approved_for_external_use=True,
                metadata_json={"title": title},
                is_active=True,
            )
            self.db.add(new_doc)
            self.db.commit()

            try:
                materializer = SalesContextMaterializer(self.db, self.tenant_id)
                await materializer.materialize_context()
            except Exception:
                pass

        # 3. Clear pending state
        data["awaiting_user_clarification"] = False
        data["pending_question"] = None
        data["clarified_at"] = datetime.now(timezone.utc).isoformat()
        lead.data = data
        self.db.commit()

        self.log_activity(
            "Sales Clarification Resolved",
            f"Sent clarified response to {lead.name} and indexed to Knowledge Base.",
            "success",
        )
        return {
            "status": "success",
            "lead_id": lead.id,
            "added_to_kb": add_to_kb,
            "message": "Clarification sent to prospect and indexed to Knowledge Base.",
        }
