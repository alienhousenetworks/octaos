"""Check that a material claim is present in the stored source passage."""
from datetime import datetime, timedelta, timezone

from app.services.sales_os.search_v4.contracts import DiscoveryRecord, IntentCategory, LeadEvidence
from app.services.sales_os.search_v4.intent import source_text
from app.services.sales_os.discovery.web_discovery import calculate_freshness_window_days

_MATERIAL = {
    IntentCategory.DIRECT_BUYING_INTENT,
    IntentCategory.ACTIVE_VENDOR_EVALUATION,
    IntentCategory.EXPRESSED_BUSINESS_PROBLEM,
    IntentCategory.RELEVANT_TRIGGER_EVENT,
}


def verify_evidence(
    record: DiscoveryRecord,
    intent: IntentCategory,
    span: str,
    explicit: bool,
    freshness: str,
    now: datetime | None = None,
) -> LeadEvidence:
    moment = now or datetime.now(timezone.utc)
    notes: list[str] = []
    passage = span.strip()
    stored = source_text(record)
    if passage and passage not in stored and passage.lower() not in stored.lower():
        notes.append("The proposed span was not found in the stored source text.")
        passage = ""

    state = "unknown"
    if intent in _MATERIAL:
        if passage and explicit:
            state = "supported"
        elif not passage:
            state = "unknown"
            notes.append("A material commercial claim needs a source passage.")
    elif intent == IntentCategory.IRRELEVANT:
        state = "supported" if record.original_url else "unknown"
        notes.append("The source was kept only to show why it was rejected.")
    elif record.original_url and (record.snippet or record.title):
        state = "supported"

    freshness_ok: bool | None = None
    if record.published_at is not None:
        published = record.published_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        max_days = calculate_freshness_window_days(freshness)
        age = moment - published.astimezone(timezone.utc)
        freshness_ok = max_days >= 9999 or age <= timedelta(days=max_days)
        if freshness_ok is False:
            state = "stale"
            notes.append("The publication time is outside the campaign freshness window.")
    else:
        notes.append("Publication time is unknown. Retrieval time is not treated as the event time.")

    if not record.original_url or not record.provider:
        state = "unknown"
        notes.append("Provenance is incomplete.")

    claim = passage or record.title or "Source retrieved without a commercial claim."
    return LeadEvidence(
        record_id=record.record_id,
        claim=claim[:500],
        passage=passage[:500],
        source_url=record.original_url,
        provider=record.provider,
        published_at=record.published_at,
        retrieved_at=record.retrieved_at,
        verification_state=state,
        explicit=explicit and bool(passage),
        freshness_ok=freshness_ok,
        notes=notes,
    )
