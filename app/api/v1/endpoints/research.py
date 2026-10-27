"""Tenant-scoped API for the shared OctaOS Search Intelligence engine."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.core.rbac import Action, Resource, require_permission
from app.models.base import User
from app.models.search_v4 import SearchV4Job
from app.services.research import EnterpriseWebResearchService
from app.services.sales_os.search_v4.store import SqlSearchStore

router = APIRouter()


class ResearchSearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=300)
    count: int = Field(default=10, ge=1, le=100)
    freshness: Literal["24_hours", "7_days", "14_days", "30_days", "90_days", "all"] = "14_days"
    geography: list[str] = Field(default_factory=list, max_length=8)
    industries: list[str] = Field(default_factory=list, max_length=12)
    buyer_roles: list[str] = Field(default_factory=list, max_length=12)
    exclusions: list[str] = Field(default_factory=list, max_length=20)
    budget_inr: float = Field(default=100.0, ge=0, le=700)

    @classmethod
    def _clean_list(cls, values: list[str], limit: int, max_length: int = 100) -> list[str]:
        clean: list[str] = []
        seen: set[str] = set()
        for raw in values[:limit]:
            item = " ".join(str(raw or "").split())[:max_length]
            key = item.casefold()
            if item and key not in seen:
                clean.append(item)
                seen.add(key)
        return clean

    def model_post_init(self, __context: Any) -> None:
        self.query = " ".join(self.query.split())
        self.geography = self._clean_list(self.geography, 8, 80)
        self.industries = self._clean_list(self.industries, 12, 100)
        self.buyer_roles = self._clean_list(self.buyer_roles, 12, 100)
        self.exclusions = self._clean_list(self.exclusions, 20, 100)


def _require_durable_search_store(db: Session) -> SqlSearchStore:
    try:
        store = SqlSearchStore(db)
        if store.available():
            return store
    except Exception:
        pass
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "SEARCH_STORAGE_UNAVAILABLE",
            "message": "Durable search storage is not available. Apply the repository migrations before running research.",
        },
    )


def _public_job(payload: dict[str, Any]) -> dict[str, Any]:
    spec = payload.get("spec") or {}
    raw_records = payload.get("records") or []
    raw_assessments = payload.get("assessments") or []
    sources: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    for index, record in enumerate(raw_records):
        sources.append({
            "record_id": record.get("record_id"),
            "title": record.get("title") or "",
            "url": record.get("original_url") or "",
            "canonical_url": record.get("canonical_url") or "",
            "snippet": record.get("snippet") or "",
            "excerpt": (record.get("page_excerpt") or "")[:1200],
            "provider": record.get("provider") or "",
            "method": record.get("method") or "",
            "published_at": record.get("published_at"),
            "retrieved_at": record.get("retrieved_at"),
            "company": record.get("company_name") or record.get("company_domain") or "",
        })
        assessment = raw_assessments[index] if index < len(raw_assessments) else {}
        evidence = assessment.get("evidence") or {}
        if evidence:
            claims.append({
                "record_id": record.get("record_id"),
                "claim": evidence.get("claim") or "",
                "passage": evidence.get("passage") or "",
                "source_url": evidence.get("source_url") or record.get("original_url") or "",
                "verification_state": evidence.get("verification_state") or "UNVERIFIED",
                "freshness_ok": evidence.get("freshness_ok"),
                "notes": evidence.get("notes") or [],
            })
    tasks = [
        {
            "task_id": task.get("task_id"),
            "method": task.get("method"),
            "provider": task.get("provider"),
            "operation": task.get("operation"),
            "query": task.get("query"),
            "status": task.get("status"),
            "reason": task.get("reason"),
            "failure_class": task.get("failure_class"),
            "attempt": task.get("attempt", 0),
        }
        for task in payload.get("tasks") or []
    ]
    return {
        "job_id": payload.get("job_id"),
        "status": payload.get("status") or "unknown",
        "query": spec.get("query") or "",
        "freshness": spec.get("freshness") or "",
        "geography": spec.get("geography") or [],
        "tasks": tasks,
        "sources": sources,
        "claims": claims,
        "usage": payload.get("ledger") or [],
        "notes": payload.get("notes") or [],
        "expansion_round": payload.get("expansion_round", 0),
        "report": ", ".join(f"{t.get('method')}/{t.get('provider')}:{t.get('status')}" for t in tasks),
        "counts": {
            "tasks": len(tasks),
            "sources": len(sources),
            "claims": len(claims),
            "succeeded": sum(1 for task in tasks if task.get("status") in {"succeeded", "empty"}),
            "failed": sum(1 for task in tasks if task.get("status") in {"failed", "blocked", "unavailable"}),
        },
    }


@router.post("/search", status_code=status.HTTP_202_ACCEPTED)
async def run_research_search(
    request: ResearchSearchRequest,
    db: Session = Depends(deps.get_db),
    user: User = Depends(require_permission(Resource.SETTINGS, Action.READ)),
) -> dict[str, Any]:
    """Queue a bounded search after persisting its tenant-scoped job record."""
    tenant_id = str(user.tenant_id or "")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="A tenant context is required.")
    _require_durable_search_store(db)

    job_id = str(uuid4())
    geographies = request.geography or list(EnterpriseWebResearchService.DEFAULT_GEOGRAPHIES)
    spec = {
        "campaign_id": "research-" + job_id,
        "correlation_id": str(uuid4()),
        "tenant_id": tenant_id,
        "query": request.query,
        "freshness": request.freshness,
        "geography": geographies,
        "industries": request.industries,
        "buyer_roles": request.buyer_roles,
        "exclusions": request.exclusions,
        "budget_inr": request.budget_inr,
        "monthly_limit_inr": request.budget_inr,
    }
    queue_task_id = str(uuid4())
    payload: dict[str, Any] = {
        "job_id": job_id,
        "queue_task_id": queue_task_id,
        "status": "queued",
        "spec": spec,
        "tasks": [],
        "records": [],
        "assessments": [],
        "ledger": [],
        "notes": ["Research is queued for the existing OctaOS background worker."],
        "expansion_done": False,
        "expansion_round": 0,
        "max_expansion_rounds": 3,
        "suppressed_domains": [],
        "run_limit": request.budget_inr,
        "requested_count": request.count,
    }
    row = SearchV4Job(id=job_id, tenant_id=tenant_id, status="queued", payload=payload)
    db.add(row)
    db.commit()

    options = {
        "freshness": request.freshness,
        "geography": geographies,
        "industries": request.industries,
        "buyer_roles": request.buyer_roles,
        "exclusions": request.exclusions,
        "budget_inr": request.budget_inr,
    }
    try:
        from app.worker.tasks import run_research_search_task

        run_research_search_task.apply_async(
            args=[tenant_id, job_id, request.query, options, False],
            task_id=queue_task_id,
        )
    except Exception as exc:
        db.rollback()
        row = db.query(SearchV4Job).filter(
            SearchV4Job.id == job_id,
            SearchV4Job.tenant_id == tenant_id,
        ).first()
        if row is not None:
            failed_payload = dict(row.payload or {})
            failed_payload["status"] = "unavailable"
            failed_payload["error_code"] = "RESEARCH_QUEUE_UNAVAILABLE"
            failed_payload["notes"] = ["The background worker could not accept this research job."]
            row.payload = failed_payload
            row.status = "unavailable"
            db.commit()
        raise HTTPException(
            status_code=503,
            detail={"code": "RESEARCH_QUEUE_UNAVAILABLE", "message": "The research worker is unavailable. The job was not started."},
        ) from exc

    row = db.query(SearchV4Job).filter(
        SearchV4Job.id == job_id,
        SearchV4Job.tenant_id == tenant_id,
    ).first()
    result = _public_job(row.payload or {}) if row is not None else {
        "job_id": job_id,
        "status": "queued",
        "query": request.query,
    }
    result["requested_count"] = request.count
    result["status_url"] = f"/research/jobs/{job_id}"
    return result


@router.get("/jobs")
def list_research_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(deps.get_db),
    user: User = Depends(require_permission(Resource.SETTINGS, Action.READ)),
) -> dict[str, Any]:
    tenant_id = str(user.tenant_id or "")
    _require_durable_search_store(db)
    rows = (
        db.query(SearchV4Job)
        .filter(SearchV4Job.tenant_id == tenant_id)
        .order_by(SearchV4Job.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "items": [
            {
                "job_id": row.id,
                "status": row.status,
                "query": (row.payload or {}).get("spec", {}).get("query", ""),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "source_count": len((row.payload or {}).get("records") or []),
                "task_count": len((row.payload or {}).get("tasks") or []),
            }
            for row in rows
        ]
    }


@router.get("/jobs/{job_id}")
def get_research_job(
    job_id: str,
    db: Session = Depends(deps.get_db),
    user: User = Depends(require_permission(Resource.SETTINGS, Action.READ)),
) -> dict[str, Any]:
    tenant_id = str(user.tenant_id or "")
    _require_durable_search_store(db)
    row = (
        db.query(SearchV4Job)
        .filter(SearchV4Job.id == job_id, SearchV4Job.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Research job not found.")
    result = _public_job(row.payload or {})
    result["created_at"] = row.created_at.isoformat() if row.created_at else None
    result["updated_at"] = row.updated_at.isoformat() if row.updated_at else None
    return result


@router.post("/jobs/{job_id}/resume")
async def resume_research_job(
    job_id: str,
    db: Session = Depends(deps.get_db),
    user: User = Depends(require_permission(Resource.SETTINGS, Action.READ)),
) -> dict[str, Any]:
    """Resume a persisted run after a worker/process interruption."""
    tenant_id = str(user.tenant_id or "")
    _require_durable_search_store(db)
    row = (
        db.query(SearchV4Job)
        .filter(SearchV4Job.id == job_id, SearchV4Job.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Research job not found.")
    if row.status not in {"running", "failed"}:
        raise HTTPException(
            status_code=409,
            detail=f"Research job cannot be resumed from status '{row.status}'.",
        )
    if row.status == "running" and row.updated_at:
        last_update = row.updated_at
        if last_update.tzinfo is None:
            last_update = last_update.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - last_update < timedelta(minutes=2):
            raise HTTPException(
                status_code=409,
                detail="This research job was updated recently and may still be running. Wait before attempting recovery.",
            )
    payload = dict(row.payload or {})
    query = str((payload.get("spec") or {}).get("query") or "")
    if not query:
        raise HTTPException(status_code=409, detail="Research job has no recoverable request specification.")
    queue_task_id = str(uuid4())
    payload["status"] = "queued"
    payload["queue_task_id"] = queue_task_id
    payload["notes"] = list(payload.get("notes") or []) + ["Recovery was queued for the background worker."]
    previous_status = row.status
    updated_rows = (
        db.query(SearchV4Job)
        .filter(
            SearchV4Job.id == job_id,
            SearchV4Job.tenant_id == tenant_id,
            SearchV4Job.status == previous_status,
        )
        .update(
            {"payload": payload, "status": "queued"},
            synchronize_session=False,
        )
    )
    db.commit()
    if updated_rows != 1:
        raise HTTPException(status_code=409, detail="Research job changed while recovery was requested. Reload and retry.")
    try:
        from app.worker.tasks import run_research_search_task

        run_research_search_task.apply_async(
            args=[tenant_id, job_id, query, {}, True],
            task_id=queue_task_id,
        )
    except Exception as exc:
        db.rollback()
        row = db.query(SearchV4Job).filter(
            SearchV4Job.id == job_id,
            SearchV4Job.tenant_id == tenant_id,
        ).first()
        if row is not None:
            failed_payload = dict(row.payload or {})
            failed_payload["status"] = "failed"
            failed_payload["error_code"] = "RESEARCH_QUEUE_UNAVAILABLE"
            row.payload = failed_payload
            row.status = "failed"
            db.commit()
        raise HTTPException(
            status_code=503,
            detail={"code": "RESEARCH_QUEUE_UNAVAILABLE", "message": "The research worker could not resume this job."},
        ) from exc
    return {
        "job_id": job_id,
        "status": "queued",
        "query": query,
        "resumed": True,
        "status_url": f"/research/jobs/{job_id}",
    }


@router.get("/providers")
def get_research_providers(
    db: Session = Depends(deps.get_db),
    user: User = Depends(require_permission(Resource.SETTINGS, Action.READ)),
) -> dict[str, Any]:
    """Return configuration state only; this endpoint does not claim live health."""
    tenant_id = str(user.tenant_id or "")
    service = EnterpriseWebResearchService(db=db, tenant_id=tenant_id)
    try:
        credentials = service._credentials()
    except Exception:
        credentials = {}
    return {
        "providers": [
            {"id": "duckduckgo", "configured": True, "state": "fallback_available", "health": "not_checked"},
            {"id": "brave", "configured": bool(credentials.get("brave_search")), "state": "configured" if credentials.get("brave_search") else "not_configured", "health": "not_checked"},
            {"id": "tavily", "configured": bool(credentials.get("tavily")), "state": "configured" if credentials.get("tavily") else "not_configured", "health": "not_checked"},
            {"id": "reddit", "configured": bool(credentials.get("reddit")), "state": "configured" if credentials.get("reddit") else "not_configured", "health": "not_checked"},
            {"id": "x", "configured": bool(credentials.get("x_search")), "state": "configured" if credentials.get("x_search") else "not_configured", "health": "not_checked"},
        ]
    }
