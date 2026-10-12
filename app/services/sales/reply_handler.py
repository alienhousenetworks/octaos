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
            booked = book_meeting_for_lead(
                self.db,
                self.tenant_id,
                lead,
                tool="google_calendar",
                suggested_time=parsed.get("suggested_time"),
                log_activity=self.log_activity,
            )

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

        prompt = f"""You are an elite Sales Assistant analyzing a REAL inbound message from a prospect.
Our Knowledge Base & Company Context:
Company Overview: {ctx.company_overview if ctx else 'Enterprise System'}
Products Catalog: {ctx.products_catalog if ctx else []}
Objection Playbook: {ctx.objection_playbook if ctx else {{}}}
Verified Knowledge Base Documents:
{doc_snippets if doc_snippets else 'No extra knowledge documents available.'}

Lead: {lead.name} at {lead.company}
Our last outreach:
{outbound}

Conversation History:
{history_text}

New inbound message ({subject or 'no subject'}):
{content}

Classify the prospect message and plan the response. Output JSON only:
{{
  "intent": "interested" | "question" | "objection" | "decline" | "neutral",
  "interested": true/false,
  "requires_human_clarification": true/false,
  "unanswered_question": "string or null",
  "confidence": 0.0 to 1.0,
  "suggested_time": "meeting time they proposed or null",
  "summary": "one line summary",
  "should_auto_reply": true/false,
  "suggested_reply": "professional reply text to send them (empty if decline or requires_human_clarification)"
}}

Strict Grounding & Human Escalation Rules:
1. interested=true only if they clearly want a call, demo, or meeting.
2. If the prospect asks a question or raises an objection that is ANSWERED by our Knowledge Base, Products Catalog, or Playbook:
   - Provide a factual, concise suggested_reply directly grounded in those facts.
   - Set requires_human_clarification = false and confidence >= 0.85.
3. If the prospect asks about a feature, pricing detail, technical integration, or policy that is NOT covered in our Knowledge Base:
   - You MUST set requires_human_clarification = true and confidence = 0.2.
   - Set unanswered_question = the specific question or topic they asked about.
   - Do NOT guess, simulate, or hallucinate an answer.
4. If they decline/unsubscribe, set interested=false, should_auto_reply=false, requires_human_clarification=false.
5. suggested_reply must sound human, concise, on-brand; never mention AI.
"""
        response = await self.llm.complete(
            prompt=prompt, provider="anthropic", model="claude-3-haiku-20240307"
        )
        try:
            cleaned = response.strip().strip("```json").strip("```").strip()
            return json.loads(cleaned)
        except Exception:
            lower = content.lower()
            interested = any(
                w in lower
                for w in ("meet", "call", "demo", "schedule", "available", "yes", "interested")
            )
            is_question = "?" in content or any(w in lower for w in ("how", "what", "pricing", "can you", "integrate", "support"))
            # If docs exist and question is asked, check if covered
            return {
                "intent": "interested" if interested else ("question" if is_question else "neutral"),
                "interested": interested,
                "requires_human_clarification": is_question and not bool(docs),
                "unanswered_question": content if (is_question and not bool(docs)) else None,
                "confidence": 0.5,
                "suggested_time": None,
                "summary": content[:120],
                "should_auto_reply": not is_question,
                "suggested_reply": (
                    "Thanks for getting back to me — happy to find a time that works. "
                    "What does your calendar look like this week?"
                ) if interested else "",
            }

    async def send_sales_reply(self, lead: Lead, channel: str, content: str) -> None:
        from app.services.email.sender import send_email
        from app.services.agents.support import SupportAgent

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
            support = SupportAgent(self.db, self.tenant_id)
            phone = lead.phone or (lead.data or {}).get("whatsapp_from")
            if phone:
                await support.send_message("whatsapp", phone, content)
                self._append_conversation(
                    lead, direction="outbound", channel=channel, content=content
                )
                self.db.commit()
                self.log_activity(
                    "Sales Reply Sent",
                    f"WhatsApp reply sent to {phone}.",
                    "success",
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
