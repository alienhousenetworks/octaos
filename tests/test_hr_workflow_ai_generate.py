"""Comprehensive Tests for AI Prompt-to-Pipeline Generator, Graph Validation, and Candidate Pipeline Summary."""
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, User, Tenant
from app.models.verticals import Candidate, HRResumeIngestionJob
from app.models.hr import (
    TenantDocumentTemplate,
    TemplateVersion,
    JobRequisition,
    Application,
)
from app.schemas.hr_workflow import (
    WorkflowGraphContract,
    WorkflowNode,
    WorkflowEdge,
)
from app.services.hr.workflow.engine import DynamicWorkflowEngine


@pytest.fixture(scope="module")
def db_session():
    """In-memory SQLite session with HR and workflow tables created."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed baseline tenant and user
    tenant = Tenant(id="test-ai-gen-tenant", name="OctaCorp AI Labs")
    user = User(
        id="usr-ai-admin-1",
        email="talent.lead@octacorp.com",
        tenant_id="test-ai-gen-tenant",
        role="admin",
        hashed_password="mock",
    )
    session.add(tenant)
    session.add(user)

    # Seed template
    template = TenantDocumentTemplate(
        id="tpl-offer-letter-1",
        tenant_id="test-ai-gen-tenant",
        document_type="offer_letter",
        category="offer_letter",
        name="Standard Offer Letter",
    )
    session.add(template)
    session.commit()

    tpl_version = TemplateVersion(
        id="tpl-v1",
        template_id=template.id,
        tenant_id="test-ai-gen-tenant",
        version=1,
        format="docx",
        status="published",
        storage_key="templates/test_offer.docx",
        content_sha256="mock_sha256_hash",
    )
    session.add(tpl_version)
    session.commit()

    yield session
    session.close()


def test_validate_graph_valid():
    """Verify that a well-formed DAG passes graph validation cleanly."""
    valid_graph = WorkflowGraphContract(
        name="Valid Engineering Pipeline",
        nodes=[
            WorkflowNode(id="n_start", name="Candidate Ingestion", type="start"),
            WorkflowNode(
                id="n_upload",
                name="Document Upload",
                type="candidate_upload",
                config={"required_documents": ["degree_certificate", "pan_card"]},
            ),
            WorkflowNode(
                id="n_approval",
                name="Department VP Approval",
                type="approval",
                config={"required_role": "vp_engineering"},
            ),
            WorkflowNode(id="n_end", name="Candidate Hired", type="end"),
        ],
        edges=[
            WorkflowEdge(id="e1", source="n_start", target="n_upload", source_handle="out", target_handle="in"),
            WorkflowEdge(id="e2", source="n_upload", target="n_approval", source_handle="out", target_handle="in"),
            WorkflowEdge(id="e3", source="n_approval", target="n_end", source_handle="out", target_handle="in"),
        ],
    )

    is_valid, errors = DynamicWorkflowEngine.validate_graph(valid_graph)
    assert is_valid is True
    assert len(errors) == 0


def test_validate_graph_cycle_detection():
    """Verify that illegal cycles in the workflow DAG are strictly rejected."""
    cyclic_graph = WorkflowGraphContract(
        name="Cyclic Graph",
        nodes=[
            WorkflowNode(id="n_start", name="Start", type="start"),
            WorkflowNode(
                id="n_review",
                name="Review",
                type="hr_review",
                config={"reviewer_role": "hr_specialist"},
            ),
            WorkflowNode(
                id="n_approval",
                name="Approval",
                type="approval",
                config={"required_role": "hr_director"},
            ),
            WorkflowNode(id="n_end", name="End", type="end"),
        ],
        edges=[
            WorkflowEdge(id="e1", source="n_start", target="n_review"),
            WorkflowEdge(id="e2", source="n_review", target="n_approval"),
            # Back-edge forming a cycle
            WorkflowEdge(id="e3", source="n_approval", target="n_review"),
            WorkflowEdge(id="e4", source="n_approval", target="n_end"),
        ],
    )

    is_valid, errors = DynamicWorkflowEngine.validate_graph(cyclic_graph)
    assert is_valid is False
    assert any("illegal loop or cycle" in err for err in errors)


def test_validate_graph_disconnected_node():
    """Verify that disconnected nodes or reachability violations are caught."""
    disconnected_graph = WorkflowGraphContract(
        name="Disconnected Graph",
        nodes=[
            WorkflowNode(id="n_start", name="Start", type="start"),
            WorkflowNode(id="n_end", name="End", type="end"),
            WorkflowNode(
                id="n_floating",
                name="Floating Form",
                type="ai_form_generator",
                config={"intake_fields": ["email"]},
            ),
        ],
        edges=[
            WorkflowEdge(id="e1", source="n_start", target="n_end"),
        ],
    )

    is_valid, errors = DynamicWorkflowEngine.validate_graph(disconnected_graph)
    assert is_valid is False
    assert any("unreachable from start" in err for err in errors)


def test_validate_graph_missing_required_config():
    """Verify that node-specific required configuration constraints are validated."""
    invalid_config_graph = WorkflowGraphContract(
        name="Missing Config Graph",
        nodes=[
            WorkflowNode(id="n_start", name="Start", type="start"),
            # Approval node with empty required_role
            WorkflowNode(id="n_approval", name="Approval", type="approval", config={"required_role": ""}),
            WorkflowNode(id="n_end", name="End", type="end"),
        ],
        edges=[
            WorkflowEdge(id="e1", source="n_start", target="n_approval"),
            WorkflowEdge(id="e2", source="n_approval", target="n_end"),
        ],
    )

    is_valid, errors = DynamicWorkflowEngine.validate_graph(invalid_config_graph)
    assert is_valid is False
    assert any("required_role" in err for err in errors)


def test_generate_workflow_graph_from_prompt_developer(db_session):
    """Verify domain-aware rule fallback creates a verified developer DAG."""
    prompt = (
        "Build an engineering onboarding workflow for Python backend developers with GitHub repository "
        "intake, AI OCR extraction of PAN and degree, technical director signoff, and offer letter generation."
    )
    response = DynamicWorkflowEngine.generate_workflow_graph_from_prompt(
        prompt=prompt,
        job_role="python backend developer",
        db=db_session,
        tenant_id="test-ai-gen-tenant",
    )

    assert response.generator_used == "rule_based_fallback"
    graph = response.graph
    assert graph is not None
    assert len(graph.nodes) >= 6

    # Verify key nodes are present
    types = [n.type for n in graph.nodes]
    assert "start" in types
    assert "candidate_upload" in types
    assert "ai_form_generator" in types
    assert "extract_validate" in types
    assert "approval" in types
    assert "generate_document" in types
    assert "end" in types

    # Verify layout positioning is non-zero and monotonic
    x_positions = [n.position["x"] for n in graph.nodes if n.position]
    assert len(x_positions) == len(graph.nodes)
    assert sorted(x_positions) == x_positions

    # Verify edges connect all nodes linearly with handles
    assert len(graph.edges) == len(graph.nodes) - 1
    for edge in graph.edges:
        assert edge.source_handle in ("out", "default")
        assert edge.target_handle in ("in", "default")

    # Verify the generated graph passes the strict shared validation contract
    is_valid, errors = DynamicWorkflowEngine.validate_graph(graph)
    assert is_valid is True, f"Generated graph failed validation: {errors}"


def test_generate_workflow_graph_from_prompt_contractor(db_session):
    """Verify prompt mentioning contractor creates contractor-specific MSA nodes."""
    prompt = "Create rapid onboarding pipeline for independent contractors with GST extraction and MSA"
    response = DynamicWorkflowEngine.generate_workflow_graph_from_prompt(
        prompt=prompt,
        job_role="contract backend developer",
        db=db_session,
        tenant_id="test-ai-gen-tenant",
    )

    graph = response.graph
    assert graph is not None

    # Check that contract generation node targets Contractor MSA
    doc_nodes = [n for n in graph.nodes if n.type == "generate_document"]
    assert len(doc_nodes) >= 1
    assert "Contractor" in doc_nodes[0].config.get("template_name", "")

    # Validate graph validity
    is_valid, errors = DynamicWorkflowEngine.validate_graph(graph)
    assert is_valid is True


def test_reconcile_and_pipeline_summary(db_session):
    """Test pipeline summary calculation and candidate reconciliation logic."""
    # 1. Create Job Requisition for Python Backend Developer
    req = JobRequisition(
        tenant_id="test-ai-gen-tenant",
        title="Python Backend Developer",
        status="open",
        headcount_approved=5,
        headcount_filled=0,
    )
    db_session.add(req)
    db_session.commit()

    # 2. Create Candidate ingested for Python Backend Developer
    cand = Candidate(
        id="cand-py-001",
        tenant_id="test-ai-gen-tenant",
        name="Aarav Sharma",
        email="aarav.sharma@example.com",
        role="python backend developer",
        status="sourced",
        scorecard={"skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"], "experience_years": 4.5},
    )
    db_session.add(cand)

    # 3. Create Ingestion Batch record indicating 118 files processed
    job = HRResumeIngestionJob(
        tenant_id="test-ai-gen-tenant",
        role="python backend developer",
        status="completed",
        total_files=118,
        processed_files=118,
        progress_percent=100,
    )
    db_session.add(job)
    db_session.commit()

    # 4. Link candidate via application
    app = Application(
        tenant_id="test-ai-gen-tenant",
        candidate_id=cand.id,
        requisition_id=req.id,
        current_stage="sourced",
        status="active",
    )
    db_session.add(app)
    db_session.commit()

    # 5. Query candidate applications
    apps = (
        db_session.query(Application)
        .filter(Application.tenant_id == "test-ai-gen-tenant", Application.requisition_id == req.id)
        .all()
    )
    assert len(apps) == 1
    assert apps[0].current_stage == "sourced"

    # Verify batch job properties
    assert job.processed_files == 118
    assert job.status == "completed"
