"""Follow-up queries only when a verified result adds a distinct signal."""
import re

from app.services.sales_os.search_v4.contracts import CampaignIntentSpec, DiscoveryRecord, QualificationAssessment
from app.services.sales_os.search_v4.planner import _task, expansion_query, semantic_duplicate
from app.services.sales_os.search_v4.registry import web_cost

_HIRING = re.compile(r"\b(hiring|job opening|we're hiring|we are hiring)\b", re.IGNORECASE)
_REQUEST = re.compile(r"\b(looking for|request for proposal|\brfp\b|recommendations for|seeking a vendor)\b", re.IGNORECASE)
_TRIGGER = re.compile(r"\b(raised|funding|series [a-d]|new office|expansion|appointed)\b", re.IGNORECASE)


def novelty_reason(record: DiscoveryRecord) -> str | None:
    text = " ".join((record.title, record.snippet, record.page_excerpt))
    if _REQUEST.search(text):
        return "explicit solution request"
    if _HIRING.search(text):
        return "hiring signal"
    if _TRIGGER.search(text):
        return "trigger event"
    return None


def propose_expansions(
    records: list[tuple[DiscoveryRecord, QualificationAssessment]],
    spec: CampaignIntentSpec,
    existing_queries: list[str],
    provider: str,
    remaining_inr: float,
    limit: int = 2,
) -> list:
    tasks = []
    queries = list(existing_queries)
    cost = web_cost(provider)
    for record, assessment in records:
        if len(tasks) >= limit or record_depth_blocked(assessment):
            break
        if assessment.decision not in {"accept", "nurture"}:
            continue
        reason = novelty_reason(record)
        if reason is None:
            continue
        company = record.company_name or record.company_domain or ""
        if not company:
            continue
        query = expansion_query(company, reason, spec)
        if semantic_duplicate(query, queries):
            continue
        if cost > remaining_inr + 1e-9:
            break
        task = _task(
            spec,
            "web",
            provider,
            "search",
            query,
            f"Follow {reason} from {record.original_url}.",
            cost,
            f"Expansion from {record.record_id}: {reason}. Success means a qualified domain that was not in the parent result.",
            60,
            parent_record_id=record.record_id,
            depth=1,
        )
        if task is None:
            continue
        tasks.append(task)
        queries.append(query)
        remaining_inr -= cost
    return tasks


def record_depth_blocked(assessment: QualificationAssessment) -> bool:
    return "scope_exclusion" in assessment.hard_disqualifiers or "suppression_match" in assessment.hard_disqualifiers
