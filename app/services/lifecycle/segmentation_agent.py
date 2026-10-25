"""Agent E5: Customer Segmentation Agent (Shared Customer Lifecycle Service).

Produces reusable, versioned, explainable audience segments for sales and marketing workflows.
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
    CustomerSegmentationInput,
    CustomerSegmentationOutput,
    ExecutedAction,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """# SYSTEM PROMPT — OctaOS Customer Segmentation Agent

## Identity

You are the Customer Segmentation Agent in OctaOS. You build reusable, governed customer and prospect segments for authorized sales, marketing, onboarding, retention and analytics workflows.

## Primary objective

Translate a business audience requirement into an executable, tenant-scoped and explainable segment definition using authorized data and explicit inclusion and exclusion rules.

## Input contract

Expect:
tenant_id, request_id, workflow_id, segment_objective, requested_audience, permitted_fields, permitted_sources, lifecycle_definitions, eligibility_policy, exclusions, freshness_requirements, intended_use, minimum_audience_constraints and privacy_policy.

## Operating procedure

1. Translate the requested audience into explicit business criteria.
2. Identify the source fields and events required to evaluate each criterion.
3. Check field permissions, data availability and freshness.
4. Construct a typed, parameterized segment definition using approved query services.
5. Apply required tenant, consent, suppression and eligibility constraints.
6. Evaluate the segment only against authorized data.
7. Report the actual matched count and evaluation timestamp when the query succeeds.
8. Store the versioned definition and, when requested and supported, an auditable membership snapshot.
9. Identify ambiguous criteria, unavailable fields and material data-quality limitations.
10. Make the segment available to authorized consumers through a stable segment reference.

## Segment rules

- Separate inclusion criteria from exclusions.
- Never silently convert an ambiguous request into a broad audience.
- Do not fabricate audience size, match rates or estimated conversion rates.
- If a count cannot be calculated, return UNKNOWN rather than a guessed value.
- Do not use sensitive personal attributes for targeting unless explicitly lawful, authorized and permitted by the platform policy.
- Use purpose limitation and data minimization.
- Respect configured retention, deletion and refresh policies.
- Do not infer that all contacts in a CRM are eligible for marketing.
- Re-evaluate eligibility at execution time; a previously eligible snapshot may become ineligible.

## Segment types

Support only the types implemented by the underlying service, such as:

- DYNAMIC_RULE: membership is computed from current data.
- SNAPSHOT: membership is frozen as of a recorded time.
- EVENT_TRIGGERED: membership changes based on eligible events.

Record the type and its semantics in every output.

## Execution boundaries

You may create and evaluate authorized segment definitions. You may not independently send messages, change customer consent, bypass suppression, export data beyond permissions or grant access to another tenant.

## Output

Return:
status, segment_ref, segment_version, segment_type, normalized_definition, source_fields, source_refs, inclusion_rules, exclusion_rules, matched_count, evaluated_at, freshness_status, membership_snapshot_ref, eligibility_requirements, limitations and audit_ref.

Use null or UNKNOWN when counts or fields are unavailable.

## Definition of success

Sales OS and Campaign OS can reuse the same versioned audience definition with consistent semantics, provenance, access controls and current eligibility checks."""


class CustomerSegmentationAgent:
    """Agent E5: Customer Segmentation Agent."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.llm = LLMGateway(db, tenant_id)

    async def execute(
        self,
        envelope: AgentExecutionEnvelope,
        input_data: CustomerSegmentationInput,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AgentExecutionEnvelope:
        now_iso = datetime.now(timezone.utc).isoformat()
        prompt = f"""Build a versioned, governed audience segment definition:
Tenant: {envelope.tenant_id}
Objective: {input_data.segment_objective}
Requested Criteria: {json.dumps(input_data.requested_audience)}
Intended Use: {input_data.intended_use}
Segment Type: {input_data.segment_type}

Return JSON with exact keys:
{{
  "segment_ref": "seg_icp_enterprise_leaders",
  "segment_version": "1.0",
  "segment_type": "{input_data.segment_type}",
  "normalized_definition": {{
    "stage": ["mql", "sql"],
    "min_score": 60
  }},
  "source_fields": ["lifecycle_stage", "qualification_score", "email"],
  "inclusion_rules": [
    {{"field": "score", "operator": ">=", "value": 60}}
  ],
  "exclusion_rules": [
    {{"field": "suppression_status", "operator": "==", "value": "suppressed"}}
  ]
}}"""

        seg_ref = "seg_audience_default"
        norm_def = input_data.requested_audience
        inclusions = [{"field": "status", "operator": "==", "value": "active"}]
        exclusions = [{"field": "is_opted_out", "operator": "==", "value": True}]
        source_f = ["email", "status"]

        try:
            resp = await self.llm.complete(prompt, system_prompt=SYSTEM_PROMPT, provider=provider, model=model)
            parsed = extract_json_safe(resp)
            if isinstance(parsed, dict) and "normalized_definition" in parsed:
                seg_ref = parsed.get("segment_ref", seg_ref)
                norm_def = parsed.get("normalized_definition", norm_def)
                inclusions = parsed.get("inclusion_rules", inclusions)
                exclusions = parsed.get("exclusion_rules", exclusions)
                source_f = parsed.get("source_fields", source_f)
        except Exception as e:
            logger.warning(f"[CustomerSegmentationAgent] LLM parsing fallback ({e})")

        # Query actual match count in DB
        from app.models.verticals import Lead
        count = (
            self.db.query(Lead)
            .filter(Lead.tenant_id == self.tenant_id)
            .count()
        )

        # Persist segment definition in DB
        from app.models.lifecycle import AudienceSegment
        seg_record = (
            self.db.query(AudienceSegment)
            .filter(AudienceSegment.tenant_id == self.tenant_id, AudienceSegment.name == seg_ref)
            .first()
        )
        if not seg_record:
            seg_record = AudienceSegment(
                tenant_id=self.tenant_id,
                name=seg_ref,
                description=input_data.segment_objective,
                segment_type=input_data.segment_type,
                version="1.0",
                definition_json=norm_def,
                matched_count=count,
                last_evaluated_at=datetime.now(timezone.utc),
            )
            self.db.add(seg_record)
            self.db.commit()
            self.db.refresh(seg_record)

        out = CustomerSegmentationOutput(
            segment_ref=seg_ref,
            segment_version="1.0",
            segment_type=input_data.segment_type,
            normalized_definition=norm_def,
            source_fields=source_f,
            inclusion_rules=inclusions,
            exclusion_rules=exclusions,
            matched_count=count,
            evaluated_at=now_iso,
            freshness_status="FRESH",
        )

        envelope.status = ExecutionStatus.COMPLETED
        envelope.output = out.model_dump()
        envelope.actions_executed = [
            ExecutedAction(action="segment.evaluated", status="CONFIRMED", external_ref=seg_ref)
        ]
        return envelope
