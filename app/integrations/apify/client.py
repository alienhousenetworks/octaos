"""Transport client for Apify Actors.
Uses apify-client SDK with budget caps (max_total_charge_usd), async thread execution,
and schema validation through ActorRegistry.
"""
import asyncio
import logging
import os
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from apify_client import ApifyClient

from app.core.config import settings
from app.integrations.apify.actor_registry import ActorRegistry
from app.integrations.apify.schemas import CollectionJobResponse
from app.services.credentials import get_decrypted_credential

logger = logging.getLogger(__name__)


class ApifyTransportClient:
    def __init__(self, token: Optional[str] = None):
        self._explicit_token = token

    @classmethod
    def resolve_token(
        cls,
        db: Optional[Session] = None,
        tenant_id: Optional[str] = None,
        explicit_token: Optional[str] = None,
    ) -> Optional[str]:
        """Resolves Apify token following priority: explicit > tenant credential > system config."""
        if explicit_token and explicit_token.strip():
            return explicit_token.strip()

        if db is not None and tenant_id:
            try:
                decrypted, _ = get_decrypted_credential(db, tenant_id, "apify")
                if decrypted and decrypted.strip():
                    return decrypted.strip()
            except Exception as exc:
                logger.warning(f"[ApifyTransport] Error checking tenant credentials for {tenant_id}: {exc}")

        env_token = getattr(settings, "APIFY_TOKEN", None) or os.environ.get("APIFY_TOKEN")
        if env_token and env_token.strip():
            return env_token.strip()

        return None

    def get_client(
        self,
        db: Optional[Session] = None,
        tenant_id: Optional[str] = None,
        token_override: Optional[str] = None,
    ) -> Optional[ApifyClient]:
        token = self.resolve_token(db=db, tenant_id=tenant_id, explicit_token=token_override or self._explicit_token)
        if not token:
            return None
        return ApifyClient(token=token)

    async def run_actor(
        self,
        actor_key: str,
        raw_input: Dict[str, Any],
        max_charge_usd: Optional[float] = None,
        timeout_seconds: Optional[int] = None,
        limit: int = 25,
        db: Optional[Session] = None,
        tenant_id: Optional[str] = None,
        token_override: Optional[str] = None,
    ) -> CollectionJobResponse:
        """Executes an approved Actor run synchronously within a worker thread.
        Enforces max_total_charge_usd and returns a normalized CollectionJobResponse.
        """
        job_id = str(uuid.uuid4())
        actor_def = ActorRegistry.get(actor_key)
        if not actor_def:
            return CollectionJobResponse(
                job_id=job_id,
                status="rejected",
                actor_key=actor_key,
                error_message=f"Actor key '{actor_key}' is not approved in OctaOS registry.",
            )

        client = self.get_client(db=db, tenant_id=tenant_id, token_override=token_override)
        if not client:
            return CollectionJobResponse(
                job_id=job_id,
                status="missing_credentials",
                actor_key=actor_key,
                error_message="Apify token is not configured (missing in tenant credentials and system environment).",
            )

        # Build and sanitize input
        try:
            run_input = ActorRegistry.validate_and_build_input(actor_key, raw_input)
        except Exception as exc:
            return CollectionJobResponse(
                job_id=job_id,
                status="invalid_input",
                actor_key=actor_key,
                error_message=f"Input validation error: {exc}",
            )

        cap_usd = Decimal(str(max_charge_usd if max_charge_usd is not None else actor_def.default_max_charge_usd))
        timeout = int(timeout_seconds if timeout_seconds is not None else actor_def.default_timeout_seconds)

        def _blocking_call():
            actor_client = client.actor(actor_def.actor_id)
            # max_total_charge_usd ensures provider-side charge bounding
            run = actor_client.call(
                run_input=run_input,
                max_total_charge_usd=cap_usd,
                timeout_secs=timeout,
            )
            return run

        try:
            run_result = await asyncio.to_thread(_blocking_call)
        except Exception as exc:
            logger.error(f"[ApifyTransport] Actor run failed for {actor_key} ({actor_def.actor_id}): {exc}")
            return CollectionJobResponse(
                job_id=job_id,
                status="error",
                actor_key=actor_key,
                error_message=f"Execution error: {exc}",
            )

        if not run_result or not isinstance(run_result, dict):
            return CollectionJobResponse(
                job_id=job_id,
                status="failed",
                actor_key=actor_key,
                error_message="Apify returned an empty or invalid run response.",
            )

        run_id = run_result.get("id")
        run_status = run_result.get("status")
        dataset_id = run_result.get("defaultDatasetId")
        actual_cost = float(run_result.get("usageTotalUsd") or 0.0)

        if run_status != "SUCCEEDED":
            return CollectionJobResponse(
                job_id=job_id,
                status="failed" if run_status in {"FAILED", "ABORTED"} else "timed_out",
                actor_key=actor_key,
                provider_run_id=run_id,
                dataset_id=dataset_id,
                actual_cost=actual_cost,
                error_message=f"Apify run finished with status {run_status}: {run_result.get('statusMessage', '')}",
            )

        # Retrieve dataset items
        items = []
        if dataset_id:
            try:
                def _fetch_items():
                    dataset_client = client.dataset(dataset_id)
                    page = dataset_client.list_items(limit=limit)
                    return page.items if hasattr(page, "items") else (page or [])

                items = await asyncio.to_thread(_fetch_items)
            except Exception as exc:
                logger.warning(f"[ApifyTransport] Could not fetch dataset {dataset_id}: {exc}")

        return CollectionJobResponse(
            job_id=job_id,
            status="succeeded",
            actor_key=actor_key,
            provider_run_id=run_id,
            dataset_id=dataset_id,
            item_count=len(items),
            estimated_cost=float(cap_usd),
            actual_cost=actual_cost,
            items=items,
        )
