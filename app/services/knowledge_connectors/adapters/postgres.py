"""Read-only PostgreSQL adapter with approved query templates and timeout guards."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy import create_engine, text

from app.services.knowledge_connectors.adapters.base import BaseConnectorAdapter
from app.services.knowledge_connectors.contracts import (
    ConnectorInvocation,
    ConnectorProvenance,
    ConnectorResult,
    ExecutionContext,
)
from app.services.knowledge_connectors.errors import ConnectorError, ConnectorSecurityError
from app.services.knowledge_connectors.normalizer import compute_schema_fingerprint

DANGEROUS_SQL_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|CREATE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)


class PostgresAdapter(BaseConnectorAdapter):
    """Adapter for executing governed, read-only SQL queries against PostgreSQL/Supabase."""

    async def validate_config(self, config: Dict[str, Any]) -> None:
        templates = config.get("allowed_query_templates", [])
        if not templates:
            raise ConnectorError(
                "PostgreSQL connector requires at least one approved query template.",
                code="INVALID_CONFIG",
            )
        for t in templates:
            if DANGEROUS_SQL_PATTERNS.search(t):
                raise ConnectorSecurityError(
                    f"Forbidden write or DDL statement detected in query template: {t}",
                    code="SQL_WRITE_FORBIDDEN",
                )

    async def test_connection(
        self,
        context: ExecutionContext,
        config: Dict[str, Any],
        secrets: Dict[str, Any],
    ) -> ConnectorResult:
        test_invocation = ConnectorInvocation(
            connector_id=config.get("connector_id", "db_probe"),
            operation="read",
            params=config.get("sample_params", {}),
        )
        return await self.execute(context, config, secrets, test_invocation)

    async def execute(
        self,
        context: ExecutionContext,
        config: Dict[str, Any],
        secrets: Dict[str, Any],
        invocation: ConnectorInvocation,
    ) -> ConnectorResult:
        db_uri = secrets.get("connection_string") or secrets.get("database_url")
        if not db_uri:
            return ConnectorResult(
                status="error",
                connector_id=invocation.connector_id,
                request_id=context.request_id,
                safe_error_code="MISSING_CREDENTIALS",
                safe_error_message="Database connection string not configured.",
                fetched_at=datetime.utcnow(),
            )

        query_templates = config.get("allowed_query_templates", [])
        template_name_or_index = invocation.params.get("template_index", 0)
        try:
            sql_template = query_templates[int(template_name_or_index)]
        except Exception:
            sql_template = query_templates[0] if query_templates else "SELECT 1"

        if DANGEROUS_SQL_PATTERNS.search(sql_template):
            return ConnectorResult(
                status="denied",
                connector_id=invocation.connector_id,
                request_id=context.request_id,
                safe_error_code="SQL_INJECTION_OR_WRITE_DETECTED",
                safe_error_message="Query contains prohibited SQL modification keywords.",
                fetched_at=datetime.utcnow(),
            )

        max_rows = min(invocation.max_records, 100)
        statement_timeout_ms = min(context.timeout_seconds * 1000, 10000)

        try:
            # Create isolated read-only engine
            engine = create_engine(
                db_uri,
                pool_pre_ping=True,
                execution_options={"isolation_level": "AUTOCOMMIT"},
            )
            with engine.connect() as conn:
                # Set session bounds
                conn.execute(text("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;"))
                conn.execute(text(f"SET statement_timeout = '{statement_timeout_ms}ms';"))
                conn.execute(text("SET lock_timeout = '2000ms';"))

                # Filter parameters to only those matching query bindings
                param_bindings = {k: v for k, v in invocation.params.items() if k != "template_index"}
                cursor = conn.execute(text(sql_template), param_bindings)
                rows = cursor.fetchmany(max_rows + 1)
                column_keys = list(cursor.keys())

            truncated = len(rows) > max_rows
            returned_rows = rows[:max_rows]

            # Convert to dictionary records
            data: List[Dict[str, Any]] = [
                {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in zip(column_keys, row)}
                for row in returned_rows
            ]

            fingerprint, _ = compute_schema_fingerprint(data)
            provenance = [
                ConnectorProvenance(
                    source_type="postgres",
                    endpoint_or_resource="read_only_postgres_replica",
                    fetched_at=datetime.utcnow(),
                    schema_fingerprint=fingerprint,
                )
            ]

            warnings = []
            if truncated:
                warnings.append(f"Result set truncated to maximum limit of {max_rows} records.")

            return ConnectorResult(
                status="partial" if truncated else "success",
                connector_id=invocation.connector_id,
                request_id=context.request_id,
                data=data,
                records_returned=len(data),
                truncated=truncated,
                truncation_reason="max_rows_exceeded" if truncated else None,
                warnings=warnings,
                provenance=provenance,
                fetched_at=datetime.utcnow(),
            )

        except Exception as err:
            return ConnectorResult(
                status="error",
                connector_id=invocation.connector_id,
                request_id=context.request_id,
                safe_error_code="DB_QUERY_FAILED",
                safe_error_message=f"Database query execution failed: {str(err)[:200]}",
                fetched_at=datetime.utcnow(),
            )

    async def health_check(
        self,
        context: ExecutionContext,
        config: Dict[str, Any],
        secrets: Dict[str, Any],
    ) -> bool:
        res = await self.test_connection(context, config, secrets)
        return res.status in ("success", "partial")
