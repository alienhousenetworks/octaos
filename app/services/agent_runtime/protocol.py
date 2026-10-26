"""Provider-neutral agent execution contract for OctaOS.

Adapters return structured outcomes and sanitized progress events. This module
intentionally does not expose model chain-of-thought or provider-specific SDKs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence
from uuid import uuid4


class AgentEventType(str, Enum):
    RUN_STARTED = "run.started"
    PROGRESS = "run.progress"
    TOOL_REQUESTED = "tool.requested"
    TOOL_SUCCEEDED = "tool.succeeded"
    TOOL_FAILED = "tool.failed"
    APPROVAL_REQUIRED = "approval.required"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    RUN_CANCELLED = "run.cancelled"


_SENSITIVE_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/-]+=*"),
)


def sanitize_public_text(value: str, limit: int = 2000) -> str:
    """Redact common credential-shaped strings and bound user-facing text."""
    result = str(value)
    for pattern in _SENSITIVE_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result[:limit]


@dataclass(frozen=True)
class AgentEvent:
    tenant_id: str
    run_id: str
    event_type: AgentEventType
    message: str
    agent_id: str | None = None
    sequence: int = 0
    payload: Mapping[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: int = 1

    def to_public_dict(self) -> dict[str, Any]:
        """Return a safe UI/SSE representation; never include hidden reasoning."""
        safe_payload: dict[str, Any] = {}
        for key, value in self.payload.items():
            if any(term in key.lower() for term in ("chain_of_thought", "private_reasoning", "system_prompt", "api_key", "token", "secret", "password")):
                continue
            if isinstance(value, str):
                safe_payload[key] = sanitize_public_text(value, 1000)
            elif isinstance(value, (int, float, bool)) or value is None:
                safe_payload[key] = value
            elif isinstance(value, (list, tuple)) and all(isinstance(item, (str, int, float, bool)) for item in value):
                safe_payload[key] = [sanitize_public_text(item, 300) if isinstance(item, str) else item for item in value[:50]]
        return {
            "event_id": self.event_id,
            "schema_version": self.schema_version,
            "tenant_id": self.tenant_id,
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "sequence": self.sequence,
            "type": self.event_type.value,
            "message": sanitize_public_text(self.message),
            "payload": safe_payload,
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass(frozen=True)
class AgentRequest:
    tenant_id: str
    run_id: str
    agent_id: str
    goal: str
    context: Mapping[str, Any] = field(default_factory=dict)
    allowed_tools: Sequence[str] = field(default_factory=tuple)
    max_output_tokens: int = 4096
    budget_limit: float | None = None
    provider: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    task_type: str = "general"
    allowed_providers: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class AgentOutcome:
    status: str
    output: str | None = None
    evidence: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    provider: str = "unknown"
    model: str = "unknown"
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"completed", "failed", "cancelled", "awaiting_approval"}:
            raise ValueError("Unsupported agent outcome status.")
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise ValueError("Token usage cannot be negative.")
        if self.cost is not None and self.cost < 0:
            raise ValueError("Cost cannot be negative.")
        if self.status == "completed" and not self.output and not self.evidence:
            raise ValueError("Completed outcomes require output or evidence.")


class AgentProviderAdapter(Protocol):
    """Provider adapter interface implemented by OpenAI/Anthropic/Gemini/etc."""

    provider_name: str

    async def execute(self, request: AgentRequest) -> AgentOutcome:
        """Execute a request within supplied limits and return a normalized outcome."""
        ...


def verify_acceptance(outcome: AgentOutcome, *, evidence_required: bool = True) -> bool:
    """Conservative success gate; provider claims alone are not verification."""
    if outcome.status != "completed":
        return False
    if evidence_required:
        return bool(outcome.evidence)
    return bool(outcome.output or outcome.evidence)
