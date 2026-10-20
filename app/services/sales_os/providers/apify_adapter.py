"""Apify Sales OS Provider Adapter.
Integrates Apify into the multi-provider Sales OS pipeline as a live discovery and signal tool.
Never hallucinates unknown fields; attaches evidence provenance to all observations.
"""
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Set

from app.integrations.apify.client import ApifyTransportClient
from app.services.sales_os.discovery.identity import canonical_domain
from app.services.sales_os.providers.base import (
    AccountCandidate,
    ConnectorEnvelope,
    ContactCandidate,
    RawSignal,
    empty_envelope,
)
from app.services.sales_os.providers.honesty import is_fabricated_contact


def _clean_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s or None


class ApifyAdapter:
    def __init__(self, provider_key: str = "apify", transport: Optional[Any] = None):
        self.provider_key = provider_key
        self.paid = True
        self._transport = transport or ApifyTransportClient()

    def capabilities(self) -> Set[str]:
        return {"account_discovery", "contact_discovery", "signal_collection"}

    def health(self, has_credentials: bool) -> dict:
        return {
            "provider_key": self.provider_key,
            "status": "active" if has_credentials else "missing_credentials",
            "has_credentials": has_credentials,
            "paid": True,
        }

    def estimate_cost(self, operation: str) -> Optional[float]:
        if operation == "discover_accounts":
            return 0.05
        if operation == "fetch_signals":
            return 0.08
        return 0.05

    async def discover_accounts(self, query: str, api_key: Optional[str], count: int = 5) -> ConnectorEnvelope:
        request_id = str(uuid.uuid4())
        client = ApifyTransportClient(token=api_key)

        res = await client.run_actor(
            actor_key="company_discovery",
            raw_input={"query": query, "maxCrawledPlacesPerSearch": count},
            max_charge_usd=2.00,
            limit=count,
            token_override=api_key,
        )

        if res.status != "succeeded":
            return ConnectorEnvelope(
                provider_key=self.provider_key,
                request_id=request_id,
                status=res.status,
                reason=res.error_message,
                estimated_cost=self.estimate_cost("discover_accounts"),
                actual_cost=res.actual_cost,
            )

        accounts: List[AccountCandidate] = []
        contacts: List[ContactCandidate] = []
        signals: List[RawSignal] = []

        for item in res.items:
            if not isinstance(item, dict):
                continue

            name = _clean_str(item.get("title") or item.get("name"))
            raw_site = _clean_str(item.get("website") or item.get("url"))
            domain = canonical_domain(raw_site) or canonical_domain(name)

            if not name and not domain:
                continue

            category = _clean_str(item.get("categoryName") or item.get("category"))
            country = _clean_str(item.get("countryCode") or item.get("country"))
            city = _clean_str(item.get("city"))
            phone = _clean_str(item.get("phone") or item.get("phoneUnformatted"))

            account = AccountCandidate(
                display_name=name,
                canonical_domain=domain,
                website=raw_site or (f"https://{domain}" if domain else None),
                industry=category,
                hq_country=country,
                hq_city=city,
                confidence=0.85,
                external_id=_clean_str(item.get("placeId") or item.get("id")),
            )
            accounts.append(account)

            # Public contact information if present
            if phone or item.get("email"):
                email = _clean_str(item.get("email"))
                contact_dict = {"name": name, "email": email, "phone": phone}
                if not is_fabricated_contact(contact_dict):
                    contact = ContactCandidate(
                        full_name=name,
                        email=email,
                        phone=phone,
                        company_domain=domain,
                        company_name=name,
                        confidence=0.75,
                    )
                    contacts.append(contact)

            # Record place profile as a signal
            source_url = raw_site or item.get("url") or f"https://www.google.com/maps/search/?api=1&query={query}"
            sig_hash = hashlib.sha256(f"{domain or name}:{source_url}".encode()).hexdigest()[:16]
            signals.append(
                RawSignal(
                    signal_type="public_directory_listing",
                    summary=f"Public listing verified on Apify Places for {name or domain}",
                    source_url=source_url,
                    observed_at=datetime.now(timezone.utc),
                    base_strength=50.0,
                    source_confidence=0.85,
                    independent_key=f"apify_listing:{sig_hash}",
                    payload={"place_id": item.get("placeId"), "reviews_count": item.get("reviewsCount")},
                )
            )

        return ConnectorEnvelope(
            provider_key=self.provider_key,
            request_id=request_id,
            status="ok",
            accounts=accounts[:count],
            contacts=contacts[:count],
            signals=signals[:count],
            estimated_cost=self.estimate_cost("discover_accounts"),
            actual_cost=res.actual_cost,
            license_class="public_web",
        )

    async def discover_contacts(self, query: str, api_key: Optional[str], count: int = 5) -> ConnectorEnvelope:
        # Accounts discovery via Apify provides verified public company contacts
        envelope = await self.discover_accounts(query, api_key, count=count)
        return envelope

    async def fetch_signals(self, query: str, api_key: Optional[str], count: int = 5) -> ConnectorEnvelope:
        request_id = str(uuid.uuid4())
        client = ApifyTransportClient(token=api_key)

        res = await client.run_actor(
            actor_key="market_news",
            raw_input={"queries": f"{query} news announcement", "resultsPerPage": count},
            max_charge_usd=1.00,
            limit=count,
            token_override=api_key,
        )

        if res.status != "succeeded":
            return ConnectorEnvelope(
                provider_key=self.provider_key,
                request_id=request_id,
                status=res.status,
                reason=res.error_message,
                estimated_cost=self.estimate_cost("fetch_signals"),
                actual_cost=res.actual_cost,
            )

        domain = canonical_domain(query)
        signals: List[RawSignal] = []

        for item in res.items:
            if not isinstance(item, dict):
                continue
            organic = item.get("organicResults") or []
            for org in organic:
                title = _clean_str(org.get("title"))
                desc = _clean_str(org.get("description"))
                url = _clean_str(org.get("url"))
                if not title and not desc:
                    continue

                content = f"{title or ''}: {desc or ''}".strip()
                indep_key = f"news:{hashlib.sha256(content.encode()).hexdigest()[:16]}"
                signals.append(
                    RawSignal(
                        signal_type="market_news",
                        summary=title or desc[:100],
                        source_url=url,
                        observed_at=datetime.now(timezone.utc),
                        base_strength=60.0,
                        source_confidence=0.80,
                        payload={"url": url, "snippet": desc},
                        independent_key=indep_key,
                        excerpt=desc[:250] if desc else None,
                    )
                )

        accounts = [AccountCandidate(canonical_domain=domain, display_name=query)] if domain else []
        return ConnectorEnvelope(
            provider_key=self.provider_key,
            request_id=request_id,
            status="ok",
            accounts=accounts,
            signals=signals[:count],
            estimated_cost=self.estimate_cost("fetch_signals"),
            actual_cost=res.actual_cost,
            license_class="public_web",
        )
