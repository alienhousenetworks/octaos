"""Account qualification gate and contact-provider routing."""
from typing import Any


def icp_gate(company: dict, profile: dict | None) -> dict[str, Any]:
    """Reject only on an evidenced mismatch. Unknown firmographics do not pass the paid gate."""
    profile = profile or {}
    comparisons: list[tuple[str, bool]] = []
    industry = (company.get("industry") or "").strip().lower()
    industries = [item.strip().lower() for item in profile.get("industries") or [] if item]
    if industry and industries:
        comparisons.append(("industry", any(industry in item or item in industry for item in industries)))
    country = (company.get("hq_country") or "").strip().lower()
    countries = [item.strip().lower() for item in profile.get("countries") or [] if item]
    if country and countries:
        comparisons.append(("country", country in countries))
    employees = company.get("employee_count")
    minimum = profile.get("employee_min")
    maximum = profile.get("employee_max")
    if employees is not None and (minimum is not None or maximum is not None):
        fits = True
        if minimum is not None and employees < minimum:
            fits = False
        if maximum is not None and employees > maximum:
            fits = False
        comparisons.append(("employees", fits))
    if not comparisons:
        return {"status": "unknown", "qualified": False, "reason": "insufficient_firmographics", "checks": []}
    failed = [name for name, ok in comparisons if not ok]
    if failed:
        return {"status": "rejected", "qualified": False, "reason": "out_of_profile", "checks": comparisons}
    score = round(100.0 * sum(1 for _, ok in comparisons if ok) / len(comparisons), 2)
    return {"status": "qualified", "qualified": True, "reason": "profile_match", "icp_score": score, "checks": comparisons}


class WaterfallStep:
    def __init__(self, provider_key: str, action: str, reason: str, estimated_cost: float | None = None):
        self.provider_key = provider_key
        self.action = action
        self.reason = reason
        self.estimated_cost = estimated_cost

    def as_dict(self) -> dict:
        return {
            "provider_key": self.provider_key,
            "action": self.action,
            "reason": self.reason,
            "estimated_cost": self.estimated_cost,
        }


def plan_contact_waterfall(
    *,
    qualified: bool,
    providers: list[str],
    costs: dict[str, float],
    budget: float | None,
    already_verified: bool = False,
) -> list[dict]:
    """Paid calls stop when the account is unqualified, verified, or over budget."""
    steps: list[WaterfallStep] = []
    spent = 0.0
    budget_known = budget is not None
    for provider in providers:
        estimate = costs.get(provider)
        if not qualified:
            steps.append(WaterfallStep(provider, "skip", "account_not_qualified", estimate))
            continue
        if already_verified:
            steps.append(WaterfallStep(provider, "skip", "sufficient_verified_data", estimate))
            continue
        if not budget_known:
            steps.append(WaterfallStep(provider, "skip", "budget_decision_required", estimate))
            continue
        price = 0.0 if estimate is None else estimate
        if spent + price > budget:
            steps.append(WaterfallStep(provider, "skip", "budget_exceeded", estimate))
            continue
        steps.append(WaterfallStep(provider, "call", "within_budget", estimate))
        spent += price
    return [step.as_dict() for step in steps]
