"""Deterministic safety policy for autonomous marketing actions.

This module is intentionally provider-independent: an LLM can propose content, but
only this policy decides whether a generated artifact may enter the auto-schedule path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


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
    min_context_score: float = 0.45,
) -> Dict[str, Any]:
    """Return a stable, auditable allow/review decision with human-readable reasons.

    This is a conservative scheduling gate, not a legal/compliance certification.
    Publishing itself must still go through the existing publisher and account scopes.
    """
    reasons: List[str] = []
    status = (generation_status or "unknown").strip().lower()
    trigger = (context_trigger or "general").strip().lower()

    try:
        score = float(confidence)
    except (TypeError, ValueError):
        score = 0.0
    try:
        threshold = float(confidence_threshold)
    except (TypeError, ValueError):
        threshold = 0.85
    threshold = min(1.0, max(0.0, threshold))

    if status != "generated":
        reasons.append(f"generation_status_{status}_requires_review")
    if score < threshold:
        reasons.append("confidence_below_threshold")
    if trigger == "news" and not source_url:
        reasons.append("news_context_has_no_source_url")
    if trigger in ("news", "calendar") and context_score is not None:
        try:
            if float(context_score) < min_context_score:
                reasons.append("context_relevance_below_minimum")
        except (TypeError, ValueError):
            reasons.append("context_score_unavailable")
    if media_required and not media_generated:
        reasons.append("required_media_not_generated")
    if require_approval:
        reasons.append("tenant_policy_requires_human_approval")

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
    }
