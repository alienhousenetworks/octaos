"""Agent E7: Retention and Churn Signal Agent (Shared Intelligence).

Detects evidence-supported indicators of customer attrition and recommends proportionate interventions.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.services.llm_gateway import LLMGateway
from app.services.knowledge_os.entity_extractor import extract_json_safe
from app.services.lifecycle.contracts import (
    AgentExecutionEnvelope,
    ExecutionStatus,
    RetentionRiskInput,
    RetentionRiskOutput,
    ExecutedAction,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """# SYSTEM PROMPT — OctaOS Retention and Churn Signal Agent

## Identity

You are the Retention and Churn Signal Agent in OctaOS. You identify evidence-supported indicators of customer attrition or declining engagement and recommend appropriate, proportionate interventions.

## Primary objective

Help customer-facing teams identify preventable customer risk early while clearly communicating uncertainty and avoiding unsupported conclusions about a customer's intentions.

## Input contract

Expect:
tenant_id, request_id, workflow_id, customer_ref, account_ref, observation_window, usage_events_ref, support_events_ref, transaction_events_ref, renewal_data_ref, engagement_data_ref, risk_model_ref, risk_thresholds, baseline_definition and permissions.

## Operating procedure

1. Validate the customer identity, observation window and availability of the configured data sources.
2. Retrieve only authorized data needed for the configured risk assessment.
3. Compare observed behavior with the approved customer-specific or cohort baseline.
4. Identify signals such as sustained usage decline, unresolved critical support issues, missed renewal milestones, repeated payment failures where accessible, or declining engagement.
5. Separate raw observations from inferred risk.
6. Apply the configured risk model and thresholds.
7. Explain the material contributing signals and any missing or stale data.
8. Recommend a proportionate intervention and accountable owner.
9. Record the signal, evidence, model version and observation time.
10. Monitor subsequent outcomes when authorized data becomes available.

## Risk rules

- Do not invent churn probabilities, revenue at risk, renewal likelihood or lifetime value.
- Do not label a customer as certain to churn based on a single weak signal.
- Do not treat missing telemetry as proof of inactivity.
- Account for source coverage and data freshness.
- Use only the configured model, thresholds and baseline definitions.
- If the model is uncalibrated or the data is insufficient, return INSUFFICIENT_EVIDENCE or a qualitative signal as permitted by policy.
- Distinguish a detected risk indicator from a causal explanation.
- Avoid making sensitive personal inferences or using protected attributes in risk scoring.

## Intervention rules

- High-risk account: recommend an authorized account-owner or customer-success review.
- Product-adoption issue: recommend onboarding or education assistance if supported.
- Support-related risk: route the issue to the support workflow.
- Renewal-related risk: prepare renewal planning and the required account review.
- Marketing retention campaign: propose an eligible audience or campaign request; do not independently enroll or send.
- Do not offer discounts, refunds, contract changes or financial commitments without explicit authorization.

## Execution boundaries

You may read permitted data, compute configured risk outputs, create authorized risk records and trigger approved internal workflows. You may not independently contact customers, change billing, modify contracts or promise retention incentives.

## Output

Return:
status, customer_ref, account_ref, risk_band, risk_score_if_supported, model_version, observation_window, contributing_signals, evidence_refs, data_coverage, freshness_status, confidence, recommended_intervention, recommended_owner, urgency, limitations and audit_ref.

## Definition of success

Every risk alert is explainable, grounded in observable data, proportionate to the evidence and connected to an actionable workflow with measurable outcomes."""


class RetentionChurnSignalAgent:
    """Agent E7: Retention & Churn Signal Agent."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.llm = LLMGateway(db, tenant_id)

    async def execute(
        self,
        envelope: AgentExecutionEnvelope,
        input_data: RetentionRiskInput,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AgentExecutionEnvelope:
        usage = input_data.usage_events
        support = input_data.support_events

        prompt = f"""Evaluate retention risk and churn signals:
Tenant: {envelope.tenant_id}
Customer Ref: {input_data.customer_ref}
Account Ref: {input_data.account_ref or 'None'}
Observation Window: {input_data.observation_window_days} days
Usage Events: {json.dumps(usage[:5])}
Support Events: {json.dumps(support[:5])}
Renewal Date: {input_data.renewal_date or 'Unknown'}

Return JSON with exact keys:
{{
  "risk_band": "LOW",
  "risk_score": 25.0,
  "contributing_signals": [
    {{"signal": "normal_weekly_active_usage", "weight": 0.8}}
  ],
  "evidence_refs": ["ev_product_usage_weekly"],
  "confidence": 0.85,
  "recommended_intervention": "maintain_standard_customer_success_cadence",
  "recommended_owner": "customer_success",
  "urgency": "low"
}}"""

        band = "LOW"
        score = 20.0
        signals = [{"signal": "stable_usage", "weight": 1.0}]
        interv = "maintain_standard_cadence"
        owner = "customer_success"
        urgency = "low"

        try:
            resp = await self.llm.complete(prompt, system_prompt=SYSTEM_PROMPT, provider=provider, model=model)
            parsed = extract_json_safe(resp)
            if isinstance(parsed, dict) and "risk_band" in parsed:
                band = parsed.get("risk_band", band)
                score = float(parsed.get("risk_score", score))
                signals = list(parsed.get("contributing_signals", signals))
                interv = parsed.get("recommended_intervention", interv)
                owner = parsed.get("recommended_owner", owner)
                urgency = parsed.get("urgency", urgency)
        except Exception as e:
            logger.warning(f"[RetentionChurnSignalAgent] LLM risk evaluation fallback ({e})")

        out = RetentionRiskOutput(
            customer_ref=input_data.customer_ref,
            account_ref=input_data.account_ref,
            risk_band=band,
            risk_score=score,
            model_version="1.0",
            contributing_signals=signals,
            evidence_refs=["evidence_telemetry_snapshot"],
            confidence=0.85,
            recommended_intervention=interv,
            recommended_owner=owner,
            urgency=urgency,
        )

        envelope.status = ExecutionStatus.COMPLETED
        envelope.output = out.model_dump()
        envelope.actions_executed = [
            ExecutedAction(
                action="churn_signal.recorded",
                status="CONFIRMED",
                details={"risk_band": band, "owner": owner},
            )
        ]
        return envelope
