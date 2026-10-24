"""Tests for the decomposed Sales domain services and SalesAgent facade."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agents.sales import SalesAgent, extract_json, _build_lead_data
from app.services.sales.discovery_service import DiscoveryService
from app.services.sales.enrichment_service import EnrichmentService
from app.services.sales.meeting_service import MeetingService
from app.services.sales.outreach_service import OutreachService
from app.services.sales.utils import extract_json as utils_extract_json


def test_extract_json_shared_utility():
    raw_markdown = "```json\n{\"company\": \"Acme Corp\", \"score\": 95}\n```"
    result = extract_json(raw_markdown)
    assert result == {"company": "Acme Corp", "score": 95}

    raw_array = "```[1, 2, 3]```"
    assert extract_json(raw_array) == [1, 2, 3]

    assert extract_json is utils_extract_json


def test_build_lead_data_structure():
    candidate = {
        "company_name": "Test Co",
        "website": "https://test.com",
        "industry": "Software",
        "contact": {
            "name": "Jane Doe",
            "title": "CTO",
            "linkedin_url": "https://linkedin.com/in/janedoe",
        },
        "why_now": "Recently raised Series A",
        "qualification_score": 88.5,
    }
    dossier = _build_lead_data(candidate)
    assert dossier["company"]["name"] == "Test Co"
    assert dossier["contact"]["name"] == "Jane Doe"
    assert dossier["contact"]["title"] == "CTO"
    assert dossier["why_now"] == "Recently raised Series A"
    assert dossier["qualification_score"] == 88.5


@pytest.mark.asyncio
async def test_sales_agent_facade_delegation():
    mock_db = MagicMock()
    tenant_id = "test-tenant-123"

    agent = SalesAgent(mock_db, tenant_id)

    # Verify decomposed sub-services are initialized
    assert isinstance(agent.discovery, DiscoveryService)
    assert isinstance(agent.enrichment, EnrichmentService)
    assert isinstance(agent.outreach, OutreachService)
    assert isinstance(agent.meeting, MeetingService)
    assert agent.orchestrator is not None

    # Test facade method delegations
    with patch.object(agent.discovery, "generate_leads", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {"status": "success", "generated_leads": 3}
        res = await agent.execute_task({"action": "generate_leads", "parameters": {"count": 3}})
        assert res["status"] == "success"
        mock_gen.assert_awaited_once_with({"count": 3})

    with patch.object(agent.outreach, "sales_outreach", new_callable=AsyncMock) as mock_outreach:
        mock_outreach.return_value = {"status": "success", "sent_count": 2}
        res = await agent.execute_task({"action": "sales_outreach", "parameters": {"channel": "smtp"}})
        assert res["sent_count"] == 2
        mock_outreach.assert_awaited_once_with({"channel": "smtp"})

    with patch.object(agent.meeting, "schedule_meeting", new_callable=AsyncMock) as mock_meeting:
        mock_meeting.return_value = {"status": "success", "booked_meetings": 1}
        res = await agent.execute_task({"action": "schedule_meeting", "parameters": {"tool": "google_calendar"}})
        assert res["booked_meetings"] == 1
        mock_meeting.assert_awaited_once_with({"tool": "google_calendar"})

    with patch.object(agent.orchestrator, "run_sales_ai_v3_workflow", new_callable=AsyncMock) as mock_wf:
        mock_wf.return_value = {"status": "success"}
        res = await agent.execute_task({"action": "run_v3_workflow"})
        assert res["status"] == "success"
        mock_wf.assert_awaited_once()


@pytest.mark.asyncio
async def test_enrichment_service_methods():
    mock_db = MagicMock()
    svc = EnrichmentService(mock_db, "tenant-1")

    # Apollo fetch with mock HTTP client
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"organizations": [{"id": "org_123"}]})
        org_id = await svc.fetch_apollo_org_data("fake-key", "example.com")
        assert org_id == "org_123"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"news_articles": [{"title": "Series B Funding", "snippet": "Raised $20M"}]},
        )
        news = await svc.fetch_apollo_news("fake-key", "org_123")
        assert len(news) == 1
        assert news[0]["title"] == "Series B Funding"


@pytest.mark.asyncio
async def test_meeting_service_handles_empty_queue():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []
    svc = MeetingService(mock_db, "tenant-1")

    res = await svc.schedule_meeting({"tool": "google_calendar"})
    assert res["status"] == "success"
    assert res["booked_meetings"] == 0
    assert res["awaiting_replies"] == 0
