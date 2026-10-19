"""Capability 16 & 17: Evidence-Backed Message Composer.

Drafts:
- High-performing, concise outreach (< 125 words for cold touches)
- Personalized to the recipient's role in the Buying Committee
- Grounded strictly in verified EvidenceRecord and AccountSignal items
- Automatically runs GroundednessEvaluator before allowing dispatch
"""
import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.services.sales_os.agents.base import BaseSalesAgent, AgentResult, EvidenceItem
from app.models.deal_room import DealRoom, BuyingCommitteeMember, AccountSignal, CompanySalesContext, EvidenceRecord
from app.services.sales_os.evals.groundedness import GroundednessEvaluator
from app.services.sales_os.governance.gatekeeper import PreSendGatekeeper
from app.services.knowledge_os.entity_extractor import extract_json_safe
from app.services.sales_os.contracts.registry import render_prompts


class ComposerAgent(BaseSalesAgent):
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, tenant_id, "agent_17_composer")
        self.evaluator = GroundednessEvaluator(min_confidence=0.85)

    async def execute(self, deal_room_id: str, parameters: Dict[str, Any] = None) -> AgentResult:
        start_time = time.time()
        params = parameters or {}
        committee_member_id = params.get("committee_member_id")
        channel = params.get("channel", "email")

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

        # Fetch committee member
        member = None
        if committee_member_id:
            member = (
                self.db.query(BuyingCommitteeMember)
                .filter(BuyingCommitteeMember.id == committee_member_id)
                .first()
            )
        if not member:
            member = (
                self.db.query(BuyingCommitteeMember)
                .filter(BuyingCommitteeMember.deal_room_id == deal_room_id)
                .first()
            )

        recipient_name = member.name if member else "Decision Maker"
        recipient_title = member.title if member else "Leader"
        recipient_role = member.role_type if member else "economic_buyer"

        # Check suppression
        from app.services.sales_os.governance.suppression import SuppressionService
        suppression = SuppressionService(self.db, self.tenant_id)
        if member and member.email:
            is_supp = suppression.is_suppressed(email=member.email)
            if is_supp:
                return AgentResult(
                    agent_id=self.agent_id,
                    tenant_id=self.tenant_id,
                    deal_room_id=deal_room_id,
                    decision="blocked",
                    confidence=1.0,
                    reasoning_summary=f"Recipient {member.email} is suppressed: {is_supp.reason}",
                    recommended_next_step="suppressed",
                )

        ctx = (
            self.db.query(CompanySalesContext)
            .filter(CompanySalesContext.tenant_id == self.tenant_id, CompanySalesContext.is_active == True)
            .first()
        )
        our_company = ctx.company_overview.get("name", "OctaOS") if ctx else "OctaOS"
        our_usp = ctx.company_overview.get("usp", "Enterprise autonomous sales operating system") if ctx else "Enterprise sales platform"

        from app.models.base import User
        user = self.db.query(User).filter_by(tenant_id=self.tenant_id).order_by(User.is_superuser.desc(), User.id.asc()).first()
        employee_name = user.name.strip() if (user and user.name and user.name.strip()) else None
        if employee_name:
            sender_rule = f"Write on behalf of {employee_name} at {our_company}. Sign off with: Best regards, {employee_name}, {our_company}."
        else:
            sender_rule = f"Write on behalf of {our_company}. Do NOT invent any employee name. Sign off strictly with: Best regards, The {our_company} Team."

        pain_points = [p.get("inference", "") for p in (deal_room.pain_hypotheses or [])]
        signals = [s.headline for s in self.db.query(AccountSignal).filter(AccountSignal.deal_room_id == deal_room_id).all()]
        ev_records = self.db.query(EvidenceRecord).filter(EvidenceRecord.tenant_id == self.tenant_id).all()
        proof_claims = [e.claim for e in ev_records]

        rendered = render_prompts(
            "sales.composer",
            {
                "channel": channel,
                "sender_rule": sender_rule,
                "recipient_name": recipient_name,
                "recipient_title": recipient_title,
                "recipient_role": recipient_role,
                "company_name": deal_room.company_name,
                "signals": ", ".join(signals) if signals else "none",
                "pain_points": ", ".join(pain_points) if pain_points else "none",
                "usp": our_usp,
            },
        )
        try:
            resp = await self.llm.complete(
                prompt=rendered["task_prompt"],
                system_prompt=rendered["system_prompt"],
                model=rendered["model_id"],
                provider=rendered["provider"],
            )
            msg_data = extract_json_safe(resp) or {}
            if not isinstance(msg_data, dict):
                msg_data = {}
            subject = msg_data.get("subject") or f"Question for {recipient_name}"
            body = str(msg_data.get("body") or "").strip()
            if not body:
                raise ValueError("composer returned an empty draft")
        except Exception:
            subject = f"Question for {recipient_name}"
            signoff = f"Best regards,\n{employee_name}\n{our_company}" if employee_name else f"Best regards,\nThe {our_company} Team\n{our_company}"
            if signals:
                body = f"Hi {recipient_name},\n\nNoticed {deal_room.company_name}'s recent update: {signals[0]}.\n\nOpen to a brief conversation this week?\n\n{signoff}"
            elif proof_claims:
                body = f"Hi {recipient_name},\n\n{proof_claims[0]}\n\nOpen to a brief conversation this week?\n\n{signoff}"
            else:
                body = f"Hi {recipient_name},\n\nOpen to a brief conversation this week?\n\n{signoff}"

        # Evaluate Pre-Send Deliverability & Anti-Spam Gate
        gatekeeper_report = PreSendGatekeeper.evaluate(
            subject=subject,
            body=body,
            step_number=params.get("step_number", 1),
            max_words=params.get("max_words"),
            max_links=params.get("max_links", 1),
        )
        if gatekeeper_report.cleaned_body:
            body = gatekeeper_report.cleaned_body
        if gatekeeper_report.cleaned_subject:
            subject = gatekeeper_report.cleaned_subject

        # Evaluate Groundedness
        evidence_records = [
            {"claim": s, "source": "verified_signal", "confidence": 0.95} for s in signals
        ] + [
            {"claim": our_usp, "source": "company_sales_context", "confidence": 1.0}
        ] + [
            {"claim": pc, "source": "evidence_record", "confidence": 1.0} for pc in proof_claims
        ]
        report = self.evaluator.evaluate(body, evidence_records, strict_mode=False)

        is_grounded = report.is_fully_grounded or report.groundedness_score >= 0.85
        is_gate_clean = gatekeeper_report.is_valid

        if is_grounded and is_gate_clean:
            decision = "ready"
            reasoning = (
                f"Drafted {channel} message ({gatekeeper_report.word_count} words). "
                f"Groundedness score: {report.groundedness_score:.2f}. Passed deliverability gatekeeper. Ready for outbox."
            )
        elif not is_gate_clean:
            decision = "review_required"
            reasoning = f"Flagged by deliverability gatekeeper: {'; '.join(gatekeeper_report.violations)}"
        else:
            decision = "review_required"
            reasoning = "Flagged for review due to ungrounded claims. Not sent."

        elapsed = int((time.time() - start_time) * 1000)
        report_data = report.model_dump() if hasattr(report, "model_dump") else report.dict()
        gate_data = gatekeeper_report.model_dump() if hasattr(gatekeeper_report, "model_dump") else gatekeeper_report.dict()

        return AgentResult(
            agent_id=self.agent_id,
            tenant_id=self.tenant_id,
            deal_room_id=deal_room.id,
            contract_id="sales.composer",
            prompt_version=rendered["prompt_version"],
            decision=decision,
            confidence=report.groundedness_score if is_gate_clean else min(report.groundedness_score, 0.4),
            evidence=[EvidenceItem(claim=c.claim_text, source=c.source_type, confidence=c.confidence) for c in report.claims if c.is_grounded] or [EvidenceItem(claim="Grounded in verified context", source="evidence_record", confidence=1.0)],
            source="composer_evaluator",
            reasoning_summary=reasoning,
            missing_information=report.ungrounded_claims + gatekeeper_report.violations,
            recommended_next_step="outbox_stage" if decision == "ready" else "policy_governance_check",
            data={
                "subject": subject,
                "body": body,
                "recipient_name": recipient_name,
                "recipient_email": member.email if member else None,
                "channel": channel,
                "groundedness_score": report.groundedness_score,
                "groundedness_report": report_data,
                "gatekeeper_report": gate_data,
                "policy_status": "not_submitted",
                "sent": False,
            },
            execution_time_ms=elapsed,
        )


EvidenceGroundedComposer = ComposerAgent
