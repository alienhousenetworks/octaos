"""One qualification decision. Unknown inputs are not filled with a middle score."""
from app.services.sales_os.contracts.outputs import QualificationDecision

_WEIGHTS = {"industry_fit": 0.40, "size_fit": 0.35, "budget_fit": 0.25}


def _industry_fit(industry: str | None, target_industries: list[str]) -> float | None:
    if not industry:
        return None
    lowered = industry.lower()
    targets = [item.lower() for item in target_industries if item]
    if not targets:
        return None
    if any(target in lowered or lowered in target for target in targets):
        return 1.0
    return 0.0


def _size_fit(employee_count: int | None) -> float | None:
    if employee_count is None:
        return None
    if 20 <= employee_count <= 2000:
        return 1.0
    if 5 <= employee_count < 20:
        return 0.6
    return 0.5


def _budget_fit(annual_revenue_usd: float | None) -> float | None:
    if annual_revenue_usd is None:
        return None
    if annual_revenue_usd >= 1_000_000:
        return 1.0
    return 0.6


def qualify_account(
    *,
    industry: str | None,
    employee_count: int | None,
    annual_revenue_usd: float | None,
    target_industries: list[str],
    timing_score: float | None = None,
    intent_score: float | None = None,
    contact_readiness: float | None = None,
    suppressed: bool = False,
) -> QualificationDecision:
    if suppressed:
        return QualificationDecision(
            decision="suppressed",
            confidence=1.0,
            disqualifiers=["suppression_record"],
            rationale="A suppression record overrides fit and intent.",
            inputs={"suppressed": True},
        )

    components = {
        "industry_fit": _industry_fit(industry, target_industries),
        "size_fit": _size_fit(employee_count),
        "budget_fit": _budget_fit(annual_revenue_usd),
    }
    unknowns = [name for name, value in components.items() if value is None]
    if timing_score is None:
        unknowns.append("timing")
    required_unknowns = [name for name in ("industry_fit", "size_fit", "budget_fit") if components[name] is None]
    known = {name: value for name, value in components.items() if value is not None}
    fit = None
    if known:
        weight = sum(_WEIGHTS[name] for name in known)
        fit = round(sum(known[name] * _WEIGHTS[name] for name in known) / weight, 3)

    disqualifiers: list[str] = []
    if components["industry_fit"] == 0.0:
        disqualifiers.append("industry_not_in_icp")

    if required_unknowns:
        decision = "needs_review"
        rationale = "Required ICP evidence is missing, so the account is not qualified."
    elif disqualifiers:
        decision = "disqualified"
        rationale = "The account contradicts the ICP."
    elif fit is not None and fit >= 0.55:
        decision = "qualified"
        rationale = "The evidenced ICP components meet the qualification threshold."
    else:
        decision = "disqualified"
        rationale = "The evidenced ICP fit is below the qualification threshold."

    evidence_quality = None if not components else round(1 - (len([item for item in unknowns if item != "timing"]) / 3), 3)
    confidence = 1.0 if not unknowns else round(max(0.0, 1 - (0.25 * len(unknowns))), 2)
    return QualificationDecision(
        fit_score=fit,
        intent_score=intent_score if intent_score is not None else timing_score,
        evidence_quality=evidence_quality,
        contact_readiness=contact_readiness,
        confidence=confidence,
        decision=decision,
        disqualifiers=disqualifiers,
        unknowns=unknowns,
        rationale=rationale,
        inputs={name: value for name, value in components.items()},
    )
