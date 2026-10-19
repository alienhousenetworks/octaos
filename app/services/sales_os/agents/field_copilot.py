"""Agent 12: Field Copilot (Voice-to-CRM & Mobile Field Assistant).

Responsibilities:
1. Ingests multilingual voice notes from field visits (English, Hindi/Hinglish, regional variants).
2. Extracts structured meeting notes (attendees, pains, competitors, budget, mutual commitments).
3. Produces atomic CRM updates and auto-drafts immediate Email & WhatsApp follow-ups.
4. Level 1 Autonomy: Drafts are delivered to the field rep for one-click mobile approval.
"""
import time
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.services.sales_os.agents.base import BaseSalesAgent, AgentResult, EvidenceItem
from app.models.deal_room import DealRoom, DealActivity
from app.schemas.sales_swarm import (
    FieldVisitSummary,
    StructuredMeetingNote,
)
from app.services.knowledge_os.entity_extractor import extract_json_safe
from app.services.sales_os.aso.field_extract import extract_field_note, grounded_in_transcript
from app.services.sales_os.contracts.registry import render_prompts

logger = logging.getLogger(__name__)


class FieldCopilotAgent(BaseSalesAgent):
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, tenant_id, "agent_12_field_copilot")

    async def execute(self, deal_room_id: str, parameters: Dict[str, Any] = None) -> AgentResult[FieldVisitSummary]:
        start_time = time.time()
        params = parameters or {}
        rep_id = params.get("rep_id", "rep_field_1")
        raw_transcript = (params.get("raw_transcript") or params.get("voice_memo") or "").strip()
        lang = params.get("language", "en-US")

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
                reasoning_summary=f"DealRoom '{deal_room_id}' not found.",
                recommended_next_step="discover_account",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        if not raw_transcript:
            empty = FieldVisitSummary(
                deal_room_id=deal_room.id,
                rep_id=rep_id,
                audio_language_detected=lang,
                raw_transcript="",
                structured_note=StructuredMeetingNote(),
                follow_up_draft_email="",
                follow_up_draft_whatsapp="",
            )
            return AgentResult(
                agent_id=self.agent_id,
                tenant_id=self.tenant_id,
                deal_room_id=deal_room.id,
                contract_id="sales.field_copilot",
                decision="insufficient_evidence",
                confidence=0.0,
                reasoning_summary="No voice transcript was supplied.",
                recommended_next_step="collect_transcript",
                data=empty,
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        rendered = render_prompts(
            "sales.field_copilot",
            {"company_name": deal_room.company_name, "transcript": raw_transcript},
        )
        data = extract_field_note(raw_transcript)
        try:
            llm_resp = await self.llm.complete(
                prompt=rendered["task_prompt"],
                system_prompt=rendered["system_prompt"],
            )
            model_data = extract_json_safe(llm_resp)
            if isinstance(model_data, dict):
                data = grounded_in_transcript(model_data, raw_transcript)
                if not data.get("client_pain_points") and not data.get("budget_discussed"):
                    data = extract_field_note(raw_transcript)
        except Exception as e:
            logger.warning("Field copilot used transcript extraction: %s", e)

        note = StructuredMeetingNote(
            attendees=data.get("attendees", []),
            client_pain_points=data.get("client_pain_points", []),
            competitor_mentions=data.get("competitor_mentions", []),
            budget_discussed=data.get("budget_discussed"),
            timeline_stated=data.get("timeline_stated"),
            commitments_made_by_rep=data.get("commitments_made_by_rep", []),
            commitments_made_by_client=data.get("commitments_made_by_client", []),
        )

        crm_updates = {
            "last_field_visit_at": datetime.now(timezone.utc).isoformat(),
            "detected_budget_usd": note.budget_discussed,
            "competitors": note.competitor_mentions,
            "pain_points": note.client_pain_points,
            "recommended_stage": data.get("recommended_stage", "proposal"),
        }

        # Log DealActivity
        act = DealActivity(
            deal_room_id=deal_room.id,
            tenant_id=self.tenant_id,
            activity_type="note_added",
            direction="internal",
            subject=f"Field Visit Voice Memo Summary (Rep: {rep_id})",
            content=f"Attendees: {', '.join(note.attendees)}\nPains: {', '.join(note.client_pain_points)}\nRep Commitments: {', '.join(note.commitments_made_by_rep)}",
            metadata_json={"raw_transcript": raw_transcript, "extracted": data},
        )
        self.db.add(act)
        self.db.commit()

        summary = FieldVisitSummary(
            deal_room_id=deal_room.id,
            rep_id=rep_id,
            audio_language_detected=lang,
            raw_transcript=raw_transcript,
            structured_note=note,
            crm_field_updates=crm_updates,
            follow_up_draft_email=data.get("email_body", ""),
            follow_up_draft_whatsapp=data.get("whatsapp_body", ""),
            recommended_stage_transition=data.get("recommended_stage"),
        )

        return AgentResult(
            agent_id=self.agent_id,
            tenant_id=self.tenant_id,
            deal_room_id=deal_room.id,
            contract_id="sales.field_copilot",
            prompt_version=rendered["prompt_version"],
            decision="ready",
            confidence=0.92,
            evidence=[
                EvidenceItem(
                    claim=f"Voice memo transcribed from on-site visit ({len(raw_transcript.split())} words)",
                    source="field_voice_memo",
                    confidence=1.0,
                )
            ],
            source="field_copilot",
            reasoning_summary=f"Processed voice note for {deal_room.company_name}. Extracted {len(note.client_pain_points)} pain points and {len(note.commitments_made_by_rep)} commitments. Drafted Email/WhatsApp follow-ups.",
            missing_information=[],
            recommended_next_step="approve_follow_up_draft_on_mobile",
            data=summary,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )
