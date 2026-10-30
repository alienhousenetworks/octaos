"""Capability 11: Sub-60s Executive Account Researcher.

Generates an Executive Account Intelligence Brief in under 60 seconds:
1. Company Overview & Business Model
2. Recent Signals & Context (with cited source URLs)
3. Buying Committee Structure
4. 2 Grounded Pain Hypotheses (Signal + Inference + Confidence)
5. Matched Proof Point from Tenant Knowledge Base
"""
import logging
import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.services.sales_os.agents.base import BaseSalesAgent, AgentResult, EvidenceItem
from app.models.deal_room import DealRoom, AccountSignal, BuyingCommitteeMember, CompanySalesContext
from app.services.knowledge_os.entity_extractor import extract_json_safe
from app.services.sales_os.aso.state_machine import apply_transition
from app.services.sales_os.contracts.registry import render_prompts

logger = logging.getLogger(__name__)


class AccountResearcherAgent(BaseSalesAgent):
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, tenant_id, "agent_11_account_researcher")

    async def execute(self, deal_room_id: str, parameters: Dict[str, Any] = None) -> AgentResult:
        start_time = time.time()
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

        # Fetch signals and committee
        signals = (
            self.db.query(AccountSignal)
            .filter(AccountSignal.deal_room_id == deal_room_id, AccountSignal.is_active == True)
            .all()
        )

        # Zero-cost direct web profiling if unprofiled
        target_web = deal_room.website or deal_room.domain
        if target_web and not signals:
            try:
                from app.services.sales_os.discovery.direct_profiler import DirectProfiler
                profile_res = await DirectProfiler.profile_url(target_web, timeout_sec=5.0)
                for sig in profile_res.signals:
                    acc_sig = AccountSignal(
                        tenant_id=self.tenant_id,
                        deal_room_id=deal_room.id,
                        signal_type=sig["signal_type"],
                        headline=sig["headline"],
                        confidence=sig["confidence"],
                        evidence_snippet=sig.get("evidence"),
                        is_active=True,
                    )
                    self.db.add(acc_sig)
                if profile_res.signals:
                    self.db.commit()
                    signals = (
                        self.db.query(AccountSignal)
                        .filter(AccountSignal.deal_room_id == deal_room_id, AccountSignal.is_active == True)
                        .all()
                    )
            except Exception as e:
                logger.debug(f"Direct web profiling skipped for {target_web}: {e}")
        committee = (
            self.db.query(BuyingCommitteeMember)
            .filter(BuyingCommitteeMember.deal_room_id == deal_room_id)
            .all()
        )

        ctx = (
            self.db.query(CompanySalesContext)
            .filter(
                CompanySalesContext.tenant_id == self.tenant_id,
                CompanySalesContext.is_active == True,  # noqa: E712
            )
            .first()
        )

        signals_text = "\n".join([f"- [{s.signal_type}]: {s.headline} (Confidence: {s.confidence})" for s in signals]) if signals else "No recent external signals logged."
        committee_text = ", ".join([f"{m.name} ({m.title}, {m.role_type})" for m in committee]) if committee else "Committee not yet mapped."
        offer_usp = ctx.company_overview.get("usp", "Enterprise automation platform") if ctx else "Sales Intelligence Platform"
        proof_points = ctx.proof_points if ctx else []
        if proof_points:
            pp_str = "; ".join([str(p.get("claim") if isinstance(p, dict) else p) for p in proof_points[:3]])
            offer_usp = f"{offer_usp}. Evidence & Proof Points: {pp_str}"

        rendered = render_prompts(
            "sales.account_researcher",
            {
                "company_name": deal_room.company_name,
                "domain": deal_room.domain,
                "industry": deal_room.industry or "unknown",
                "employee_count": "unknown" if deal_room.employee_count is None else str(deal_room.employee_count),
                "signals": signals_text,
                "committee": committee_text,
                "value_proposition": offer_usp,
            },
        )

        brief_data = None
        try:
            resp = await self.llm.complete(
                prompt=rendered["task_prompt"],
                system_prompt=rendered["system_prompt"],
                model=rendered["model_id"],
                provider=rendered["provider"],
            )
            parsed = extract_json_safe(resp)
            if isinstance(parsed, dict):
                brief_data = parsed
        except Exception:
            brief_data = None

        import re
        hypotheses = []
        if isinstance(brief_data, dict):
            raw_hypotheses = brief_data.get("pain_hypotheses") or []
            if isinstance(raw_hypotheses, list):
                for item in raw_hypotheses:
                    if not isinstance(item, dict):
                        continue
                    signal = str(item.get("signal") or "").strip()
                    if not signal:
                        continue
                    if signal.lower() in signals_text.lower():
                        hypotheses.append(item)
                        continue
                    # Match on significant token overlap with any logged signal headline
                    sig_tokens = {w for w in re.findall(r"\w{4,}", signal.lower())}
                    if sig_tokens and any(
                        len(sig_tokens & {w for w in re.findall(r"\w{4,}", s.headline.lower())}) >= 1
                        for s in signals
                    ):
                        hypotheses.append(item)

            brief_data["pain_hypotheses"] = hypotheses
            brief_data["company_name"] = deal_room.company_name

        status = "insufficient_evidence"
        if isinstance(brief_data, dict) and brief_data.get("executive_summary") and hypotheses:
            status = str(brief_data.get("status") or "complete")
            if status not in {"complete", "conflicting_evidence"}:
                status = "complete"
        elif isinstance(brief_data, dict):
            brief_data["status"] = "insufficient_evidence"
            brief_data["company_name"] = deal_room.company_name
        else:
            brief_data = {
                "status": "insufficient_evidence",
                "company_name": deal_room.company_name,
                "executive_summary": "",
                "business_model": "",
                "pain_hypotheses": [],
                "recommended_angle": "",
            }

        if status == "complete":
            transition = apply_transition(
                deal_room,
                "research_complete",
                actor="sales.account_researcher",
                reason="Account brief is grounded in supplied signals.",
            )
            decision = "ready" if transition["applied"] else "blocked"
        else:
            transition = {"applied": False, "current_state": deal_room.stage, "reason": "insufficient_evidence"}
            decision = "insufficient_evidence"

        deal_room.account_brief = brief_data
        deal_room.pain_hypotheses = hypotheses
        self.db.commit()

        elapsed = int((time.time() - start_time) * 1000)
        summary = brief_data.get("executive_summary") or "Insufficient evidence for an account brief."
        return AgentResult(
            agent_id=self.agent_id,
            tenant_id=self.tenant_id,
            deal_room_id=deal_room.id,
            contract_id="sales.account_researcher",
            prompt_version=rendered["prompt_version"],
            decision=decision,
            confidence=0.0 if decision != "ready" else 0.7,
            evidence=[
                EvidenceItem(
                    claim=f"{deal_room.company_name}: {summary[:160]}",
                    source="account_researcher",
                    confidence=0.0 if decision != "ready" else 0.7,
                )
            ],
            source="account_researcher",
            reasoning_summary=summary[:240],
            missing_information=[] if hypotheses else ["pain_hypothesis"],
            recommended_next_step="strategist_cadence" if decision == "ready" else "collect_evidence",
            data={
                "brief": brief_data,
                "pain_hypotheses": hypotheses,
                "status": brief_data.get("status"),
                "transition": transition,
                **brief_data,
            },
            execution_time_ms=elapsed,
        )
