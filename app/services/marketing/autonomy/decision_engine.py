"""Deterministic decision helpers for evidence-aware marketing autonomy.

These helpers deliberately do not call an LLM. They make scheduling and context
selection predictable, inspectable, and safe to unit test.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from math import exp
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if result == result and abs(result) != float("inf") else default


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def score_context_signal(
    signal: Dict[str, Any],
    *,
    kind: str,
    now: Optional[datetime] = None,
    industry: str = "",
    company_name: str = "",
) -> float:
    """Rank only supplied context; missing evidence never receives an invented score.

    Scores are a deterministic prioritization heuristic, not a claim that a trend
    is viral. Callers should retain the component scores and source evidence.
    """
    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    explicit_relevance = _number(signal.get("relevance_score", signal.get("brand_fit_score")))
    relevance = max(0.0, min(1.0, explicit_relevance / 100.0 if explicit_relevance > 1 else explicit_relevance))

    confidence_value = signal.get("confidence", signal.get("confidence_score"))
    confidence = _number(confidence_value, 0.5)
    confidence = max(0.0, min(1.0, confidence / 100.0 if confidence > 1 else confidence))

    risk_value = signal.get("risk_score", signal.get("brand_safety_risk"))
    risk = _number(risk_value, 0.0)
    risk = max(0.0, min(1.0, risk / 100.0 if risk > 1 else risk))

    observed = _parse_datetime(
        signal.get("observed_at") or signal.get("published_at") or signal.get("created_at") or signal.get("timestamp")
    )
    if observed:
        age_hours = max(0.0, (now_utc - observed).total_seconds() / 3600.0)
        recency = exp(-age_hours / (72.0 if kind == "news" else 24.0))
        if observed > now_utc:
            recency = 0.8
    elif kind == "calendar":
        days = _number(signal.get("days_away", signal.get("days_until", 30)), 30.0)
        recency = exp(-abs(days) / 30.0)
    else:
        # An undated item is not treated as fresh.
        recency = 0.25

    velocity = _number(signal.get("velocity_score", signal.get("trend_velocity", 0.0)))
    velocity = max(0.0, min(1.0, velocity / 100.0 if velocity > 1 else velocity))
    persistence = _number(signal.get("persistence_score", 0.5), 0.5)
    persistence = max(0.0, min(1.0, persistence / 100.0 if persistence > 1 else persistence))

    # Exact scoring weights are configuration-like defaults and can be calibrated
    # from measured outcomes later. Popularity alone is intentionally insufficient.
    score = (0.34 * relevance) + (0.24 * recency) + (0.18 * confidence)
    score += (0.12 * velocity) + (0.12 * persistence) - (0.30 * risk)

    text = " ".join(str(signal.get(key, "")) for key in ("topic", "name", "signal", "hook", "title")).lower()
    brand_terms = [term.lower() for term in (industry, company_name) if term and len(term.strip()) > 2]
    if brand_terms and any(term in text for term in brand_terms):
        score += 0.04
    return round(max(0.0, min(1.0, score)), 6)


def rank_context_signals(
    calendar_events: Iterable[Dict[str, Any]],
    news_signals: Iterable[Dict[str, Any]],
    *,
    now: Optional[datetime] = None,
    industry: str = "",
    company_name: str = "",
) -> List[Dict[str, Any]]:
    """Return normalized calendar/news candidates in descending evidence-aware order."""
    ranked: List[Dict[str, Any]] = []
    for kind, values in (("calendar", calendar_events), ("news", news_signals)):
        for item in values or []:
            if not isinstance(item, dict):
                continue
            title = item.get("name") if kind == "calendar" else item.get("topic")
            if not title:
                continue
            evidence_url = item.get("url") or item.get("source_url") or item.get("canonical_url")
            ranked.append({
                "kind": kind,
                "name": str(title),
                "hook": str(item.get("hook") or item.get("signal") or ""),
                "score": score_context_signal(
                    item, kind=kind, now=now, industry=industry, company_name=company_name
                ),
                "source_url": evidence_url,
                "observed_at": item.get("observed_at") or item.get("published_at") or item.get("created_at"),
                "evidence_status": "source_linked" if evidence_url else "source_unlinked",
                "raw": item,
            })
    return sorted(ranked, key=lambda item: (item["score"], item["kind"] == "news"), reverse=True)


def compute_schedule_time(
    platform: str,
    *,
    offset_days: int = 0,
    timezone_name: str = "UTC",
    now: Optional[datetime] = None,
    preferred_hours: Optional[Dict[str, int]] = None,
) -> datetime:
    """Compute a timezone-aware local posting slot and return UTC for persistence.

    Hours are fallbacks only. If the tenant supplies measured best-time hours,
    pass them via preferred_hours; do not present these defaults as measured data.
    """
    try:
        zone = ZoneInfo(timezone_name or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo("UTC")

    now_utc = now or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    local_now = now_utc.astimezone(zone)
    fallback_hours = {
        "linkedin": 9, "instagram": 18, "facebook": 14,
        "twitter": 11, "x": 11, "youtube": 15, "tiktok": 19,
    }
    hours = preferred_hours or {}
    target_hour = int(hours.get(platform.lower(), fallback_hours.get(platform.lower(), 12)))
    target_hour = max(0, min(23, target_hour))
    candidate_date: date = (local_now + timedelta(days=max(0, offset_days))).date()
    candidate = datetime.combine(candidate_date, time(hour=target_hour), tzinfo=zone)
    if candidate <= local_now:
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc)
