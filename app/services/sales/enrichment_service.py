"""Enrichment Service for Sales OS: Apollo, company intelligence, and external enrichment."""
import logging
import httpx
from typing import Any, Callable, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.http_utils import with_retry

logger = logging.getLogger(__name__)


class EnrichmentService:
    def __init__(self, db: Session, tenant_id: str, log_activity: Optional[Callable] = None):
        self.db = db
        self.tenant_id = tenant_id
        self._log_activity = log_activity or (lambda *args, **kwargs: None)

    @with_retry
    async def fetch_apollo_org_data(self, api_key: str, domain: str) -> Optional[str]:
        """Fetch Apollo organization ID for a given domain."""
        async with httpx.AsyncClient() as client:
            headers = {"Content-Type": "application/json", "Cache-Control": "no-cache", "X-Api-Key": api_key}
            try:
                response = await client.post(
                    "https://api.apollo.io/v1/mixed_companies/search",
                    headers=headers,
                    json={"q_organization_domains": domain},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    orgs = data.get("organizations", [])
                    if orgs:
                        return orgs[0].get("id")
            except Exception:
                pass
        return None

    @with_retry
    async def fetch_apollo_news(self, api_key: str, org_id: str) -> list:
        """Fetch recent news articles for an Apollo organization."""
        async with httpx.AsyncClient() as client:
            headers = {"Content-Type": "application/json", "Cache-Control": "no-cache", "X-Api-Key": api_key}
            try:
                response = await client.post(
                    "https://api.apollo.io/api/v1/news_articles/search",
                    headers=headers,
                    json={"organization_ids": [org_id]},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    articles = response.json().get("news_articles", [])[:2]
                    return [{"title": a.get("title"), "snippet": a.get("snippet")} for a in articles]
            except Exception:
                pass
        return []

    @with_retry
    async def fetch_apollo_jobs(self, api_key: str, org_id: str) -> list:
        """Fetch open job postings for an Apollo organization."""
        async with httpx.AsyncClient() as client:
            headers = {"Content-Type": "application/json", "Cache-Control": "no-cache", "X-Api-Key": api_key}
            try:
                response = await client.get(
                    f"https://api.apollo.io/api/v1/organizations/{org_id}/job_postings",
                    headers=headers,
                    timeout=10.0,
                )
                if response.status_code == 200:
                    jobs = response.json().get("organization_job_postings", [])[:2]
                    return [{"title": j.get("title")} for j in jobs]
            except Exception:
                pass
        return []
