"""Web research keeps searching when a round is empty, and still refuses invented emails."""
import json

import pytest

from app.services.sales_os.discovery import web_discovery
from app.services.sales_os.discovery.web_discovery import (
    analyst_instructions,
    discover_leads_from_web,
    research_brief,
    _usable_result,
)


def test_analyst_prompt_keeps_the_brief_and_drops_the_source_tag():
    text = analyst_instructions("Find clinics.\n\n[MANUAL_SOURCE_OVERRIDE: apollo]")
    assert "Find clinics." in text
    assert "MANUAL_SOURCE_OVERRIDE" not in text


def test_research_brief_includes_profile_facts_without_replacing_them():
    brief = research_brief(
        "clinics",
        industries=["healthcare"],
        countries=["UAE", "India"],
        buyers=["Founder"],
        budget="3L-10L",
        offer="Custom Flutter apps",
    )
    assert "Search target: clinics" in brief
    assert "UAE" in brief
    assert "Custom Flutter apps" in brief


def test_public_social_posts_stay_searchable_and_social_feeds_do_not():
    assert _usable_result("https://www.linkedin.com/posts/acme-1")
    assert _usable_result("https://x.com/acme/status/1")
    assert _usable_result("https://www.reddit.com/r/startups/comments/abc")
    assert not _usable_result("https://www.facebook.com/acme")
    assert not _usable_result("https://www.google.com/search?q=acme")


@pytest.mark.asyncio
async def test_empty_round_starts_another_search(monkeypatch):
    plans = []

    async def complete(prompt, **kwargs):
        if "Plan the next web searches" in prompt:
            plans.append(prompt)
            if len(plans) == 1:
                return json.dumps(["alpha clinics nothing"])
            return json.dumps(["beta clinics contact"])
        return json.dumps([{
            "name": "Ada Lovelace",
            "title": "Founder",
            "email": "ada@acme.test",
            "company": "Acme",
            "phone": "555",
        }])

    async def search(client, query, limit):
        if "nothing" in query:
            return []
        return ["https://acme.test/contact"]

    async def fetch(client, url):
        return "Founder Ada Lovelace ada@acme.test Acme Clinic"

    monkeypatch.setattr(web_discovery, "_search", search)
    monkeypatch.setattr(web_discovery, "_fetch_text", fetch)
    monkeypatch.setattr(web_discovery, "_has_mx", lambda domain: True)

    leads = await discover_leads_from_web(
        complete,
        json.loads,
        "clinics",
        5,
        analyst_prompt="Find clinics that need a custom app.",
        max_rounds=2,
    )

    assert len(plans) == 2
    assert leads[0]["email"] == "ada@acme.test"
    assert leads[0]["name"] == "Ada Lovelace"
    assert leads[0]["evidence_url"] == "https://acme.test/contact"


@pytest.mark.asyncio
async def test_email_must_appear_on_the_page(monkeypatch):
    async def complete(prompt, **kwargs):
        if "Plan the next web searches" in prompt:
            return json.dumps(["clinics contact"])
        return json.dumps([{
            "name": "Ada Lovelace",
            "title": "Founder",
            "email": "invented@acme.test",
            "company": "Acme",
            "phone": "",
        }])

    async def search(client, query, limit):
        return ["https://acme.test/contact"]

    async def fetch(client, url):
        return "Write to ada@acme.test about the clinic portal."

    monkeypatch.setattr(web_discovery, "_search", search)
    monkeypatch.setattr(web_discovery, "_fetch_text", fetch)
    monkeypatch.setattr(web_discovery, "_has_mx", lambda domain: True)

    leads = await discover_leads_from_web(complete, json.loads, "clinics", 5, max_rounds=1)

    assert [lead["email"] for lead in leads] == ["ada@acme.test"]


@pytest.mark.asyncio
async def test_all_empty_rounds_report_the_search_instead_of_stopping_early(monkeypatch):
    searches = []

    async def complete(prompt, **kwargs):
        return json.dumps([f"query-{len(searches) + 1}"])

    async def search(client, query, limit):
        searches.append(query)
        return []

    monkeypatch.setattr(web_discovery, "_search", search)

    with pytest.raises(RuntimeError) as caught:
        await discover_leads_from_web(complete, json.loads, "clinics", 5, max_rounds=3)

    assert len(searches) == 3
    assert "3 search rounds" in str(caught.value)
    assert "query-1" in str(caught.value)
