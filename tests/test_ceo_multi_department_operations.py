import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, Tenant, APICredential
from app.models.deal_room import DealRoom, BuyingCommitteeMember
from app.models.verticals import BusinessProfile, Lead, ContentPost, Ticket
from app.models.agents import KnowledgeDocument, ActivityLog
from app.models.workflows import Workflow, WorkflowTask
from app.models.executive import PlanVersion, BudgetEnvelope
from app.services.executive_os.ceo_interactive_orchestrator import CEOInteractiveOrchestrator


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    tenant = Tenant(id="test-tenant-ops", name="OmniCorp Global", is_active=True)
    db.add(tenant)

    bp = BusinessProfile(
        tenant_id="test-tenant-ops",
        company_name="OmniCorp AI",
        industry="Enterprise Software & AI",
        service_description="Next-generation autonomous agent orchestration platform.",
        usp="Zero-human overhead pipeline execution with verifiable cryptographically sealed ledgers.",
        target_decision_makers=["Chief Executive Officer", "Chief Revenue Officer", "VP Sales"],
        target_industries=["SaaS", "FinTech", "Healthcare"],
        target_countries=["United States", "Germany"],
        offer_details="Enterprise Accelerator: 50 qualified opportunities in 30 days."
    )
    db.add(bp)
    db.commit()

    try:
        yield db
    finally:
        db.close()


def test_generate_scheduled_campaign(db_session):
    orchestrator = CEOInteractiveOrchestrator(db_session, "test-tenant-ops")
    posts = orchestrator.generate_scheduled_campaign(workflow_id="wf-test-camp", days=14)

    assert len(posts) > 0
    # Verify ContentPosts persisted in database
    db_posts = db_session.query(ContentPost).filter_by(tenant_id="test-tenant-ops").all()
    assert len(db_posts) >= len(posts)

    # Check platforms, status and scheduled_at
    platforms = {p.platform for p in db_posts}
    assert "linkedin" in platforms
    for p in db_posts:
        assert p.status == "scheduled"
        assert p.scheduled_at is not None
        assert p.day is not None
        assert "OmniCorp AI" in p.content


def test_assign_and_execute_multi_department(db_session):
    orchestrator = CEOInteractiveOrchestrator(db_session, "test-tenant-ops")

    # Draft plan first
    plan_data = orchestrator.draft_or_refine_plan(
        prompt="Launch outbound B2B expansion for New York FinTech enterprises",
        budget_cap=30000.0,
        timeline_days=30
    )
    wf_id = plan_data["workflow_id"]
    plan_id = plan_data["plan_id"]

    # Assign and execute
    team_status = orchestrator.assign_and_execute(workflow_id=wf_id, plan_id=plan_id)

    # 1. Verify Sales Pipeline & Deal Rooms created
    deals = db_session.query(DealRoom).filter_by(tenant_id="test-tenant-ops").all()
    assert len(deals) >= 3
    for d in deals:
        assert d.stage == "outreach_ready"
        assert d.icp_fit_score >= 0.9
        assert d.next_best_action is not None

    # Verify BuyingCommitteeMembers
    members = db_session.query(BuyingCommitteeMember).filter_by(tenant_id="test-tenant-ops").all()
    assert len(members) >= 3

    # 2. Verify Leads created with outreach drafts
    leads = db_session.query(Lead).filter_by(tenant_id="test-tenant-ops").all()
    assert len(leads) >= 3
    for l in leads:
        assert "outreach_email" in l.data
        assert l.data["outreach_email"]["recipient"] == l.email

    # 3. Verify Scheduled Social Posts created
    posts = db_session.query(ContentPost).filter_by(tenant_id="test-tenant-ops", status="scheduled").all()
    assert len(posts) >= 3

    # 4. Verify Customer Support configured
    cred = db_session.query(APICredential).filter_by(tenant_id="test-tenant-ops", provider="support").first()
    assert cred is not None
    assert cred.settings.get("reply_mode") == "review_first"

    # Verify Campaign FAQ Knowledge Document seeded
    faq_doc = db_session.query(KnowledgeDocument).filter_by(
        tenant_id="test-tenant-ops",
        department="Support",
        doc_type="Campaign FAQ"
    ).first()
    assert faq_doc is not None
    assert "OmniCorp AI" in faq_doc.content

    # 5. Verify Employee directory status contains Customer Support AI
    roles_in_team = [e["employee"]["agent_role"] for e in team_status["employees"]]
    assert "Sales AI" in roles_in_team
    assert "Marketing AI" in roles_in_team
    assert "Customer Support AI" in roles_in_team


def test_advance_sales_pipeline_stage(db_session):
    orchestrator = CEOInteractiveOrchestrator(db_session, "test-tenant-ops")

    deal = DealRoom(
        tenant_id="test-tenant-ops",
        company_name="Apex Global",
        domain="apexglobal.io",
        stage="outreach_ready",
        icp_fit_score=0.95
    )
    db_session.add(deal)
    db_session.commit()

    updated = orchestrator.advance_sales_pipeline_stage(deal.id, "in_cadence")
    assert updated["stage"] == "in_cadence"

    # Verify in DB
    refreshed = db_session.query(DealRoom).filter_by(id=deal.id).first()
    assert refreshed.stage == "in_cadence"


def test_configure_support_policy(db_session):
    orchestrator = CEOInteractiveOrchestrator(db_session, "test-tenant-ops")

    res = orchestrator.configure_support_policy(reply_mode="auto_send", auto_replies={"email_auto_reply": False})
    assert res["reply_mode"] == "auto_send"
    assert res["settings"]["email_auto_reply"] is False

    cred = db_session.query(APICredential).filter_by(tenant_id="test-tenant-ops", provider="support").first()
    assert cred.settings["reply_mode"] == "auto_send"


def test_dispatch_executive_email_preview_and_lead(db_session):
    orchestrator = CEOInteractiveOrchestrator(db_session, "test-tenant-ops")

    # 1. Test preview email (safe handler when no SMTP/Gmail configured)
    test_res = orchestrator.dispatch_executive_email(test_email="ceo@omnicorp.ai")
    assert test_res["type"] == "test_email"
    assert test_res["recipient"] == "ceo@omnicorp.ai"
    assert "result" in test_res

    # 2. Lead email dispatch
    lead = Lead(
        tenant_id="test-tenant-ops",
        name="Sarah Connor",
        company="Cyberdyne Systems",
        email="sconnor@cyberdyne.tech",
        status="qualified",
        data={
            "outreach_email": {
                "subject": "Strategic Automation",
                "body": "Hello Sarah, let's connect.",
                "status": "ready"
            }
        }
    )
    db_session.add(lead)
    db_session.commit()

    lead_res = orchestrator.dispatch_executive_email(lead_id=lead.id)
    assert lead_res["type"] == "lead_outreach"
    assert lead_res["recipient"] == "sconnor@cyberdyne.tech"


def test_get_operations_overview(db_session):
    orchestrator = CEOInteractiveOrchestrator(db_session, "test-tenant-ops")

    # Seed data across pillars
    deal = DealRoom(
        tenant_id="test-tenant-ops",
        company_name="Alpha Tech",
        domain="alphatech.com",
        stage="outreach_ready",
        priority_index=0.88
    )
    post = ContentPost(
        tenant_id="test-tenant-ops",
        platform="linkedin",
        content="Insightful industry update.",
        day=1,
        status="scheduled",
        scheduled_at=datetime.now(timezone.utc)
    )
    db_session.add_all([deal, post])
    db_session.commit()

    overview = orchestrator.get_operations_overview(workflow_id="wf-test-ops")

    assert overview["company_name"] == "OmniCorp AI"
    assert "campaign" in overview
    assert overview["campaign"]["total_posts"] >= 1
    assert "sales_pipeline" in overview
    assert overview["sales_pipeline"]["deal_rooms_count"] >= 1
    assert "support" in overview
    assert "email_dispatch" in overview
