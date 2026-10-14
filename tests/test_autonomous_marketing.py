import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.base
import app.models.deal_room
import app.models.sales_intelligence
import app.models.enterprise
import app.models.verticals
import app.models.agents

from app.models.base import Base, Tenant
from app.models.verticals import BusinessProfile, ContentPost
from app.models.agents import KnowledgeDocument
from app.models.enterprise import ApprovalRequest
from app.services.knowledge_os.brand_synthesizer import BrandKnowledgeService
from app.services.marketing.context_radar.calendar_engine import CalendarEngine
from app.services.marketing.context_radar.news_radar import NewsRadar
from app.services.marketing.context_radar.trend_synthesizer import TrendSynthesizer, CreativeBrief
from app.services.agents.marketing import MarketingAgent


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_tenant_data(db_session):
    tenant_id = "test-tenant-auto"
    tenant = Tenant(id=tenant_id, name="ApexAI", subdomain="apexai")
    profile = BusinessProfile(
        tenant_id=tenant_id,
        company_name="ApexAI Systems",
        website="https://apexai.io",
        industry="Technology",
        service_description="Next-generation autonomous agent orchestration platform for enterprise teams.",
        usp="Reduces operational complexity by 70% with verified safety gates.",
        target_industries="B2B SaaS, Finance, Logistics",
        target_decision_makers="CTO, VP of Engineering, Head of Automation",
    )
    doc1 = KnowledgeDocument(
        tenant_id=tenant_id,
        doc_type="Product Catalog",
        department="Product",
        content="Product: Apex Orchestrator. Price: $499/mo. Solves manual coordination. USP: Real-time autonomous DAG execution.",
        is_active=True,
    )
    doc2 = KnowledgeDocument(
        tenant_id=tenant_id,
        doc_type="Brand Guidelines",
        department="Marketing",
        content="Tone: Authoritative and visionary. Banned words: revolutionary, magic, silver bullet.",
        is_active=True,
    )
    db_session.add_all([tenant, profile, doc1, doc2])
    db_session.commit()
    return tenant_id


def test_brand_knowledge_synthesizer(db_session, sample_tenant_data):
    service = BrandKnowledgeService(db_session, sample_tenant_data)
    snapshot = service.synthesize()

    assert snapshot["company_name"] == "ApexAI Systems"
    assert snapshot["industry"] == "Technology"
    assert "products_catalog" in snapshot
    assert len(snapshot["products_catalog"]) >= 1
    assert "brand_voice" in snapshot
    assert "motion_design_tokens" in snapshot
    assert snapshot["motion_design_tokens"]["aspect_ratios"]["reels"] == "9:16"


def test_calendar_engine(db_session, sample_tenant_data):
    from datetime import date
    from app.services.marketing.context_radar.calendar_api import CalendarApiClient

    sample_events = [
        {"name": "Innovation Summit", "date": date.today().isoformat(), "category": "tech", "scope": "country", "country": "United States", "country_code": "US", "source": "google_calendar_api"},
    ]
    with patch.object(CalendarApiClient, "fetch_google_calendar_events", return_value=sample_events):
        engine = CalendarEngine(db_session, sample_tenant_data)
        events = engine.get_upcoming_events(days_ahead=30)

    assert isinstance(events, list)
    assert len(events) > 0
    first = events[0]
    assert "name" in first
    assert "hook" in first
    assert "days_until" in first
    assert first["days_until"] >= 0


def test_news_radar(db_session, sample_tenant_data):
    radar = NewsRadar(db_session, sample_tenant_data)
    signals = radar.get_top_signals(limit=5, brand_context="Technology")

    assert isinstance(signals, list)
    assert len(signals) > 0
    sig = signals[0]
    assert "topic" in sig
    assert "signal" in sig
    assert "relevance_score" in sig
    assert sig["relevance_score"] > 0


@pytest.mark.asyncio
async def test_trend_synthesizer(db_session, sample_tenant_data):
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value='{"topic": "Autonomous Future", "hook": "Are manual workflows holding your team back?", "narrative_angle": "ApexAI eliminates friction.", "call_to_action": "Try the interactive demo.", "media_type": "video", "video_prompt": "Cinematic 4K hyperlapse of autonomous servers", "video_provider": "together", "video_model": "Wan-AI/Wan2.1-T2V-14B"}')

    synthesizer = TrendSynthesizer(db_session, sample_tenant_data, mock_llm)
    brief = await synthesizer.synthesize_angle(
        brand_knowledge={"company_name": "ApexAI", "industry": "Technology"},
        calendar_events=[{"name": "World Creativity Day", "hook": "Innovation leads progress."}],
        news_signals=[{"topic": "Agentic AI", "signal": "Agentic AI is the future.", "relevance_score": 0.95}],
        platform="instagram",
    )

    assert isinstance(brief, CreativeBrief)
    assert brief.topic == "Autonomous Future"
    assert "Wan2.1" in (brief.video_model or "")
    assert brief.media_type == "video"


@pytest.mark.asyncio
async def test_marketing_agent_autonomous_pulse(db_session, sample_tenant_data):
    agent = MarketingAgent(db_session, sample_tenant_data)

    # Mock LLM generation to avoid live network requests
    agent.llm.complete = AsyncMock(return_value="Automation is redefining software engineering in 2026. Here is why your team should adapt.\n\n#ApexAI #Enterprise")
    agent.llm.generate_video = AsyncMock(return_value="https://cdn.example.com/videos/test-wan2.mp4")
    agent.llm.generate_image = AsyncMock(return_value="https://cdn.example.com/images/test-flux.jpg")

    with patch("app.services.agents.marketing.ensure_public_url", new=AsyncMock(side_effect=lambda x, **kw: x)):
        result = await agent.autonomous_marketing_pulse({
            "platforms": ["linkedin", "instagram"],
            "media_type": "video",
            "auto_schedule": True,
            "confidence_threshold": 0.80,
        })

    assert result["status"] == "success"
    assert result["posts_created"] == 2
    assert len(result["posts"]) == 2

    # Verify posts persisted to database
    posts = db_session.query(ContentPost).filter(ContentPost.tenant_id == sample_tenant_data).all()
    assert len(posts) == 2
    for p in posts:
        assert p.platform in ["linkedin", "instagram"]
        assert p.status in ["scheduled", "draft"]
        assert p.video_url is not None
