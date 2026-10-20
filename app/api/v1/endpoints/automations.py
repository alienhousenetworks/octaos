"""
OctaOS Enterprise Automation Platform API Endpoints.
Provides natural-language creation, workflow management, connection status,
execution observability, and secure visual canvas launcher.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.core.rbac import Action, Resource, require_permission
from app.models.base import User
from app.models.automations import (
    AutomationWorkflow,
    AutomationWorkflowVersion,
    AutomationExecution,
    AutomationTenantEnvironment,
)
from app.services.automation.base import AutomationIR, WorkflowStatus
from app.services.automation.ai_service import AIAutomationService
from app.services.automation.factory import get_automation_engine
from app.services.automation.templates import ENTERPRISE_TEMPLATES
from app.services.automation.event_bridge import AutomationEventBridge
from app.schemas.automation.graph import (
    AutomationGraph,
    convert_graph_to_legacy_ir,
    convert_legacy_ir_to_graph,
)
from app.services.automation.graph_validator import GraphValidator
from app.services.automation.compiler import FlowCompiler

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Pydantic Request & Response Schemas ─────────────────────────────────────

class GenerateAutomationRequest(BaseModel):
    prompt: str = Field(..., description="Natural language intent describing what to automate")
    category: str = Field("operations", description="sales | support | marketing | operations | executive")
    provider: Optional[str] = None
    model: Optional[str] = None


class CreateAutomationRequest(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    category: str = "operations"
    definition_ir: Dict[str, Any]
    activate_now: bool = False
    ai_prompt: Optional[str] = None


class ToggleActiveRequest(BaseModel):
    active: bool


class ManualRunRequest(BaseModel):
    payload: Optional[Dict[str, Any]] = None


class TestEventDispatchRequest(BaseModel):
    event_type: str = Field(..., description="e.g. lead.qualified, ticket.escalated")
    payload: Dict[str, Any] = Field(default_factory=dict)


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("")
def list_automations(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    category: Optional[str] = None,
) -> Any:
    """Lists all enterprise automations configured for the tenant."""
    query = db.query(AutomationWorkflow).filter_by(tenant_id=tenant_id)
    if category and category != "all":
        query = query.filter_by(category=category)

    workflows = query.order_by(AutomationWorkflow.created_at.desc()).all()
    results = []

    for wf in workflows:
        runs_count = db.query(AutomationExecution).filter_by(workflow_id=wf.id).count()
        last_run = (
            db.query(AutomationExecution)
            .filter_by(workflow_id=wf.id)
            .order_by(AutomationExecution.created_at.desc())
            .first()
        )
        steps_count = len(wf.definition_ir.get("steps", [])) if isinstance(wf.definition_ir, dict) else 0

        results.append({
            "id": wf.id,
            "name": wf.name,
            "slug": wf.slug,
            "description": wf.description,
            "category": wf.category,
            "status": wf.status,
            "engine_type": wf.engine_type,
            "trigger_type": wf.trigger_type,
            "trigger_event": wf.trigger_event,
            "steps_count": steps_count,
            "total_runs": runs_count,
            "last_run_status": last_run.status if last_run else None,
            "last_run_at": last_run.created_at.isoformat() if last_run and last_run.created_at else None,
            "is_ai_generated": wf.is_ai_generated,
            "requires_approval": wf.requires_approval,
            "risk_level": wf.risk_level,
            "created_at": wf.created_at.isoformat() if wf.created_at else None,
        })

    return results


@router.get("/templates")
def list_templates() -> Any:
    """Returns the library of battle-tested enterprise automation blueprints."""
    return ENTERPRISE_TEMPLATES


@router.get("/connections")
async def list_connections(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """
    Returns connection statuses in the Connection Center without leaking credentials.
    """
    adapter = get_automation_engine(tenant_id, db)
    connections = await adapter.list_connections(tenant_id)
    return [c.model_dump() for c in connections]


@router.get("/usage")
def get_automation_usage(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """Returns automation metering and plan limit consumption."""
    env = db.query(AutomationTenantEnvironment).filter_by(tenant_id=tenant_id).first()
    active_count = db.query(AutomationWorkflow).filter_by(tenant_id=tenant_id, status="active").count()
    total_count = db.query(AutomationWorkflow).filter_by(tenant_id=tenant_id).count()
    executions_count = db.query(AutomationExecution).filter_by(tenant_id=tenant_id).count()
    failed_count = db.query(AutomationExecution).filter_by(tenant_id=tenant_id, status="failed").count()

    limit_monthly = env.execution_limit_monthly if env else 5000
    wf_limit = env.workflow_limit if env else 50

    return {
        "active_workflows": active_count,
        "total_workflows": total_count,
        "workflow_limit": wf_limit,
        "executions_this_month": executions_count,
        "execution_limit_monthly": limit_monthly,
        "failed_executions": failed_count,
        "success_rate": round(((executions_count - failed_count) / max(executions_count, 1)) * 100, 1),
        "engine": env.engine_type if env else "activepieces",
        "subdomain": env.subdomain if env else f"tenant-{tenant_id[:8]}.flows.octaos.org",
        "status": env.status if env else "active",
    }


@router.post("/generate")
async def generate_automation(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.SETTINGS, Action.CREATE)),
    request: GenerateAutomationRequest,
) -> Any:
    """
    AI Prompt-to-Automation generator with Multi-Gate Governance validation.
    Generates draft Intermediate Representation (IR) without mutating production.
    """
    try:
        service = AIAutomationService(db, tenant_id)
        ir, validations, is_template = await service.generate_workflow(
            prompt=request.prompt,
            category=request.category,
            provider=request.provider,
            model=request.model,
        )

        all_passed = all(v.passed for v in validations)

        # Compile preview schema
        adapter = get_automation_engine(tenant_id, db)
        preview_deploy = await adapter.compile_and_deploy_workflow(tenant_id, ir)

        return {
            "is_template_match": is_template,
            "validation_passed": all_passed,
            "validation_gates": [v.to_dict() for v in validations],
            "definition_ir": ir.model_dump(),
            "compiled_schema": preview_deploy.get("compiled_schema", {}),
            "risk_level": ir.risk_level.value if hasattr(ir.risk_level, "value") else str(ir.risk_level),
            "requires_approval": ir.requires_approval,
        }
    except ValueError as e:
        logger.warning(f"Configuration or validation error in /automations/generate: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating automation workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate automation workflow: {str(e)}"
        )


@router.post("")
async def create_automation(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(require_permission(Resource.SETTINGS, Action.CREATE)),
    request: CreateAutomationRequest,
) -> Any:
    """
    Persists a new automation workflow and deploys it to the automation engine.
    """
    try:
        ir = AutomationIR(**request.definition_ir)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid AutomationIR structure: {e}")

    slug = request.slug or ir.slug or request.name.lower().replace(" ", "_")
    adapter = get_automation_engine(tenant_id, db)

    # 1. Compile & deploy to engine
    deploy_result = await adapter.compile_and_deploy_workflow(tenant_id, ir)
    external_id = deploy_result.get("external_id")
    compiled = deploy_result.get("compiled_schema", {})

    status_val = WorkflowStatus.ACTIVE.value if request.activate_now and not ir.requires_approval else WorkflowStatus.DRAFT.value

    # 2. Persist workflow
    wf = AutomationWorkflow(
        tenant_id=tenant_id,
        name=request.name or ir.name,
        slug=slug,
        description=request.description or ir.description,
        category=request.category or ir.category,
        status=status_val,
        engine_type=adapter.engine_type.value,
        external_flow_id=external_id,
        trigger_type=ir.trigger.type,
        trigger_event=ir.trigger.event,
        definition_ir=ir.model_dump(),
        compiled_schema=compiled,
        current_version=1,
        is_ai_generated=bool(request.ai_prompt),
        ai_prompt=request.ai_prompt,
        requires_approval=ir.requires_approval,
        risk_level=ir.risk_level.value if hasattr(ir.risk_level, "value") else str(ir.risk_level),
        created_by_user_id=current_user.id,
    )
    db.add(wf)
    db.flush()

    # 3. Version record
    ver = AutomationWorkflowVersion(
        workflow_id=wf.id,
        version=1,
        definition_ir=ir.model_dump(),
        compiled_schema=compiled,
        change_reason="Initial creation",
        created_by=current_user.email,
    )
    db.add(ver)

    # 4. Activate in engine if requested
    if request.activate_now and external_id:
        await adapter.activate_workflow(tenant_id, external_id, True)

    db.commit()
    db.refresh(wf)

    return {
        "id": wf.id,
        "name": wf.name,
        "slug": wf.slug,
        "status": wf.status,
        "external_flow_id": wf.external_flow_id,
        "version": wf.current_version,
    }


@router.get("/{workflow_id}")
def get_automation(
    workflow_id: str,
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """Returns complete workflow details including version history."""
    wf = db.query(AutomationWorkflow).filter_by(id=workflow_id, tenant_id=tenant_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    versions = (
        db.query(AutomationWorkflowVersion)
        .filter_by(workflow_id=wf.id)
        .order_by(AutomationWorkflowVersion.version.desc())
        .all()
    )

    return {
        "id": wf.id,
        "name": wf.name,
        "slug": wf.slug,
        "description": wf.description,
        "category": wf.category,
        "status": wf.status,
        "engine_type": wf.engine_type,
        "external_flow_id": wf.external_flow_id,
        "trigger_type": wf.trigger_type,
        "trigger_event": wf.trigger_event,
        "definition_ir": wf.definition_ir,
        "compiled_schema": wf.compiled_schema,
        "current_version": wf.current_version,
        "is_ai_generated": wf.is_ai_generated,
        "ai_prompt": wf.ai_prompt,
        "risk_level": wf.risk_level,
        "requires_approval": wf.requires_approval,
        "versions": [
            {
                "version": v.version,
                "change_reason": v.change_reason,
                "created_by": v.created_by,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
    }


@router.post("/{workflow_id}/activate")
async def toggle_activation(
    workflow_id: str,
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.SETTINGS, Action.UPDATE)),
    request: ToggleActiveRequest,
) -> Any:
    """Toggles workflow active / paused state in both OctaOS and the engine."""
    wf = db.query(AutomationWorkflow).filter_by(id=workflow_id, tenant_id=tenant_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if request.active and wf.requires_approval and wf.status == WorkflowStatus.DRAFT.value:
        raise HTTPException(status_code=403, detail="Workflow requires executive approval before activation.")

    adapter = get_automation_engine(tenant_id, db)
    if wf.external_flow_id:
        await adapter.activate_workflow(tenant_id, wf.external_flow_id, request.active)

    wf.status = WorkflowStatus.ACTIVE.value if request.active else WorkflowStatus.PAUSED.value
    db.commit()

    return {"id": wf.id, "status": wf.status}


@router.post("/{workflow_id}/run")
async def manual_run(
    workflow_id: str,
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.SETTINGS, Action.CREATE)),
    request: ManualRunRequest,
) -> Any:
    """Triggers an immediate test execution of the workflow."""
    wf = db.query(AutomationWorkflow).filter_by(id=workflow_id, tenant_id=tenant_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    adapter = get_automation_engine(tenant_id, db)
    payload = request.payload or {"test": True, "source": "OctaOS Manual Console"}

    execution = AutomationExecution(
        tenant_id=tenant_id,
        workflow_id=wf.id,
        trigger_type="manual",
        status="running",
        inputs=payload,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    try:
        res = await adapter.trigger_workflow_manually(tenant_id, wf.external_flow_id or wf.id, payload)
        execution.status = "succeeded"
        execution.external_execution_id = res.get("execution_id")
        execution.outputs = res.get("outputs", {})
        db.commit()
        return {"status": "succeeded", "execution_id": execution.id, "outputs": execution.outputs}
    except Exception as e:
        execution.status = "failed"
        execution.failure_reason = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Execution failed: {e}")


@router.get("/{workflow_id}/editor-url")
async def get_editor_session(
    workflow_id: str,
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(require_permission(Resource.SETTINGS, Action.UPDATE)),
) -> Any:
    """Generates the secure deep link URL for visual workflow canvas editing (builder permission required)."""
    wf = db.query(AutomationWorkflow).filter_by(id=workflow_id, tenant_id=tenant_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    adapter = get_automation_engine(tenant_id, db)
    editor_url = await adapter.get_workflow_editor_url(
        tenant_id=tenant_id,
        external_id=wf.external_flow_id or wf.id,
        user_email=current_user.email,
    )

    return {
        "workflow_id": wf.id,
        "editor_url": editor_url,
        "engine_type": wf.engine_type,
    }


@router.get("/{workflow_id}/executions")
def list_executions(
    workflow_id: str,
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    limit: int = 20,
) -> Any:
    """Returns execution logs with classified root causes for the workflow."""
    executions = (
        db.query(AutomationExecution)
        .filter_by(workflow_id=workflow_id, tenant_id=tenant_id)
        .order_by(AutomationExecution.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": ex.id,
            "status": ex.status,
            "trigger_type": ex.trigger_type,
            "trigger_event": ex.trigger_event,
            "failure_classification": ex.failure_classification,
            "failure_reason": ex.failure_reason,
            "duration_ms": ex.duration_ms,
            "inputs": ex.inputs,
            "outputs": ex.outputs,
            "started_at": ex.started_at.isoformat() if ex.started_at else None,
            "finished_at": ex.finished_at.isoformat() if ex.finished_at else None,
        }
        for ex in executions
    ]


@router.post("/events/test-dispatch")
async def test_dispatch_event(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.SETTINGS, Action.CREATE)),
    request: TestEventDispatchRequest,
) -> Any:
    """Simulates an internal OctaOS event to verify end-to-end automation triggering."""
    bridge = AutomationEventBridge(db, tenant_id)
    results = await bridge.dispatch_event(request.event_type, request.payload)
    return {"event": request.event_type, "triggered_workflows": results}


# ─── Visual Canvas Graph Endpoints (n8n-Style Builder) ───────────────────────

@router.get("/{workflow_id}/graph")
def get_workflow_graph(
    workflow_id: str,
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """
    Returns the canonical visual AutomationGraph for the canvas builder.
    If only a legacy definition_ir exists, it is automatically converted into a structured graph.
    """
    wf = db.query(AutomationWorkflow).filter_by(id=workflow_id, tenant_id=tenant_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    graph = wf.get_graph()
    validation = GraphValidator.validate(graph)

    return {
        "workflow_id": wf.id,
        "name": wf.name,
        "slug": wf.slug,
        "status": wf.status,
        "current_version": wf.current_version,
        "published_version": wf.published_version,
        "graph": graph.model_dump(),
        "graph_hash": wf.graph_hash or graph.calculate_hash(),
        "validation": validation.to_dict(),
    }


@router.put("/{workflow_id}/graph")
async def save_workflow_graph(
    workflow_id: str,
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(require_permission(Resource.SETTINGS, Action.UPDATE)),
    graph_payload: AutomationGraph,
) -> Any:
    """
    Saves and persists an updated visual workflow canvas graph draft.
    Validates graph DAG topology and compiles downstream Activepieces schemas.
    """
    wf = db.query(AutomationWorkflow).filter_by(id=workflow_id, tenant_id=tenant_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    validation = GraphValidator.validate(graph_payload)
    graph_dict = graph_payload.model_dump()
    graph_hash = graph_payload.calculate_hash()

    # Convert graph to legacy IR to maintain engine compatibility
    legacy_ir = convert_graph_to_legacy_ir(graph_payload)

    # Compile target Activepieces schema
    try:
        from app.services.automation.base import AutomationIR
        ir_obj = AutomationIR(**legacy_ir)
        compiled = FlowCompiler.compile_to_activepieces(ir_obj)
    except Exception as e:
        logger.warning(f"Could not compile Activepieces schema: {e}")
        compiled = wf.compiled_schema or {}

    # Update workflow draft
    wf.name = graph_payload.name or wf.name
    wf.description = graph_payload.description or wf.description
    wf.graph_json = graph_dict
    wf.graph_hash = graph_hash
    wf.definition_ir = legacy_ir
    wf.compiled_schema = compiled
    wf.current_version = (wf.current_version or 1) + 1

    # Record version snapshot
    version_record = AutomationWorkflowVersion(
        workflow_id=wf.id,
        version=wf.current_version,
        definition_ir=legacy_ir,
        graph_json=graph_dict,
        graph_hash=graph_hash,
        compiled_schema=compiled,
        change_reason="Visual canvas draft update",
        created_by=current_user.email,
    )
    db.add(version_record)
    db.commit()
    db.refresh(wf)

    return {
        "status": "saved",
        "workflow_id": wf.id,
        "version": wf.current_version,
        "graph_hash": graph_hash,
        "validation": validation.to_dict(),
    }


@router.post("/{workflow_id}/validate")
def validate_workflow_graph(
    workflow_id: str,
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    graph_payload: AutomationGraph,
) -> Any:
    """Validates an in-memory graph without saving, returning cycle and port checks."""
    wf = db.query(AutomationWorkflow).filter_by(id=workflow_id, tenant_id=tenant_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    validation = GraphValidator.validate(graph_payload)
    return validation.to_dict()


@router.post("/{workflow_id}/publish")
async def publish_workflow_graph(
    workflow_id: str,
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(require_permission(Resource.SETTINGS, Action.UPDATE)),
) -> Any:
    """
    Publishes the current graph version into active production.
    Strictly enforces zero validation errors.
    """
    wf = db.query(AutomationWorkflow).filter_by(id=workflow_id, tenant_id=tenant_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    graph = wf.get_graph()
    validation = GraphValidator.validate(graph)

    if not validation.is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot publish workflow with validation errors: {', '.join(validation.errors)}",
        )

    wf.published_version = wf.current_version
    wf.status = "active"

    # Activate in external engine if configured
    if wf.external_flow_id:
        adapter = get_automation_engine(tenant_id, db)
        await adapter.activate_workflow(tenant_id, wf.external_flow_id, True)

    db.commit()
    db.refresh(wf)

    return {
        "status": "published",
        "workflow_id": wf.id,
        "published_version": wf.published_version,
        "workflow_status": wf.status,
    }

