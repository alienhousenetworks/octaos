"""Universal typed connector contracts and protocols for OctaOS."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Protocol, runtime_checkable
from pydantic import BaseModel, Field


ExecutionStatus = Literal[
    "success",
    "partial",
    "stale",
    "denied",
    "timeout",
    "error",
]


class ConnectorProvenance(BaseModel):
    """Immutable audit & provenance reference for retrieved data."""
    source_type: str
    endpoint_or_resource: str
    record_reference: Optional[str] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    freshness_seconds: Optional[int] = None
    schema_fingerprint: str = ""


class ConnectorResult(BaseModel):
    """Universal bounded execution envelope for all data sources."""
    status: ExecutionStatus
    connector_id: str
    request_id: str
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    source_version: Optional[str] = None
    data: Any = None
    records_returned: int = 0
    truncated: bool = False
    truncation_reason: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    provenance: List[ConnectorProvenance] = Field(default_factory=list)
    safe_error_code: Optional[str] = None
    safe_error_message: Optional[str] = None


class ConnectorInvocation(BaseModel):
    """Parameters passed by an agent or user to query a connector."""
    connector_id: str
    operation: str = "read"
    params: Dict[str, Any] = Field(default_factory=dict)
    force_refresh: bool = False
    max_records: int = 100


class ExecutionContext(BaseModel):
    """Authenticated runtime identity and governance parameters."""
    tenant_id: str
    acting_agent_id: Optional[str] = None
    acting_user_id: Optional[str] = None
    department: str = "general"
    request_id: str
    timeout_seconds: int = 10
    byte_budget: int = 2 * 1024 * 1024  # 2MB default streaming limit


@runtime_checkable
class ConnectorAdapter(Protocol):
    """Universal protocol implemented by all source adapters."""

    async def validate_config(self, config: Dict[str, Any]) -> None:
        """Validates configuration parameters and security bounds."""
        ...

    async def test_connection(
        self,
        context: ExecutionContext,
        config: Dict[str, Any],
        secrets: Dict[str, Any],
    ) -> ConnectorResult:
        """Executes a non-destructive test handshake and infers initial schema."""
        ...

    async def execute(
        self,
        context: ExecutionContext,
        config: Dict[str, Any],
        secrets: Dict[str, Any],
        invocation: ConnectorInvocation,
    ) -> ConnectorResult:
        """Executes authorized bounded retrieval and returns a typed ConnectorResult."""
        ...

    async def health_check(
        self,
        context: ExecutionContext,
        config: Dict[str, Any],
        secrets: Dict[str, Any],
    ) -> bool:
        """Periodic liveness probe for monitoring."""
        ...
