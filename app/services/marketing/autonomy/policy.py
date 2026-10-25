"""Deterministic safety policy for autonomous marketing actions.

This module is intentionally provider-independent: an LLM can propose content, but
only this policy decides whether a generated artifact may enter the auto-schedule path.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit


def _finite_number(value: Any) -> Optional[float]:
    """Parse a finite numeric value without accepting NaN or infinity."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _valid_http_url(value: Any) -> bool:
    """Accept only absolute HTTP(S) URLs with a hostname."""
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = urlsplit(value.strip())
        return (
            parsed.scheme.lower() in {"http", "https"}
            and bool(parsed.hostname)
            and not any(ch.isspace() for ch in value.strip())
            and parsed.username is None
            and parsed.password is None
        )
    except (TypeError, ValueError):
        return False


def evaluate_marketing_action(
    *,
    confidence: float,
    confidence_threshold: float = 0.85,
    generation_status: str = "generated",
    context_trigger: str = "general",
    context_score: Optional[float] = None,
    source_url: Optional[str] = None,
    media_required: bool = False,
    media_generated: bool = True,
    require_approval: bool = False,
    publisher_supported: bool = True,
    min_context_score: float = 0.45,
) -> Dict[str, Any]:
    """Return a stable, auditable allow/review decision with human-readable reasons.

    Invalid, missing, or non-finite numeric inputs fail closed. This is a
    conservative scheduling gate, not a legal/compliance certification. Publishing
    must still go through the existing publisher and account-scope checks.
    """
    reasons: List[str] = []
    status = str(generation_status or "unknown").strip().lower()
    trigger = str(context_trigger or "general").strip().lower()

    score_value = _finite_number(confidence)
    if score_value is None or not 0.0 <= score_value <= 1.0:
        score = 0.0
        reasons.append("confidence_unavailable_or_invalid")
    else:
        score = score_value

    threshold_value = _finite_number(confidence_threshold)
    if threshold_value is None or not 0.0 <= threshold_value <= 1.0:
        threshold = 0.85
        reasons.append("confidence_threshold_invalid")
    else:
        threshold = threshold_value

    if status != "generated":
        reasons.append(f"generation_status_{status}_requires_review")
    if score < threshold:
        reasons.append("confidence_below_threshold")

    valid_source = _valid_http_url(source_url)
    if source_url and not valid_source:
        reasons.append("source_url_invalid")
    if trigger == "news" and not valid_source:
        reasons.append("news_context_has_no_valid_source_url")

    if trigger in ("news", "calendar") and context_score is not None:
        context_value = _finite_number(context_score)
        minimum_value = _finite_number(min_context_score)
        if context_value is None or not 0.0 <= context_value <= 1.0:
            reasons.append("context_score_unavailable_or_invalid")
        elif minimum_value is None or not 0.0 <= minimum_value <= 1.0:
            reasons.append("minimum_context_score_invalid")
        elif context_value < minimum_value:
            reasons.append("context_relevance_below_minimum")

    if media_required and not media_generated:
        reasons.append("required_media_not_generated")
    if not publisher_supported:
        reasons.append("publisher_adapter_unavailable")
    if require_approval:
        reasons.append("tenant_policy_requires_human_approval")

    # Preserve reason order while avoiding duplicate explanations.
    reasons = list(dict.fromkeys(reasons))
    approved = not reasons
    return {
        "decision": "allow_schedule" if approved else "needs_review",
        "approved": approved,
        "reasons": reasons,
        "confidence": round(score, 4),
        "confidence_threshold": threshold,
        "generation_status": status,
        "context_trigger": trigger,
        "context_score": context_score,
        "source_url": source_url,
        "publisher_supported": publisher_supported,
    }
