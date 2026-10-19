"""Enterprise Code-Level Policy Engine for the Autonomous Sales Organization (ASO).

Enforces deterministic business guardrails in pure Python code:
1. Autonomy Ladder Tiers: L0 (Suggest), L1 (Approve), L2 (Guardrailed Auto), L3 (Autonomous)
2. Pricing & Discount Limits (10% standard, 10-20% AE approval, >20% VP Sales veto)
3. International Privacy & Compliance (DPDP Act, GDPR, CAN-SPAM, TRAI WhatsApp opt-in)
4. Groundedness Thresholds (min 0.85 groundedness score against verified EvidenceRecords)
5. Frequency Limits & 3-Point Suppression
"""
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.services.sales_os.governance.policy_engine import SalesPolicyEngine
from app.services.sales_os.governance.suppression import SuppressionService

logger = logging.getLogger(__name__)


class PolicyDecision(BaseModel):
    status: str  # AUTO_APPROVED_L2 | APPROVAL_REQUIRED_L1 | ESCALATE_L0 | BLOCKED
    decision: str  # "auto_execute" | "queue_for_approval" | "blocked" (for backward compatibility)
    reason: str
    requires_approval: bool = False
    violations: List[str] = Field(default_factory=list)
    groundedness_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    canonical: str = ""
    rule_ids: List[str] = Field(default_factory=list)
    scope: str = "tenant"
    llm_may_override: bool = False

    @model_validator(mode="after")
    def bind_contract(self) -> "PolicyDecision":
        mapping = {
            "auto_execute": "allow",
            "allow": "allow",
            "blocked": "deny",
            "deny": "deny",
            "queue_for_approval": "require_approval",
            "require_approval": "require_approval",
        }
        self.canonical = mapping.get(self.decision, "require_approval")
        self.llm_may_override = False
        if not self.rule_ids:
            defaults = {
                "BLOCKED": ["policy.blocked"],
                "APPROVAL_REQUIRED_L1": ["policy.approval_required"],
                "ESCALATE_L0": ["pricing.discount_hard_cap"],
                "AUTO_APPROVED_L2": ["policy.authorized"],
            }
            self.rule_ids = defaults.get(self.status, ["policy.unspecified"])
        return self


class EnterpriseSalesPolicyEngine(SalesPolicyEngine):
    """Production-grade policy engine evaluating both commercial terms and outreach compliance."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, tenant_id)
        self.suppression = SuppressionService(db, tenant_id)

    def evaluate_pricing_and_discount(
        self,
        requested_discount_pct: float,
        deal_value_usd: float = 0.0,
        contract_term_months: int = 12,
        payment_terms: str = "Net 30",
    ) -> PolicyDecision:
        """Enforces commercial pricing caps and approval boundaries."""
        violations = []

        # Rule 1: Extreme Discount (> 20%) -> L0 Hard Veto / VP Sales Escalation
        if requested_discount_pct > 20.0:
            violations.append(f"Requested discount ({requested_discount_pct:.1f}%) exceeds hard ceiling of 20.0%")
            return PolicyDecision(
                status="ESCALATE_L0",
                decision="queue_for_approval",
                reason="Discount exceeds 20.0% hard cap. Level 0: Requires VP of Sales or CFO approval.",
                requires_approval=True,
                violations=violations,
                metadata={"requested_discount_pct": requested_discount_pct, "escalation_level": "VP_SALES"},
            )

        # Rule 2: Substantial Discount (10% < discount <= 20%) -> L1 Human AE Sign-off
        if requested_discount_pct > 10.0:
            return PolicyDecision(
                status="APPROVAL_REQUIRED_L1",
                decision="queue_for_approval",
                reason=f"Discount of {requested_discount_pct:.1f}% requires Level 1 Account Executive approval.",
                requires_approval=True,
                metadata={"requested_discount_pct": requested_discount_pct, "escalation_level": "AE"},
            )

        # Rule 3: Extended Payment Terms (Net 60 or Net 90) on short contracts
        if payment_terms.lower() in ("net 60", "net 90") and contract_term_months < 12:
            violations.append(f"Payment terms '{payment_terms}' require at least 12-month contract duration.")
            return PolicyDecision(
                status="APPROVAL_REQUIRED_L1",
                decision="queue_for_approval",
                reason=f"Extended payment terms '{payment_terms}' require Level 1 AE approval.",
                requires_approval=True,
                violations=violations,
            )

        # Rule 4: Within 10% standard band -> L2 Auto-Approved
        return PolicyDecision(
            status="AUTO_APPROVED_L2",
            decision="auto_execute",
            reason="Pricing and discount within authorized commercial limits.",
            requires_approval=False,
            metadata={"effective_discount_pct": requested_discount_pct},
        )

    def evaluate_communication_compliance(
        self,
        recipient_email: str,
        channel: str = "email",
        country: Optional[str] = None,
        content: str = "",
        groundedness_score: float = 1.0,
        is_enterprise_tier: bool = False,
        deal_room_id: Optional[str] = None,
        has_explicit_opt_in: bool = False,
    ) -> PolicyDecision:
        """Evaluates communication against international laws, suppression, and groundedness."""
        violations = []

        # 1. 3-Point Suppression Check
        is_supp, supp_reason = self.suppression.is_suppressed(email=recipient_email)
        if is_supp:
            violations.append(f"Recipient suppressed: {supp_reason}")
            return PolicyDecision(
                status="BLOCKED",
                decision="blocked",
                reason=f"Outreach blocked by suppression registry: {supp_reason}",
                requires_approval=False,
                violations=violations,
                rule_ids=["suppression.precedence"],
            )

        # 2. Frequency Limit Check
        freq_ok, freq_reason = self.suppression.check_frequency_limit(
            email=recipient_email, deal_room_id=deal_room_id
        )
        if not freq_ok:
            violations.append(f"Frequency limit exceeded: {freq_reason}")
            return PolicyDecision(
                status="BLOCKED",
                decision="blocked",
                reason=f"Outreach blocked: {freq_reason}",
                requires_approval=False,
                violations=violations,
            )

        # 3. Groundedness Gate (min 0.85 score)
        if groundedness_score < 0.85:
            violations.append(f"Groundedness score ({groundedness_score:.2f}) below threshold (0.85)")
            return PolicyDecision(
                status="APPROVAL_REQUIRED_L1",
                decision="queue_for_approval",
                reason=f"Groundedness score ({groundedness_score:.2f}) is below 0.85. Human review required to verify citations.",
                requires_approval=True,
                violations=violations,
                groundedness_score=groundedness_score,
            )

        # 4. Regional Jurisdictional Compliance
        c_code = (country or "").strip().upper()
        
        # India: DPDP Act + TRAI WhatsApp rules
        if c_code in ("IN", "INDIA") and channel == "whatsapp" and not has_explicit_opt_in:
            violations.append("TRAI / DPDP compliance: WhatsApp messaging requires verified prior opt-in.")
            return PolicyDecision(
                status="BLOCKED",
                decision="blocked",
                reason="WhatsApp dispatch to Indian recipient blocked: No verified prior opt-in found.",
                requires_approval=False,
                violations=violations,
            )

        # US CAN-SPAM: Must have opt-out instructions or unsubscribe tag
        if c_code in ("US", "USA", "UNITED STATES") and channel == "email" and content:
            lower_c = content.lower()
            if not any(k in lower_c for k in ("unsubscribe", "opt out", "reply stop", "remove")):
                violations.append("CAN-SPAM compliance: Missing clear opt-out / unsubscribe notice.")
                return PolicyDecision(
                    status="APPROVAL_REQUIRED_L1",
                    decision="queue_for_approval",
                    reason="CAN-SPAM check: Outbound email missing unsubscribe instructions. AE review required.",
                    requires_approval=True,
                    violations=violations,
                )

        # 5. Delegate to existing tenant autonomy mode policy check
        base_decision = self.evaluate_outreach_action(
            action_type="follow_up" if deal_room_id else "first_touch",
            deal_room_id=deal_room_id or "",
            recipient_email=recipient_email,
            content=content,
            groundedness_score=groundedness_score,
            is_enterprise_tier=is_enterprise_tier,
        )

        status = {
            "auto_execute": "AUTO_APPROVED_L2",
            "queue_for_approval": "APPROVAL_REQUIRED_L1",
            "blocked": "BLOCKED",
        }.get(base_decision["decision"], "APPROVAL_REQUIRED_L1")
        return PolicyDecision(
            status=status,
            decision=base_decision["decision"],
            reason=base_decision["reason"],
            requires_approval=base_decision["requires_approval"],
            groundedness_score=groundedness_score,
            rule_ids=list(base_decision.get("rule_ids") or []),
        )
