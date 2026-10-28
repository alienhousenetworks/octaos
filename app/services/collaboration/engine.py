"""Core Bidirectional AI Collaboration Engine for OctaOS."""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.base import tenant_context
from app.models.collaborative_workforce import AgentMessage, DelegationReceipt
from app.services.ai_gateway import ai_gateway
from app.services.audit_service import AuditService
from app.services.collaboration.contracts import (
    CollaborationTaskSubmitRequest,
    TaskStatusResponse,
    redact_sensitive_context,
)
from app.services.collaboration.orchestrator import (
    check_duplicate_task,
    compute_task_fingerprint,
    dispatch_signed_webhook,
    validate_delegation_safety,
)
from app.services.collaboration.provider_registry import AIProviderRegistry, ProviderDescriptor
from app.services.collaboration.security import validate_json_schema, bounded_json_size, validate_public_https_url

logger = logging.getLogger(__name__)


class AICollaborationEngine:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    # ---------------------------------------------------------------------
    # 1. OUTBOUND: OctaOS AI Employee → Connected External AI
    # ---------------------------------------------------------------------
    async def collaborate_with_external_ai(
        self,
        *,
        task: Dict[str, Any],
        required_capabilities: List[str],
        context: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None,
        calling_agent: str = "Sales AI",
        parent_task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        lineage: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Outbound collaboration: Called by any OctaOS AI employee to delegate a subtask
        to a connected frontier AI model (Claude, Grok, ChatGPT, DeepSeek, etc.).
        """
        constraints = constraints or {}
        lineage = lineage or [calling_agent]
        corr_id = correlation_id or parent_task_id or str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        task_desc = task.get("description") or task.get("title") or "Collaborative AI Subtask"
        preferred_provider = constraints.get("preferred_provider") or task.get("target_provider")

        # 1. Orchestration & Loop Prevention Check
        target_name = f"external:{preferred_provider}" if preferred_provider else "external:ai_provider"
        new_depth, updated_lineage = validate_delegation_safety(
            self.db,
            tenant_id=self.tenant_id,
            source_agent=calling_agent,
            target=target_name,
            lineage=lineage,
            parent_task_id=parent_task_id,
        )

        # 2. Discover & Select Eligible Provider
        eligible_providers = AIProviderRegistry.get_eligible_providers_for_task(
            self.db,
            self.tenant_id,
            required_capabilities=required_capabilities,
            max_cost=constraints.get("max_cost_usd"),
        )

        selected_provider: Optional[ProviderDescriptor] = None
        if preferred_provider:
            for p in eligible_providers:
                if p.provider.lower() == preferred_provider.lower():
                    selected_provider = p
                    break

        if not selected_provider and eligible_providers:
            selected_provider = eligible_providers[0]

        # 3. Handle Missing Provider Safely (Graceful Fallback)
        if not selected_provider and not constraints.get("_test_mock_response"):
            logger.info("No eligible external AI provider found for capabilities %s in tenant %s", required_capabilities, self.tenant_id)
            return {
                "status": "fallback_local",
                "message": f"No connected external AI provider configured for capabilities: {required_capabilities}. Resuming with internal workforce.",
                "calling_agent": calling_agent,
                "task_id": task_id,
                "executed_externally": False,
            }

        provider_name = selected_provider.provider if selected_provider else (preferred_provider or "mock_provider")
        model_name = constraints.get("model") or (selected_provider.default_model if selected_provider else "default_model")

        # 4. Prepare Minimum-Necessary Redacted Context
        clean_context = redact_sensitive_context(context)
        sanitized_task = redact_sensitive_context(task)

        # 5. Persist Durable Task Message & Delegation Receipt
        msg = AgentMessage(
            id=task_id,
            tenant_id=self.tenant_id,
            correlation_id=corr_id,
            idempotency_key=f"outbound:{task_id}",
            from_agent=calling_agent,
            to_agent=f"provider:{provider_name}",
            message_type="outbound_collaboration",
            status="processing",
            payload={
                "task": sanitized_task,
                "context": clean_context,
                "required_capabilities": required_capabilities,
                "parent_task_id": parent_task_id,
                "lineage": updated_lineage,
                "depth": new_depth,
            },
        )
        self.db.add(msg)

        receipt = DelegationReceipt(
            tenant_id=self.tenant_id,
            task_id=task_id,
            parent_agent=calling_agent,
            child_agent=f"external:{provider_name}:{model_name}",
            request_message_id=task_id,
            status="in_progress",
            acceptance_criteria=task.get("acceptance_criteria", []),
            evidence=[],
        )
        self.db.add(receipt)
        self.db.commit()

        # 6. Execute Provider Request
        start_time = time.time()
        error_msg = None
        result_payload = {}
        tokens_info = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}

        try:
            # Test Hook for deterministic tests without hitting live paid external endpoints
            if constraints.get("_test_mock_response"):
                await asyncio.sleep(0.01)
                mock_data = constraints["_test_mock_response"]
                result_payload = mock_data if isinstance(mock_data, dict) else {"response": mock_data}
                tokens_info = {"input_tokens": 150, "output_tokens": 80, "cost": 0.002}
            else:
                prompt_text = (
                    f"Task: {task_desc}\n\n"
                    f"Requirements: {json.dumps(sanitized_task, indent=2)}\n\n"
                    f"Context: {json.dumps(clean_context, indent=2)}"
                )
                system_prompt = (
                    f"You are {provider_name.upper()} collaborating as an external intelligence unit for OctaOS {calling_agent}. "
                    f"Provide clear, factual, actionable findings in structured JSON."
                )

                content = await asyncio.wait_for(ai_gateway.executeRequest(
                    db=self.db,
                    tenant_id=self.tenant_id,
                    prompt=prompt_text,
                    provider=provider_name,
                    model=model_name,
                    system_prompt=system_prompt,
                    task_type="collaboration",
                    correlation_id=corr_id,
                ), timeout=max(1, min(int(selected_provider.timeout_seconds if selected_provider else 60), 180)))
                try:
                    result_payload = json.loads(content)
                except Exception:
                    result_payload = {"raw_output": content}

        except Exception as e:
            logger.error("Outbound collaboration failed on %s: %s", provider_name, e)
            error_msg = str(e)
            result_payload = {"error": error_msg}

        latency = time.time() - start_time
        success = error_msg is None

        # 7. Validate Output Schema Contract if Specified
        schema_validation_passed = True
        schema = task.get("output_schema")
        if success:
            try:
                bounded_json_size(result_payload)
                if schema:
                    validate_json_schema(result_payload, schema)
            except Exception as exc:
                schema_validation_passed = False
                error_msg = str(exc)[:500]
                success = False

        # 8. Update Durable Records
        now_iso = datetime.now(timezone.utc).isoformat()
        msg.status = "completed" if success else "failed"
        msg.response = result_payload
        msg.error_code = error_msg
        msg.completed_at = datetime.now(timezone.utc)

        receipt.status = "verified" if success else "failed"
        receipt.result = result_payload
        receipt.evidence = [{
            "provider": provider_name,
            "model": model_name,
            "latency": latency,
            "timestamp": now_iso,
            "schema_validated": schema_validation_passed,
            "tokens": tokens_info,
        }]
        if error_msg:
            receipt.verification_errors = [error_msg]

        self.db.commit()

        AuditService.log_event(
            db=self.db,
            action="collaboration.outbound_executed",
            tenant_id=self.tenant_id,
            resource="collaboration_task",
            resource_id=task_id,
            details={"provider": provider_name, "model": model_name, "success": success, "latency": latency},
        )

        return {
            "status": "success" if success else "failed",
            "task_id": task_id,
            "correlation_id": corr_id,
            "executed_externally": True,
            "target_provider": provider_name,
            "model": model_name,
            "latency": latency,
            "provenance": {
                "source_agent": calling_agent,
                "target_provider": provider_name,
                "model": model_name,
                "timestamp": now_iso,
                "cost_usd": tokens_info.get("cost", 0.0),
            },
            "result": result_payload,
            "error": error_msg,
        }

    # ---------------------------------------------------------------------
    # 2. INBOUND: External AI → OctaOS AI Employee
    # ---------------------------------------------------------------------
    async def submit_inbound_task(
        self,
        request: CollaborationTaskSubmitRequest,
        source_identifier: str = "external:generic_client",
        mcp_credential: Any = None,
    ) -> TaskStatusResponse:
        """
        Inbound collaboration: An external AI model (or system) submits a task
        or delegates work to an OctaOS AI Employee.
        """
        from app.services.mcp.server import mcp_server

        # 1. Duplicate & Idempotency Check
        fingerprint = request.idempotency_key or compute_task_fingerprint(
            self.tenant_id, request.task_description, request.context
        )
        existing = check_duplicate_task(self.db, tenant_id=self.tenant_id, fingerprint=fingerprint)
        if existing and existing.status in ("completed", "processing", "queued"):
            receipt = self.db.query(DelegationReceipt).filter_by(
                tenant_id=self.tenant_id, task_id=existing.id
            ).first()
            return TaskStatusResponse(
                task_id=existing.id,
                parent_task_id=existing.payload.get("parent_task_id"),
                correlation_id=existing.correlation_id,
                tenant_id=self.tenant_id,
                source_agent=existing.from_agent,
                target_employee=existing.to_agent,
                task_description=request.task_description,
                status=existing.status,
                result=existing.response,
                evidence=receipt.evidence if receipt else [],
                created_at=existing.created_at.isoformat(),
                completed_at=existing.completed_at.isoformat() if existing.completed_at else None,
            )

        task_id = str(uuid.uuid4())
        corr_id = request.parent_task_id or str(uuid.uuid4())
        target_emp = request.target_employee or "sales"
        if request.webhook_url:
            # Validate before persisting/accepting the callback destination.
            validate_public_https_url(request.webhook_url)
        if request.timeout_seconds < 1 or request.timeout_seconds > 300:
            raise ValueError("timeout_seconds must be between 1 and 300.")
        if request.cost_limit_usd <= 0:
            raise ValueError("cost_limit_usd must be greater than zero.")

        # 2. Loop & Limit Prevention Check
        new_depth, updated_lineage = validate_delegation_safety(
            self.db,
            tenant_id=self.tenant_id,
            source_agent=source_identifier,
            target=f"octaos:{target_emp}",
            lineage=[source_identifier],
            parent_task_id=request.parent_task_id,
        )

        msg = AgentMessage(
            id=task_id,
            tenant_id=self.tenant_id,
            correlation_id=corr_id,
            idempotency_key=fingerprint,
            from_agent=source_identifier,
            to_agent=f"octaos:{target_emp}",
            message_type="inbound_collaboration",
            status="queued" if request.async_execution else "processing",
            payload={
                "description": request.task_description,
                "context": request.context,
                "input_references": [r.model_dump() for r in request.input_references],
                "parent_task_id": request.parent_task_id,
                "webhook_url": request.webhook_url,
                "lineage": updated_lineage,
                "depth": new_depth,
            },
        )
        self.db.add(msg)

        receipt = DelegationReceipt(
            tenant_id=self.tenant_id,
            task_id=task_id,
            parent_agent=source_identifier,
            child_agent=f"octaos:{target_emp}",
            request_message_id=task_id,
            status="requested" if request.async_execution else "in_progress",
            acceptance_criteria=[request.task_description],
            evidence=[],
        )
        self.db.add(receipt)
        self.db.commit()

        # 3. Synchronous Execution
        if not request.async_execution:
            now_iso = datetime.now(timezone.utc).isoformat()
            tool_args = {
                "employee": target_emp,
                "task_type": request.target_capability or "execute_task",
                "parameters": request.context,
                "instructions": request.task_description,
            }

            tool_result = await asyncio.wait_for(
                mcp_server.registry.call_tool(
                    credential=mcp_credential,
                    tool_name="octaos_delegate_ai_employee",
                    arguments=tool_args,
                ),
                timeout=max(1, min(int(request.timeout_seconds), 300)),
            )

            content_text = "".join(getattr(c, "text", str(c)) for c in tool_result.content)
            try:
                parsed_res = json.loads(content_text)
            except Exception:
                parsed_res = {"result": content_text}

            is_error = bool(tool_result.isError)
            try:
                bounded_json_size(parsed_res)
                if request.output_schema:
                    validate_json_schema(parsed_res, request.output_schema)
            except Exception as exc:
                is_error = True
                msg.error_code = "OUTPUT_VALIDATION_FAILED"
                receipt.verification_errors = [str(exc)[:500]]
            msg.status = "completed" if not is_error else "failed"
            msg.response = parsed_res
            msg.completed_at = datetime.now(timezone.utc)

            evidence_item = {
                "action": "ai_employee_execution",
                "employee": target_emp,
                "timestamp": now_iso,
                "success": not is_error,
            }
            receipt.status = "verified" if not is_error else "failed"
            receipt.result = parsed_res
            receipt.evidence = [evidence_item]
            self.db.commit()

            # Do not use a process-local fire-and-forget task: await delivery here.
            # The dispatcher has strict URL validation, no redirects, and a bounded timeout.
            if request.webhook_url:
                secret = getattr(mcp_credential, "webhook_secret", None)
                if not secret:
                    logger.warning("Webhook requested for task %s but no dedicated webhook secret is configured", task_id)
                else:
                    await dispatch_signed_webhook(
                        webhook_url=request.webhook_url,
                        payload={"task_id": task_id, "status": msg.status, "result": parsed_res},
                        secret=secret,
                    )

            return TaskStatusResponse(
                task_id=task_id,
                parent_task_id=request.parent_task_id,
                correlation_id=corr_id,
                tenant_id=self.tenant_id,
                source_agent=source_identifier,
                target_employee=target_emp,
                target_capability=request.target_capability,
                task_description=request.task_description,
                status=msg.status,
                lineage=updated_lineage,
                depth=new_depth,
                result=parsed_res,
                evidence=[evidence_item],
                created_at=now_iso,
                completed_at=now_iso,
            )

        # 4. Durable handoff: the task row is committed before publishing to Celery.
        # A failed publish is surfaced and the row is marked failed, never left queued silently.
        from app.core.celery_app import celery_app
        from app.models.mcp import SystemMCPCredential
        credential_id = getattr(mcp_credential, "id", None)
        if not credential_id:
            msg.status = "failed"
            msg.error_code = "MISSING_EXECUTION_CREDENTIAL"
            msg.completed_at = datetime.now(timezone.utc)
            receipt.status = "failed"
            receipt.verification_errors = ["No execution credential was available for durable handoff."]
            self.db.commit()
            raise RuntimeError("An authenticated execution credential is required for asynchronous collaboration.")
        msg.payload = {**(msg.payload or {}), "credential_id": credential_id,
                       "target_capability": request.target_capability,
                       "output_schema": request.output_schema,
                       "timeout_seconds": request.timeout_seconds,
                       "cost_limit_usd": request.cost_limit_usd}
        self.db.commit()
        try:
            celery_app.send_task(
                "octaos.execute_inbound_collaboration",
                args=[task_id, self.tenant_id],
                queue="main-queue",
                task_id=task_id,
            )
        except Exception as exc:
            msg.status = "failed"
            msg.error_code = "DURABLE_HANDOFF_FAILED"
            msg.completed_at = datetime.now(timezone.utc)
            receipt.status = "failed"
            receipt.verification_errors = ["Durable worker handoff failed."]
            self.db.commit()
            logger.error("Collaboration task %s could not be enqueued (%s)", task_id, type(exc).__name__)
            raise RuntimeError("Collaboration task could not be queued for execution.") from exc

        now_iso = datetime.now(timezone.utc).isoformat()
        return TaskStatusResponse(
            task_id=task_id,
            parent_task_id=request.parent_task_id,
            correlation_id=corr_id,
            tenant_id=self.tenant_id,
            source_agent=source_identifier,
            target_employee=target_emp,
            target_capability=request.target_capability,
            task_description=request.task_description,
            status="queued",
            lineage=updated_lineage,
            depth=new_depth,
            created_at=now_iso,
        )

    # ---------------------------------------------------------------------
    # 3. TASK STATUS, CANCELLATION & APPROVAL MANAGEMENT
    # ---------------------------------------------------------------------
    def get_task_status(self, task_id: str) -> Optional[TaskStatusResponse]:
        """
        Poll status, evidence, child tasks and outcome for a given collaboration task.
        Guarantees strict tenant isolation.
        """
        msg = (
            self.db.query(AgentMessage)
            .filter(AgentMessage.tenant_id == self.tenant_id, AgentMessage.id == task_id)
            .first()
        )
        if not msg:
            return None

        receipt = (
            self.db.query(DelegationReceipt)
            .filter(DelegationReceipt.tenant_id == self.tenant_id, DelegationReceipt.task_id == task_id)
            .first()
        )

        return TaskStatusResponse(
            task_id=msg.id,
            parent_task_id=msg.payload.get("parent_task_id"),
            correlation_id=msg.correlation_id,
            tenant_id=self.tenant_id,
            source_agent=msg.from_agent,
            target_employee=msg.to_agent,
            task_description=msg.payload.get("description", ""),
            status=msg.status,
            lineage=msg.payload.get("lineage", []),
            depth=msg.payload.get("depth", 0),
            result=msg.response,
            evidence=receipt.evidence if receipt else [],
            error_details=msg.error_code,
            created_at=msg.created_at.isoformat(),
            completed_at=msg.completed_at.isoformat() if msg.completed_at else None,
        )

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running collaboration task."""
        msg = (
            self.db.query(AgentMessage)
            .filter(AgentMessage.tenant_id == self.tenant_id, AgentMessage.id == task_id)
            .first()
        )
        if not msg or msg.status in ("completed", "cancelled"):
            return False

        msg.status = "cancelled"
        msg.completed_at = datetime.now(timezone.utc)
        msg.error_code = "CANCELLED_BY_REQUEST"

        receipt = (
            self.db.query(DelegationReceipt)
            .filter(DelegationReceipt.tenant_id == self.tenant_id, DelegationReceipt.task_id == task_id)
            .first()
        )
        if receipt:
            receipt.status = "cancelled"

        self.db.commit()
        # Revoke the matching Celery delivery as a best-effort interruption.
        # The worker also re-checks persisted cancellation before writing a result.
        if msg.message_type == "inbound_collaboration":
            try:
                from app.core.celery_app import celery_app
                celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
            except Exception as exc:
                logger.warning("Could not signal cancellation for task %s (%s)", task_id, type(exc).__name__)
        return True
