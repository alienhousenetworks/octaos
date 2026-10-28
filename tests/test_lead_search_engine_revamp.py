import pytest
from app.services.sales_os.search_v4.contracts import (
    CampaignIntentSpec,
    DiscoveryRecord,
    IntentCategory,
    QualifiedCandidate,
    SearchBatch,
)
from app.services.sales_os.search_v4.bridge import _lead_from_candidate, merge_connector_leads
from app.services.sales_os.search_v4.connectors.extract import contact_from_text
from app.services.research import EnterpriseWebResearchService
from app.services.sales_os.search_v4.evidence import verify_evidence
from app.services.sales_os.search_v4.scoring import score_record
from app.services.sales_os.search_v4.registry import credential_map, choose_web_provider, ProviderStats, ProviderHealth


def _make_spec():
    return CampaignIntentSpec(
        campaign_id="test-camp",
        tenant_id="tenant-1",
        query="SaaS automation tools",
        industries=["tech"],
        buyer_roles=["Founder"],
        geography=["United States"],
        freshness="30_days",
        budget_inr=500.0,
    )


def _make_candidate(company="Acme SaaS", domain="acmesaasonline.com", email="", name="", decision="accept"):
    rec = DiscoveryRecord(
        correlation_id="c1",
        task_id="t1",
        tenant_id="tenant-1",
        method="web",
        provider="duckduckgo",
        original_url=f"https://{domain}/pricing",
        canonical_url=f"{domain}/pricing",
        title=f"{company} - Modern SaaS Platform",
        snippet=f"{company} offers enterprise workflow automation.",
        dedupe_key=f"{domain}/pricing",
        company_name=company,
        company_domain=domain,
        contact_name=name,
        contact_email=email,
    )
    ev = verify_evidence(rec, IntentCategory.DIRECT_BUYING_INTENT, rec.snippet, True, "30_days")
    assessment = score_record(rec, _make_spec(), IntentCategory.DIRECT_BUYING_INTENT, ev, set())
    assessment.decision = decision
    return QualifiedCandidate(record=rec, evidence=ev, assessment=assessment)


def test_bridge_preserves_company_account_leads_when_no_personal_email():
    """Real business accounts with domains should not be discarded as None."""
    candidate = _make_candidate(company="FlowState Inc", domain="flowstate.io", email="", name="")
    lead = _lead_from_candidate(candidate)

    assert lead is not None
    assert lead["company"] == "FlowState Inc"
    assert lead["website"] == "flowstate.io"
    assert lead["name"] == "FlowState Inc"
    assert lead["email"] is None

    batch = SearchBatch(
        job_id="j1",
        correlation_id="c1",
        tenant_id="tenant-1",
        status="succeeded",
        tasks=[],
        records=[candidate.record],
        candidates=[candidate],
        qualified=[candidate],
        rejected=[],
        ledger=[],
        report="qualified=1",
    )
    merged, report = merge_connector_leads([], batch)
    assert len(merged) == 1
    assert merged[0]["company"] == "FlowState Inc"
    assert merged[0]["website"] == "flowstate.io"


def test_enterprise_web_summarize_promotes_company_leads():
    """When personal contacts are fewer than count, valid companies should be promoted to contacts."""
    cand1 = _make_candidate(company="LeadGen Co", domain="leadgen.ai", email="", name="")
    cand2 = _make_candidate(company="CloudSync", domain="cloudsync.net", email="sales@cloudsync.net", name="Sales Team")

    batch = SearchBatch(
        job_id="j2",
        correlation_id="c2",
        tenant_id="tenant-1",
        status="succeeded",
        tasks=[],
        records=[cand1.record, cand2.record],
        candidates=[cand1, cand2],
        qualified=[cand1, cand2],
        rejected=[],
        ledger=[],
        report="qualified=2",
    )

    summary = EnterpriseWebResearchService.summarize(batch, count=5)
    # Both cand2 (personal/team email) and cand1 (company lead) should be in contacts
    assert len(summary["contacts"]) == 2
    companies = [c["company"] for c in summary["contacts"]]
    assert "CloudSync" in companies
    assert "LeadGen Co" in companies


def test_contact_from_text_extracts_corporate_inboxes():
    """Extracts support/sales inboxes and names forward or backward without 80-char rigid block."""
    html_snippet = "Welcome to CloudCorp. Contact our team at sales@cloudcorp.com or call our offices."
    name, email = contact_from_text(html_snippet, "https://cloudcorp.com")
    assert email == "sales@cloudcorp.com"

    html_snippet_with_name = "Chief Technology Officer: Alice Smith. Email: alice@cloudcorp.com"
    name2, email2 = contact_from_text(html_snippet_with_name, "https://cloudcorp.com")
    assert email2 == "alice@cloudcorp.com"
    assert name2 == "Alice Smith"


def test_search_v4_registry_loads_firecrawl_credential(monkeypatch):
    """Firecrawl key is loaded into credential_map and recognized in choose_web_provider."""
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test-key-123")
    creds = credential_map()
    assert creds.get("firecrawl") == "fc-test-key-123"

    stats = ProviderStats()
    health = ProviderHealth()
    provider, reason, cost = choose_web_provider(creds, stats, health)
    assert provider == "firecrawl"
    assert cost == 0.50
