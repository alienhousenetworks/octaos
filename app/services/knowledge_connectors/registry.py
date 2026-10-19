"""Adapter registry mapping connector types to their adapter implementations."""
from __future__ import annotations

from typing import Dict, Type
from app.services.knowledge_connectors.adapters.base import BaseConnectorAdapter
from app.services.knowledge_connectors.adapters.rest_api import RestApiAdapter
from app.services.knowledge_connectors.adapters.postgres import PostgresAdapter
from app.services.knowledge_connectors.errors import ConnectorError


class ConnectorAdapterRegistry:
    """Registry managing available source adapter singletons."""

    def __init__(self):
        self._adapters: Dict[str, BaseConnectorAdapter] = {
            "rest_api": RestApiAdapter(),
            "postgres": PostgresAdapter(),
            "postgresql": PostgresAdapter(),
            "supabase": PostgresAdapter(),
        }

    def register(self, connector_type: str, adapter: BaseConnectorAdapter) -> None:
        self._adapters[connector_type.lower()] = adapter

    def get(self, connector_type: str) -> BaseConnectorAdapter:
        adapter = self._adapters.get(connector_type.lower())
        if not adapter:
            raise ConnectorError(
                f"No adapter registered for connector type '{connector_type}'. Supported: {list(self._adapters.keys())}",
                code="UNSUPPORTED_CONNECTOR_TYPE",
            )
        return adapter


connector_registry = ConnectorAdapterRegistry()
