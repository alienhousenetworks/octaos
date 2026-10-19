"""Central service coordinating control plane lifecycle and data plane query execution."""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.knowledge_connectors import (
    ConnectorAuditEvent,
    ConnectorConfigVersion,
    ConnectorExecution,
    ConnectorPermission,
    ConnectorSchemaVersion,
    KnowledgeConnector,
)
from app.services.knowledge_connectors.cache import ConnectorCacheManager
from app.services.knowledge_connectors.contracts import (
    ConnectorInvocation,
    ConnectorResult,
    ExecutionContext,
)
from app.services.knowledge_connectors.errors import (
    ConnectorNotFoundError,
    ConnectorPermissionDeniedError,
)
from app.services.knowledge_connectors.normalizer import (
    compute_schema_fingerprint,
    detect_schema_drift,
)
from app.services.knowledge_connectors.policy import ConnectorPolicyEngine
from app.services.knowledge_connectors.registry import connector_registry
from app.services.knowledge_connectors.secrets import ConnectorSecretVault
from app.services.knowledge_connectors.security.redaction import redact_dictionary


class ConnectorService:
    """Enterprise service orchestrating both Control Plane and Data Plane operations."""

    @staticmethod
    def create_connector(
        db: Session,
        tenant_id: str,
        name: str,
        slug: str,
        connector_type: str,
        description: Optional[str] = None,
    ) -> KnowledgeConnector:
        connector = KnowledgeConnector(
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            connector_type=connector_type.lower(),
            description=description,
            state="draft",
            current_config_version=1,
            is_active=True,
        )
        db.add(connector)
        db.commit()
        db.refresh(connector)

        # Audit creation
        audit = ConnectorAuditEvent(
            connector_id=connector.id,
            tenant_id=tenant_id,
            actor_type="user",
            actor_id="system_or_admin",
            event_type="created",
            event_details={"name": name, "type": connector_type, "slug": slug},
        )
        db.add(audit)
        db.commit()
        return connector

    @staticmethod
    def configure_version(
        db: Session,
        connector_id: str,
        tenant_id: str,
        endpoint_template: Optional[str] = None,
        http_method: str = "GET",
        parameter_schema: Optional[Dict[str, Any]] = None,
        extraction_rules: Optional[Dict[str, Any]] = None,
        allowed_query_templates: Optional[List[str]] = None,
        timeout_seconds: int = 10,
        max_response_bytes: int = 2 * 1024 * 1024,
        allow_redirects: bool = False,
        cache_ttl_seconds: int = 300,
    ) -> ConnectorConfigVersion:
        connector = db.query(KnowledgeConnector).filter_by(id=connector_id, tenant_id=tenant_id).first()
        if not connector:
            raise ConnectorNotFoundError(connector_id, tenant_id)

        existing_configs = db.query(ConnectorConfigVersion).filter_by(connector_id=connector.id).all()
        new_version_num = max([c.version for c in existing_configs], default=0) + 1

        config_ver = ConnectorConfigVersion(
            connector_id=connector.id,
            version=new_version_num,
            endpoint_template=endpoint_template,
            http_method=http_method,
            parameter_schema=parameter_schema or {},
            extraction_rules=extraction_rules or {},
            allowed_query_templates=allowed_query_templates or [],
            timeout_seconds=timeout_seconds,
            max_response_bytes=max_response_bytes,
            allow_redirects=allow_redirects,
            cache_ttl_seconds=cache_ttl_seconds,
        )
        connector.current_config_version = new_version_num
        db.add(config_ver)
        db.commit()
        db.refresh(config_ver)
        return config_ver

    @staticmethod
    def store_secrets(
        db: Session,
        connector_id: str,
        tenant_id: str,
        secret_payload: Dict[str, Any],
    ) -> None:
        connector = db.query(KnowledgeConnector).filter_by(id=connector_id, tenant_id=tenant_id).first()
        if not connector:
            raise ConnectorNotFoundError(connector_id, tenant_id)
        ConnectorSecretVault.store_secrets(db, connector, secret_payload)

    @staticmethod
    def set_permission(
        db: Session,
        connector_id: str,
        tenant_id: str,
        department: str = "general",
        agent_id: Optional[str] = None,
        allowed_operations: Optional[List[str]] = None,
        permitted_fields: Optional[List[str]] = None,
        denied_fields: Optional[List[str]] = None,
        requires_human_approval: bool = False,
    ) -> ConnectorPermission:
        connector = db.query(KnowledgeConnector).filter_by(id=connector_id, tenant_id=tenant_id).first()
        if not connector:
            raise ConnectorNotFoundError(connector_id, tenant_id)

        perm = ConnectorPermission(
            connector_id=connector.id,
            agent_id=agent_id,
            department=department,
            allowed_operations=allowed_operations or ["read"],
            permitted_fields=permitted_fields or [],
            denied_fields=denied_fields or [],
            requires_human_approval=requires_human_approval,
        )
        db.add(perm)
        db.commit()
        db.refresh(perm)
        return perm

    @classmethod
    async def test_connector(
        cls,
        db: Session,
        connector_id: str,
        context: ExecutionContext,
        sample_params: Optional[Dict[str, Any]] = None,
    ) -> ConnectorResult:
        connector = db.query(KnowledgeConnector).filter_by(id=connector_id, tenant_id=context.tenant_id).first()
        if not connector:
            raise ConnectorNotFoundError(connector_id, context.tenant_id)

        # Policy check in test mode
        decision = ConnectorPolicyEngine.evaluate(
            db, connector, context, operation="read", is_test_execution=True
        )
        if not decision.allowed:
            return ConnectorResult(
                status="denied",
                connector_id=connector_id,
                request_id=context.request_id,
                safe_error_code="TEST_POLICY_DENIED",
                safe_error_message=decision.reason,
                fetched_at=datetime.utcnow(),
            )

        active_config = db.query(ConnectorConfigVersion).filter_by(
            connector_id=connector.id,
            version=connector.current_config_version,
        ).first()
        config_dict = {
            "endpoint_template": active_config.endpoint_template if active_config else None,
            "http_method": active_config.http_method if active_config else "GET",
            "allowed_query_templates": active_config.allowed_query_templates if active_config else [],
            "timeout_seconds": active_config.timeout_seconds if active_config else context.timeout_seconds,
            "max_response_bytes": active_config.max_response_bytes if active_config else context.byte_budget,
            "allow_redirects": active_config.allow_redirects if active_config else False,
            "connector_id": connector.id,
            "sample_params": sample_params or {},
            "allow_http_for_testing": True,  # Enables localhost mock fixtures in test suites
        }

        secrets = ConnectorSecretVault.retrieve_secrets(db, connector.id)
        adapter = connector_registry.get(connector.connector_type)
        result = await adapter.test_connection(context, config_dict, secrets)

        # Record test outcome
        if result.status in ("success", "partial"):
            # Update schema version record
            fingerprint, fields = compute_schema_fingerprint(result.data)
            schema_ver = ConnectorSchemaVersion(
                connector_id=connector.id,
                schema_fingerprint=fingerprint,
                observed_fields=fields,
                drift_detected=False,
            )
            db.add(schema_ver)
            connector.state = "active"
            db.commit()

        return result

    @classmethod
    async def execute_query(
        cls,
        db: Session,
        connector_id: str,
        context: ExecutionContext,
        invocation: ConnectorInvocation,
    ) -> ConnectorResult:
        start_time = time.time()
        # 1. Resolve connector by ID or slug
        connector = db.query(KnowledgeConnector).filter(
            (KnowledgeConnector.id == connector_id) | (KnowledgeConnector.slug == connector_id),
            KnowledgeConnector.tenant_id == context.tenant_id,
        ).first()

        if not connector:
            raise ConnectorNotFoundError(connector_id, context.tenant_id)

        # 2. Central Policy Gate
        decision = ConnectorPolicyEngine.evaluate(
            db, connector, context, operation=invocation.operation
        )
        if not decision.allowed:
            # Audit denied attempt
            audit = ConnectorAuditEvent(
                connector_id=connector.id,
                tenant_id=context.tenant_id,
                actor_type="agent" if context.acting_agent_id else "user",
                actor_id=context.acting_agent_id or context.acting_user_id or "unknown",
                event_type="access_denied",
                event_details={"reason": decision.reason, "operation": invocation.operation},
            )
            db.add(audit)
            db.commit()

            return ConnectorResult(
                status="denied",
                connector_id=connector.id,
                request_id=context.request_id,
                safe_error_code="ACCESS_DENIED",
                safe_error_message=decision.reason,
                fetched_at=datetime.utcnow(),
            )

        # 3. Cache Check (if force_refresh is False)
        if not invocation.force_refresh:
            cached_result = ConnectorCacheManager.get(db, connector.id, context, invocation.params)
            if cached_result:
                return cached_result

        # 4. Resolve Active Config and Secrets
        active_config = db.query(ConnectorConfigVersion).filter_by(
            connector_id=connector.id,
            version=connector.current_config_version,
        ).first()

        config_dict = {
            "endpoint_template": active_config.endpoint_template if active_config else None,
            "http_method": active_config.http_method if active_config else "GET",
            "allowed_query_templates": active_config.allowed_query_templates if active_config else [],
            "timeout_seconds": active_config.timeout_seconds if active_config else context.timeout_seconds,
            "max_response_bytes": active_config.max_response_bytes if active_config else context.byte_budget,
            "allow_redirects": active_config.allow_redirects if active_config else False,
            "connector_id": connector.id,
        }

        secrets = ConnectorSecretVault.retrieve_secrets(db, connector.id)

        # 5. Execute via Adapter
        adapter = connector_registry.get(connector.connector_type)
        result = await adapter.execute(context, config_dict, secrets, invocation)

        # 6. Apply Redaction and Field Masking
        if result.data and decision.denied_fields:
            result.data = redact_dictionary(result.data, denied_fields=decision.denied_fields)

        # 7. Schema Drift Detection against Baseline
        baseline_schema = db.query(ConnectorSchemaVersion).filter_by(
            connector_id=connector.id
        ).order_by(ConnectorSchemaVersion.observed_at.desc()).first()

        drift_detected = False
        if baseline_schema and result.data:
            _, current_fields = compute_schema_fingerprint(result.data)
            drift, warnings = detect_schema_drift(current_fields, baseline_schema.observed_fields or {})
            if drift:
                drift_detected = True
                result.warnings.extend(warnings)

        duration_ms = int((time.time() - start_time) * 1000)

        # 8. Record Execution Log & Telemetry
        execution_log = ConnectorExecution(
            connector_id=connector.id,
            tenant_id=context.tenant_id,
            request_id=context.request_id,
            acting_agent_id=context.acting_agent_id,
            acting_user_id=context.acting_user_id,
            status=result.status,
            duration_ms=duration_ms,
            bytes_received=len(str(result.data)),
            records_returned=result.records_returned,
            truncated=result.truncated,
            truncation_reason=result.truncation_reason,
            error_code=result.safe_error_code,
            error_message=result.safe_error_message,
            provenance=[p.model_dump(mode="json") for p in result.provenance],
        )
        db.add(execution_log)

        # 9. Cache successful results
        ttl = active_config.cache_ttl_seconds if active_config else 300
        ConnectorCacheManager.set(db, connector.id, context, invocation.params, result, ttl_seconds=ttl)

        db.commit()
        return result
