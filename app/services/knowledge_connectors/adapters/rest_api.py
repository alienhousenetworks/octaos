"""Governed REST API adapter with safe egress, declared parameters, and streaming bounds."""
from __future__ import annotations

import json
import urllib.parse
from datetime import datetime
from typing import Any, Dict
import httpx

from app.services.knowledge_connectors.adapters.base import BaseConnectorAdapter
from app.services.knowledge_connectors.contracts import (
    ConnectorInvocation,
    ConnectorProvenance,
    ConnectorResult,
    ExecutionContext,
)
from app.services.knowledge_connectors.errors import (
    ConnectorError,
    ConnectorSecurityError,
    SSRFProtectionError,
)
from app.services.knowledge_connectors.normalizer import compute_schema_fingerprint
from app.services.knowledge_connectors.security.egress import SafeHTTPClient
from app.services.knowledge_connectors.security.streaming import read_stream_bounded


class RestApiAdapter(BaseConnectorAdapter):
    """Adapter for executing external HTTP REST APIs with strict egress security."""

    async def validate_config(self, config: Dict[str, Any]) -> None:
        template = config.get("endpoint_template")
        if not template:
            raise ConnectorError("Missing 'endpoint_template' in REST configuration.", code="INVALID_CONFIG")
        parsed = urllib.parse.urlparse(template)
        if not parsed.scheme or not parsed.netloc:
            raise ConnectorError(f"Invalid URL template: '{template}'", code="INVALID_CONFIG")

    async def test_connection(
        self,
        context: ExecutionContext,
        config: Dict[str, Any],
        secrets: Dict[str, Any],
    ) -> ConnectorResult:
        # Build test invocation with sample or empty params
        test_invocation = ConnectorInvocation(
            connector_id=config.get("connector_id", "test_probe"),
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
        endpoint_template = config.get("endpoint_template", "")
        http_method = config.get("http_method", "GET").upper()
        max_bytes = config.get("max_response_bytes", context.byte_budget)
        timeout_seconds = config.get("timeout_seconds", context.timeout_seconds)
        allow_redirects = config.get("allow_redirects", False)
        allow_http_for_testing = config.get("allow_http_for_testing", False)

        # 1. Parameter Substitution
        # Only substitute declared parameters, escape inputs safely
        url = endpoint_template
        unmatched_params = {}
        for param_key, param_val in invocation.params.items():
            token_bracket = f"{{{param_key}}}"
            token_colon = f":{param_key}"
            val_escaped = urllib.parse.quote(str(param_val))
            if token_bracket in url:
                url = url.replace(token_bracket, val_escaped)
            elif token_colon in url:
                url = url.replace(token_colon, val_escaped)
            else:
                unmatched_params[param_key] = param_val

        # If HTTP GET and leftover params, append as query string
        if http_method == "GET" and unmatched_params:
            delim = "&" if "?" in url else "?"
            query_str = urllib.parse.urlencode(unmatched_params)
            url = f"{url}{delim}{query_str}"

        # 2. Prepare Authentication Headers
        headers = config.get("headers", {}).copy()
        auth_type = secrets.get("auth_type", "bearer").lower()
        if auth_type == "bearer" and secrets.get("bearer_token"):
            headers["Authorization"] = f"Bearer {secrets['bearer_token']}"
        elif auth_type == "custom_header" and secrets.get("header_name") and secrets.get("header_value"):
            headers[secrets["header_name"]] = secrets["header_value"]
        elif auth_type == "basic" and secrets.get("username") and secrets.get("password"):
            import base64
            userpass = f"{secrets['username']}:{secrets['password']}"
            encoded = base64.b64encode(userpass.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        elif secrets.get("raw_token"):
            headers["Authorization"] = f"Bearer {secrets['raw_token']}"

        headers.setdefault("Accept", "application/json")
        headers.setdefault("User-Agent", "OctaOS-Governed-Connector/1.0")

        # 3. Safe Outbound Execution
        client = SafeHTTPClient(
            timeout_seconds=float(timeout_seconds),
            allow_redirects=allow_redirects,
            allow_http_for_testing=allow_http_for_testing,
        )

        try:
            resp = await client.execute_request(
                method=http_method,
                url=url,
                headers=headers,
            )

            # Check status code
            if resp.status_code >= 400:
                return ConnectorResult(
                    status="error",
                    connector_id=invocation.connector_id,
                    request_id=context.request_id,
                    safe_error_code=f"HTTP_{resp.status_code}",
                    safe_error_message=f"Upstream returned HTTP {resp.status_code}",
                    fetched_at=datetime.utcnow(),
                )

            # 4. Stream response bounded by max_bytes
            raw_bytes, truncated, reason = await read_stream_bounded(resp, max_bytes=max_bytes)

            try:
                data = json.loads(raw_bytes.decode("utf-8"))
            except Exception:
                data = raw_bytes.decode("utf-8", errors="replace")

            records_count = len(data) if isinstance(data, list) else (1 if data else 0)
            fingerprint, _ = compute_schema_fingerprint(data)

            provenance = [
                ConnectorProvenance(
                    source_type="rest_api",
                    endpoint_or_resource=url.split("?")[0],
                    fetched_at=datetime.utcnow(),
                    schema_fingerprint=fingerprint,
                )
            ]

            warnings = []
            if truncated:
                warnings.append(reason or "Response was truncated to fit byte limits.")

            return ConnectorResult(
                status="partial" if truncated else "success",
                connector_id=invocation.connector_id,
                request_id=context.request_id,
                fetched_at=datetime.utcnow(),
                data=data,
                records_returned=records_count,
                truncated=truncated,
                truncation_reason=reason,
                warnings=warnings,
                provenance=provenance,
            )

        except SSRFProtectionError as ssrf_err:
            return ConnectorResult(
                status="denied",
                connector_id=invocation.connector_id,
                request_id=context.request_id,
                safe_error_code="SSRF_DESTINATION_FORBIDDEN",
                safe_error_message=str(ssrf_err),
                fetched_at=datetime.utcnow(),
            )
        except httpx.TimeoutException:
            return ConnectorResult(
                status="timeout",
                connector_id=invocation.connector_id,
                request_id=context.request_id,
                safe_error_code="UPSTREAM_TIMEOUT",
                safe_error_message=f"Upstream API timed out after {timeout_seconds}s.",
                fetched_at=datetime.utcnow(),
            )
        except Exception as e:
            return ConnectorResult(
                status="error",
                connector_id=invocation.connector_id,
                request_id=context.request_id,
                safe_error_code="EXECUTION_FAILED",
                safe_error_message=f"Connector call failed: {str(e)[:200]}",
                fetched_at=datetime.utcnow(),
            )

    async def health_check(
        self,
        context: ExecutionContext,
        config: Dict[str, Any],
        secrets: Dict[str, Any],
    ) -> bool:
        try:
            res = await self.test_connection(context, config, secrets)
            return res.status in ("success", "partial")
        except Exception:
            return False
