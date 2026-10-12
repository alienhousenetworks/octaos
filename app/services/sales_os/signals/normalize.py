"""Normalize a raw provider event into one signal plus an evidence hash."""
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.services.sales_os.signals.taxonomy import family_for, half_life_for


class SignalNormalizationError(ValueError):
    pass


@dataclass
class NormalizedSignal:
    signal_type: str
    family: str
    base_strength: float | None
    source_confidence: float | None
    half_life_days: int
    observed_at: datetime | None
    retrieved_at: datetime
    source_key: str
    source_url: str | None
    summary: str | None
    payload_hash: str
    independent_key: str
    is_inferred: bool
    inference_method: str | None
    inference_model: str | None
    excerpt: str | None
    license_class: str | None


def evidence_hash(
    provider_key: str,
    source_url: str | None,
    excerpt: str | None,
    payload: Any,
) -> str:
    body = {
        "provider_key": provider_key,
        "source_url": source_url,
        "excerpt": excerpt,
        "payload": payload,
    }
    raw = json.dumps(body, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def normalize_signal(
    *,
    signal_type: str,
    source_key: str,
    retrieved_at: datetime,
    payload: Any,
    observed_at: datetime | None = None,
    source_url: str | None = None,
    summary: str | None = None,
    excerpt: str | None = None,
    base_strength: float | None = None,
    source_confidence: float | None = None,
    half_life_days: int | None = None,
    independent_key: str | None = None,
    is_inferred: bool = False,
    inference_method: str | None = None,
    inference_model: str | None = None,
    license_class: str | None = None,
) -> NormalizedSignal:
    family = family_for(signal_type)
    if not family:
        raise SignalNormalizationError(f"Unknown signal type: {signal_type}")
    if not source_key:
        raise SignalNormalizationError("source_key is required")
    if summary is None and excerpt is None and not payload:
        raise SignalNormalizationError("Refusing to normalize an empty claim")
    if is_inferred and not inference_method:
        raise SignalNormalizationError("Inferred signals must record inference_method")
    half_life = half_life_for(signal_type, half_life_days)
    if half_life is None:
        raise SignalNormalizationError("half_life_days is required")
    digest = evidence_hash(source_key, source_url, excerpt or summary, payload)
    return NormalizedSignal(
        signal_type=signal_type,
        family=family,
        base_strength=base_strength,
        source_confidence=source_confidence,
        half_life_days=half_life,
        observed_at=observed_at,
        retrieved_at=retrieved_at,
        source_key=source_key,
        source_url=source_url,
        summary=summary,
        payload_hash=digest,
        independent_key=independent_key or digest,
        is_inferred=is_inferred,
        inference_method=inference_method,
        inference_model=inference_model,
        excerpt=excerpt or summary,
        license_class=license_class,
    )
