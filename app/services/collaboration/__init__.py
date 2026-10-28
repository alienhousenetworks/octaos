"""Bidirectional Universal AI Collaboration Engine for OctaOS."""
from app.services.collaboration.engine import AICollaborationEngine
from app.services.collaboration.provider_registry import AIProviderRegistry, ProviderDescriptor
from app.services.collaboration.contracts import (
    CollaborationTaskSubmitRequest,
    TaskStatusResponse,
    ExecutionBridgeRequest,
    ExecutionBridgeResponse,
    redact_sensitive_context,
)
from app.services.collaboration.orchestrator import (
    DelegationLoopError,
    DelegationLimitError,
    validate_delegation_safety,
    compute_task_fingerprint,
    dispatch_signed_webhook,
)
from app.services.collaboration.execution_bridge import ExecutionBridge
from app.services.collaboration.live_terminal import LiveTerminalManager, TerminalLogEntry, ProcessStatusResponse

__all__ = [
    "AICollaborationEngine",
    "AIProviderRegistry",
    "ProviderDescriptor",
    "CollaborationTaskSubmitRequest",
    "TaskStatusResponse",
    "ExecutionBridgeRequest",
    "ExecutionBridgeResponse",
    "redact_sensitive_context",
    "DelegationLoopError",
    "DelegationLimitError",
    "validate_delegation_safety",
    "compute_task_fingerprint",
    "dispatch_signed_webhook",
    "ExecutionBridge",
    "LiveTerminalManager",
    "TerminalLogEntry",
    "ProcessStatusResponse",
]
