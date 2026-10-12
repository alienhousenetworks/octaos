import pytest
from app.services.sales_os.discovery.source_registry import (
    get_all_sources,
    get_all_source_ids,
    get_source,
    get_sources_by_tier,
    get_sources_by_capability,
    SourceTier,
    SourceCapability,
    BLUEPRINT_CANONICAL,
)
from app.services.sales_os.discovery.connectors import fetch_leads_from_source
from app.services.sales_os.providers.base import ConnectorUnavailable


def test_source_registry_catalogue():
    sources = get_all_sources()
    source_ids = get_all_source_ids()
    
    # Verify catalogue contains 60+ sources
    assert len(sources) >= 60, f"Expected >= 60 sources, found {len(sources)}"
    assert len(source_ids) == len(sources)

    # Verify baseline 13 sources are present
    baseline_13 = [
        "apollo", "hunter", "google_places", "apify_google_places",
        "apify_instagram", "apify_linkedin", "apify_crawler", "zoominfo",
        "cognism", "people_data_labs", "clearbit", "crunchbase", "csv_json_bulk"
    ]
    for b in baseline_13:
        assert b in sources, f"Baseline source {b} missing from catalogue"

    # Verify 40+ signal sources across all tiers are present
    intent_sources = [
        "greenhouse", "lever", "ashby", "workable", "hn_hiring",
        "pitchbook", "dealroom", "tracxn", "sec_edgar",
        "builtwith", "wappalyzer", "storeleads", "dns_mx_inspect",
        "g2", "capterra", "trustpilot", "reddit_intent",
        "gem_portal", "cppp_portal", "sam_gov",
        "lusha", "rocketreach", "snov", "prospeo", "findymail", "fullenrich",
        "indiamart", "tradeindia", "clutch", "goodfirms"
    ]
    for s in intent_sources:
        assert s in sources, f"Signal source {s} missing from catalogue"


def test_source_tier_groupings():
    hiring_sources = get_sources_by_tier(SourceTier.TIER_A_HIRING)
    assert len(hiring_sources) >= 8
    
    procurement_sources = get_sources_by_tier(SourceTier.TIER_A_PROCUREMENT)
    assert len(procurement_sources) >= 4
    
    enrichment_sources = get_sources_by_tier(SourceTier.TIER_B_ENRICHMENT)
    assert len(enrichment_sources) >= 10


def test_every_source_has_a_lead_adapter():
    from app.services.sales_os.providers.adapters import build_adapter
    from app.services.sales_os.providers.registry import implementation_status

    for source_id in get_all_source_ids():
        status = implementation_status(source_id)
        assert status in {"live", "partial"}, source_id
        adapter = build_adapter(source_id)
        assert adapter.provider_key == source_id
        assert adapter.capabilities() or status == "partial"


def test_blueprint_ids_resolve():
    assert len(BLUEPRINT_CANONICAL) == 79
    for blueprint_id, source_id in BLUEPRINT_CANONICAL.items():
        assert get_source(source_id) is not None, f"{blueprint_id} -> {source_id} is not in the catalogue"


class _Response:
    def __init__(self, status_code: int, body=None, text: str = ""):
        self.status_code = status_code
        self._body = body
        self.text = text

    def json(self):
        if isinstance(self._body, str):
            raise ValueError("not json")
        return self._body


@pytest.mark.asyncio
async def test_failed_connectors_do_not_invent_leads():
    async def transport(method, url, **kwargs):
        del method, url, kwargs
        return _Response(500, {}, text="upstream failed")

    for provider in ("greenhouse", "builtwith", "gem_portal", "lusha"):
        with pytest.raises(ConnectorUnavailable) as caught:
            await fetch_leads_from_source(provider, "mock_key", "Acme Corp", count=2, transport=transport)
        message = str(caught.value).lower()
        assert "@" not in message
        assert "talent" not in message
        assert "vp" not in message


@pytest.mark.asyncio
async def test_greenhouse_jobs_become_leads_without_invented_email():
    async def transport(method, url, **kwargs):
        del method, kwargs
        assert "boards-api.greenhouse.io" in url
        return _Response(200, {"jobs": [{"id": 7, "title": "Account Executive", "absolute_url": "https://boards.greenhouse.io/acme/jobs/7", "location": {"name": "Pune"}}]})

    leads = await fetch_leads_from_source("greenhouse", "", "acme.com", count=2, transport=transport)
    assert leads
    assert leads[0]["company"]
    assert leads[0]["email"] == ""
    assert "Account Executive" in (leads[0].get("title") or "")
    assert leads[0]["evidence_url"].startswith("https://boards.greenhouse.io/")
