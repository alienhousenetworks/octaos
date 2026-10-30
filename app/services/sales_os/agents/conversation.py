"""Capability 19: Conversation & Objection Handling Agent.

Handles inbound prospect replies:
1. Intent Classification: interested | objection | wrong_person | unsubscribe | timing_later | question
2. Unsubscribe Suppression: immediately halts outreach and records DNC entry in SuppressionRecord.
3. Objection Playbook Resolution: matches prospect objections against proven Tenant Playbooks.
4. Meeting Scheduling: syncs calendar slots with Google Calendar.
"""
import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.services.sales_os.agents.base import BaseSalesAgent, AgentResult, EvidenceItem
from app.models.deal_room import DealRoom, DealObjection, CompanySalesContext, BuyingCommitteeMember
from app.services.sales_os.governance.suppression import SuppressionService
from app.services.knowledge_os.entity_extractor import extract_json_safe
from app.services.rag.hybrid_engine import HybridRAGEngine
from app.services.sales_os.aso.reply_taxonomy import normalize_reply_intent, detect_reply_intent_from_text
from app.services.sales_os.aso.state_machine import apply_transition
from app.services.sales_os.contracts.registry import render_prompts


class ConversationAgent(BaseSalesAgent):
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, tenant_id, "agent_19_conversation")
        self.suppression = SuppressionService(db, tenant_id)
        self.rag = HybridRAGEngine(db, tenant_id)

    async def execute(self, deal_room_id: str, parameters: Dict[str, Any] = None) -> AgentResult:
        start_time = time.time()
        params = parameters or {}
        inbound_text = (params.get("inbound_text") or params.get("reply_text") or "").strip()
        sender_email = params.get("sender_email", "")
        committee_member_id = params.get("committee_member_id")

        if not sender_email and committee_member_id:
            member = (
                self.db.query(BuyingCommitteeMember)
                .filter(BuyingCommitteeMember.id == committee_member_id)
                .first()
            )
            if member:
                sender_email = member.email

        deal_room = (
            self.db.query(DealRoom)
            .filter(DealRoom.id == deal_room_id, DealRoom.tenant_id == self.tenant_id)
            .first()
        )
        if not deal_room:
            return AgentResult(
                agent_id=self.agent_id,
                tenant_id=self.tenant_id,
                decision="error",
                confidence=0.0,
                reasoning_summary="DealRoom not found",
                recommended_next_step="discover_account",
            )

        lower_inbound = inbound_text.lower()
        parsed: dict = {}
        detected = detect_reply_intent_from_text(inbound_text)
        if detected in ("unsubscribe", "out_of_office", "decline", "wrong_person", "timing_later"):
            intent = detected
            parsed = {"intent": detected}
        is_pricing_inquiry = any(p in lower_inbound for p in ["send pricing", "share pricing", "what is the price", "what is the pricing", "pricing options", "pricing sheet", "how much does it cost", "how much is", "what does it cost", "rate card", "quote for"])
        is_cost_objection = any(w in lower_inbound for w in ["too expensive", "over budget", "no budget", "tight budget", "out of budget", "cannot afford", "can't afford", "cost prohibitive", "pricing is high"])
        if is_cost_objection:
            intent = "objection"
            parsed = {"intent": "objection", "objection_category": "pricing"}
        elif is_pricing_inquiry:
            intent = "question"
            parsed = {"intent": "question", "question_category": "pricing"}
        elif any(w in lower_inbound for w in ["competitor", "already using", "alternative", "using another vendor"]):
            intent = "objection"
            parsed = {"intent": "objection", "objection_category": "competitor"}
        else:
            rendered = render_prompts(
                "sales.conversation",
                {"company_name": deal_room.company_name, "inbound_text": inbound_text or "empty"},
            )
            try:
                resp = await self.llm.complete(
                    prompt=rendered["task_prompt"],
                    system_prompt=rendered["system_prompt"],
                    model=rendered["model_id"],
                    provider=rendered["provider"],
                )
                parsed = extract_json_safe(resp) or {}
                if not isinstance(parsed, dict):
                    parsed = {}
                intent = parsed.get("intent")
            except Exception:
                intent = None
                parsed = {}

        assessment = normalize_reply_intent(intent, parsed.get("objection_category"))
        intent = assessment.intent
        if intent == "needs_human_review":
            return AgentResult(
                agent_id=self.agent_id,
                tenant_id=self.tenant_id,
                deal_room_id=deal_room.id,
                contract_id="sales.conversation",
                decision="needs_human_review",
                confidence=0.0,
                source="inbound_reply",
                reasoning_summary="The reply did not match the canonical taxonomy.",
                recommended_next_step="human_review",
                data=assessment.model_dump(),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        # 2. Action based on intent
        if intent == "unsubscribe":
            # Add to global suppression registry
            if sender_email:
                self.suppression.add_suppression(
                    identifier_type="email",
                    identifier_value=sender_email,
                    reason="prospect_unsubscribe_request",
                    origin="conversation_agent",
                    notes=f"Unsubscribed via inbound message: {inbound_text[:80]}",
                )
            apply_transition(
                deal_room,
                "suppress",
                actor="sales.conversation",
                reason="Explicit unsubscribe.",
            )
            self.db.commit()

            return AgentResult(
                agent_id=self.agent_id,
                tenant_id=self.tenant_id,
                deal_room_id=deal_room.id,
                decision="executed",
                confidence=1.0,
                source="inbound_reply",
                reasoning_summary=f"Prospect requested removal. Contact {sender_email} added to suppression registry.",
                recommended_next_step="halt_all_cadences",
                data={"intent": "unsubscribe", "suppressed": True},
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        elif intent == "objection":
            obj_cat = parsed.get("objection_category") or "pricing"
            
            # Fetch playbook counter-argument
            ctx = (
                self.db.query(CompanySalesContext)
                .filter(CompanySalesContext.tenant_id == self.tenant_id, CompanySalesContext.is_active == True)
                .first()
            )
            playbook = ctx.objection_playbook if ctx else {}
            cat_entry = playbook.get(obj_cat, ["We understand. Many of our current clients had the same initial thought before seeing measurable ROI."])
            if isinstance(cat_entry, dict):
                pts = cat_entry.get("talking_points", ["We understand. Many of our current clients had the same initial thought before seeing measurable ROI."])
                suggested_counter = pts[0] if isinstance(pts, list) and pts else str(pts)
            elif isinstance(cat_entry, list):
                suggested_counter = cat_entry[0] if cat_entry else "We understand. Many of our current clients had the same initial thought before seeing measurable ROI."
            else:
                suggested_counter = str(cat_entry)

            # Log objection to DealRoom
            deal_obj = DealObjection(
                deal_room_id=deal_room.id,
                tenant_id=self.tenant_id,
                objection_category=obj_cat,
                prospect_statement=inbound_text,
                applied_counter_argument=suggested_counter,
                status="open",
            )
            self.db.add(deal_obj)
            self.db.commit()

            return AgentResult(
                agent_id=self.agent_id,
                tenant_id=self.tenant_id,
                deal_room_id=deal_room.id,
                decision="action_required",
                confidence=0.90,
                evidence=[EvidenceItem(claim=f"Playbook counter-argument for {obj_cat}", source="objection_playbook")],
                source="objection_playbook",
                reasoning_summary=f"Objection ({obj_cat}) detected. Formulated response from sales playbook.",
                recommended_next_step="send_counter_argument",
                data={
                    "intent": "objection",
                    "category": obj_cat,
                    "counter_argument": suggested_counter,
                    "draft_reply": parsed.get("suggested_reply", suggested_counter),
                },
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        elif intent == "interested":
            transition = apply_transition(
                deal_room,
                "reply_received",
                actor="sales.conversation",
                reason="Positive interest detected from inbound prospect.",
            )
            if not transition.get("applied"):
                deal_room.stage = "replied"
            self.db.commit()

            from app.models.verticals import BusinessProfile
            bp = self.db.query(BusinessProfile).filter_by(tenant_id=self.tenant_id).first()
            calendar_link = (bp.calendars or [{}])[0].get("booking_url") if bp and bp.calendars else None
            if calendar_link:
                meeting_draft = f"Thanks for getting back to me! You can book a time directly here: {calendar_link}, or let me know a couple of slots that work for you."
            else:
                meeting_draft = "Thanks for getting back to me! Would you have 15 minutes early next week for a brief conversation? Let me know what days work best on your side."

            return AgentResult(
                agent_id=self.agent_id,
                tenant_id=self.tenant_id,
                deal_room_id=deal_room.id,
                decision="meeting_requested",
                confidence=0.95,
                source="inbound_reply",
                reasoning_summary="Positive interest detected. Ready to book calendar meeting.",
                recommended_next_step="schedule_calendar_meeting",
                data={
                    "intent": "interested",
                    "draft_reply": meeting_draft,
                    "transition": transition,
                },
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        else:
            # Query hybrid RAG to answer technical or product question
            rag_context = self.rag.assemble_context(inbound_text, top_k=2)
            context_text = rag_context.get("context") or ""
            citations = rag_context.get("citations", [])

            draft_answer = parsed.get("suggested_reply")
            if not draft_answer and context_text and self.llm:
                try:
                    q_prompt = (
                        f"Prospect Question: \"{inbound_text}\"\n"
                        f"Verified Knowledge:\n{context_text}\n\n"
                        f"Draft a helpful, 2-sentence response answering the question based strictly on verified documentation. Offer a brief discovery call."
                    )
                    draft_answer = await self.llm.complete(q_prompt)
                except Exception:
                    draft_answer = None

            if not draft_answer:
                draft_answer = "Thanks for reaching out! I've noted your question and am reviewing with our team to get you a detailed answer."

            return AgentResult(
                agent_id=self.agent_id,
                tenant_id=self.tenant_id,
                deal_room_id=deal_room.id,
                decision="question_answered",
                confidence=0.88,
                source="hybrid_rag",
                reasoning_summary="Grounded answer formulated from knowledge base.",
                recommended_next_step="send_answer_and_re_engage",
                data={
                    "intent": intent,
                    "draft_reply": draft_answer,
                    "citations": citations,
                },
                execution_time_ms=int((time.time() - start_time) * 1000),
            )


ConversationIntelligenceAgent = ConversationAgent
