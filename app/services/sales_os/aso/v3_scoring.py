"""Interpret model score and pain output without filling gaps."""
V3_WEIGHTS = {
    "budget_score": 0.25,
    "pain_score": 0.25,
    "intent_score": 0.20,
    "industry_score": 0.15,
    "growth_score": 0.10,
    "contact_score": 0.05,
}
_COMPONENT_KEYS = ("budget_score", "pain_score", "intent_score", "industry_score", "growth_score")


def parse_pain_points(raw) -> list[str]:
    if isinstance(raw, dict):
        if raw.get("status") == "insufficient_evidence":
            return []
        raw = raw.get("pain_points") or []
    if not isinstance(raw, list):
        return []
    points = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            points.append(item.strip())
        elif isinstance(item, dict) and str(item.get("text") or "").strip():
            points.append(str(item["text"]).strip())
    return points


def parse_component_scores(raw: dict | None) -> dict[str, float | None]:
    source = raw if isinstance(raw, dict) else {}
    parsed: dict[str, float | None] = {}
    for key in _COMPONENT_KEYS:
        value = source.get(key)
        if value is None or value == "":
            parsed[key] = None
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            parsed[key] = None
            continue
        parsed[key] = max(0.0, min(100.0, number))
    return parsed


def combine_v3_scores(components: dict[str, float | None], contact_score: float | None) -> dict:
    values = dict(components)
    values["contact_score"] = contact_score
    known = {key: value for key, value in values.items() if value is not None and key in V3_WEIGHTS}
    unknown = [key for key in V3_WEIGHTS if values.get(key) is None]
    if not known:
        return {
            "inputs": values,
            "unknown_components": unknown,
            "total": None,
            "category": "insufficient_evidence",
        }
    used = sum(V3_WEIGHTS[key] for key in known)
    total = int(round(sum(known[key] * V3_WEIGHTS[key] for key in known) / used))
    if total >= 85:
        category = "Hot Lead"
    elif total >= 72:
        category = "Warm Lead"
    elif total >= 60:
        category = "Qualified Lead"
    else:
        category = "Ignore"
    return {
        "inputs": values,
        "unknown_components": unknown,
        "total": total,
        "category": category,
    }
