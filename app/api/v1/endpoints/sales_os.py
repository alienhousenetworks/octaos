"""Account-first sales intelligence. Discovery stays planned until execute is true."""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.models.sales_intelligence import SalesOpportunity, SalesSignal, SignalEvidence, SourceCost, SourceRun
from app.services.sales_os.attribution.source_roi import summarize_roi
from app.services.sales_os.discovery.source_registry import get_all_source_ids
from app.services.sales_os.governance.suppression import SuppressionService
from app.services.sales_os.orchestration.credentials import configured_providers, provider_secrets
from app.services.sales_os.orchestration.sales_pipeline import SalesPipeline
from app.services.sales_os.orchestration.store import SalesIntelligenceStore
from app.services.sales_os.providers.registry import describe_all

router = APIRouter(dependencies=[Depends(deps.check_access("sales"))])


class DiscoveryRequest(BaseModel):
    query: str
    provider_keys: Optional[list[str]] = None
    budget: Optional[float] = None
    execute: bool = False
    enqueue: bool = False
    profile: Optional[dict] = None


class EnrichRequest(BaseModel):
    provider_keys: list[str] = Field(default_factory=list)
    budget: Optional[float] = None
    execute: bool = False
    profile: Optional[dict] = None


class VerifyRequest(BaseModel):
    suppressed: bool = False
    suppression_reason: Optional[str] = None
    permission_state: str = "unknown"
    jurisdiction: Optional[str] = None
    legal_basis: Optional[str] = None
    employment_current: Optional[bool] = None
    verifier_result: Optional[dict] = None


class SuppressionRequest(BaseModel):
    identifier_type: str
    identifier_value: str
    reason: str
    origin: str = "user"
    notes: Optional[str] = None
    channel: Optional[str] = None
    jurisdiction: Optional[str] = None
    scope: str = "tenant"
    expires_days: Optional[int] = None


class OutcomeRequest(BaseModel):
    provider_key: str
    outcome_type: str
    company_id: Optional[str] = None
    contact_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    lead_id: Optional[str] = None
    amount: Optional[float] = None
    touch_role: str = "unknown"


def _iso(value) -> str | None:
    return value.isoformat() if value else None


def _run_dict(run: SourceRun) -> dict:
    return {
        "id": run.id,
        "status": run.status,
        "query": run.query,
        "trigger": run.trigger,
        "counts": run.counts or {},
        "error_summary": run.error_summary,
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.finished_at),
    }


def _signal_dict(row: SalesSignal) -> dict:
    return {
        "id": row.id,
        "signal_type": row.signal_type,
        "family": row.family,
        "base_strength": row.base_strength,
        "source_confidence": row.source_confidence,
        "half_life_days": row.half_life_days,
        "observed_at": _iso(row.observed_at),
        "retrieved_at": _iso(row.retrieved_at),
        "source_key": row.source_key,
        "independent_key": row.independent_key,
        "summary": row.summary,
        "payload_hash": row.payload_hash,
        "evidence_id": row.evidence_id,
        "is_inferred": bool(row.is_inferred),
    }


def _evidence_dict(row: SignalEvidence) -> dict:
    return {
        "id": row.id,
        "source_key": row.source_key,
        "source_url": row.source_url,
        "claim": row.claim,
        "excerpt": row.excerpt,
        "payload_hash": row.payload_hash,
        "confidence": row.confidence,
        "license_class": row.license_class,
        "observed_at": _iso(row.observed_at),
        "retrieved_at": _iso(row.retrieved_at),
    }


def _opportunity_dict(row: SalesOpportunity) -> dict:
    return {
        "id": row.id,
        "company_id": row.company_id,
        "stage": row.stage,
        "score": row.score,
        "component_scores": row.component_scores or {},
        "explanation": row.explanation or {},
        "rationale": row.rationale,
        "score_version": row.score_version,
        "config_hash": row.config_hash,
        "tier6_state": row.tier6_state,
        "confidence": row.confidence,
        "evidence_ids": row.evidence_ids or [],
    }


def _keys(requested: list[str] | None) -> list[str]:
    return requested if requested else get_all_source_ids()


@router.post("/discovery/runs")
async def create_discovery_run(
    body: DiscoveryRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    keys = _keys(body.provider_keys)
    credentialed = configured_providers(db, tenant_id)
    if body.enqueue:
        from app.workers.sales_os.discovery import run_sales_os_discovery_task

        task = run_sales_os_discovery_task.delay(
            tenant_id,
            body.query,
            keys,
            body.budget,
            body.execute,
            body.profile,
        )
        return {"status": "queued", "task_id": task.id, "execute": body.execute}
    secrets = provider_secrets(db, tenant_id, set(keys) & credentialed) if body.execute else {}
    pipeline = SalesPipeline(db, tenant_id)
    return await pipeline.run(
        query=body.query,
        provider_keys=keys,
        credentialed=credentialed,
        credentials=secrets,
        profile=body.profile,
        budget=body.budget,
        execute=body.execute,
    )


@router.get("/discovery/runs")
def list_discovery_runs(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    limit: int = 20,
) -> Any:
    rows = (
        db.query(SourceRun)
        .filter(SourceRun.tenant_id == tenant_id)
        .order_by(SourceRun.created_at.desc())
        .limit(min(limit, 100))
        .all()
    )
    return [_run_dict(row) for row in rows]


@router.get("/discovery/runs/{run_id}")
def get_discovery_run(
    run_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    row = db.query(SourceRun).filter(SourceRun.id == run_id, SourceRun.tenant_id == tenant_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Discovery run not found")
    return _run_dict(row)


@router.get("/companies")
def list_companies(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    limit: int = 100,
) -> Any:
    store = SalesIntelligenceStore(db, tenant_id)
    rows = []
    for company in store.list_companies(limit=min(limit, 200)):
        opportunity = store.latest_opportunity(company.id)
        item = store.company_dict(company)
        item["tier6_state"] = opportunity.tier6_state if opportunity else None
        item["score"] = opportunity.score if opportunity else None
        item["score_version"] = opportunity.score_version if opportunity else None
        rows.append(item)
    return rows


@router.get("/companies/{company_id}")
def get_company(
    company_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    store = SalesIntelligenceStore(db, tenant_id)
    company = store.get_company(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return store.company_dict(company)


@router.get("/companies/{company_id}/signals")
def list_signals(
    company_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    store = SalesIntelligenceStore(db, tenant_id)
    if store.get_company(company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return [_signal_dict(row) for row in store.list_signals(company_id)]


@router.get("/companies/{company_id}/evidence")
def list_evidence(
    company_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    store = SalesIntelligenceStore(db, tenant_id)
    if store.get_company(company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return [_evidence_dict(row) for row in store.list_evidence(company_id)]


@router.get("/companies/{company_id}/opportunity")
def get_opportunity(
    company_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    store = SalesIntelligenceStore(db, tenant_id)
    if store.get_company(company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    opportunity = store.latest_opportunity(company_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return _opportunity_dict(opportunity)


@router.post("/companies/{company_id}/enrich")
async def enrich_company(
    company_id: str,
    body: EnrichRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    credentialed = configured_providers(db, tenant_id)
    pipeline = SalesPipeline(db, tenant_id)
    try:
        if body.execute:
            secrets = provider_secrets(db, tenant_id, set(body.provider_keys) & credentialed)
            return await pipeline.execute_enrichment(
                company_id, body.provider_keys, body.budget, credentialed, secrets, body.profile
            )
        return pipeline.enrich_contacts(company_id, body.provider_keys, body.budget, credentialed, body.profile)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/contacts/{contact_id}/verify")
def verify_contact(
    contact_id: str,
    body: VerifyRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    pipeline = SalesPipeline(db, tenant_id)
    try:
        return pipeline.verify_contact(
            contact_id,
            suppressed=body.suppressed,
            suppression_reason=body.suppression_reason,
            permission_state=body.permission_state,
            jurisdiction=body.jurisdiction,
            legal_basis=body.legal_basis,
            verifier_result=body.verifier_result,
            employment_current=body.employment_current,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sources")
def list_sources(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    return describe_all(configured_providers(db, tenant_id))


@router.get("/sources/health")
def source_health(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    rows = describe_all(configured_providers(db, tenant_id))
    by_activation: dict[str, int] = {}
    by_implementation: dict[str, int] = {}
    for row in rows:
        by_activation[row["activation_status"]] = by_activation.get(row["activation_status"], 0) + 1
        by_implementation[row["implementation"]] = by_implementation.get(row["implementation"], 0) + 1
    return {
        "sources": len(rows),
        "sales_os_callable": sum(1 for row in rows if row["sales_os_callable"]),
        "by_activation": by_activation,
        "by_implementation": by_implementation,
    }


@router.get("/sources/costs")
def source_costs(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    rows = db.query(SourceCost).filter(SourceCost.tenant_id == tenant_id).all()
    return [
        {
            "id": row.id,
            "provider_key": row.provider_key,
            "operation": row.operation,
            "currency": row.currency,
            "estimated_amount": row.estimated_amount,
            "actual_amount": row.actual_amount,
            "credits": row.credits,
        }
        for row in rows
    ]


@router.get("/attribution/roi")
def attribution_roi(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    store = SalesIntelligenceStore(db, tenant_id)
    costs = [
        {
            "provider_key": row.provider_key,
            "estimated_amount": row.estimated_amount,
            "actual_amount": row.actual_amount,
        }
        for row in store.list_costs()
    ]
    outcomes = [
        {
            "provider_key": row.provider_key,
            "outcome_type": row.outcome_type,
            "amount": row.amount,
            "touch_role": row.touch_role,
        }
        for row in store.list_outcomes()
    ]
    return summarize_roi(costs, outcomes)


@router.post("/suppressions")
def add_suppression(
    body: SuppressionRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    record = SuppressionService(db, tenant_id).add_suppression(
        body.identifier_type,
        body.identifier_value,
        body.reason,
        origin=body.origin,
        notes=body.notes,
        expires_days=body.expires_days,
        channel=body.channel,
        jurisdiction=body.jurisdiction,
        scope=body.scope,
    )
    return {
        "id": record.id,
        "identifier_type": record.identifier_type,
        "identifier_value": record.identifier_value,
        "reason": record.reason,
        "channel": record.channel,
        "jurisdiction": record.jurisdiction,
        "scope": record.scope,
    }


@router.post("/outcomes")
def add_outcome(
    body: OutcomeRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    store = SalesIntelligenceStore(db, tenant_id)
    row = store.add_outcome(body.model_dump())
    db.commit()
    return {
        "id": row.id,
        "provider_key": row.provider_key,
        "outcome_type": row.outcome_type,
        "amount": row.amount,
        "touch_role": row.touch_role,
        "attribution_is_causal": False,
    }


@router.post("/leads/backfill")
def backfill_leads(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    store = SalesIntelligenceStore(db, tenant_id)
    result = store.backfill_leads()
    db.commit()
    return result
