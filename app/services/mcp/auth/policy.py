"""Central authorization boundary and field-level policy kernel for MCP."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from app.models.mcp import SystemMCPCredential, CapabilityGrant
from app.services.policy_engine import PolicyEngine


class AuthorizationDecision:
    def __init__(
        self,
        allowed: bool,
        reason: Optional[str] = None,
        permitted_fields: Optional[List[str]] = None,
        denied_fields: Optional[List[str]] = None,
        requires_approval: bool = False,
        approval_id: Optional[str] = None,
    ):
        self.allowed = allowed
        self.reason = reason
        self.permitted_fields = permitted_fields or []
        self.denied_fields = denied_fields or []
        self.requires_approval = requires_approval
        self.approval_id = approval_id


class PolicyKernel:
    """
    Central Policy Boundary:
    Evaluates principal grants, action permissions, field-level allow/deny masks,
    and human-in-the-loop approval rules.
    """

    @staticmethod
    def authorize_action(
        db: Session,
        credential: SystemMCPCredential,
        connector_slug: str,
        object_name: str,
        action: str, # "discover", "read", "query", "create", "update", "delete", "invoke"
        payload_fields: Optional[Set[str]] = None,
    ) -> AuthorizationDecision:
        """
        Validates whether the credential has permission to execute the action on the target object.
        """
        # Super admin / Admin role override
        if credential.role in ("admin", "super_admin"):
            return AuthorizationDecision(
                allowed=True,
                permitted_fields=[],
                denied_fields=["password", "hashed_password", "encrypted_key"],
                requires_approval=False,
            )

        # Retrieve grants for this credential
        grants = (
            db.query(CapabilityGrant)
            .filter(
                CapabilityGrant.credential_id == credential.id,
                CapabilityGrant.tenant_id == credential.tenant_id,
            )
            .all()
        )

        matched_grant = None
        for g in grants:
            c_match = g.connector_slug in ("*", connector_slug)
            o_match = g.object_name in ("*", object_name)
            if c_match and o_match:
                actions = g.allowed_actions or []
                if "*" in actions or action in actions:
                    matched_grant = g
                    break

        if not matched_grant:
            return AuthorizationDecision(
                allowed=False,
                reason=f"Permission Denied: Credential '{credential.name}' lacks '{action}' grant on '{connector_slug}/{object_name}'.",
            )

        # Check field permissions for input payload (create/update)
        if payload_fields:
            denied = set(matched_grant.denied_fields or [])
            forbidden_attempted = payload_fields.intersection(denied)
            if forbidden_attempted:
                return AuthorizationDecision(
                    allowed=False,
                    reason=f"Permission Denied: Credential is not allowed to modify sensitive fields: {list(forbidden_attempted)}",
                )

            permitted = set(matched_grant.permitted_fields or [])
            if permitted:
                disallowed = payload_fields.difference(permitted)
                if disallowed:
                    return AuthorizationDecision(
                        allowed=False,
                        reason=f"Permission Denied: Fields not in permitted allowlist: {list(disallowed)}",
                    )

        # Check human approval requirement
        if matched_grant.requires_approval or action in ("delete", "invoke"):
            # Check tenant policy engine
            policy_engine = PolicyEngine(db, credential.tenant_id)
            eval_res = policy_engine.evaluate(
                action_type=f"mcp.{connector_slug}.{object_name}.{action}",
                agent_name=credential.name,
                requested_by=credential.user_id or credential.id,
            )
            decision = eval_res.get("decision", "allow_auto")
            if decision == "block":
                return AuthorizationDecision(
                    allowed=False,
                    reason=f"Action blocked by tenant policy: {eval_res.get('reason')}",
                )
            elif decision == "queue_approval" or matched_grant.requires_approval:
                return AuthorizationDecision(
                    allowed=True,
                    requires_approval=True,
                    approval_id=eval_res.get("approval_id"),
                    permitted_fields=matched_grant.permitted_fields,
                    denied_fields=matched_grant.denied_fields,
                )

        return AuthorizationDecision(
            allowed=True,
            permitted_fields=matched_grant.permitted_fields,
            denied_fields=matched_grant.denied_fields,
            requires_approval=False,
        )

    @staticmethod
    def redact_record(
        record: Dict[str, Any],
        permitted_fields: List[str],
        denied_fields: List[str],
    ) -> Dict[str, Any]:
        """
        Redacts denied fields or restricts to permitted fields in output data.
        Recursively scrubs sensitive fields from nested dictionaries.
        """
        if not isinstance(record, dict):
            return record

        denied_set = set(denied_fields or [])
        # Always redact low-level security fields
        denied_set.update({"password", "hashed_password", "otp", "encrypted_key"})

        permitted_set = set(permitted_fields) if permitted_fields else None

        redacted: Dict[str, Any] = {}
        for k, v in record.items():
            if k in denied_set:
                continue
            if permitted_set is not None and k not in permitted_set:
                continue

            if isinstance(v, dict):
                redacted[k] = PolicyKernel.redact_record(v, permitted_fields, denied_fields)
            elif isinstance(v, list):
                redacted[k] = [
                    PolicyKernel.redact_record(item, permitted_fields, denied_fields)
                    if isinstance(item, dict) else item
                    for item in v
                ]
            else:
                redacted[k] = v

        return redacted
