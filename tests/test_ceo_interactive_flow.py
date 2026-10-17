import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, Tenant
# Required to prevent foreign key errors with sales_companies.deal_room_id in SQLite
from app.models.deal_room import DealRoom
from app.models.verticals import BusinessProfile, Lead, AgentMeeting, ContentPost
from app.models.agents import KnowledgeDocument, ActivityLog
from app.models.workflows import Workflow, WorkflowTask
from app.models.executive import PlanVersion, BudgetEnvelope, WorkflowEvent
from app.models.flow_engine import AgentDefinition
from app.services.executive_os.ceo_interactive_orchestrator import CEOInteractiveOrchestrator


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Seed test tenant
    tenant = Tenant(id="test-tenant-123", name="Acme Enterprises", is_active=True)
    db.add(tenant)

    # Seed BusinessProfile
    bp = BusinessProfile(
        tenant_id="test-tenant-123",
        company_name="Acme Autonomous AI",
        industry="Enterprise B2B Automation",
        service_description="Autonomous AI workforce and SDR pipeline agents.",
        usp="Provable zero-human overhead revenue operations with verifiable cryptographic event ledgers.",
        target_decision_makers=["Chief Revenue Officer", "VP Sales", "CEO"],
        target_industries=["Fintech", "SaaS", "Healthcare"],
        target_countries=["United States", "United Kingdom"],
        offer_details="Enterprise Trial: 100 verified pipeline opportunities in 14 days."
    )
    db.add(bp)

    # Seed KnowledgeDocument
    kd = KnowledgeDocument(
        tenant_id="test-tenant-123",
        department="Marketing",
        doc_type="Brand Guidelines",
        content="Always highlight our verifiable audit ledger and enterprise compliance guarantees.",
        is_active=True
    )
    db.add(kd)
    db.commit()

    try:
        yield db
    finally:
        db.close()


def test_interactive_draft_and_refine_plan(db_session):
    orchestrator = CEOInteractiveOrchestrator(db_session, "test-tenant-123")

    # Step 1: Initial plan draft
    initial_plan = orchestrator.draft_or_refine_plan(
        prompt="Accelerate enterprise SDR pipeline targeting Series B fintech companies",
        budget_cap=30000.0,
        timeline_days=30
    )

    assert initial_plan["plan_id"] is not None
    assert initial_plan["version_num"] == 1
    assert initial_plan["company_name"] == "Acme Autonomous AI"
    assert "Chief Revenue Officer" in initial_plan["target_decision_makers"]
    assert len(initial_plan["assigned_employees"]) >= 3
    assert len(initial_plan["budget_allocations"]) >= 3
    assert initial_plan["status"] == "AWAITING_USER_APPROVAL"

    # Step 2: User review feedback loop
    feedback_text = "Prioritize outbound outreach by Sales AI over broad brand campaigns, and ensure compliance with UK privacy rules"
    refined_plan = orchestrator.draft_or_refine_plan(
        prompt="Accelerate enterprise SDR pipeline targeting Series B fintech companies",
        budget_cap=30000.0,
        timeline_days=30,
        user_feedback=feedback_text,
        feedback_history=initial_plan["feedback_history"],
        workflow_id=initial_plan["workflow_id"]
    )

    assert refined_plan["version_num"] == 2
    assert len(refined_plan["feedback_history"]) == 1
    assert feedback_text in refined_plan["revision_note"]
    assert refined_plan["workflow_id"] == initial_plan["workflow_id"]


def test_interactive_summon_council_meeting(db_session):
    orchestrator = CEOInteractiveOrchestrator(db_session, "test-tenant-123")

    plan = orchestrator.draft_or_refine_plan(
        prompt="Launch outbound SDR sequence for Series B SaaS",
        budget_cap=25000.0
    )

    meeting = orchestrator.conduct_interactive_meeting(
        prompt="Launch outbound SDR sequence for Series B SaaS",
        plan_id=plan["plan_id"],
        budget_cap=25000.0,
        timeline_days=30,
        user_feedback="CFO AI: ensure strict 45-day payback guardrails",
        workflow_id=plan["workflow_id"]
    )

    assert meeting["meeting_id"] is not None
    assert meeting["status"] == "AWAITING_USER_DECISION"
    assert len(meeting["dialogue"]) >= 4

    # Verify dialogue participants include CFO AI, Sales AI, Red Team AI, and CEO AI
    speakers = [d["speaker_name"] for d in meeting["dialogue"]]
    assert "CFO AI" in speakers
    assert "Sales AI" in speakers
    assert "Red Team AI" in speakers
    assert "CEO AI" in speakers

    # Verify ROI scorecard
    roi = meeting["roi_scorecard"]
    assert roi["optimized_roi"] > roi["initial_roi"]
    assert roi["payback_months"] > 0
    assert len(roi["key_optimizations"]) > 0

    # Verify meeting recorded in DB
    db_meeting = db_session.query(AgentMeeting).filter_by(id=meeting["meeting_id"]).first()
    assert db_meeting is not None
    assert db_meeting.status == "completed"


def test_interactive_assign_and_execute(db_session):
    orchestrator = CEOInteractiveOrchestrator(db_session, "test-tenant-123")

    plan = orchestrator.draft_or_refine_plan(
        prompt="B2B outbound sales execution",
        budget_cap=20000.0
    )

    meeting = orchestrator.conduct_interactive_meeting(
        prompt="B2B outbound sales execution",
        plan_id=plan["plan_id"],
        budget_cap=20000.0,
        workflow_id=plan["workflow_id"]
    )

    team_status = orchestrator.assign_and_execute(
        workflow_id=plan["workflow_id"],
        plan_id=plan["plan_id"],
        meeting_id=meeting["meeting_id"]
    )

    assert team_status["workflow_id"] == plan["workflow_id"]
    assert team_status["overall_progress_pct"] > 0
    assert len(team_status["employees"]) >= 4

    # Verify real deliverables created in database
    leads = db_session.query(Lead).filter_by(tenant_id="test-tenant-123").all()
    assert len(leads) >= 3
    # Check lead was assigned to Sales AI (or tenant employee)
    sales_leads = [l for l in leads if "Sales AI" in (l.assigned_to or "")]
    assert len(sales_leads) >= 1

    # Check Workflow status updated to RUNNING
    wf = db_session.query(Workflow).filter_by(id=plan["workflow_id"]).first()
    assert wf.status == "RUNNING"

    # Check WorkflowTasks created
    tasks = db_session.query(WorkflowTask).filter_by(workflow_id=plan["workflow_id"]).all()
    assert len(tasks) >= 4


def test_interactive_get_team_status(db_session):
    orchestrator = CEOInteractiveOrchestrator(db_session, "test-tenant-123")

    plan = orchestrator.draft_or_refine_plan(prompt="Test workflow team status")
    orchestrator.assign_and_execute(
        workflow_id=plan["workflow_id"],
        plan_id=plan["plan_id"]
    )

    status = orchestrator.get_team_status(plan["workflow_id"])
    assert status["active_workforce_count"] >= 4
    for emp in status["employees"]:
        assert "name" in emp["employee"]
        assert "avatar" in emp["employee"]
        assert "status" in emp
        assert "progress_pct" in emp
        assert "active_task" in emp
        assert len(emp["deliverables"]) >= 1


def test_interactive_workspace_lifecycle(db_session):
    orchestrator = CEOInteractiveOrchestrator(db_session, "test-tenant-123")

    # 1. Create a plan and meeting
    plan = orchestrator.draft_or_refine_plan(prompt="Lifecycle Test Strategy Directive")
    wf_id = plan["workflow_id"]
    orchestrator.conduct_interactive_meeting(
        prompt="Lifecycle Test Strategy Directive",
        plan_id=plan["plan_id"],
        workflow_id=wf_id
    )

    # 2. List workspaces
    workspaces = orchestrator.list_workspaces()
    assert len(workspaces) >= 1
    found = next((w for w in workspaces if w["id"] == wf_id), None)
    assert found is not None
    assert found["has_meeting"] is True

    # 3. Get workspace state
    state = orchestrator.get_workspace_state(wf_id)
    assert state["workflow"]["id"] == wf_id
    assert state["plan"] is not None
    assert state["meeting"] is not None

    # 4. Delete workspace
    success = orchestrator.delete_workspace(wf_id)
    assert success is True

    # 5. Verify deleted from list
    workspaces_after = orchestrator.list_workspaces()
    assert not any(w["id"] == wf_id for w in workspaces_after)


def test_cto_and_custom_agent_decision_and_grounding(db_session):
    orchestrator = CEOInteractiveOrchestrator(db_session, "test-tenant-123")

    # 1. Update business profile to match AlienHouse Networks (Software Development, targeting CTOs)
    bp = db_session.query(BusinessProfile).filter_by(tenant_id="test-tenant-123").first()
    bp.company_name = "AlienHouse Networks"
    bp.industry = "Software Development"
    bp.usp = "Zero-human overhead multi-agent executive automation with verifiable ledger auditability."
    bp.target_decision_makers = ["CEO", "VP Sales", "Chief Revenue Officer", "CTO"]
    db_session.commit()

    # 2. Seed a custom-built agent
    custom_agent = AgentDefinition(
        id="custom_devops_lead",
        tenant_id="test-tenant-123",
        name="Kaelen Frost",
        slug="devops-lead",
        department="operations",
        role="DevOps & Infrastructure Architect",
        description="Kubernetes multi-region failover and ledger sync operations"
    )
    db_session.add(custom_agent)
    db_session.commit()

    # 3. Test agent council selection for technical software directive
    selection = orchestrator.select_council_participants(
        prompt="Deploy automated microservices pipeline with Kubernetes failover targeting enterprise CTOs"
    )

    summoned_roles = [a["agent_role"] for a in selection["summoned_agents"]]
    summoned_names = [a["name"] for a in selection["summoned_agents"]]

    # Verify Technical AI is summoned
    assert "Technical AI" in summoned_roles
    technical = next(a for a in selection["summoned_agents"] if a["agent_role"] == "Technical AI")
    assert "software development" in technical["attendance_reason"].lower() or "cto" in technical["attendance_reason"].lower()

    # Verify custom-built agent is summoned based on specialized capabilities match
    assert "Kaelen Frost" in summoned_names
    kaelen = next(a for a in selection["summoned_agents"] if a["name"] == "Kaelen Frost")
    assert "Specialized capabilities" in kaelen["attendance_reason"]

    # Verify mandatory governance agents (CFO and Red Team) are summoned
    assert "CFO AI" in summoned_roles
    assert "Red Team AI" in summoned_roles

    # 4. Test council meeting includes Technical AI dialogue
    plan = orchestrator.draft_or_refine_plan(
        prompt="Deploy automated microservices pipeline with Kubernetes failover targeting enterprise CTOs",
        budget_cap=35000.0
    )
    meeting = orchestrator.conduct_interactive_meeting(
        prompt="Deploy automated microservices pipeline with Kubernetes failover targeting enterprise CTOs",
        plan_id=plan["plan_id"],
        budget_cap=35000.0,
        workflow_id=plan["workflow_id"]
    )

    speakers = [d["speaker_name"] for d in meeting["dialogue"]]
    assert "Technical AI" in speakers
    assert "Kaelen Frost" in speakers
    assert "CEO AI" in speakers

    tech_turn = next(d for d in meeting["dialogue"] if d["speaker_name"] == "Technical AI")
    assert tech_turn["agent_role"] == "Technical AI"
    assert "Technical AI, CTO" in tech_turn["message"]
    assert "AlienHouse Networks" in tech_turn["message"]

    # 5. Execute plan and verify team status contains Technical AI deliverables
    team_status = orchestrator.assign_and_execute(
        workflow_id=plan["workflow_id"],
        plan_id=plan["plan_id"],
        meeting_id=meeting["meeting_id"]
    )

    status_roles = [e["employee"]["agent_role"] for e in team_status["employees"]]
    assert "Technical AI" in status_roles

    tech_status = next(e for e in team_status["employees"] if e["employee"]["agent_role"] == "Technical AI")
    assert len(tech_status["deliverables"]) >= 1
    assert tech_status["deliverables"][0]["type"] == "TECHNICAL"


def test_ten_agents_critique_loop_and_live_dag_transcripts(db_session):
    from app.services.executive_os.ceo_interactive_orchestrator import EMPLOYEE_DIRECTORY

    # 1. Verify 10 AI Agents in Executive Directory
    assert len(EMPLOYEE_DIRECTORY) == 10
    expected_roles = [
        "Marketing AI", "Sales AI", "CFO AI", "HR AI", "Customer Support AI",
        "Technical AI", "Red Team AI", "Operations AI", "Product AI", "Legal AI"
    ]
    for role in expected_roles:
        assert role in EMPLOYEE_DIRECTORY
        assert EMPLOYEE_DIRECTORY[role]["is_custom"] is False
        assert "avatar" in EMPLOYEE_DIRECTORY[role]
        assert len(EMPLOYEE_DIRECTORY[role]["skills"]) >= 2

    # 2. Verify Autonomous 3-Agent Critique Loop during planning
    bp = db_session.query(BusinessProfile).filter_by(tenant_id="test-tenant-123").first()
    bp.company_name = "AlienHouse Networks"
    bp.industry = "Software Development"
    bp.usp = "Zero-human overhead multi-agent executive automation with verifiable ledger auditability."
    bp.target_decision_makers = ["CEO", "VP Sales", "Chief Revenue Officer", "CTO"]
    db_session.commit()

    orchestrator = CEOInteractiveOrchestrator(db_session, "test-tenant-123")
    plan = orchestrator.draft_or_refine_plan(
        prompt="Launch high-growth B2B enterprise SDR automation with SOC2 compliance and zero-human overhead",
        budget_cap=50000.0,
        timeline_days=30
    )

    # Check consensus status and phrase
    assert plan["consensus_status"] == "UNANIMOUS_CONSENSUS"
    assert plan["consensus_phrase"] == "We can do it"
    assert "Unanimous council consensus achieved" in plan["consensus_rationale"]

    # Check 3 critics in critique loop history
    critique_history = plan["critique_loop_history"]
    assert len(critique_history) == 2  # Round 1 issues + Round 2 consensus
    assert critique_history[0]["status"] == "ISSUES_IDENTIFIED"
    assert critique_history[1]["status"] == "UNANIMOUS_CONSENSUS"

    critics_r1 = [c["critic_name"] for c in critique_history[0]["critiques"]]
    assert "Technical AI" in critics_r1  # Technical Critic
    assert "CFO AI" in critics_r1  # Financial Critic (CFO)
    assert "Red Team AI" in critics_r1  # Adversarial Critic (Red Team)

    critics_r2 = [c["verdict"] for c in critique_history[1]["critiques"]]
    assert all(v == "We can do it" for v in critics_r2)

    # Check fact grounding matrix
    facts = plan["source_facts_matrix"]
    assert facts["organization"] == "AlienHouse Networks"
    assert facts["industry"] == "Software Development"
    assert "Zero-human overhead" in facts["core_usp"]
    assert len(facts["sources_cited"]) >= 4

    # 3. Verify Topological DAG Nodes have Live Transcripts
    nodes = plan["nodes"]
    assert len(nodes) == 6
    for node in nodes:
        params = node["parameters"]
        assert "assigned_agent" in params
        assert "live_transcript" in params
        transcript = params["live_transcript"]
        assert len(transcript) >= 2
        for entry in transcript:
            assert "speaker" in entry
            assert "thought" in entry
            assert "action" in entry
            assert "result" in entry
            assert "timestamp" in entry

    # Verify node 2 is Technical AI and node 6 is Operations AI
    node_2 = next(n for n in nodes if n["id"].endswith("_2"))
    assert node_2["parameters"]["assigned_agent"] == "Technical AI"
    assert node_2["department"] == "ENGINEERING"

    node_6 = next(n for n in nodes if n["id"].endswith("_6"))
    assert node_6["parameters"]["assigned_agent"] == "Operations AI"
    assert node_6["department"] == "OPERATIONS"



