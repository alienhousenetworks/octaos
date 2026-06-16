from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Any, Optional, List
from pydantic import BaseModel

from app.api import deps
from app.core.rbac import require_permission, Resource, Action
from app.models.base import User
from app.services.usage_service import UsageService

router = APIRouter()

class BillingSummaryResponse(BaseModel):
    tenant_id: str
    organization_id: Optional[str] = None
    total_cost: float
    total_input_tokens: int
    total_output_tokens: int
    total_calls: int

class ProviderBreakdownResponse(BaseModel):
    provider: str
    cost: float
    input_tokens: int
    output_tokens: int
    calls: int

class CacheEfficiencyResponse(BaseModel):
    total_calls: int
    cache_hits: int
    cache_misses: int
    hit_rate: float
    total_cached_tokens: int
    cost_savings_estimate: float

@router.get("/summary", response_model=BillingSummaryResponse)
def get_billing_summary(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_permission(Resource.SETTINGS, Action.READ)),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    organization_id: Optional[str] = Query(None)
) -> Any:
    """
    Retrieve billing summary for a tenant / organization.
    """
    return UsageService.get_billing_summary(db, tenant_id, organization_id)

@router.get("/providers", response_model=List[ProviderBreakdownResponse])
def get_provider_breakdown(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_permission(Resource.SETTINGS, Action.READ)),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    organization_id: Optional[str] = Query(None)
) -> Any:
    """
    Get billing and token count breakdowns by provider.
    """
    return UsageService.get_provider_breakdown(db, tenant_id, organization_id)

@router.get("/cache-efficiency", response_model=CacheEfficiencyResponse)
def get_cache_efficiency(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_permission(Resource.SETTINGS, Action.READ)),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    organization_id: Optional[str] = Query(None)
) -> Any:
    """
    Get token cache efficiency and cost savings estimation.
    """
    return UsageService.get_cache_efficiency(db, tenant_id, organization_id)
