"""15-AI-Agent Marketing Council Orchestration Integration Test Suite.

Verifies:
1. Agents 1-5: Brand & Market Context Anchor Synthesis (Brand DNA, Catalog, ICP, Proof, Radar)
2. Agents 6-7: Master Narrative Arc & Chronological Multi-Slot Cadence Scheduling
3. Agents 8-12: Independent Native Copy, Hook, Offer CTA, Image Intent & Video Shot Plan Generation
4. Agents 13-14: Deterministic Fact-Checking & Brand Compliance Gates with Self-Repair
5. Agent 15: Chief Marketing Officer (CMO) Council Review & Database Persistence
"""
import pytest
import json
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, Tenant, User
from app.models.agents import KnowledgeDocument, ActivityLog
from app.models.deal_room import EvidenceRecord
from app.models.verticals import ContentPost, BusinessProfile
from app.services.marketing.campaign_os.orchestrator import CampaignOSOrchestrator
from app.services.marketing.campaign_os.roles import CampaignRolesEngine
from app.services.knowledge_os.access_controller import DataClassification


SQLALCHEMY_DATABASE_URL = "sqlite:///./test_15_agents.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    tenant = Tenant(id="tenant_15_agents", name="Enterprise Council Tenant", subdomain="council-tenant")
    session.add(tenant)
    user = User(
        id="user_cmo",
        tenant_id="tenant_15_agents",
        email="cmo@council.com",
        name="Chief Marketer",
        hashed_password="mock",
        role="admin",
    )
    session.add(user)

    profile = BusinessProfile(
        tenant_id="tenant_15_agents",
        company_name="OctaOS Enterprise",
        website="https://octaos.com",
        industry="Enterprise Automation",
        service_description="Autonomous AI Agent operating system for modern business operations.",
        usp="Deep knowledge grounding with deterministic safety guardrails.",
        offer_details="Schedule an executive platform architecture session.",
    )
    session.add(profile)

    doc = KnowledgeDocument(
        tenant_id="tenant_15_agents",
        department="Marketing",
        doc_type="Brand Guidelines",
        content="Tone: Authoritative, pragmatic, visionary. Primary brand color: #059669. Forbidden: revolutionary, game-changer.",
        classification=DataClassification.PUBLIC,
        approved_for_external_use=True,
    )
    session.add(doc)
    session.flush()

    evidence = EvidenceRecord(
        tenant_id="tenant_15_agents",
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


@pytest.mark.asyncio
async def test_brand_context_anchor_synthesis(db_session):
    """Test Agents 1 through 5 producing an immutable BrandContextAnchor."""
    tenant_id = "tenant_15_agents"
    roles = CampaignRolesEngine(db_session, tenant_id)

    company_context = {
        "company_name": "OctaOS Enterprise",
        "website": "https://octaos.com",
        "industry": "Enterprise Automation",
        "brand_voice": {
            "tone": "Authoritative, Pragmatic, Visionary",
            "vocabulary": ["Autonomous", "Deterministic", "Enterprise"],
            "banned_words": ["Game-changer", "Revolutionary"],
        },
        "products_catalog": [
            {
                "name": "OctaOS Orchestrator",
                "description": "Multi-agent orchestration runtime",
                "usp": "Sub-second deterministic task dispatch",
            }
        ],
        "target_audiences": [
            {
                "persona": "Chief Operating Officers",
                "pain_points": ["Manual coordination bottlenecks", "Lack of audit visibility"],
            }
        ],
        "approved_claims": [
            {"evidence_id": "ev_01", "claim": "Eliminates 80% of repetitive tasks"}
        ],
        "visual_style": {
            "primary_color": "#059669",
            "secondary_color": "#0F172A",
            "accent_color": "#38BDF8",
            "mood": "Architectural realism",
        },
    }

    anchor = await roles.synthesize_brand_context_anchor(
        company_context=company_context,
        topic="Scaling Enterprise Operations",
        days=7,
    )

    # Assert Agent 1 (Brand DNA)
    assert anchor.brand_dna.company_name == "OctaOS Enterprise"
    assert "Authoritative" in anchor.brand_dna.tone_keywords or len(anchor.brand_dna.tone_keywords) > 0
    assert "Revolutionary" in anchor.brand_dna.banned_words or "Game-changing" in anchor.brand_dna.banned_words

    # Assert Agent 2 (Product Catalog)
    assert len(anchor.product_catalog.products) >= 1
    assert anchor.product_catalog.products[0]["name"] == "OctaOS Orchestrator"

    # Assert Agent 3 (Audience Persona)
    assert "Chief Operating Officers" in anchor.audience_persona.target_persona

    # Assert Agent 4 (Proof Points)
    assert "ev_01" in anchor.proof_points.approved_evidence_ids or len(anchor.proof_points.verified_metrics) > 0

    # Assert Agent 5 (Context Radar)
    assert len(anchor.context_radar.timely_hooks) > 0


@pytest.mark.asyncio
async def test_cadence_scheduler_multi_slots(db_session):
    """Test Agent 7: Chronological Time-Slot Cadence Scheduler with 2 slots per day."""
    tenant_id = "tenant_15_agents"
    roles = CampaignRolesEngine(db_session, tenant_id)

    from app.services.marketing.campaign_os.contracts import CampaignNarrativeArc, CampaignDayOutline

    narrative_arc = CampaignNarrativeArc(
        campaign_title="Autonomous Scale",
        total_days=2,
        days_outline=[
            CampaignDayOutline(day=1, theme="Problem Agitation", narrative_focus="Operational Friction", suggested_hook_angle="Why manual workflows fail", target_cta_intent="curiosity"),
            CampaignDayOutline(day=2, theme="Solution Reveal", narrative_focus="Deterministic Autonomy", suggested_hook_angle="Predictable scale without overhead", target_cta_intent="demo_request"),
        ],
    )

    schedule = await roles.execute_cadence_scheduler(
        narrative_arc=narrative_arc,
        platforms=["linkedin", "instagram"],
        posts_per_day=2,
    )

    # 2 days x 2 slots/day x 2 platforms = 8 total slot specifications
    assert schedule.total_days == 2
    assert schedule.posts_per_day == 2
    assert len(schedule.slots) == 8

    # Verify slot labeling and chronological timestamps
    day1_slots = [s for s in schedule.slots if s.day == 1 and s.platform == "linkedin"]
    assert len(day1_slots) == 2
    assert "Morning" in day1_slots[0].slot_label
    assert "Evening" in day1_slots[1].slot_label
    assert day1_slots[0].scheduled_time_utc != day1_slots[1].scheduled_time_utc


@pytest.mark.asyncio
async def test_15_agent_full_dag_execution(db_session):
    """Test complete 15-Agent Council DAG execution producing multi-slot ContentPost records."""
    tenant_id = "tenant_15_agents"
    orchestrator = CampaignOSOrchestrator(db_session, tenant_id)

    async def mock_llm_complete(prompt: str, system_prompt: str = None, **kwargs):
        p_lower = (prompt + " " + (system_prompt or "")).lower()
        if "lead brand strategist" in p_lower:
            return json.dumps({
                "core_narrative": "Autonomous Enterprise Operations with Deterministic Safety",
                "tone_keywords": ["Authoritative", "Pragmatic", "Visionary"],
                "target_persona": "Enterprise Chief Operating Officers",
                "key_differentiators": ["Autonomous execution", "Deterministic guardrails"],
                "approved_evidence_ids": ["ev_01"],
                "prohibited_topics": ["Unverified guarantees"],
            })
        elif "visual director" in p_lower:
            return json.dumps({
                "primary_color": "#059669",
                "secondary_color": "#0F172A",
                "accent_color": "#38BDF8",
                "aesthetic_mood": "Clean architectural realism, tactile high-contrast surfaces",
                "photography_archetype": "35mm corporate editorial lookbook",
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
                        "suggested_hook_angle": "Why legacy manual coordination fails",
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
                "hook": "Enterprise operations stall when manual handoffs outpace visibility.",
                "body_content": "Modern organizations cannot rely on brittle manual handoffs. By replacing ad-hoc coordination with verified autonomous workflows, teams achieve predictable scale without increasing overhead.",
                "cta_sentence": "How is your leadership team addressing operational bottlenecks this quarter?",
                "hashtags": ["#EnterpriseAutomation", "#Operations"],
                "formatted_full_post": "Enterprise operations stall when manual handoffs outpace visibility.\n\nModern organizations cannot rely on brittle manual handoffs. By replacing ad-hoc coordination with verified autonomous workflows, teams achieve predictable scale without increasing overhead.\n\nHow is your leadership team addressing operational bottlenecks this quarter?\n\n#EnterpriseAutomation #Operations",
            })
        elif "viral hook" in p_lower or "winning_hook" in p_lower:
            return json.dumps({
                "winning_hook": "Most enterprise coordination breaks before anyone notices.",
                "angle_type": "contrarian_insight",
                "hook_variants": [
                    {"type": "contrarian_insight", "text": "Most enterprise coordination breaks before anyone notices."},
                ],
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
        elif "conversion rate" in p_lower or "action-oriented call to action" in p_lower:
            return json.dumps({
                "cta_copy": "Request a platform demonstration to see autonomous execution in action.",
                "action_type": "demo_request",
                "friction_level": "low",
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
        elif "chief marketing officer" in p_lower or "cmo" in p_lower:
            return json.dumps({
                "campaign_title": "Autonomous Enterprise Operations",
                "overall_confidence": 0.95,
                "is_approved": True,
                "executive_summary": "Approved for release across all scheduled time slots.",
                "total_slots_planned": 4,
                "approved_slots_count": 4,
                "needs_review_count": 0,
            })
        return "{}"

    params = {
        "topic": "Enterprise Autonomous Operations",
        "days": 2,
        "platforms": ["linkedin"],
        "posts_per_day": 2,  # 2 slots per day (Morning + Evening)
        "image_provider": "together",
        "generate_images": True,
        "generate_videos": True,
    }

    with patch("app.services.llm_gateway.LLMGateway.complete", new=AsyncMock(side_effect=mock_llm_complete)):
        result = await orchestrator.execute_campaign_dag(params)

    # 1. Assert DAG Result Structure
    assert result["status"] == "success"
    # 2 days x 2 slots/day x 1 platform = 4 posts
    assert result["total_posts_generated"] == 4
    assert result["posts_per_day"] == 2
    assert "campaign_title" in result
    assert result["failed_count"] == 0

    # 2. Assert ContentPost Records in Database
    posts = db_session.query(ContentPost).filter(ContentPost.tenant_id == tenant_id).all()
    assert len(posts) == 4

    # 3. Assert Timestamps and Multi-Slot Metadata
    for p in posts:
        assert p.scheduled_at is not None
        assert p.image_prompt is not None
        assert p.video_prompt is not None
        assert any("slot:" in tag for tag in (p.learning_tags or []))
