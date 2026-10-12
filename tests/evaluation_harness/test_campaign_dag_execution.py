"""Campaign OS DAG End-to-End Integration Test Suite.

Workstream B & Workstream E:
- Verifies 3-stage DAG execution (Strategy Root -> Idempotent Fan-Out -> Critic & Dispatch)
- Asserts creation of ContentPost records with compiled media prompts
- Asserts ActivityLog entries and HITL approval routing
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, Tenant, User
from app.models.agents import KnowledgeDocument, ActivityLog
from app.models.deal_room import EvidenceRecord
from app.models.verticals import ContentPost, BusinessProfile
from app.models.enterprise import ApprovalRequest
from app.services.marketing.campaign_os.orchestrator import CampaignOSOrchestrator
from app.services.knowledge_os.access_controller import DataClassification


SQLALCHEMY_DATABASE_URL = "sqlite:///./test_campaign_dag.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    tenant = Tenant(id="tenant_camp_dag", name="Campaign Tenant", subdomain="camp-tenant")
    session.add(tenant)
    user = User(
        id="user_creator",
        tenant_id="tenant_camp_dag",
        email="creator@camp.com",
        name="Creator",
        hashed_password="mock",
        role="admin",
    )
    session.add(user)
    
    profile = BusinessProfile(
        tenant_id="tenant_camp_dag",
        company_name="OctaOS",
        website="https://octaos.com",
        industry="Enterprise Automation",
        service_description="Autonomous AI Agent operating system for modern business operations.",
        usp="Deep knowledge grounding with deterministic safety guardrails.",
        offer_details="Schedule a live architecture teardown and platform trial.",
    )
    session.add(profile)
    
    # Approved Public Brand Kit
    doc = KnowledgeDocument(
        tenant_id="tenant_camp_dag",
        department="Marketing",
        doc_type="Brand Guidelines",
        content="OctaOS tone is authoritative, pragmatic, and visionary. Primary brand color is emerald green (#059669).",
        classification=DataClassification.PUBLIC,
        approved_for_external_use=True,
    )
    session.add(doc)
    session.flush()
    
    # Verified Evidence Record
    evidence = EvidenceRecord(
        tenant_id="tenant_camp_dag",
        claim="OctaOS eliminates 80% of repetitive operational tasks for enterprise teams.",
        source_type="company_doc",
        source_id=doc.id,
        raw_snippet="eliminates 80% of repetitive tasks",
        is_valid=True,
    )
    session.add(evidence)
    session.commit()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)


import json
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_campaign_os_dag_execution(db_session):
    """Test full execution of Campaign OS DAG producing posts and compiled media prompts with real AI flow."""
    tenant_id = "tenant_camp_dag"
    orchestrator = CampaignOSOrchestrator(db_session, tenant_id)

    async def mock_llm_complete(prompt: str, system_prompt: str = None, **kwargs):
        p_lower = (prompt + " " + (system_prompt or "")).lower()
        if "lead brand strategist" in p_lower:
            return json.dumps({
                "core_narrative": "Autonomous Enterprise Workflows with Deterministic Safety",
                "tone_keywords": ["Authoritative", "Pragmatic", "Pioneering"],
                "target_persona": "Enterprise Chief Operating Officers",
                "key_differentiators": ["Autonomous execution", "Deterministic guardrails"],
                "approved_evidence_ids": ["evidence_1"],
                "prohibited_topics": ["Unverified guarantees"],
            })
        elif "visual director" in p_lower:
            return json.dumps({
                "primary_color": "#059669",
                "secondary_color": "#0F172A",
                "accent_color": "#38BDF8",
                "aesthetic_mood": "Clean architectural realism, tactile high-contrast surfaces",
                "photography_archetype": "35mm corporate editorial lookbook, natural daylight",
                "sref_url": None,
            })
        elif "narrative architect" in p_lower:
            return json.dumps({
                "campaign_title": "Autonomous Enterprise Operations",
                "total_days": 2,
                "days_outline": [
                    {
                        "day": 1,
                        "theme": "Operational Fragility",
                        "narrative_focus": "Problem Agitation",
                        "suggested_hook_angle": "Why legacy manual coordination fails at modern scale",
                        "target_cta_intent": "curiosity",
                    },
                    {
                        "day": 2,
                        "theme": "Architectural Certainty",
                        "narrative_focus": "Solution & Proof",
                        "suggested_hook_angle": "How deterministic AI pipelines execute repeatable workflows",
                        "target_cta_intent": "demo_request",
                    },
                ],
            })
        elif "copywriter" in p_lower or "write high-impact" in p_lower:
            return json.dumps({
                "platform": "linkedin",
                "day": 1,
                "hook": "Enterprise operations stall when manual steps outpace visibility.",
                "body_content": "Modern organizations cannot rely on brittle manual handoffs. By replacing ad-hoc coordination with verified autonomous workflows, teams achieve predictable scale without increasing overhead.",
                "cta_sentence": "How is your leadership team addressing operational bottlenecks this quarter?",
                "hashtags": ["#EnterpriseAutomation", "#Operations", "#Strategy"],
                "formatted_full_post": "Enterprise operations stall when manual steps outpace visibility.\n\nModern organizations cannot rely on brittle manual handoffs. By replacing ad-hoc coordination with verified autonomous workflows, teams achieve predictable scale without increasing overhead.\n\nHow is your leadership team addressing operational bottlenecks this quarter?\n\n#EnterpriseAutomation #Operations #Strategy",
            })
        elif "art director" in p_lower:
            return json.dumps({
                "subject": "Enterprise systems architects collaborating in a modern studio",
                "action_or_state": "evaluating workflow architecture telemetry on high-resolution displays",
                "environment_setting": "minimalist architectural atelier with textured oak panels and concrete",
                "emotional_mood": "composed, authoritative, focused",
                "shot_type": "cinematic medium wide shot",
                "lighting_intent": "soft directional morning key light with subtle emerald reflections",
                "negative_space_direction": "right_40pct",
                "color_accents": ["#059669", "#0F172A"],
            })
        elif "cinematic director" in p_lower or "video shot plan" in p_lower:
            return json.dumps({
                "scene_description": "Smooth camera track across modern enterprise operations room displaying real-time automation telemetry",
                "duration_seconds": 5,
                "camera_movement": "slow cinematic push-in at 0.4m/s with subtle rack focus",
                "focal_motion": "dynamic data telemetry streams subtly illuminating matte glass surfaces",
                "atmosphere_notes": "volumetric morning light filtering through high windows",
                "aspect_ratio": "16:9",
            })
        elif "executive editor" in p_lower or "audit" in p_lower:
            return json.dumps({
                "platform_fit_score": 0.95,
                "brand_voice_score": 0.92,
                "critique_notes": "Well-grounded, clear strategic tone, matches audience.",
            })
        elif "conversion rate" in p_lower or "cta" in p_lower:
            return json.dumps({
                "cta_copy": "Request a platform demonstration to see autonomous execution in action.",
                "action_type": "demo_request",
                "friction_level": "low",
            })
        return "{}"

    params = {
        "topic": "Enterprise Autonomous Operations",
        "days": 2,
        "platforms": ["linkedin", "instagram"],
        "image_provider": "together",
        "generate_images": True,
        "generate_videos": True,
    }

    with patch("app.services.llm_gateway.LLMGateway.complete", new=AsyncMock(side_effect=mock_llm_complete)):
        result = await orchestrator.execute_campaign_dag(params)

    # 1. Assert DAG Result Structure
    assert result["status"] == "success"
    assert result["total_posts_generated"] == 4  # 2 days x 2 platforms
    assert "campaign_title" in result
    assert result["failed_count"] == 0

    # 2. Assert ContentPost Records in Database
    posts = db_session.query(ContentPost).filter(ContentPost.tenant_id == tenant_id).all()
    assert len(posts) == 4

    platforms_seen = [p.platform for p in posts]
    assert "linkedin" in platforms_seen
    assert "instagram" in platforms_seen

    # 3. Assert ContentPost contains actual generated content, not synthetic fallback
    for post in posts:
        assert post.content is not None
        assert len(post.content) > 30
        assert "In modern enterprise workflows, consistency is the key differentiator" not in post.content
        assert post.status == "draft"
        assert post.approval_status in ("approved", "pending")
        assert post.image_prompt is not None

    # 4. Assert Activity Logs Recorded
    logs = db_session.query(ActivityLog).filter(ActivityLog.tenant_id == tenant_id).all()
    assert len(logs) >= 2
    actions = [l.action for l in logs]
    assert "Campaign Strategy" in actions or "Campaign Blueprint" in actions
    assert "Campaign Generation Completed" in actions


@pytest.mark.asyncio
async def test_campaign_os_dag_failure_reporting(db_session):
    """Verify that when the AI provider fails, no synthetic data is fabricated and the error reason is exposed."""
    tenant_id = "tenant_camp_dag"
    orchestrator = CampaignOSOrchestrator(db_session, tenant_id)

    async def mock_failing_llm(*args, **kwargs):
        raise RuntimeError("OpenRouter API error (status 402): Insufficient balance")

    params = {
        "topic": "Enterprise Autonomous Operations",
        "days": 2,
        "platforms": ["linkedin"],
    }

    with patch("app.services.llm_gateway.LLMGateway.complete", new=AsyncMock(side_effect=mock_failing_llm)):
        result = await orchestrator.execute_campaign_dag(params)

    # Must fail fast and clearly report the error reason
    assert result["status"] == "failed"
    assert "Insufficient balance" in result["error"]
    assert result["total_posts_generated"] == 0

    # Verify ActivityLog captures the exact failure
    log = db_session.query(ActivityLog).filter(
        ActivityLog.tenant_id == tenant_id,
        ActivityLog.status == "failed",
    ).first()
    assert log is not None
    assert "Insufficient balance" in log.description


@pytest.mark.asyncio
async def test_campaign_os_dag_post_level_failure_handling(db_session):
    """Verify that if post generation fails for a specific platform, the failed post is recorded with the exact reason."""
    tenant_id = "tenant_camp_dag"
    orchestrator = CampaignOSOrchestrator(db_session, tenant_id)

    call_count = 0

    async def mock_partial_llm(prompt: str, system_prompt: str = None, **kwargs):
        nonlocal call_count
        call_count += 1
        p_lower = (prompt + " " + (system_prompt or "")).lower()
        if "lead brand strategist" in p_lower:
            return json.dumps({
                "core_narrative": "Scale Through Autonomous Agents",
                "tone_keywords": ["Visionary"],
                "target_persona": "Tech Leaders",
                "key_differentiators": ["Autonomy"],
                "approved_evidence_ids": [],
                "prohibited_topics": [],
            })
        elif "narrative architect" in p_lower:
            return json.dumps({
                "campaign_title": "Scale Campaign",
                "total_days": 1,
                "days_outline": [
                    {
                        "day": 1,
                        "theme": "Scale",
                        "narrative_focus": "Solution",
                        "suggested_hook_angle": "Scaling without overhead",
                        "target_cta_intent": "demo",
                    }
                ],
            })
        elif "copywriter" in p_lower or "write high-impact" in p_lower:
            raise RuntimeError("Rate limit exceeded on provider 'openrouter'")
        return "{}"

    params = {
        "topic": "Scaling Automation",
        "days": 1,
        "platforms": ["linkedin"],
    }

    with patch("app.services.llm_gateway.LLMGateway.complete", new=AsyncMock(side_effect=mock_partial_llm)):
        result = await orchestrator.execute_campaign_dag(params)

    # Post should be marked as failed with the reason
    assert result["failed_count"] == 1
    failed_posts = db_session.query(ContentPost).filter(
        ContentPost.tenant_id == tenant_id,
        ContentPost.status == "failed",
    ).all()
    assert len(failed_posts) == 1
    post = failed_posts[0]
    assert post.approval_status == "failed"
    assert "Rate limit exceeded" in post.fallback_reason


@pytest.mark.asyncio
async def test_critique_score_card_resilience_with_list_notes():
    """Verify CritiqueScoreCard and Critic role accept list or string critique_notes without Pydantic ValidationError."""
    from app.services.marketing.campaign_os.contracts import CritiqueScoreCard

    # 1. Pydantic contract instantiation with a list (the exact error scenario reported)
    card = CritiqueScoreCard(
        groundedness_score=0.9,
        platform_fit_score=0.95,
        brand_voice_score=0.92,
        overall_confidence=0.9,
        critique_notes=[
            "Uses the company's narrative well.",
            "Could revise it in one sentence.",
        ],
    )
    assert isinstance(card.critique_notes, str)
    assert "Uses the company's narrative well." in card.critique_notes
    assert "Could revise it in one sentence." in card.critique_notes

    # 2. Pydantic contract with string critique_notes
    card_str = CritiqueScoreCard(
        groundedness_score=0.9,
        platform_fit_score=0.95,
        brand_voice_score=0.92,
        overall_confidence=0.9,
        critique_notes="Direct string note",
    )
    assert card_str.critique_notes == "Direct string note"

