import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.services.sales_os.discovery.web_discovery import (
    synthesize_corporate_email,
    _usable_result,
    discover_leads_from_web,
)
from app.services.sales_os.search_v4.connectors.extract import contact_from_text
from app.services.sales_os.search_v4.planner import plan_tasks
from app.services.sales_os.search_v4.contracts import CampaignIntentSpec
from app.services.sales_os.search_v4.registry import ProviderHealth, ProviderStats


def test_synthesize_corporate_email():
    # Standard first.last
    email = synthesize_corporate_email("Satya Nadella", "microsoft.com")
    assert email == "satya.nadella@microsoft.com"

    # Single name
    email_single = synthesize_corporate_email("Cher", "acme.io")
    assert email_single == "cher@acme.io"

    # Honorific prefix stripping
    email_prefix = synthesize_corporate_email("Dr. Jane Watson", "healthcorp.org")
    assert email_prefix == "jane.watson@healthcorp.org"

    # Public webmail rejected
    assert synthesize_corporate_email("John Doe", "gmail.com") is None
    assert synthesize_corporate_email("Jane Smith", "yahoo.com") is None


def test_usable_result_allows_social_and_company_profiles():
    assert _usable_result("https://www.linkedin.com/in/satyanadella") is True
    assert _usable_result("https://www.linkedin.com/company/microsoft") is True
    assert _usable_result("https://twitter.com/sama") is True
    assert _usable_result("https://x.com/elonmusk") is True
    assert _usable_result("https://acme.com/about-us") is True
    # Private search engines and video portals skipped
    assert _usable_result("https://www.youtube.com/watch?v=123") is False
    assert _usable_result("https://duckduckgo.com/?q=test") is False


def test_contact_from_text_supports_cross_domain_platforms():
    text = "Join us in welcoming John Doe (john.doe@techscale.io), our new VP of Engineering at TechScale."
    name, email = contact_from_text(text, "https://www.linkedin.com/posts/techscale-update-123")
    assert email == "john.doe@techscale.io"
    assert name == "John Doe"


def test_planner_generates_dynamic_buyer_and_social_tasks():
    spec = CampaignIntentSpec(
        campaign_id="test-camp-1",
        tenant_id="tenant-1",
        query="Cybersecurity Penetration Testing",
        industries=["Fintech"],
        buyer_roles=["CISO"],
        geography=["United States"],
        freshness="30_days",
    )
    health = ProviderHealth()
    stats = ProviderStats()
    tasks, notes = plan_tasks(spec, credentials={}, history=[], stats=stats, health=health, remaining_inr=500.0)

    queries = [t.query for t in tasks]
    # Verify dynamic buyer phrases contain the specific topic rather than hardcoded web developer phrases
    assert any("Cybersecurity Penetration Testing" in q for q in queries)
    # Verify LinkedIn or Twitter search task is planned
    assert any("site:linkedin.com" in q or "site:twitter.com" in q for q in queries)


@pytest.mark.asyncio
async def test_discover_leads_from_web_extracts_and_synthesizes():
    mock_complete = AsyncMock(return_value="""[
        {
            "name": "Alex Mercer",
            "title": "Founder & CEO",
            "company": "CloudForge Systems",
            "email": "",
            "phone": "+1 415 555 0199"
        }
    ]""")
    mock_extract_json = lambda s: [
        {
            "name": "Alex Mercer",
            "title": "Founder & CEO",
            "company": "CloudForge Systems",
            "email": "",
            "phone": "+1 415 555 0199"
        }
    ]

    # Mock page fetcher returning HTML with founder info but no raw body email
    async def mock_fetch_html(client, url):
        return (
            "<html><head><title>CloudForge Systems | NextGen Cloud</title></head>"
            "<body><h1>CloudForge Systems</h1><p>Founded by Alex Mercer in 2026.</p></body></html>",
            "CloudForge Systems. Founded by Alex Mercer, Founder & CEO. Contact our team.",
            {"date": "2026-10-01"}
        )

    import app.services.sales_os.discovery.web_discovery as wd
    orig_fetch = wd._fetch_html_and_text
    orig_search = wd._search
    orig_has_mx = wd._has_mx
    try:
        wd._fetch_html_and_text = mock_fetch_html
        wd._search = AsyncMock(return_value=["https://cloudforge.io"])
        wd._has_mx = lambda d: True

        leads = await discover_leads_from_web(
            complete=mock_complete,
            extract_json=mock_extract_json,
            query="Cloud Infrastructure",
            count=1,
            freshness_window="30_days",
        )

        assert len(leads) >= 1
        lead = leads[0]
        assert lead["name"] == "Alex Mercer"
        assert lead["company"] == "CloudForge Systems"
        # Corporate email synthesized from name + website domain
        assert lead["email"] == "alex.mercer@cloudforge.io"
        assert lead["website"] == "cloudforge.io"
    finally:
        wd._fetch_html_and_text = orig_fetch
        wd._search = orig_search
        wd._has_mx = orig_has_mx
