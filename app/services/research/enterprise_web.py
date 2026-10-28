"""Tenant-scoped, multi-channel public web research.

This is an assistant-neutral facade over the durable Sales search-v4 engine.
It returns evidence and honest unavailable states; it never turns a search hit
into a verified contact without a public name and address from the source.
"""
from __future__ import annotations

from typing import Any, Iterable
from uuid import uuid4

from app.services.sales_os.search_v4 import resume_parallel_search, run_parallel_search
from app.services.sales_os.search_v4.contracts import CampaignIntentSpec, SearchBatch
from app.services.sales_os.search_v4.registry import credential_map


class EnterpriseWebResearchService:
    """Run the common web, news, hiring, company, and public-social pipeline."""

    DEFAULT_GEOGRAPHIES = ("India", "United States", "United Kingdom")

    def __init__(self, db=None, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = str(tenant_id or "")

    def _credentials(self) -> dict[str, str]:
        overrides: dict[str, str] = {}
        if self.db and self.tenant_id:
            from app.core.security import decrypt_api_key
            from app.models.base import APICredential

            aliases = {
                "brave_search": "brave_search",
                "tavily": "tavily",
                "reddit": "reddit",
                "reddit_intent": "reddit",
                "x": "x_search",
                "x_search": "x_search",
                "twitter_intent": "x_search",
            }
            try:
                credentials = self.db.query(APICredential).filter_by(tenant_id=self.tenant_id).all()
            except Exception:
                credentials = []
            for credential in credentials:
                target = aliases.get(credential.provider)
                if not target or not credential.encrypted_key:
                    continue
                try:
                    value = decrypt_api_key(credential.encrypted_key)
                except Exception:
                    continue
                if value:
                    overrides[target] = value
        return credential_map(overrides)

    @staticmethod
    def _as_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(value, Iterable):
            return [str(part).strip() for part in value if str(part).strip()]
        return [str(value).strip()]

    async def run(
        self,
        query: str,
        *,
        count: int = 10,
        freshness: str = "14_days",
        geography: Any = None,
        industries: Any = None,
        buyer_roles: Any = None,
        exclusions: Any = None,
        offer: str = "",
        seed_urls: Any = None,
        budget_inr: float = 700.0,
        job_id: str | None = None,
    ) -> SearchBatch:
        requested_geographies = self._as_list(geography)
        ordered_geographies = requested_geographies or list(self.DEFAULT_GEOGRAPHIES)
        spec = CampaignIntentSpec(
            campaign_id=f"assistant-research-{uuid4()}",
            tenant_id=self.tenant_id,
            query=(query or "public buyer requests")[:300],
            industries=self._as_list(industries),
            buyer_roles=self._as_list(buyer_roles),
            geography=ordered_geographies,
            exclusions=self._as_list(exclusions),
            freshness=freshness or "14_days",
            budget_inr=max(0.0, float(budget_inr)),
            monthly_limit_inr=max(0.0, float(budget_inr)),
            offer=(offer or "")[:500],
            seed_urls=self._as_list(seed_urls)[:5],
        )
        suppressed_domains = self._suppressed_domains()
        return await run_parallel_search(
            spec,
            credentials=self._credentials(),
            suppressed_domains=suppressed_domains,
            db=self.db,
            job_id=job_id,
        )

    async def resume(self, job_id: str) -> SearchBatch:
        """Resume an existing job only within this service's tenant context."""
        if not self.db or not self.tenant_id:
            raise RuntimeError("Durable tenant-scoped storage is required to resume research.")
        return await resume_parallel_search(
            self.tenant_id,
            job_id,
            credentials=self._credentials(),
            db=self.db,
        )

    def _suppressed_domains(self) -> set[str]:
        if not self.db or not self.tenant_id:
            return set()
        try:
            from app.models.deal_room import SuppressionRecord

            return {
                row.identifier_value.strip().lower()
                for row in self.db.query(SuppressionRecord).filter_by(
                    tenant_id=self.tenant_id,
                    identifier_type="domain",
                ).all()
                if row.identifier_value
            }
        except Exception:
            return set()

    @staticmethod
    def summarize(batch: SearchBatch, count: int = 10) -> dict[str, Any]:
        contacts = []
        extras = []
        for candidate in batch.candidates:
            if candidate.assessment and candidate.assessment.decision == "reject":
                continue
            record = candidate.record
            company = record.company_name or record.company_domain or ""
            name = record.contact_name or ""
            email = record.contact_email or ""
            item = {
                "company": company,
                "name": name or company or "Business Contact",
                "email": email,
                "title": record.title,
                "url": record.original_url,
                "source": f"{record.method}/{record.provider}",
                "intent": candidate.assessment.intent.value if candidate.assessment and candidate.assessment.intent else "unclear",
                "decision": candidate.assessment.decision if candidate.assessment else "accept",
                "verification_state": candidate.evidence.verification_state if candidate.evidence else "unverified",
                "published_at": record.published_at.isoformat() if record.published_at else None,
                "reason": candidate.assessment.rationale if candidate.assessment else "",
            }
            if email and name:
                contacts.append(item)
            elif company or email or record.original_url:
                extras.append(item)

        # When direct executive contacts are fewer than count, promote company leads from extras
        # so callers and agents receive actionable target accounts rather than an empty list
        if len(contacts) < count and extras:
            needed = count - len(contacts)
            contacts.extend(extras[:needed])

        return {
            "job_id": batch.job_id,
            "status": batch.status,
            "requested_count": count,
            "contacts": contacts[:count],
            "extras": extras[: max(20, count * 2)],
            "methods": [
                {
                    "method": task.method,
                    "provider": task.provider,
                    "status": task.status,
                    "reason": task.reason,
                    "query": task.query,
                }
                for task in batch.tasks
            ],
            "report": batch.report,
        }
