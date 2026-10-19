"""Structured error hierarchy for the Governed Dynamic Knowledge Connector Platform."""
from __future__ import annotations
from typing import Optional


class ConnectorError(Exception):
    """Base error for all connector operations."""
    def __init__(self, message: str, code: str = "CONNECTOR_ERROR", details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class ConnectorSecurityError(ConnectorError):
    """Security violation such as unauthorized egress, scheme prohibition, or credential leakage."""
    def __init__(self, message: str, code: str = "SECURITY_VIOLATION", details: Optional[dict] = None):
        super().__init__(message, code=code, details=details)


class SSRFProtectionError(ConnectorSecurityError):
    """Attempted access to loopback, private, link-local, multicast, or cloud metadata endpoints."""
    def __init__(self, message: str, ip: Optional[str] = None, host: Optional[str] = None):
        super().__init__(
            message=message,
            code="SSRF_DESTINATION_FORBIDDEN",
            details={"ip": ip, "host": host},
        )


class ConnectorNotFoundError(ConnectorError):
    """Connector not found or not owned by the requested tenant."""
    def __init__(self, connector_id: str, tenant_id: str):
        super().__init__(
            message=f"Connector '{connector_id}' not found for tenant '{tenant_id}'.",
            code="CONNECTOR_NOT_FOUND",
            details={"connector_id": connector_id, "tenant_id": tenant_id},
        )


class ConnectorPermissionDeniedError(ConnectorSecurityError):
    """Acting agent or user does not possess required department/tool grants."""
    def __init__(self, message: str, connector_id: str, agent_id: Optional[str] = None):
        super().__init__(
            message=message,
            code="ACCESS_DENIED",
            details={"connector_id": connector_id, "agent_id": agent_id},
        )


class ConnectorTimeoutError(ConnectorError):
    """Connector execution exceeded configured deadline."""
    def __init__(self, timeout_seconds: int, connector_id: str):
        super().__init__(
            message=f"Connector execution timed out after {timeout_seconds}s.",
            code="EXECUTION_TIMEOUT",
            details={"timeout_seconds": timeout_seconds, "connector_id": connector_id},
        )


class ConnectorBudgetExceededError(ConnectorError):
    """Response exceeded streaming byte, record, or nesting depth limits."""
    def __init__(self, message: str, bytes_read: int, byte_budget: int):
        super().__init__(
            message=message,
            code="BYTE_BUDGET_EXCEEDED",
            details={"bytes_read": bytes_read, "byte_budget": byte_budget},
        )


class ConnectorSchemaDriftError(ConnectorError):
    """Expected fields are missing or type definitions have altered upstream."""
    def __init__(self, message: str, missing_fields: list[str]):
        super().__init__(
            message=message,
            code="SCHEMA_DRIFT_DETECTED",
            details={"missing_fields": missing_fields},
        )
