"""Durable Celery worker for inbound AI collaboration tasks."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.collaborative_workforce import AgentMessage, DelegationReceipt
from app.models.mcp import SystemMCPCredential
from app.services.collaboration.orchestrator import dispatch_signed_webhook
from app.services.collaboration.security import bounded_json_size, validate_json_schema
from app.services.collaboration.outbox import persist_webhook_outbox
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
        webhook_url = payload.get("webhook_url")
        if webhook_url:
            persist_webhook_outbox(
                db,
                tenant_id=tenant_id,
                task_id=task_id,
                webhook_url=webhook_url,
                callback_payload={"task_id": task_id, "status": msg.status, "result": result},
                credential_id=str(credential.id),
            )
        # Result and callback intent are committed in one transaction.
        db.commit()
        return {"task_id": task_id, "status": msg.status}
    finally:
        db.close()

@celery_app.task(name="octaos.drain_collaboration_webhook_outbox")
def drain_collaboration_webhook_outbox():
    """Reconcile queued/stale webhook outbox rows after broker or worker outages."""
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(minutes=5)
    try:
        rows = db.query(AgentMessage).filter(
            AgentMessage.message_type == "webhook_outbox",
            AgentMessage.tenant_id.isnot(None),
            (
                (AgentMessage.status == "queued") |
                ((AgentMessage.status == "dispatching") & (AgentMessage.updated_at < stale_before))
            ),
        ).order_by(AgentMessage.created_at.asc()).limit(100).all()
        scheduled = 0
        for row in rows:
            payload = dict(row.payload or {})
            tenant_id = row.tenant_id
            row.status = "dispatching"
            row.error_code = None
            db.commit()
            try:
                celery_app.send_task(
                    "octaos.deliver_collaboration_webhook",
                    args=[row.id, tenant_id],
                    queue="main-queue",
                    task_id=f"webhook-{row.id}",
                )
                scheduled += 1
            except Exception as exc:
                db.rollback()
                current = db.query(AgentMessage).filter(
                    AgentMessage.id == row.id, AgentMessage.tenant_id == tenant_id
                ).first()
                if current:
                    current.status = "queued"
                    current.error_code = "WEBHOOK_BROKER_UNAVAILABLE"
                    db.commit()
                logger.warning("Webhook outbox enqueue failed (%s)", type(exc).__name__)
        return {"scheduled": scheduled}
    finally:
        db.close()


@celery_app.task(name="octaos.deliver_collaboration_webhook", bind=True, max_retries=5, default_retry_delay=10)
def deliver_collaboration_webhook(self, outbox_id: str, tenant_id: str):
    """Deliver a tenant-scoped outbox row; retries never rerun the employee action."""
    db = SessionLocal()
    try:
        row = db.query(AgentMessage).filter(
            AgentMessage.id == outbox_id,
            AgentMessage.tenant_id == tenant_id,
            AgentMessage.message_type == "webhook_outbox",
        ).first()
        if not row:
            return {"outbox_id": outbox_id, "status": "not_found"}
        if row.status == "completed":
            return {"outbox_id": outbox_id, "status": "completed"}
        payload = dict(row.payload or {})
        credential = db.query(SystemMCPCredential).filter(
            SystemMCPCredential.id == payload.get("credential_id"),
            SystemMCPCredential.tenant_id == tenant_id,
            SystemMCPCredential.is_active.is_(True),
        ).first()
        if not credential:
            row.status = "queued"
            row.error_code = "WEBHOOK_CREDENTIAL_UNAVAILABLE"
            db.commit()
            raise self.retry(exc=RuntimeError("Webhook signing credential unavailable."))
        row.status = "processing"
        db.commit()
        delivered = asyncio.run(dispatch_signed_webhook(
            webhook_url=payload.get("webhook_url", ""),
            payload=payload.get("callback_payload") or {},
            secret=credential.key_hash,
            timeout_seconds=10,
        ))
        if delivered:
            row.status = "completed"
            row.error_code = None
            db.commit()
            return {"outbox_id": outbox_id, "status": "completed"}
        row.status = "queued"
        row.error_code = "WEBHOOK_DELIVERY_FAILED"
        db.commit()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=RuntimeError("Webhook delivery failed or destination was rejected."))
        return {"outbox_id": outbox_id, "status": "queued", "error_code": "WEBHOOK_DELIVERY_FAILED"}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
