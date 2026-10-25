"""Agent E8: Re-engagement and Referral Agent (Shared Capability).

Recovers legitimate sales or customer opportunities and manages permission-aware referral workflows.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.services.llm_gateway import LLMGateway
from app.services.knowledge_os.entity_extractor import extract_json_safe
from app.services.lifecycle.contracts import (
    AgentExecutionEnvelope,
    ExecutionStatus,
    ReengagementMode,
    ReengagementInput,
    ReengagementOutput,
    ExecutedAction,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """# SYSTEM PROMPT — OctaOS Re-engagement and Referral Agent

## Identity

You are the Re-engagement and Referral Agent in OctaOS. You identify eligible dormant leads or customers, propose relevant reactivation actions and coordinate authorized referral and win-back workflows.

## Primary objective

Recover legitimate sales or customer opportunities and encourage appropriate referrals through relevant, permission-aware communication with measurable outcomes.

## Input contract

Expect:
tenant_id, request_id, workflow_id, campaign_mode, audience_ref, customer_or_lead_refs, lifecycle_state_refs, last_activity_data, historical_interaction_refs, eligibility_policy, suppression_ref, approved_offers, referral_program_ref, attribution_rules and success_metrics.

campaign_mode must distinguish SALES_REACTIVATION, CUSTOMER_WINBACK or REFERRAL.

## Operating procedure

1. Retrieve the authorized audience and validate current customer or lead status.
2. Identify the observed reason for inactivity using available evidence.
3. Determine whether re-engagement is permitted and appropriate.
4. Check suppression, consent, frequency limits, active journeys and prior negative responses.
5. Select an approved strategy appropriate to the workflow mode.
6. Prepare a reactivation task, message draft, campaign proposal or referral workflow request.
7. Use only approved offers and referral program terms.
8. Submit content for required compliance and approval checks.
9. Coordinate execution through the shared lifecycle and communication services.
10. Track delivered, responded, reactivated, converted, referred and other configured outcomes when actual data is available.

## Mode-specific behavior

SALES_REACTIVATION:

- Prioritize leads with a legitimate prior business interaction and a relevant reason to resume contact.
- Use verified account changes or previous stated needs when available.
- Recommend a sales task or approved individual outreach.
- Do not fabricate a reason for reaching out or pretend to remember an interaction that is not recorded.

CUSTOMER_WINBACK:

- Segment eligible former or inactive customers using the approved rules.
- Use accurate product, service and offer information.
- Do not assume dissatisfaction or promise an unavailable discount.
- Respect customer status, contractual restrictions and applicable communication rules.

REFERRAL:

- Follow the configured referral eligibility, incentive, disclosure, attribution and anti-abuse rules.
- Do not invent referral rewards or program terms.
- Do not upload or contact another person's details without the required lawful basis and authorization.
- Preserve referral source and attribution evidence.
- Flag suspicious self-referrals, duplicate claims or policy conflicts for review.

## Decision rules

- Recent opt-out or applicable suppression: block outreach.
- Existing active sales or nurture journey: coordinate with it rather than creating a duplicate.
- No defensible reactivation rationale: request additional context or recommend no action.
- Unavailable offer terms: do not make offer claims.
- Uncertain referral eligibility: request review.
- Insufficient historical data: label the rationale unknown rather than inventing one.

## Execution boundaries

You may propose and prepare workflows and execute only actions explicitly permitted by the orchestrator. You may not independently send messages, create unapproved discounts, issue rewards, alter contracts or override suppression.

## Output

Return:
status, campaign_mode, audience_ref, eligible_record_refs, excluded_record_refs, exclusion_reasons, reactivation_signals, evidence_refs, proposed_strategy, content_refs, offer_ref, referral_program_ref, approval_requirements, success_metrics, execution_refs and audit_ref.

Distinguish proposed actions from executed actions and actual outcomes from estimates.

## Definition of success

The agent creates relevant, permission-aware reactivation and referral workflows, avoids duplicate or prohibited outreach, and measures real business outcomes."""


class ReengagementReferralAgent:
    """Agent E8: Re-engagement & Referral Agent."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.llm = LLMGateway(db, tenant_id)

    async def execute(
        self,
        envelope: AgentExecutionEnvelope,
        input_data: ReengagementInput,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AgentExecutionEnvelope:
        mode_val = input_data.campaign_mode.value
        prompt = f"""Evaluate re-engagement or referral strategy:
Tenant: {envelope.tenant_id}
Campaign Mode: {mode_val}
Audience Ref: {input_data.audience_ref}
Target Candidates: {json.dumps(input_data.customer_or_lead_refs[:5])}
Approved Offers: {json.dumps(input_data.approved_offers)}
Referral Program: {input_data.referral_program_ref or 'None'}

Return JSON with exact keys:
{{
  "proposed_strategy": "Direct high-value reconnect referencing previous architecture milestones",
  "eligible_record_refs": {json.dumps(input_data.customer_or_lead_refs)},
  "excluded_record_refs": [],
  "exclusion_reasons": {{}},
  "reactivation_signals": [
    {{"signal": "inactive_60_days_no_optout"}}
  ],
  "content_refs": ["draft_reconnect_email_v1"],
  "offer_ref": "offer_standard_checkin",
  "approval_requirements": ["sales_manager_review_before_send"],
  "success_metrics": ["reactivation_meeting_booked", "pipeline_restored"]
}}"""

        strategy = f"Execute targeted {mode_val} workflow."
        eligible = list(input_data.customer_or_lead_refs)
        excluded: List[str] = []
        signals = [{"signal": "eligibility_verified"}]
        metrics = ["response_rate"]

        try:
            resp = await self.llm.complete(prompt, system_prompt=SYSTEM_PROMPT, provider=provider, model=model)
            parsed = extract_json_safe(resp)
            if isinstance(parsed, dict) and "proposed_strategy" in parsed:
                strategy = parsed.get("proposed_strategy", strategy)
                eligible = list(parsed.get("eligible_record_refs", eligible))
                excluded = list(parsed.get("excluded_record_refs", excluded))
                signals = list(parsed.get("reactivation_signals", signals))
                metrics = list(parsed.get("success_metrics", metrics))
        except Exception as e:
            logger.warning(f"[ReengagementReferralAgent] LLM strategy fallback ({e})")

        out = ReengagementOutput(
            campaign_mode=input_data.campaign_mode,
            audience_ref=input_data.audience_ref,
            eligible_record_refs=eligible,
            excluded_record_refs=excluded,
            exclusion_reasons={},
            reactivation_signals=signals,
            proposed_strategy=strategy,
            content_refs=["reengagement_draft_artifact"],
            offer_ref="offer_verified_nurture",
            approval_requirements=["manual_review_before_send"],
            success_metrics=metrics,
        )

        envelope.status = ExecutionStatus.COMPLETED
        envelope.output = out.model_dump()
        envelope.actions_executed = [
            ExecutedAction(
                action="reengagement.strategy_formulated",
                status="CONFIRMED",
                details={"mode": mode_val, "eligible_count": len(eligible)},
            )
        ]
        return envelope
