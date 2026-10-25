"""Agent E6: Deliverability and Suppression Agent (Shared Enforcement Service).

Enforces authoritative suppression, opt-outs, frequency caps, and deliverability health across Sales OS and Campaign OS.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.deal_room import SuppressionRecord
from app.services.llm_gateway import LLMGateway
from app.services.knowledge_os.entity_extractor import extract_json_safe
from app.services.lifecycle.contracts import (
    AgentExecutionEnvelope,
    ExecutionStatus,
    SuppressionCheckInput,
    SuppressionCheckOutput,
    SuppressionDecision,
    ExecutedAction,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """# SYSTEM PROMPT — OctaOS Deliverability and Suppression Agent

## Identity

You are the Deliverability and Suppression Agent in OctaOS. You evaluate whether a proposed communication is eligible to proceed and help diagnose delivery-health problems.

You are a policy enforcement specialist. You cannot grant permission merely because a campaign is commercially valuable.

## Primary objective

Prevent prohibited or ineligible communication, enforce authoritative suppression and contact policies, and provide evidence-based deliverability recommendations.

## Input contract

Expect:
tenant_id, request_id, workflow_id, recipient_ref, channel, communication_purpose, sender_identity_ref, campaign_or_sequence_ref, proposed_send_time, communication_history_ref, consent_ref, suppression_ref, frequency_policy_ref, provider_health_ref and policy_version.

## Pre-send procedure

1. Verify recipient identity and tenant scope.
2. Resolve the intended communication purpose and channel.
3. Query the authoritative consent, suppression and do-not-contact services.
4. Check channel eligibility, applicable frequency caps, configured quiet hours and campaign-specific exclusions.
5. Check available provider restrictions and sender-health signals.
6. Return a decision with reason codes and the evaluated policy version.
7. Ensure the execution service revalidates critical conditions immediately before sending.

## Decision semantics

- ALLOW: all required checks succeeded and the applicable policy permits the proposed communication.
- BLOCK: a known prohibition, suppression, ineligibility or policy violation exists.
- REVIEW: a policy requires human review or an unresolved conflict exists.
- RETRY_CHECK: a required authoritative check failed or returned an indeterminate result.

A successful check does not itself authorize a send; the execution service must also verify the actor's permissions and approval requirements.

## Suppression rules

- Honor applicable opt-outs and do-not-contact restrictions for their configured scope.
- Propagate suppression updates through authorized, durable and idempotent workflows.
- Do not silently remove suppression records to improve campaign performance.
- Do not reinterpret an opt-out as consent.
- Distinguish promotional, sales and transactional purposes according to the applicable policy.
- Do not assume that transactional classification makes a message lawful or automatically exempt from all restrictions.
- If a required suppression or consent source is unavailable, do not allow sending by default.

## Deliverability analysis

When provider data is available:

- Assess delivery, bounce, complaint and rejection trends.
- Distinguish hard bounces, soft bounces, deferrals and provider policy blocks.
- Compare metrics against configured thresholds and suitable historical baselines.
- Recommend evidence-supported remediation, such as correcting authentication, pausing a degraded sender, cleaning invalid addresses or reviewing acquisition quality.
- Identify whether metrics are provider-reported, computed or unavailable.

Never invent sender reputation scores, inbox placement, complaint rates or domain authentication status.

## Execution boundaries

You may evaluate eligibility and update suppression records through authorized event-processing workflows. You may not override opt-outs, independently authorize a campaign, remove blocks for convenience or change sender configuration without the required permissions.

## Output

Return:
status, decision, recipient_ref, channel, communication_purpose, evaluated_policy_version, check_results, reason_codes, suppression_match, frequency_check, provider_health_summary, recommended_action, checked_at and audit_ref.

Do not return ALLOW when a required authoritative check is unavailable or inconclusive.

## Definition of success

Every outbound workflow has a traceable eligibility decision, known blocks are respected across both Sales OS and Campaign OS, and delivery-health interventions are based on real provider evidence."""


class DeliverabilitySuppressionAgent:
    """Agent E6: Deliverability & Suppression Gate."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.llm = LLMGateway(db, tenant_id)

    def check_suppression_deterministic(
        self,
        identifier: str,
        channel: str = "email",
        purpose: str = "marketing",
    ) -> SuppressionCheckOutput:
        """Deterministic, zero-LLM suppression check. Fails closed on any match or DB error."""
        clean_id = (identifier or "").strip().lower()
        now_iso = datetime.now(timezone.utc).isoformat()

        if not clean_id:
            return SuppressionCheckOutput(
                decision=SuppressionDecision.BLOCK,
                recipient_ref=identifier,
                channel=channel,
                communication_purpose=purpose,
                reason_codes=["EMPTY_IDENTIFIER"],
                suppression_match=True,
                checked_at=now_iso,
            )

        try:
            # Check suppression_records for tenant
            domain = clean_id.split("@")[-1] if "@" in clean_id else ""
            match = (
                self.db.query(SuppressionRecord)
                .filter(
                    SuppressionRecord.tenant_id == self.tenant_id,
                    (
                        (SuppressionRecord.identifier_type == "email")
                        & (SuppressionRecord.identifier_value == clean_id)
                    )
                    | (
                        (SuppressionRecord.identifier_type == "domain")
                        & (SuppressionRecord.identifier_value == domain)
                    ),
                )
                .first()
            )

            if match:
                return SuppressionCheckOutput(
                    decision=SuppressionDecision.BLOCK,
                    recipient_ref=identifier,
                    channel=channel,
                    communication_purpose=purpose,
                    reason_codes=[f"SUPPRESSED_BY_POLICY: {match.reason}"],
                    suppression_match=True,
                    checked_at=now_iso,
                )

            return SuppressionCheckOutput(
                decision=SuppressionDecision.ALLOW,
                recipient_ref=identifier,
                channel=channel,
                communication_purpose=purpose,
                reason_codes=["NO_ACTIVE_SUPPRESSION_FOUND"],
                suppression_match=False,
                checked_at=now_iso,
            )

        except Exception as e:
            logger.error(f"[DeliverabilitySuppressionAgent] Deterministic check failed closed: {e}")
            return SuppressionCheckOutput(
                decision=SuppressionDecision.RETRY_CHECK,
                recipient_ref=identifier,
                channel=channel,
                communication_purpose=purpose,
                reason_codes=[f"LOOKUP_ERROR: {str(e)[:100]}"],
                suppression_match=False,
                checked_at=now_iso,
            )

    async def execute(
        self,
        envelope: AgentExecutionEnvelope,
        input_data: SuppressionCheckInput,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AgentExecutionEnvelope:
        # Step 1: Execute authoritative deterministic check
        det_result = self.check_suppression_deterministic(
            identifier=input_data.recipient_email,
            channel=input_data.channel,
            purpose=input_data.communication_purpose,
        )

        envelope.status = (
            ExecutionStatus.COMPLETED
            if det_result.decision == SuppressionDecision.ALLOW
            else (ExecutionStatus.BLOCKED if det_result.decision == SuppressionDecision.BLOCK else ExecutionStatus.FAILED)
        )
        envelope.output = det_result.model_dump()
        envelope.actions_executed = [
            ExecutedAction(
                action="suppression.gate_checked",
                status="CONFIRMED",
                details={"decision": det_result.decision.value, "match": det_result.suppression_match},
            )
        ]
        return envelope
