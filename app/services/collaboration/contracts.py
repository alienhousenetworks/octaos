"""Shared Task Contracts and Data Models for Universal Bidirectional AI Collaboration."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


SENSITIVE_KEY_PATTERNS = [
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"auth(?:orization)?", re.IGNORECASE),
    re.compile(r"private[_-]?key", re.IGNORECASE),
    re.compile(r"bearer", re.IGNORECASE),
    re.compile(r"session", re.IGNORECASE),
]

SENSITIVE_VALUE_REGEXES = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"xai-[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"gsk_[a-zA-Z0-9]{20,}", re.IGNORECASE),
]


def redact_sensitive_context(data: Any) -> Any:
    """
    Recursively redacts sensitive API keys, secrets, tokens, and credentials
    from context dictionaries before external transmission.
    """
    if isinstance(data, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in data.items():
            if any(pat.search(str(k)) for pat in SENSITIVE_KEY_PATTERNS):
                cleaned[k] = "[REDACTED_SECRET]"
            else:
                cleaned[k] = redact_sensitive_context(v)
        return cleaned
    elif isinstance(data, list):
        return [redact_sensitive_context(item) for item in data]
    elif isinstance(data, str):
        val = data
        for reg in SENSITIVE_VALUE_REGEXES:
            val = reg.sub("[REDACTED_KEY]", val)
        return val
    return data


class TaskInputReference(BaseModel):
    name: str
    type: str = Field(description="'media', 'document', 'url', 'dataset', 'code'")
    url: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CollaborationTaskSubmitRequest(BaseModel):
    """External client submission request schema."""
    target_employee: Optional[str] = Field(
        default="sales",
        description="Target OctaOS AI Employee: 'marketing', 'sales', 'support', 'hr', 'ceo', or 'orchestrator'"
    )
    target_provider: Optional[str] = Field(
        default=None,
        description="Optional preferred external provider for outbound delegation (e.g. 'claude', 'grok', 'openai')"
    )
    target_capability: Optional[str] = Field(
        default="execute_task",
        description="Requested capability: 'market_research', 'social_publish', 'code_review', 'lead_qualification', etc."
    )
    task_description: str = Field(description="Clear instructions and objectives for the task")
    context: Dict[str, Any] = Field(default_factory=dict, description="Task context data")
    input_references: List[TaskInputReference] = Field(default_factory=list, description="Media or document attachments")
    output_schema: Optional[Dict[str, Any]] = Field(default=None, description="Expected JSON output schema contract")
    permissions: List[str] = Field(default_factory=list, description="Explicit permitted actions")
    parent_task_id: Optional[str] = Field(default=None, description="Parent task correlation if subtask")
    cost_limit_usd: float = Field(default=2.0, description="Maximum cost ceiling in USD")
    timeout_seconds: int = Field(default=90, description="Task execution timeout in seconds")
    async_execution: bool = Field(default=False, description="Whether to execute asynchronously in the background")
    webhook_url: Optional[str] = Field(default=None, description="Signed webhook destination on completion")
    idempotency_key: Optional[str] = Field(default=None, description="Client idempotency key for replay prevention")


class TaskStatusResponse(BaseModel):
    task_id: str
    parent_task_id: Optional[str] = None
    correlation_id: str
    tenant_id: str
    source_agent: str
    target_provider: Optional[str] = None
    target_employee: Optional[str] = None
    target_capability: Optional[str] = None
    task_description: str
    status: str = Field(description="'queued', 'processing', 'completed', 'failed', 'cancelled', 'waiting_approval', 'verified'")
    lineage: List[str] = Field(default_factory=list)
    depth: int = 0
    cost_spent_usd: float = 0.0
    result: Optional[Dict[str, Any]] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    error_details: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None
    usage_metadata: Optional[Dict[str, Any]] = None
    created_at: str
    completed_at: Optional[str] = None


class ExecutionBridgeRequest(BaseModel):
    """
    Request from an external or internal AI to execute a proposed action through
    OctaOS's verified tool execution bridge.
    """
    task_id: str = Field(description="Associated collaboration task ID")
    proposed_tool: str = Field(description="OctaOS registered tool name, e.g. 'octaos_social_publish_post'")
    action_type: str = Field(default="tool_execution", description="Policy action category")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Action arguments")
    intent_description: str = Field(description="Why this action is proposed")
    confidence: Optional[float] = Field(default=None, description="Caller confidence scored against the tenant auto-execution policy")
    idempotency_key: Optional[str] = None


class ExecutionBridgeResponse(BaseModel):
    task_id: str
    status: str = Field(description="'executed', 'waiting_approval', 'blocked', 'failed'")
    verified: bool
    policy_decision: str
    approval_request_id: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    execution_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
