"""Versioned qualification. A high label cannot override an exclusion or a missing passage."""
import re

from app.services.sales_os.search_v4.contracts import (
    CampaignIntentSpec,
    DiscoveryRecord,
    IntentCategory,
    LeadEvidence,
    QualificationAssessment,
)

_ACCEPT_INTENTS = {
    IntentCategory.DIRECT_BUYING_INTENT,
    IntentCategory.ACTIVE_VENDOR_EVALUATION,
    IntentCategory.EXPRESSED_BUSINESS_PROBLEM,
}
_RULE_VERSION = "score-rules-v1"


def _tokens(text: str) -> set[str]:
    stop = {"the", "and", "for", "with", "that", "this", "from", "your", "our"}
    return {token for token in re.findall(r"[a-z0-9]{3,}", text.lower()) if token not in stop}


def score_record(
    record: DiscoveryRecord,
    spec: CampaignIntentSpec,
    intent: IntentCategory,
    evidence: LeadEvidence,
    suppressed_domains: set[str] | None = None,
) -> QualificationAssessment:
    blocked = {item.strip().lower() for item in (suppressed_domains or set()) if item and item.strip()}
    hard: list[str] = []
    uncertainty = list(evidence.notes)
    text = " ".join((record.title, record.snippet, record.page_excerpt)).lower()

    for exclusion in spec.exclusions:
        needle = exclusion.strip().lower()
        if needle and needle in text:
            hard.append("scope_exclusion")
            break

    domain = (record.company_domain or "").lower().removeprefix("www.")
    email_domain = ""
    if "@" in (record.contact_email or ""):
        email_domain = record.contact_email.split("@", 1)[1].lower()
    if domain in blocked or email_domain in blocked:
        hard.append("suppression_match")

    if spec.evidence_required and intent in _ACCEPT_INTENTS | {IntentCategory.RELEVANT_TRIGGER_EVENT}:
        if evidence.verification_state != "supported" or not evidence.passage:
            hard.append("missing_mandatory_evidence")
    if evidence.verification_state == "stale":
        hard.append("stale_evidence")
    if intent in {IntentCategory.IRRELEVANT, IntentCategory.INSUFFICIENT_EVIDENCE}:
        hard.append("missing_mandatory_evidence")

    campaign_tokens = _tokens(" ".join([spec.query, *spec.industries, *spec.buyer_roles, *spec.geography]))
    source_tokens = _tokens(text)
    if campaign_tokens:
        icp_fit = min(1.0, len(campaign_tokens & source_tokens) / min(4, len(campaign_tokens)))
    else:
        icp_fit = 0.0

    strength = {
        IntentCategory.DIRECT_BUYING_INTENT: 0.95,
        IntentCategory.ACTIVE_VENDOR_EVALUATION: 0.85,
        IntentCategory.EXPRESSED_BUSINESS_PROBLEM: 0.7,
        IntentCategory.RELEVANT_TRIGGER_EVENT: 0.45,
        IntentCategory.GENERAL_INTEREST: 0.2,
        IntentCategory.IRRELEVANT: 0.0,
        IntentCategory.INSUFFICIENT_EVIDENCE: 0.0,
    }[intent]
    freshness = 1.0 if evidence.freshness_ok else 0.35 if evidence.freshness_ok is None else 0.0
    evidence_quality = 1.0 if evidence.verification_state == "supported" and evidence.passage else 0.25 if record.original_url else 0.0
    contactability = 1.0 if record.contact_email else 0.35 if record.original_url else 0.0
    composite = round((strength * 0.35) + (icp_fit * 0.25) + (freshness * 0.15) + (evidence_quality * 0.15) + (contactability * 0.10), 4)

    if hard:
        decision = "reject"
        rationale = "Rejected by " + ", ".join(hard) + f" under {_RULE_VERSION}."
    elif intent in _ACCEPT_INTENTS and evidence.verification_state == "supported" and icp_fit >= 0.25 and composite >= 0.55:
        decision = "accept"
        rationale = f"Accepted under {_RULE_VERSION}: {intent.value} is supported and the source overlaps the campaign."
    elif intent == IntentCategory.RELEVANT_TRIGGER_EVENT and evidence.verification_state == "supported":
        decision = "nurture"
        rationale = "The source shows a trigger event. It is not treated as an active buyer."
    elif intent == IntentCategory.GENERAL_INTEREST:
        decision = "nurture"
        rationale = "The source matches the topic without a commercial request."
    else:
        decision = "reject"
        rationale = f"Rejected under {_RULE_VERSION}: intent {intent.value} did not meet the evidence and fit bar."

    uncertainty.append("Inferred budget and purchase authority remain unknown.")
    return QualificationAssessment(
        record_id=record.record_id,
        rule_version=_RULE_VERSION,
        intent=intent,
        intent_strength=strength,
        icp_fit=round(icp_fit, 4),
        freshness=freshness,
        evidence_quality=evidence_quality,
        contactability=contactability,
        composite=composite,
        hard_disqualifiers=hard,
        decision=decision,
        rationale=rationale,
        uncertainty=uncertainty,
    )
