"""Job memory. SQL persistence is used when the search tables exist."""
from datetime import datetime, timezone
from typing import Any

from app.services.sales_os.search_v4.registry import ProviderStats


class MemorySearchStore:
    def __init__(self):
        self.jobs: dict[tuple[str, str], dict[str, Any]] = {}
        self.cache: dict[tuple[str, str], dict[str, Any]] = {}
        self.spend: list[tuple[str, datetime, float]] = []
        self.stats = ProviderStats()

    def save_job(self, tenant_id: str, job_id: str, payload: dict[str, Any]) -> None:
        self.jobs[(tenant_id, job_id)] = payload

    def get_job(self, tenant_id: str, job_id: str) -> dict[str, Any] | None:
        payload = self.jobs.get((tenant_id, job_id))
        return None if payload is None else payload

    def get_cached(self, tenant_id: str, idempotency_key: str) -> dict[str, Any] | None:
        return self.cache.get((tenant_id, idempotency_key))

    def put_cached(self, tenant_id: str, idempotency_key: str, payload: dict[str, Any]) -> None:
        self.cache[(tenant_id, idempotency_key)] = payload

    def month_spend_inr(self, tenant_id: str, now: datetime) -> float:
        total = 0.0
        for owner, moment, amount in self.spend:
            if owner == tenant_id and moment.year == now.year and moment.month == now.month:
                total += amount
        return total

    def add_spend(self, tenant_id: str, amount: float, now: datetime) -> None:
        if amount:
            self.spend.append((tenant_id, now, amount))

    def provider_stats(self) -> ProviderStats:
        return self.stats

    def record_yield(self, provider: str, qualified: int) -> None:
        self.stats.samples[provider] = self.stats.sample(provider) + 1
        self.stats.qualified[provider] = int(self.stats.qualified.get(provider) or 0) + qualified


class SqlSearchStore:
    """Tenant-filtered rows in search_v4_* tables. Falls back when the tables are absent."""

    def __init__(self, db):
        self.db = db

    def available(self) -> bool:
        from sqlalchemy import inspect

        bind = self.db.get_bind()
        return inspect(bind).has_table("search_v4_jobs")

    def save_job(self, tenant_id: str, job_id: str, payload: dict[str, Any]) -> None:
        from app.models.search_v4 import SearchV4Job

        row = self.db.query(SearchV4Job).filter_by(id=job_id, tenant_id=tenant_id).first()
        if row is None:
            row = SearchV4Job(id=job_id, tenant_id=tenant_id, payload=payload, status=payload.get("status") or "running")
            self.db.add(row)
        else:
            row.payload = payload
            row.status = payload.get("status") or row.status
        self.db.commit()

    def get_job(self, tenant_id: str, job_id: str) -> dict[str, Any] | None:
        from app.models.search_v4 import SearchV4Job

        row = self.db.query(SearchV4Job).filter_by(id=job_id, tenant_id=tenant_id).first()
        if row is None:
            return None
        return row.payload

    def get_cached(self, tenant_id: str, idempotency_key: str) -> dict[str, Any] | None:
        from app.models.search_v4 import SearchV4TaskRow

        row = self.db.query(SearchV4TaskRow).filter_by(tenant_id=tenant_id, idempotency_key=idempotency_key).first()
        if row is None or row.status not in {"succeeded", "empty"}:
            return None
        return row.result

    def put_cached(self, tenant_id: str, idempotency_key: str, payload: dict[str, Any]) -> None:
        from app.models.search_v4 import SearchV4TaskRow

        row = self.db.query(SearchV4TaskRow).filter_by(tenant_id=tenant_id, idempotency_key=idempotency_key).first()
        if row is None:
            row = SearchV4TaskRow(
                tenant_id=tenant_id,
                idempotency_key=idempotency_key,
                status=payload.get("status") or "succeeded",
                result=payload,
            )
            self.db.add(row)
        else:
            row.status = payload.get("status") or row.status
            row.result = payload
        self.db.commit()

    def month_spend_inr(self, tenant_id: str, now: datetime) -> float:
        from app.models.search_v4 import SearchV4LedgerRow

        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        rows = (
            self.db.query(SearchV4LedgerRow)
            .filter(SearchV4LedgerRow.tenant_id == tenant_id, SearchV4LedgerRow.created_at >= start)
            .all()
        )
        return sum(float(row.actual_cost_inr or 0) for row in rows if row.status == "reconciled")

    def add_spend(self, tenant_id: str, amount: float, now: datetime) -> None:
        from app.models.search_v4 import SearchV4LedgerRow

        if not amount:
            return
        self.db.add(
            SearchV4LedgerRow(
                tenant_id=tenant_id,
                provider="search_v4",
                operation="reconcile",
                estimated_cost_inr=amount,
                actual_cost_inr=amount,
                status="reconciled",
                created_at=now,
            )
        )
        self.db.commit()

    def provider_stats(self) -> ProviderStats:
        return ProviderStats()

    def record_yield(self, provider: str, qualified: int) -> None:
        del provider, qualified


def store_for_session(db) -> MemorySearchStore | SqlSearchStore:
    if db is None:
        return MemorySearchStore()
    try:
        candidate = SqlSearchStore(db)
        if candidate.available():
            return candidate
    except Exception:
        return MemorySearchStore()
    return MemorySearchStore()
