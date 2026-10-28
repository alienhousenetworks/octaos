"""Result-to-Execution Bridge: Validates external AI proposals, evaluates policy, and records verified execution evidence."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.models.collaborative_workforce import AgentMessage, DelegationReceipt
from app.models.enterprise import ApprovalRequest
from app.services.audit_service import AuditService
from app.services.collaboration.contracts import ExecutionBridgeRequest, ExecutionBridgeResponse
from app.services.policy_engine import PolicyEngine

logger = logging.getLogger(__name__)


class ExecutionBridge:
    """
    Enforces that external AI proposals, findings, or code are NEVER treated as executed work
    until validated against security policy, executed in a governed tool, and evidenced.
    """

    @classmethod
    async def process_proposed_action(
        cls,
        db: Session,
        tenant_id: str,
        request: ExecutionBridgeRequest,
        mcp_credential: Any,
    ) -> ExecutionBridgeResponse:
        from app.services.mcp.server import mcp_server

        # 1. Bind execution to the authenticated tenant and a durable collaboration receipt.
        # Never allow the bridge to become a general-purpose tool execution endpoint.
        credential_tenant = getattr(mcp_credential, "tenant_id", None)
        if not tenant_id or (credential_tenant and str(credential_tenant) != str(tenant_id)):
            return ExecutionBridgeResponse(
                task_id=request.task_id,
                status="blocked",
                verified=False,
                policy_decision="block",
                error="Execution bridge tenant does not match the authenticated credential.",
            )

        receipt = db.query(DelegationReceipt).filter_by(
            tenant_id=tenant_id, task_id=request.task_id
        ).first()
        if receipt is None:
            AuditService.log_event(
                db=db,
                action="execution_bridge.blocked_missing_receipt",
                tenant_id=tenant_id,
                resource="collaboration_bridge",
                resource_id=request.task_id,
                details={"tool": request.proposed_tool, "reason": "No tenant-scoped collaboration receipt"},
            )
            return ExecutionBridgeResponse(
                task_id=request.task_id,
                status="blocked",
                verified=False,
                policy_decision="block",
                error="A valid collaboration task receipt is required before executing a proposed action.",
            )

        policy_engine = PolicyEngine(db, tenant_id)

        # 2. Evaluate Policy & Human-in-the-Loop gates
        eval_result = policy_engine.evaluate(
            action_type=request.action_type or request.proposed_tool,
            title=f"Collaboration Execution Bridge: {request.proposed_tool}",
            payload={"tool": request.proposed_tool, "arguments": request.arguments, "intent": request.intent_description},
            resource_type="collaboration_task",
            resource_id=request.task_id,
            requested_by="execution_bridge",
        )

        decision = eval_result.get("decision", "allow_auto")
        reason = eval_result.get("reason", "")
        approval_id = eval_result.get("approval_id")

        # Credential role authorizes access to the bridge; it must never override
        # policy-engine approval requirements. Approval is a separate governance decision.

        now_iso = datetime.now(timezone.utc).isoformat()

        # A. Blocked by Policy
        if decision == "block":
            AuditService.log_event(
                db=db,
                action="execution_bridge.blocked",
                tenant_id=tenant_id,
                resource="collaboration_bridge",
                resource_id=request.task_id,
                details={"tool": request.proposed_tool, "reason": reason},
            )
            return ExecutionBridgeResponse(
                task_id=request.task_id,
                status="blocked",
                verified=False,
                policy_decision="block",
                error=f"Policy Block: {reason}",
            )

        # B. Gated by Human Approval
        if decision == "queue_approval" or approval_id:
            # Update receipt status to waiting_approval
            if receipt:
                receipt.status = "waiting_approval"
                evidence_list = list(receipt.evidence or [])
                evidence_list.append({
                    "stage": "policy_gate",
                    "status": "waiting_approval",
                    "approval_id": approval_id,
                    "reason": reason,
                    "timestamp": now_iso,
                })
                receipt.evidence = evidence_list
                db.commit()

            AuditService.log_event(
                db=db,
                action="execution_bridge.queued_approval",
                tenant_id=tenant_id,
                resource="collaboration_bridge",
                resource_id=request.task_id,
                details={"tool": request.proposed_tool, "approval_id": approval_id, "reason": reason},
            )
            return ExecutionBridgeResponse(
                task_id=request.task_id,
                status="waiting_approval",
                verified=False,
                policy_decision="queue_approval",
                approval_request_id=approval_id,
                evidence={"approval_required": True, "reason": reason},
            )

        # C. Authorized: Execute via Governed Tool Registry
        try:
            tool_result = await mcp_server.registry.call_tool(
                credential=mcp_credential,
                tool_name=request.proposed_tool,
                arguments=request.arguments,
            )

            content_text = "".join(getattr(c, "text", str(c)) for c in tool_result.content)
            try:
                parsed_exec = json.loads(content_text)
            except Exception:
                parsed_exec = {"result": content_text}

            is_error = tool_result.isError

            # 4. Formulate Concrete Evidence Record
            evidence_record = {
                "tool_executed": request.proposed_tool,
                "execution_timestamp": now_iso,
                "is_error": is_error,
                "intent": request.intent_description,
                "output_sample": str(parsed_exec)[:500],
            }

            if receipt:
                evidence_list = list(receipt.evidence or [])
                evidence_list.append(evidence_record)
                receipt.evidence = evidence_list
                receipt.status = "verified" if not is_error else "failed"
                receipt.result = parsed_exec
                db.commit()

            AuditService.log_event(
                db=db,
                action="execution_bridge.executed",
                tenant_id=tenant_id,
                resource="collaboration_bridge",
                resource_id=request.task_id,
                details={"tool": request.proposed_tool, "success": not is_error, "evidence": evidence_record},
            )

            return ExecutionBridgeResponse(
                task_id=request.task_id,
                status="executed" if not is_error else "failed",
                verified=not is_error,
                policy_decision="allow_auto",
                evidence=evidence_record,
                execution_result=parsed_exec,
                error=content_text if is_error else None,
            )

        except Exception as e:
            logger.error("Execution bridge invocation error: %s", e)
            return ExecutionBridgeResponse(
                task_id=request.task_id,
                status="failed",
                verified=False,
                policy_decision="allow_auto",
                error=f"Execution error: {str(e)}",
            )
