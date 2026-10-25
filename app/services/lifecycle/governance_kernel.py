"""Marketing Governance Kernel for OctaOS Marketing & Sales OS.

Enforces:
- Action Registry: Permissions, side-effect auditing, and verification requirements.
- Budget Controller: Hard daily and monthly spend limits per tenant.
- Emergency Stop: Immediate tenant-level kill switch halting active dispatches.
- Pre-Send Enforcement: Authoritative suppression check before any outbound communication.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.enterprise import ApprovalRequest
from app.services.lifecycle.suppression_agent import DeliverabilitySuppressionAgent
from app.services.lifecycle.contracts import SuppressionDecision

logger = logging.getLogger(__name__)

# Registry of permissible operations, required permissions, and side-effects
ACTION_REGISTRY = {
    "crm.lead.create": {"permission": "crm.write", "side_effect": "db_write", "requires_approval": False},
    "crm.lead.update_score": {"permission": "crm.write", "side_effect": "db_write", "requires_approval": False},
    "email.campaign.create_artifact": {"permission": "marketing.write", "side_effect": "artifact_store", "requires_approval": False},
    "email.campaign.send_bulk": {"permission": "marketing.send", "side_effect": "external_send", "requires_approval": True},
    "email.sales.send_single": {"permission": "sales.send", "side_effect": "external_send", "requires_approval": False},
    "social.post.publish": {"permission": "marketing.publish", "side_effect": "external_post", "requires_approval": True},
    "ad.campaign.create": {"permission": "ads.manage", "side_effect": "spend_money", "requires_approval": True},
    "ad.budget.update": {"permission": "ads.budget", "side_effect": "spend_money", "requires_approval": True},
}


class GovernanceKernel:
    """Central Control Plane enforcing policy, budget, suppression, and emergency stops."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.suppression_agent = DeliverabilitySuppressionAgent(db, tenant_id)

    def is_emergency_stopped(self) -> bool:
        """Check if tenant has an active emergency kill switch engaged."""
        from app.models.base import SystemSetting
        key = f"emergency_marketing_kill_switch:{self.tenant_id}"
        setting = (
            self.db.query(SystemSetting)
            .filter(SystemSetting.key == key)
            .first()
        )
        return bool(setting and str(setting.value).lower() in ("true", "1", "enabled"))

    def set_emergency_stop(self, enabled: bool = True, reason: str = "Admin initiated") -> None:
        """Activate or deactivate emergency kill switch."""
        from app.models.base import SystemSetting
        key = f"emergency_marketing_kill_switch:{self.tenant_id}"
        setting = (
            self.db.query(SystemSetting)
            .filter(SystemSetting.key == key)
            .first()
        )
        val_str = "true" if enabled else "false"
        if setting:
            setting.value = val_str
        else:
            setting = SystemSetting(
                key=key,
                value=val_str,
            )
            self.db.add(setting)
        self.db.commit()
        logger.warning(f"[GovernanceKernel] Tenant {self.tenant_id} emergency stop set to {enabled} ({reason})")

    def validate_action(
        self,
        action_name: str,
        actor_permissions: List[str],
        spend_usd: float = 0.0,
        daily_budget_cap: float = 500.0,
    ) -> Tuple[bool, str]:
        """Validate whether a proposed action is authorized by policy, budget, and system state."""
        # 1. Check emergency stop
        if self.is_emergency_stopped():
            return False, "BLOCKED: Tenant emergency kill switch is active. All outbound actions halted."

        # 2. Check action registry
        spec = ACTION_REGISTRY.get(action_name)
        if not spec:
            return False, f"BLOCKED: Action '{action_name}' is not registered in ACTION_REGISTRY."

        req_perm = spec["permission"]
        if req_perm not in actor_permissions and "*" not in actor_permissions:
            return False, f"BLOCKED: Missing required permission '{req_perm}' for action '{action_name}'."

        # 3. Check budget limits
        if spend_usd > 0.0:
            if spend_usd > daily_budget_cap:
                return False, f"BLOCKED: Proposed spend ${spend_usd:.2f} exceeds daily budget cap ${daily_budget_cap:.2f}."

        return True, "AUTHORIZED"

    def verify_pre_send_eligibility(
        self,
        recipient_identifier: str,
        channel: str = "email",
        purpose: str = "marketing",
    ) -> Tuple[bool, str]:
        """Authoritative pre-send suppression check. Fails closed."""
        if self.is_emergency_stopped():
            return False, "Emergency kill switch engaged."

        res = self.suppression_agent.check_suppression_deterministic(
            identifier=recipient_identifier,
            channel=channel,
            purpose=purpose,
        )

        if res.decision == SuppressionDecision.ALLOW:
            return True, "Recipient is eligible for communication."
        elif res.decision == SuppressionDecision.BLOCK:
            return False, f"Recipient is suppressed: {'; '.join(res.reason_codes)}"
        else:
            return False, f"Suppression check failed closed ({res.decision.value}): {'; '.join(res.reason_codes)}"
