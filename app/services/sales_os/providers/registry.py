"""Activation state for every catalogue source. Missing adapters stay inactive."""
from typing import Any

from app.services.sales_os.discovery.source_registry import SourceDefinition, get_all_sources, get_source

# live: sales-os adapter calls the provider and returns only fields it sent back
# partial: a real HTTP client exists, but coverage is incomplete
# legacy: an older lead or CRM path may call it; sales-os will not
# unavailable: registered only
IMPLEMENTATION = {
    "apollo": "live",
    "hunter": "live",
    "google_places": "live",
    "hn_hiring": "live",
    "dns_mx_inspect": "live",
    "crunchbase": "partial",
    "clearbit": "partial",
    "zoominfo": "partial",
    "cognism": "partial",
    "people_data_labs": "partial",
    "csv_json_bulk": "legacy",
    "direct_api": "legacy",
    "hubspot": "legacy",
    "salesforce": "legacy",
    "zendesk": "legacy",
    "gmail": "legacy",
    "google_calendar": "legacy",
    "apify_google_places": "legacy",
    "apify_instagram": "legacy",
    "apify_linkedin": "legacy",
    "apify_crawler": "legacy",
}

PAID_PROVIDERS = {
    "apollo", "hunter", "google_places", "zoominfo", "cognism", "people_data_labs", "clearbit",
    "crunchbase", "lusha", "rocketreach", "clay", "builtwith", "wappalyzer",
    "storeleads", "zerobounce", "bouncer", "neverbounce", "kickbox", "emailrep",
    "hunter_verifier", "similarweb", "semrush", "ahrefs", "majestic", "serpapi",
    "snov", "prospeo", "findymail", "dropcontact", "fullenrich", "dealroom", "tracxn",
    "yelp", "foursquare", "trustpilot", "securitytrails", "twitter_intent",
    "google_reviews", "google_business_profile",
    "apify_google_places", "apify_instagram", "apify_linkedin", "apify_crawler",
}

# Estimated USD per call. None means the price is unknown and must not be treated as free.
ESTIMATED_COST = {
    "apollo": 0.10,
    "hunter": 0.05,
    "zoominfo": 0.50,
    "cognism": 0.40,
    "people_data_labs": 0.15,
    "clearbit": 0.10,
    "crunchbase": 0.20,
    "google_places": 0.01,
    "hn_hiring": 0.0,
    "dns_mx_inspect": 0.0,
}

SALES_OS_CALLABLE = {
    key for key, status in IMPLEMENTATION.items() if status in {"live", "partial"}
}


def _catalogue_spec(source_id: str):
    from app.services.sales_os.providers.catalogue_fetch import spec_for
    return spec_for(source_id)


def implementation_status(source_id: str) -> str:
    spec = _catalogue_spec(source_id)
    if spec is not None:
        return spec.level
    return IMPLEMENTATION.get(source_id, "unavailable")


def source_needs_key(source: SourceDefinition) -> bool:
    spec = _catalogue_spec(source.id)
    if spec is not None:
        return spec.needs_key
    return source.requires_key


def cost_for(source_id: str) -> float | None:
    if source_id in ESTIMATED_COST:
        return ESTIMATED_COST[source_id]
    spec = _catalogue_spec(source_id)
    if spec is not None and not spec.paid:
        return 0.0
    return None


def activation_for(source: SourceDefinition, has_credentials: bool) -> dict[str, Any]:
    status = implementation_status(source.id)
    needs_key = source_needs_key(source)
    if status == "unavailable":
        return {
            "activation_status": "not_activated",
            "reason": "No adapter is activated. Missing fields stay unknown.",
        }
    if status == "legacy":
        if needs_key and not has_credentials:
            return {
                "activation_status": "missing_credentials",
                "reason": "Legacy integration only. Credentials are not configured, and sales-os will not call it.",
            }
        return {
            "activation_status": "legacy_only",
            "reason": "Available on the legacy lead, mail, calendar, or CRM path. Sales-os does not call it.",
        }
    if needs_key and not has_credentials:
        return {
            "activation_status": "missing_credentials",
            "reason": "Adapter is implemented. Credentials are not configured.",
        }
    return {"activation_status": "active", "reason": None}


def describe_source(source_id: str, has_credentials: bool = False) -> dict[str, Any] | None:
    source = get_source(source_id)
    if source is None:
        return None
    activation = activation_for(source, has_credentials)
    return {
        "id": source.id,
        "name": source.name,
        "category": source.category,
        "capabilities": [item.value for item in source.capabilities],
        "implementation": implementation_status(source.id),
        "activation_status": activation["activation_status"],
        "reason": activation["reason"],
        "requires_key": source_needs_key(source),
        "has_credentials": has_credentials,
        "paid": source.id in PAID_PROVIDERS,
        "estimated_cost_usd": cost_for(source.id),
        "sales_os_callable": implementation_status(source.id) in {"live", "partial"} and activation["activation_status"] == "active",
        "default_confidence": source.default_confidence,
        "half_life_days": source.half_life_days,
    }


def describe_all(credential_providers: set[str] | None = None) -> list[dict[str, Any]]:
    owned = credential_providers or set()
    rows = []
    for source in get_all_sources().values():
        described = describe_source(source.id, source.id in owned)
        if described:
            rows.append(described)
    return sorted(rows, key=lambda row: row["id"])
