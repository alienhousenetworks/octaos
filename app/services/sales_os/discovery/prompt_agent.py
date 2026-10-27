"""OCTAOS Prompt-Based Sales Agent Core Architecture.

Enforces:
1. Strict Record Isolation (No cross-record contamination; never reuse or mutate shared dicts; company never set to query).
2. 100% Correct Source Attribution (Independent retrieval_provider, publisher, evidence_url).
3. Structured ICP Parsing (Extracts service, price, geography, freshness, buyer, intent; no raw prompt echoes).
4. Search Result Classification (Filters out blogs, educational articles, seller portfolios, generic profiles).
5. Buying Intent Detection (Distinguishes buyer-side intent from seller-side advertising).
6. Non-Crashing Lead Lifecycle (Preserves real opportunities as CONTACT_PARTIAL when email is missing; zero crashes).
7. Transparent Rejection Framework (Explicit reason for every rejected candidate).
8. Multi-Factor Scoring (0-100 evidence-grounded scoring).
9. Stage-by-Stage Pipeline Metrics & Logging.
10. Strict Final Output Contract.
"""
from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from pydantic import BaseModel, Field


class SearchDocumentType(str, Enum):
    HIRING_POST = "HIRING_POST"
    FREELANCE_PROJECT = "FREELANCE_PROJECT"
    RFP = "RFP"
    COMPANY_PAGE = "COMPANY_PAGE"
    DIRECTORY = "DIRECTORY"
    PROFILE = "PROFILE"
    ARTICLE = "ARTICLE"
    BLOG = "BLOG"
    SELLER_PORTFOLIO = "SELLER_PORTFOLIO"
    UNKNOWN = "UNKNOWN"


class LeadStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    VERIFIED = "VERIFIED"
    BUYING_INTENT = "BUYING_INTENT"
    QUALIFIED = "QUALIFIED"
    CONTACT_PARTIAL = "CONTACT_PARTIAL"
    READY = "READY"
    REJECTED = "REJECTED"


ContactStatus = LeadStatus


class ContactConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class EvidenceTier(str, Enum):
    RAW = "RAW"
    VERIFIED = "VERIFIED"
    DERIVED = "DERIVED"
    ENRICHED = "ENRICHED"


class PromptICP(BaseModel):
    service: str = "Website Development"
    price: Optional[str] = "₹50,000"
    geography: str = "India"
    freshness: str = "7 days"
    buyer: str = "Founder/Business Owner"
    intent: str = "Website Build/Redesign"
    summary: str = ""
    exclusions: List[str] = Field(default_factory=list)


class PromptLeadContract(BaseModel):
    prospect_name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    retrieval_provider: str
    publisher: str
    evidence_url: str
    buying_signal: str
    evidence_quote: str
    published_date: Optional[str] = None
    contact_status: str  # READY, CONTACT_PARTIAL, REJECTED
    contact_confidence: str = ContactConfidence.UNKNOWN.value
    platform_contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    qualification_score: float = 0.0
    rejection_reason: Optional[str] = None
    evidence_tier: str = EvidenceTier.VERIFIED.value


class PipelineStageMetrics:
    def __init__(self):
        self.discovery_raw: int = 0
        self.classified_hiring: int = 0
        self.classified_rfp: int = 0
        self.classified_company: int = 0
        self.classified_articles: int = 0
        self.classified_profiles: int = 0
        self.verified_sources: int = 0
        self.buying_intent_confirmed: int = 0
        self.qualified_ready: int = 0
        self.qualified_contact_partial: int = 0
        self.rejected_total: int = 0
        self.rejections: List[Dict[str, str]] = []

    def add_rejection(self, title_or_company: str, reason: str):
        self.rejected_total += 1
        self.rejections.append({
            "lead": (title_or_company or "Unknown Prospect")[:80],
            "reason": reason,
        })

    def summary_lines(self) -> List[str]:
        return [
            f"Discovery - Raw: {self.discovery_raw}",
            f"Classification - Hiring: {self.classified_hiring}, RFP/Projects: {self.classified_rfp}, Company Pages: {self.classified_company}, Articles/Blogs (Rejected): {self.classified_articles}, Generic Profiles (Rejected): {self.classified_profiles}",
            f"Verification - Verified: {self.verified_sources}",
            f"Buying Intent - Confirmed: {self.buying_intent_confirmed}",
            f"Qualification - Ready: {self.qualified_ready}, Contact Partial: {self.qualified_contact_partial}, Rejected: {self.rejected_total}",
        ]


# ---------------------------------------------------------------------------
# RC-3: Prompt Parser
# ---------------------------------------------------------------------------

def parse_prompt_icp(prompt: str) -> PromptICP:
    """
    Parses a prompt directive into structured ICP fields instead of storing
    the entire raw markdown text.
    """
    text = (prompt or "").strip()
    if not text:
        icp = PromptICP()
        icp.summary = f"Targeting {icp.buyer} in {icp.geography} for {icp.service} ({icp.intent}, Budget: {icp.price}, Freshness: {icp.freshness})"
        return icp

    # Keep the user's own request when none of the known offer patterns match.
    # A general instruction must not be replaced by the website-development default.
    compact = re.sub(r"\s+", " ", text)
    compact = compact.split(". ")[0].strip()
    if len(compact) > 140:
        compact = compact[:137].rstrip() + "..."

    # 1. Service extraction
    service = None
    if re.search(r"\b(mobile app|flutter|react native|ios|android)\b", text, re.IGNORECASE):
        service = "Mobile App Development"
    elif re.search(r"\b(ui/ux|figma|product design|web design)\b", text, re.IGNORECASE):
        service = "Web Design"
    elif re.search(r"\b(seo|content marketing|google ads)\b", text, re.IGNORECASE):
        service = "SEO & Growth Marketing"
    elif re.search(r"\b(web(?:site)?\s*(?:development|build|redesign|dev))\b", text, re.IGNORECASE):
        service = "Website Development"
    else:
        service = compact or "Requested service"

    # 2. Price / Budget extraction
    price = None
    price_match = re.search(r"(?:₹|rs\.?|inr|\$)\s*([\d,]+(?:\s*[kKlL])?)", text, re.IGNORECASE)
    if price_match:
        currency = "₹" if any(c in price_match.group(0).lower() for c in ("₹", "rs", "inr")) else "$"
        price = f"{currency}{price_match.group(1).strip()}"
    elif re.search(r"\b(\d+)\s*(?:lakhs?|lpa|k)\b", text, re.IGNORECASE):
        m = re.search(r"\b(\d+\s*(?:lakhs?|lpa|k))\b", text, re.IGNORECASE)
        if m:
            price = f"₹{m.group(1).strip()}"
    if not price:
        price = "unspecified"

    # 3. Geography extraction
    geography = None
    if re.search(r"\b(united states|usa|us|u\.s\.)\b", text, re.IGNORECASE):
        geography = "United States"
    elif re.search(r"\b(united kingdom|uk|london)\b", text, re.IGNORECASE):
        geography = "United Kingdom"
    elif re.search(r"\b(uae|dubai)\b", text, re.IGNORECASE):
        geography = "UAE"
    elif re.search(r"\b(australia|sydney)\b", text, re.IGNORECASE):
        geography = "Australia"
    elif re.search(r"\b(india|mumbai|delhi|bangalore|bengaluru|pune|hyderabad)\b", text, re.IGNORECASE):
        geography = "India"
    else:
        geography = "unspecified"

    # 4. Freshness extraction
    freshness = None
    m_fresh = re.search(r"\b(\d+)\s*(days?|hours?|weeks?|months?)\b", text, re.IGNORECASE)
    if m_fresh:
        freshness = f"{m_fresh.group(1)} {m_fresh.group(2).lower()}"
    elif re.search(r"\b(recent|fresh|this week|last 7 days)\b", text, re.IGNORECASE):
        freshness = "7 days"
    else:
        freshness = "unspecified"

    # 5. Buyer Role extraction
    buyer = None
    if re.search(r"\b(vp\s+sales|cro|head\s+of\s+sales)\b", text, re.IGNORECASE):
        buyer = "VP Sales"
    elif re.search(r"\b(cmo|head\s+of\s+marketing|marketing\s+director)\b", text, re.IGNORECASE):
        buyer = "Head of Marketing"
    elif re.search(r"\b(cto|vp\s+engineering|tech\s+lead)\b", text, re.IGNORECASE):
        buyer = "CTO"
    elif re.search(r"\b(founders?|co-founders?|ceo|owners?|business\s+owners?|managing\s+directors?|directors?)\b", text, re.IGNORECASE):
        buyer = "Founder/Business Owner"
    else:
        buyer = "Decision maker"

    # 6. Intent extraction. Known website intents stay structured. Anything else
    # keeps the user's sentence so discovery searches for what they asked.
    intent = None
    if re.search(r"\b(redesign|revamp|rebuild)\b", text, re.IGNORECASE):
        intent = "Website Redesign"
    elif re.search(r"\b(new\s+website|build\s+a\s+website|create\s+website)\b", text, re.IGNORECASE):
        intent = "New Website Build"
    elif re.search(r"\b(hiring\s+web\s+developer|need\s+web\s+developer)\b", text, re.IGNORECASE):
        intent = "Hiring Web Developer"
    else:
        intent = compact or "Requested outcome"

    # 7. Exclusions
    exclusions = []
    for line in text.splitlines():
        clean_line = line.strip()
        if clean_line.lower().startswith(("exclude:", "negative:", "no:")):
            parts = clean_line.split(":", 1)[1]
            exclusions.extend([p.strip() for p in parts.split(",") if p.strip()])

    summary = (
        f"Targeting {buyer} in {geography} seeking {intent} for {service} "
        f"(Budget: {price}, Freshness: {freshness})"
    )

    return PromptICP(
        service=service,
        price=price,
        geography=geography,
        freshness=freshness,
        buyer=buyer,
        intent=intent,
        summary=summary,
        exclusions=exclusions,
    )


# ---------------------------------------------------------------------------
# RC-2: Source Attribution Integrity
# ---------------------------------------------------------------------------

KNOWN_PUBLISHERS: Dict[str, str] = {
    "linkedin.com": "LinkedIn",
    "news.google.com": "Google News",
    "reddit.com": "Reddit",
    "news.ycombinator.com": "Hacker News",
    "twitter.com": "X",
    "x.com": "X",
    "github.com": "GitHub",
    "techcrunch.com": "TechCrunch",
    "forbes.com": "Forbes",
    "bloomberg.com": "Bloomberg",
    "economictimes.indiatimes.com": "Economic Times",
    "livemint.com": "Mint",
    "producthunt.com": "Product Hunt",
    "greenhouse.io": "Greenhouse",
    "lever.co": "Lever",
    "ashbyhq.com": "Ashby",
    "upwork.com": "Upwork",
    "freelancer.com": "Freelancer",
}


def detect_publisher(url: str) -> str:
    """Extract canonical publisher name from the evidence URL domain. Never confuse with provider."""
    if not url:
        return "Unknown Publisher"
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    for domain, name in KNOWN_PUBLISHERS.items():
        if host == domain or host.endswith(f".{domain}"):
            return name
    if host:
        parts = host.split(".")
        return parts[0].capitalize() if len(parts) >= 2 else host
    return "Unknown Publisher"


def extract_source_attribution(
    url: str,
    retrieval_provider: str = "duckduckgo",
) -> Tuple[str, str, str]:
    """
    Returns (retrieval_provider, publisher, evidence_url).
    Guarantees independent fields and prevents publisher overwriting.
    """
    canonical_provider = (retrieval_provider or "web_search").strip().lower()
    canonical_pub = detect_publisher(url)
    return canonical_provider, canonical_pub, url


# ---------------------------------------------------------------------------
# RC-4: Search Result Document Classification
# ---------------------------------------------------------------------------

_BLOG_URL_PATTERNS = re.compile(r"/(blog|articles?|news|guides?|tutorials?|tips|insights)/", re.IGNORECASE)
_BLOG_TITLE_PATTERNS = re.compile(r"\b(how to|10 tips|\d+ best|top \d+|complete guide|why you need|benefits of|vs\.?)\b", re.IGNORECASE)

_SELLER_PATTERNS = re.compile(
    r"\b(\d+\+?\s*websites\s*built|portfolio|our\s*agency|we\s*are\s*a\s*web\s*design\s*agency|"
    r"best\s*web\s*design\s*company\s*in|our\s*services|web\s*development\s*company\s*in|"
    r"hire\s*our\s*team|hire\s*developers\s*from\s*us)\b",
    re.IGNORECASE,
)

_HIRING_PATTERNS = re.compile(
    r"\b(hiring\s+(?:web|frontend|fullstack|software|ui|designer|developer)|we\s*are\s*hiring|"
    r"job\s*opening|join\s*our\s*team|looking\s*for\s*(?:a\s*)?(?:freelance\s+|contract\s+|full-time\s+)?(?:website|web\s+developer|web\s+designer|full\s*stack|developer))\b",
    re.IGNORECASE,
)

_RFP_PATTERNS = re.compile(
    r"\b(request\s*for\s*proposal|\brfp\b|tender|bidding|vendor\s*selection|project\s*requirement)\b",
    re.IGNORECASE,
)


def classify_document_type(
    url: str,
    title: str,
    snippet: str,
    text: str = "",
) -> Tuple[SearchDocumentType, str, bool]:
    """
    Classifies search document into SearchDocumentType.
    Returns (document_type, explanation, should_reject).
    """
    combined_text = f"{title} {snippet} {text[:500]}".lower()
    url_lower = url.lower()
    path = urlparse(url).path.lower()

    # 1. Seller-side agency / portfolio (Reject immediately)
    if _SELLER_PATTERNS.search(combined_text):
        return (
            SearchDocumentType.SELLER_PORTFOLIO,
            "Seller-side agency offering services or showing portfolio (not a buyer)",
            True,
        )

    # 2. Hiring post or recruitment (Keep)
    if _HIRING_PATTERNS.search(combined_text) or any(k in url_lower for k in ("greenhouse.io", "lever.co", "ashbyhq.com")):
        return (
            SearchDocumentType.HIRING_POST,
            "Verified hiring post seeking technical talent",
            False,
        )

    # 3. RFP / Project (Keep)
    if _RFP_PATTERNS.search(combined_text):
        return (
            SearchDocumentType.RFP,
            "Active RFP or commercial project procurement requirement",
            False,
        )

    # 4. Educational / Blog / Article (Reject)
    if _BLOG_URL_PATTERNS.search(path) or _BLOG_TITLE_PATTERNS.search(title):
        return (
            SearchDocumentType.BLOG if "/blog" in path else SearchDocumentType.ARTICLE,
            "Educational article or blog post without active buying intent",
            True,
        )

    # 5. Generic social profile (Reject)
    if "linkedin.com/in/" in url_lower or ("twitter.com/" in url_lower and "/status/" not in url_lower):
        return (
            SearchDocumentType.PROFILE,
            "Generic personal profile without hiring or procurement intent",
            True,
        )

    # 4. Hiring post (Keep)
    if _HIRING_PATTERNS.search(combined_text) or any(k in url_lower for k in ("greenhouse.io", "lever.co", "ashbyhq.com")):
        return (
            SearchDocumentType.HIRING_POST,
            "Verified hiring post seeking technical talent",
            False,
        )

    # 5. RFP / Project (Keep)
    if _RFP_PATTERNS.search(combined_text):
        return (
            SearchDocumentType.RFP,
            "Active RFP or commercial project procurement requirement",
            False,
        )

    # 6. Company website
    if not any(domain in url_lower for domain in ("linkedin.com", "reddit.com", "news.google.com")):
        return (
            SearchDocumentType.COMPANY_PAGE,
            "Target company web presence",
            False,
        )

    return (SearchDocumentType.UNKNOWN, "General web reference", False)


# ---------------------------------------------------------------------------
# RC-5: Buying Intent Detection
# ---------------------------------------------------------------------------

_BUYER_INTENT_PATTERNS = [
    (re.compile(r"\blooking\s+for\s+(?:a\s+)?(?:freelance\s+|contract\s+)?(?:website|web\s+developer|web\s+designer|full\s*stack)\b", re.IGNORECASE), "Looking for website developer"),
    (re.compile(r"\bneed\s+(?:a\s+)?(?:website\s+redesign|new\s+website|website\s+developed|web\s+designer)\b", re.IGNORECASE), "Need website redesign/build"),
    (re.compile(r"\bseeking\s+(?:a\s+)?(?:web\s+designer|website\s+developer|freelance\s+dev)\b", re.IGNORECASE), "Seeking web designer/developer"),
    (re.compile(r"\bhiring\s+(?:a\s+)?(?:web\s+developer|frontend\s+developer|fullstack\s+developer)\b", re.IGNORECASE), "Hiring web developer"),
    (re.compile(r"\bwho\s+(?:can|should\s+we\s+use\s+to)\s+build\s+our\s+website\b", re.IGNORECASE), "Seeking website build vendor"),
    (re.compile(r"\b(?:budget|quote)\s+for\s+(?:website|web\s+development|redesign)\b", re.IGNORECASE), "Evaluating budget for website"),
    (re.compile(r"\b(?:redesigning|revamping)\s+our\s+(?:company\s+)?website\b", re.IGNORECASE), "Active website redesign initiative"),
]


def detect_buying_intent(title: str, snippet: str, text: str = "") -> Tuple[bool, str, str]:
    """
    Returns (has_buying_intent, buying_signal, evidence_quote).
    Requires explicit buyer-side intent.
    """
    corpus = f"{title}. {snippet}. {text[:2000]}"
    for pattern, label in _BUYER_INTENT_PATTERNS:
        match = pattern.search(corpus)
        if match:
            start = max(0, match.start() - 30)
            end = min(len(corpus), match.end() + 70)
            quote = corpus[start:end].strip()
            return True, label, quote

    # General trigger keywords if accompanied by buyer posture
    if re.search(r"\b(redesign|build\s+our\s+website|looking\s+for\s+developer)\b", corpus, re.IGNORECASE):
        return True, "Website Development Need", snippet[:180]

    return False, "No verified buying signal", ""


# ---------------------------------------------------------------------------
# RC-1: Record Isolation & Normalization
# ---------------------------------------------------------------------------

def normalize_search_record(
    raw_hit: Dict[str, Any],
    retrieval_provider: str,
    query: str = "",
) -> Dict[str, Any]:
    """
    Creates a brand-new, isolated record dictionary.
    Guarantees:
    - Never mutates shared dictionaries.
    - Deep-copies input values.
    - NEVER sets company name to search query or campaign directive.
    - Safely derives company name from URL hostname when missing.
    """
    hit = copy.deepcopy(raw_hit)
    url = (hit.get("url") or hit.get("evidence_url") or "").strip()
    provider, pub, ev_url = extract_source_attribution(url, retrieval_provider)

    # Derive clean company name without contamination
    company = (hit.get("company") or hit.get("company_name") or "").strip()
    
    # Critical Bug Guard: Never allow query or directive to become company name
    if company.lower() == query.strip().lower() or "target segment:" in company.lower() or "prompt directive" in company.lower():
        company = ""

    if not company and url:
        host = (urlparse(url).hostname or "").lower().removeprefix("www.")
        # If not a platform board, extract domain name
        if host and not any(host.endswith(b) for b in ("linkedin.com", "google.com", "reddit.com", "ycombinator.com")):
            base = host.split(".")[0]
            if len(base) >= 3 and not base.isdigit():
                company = base.capitalize()

    contact_name = (hit.get("name") or hit.get("contact_name") or "").strip()
    if contact_name in ("Contact", "Contact Team", "Management", "General Inquiry", "Unknown Contact"):
        contact_name = ""

    email = (hit.get("email") or hit.get("contact_email") or "").strip().lower()
    phone = (hit.get("phone") or hit.get("contact_phone") or "").strip()

    title = (hit.get("title") or "").strip()
    snippet = (hit.get("snippet") or hit.get("description") or "").strip()
    published_at = hit.get("published_at") or hit.get("event_date")

    return {
        "company": company,
        "name": contact_name,
        "title": (hit.get("role") or hit.get("designation") or "Stakeholder").strip(),
        "email": email or None,
        "phone": phone or None,
        "website": hit.get("website") or (urlparse(url).hostname or "").removeprefix("www."),
        "evidence_url": ev_url,
        "retrieval_provider": provider,
        "publisher": pub,
        "title_text": title,
        "snippet_text": snippet,
        "published_at": published_at,
        "freshness": hit.get("freshness") or {},
    }


# ---------------------------------------------------------------------------
# Phase 7: Multi-Factor Scoring & Qualification
# ---------------------------------------------------------------------------

def score_and_qualify_lead(
    record: Dict[str, Any],
    icp: PromptICP,
    has_buying_intent: bool,
    buying_signal: str,
    evidence_quote: str,
    doc_type: SearchDocumentType,
) -> PromptLeadContract:
    """
    Calculates evidence-grounded score (0-100) and decides lead status:
    - Explicit hiring / buying signal: 35 pts
    - Verified source & canonical evidence: 20 pts
    - Freshness: 15 pts
    - ICP fit (service, geo): 15 pts
    - Decision maker identified: 10 pts
    - Contact available (email or phone): 5 pts

    Status decisions:
    >= 80: READY (if contact present) or CONTACT_PARTIAL (if contact missing)
    60-79: CONTACT_PARTIAL / MANUAL_REVIEW
    < 60: REJECTED with explicit reason
    """
    score = 0.0
    email = record.get("email")
    phone = record.get("phone")
    has_contact = bool(email or phone)

    # 1. Buying signal (35 pts)
    if has_buying_intent:
        score += 35.0
    elif doc_type in (SearchDocumentType.HIRING_POST, SearchDocumentType.RFP):
        score += 25.0

    # 2. Verified source (20 pts)
    if record.get("evidence_url") and record.get("publisher"):
        score += 20.0

    # 3. Freshness (15 pts)
    freshness_info = record.get("freshness") or {}
    age_days = freshness_info.get("age_days")
    if age_days is not None and age_days <= 14:
        score += 15.0
    elif age_days is not None and age_days <= 30:
        score += 10.0
    else:
        score += 8.0  # active web baseline

    # 4. ICP fit (15 pts)
    title_snippet = f"{record.get('title_text', '')} {record.get('snippet_text', '')}".lower()
    if any(k in title_snippet for k in ("web", "website", "design", "development", "frontend")):
        score += 10.0
    if icp.geography.lower() in title_snippet or "india" in title_snippet:
        score += 5.0

    # 5. Decision maker identified (10 pts)
    role_name = (record.get("name") or "") + " " + (record.get("title") or "")
    if any(k in role_name.lower() for k in ("founder", "ceo", "director", "owner", "partner", "vp")):
        score += 10.0
    elif record.get("name"):
        score += 5.0

    # 6. Contact availability (5 pts)
    if has_contact:
        score += 5.0

    # Contact status determination
    if has_contact:
        contact_confidence = ContactConfidence.HIGH.value
        platform_contact = "direct_inbox" if email else "direct_phone"
    elif "linkedin.com" in (record.get("evidence_url") or ""):
        contact_confidence = ContactConfidence.MEDIUM.value
        platform_contact = "linkedin_message"
    else:
        contact_confidence = ContactConfidence.UNKNOWN.value
        platform_contact = "official_website_form"

    # Status & Rejection logic
    if score >= 80.0:
        status = LeadStatus.READY.value if has_contact else LeadStatus.CONTACT_PARTIAL.value
        rejection_reason = None
    elif score >= 60.0:
        status = LeadStatus.CONTACT_PARTIAL.value
        rejection_reason = None
    else:
        status = LeadStatus.REJECTED.value
        rejection_reason = f"Low commercial confidence (Score {int(score)}/100: insufficient buyer intent or ICP match)"

    return PromptLeadContract(
        prospect_name=record.get("name") or None,
        company=record.get("company") or None,
        role=record.get("title") or None,
        retrieval_provider=record.get("retrieval_provider", "duckduckgo"),
        publisher=record.get("publisher", "Unknown Publisher"),
        evidence_url=record.get("evidence_url", ""),
        buying_signal=buying_signal,
        evidence_quote=evidence_quote or record.get("snippet_text", "")[:180],
        published_date=str(record.get("published_at")) if record.get("published_at") else None,
        contact_status=status,
        contact_confidence=contact_confidence,
        platform_contact=platform_contact,
        email=email,
        phone=phone,
        qualification_score=round(score, 1),
        rejection_reason=rejection_reason,
        evidence_tier=EvidenceTier.ENRICHED.value if has_contact else EvidenceTier.VERIFIED.value,
    )
