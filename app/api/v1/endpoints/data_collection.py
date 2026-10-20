"""Data Collection & Apify Web Automation Endpoints.
Provides tenant-isolated access to approved Actors, budget enforcement, and collection jobs.
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.integrations.apify.actor_registry import ActorRegistry
from app.integrations.apify.client import ApifyTransportClient
from app.integrations.apify.schemas import (
    ActorCapability,
    ApprovedActorDefinition,
    CollectionJobRequest,
    CollectionJobResponse,
)

router = APIRouter()


@router.get("/actors", response_model=List[ApprovedActorDefinition])
def list_approved_actors(
    capability: Optional[ActorCapability] = None,
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """Lists all approved Actors available for autonomous or interactive data collection."""
    return ActorRegistry.list(capability=capability)


@router.get("/actors/{actor_key}", response_model=ApprovedActorDefinition)
def get_actor_definition(
    actor_key: str,
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """Retrieves full details and input schema constraints for an approved Actor."""
    actor = ActorRegistry.get(actor_key)
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Actor '{actor_key}' is not approved or is currently disabled.",
        )
    return actor


@router.get("/status")
def get_apify_integration_status(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """Returns credential status and available collection capabilities for the tenant."""
    from app.services.credentials import get_decrypted_credential
    tenant_token, _ = get_decrypted_credential(db, tenant_id, "apify")
    resolved_token = ApifyTransportClient.resolve_token(db=db, tenant_id=tenant_id)

    return {
        "tenant_id": tenant_id,
        "has_tenant_credential": bool(tenant_token),
        "is_callable": bool(resolved_token),
        "auth_source": "tenant_credential" if tenant_token else ("system_fallback" if resolved_token else "none"),
        "approved_actors_count": len(ActorRegistry.list()),
    }


@router.post("/jobs", response_model=CollectionJobResponse)
async def submit_collection_job(
    request: CollectionJobRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """Submits a bounded, tenant-isolated data collection job.
    Enforces spending cap (max_charge_usd) and input validation against the approved Actor definition.
    """
    actor = ActorRegistry.get(request.actor_key)
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Actor '{request.actor_key}' is not registered as an approved OctaOS Actor.",
        )

    client = ApifyTransportClient()
    response = await client.run_actor(
        actor_key=request.actor_key,
        raw_input=request.input_data,
        max_charge_usd=request.max_charge_usd,
        timeout_seconds=request.timeout_seconds,
        db=db,
        tenant_id=tenant_id,
    )

    if response.status == "missing_credentials":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Apify credentials are not configured for this tenant. Please configure your Apify API Token in Integrations.",
        )

    return response
