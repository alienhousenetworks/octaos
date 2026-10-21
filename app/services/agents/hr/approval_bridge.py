"""
Approval Bridge for HR Consequential Operations.
Integrates with the OctaOS Enterprise Approvals subsystem to enforce Human-in-the-Loop review.
"""
from typing import Dict, Any, Optional
import hashlib
import json
import logging
from sqlalchemy.orm import Session
from app.models.enterprise import ApprovalRequest
from app.services.agents.hr.schemas import RiskTier

logger = logging.getLogger(__name__)


class HRApprovalBridge:
    """Enforces human-in-the-loop authorization before any consequential HR action executes."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    @staticmethod
    def compute_payload_hash(action_type: str, payload: Dict[str, Any]) -> str:
        """Deterministic SHA-256 fingerprint of the exact proposed action and parameters."""
        canonical = json.dumps({"action": action_type, "payload": payload}, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def submit_for_approval(
        self,
        action_type: str,
        title: str,
        resource_id: Optional[str],
        payload: Dict[str, Any],
        rationale: str,
        requested_by: str,
        risk_tier: RiskTier = RiskTier.R3_MATERIAL,
        agent_name: str = "HR Universal Copilot"
    ) -> ApprovalRequest:
        """Creates an immutable approval request in the Enterprise Approvals queue."""
        payload_hash = self.compute_payload_hash(action_type, payload)

        # Check for existing pending approval with identical hash to prevent duplicates
        existing = self.db.query(ApprovalRequest).filter_by(
            tenant_id=self.tenant_id,
            action_type=action_type,
            resource_id=resource_id,
            status="pending"
        ).first()

        if existing:
            # Check if payload matches
            if existing.payload.get("_payload_sha256") == payload_hash:
                return existing

        enriched_payload = dict(payload)
        enriched_payload["_payload_sha256"] = payload_hash
        enriched_payload["_risk_tier"] = risk_tier.value
        enriched_payload["_rationale"] = rationale

        approval_req = ApprovalRequest(
            tenant_id=self.tenant_id,
            action_type=action_type,
            resource_type="hr_resource",
            resource_id=resource_id,
            title=title,
            payload=enriched_payload,
            confidence=0.95,
            status="pending",
            policy_reason=rationale,
            requested_by=requested_by,
            agent_name=agent_name
        )

        self.db.add(approval_req)
        self.db.commit()
        self.db.refresh(approval_req)
        logger.info(f"[HRApprovalBridge] Submitted approval request {approval_req.id} for action '{action_type}'")
        return approval_req

    def verify_authorization(self, approval_request_id: str, current_payload: Dict[str, Any]) -> bool:
        """
        Immediately prior to execution, confirms that:
        1. Request exists and is belonging to tenant.
        2. Status is explicitly 'approved'.
        3. The payload has not mutated since human approval was granted.
        """
        req = self.db.query(ApprovalRequest).filter_by(
            id=approval_request_id, tenant_id=self.tenant_id
        ).first()

        if not req:
            logger.warning(f"[HRApprovalBridge] Approval request {approval_request_id} not found.")
            return False

        if req.status != "approved":
            logger.warning(f"[HRApprovalBridge] Approval request {approval_request_id} status is '{req.status}', not 'approved'.")
            return False

        expected_hash = req.payload.get("_payload_sha256")
        current_hash = self.compute_payload_hash(req.action_type, current_payload)

        if expected_hash and current_hash != expected_hash:
            logger.error(f"[HRApprovalBridge] Payload mutation detected! Stored hash: {expected_hash}, Current hash: {current_hash}")
            return False

        return True
