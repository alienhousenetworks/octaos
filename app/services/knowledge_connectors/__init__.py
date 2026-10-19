"""Governed Dynamic Knowledge Connector Platform package."""
from app.services.knowledge_connectors.contracts import (
    ConnectorResult,
    ConnectorInvocation,
    ConnectorProvenance,
    ExecutionContext,
    ConnectorAdapter,
)
from app.services.knowledge_connectors.service import ConnectorService
from app.services.knowledge_connectors.registry import connector_registry

__all__ = [
    "ConnectorResult",
    "ConnectorInvocation",
    "ConnectorProvenance",
    "ExecutionContext",
    "ConnectorAdapter",
    "ConnectorService",
    "connector_registry",
]
