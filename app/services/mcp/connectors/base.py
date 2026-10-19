"""Abstract Base Class for Governed MCP Connector Adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConnectorContext(BaseModel):
    tenant_id: str
    connector_slug: str
    config: Dict[str, Any] = Field(default_factory=dict)
    credential_id: Optional[str] = None


class DiscoveredObjectMeta(BaseModel):
    object_name: str
    display_name: str
    description: Optional[str] = None
    primary_key: str = "id"
    supported_operations: List[str] = Field(default_factory=lambda: ["read", "query"])
    json_schema: Dict[str, Any]
    relationships: Dict[str, Any] = Field(default_factory=dict)


class ConnectorAdapter(ABC):
    """
    Standard interface that every data source adapter must implement.
    Allows OctaOS to discover, describe, query, and mutate arbitrary business data
    without hardcoding Pydantic schemas.
    """

    @abstractmethod
    async def discover_objects(self, ctx: ConnectorContext) -> List[DiscoveredObjectMeta]:
        """Inspect source and return all available business objects and their JSON schemas."""
        pass

    @abstractmethod
    async def describe_object(self, ctx: ConnectorContext, object_name: str) -> Optional[DiscoveredObjectMeta]:
        """Fetch latest schema definition and capabilities for a specific object."""
        pass

    @abstractmethod
    async def query_records(
        self,
        ctx: ConnectorContext,
        object_name: str,
        query: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a validated query using the safe typed query DSL.
        Returns: {"records": [...], "total_count": int, "has_more": bool, "cursor": str}
        """
        pass

    @abstractmethod
    async def get_record(
        self,
        ctx: ConnectorContext,
        object_name: str,
        record_id: str,
        fields: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a single record by primary key."""
        pass

    @abstractmethod
    async def create_record(
        self,
        ctx: ConnectorContext,
        object_name: str,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a new record and return the created data with server-assigned ID."""
        pass

    @abstractmethod
    async def update_record(
        self,
        ctx: ConnectorContext,
        object_name: str,
        record_id: str,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update an existing record and return the updated data."""
        pass

    @abstractmethod
    async def delete_record(
        self,
        ctx: ConnectorContext,
        object_name: str,
        record_id: str,
    ) -> bool:
        """Delete a record by primary key."""
        pass

    @abstractmethod
    async def invoke_action(
        self,
        ctx: ConnectorContext,
        action_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a domain business action (e.g. qualify_lead, reply_ticket, trigger_workflow)."""
        pass
