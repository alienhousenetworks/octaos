import pytest
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.base
import app.models.deal_room
import app.models.sales_intelligence
import app.models.enterprise
import app.models.verticals
import app.models.agents

from app.models.base import Base, Tenant
from app.models.verticals import BusinessProfile
from app.services.marketing.context_radar.calendar_engine import CalendarEngine
from app.services.agents.marketing import MarketingAgent
from app.worker.tasks import scan_regional_context_radar_task


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def indian_tenant_data(db_session):
    tenant_id = "test-tenant-india"
    tenant = Tenant(id=tenant_id, name="BharatGrowth", subdomain="bharatgrowth")
    profile = BusinessProfile(
        tenant_id=tenant_id,
        company_name="BharatTech Solutions",
        website="https://bharattech.in",
        industry="Technology",
        service_description="Enterprise cloud automation platform tailored for fast-growing Indian enterprises.",
        usp="Cut operational bottlenecks by 60% with sovereign cloud security.",
        target_countries=["India"],
    )
    db_session.add_all([tenant, profile])
    db_session.commit()
    return tenant_id


def test_target_region_detection(db_session, indian_tenant_data):
    engine = CalendarEngine(db_session, indian_tenant_data)
    regions = engine.get_target_regions()
    assert regions == ["india"]


def test_regional_calendar_events_detection_october_2026(db_session, indian_tenant_data):
    engine = CalendarEngine(db_session, indian_tenant_data)

    # Mock today to October 12, 2026 (same day as current run)
    fake_today = date(2026, 10, 12)
    with patch("app.services.marketing.context_radar.calendar_engine.date") as mock_date:
        mock_date.today.return_value = fake_today
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        mock_date.fromisoformat = date.fromisoformat

        events = engine.get_upcoming_events(days_ahead=14)

    assert isinstance(events, list)
    event_names = [e["name"] for e in events]

    # Verify both global and regional events are present
    assert any("Cybersecurity Awareness" in n for n in event_names)
    assert any("World Food Day" in n for n in event_names)
    # Durga Puja & Navratri must be detected!
    assert any("Navratri & Durga Puja" in n for n in event_names)
    assert any("Dussehra" in n for n in event_names)

    # Check the Durga Puja event details
    dp_event = next(e for e in events if "Navratri & Durga Puja" in e["name"])
    assert dp_event["region"] == "India"
    assert dp_event["category"] == "cultural"
    assert dp_event["days_until"] >= 0
    assert "hook" in dp_event


@pytest.mark.asyncio
async def test_agentic_live_context_search_discovery(db_session, indian_tenant_data):
    engine = CalendarEngine(db_session, indian_tenant_data)

    fake_today = date(2026, 10, 12)
    with patch("app.services.marketing.context_radar.calendar_engine.date") as mock_date:
        mock_date.today.return_value = fake_today
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        mock_date.fromisoformat = date.fromisoformat

        # Mock LLMGateway to return custom live discovered cultural events
        mock_llm_resp = """
        [
            {
                "name": "Kolkata Durga Puja Carnival & Festive Sprint",
                "date": "2026-10-22",
                "hook": "Join the celebratory spirit with grand festive discounts and customer appreciation.",
                "category": "cultural",
                "region": "India"
            }
        ]
        """
        with patch("app.services.llm_gateway.LLMGateway.has_configured_provider", return_value=True):
            with patch("app.services.llm_gateway.LLMGateway.complete", new=AsyncMock(return_value=mock_llm_resp)):
                discovered = await engine.discover_agentic_regional_events(
                    days_ahead=30,
                    force_refresh=True,
                )

    assert len(discovered) >= 1
    assert any("Durga Puja Carnival" in e["name"] for e in discovered)
    dp_discovered = next(e for e in discovered if "Durga Puja Carnival" in e["name"])
    assert dp_discovered["source"] == "agentic_radar"
    assert dp_discovered["region"] == "India"

    # Verify cached in BusinessProfile
    profile = db_session.query(BusinessProfile).filter_by(tenant_id=indian_tenant_data).first()
    assert profile.calendars is not None
    assert any("Durga Puja Carnival" in c.get("name", "") for c in profile.calendars)


@pytest.mark.asyncio
async def test_marketing_agent_scan_context_radar_with_regions(db_session, indian_tenant_data):
    agent = MarketingAgent(db_session, indian_tenant_data)

    fake_today = date(2026, 10, 12)
    with patch("app.services.marketing.context_radar.calendar_engine.date") as mock_date:
        mock_date.today.return_value = fake_today
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        mock_date.fromisoformat = date.fromisoformat

        radar_data = await agent.scan_context_radar({"days_ahead": 14})

    assert "target_regions" in radar_data
    assert "india" in radar_data["target_regions"]
    assert len(radar_data["upcoming_events"]) > 0

    event_names = [e["name"] for e in radar_data["upcoming_events"]]
    assert any("Navratri & Durga Puja" in n for n in event_names)
