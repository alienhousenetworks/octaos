"""
Risk Classifier for HR Agentic Operations.
Categorizes actions into R0-R5 risk tiers and determines mandatory approval requirements.
"""
from typing import Dict, Any, Tuple
from app.services.agents.hr.schemas import RiskTier, AutonomyLevel


# Deterministic mapping of action types to baseline risk tiers
ACTION_RISK_MAP: Dict[str, Tuple[RiskTier, AutonomyLevel, bool]] = {
    # R0 - Read-only queries
    "policy.query": (RiskTier.R0_READ_ONLY, AutonomyLevel.L0_INFORMATIONAL, False),
    "employee.view": (RiskTier.R0_READ_ONLY, AutonomyLevel.L0_INFORMATIONAL, False),
    "analytics.view": (RiskTier.R0_READ_ONLY, AutonomyLevel.L0_INFORMATIONAL, False),
    "leave.check_balance": (RiskTier.R0_READ_ONLY, AutonomyLevel.L0_INFORMATIONAL, False),
    "roster.view": (RiskTier.R0_READ_ONLY, AutonomyLevel.L0_INFORMATIONAL, False),

    # R1 - Low impact drafts
    "outreach.draft": (RiskTier.R1_LOW_IMPACT, AutonomyLevel.L1_SUGGESTIVE, False),
    "review.synthesize": (RiskTier.R1_LOW_IMPACT, AutonomyLevel.L1_SUGGESTIVE, False),
    "leave.simulate_coverage": (RiskTier.R1_LOW_IMPACT, AutonomyLevel.L1_SUGGESTIVE, False),
    "roster.propose_schedule": (RiskTier.R1_LOW_IMPACT, AutonomyLevel.L1_SUGGESTIVE, False),
    "document.draft": (RiskTier.R1_LOW_IMPACT, AutonomyLevel.L1_SUGGESTIVE, False),

    # R2 - Reversible routine actions within bounds
    "leave.request_submit": (RiskTier.R2_REVERSIBLE, AutonomyLevel.L2_BOUNDED_EXECUTION, False),
    "attendance.punch": (RiskTier.R2_REVERSIBLE, AutonomyLevel.L2_BOUNDED_EXECUTION, False),
    "ticket.create": (RiskTier.R2_REVERSIBLE, AutonomyLevel.L2_BOUNDED_EXECUTION, False),
    "notification.send_reminder": (RiskTier.R2_REVERSIBLE, AutonomyLevel.L2_BOUNDED_EXECUTION, False),

    # R3 - Material actions (Requires Approval)
    "leave.approve": (RiskTier.R3_MATERIAL, AutonomyLevel.L3_APPROVAL_GATED, True),
    "leave.reject": (RiskTier.R3_MATERIAL, AutonomyLevel.L3_APPROVAL_GATED, True),
    "roster.publish": (RiskTier.R3_MATERIAL, AutonomyLevel.L3_APPROVAL_GATED, True),
    "attendance.correct": (RiskTier.R3_MATERIAL, AutonomyLevel.L3_APPROVAL_GATED, True),
    "contract.dispatch": (RiskTier.R3_MATERIAL, AutonomyLevel.L3_APPROVAL_GATED, True),
    "policy.publish": (RiskTier.R3_MATERIAL, AutonomyLevel.L3_APPROVAL_GATED, True),

    # R4 - High consequence (Mandatory authorized human decision; AI cannot independently decide)
    "employee.terminate": (RiskTier.R4_HIGH_CONSEQUENCE, AutonomyLevel.L4_RESTRICTED, True),
    "discipline.issue_pip": (RiskTier.R4_HIGH_CONSEQUENCE, AutonomyLevel.L4_RESTRICTED, True),
    "compensation.modify_salary": (RiskTier.R4_HIGH_CONSEQUENCE, AutonomyLevel.L4_RESTRICTED, True),
    "candidate.reject_final": (RiskTier.R4_HIGH_CONSEQUENCE, AutonomyLevel.L4_RESTRICTED, True),

    # R5 - Prohibited autonomy
    "retaliation.action": (RiskTier.R5_PROHIBITED, AutonomyLevel.L4_RESTRICTED, True),
    "whistleblower.de_anonymize": (RiskTier.R5_PROHIBITED, AutonomyLevel.L4_RESTRICTED, True),
}


class HRRiskClassifier:
    """Classifies risk tiers and enforces approval prerequisites."""

    @staticmethod
    def classify_action(action_type: str, payload: Dict[str, Any] = None) -> Tuple[RiskTier, AutonomyLevel, bool]:
        """
        Returns (risk_tier, autonomy_level, requires_human_approval).
        Defaults to R3 (Material) if unknown to ensure strict safety.
        """
        normalized = (action_type or "").strip().lower()
        if normalized in ACTION_RISK_MAP:
            return ACTION_RISK_MAP[normalized]
        
        # Check for keywords that elevate risk dynamically
        if any(w in normalized for w in ["terminate", "fire", "salary", "pay", "pip", "discipline", "dismiss"]):
            return (RiskTier.R4_HIGH_CONSEQUENCE, AutonomyLevel.L4_RESTRICTED, True)

        # Conservative fallback: treat unmapped writes as requiring approval
        return (RiskTier.R3_MATERIAL, AutonomyLevel.L3_APPROVAL_GATED, True)
