from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Any, List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.api import deps
from app.core.rbac import Action, Resource, require_permission
from app.models.base import User
from app.models.workflows import Workflow, WorkflowTask
from app.services.agents.ceo import CEOService
from app.core.celery_app import celery_app
from app.api.v1.endpoints.ceo_v5 import router as ceo_v5_router

router = APIRouter()
router.include_router(ceo_v5_router, prefix="", tags=["ceo-v5"])
router.include_router(ceo_v5_router, prefix="/v5", tags=["ceo-v5"])

class ObjectiveRequest(BaseModel):
    prompt: str
    provider: Optional[str] = "gemini"
    model: Optional[str] = None

class TaskResponse(BaseModel):
    id: str
    workflow_id: str
    name: str
    task_type: str
    status: str
    payload: Optional[dict] = None
    result: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class WorkflowResponse(BaseModel):
    id: str
    name: str
    vertical: str
    status: str
    created_at: datetime
    tasks: List[TaskResponse]

    class Config:
        from_attributes = True


@router.get("/workflows", response_model=List[WorkflowResponse])
def get_ceo_workflows(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    workflows = db.query(Workflow).filter(
        Workflow.tenant_id == tenant_id,
        Workflow.vertical.in_(["CEO", "EXECUTIVE"])
    ).order_by(Workflow.created_at.desc()).all()
    return workflows

@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
def get_ceo_workflow_details(
    workflow_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.tenant_id == tenant_id,
        Workflow.vertical.in_(["CEO", "EXECUTIVE"])
    ).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="CEO Strategy Workflow not found")
    return workflow

@router.delete("/workflows/{workflow_id}")
def delete_ceo_workflow(
    workflow_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    from app.services.executive_os.ceo_interactive_orchestrator import CEOInteractiveOrchestrator
    orchestrator = CEOInteractiveOrchestrator(db, tenant_id)
    success = orchestrator.delete_workspace(workflow_id)
    return {"status": "DELETED", "workflow_id": workflow_id, "success": success}

@router.post("/plan", response_model=WorkflowResponse)
async def generate_ceo_plan(
    payload: ObjectiveRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Objective prompt cannot be empty.")
    
    service = CEOService(db, tenant_id)
    try:
        workflow = await service.generate_plan(
            objective=payload.prompt,
            provider=payload.provider,
            model=payload.model
        )
        return workflow
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate CEO plan: {str(e)}")

@router.post("/run/{workflow_id}")
async def run_ceo_workflow(
    workflow_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.tenant_id == tenant_id,
        Workflow.vertical == "CEO"
    ).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="CEO Strategy Workflow not found")

    if workflow.status == "executing":
        return {"status": "already_running", "message": "Workflow is already executing."}

    # Trigger async Celery task or FastAPI background task
    try:
        celery_app.send_task("run_ceo_workflow_task", args=[tenant_id, workflow.id])
        return {"status": "queued", "message": "Growth strategy execution plan has been queued in background worker."}
    except Exception as e:
        print(f"Failed to queue Celery task, running in FastAPI background task: {e}")
        service = CEOService(db, tenant_id)
        background_tasks.add_task(service.execute_workflow, workflow.id)
        return {"status": "started", "message": "Growth strategy execution plan started in FastAPI thread."}


# ==============================================================================
# Business Autonomy & Control Plane — Objective & Outcome Management Endpoints
# ==============================================================================

class ObjectiveCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    department: Optional[str] = None
    target_metric: str
    baseline_value: float
    target_value: float
    current_value: Optional[float] = None
    unit: str = "percent"
    priority: int = 1
    budget_limit: float = 10000.0
    deadline: datetime
    constraints: Optional[dict] = None
    success_criteria: Optional[List[dict]] = None


class ObjectiveMetricCreateRequest(BaseModel):
    measured_value: float
    budget_spent_to_date: float = 0.0
    evidence_source: Optional[str] = None
    evidence_reference_id: Optional[str] = None
    variance_pct: Optional[float] = None


@router.get("/objectives")
def list_objectives(
    status: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    from app.models.objectives import BusinessObjective
    query = db.query(BusinessObjective).filter(BusinessObjective.tenant_id == tenant_id)
    if status and status.upper() != "ALL":
        query = query.filter(BusinessObjective.status == status.upper())
    if department and department.upper() != "ALL":
        query = query.filter(BusinessObjective.department == department)
    
    objectives = query.order_by(BusinessObjective.priority.asc(), BusinessObjective.created_at.desc()).all()
    results = []
    for obj in objectives:
        # Calculate dynamic health score
        target_diff = abs(obj.target_value - obj.baseline_value)
        actual_progress = abs(obj.current_value - obj.baseline_value)
        progress_pct = round((actual_progress / target_diff) * 100, 1) if target_diff > 0 else 0.0
        
        budget_limit = float(obj.budget_limit or 0)
        consumed_budget = float(obj.consumed_budget or 0)
        budget_util_pct = round((consumed_budget / budget_limit) * 100, 1) if budget_limit > 0 else 0.0

        health = "ON_TRACK"
        if budget_util_pct > 90 and progress_pct < 70:
            health = "AT_RISK"
        elif progress_pct < 30 and obj.status == "ACTIVE":
            health = "NEEDS_ATTENTION"

        results.append({
            "id": obj.id,
            "version": obj.version,
            "title": obj.title,
            "description": obj.description,
            "department": obj.department,
            "owner_user_id": obj.owner_user_id,
            "target_metric": obj.target_metric,
            "baseline_value": obj.baseline_value,
            "target_value": obj.target_value,
            "current_value": obj.current_value,
            "unit": obj.unit,
            "priority": obj.priority,
            "budget_limit": budget_limit,
            "consumed_budget": consumed_budget,
            "budget_utilization_pct": budget_util_pct,
            "progress_pct": min(progress_pct, 100.0),
            "health": health,
            "deadline": obj.deadline.isoformat() if obj.deadline else None,
            "status": obj.status,
            "constraints": obj.constraints,
            "success_criteria": obj.success_criteria,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
        })
    return results


@router.post("/objectives")
def create_objective(
    payload: ObjectiveCreateRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    from app.models.objectives import BusinessObjective
    from decimal import Decimal
    
    obj = BusinessObjective(
        tenant_id=tenant_id,
        version=1,
        title=payload.title,
        description=payload.description,
        department=payload.department,
        owner_user_id=current_user.id if current_user else "user-executive",
        target_metric=payload.target_metric,
        baseline_value=payload.baseline_value,
        target_value=payload.target_value,
        current_value=payload.current_value if payload.current_value is not None else payload.baseline_value,
        unit=payload.unit,
        priority=payload.priority,
        budget_limit=Decimal(str(payload.budget_limit)),
        consumed_budget=Decimal("0.00"),
        deadline=payload.deadline,
        status="ACTIVE",
        constraints=payload.constraints or {},
        success_criteria=payload.success_criteria or [],
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {
        "status": "CREATED",
        "objective_id": obj.id,
        "title": obj.title,
        "message": f"Business objective '{obj.title}' created as active commitment."
    }


@router.get("/objectives/{objective_id}")
def get_objective_details(
    objective_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    from app.models.objectives import BusinessObjective
    obj = db.query(BusinessObjective).filter(
        BusinessObjective.id == objective_id,
        BusinessObjective.tenant_id == tenant_id
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")
    
    metrics = [{
        "id": m.id,
        "measured_value": m.measured_value,
        "budget_spent_to_date": float(m.budget_spent_to_date or 0),
        "evidence_source": m.evidence_source,
        "evidence_reference_id": m.evidence_reference_id,
        "variance_pct": m.variance_pct,
        "recorded_at": m.recorded_at.isoformat() if m.recorded_at else None,
    } for m in obj.metric_snapshots]

    plans = [{
        "id": p.id,
        "version_num": p.version_num,
        "strategy_variant": p.strategy_variant,
        "status": p.status,
        "estimated_budget": float(p.estimated_budget or 0),
        "executive_summary": p.executive_summary,
    } for p in obj.plans]

    return {
        "id": obj.id,
        "title": obj.title,
        "description": obj.description,
        "department": obj.department,
        "owner_user_id": obj.owner_user_id,
        "target_metric": obj.target_metric,
        "baseline_value": obj.baseline_value,
        "target_value": obj.target_value,
        "current_value": obj.current_value,
        "unit": obj.unit,
        "priority": obj.priority,
        "budget_limit": float(obj.budget_limit or 0),
        "consumed_budget": float(obj.consumed_budget or 0),
        "deadline": obj.deadline.isoformat() if obj.deadline else None,
        "status": obj.status,
        "constraints": obj.constraints,
        "success_criteria": obj.success_criteria,
        "metrics": metrics,
        "linked_plans": plans,
    }


@router.post("/objectives/{objective_id}/metrics")
def record_objective_metric(
    objective_id: str,
    payload: ObjectiveMetricCreateRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    from app.models.objectives import BusinessObjective, ObjectiveMetric
    from decimal import Decimal
    obj = db.query(BusinessObjective).filter(
        BusinessObjective.id == objective_id,
        BusinessObjective.tenant_id == tenant_id
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")

    variance = payload.variance_pct
    if variance is None and obj.target_value:
        variance = round((payload.measured_value - obj.target_value) / obj.target_value, 4)

    snapshot = ObjectiveMetric(
        tenant_id=tenant_id,
        objective_id=obj.id,
        measured_value=payload.measured_value,
        budget_spent_to_date=Decimal(str(payload.budget_spent_to_date)),
        evidence_source=payload.evidence_source,
        evidence_reference_id=payload.evidence_reference_id,
        variance_pct=variance or 0.0,
    )
    db.add(snapshot)
    
    # Update objective current progress
    obj.current_value = payload.measured_value
    if payload.budget_spent_to_date:
        obj.consumed_budget = Decimal(str(payload.budget_spent_to_date))
    db.commit()
    return {"status": "RECORDED", "current_value": obj.current_value, "variance_pct": variance}
