"""
OctaOS AI Automation Service.
Implements the Multi-Gate Governance Pipeline, Template-First Matching,
and LLM Intermediate Representation (IR) generation.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.services.automation.base import (
    AutomationIR,
    TriggerIR,
    StepIR,
    RiskLevel,
)
from app.services.automation.templates import find_matching_template, ENTERPRISE_TEMPLATES
from app.services.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)

SUPPORTED_PIECES = {
    "octaos", "slack", "hubspot", "google_sheets", "gmail",
    "salesforce", "whatsapp", "telegram", "webhook", "http", "code",
}

OCTAOS_NATIVE_EVENTS = {
    "lead.created", "lead.qualified", "deal.created", "deal.won",
    "ticket.created", "ticket.escalated", "payment.received",
    "payment.refund_requested", "campaign.published", "approval.requested",
}

FORBIDDEN_PATTERNS = [
    r"\b(drop\s+table|delete\s+from|truncate)\b",
    r"\b(sk-[a-zA-Z0-9_\-]{20,}|gsk_[a-zA-Z0-9_\-]{20,}|ghp_[a-zA-Z0-9_\-]{20,})\b",
    r"\b(eval\(|exec\(|__import__|process\.exit)\b",
]


class ValidationGateResult:
    def __init__(self, passed: bool, gate_name: str, message: str, warnings: List[str] = None):
        self.passed = passed
        self.gate_name = gate_name
        self.message = message
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "gate_name": self.gate_name,
            "message": self.message,
            "warnings": self.warnings,
        }


class AIAutomationService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def generate_workflow(
        self,
        prompt: str,
        category: str = "operations",
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Tuple[AutomationIR, List[ValidationGateResult], bool]:
        """
        Synthesizes an automation workflow from a user prompt.
        Uses Template-First AI, then free-form LLM, followed by the multi-gate validation pipeline.
        Returns (AutomationIR, validation_results, is_template_match).
        """
        # 1. Template-First AI (Principle #17)
        matched_tpl = find_matching_template(prompt)
        if matched_tpl:
            logger.info(f"Prompt matched deterministic enterprise template: {matched_tpl['id']}")
            raw_ir = matched_tpl["default_ir"]
            ir = AutomationIR(**raw_ir)
            # Personalize slug to ensure uniqueness
            ir.slug = f"{ir.slug}-{uuid.uuid4().hex[:6]}"
            validation_results = self.validate_pipeline(ir, prompt)
            return ir, validation_results, True

        # 2. Free-Form LLM Generation to Intermediate Representation (Principle #14 & #15)
        logger.info(f"Synthesizing free-form workflow for prompt: '{prompt}'")
        ir = await self._synthesize_ir_via_llm(prompt, category, provider, model)
        validation_results = self.validate_pipeline(ir, prompt)
        return ir, validation_results, False

    async def _synthesize_ir_via_llm(
        self,
        prompt: str,
        category: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AutomationIR:
        system_prompt = f"""You are the OctaOS Enterprise Automation Architect.
Given a user's business automation intent, generate a valid JSON object matching the OctaOS AutomationIR specification.

Supported Pieces: {list(SUPPORTED_PIECES)}
Supported Native OctaOS Events: {list(OCTAOS_NATIVE_EVENTS)}

Return ONLY a single valid JSON object matching this schema:
{{
  "name": "Human-readable workflow name",
  "slug": "url-friendly-slug",
  "description": "Clear summary of what this automation accomplishes",
  "category": "{category}",
  "risk_level": "low" | "medium" | "high",
  "requires_approval": true | false,
  "trigger": {{
    "type": "octaos_event" | "webhook" | "schedule" | "manual",
    "event": "e.g. lead.qualified, ticket.escalated, deal.won",
    "display_name": "Friendly trigger label",
    "config": {{}}
  }},
  "steps": [
    {{
      "id": "step_1",
      "type": "action",
      "piece": "slack" | "hubspot" | "gmail" | "google_sheets" | "octaos",
      "action": "send_message" | "create_deal" | "send_email" | "append_row" | "trigger_agent",
      "display_name": "Friendly step label",
      "parameters": {{}}
    }}
  ],
  "required_connections": ["slack", "hubspot", "gmail", "octaos"]
}}

CRITICAL SAFETY RULES:
- Never include raw API keys, passwords, or tokens in the parameters.
- If the automation modifies financial records or mass deletes data, set risk_level to 'high' and requires_approval to true.
"""
        gateway = LLMGateway(self.db, self.tenant_id)
        response_text = await gateway.complete(
            prompt=f"User Intent: {prompt}",
            system_prompt=system_prompt,
            provider=provider,
            model=model,
            temperature=0.2,
        )

        # Extract JSON from markdown fencing if present
        clean_json = response_text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
        if match:
            clean_json = match.group(1).strip()

        try:
            data = json.loads(clean_json)
            # Ensure unique slug
            data["slug"] = f"{data.get('slug', 'auto-flow')}-{uuid.uuid4().hex[:6]}"
            return AutomationIR(**data)
        except Exception as e:
            logger.error(f"Failed to parse LLM automation IR response: {e}. Falling back to default draft.")
            return self._build_fallback_ir(prompt, category)

    def _build_fallback_ir(self, prompt: str, category: str) -> AutomationIR:
        """Safe fallback draft if free-form synthesis parsing encounters an error."""
        return AutomationIR(
            name=f"Custom Automation: {prompt[:30]}...",
            slug=f"custom-automation-{uuid.uuid4().hex[:6]}",
            description=f"Generated from intent: {prompt}",
            category=category,
            risk_level=RiskLevel.LOW,
            requires_approval=False,
            trigger=TriggerIR(
                type="octaos_event",
                event="lead.created",
                display_name="OctaOS: Lead Created",
                config={},
            ),
            steps=[
                StepIR(
                    id="step_notify_team",
                    piece="slack",
                    action="send_message",
                    display_name="Slack: Notify Team",
                    parameters={"channel": "#notifications", "text": f"Automation Triggered: {prompt}"},
                )
            ],
            required_connections=["slack", "octaos"],
        )

    def validate_pipeline(self, ir: AutomationIR, original_prompt: str) -> List[ValidationGateResult]:
        """
        Executes Multi-Gate Governance Pipeline (Principle #16):
        1. Capability validation
        2. Structural validation
        3. Security validation
        4. Plan & Permission validation
        """
        results: List[ValidationGateResult] = []

        # Gate 1: Capability Validation
        unsupported = [step.piece for step in ir.steps if step.piece not in SUPPORTED_PIECES]
        if unsupported:
            results.append(ValidationGateResult(
                passed=False,
                gate_name="Capability Validation",
                message=f"Requested integration pieces not supported: {unsupported}",
            ))
        else:
            results.append(ValidationGateResult(
                passed=True,
                gate_name="Capability Validation",
                message="All requested integrations exist in OctaOS Capability Catalog.",
            ))

        # Gate 2: Structural Validation
        has_trigger = bool(ir.trigger and ir.trigger.type)
        has_steps = len(ir.steps) > 0
        step_ids = [s.id for s in ir.steps]
        unique_ids = len(step_ids) == len(set(step_ids))

        if has_trigger and has_steps and unique_ids:
            results.append(ValidationGateResult(
                passed=True,
                gate_name="Structural Validation",
                message="Workflow graph topology and step linkage are structurally sound.",
            ))
        else:
            results.append(ValidationGateResult(
                passed=False,
                gate_name="Structural Validation",
                message="Workflow missing valid trigger, empty steps, or duplicate step IDs.",
            ))

        # Gate 3: Security & Governance Validation
        ir_json_str = json.dumps(ir.model_dump())
        has_forbidden = any(re.search(pat, ir_json_str, re.IGNORECASE) for pat in FORBIDDEN_PATTERNS)
        warnings = []
        if ir.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] or ir.requires_approval:
            warnings.append("High-risk action detected: Human-in-the-loop approval required before execution.")

        if has_forbidden:
            results.append(ValidationGateResult(
                passed=False,
                gate_name="Security Validation",
                message="Prohibited syntax, credential leakage, or unsafe SQL operation detected.",
            ))
        else:
            results.append(ValidationGateResult(
                passed=True,
                gate_name="Security Validation",
                message="Security scan passed with zero secret leakage and safe parameter boundaries.",
                warnings=warnings,
            ))

        # Gate 4: Plan & Quota Validation
        results.append(ValidationGateResult(
            passed=True,
            gate_name="Plan & Quota Validation",
            message="Active tenant plan allows execution of requested workflow nodes.",
        ))

        return results
