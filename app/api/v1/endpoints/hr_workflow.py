"""API Endpoints for OctaOS Dynamic HR Document Intelligence & Workflow Builder."""
import hashlib
import io
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.base import User
from app.models.verticals import Candidate
from app.models.hr import (
    TenantDocumentTemplate,
    TemplateVersion,
    TemplateVariableSchema,
    HRWorkflowDefinition,
    HRWorkflowInstance,
    HRWorkflowTask,
    CandidateFieldValue,
    CandidateEvidence,
    DocumentDraft,
    DocumentReviewComment,
    ScheduledDelivery,
    Application,
)
from app.schemas.hr_workflow import (
    TemplateAnalysisResponse,
    TemplatePublishRequest,
    WorkflowDefinitionCreate,
    WorkflowDefinitionUpdate,
    NodeTypeMetadata,
    WorkflowTestRunRequest,
    WorkflowTestRunResponse,
    WorkflowGraphSchema,
    AIPipelineGenerateRequest,
    AIPipelineGenerateResponse,
    DraftPreviewResponse,
    DraftEditRequest,
    DraftApprovalRequest,
    DraftScheduleRequest,
    ReconciliationSummary,
    AddReviewCommentRequest,
)
from app.services.hr.template_hub.parser import DocumentTemplateParser
from app.services.hr.template_hub.intelligence import TemplateIntelligenceAnalyzer
from app.services.hr.workflow.engine import DynamicWorkflowEngine
from app.services.hr.candidate_portal.service import CandidatePortalService
from app.services.hr.extraction.reconciliation import EvidenceReconciliationService
from app.services.hr.review_studio.renderer import ReviewStudioRenderer
from app.services.hr.delivery.scheduler import DeliverySchedulerService
from app.services.hr.document_store import DocumentStore


router = APIRouter()


# --- TEMPLATE HUB ENDPOINTS ---

@router.post("/templates/upload", response_model=TemplateAnalysisResponse)
async def upload_template(
    file: UploadFile = File(...),
    name: str = Form(...),
    category: str = Form("onboarding"),
    folder_path: str = Form("/"),
    tags: str = Form(""),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Uploads a DOCX or HTML template, calculates SHA-256, parses structure, and proposes canonical mappings."""
    tenant_id = current_user.tenant_id
    content_bytes = await file.read()
    filename = file.filename or "template.docx"
    doc_format = "docx" if filename.lower().endswith(".docx") else "html"
    content_sha = hashlib.sha256(content_bytes).hexdigest()

    # Parse structure and placeholders
    paragraphs_sample: List[str] = []
    if doc_format == "docx":
        placeholders, meta = DocumentTemplateParser.parse_docx(content_bytes)
        try:
            import docx
            doc = docx.Document(io.BytesIO(content_bytes))
            paragraphs_sample = [p.text for p in doc.paragraphs if p.text]
        except Exception:
            paragraphs_sample = []
    else:
        html_str = content_bytes.decode("utf-8", errors="ignore")
        placeholders, meta = DocumentTemplateParser.parse_html(html_str)
        paragraphs_sample = [s.strip() for s in html_str.split("</p>") if s.strip()]

    # Run AI intelligence analyzer
    proposed_mappings, detected_clauses = TemplateIntelligenceAnalyzer.analyze_template(
        placeholders=placeholders,
        paragraphs_text=paragraphs_sample,
    )

    # Store file binary safely
    storage_key = DocumentStore.save(
        tenant_id=tenant_id,
        filename=filename,
        content=content_bytes,
        prefix="templates",
    )

    # Persist or update template
    parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]
    template = db.query(TenantDocumentTemplate).filter_by(
        tenant_id=tenant_id,
        name=name,
    ).first()

    if not template:
        template = TenantDocumentTemplate(
            tenant_id=tenant_id,
            document_type=category,
            category=category,
            name=name,
            folder_path=folder_path,
            tags=parsed_tags,
        )
        db.add(template)
        db.flush()

    # Create new version
    version_count = db.query(TemplateVersion).filter_by(template_id=template.id).count()
    template_version = TemplateVersion(
        template_id=template.id,
        tenant_id=tenant_id,
        version=version_count + 1,
        format=doc_format,
        status="analyzed",
        storage_key=storage_key,
        content_sha256=content_sha,
        raw_content=content_bytes.decode("utf-8", errors="ignore") if doc_format == "html" else None,
        docx_structure=meta,
        detected_clauses=[c.model_dump() for c in detected_clauses],
        proposed_mappings=[m.model_dump() for m in proposed_mappings],
    )
    db.add(template_version)
    db.commit()
    db.refresh(template_version)

    return TemplateAnalysisResponse(
        template_id=template.id,
        version_id=template_version.id,
        format=doc_format,
        content_sha256=content_sha,
        placeholders=placeholders,
        proposed_mappings=proposed_mappings,
        detected_clauses=detected_clauses,
        table_count=meta.get("table_count", 0),
        paragraph_count=meta.get("paragraph_count", 0),
    )


@router.post("/templates/{version_id}/publish")
def publish_template(
    version_id: str,
    req: TemplatePublishRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Approves canonical mappings and publishes the template version for workflows."""
    version = db.query(TemplateVersion).filter_by(
        id=version_id,
        tenant_id=current_user.tenant_id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Template version not found")

    # Record approved variable schemas
    for m in req.approved_mappings:
        var_schema = TemplateVariableSchema(
            template_version_id=version.id,
            variable_name=m.canonical_key,
            data_type=m.data_type,
            is_required=m.is_required,
            source_field=m.canonical_key,
            sensitivity="confidential",
            editable_by_recruiter=True,
        )
        db.add(var_schema)

    version.status = "published"
    version.published_at = datetime.now(timezone.utc)
    version.published_by_user_id = current_user.id
    db.commit()
    return {"status": "published", "version_id": version.id}


@router.get("/templates")
def list_templates(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Lists all document templates and their latest versions for the tenant."""
    templates = db.query(TenantDocumentTemplate).filter_by(
        tenant_id=current_user.tenant_id,
    ).all()

    result = []
    for t in templates:
        latest_ver = (
            db.query(TemplateVersion)
            .filter_by(template_id=t.id)
            .order_by(TemplateVersion.version.desc())
            .first()
        )
        result.append({
            "id": t.id,
            "name": t.name,
            "category": t.category,
            "folder_path": t.folder_path,
            "tags": t.tags or [],
            "latest_version": latest_ver.version if latest_ver else 1,
            "status": latest_ver.status if latest_ver else "draft",
            "format": latest_ver.format if latest_ver else "docx",
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return result


# --- WORKFLOW BUILDER ENDPOINTS ---

@router.post("/definitions")
def create_workflow_definition(
    req: WorkflowDefinitionCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Creates a new dynamic workflow graph definition."""
    is_valid, errors = DynamicWorkflowEngine.validate_graph(req.graph_schema)
    if not is_valid:
        raise HTTPException(status_code=400, detail={"errors": errors})

    wf = HRWorkflowDefinition(
        tenant_id=current_user.tenant_id,
        name=req.name,
        description=req.description,
        graph_schema=req.graph_schema.model_dump(),
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return {"id": wf.id, "name": wf.name, "version": wf.version}


@router.get("/definitions")
def list_workflow_definitions(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Lists all workflow definitions for the current tenant."""
    workflows = db.query(HRWorkflowDefinition).filter_by(
        tenant_id=current_user.tenant_id,
    ).all()
    return [
        {
            "id": w.id,
            "name": w.name,
            "description": w.description,
            "is_active": w.is_active,
            "version": w.version,
            "node_count": len((w.graph_schema or {}).get("nodes", [])),
            "created_at": w.created_at.isoformat() if w.created_at else None,
        }
        for w in workflows
    ]


@router.get("/node-registry", response_model=List[NodeTypeMetadata])
def get_node_registry():
    """Returns the comprehensive registry of all 15 configurable node types."""
    return DynamicWorkflowEngine.get_node_registry()


@router.post("/ai-generate", response_model=AIPipelineGenerateResponse)
def ai_generate_workflow(
    req: AIPipelineGenerateRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Synthesizes a proposed DAG workflow from a natural-language prompt.
    Validates the generated graph against the shared WorkflowGraphContract schema.
    Does NOT publish or execute candidate actions automatically.
    """
    return DynamicWorkflowEngine.generate_workflow_graph_from_prompt(
        prompt=req.prompt,
        job_role=req.job_role,
        tenant_id=current_user.tenant_id,
        db=db,
    )


@router.get("/definitions/{definition_id}")
def get_workflow_definition(
    definition_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Retrieves full workflow definition with its graph schema for the visual canvas."""
    wf = db.query(HRWorkflowDefinition).filter_by(
        id=definition_id,
        tenant_id=current_user.tenant_id,
    ).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow definition not found")

    return {
        "id": wf.id,
        "name": wf.name,
        "description": wf.description,
        "is_active": wf.is_active,
        "version": wf.version,
        "graph_schema": wf.graph_schema or {"nodes": [], "edges": []},
        "created_at": wf.created_at.isoformat() if wf.created_at else None,
        "updated_at": wf.updated_at.isoformat() if wf.updated_at else None,
    }


@router.put("/definitions/{definition_id}")
def update_workflow_definition(
    definition_id: str,
    req: WorkflowDefinitionUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Updates a workflow definition and its visual graph schema."""
    wf = db.query(HRWorkflowDefinition).filter_by(
        id=definition_id,
        tenant_id=current_user.tenant_id,
    ).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow definition not found")

    if req.graph_schema:
        is_valid, errors = DynamicWorkflowEngine.validate_graph(req.graph_schema)
        if not is_valid:
            raise HTTPException(status_code=400, detail={"errors": errors})
        wf.graph_schema = req.graph_schema.model_dump()

    if req.name is not None:
        wf.name = req.name
    if req.description is not None:
        wf.description = req.description
    if req.is_active is not None:
        wf.is_active = req.is_active

    db.commit()
    db.refresh(wf)
    return {
        "id": wf.id,
        "name": wf.name,
        "version": wf.version,
        "is_active": wf.is_active,
        "updated_at": wf.updated_at.isoformat() if wf.updated_at else None,
    }


@router.post("/definitions/{definition_id}/publish")
def publish_workflow_definition(
    definition_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Validates and publishes an immutable version of the workflow definition."""
    wf = db.query(HRWorkflowDefinition).filter_by(
        id=definition_id,
        tenant_id=current_user.tenant_id,
    ).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow definition not found")

    # Validate graph structure before publishing
    schema = WorkflowGraphSchema(**(wf.graph_schema or {"nodes": [], "edges": []}))
    is_valid, errors = DynamicWorkflowEngine.validate_graph(schema)
    if not is_valid:
        raise HTTPException(status_code=400, detail={"detail": "Cannot publish invalid workflow", "errors": errors})

    wf.version = (wf.version or 1) + 1
    wf.is_active = True
    db.commit()
    return {"status": "published", "id": wf.id, "version": wf.version}


@router.delete("/definitions/{definition_id}")
def delete_workflow_definition(
    definition_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Deletes or deactivates a workflow definition."""
    wf = db.query(HRWorkflowDefinition).filter_by(
        id=definition_id,
        tenant_id=current_user.tenant_id,
    ).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow definition not found")

    wf.is_active = False
    db.commit()
    return {"status": "deactivated", "id": wf.id}


@router.post("/definitions/test-run", response_model=WorkflowTestRunResponse)
def test_run_workflow(req: WorkflowTestRunRequest):
    """Simulates a test run of a workflow DAG against sample candidate context."""
    return DynamicWorkflowEngine.evaluate_traversal(
        graph=req.graph_schema,
        context=req.sample_context,
    )


@router.post("/definitions/{definition_id}/instantiate")
def instantiate_workflow(
    definition_id: str,
    candidate_id: str = Form(...),
    application_id: str = Form(...),
    context_data: Optional[Dict[str, Any]] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Launches a dynamic workflow instance for a candidate application and generates candidate portal link."""
    wf_def = db.query(HRWorkflowDefinition).filter_by(
        id=definition_id,
        tenant_id=current_user.tenant_id,
    ).first()
    if not wf_def:
        raise HTTPException(status_code=404, detail="Workflow definition not found")

    raw_token, token_hash, expires_at = CandidatePortalService.generate_token_pair(expires_in_days=7)

    instance = HRWorkflowInstance(
        tenant_id=current_user.tenant_id,
        workflow_definition_id=wf_def.id,
        application_id=application_id,
        candidate_id=candidate_id,
        current_state="intake_pending",
        candidate_token_hash=token_hash,
        token_expires_at=expires_at,
        context_data=context_data or {},
    )
    db.add(instance)
    db.flush()

    # Create initial tasks from graph
    nodes = (wf_def.graph_schema or {}).get("nodes", [])
    for node in nodes:
        task = HRWorkflowTask(
            tenant_id=current_user.tenant_id,
            instance_id=instance.id,
            node_id=node.get("id"),
            task_type=node.get("type", "candidate_intake"),
            status="pending",
        )
        db.add(task)

    db.commit()

    return {
        "instance_id": instance.id,
        "candidate_portal_token": raw_token,
        "candidate_portal_url": f"/candidate-portal/{raw_token}",
        "expires_at": expires_at.isoformat(),
        "status": instance.current_state,
    }


@router.get("/instances/{instance_id}")
def get_instance_details(
    instance_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Retrieves full workflow instance state, tasks, and candidate progress."""
    instance = db.query(HRWorkflowInstance).filter_by(
        id=instance_id,
        tenant_id=current_user.tenant_id,
    ).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    tasks = db.query(HRWorkflowTask).filter_by(instance_id=instance.id).all()
    evidence = db.query(CandidateEvidence).filter_by(instance_id=instance.id).all()
    fields = db.query(CandidateFieldValue).filter_by(instance_id=instance.id).all()

    return {
        "id": instance.id,
        "workflow_definition_id": instance.workflow_definition_id,
        "candidate_id": instance.candidate_id,
        "current_state": instance.current_state,
        "expires_at": instance.token_expires_at.isoformat(),
        "tasks": [
            {"id": t.id, "node_id": t.node_id, "type": t.task_type, "status": t.status}
            for t in tasks
        ],
        "evidence_count": len(evidence),
        "fields": {f.canonical_key: f.resolved_value for f in fields},
    }


@router.post("/instances/{instance_id}/reconcile", response_model=ReconciliationSummary)
def reconcile_instance(
    instance_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Reconciles candidate provided data with OCR evidence and flags conflicts."""
    instance = db.query(HRWorkflowInstance).filter_by(
        id=instance_id,
        tenant_id=current_user.tenant_id,
    ).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    summary = EvidenceReconciliationService.reconcile_instance_data(db, instance_id)
    if not summary.is_blocked:
        instance.current_state = "review_ready"
        db.commit()
    return summary


# --- REVIEW STUDIO ENDPOINTS ---

@router.get("/drafts/{draft_id}/preview", response_model=DraftPreviewResponse)
def get_draft_preview(
    draft_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Fetches high-fidelity paginated preview pages for Review Studio."""
    draft = db.query(DocumentDraft).filter_by(
        id=draft_id,
        tenant_id=current_user.tenant_id,
    ).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Document draft not found")

    # Load content
    content_bytes = DocumentStore.read(draft.storage_key)
    pages = ReviewStudioRenderer.generate_paginated_preview(content_bytes)

    # Fetch conflicts if any
    conflicts_recs = db.query(CandidateFieldValue).filter_by(
        instance_id=draft.instance_id,
        has_conflict=True,
    ).all()
    conflicts = [
        {
            "canonical_key": c.canonical_key,
            "candidate_value": c.candidate_provided_value,
            "extracted_value": c.document_extracted_value,
            "source_snippet": (c.source_provenance or {}).get("snippet"),
            "confidence": (c.source_provenance or {}).get("confidence", 0.0),
            "reason": (c.conflict_details or {}).get("reason", "Conflict detected"),
        }
        for c in conflicts_recs
    ]

    comments = db.query(DocumentReviewComment).filter_by(draft_id=draft.id).all()

    return DraftPreviewResponse(
        draft_id=draft.id,
        document_name=draft.document_name,
        template_version_id=draft.template_version_id,
        current_approval_status=draft.current_approval_status,
        content_sha256=draft.content_sha256,
        field_values=draft.field_overrides or {},
        pages=pages,
        conflicts=conflicts,
        revisions=draft.editor_revisions or [],
        comments=[
            {"id": c.id, "user_name": c.user_name, "paragraph_index": c.paragraph_index, "text": c.comment_text}
            for c in comments
        ],
    )


@router.put("/drafts/{draft_id}/edit")
def edit_draft(
    draft_id: str,
    req: DraftEditRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Edits draft content and strictly invalidates prior approvals."""
    draft = ReviewStudioRenderer.apply_draft_edit(
        db=db,
        draft_id=draft_id,
        user_id=current_user.id,
        field_overrides=req.field_overrides,
        paragraph_updates=req.paragraph_updates,
        edit_summary=req.edit_summary,
    )
    return {
        "status": "updated",
        "current_approval_status": draft.current_approval_status,
        "approval_invalidated": draft.current_approval_status == "draft",
    }


@router.post("/drafts/{draft_id}/approve")
def approve_draft(
    draft_id: str,
    req: DraftApprovalRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Authorizes document draft, binding cryptographically to content SHA-256."""
    draft = db.query(DocumentDraft).filter_by(
        id=draft_id,
        tenant_id=current_user.tenant_id,
    ).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    draft.current_approval_status = "approved"
    draft.approved_by_user_id = current_user.id
    draft.approved_at = datetime.now(timezone.utc)
    draft.bound_approval_sha256 = draft.content_sha256
    db.commit()

    return {
        "status": "approved",
        "bound_approval_sha256": draft.bound_approval_sha256,
        "approved_at": draft.approved_at.isoformat(),
    }


@router.post("/drafts/{draft_id}/schedule")
def schedule_draft_delivery(
    draft_id: str,
    req: DraftScheduleRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Schedules dispatch of an approved document in the configured timezone."""
    try:
        delivery = DeliverySchedulerService.schedule_delivery(
            db=db,
            draft_id=draft_id,
            scheduled_for=req.scheduled_for,
            timezone_str=req.timezone,
            recipient_email=req.recipient_email,
        )
        return {
            "delivery_id": delivery.id,
            "status": delivery.status,
            "scheduled_for": delivery.scheduled_for.isoformat(),
            "timezone": delivery.timezone,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/deliveries/{delivery_id}/dispatch")
def trigger_dispatch(
    delivery_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Executes pre-flight revalidation and dispatches the document."""
    success, message = DeliverySchedulerService.revalidate_and_dispatch(db, delivery_id)
    if not success:
        raise HTTPException(status_code=409, detail=message)
    return {"status": "dispatched", "message": message}
