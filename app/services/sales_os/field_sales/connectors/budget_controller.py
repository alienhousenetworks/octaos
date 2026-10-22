"""
Connector budget controller for caching, quota enforcement, and audit ledger tracking.
Ensures mapping and routing calls never run up unexpected third-party bills.
"""
from __future__ import annotations
import time
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session
from app.models.field_sales import ConnectorUsageAudit
from app.services.sales_os.field_sales.connectors.base import MappingConnector
from app.services.sales_os.field_sales.connectors.google_maps import GoogleMapsConnector
from app.services.sales_os.field_sales.connectors.local_fallback import LocalRoadsFallbackConnector


class ConnectorBudgetController(MappingConnector):
    """
    Budget Controller wrapper around mapping connectors.
    Handles per-tenant daily quota, caching, and audit persistence.
    """

    DEFAULT_DAILY_QUOTA = 500  # API calls per day
    COST_PER_ROUTE_USD = 0.005  # Google Routes estimate
    COST_PER_GEOCODE_USD = 0.005  # Google Geocode estimate

    # In-memory cache structures
    _geocode_cache: dict[str, dict[str, Any]] = {}
    _route_cache: dict[str, tuple[float, dict[str, Any]]] = {}  # key -> (timestamp, data)

    def __init__(self, db: Session, tenant_id: str, primary_connector: MappingConnector | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.connector = primary_connector or GoogleMapsConnector()
        self.fallback = LocalRoadsFallbackConnector()

    def _get_daily_call_count(self) -> int:
        """Count billable calls made by this tenant today."""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        count = (
            self.db.query(ConnectorUsageAudit)
            .filter(
                ConnectorUsageAudit.tenant_id == self.tenant_id,
                ConnectorUsageAudit.timestamp >= today_start,
                ConnectorUsageAudit.cache_hit == False,
            )
            .count()
        )
        return count

    def _record_audit(
        self,
        provider: str,
        endpoint: str,
        cost_usd: float = 0.0,
        cache_hit: bool = False,
    ) -> None:
        """Persist audit record in the main database."""
        try:
            audit = ConnectorUsageAudit(
                tenant_id=self.tenant_id,
                provider=provider,
                endpoint=endpoint,
                call_count=1,
                cost_estimate_usd=cost_usd,
                cache_hit=cache_hit,
            )
            self.db.add(audit)
            self.db.commit()
        except Exception:
            self.db.rollback()

    async def geocode(self, address: str) -> dict[str, Any]:
        """Geocodes with perpetual address caching."""
        normalized = (address or "").strip().lower()
        if not normalized:
            return await self.fallback.geocode(address)

        if normalized in self._geocode_cache:
            self._record_audit(provider="cache", endpoint="geocode", cost_usd=0.0, cache_hit=True)
            cached = dict(self._geocode_cache[normalized])
            cached["cached"] = True
            return cached

        # Check quota
        if self._get_daily_call_count() >= self.DEFAULT_DAILY_QUOTA:
            res = await self.fallback.geocode(address)
            res["status"] = "QUOTA_EXCEEDED_FALLBACK"
            return res

        res = await self.connector.geocode(address)
        self._geocode_cache[normalized] = res
        cost = self.COST_PER_GEOCODE_USD if res.get("provider") == "google_maps" else 0.0
        self._record_audit(provider=res.get("provider", "unknown"), endpoint="geocode", cost_usd=cost, cache_hit=False)
        return res

    async def calculate_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> dict[str, Any]:
        """Route calculation with 30-minute validity cache."""
        cache_key = f"{round(origin_lat, 4)},{round(origin_lng, 4)}->{round(dest_lat, 4)},{round(dest_lng, 4)}"
        now = time.time()

        if cache_key in self._route_cache:
            ts, data = self._route_cache[cache_key]
            if now - ts < 1800:  # 30 minutes
                self._record_audit(provider="cache", endpoint="route", cost_usd=0.0, cache_hit=True)
                cached = dict(data)
                cached["cached"] = True
                return cached

        # Check quota
        if self._get_daily_call_count() >= self.DEFAULT_DAILY_QUOTA:
            res = await self.fallback.calculate_route(origin_lat, origin_lng, dest_lat, dest_lng)
            res["status"] = "QUOTA_EXCEEDED_FALLBACK"
            return res

        res = await self.connector.calculate_route(origin_lat, origin_lng, dest_lat, dest_lng)
        self._route_cache[cache_key] = (now, res)
        cost = self.COST_PER_ROUTE_USD if res.get("provider") == "google_maps" else 0.0
        self._record_audit(provider=res.get("provider", "unknown"), endpoint="route", cost_usd=cost, cache_hit=False)
        return res

    async def calculate_matrix(
        self,
        origins: list[tuple[float, float]],
        destinations: list[tuple[float, float]],
    ) -> dict[str, Any]:
        """Calculates distance/duration matrix."""
        res = await self.connector.calculate_matrix(origins, destinations)
        self._record_audit(provider=res.get("provider", "unknown"), endpoint="matrix", cost_usd=0.0, cache_hit=False)
        return res

    def get_budget_stats(self) -> dict[str, Any]:
        """Returns quota usage, cost, and cache efficiency for dashboard."""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        audits = (
            self.db.query(ConnectorUsageAudit)
            .filter(
                ConnectorUsageAudit.tenant_id == self.tenant_id,
                ConnectorUsageAudit.timestamp >= today_start,
            )
            .all()
        )
        total_requests = len(audits)
        cache_hits = sum(1 for a in audits if a.cache_hit)
        billable_calls = total_requests - cache_hits
        total_cost = sum(a.cost_estimate_usd or 0.0 for a in audits)

        return {
            "daily_quota": self.DEFAULT_DAILY_QUOTA,
            "calls_used": billable_calls,
            "calls_remaining": max(0, self.DEFAULT_DAILY_QUOTA - billable_calls),
            "quota_used_pct": round((billable_calls / max(1, self.DEFAULT_DAILY_QUOTA)) * 100, 1),
            "cache_hits": cache_hits,
            "cache_efficiency_pct": round((cache_hits / max(1, total_requests)) * 100, 1) if total_requests else 100.0,
            "estimated_daily_cost_usd": round(total_cost, 4),
            "status": "HEALTHY" if billable_calls < self.DEFAULT_DAILY_QUOTA * 0.8 else ("WARNING" if billable_calls < self.DEFAULT_DAILY_QUOTA else "EXCEEDED"),
        }
