"""Source spend and downstream outcomes. Views are attribution, not causal claims."""
from collections import defaultdict
from typing import Any


def summarize_roi(costs: list[dict], outcomes: list[dict]) -> dict[str, Any]:
    spend = 0.0
    spend_known = False
    by_provider: dict[str, dict[str, float]] = defaultdict(
        lambda: {"spend": 0.0, "meetings": 0.0, "revenue": 0.0, "outcomes": 0.0, "verified_leads": 0.0}
    )
    for cost in costs:
        amount = cost.get("actual_amount")
        if amount is None:
            amount = cost.get("estimated_amount")
        if amount is None:
            continue
        spend_known = True
        spend += float(amount)
        by_provider[cost.get("provider_key") or "unknown"]["spend"] += float(amount)
    meetings = 0
    verified_leads = 0
    revenue = 0.0
    revenue_known = False
    views = {"first_touch": defaultdict(float), "last_touch": defaultdict(float), "multi_touch": defaultdict(float)}
    for outcome in outcomes:
        provider = outcome.get("provider_key") or "unknown"
        by_provider[provider]["outcomes"] += 1
        kind = outcome.get("outcome_type")
        if kind == "meeting":
            meetings += 1
            by_provider[provider]["meetings"] += 1
        elif kind == "verified_lead":
            verified_leads += 1
            by_provider[provider]["verified_leads"] += 1
        if kind == "revenue" and outcome.get("amount") is not None:
            revenue_known = True
            amount = float(outcome["amount"])
            revenue += amount
            by_provider[provider]["revenue"] += amount
            role = outcome.get("touch_role") or "unknown"
            if role == "first":
                views["first_touch"][provider] += amount
            elif role == "last":
                views["last_touch"][provider] += amount
            else:
                views["multi_touch"][provider] += amount
    return {
        "attribution_is_causal": False,
        "spend": round(spend, 4) if spend_known else None,
        "meetings": meetings,
        "verified_leads": verified_leads,
        "revenue": round(revenue, 4) if revenue_known else None,
        "cost_per_meeting": round(spend / meetings, 4) if spend_known and meetings else None,
        "cost_per_verified_lead": round(spend / verified_leads, 4) if spend_known and verified_leads else None,
        "revenue_per_dollar": round(revenue / spend, 4) if spend_known and spend and revenue_known else None,
        "sample_size": len(outcomes),
        "cost_sample_size": len(costs),
        "by_provider": {key: value for key, value in by_provider.items()},
        "views": {name: dict(bucket) for name, bucket in views.items()},
    }
