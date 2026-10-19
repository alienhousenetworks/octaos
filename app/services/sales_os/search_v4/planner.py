"""Deterministic search plans. This module does not call providers."""
import hashlib
import re

from app.services.sales_os.search_v4.contracts import CampaignIntentSpec, SearchTask
from app.services.sales_os.search_v4.prompts import PROMPT_VERSION
from app.services.sales_os.search_v4.registry import ProviderHealth, ProviderStats, choose_web_provider, web_cost

_STOP = {"the", "and", "for", "with", "that", "this", "from"}


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]{3,}", text.lower()) if token not in _STOP}


def semantic_duplicate(query: str, prior: list[str], threshold: float = 0.8) -> bool:
    current = _tokens(query)
    if not current:
        return False
    for item in prior:
        previous = _tokens(item)
        if not previous:
            continue
        overlap = len(current & previous) / len(current | previous)
        if overlap >= threshold:
            return True
    return False


def idempotency_key(tenant_id: str, provider: str, operation: str, query: str, freshness: str) -> str:
    raw = "|".join([tenant_id, provider, operation, " ".join(query.lower().split()), freshness])
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _task(
    spec: CampaignIntentSpec,
    method: str,
    provider: str,
    operation: str,
    query: str,
    hypothesis: str,
    cost: float,
    reason: str,
    priority: int,
    parent_record_id: str | None = None,
    depth: int = 0,
) -> SearchTask | None:
    cleaned = " ".join(query.split())
    if not cleaned:
        return None
    return SearchTask(
        correlation_id=spec.correlation_id,
        campaign_id=spec.campaign_id,
        tenant_id=spec.tenant_id,
        method=method,
        provider=provider,
        operation=operation,
        query=cleaned[:300],
        intent_hypothesis=hypothesis,
        freshness_window=spec.freshness,
        exclusions=list(spec.exclusions),
        estimated_cost_inr=cost,
        stop_condition="Stop after one provider page when the result set is empty or the budget is exhausted.",
        priority=priority,
        idempotency_key=idempotency_key(spec.tenant_id, provider, operation, cleaned, spec.freshness),
        selection_reason=reason,
        parent_record_id=parent_record_id,
        depth=depth,
        prompt_version=PROMPT_VERSION,
    )


def plan_tasks(
    spec: CampaignIntentSpec,
    credentials: dict[str, str],
    history: list[str],
    stats: ProviderStats,
    health: ProviderHealth,
    remaining_inr: float,
) -> tuple[list[SearchTask], list[str]]:
    """Return accepted tasks and human-readable reasons for tasks that were not planned."""
    provider, why, cost = choose_web_provider(credentials, stats, health)
    if cost > remaining_inr + 1e-9:
        provider, why, cost = (
            "duckduckgo",
            "The paid web estimate exceeds the remaining budget. Using the existing DuckDuckGo path.",
            0.0,
        )
    geo = spec.geography[0] if spec.geography else ""
    role = spec.buyer_roles[0] if spec.buyer_roles else ""
    subject = " ".join(part for part in (spec.query, geo) if part).strip()
    proposals = [
        _task(
            spec, "web", provider, "search",
            " ".join(part for part in (subject, role, "looking for") if part),
            "Companies publishing an explicit request that matches the campaign.",
            cost,
            why,
            10,
        ),
        _task(
            spec, "news", "google_news", "rss_search",
            " ".join(part for part in (subject, "funding expansion") if part),
            "Recent trigger events that may change the buying situation.",
            0.0,
            "Google News RSS is a free public headline source and does not replace the lead connectors.",
            20,
        ),
        _task(
            spec, "jobs", "hn_algolia", "hiring_search",
            " ".join(part for part in (spec.query, "hiring", role) if part),
            "Hiring language can reveal a team taking on the problem the offer addresses.",
            0.0,
            "Hacker News search is a free public hiring signal and does not invent contacts.",
            30,
        ),
        _task(
            spec, "social_reddit", "reddit", "official_search",
            " ".join(part for part in (spec.query, "recommendation") if part),
            "Public posts may contain a request for recommendations.",
            0.0,
            "Reddit runs only with an authorized client credential. Otherwise the task is marked unavailable.",
            40,
        ),
        _task(
            spec, "social_x", "x", "recent_search",
            " ".join(part for part in (spec.query, role) if part),
            "Public posts may contain a timely commercial request.",
            0.0,
            "X runs only with an authorized search credential. Otherwise the task is marked unavailable.",
            50,
        ),
    ]
    for url in spec.seed_urls[:2]:
        proposals.append(
            _task(
                spec, "company", "company_page", "fetch",
                url,
                "A known company page may contain an on-site commercial signal.",
                0.0,
                "Company fetch runs only for a URL the campaign already supplied.",
                15,
            )
        )

    accepted: list[SearchTask] = []
    notes: list[str] = []
    exact_seen = {" ".join(item.lower().split()) for item in history}
    seen_by_method: dict[str, list[str]] = {"web": list(history)}
    for task in proposals:
        if task is None:
            continue
        if task.method not in {"web", "news", "jobs", "company", "social_reddit", "social_x"}:
            notes.append(f"Rejected {task.method}: unauthorized method.")
            continue
        normalized = " ".join(task.query.lower().split())
        if normalized in exact_seen or semantic_duplicate(task.query, seen_by_method.get(task.method, [])):
            notes.append(f"Rejected duplicate query for {task.method}.")
            continue
        if task.estimated_cost_inr > remaining_inr + 1e-9:
            notes.append(f"Rejected {task.provider}: estimate {task.estimated_cost_inr:.2f} exceeds remaining INR {remaining_inr:.2f}.")
            continue
        accepted.append(task)
        exact_seen.add(normalized)
        seen_by_method.setdefault(task.method, []).append(task.query)
        remaining_inr -= task.estimated_cost_inr
    return accepted, notes


def expansion_query(company: str, reason: str, spec: CampaignIntentSpec) -> str:
    if reason == "hiring signal":
        return f"{company} hiring {spec.buyer_roles[0] if spec.buyer_roles else spec.query}".strip()
    if reason == "explicit solution request":
        return f"{company} {spec.query} vendor".strip()
    if reason == "trigger event":
        return f"{company} {spec.query} announcement".strip()
    return f"{company} {spec.query}".strip()


def web_provider_cost(provider: str) -> float:
    return web_cost(provider)
