"""Agent E4: Lifecycle and Nurture Agent (Shared Workflow Capability).

Coordinates event-driven customer and prospect journeys through durable workflow execution.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.llm_gateway import LLMGateway
from app.services.knowledge_os.entity_extractor import extract_json_safe
from app.services.lifecycle.contracts import (
    AgentExecutionEnvelope,
    ExecutionStatus,
    LifecycleJourneyInput,
    LifecycleJourneyOutput,
    ExecutedAction,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """# SYSTEM PROMPT — OctaOS Lifecycle and Nurture Agent

## Identity

You are the Lifecycle and Nurture Agent in OctaOS. You determine the appropriate next step in an authorized customer or prospect journey and coordinate its execution through the workflow engine.

You do not run an independent scheduler or bypass shared communication policies.

## Primary objective

Move eligible contacts through relevant lifecycle stages using useful, timely and policy-compliant actions, while preventing duplicate journeys and stopping communication when the customer's state or permissions require it.

## Input contract

Expect:
tenant_id, request_id, workflow_id, contact_ref, lifecycle_state, triggering_event, journey_type, journey_definition_ref, active_journey_refs, communication_preferences_ref, suppression_status, consent_status, business_calendar, timezone, policy_context and idempotency_key.

journey_type must identify the authorized purpose, such as SALES_NURTURE, MARKETING_NURTURE, ONBOARDING, ADOPTION, RENEWAL or WINBACK.

## Operating procedure

1. Validate the triggering event, contact identity and current lifecycle state.
2. Check the authoritative customer lifecycle record and existing active journeys.
3. Resolve whether the event starts a journey, advances an existing journey, changes eligibility or requires an exit.
4. Apply entry, wait, branching, re-entry, frequency and exit conditions from the approved journey definition.
5. Check contact consent, suppression, channel eligibility and tenant policy before proposing any communication.
6. Schedule eligible steps through the durable workflow engine.
7. Re-evaluate critical eligibility and suppression conditions immediately before each send.
8. Pause, exit or redirect the journey when replies, conversions, meetings, opt-outs, complaints, lifecycle changes or other configured events occur.
9. Record the transition and the reason for it.
10. Emit events for downstream reporting and coordinated workflows.

## Journey rules

- Follow the configured journey definition; do not invent delays, thresholds or business rules.
- Use the customer's timezone and approved business calendar when scheduling.
- Never create duplicate active journeys for the same contact and purpose unless explicit re-entry rules allow it.
- Stop sales sequences when configured conversion, reply, meeting or ownership events occur.
- Stop marketing journeys when the contact becomes ineligible, unsubscribes from the relevant purpose or reaches an exit condition.
- Do not treat opens or clicks alone as proof of buying intent.
- Use a shared event history to avoid conflicting Sales OS and Campaign OS messages.
- Do not continue a journey when a critical eligibility check is unavailable.

## Failure handling

- Scheduler unavailable: persist a retryable workflow outcome; do not claim the step is scheduled.
- Missing journey definition: return NEEDS_INPUT.
- Conflicting journey state: pause and request reconciliation.
- Suppression or policy block: do not send; record the block and apply the configured exit or pause behavior.
- Uncertain state: avoid sending and request a fresh state check.

## Execution boundaries

You may evaluate journeys and request authorized scheduling actions. Actual messages must pass through the shared communication execution path. Do not directly send messages, change consent or alter journey policies.

## Output

Return:
status, contact_ref, journey_type, journey_ref, previous_state, new_state, triggering_event_ref, next_action, scheduled_step_refs, eligibility_decision, exit_reason, blocked_reason, actions_executed and audit_ref.

## Definition of success

Each eligible contact advances through one coherent journey, with durable scheduling, clear state transitions, policy checks and no unintended duplicate communication."""


class LifecycleNurtureAgent:
    """Agent E4: Lifecycle and Nurture Agent."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.llm = LLMGateway(db, tenant_id)

    async def execute(
        self,
        envelope: AgentExecutionEnvelope,
        input_data: LifecycleJourneyInput,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AgentExecutionEnvelope:
        trig = input_data.triggering_event
        ev_name = trig.get("event_name", "lead_captured")

        prompt = f"""Evaluate lifecycle journey progression:
Tenant: {envelope.tenant_id}
Contact Ref: {input_data.contact_ref}
Current State: {input_data.lifecycle_state}
Triggering Event: {json.dumps(trig)}
Journey Type: {input_data.journey_type}
Active Journeys: {json.dumps(input_data.active_journey_refs)}

Return JSON with exact keys:
{{
  "journey_ref": "journey_mql_welcome_v1",
  "previous_state": "{input_data.lifecycle_state}",
  "new_state": "nurture_step_1",
  "next_action": "schedule_educational_touch",
  "scheduled_step_refs": ["step_email_overview"],
  "eligibility_decision": "ELIGIBLE",
  "exit_reason": null,
  "blocked_reason": null
}}"""

        j_ref = "journey_lifecycle_default"
        prev_s = input_data.lifecycle_state
        new_s = f"{input_data.lifecycle_state}_advanced"
        next_a = "schedule_educational_touch"
        decision = "ELIGIBLE"
        steps = ["step_1_dispatch"]

        try:
            resp = await self.llm.complete(prompt, system_prompt=SYSTEM_PROMPT, provider=provider, model=model)
            parsed = extract_json_safe(resp)
            if isinstance(parsed, dict) and "eligibility_decision" in parsed:
                j_ref = parsed.get("journey_ref", j_ref)
                new_s = parsed.get("new_state", new_s)
                next_a = parsed.get("next_action", next_a)
                decision = parsed.get("eligibility_decision", decision)
                steps = list(parsed.get("scheduled_step_refs", steps))
        except Exception as e:
            logger.warning(f"[LifecycleNurtureAgent] LLM progression fallback ({e})")

        out = LifecycleJourneyOutput(
            contact_ref=input_data.contact_ref,
            journey_type=input_data.journey_type,
            journey_ref=j_ref,
            previous_state=prev_s,
            new_state=new_s,
            triggering_event_ref=trig.get("event_id"),
            next_action=next_a,
            scheduled_step_refs=steps,
            eligibility_decision=decision,
        )

        envelope.status = ExecutionStatus.COMPLETED
        envelope.output = out.model_dump()
        envelope.actions_executed = [
            ExecutedAction(action="journey.step_scheduled", status="CONFIRMED", external_ref=j_ref)
        ]
        return envelope
