"""Deterministic signal decay. Missing inputs stay unknown."""
from datetime import datetime, timezone


def effective_strength(
    base_strength: float | None,
    source_confidence: float | None,
    age_days: float | None,
    half_life_days: float | None,
) -> float | None:
    """base_strength * source_confidence * 0.5 ** (age_days / half_life_days)."""
    if base_strength is None or source_confidence is None or age_days is None or half_life_days is None:
        return None
    if half_life_days <= 0:
        return None
    if age_days < 0:
        age_days = 0.0
    return float(base_strength) * float(source_confidence) * (0.5 ** (float(age_days) / float(half_life_days)))


def age_in_days(observed_at: datetime | None, now: datetime | None = None) -> float | None:
    if observed_at is None:
        return None
    current = now or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return max(0.0, (current - observed_at).total_seconds() / 86400.0)
