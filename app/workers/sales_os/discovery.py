"""Manual sales-os discovery. This task is not scheduled, so it cannot spend credits on its own."""
from asgiref.sync import async_to_sync

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.sales_os.discovery.source_registry import get_all_source_ids
from app.services.sales_os.orchestration.credentials import configured_providers, provider_secrets
from app.services.sales_os.orchestration.sales_pipeline import SalesPipeline


def _provider_keys(requested: list[str] | None) -> list[str]:
    if requested:
        return requested
    return get_all_source_ids()


@celery_app.task(name="run_sales_os_discovery_task")
def run_sales_os_discovery_task(
    tenant_id: str,
    query: str,
    provider_keys: list | None = None,
    budget: float | None = None,
    execute: bool = False,
    profile: dict | None = None,
):
    db = SessionLocal()
    try:
        keys = _provider_keys(provider_keys)
        credentialed = configured_providers(db, tenant_id)
        secrets = provider_secrets(db, tenant_id, set(keys) & credentialed) if execute else {}
        pipeline = SalesPipeline(db, tenant_id)
        return async_to_sync(pipeline.run)(
            query=query,
            provider_keys=keys,
            credentialed=credentialed,
            credentials=secrets,
            profile=profile,
            budget=budget,
            execute=execute,
        )
    finally:
        db.close()
