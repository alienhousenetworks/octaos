"""Discovery through governance. One failed provider does not stop the run."""
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.services.sales_os.discovery.identity import canonical_domain
from app.services.sales_os.discovery.waterfall import icp_gate, plan_contact_waterfall
from app.services.sales_os.providers.adapters import build_adapter
from app.services.sales_os.providers.base import ConnectorEnvelope
from app.services.sales_os.providers.registry import ESTIMATED_COST, PAID_PROVIDERS, SALES_OS_CALLABLE, describe_source
from app.services.sales_os.scoring.engine import score_opportunity
from app.services.sales_os.signals.convergence import convergence_bonus
from app.services.sales_os.signals.decay import age_in_days, effective_strength
from app.services.sales_os.signals.normalize import normalize_signal
from app.services.sales_os.orchestration.store import SalesIntelligenceStore
from app.services.sales_os.verification.engine import (
    tier0_identity,
    tier1_syntax,
    tier2_deliverability,
    tier3_employment,
    tier4_compliance,
    tier6_state,
)


class CircuitBreaker:
    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self.failures: dict[str, int] = {}

    def allow(self, provider_key: str) -> bool:
        return self.failures.get(provider_key, 0) < self.threshold

    def record_failure(self, provider_key: str) -> None:
        self.failures[provider_key] = self.failures.get(provider_key, 0) + 1


class SalesPipeline:
    def __init__(self, db: Session, tenant_id: str, adapters: dict | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.store = SalesIntelligenceStore(db, tenant_id)
        self.adapters = adapters or {}
        self.breaker = CircuitBreaker()

    def adapter_for(self, provider_key: str):
        if provider_key not in self.adapters:
            self.adapters[provider_key] = build_adapter(provider_key)
        return self.adapters[provider_key]

    def plan(self, provider_keys: list[str], *, qualified: bool, budget: float | None, credentialed: set[str]) -> list[dict]:
        steps = []
        paid: list[str] = []
        for key in provider_keys:
            described = describe_source(key, key in credentialed)
            if described is None:
                steps.append({"provider_key": key, "action": "skip", "reason": "unknown_provider"})
                continue
            if key in PAID_PROVIDERS:
                if not described["sales_os_callable"]:
                    steps.append({"provider_key": key, "action": "skip", "reason": described["activation_status"], "detail": described["reason"]})
                else:
                    paid.append(key)
                continue
            if not described["sales_os_callable"]:
                steps.append({"provider_key": key, "action": "skip", "reason": described["activation_status"], "detail": described["reason"]})
                continue
            steps.append({"provider_key": key, "action": "call", "reason": "public_or_configured", "estimated_cost": described["estimated_cost_usd"]})
        steps.extend(plan_contact_waterfall(
            qualified=qualified,
            providers=paid,
            costs=ESTIMATED_COST,
            budget=budget,
        ))
        return steps

    async def run(
        self,
        *,
        query: str,
        provider_keys: list[str],
        credentialed: set[str],
        credentials: dict[str, str],
        profile: dict | None = None,
        budget: float | None = None,
        execute: bool = False,
    ) -> dict[str, Any]:
        run = self.store.start_run(query)
        domain = canonical_domain(query)
        company = self.store.upsert_company({"canonical_domain": domain, "display_name": None if domain else query, "website": domain}, "discovery_query") if domain else None
        gate = icp_gate(
            {
                "industry": company.industry if company else None,
                "hq_country": company.hq_country if company else None,
                "employee_count": company.employee_count if company else None,
            },
            profile,
        )
        if company and gate.get("icp_score") is not None:
            company.icp_score = gate["icp_score"]
        steps = self.plan(provider_keys, qualified=gate["qualified"], budget=budget, credentialed=credentialed)
        counts = {"called": 0, "skipped": 0, "errors": 0, "signals": 0, "contacts": 0}
        results = []
        if not execute:
            self.store.finish_run(run, "planned", {**counts, "steps": steps})
            self.db.commit()
            return {"run_id": run.id, "status": "planned", "gate": gate, "steps": steps, "company_id": company.id if company else None}
        for step in steps:
            if step["action"] != "call":
                counts["skipped"] += 1
                self.store.add_source_record(run.id, step["provider_key"], "discover", "skipped", str(uuid.uuid4()), reason=step.get("reason"), estimated_cost=step.get("estimated_cost"))
                results.append(step)
                continue
            provider_key = step["provider_key"]
            if not self.breaker.allow(provider_key):
                counts["skipped"] += 1
                self.store.add_source_record(run.id, provider_key, "discover", "circuit_open", str(uuid.uuid4()), reason="circuit_breaker")
                continue
            if provider_key in PAID_PROVIDERS and budget is None:
                counts["skipped"] += 1
                self.store.add_source_record(run.id, provider_key, "discover", "skipped", str(uuid.uuid4()), reason="budget_decision_required", estimated_cost=ESTIMATED_COST.get(provider_key))
                continue
            adapter = self.adapter_for(provider_key)
            started = time.perf_counter()
            try:
                envelope = await self._call_adapter(adapter, query, credentials.get(provider_key))
            except Exception as exc:
                self.breaker.record_failure(provider_key)
                counts["errors"] += 1
                self.store.add_source_record(run.id, provider_key, "discover", "error", str(uuid.uuid4()), reason=str(exc)[:300])
                results.append({"provider_key": provider_key, "action": "error", "reason": str(exc)[:300]})
                continue
            latency = int((time.perf_counter() - started) * 1000)
            counts["called"] += 1
            if envelope.status not in {"ok", "missing_credentials", "not_activated", "unsupported"}:
                self.breaker.record_failure(provider_key)
                counts["errors"] += 1
            self.store.add_source_record(
                run.id,
                provider_key,
                "discover",
                envelope.status,
                envelope.request_id,
                reason=envelope.reason,
                estimated_cost=envelope.estimated_cost,
                actual_cost=envelope.actual_cost,
                latency_ms=latency,
            )
            company = self._apply_envelope(company, envelope, counts) or company
            results.append(envelope.as_dict())
        opportunity = None
        if company is not None:
            opportunity = self._score_company(company.id)
        self.store.finish_run(run, "completed", counts)
        self.db.commit()
        return {
            "run_id": run.id,
            "status": "completed",
            "gate": gate,
            "steps": steps,
            "results": results,
            "counts": counts,
            "company_id": company.id if company else None,
            "opportunity_id": opportunity.id if opportunity else None,
            "tier6_state": opportunity.tier6_state if opportunity else None,
        }

    async def _call_adapter(self, adapter, query: str, api_key: str | None) -> ConnectorEnvelope:
        capabilities = adapter.capabilities()
        if "contact_discovery" in capabilities:
            return await adapter.discover_contacts(query, api_key)
        if "account_discovery" in capabilities:
            return await adapter.discover_accounts(query, api_key)
        return await adapter.fetch_signals(query, api_key)

    def _apply_envelope(self, company, envelope: ConnectorEnvelope, counts: dict):
        if company is None and envelope.accounts:
            first = envelope.accounts[0]
            if first.canonical_domain or first.display_name:
                company = self.store.upsert_company(
                    {
                        "canonical_domain": first.canonical_domain,
                        "display_name": first.display_name,
                        "website": first.website,
                        "industry": first.industry,
                        "employee_count": first.employee_count,
                        "hq_country": first.hq_country,
                        "hq_city": first.hq_city,
                    },
                    envelope.provider_key,
                )
                company_id = company.id
            else:
                return company
        elif company is not None:
            company_id = company.id
            for account in envelope.accounts:
                self.store.upsert_company(
                    {
                        "canonical_domain": account.canonical_domain or company.canonical_domain,
                        "display_name": account.display_name,
                        "website": account.website,
                        "industry": account.industry,
                        "employee_count": account.employee_count,
                        "hq_country": account.hq_country,
                        "hq_city": account.hq_city,
                    },
                    envelope.provider_key,
                )
        elif envelope.contacts:
            first = envelope.contacts[0]
            if first.company_domain or first.company_name:
                company = self.store.upsert_company(
                    {
                        "canonical_domain": first.company_domain,
                        "display_name": first.company_name,
                        "website": first.company_domain,
                    },
                    envelope.provider_key,
                )
                company_id = company.id
            else:
                return company
        else:
            return company
        for signal in envelope.signals:
            normalized = normalize_signal(
                signal_type=signal.signal_type,
                source_key=envelope.provider_key,
                retrieved_at=envelope.retrieved_at,
                payload=signal.payload,
                observed_at=signal.observed_at,
                source_url=signal.source_url,
                summary=signal.summary,
                excerpt=signal.excerpt,
                base_strength=signal.base_strength,
                source_confidence=signal.source_confidence,
                independent_key=signal.independent_key,
                license_class=envelope.license_class,
            )
            self.store.record_signal(company_id, normalized, envelope.license_class)
            counts["signals"] += 1
        for contact in envelope.contacts:
            saved = self.store.upsert_contact(
                company_id,
                {
                    "full_name": contact.full_name,
                    "email": contact.email,
                    "phone": contact.phone,
                    "role_title": contact.title,
                    "department": contact.department,
                    "linkedin_url": contact.linkedin_url,
                    "provider_id": contact.provider_id,
                    "confidence": contact.confidence,
                },
                envelope.provider_key,
            )
            if saved:
                counts["contacts"] += 1
        return self.store.get_company(company_id)

    def _score_company(self, company_id: str):
        company = self.store.get_company(company_id)
        signals = self.store.list_signals(company_id)
        now = datetime.now(timezone.utc)
        decayed = []
        families = []
        for signal in signals:
            strength = effective_strength(
                signal.base_strength,
                signal.source_confidence,
                age_in_days(signal.observed_at, now),
                signal.half_life_days,
            )
            if strength is not None:
                decayed.append(strength)
            families.append({
                "family": signal.family,
                "payload_hash": signal.payload_hash,
                "independent_key": signal.independent_key,
            })
        intent = round(min(100.0, sum(decayed) / len(decayed)), 2) if decayed else None
        timing = round(min(100.0, max(decayed)), 2) if decayed else None
        convergence = convergence_bonus(families)
        components = {
            "icp": company.icp_score if company else None,
            "intent": intent,
            "timing": timing,
            "problem_fit": None,
            "account_value": None,
            "data_confidence": round(sum(item.source_confidence or 0 for item in signals) / len(signals) * 100, 2) if signals and any(item.source_confidence is not None for item in signals) else None,
            "contactability": None,
            "engagement": None,
        }
        flags = {
            "single_source": len({item.source_key for item in signals}) <= 1 and len(signals) > 0,
            "stale": False,
            "inferred": any(item.is_inferred for item in signals),
            "contradictory": bool(company and company.conflicts),
        }
        scored = score_opportunity(components, flags=flags, convergence_bonus=convergence["bonus"])
        tiers = [
            tier0_identity(canonical_domain=company.canonical_domain if company else None, email=None),
            tier3_employment(has_current_role_evidence=None),
            tier4_compliance(suppressed=False),
        ]
        state = tier6_state(tiers=tiers, score=scored["score"], suppressed=False)
        evidence_ids = [item.evidence_id for item in signals if item.evidence_id]
        if company and intent is not None:
            company.intent_score = intent
        return self.store.save_opportunity(company_id, scored, state, evidence_ids)

    def verify_contact(self, contact_id: str, *, suppressed: bool = False, suppression_reason: str | None = None, permission_state: str = "unknown", jurisdiction: str | None = None, legal_basis: str | None = None, verifier_result: dict | None = None, employment_current: bool | None = None, mx_lookup=None) -> dict:
        contact = self.store.get_contact(contact_id)
        if contact is None:
            raise ValueError("Contact not found")
        company = self.store.get_company(contact.company_id)
        tiers = [
            tier0_identity(canonical_domain=company.canonical_domain if company else None, email=contact.email, provider_ids=contact.provider_ids),
            tier1_syntax(contact.email, mx_lookup=mx_lookup),
            tier2_deliverability(verifier_result),
            tier3_employment(has_current_role_evidence=employment_current),
            tier4_compliance(
                suppressed=suppressed,
                suppression_reason=suppression_reason,
                permission_state=permission_state,
                jurisdiction=jurisdiction,
                legal_basis=legal_basis,
            ),
        ]
        for tier in tiers:
            self.store.save_verification(contact_id, tier)
        opportunity = self.store.latest_opportunity(contact.company_id)
        score = opportunity.score if opportunity else None
        state = tier6_state(tiers=tiers, score=score, suppressed=suppressed, suppression_reason=suppression_reason)
        if opportunity:
            opportunity.tier6_state = state
        self.db.commit()
        return {"contact_id": contact_id, "tiers": tiers, "tier6_state": state}

    def enrich_contacts(self, company_id: str, provider_keys: list[str], budget: float | None, credentialed: set[str], profile: dict | None = None) -> dict:
        company = self.store.get_company(company_id)
        if company is None:
            raise ValueError("Company not found")
        gate = icp_gate(
            {"industry": company.industry, "hq_country": company.hq_country, "employee_count": company.employee_count},
            profile,
        )
        qualified = bool(gate["qualified"])
        prepared = []
        callable_keys = []
        for key in provider_keys:
            described = describe_source(key, key in credentialed)
            if described is None:
                prepared.append({"provider_key": key, "action": "skip", "reason": "unknown_provider", "estimated_cost": None})
                continue
            if not described["sales_os_callable"]:
                prepared.append({
                    "provider_key": key,
                    "action": "skip",
                    "reason": described["activation_status"],
                    "estimated_cost": described["estimated_cost_usd"],
                })
                continue
            callable_keys.append(key)
        steps = prepared + plan_contact_waterfall(
            qualified=qualified,
            providers=callable_keys,
            costs={key: ESTIMATED_COST.get(key) for key in callable_keys},
            budget=budget,
        )
        calls = [step for step in steps if step["action"] == "call"]
        if not qualified:
            return {"executed": False, "reason": "account_not_qualified", "steps": steps}
        if budget is None:
            return {"executed": False, "reason": "budget_decision_required", "steps": steps}
        return {"executed": False, "reason": "plan_only", "steps": steps, "would_call": [step["provider_key"] for step in calls], "company_id": company_id}

    async def execute_enrichment(self, company_id: str, provider_keys: list[str], budget: float | None, credentialed: set[str], credentials: dict[str, str], profile: dict | None = None) -> dict:
        plan = self.enrich_contacts(company_id, provider_keys, budget, credentialed, profile)
        if plan["reason"] != "plan_only":
            return plan
        company = self.store.get_company(company_id)
        counts = {"contacts": 0, "signals": 0}
        results = []
        run = self.store.start_run(company.canonical_domain or company.display_name or company_id, trigger="enrich")
        for step in plan["steps"]:
            if step["action"] != "call":
                self.store.add_source_record(run.id, step["provider_key"], "enrich", "skipped", str(uuid.uuid4()), reason=step["reason"], estimated_cost=step.get("estimated_cost"))
                continue
            adapter = self.adapter_for(step["provider_key"])
            try:
                envelope = await adapter.discover_contacts(company.canonical_domain or company.display_name or "", credentials.get(step["provider_key"]))
            except Exception as exc:
                self.breaker.record_failure(step["provider_key"])
                self.store.add_source_record(run.id, step["provider_key"], "enrich", "error", str(uuid.uuid4()), reason=str(exc)[:300])
                results.append({"provider_key": step["provider_key"], "action": "error", "reason": str(exc)[:300]})
                continue
            self.store.add_source_record(
                run.id,
                step["provider_key"],
                "enrich",
                envelope.status,
                envelope.request_id,
                reason=envelope.reason,
                estimated_cost=envelope.estimated_cost,
                actual_cost=envelope.actual_cost,
            )
            self._apply_envelope(company, envelope, counts)
            results.append(envelope.as_dict())
        self.store.finish_run(run, "completed", counts)
        self.db.commit()
        plan["executed"] = True
        plan["reason"] = "completed"
        plan["results"] = results
        plan["run_id"] = run.id
        return plan
