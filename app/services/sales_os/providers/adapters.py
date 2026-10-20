"""Sales-os adapters. Unactivated providers return an empty envelope."""
import socket
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import httpx

from app.services.sales_os.discovery.identity import canonical_domain
from app.services.sales_os.providers.base import (
    AccountCandidate,
    ConnectorEnvelope,
    ContactCandidate,
    RawSignal,
    empty_envelope,
)
from app.services.sales_os.providers.honesty import is_fabricated_contact
from app.services.sales_os.providers.registry import ESTIMATED_COST, PAID_PROVIDERS, SALES_OS_CALLABLE

Transport = Callable[..., Awaitable[Any]]


def _blank(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _contact(**parts: Any) -> ContactCandidate | None:
    candidate = ContactCandidate(
        full_name=_blank(parts.get("full_name")),
        email=_blank(parts.get("email")),
        phone=_blank(parts.get("phone")),
        title=_blank(parts.get("title")),
        department=_blank(parts.get("department")),
        linkedin_url=_blank(parts.get("linkedin_url")),
        provider_id=_blank(parts.get("provider_id")),
        confidence=parts.get("confidence"),
        company_domain=canonical_domain(parts.get("company_domain")),
        company_name=_blank(parts.get("company_name")),
    )
    if is_fabricated_contact({"name": candidate.full_name, "email": candidate.email, "phone": candidate.phone}):
        return None
    if not any([candidate.full_name, candidate.email, candidate.phone, candidate.provider_id]):
        return None
    return candidate


class UnavailableAdapter:
    def __init__(self, provider_key: str):
        self.provider_key = provider_key
        self.paid = provider_key in PAID_PROVIDERS

    def capabilities(self) -> set[str]:
        return set()

    def health(self, has_credentials: bool) -> dict:
        return {"provider_key": self.provider_key, "status": "not_activated", "has_credentials": has_credentials}

    def estimate_cost(self, operation: str) -> float | None:
        return ESTIMATED_COST.get(self.provider_key)

    async def discover_accounts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        return empty_envelope(self.provider_key, "not_activated", "No adapter is activated for this provider.")

    async def discover_contacts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        return empty_envelope(self.provider_key, "not_activated", "No adapter is activated for this provider.")

    async def fetch_signals(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        return empty_envelope(self.provider_key, "not_activated", "No adapter is activated for this provider.")


class HttpAdapter:
    provider_key = ""
    paid = False
    capability_set: set[str] = set()

    def __init__(self, transport: Transport | None = None):
        self.transport = transport

    def capabilities(self) -> set[str]:
        return set(self.capability_set)

    def health(self, has_credentials: bool) -> dict:
        if self.paid and not has_credentials:
            return {"provider_key": self.provider_key, "status": "missing_credentials"}
        return {"provider_key": self.provider_key, "status": "ok"}

    def estimate_cost(self, operation: str) -> float | None:
        return ESTIMATED_COST.get(self.provider_key)

    async def _send(self, method: str, url: str, **kwargs: Any) -> Any:
        if self.transport is not None:
            return await self.transport(method, url, **kwargs)
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.request(method, url, **kwargs)
            return response

    def _needs_key(self, api_key: str | None) -> ConnectorEnvelope | None:
        if self.paid and not api_key:
            return empty_envelope(self.provider_key, "missing_credentials", "Credentials are not configured.", self.estimate_cost("discover"))
        return None

    async def discover_accounts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        blocked = self._needs_key(api_key)
        if blocked:
            return blocked
        return empty_envelope(self.provider_key, "unsupported", "This adapter does not discover accounts.")

    async def discover_contacts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        blocked = self._needs_key(api_key)
        if blocked:
            return blocked
        return empty_envelope(self.provider_key, "unsupported", "This adapter does not discover contacts.")

    async def fetch_signals(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        blocked = self._needs_key(api_key)
        if blocked:
            return blocked
        return empty_envelope(self.provider_key, "unsupported", "This adapter does not fetch signals.")


def _envelope(provider: str, status: str, **kwargs: Any) -> ConnectorEnvelope:
    return ConnectorEnvelope(provider_key=provider, status=status, estimated_cost=ESTIMATED_COST.get(provider), **kwargs)


class ApolloAdapter(HttpAdapter):
    provider_key = "apollo"
    paid = True
    capability_set = {"account_discovery", "contact_discovery", "enrichment"}

    async def discover_contacts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        blocked = self._needs_key(api_key)
        if blocked:
            return blocked
        response = await self._send(
            "POST",
            "https://api.apollo.io/api/v1/mixed_people/api_search",
            headers={"Content-Type": "application/json", "X-Api-Key": api_key or ""},
            json={"q_keywords": query, "page": 1, "per_page": count},
        )
        if response.status_code != 200:
            return _envelope("apollo", "error", request_id=_request_id(), reason=f"Apollo HTTP {response.status_code}", http_status=response.status_code)
        contacts = []
        accounts = []
        for person in (response.json() or {}).get("people") or []:
            first = _blank(person.get("first_name"))
            last = _blank(person.get("last_name"))
            if last and "***" in last:
                continue
            organization = person.get("organization") or {}
            domain = canonical_domain(organization.get("primary_domain") or organization.get("website_url"))
            name = " ".join(part for part in [first, last] if part) or None
            contact = _contact(
                full_name=name,
                email=person.get("email"),
                phone=(person.get("sanitized_phone") or person.get("primary_phone")),
                title=person.get("title"),
                provider_id=person.get("id"),
                company_domain=domain,
                company_name=organization.get("name"),
            )
            if contact:
                contacts.append(contact)
            if domain or organization.get("name"):
                accounts.append(AccountCandidate(
                    display_name=_blank(organization.get("name")),
                    canonical_domain=domain,
                    website=_blank(organization.get("website_url")),
                    confidence=None,
                ))
        return _envelope("apollo", "ok", request_id=_request_id(), contacts=contacts[:count], accounts=accounts[:count], license_class="paid_api", http_status=200)


class HunterAdapter(HttpAdapter):
    provider_key = "hunter"
    paid = True
    capability_set = {"contact_discovery", "verification"}

    async def discover_contacts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        blocked = self._needs_key(api_key)
        if blocked:
            return blocked
        domain = canonical_domain(query)
        if domain is None:
            response = await self._send(
                "POST",
                f"https://api.hunter.io/v2/discover?api_key={api_key}",
                json={"query": query},
            )
            if response.status_code != 200:
                return _envelope("hunter", "error", request_id=_request_id(), reason=f"Hunter HTTP {response.status_code}", http_status=response.status_code)
            domains = [canonical_domain(item.get("domain")) for item in (response.json() or {}).get("data") or []]
            domains = [item for item in domains if item]
            if not domains:
                return _envelope("hunter", "ok", request_id=_request_id(), reason="Hunter returned no domains.", license_class="paid_api", http_status=200)
            domain = domains[0]
        response = await self._send(
            "GET",
            f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}&type=personal&limit={count}",
        )
        if response.status_code != 200:
            return _envelope("hunter", "error", request_id=_request_id(), reason=f"Hunter HTTP {response.status_code}", http_status=response.status_code)
        data = (response.json() or {}).get("data") or {}
        contacts = []
        for email in data.get("emails") or []:
            name = " ".join(part for part in [_blank(email.get("first_name")), _blank(email.get("last_name"))] if part) or None
            contact = _contact(
                full_name=name,
                email=email.get("value"),
                phone=email.get("phone_number"),
                title=email.get("position"),
                company_domain=domain,
                company_name=data.get("organization"),
            )
            if contact:
                contacts.append(contact)
        accounts = [AccountCandidate(display_name=_blank(data.get("organization")), canonical_domain=domain)] if domain else []
        return _envelope("hunter", "ok", request_id=_request_id(), contacts=contacts[:count], accounts=accounts, license_class="paid_api", http_status=200)


class GooglePlacesAdapter(HttpAdapter):
    provider_key = "google_places"
    paid = True
    capability_set = {"account_discovery"}

    async def discover_accounts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        blocked = self._needs_key(api_key)
        if blocked:
            return blocked
        response = await self._send(
            "GET",
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params={"query": query, "key": api_key},
        )
        if response.status_code != 200:
            return _envelope("google_places", "error", request_id=_request_id(), reason=f"Places HTTP {response.status_code}", http_status=response.status_code)
        accounts = []
        for place in (response.json() or {}).get("results") or []:
            accounts.append(AccountCandidate(
                display_name=_blank(place.get("name")),
                website=None,
                hq_city=_blank(place.get("formatted_address")),
                external_id=_blank(place.get("place_id")),
            ))
            if len(accounts) >= count:
                break
        return _envelope("google_places", "ok", request_id=_request_id(), accounts=accounts, license_class="paid_api", http_status=200)


class _OrgSearchAdapter(HttpAdapter):
    """Maps an organization search body. Contact fields are copied only when present."""

    url = ""
    method = "POST"

    def _headers(self, api_key: str | None) -> dict:
        return {}

    def _body(self, query: str, count: int) -> dict:
        return {}

    def _entities(self, payload: dict) -> list[dict]:
        return []

    def _account(self, entity: dict, query: str) -> AccountCandidate | None:
        return None

    async def discover_accounts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        blocked = self._needs_key(api_key)
        if blocked:
            return blocked
        response = await self._send(self.method, self.url, headers=self._headers(api_key), json=self._body(query, count))
        if response.status_code != 200:
            return _envelope(self.provider_key, "error", request_id=_request_id(), reason=f"{self.provider_key} HTTP {response.status_code}", http_status=response.status_code)
        accounts = []
        for entity in self._entities(response.json() or {}):
            account = self._account(entity, query)
            if account and (account.display_name or account.canonical_domain):
                accounts.append(account)
        return _envelope(self.provider_key, "ok", request_id=_request_id(), accounts=accounts[:count], license_class="paid_api", http_status=200)


class CrunchbaseAdapter(_OrgSearchAdapter):
    provider_key = "crunchbase"
    paid = True
    capability_set = {"account_discovery", "intent_signal"}
    url = "https://api.crunchbase.com/api/v4/searches/organizations"

    def _headers(self, api_key: str | None) -> dict:
        return {"X-cb-user-key": api_key or "", "Content-Type": "application/json"}

    def _body(self, query: str, count: int) -> dict:
        return {"query": [{"type": "predicate", "field_id": "identifier", "operator_id": "contains", "values": [query]}], "limit": count}

    def _entities(self, payload: dict) -> list[dict]:
        return payload.get("entities") or []

    def _account(self, entity: dict, query: str) -> AccountCandidate | None:
        props = entity.get("properties") or {}
        identifier = props.get("identifier") or {}
        return AccountCandidate(display_name=_blank(identifier.get("value")), website=_blank(props.get("website_url")))


class ClearbitAdapter(_OrgSearchAdapter):
    provider_key = "clearbit"
    paid = True
    capability_set = {"account_discovery", "enrichment"}
    method = "GET"
    url = "https://discovery.clearbit.com/v1/companies/search"

    def _headers(self, api_key: str | None) -> dict:
        return {"Authorization": f"Bearer {api_key or ''}"}

    async def discover_accounts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        blocked = self._needs_key(api_key)
        if blocked:
            return blocked
        response = await self._send("GET", f"{self.url}?query=name:{query}&limit={count}", headers=self._headers(api_key))
        if response.status_code != 200:
            return _envelope("clearbit", "error", request_id=_request_id(), reason=f"Clearbit HTTP {response.status_code}", http_status=response.status_code)
        accounts = []
        for company in (response.json() or {}).get("results") or []:
            accounts.append(AccountCandidate(
                display_name=_blank(company.get("name")),
                canonical_domain=canonical_domain(company.get("domain")),
                employee_count=company.get("metrics", {}).get("employees") if isinstance(company.get("metrics"), dict) else None,
            ))
        return _envelope("clearbit", "ok", request_id=_request_id(), accounts=accounts[:count], license_class="paid_api", http_status=200)


class ZoomInfoAdapter(HttpAdapter):
    provider_key = "zoominfo"
    paid = True
    capability_set = {"contact_discovery"}

    async def discover_contacts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        blocked = self._needs_key(api_key)
        if blocked:
            return blocked
        token = api_key or ""
        if ":" in token:
            username, password = token.split(":", 1)
            auth = await self._send(
                "POST",
                "https://api.zoominfo.com/authenticate",
                json={"username": username, "password": password},
            )
            if auth.status_code != 200:
                return _envelope("zoominfo", "error", request_id=_request_id(), reason=f"ZoomInfo auth HTTP {auth.status_code}", http_status=auth.status_code)
            token = _blank((auth.json() or {}).get("jwt")) or ""
            if not token:
                return _envelope("zoominfo", "error", request_id=_request_id(), reason="ZoomInfo did not return a JWT.")
        return await _bearer_people_search(self, query, token, count, "https://api.zoominfo.com/search/contact", "data", "firstName", "lastName", "email", "phone", "jobTitle", "companyName")


class CognismAdapter(HttpAdapter):
    provider_key = "cognism"
    paid = True
    capability_set = {"contact_discovery"}

    async def discover_contacts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        return await _bearer_people_search(self, query, api_key, count, "https://api.cognism.com/api/v2/search/contacts", "contacts", "firstName", "lastName", "emailAddress", "directDial", "jobTitle", "companyName")


class PeopleDataLabsAdapter(HttpAdapter):
    provider_key = "people_data_labs"
    paid = True
    capability_set = {"contact_discovery", "enrichment"}

    async def discover_contacts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        blocked = self._needs_key(api_key)
        if blocked:
            return blocked
        response = await self._send(
            "POST",
            "https://api.peopledatalabs.com/v5/person/search",
            headers={"X-Api-Key": api_key or "", "Content-Type": "application/json"},
            json={"size": count, "query": {"term": {"job_company_name": query}}},
        )
        if response.status_code != 200:
            return _envelope("people_data_labs", "error", request_id=_request_id(), reason=f"PDL HTTP {response.status_code}", http_status=response.status_code)
        contacts = []
        for person in (response.json() or {}).get("data") or []:
            emails = person.get("emails") or []
            phones = person.get("phone_numbers") or []
            email = emails[0].get("address") if emails and isinstance(emails[0], dict) else None
            phone = phones[0] if phones else None
            contact = _contact(
                full_name=person.get("full_name"),
                email=email,
                phone=phone,
                title=person.get("job_title"),
                provider_id=person.get("id"),
                company_name=person.get("job_company_name") or query,
            )
            if contact:
                contacts.append(contact)
        return _envelope("people_data_labs", "ok", request_id=_request_id(), contacts=contacts[:count], license_class="paid_api", http_status=200)


async def _bearer_people_search(adapter: HttpAdapter, query: str, api_key: str | None, count: int, url: str, list_key: str, first_key: str, last_key: str, email_key: str, phone_key: str, title_key: str, company_key: str) -> ConnectorEnvelope:
    blocked = adapter._needs_key(api_key)
    if blocked:
        return blocked
    response = await adapter._send(
        "POST",
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"query": query, "companyName": query, "limit": count, "rpp": count},
    )
    if response.status_code != 200:
        return _envelope(adapter.provider_key, "error", request_id=_request_id(), reason=f"{adapter.provider_key} HTTP {response.status_code}", http_status=response.status_code)
    contacts = []
    for person in (response.json() or {}).get(list_key) or []:
        name = " ".join(part for part in [_blank(person.get(first_key)), _blank(person.get(last_key))] if part) or None
        contact = _contact(
            full_name=name,
            email=person.get(email_key),
            phone=person.get(phone_key),
            title=person.get(title_key),
            company_name=person.get(company_key),
        )
        if contact:
            contacts.append(contact)
    return _envelope(adapter.provider_key, "ok", request_id=_request_id(), contacts=contacts[:count], license_class="paid_api", http_status=200)


class HackerNewsHiringAdapter(HttpAdapter):
    provider_key = "hn_hiring"
    paid = False
    capability_set = {"intent_signal", "account_discovery"}

    async def fetch_signals(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        response = await self._send(
            "GET",
            "https://hn.algolia.com/api/v1/search",
            params={"query": f"{query} hiring", "tags": "comment", "hitsPerPage": count},
        )
        if response.status_code != 200:
            return _envelope("hn_hiring", "error", request_id=_request_id(), reason=f"HN HTTP {response.status_code}", http_status=response.status_code)
        signals = []
        for hit in (response.json() or {}).get("hits") or []:
            story_id = hit.get("story_id") or hit.get("objectID")
            excerpt = _blank(hit.get("comment_text"))
            if not excerpt:
                continue
            signals.append(RawSignal(
                signal_type="job_opening",
                summary=excerpt[:280],
                source_url=f"https://news.ycombinator.com/item?id={story_id}" if story_id else None,
                base_strength=60,
                source_confidence=0.7,
                payload={"object_id": hit.get("objectID"), "author": hit.get("author")},
                independent_key=f"hn:{hit.get('objectID')}",
                excerpt=excerpt[:280],
            ))
        return _envelope("hn_hiring", "ok", request_id=_request_id(), signals=signals[:count], actual_cost=0.0, license_class="public_api", http_status=200)


class DnsMxAdapter:
    provider_key = "dns_mx_inspect"
    paid = False

    def __init__(self, resolver: Callable[[str], list[str]] | None = None):
        self.resolver = resolver or _resolve_mx

    def capabilities(self) -> set[str]:
        return {"intent_signal", "enrichment"}

    def health(self, has_credentials: bool) -> dict:
        return {"provider_key": self.provider_key, "status": "ok"}

    def estimate_cost(self, operation: str) -> float | None:
        return 0.0

    async def discover_accounts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        return empty_envelope(self.provider_key, "unsupported", "DNS inspection does not discover accounts.", 0.0)

    async def discover_contacts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        return empty_envelope(self.provider_key, "unsupported", "DNS inspection does not discover contacts.", 0.0)

    async def fetch_signals(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        domain = canonical_domain(query)
        if not domain:
            return empty_envelope(self.provider_key, "ok", "No canonical domain to inspect.", 0.0)
        try:
            hosts = self.resolver(domain)
        except Exception as exc:
            return _envelope("dns_mx_inspect", "error", request_id=_request_id(), reason=f"MX lookup failed: {exc}"[:200], actual_cost=0.0)
        if not hosts:
            return _envelope("dns_mx_inspect", "ok", request_id=_request_id(), reason="No MX records were returned. This is not treated as proof of absence.", actual_cost=0.0, license_class="public_protocol")
        summary = "MX hosts: " + ", ".join(hosts)
        signal = RawSignal(
            signal_type="tech_added",
            summary=summary,
            source_url=None,
            observed_at=datetime.now(timezone.utc),
            base_strength=40,
            source_confidence=0.9,
            payload={"domain": domain, "mx": hosts},
            independent_key=f"mx:{domain}:{','.join(sorted(hosts))}",
            excerpt=summary,
        )
        return _envelope(
            "dns_mx_inspect",
            "ok",
            request_id=_request_id(),
            accounts=[AccountCandidate(canonical_domain=domain, display_name=domain)],
            signals=[signal],
            actual_cost=0.0,
            license_class="public_protocol",
        )


def _resolve_mx(domain: str) -> list[str]:
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, "MX")
        return [str(item.exchange).rstrip(".") for item in answers]
    except Exception:
        hosts: list[str] = []
        try:
            socket.getaddrinfo(domain, 25)
        except Exception:
            return hosts
        return hosts


def _request_id() -> str:
    import uuid
    return str(uuid.uuid4())


def build_adapter(provider_key: str, transport: Transport | None = None) -> Any:
    from app.services.sales_os.providers.catalogue_fetch import SPECS, CatalogueAdapter

    mapping = {
        "apollo": ApolloAdapter,
        "hunter": HunterAdapter,
        "google_places": GooglePlacesAdapter,
        "crunchbase": CrunchbaseAdapter,
        "clearbit": ClearbitAdapter,
        "zoominfo": ZoomInfoAdapter,
        "cognism": CognismAdapter,
        "people_data_labs": PeopleDataLabsAdapter,
        "hn_hiring": HackerNewsHiringAdapter,
    }
    if provider_key == "dns_mx_inspect":
        return DnsMxAdapter()
    if provider_key == "apify" or provider_key.startswith("apify_"):
        from app.services.sales_os.providers.apify_adapter import ApifyAdapter
        return ApifyAdapter(provider_key=provider_key, transport=transport)
    if provider_key in mapping and provider_key in SALES_OS_CALLABLE:
        return mapping[provider_key](transport=transport)
    if provider_key in SPECS:
        return CatalogueAdapter(provider_key, transport=transport)
    return UnavailableAdapter(provider_key)
