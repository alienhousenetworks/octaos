"""Deterministic commercial-intent labels. Source text is matched, never executed."""
import re

from app.services.sales_os.search_v4.contracts import DiscoveryRecord, IntentCategory

_BUYING = re.compile(
    r"\b(looking for|seeking|need a vendor|request for proposal|\brfp\b|who should we use|recommendations for)\b",
    re.IGNORECASE,
)
_PROCUREMENT = re.compile(
    r"\b(request for proposal|\brfp\b|tender notice|invitation to bid|call for proposals|seeking vendor proposals|expression of interest)\b",
    re.IGNORECASE,
)
_SELLER_CTA = re.compile(
    r"\b(are you looking for|if you are looking for|looking for (?:a |the )?(?:best|top|leading|reliable|affordable)?\s*(?:agency|company|developer|firm|team|service|vendor)\??|contact us for|hire (?:us|our|dedicated)|get a free quote)\b",
    re.IGNORECASE,
)
_SELLER_IDENTITY = re.compile(
    r"\b(we (?:are a|offer|provide|specialize in|build|develop)|our (?:services|solutions|agency|developers|team)|leading (?:web|software|seo|marketing|design) (?:agency|company)|hire web developers|website design services at|web development company|software development company)\b",
    re.IGNORECASE,
)
_EVALUATION = re.compile(
    r"\b(comparing|alternatives to|shortlist|vendor evaluation|evaluating)\b",
    re.IGNORECASE,
)
_PROBLEM = re.compile(
    r"\b(struggling with|bottleneck|pain point|challenge with|problem with)\b",
    re.IGNORECASE,
)
_TRIGGER = re.compile(
    r"\b(hiring|job opening|raised|funding|series [a-d]|new office|expansion|appointed|opens a)\b",
    re.IGNORECASE,
)


def _span(pattern: re.Pattern, text: str) -> str:
    match = pattern.search(text)
    if not match:
        return ""
    start = max(0, match.start() - 40)
    end = min(len(text), match.end() + 80)
    return text[start:end].strip()


def source_text(record: DiscoveryRecord) -> str:
    return " ".join(part for part in (record.title, record.snippet, record.page_excerpt) if part).strip()


def classify_intent(record: DiscoveryRecord, query_tokens: set[str]) -> tuple[IntentCategory, str, bool, list[str]]:
    """Return intent, supporting span, whether the span is explicit, and uncertainty notes."""
    text = source_text(record)
    notes: list[str] = []
    if not text:
        return IntentCategory.INSUFFICIENT_EVIDENCE, "", False, ["No source text was retrieved."]

    procurement = _span(_PROCUREMENT, text)
    if procurement:
        notes.append("Explicit public procurement or RFP language detected.")
        return IntentCategory.DIRECT_BUYING_INTENT, procurement, True, notes

    # Check for seller / agency promotional rhetoric before flagging generic "looking for" phrases
    is_seller = bool(_SELLER_CTA.search(text) or _SELLER_IDENTITY.search(text))

    buying = _span(_BUYING, text)
    if buying:
        if is_seller and not _PROCUREMENT.search(buying):
            notes.append("Source contains vendor/agency promotional rhetoric rather than independent buyer intent.")
            return IntentCategory.GENERAL_INTEREST, buying, False, notes
        notes.append("Budget, authority, and purchase timing are not established by this passage.")
        return IntentCategory.DIRECT_BUYING_INTENT, buying, True, notes
    evaluation = _span(_EVALUATION, text)
    if evaluation:
        notes.append("Vendor evaluation is explicit. A selected vendor is not shown.")
        return IntentCategory.ACTIVE_VENDOR_EVALUATION, evaluation, True, notes
    problem = _span(_PROBLEM, text)
    if problem:
        return IntentCategory.EXPRESSED_BUSINESS_PROBLEM, problem, True, notes
    trigger = _span(_TRIGGER, text)
    if trigger:
        notes.append("A trigger event is not treated as proof that the account is buying.")
        return IntentCategory.RELEVANT_TRIGGER_EVENT, trigger, True, notes

    tokens = set(re.findall(r"[a-z0-9]{3,}", text.lower()))
    if query_tokens and query_tokens & tokens:
        return IntentCategory.GENERAL_INTEREST, text[:180], False, ["Overlap with the campaign query is not a buying signal."]
    return IntentCategory.IRRELEVANT, "", False, ["The source does not match the campaign query or a commercial phrase."]

