"""Durable Celery worker for inbound AI collaboration tasks."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.collaborative_workforce import AgentMessage, DelegationReceipt
from app.models.mcp import SystemMCPCredential
from app.services.collaboration.orchestrator import dispatch_signed_webhook
from app.services.collaboration.security import bounded_json_size, validate_json_schema
from app.services.mcp.server import mcp_server

logger = logging.getLogger(__name__)


@celery_app.task(name="octaos.execute_inbound_collaboration", bind=True, max_retries=3, default_retry_delay=5)
def execute_inbound_collaboration(self, task_id: str, tenant_id: str):
    """Execute a committed collaboration row; durable DB state remains canonical."""
    db = SessionLocal()
    try:
        msg = db.query(AgentMessage).filter(
            AgentMessage.id == task_id, AgentMessage.tenant_id == tenant_id
        ).first()
        receipt = db.query(DelegationReceipt).filter(
            DelegationReceipt.task_id == task_id, DelegationReceipt.tenant_id == tenant_id
        ).first()
        if not msg or not receipt:
            return {"task_id": task_id, "status": "not_found"}
        if msg.status == "cancelled":
            return {"task_id": task_id, "status": "cancelled"}
        if msg.status not in {"queued", "processing"}:
            return {"task_id": task_id, "status": msg.status}

        payload = dict(msg.payload or {})
        credential = db.query(SystemMCPCredential).filter(
            SystemMCPCredential.id == payload.get("credential_id"),
            SystemMCPCredential.tenant_id == tenant_id,
            SystemMCPCredential.is_active.is_(True),
        ).first()
        if not credential:
            msg.status = "failed"
            msg.error_code = "EXECUTION_CREDENTIAL_UNAVAILABLE"
            msg.completed_at = datetime.now(timezone.utc)
            receipt.status = "failed"
            receipt.verification_errors = ["Execution credential was unavailable or inactive."]
            db.commit()
            return {"task_id": task_id, "status": "failed"}

        msg.status = "processing"
        msg.attempt_count = int(msg.attempt_count or 0) + 1
        db.commit()
        arguments = {
            "employee": msg.to_agent.removeprefix("octaos:"),
            "task_type": payload.get("target_capability") or "execute_task",
            "parameters": payload.get("context") or {},
            "instructions": payload.get("description") or "",
        }
        timeout = max(1, min(int(payload.get("timeout_seconds", 90)), 300))
        try:
            tool_result = asyncio.run(asyncio.wait_for(
                mcp_server.registry.call_tool(
                    credential=credential,
                    tool_name="octaos_delegate_ai_employee",
                    arguments=arguments,
                ),
                timeout=timeout,
            ))
            text_result = "".join(getattr(item, "text", str(item)) for item in tool_result.content)
            try:
                result = json.loads(text_result)
            except (TypeError, ValueError):
                result = {"result": text_result}
            if len(json.dumps(result, default=str).encode("utf-8")) > 1_000_000:
                raise ValueError("Result exceeds the 1 MB collaboration payload limit.")
            schema = payload.get("output_schema")
            if schema:
                validate_json_schema(result, schema)
            succeeded = not bool(getattr(tool_result, "isError", True))
            evidence = [{
                "action": "ai_employee_execution",
                "employee": arguments["employee"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "success": succeeded,
                "schema_validated": bool(schema),
                "worker_attempt": msg.attempt_count,
            }]
        except Exception as exc:
            db.rollback()
            msg = db.query(AgentMessage).filter(
                AgentMessage.id == task_id, AgentMessage.tenant_id == tenant_id
            ).first()
            receipt = db.query(DelegationReceipt).filter(
                DelegationReceipt.task_id == task_id, DelegationReceipt.tenant_id == tenant_id
            ).first()
            if not msg or msg.status == "cancelled":
                return {"task_id": task_id, "status": "cancelled"}
            if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
                error_code = "EXECUTION_TIMEOUT"
            elif isinstance(exc, ValueError):
                error_code = "OUTPUT_VALIDATION_FAILED"
            else:
                error_code = "EXECUTION_FAILED"
            # Retry transient failures through Celery; terminal status is written on final attempt.
            if self.request.retries < self.max_retries:
                msg.status = "queued"
                msg.error_code = error_code
                db.commit()
                raise self.retry(exc=exc)
            msg.status = "failed"
            msg.error_code = error_code
            msg.completed_at = datetime.now(timezone.utc)
            if receipt:
                receipt.status = "failed"
                receipt.verification_errors = [error_code]
            db.commit()
            logger.warning("Inbound collaboration task %s failed (%s)", task_id, error_code)
            return {"task_id": task_id, "status": "failed", "error_code": error_code}

        # Re-read before finalizing: cancellation wins over a late provider response.
        db.expire_all()
        msg = db.query(AgentMessage).filter(
            AgentMessage.id == task_id, AgentMessage.tenant_id == tenant_id
        ).first()
        receipt = db.query(DelegationReceipt).filter(
            DelegationReceipt.task_id == task_id, DelegationReceipt.tenant_id == tenant_id
        ).first()
        if not msg or msg.status == "cancelled":
            return {"task_id": task_id, "status": "cancelled"}
        msg.status = "completed" if succeeded else "failed"
        msg.response = result
        msg.error_code = None if succeeded else "EMPLOYEE_EXECUTION_FAILED"
        msg.completed_at = datetime.now(timezone.utc)
        if receipt:
            receipt.status = "verified" if succeeded else "failed"
            receipt.result = result
            receipt.evidence = evidence
            if not succeeded:
                receipt.verification_errors = ["Employee tool returned an error."]
        db.commit()

        webhook_url = payload.get("webhook_url")
        if webhook_url:
            # The credential hash is the stable shared signing key; a client holding
            # the API token can derive the same SHA-256 digest for signature checks.
            delivered = asyncio.run(dispatch_signed_webhook(
                webhook_url=webhook_url,
                payload={"task_id": task_id, "status": msg.status, "result": result},
                secret=credential.key_hash,
            ))
            if not delivered:
                logger.warning("Webhook delivery failed for collaboration task %s", task_id)
        return {"task_id": task_id, "status": msg.status}
    finally:
        db.close()

@celery_app.task(name="octaos.deliver_collaboration_webhook", bind=True, max_retries=5, default_retry_delay=10)
def deliver_collaboration_webhook(self, webhook_url: str, payload: dict, signing_secret: str):
    """Durable webhook delivery with bounded retries; each attempt revalidates the URL."""
    delivered = asyncio.run(dispatch_signed_webhook(
        webhook_url=webhook_url,
        payload=payload,
        secret=signing_secret,
        timeout_seconds=10,
    ))
    if not delivered:
        raise self.retry(exc=RuntimeError("Webhook delivery failed or destination was rejected."))
    return {"delivered": True, "task_id": payload.get("task_id")}
