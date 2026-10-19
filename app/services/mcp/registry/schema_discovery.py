"""Schema discovery, fingerprinting, and drift detection registry service."""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.mcp import DynamicConnector, DynamicObjectDefinition
from app.services.mcp.connectors.base import ConnectorAdapter, ConnectorContext


def compute_schema_fingerprint(schema_json: Dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 hash of a JSON Schema definition."""
    canonical_str = json.dumps(schema_json, sort_keys=True)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


class SchemaDiscoveryService:
    """
    Syncs and version-tracks business objects discovered across connectors.
    Maintains the DynamicObjectDefinition catalog and flags schema drift.
    """

    @staticmethod
    async def sync_connector_schemas(
        db: Session,
        tenant_id: str,
        connector: DynamicConnector,
        adapter: ConnectorAdapter,
    ) -> List[DynamicObjectDefinition]:
        """
        Executes discovery on the adapter, creates or updates ObjectDefinitions,
        and flags drift if fields changed.
        """
        ctx = ConnectorContext(
            tenant_id=tenant_id,
            connector_slug=connector.slug,
            config={},
        )
        discovered_objects = await adapter.discover_objects(ctx)
        synced_records = []

        for meta in discovered_objects:
            fingerprint = compute_schema_fingerprint(meta.json_schema)

            existing = (
                db.query(DynamicObjectDefinition)
                .filter(
                    DynamicObjectDefinition.tenant_id == tenant_id,
                    DynamicObjectDefinition.connector_id == connector.id,
                    DynamicObjectDefinition.object_name == meta.object_name,
                )
                .first()
            )

            if existing:
                # Check for schema drift
                if existing.schema_fingerprint != fingerprint:
                    existing.is_stale = True
                    existing.schema_fingerprint = fingerprint
                    existing.schema_json = meta.json_schema
                    existing.supported_operations = meta.supported_operations
                    existing.relationships = meta.relationships
                    existing.updated_at = datetime.now(timezone.utc)
                synced_records.append(existing)
            else:
                new_def = DynamicObjectDefinition(
                    tenant_id=tenant_id,
                    connector_id=connector.id,
                    object_name=meta.object_name,
                    display_name=meta.display_name,
                    description=meta.description,
                    primary_key_field=meta.primary_key,
                    supported_operations=meta.supported_operations,
                    schema_fingerprint=fingerprint,
                    schema_json=meta.json_schema,
                    relationships=meta.relationships,
                    is_stale=False,
                )
                db.add(new_def)
                synced_records.append(new_def)

        connector.last_synced_at = datetime.now(timezone.utc)
        db.commit()
        return synced_records

    @staticmethod
    def get_or_register_default_octaos_connector(db: Session, tenant_id: str) -> DynamicConnector:
        """Ensures the core OctaOS connector is registered for the tenant."""
        conn = (
            db.query(DynamicConnector)
            .filter(
                DynamicConnector.tenant_id == tenant_id,
                DynamicConnector.slug == "octaos",
            )
            .first()
        )
        if not conn:
            conn = DynamicConnector(
                tenant_id=tenant_id,
                name="OctaOS Core Services",
                slug="octaos",
                connector_type="internal_octaos",
                is_read_only=False,
                status="active",
            )
            db.add(conn)
            db.commit()
            db.refresh(conn)
        return conn
