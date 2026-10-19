"""Modular skills for the gaps between the current agents and a governed sales system.

These functions do not call a model and do not perform external side effects.
"""
import hashlib
from datetime import datetime, timezone

from app.services.sales_os.attribution.source_roi import summarize_roi
from app.services.sales_os.contracts.outputs import (
    BuyingCommitteeMap,
    CadenceDecision,
    EvaluationReport,
    EvidenceAssessment,
    ExperimentReport,
    MeetingHandoff,
    PlaybookUpdate,
    PolicyDecisionContract,
    ReconciliationResult,
    SalesRiskIncident,
    SalesSignal,
    SearchPlan,
    SourceOutcome,
)
from app.services.sales_os.contracts.registry import ContractError, get_contract, validate_registry
from app.services.sales_os.search_v4.contracts import CampaignIntentSpec
from app.services.sales_os.search_v4.planner import plan_tasks
from app.services.sales_os.search_v4.registry import ProviderHealth, ProviderStats
from app.services.sales_os.signals.decay import age_in_days, effective_strength
from app.services.sales_os.signals.taxonomy import half_life_for
from app.services.sales_os.aso.qualification import qualify_account
from app.services.sales_os.aso.reply_taxonomy import normalize_reply_intent

_FREE_SOURCES = {"duckduckgo", "google_news", "hn_algolia", "company_page"}
_ROLE_HINTS = (
    ("economic_buyer", ("cro", "cfo", "ceo", "chief revenue", "chief financial", "vp sales", "head of sales")),
    ("champion", ("champion",)),
    ("technical_evaluator", ("cto", "engineer", "architect", "cio")),
    ("procurement", ("procurement", "purchasing", "legal")),
    ("end_user", ("operator", "end user")),
)
_REQUIRED_ROLES = ("economic_buyer", "champion", "technical_evaluator", "procurement")
_PRECEDENCE = {"verified_human": 4, "crm": 3, "provider": 2, "inferred": 1}


def _require_testing(agent_id: str) -> None:
    contract = get_contract(agent_id)
    if contract.lifecycle_status.value in {"draft", "disabled", "deprecated"}:
        raise ContractError(f"{agent_id} is not executable")
    if contract.uses_llm:
        raise ContractError(f"{agent_id} is rendered through the prompt registry, not run as a side effect")


def _parse_time(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        observed = value
    else:
        observed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return observed


def _supports(claim: str, source_text: str) -> bool:
    claim_text = " ".join(claim.lower().split())
    source = " ".join(source_text.lower().split())
    if len(claim_text) < 8 or not source:
        return False
    if claim_text in source or source in claim_text:
        return True
    claim_tokens = set(claim_text.split())
    source_tokens = set(source.split())
    if not claim_tokens:
        return False
    return len(claim_tokens & source_tokens) / len(claim_tokens) >= 0.7


def plan_search(payload: dict) -> SearchPlan:
    _require_testing("sales.search_strategy")
    allowed = [str(item) for item in payload.get("allowed_providers") or []]
    credentials = {name: "configured" for name in allowed}
    if "brave" in credentials:
        credentials["brave_search"] = "configured"
    if "brave_search" in credentials:
        allowed.append("brave")
    spec = CampaignIntentSpec(
        campaign_id=str(payload.get("campaign_id") or "campaign"),
        tenant_id=str(payload.get("tenant_id") or ""),
        query=str(payload.get("query") or ""),
        industries=list(payload.get("industries") or []),
        buyer_roles=list(payload.get("buyer_roles") or []),
        geography=list(payload.get("geography") or []),
        exclusions=list(payload.get("exclusions") or []),
        budget_inr=float(payload.get("budget_inr") or 0),
        monthly_limit_inr=float(payload.get("budget_inr") or 0),
        seed_urls=list(payload.get("seed_urls") or []),
    )
    tasks, notes = plan_tasks(
        spec,
        credentials,
        list(payload.get("history") or []),
        ProviderStats(),
        ProviderHealth(),
        spec.budget_inr,
    )
    families = []
    sources: list[str] = []
    for task in tasks:
        executable = task.provider in _FREE_SOURCES or task.provider in allowed or task.provider in credentials
        if task.provider in {"reddit", "x"} and task.provider not in allowed:
            notes.append(f"{task.provider} stays unavailable until an authorized credential is configured.")
            executable = False
        if executable:
            sources.append(task.provider)
        families.append(
            {
                "method": task.method,
                "provider": task.provider,
                "query": task.query,
                "estimated_cost_inr": task.estimated_cost_inr,
                "stop_condition": task.stop_condition,
                "executable": executable,
            }
        )
    spent = round(sum(item["estimated_cost_inr"] for item in families if item["executable"]), 4)
    return SearchPlan(
        query_families=families,
        allowed_sources=sorted(set(sources)),
        budget_inr=spec.budget_inr,
        spent_estimate_inr=spent,
        stop_conditions=[
            "Stop when the remaining budget cannot pay the next paid call.",
            "Stop when a query repeats a previous query for the same method.",
            "Stop when the provider returns an empty page.",
        ],
        expected_outcomes="Qualified accounts are not guaranteed. Yield depends on the ICP, source access, and evidence.",
        notes=notes,
    )


def interpret_signal(payload: dict) -> SalesSignal:
    _require_testing("sales.buying_signals")
    signal_type = str(payload.get("signal_type") or "")
    observed = _parse_time(payload.get("observed_at"))
    half_life = half_life_for(signal_type, payload.get("half_life_days"))
    strength = effective_strength(
        payload.get("base_strength"),
        payload.get("source_confidence"),
        age_in_days(observed) if observed else None,
        half_life,
    )
    return SalesSignal(
        signal_type=signal_type or "unknown",
        source=str(payload.get("source") or ""),
        observation_time=observed,
        expiry_policy=f"half_life_days={half_life}" if half_life else "unknown",
        evidence=list(payload.get("evidence") or []),
        fact=str(payload.get("fact") or ""),
        inference=payload.get("inference"),
        confidence=payload.get("source_confidence"),
        strength=None if strength is None else round(strength, 4),
    )


def assess_evidence(payload: dict) -> EvidenceAssessment:
    _require_testing("sales.evidence_verifier")
    sources = {item.get("id"): item for item in payload.get("sources") or [] if item.get("id")}
    supported: list[str] = []
    missing: list[str] = []
    for claim in payload.get("claims") or []:
        text = str(claim.get("text") or "").strip()
        if not text:
            continue
        refs = claim.get("evidence_refs") or []
        if any(_supports(text, (sources.get(ref) or {}).get("text") or "") for ref in refs):
            supported.append(text)
        else:
            missing.append(text)
    conflicts = []
    grouped: dict[str, set[str]] = {}
    for record in payload.get("records") or []:
        field = str(record.get("field") or "")
        if not field:
            continue
        grouped.setdefault(field, set()).add(str(record.get("value")))
    for field, values in grouped.items():
        if len(values) > 1:
            conflicts.append(f"{field}: {' vs '.join(sorted(values))}")
    if conflicts:
        status = "conflicting"
        uses: list[str] = []
    elif not supported:
        status = "unavailable"
        uses = []
    elif missing:
        status = "inference"
        uses = ["internal_review"]
    else:
        status = "verified"
        uses = ["scoring", "research_brief"]
    return EvidenceAssessment(
        status=status,
        supported_claims=supported,
        conflicts=conflicts,
        missing_evidence=missing,
        allowed_uses=uses,
        confidence=1.0 if status == "verified" else 0.0 if status == "unavailable" else 0.4,
    )


def map_committee(payload: dict) -> BuyingCommitteeMap:
    _require_testing("sales.buying_committee")
    members = []
    found_roles: set[str] = set()
    for person in payload.get("people") or []:
        name = str(person.get("name") or "").strip()
        if not name:
            continue
        title = str(person.get("title") or "")
        lowered = title.lower()
        role = "unknown"
        for candidate, hints in _ROLE_HINTS:
            if any(hint in lowered for hint in hints):
                role = candidate
                break
        if role != "unknown":
            found_roles.add(role)
        members.append(
            {
                "name": name,
                "title": title,
                "role": role,
                "evidence_ref": person.get("evidence_ref"),
                "confidence": 0.6 if role != "unknown" else None,
            }
        )
    missing = [role for role in _REQUIRED_ROLES if role not in found_roles]
    return BuyingCommitteeMap(
        members=members,
        missing_roles=missing,
        single_threaded=len(members) < 2,
        confidence=0.6 if members else None,
    )


def decide_policy(payload: dict) -> PolicyDecisionContract:
    _require_testing("sales.policy_controller")
    reasons = []
    if payload.get("suppressed"):
        reasons.append(str(payload.get("suppression_reason") or "suppression record"))
        return PolicyDecisionContract(
            decision="deny",
            rule_ids=["suppression.precedence"],
            reasons=reasons,
            llm_may_override=False,
        )
    if payload.get("frequency_ok") is False:
        return PolicyDecisionContract(
            decision="deny",
            rule_ids=["cadence.frequency_cap"],
            reasons=[str(payload.get("frequency_reason") or "frequency cap")],
            llm_may_override=False,
        )
    groundedness = payload.get("groundedness")
    if groundedness is not None and float(groundedness) < 0.85:
        return PolicyDecisionContract(
            decision="require_approval",
            rule_ids=["evidence.groundedness_threshold"],
            reasons=["Groundedness is below 0.85."],
            llm_may_override=False,
        )
    mode = str(payload.get("autonomy_mode") or "draft_only")
    action = str(payload.get("action_type") or "first_touch")
    if mode in {"draft_only", "assist"}:
        return PolicyDecisionContract(
            decision="require_approval",
            rule_ids=["autonomy.assist"],
            reasons=["The tenant autonomy mode requires approval before a send."],
            llm_may_override=False,
        )
    if mode in {"auto_with_rules", "copilot"} and action == "first_touch":
        return PolicyDecisionContract(
            decision="require_approval",
            rule_ids=["autonomy.copilot_first_touch"],
            reasons=["A first touch in copilot mode requires approval."],
            llm_may_override=False,
        )
    if mode in {"auto_with_rules", "copilot", "autonomous"}:
        return PolicyDecisionContract(
            decision="allow",
            rule_ids=["autonomy.authorized_follow_up"],
            reasons=["The action is inside the configured autonomy band."],
            llm_may_override=False,
        )
    return PolicyDecisionContract(
        decision="require_approval",
        rule_ids=["autonomy.unknown_mode"],
        reasons=[f"Unknown autonomy mode {mode}."],
        llm_may_override=False,
    )


def decide_cadence(payload: dict) -> CadenceDecision:
    _require_testing("sales.cadence_optimizer")
    key_raw = "|".join(
        [
            str(payload.get("tenant_id") or ""),
            str(payload.get("recipient") or ""),
            str(payload.get("channel") or "email"),
            str(payload.get("step") or "1"),
            str(payload.get("campaign_id") or ""),
        ]
    )
    key = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()
    if payload.get("suppressed"):
        return CadenceDecision(eligible=False, next_action="suppress", reason="Suppression overrides the cadence.", idempotency_key=key)
    if payload.get("consent") is not True:
        return CadenceDecision(eligible=False, next_action="wait_for_consent", reason="The channel has no recorded consent.", idempotency_key=key)
    if payload.get("frequency_ok") is False:
        return CadenceDecision(eligible=False, next_action="backoff", reason="The frequency cap has been reached.", idempotency_key=key)
    if payload.get("duplicate") is True:
        return CadenceDecision(eligible=False, next_action="skip_duplicate", reason="This action key was already claimed.", idempotency_key=key)
    return CadenceDecision(
        eligible=True,
        next_action=str(payload.get("proposed_action") or "send_next_step"),
        reason="Consent, suppression, and frequency checks passed.",
        idempotency_key=key,
    )


def prepare_meeting(payload: dict) -> MeetingHandoff:
    _require_testing("sales.meeting_handoff")
    if payload.get("suppressed"):
        return MeetingHandoff(scheduling_status="suppressed", calendar_written=False)
    text = str(payload.get("reply_text") or "")
    has_time = any(token in text.lower() for token in ("monday", "tuesday", "wednesday", "thursday", "friday", "am", "pm", ":"))
    if not has_time:
        return MeetingHandoff(
            scheduling_status="insufficient_detail",
            attendees=list(payload.get("attendees") or []),
            owner=payload.get("owner"),
            calendar_written=False,
        )
    agenda = [item for item in payload.get("agenda") or [] if item]
    if not agenda:
        agenda = ["Confirm the problem the prospect described.", "Agree the next step."]
    return MeetingHandoff(
        scheduling_status="needs_confirmation",
        attendees=list(payload.get("attendees") or []),
        agenda=agenda,
        owner=payload.get("owner"),
        calendar_written=False,
    )


def attribute_sources(payload: dict) -> tuple[SourceOutcome, ExperimentReport]:
    _require_testing("sales.attribution")
    seen: set[str] = set()
    outcomes = []
    for outcome in payload.get("outcomes") or []:
        deal_id = str(outcome.get("deal_id") or "")
        kind = outcome.get("outcome_type")
        if kind == "revenue" and deal_id:
            if deal_id in seen:
                continue
            seen.add(deal_id)
        outcomes.append(outcome)
    summary = summarize_roi(list(payload.get("costs") or []), outcomes)
    provider = str(payload.get("source") or "unknown")
    sample = int(summary["sample_size"])
    minimum = int(payload.get("minimum_sample") or 30)
    report = ExperimentReport(
        experiment_id=str(payload.get("experiment_id") or "baseline"),
        sample_size=sample,
        sufficient_sample=sample >= minimum,
        uncertainty="The sample is below the minimum." if sample < minimum else "The sample meets the minimum. This is still not a causal estimate.",
        recommendation="Hold the current allocation." if sample < minimum else "Compare this source with the fixed baseline before shifting budget.",
    )
    return (
        SourceOutcome(
            source=provider,
            cost=summary["spend"],
            meetings=int(summary["meetings"]),
            revenue=summary["revenue"],
            revenue_confidence=None if summary["revenue"] is None else min(1.0, sample / max(minimum, 1)),
            sample_size=sample,
            counted_deal_ids=sorted(seen),
            attribution_is_causal=False,
        ),
        report,
    )


def propose_playbook(payload: dict) -> PlaybookUpdate:
    _require_testing("sales.playbook_curator")
    refs = [str(item) for item in payload.get("source_refs") or [] if item]
    if not refs:
        return PlaybookUpdate(status="rejected", applied=False, reason="A playbook change needs a source reference.")
    if payload.get("human_approved") is not True or not payload.get("approval_id"):
        return PlaybookUpdate(
            status="review_required",
            source_refs=refs,
            applied=False,
            reason="Authoritative playbook text stays unchanged until a person approves it.",
        )
    return PlaybookUpdate(
        status="pending_approval",
        source_refs=refs,
        applied=False,
        reason="The approval id was recorded. Applying the change is a separate governed write.",
    )


def evaluate_release(payload: dict | None = None) -> EvaluationReport:
    _require_testing("sales.evaluation")
    payload = payload or {}
    failures = list(validate_registry())
    unknown = normalize_reply_intent(payload.get("reply_probe") or "please do the needful")
    if unknown.intent != "needs_human_review" or unknown.opt_out:
        failures.append("unknown reply became an action")
    denied = decide_policy({"suppressed": True, "llm_override": True, "autonomy_mode": "autonomous"})
    if denied.decision != "deny" or denied.llm_may_override:
        failures.append("suppression was overridable")
    unsupported = assess_evidence(
        {"claims": [{"text": "The company signed a renewal yesterday", "evidence_refs": ["s1"]}], "sources": [{"id": "s1", "text": "The company posted a job."}]}
    )
    if unsupported.status == "verified" or "The company signed a renewal yesterday" in unsupported.supported_claims:
        failures.append("unsupported claim was accepted")
    review = qualify_account(industry=None, employee_count=500, annual_revenue_usd=5_000_000, target_industries=["saas"])
    if review.decision == "qualified":
        failures.append("missing industry qualified the account")
    return EvaluationReport(
        metric_changes=[],
        failed_cases=failures,
        severity="none" if not failures else "high",
        release_recommendation="promote_candidate" if not failures else "hold",
    )


def reconcile_records(payload: dict) -> ReconciliationResult:
    _require_testing("sales.crm_reconciliation")
    current = payload.get("current") or {}
    incoming = payload.get("incoming") or {}
    applied = []
    conflicts = []
    proposed = []
    for field, new_value in incoming.items():
        proposal = new_value if isinstance(new_value, dict) else {"value": new_value, "source_class": "provider"}
        existing = current.get(field)
        if existing is None or existing.get("value") in (None, ""):
            applied.append({"field": field, "value": proposal.get("value"), "source_class": proposal.get("source_class")})
            continue
        if existing.get("value") == proposal.get("value"):
            continue
        current_rank = _PRECEDENCE.get(str(existing.get("source_class")), 0)
        incoming_rank = _PRECEDENCE.get(str(proposal.get("source_class")), 0)
        if current_rank >= incoming_rank:
            conflicts.append(
                {
                    "field": field,
                    "kept": existing.get("value"),
                    "rejected": proposal.get("value"),
                    "reason": "lower_or_equal_precedence",
                }
            )
        else:
            proposed.append({"field": field, "value": proposal.get("value"), "source_class": proposal.get("source_class")})
            applied.append({"field": field, "value": proposal.get("value"), "source_class": proposal.get("source_class")})
    if conflicts:
        status = "quarantined"
    elif applied:
        status = "applied"
    else:
        status = "unchanged"
    return ReconciliationResult(proposed_changes=proposed, conflicts=conflicts, applied=applied, status=status)


def monitor_risk(payload: dict) -> list[SalesRiskIncident]:
    _require_testing("sales.risk_monitor")
    incidents: list[SalesRiskIncident] = []
    bounce = payload.get("bounce_rate")
    previous_bounce = payload.get("previous_bounce_rate")
    if bounce is not None and float(bounce) >= 0.08 and (previous_bounce is None or float(bounce) >= float(previous_bounce) * 2):
        incidents.append(
            SalesRiskIncident(
                severity="critical",
                scope=str(payload.get("scope") or "sender"),
                evidence=[f"bounce_rate={bounce}", f"previous_bounce_rate={previous_bounce}"],
                containment="pause_affected_sender",
            )
        )
    if int(payload.get("duplicate_sends") or 0) > 0:
        incidents.append(
            SalesRiskIncident(
                severity="warning",
                scope=str(payload.get("scope") or "campaign"),
                evidence=[f"duplicate_sends={payload.get('duplicate_sends')}"],
                containment="halt_duplicate_actions",
            )
        )
    cost = payload.get("cost_inr")
    previous_cost = payload.get("previous_cost_inr")
    if cost is not None and previous_cost not in (None, 0) and float(cost) > float(previous_cost) * 3 and float(cost) - float(previous_cost) > 50:
        incidents.append(
            SalesRiskIncident(
                severity="warning",
                scope=str(payload.get("scope") or "connector"),
                evidence=[f"cost_inr={cost}", f"previous_cost_inr={previous_cost}"],
                containment="stop_paid_source",
            )
        )
    if not incidents:
        incidents.append(SalesRiskIncident(severity="info", scope=str(payload.get("scope") or "tenant"), evidence=[], containment="none"))
    return incidents


_RUNNERS = {
    "sales.search_strategy": plan_search,
    "sales.buying_signals": interpret_signal,
    "sales.evidence_verifier": assess_evidence,
    "sales.buying_committee": map_committee,
    "sales.policy_controller": decide_policy,
    "sales.cadence_optimizer": decide_cadence,
    "sales.meeting_handoff": prepare_meeting,
    "sales.attribution": attribute_sources,
    "sales.playbook_curator": propose_playbook,
    "sales.evaluation": evaluate_release,
    "sales.crm_reconciliation": reconcile_records,
    "sales.risk_monitor": monitor_risk,
}


def run_skill(agent_id: str, payload: dict | None = None):
    runner = _RUNNERS.get(get_contract(agent_id).agent_id)
    if runner is None:
        raise ContractError(f"{agent_id} is not a modular skill")
    return runner(payload or {})
