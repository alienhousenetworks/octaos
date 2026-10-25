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
    def unique(values: list[str]) -> list[str]:
        result = []
        for value in values:
            cleaned = " ".join(str(value or "").split())
            if cleaned and cleaned.casefold() not in {item.casefold() for item in result}:
                result.append(cleaned)
        return result

    industries = unique(spec.industries) or [spec.query]
    geographies = unique(spec.geography) or [""]
    roles = unique(spec.buyer_roles) or [""]
    # Guarantee axis coverage first, then add distinct combinations. A bounded
    # plan keeps broad campaigns useful without creating an unbounded search bill.
    coverage: list[tuple[str, str, str]] = []

    def add_coverage(industry: str, geography: str, role: str) -> None:
        item = (industry, geography, role)
        if item not in coverage and len(coverage) < 12:
            coverage.append(item)

    for industry in industries:
        add_coverage(industry, geographies[0], roles[0])
    for geography in geographies:
        add_coverage(industries[0], geography, roles[0])
    for role in roles:
        add_coverage(industries[0], geographies[0], role)
    for industry in industries:
        for geography in geographies:
            for role in roles:
                add_coverage(industry, geography, role)

    proposals = [
        _task(
            spec, "web", provider, "search",
            " ".join(part for part in (spec.query, geographies[0], roles[0], "looking for") if part),
            "Baseline explicit-buying-intent query for compatibility and campaign-level discovery.",
            cost, why, 5,
        )
    ]
    for index, (industry, geography, role) in enumerate(coverage):
        subject_parts = [industry, geography, role, spec.query]
        query = " ".join(part for part in subject_parts if part)
        query += " companies with relevant business needs vendors RFP"
        proposals.append(
            _task(
                spec, "web", provider, "search", query,
                "Find distinct companies across the campaign's industry, geography, and buyer-role coverage.",
                cost, why, 10 + index,
            )
        )

    # Trigger and hiring research is distributed across industries/geographies,
    # rather than silently searching only the first configured value.
    for index, (industry, geography, role) in enumerate(coverage[:6]):
        subject = " ".join(part for part in (industry, geography, spec.query) if part)
        proposals.append(
            _task(
                spec, "news", "google_news", "rss_search",
                " ".join(part for part in (subject, "funding expansion new leadership procurement") if part),
                "Recent trigger events that may change the buying situation.",
                0.0,
                "Google News RSS is a free public headline source and does not replace the lead connectors.",
                30 + index,
            )
        )
        proposals.append(
            _task(
                spec, "jobs", "hn_algolia", "hiring_search",
                " ".join(part for part in (industry, geography, "hiring", role, spec.query) if part),
                "Hiring language can reveal a team taking on the problem the offer addresses.",
                0.0,
                "Hacker News search is a free public hiring signal and does not invent contacts.",
                40 + index,
            )
        )

    proposals.extend([
        _task(
            spec, "social_reddit", "reddit", "official_search",
            " ".join(part for part in (spec.query, "recommendation vendor problem") if part),
            "Public posts may contain a request for recommendations.",
            0.0,
            "Reddit runs only with an authorized client credential. Otherwise the task is marked unavailable.",
            60,
        ),
        _task(
            spec, "social_x", "x", "recent_search",
            " ".join(part for part in (spec.query, "looking for vendor", roles[0]) if part),
            "Public posts may contain a timely commercial request.",
            0.0,
            "X runs only with an authorized search credential. Otherwise the task is marked unavailable.",
            61,
        ),
    ])
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
