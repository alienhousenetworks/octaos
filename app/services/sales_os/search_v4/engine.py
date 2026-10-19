"""Run the additional search methods, then score what they actually returned."""
import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.services.sales_os.search_v4.budget import BudgetLedger
from app.services.sales_os.search_v4.connectors.base import ConnectorResult, Hit
from app.services.sales_os.search_v4.contracts import (
    CampaignIntentSpec,
    DiscoveryRecord,
    QualifiedCandidate,
    SearchBatch,
    SearchTask,
    new_id,
)
from app.services.sales_os.search_v4.evidence import verify_evidence
from app.services.sales_os.search_v4.expansion import propose_expansions
from app.services.sales_os.search_v4.intent import classify_intent
from app.services.sales_os.search_v4.planner import _task, plan_tasks
from app.services.sales_os.search_v4.registry import ProviderHealth, choose_web_provider
from app.services.sales_os.search_v4.scoring import _tokens, score_record
from app.services.sales_os.search_v4.store import MemorySearchStore
from app.services.sales_os.search_v4.urls import canonical_url, dedupe_key, host_of, is_company_site

logger = logging.getLogger(__name__)


class SearchEngine:
    def __init__(self, store: MemorySearchStore, connectors, credentials: dict[str, str] | None = None):
        self.store = store
        self.connectors = connectors
        self.credentials = credentials or {}
        self.health = ProviderHealth()

    async def run(
        self,
        spec: CampaignIntentSpec,
        history: list[str] | None = None,
        suppressed_domains: set[str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> SearchBatch:
        now = datetime.now(timezone.utc)
        spent = self.store.month_spend_inr(spec.tenant_id, now)
        run_limit = max(0.0, min(spec.budget_inr, spec.monthly_limit_inr - spent))
        tasks, notes = plan_tasks(
            spec,
            self.credentials,
            history or [],
            self.store.provider_stats(),
            self.health,
            run_limit,
        )
        payload = {
            "job_id": new_id(),
            "status": "running",
            "spec": spec.model_dump(mode="json"),
            "tasks": [task.model_dump(mode="json") for task in tasks],
            "records": [],
            "assessments": [],
            "ledger": [],
            "notes": notes,
            "expansion_done": False,
            "suppressed_domains": sorted(suppressed_domains or []),
            "run_limit": run_limit,
        }
        self.store.save_job(spec.tenant_id, payload["job_id"], payload)
        return await self._continue(payload, spec, client, resumed=False)

    async def resume(self, tenant_id: str, job_id: str, client: httpx.AsyncClient | None = None) -> SearchBatch:
        payload = self.store.get_job(tenant_id, job_id)
        if payload is None:
            raise KeyError(f"Search job {job_id} was not found for this tenant.")
        spec = CampaignIntentSpec.model_validate(payload["spec"])
        if payload.get("status") == "cancelled":
            return self._batch(payload, spec, resumed=True)
        payload["status"] = "running"
        return await self._continue(payload, spec, client, resumed=True)

    def cancel(self, tenant_id: str, job_id: str) -> None:
        payload = self.store.get_job(tenant_id, job_id)
        if payload is None:
            return
        payload["status"] = "cancelled"
        self.store.save_job(tenant_id, job_id, payload)

    async def _continue(self, payload: dict, spec: CampaignIntentSpec, client: httpx.AsyncClient | None, resumed: bool) -> SearchBatch:
        owns_client = client is None
        if owns_client:
            client = httpx.AsyncClient(timeout=12.0)
        try:
            await self._execute_pending(payload, spec, client)
            if not payload.get("expansion_done") and payload.get("status") != "cancelled":
                payload["expansion_done"] = True
                self._add_followups(payload, spec)
                await self._execute_pending(payload, spec, client)
            self._score(payload, spec)
            self._record_yield(payload)
            payload["status"] = self._job_status(payload)
            self.store.save_job(spec.tenant_id, payload["job_id"], payload)
            return self._batch(payload, spec, resumed=resumed)
        finally:
            if owns_client:
                await client.aclose()

    async def _execute_pending(self, payload: dict, spec: CampaignIntentSpec, client: httpx.AsyncClient) -> None:
        ledger = self._ledger(payload, spec)
        for _wave in range(3):
            if payload.get("status") == "cancelled":
                return
            runnable = []
            for task in payload["tasks"]:
                if task["status"] not in {"planned", "running"}:
                    continue
                cached = self.store.get_cached(spec.tenant_id, task["idempotency_key"])
                if cached:
                    self._apply_cached(payload, task, cached)
                    continue
                if not self.health.allows(task["provider"]):
                    task["status"] = "blocked"
                    task["reason"] = "circuit_open"
                    task["failure_class"] = "circuit_open"
                    continue
                entry = ledger.reserve(task["provider"], task["operation"], task["estimated_cost_inr"], task["task_id"])
                payload["ledger"].append(entry.model_dump(mode="json"))
                if entry.status != "reserved":
                    task["status"] = "blocked"
                    task["reason"] = "budget_exceeded"
                    task["failure_class"] = "budget"
                    continue
                task["reservation_id"] = entry.entry_id
                task["status"] = "running"
                runnable.append(task)
            self.store.save_job(spec.tenant_id, payload["job_id"], payload)
            if not runnable:
                break
            results = await asyncio.gather(
                *[self._call(SearchTask.model_validate(task), client) for task in runnable],
                return_exceptions=True,
            )
            retry = False
            for task, result in zip(runnable, results):
                if isinstance(result, Exception):
                    result = ConnectorResult(status="failed", failure_class="transient", reason=result.__class__.__name__)
                self._apply_result(payload, spec, task, result, ledger)
                if task["status"] == "planned":
                    retry = True
            self.store.save_job(spec.tenant_id, payload["job_id"], payload)
            if not retry:
                break

    async def _call(self, task: SearchTask, client: httpx.AsyncClient) -> ConnectorResult:
        return await self.connectors.execute(task, client)

    def _apply_cached(self, payload: dict, task: dict, cached: dict) -> None:
        task["status"] = cached.get("status") or "succeeded"
        task["reason"] = cached.get("reason") or "Reused a stored result for this query."
        task["failure_class"] = cached.get("failure_class")
        self._add_hits(payload, task, cached.get("hits") or [])

    def _apply_result(self, payload: dict, spec: CampaignIntentSpec, task: dict, result: ConnectorResult, ledger: BudgetLedger) -> None:
        reservation_id = task.get("reservation_id")
        task["attempt"] = int(task.get("attempt") or 0) + 1
        task["reason"] = result.reason
        task["failure_class"] = result.failure_class
        if result.status == "failed" and result.failure_class == "transient" and task["attempt"] < int(task.get("retry_limit") or 2):
            if reservation_id:
                ledger.release(reservation_id)
                self._mirror_ledger(payload, reservation_id, "released", 0.0)
            task["status"] = "planned"
            self.health.record_failure(task["provider"])
            return
        if result.status == "ok":
            task["status"] = "succeeded"
        elif result.status in {"empty", "unavailable", "failed"}:
            task["status"] = result.status
        else:
            task["status"] = "failed"
        if result.billable and task["status"] in {"succeeded", "empty"}:
            if reservation_id:
                ledger.reconcile(reservation_id, result.actual_cost_inr)
                self._mirror_ledger(payload, reservation_id, "reconciled", result.actual_cost_inr)
            self.store.add_spend(spec.tenant_id, result.actual_cost_inr, datetime.now(timezone.utc))
        elif reservation_id:
            ledger.release(reservation_id)
            self._mirror_ledger(payload, reservation_id, "released", 0.0)
        if task["status"] in {"succeeded", "empty"}:
            self.health.record_success(task["provider"])
        elif task["status"] == "failed":
            self.health.record_failure(task["provider"])
        hits = [self._hit_dump(hit) for hit in result.hits]
        self._add_hits(payload, task, hits)
        if task["status"] in {"succeeded", "empty", "unavailable"} or result.failure_class in {"permission", "invalid"}:
            self.store.put_cached(
                spec.tenant_id,
                task["idempotency_key"],
                {"status": task["status"], "reason": task["reason"], "failure_class": task["failure_class"], "hits": hits},
            )
    def _mirror_ledger(self, payload: dict, entry_id: str, status: str, actual: float) -> None:
        for row in payload["ledger"]:
            if row.get("entry_id") == entry_id:
                row["status"] = status
                row["actual_cost_inr"] = actual

    def _add_hits(self, payload: dict, task: dict, hits: list[dict]) -> None:
        seen = {row["dedupe_key"] for row in payload["records"]}
        for hit in hits:
            url = hit.get("url") or ""
            key = dedupe_key(url)
            if not key or key in seen:
                continue
            seen.add(key)
            domain = hit.get("company_domain") or (host_of(url) if is_company_site(url) else None)
            record = DiscoveryRecord(
                correlation_id=task["correlation_id"],
                task_id=task["task_id"],
                tenant_id=task["tenant_id"],
                method=task["method"],
                provider=task["provider"],
                original_url=url,
                canonical_url=canonical_url(url) or url,
                title=hit.get("title") or "",
                snippet=hit.get("snippet") or "",
                page_excerpt=(hit.get("page_excerpt") or "")[:700],
                provider_native_id=hit.get("provider_native_id"),
                dedupe_key=key,
                company_name=hit.get("company_name") or "",
                company_domain=domain,
                contact_name=hit.get("contact_name") or "",
                contact_email=hit.get("contact_email") or "",
            )
            payload["records"].append(record.model_dump(mode="json"))

    def _score(self, payload: dict, spec: CampaignIntentSpec) -> None:
        tokens = _tokens(" ".join([spec.query, *spec.industries, *spec.buyer_roles]))
        suppressed = set(payload.get("suppressed_domains") or [])
        assessments = []
        for raw in payload["records"]:
            record = DiscoveryRecord.model_validate(raw)
            intent, span, explicit, notes = classify_intent(record, tokens)
            evidence = verify_evidence(record, intent, span, explicit, spec.freshness)
            if intent.value not in {"IRRELEVANT", "GENERAL_INTEREST", "INSUFFICIENT_EVIDENCE"} and evidence.verification_state != "supported":
                from app.services.sales_os.search_v4.contracts import IntentCategory

                intent = IntentCategory.INSUFFICIENT_EVIDENCE
            assessment = score_record(record, spec, intent, evidence, suppressed)
            assessment.uncertainty.extend(notes)
            assessments.append({"assessment": assessment.model_dump(mode="json"), "evidence": evidence.model_dump(mode="json")})
        payload["assessments"] = assessments

    def _add_followups(self, payload: dict, spec: CampaignIntentSpec) -> None:
        from app.services.sales_os.search_v4.contracts import IntentCategory, LeadEvidence

        self._score(payload, spec)
        built = []
        for raw, scored in zip(payload["records"], payload["assessments"]):
            record = DiscoveryRecord.model_validate(raw)
            evidence = LeadEvidence.model_validate(scored["evidence"])
            assessment = score_record(
                record,
                spec,
                IntentCategory(scored["assessment"]["intent"]),
                evidence,
                set(payload.get("suppressed_domains") or []),
            )
            built.append((record, assessment))
        provider, _why, _cost = choose_web_provider(self.credentials, self.store.provider_stats(), self.health)
        queries = [task["query"] for task in payload["tasks"]]
        extra = propose_expansions(built, spec, queries, provider, self._remaining_inr(payload))
        company_tasks = 0
        for record, assessment in built:
            if company_tasks >= 2:
                break
            if assessment.decision not in {"accept", "nurture"} or not record.company_domain:
                continue
            url = f"https://{record.company_domain}"
            if not is_company_site(url) or any(task["query"] == url for task in payload["tasks"]):
                continue
            task = _task(
                spec,
                "company",
                "company_page",
                "fetch",
                url,
                "Read the company site that a search result already identified.",
                0.0,
                f"Company page for {record.company_domain} from record {record.record_id}.",
                15,
                parent_record_id=record.record_id,
                depth=1,
            )
            if task is not None:
                extra.append(task)
                company_tasks += 1
        existing_keys = {task["idempotency_key"] for task in payload["tasks"]}
        for task in extra:
            if task.idempotency_key in existing_keys:
                continue
            payload["tasks"].append(task.model_dump(mode="json"))
            existing_keys.add(task.idempotency_key)

    def _remaining_inr(self, payload: dict) -> float:
        spent = sum(float(entry.get("actual_cost_inr") or 0) for entry in payload["ledger"] if entry.get("status") == "reconciled")
        reserved = sum(float(entry.get("estimated_cost_inr") or 0) for entry in payload["ledger"] if entry.get("status") == "reserved")
        return max(0.0, float(payload.get("run_limit") or 0) - spent - reserved)

    def _ledger(self, payload: dict, spec: CampaignIntentSpec) -> BudgetLedger:
        return BudgetLedger(spec.tenant_id, spec.correlation_id, self._remaining_inr(payload))

    def _job_status(self, payload: dict) -> str:
        if payload.get("status") == "cancelled":
            return "cancelled"
        statuses = [task["status"] for task in payload["tasks"]]
        if any(status in {"succeeded", "empty", "unavailable", "blocked"} for status in statuses):
            return "succeeded"
        if statuses and all(status == "failed" for status in statuses):
            return "failed"
        return "succeeded"

    def _batch(self, payload: dict, spec: CampaignIntentSpec, resumed: bool) -> SearchBatch:
        tasks = [SearchTask.model_validate(task) for task in payload["tasks"]]
        records = [DiscoveryRecord.model_validate(row) for row in payload["records"]]
        candidates: list[QualifiedCandidate] = []
        qualified: list[QualifiedCandidate] = []
        rejected: list[QualifiedCandidate] = []
        from app.services.sales_os.search_v4.contracts import LeadEvidence, QualificationAssessment

        for record, scored in zip(records, payload.get("assessments") or []):
            evidence = LeadEvidence.model_validate(scored["evidence"])
            assessment = QualificationAssessment.model_validate(scored["assessment"])
            candidate = QualifiedCandidate(record=record, evidence=evidence, assessment=assessment)
            candidates.append(candidate)
            if assessment.decision == "accept":
                qualified.append(candidate)
            elif assessment.decision == "reject":
                rejected.append(candidate)
        parts = [f"{task.method}/{task.provider}:{task.status}" for task in tasks]
        from app.services.sales_os.search_v4.contracts import UsageLedgerEntry

        ledger = [UsageLedgerEntry.model_validate(row) for row in payload["ledger"]]
        spent = sum(entry.actual_cost_inr for entry in ledger if entry.status == "reconciled")
        report = ", ".join(parts) + f"; qualified={len(qualified)}; cost_inr={spent:.2f}"
        if payload.get("notes"):
            report += "; " + "; ".join(payload["notes"])
        return SearchBatch(
            job_id=payload["job_id"],
            correlation_id=spec.correlation_id,
            tenant_id=spec.tenant_id,
            status=payload.get("status") or "succeeded",
            tasks=tasks,
            records=records,
            candidates=candidates,
            qualified=qualified,
            rejected=rejected,
            ledger=ledger,
            report=report,
            resumed=resumed,
        )

    def _record_yield(self, payload: dict) -> None:
        if payload.get("yield_recorded"):
            return
        accepted_providers = set()
        for raw, scored in zip(payload["records"], payload.get("assessments") or []):
            if (scored.get("assessment") or {}).get("decision") == "accept":
                accepted_providers.add(raw.get("provider"))
        counted = set(payload.get("yield_task_ids") or [])
        for task in payload["tasks"]:
            if task["status"] not in {"succeeded", "empty"} or task["task_id"] in counted:
                continue
            qualified = 1 if task["provider"] in accepted_providers and task["status"] == "succeeded" else 0
            self.store.record_yield(task["provider"], qualified)
            counted.add(task["task_id"])
        payload["yield_task_ids"] = list(counted)
        payload["yield_recorded"] = True

    def _hit_dump(self, hit: Hit) -> dict:
        return {
            "url": hit.url,
            "title": hit.title,
            "snippet": hit.snippet,
            "page_excerpt": hit.page_excerpt,
            "provider_native_id": hit.provider_native_id,
            "company_name": hit.company_name,
            "company_domain": hit.company_domain,
            "contact_name": hit.contact_name,
            "contact_email": hit.contact_email,
        }
