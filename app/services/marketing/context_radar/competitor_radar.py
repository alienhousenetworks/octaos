"""Competitor & Public Web Intelligence Radar.
Uses approved Apify website crawling to gather competitor signals, product launches,
and public announcement changes with source provenance.
"""
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.integrations.apify.client import ApifyTransportClient

logger = logging.getLogger(__name__)


class CompetitorRadar:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self._client = ApifyTransportClient()

    async def inspect_competitor_website(
        self,
        domain_or_url: str,
        max_pages: int = 5,
        token_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Inspects competitor public website for announcements, product changes, and positioning."""
        url = domain_or_url if domain_or_url.startswith("http") else f"https://{domain_or_url}"

        response = await self._client.run_actor(
            actor_key="website_intelligence",
            raw_input={"startUrls": [{"url": url}], "maxCrawlPages": max_pages},
            max_charge_usd=2.50,
            limit=max_pages,
            db=self.db,
            tenant_id=self.tenant_id,
            token_override=token_override,
        )

        if response.status != "succeeded":
            return {
                "status": response.status,
                "url": url,
                "signals": [],
                "error": response.error_message,
            }

        extracted_signals: List[Dict[str, Any]] = []
        for item in response.items:
            if not isinstance(item, dict):
                continue
            page_url = item.get("url") or url
            text = (item.get("text") or item.get("markdown") or "")[:2000]
            title = (item.get("metadata", {}).get("title") or item.get("title") or "")[:120]

            if not text and not title:
                continue

            sig_hash = hashlib.sha256(f"{page_url}:{title}".encode()).hexdigest()[:16]
            extracted_signals.append({
                "title": title or "Website Content Snapshot",
                "source_url": page_url,
                "snippet": text[:350],
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "content_hash": sig_hash,
            })

        return {
            "status": "succeeded",
            "url": url,
            "page_count": len(extracted_signals),
            "actual_cost": response.actual_cost,
            "signals": extracted_signals,
        }
