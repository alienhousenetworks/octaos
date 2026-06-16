import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.base import ProviderUsage, bypass_tenant_isolation

logger = logging.getLogger(__name__)

class UsageService:
    @staticmethod
    def get_billing_summary(
        db: Session,
        tenant_id: str,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieves cost summary and usage aggregates for a tenant / organization.
        """
        try:
            # We construct a query based on target criteria
            query = db.query(
                func.sum(ProviderUsage.cost).label("total_cost"),
                func.sum(ProviderUsage.input_tokens).label("total_input_tokens"),
                func.sum(ProviderUsage.output_tokens).label("total_output_tokens"),
                func.count(ProviderUsage.id).label("total_calls")
            ).filter(ProviderUsage.tenant_id == tenant_id)

            if organization_id:
                query = query.filter(ProviderUsage.organization_id == organization_id)

            result = query.first()
            
            total_cost = float(result.total_cost or 0.0) if result else 0.0
            total_input_tokens = int(result.total_input_tokens or 0) if result else 0
            total_output_tokens = int(result.total_output_tokens or 0) if result else 0
            total_calls = int(result.total_calls or 0) if result else 0

            return {
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "total_cost": total_cost,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_calls": total_calls
            }
        except Exception as e:
            logger.error(f"Failed to retrieve billing summary: {e}")
            raise e

    @staticmethod
    def get_provider_breakdown(
        db: Session,
        tenant_id: str,
        organization_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Group usage and costs by provider.
        """
        try:
            query = db.query(
                ProviderUsage.provider,
                func.sum(ProviderUsage.cost).label("cost"),
                func.sum(ProviderUsage.input_tokens).label("input_tokens"),
                func.sum(ProviderUsage.output_tokens).label("output_tokens"),
                func.count(ProviderUsage.id).label("calls")
            ).filter(ProviderUsage.tenant_id == tenant_id)

            if organization_id:
                query = query.filter(ProviderUsage.organization_id == organization_id)

            breakdowns = query.group_by(ProviderUsage.provider).all()

            return [
                {
                    "provider": b.provider,
                    "cost": float(b.cost or 0.0),
                    "input_tokens": int(b.input_tokens or 0),
                    "output_tokens": int(b.output_tokens or 0),
                    "calls": int(b.calls or 0)
                }
                for b in breakdowns
            ]
        except Exception as e:
            logger.error(f"Failed to retrieve provider breakdown: {e}")
            raise e

    @staticmethod
    def get_cache_efficiency(
        db: Session,
        tenant_id: str,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates prompt caching efficiency, token savings, and cost savings.
        """
        try:
            # We want to retrieve aggregate counts of hits vs misses
            query = db.query(
                ProviderUsage.cache_hit,
                func.count(ProviderUsage.id).label("calls"),
                func.sum(ProviderUsage.cached_tokens).label("cached_tokens")
            ).filter(ProviderUsage.tenant_id == tenant_id)

            if organization_id:
                query = query.filter(ProviderUsage.organization_id == organization_id)

            results = query.group_by(ProviderUsage.cache_hit).all()

            hits = 0
            misses = 0
            total_cached_tokens = 0

            for r in results:
                if r.cache_hit:
                    hits = r.calls
                    total_cached_tokens += (r.cached_tokens or 0)
                else:
                    misses = r.calls

            total = hits + misses
            hit_rate = (hits / total) if total > 0 else 0.0

            # Approximate cost savings (assuming an average cost of $3 per 1M input tokens saved)
            cost_savings = (total_cached_tokens * 3.0 / 1_000_000)

            return {
                "total_calls": total,
                "cache_hits": hits,
                "cache_misses": misses,
                "hit_rate": hit_rate,
                "total_cached_tokens": total_cached_tokens,
                "cost_savings_estimate": cost_savings
            }
        except Exception as e:
            logger.error(f"Failed to retrieve cache efficiency: {e}")
            raise e
