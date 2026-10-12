"""Real lead retrieval for catalogue sources that do not have a dedicated adapter.

Each runner calls a public feed or a documented vendor API. Contact fields are copied
only when that response includes them. Sources with no such API return an explicit
status and do not invent a person, an email, or a phone.
"""
from __future__ import annotations

import csv
import io
import re
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from urllib.parse import quote_plus, urlparse

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

Transport = Callable[..., Awaitable[Any]]
USER_AGENT = "OctaOS-Sales/1.0 (lead-discovery)"
_EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    level: str
    needs_key: bool
    paid: bool
    capabilities: frozenset[str]
    run: Callable[..., Awaitable[ConnectorEnvelope]]


def _request_id() -> str:
    return str(uuid.uuid4())


def _blank(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def _safe_reason(value: Any) -> str:
    text = _EMAIL_RE.sub("[email]", str(value or ""))
    return text[:200]


def _envelope(provider: str, status: str, reason: str | None = None, **kwargs: Any) -> ConnectorEnvelope:
    return ConnectorEnvelope(
        provider_key=provider,
        request_id=_request_id(),
        status=status,
        reason=_safe_reason(reason) if reason else None,
        **kwargs,
    )


def _contact(**parts: Any) -> ContactCandidate | None:
    candidate = ContactCandidate(
        full_name=_blank(parts.get("full_name")),
        email=_blank(parts.get("email")),
        phone=_blank(parts.get("phone")),
        title=_blank(parts.get("title")),
        department=_blank(parts.get("department")),
        linkedin_url=_blank(parts.get("linkedin_url")),
        provider_id=_blank(parts.get("provider_id")),
        confidence=None,
        company_domain=canonical_domain(parts.get("company_domain")),
        company_name=_blank(parts.get("company_name")),
    )
    if is_fabricated_contact({"name": candidate.full_name, "email": candidate.email, "phone": candidate.phone}):
        return None
    if not any([candidate.full_name, candidate.email, candidate.phone, candidate.provider_id]):
        return None
    return candidate


def _account(**parts: Any) -> AccountCandidate | None:
    account = AccountCandidate(
        display_name=_blank(parts.get("display_name")),
        canonical_domain=canonical_domain(parts.get("canonical_domain") or parts.get("website")),
        website=_blank(parts.get("website")),
        industry=_blank(parts.get("industry")),
        employee_count=parts.get("employee_count") if isinstance(parts.get("employee_count"), int) else None,
        hq_country=_blank(parts.get("hq_country")),
        hq_city=_blank(parts.get("hq_city")),
        external_id=_blank(parts.get("external_id")),
    )
    if not account.display_name and not account.canonical_domain:
        return None
    return account


def _signal(signal_type: str, summary: str | None, source_url: str | None = None, **payload: Any) -> RawSignal | None:
    text = _blank(summary)
    if not text:
        return None
    key = _blank(payload.pop("independent_key", None)) or source_url or text[:120]
    return RawSignal(
        signal_type=signal_type,
        summary=text[:300],
        source_url=_blank(source_url),
        base_strength=payload.pop("base_strength", 50),
        source_confidence=payload.pop("source_confidence", 0.7),
        payload=payload,
        independent_key=key[:180],
        excerpt=text[:300],
    )


def _slugs(query: str) -> list[str]:
    domain = canonical_domain(query)
    raw = domain.split(".")[0] if domain else query
    hyphen = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    compact = hyphen.replace("-", "")
    slugs: list[str] = []
    for item in (hyphen, compact):
        if item and item not in slugs:
            slugs.append(item)
    return slugs[:2]


def _public_domain(query: str) -> str | None:
    domain = canonical_domain(query)
    if not domain:
        return None
    if domain.endswith((".local", ".internal", ".localhost", ".invalid")):
        return None
    host = domain.split(":")[0]
    if host in {"localhost", "metadata.google.internal"}:
        return None
    return domain


def _email_in(value: str | None) -> str | None:
    if not value:
        return None
    match = _EMAIL_RE.search(value)
    if not match:
        return None
    email = match.group(0).strip(".,;:<>")
    if is_fabricated_contact({"email": email}):
        return None
    return email


def _xml_entries(text: str) -> list[dict[str, str]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    rows: list[dict[str, str]] = []
    for item in root.findall(".//item"):
        title = _blank(item.findtext("title")) or ""
        link = _blank(item.findtext("link")) or ""
        if title:
            rows.append({"title": title, "link": link})
    if rows:
        return rows
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//a:entry", ns):
        title = _blank(entry.findtext("a:title", default="", namespaces=ns)) or ""
        link_el = entry.find("a:link", ns)
        link = ""
        if link_el is not None:
            link = _blank(link_el.get("href")) or ""
        if title:
            rows.append({"title": title, "link": link})
    return rows


def _items_of(payload: Any, *keys: str) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            for nested in ("data", "results", "items", "contacts", "companies", "people"):
                inner = value.get(nested)
                if isinstance(inner, list):
                    return [item for item in inner if isinstance(item, dict)]
    return []


class CatalogueAdapter:
    def __init__(self, provider_key: str, transport: Transport | None = None):
        spec = SPECS[provider_key]
        self.provider_key = provider_key
        self.paid = spec.paid
        self._spec = spec
        self.transport = transport

    def capabilities(self) -> set[str]:
        return set(self._spec.capabilities)

    def health(self, has_credentials: bool) -> dict:
        if self._spec.needs_key and not has_credentials:
            return {"provider_key": self.provider_key, "status": "missing_credentials"}
        return {"provider_key": self.provider_key, "status": "ok"}

    def estimate_cost(self, operation: str) -> float | None:
        return 0.0 if not self.paid else None

    async def _send(self, method: str, url: str, **kwargs: Any) -> Any:
        if self.transport is not None:
            return await self.transport(method, url, **kwargs)
        timeout = kwargs.pop("timeout", 8.0)
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.setdefault("User-Agent", USER_AGENT)
        headers.setdefault("Accept", "application/json, application/xml, text/xml, */*")
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            return await client.request(method, url, headers=headers, **kwargs)

    async def _run(self, query: str, api_key: str | None, count: int) -> ConnectorEnvelope:
        if self._spec.needs_key and not api_key:
            return empty_envelope(self.provider_key, "missing_credentials", "Credentials are not configured.")
        try:
            return await self._spec.run(self.provider_key, query, api_key, count, self._send)
        except Exception as exc:
            return _envelope(self.provider_key, "error", reason=f"{type(exc).__name__}: {exc}")

    async def discover_accounts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        return await self._run(query, api_key, count)

    async def discover_contacts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        return await self._run(query, api_key, count)

    async def fetch_signals(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        return await self._run(query, api_key, count)


async def _read_json(send, method: str, url: str, **kwargs: Any) -> tuple[int, Any, str]:
    response = await send(method, url, **kwargs)
    status = getattr(response, "status_code", 0)
    text = getattr(response, "text", "") or ""
    if status == 404:
        return status, None, text
    try:
        return status, response.json(), text
    except Exception:
        return status, None, text


def _news_envelope(provider: str, rows: list[dict[str, str]], signal_type: str, query: str, license_class: str) -> ConnectorEnvelope:
    accounts: list[AccountCandidate] = []
    signals: list[RawSignal] = []
    seen: set[str] = set()
    for row in rows:
        title = row.get("title") or ""
        link = row.get("link") or ""
        subject = title.split(" - ")[0].strip() or query
        if subject.lower() in seen:
            continue
        seen.add(subject.lower())
        account = _account(display_name=subject[:180], website=link if link.startswith("http") and "news.google.com" not in link else None)
        if account:
            accounts.append(account)
        signal = _signal(signal_type, title, link or None, retrieved_via=license_class, query=query, independent_key=link or title)
        if signal:
            signals.append(signal)
    return _envelope(provider, "ok", accounts=accounts, signals=signals, actual_cost=0.0, license_class=license_class)


async def _google_news(provider: str, query: str, signal_type: str, count: int, send, site: str | None = None, extra: str = "") -> ConnectorEnvelope:
    terms = " ".join(part for part in (f"site:{site}" if site else "", query, extra) if part).strip()
    if not terms:
        return _envelope(provider, "ok", reason="No query to search.", actual_cost=0.0, license_class="public_rss")
    url = f"https://news.google.com/rss/search?q={quote_plus(terms)}&hl=en-US&gl=US&ceid=US:en"
    response = await send("GET", url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml"})
    status = getattr(response, "status_code", 0)
    if status != 200:
        return _envelope(provider, "error", reason=f"Google News HTTP {status}", http_status=status)
    tokens = [part for part in re.findall(r"[a-z0-9]{4,}", query.lower())]
    rows = []
    for row in _xml_entries(getattr(response, "text", "") or ""):
        hay = row["title"].lower()
        if tokens and not any(token in hay for token in tokens):
            continue
        rows.append(row)
        if len(rows) >= count:
            break
    if not rows:
        return _envelope(provider, "ok", reason="The news feed returned no items that mention the query.", actual_cost=0.0, license_class="public_rss")
    return _news_envelope(provider, rows, signal_type, query, "public_rss")


def _news_runner(signal_type: str, site: str | None = None, extra: str = ""):
    async def run(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
        del api_key
        return await _google_news(provider, query, signal_type, count, send, site=site, extra=extra)
    return run


async def _job_board(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    del api_key
    slugs = _slugs(query)
    if not slugs:
        return _envelope(provider, "ok", reason="No company slug could be derived from the query.", actual_cost=0.0)
    last_status = None
    for slug in slugs:
        if provider == "greenhouse":
            url = f"https://boards-api.greenhouse.io/v1/boards/{quote_plus(slug)}/jobs"
        elif provider == "lever":
            url = f"https://api.lever.co/v0/postings/{quote_plus(slug)}?mode=json"
        elif provider == "ashby":
            url = f"https://api.ashbyhq.com/posting-api/job-board/{quote_plus(slug)}"
        else:
            url = f"https://apply.workable.com/api/v1/widget/accounts/{quote_plus(slug)}"
        status, payload, _text = await _read_json(send, "GET", url)
        last_status = status
        if status != 200 or payload is None:
            continue
        jobs: list[dict] = []
        company = slug.replace("-", " ").title()
        if provider == "workable" and isinstance(payload, dict):
            company = _blank(payload.get("name")) or company
            jobs = _items_of(payload, "jobs")
        elif provider == "ashby":
            jobs = _items_of(payload, "jobs")
        elif provider == "lever":
            jobs = _items_of(payload, "postings") or (payload if isinstance(payload, list) else [])
        else:
            jobs = _items_of(payload, "jobs")
        if not jobs:
            continue
        accounts = [_account(display_name=company, external_id=slug)]
        signals: list[RawSignal] = []
        for job in jobs[:count]:
            title = _blank(job.get("title") or job.get("text") or job.get("name"))
            link = _blank(job.get("absolute_url") or job.get("hostedUrl") or job.get("jobUrl") or job.get("url") or job.get("shortlink"))
            location = job.get("location")
            if isinstance(location, dict):
                location = location.get("name")
            summary = title or "Open role"
            if location and isinstance(location, str):
                summary = f"{summary} ({location})"
            signal = _signal("job_opening", summary, link, company=company, independent_key=f"{provider}:{slug}:{job.get('id') or title}")
            if signal:
                signals.append(signal)
        if signals:
            account = accounts[0]
            return _envelope(provider, "ok", accounts=[account] if account else [], signals=signals, actual_cost=0.0, license_class="public_api")
    if last_status and last_status >= 500:
        return _envelope(provider, "error", reason=f"{provider} HTTP {last_status}", http_status=last_status)
    return _envelope(provider, "ok", reason="No public job board returned openings for this company.", actual_cost=0.0, license_class="public_api")


async def _hn(provider: str, query: str, api_key: str | None, count: int, send, suffix: str, tags: str, signal_type: str) -> ConnectorEnvelope:
    del api_key
    status, payload, _text = await _read_json(
        send,
        "GET",
        "https://hn.algolia.com/api/v1/search",
        params={"query": f"{query} {suffix}".strip(), "tags": tags, "hitsPerPage": count},
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"HN HTTP {status}", http_status=status)
    signals: list[RawSignal] = []
    accounts: list[AccountCandidate] = []
    for hit in payload.get("hits") or []:
        if not isinstance(hit, dict):
            continue
        title = _blank(hit.get("title") or hit.get("story_title") or hit.get("comment_text"))
        story_id = hit.get("story_id") or hit.get("objectID")
        link = f"https://news.ycombinator.com/item?id={story_id}" if story_id else None
        signal = _signal(signal_type, (title or "")[:280], link, author=hit.get("author"), independent_key=f"hn:{hit.get('objectID')}")
        if signal:
            signals.append(signal)
        email = _email_in(hit.get("comment_text") or "")
        if email:
            contact_account = _account(display_name=hit.get("author") or query)
            if contact_account and not accounts:
                accounts.append(contact_account)
    return _envelope(provider, "ok", accounts=accounts, signals=signals[:count], actual_cost=0.0, license_class="public_api")


async def _sec(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    del api_key
    status, payload, _text = await _read_json(
        send,
        "GET",
        "https://efts.sec.gov/LATEST/search-index",
        params={"q": f'"{query}"', "forms": "D,S-1,8-K,10-K"},
        headers={"User-Agent": "OctaOS research dev@localhost", "Accept": "application/json"},
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"SEC HTTP {status}", http_status=status)
    hits = ((payload.get("hits") or {}).get("hits") or [])[:40]
    accounts: list[AccountCandidate] = []
    signals: list[RawSignal] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        source = hit.get("_source") or {}
        names = source.get("display_names") or []
        name = names[0] if isinstance(names, list) and names else query
        if isinstance(name, str):
            name = name.split("  (")[0].strip()
        if query.lower() not in str(name).lower() and query.lower() not in str(source).lower():
            continue
        form = _blank(source.get("form") or source.get("file_type")) or "filing"
        filed = _blank(source.get("file_date"))
        ciks = source.get("ciks") or []
        cik = ciks[0] if isinstance(ciks, list) and ciks else None
        link = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}" if cik else None
        signal_type = "funding_round" if form.upper() in {"D", "S-1"} else "product_launch"
        summary = f"SEC {form} filing: {name}" + (f" filed {filed}" if filed else "")
        signal = _signal(signal_type, summary, link, form=form, independent_key=str(hit.get("_id") or summary))
        if signal:
            signals.append(signal)
        account = _account(display_name=name, external_id=str(cik) if cik else None)
        if account:
            accounts.append(account)
        if len(signals) >= count:
            break
    return _envelope(provider, "ok", accounts=accounts[:count], signals=signals, actual_cost=0.0, license_class="public_api")


async def _ted(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    del api_key
    safe = re.sub(r"[^A-Za-z0-9 .&-]", " ", query).strip() or query
    status, payload, _text = await _read_json(
        send,
        "POST",
        "https://api.ted.europa.eu/v3/notices/search",
        json={"query": f'buyer-name ~ "{safe}" OR notice-title ~ "{safe}"', "limit": count, "page": 1, "fields": ["publication-number", "notice-title", "buyer-name"]},
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"TED HTTP {status}", http_status=status)
    accounts: list[AccountCandidate] = []
    signals: list[RawSignal] = []
    for notice in (payload.get("notices") or [])[:count]:
        if not isinstance(notice, dict):
            continue
        title = notice.get("notice-title")
        if isinstance(title, dict):
            title = next(iter(title.values()), None)
            if isinstance(title, list):
                title = title[0] if title else None
        buyer = notice.get("buyer-name")
        if isinstance(buyer, dict):
            buyer = next(iter(buyer.values()), None)
            if isinstance(buyer, list):
                buyer = buyer[0] if buyer else None
        pub = _blank(notice.get("publication-number"))
        link = f"https://ted.europa.eu/en/notice/{pub}/html" if pub else None
        name = _blank(buyer) or _blank(title) or query
        signal = _signal("tender", _blank(title) or f"TED notice {pub or name}", link, buyer=buyer, independent_key=pub or name)
        if signal:
            signals.append(signal)
        account = _account(display_name=name, external_id=pub)
        if account:
            accounts.append(account)
    return _envelope(provider, "ok", accounts=accounts, signals=signals, actual_cost=0.0, license_class="public_api")


async def _world_bank(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    del api_key
    status, payload, _text = await _read_json(
        send,
        "GET",
        "https://search.worldbank.org/api/v2/procnotices",
        params={"format": "json", "qterm": query, "rows": count},
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"World Bank HTTP {status}", http_status=status)
    accounts: list[AccountCandidate] = []
    signals: list[RawSignal] = []
    for notice in (payload.get("procnotices") or [])[:count]:
        if not isinstance(notice, dict):
            continue
        name = _blank(notice.get("project_name") or notice.get("bid_description") or notice.get("notice_type"))
        notice_id = _blank(notice.get("id"))
        summary = " ".join(part for part in (_blank(notice.get("notice_type")), name, _blank(notice.get("noticedate"))) if part)
        signal = _signal("procurement_notice", summary or name, None, independent_key=notice_id or summary)
        if signal:
            signals.append(signal)
        account = _account(display_name=name, hq_country=_blank(notice.get("notice_lang_name")), external_id=notice_id)
        if account:
            accounts.append(account)
    return _envelope(provider, "ok", accounts=accounts, signals=signals, actual_cost=0.0, license_class="public_api")


async def _nominatim(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    del api_key
    status, payload, _text = await _read_json(
        send,
        "GET",
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "jsonv2", "addressdetails": 1, "extratags": 1, "limit": count},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    if status != 200 or not isinstance(payload, list):
        return _envelope(provider, "error", reason=f"OpenStreetMap HTTP {status}", http_status=status)
    accounts: list[AccountCandidate] = []
    contacts: list[ContactCandidate] = []
    for place in payload[:count]:
        if not isinstance(place, dict):
            continue
        address = place.get("address") or {}
        tags = place.get("extratags") or {}
        website = _blank(tags.get("website") or tags.get("contact:website"))
        account = _account(
            display_name=place.get("name") or place.get("display_name"),
            website=website,
            hq_city=_blank(address.get("city") or address.get("town") or address.get("village")),
            hq_country=_blank(address.get("country")),
            external_id=str(place.get("osm_id") or ""),
        )
        if account:
            accounts.append(account)
        phone = _blank(tags.get("phone") or tags.get("contact:phone"))
        contact = _contact(full_name=tags.get("contact:name"), phone=phone, company_name=account.display_name if account else None, company_domain=website)
        if contact:
            contacts.append(contact)
    return _envelope(provider, "ok", accounts=accounts, contacts=contacts, actual_cost=0.0, license_class="public_api")


async def _itunes(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    del api_key
    status, payload, _text = await _read_json(
        send,
        "GET",
        "https://itunes.apple.com/search",
        params={"term": query, "entity": "software", "limit": count},
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"iTunes HTTP {status}", http_status=status)
    accounts: list[AccountCandidate] = []
    signals: list[RawSignal] = []
    for app in (payload.get("results") or [])[:count]:
        if not isinstance(app, dict):
            continue
        name = _blank(app.get("trackName") or app.get("sellerName"))
        seller = _blank(app.get("sellerName") or app.get("artistName"))
        link = _blank(app.get("trackViewUrl"))
        account = _account(display_name=seller or name, website=link, external_id=str(app.get("trackId") or ""))
        if account:
            accounts.append(account)
        rating = app.get("averageUserRating")
        signal_type = "low_rating" if isinstance(rating, (int, float)) and rating < 3.5 else "product_launch"
        summary = name or seller
        if isinstance(rating, (int, float)):
            summary = f"{summary} rating {rating}"
        signal = _signal(signal_type, summary, link, independent_key=str(app.get("trackId") or summary))
        if signal:
            signals.append(signal)
    return _envelope(provider, "ok", accounts=accounts, signals=signals, actual_cost=0.0, license_class="public_api")


async def _github(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    status, payload, _text = await _read_json(
        send,
        "GET",
        "https://api.github.com/search/users",
        params={"q": f"{query} type:org", "per_page": count},
        headers=headers,
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"GitHub HTTP {status}", http_status=status)
    accounts: list[AccountCandidate] = []
    signals: list[RawSignal] = []
    for org in (payload.get("items") or [])[:count]:
        if not isinstance(org, dict):
            continue
        login = _blank(org.get("login"))
        link = _blank(org.get("html_url"))
        account = _account(display_name=login, website=link, external_id=str(org.get("id") or ""))
        if account:
            accounts.append(account)
        signal = _signal("tech_added", f"GitHub organization {login} matches {query}", link, independent_key=f"gh:{org.get('id')}")
        if signal:
            signals.append(signal)
    return _envelope(provider, "ok", accounts=accounts, signals=signals, actual_cost=0.0, license_class="public_api")


async def _certs(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    del api_key
    domain = _public_domain(query)
    if not domain:
        return _envelope(provider, "ok", reason="Certificate search needs a domain.", actual_cost=0.0)
    status, payload, _text = await _read_json(
        send,
        "GET",
        "https://api.certspotter.com/v1/issuances",
        params={"domain": domain, "include_subdomains": "true", "expand": "dns_names"},
    )
    if status != 200 or not isinstance(payload, list):
        return _envelope(provider, "error", reason=f"Certificate transparency HTTP {status}", http_status=status)
    names: list[str] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        for dns in row.get("dns_names") or []:
            if isinstance(dns, str) and dns not in names:
                names.append(dns)
            if len(names) >= count:
                break
    if not names:
        return _envelope(provider, "ok", reason="No certificate names were returned.", actual_cost=0.0, license_class="public_api")
    summary = "Certificate names: " + ", ".join(names[:count])
    signal = _signal("tech_added", summary, f"https://api.certspotter.com/v1/issuances?domain={domain}", domain=domain, independent_key=f"ct:{domain}:{','.join(names[:5])}")
    account = _account(display_name=domain, canonical_domain=domain, website=f"https://{domain}")
    return _envelope(
        provider,
        "ok",
        accounts=[account] if account else [],
        signals=[signal] if signal else [],
        actual_cost=0.0,
        license_class="public_api",
    )


async def _product_hunt(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    del api_key
    response = await send("GET", "https://www.producthunt.com/feed", headers={"User-Agent": USER_AGENT, "Accept": "application/atom+xml"})
    status = getattr(response, "status_code", 0)
    if status != 200:
        return _envelope(provider, "error", reason=f"Product Hunt HTTP {status}", http_status=status)
    needle = query.lower().strip()
    rows = [row for row in _xml_entries(getattr(response, "text", "") or "") if not needle or needle in row["title"].lower()][:count]
    if not rows:
        return _envelope(provider, "ok", reason="No Product Hunt posts matched the query.", actual_cost=0.0, license_class="public_rss")
    return _news_envelope(provider, rows, "product_launch", query, "public_rss")


async def _career_page(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    del api_key
    domain = _public_domain(query)
    if not domain:
        return _envelope(provider, "ok", reason="Career-page lookup needs a company domain.", actual_cost=0.0)
    signals: list[RawSignal] = []
    contacts: list[ContactCandidate] = []
    for path in ("/careers", "/jobs"):
        url = f"https://{domain}{path}"
        response = await send("GET", url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
        status = getattr(response, "status_code", 0)
        final_url = str(getattr(response, "url", url))
        host = (urlparse(final_url).hostname or "").lower()
        if host in {"localhost", "metadata.google.internal"} or host.endswith(".internal"):
            continue
        if status != 200:
            continue
        html = (getattr(response, "text", "") or "")[:400_000]
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
        page_title = _blank(re.sub(r"\s+", " ", title_match.group(1))) if title_match else None
        if page_title:
            signal = _signal("hiring_page_change", page_title, url, independent_key=f"career:{url}")
            if signal:
                signals.append(signal)
        for email in _EMAIL_RE.findall(html)[:count]:
            contact = _contact(email=email, company_domain=domain, company_name=domain)
            if contact:
                contacts.append(contact)
        for href, text in re.findall(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>([^<]{2,80})</a>", html, flags=re.I)[: count * 3]:
            if "/job" not in href.lower() and "career" not in href.lower():
                continue
            label = _blank(re.sub(r"\s+", " ", text))
            link = href if href.startswith("http") else f"https://{domain}{href if href.startswith('/') else '/' + href}"
            signal = _signal("job_opening", label, link, independent_key=link)
            if signal:
                signals.append(signal)
            if len(signals) >= count:
                break
        if signals or contacts:
            break
    account = _account(display_name=domain, canonical_domain=domain, website=f"https://{domain}")
    return _envelope(
        provider,
        "ok",
        accounts=[account] if account and (signals or contacts) else [],
        contacts=contacts[:count],
        signals=signals[:count],
        actual_cost=0.0,
        license_class="public_page",
        reason=None if signals or contacts else "The public careers page returned no job links or emails.",
    )


async def _places_like(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    status, payload, _text = await _read_json(
        send,
        "GET",
        "https://maps.googleapis.com/maps/api/place/textsearch/json",
        params={"query": query, "key": api_key},
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"Places HTTP {status}", http_status=status)
    api_status = payload.get("status")
    if api_status not in {None, "OK", "ZERO_RESULTS"}:
        return _envelope(provider, "error", reason=f"Places status {api_status}", http_status=status)
    accounts: list[AccountCandidate] = []
    signals: list[RawSignal] = []
    for place in (payload.get("results") or [])[:count]:
        if not isinstance(place, dict):
            continue
        account = _account(
            display_name=place.get("name"),
            hq_city=_blank(place.get("formatted_address")),
            external_id=_blank(place.get("place_id")),
        )
        if account:
            accounts.append(account)
        rating = place.get("rating")
        if isinstance(rating, (int, float)):
            signal = _signal(
                "low_rating" if rating < 3.5 else "product_launch",
                f"{place.get('name')} rating {rating}",
                None,
                independent_key=str(place.get("place_id") or place.get("name")),
            )
            if signal:
                signals.append(signal)
    return _envelope(provider, "ok", accounts=accounts, signals=signals, license_class="paid_api", http_status=200)


def _people_from_rows(rows: list[dict], query: str) -> tuple[list[AccountCandidate], list[ContactCandidate]]:
    accounts: list[AccountCandidate] = []
    contacts: list[ContactCandidate] = []
    for row in rows:
        if isinstance(row.get("properties"), dict):
            merged = dict(row["properties"])
            merged.setdefault("id", row.get("id"))
            row = {**row, **merged}
        if isinstance(row.get("item"), dict):
            row = {**row, **row["item"]}
        first = _blank(row.get("first_name") or row.get("firstName") or row.get("firstname"))
        last = _blank(row.get("last_name") or row.get("lastName") or row.get("lastname"))
        name = _blank(row.get("full_name") or row.get("fullName"))
        if not name and (first or last):
            name = " ".join(part for part in (first, last) if part)
        elif not name and (row.get("email") or row.get("jobTitle") or row.get("job_title") or row.get("title")):
            name = _blank(row.get("name"))
        email = _blank(row.get("email") or row.get("emailAddress") or row.get("value"))
        if isinstance(row.get("emails"), list) and row["emails"]:
            item = row["emails"][0]
            email = _blank(item.get("address") or item.get("email") or item.get("value")) if isinstance(item, dict) else _blank(item)
        phone = _blank(row.get("phone") or row.get("phone_number") or row.get("directDial"))
        if isinstance(row.get("phones"), list) and row["phones"]:
            item = row["phones"][0]
            phone = _blank(item.get("number") or item.get("phone")) if isinstance(item, dict) else _blank(item)
        business_name = _blank(row.get("name"))
        company = _blank(row.get("company") or row.get("companyName") or row.get("organization") or row.get("current_employer"))
        if not company and business_name and business_name != name:
            company = business_name
        company = company or _blank(query)
        if isinstance(row.get("account"), dict):
            company = _blank(row["account"].get("name")) or company
        domain = _blank(row.get("domain") or row.get("website") or row.get("company_domain"))
        title = _blank(row.get("title") or row.get("jobTitle") or row.get("job_title") or row.get("position"))
        contact = _contact(
            full_name=name,
            email=email,
            phone=phone,
            title=title,
            linkedin_url=row.get("linkedin_url") or row.get("linkedinUrl"),
            provider_id=row.get("id") or row.get("provider_id"),
            company_name=company,
            company_domain=domain,
        )
        if contact:
            contacts.append(contact)
        account = _account(display_name=company, website=domain, canonical_domain=domain)
        if account:
            accounts.append(account)
    return accounts, contacts


async def _keyed_json(
    provider: str,
    query: str,
    api_key: str | None,
    count: int,
    send,
    *,
    method: str,
    url: str,
    headers: dict | None = None,
    params: dict | None = None,
    body: dict | None = None,
    list_keys: tuple[str, ...] = ("results", "data", "contacts", "people", "companies"),
    license_class: str = "paid_api",
) -> ConnectorEnvelope:
    status, payload, text = await _read_json(send, method, url, headers=headers, params=params, json=body)
    if status != 200:
        detail = _safe_reason(text)[:120]
        return _envelope(provider, "error", reason=f"{provider} HTTP {status} {detail}".strip(), http_status=status)
    rows = _items_of(payload, *list_keys)
    accounts, contacts = _people_from_rows(rows, query)
    if not accounts and isinstance(payload, dict):
        name = _blank(payload.get("name") or payload.get("company") or (payload.get("company") if isinstance(payload.get("company"), str) else None))
        domain = _blank(payload.get("domain") or payload.get("website"))
        account = _account(display_name=name or query, website=domain, canonical_domain=domain)
        if account and (payload.get("name") or payload.get("domain")):
            accounts.append(account)
    return _envelope(provider, "ok", accounts=accounts[:count], contacts=contacts[:count], license_class=license_class, http_status=200)


async def _lusha(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    domain = canonical_domain(query)
    company: dict[str, str] = {"clientReferenceId": "q1"}
    if domain:
        company["domain"] = domain
    else:
        company["name"] = query
    return await _keyed_json(
        provider, query, api_key, count, send,
        method="POST",
        url="https://api.lusha.com/v3/companies/search",
        headers={"api_key": api_key or "", "Content-Type": "application/json"},
        body={"companies": [company], "options": {"includePartialProfiles": True}},
        list_keys=("results", "companies", "data"),
    )


async def _rocketreach(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    domain = canonical_domain(query)
    search = {"current_employer": [f'"{query}"']} if not domain else {"keyword": [domain]}
    return await _keyed_json(
        provider, query, api_key, count, send,
        method="POST",
        url="https://api.rocketreach.co/api/v2/person/search",
        headers={"Api-Key": api_key or "", "Content-Type": "application/json"},
        body={"query": search, "page_size": count, "start": 1},
        list_keys=("profiles", "people", "results"),
    )


async def _companies_house(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    import base64
    token = base64.b64encode(f"{api_key}:".encode()).decode()
    status, payload, text = await _read_json(
        send,
        "GET",
        "https://api.company-information.service.gov.uk/search/companies",
        params={"q": query, "items_per_page": count},
        headers={"Authorization": f"Basic {token}"},
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"Companies House HTTP {status} {_safe_reason(text)[:80]}", http_status=status)
    accounts: list[AccountCandidate] = []
    for item in (payload.get("items") or [])[:count]:
        if not isinstance(item, dict):
            continue
        address = item.get("address") or {}
        account = _account(
            display_name=item.get("title"),
            hq_city=_blank(address.get("locality")),
            hq_country=_blank(address.get("country")) or "United Kingdom",
            external_id=_blank(item.get("company_number")),
        )
        if account:
            accounts.append(account)
    return _envelope(provider, "ok", accounts=accounts, license_class="public_api", http_status=200)


async def _opencorporates(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    status, payload, text = await _read_json(
        send,
        "GET",
        "https://api.opencorporates.com/v0.4/companies/search",
        params={"q": query, "per_page": count, "api_token": api_key},
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"OpenCorporates HTTP {status} {_safe_reason(text)[:80]}", http_status=status)
    companies = ((payload.get("results") or {}).get("companies") or [])[:count]
    accounts: list[AccountCandidate] = []
    for wrap in companies:
        company = wrap.get("company") if isinstance(wrap, dict) else None
        if not isinstance(company, dict):
            continue
        account = _account(
            display_name=company.get("name"),
            hq_country=_blank((company.get("jurisdiction_code") or "").split("_")[-1] if company.get("jurisdiction_code") else None),
            external_id=_blank(company.get("company_number")),
            website=company.get("opencorporates_url"),
        )
        if account:
            accounts.append(account)
    return _envelope(provider, "ok", accounts=accounts, license_class="paid_api", http_status=200)


async def _sam(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    status, payload, text = await _read_json(
        send,
        "GET",
        "https://api.sam.gov/opportunities/v2/search",
        params={
            "api_key": api_key,
            "title": query,
            "limit": count,
            "postedFrom": "01/01/2025",
            "postedTo": "12/31/2026",
        },
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"SAM.gov HTTP {status} {_safe_reason(text)[:80]}", http_status=status)
    accounts: list[AccountCandidate] = []
    signals: list[RawSignal] = []
    for notice in _items_of(payload, "opportunitiesData", "opportunities", "results")[:count]:
        title = _blank(notice.get("title"))
        link = _blank(notice.get("uiLink") or notice.get("additionalInfoLink"))
        office = _blank(notice.get("fullParentPathName") or notice.get("organizationName") or title)
        signal = _signal("tender", title or office, link, independent_key=_blank(notice.get("noticeId")) or title)
        if signal:
            signals.append(signal)
        account = _account(display_name=office, external_id=_blank(notice.get("noticeId")))
        if account:
            accounts.append(account)
    return _envelope(provider, "ok", accounts=accounts, signals=signals, license_class="public_api", http_status=200)


async def _builtwith(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    domain = _public_domain(query) or query
    status, payload, text = await _read_json(
        send,
        "GET",
        "https://api.builtwith.com/v21/api.json",
        params={"KEY": api_key, "LOOKUP": domain},
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"BuiltWith HTTP {status} {_safe_reason(text)[:80]}", http_status=status)
    names: list[str] = []
    for result in payload.get("Results") or []:
        for path in (result or {}).get("Result", {}).get("Paths") or []:
            for tech in path.get("Technologies") or []:
                name = _blank(tech.get("Name"))
                if name and name not in names:
                    names.append(name)
                if len(names) >= count:
                    break
    summary = "Technologies: " + ", ".join(names) if names else None
    signal = _signal("tech_added", summary, None, domain=domain, independent_key=f"builtwith:{domain}:{','.join(names[:8])}")
    account = _account(display_name=domain, canonical_domain=_public_domain(query), website=f"https://{domain}" if _public_domain(query) else None)
    return _envelope(provider, "ok", accounts=[account] if account else [], signals=[signal] if signal else [], license_class="paid_api", http_status=200, reason=None if names else "BuiltWith returned no technologies.")


async def _verifier(provider: str, query: str, api_key: str | None, count: int, send, url: str, headers: dict | None = None, params: dict | None = None) -> ConnectorEnvelope:
    del count
    email = _email_in(query)
    if not email:
        return _envelope(provider, "ok", reason="Email verification needs an email address in the query.", license_class="paid_api")
    status, payload, text = await _read_json(send, "GET", url, headers=headers, params=params)
    if status != 200:
        return _envelope(provider, "error", reason=f"{provider} HTTP {status} {_safe_reason(text)[:80]}", http_status=status)
    blob = str(payload).lower()
    valid = any(token in blob for token in ("valid", "deliverable", "\"ok\"")) and not any(token in blob for token in ("invalid", "undeliverable"))
    if not valid:
        return _envelope(provider, "ok", reason="Verifier did not mark the address deliverable. No contact was saved.", license_class="paid_api", http_status=200)
    contact = _contact(email=email, company_domain=email.split("@", 1)[1])
    return _envelope(provider, "ok", contacts=[contact] if contact else [], license_class="paid_api", http_status=200)


async def _hunter_verifier(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    email = _email_in(query) or ""
    return await _verifier(provider, query, api_key, count, send, "https://api.hunter.io/v2/email-verifier", params={"email": email, "api_key": api_key})


async def _zerobounce(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    email = _email_in(query) or ""
    return await _verifier(provider, query, api_key, count, send, "https://api.zerobounce.net/v2/validate", params={"api_key": api_key, "email": email})


async def _neverbounce(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    email = _email_in(query) or ""
    return await _verifier(provider, query, api_key, count, send, "https://api.neverbounce.com/v4/single/check", params={"key": api_key, "email": email})


async def _kickbox(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    email = _email_in(query) or ""
    return await _verifier(provider, query, api_key, count, send, "https://api.kickbox.com/v2/verify", headers={"Authorization": f"Bearer {api_key}"}, params={"email": email})


async def _bouncer(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    email = _email_in(query) or ""
    return await _verifier(provider, query, api_key, count, send, "https://api.usebouncer.com/v1.1/email/verify", headers={"x-api-key": api_key or ""}, params={"email": email})


async def _emailrep(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    email = _email_in(query) or "none@example.com"
    return await _verifier(provider, query, api_key, count, send, f"https://emailrep.io/{quote_plus(email)}", headers={"Key": api_key or ""})


async def _yelp(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    return await _keyed_json(
        provider, query, api_key, count, send,
        method="GET",
        url="https://api.yelp.com/v3/businesses/search",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"term": query, "limit": count},
        list_keys=("businesses",),
    )


async def _foursquare(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    return await _keyed_json(
        provider, query, api_key, count, send,
        method="GET",
        url="https://api.foursquare.com/v3/places/search",
        headers={"Authorization": api_key or "", "Accept": "application/json"},
        params={"query": query, "limit": count},
        list_keys=("results",),
    )


async def _serpapi(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    status, payload, text = await _read_json(
        send,
        "GET",
        "https://serpapi.com/search.json",
        params={"engine": "google", "q": query, "api_key": api_key, "num": count},
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"SerpAPI HTTP {status} {_safe_reason(text)[:80]}", http_status=status)
    accounts: list[AccountCandidate] = []
    signals: list[RawSignal] = []
    for row in (payload.get("organic_results") or [])[:count]:
        if not isinstance(row, dict):
            continue
        title = _blank(row.get("title"))
        link = _blank(row.get("link"))
        account = _account(display_name=title, website=link)
        if account:
            accounts.append(account)
        signal = _signal("search_demand", title, link, independent_key=link or title)
        if signal:
            signals.append(signal)
    return _envelope(provider, "ok", accounts=accounts, signals=signals, license_class="paid_api", http_status=200)


async def _securitytrails(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    del count
    domain = _public_domain(query)
    if not domain:
        return _envelope(provider, "ok", reason="SecurityTrails needs a domain.", license_class="paid_api")
    status, payload, text = await _read_json(
        send,
        "GET",
        f"https://api.securitytrails.com/v1/domain/{quote_plus(domain)}",
        headers={"APIKEY": api_key or ""},
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"SecurityTrails HTTP {status} {_safe_reason(text)[:80]}", http_status=status)
    host = _blank(payload.get("hostname") or domain)
    alexa = payload.get("alexa")
    summary = f"SecurityTrails domain {host}"
    signal = _signal("tech_added", summary, None, independent_key=f"st:{host}", alexa=alexa)
    account = _account(display_name=host, canonical_domain=domain, website=f"https://{domain}")
    return _envelope(provider, "ok", accounts=[account] if account else [], signals=[signal] if signal else [], license_class="paid_api", http_status=200)


async def _hubspot(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    return await _keyed_json(
        provider, query, api_key, count, send,
        method="POST",
        url="https://api.hubapi.com/crm/v3/objects/contacts/search",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        body={
            "query": query,
            "limit": count,
            "properties": ["email", "firstname", "lastname", "jobtitle", "phone", "company", "website"],
        },
        list_keys=("results",),
        license_class="first_party",
    )


async def _pipedrive(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    return await _keyed_json(
        provider, query, api_key, count, send,
        method="GET",
        url="https://api.pipedrive.com/v1/persons/search",
        params={"term": query, "limit": count, "api_token": api_key},
        list_keys=("items", "data"),
        license_class="first_party",
    )


async def _stripe(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    safe = query.replace('"', "")
    return await _keyed_json(
        provider, query, api_key, count, send,
        method="GET",
        url="https://api.stripe.com/v1/customers/search",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"query": f'name~"{safe}" OR email~"{safe}"', "limit": count},
        list_keys=("data",),
        license_class="first_party",
    )


async def _gmail(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    status, payload, text = await _read_json(
        send,
        "GET",
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"q": query, "maxResults": count},
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"Gmail HTTP {status} {_safe_reason(text)[:80]}", http_status=status)
    contacts: list[ContactCandidate] = []
    signals: list[RawSignal] = []
    for item in (payload.get("messages") or [])[:count]:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        m_status, message, _mtext = await _read_json(
            send,
            "GET",
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{item['id']}",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"format": "metadata", "metadataHeaders": ["From", "Subject"]},
        )
        if m_status != 200 or not isinstance(message, dict):
            continue
        headers = {h.get("name", "").lower(): h.get("value") for h in (message.get("payload") or {}).get("headers") or []}
        email = _email_in(headers.get("from"))
        subject = _blank(headers.get("subject"))
        contact = _contact(email=email, full_name=_blank((headers.get("from") or "").split("<")[0]), provider_id=item.get("id"))
        if contact:
            contacts.append(contact)
        signal = _signal("reply", subject or "Mailbox message", None, independent_key=f"gmail:{item.get('id')}")
        if signal:
            signals.append(signal)
    return _envelope(provider, "ok", contacts=contacts, signals=signals, license_class="first_party")


async def _graph_mail(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    safe = query.replace('"', "")
    status, payload, text = await _read_json(
        send,
        "GET",
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"$search": f'"{safe}"', "$top": count},
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"Microsoft Graph HTTP {status} {_safe_reason(text)[:80]}", http_status=status)
    contacts: list[ContactCandidate] = []
    signals: list[RawSignal] = []
    for item in (payload.get("value") or [])[:count]:
        if not isinstance(item, dict):
            continue
        sender = ((item.get("from") or {}).get("emailAddress") or {})
        contact = _contact(full_name=sender.get("name"), email=sender.get("address"), provider_id=item.get("id"))
        if contact:
            contacts.append(contact)
        signal = _signal("reply", _blank(item.get("subject")), item.get("webLink"), independent_key=f"graph:{item.get('id')}")
        if signal:
            signals.append(signal)
    return _envelope(provider, "ok", contacts=contacts, signals=signals, license_class="first_party")


async def _gcal(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    status, payload, text = await _read_json(
        send,
        "GET",
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"q": query, "maxResults": count, "singleEvents": "true", "orderBy": "startTime"},
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"Google Calendar HTTP {status} {_safe_reason(text)[:80]}", http_status=status)
    contacts: list[ContactCandidate] = []
    signals: list[RawSignal] = []
    for event in (payload.get("items") or [])[:count]:
        if not isinstance(event, dict):
            continue
        summary = _blank(event.get("summary"))
        signal = _signal("meeting", summary, event.get("htmlLink"), independent_key=f"gcal:{event.get('id')}")
        if signal:
            signals.append(signal)
        for person in event.get("attendees") or []:
            if not isinstance(person, dict):
                continue
            contact = _contact(email=person.get("email"), full_name=person.get("displayName"), provider_id=event.get("id"))
            if contact:
                contacts.append(contact)
    return _envelope(provider, "ok", contacts=contacts[:count], signals=signals, license_class="first_party")


async def _twitter(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    status, payload, text = await _read_json(
        send,
        "GET",
        "https://api.twitter.com/2/tweets/search/recent",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"query": query, "max_results": max(10, min(count, 10)), "tweet.fields": "text,author_id"},
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"X API HTTP {status} {_safe_reason(text)[:80]}", http_status=status)
    signals: list[RawSignal] = []
    for tweet in (payload.get("data") or [])[:count]:
        if not isinstance(tweet, dict):
            continue
        text_value = _blank(tweet.get("text"))
        link = f"https://x.com/i/web/status/{tweet.get('id')}" if tweet.get("id") else None
        signal = _signal("buying_question", text_value, link, independent_key=f"x:{tweet.get('id')}")
        if signal:
            signals.append(signal)
    return _envelope(provider, "ok", signals=signals, license_class="paid_api", http_status=200)


async def _reddit(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    if not api_key or ":" not in api_key:
        return await _google_news(provider, query, "buying_question", count, send, site="reddit.com")
    client_id, secret = api_key.split(":", 1)
    token_response = await send(
        "POST",
        "https://www.reddit.com/api/v1/access_token",
        headers={"User-Agent": USER_AGENT},
        data={"grant_type": "client_credentials"},
        auth=(client_id, secret),
    )
    token_status = getattr(token_response, "status_code", 0)
    try:
        token = token_response.json().get("access_token")
    except Exception:
        token = None
    if token_status != 200 or not token:
        return _envelope(provider, "error", reason=f"Reddit auth HTTP {token_status}", http_status=token_status)
    status, payload, text = await _read_json(
        send,
        "GET",
        "https://oauth.reddit.com/search",
        headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
        params={"q": query, "limit": count, "sort": "new"},
    )
    if status != 200 or not isinstance(payload, dict):
        return _envelope(provider, "error", reason=f"Reddit HTTP {status} {_safe_reason(text)[:80]}", http_status=status)
    signals: list[RawSignal] = []
    accounts: list[AccountCandidate] = []
    for child in ((payload.get("data") or {}).get("children") or [])[:count]:
        data = child.get("data") if isinstance(child, dict) else None
        if not isinstance(data, dict):
            continue
        title = _blank(data.get("title"))
        link = _blank(data.get("url"))
        signal = _signal("buying_question", title, link, independent_key=f"reddit:{data.get('id')}")
        if signal:
            signals.append(signal)
        account = _account(display_name=title, website=link)
        if account:
            accounts.append(account)
    return _envelope(provider, "ok", accounts=accounts, signals=signals, license_class="public_api")


async def _csv(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    del query, send
    if not api_key or "email" not in api_key.lower() or "," not in api_key:
        return _envelope(provider, "unsupported", reason="Save CSV text on the csv_json_bulk integration, with a header row that includes email. This source does not search the web.")
    reader = csv.DictReader(io.StringIO(api_key))
    contacts: list[ContactCandidate] = []
    accounts: list[AccountCandidate] = []
    for row in reader:
        if len(contacts) >= count:
            break
        lowered = {str(key).strip().lower(): value for key, value in row.items() if key}
        contact = _contact(
            full_name=lowered.get("name") or lowered.get("full_name"),
            email=lowered.get("email"),
            phone=lowered.get("phone"),
            title=lowered.get("title"),
            company_name=lowered.get("company"),
            company_domain=lowered.get("website") or lowered.get("domain"),
        )
        if contact:
            contacts.append(contact)
        account = _account(display_name=lowered.get("company"), website=lowered.get("website") or lowered.get("domain"))
        if account:
            accounts.append(account)
    return _envelope(provider, "ok", accounts=accounts[:count], contacts=contacts, license_class="first_party", reason=None if contacts or accounts else "The CSV had no usable rows.")


async def _apify(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    if not api_key or "|" not in api_key:
        return _envelope(provider, "missing_credentials", reason="Save the Apify credential as token|username/actor-name. No default scraper actor is selected.")
    token, actor = api_key.split("|", 1)
    actor = actor.strip().replace("/", "~")
    if not token.strip() or "~" not in actor:
        return _envelope(provider, "missing_credentials", reason="Save the Apify credential as token|username/actor-name.")
    status, payload, text = await _read_json(
        send,
        "POST",
        f"https://api.apify.com/v2/acts/{quote_plus(actor)}/run-sync-get-dataset-items",
        params={"token": token.strip()},
        json={"query": query, "search": query, "maxItems": count},
        timeout=20.0,
    )
    if status not in {200, 201} or not isinstance(payload, list):
        return _envelope(provider, "error", reason=f"Apify HTTP {status} {_safe_reason(text)[:80]}", http_status=status)
    accounts, contacts = _people_from_rows([row for row in payload if isinstance(row, dict)], query)
    return _envelope(provider, "ok", accounts=accounts[:count], contacts=contacts[:count], license_class="paid_api", http_status=status)


async def _salesforce(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    if not api_key or "|" not in api_key:
        return _envelope(provider, "missing_credentials", reason="Save Salesforce as https://your-instance.salesforce.com|access_token.")
    instance, token = api_key.split("|", 1)
    instance = instance.rstrip("/")
    safe = query.replace("'", "")
    soql = f"SELECT Id, Name, Email, Phone, Title FROM Contact WHERE Name LIKE '%{safe}%' LIMIT {int(count)}"
    return await _keyed_json(
        provider, query, token, count, send,
        method="GET",
        url=f"{instance}/services/data/v59.0/query",
        headers={"Authorization": f"Bearer {token}"},
        params={"q": soql},
        list_keys=("records",),
        license_class="first_party",
    )


async def _snov(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    parts = (api_key or "").split("|")
    if len(parts) != 2:
        return _envelope(provider, "missing_credentials", reason="Save Snov as client_id|client_secret.")
    client_id, secret = parts
    status, payload, text = await _read_json(
        send,
        "POST",
        "https://api.snov.io/v1/oauth/access_token",
        json={"grant_type": "client_credentials", "client_id": client_id, "client_secret": secret},
    )
    if status != 200 or not isinstance(payload, dict) or not payload.get("access_token"):
        return _envelope(provider, "error", reason=f"Snov auth HTTP {status} {_safe_reason(text)[:80]}", http_status=status)
    domain = _public_domain(query) or query
    return await _keyed_json(
        provider, query, payload["access_token"], count, send,
        method="GET",
        url="https://api.snov.io/v1/get-domain-emails-from-url",
        params={"domain": domain, "access_token": payload["access_token"], "limit": count},
        list_keys=("emails", "data"),
    )


async def _bearer_post(provider: str, query: str, api_key: str | None, count: int, send, url: str, body: dict, list_keys: tuple[str, ...] = ("data", "results", "contacts")) -> ConnectorEnvelope:
    return await _keyed_json(
        provider, query, api_key, count, send,
        method="POST",
        url=url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        body=body,
        list_keys=list_keys,
    )


async def _refuse(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    del query, api_key, count, send
    reasons = {
        "peoplefinders": "No consumer people-search API is called. Use apollo, hunter, or people_data_labs for B2B contacts.",
        "direct_api": "Inbound webhooks deliver leads into OctaOS. This source does not search an external directory.",
        "rb2b": "RB2B identifies visitors through its own webhook. There is no search API to call.",
        "clay": "Clay is an orchestration product. Connect the underlying provider key instead of a Clay search.",
        "pitchbook": "PitchBook has no self-serve search API. A public mention search is not a PitchBook record.",
        "hg_insights": "HG Insights requires an enterprise contract and does not publish a simple search endpoint.",
        "mca_roc": "MCA does not publish a stable company-search API.",
    }
    if provider in {"pitchbook", "hg_insights", "mca_roc"}:
        return await _google_news(provider, query, "product_launch", count, send)
    return _envelope(provider, "unsupported", reason=reasons.get(provider, "No authorized search API is available for this source."))


def _spec(source_id: str, level: str, needs_key: bool, paid: bool, capabilities: set[str], run) -> SourceSpec:
    return SourceSpec(source_id, level, needs_key, paid, frozenset(capabilities), run)


def _build_specs() -> dict[str, SourceSpec]:
    account = {"account_discovery"}
    signal = {"intent_signal"}
    both = {"account_discovery", "intent_signal"}
    contact = {"contact_discovery"}
    specs: dict[str, SourceSpec] = {}

    def add(source_id: str, level: str, needs_key: bool, paid: bool, capabilities: set[str], run) -> None:
        specs[source_id] = _spec(source_id, level, needs_key, paid, capabilities, run)

    for source_id in ("greenhouse", "lever", "ashby", "workable"):
        add(source_id, "live", False, False, both, _job_board)
    add("hn_intent", "live", False, False, both, lambda p, q, k, c, s: _hn(p, q, k, c, s, "", "story", "buying_question"))
    add("y_combinator", "live", False, False, both, lambda p, q, k, c, s: _hn(p, q, k, c, s, "YC", "story", "product_launch"))
    add("sec_edgar", "live", False, False, both, _sec)
    add("ted_procurement", "live", False, False, both, _ted)
    add("un_worldbank_tenders", "live", False, False, both, _world_bank)
    add("openstreetmap", "live", False, False, account, _nominatim)
    add("app_store_reviews", "live", False, False, signal, _itunes)
    add("github_ecosystem", "live", False, False, both, _github)
    add("ssl_transparency", "live", False, False, both, _certs)
    add("product_hunt", "live", False, False, both, _product_hunt)
    add("career_pages", "live", False, False, signal, _career_page)
    add("google_search_news", "partial", False, False, signal, _news_runner("search_demand"))
    add("executive_moves", "partial", False, False, both, _news_runner("executive_joined", extra='(appointed OR "named CEO" OR "joins as")'))
    add("event_exhibitors", "partial", False, False, both, _news_runner("product_launch", extra="(exhibitor OR sponsor) (conference OR summit)"))

    news_sources = {
        "indeed": ("indeed.com", "job_opening"),
        "linkedin_jobs": ("linkedin.com/jobs", "job_opening"),
        "linkedin": ("linkedin.com", "job_opening"),
        "naukri": ("naukri.com", "job_opening"),
        "foundit": ("foundit.in", "job_opening"),
        "wellfound": ("wellfound.com", "job_opening"),
        "techcrunch": ("techcrunch.com", "funding_round"),
        "entrackr": ("entrackr.com", "funding_round"),
        "inc42": ("inc42.com", "funding_round"),
        "yourstory": ("yourstory.com", "funding_round"),
        "startup_india": ("startupindia.gov.in", "funding_round"),
        "pr_newswire": ("prnewswire.com", "product_launch"),
        "quora_intent": ("quora.com", "buying_question"),
        "kaggle": ("kaggle.com", "tech_added"),
        "gem_portal": ("gem.gov.in", "tender"),
        "cppp_portal": ("eprocure.gov.in", "tender"),
        "g2": ("g2.com", "competitor_dissatisfaction"),
        "capterra": ("capterra.com", "competitor_dissatisfaction"),
        "glassdoor": ("glassdoor.com", "complaint_spike"),
        "comparably": ("comparably.com", "complaint_spike"),
        "tripadvisor": ("tripadvisor.com", "low_rating"),
        "clutch": ("clutch.co", "product_launch"),
        "goodfirms": ("goodfirms.co", "product_launch"),
        "indiamart": ("indiamart.com", "product_launch"),
        "tradeindia": ("tradeindia.com", "product_launch"),
        "justdial": ("justdial.com", "product_launch"),
        "the_org": ("theorg.com", "executive_joined"),
        "owler": ("owler.com", "product_launch"),
        "instagram": ("instagram.com", "product_launch"),
    }
    for source_id, (site, signal_type) in news_sources.items():
        caps = signal if source_id in {"quora_intent", "kaggle", "g2", "capterra", "glassdoor", "comparably", "tripadvisor"} else both
        add(source_id, "partial", False, False, caps, _news_runner(signal_type, site=site))
    add("trademark_patent", "partial", False, False, both, _news_runner("product_launch", site="uspto.gov"))

    add("reddit_intent", "partial", False, False, both, _reddit)
    add("google_reviews", "live", True, True, signal, _places_like)
    add("google_business_profile", "live", True, True, signal, _places_like)
    add("lusha", "live", True, True, contact | account, _lusha)
    add("rocketreach", "live", True, True, contact, _rocketreach)
    add("companies_house", "live", True, False, both, _companies_house)
    add("opencorporates", "live", True, False, account | {"enrichment"}, _opencorporates)
    add("sam_gov", "live", True, False, both, _sam)
    add("builtwith", "live", True, True, both | {"enrichment"}, _builtwith)
    add("hunter_verifier", "live", True, True, {"verification"}, _hunter_verifier)
    add("zerobounce", "live", True, True, {"verification"}, _zerobounce)
    add("neverbounce", "live", True, True, {"verification"}, _neverbounce)
    add("kickbox", "live", True, True, {"verification"}, _kickbox)
    add("bouncer", "live", True, True, {"verification"}, _bouncer)
    add("emailrep", "live", True, True, {"verification"}, _emailrep)
    add("yelp", "live", True, True, both, _yelp)
    add("foursquare", "live", True, True, account, _foursquare)
    add("serpapi", "live", True, True, signal, _serpapi)
    add("securitytrails", "live", True, True, signal, _securitytrails)
    add("twitter_intent", "live", True, True, both, _twitter)
    add("hubspot", "live", True, False, contact | account | {"first_party"}, _hubspot)
    add("pipedrive", "live", True, False, contact | {"first_party"}, _pipedrive)
    add("stripe", "live", True, False, account | {"first_party"}, _stripe)
    add("gmail", "live", True, False, contact | {"first_party"}, _gmail)
    add("microsoft_graph", "live", True, False, contact | {"first_party"}, _graph_mail)
    add("google_calendar", "live", True, False, contact | {"first_party"}, _gcal)
    add("salesforce", "partial", True, False, contact | account | {"first_party"}, _salesforce)
    add("zendesk", "partial", True, False, contact | {"first_party"}, _zendesk_fixed)
    add("snov", "partial", True, True, contact | {"verification"}, _snov)
    add("csv_json_bulk", "partial", False, False, account | {"first_party"}, _csv)

    async def prospeo(p, q, k, c, s):
        domain = _public_domain(q) or q
        return await _bearer_post(p, q, k, c, s, "https://api.prospeo.io/domain-search", {"company": domain, "limit": c}, ("email_list", "emails", "data"))

    async def findymail(p, q, k, c, s):
        domain = _public_domain(q) or q
        return await _keyed_json(p, q, k, c, s, method="POST", url="https://app.findymail.com/api/search/domain", headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"}, body={"domain": domain}, list_keys=("contacts", "data"))

    async def dropcontact(p, q, k, c, s):
        domain = _public_domain(q)
        return await _keyed_json(p, q, k, c, s, method="POST", url="https://api.dropcontact.io/v1/enrich/all", headers={"X-Access-Token": k or "", "Content-Type": "application/json"}, body={"data": [{"company": q, "website": domain}] if domain else [{"company": q}]}, list_keys=("data",))

    async def fullenrich(p, q, k, c, s):
        domain = _public_domain(q)
        return await _bearer_post(p, q, k, c, s, "https://app.fullenrich.com/api/v1/contact/enrich/bulk", {"datas": [{"domain": domain or q, "company": q}][:c]})

    async def wappalyzer(p, q, k, c, s):
        domain = _public_domain(q) or q
        return await _keyed_json(p, q, k, c, s, method="GET", url="https://api.wappalyzer.com/v2/lookup/", headers={"x-api-key": k or ""}, params={"urls": f"https://{domain}"}, list_keys=("technologies", "results"))

    async def storeleads(p, q, k, c, s):
        domain = _public_domain(q) or q
        return await _keyed_json(p, q, k, c, s, method="GET", url=f"https://storeleads.app/json/api/v1/all/domain/{quote_plus(domain)}", headers={"Authorization": f"Bearer {k}"}, list_keys=("domains", "data"))

    async def similarweb(p, q, k, c, s):
        del c
        domain = _public_domain(q) or q
        return await _keyed_json(p, q, k, 1, s, method="GET", url=f"https://api.similarweb.com/v1/similar-rank/{quote_plus(domain)}/rank", params={"api_key": k}, list_keys=("data",))

    async def semrush(p, q, k, c, s):
        domain = _public_domain(q) or q
        return await _keyed_json(p, q, k, c, s, method="GET", url="https://api.semrush.com/", params={"type": "domain_ranks", "key": k, "export_columns": "Dn,Rk,Or", "domain": domain, "database": "us"}, list_keys=("data",))

    async def ahrefs(p, q, k, c, s):
        domain = _public_domain(q) or q
        return await _keyed_json(p, q, k, c, s, method="GET", url="https://api.ahrefs.com/v3/site-explorer/overview", headers={"Authorization": f"Bearer {k}"}, params={"target": domain, "mode": "domain"}, list_keys=("data",))

    async def majestic(p, q, k, c, s):
        del c
        domain = _public_domain(q) or q
        return await _keyed_json(p, q, k, 1, s, method="GET", url="https://api.majestic.com/api/json", params={"app_api_key": k, "cmd": "GetIndexItemInfo", "items": 1, "item0": domain}, list_keys=("DataTables", "Results"))

    async def trustpilot(p, q, k, c, s):
        del c
        return await _keyed_json(p, q, k, 1, s, method="GET", url="https://api.trustpilot.com/v1/business-units/find", params={"name": _public_domain(q) or q, "apikey": k}, list_keys=("data",))

    async def dealroom(p, q, k, c, s):
        import base64
        token = base64.b64encode(f"{k}:".encode()).decode()
        return await _keyed_json(p, q, k, c, s, method="GET", url="https://api.dealroom.co/api/v1/companies", headers={"Authorization": f"Basic {token}"}, params={"keyword": q, "limit": c}, list_keys=("items", "companies"))

    async def tracxn(p, q, k, c, s):
        return await _bearer_post(p, q, k, c, s, "https://platform.tracxn.com/api/2.2/companies", {"filter": {"companyName": q}, "size": c}, ("result", "companies"))

    async def typeform(p, q, k, c, s):
        return await _keyed_json(p, q, k, c, s, method="GET", url="https://api.typeform.com/forms", headers={"Authorization": f"Bearer {k}"}, params={"search": q, "page_size": c}, list_keys=("items",), license_class="first_party")

    async def tally(p, q, k, c, s):
        return await _keyed_json(p, q, k, c, s, method="GET", url="https://api.tally.so/forms", headers={"Authorization": f"Bearer {k}"}, params={"search": q}, list_keys=("forms", "data"), license_class="first_party")

    async def calendly(p, q, k, c, s):
        del q, c
        return await _keyed_json(p, "me", k, 1, s, method="GET", url="https://api.calendly.com/users/me", headers={"Authorization": f"Bearer {k}"}, list_keys=("resource",), license_class="first_party")

    async def intercom(p, q, k, c, s):
        return await _keyed_json(
            p, q, k, c, s,
            method="POST",
            url="https://api.intercom.io/contacts/search",
            headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json", "Intercom-Version": "2.11"},
            body={"query": {"field": "name", "operator": "~", "value": q}},
            list_keys=("data",),
            license_class="first_party",
        )

    async def meta_leads(p, q, k, c, s):
        del q
        parts = (k or "").split("|")
        if len(parts) != 2:
            return _envelope(p, "missing_credentials", reason="Save Meta lead ads as page_id|page_access_token.")
        page_id, token = parts
        return await _keyed_json(p, page_id, token, c, s, method="GET", url=f"https://graph.facebook.com/v19.0/{page_id}/leadgen_forms", params={"access_token": token, "limit": c}, list_keys=("data",), license_class="first_party")

    async def google_ads(p, q, k, c, s):
        del q, c
        parts = (k or "").split("|")
        if len(parts) != 3:
            return _envelope(p, "missing_credentials", reason="Save Google Ads as developer_token|access_token|customer_id.")
        developer, access, customer = parts
        customer = re.sub(r"\D", "", customer)
        return await _keyed_json(
            p, customer, access, 5, s,
            method="POST",
            url=f"https://googleads.googleapis.com/v18/customers/{customer}/googleAds:search",
            headers={"Authorization": f"Bearer {access}", "developer-token": developer, "Content-Type": "application/json"},
            body={"query": "SELECT customer.id, customer.descriptive_name FROM customer LIMIT 1"},
            list_keys=("results",),
            license_class="first_party",
        )

    for source_id, runner, caps in (
        ("prospeo", prospeo, contact | {"verification"}),
        ("findymail", findymail, contact | {"verification"}),
        ("dropcontact", dropcontact, contact | {"enrichment"}),
        ("fullenrich", fullenrich, contact | {"enrichment", "verification"}),
        ("wappalyzer", wappalyzer, {"enrichment", "intent_signal"}),
        ("storeleads", storeleads, both | {"enrichment"}),
        ("similarweb", similarweb, signal),
        ("semrush", semrush, signal),
        ("ahrefs", ahrefs, signal),
        ("majestic", majestic, signal),
        ("trustpilot", trustpilot, signal),
        ("dealroom", dealroom, both),
        ("tracxn", tracxn, both),
    ):
        add(source_id, "partial", True, True, caps, runner)
    for source_id, runner in (
        ("typeform", typeform),
        ("tally", tally),
        ("calendly", calendly),
        ("intercom", intercom),
        ("meta_lead_ads", meta_leads),
        ("google_ads_leads", google_ads),
    ):
        add(source_id, "partial", True, False, {"first_party", "account_discovery"}, runner)
    for source_id in ("apify_google_places", "apify_instagram", "apify_linkedin", "apify_crawler"):
        add(source_id, "partial", True, True, both, _apify)
    for source_id in ("peoplefinders", "direct_api", "rb2b", "clay", "pitchbook", "hg_insights", "mca_roc"):
        add(source_id, "partial", source_id in {"peoplefinders", "clay", "rb2b"}, False, both, _refuse)
    return specs


async def _zendesk_fixed(provider: str, query: str, api_key: str | None, count: int, send) -> ConnectorEnvelope:
    parts = (api_key or "").split("|")
    if len(parts) != 3:
        return _envelope(provider, "missing_credentials", reason="Save Zendesk as subdomain|email|api_token.")
    subdomain, email, token = [part.strip() for part in parts]
    import base64
    basic = base64.b64encode(f"{email}/token:{token}".encode()).decode()
    return await _keyed_json(
        provider, query, api_key, count, send,
        method="GET",
        url=f"https://{subdomain}.zendesk.com/api/v2/search.json",
        headers={"Authorization": f"Basic {basic}"},
        params={"query": query, "per_page": count},
        list_keys=("results",),
        license_class="first_party",
    )


SPECS: dict[str, SourceSpec] = _build_specs()


def spec_for(source_id: str) -> SourceSpec | None:
    return SPECS.get(source_id)


def catalogue_source_ids() -> list[str]:
    return sorted(SPECS)
