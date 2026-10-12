"""Versioned opportunity score. Unknown components are excluded, not treated as zero."""
import hashlib
import json
from typing import Any

SCORE_VERSION = "sales-os-score-v1"

DEFAULT_WEIGHTS = {
    "icp": 0.20,
    "intent": 0.25,
    "timing": 0.15,
    "problem_fit": 0.15,
    "account_value": 0.10,
    "data_confidence": 0.05,
    "contactability": 0.05,
    "engagement": 0.05,
}

_CONFIDENCE_CAPS = {
    "single_source": 70.0,
    "stale": 60.0,
    "inferred": 50.0,
    "contradictory": 40.0,
}


def config_hash(weights: dict[str, float] | None = None, version: str = SCORE_VERSION) -> str:
    payload = {"version": version, "weights": weights or DEFAULT_WEIGHTS}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def apply_confidence_caps(score: float, flags: dict[str, bool]) -> tuple[float, list[str]]:
    cap = 100.0
    reasons: list[str] = []
    for flag, limit in _CONFIDENCE_CAPS.items():
        if flags.get(flag):
            cap = min(cap, limit)
            reasons.append(flag)
    return min(score, cap), reasons


def score_opportunity(
    components: dict[str, float | None],
    *,
    weights: dict[str, float] | None = None,
    flags: dict[str, bool] | None = None,
    convergence_bonus: float = 0.0,
) -> dict[str, Any]:
    active_weights = dict(DEFAULT_WEIGHTS if weights is None else weights)
    weight_total = sum(active_weights.values())
    if abs(weight_total - 1.0) > 0.001:
        raise ValueError("Score weights must sum to 1")
    known = {key: value for key, value in components.items() if value is not None and key in active_weights}
    unknown = [key for key in active_weights if components.get(key) is None]
    digest = config_hash(active_weights)
    if not known:
        return {
            "score": None,
            "components": components,
            "unknown_components": unknown,
            "score_version": SCORE_VERSION,
            "config_hash": digest,
            "cap_reasons": [],
            "convergence_bonus": 0.0,
            "explanation": "No scored components had evidence.",
        }
    used_weight = sum(active_weights[key] for key in known)
    raw = sum(float(known[key]) * active_weights[key] for key in known) / used_weight
    raw = min(100.0, raw + max(0.0, convergence_bonus))
    capped, reasons = apply_confidence_caps(raw, flags or {})
    score = round(capped, 2)
    return {
        "score": score,
        "components": {key: (None if components.get(key) is None else round(float(components[key]), 2)) for key in active_weights},
        "unknown_components": unknown,
        "weights_used": {key: active_weights[key] for key in known},
        "score_version": SCORE_VERSION,
        "config_hash": digest,
        "cap_reasons": reasons,
        "convergence_bonus": convergence_bonus,
        "explanation": (
            f"Score {score} from {len(known)} evidenced components"
            + (f"; unknown: {', '.join(unknown)}" if unknown else "")
            + (f"; caps: {', '.join(reasons)}" if reasons else "")
            + "."
        ),
    }
