"""Comprehensive Tests for OctaOS Dynamic HR Document Intelligence & Workflow Builder."""
import io
import docx
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, User, Tenant
from app.models.verticals import Candidate
from app.models.hr import (
    TenantDocumentTemplate,
    TemplateVersion,
    HRWorkflowDefinition,
    HRWorkflowInstance,
    HRWorkflowTask,
    CandidateEvidence,
    CandidateFieldValue,
    DocumentDraft,
    ScheduledDelivery,
    Application,
    JobRequisition,
)
from app.schemas.hr_workflow import (
    WorkflowGraphSchema,
    WorkflowNode,
    WorkflowEdge,
    ProposedFieldMapping,
    DraftEditRequest,
)
from app.services.hr.template_hub.parser import DocumentTemplateParser
from app.services.hr.template_hub.intelligence import TemplateIntelligenceAnalyzer
from app.services.hr.workflow.engine import DynamicWorkflowEngine
from app.services.hr.candidate_portal.service import CandidatePortalService
from app.services.hr.extraction.reconciliation import EvidenceReconciliationService
from app.services.hr.review_studio.renderer import ReviewStudioRenderer
from app.services.hr.delivery.scheduler import DeliverySchedulerService
from app.services.hr.document_store import DocumentStore


@pytest.fixture(scope="module")
def db_session():
    """In-memory SQLite session with all tables created."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed baseline tenant and user
    tenant = Tenant(id="test-dynamic-tenant", name="OctaCorp Global")
    user = User(
        id="usr-hr-admin-1",
        email="hr.admin@octacorp.com",
        tenant_id="test-dynamic-tenant",
        role="admin",
        hashed_password="mock",
    )
    candidate = Candidate(
        id="cand-dynamic-1",
        tenant_id="test-dynamic-tenant",
        name="Priya Sharma",
        email="priya.sharma@example.com",
    )
    req = JobRequisition(
        id="req-dynamic-1",
        tenant_id="test-dynamic-tenant",
        title="Senior Product Designer",
    )
    app = Application(
        id="app-dynamic-1",
        tenant_id="test-dynamic-tenant",
        candidate_id="cand-dynamic-1",
        requisition_id="req-dynamic-1",
    )
    session.add_all([tenant, user, candidate, req, app])
    session.commit()

    yield session
    session.close()


def create_sample_docx_bytes() -> bytes:
    """Creates an in-memory DOCX with paragraphs, tables, and clauses."""
    doc = docx.Document()
    doc.add_heading("EMPLOYMENT AGREEMENT", 0)
    doc.add_paragraph("This Agreement is made between OctaCorp and {{ candidate.full_name }} (the [Employee Name]).")
    doc.add_paragraph("Designation: << role.title >> in department << role.department >>.")
    doc.add_paragraph("Commencing on {{ role.start_date }} with annual CTC of {{ compensation.annual_ctc }}.")

    # Add a table
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Component"
    table.rows[0].cells[1].text = "Value"
    table.rows[1].cells[0].text = "Base Salary"
    table.rows[1].cells[1].text = "{{ compensation.base_amount }}"

    # Add sensitive clause
    doc.add_heading("Confidentiality and Non-Disclosure", level=1)
    doc.add_paragraph("The Employee agrees to preserve strict secrecy of all proprietary information and trade secrets of OctaCorp.")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# 1. TEMPLATE HUB & INTELLIGENCE TESTS

def test_template_hub_docx_parsing_and_clause_detection():
    docx_bytes = create_sample_docx_bytes()
    placeholders, meta = DocumentTemplateParser.parse_docx(docx_bytes)

    assert len(placeholders) >= 4
    inferred_keys = [p.inferred_key for p in placeholders]
    assert any("candidate" in k or "employee_name" in k for k in inferred_keys)
    assert any("annual_ctc" in k for k in inferred_keys)
    assert meta["table_count"] == 1
    assert meta["paragraph_count"] >= 4

    # Run AI intelligence analyzer
    paragraphs_sample = [
        "This Agreement is made between OctaCorp and {{ candidate.full_name }}.",
        "Designation: << role.title >> in department << role.department >>.",
        "The Employee agrees to preserve strict secrecy of all proprietary information and trade secrets of OctaCorp.",
    ]
    proposed_mappings, detected_clauses = TemplateIntelligenceAnalyzer.analyze_template(
        placeholders=placeholders,
        paragraphs_text=paragraphs_sample,
    )

    assert len(proposed_mappings) >= 4
    # Check canonical mapping
    name_mapping = next((m for m in proposed_mappings if m.canonical_key == "candidate.full_name"), None)
    assert name_mapping is not None
    assert name_mapping.data_type == "string"
    assert name_mapping.confidence >= 0.90

    # Check clause detection
    assert len(detected_clauses) >= 1
    conf_clause = next((c for c in detected_clauses if c.clause_type == "confidentiality"), None)
    assert conf_clause is not None
    assert "confidential" in conf_clause.title.lower() or "secrecy" in conf_clause.summary.lower()


# 2. DYNAMIC WORKFLOW BUILDER & DAG ORCHESTRATION TESTS

def test_dynamic_workflow_dag_evaluation_and_conditional_branching():
    # Construct a DAG with conditional branching:
    # intake -> condition -> (if permanent -> offer & employment_agreement)
    #                     -> (if contractor -> service_agreement & tax_forms)
    graph = WorkflowGraphSchema(
        nodes=[
            WorkflowNode(id="n_intake", name="Candidate Intake", type="candidate_intake", config={"intake_fields": ["candidate.full_name", "candidate.email", "candidate.current_address"]}),
            WorkflowNode(id="n_branch", name="Evaluate Type", type="condition_branch", config={}),
            WorkflowNode(id="n_fte_offer", name="Permanent Offer", type="document_generation", config={"template_name": "FTE Offer Letter", "required_fields": ["compensation.annual_ctc"]}),
            WorkflowNode(id="n_fte_contract", name="Employment Agreement", type="document_generation", config={"template_name": "Full Employment Agreement", "required_fields": ["role.start_date"]}),
            WorkflowNode(id="n_contractor_agreement", name="Service Agreement", type="document_generation", config={"template_name": "Contractor Master Services Agreement", "required_fields": ["contractor.daily_rate"]}),
        ],
        edges=[
            WorkflowEdge(id="e1", source="n_intake", target="n_branch"),
            WorkflowEdge(id="e2", source="n_branch", target="n_fte_offer", condition="context.employment_type == 'permanent'"),
            WorkflowEdge(id="e3", source="n_fte_offer", target="n_fte_contract"),
            WorkflowEdge(id="e4", source="n_branch", target="n_contractor_agreement", condition="context.employment_type == 'contractor'"),
        ],
    )

    # Permanent employee test run
    res_fte = DynamicWorkflowEngine.evaluate_traversal(graph, {"employment_type": "permanent"})
    assert res_fte.is_valid is True
    assert "n_fte_offer" in res_fte.traversed_path
    assert "n_fte_contract" in res_fte.traversed_path
    assert "n_contractor_agreement" not in res_fte.traversed_path
    assert "FTE Offer Letter" in res_fte.evaluated_documents
    assert "Full Employment Agreement" in res_fte.evaluated_documents
    assert "candidate.email" in res_fte.required_candidate_fields
    assert "compensation.annual_ctc" in res_fte.required_candidate_fields

    # Contractor test run
    res_contractor = DynamicWorkflowEngine.evaluate_traversal(graph, {"employment_type": "contractor"})
    assert res_contractor.is_valid is True
    assert "n_contractor_agreement" in res_contractor.traversed_path
    assert "n_fte_offer" not in res_contractor.traversed_path
    assert "Contractor Master Services Agreement" in res_contractor.evaluated_documents
    assert "contractor.daily_rate" in res_contractor.required_candidate_fields


# 3. CANDIDATE PORTAL & INTAKE SYNTHESIS TESTS

def test_candidate_portal_token_security_and_intake_synthesis(db_session):
    raw_token, token_hash, expires_at = CandidatePortalService.generate_token_pair(expires_in_days=7)
    assert len(raw_token) >= 32
    assert CandidatePortalService.hash_token(raw_token) == token_hash

    # Create workflow definition in DB
    wf_def = HRWorkflowDefinition(
        tenant_id="test-dynamic-tenant",
        name="Standard Onboarding Flow",
        graph_schema={
            "nodes": [
                {"id": "n1", "name": "Intake", "type": "candidate_intake", "config": {"intake_fields": ["candidate.full_name", "candidate.email", "candidate.pan_number"]}},
                {"id": "n2", "name": "Contract", "type": "document_generation", "config": {"required_fields": ["candidate.current_address", "role.start_date"]}},
            ],
            "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
        },
    )
    db_session.add(wf_def)
    db_session.flush()

    instance = HRWorkflowInstance(
        tenant_id="test-dynamic-tenant",
        workflow_definition_id=wf_def.id,
        application_id="app-dynamic-1",
        candidate_id="cand-dynamic-1",
        candidate_token_hash=token_hash,
        token_expires_at=expires_at,
        context_data={"employment_type": "permanent"},
    )
    db_session.add(instance)
    db_session.commit()

    # Resolve session
    session_data = CandidatePortalService.resolve_session(db_session, raw_token)
    assert session_data is not None
    assert session_data.candidate_name == "Priya Sharma"
    assert session_data.role_title == "Senior Product Designer"
    assert session_data.company_name == "OctaCorp Global"

    # Verify synthesized fields (no duplicate requests)
    field_keys = [f.canonical_key for f in session_data.synthesized_fields]
    assert "candidate.full_name" in field_keys
    assert "candidate.pan_number" in field_keys
    assert len(field_keys) == len(set(field_keys))  # Deduplicated

    # Verify expired token rejection
    instance.token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()
    assert CandidatePortalService.resolve_session(db_session, raw_token) is None


# 4. EVIDENCE EXTRACTION & RECONCILIATION TESTS

def test_evidence_reconciliation_detects_conflicts_and_hr_override(db_session):
    instance_id = "inst-reconcile-test-1"
    raw_token, token_hash, expires_at = CandidatePortalService.generate_token_pair(expires_in_days=7)

    instance = HRWorkflowInstance(
        id=instance_id,
        tenant_id="test-dynamic-tenant",
        workflow_definition_id="mock-wf",
        application_id="app-dynamic-1",
        candidate_id="cand-dynamic-1",
        candidate_token_hash=token_hash,
        token_expires_at=expires_at,
    )
    db_session.add(instance)
    db_session.commit()

    # Candidate entered "Priya S."
    field_name = CandidateFieldValue(
        tenant_id="test-dynamic-tenant",
        instance_id=instance_id,
        canonical_key="candidate.full_name",
        candidate_provided_value="Priya S.",
    )
    # Candidate entered correct PAN
    field_pan = CandidateFieldValue(
        tenant_id="test-dynamic-tenant",
        instance_id=instance_id,
        canonical_key="candidate.pan_number",
        candidate_provided_value="ABCDE1234F",
    )
    db_session.add_all([field_name, field_pan])
    db_session.commit()

    # Uploaded passport has official name "Priya Sharma"
    ev1 = CandidateEvidence(
        tenant_id="test-dynamic-tenant",
        instance_id=instance_id,
        document_name="passport_scan.pdf",
        document_category="passport",
        storage_key="test/passport.pdf",
        file_sha256="mock_sha_passport",
        mime_type="application/pdf",
        extracted_data={
            "candidate.full_name": {
                "value": "Priya Sharma",
                "confidence": 0.95,
                "page": 1,
                "snippet": "Name: Priya Sharma",
            }
        },
    )
    # Uploaded tax form matches PAN
    ev2 = CandidateEvidence(
        tenant_id="test-dynamic-tenant",
        instance_id=instance_id,
        document_name="pan_card.pdf",
        document_category="tax_form",
        storage_key="test/pan.pdf",
        file_sha256="mock_sha_pan",
        mime_type="application/pdf",
        extracted_data={
            "candidate.pan_number": {
                "value": "ABCDE1234F",
                "confidence": 0.98,
                "page": 1,
                "snippet": "PAN: ABCDE1234F",
            }
        },
    )
    db_session.add_all([ev1, ev2])
    db_session.commit()

    # Run reconciliation
    summary = EvidenceReconciliationService.reconcile_instance_data(db_session, instance_id)
    # PAN matches -> reconciled
    # Name has discrepancy ("Priya S." vs "Priya Sharma") -> conflict flagged
    assert summary.conflict_count == 1
    assert summary.is_blocked is True
    conflict = summary.conflicts[0]
    assert conflict.canonical_key == "candidate.full_name"
    assert conflict.candidate_value == "Priya S."
    assert conflict.extracted_value == "Priya Sharma"

    # Now HR explicitly overrides the legal name
    field_name.hr_approved_value = "Priya Sharma"
    db_session.commit()

    summary2 = EvidenceReconciliationService.reconcile_instance_data(db_session, instance_id)
    assert summary2.conflict_count == 0
    assert summary2.is_blocked is False
    assert field_name.resolved_value == "Priya Sharma"
    assert field_name.status == "hr_overridden"


# 5. REVIEW STUDIO & STRICT APPROVAL INVALIDATION TESTS

def test_review_studio_rendering_and_approval_invalidation(db_session):
    docx_bytes = create_sample_docx_bytes()
    storage_key = DocumentStore.save(
        tenant_id="test-dynamic-tenant",
        filename="test_draft.docx",
        content=docx_bytes,
        prefix="drafts",
    )

    rendered_bytes, content_sha = ReviewStudioRenderer.render_docx_draft(
        template_bytes=docx_bytes,
        field_values={
            "candidate.full_name": "Priya Sharma",
            "role.title": "Senior Product Designer",
            "role.department": "UX & Design",
            "role.start_date": "2026-11-01",
            "compensation.annual_ctc": "INR 2,200,000",
            "compensation.base_amount": "INR 1,800,000",
        },
    )
    assert len(rendered_bytes) > 0
    assert len(content_sha) == 64

    # Create draft in DB
    draft = DocumentDraft(
        id="draft-studio-1",
        tenant_id="test-dynamic-tenant",
        instance_id="inst-reconcile-test-1",
        template_version_id="mock-ver-1",
        document_name="Appointment Letter — Priya Sharma",
        format="docx",
        storage_key=storage_key,
        content_sha256=content_sha,
        current_approval_status="approved",  # Approved by HR
        approved_by_user_id="usr-hr-admin-1",
        approved_at=datetime.now(timezone.utc),
        bound_approval_sha256=content_sha,
    )
    db_session.add(draft)
    db_session.commit()

    # Generate paginated preview
    pages = ReviewStudioRenderer.generate_paginated_preview(rendered_bytes, paragraphs_per_page=4)
    assert len(pages) >= 1
    assert "EMPLOYMENT AGREEMENT" in pages[0].html_content

    # Now HR edits paragraph or compensation in the draft
    updated_draft = ReviewStudioRenderer.apply_draft_edit(
        db=db_session,
        draft_id="draft-studio-1",
        user_id="usr-hr-admin-1",
        field_overrides={"compensation.annual_ctc": "INR 2,400,000"},
        edit_summary="Increased CTC by 2L",
    )

    # Core Rule: Any edit after approval MUST strictly invalidate approval!
    assert updated_draft.current_approval_status == "draft"
    assert updated_draft.approved_by_user_id is None
    assert updated_draft.approved_at is None
    assert updated_draft.bound_approval_sha256 is None
    assert len(updated_draft.editor_revisions) == 1
    assert updated_draft.editor_revisions[0]["prior_approval_invalidated"] is True


# 6. SCHEDULED DELIVERY & PRE-FLIGHT REVALIDATION TESTS

def test_scheduled_delivery_preflight_revalidation_aborts_on_unapproved_or_modified_draft(db_session):
    draft = db_session.query(DocumentDraft).filter_by(id="draft-studio-1").first()

    # 1. Attempting to schedule an unapproved draft should raise ValueError
    with pytest.raises(ValueError, match="Cannot schedule draft with status 'draft'"):
        DeliverySchedulerService.schedule_delivery(
            db=db_session,
            draft_id="draft-studio-1",
            scheduled_for=datetime.now(timezone.utc) + timedelta(days=1),
            timezone_str="Asia/Kolkata",
            recipient_email="priya.sharma@example.com",
        )

    # 2. Re-approve the draft
    draft.current_approval_status = "approved"
    draft.bound_approval_sha256 = draft.content_sha256
    db_session.commit()

    # Now scheduling succeeds
    delivery = DeliverySchedulerService.schedule_delivery(
        db=db_session,
        draft_id="draft-studio-1",
        scheduled_for=datetime.now(timezone.utc) + timedelta(days=1),
        timezone_str="Asia/Kolkata",
        recipient_email="priya.sharma@example.com",
    )
    assert delivery.status == "scheduled"

    # 3. Simulate pre-flight revalidation when draft is legitimately approved
    success, msg = DeliverySchedulerService.revalidate_and_dispatch(db_session, delivery.id)
    assert success is True
    assert delivery.status == "dispatched"
    assert delivery.dispatched_at is not None

    # 4. Simulate a new scheduled delivery where someone secretly modifies the draft content
    delivery2 = ScheduledDelivery(
        tenant_id="test-dynamic-tenant",
        draft_id="draft-studio-1",
        scheduled_for=datetime.now(timezone.utc),
        timezone="UTC",
        recipient_email="priya.sharma@example.com",
        status="scheduled",
    )
    db_session.add(delivery2)
    # Alter content_sha256 without re-approving
    draft.content_sha256 = "altered_tampered_sha256_abcdef1234567890"
    db_session.commit()

    # Pre-flight revalidation MUST detect the tampering and abort dispatch!
    success2, err_msg = DeliverySchedulerService.revalidate_and_dispatch(db_session, delivery2.id)
    assert success2 is False
    assert delivery2.status == "failed"
    assert "Current content SHA-256 does not match hash bound at approval time" in err_msg


# 7. NODE REGISTRY & GRAPH ORCHESTRATION TESTS

def test_node_registry_completeness():
    """Verify all 15 configurable node types are registered with valid schemas."""
    registry = DynamicWorkflowEngine.get_node_registry()
    assert len(registry) == 15

    types = {item.node_type for item in registry}
    expected_types = {
        "start",
        "generate_document",
        "upload_template",
        "candidate_upload",
        "ai_form_generator",
        "candidate_email",
        "extract_validate",
        "condition_branch",
        "hr_review",
        "approval",
        "wait_schedule",
        "notification",
        "signature",
        "export_archive",
        "end",
    }
    assert types == expected_types

    # Verify category assignments
    categories = {item.category for item in registry}
    assert "Triggers" in categories
    assert "Documents & Templates" in categories
    assert "Candidate Interaction" in categories
    assert "Extraction & Logic" in categories
    assert "Review & Governance" in categories
    assert "Automation & Scheduling" in categories


def test_visual_pipeline_cycle_detection():
    """Verify that illegal loops/cycles in the workflow graph are detected and rejected."""
    cyclic_graph = WorkflowGraphSchema(
        nodes=[
            WorkflowNode(id="n1", name="Step 1", type="start"),
            WorkflowNode(id="n2", name="Step 2", type="generate_document"),
            WorkflowNode(id="n3", name="Step 3", type="hr_review"),
        ],
        edges=[
            WorkflowEdge(id="e1", source="n1", target="n2"),
            WorkflowEdge(id="e2", source="n2", target="n3"),
            WorkflowEdge(id="e3", source="n3", target="n1"),  # Creates a cycle n1 -> n2 -> n3 -> n1
        ],
    )
    is_valid, errors = DynamicWorkflowEngine.validate_graph(cyclic_graph)
    assert is_valid is False
    assert any("cycle" in e.lower() or "loop" in e.lower() for e in errors)


def test_15_node_traversal_and_field_deduplication():
    """Verify end-to-end traversal from Start to End evaluates document generation and deduplicates fields."""
    graph = WorkflowGraphSchema(
        nodes=[
            WorkflowNode(id="start_node", name="Start", type="start"),
            WorkflowNode(
                id="form_node",
                name="AI Form",
                type="ai_form_generator",
                config={"intake_fields": ["candidate.full_name", "candidate.email", "candidate.pan_number"]},
            ),
            WorkflowNode(
                id="upload_node",
                name="Candidate Upload",
                type="candidate_upload",
                config={"required_documents": [{"category": "passport"}, {"category": "tax_id"}]},
            ),
            WorkflowNode(id="branch_node", name="Branch", type="condition_branch"),
            WorkflowNode(
                id="doc_fte",
                name="Executive Agreement",
                type="generate_document",
                config={"template_name": "Executive Employment Agreement", "required_fields": ["candidate.full_name", "compensation.annual_ctc"]},
            ),
            WorkflowNode(id="review_node", name="HR Review", type="hr_review"),
            WorkflowNode(id="approval_node", name="Approval", type="approval"),
            WorkflowNode(id="end_node", name="Complete", type="end"),
        ],
        edges=[
            WorkflowEdge(id="e1", source="start_node", target="form_node"),
            WorkflowEdge(id="e2", source="form_node", target="upload_node"),
            WorkflowEdge(id="e3", source="upload_node", target="branch_node"),
            WorkflowEdge(id="e4", source="branch_node", target="doc_fte", condition="context.employment_type == 'permanent'"),
            WorkflowEdge(id="e5", source="doc_fte", target="review_node"),
            WorkflowEdge(id="e6", source="review_node", target="approval_node"),
            WorkflowEdge(id="e7", source="approval_node", target="end_node"),
        ],
    )

    result = DynamicWorkflowEngine.evaluate_traversal(graph, {"employment_type": "permanent"})
    assert result.is_valid is True
    assert "start_node" in result.traversed_path
    assert "doc_fte" in result.traversed_path
    assert "end_node" in result.traversed_path
    assert "Executive Employment Agreement" in result.evaluated_documents
    # Field deduplication verification
    assert "candidate.full_name" in result.required_candidate_fields
    assert "evidence.passport" in result.required_candidate_fields
    assert len(result.required_candidate_fields) == len(set(result.required_candidate_fields))


def test_custom_required_documents_and_smart_missing_triage():
    # 1. Custom documents configured by HR
    custom_docs = [
        {
            "document_category": "relieving_letter",
            "title": "Previous Employer Relieving Letter",
            "description": "Upload official relieving letter",
            "is_mandatory": True,
        },
        {
            "document_category": "payslips",
            "title": "Last 3 Months Payslips",
            "description": "Salary slips from previous employer",
            "is_mandatory": False,
        },
    ]

    context = {
        "required_documents": custom_docs,
        "company_fields": {
            "department": "Engineering",
            # CTC and Start Date intentionally omitted to test company missing detection
        },
    }

    req_docs = CandidatePortalService.get_required_documents(context)
    assert len(req_docs) == 2
    assert req_docs[0].document_category == "relieving_letter"
    assert req_docs[0].title == "Previous Employer Relieving Letter"
    assert req_docs[0].is_mandatory is True
    assert req_docs[1].is_mandatory is False

    # 2. Smart missing items categorization
    synthesized_fields = CandidatePortalService.synthesize_intake_questionnaire(["candidate.full_name", "candidate.email"])
    field_values = {"candidate.full_name": "John Doe"}  # email is missing

    missing_company, missing_candidate = CandidatePortalService.audit_missing_items(
        context=context,
        synthesized_fields=synthesized_fields,
        required_documents=req_docs,
        uploaded_evidence=[],  # no evidence uploaded yet
        field_values=field_values,
    )

    # Missing from company should detect CTC, Start Date, Signatory
    assert any("CTC" in item for item in missing_company)
    assert any("Start Date" in item for item in missing_company)

    # Missing from candidate should detect missing email and relieving letter (mandatory)
    # But payslips is optional, so it shouldn't block
    assert "Email Address" in missing_candidate
    assert "Previous Employer Relieving Letter" in missing_candidate
    assert "Last 3 Months Payslips" not in missing_candidate


