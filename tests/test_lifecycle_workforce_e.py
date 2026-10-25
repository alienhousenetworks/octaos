"""Unit and Integration Tests for OctaOS Customer Lifecycle Workforce E (Agents E1 to E8),
Governance Kernel, and Automation Scorecard.
"""
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.deal_room import SuppressionRecord
from app.models.verticals import Lead, ContentPost
from app.models.lifecycle import CustomerIdentity, AudienceSegment, CommunicationLog
from app.services.lifecycle.contracts import (
    AgentExecutionEnvelope,
    ExecutionStatus,
    CampaignMode,
    ReengagementMode,
    SuppressionDecision,
    LeadCaptureInput,
    LeadEnrichmentInput,
    EmailCampaignInput,
    LifecycleJourneyInput,
    CustomerSegmentationInput,
    SuppressionCheckInput,
    RetentionRiskInput,
    ReengagementInput,
)
from app.services.sales_os.lifecycle.lead_capture_agent import LeadCaptureRoutingAgent
from app.services.sales_os.lifecycle.lead_enrichment_agent import LeadEnrichmentQualificationAgent
from app.services.marketing.campaign_os.email_architect import EmailCampaignArchitectAgent
from app.services.lifecycle.nurture_agent import LifecycleNurtureAgent
from app.services.lifecycle.segmentation_agent import CustomerSegmentationAgent
from app.services.lifecycle.suppression_agent import DeliverabilitySuppressionAgent
from app.services.lifecycle.churn_signal_agent import RetentionChurnSignalAgent
from app.services.lifecycle.reengagement_agent import ReengagementReferralAgent
from app.services.lifecycle.governance_kernel import GovernanceKernel
from app.services.lifecycle.automation_scorecard import MarketingAutomationScorecardService


@pytest.fixture
def db_session():
    """In-memory SQLite test database session."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_agent_execution_envelope_schema():
    """Verify canonical execution envelope serialization and default fields."""
    env = AgentExecutionEnvelope(
        tenant_id="tenant_123",
        request_id="req_456",
        workflow_id="wf_789",
        agent_id="test_agent",
        objective="Verify envelope validation",
        idempotency_key="idemp_001",
    )
    assert env.status == ExecutionStatus.COMPLETED
    assert env.agent_version == "1.0.0"
    data = env.model_dump()
    assert data["tenant_id"] == "tenant_123"
    assert data["idempotency_key"] == "idemp_001"


@pytest.mark.asyncio
async def test_agent_e1_lead_capture_and_routing(db_session):
    """Verify Agent E1 captures, normalizes, and routes an inbound lead."""
    agent = LeadCaptureRoutingAgent(db_session, "tenant_test")
    env = AgentExecutionEnvelope(
        tenant_id="tenant_test",
        request_id="req_e1",
        workflow_id="wf_e1",
        agent_id="lead_capture",
        objective="Capture inbound lead",
        idempotency_key="idemp_e1_01",
    )
    inp = LeadCaptureInput(
        source_type="website_demo_form",
        source_event_id="evt_web_123",
        lead_payload={
            "name": "Alex Mercer",
            "email": "alex.mercer@enterprise.com",
            "phone": "+1-555-0199",
            "company": "Apex Industries",
        },
        attribution_metadata={"utm_source": "google_search"},
    )

    with patch.object(agent.llm, "complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = '{"match_status": "NEW_RECORD", "routing_decision": "ASSIGNED", "assigned_owner": "Enterprise Rep A", "next_action": "lead.qualification.evaluate"}'
        res_env = await agent.execute(env, inp)

    assert res_env.status == ExecutionStatus.COMPLETED
    out = res_env.output
    assert out["match_status"] == "NEW_RECORD"
    assert out["routing_decision"] == "ASSIGNED"
    assert out["assigned_owner"] == "Enterprise Rep A"

    # Verify persisted in DB
    lead = db_session.query(Lead).filter(Lead.email == "alex.mercer@enterprise.com").first()
    assert lead is not None
    assert lead.company == "Apex Industries"


@pytest.mark.asyncio
async def test_agent_e2_lead_enrichment_and_qualification(db_session):
    """Verify Agent E2 computes transparent fit and intent scores."""
    # Seed a lead in DB
    lead = Lead(
        tenant_id="tenant_test",
        name="Sarah Connor",
        email="sconnor@cyberdyne.io",
        company="Cyberdyne",
        status="captured",
    )
    db_session.add(lead)
    db_session.commit()

    agent = LeadEnrichmentQualificationAgent(db_session, "tenant_test")
    env = AgentExecutionEnvelope(
        tenant_id="tenant_test",
        request_id="req_e2",
        workflow_id="wf_e2",
        agent_id="lead_enrichment",
        objective="Qualify lead",
        idempotency_key="idemp_e2_01",
    )
    inp = LeadEnrichmentInput(
        lead_id=lead.id,
        lead_record={"company": "Cyberdyne", "email": "sconnor@cyberdyne.io", "industry": "Robotics"},
        icp_profile={"target_industry": "Robotics"},
    )

    with patch.object(agent.llm, "complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = '{"fit_score": 92.0, "intent_score": 88.0, "completeness_score": 85.0, "qualification_status": "QUALIFIED", "reason_codes": ["ICP_ROBOTICS_MATCH"], "recommended_next_action": "sales.rep.schedule_discovery"}'
        res_env = await agent.execute(env, inp)

    assert res_env.status == ExecutionStatus.COMPLETED
    out = res_env.output
    assert out["fit_score"] == 92.0
    assert out["qualification_status"] == "QUALIFIED"

    # Verify lead updated in DB
    db_session.refresh(lead)
    assert lead.score == 90
    assert lead.status == "qualified"


@pytest.mark.asyncio
async def test_agent_e3_email_campaign_architect_marketing_mode(db_session):
    """Verify Agent E3 generates structured campaign brief and message variants."""
    agent = EmailCampaignArchitectAgent(db_session, "tenant_test")
    env = AgentExecutionEnvelope(
        tenant_id="tenant_test",
        request_id="req_e3",
        workflow_id="wf_e3",
        agent_id="email_architect",
        objective="Product launch email",
        idempotency_key="idemp_e3_01",
    )
    inp = EmailCampaignInput(
        campaign_mode=CampaignMode.MARKETING,
        objective="Q4 Enterprise Automation Launch",
        audience_ref="aud_vp_engineering",
        approved_claims=["99.99% uptime verified"],
    )

    with patch.object(agent.llm, "complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = '{"campaign_brief": "Executive briefing on automated resilience", "message_variants": [{"variant_id": "v1", "subject_line": "Scaling Autonomous Operations", "preview_text": "Verified operational benchmarks", "body_markdown": "Hello {{first_name}}, see our results.", "cta_copy": "Explore Platform", "cta_url_placeholder": "https://example.com/demo", "personalization_fields": ["first_name"]}]}'
        res_env = await agent.execute(env, inp)

    assert res_env.status == ExecutionStatus.COMPLETED
    out = res_env.output
    assert out["campaign_mode"] == "MARKETING"
    assert len(out["message_variants"]) == 1
    assert out["message_variants"][0]["subject_line"] == "Scaling Autonomous Operations"


@pytest.mark.asyncio
async def test_agent_e4_lifecycle_nurture_agent(db_session):
    """Verify Agent E4 advances journey progression without competing sequence engines."""
    agent = LifecycleNurtureAgent(db_session, "tenant_test")
    env = AgentExecutionEnvelope(
        tenant_id="tenant_test",
        request_id="req_e4",
        workflow_id="wf_e4",
        agent_id="lifecycle_nurture",
        objective="Advance onboarding sequence",
        idempotency_key="idemp_e4_01",
    )
    inp = LifecycleJourneyInput(
        contact_ref="contact_001",
        lifecycle_state="onboarding_day_1",
        triggering_event={"event_name": "user_logged_in_first_time"},
        journey_type="ONBOARDING",
    )

    with patch.object(agent.llm, "complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = '{"journey_ref": "journey_onboarding_v1", "previous_state": "onboarding_day_1", "new_state": "onboarding_day_3", "next_action": "send_getting_started_guide", "scheduled_step_refs": ["step_guide_email"], "eligibility_decision": "ELIGIBLE"}'
        res_env = await agent.execute(env, inp)

    assert res_env.status == ExecutionStatus.COMPLETED
    out = res_env.output
    assert out["eligibility_decision"] == "ELIGIBLE"
    assert out["new_state"] == "onboarding_day_3"


@pytest.mark.asyncio
async def test_agent_e5_customer_segmentation_agent(db_session):
    """Verify Agent E5 produces governed, explainable audience segments."""
    # Seed 3 leads
    for i in range(3):
        db_session.add(Lead(tenant_id="tenant_test", name=f"User {i}", email=f"user{i}@test.com"))
    db_session.commit()

    agent = CustomerSegmentationAgent(db_session, "tenant_test")
    env = AgentExecutionEnvelope(
        tenant_id="tenant_test",
        request_id="req_e5",
        workflow_id="wf_e5",
        agent_id="segmentation",
        objective="Create active leads segment",
        idempotency_key="idemp_e5_01",
    )
    inp = CustomerSegmentationInput(
        segment_objective="Target all active enterprise leads",
        requested_audience={"status": "captured"},
        intended_use="marketing_email",
    )

    with patch.object(agent.llm, "complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = '{"segment_ref": "seg_active_enterprise_leads", "segment_version": "1.0", "segment_type": "DYNAMIC_RULE", "normalized_definition": {"status": "captured"}, "source_fields": ["status", "email"], "inclusion_rules": [{"field": "status", "operator": "==", "value": "captured"}], "exclusion_rules": []}'
        res_env = await agent.execute(env, inp)

    assert res_env.status == ExecutionStatus.COMPLETED
    out = res_env.output
    assert out["segment_ref"] == "seg_active_enterprise_leads"
    assert out["matched_count"] == 3


def test_agent_e6_deterministic_suppression_enforcement(db_session):
    """Verify Agent E6 suppression gate: allows clean recipients, blocks suppressed ones."""
    agent = DeliverabilitySuppressionAgent(db_session, "tenant_test")

    # 1. Unsuppressed recipient -> ALLOW
    res_clean = agent.check_suppression_deterministic("clean.user@example.com")
    assert res_clean.decision == SuppressionDecision.ALLOW
    assert res_clean.suppression_match is False

    # 2. Add suppression record (opt-out / unsubscribe)
    supp = SuppressionRecord(
        tenant_id="tenant_test",
        identifier_type="email",
        identifier_value="optout.user@example.com",
        reason="unsubscribe",
        scope="all",
    )
    db_session.add(supp)
    db_session.commit()

    # 3. Suppressed recipient -> BLOCK (Fail Closed)
    res_blocked = agent.check_suppression_deterministic("optout.user@example.com")
    assert res_blocked.decision == SuppressionDecision.BLOCK
    assert res_blocked.suppression_match is True
    assert "unsubscribe" in res_blocked.reason_codes[0]

    # 4. Empty identifier -> BLOCK
    res_empty = agent.check_suppression_deterministic("")
    assert res_empty.decision == SuppressionDecision.BLOCK


@pytest.mark.asyncio
async def test_agent_e7_retention_and_churn_signals(db_session):
    """Verify Agent E7 produces explainable churn signals and proportionate interventions."""
    agent = RetentionChurnSignalAgent(db_session, "tenant_test")
    env = AgentExecutionEnvelope(
        tenant_id="tenant_test",
        request_id="req_e7",
        workflow_id="wf_e7",
        agent_id="churn_signal",
        objective="Assess account renewal risk",
        idempotency_key="idemp_e7_01",
    )
    inp = RetentionRiskInput(
        customer_ref="cust_101",
        account_ref="acc_101",
        usage_events=[{"event": "login_decline_40pct"}],
        support_events=[{"ticket": "unresolved_integration_blocker"}],
    )

    with patch.object(agent.llm, "complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = '{"risk_band": "HIGH", "risk_score": 78.0, "contributing_signals": [{"signal": "login_decline_40pct", "weight": 0.6}, {"signal": "unresolved_support_ticket", "weight": 0.4}], "recommended_intervention": "executive_sponsor_outreach", "recommended_owner": "customer_success", "urgency": "high"}'
        res_env = await agent.execute(env, inp)

    assert res_env.status == ExecutionStatus.COMPLETED
    out = res_env.output
    assert out["risk_band"] == "HIGH"
    assert out["recommended_owner"] == "customer_success"


@pytest.mark.asyncio
async def test_agent_e8_reengagement_and_referral(db_session):
    """Verify Agent E8 handles reactivation workflows cleanly."""
    agent = ReengagementReferralAgent(db_session, "tenant_test")
    env = AgentExecutionEnvelope(
        tenant_id="tenant_test",
        request_id="req_e8",
        workflow_id="wf_e8",
        agent_id="reengagement",
        objective="Reopen dormant leads",
        idempotency_key="idemp_e8_01",
    )
    inp = ReengagementInput(
        campaign_mode=ReengagementMode.SALES_REACTIVATION,
        audience_ref="aud_dormant_leads_60d",
        customer_or_lead_refs=["lead_d1", "lead_d2"],
        approved_offers=[{"offer": "free_architecture_audit"}],
    )

    with patch.object(agent.llm, "complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = '{"proposed_strategy": "Personalized technical reconnect regarding Q4 roadmap", "eligible_record_refs": ["lead_d1", "lead_d2"], "excluded_record_refs": [], "reactivation_signals": [{"signal": "inactive_60_days"}], "success_metrics": ["meeting_booked"]}'
        res_env = await agent.execute(env, inp)

    assert res_env.status == ExecutionStatus.COMPLETED
    out = res_env.output
    assert out["campaign_mode"] == "SALES_REACTIVATION"
    assert len(out["eligible_record_refs"]) == 2


def test_governance_kernel_and_emergency_stop(db_session):
    """Verify GovernanceKernel validates actions, enforces budget caps, and emergency kill switch."""
    kernel = GovernanceKernel(db_session, "tenant_gov")

    # 1. Normal permitted action
    ok, reason = kernel.validate_action("crm.lead.create", actor_permissions=["crm.write"])
    assert ok is True

    # 2. Unauthorized action
    ok, reason = kernel.validate_action("ad.campaign.create", actor_permissions=["crm.write"])
    assert ok is False
    assert "Missing required permission" in reason

    # 3. Budget cap breach
    ok, reason = kernel.validate_action("ad.campaign.create", actor_permissions=["ads.manage"], spend_usd=600.0, daily_budget_cap=500.0)
    assert ok is False
    assert "exceeds daily budget cap" in reason

    # 4. Emergency Kill Switch engaged
    kernel.set_emergency_stop(True, reason="Detected anomalous ad spend")
    assert kernel.is_emergency_stopped() is True

    ok, reason = kernel.validate_action("crm.lead.create", actor_permissions=["*"])
    assert ok is False
    assert "kill switch is active" in reason

    # Pre-send check also blocked by emergency kill switch
    allowed, pre_reason = kernel.verify_pre_send_eligibility("user@example.com")
    assert allowed is False
    assert "kill switch" in pre_reason.lower()


def test_marketing_automation_scorecard(db_session):
    """Verify MarketingAutomationScorecardService calculates task automation and autonomy rates."""
    # Seed 4 posts (3 approved, 1 pending review)
    for i in range(3):
        db_session.add(ContentPost(tenant_id="tenant_sc", platform="linkedin", status="draft", approval_status="approved"))
    db_session.add(ContentPost(tenant_id="tenant_sc", platform="linkedin", status="draft", approval_status="pending"))

    # Seed 2 leads (1 qualified, 1 captured)
    db_session.add(Lead(tenant_id="tenant_sc", email="l1@test.com", status="qualified"))
    db_session.add(Lead(tenant_id="tenant_sc", email="l2@test.com", status="captured"))
    db_session.commit()

    service = MarketingAutomationScorecardService(db_session, "tenant_sc")
    card = service.compute_scorecard(window_days=30)

    metrics = card["metrics"]
    # Total eligible tasks = 4 posts + 2 leads = 6
    # Automated tasks = 3 approved posts + 1 qualified lead = 4
    # Rate = 4/6 = 66.7%
    assert metrics["eligible_tasks_total"] == 6
    assert metrics["tasks_automated_count"] == 4
    assert metrics["task_automation_rate_pct"] == 66.7
