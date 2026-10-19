"""Policy enforcement and authorization engine for knowledge connectors."""
from __future__ import annotations

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.knowledge_connectors import KnowledgeConnector, ConnectorPermission
from app.services.knowledge_connectors.contracts import ExecutionContext
from app.services.knowledge_connectors.errors import (
    ConnectorNotFoundError,
    ConnectorPermissionDeniedError,
    ConnectorSecurityError,
)


class ConnectorPolicyDecision:
    def __init__(
        self,
        allowed: bool,
        reason: Optional[str] = None,
        permitted_fields: Optional[List[str]] = None,
        denied_fields: Optional[List[str]] = None,
        requires_approval: bool = False,
    ):
        self.allowed = allowed
        self.reason = reason
        self.permitted_fields = permitted_fields or []
        self.denied_fields = denied_fields or []
        self.requires_approval = requires_approval


class ConnectorPolicyEngine:
    """Central authority evaluating tenant boundaries, agent grants, and field policies."""

    @staticmethod
    def evaluate(
        db: Session,
        connector: KnowledgeConnector,
        context: ExecutionContext,
        operation: str = "read",
        is_test_execution: bool = False,
    ) -> ConnectorPolicyDecision:
        # 1. Strict Tenant Boundary Isolation
        if connector.tenant_id != context.tenant_id:
            raise ConnectorNotFoundError(connector.id, context.tenant_id)

        # 2. Lifecycle State Gate
        if not is_test_execution:
            if connector.state != "active":
                return ConnectorPolicyDecision(
                    allowed=False,
                    reason=f"Connector '{connector.name}' is in '{connector.state}' state (not active).",
                )
        else:
            # During test execution, states draft, testing, or active are permitted
            if connector.state not in ("draft", "testing", "active", "degraded"):
                return ConnectorPolicyDecision(
                    allowed=False,
                    reason=f"Cannot test connector in state '{connector.state}'.",
                )

        # 3. If acting_agent_id or department is specified, check ConnectorPermission
        permissions = db.query(ConnectorPermission).filter(
            ConnectorPermission.connector_id == connector.id,
        ).all()

        if not permissions:
            # Default allow for tenant agents in same department or general if no specific permission rows
            return ConnectorPolicyDecision(allowed=True)

        # Check matching grants
        matching = []
        for p in permissions:
            dept_match = p.department.lower() in ("general", context.department.lower(), "*")
            agent_match = (p.agent_id is None) or (p.agent_id == context.acting_agent_id)
            if dept_match and agent_match:
                matching.append(p)

        if not matching:
            return ConnectorPolicyDecision(
                allowed=False,
                reason=f"Agent '{context.acting_agent_id}' (dept: {context.department}) has no grant for connector '{connector.name}'.",
            )

        # Aggregate allowed operations and fields
        combined_permitted: List[str] = []
        combined_denied: List[str] = []
        requires_approval = False

        for p in matching:
            allowed_ops = [op.lower() for op in (p.allowed_operations or ["read"])]
            if operation.lower() not in allowed_ops and "*" not in allowed_ops:
                continue
            if p.permitted_fields:
                combined_permitted.extend(p.permitted_fields)
            if p.denied_fields:
                combined_denied.extend(p.denied_fields)
            if p.requires_human_approval:
                requires_approval = True

        return ConnectorPolicyDecision(
            allowed=True,
            permitted_fields=list(set(combined_permitted)),
            denied_fields=list(set(combined_denied)),
            requires_approval=requires_approval,
        )
