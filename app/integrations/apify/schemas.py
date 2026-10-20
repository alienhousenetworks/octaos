"""Schemas for Apify Data Collection & Actor Registry."""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ActorCapability(str, Enum):
    ACCOUNT_DISCOVERY = "account_discovery"
    CONTACT_DISCOVERY = "contact_discovery"
    SIGNAL_COLLECTION = "signal_collection"
    MARKET_RESEARCH = "market_research"
    CONTENT_CRAWL = "content_crawl"


class ActorPricingModel(str, Enum):
    FREE = "free"
    PER_RESULT = "per_result"
    USAGE_BASED = "usage_based"
    FLAT = "flat"


class ApprovedActorDefinition(BaseModel):
    actor_key: str = Field(..., description="Internal reference key, e.g. company_discovery")
    actor_id: str = Field(..., description="Apify Actor identifier, e.g. compass/crawler-google-places")
    name: str
    description: str
    capabilities: List[ActorCapability]
    default_max_charge_usd: float = 2.00
    default_timeout_seconds: int = 300
    pricing_model: ActorPricingModel = ActorPricingModel.USAGE_BASED
    input_schema_template: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    schema_version: str = "1.0.0"


class CollectionJobRequest(BaseModel):
    actor_key: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    max_charge_usd: Optional[float] = Field(default=2.00, ge=0.0, le=50.0)
    timeout_seconds: Optional[int] = Field(default=300, ge=10, le=1200)
    idempotency_key: Optional[str] = None


class CollectionJobResponse(BaseModel):
    job_id: str
    status: str  # queued, running, succeeded, failed, timed_out, cancelled
    actor_key: str
    provider_run_id: Optional[str] = None
    dataset_id: Optional[str] = None
    item_count: int = 0
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    items: List[Dict[str, Any]] = Field(default_factory=list)
    error_message: Optional[str] = None
