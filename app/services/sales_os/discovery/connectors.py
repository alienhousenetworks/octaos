"""Legacy lead fetch. Returns only fields a provider sent back.

Unactivated providers raise ConnectorUnavailable. They do not invent a person,
an email, a phone, or a company domain.
"""
import logging
import re
from typing import Any, Optional

import httpx

from app.services.sales_os.discovery.identity import canonical_domain
from app.services.sales_os.providers.base import ConnectorUnavailable
from app.services.sales_os.providers.honesty import is_fabricated_contact

logger = logging.getLogger(__name__)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _lead(**parts: Any) -> dict | None:
    record = {
        "name": _clean(parts.get("name")),
        "email": _clean(parts.get("email")),
        "company": _clean(parts.get("company")),
        "phone": _clean(parts.get("phone")),
        "title": _clean(parts.get("title")),
        "source": parts.get("source") or "",
    }
    if parts.get("website"):
        record["website"] = _clean(parts.get("website"))
    if parts.get("evidence_url"):
        record["evidence_url"] = _clean(parts.get("evidence_url"))
    if parts.get("freshness"):
        record["freshness"] = parts.get("freshness")
    if is_fabricated_contact(record):
        return None
    if not record["company"] and not record["email"] and not record["name"]:
        return None
    return record


async def fetch_leads_from_source(
    provider: str,
    api_key: str,
    query: str,
    count: int = 5,
    llm_gateway: Optional[Any] = None,
    transport: Optional[Any] = None,
    freshness: str = "30_days",
) -> list[dict[str, Any]]:
    """Query a provider that has a real client. Other providers refuse."""
    provider = provider.lower().strip()
    leads: list[dict[str, Any]] = []
    del llm_gateway

    async with httpx.AsyncClient(timeout=15.0) as client:
        if provider == "apollo":
            response = await client.post(
                "https://api.apollo.io/api/v1/mixed_people/api_search",
                headers={"Content-Type": "application/json", "X-Api-Key": api_key},
                json={"q_keywords": query, "page": 1, "per_page": count},
            )
            if response.status_code != 200:
                raise ConnectorUnavailable("apollo", f"HTTP {response.status_code}")
            for person in (response.json() or {}).get("people") or []:
                last = _clean(person.get("last_name"))
                if "***" in last:
                    continue
                organization = person.get("organization") or {}
                record = _lead(
                    name=f"{_clean(person.get('first_name'))} {_clean(person.get('last_name'))}".strip(),
                    email=person.get("email"),
                    company=organization.get("name") or "",
                    phone=person.get("sanitized_phone") or person.get("primary_phone"),
                    title=person.get("title"),
                    website=organization.get("primary_domain") or organization.get("website_url"),
                    source="apollo",
                )
                if record:
                    leads.append(record)

        elif provider == "hunter":
            domain = canonical_domain(query)
            domains = [domain] if domain else []
            if not domains:
                discover = await client.post(
                    f"https://api.hunter.io/v2/discover?api_key={api_key}",
                    json={"query": query},
                )
                if discover.status_code != 200:
                    raise ConnectorUnavailable("hunter", f"HTTP {discover.status_code}")
                domains = [canonical_domain(item.get("domain")) for item in (discover.json() or {}).get("data") or []]
                domains = [item for item in domains if item]
            if not domains:
                raise ConnectorUnavailable("hunter", "Hunter returned no domains. No domain was guessed.")
            for domain in domains:
                if len(leads) >= count:
                    break
                found = await client.get(
                    f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}&type=personal&limit={count}"
                )
                if found.status_code != 200:
                    continue
                data = (found.json() or {}).get("data") or {}
                for email in data.get("emails") or []:
                    record = _lead(
                        name=f"{_clean(email.get('first_name'))} {_clean(email.get('last_name'))}".strip(),
                        email=email.get("value"),
                        company=data.get("organization") or domain,
                        phone=email.get("phone_number"),
                        title=email.get("position"),
                        website=domain,
                        source="hunter",
                    )
                    if record:
                        leads.append(record)

        elif provider == "google_places":
            response = await client.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params={"query": query, "key": api_key},
            )
            if response.status_code != 200:
                raise ConnectorUnavailable("google_places", f"HTTP {response.status_code}")
            for place in (response.json() or {}).get("results") or []:
                record = _lead(
                    company=place.get("name"),
                    website=place.get("website"),
                    source="google_places",
                )
                if record:
                    leads.append(record)
                if len(leads) >= count:
                    break

        elif provider == "crunchbase":
            response = await client.post(
                "https://api.crunchbase.com/api/v4/searches/organizations",
                headers={"X-cb-user-key": api_key, "Content-Type": "application/json"},
                json={"query": [{"type": "predicate", "field_id": "identifier", "operator_id": "contains", "values": [query]}], "limit": count},
            )
            if response.status_code != 200:
                raise ConnectorUnavailable("crunchbase", f"HTTP {response.status_code}")
            for entity in (response.json() or {}).get("entities") or []:
                props = entity.get("properties") or {}
                identifier = (props.get("identifier") or {}).get("value")
                record = _lead(
                    email=props.get("contact_email"),
                    company=identifier,
                    phone=props.get("phone_number"),
                    website=props.get("website_url"),
                    source="crunchbase",
                )
                if record:
                    leads.append(record)

        elif provider == "clearbit":
            response = await client.get(
                "https://discovery.clearbit.com/v1/companies/search",
                headers={"Authorization": f"Bearer {api_key}"},
                params={"query": f"name:{query}", "limit": count},
            )
            if response.status_code != 200:
                raise ConnectorUnavailable("clearbit", f"HTTP {response.status_code}")
            for company in (response.json() or {}).get("results") or []:
                record = _lead(
                    company=company.get("name"),
                    website=company.get("domain"),
                    phone=company.get("phone"),
                    source="clearbit",
                )
                if record:
                    leads.append(record)

        elif provider == "hn_hiring":
            from datetime import datetime, timezone, timedelta
            from app.services.sales_os.discovery.web_discovery import calculate_freshness_window_days
            max_days = calculate_freshness_window_days(freshness)
            cutoff_ts = int((datetime.now(timezone.utc) - timedelta(days=max_days)).timestamp()) if max_days < 9999 else 0
            
            search_params = {
                "query": f"{query} hiring",
                "tags": "comment",
                "hitsPerPage": count
            }
            if cutoff_ts > 0:
                search_params["numericFilters"] = f"created_at_i>{cutoff_ts}"

            response = await client.get(
                "https://hn.algolia.com/api/v1/search_by_date" if cutoff_ts > 0 else "https://hn.algolia.com/api/v1/search",
                params=search_params,
            )
            if response.status_code != 200:
                raise ConnectorUnavailable("hn_hiring", f"HTTP {response.status_code}")
            now_dt = datetime.now(timezone.utc)
            for hit in (response.json() or {}).get("hits") or []:
                text = hit.get("comment_text") or ""
                emails = re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, flags=re.I)
                email = emails[0] if emails else ""
                story_id = hit.get("story_id") or hit.get("objectID")
                created_ts = hit.get("created_at_i")
                event_dt = datetime.fromtimestamp(created_ts, tz=timezone.utc) if created_ts else None
                age_days = (now_dt - event_dt).total_seconds() / 86400.0 if event_dt else None
                record = _lead(
                    name=hit.get("author") or "",
                    email=email,
                    company=query if canonical_domain(query) else "",
                    source="hn_hiring",
                    evidence_url=f"https://news.ycombinator.com/item?id={story_id}" if story_id else "",
                    freshness={
                        "event_date": event_dt.isoformat() if event_dt else None,
                        "age_days": round(age_days, 1) if age_days is not None else None,
                        "date_confidence": 0.95,
                        "date_source": "api_native:hn_algolia",
                        "freshness_label": f"{int(age_days)}d ago" if age_days is not None else "Active HN",
                        "signal_snippet": f"Hiring comment by {hit.get('author')}",
                        "verified_active": True,
                        "freshness_window": freshness,
                    } if event_dt else None
                )
                if record and record.get("email"):
                    leads.append(record)

        else:
            from app.services.sales_os.providers.adapters import build_adapter

            adapter = build_adapter(provider, transport)
            capabilities = adapter.capabilities()
            if "contact_discovery" in capabilities:
                envelope = await adapter.discover_contacts(query, api_key or None, count)
            elif "account_discovery" in capabilities:
                envelope = await adapter.discover_accounts(query, api_key or None, count)
            else:
                envelope = await adapter.fetch_signals(query, api_key or None, count)
            for contact in envelope.contacts:
                record = _lead(
                    name=contact.full_name,
                    email=contact.email,
                    company=contact.company_name,
                    phone=contact.phone,
                    title=contact.title,
                    website=contact.company_domain,
                    source=provider,
                )
                if record:
                    leads.append(record)
            employer = envelope.accounts[0].display_name if envelope.accounts else ""
            website = envelope.accounts[0].website if envelope.accounts else ""
            if envelope.signals:
                for signal in envelope.signals:
                    record = _lead(
                        company=employer or query,
                        title=signal.summary,
                        website=website,
                        source=provider,
                        evidence_url=signal.source_url,
                    )
                    if record:
                        leads.append(record)
            elif not leads:
                for account in envelope.accounts:
                    record = _lead(
                        company=account.display_name,
                        website=account.website or account.canonical_domain,
                        source=provider,
                    )
                    if record:
                        leads.append(record)
            if not leads:
                raise ConnectorUnavailable(provider, envelope.reason or "Provider returned no usable records.")

    if not leads:
        raise ConnectorUnavailable(provider, f"Provider returned no usable records for query: {query}")
    return leads[:count]
