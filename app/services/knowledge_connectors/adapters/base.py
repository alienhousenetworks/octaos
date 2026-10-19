"""Base abstract adapter defining execution contracts."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict
from app.services.knowledge_connectors.contracts import (
    ConnectorAdapter,
    ConnectorInvocation,
    ConnectorResult,
    ExecutionContext,
)


class BaseConnectorAdapter(ABC):
    """Abstract base class for all connector source adapters."""

    @abstractmethod
    async def validate_config(self, config: Dict[str, Any]) -> None:
        """Validates configuration parameters and boundaries."""
        pass

    @abstractmethod
    async def test_connection(
        self,
        context: ExecutionContext,
        config: Dict[str, Any],
        secrets: Dict[str, Any],
    ) -> ConnectorResult:
        """Executes test probe and returns schema fingerprint."""
        pass

    @abstractmethod
    async def execute(
        self,
        context: ExecutionContext,
        config: Dict[str, Any],
        secrets: Dict[str, Any],
        invocation: ConnectorInvocation,
    ) -> ConnectorResult:
        """Executes authorized bounded retrieval."""
        pass

    @abstractmethod
    async def health_check(
        self,
        context: ExecutionContext,
        config: Dict[str, Any],
        secrets: Dict[str, Any],
    ) -> bool:
        """Liveness check."""
        pass
