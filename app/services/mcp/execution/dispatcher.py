"""Governed Execution Dispatcher: The single, verified path for all MCP operations."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Set
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.base import tenant_context
from app.models.mcp import SystemMCPCredential, DynamicConnector, DynamicObjectDefinition
from app.services.audit_service import AuditService
from app.services.mcp.auth.policy import PolicyKernel, AuthorizationDecision
from app.services.mcp.connectors.base import ConnectorAdapter, ConnectorContext
from app.services.mcp.connectors.octaos_internal import OctaOSInternalAdapter
from app.services.mcp.connectors.marketing_adapter import MarketingIntegrationsAdapter
from app.services.mcp.execution.query_engine import validate_query_dsl, QueryValidationError
from app.services.mcp.registry.schema_validation import validate_record_against_schema
from app.services.mcp.protocol import ToolResult, TextContent

logger = logging.getLogger(__name__)


class ExecutionException(Exception):
    def __init__(self, message: str, code: int = -32000, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class GovernedExecutionDispatcher:
    """
    Executes all MCP operations across universal and domain tools.
    Enforces the mandatory execution sequence:
    Authenticate -> Resolve Tenant -> Authorize -> Evaluate Policy ->
    Validate Dynamic Schema -> Execute Adapter -> Redact -> Audit.
    """

    def __init__(self, db_factory=SessionLocal):
        self.db_factory = db_factory
        marketing_adapter = MarketingIntegrationsAdapter(db_factory=db_factory)
        # Registry of instantiated adapters per connector slug
        self._adapters: Dict[str, ConnectorAdapter] = {
            "octaos": OctaOSInternalAdapter(db_factory=db_factory),
            "marketing": marketing_adapter,
            "integrations": marketing_adapter,
            "crm": marketing_adapter,
        }

    def register_adapter(self, connector_slug: str, adapter: ConnectorAdapter) -> None:
        self._adapters[connector_slug] = adapter

    def get_adapter(self, connector_slug: str) -> ConnectorAdapter:
        adapter = self._adapters.get(connector_slug)
        if not adapter:
            # Fall back to internal OctaOS adapter if unknown or default
            return self._adapters["octaos"]
        return adapter

    async def execute(
        self,
        credential: SystemMCPCredential,
        connector_slug: str,
        object_name: str,
        action: str, # "discover", "read", "query", "create", "update", "delete", "invoke"
        parameters: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> ToolResult:
        start_time = time.time()
        db: Session = self.db_factory()
        tenant_token = None

        try:
            # 1. Resolve trusted server-side tenant isolation
            tenant_id = credential.tenant_id
            tenant_token = tenant_context.set(tenant_id)

            # 2. Extract input payload fields for authorization check
            payload_fields: Optional[Set[str]] = None
            if action in ("create", "update"):
                rec_val = parameters.get("record") or parameters.get("values") or {}
                if isinstance(rec_val, dict):
                    payload_fields = set(rec_val.keys())

            # 3. Central Policy Kernel: Authorize action & field grants
            auth_decision: AuthorizationDecision = PolicyKernel.authorize_action(
                db=db,
                credential=credential,
                connector_slug=connector_slug,
                object_name=object_name,
                action=action,
                payload_fields=payload_fields,
            )

            if not auth_decision.allowed:
                self._log_audit(
                    db=db,
                    credential=credential,
                    connector_slug=connector_slug,
                    object_name=object_name,
                    action=action,
                    status="denied",
                    details={"reason": auth_decision.reason},
                )
                return ToolResult(
                    content=[TextContent(text=f"Unauthorized: {auth_decision.reason}")],
                    isError=True,
                    metadata={"error_code": "PERMISSION_DENIED"},
                )

            if auth_decision.requires_approval:
                self._log_audit(
                    db=db,
                    credential=credential,
                    connector_slug=connector_slug,
                    object_name=object_name,
                    action=action,
                    status="approval_required",
                    details={"approval_id": auth_decision.approval_id},
                )
                return ToolResult(
                    content=[TextContent(text=f"Action requires human approval. Queued Approval Request ID: {auth_decision.approval_id}")],
                    isError=False,
                    metadata={"status": "pending_approval", "approval_id": auth_decision.approval_id},
                )

            # 4. Resolve connector and adapter
            adapter = self.get_adapter(connector_slug)
            ctx = ConnectorContext(
                tenant_id=tenant_id,
                connector_slug=connector_slug,
                credential_id=credential.id,
            )

            # 5. Schema Validation for Writes (create / update)
            if action in ("create", "update") and object_name != "*":
                obj_meta = await adapter.describe_object(ctx, object_name)
                if obj_meta:
                    record_data = parameters.get("record") or parameters.get("values") or {}
                    is_valid, val_errors = validate_record_against_schema(
                        record=record_data,
                        json_schema=obj_meta.json_schema,
                        allow_partial=(action == "update"),
                    )
                    if not is_valid:
                        return ToolResult(
                            content=[TextContent(text=f"Schema Validation Error: {val_errors}")],
                            isError=True,
                            metadata={"validation_errors": val_errors},
                        )

            # 6. Execute operation through adapter
            raw_result = await self._dispatch_to_adapter(
                adapter=adapter,
                ctx=ctx,
                action=action,
                object_name=object_name,
                parameters=parameters,
                credential=credential,
            )

            # 7. Redact output data according to field permissions
            redacted_result = self._redact_output(raw_result, auth_decision)

            duration_ms = int((time.time() - start_time) * 1000)

            # 8. Immutable Audit Log
            self._log_audit(
                db=db,
                credential=credential,
                connector_slug=connector_slug,
                object_name=object_name,
                action=action,
                status="success",
                details={"duration_ms": duration_ms, "idempotency_key": idempotency_key},
            )

            import json
            return ToolResult(
                content=[TextContent(text=json.dumps(redacted_result, indent=2, default=str))],
                isError=False,
                metadata={"duration_ms": duration_ms},
            )

        except QueryValidationError as qe:
            return ToolResult(
                content=[TextContent(text=f"Invalid Query: {str(qe)}")],
                isError=True,
                metadata={"error_code": "INVALID_QUERY"},
            )
        except Exception as e:
            logger.exception(f"Governed execution failure: {e}")
            self._log_audit(
                db=db,
                credential=credential,
                connector_slug=connector_slug,
                object_name=object_name,
                action=action,
                status="error",
                details={"error": str(e)},
            )
            return ToolResult(
                content=[TextContent(text=f"Execution Error: {str(e)}")],
                isError=True,
                metadata={"error_code": "EXECUTION_ERROR"},
            )
        finally:
            if tenant_token:
                tenant_context.reset(tenant_token)
            db.close()

    async def _dispatch_to_adapter(
        self,
        adapter: ConnectorAdapter,
        ctx: ConnectorContext,
        action: str,
        object_name: str,
        parameters: Dict[str, Any],
        credential: SystemMCPCredential,
    ) -> Any:
        if action == "discover":
            objects = await adapter.discover_objects(ctx)
            return [o.model_dump() for o in objects]

        elif action == "describe":
            meta = await adapter.describe_object(ctx, object_name)
            return meta.model_dump() if meta else None

        elif action == "query":
            raw_query = parameters.get("query") or parameters
            valid_query = validate_query_dsl(
                query=raw_query,
                max_allowed_limit=credential.max_records_per_query,
            )
            return await adapter.query_records(ctx, object_name, valid_query)

        elif action == "read":
            record_id = parameters.get("id") or parameters.get("record_id")
            fields = parameters.get("fields")
            return await adapter.get_record(ctx, object_name, str(record_id), fields=fields)

        elif action == "create":
            values = parameters.get("record") or parameters.get("values") or {}
            return await adapter.create_record(ctx, object_name, values)

        elif action == "update":
            record_id = parameters.get("id") or parameters.get("record_id")
            values = parameters.get("record") or parameters.get("values") or {}
            return await adapter.update_record(ctx, object_name, str(record_id), values)

        elif action == "delete":
            record_id = parameters.get("id") or parameters.get("record_id")
            deleted = await adapter.delete_record(ctx, object_name, str(record_id))
            return {"deleted": deleted, "id": record_id}

        elif action == "invoke":
            action_name = parameters.get("action_name") or parameters.get("action")
            arguments = parameters.get("arguments") or parameters.get("args") or {}
            return await adapter.invoke_action(ctx, action_name, arguments)

        raise ValueError(f"Unsupported action: '{action}'")

    def _redact_output(self, raw_result: Any, auth_decision: AuthorizationDecision) -> Any:
        if isinstance(raw_result, dict):
            if "records" in raw_result and isinstance(raw_result["records"], list):
                raw_result["records"] = [
                    PolicyKernel.redact_record(r, auth_decision.permitted_fields, auth_decision.denied_fields)
                    for r in raw_result["records"]
                ]
                return raw_result
            return PolicyKernel.redact_record(raw_result, auth_decision.permitted_fields, auth_decision.denied_fields)
        elif isinstance(raw_result, list):
            return [
                PolicyKernel.redact_record(item, auth_decision.permitted_fields, auth_decision.denied_fields)
                if isinstance(item, dict) else item
                for item in raw_result
            ]
        return raw_result

    def _log_audit(
        self,
        db: Session,
        credential: SystemMCPCredential,
        connector_slug: str,
        object_name: str,
        action: str,
        status: str,
        details: Dict[str, Any],
    ) -> None:
        try:
            AuditService.log_event(
                db=db,
                action=f"mcp.{connector_slug}.{object_name}.{action}",
                tenant_id=credential.tenant_id,
                user_id=credential.user_id,
                resource="mcp_execution",
                resource_id=f"{connector_slug}:{object_name}",
                details={
                    "credential_id": credential.id,
                    "credential_name": credential.name,
                    "status": status,
                    **details,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to record audit log: {e}")
