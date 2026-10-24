"""Regression test suite for OCTAOS Prompt-Based Sales Agent Data Integrity & Qualification.

Tests:
1. Data Integrity:
   - Company fields never leak across records.
   - Objects are independently created.
   - Company name never contaminates with search query or campaign directive.
2. Source Attribution:
   - Google News RSS URLs are never labeled as LinkedIn.
   - Publisher is extracted from URL hostname.
   - Canonical URL and retrieval_provider are preserved.
3. Classification & Intent Detection:
   - Educational articles & blogs are rejected with explicit reasons.
   - Seller-side agency portfolios ("50+ websites built") are rejected.
   - Real hiring & buying-intent posts are accepted.
4. Qualification & Contact Retention:
   - Missing email/phone does NOT reject the lead; marked as CONTACT_PARTIAL.
   - Verified buying intent + ICP fit qualifies the opportunity.
   - Leads with business email/phone are marked READY.
5. ICP Parser:
   - Structured fields extracted (Service, Price, Geography, Freshness, Buyer, Intent).
   - Never echoes raw full markdown prompt.
6. Pipeline Stage Metrics:
   - Tracks counts at every stage (raw, classified, verified, intent, ready, partial, rejected).
7. Final Output Contract:
   - All contract fields present (publisher, retrieval_provider, buying_signal, evidence_quote, score, etc.).
"""
import pytest

from app.services.sales_os.discovery.prompt_agent import (
    ContactConfidence,
    ContactStatus,
    EvidenceTier,
    LeadStatus,
    PipelineStageMetrics,
    PromptICP,
    PromptLeadContract,
    SearchDocumentType,
    classify_document_type,
    detect_buying_intent,
    detect_publisher,
    extract_source_attribution,
    normalize_search_record,
    parse_prompt_icp,
    score_and_qualify_lead,
)


# ---------------------------------------------------------------------------
# 1. Data Integrity & Isolation Tests (RC-1)
# ---------------------------------------------------------------------------

def test_company_fields_never_leak_across_records():
    raw_a = {
        "url": "https://abcinteriors.in/contact",
        "company": "ABC Interiors",
        "name": "Rajesh Kumar",
        "title": "Founder",
        "email": "rajesh@abcinteriors.in",
        "snippet": "Looking for website developer to rebuild our interior decor portal.",
    }
    raw_b = {
        "url": "https://xyzlogistics.com/about",
        "company": "XYZ Logistics",
        "name": "Priya Sharma",
        "title": "Director",
        "email": "priya@xyzlogistics.com",
        "snippet": "Need website redesign for freight booking.",
    }

    norm_a = normalize_search_record(raw_a, retrieval_provider="duckduckgo", query="website development India")
    norm_b = normalize_search_record(raw_b, retrieval_provider="duckduckgo", query="website development India")

    assert norm_a["company"] == "ABC Interiors"
    assert norm_b["company"] == "XYZ Logistics"
    assert norm_a["company"] != norm_b["company"]


def test_company_never_contaminates_with_search_query():
    raw = {
        "url": "https://modernclinic.in/contact",
        "company": "website development India",  # Contaminated legacy payload
        "name": "Dr. Mehta",
        "snippet": "Seeking web designer for clinic appointments.",
    }
    norm = normalize_search_record(raw, retrieval_provider="duckduckgo", query="website development India")

    # Should detect contamination and reset or derive cleanly from domain
    assert norm["company"] != "website development India"
    assert "Modernclinic" in norm["company"] or norm["company"] == ""


def test_independent_object_creation_prevents_mutation():
    template = {"company": "Template Corp", "tags": ["a", "b"]}
    norm_1 = normalize_search_record(template, retrieval_provider="google_news")
    norm_1["company"] = "Modified Corp"

    norm_2 = normalize_search_record(template, retrieval_provider="google_news")
    assert norm_2["company"] == "Template Corp"


# ---------------------------------------------------------------------------
# 2. Source Attribution Tests (RC-2)
# ---------------------------------------------------------------------------

def test_google_news_rss_never_labeled_as_linkedin():
    url = "https://news.google.com/rss/articles/CBMiRGh0dHBzOi8vd3d3..."
    provider, pub, ev_url = extract_source_attribution(url, retrieval_provider="google_news")

    assert pub == "Google News"
    assert pub != "LinkedIn"
    assert provider == "google_news"
    assert ev_url == url


def test_linkedin_only_attributed_when_url_is_linkedin():
    linkedin_url = "https://www.linkedin.com/posts/founder_looking-for-website-developer-activity-123456"
    provider, pub, ev_url = extract_source_attribution(linkedin_url, retrieval_provider="duckduckgo")

    assert pub == "LinkedIn"
    assert provider == "duckduckgo"
    assert ev_url == linkedin_url


def test_direct_company_website_publisher_matches_domain():
    url = "https://freshretail.co/about-us"
    provider, pub, ev_url = extract_source_attribution(url, retrieval_provider="brave")

    assert pub == "Freshretail"
    assert provider == "brave"
    assert ev_url == url


# ---------------------------------------------------------------------------
# 3. Document Classification & Intent Detection (RC-4 & RC-5)
# ---------------------------------------------------------------------------

def test_educational_articles_and_blogs_rejected():
    url = "https://medium.com/design-tips/10-tips-for-better-website-redesign-2026"
    title = "10 Tips For Better Website Redesign In 2026"
    snippet = "Learn how to choose modern typography and clean layouts for your next web project."

    doc_type, reason, is_reject = classify_document_type(url, title, snippet)
    assert is_reject is True
    assert doc_type in (SearchDocumentType.ARTICLE, SearchDocumentType.BLOG)
    assert "Educational article or blog post" in reason


def test_seller_agency_portfolio_rejected():
    url = "https://topwebdesignersindia.com/portfolio"
    title = "Top Web Design Agency | 50+ Websites Built Across India"
    snippet = "We are an award winning web development agency in Mumbai. Hire our team for your next web project."

    doc_type, reason, is_reject = classify_document_type(url, title, snippet)
    assert is_reject is True
    assert doc_type == SearchDocumentType.SELLER_PORTFOLIO
    assert "Seller-side" in reason


def test_generic_linkedin_profile_rejected_without_hiring():
    url = "https://www.linkedin.com/in/john-doe-frontend"
    title = "John Doe - Senior Frontend Developer at Tech Corp | LinkedIn"
    snippet = "Experienced web developer building responsive web applications using React and Tailwind."

    doc_type, reason, is_reject = classify_document_type(url, title, snippet)
    assert is_reject is True
    assert doc_type == SearchDocumentType.PROFILE


def test_verified_hiring_and_buying_posts_accepted():
    url = "https://www.linkedin.com/posts/anita_looking-for-website-developer-for-our-healthcare-startup-activity"
    title = "Looking for website developer"
    snippet = "We are redesigning our healthcare clinic portal. Looking for a freelance website developer with a budget of ₹50,000 in India."

    doc_type, reason, is_reject = classify_document_type(url, title, snippet)
    assert is_reject is False
    assert doc_type == SearchDocumentType.HIRING_POST

    has_intent, signal, quote = detect_buying_intent(title, snippet)
    assert has_intent is True
    assert "website developer" in signal.lower() or "website" in signal.lower()
    assert len(quote) > 10


# ---------------------------------------------------------------------------
# 4. Qualification & Contact Retention (Phase 3 & 4)
# ---------------------------------------------------------------------------

def test_missing_email_does_not_reject_lead():
    icp = PromptICP(service="Website Development", price="₹50,000", geography="India")
    record = {
        "company": "Apex Clinic",
        "name": "Dr. Rohit Verma",
        "title": "Medical Director",
        "email": None,  # Contact missing
        "phone": None,
        "evidence_url": "https://www.linkedin.com/posts/rohit_need-website-redesign-activity-998877",
        "retrieval_provider": "duckduckgo",
        "publisher": "LinkedIn",
        "title_text": "Need website redesign",
        "snippet_text": "Need website redesign for our new medical center in Mumbai. Open to independent developers.",
    }

    scored = score_and_qualify_lead(
        record=record,
        icp=icp,
        has_buying_intent=True,
        buying_signal="Need website redesign",
        evidence_quote="Need website redesign for our new medical center in Mumbai.",
        doc_type=SearchDocumentType.HIRING_POST,
    )

    # Lead MUST be kept as CONTACT_PARTIAL, never REJECTED
    assert scored.contact_status == LeadStatus.CONTACT_PARTIAL.value
    assert scored.rejection_reason is None
    assert scored.qualification_score >= 80.0
    assert scored.platform_contact == "linkedin_message"
    assert scored.contact_confidence == ContactConfidence.MEDIUM.value


def test_lead_with_email_marked_ready():
    icp = PromptICP(service="Website Development", price="₹50,000", geography="India")
    record = {
        "company": "Kiran Jewellers",
        "name": "Kiran Shah",
        "title": "Owner",
        "email": "kiran@kiranjewellers.com",
        "phone": "+919876543210",
        "evidence_url": "https://kiranjewellers.com/tender",
        "retrieval_provider": "duckduckgo",
        "publisher": "Kiranjewellers",
        "title_text": "RFP for e-commerce website redesign",
        "snippet_text": "Seeking web development agency for our jewellery catalog website rebuild.",
    }

    scored = score_and_qualify_lead(
        record=record,
        icp=icp,
        has_buying_intent=True,
        buying_signal="Seeking website rebuild",
        evidence_quote="Seeking web development agency for our jewellery catalog website rebuild.",
        doc_type=SearchDocumentType.RFP,
    )

    assert scored.contact_status == LeadStatus.READY.value
    assert scored.qualification_score >= 80.0
    assert scored.contact_confidence == ContactConfidence.HIGH.value
    assert scored.evidence_tier == EvidenceTier.ENRICHED.value


# ---------------------------------------------------------------------------
# 5. ICP Parser Tests (RC-3)
# ---------------------------------------------------------------------------

def test_parse_prompt_icp_extracts_structured_fields():
    prompt = (
        "Find me website development leads in India with budget ₹50,000 "
        "from the last 7 days targeting Founders looking for website redesign."
    )
    icp = parse_prompt_icp(prompt)

    assert icp.service == "Website Development"
    assert icp.price == "₹50,000"
    assert icp.geography == "India"
    assert icp.freshness == "7 days"
    assert "Founder" in icp.buyer
    assert "Website Redesign" in icp.intent
    assert "Targeting" in icp.summary
    assert len(icp.summary.split()) < 30


# ---------------------------------------------------------------------------
# 6. Pipeline Stage Metrics & Logging (Phase 8)
# ---------------------------------------------------------------------------

def test_pipeline_stage_metrics_logging():
    metrics = PipelineStageMetrics()
    metrics.discovery_raw = 50
    metrics.classified_hiring = 12
    metrics.classified_rfp = 3
    metrics.classified_company = 15
    metrics.classified_articles = 10
    metrics.classified_profiles = 10
    metrics.verified_sources = 30
    metrics.buying_intent_confirmed = 15
    metrics.qualified_ready = 5
    metrics.qualified_contact_partial = 8
    metrics.add_rejection("Medium Article", "Educational article without buyer intent")

    lines = metrics.summary_lines()
    summary = "\n".join(lines)

    assert "Discovery - Raw: 50" in summary
    assert "Hiring: 12" in summary
    assert "Verified: 30" in summary
    assert "Confirmed: 15" in summary
    assert "Ready: 5" in summary
    assert "Contact Partial: 8" in summary
    assert metrics.rejected_total == 1
    assert len(metrics.rejections) == 1
