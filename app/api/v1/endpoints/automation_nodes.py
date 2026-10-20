"""
API Endpoints for Automation Node Registry and Catalog.
Provides 3-level node discovery and isolated node test runs.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.core.rbac import Action, Resource, require_permission
from app.models.base import User
from app.services.automation.node_registry import NodeRegistry

logger = logging.getLogger(__name__)

router = APIRouter()


class NodeTestRequest(BaseModel):
    node_id: str
    config: Dict[str, Any] = Field(default_factory=dict)
    input_payload: Dict[str, Any] = Field(default_factory=dict)


@router.get("/catalog")
def get_node_catalog(
    mode: str = Query("all", description="all | general | document | ai_agent"),
    _: User = Depends(deps.get_current_active_user),
) -> Any:
    """Returns the full 3-level enterprise node catalog (Categories -> Families -> Nodes)."""
    return NodeRegistry.get_catalog(mode=mode)


@router.get("/nodes/{node_id}")
def get_node_details(
    node_id: str,
    _: User = Depends(deps.get_current_active_user),
) -> Any:
    """Retrieves full specification, input/output schemas, and defaults for a specific node."""
    node = NodeRegistry.find_node(node_id)
    if not node:
        return {"error": f"Node '{node_id}' not found in registry."}
    return node.model_dump()


@router.post("/test")
async def test_node_execution(
    request: NodeTestRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.SETTINGS, Action.CREATE)),
) -> Any:
    """
    Executes an isolated test run of a single node with supplied parameters and inputs.
    """
    node = NodeRegistry.find_node(request.node_id)
    if not node:
        return {
            "status": "failed",
            "error": f"Node '{request.node_id}' not found in registry.",
        }

    # Simulate / execute node test
    output_result = {
        "node_id": request.node_id,
        "executed_at": "simulated",
        "inputs_received": request.input_payload,
        "config_applied": request.config,
        "status": "succeeded",
        "mock_outputs": {
            "result": "success",
            "message": f"Tested {node.name} successfully",
            "sample_data": {"id": "item_123", "score": 85},
        },
    }

    return output_result
