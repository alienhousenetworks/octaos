"""FastAPI router for Governed Knowledge Connector Platform."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.base import User
from app.models.knowledge_connectors import (
    ConnectorAuditEvent,
    ConnectorConfigVersion,
    ConnectorExecution,
    ConnectorPermission,
    ConnectorSchemaVersion,
    KnowledgeConnector,
)
from app.services.knowledge_connectors.contracts import ExecutionContext
from app.services.knowledge_connectors.service import ConnectorService

router = APIRouter()


class CreateConnectorRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50)
    connector_type: str = Field(..., description="rest_api, postgres, google_sheets, etc.")
    description: Optional[str] = None


class ConfigureVersionRequest(BaseModel):
    endpoint_template: Optional[str] = None
    http_method: str = "GET"
    parameter_schema: Dict[str, Any] = Field(default_factory=dict)
    extraction_rules: Dict[str, Any] = Field(default_factory=dict)
    allowed_query_templates: List[str] = Field(default_factory=list)
    timeout_seconds: int = 10
    max_response_bytes: int = 2 * 1024 * 1024
    allow_redirects: bool = False
    cache_ttl_seconds: int = 300


class StoreSecretsRequest(BaseModel):
    secrets: Dict[str, Any]


class SetPermissionRequest(BaseModel):
    department: str = "general"
    agent_id: Optional[str] = None
    allowed_operations: List[str] = Field(default_factory=lambda: ["read"])
    permitted_fields: List[str] = Field(default_factory=list)
    denied_fields: List[str] = Field(default_factory=list)
    requires_human_approval: bool = False


class TestConnectorRequest(BaseModel):
    sample_params: Dict[str, Any] = Field(default_factory=dict)


@router.get("", response_model=List[Dict[str, Any]])
def list_connectors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connectors = db.query(KnowledgeConnector).filter_by(
        tenant_id=current_user.tenant_id,
        is_active=True,
    ).order_by(KnowledgeConnector.created_at.desc()).all()

    results = []
    for c in connectors:
        latest_schema = db.query(ConnectorSchemaVersion).filter_by(
            connector_id=c.id
        ).order_by(ConnectorSchemaVersion.observed_at.desc()).first()

        results.append({
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "connector_type": c.connector_type,
            "description": c.description,
            "state": c.state,
            "current_config_version": c.current_config_version,
            "schema_fingerprint": latest_schema.schema_fingerprint if latest_schema else None,
            "drift_detected": latest_schema.drift_detected if latest_schema else False,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return results


@router.post("", status_code=status.HTTP_201_CREATED)
def create_connector(
    payload: CreateConnectorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        connector = ConnectorService.create_connector(
            db=db,
            tenant_id=current_user.tenant_id,
            name=payload.name,
            slug=payload.slug,
            connector_type=payload.connector_type,
            description=payload.description,
        )
        return {
            "id": connector.id,
            "name": connector.name,
            "slug": connector.slug,
            "state": connector.state,
            "message": "Connector registered in draft state. Configure endpoint and test to activate.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{connector_id}")
def get_connector(
    connector_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connector = db.query(KnowledgeConnector).filter_by(
        id=connector_id,
        tenant_id=current_user.tenant_id,
    ).first()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    active_config = db.query(ConnectorConfigVersion).filter_by(
        connector_id=connector.id,
        version=connector.current_config_version,
    ).first()

    permissions = db.query(ConnectorPermission).filter_by(connector_id=connector.id).all()
    latest_schema = db.query(ConnectorSchemaVersion).filter_by(
        connector_id=connector.id
    ).order_by(ConnectorSchemaVersion.observed_at.desc()).first()

    return {
        "id": connector.id,
        "name": connector.name,
        "slug": connector.slug,
        "connector_type": connector.connector_type,
        "description": connector.description,
        "state": connector.state,
        "config": {
            "version": active_config.version if active_config else 1,
            "endpoint_template": active_config.endpoint_template if active_config else None,
            "http_method": active_config.http_method if active_config else "GET",
            "parameter_schema": active_config.parameter_schema if active_config else {},
            "allowed_query_templates": active_config.allowed_query_templates if active_config else [],
            "timeout_seconds": active_config.timeout_seconds if active_config else 10,
            "max_response_bytes": active_config.max_response_bytes if active_config else 2097152,
            "cache_ttl_seconds": active_config.cache_ttl_seconds if active_config else 300,
        },
        "permissions": [
            {
                "id": p.id,
                "department": p.department,
                "agent_id": p.agent_id,
                "allowed_operations": p.allowed_operations,
                "permitted_fields": p.permitted_fields,
                "denied_fields": p.denied_fields,
                "requires_human_approval": p.requires_human_approval,
            }
            for p in permissions
        ],
        "schema": {
            "observed_fields": latest_schema.observed_fields if latest_schema else {},
            "schema_fingerprint": latest_schema.schema_fingerprint if latest_schema else None,
            "drift_detected": latest_schema.drift_detected if latest_schema else False,
        },
    }


@router.put("/{connector_id}/config")
def update_config(
    connector_id: str,
    payload: ConfigureVersionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        config_ver = ConnectorService.configure_version(
            db=db,
            connector_id=connector_id,
            tenant_id=current_user.tenant_id,
            endpoint_template=payload.endpoint_template,
            http_method=payload.http_method,
            parameter_schema=payload.parameter_schema,
            extraction_rules=payload.extraction_rules,
            allowed_query_templates=payload.allowed_query_templates,
            timeout_seconds=payload.timeout_seconds,
            max_response_bytes=payload.max_response_bytes,
            allow_redirects=payload.allow_redirects,
            cache_ttl_seconds=payload.cache_ttl_seconds,
        )
        return {
            "version": config_ver.version,
            "message": f"Connector configuration updated to version {config_ver.version}.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{connector_id}/secrets")
def store_secrets(
    connector_id: str,
    payload: StoreSecretsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        ConnectorService.store_secrets(
            db=db,
            connector_id=connector_id,
            tenant_id=current_user.tenant_id,
            secret_payload=payload.secrets,
        )
        return {"status": "success", "message": "Credentials encrypted and stored in secret vault."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{connector_id}/permissions")
def set_permission(
    connector_id: str,
    payload: SetPermissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        perm = ConnectorService.set_permission(
            db=db,
            connector_id=connector_id,
            tenant_id=current_user.tenant_id,
            department=payload.department,
            agent_id=payload.agent_id,
            allowed_operations=payload.allowed_operations,
            permitted_fields=payload.permitted_fields,
            denied_fields=payload.denied_fields,
            requires_human_approval=payload.requires_human_approval,
        )
        return {"id": perm.id, "message": "Permission grant saved."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{connector_id}/test")
async def test_connector(
    connector_id: str,
    payload: TestConnectorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    context = ExecutionContext(
        tenant_id=current_user.tenant_id,
        acting_user_id=current_user.id,
        department="general",
        request_id=f"test_probe_{uuid.uuid4().hex[:8]}",
    )
    result = await ConnectorService.test_connector(
        db=db,
        connector_id=connector_id,
        context=context,
        sample_params=payload.sample_params,
    )
    return result.model_dump(mode="json")


@router.post("/{connector_id}/activate")
def activate_connector(
    connector_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connector = db.query(KnowledgeConnector).filter_by(
        id=connector_id,
        tenant_id=current_user.tenant_id,
    ).first()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    connector.state = "active"
    db.commit()
    return {"id": connector.id, "state": connector.state, "message": "Connector activated for agent queries."}


@router.post("/{connector_id}/suspend")
def suspend_connector(
    connector_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connector = db.query(KnowledgeConnector).filter_by(
        id=connector_id,
        tenant_id=current_user.tenant_id,
    ).first()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    connector.state = "suspended"
    db.commit()
    return {"id": connector.id, "state": connector.state, "message": "Connector suspended. All agent executions denied."}


@router.delete("/{connector_id}")
def delete_connector(
    connector_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connector = db.query(KnowledgeConnector).filter_by(
        id=connector_id,
        tenant_id=current_user.tenant_id,
    ).first()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    connector.is_active = False
    connector.state = "suspended"
    db.commit()
    return {"status": "success", "message": "Connector deleted."}


@router.get("/{connector_id}/executions")
def list_executions(
    connector_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = db.query(ConnectorExecution).filter_by(
        connector_id=connector_id,
        tenant_id=current_user.tenant_id,
    ).order_by(ConnectorExecution.executed_at.desc()).limit(limit).all()

    return [
        {
            "id": l.id,
            "request_id": l.request_id,
            "acting_agent_id": l.acting_agent_id,
            "status": l.status,
            "duration_ms": l.duration_ms,
            "bytes_received": l.bytes_received,
            "records_returned": l.records_returned,
            "truncated": l.truncated,
            "error_code": l.error_code,
            "executed_at": l.executed_at.isoformat() if l.executed_at else None,
        }
        for l in logs
    ]
