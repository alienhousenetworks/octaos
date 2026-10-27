"""Human-in-the-loop policy engine for outbound / autonomous actions."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.enterprise import ApprovalRequest, TenantPolicy
from app.services.audit_service import AuditService
from app.services.runtime_governance.tool_policy import action_fingerprint

logger = logging.getLogger(__name__)

DEFAULT_ALWAYS_APPROVE = [
    "first_touch_email",
    "public_post",
    "price_quote",
    "refund",
    "linkedin_dm",
]


class PolicyEngine:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def get_or_create_policy(self) -> TenantPolicy:
        policy = (
            self.db.query(TenantPolicy)
            .filter(TenantPolicy.tenant_id == self.tenant_id)
            .first()
        )
        if not policy:
            policy = TenantPolicy(
                tenant_id=self.tenant_id,
                default_mode="draft_only",
                min_confidence=0.85,
                max_auto_amount=0.0,
                always_approve=list(DEFAULT_ALWAYS_APPROVE),
                support_refuse_if_not_in_kb=True,
            )
            self.db.add(policy)
            self.db.commit()
            self.db.refresh(policy)
        return policy

    def update_policy(self, updates: Dict[str, Any]) -> TenantPolicy:
        policy = self.get_or_create_policy()
        for key, value in updates.items():
            if hasattr(policy, key) and value is not None:
                setattr(policy, key, value)
        self.db.commit()
        self.db.refresh(policy)
        AuditService.log_event(
            self.db,
            action="policy.updated",
            tenant_id=self.tenant_id,
            resource="policy",
            details=updates,
        )
        return policy

    def evaluate(
        self,
        *,
        action_type: str,
        channel: Optional[str] = None,
        agent_name: Optional[str] = None,
        confidence: Optional[float] = None,
        amount: Optional[float] = None,
        brand_pass: bool = True,
        title: str = "",
        payload: Optional[Dict[str, Any]] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        requested_by: Optional[str] = None,
        action_binding: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Returns decision:
          allow_auto | queue_approval | block
        """
        policy = self.get_or_create_policy()
        payload = payload or {}

        # Kill switches
        channel_ks = policy.channel_kill_switches or {}
        agent_ks = policy.agent_kill_switches or {}
        if channel and channel_ks.get(channel):
            return self._block(f"Channel kill-switch active: {channel}")
        if agent_name and agent_ks.get(agent_name.lower().replace(" ", "_").replace(" ai", "")):
            return self._block(f"Agent kill-switch active: {agent_name}")
        # also check raw agent name
        if agent_name and agent_ks.get(agent_name):
            return self._block(f"Agent kill-switch active: {agent_name}")

        allowed = policy.allowed_channels or []
        if channel and allowed and channel not in allowed:
            return self._block(f"Channel not allowed: {channel}")

        always = policy.always_approve or DEFAULT_ALWAYS_APPROVE
        needs_approval = action_type in always or policy.default_mode == "draft_only"

        conf = confidence if confidence is not None else 0.0
        if policy.require_brand_pass and not brand_pass:
            needs_approval = True
            reason = "Brand language check failed"
        elif conf < (policy.min_confidence or 0.85):
            needs_approval = True
            reason = f"Confidence {conf:.2f} below min {policy.min_confidence}"
        elif amount is not None and amount > (policy.max_auto_amount or 0):
            needs_approval = True
            reason = f"Amount {amount} exceeds max auto {policy.max_auto_amount}"
        else:
            reason = "Within auto-send rules"

        if policy.default_mode == "auto_with_rules" and not needs_approval and action_type not in always:
            return {
                "decision": "allow_auto",
                "reason": reason,
                "approval_id": None,
            }

        binding = None
        binding_fingerprint = None
        policy_version = "1"
        if action_binding:
            required_binding_fields = {"run_id", "bot_id", "tool_name", "target", "payload"}
            if not required_binding_fields.issubset(action_binding):
                return self._block("Invalid action binding: run_id, bot_id, tool_name, target, and payload are required.")
            if not isinstance(action_binding.get("payload"), dict):
                return self._block("Invalid action binding payload.")
            policy_version = str(action_binding.get("policy_version") or "1")
            binding = {
                "run_id": str(action_binding["run_id"]),
                "bot_id": str(action_binding["bot_id"]),
                "tool_name": str(action_binding["tool_name"]),
                "target": str(action_binding["target"]),
                "payload": action_binding["payload"],
                "policy_version": policy_version,
            }
            binding_fingerprint = action_fingerprint(
                tenant_id=self.tenant_id,
                run_id=binding["run_id"],
                bot_id=binding["bot_id"],
                tool_name=binding["tool_name"],
                target=binding["target"],
                payload=binding["payload"],
                policy_version=policy_version,
            )

        approval = ApprovalRequest(
            tenant_id=self.tenant_id,
            action_type=action_type,
            channel=channel,
            agent_name=agent_name,
            resource_type=resource_type,
            resource_id=resource_id,
            title=title or f"Approve {action_type}",
            payload=payload,
            confidence=confidence,
            status="pending",
            policy_reason=reason if needs_approval else "Always requires approval",
            action_fingerprint=binding_fingerprint,
            action_binding=binding,
            policy_version=policy_version if binding else None,
            requested_by=requested_by,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
        )
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)

        AuditService.log_event(
            self.db,
            action="approval.queued",
            tenant_id=self.tenant_id,
            resource="approval",
            resource_id=approval.id,
            details={
                "action_type": action_type,
                "channel": channel,
            },
        )

        return {
            "decision": "queue_approval",
            "reason": approval.policy_reason,
            "approval_id": approval.id,
            "status": "pending",
        }

    def _block(self, reason: str) -> Dict[str, Any]:
        return {"decision": "block", "reason": reason, "approval_id": None}

    def review(
        self,
        approval_id: str,
        *,
        approve: bool,
        reviewer_id: str,
        note: Optional[str] = None,
    ) -> ApprovalRequest:
        approval = (
            self.db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.id == approval_id,
                ApprovalRequest.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not approval:
            raise ValueError("Approval not found")
        if approval.status != "pending":
            raise ValueError(f"Approval already {approval.status}")
        binding_tool = str((approval.action_binding or {}).get("tool_name") or approval.action_type)
        from app.services.runtime_governance.tool_policy import HIGH_RISK_ACTION_PREFIXES
        if approve and any(binding_tool == prefix or binding_tool.startswith(prefix) for prefix in HIGH_RISK_ACTION_PREFIXES):
            if not approval.action_fingerprint or not approval.action_binding:
                raise ValueError("High-risk approval requires a persisted exact action binding; edit/recreate the approval with one.")

        approval.status = "approved" if approve else "rejected"
        # Fingerprints are immutable after review; any edit must create a new approval.
        approval.reviewed_by = reviewer_id
        approval.review_note = note
        approval.reviewed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(approval)

        # Execute side-effects for linked resources upon approval/rejection
        try:
            if approval.resource_type in ["post", "content_post"] or approval.action_type == "public_post":
                from app.models.verticals import ContentPost
                post_id = approval.resource_id or (approval.payload or {}).get("post_id")
                if post_id:
                    post = self.db.query(ContentPost).filter_by(id=post_id, tenant_id=self.tenant_id).first()
                    if post:
                        post.approval_status = "approved" if approve else "rejected"
                        if not approve:
                            post.status = "draft"
                        self.db.commit()
            elif approval.resource_type == "lead":
                from app.models.verticals import Lead
                lead_id = approval.resource_id or (approval.payload or {}).get("lead_id")
                if lead_id:
                    lead = self.db.query(Lead).filter_by(id=lead_id, tenant_id=self.tenant_id).first()
                    if lead:
                        lead.approval_status = "approved" if approve else "rejected"
                        self.db.commit()
        except Exception as e:
            logger.warning(f"Error applying side-effects for approval {approval_id}: {e}")

        AuditService.log_event(
            self.db,
            action="approval.reviewed",
            tenant_id=self.tenant_id,
            user_id=reviewer_id,
            resource="approval",
            resource_id=approval_id,
            details={
                "status": approval.status,
                "note": note,
            },
        )
        return approval

    def list_pending(self, limit: int = 50):
        return (
            self.db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.tenant_id == self.tenant_id,
                ApprovalRequest.status == "pending",
            )
            .order_by(ApprovalRequest.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_approvals(
        self,
        status: Optional[str] = "pending",
        action_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[ApprovalRequest]:
        q = self.db.query(ApprovalRequest).filter(ApprovalRequest.tenant_id == self.tenant_id)
        if status and status.lower() != "all":
            q = q.filter(ApprovalRequest.status == status.lower())
        if action_type and action_type.lower() != "all":
            q = q.filter(ApprovalRequest.action_type == action_type.lower())
        return q.order_by(ApprovalRequest.created_at.desc()).limit(limit).all()

    def get_metrics(self) -> Dict[str, int]:
        total = self.db.query(ApprovalRequest).filter(ApprovalRequest.tenant_id == self.tenant_id).count()
        pending = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.tenant_id == self.tenant_id,
            ApprovalRequest.status == "pending"
        ).count()
        approved = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.tenant_id == self.tenant_id,
            ApprovalRequest.status == "approved"
        ).count()
        rejected = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.tenant_id == self.tenant_id,
            ApprovalRequest.status == "rejected"
        ).count()
        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
        }
