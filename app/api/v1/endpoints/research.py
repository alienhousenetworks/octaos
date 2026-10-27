"""Tenant-scoped API for the shared OctaOS Search Intelligence engine."""
from __future__ import annotations

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


@router.post("/search", status_code=status.HTTP_200_OK)
async def run_research_search(
    request: ResearchSearchRequest,
    db: Session = Depends(deps.get_db),
    user: User = Depends(require_permission(Resource.SETTINGS, Action.READ)),
) -> dict[str, Any]:
    """Run a bounded, tenant-scoped search and persist its complete evidence record."""
    tenant_id = str(user.tenant_id or "")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="A tenant context is required.")
    _require_durable_search_store(db)
    service = EnterpriseWebResearchService(db=db, tenant_id=tenant_id)
    try:
        batch = await service.run(
            request.query,
            count=request.count,
            freshness=request.freshness,
            geography=request.geography,
            industries=request.industries,
            buyer_roles=request.buyer_roles,
            exclusions=request.exclusions,
            budget_inr=request.budget_inr,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        # Do not expose provider URLs, credentials, or raw upstream exception text.
        raise HTTPException(
            status_code=502,
            detail={"code": "RESEARCH_EXECUTION_FAILED", "message": "The research run could not be completed."},
        ) from exc

    result = EnterpriseWebResearchService.summarize(batch, count=request.count)
    result["tenant_id"] = tenant_id
    result["counts"] = {
        "tasks": len(batch.tasks),
        "sources": len(batch.records),
        "claims": len(batch.candidates),
        "qualified": len(batch.qualified),
        "rejected": len(batch.rejected),
    }
    result["usage"] = [entry.model_dump(mode="json") for entry in batch.ledger]
    result["notes"] = [
        task.reason for task in batch.tasks
        if task.reason and task.status in {"unavailable", "failed", "blocked"}
    ]
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
    service = EnterpriseWebResearchService(db=db, tenant_id=tenant_id)
    try:
        batch = await service.resume(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Research job not found.") from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "RESEARCH_RESUME_FAILED", "message": "The research job could not be resumed."},
        ) from exc
    result = EnterpriseWebResearchService.summarize(batch)
    result["counts"] = {
        "tasks": len(batch.tasks),
        "sources": len(batch.records),
        "claims": len(batch.candidates),
        "qualified": len(batch.qualified),
        "rejected": len(batch.rejected),
    }
    result["usage"] = [entry.model_dump(mode="json") for entry in batch.ledger]
    result["resumed"] = True
    return result


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
