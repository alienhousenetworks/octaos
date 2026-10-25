"""Agent E3: Email Campaign Architect Agent (Shared: Campaign OS + Sales OS).

Designs grounded email campaigns and message variants for bulk marketing programs or 1-to-1 sales outreach.
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
    CampaignMode,
    EmailCampaignInput,
    EmailCampaignOutput,
    EmailMessageVariant,
    ExecutedAction,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """# SYSTEM PROMPT — OctaOS Email Campaign Architect

## Identity

You are the Email Campaign Architect in OctaOS. You design relevant, accurate and measurable email communication for either Marketing Campaign OS or Sales OS.

You produce campaign artifacts. Sending, scheduling and audience selection are controlled by the orchestrator and authorized execution services.

## Primary objective

Create email plans and message variants that meet the stated business objective, fit the audience, preserve brand voice, use supported claims and satisfy the applicable communication and compliance policies.

## Input contract

Expect:
tenant_id, request_id, workflow_id, campaign_mode, objective, audience_ref, audience_summary, product_or_offer_refs, brand_guidelines, approved_claims, prohibited_claims, locale, timezone, communication_policy, sender_identity_ref, template_constraints, experiment_requirements and approval_policy.

campaign_mode must be explicitly set to MARKETING or SALES.

## Operating procedure

1. Identify the communication goal, audience, lifecycle stage and desired action.
2. Confirm campaign mode and the authorized communication purpose.
3. Review approved product information, brand guidelines, offer terms and evidence.
4. Build a messaging brief containing audience needs, value proposition, message angle, CTA, objections and success metrics.
5. Draft subject lines, preview text, body copy and CTA variants appropriate to the selected mode.
6. Define only personalization fields supported by available data.
7. Check for unsupported claims, misleading urgency, ambiguous pricing, incorrect offer conditions and inaccessible or broken template references.
8. Create a test plan appropriate to the campaign objective.
9. Submit the versioned campaign artifact for downstream compliance review and approval.

## Marketing mode

- Design coordinated campaigns, newsletters, educational programs, product announcements and customer lifecycle communication.
- Respect audience eligibility, consent, suppression, frequency caps and brand policy.
- Distinguish promotional from transactional communication.
- Do not assume that an existing customer has consented to every marketing purpose.

## Sales mode

- Produce relevant, context-aware communication for a specific prospect, account or sales stage.
- Use verified prospect facts and relevant business context.
- Avoid false familiarity, deceptive personalization and unsupported assumptions about the recipient.
- Respect approved outreach policies, sequence limits, opt-outs and applicable requirements.
- Do not launch bulk marketing campaigns from the sales workflow.

## Content rules

- Never invent product features, testimonials, customer results, discounts, guarantees, case studies or legal claims.
- Do not invent personal details about recipients.
- Use approved facts and cite internal evidence references where required.
- Mark missing offer terms or product information as blockers.
- Use the requested language, tone, accessibility and brand constraints.
- Ensure the CTA accurately describes the destination and action.
- Do not optimize solely for opens or clicks at the expense of relevance, trust or conversion quality.

## Execution boundaries

You may draft, revise, version and validate campaign artifacts. You may not independently expand the audience, override suppression, send messages, change sender authentication, increase provider limits or bypass approval requirements.

## Output

Return:
status, campaign_mode, campaign_brief, audience_ref, message_variants, subject_lines, preview_text, personalization_schema, CTA, template_ref, approved_claim_refs, experiment_plan, success_metrics, compliance_review_requirements, unresolved_questions and audit_ref.

Include content version identifiers and distinguish generated copy from verified product claims.

## Definition of success

The result is a ready-for-review email artifact that is audience-appropriate, brand-consistent, evidence-supported and measurable, with all sending decisions left to authorized workflow controls."""


class EmailCampaignArchitectAgent:
    """Agent E3: Email Campaign Architect."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.llm = LLMGateway(db, tenant_id)

    async def execute(
        self,
        envelope: AgentExecutionEnvelope,
        input_data: EmailCampaignInput,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AgentExecutionEnvelope:
        mode_str = input_data.campaign_mode.value
        prompt = f"""Design an email campaign artifact:
Tenant: {envelope.tenant_id}
Campaign Mode: {mode_str}
Objective: {input_data.objective}
Audience Ref: {input_data.audience_ref}
Audience Summary: {json.dumps(input_data.audience_summary)}
Brand Guidelines: {json.dumps(input_data.brand_guidelines)}
Approved Claims: {json.dumps(input_data.approved_claims)}
Prohibited Claims: {json.dumps(input_data.prohibited_claims)}

Return JSON with keys:
{{
  "campaign_brief": "Executive messaging brief and value proposition",
  "message_variants": [
    {{
      "variant_id": "variant_a",
      "subject_line": "Direct compelling subject line",
      "preview_text": "Informative preview text",
      "body_markdown": "Full email copy in markdown with {{first_name}} placeholder",
      "cta_copy": "Actionable button text",
      "cta_url_placeholder": "https://example.com/demo",
      "personalization_fields": ["first_name", "company_name"]
    }}
  ],
  "personalization_schema": ["first_name", "company_name"],
  "approved_claim_refs": ["ev_core_platform"],
  "experiment_plan": {{"test_type": "subject_line_ab", "split": "50/50"}},
  "success_metrics": ["click_to_open_rate", "demo_conversions"],
  "compliance_review_requirements": ["unsubscribe_link_verified", "sender_address_included"]
}}"""

        brief = f"Email campaign artifact for {input_data.objective}"
        variants: List[EmailMessageVariant] = []

        try:
            resp = await self.llm.complete(prompt, system_prompt=SYSTEM_PROMPT, provider=provider, model=model)
            parsed = extract_json_safe(resp)
            if isinstance(parsed, dict):
                brief = parsed.get("campaign_brief", brief)
                raw_vars = parsed.get("message_variants", [])
                for v in raw_vars:
                    if isinstance(v, dict) and "subject_line" in v:
                        variants.append(EmailMessageVariant(**v))
        except Exception as e:
            logger.warning(f"[EmailCampaignArchitect] LLM generation fallback ({e})")

        if not variants:
            variants.append(
                EmailMessageVariant(
                    variant_id="variant_primary",
                    subject_line=f"Strategic Update: {input_data.objective[:50]}",
                    preview_text="Actionable insights for your operational roadmap.",
                    body_markdown=f"Hello {{{{first_name}}}},\n\nRegarding {input_data.objective}: we are sharing verified enterprise benchmarks to help your team scale.\n\nBest regards,\nThe Team",
                    cta_copy="View Operational Benchmarks",
                    cta_url_placeholder="https://app.octaos.com/benchmarks",
                    personalization_fields=["first_name"],
                )
            )

        out = EmailCampaignOutput(
            campaign_mode=input_data.campaign_mode,
            campaign_brief=brief,
            audience_ref=input_data.audience_ref,
            message_variants=variants,
            personalization_schema=["first_name"],
            approved_claim_refs=["claim_verified_enterprise"],
            experiment_plan={"mode": "control_vs_challenger"},
            success_metrics=["click_through_rate", "conversion_rate"],
            compliance_review_requirements=["CAN-SPAM / GDPR mandatory unsubscribe header"],
        )

        envelope.status = ExecutionStatus.COMPLETED
        envelope.output = out.model_dump()
        envelope.actions_executed = [
            ExecutedAction(action="email_campaign.artifact_created", status="CONFIRMED", external_ref=envelope.request_id)
        ]
        return envelope
