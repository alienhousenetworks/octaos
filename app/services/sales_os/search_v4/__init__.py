"""Parallel search methods for Sales AI. Existing lead connectors stay in place."""
import httpx

from app.services.sales_os.search_v4.connectors import MethodConnectors
from app.services.sales_os.search_v4.contracts import CampaignIntentSpec, SearchBatch
from app.services.sales_os.search_v4.engine import SearchEngine
from app.services.sales_os.search_v4.registry import PARALLEL_EXISTING_NOTE, credential_map
from app.services.sales_os.search_v4.store import MemorySearchStore, store_for_session

__all__ = ["PARALLEL_EXISTING_NOTE", "run_parallel_search"]


async def run_parallel_search(
    spec: CampaignIntentSpec,
    credentials: dict[str, str] | None = None,
    history: list[str] | None = None,
    suppressed_domains: set[str] | None = None,
    client: httpx.AsyncClient | None = None,
    store=None,
    connectors=None,
    db=None,
) -> SearchBatch:
    resolved = credential_map(credentials)
    engine = SearchEngine(
        store if store is not None else store_for_session(db),
        connectors if connectors is not None else MethodConnectors(resolved),
        resolved,
    )
    return await engine.run(spec, history=history, suppressed_domains=suppressed_domains, client=client)


def empty_store() -> MemorySearchStore:
    return MemorySearchStore()
