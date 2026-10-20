"""
OctaOS Sales Intelligence - Unified Source Registry
Defines the complete catalogue of 60+ sourcing channels organized across:
- Tier S: First-Party / Warm Intelligence
- Tier A: Active Buying-Intent Sources (Hiring, Funding, Registry, Technographics, Reviews, Social, Leadership, Procurement, Events)
- Tier B: Waterfall Contact Discovery & Enrichment
- Tier C: Directory & Vertical Fallbacks
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel


class SourceTier(str, Enum):
    TIER_S = "tier_s"                       # First-party / warm intelligence
    TIER_A_HIRING = "tier_a_hiring"         # Job postings, headcount growth
    TIER_A_FUNDING = "tier_a_funding"       # Capital raises, M&A, SEC filings
    TIER_A_REGISTRY = "tier_a_registry"     # Corporate registrar, trademarks
    TIER_A_TECH = "tier_a_technographics"   # Software stack changes, DNS/SSL
    TIER_A_REVIEWS = "tier_a_reviews"       # Review complaints & competitor dissatisfaction
    TIER_A_SOCIAL = "tier_a_social"         # Community intent & problem awareness
    TIER_A_LEADERSHIP = "tier_a_leadership" # Exec moves, new VPs/CXOs
    TIER_A_NEWS = "tier_a_news"             # Press releases & market expansion
    TIER_A_PROCUREMENT = "tier_a_rfp"       # Public & enterprise tenders/RFPs
    TIER_A_EVENTS = "tier_a_events"         # Conference sponsors & exhibitors
    TIER_B_ENRICHMENT = "tier_b_enrichment" # Contact waterfall enrichment
    TIER_C_DIRECTORY = "tier_c_directory"   # General & vertical directory fallbacks


class SourceCapability(str, Enum):
    ACCOUNT_DISCOVERY = "account_discovery"
    CONTACT_DISCOVERY = "contact_discovery"
    INTENT_SIGNAL = "intent_signal"
    ENRICHMENT = "enrichment"
    VERIFICATION = "verification"
    FIRST_PARTY = "first_party"


class SourceDefinition(BaseModel):
    id: str
    name: str
    tier: SourceTier
    category: str
    description: str
    capabilities: List[SourceCapability]
    hint: str = "API Key / Auth"
    url: str = ""
    default_confidence: float = 0.85
    half_life_days: int = 30
    is_external_api: bool = True
    requires_key: bool = True


# Complete catalogue of 60+ unified sources
SOURCE_CATALOGUE: Dict[str, SourceDefinition] = {
    # -------------------------------------------------------------
    # BASELINE ORIGINAL 13 SOURCES
    # -------------------------------------------------------------
    "apollo": SourceDefinition(
        id="apollo",
        name="Apollo.io",
        tier=SourceTier.TIER_B_ENRICHMENT,
        category="Contact Discovery & Waterfall",
        description="B2B person/email discovery and account firmographic enrichment.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.CONTACT_DISCOVERY, SourceCapability.ENRICHMENT],
        hint="API Key",
        url="https://app.apollo.io/#/settings/integrations/api",
        default_confidence=0.90,
        half_life_days=60
    ),
    "hunter": SourceDefinition(
        id="hunter",
        name="Hunter.io",
        tier=SourceTier.TIER_B_ENRICHMENT,
        category="Domain & Email Discovery",
        description="Domain search, email pattern discovery, and deliverability verification.",
        capabilities=[SourceCapability.CONTACT_DISCOVERY, SourceCapability.VERIFICATION],
        hint="API Key",
        url="https://hunter.io/api-keys",
        default_confidence=0.88,
        half_life_days=45
    ),
    "google_places": SourceDefinition(
        id="google_places",
        name="Google Places API",
        tier=SourceTier.TIER_C_DIRECTORY,
        category="Local Business Discovery",
        description="Brick-and-mortar and localized commercial entity discovery via Google Maps.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY],
        hint="GCP API Key",
        url="https://console.cloud.google.com/",
        default_confidence=0.85,
        half_life_days=90
    ),
    "apify": SourceDefinition(
        id="apify",
        name="Apify Web Automation & Lead Discovery",
        tier=SourceTier.TIER_C_DIRECTORY,
        category="Public Web Data Collection",
        description="Public business discovery, market research, and web signals via approved Apify Actors.",
        capabilities=[
            SourceCapability.ACCOUNT_DISCOVERY,
            SourceCapability.CONTACT_DISCOVERY,
            SourceCapability.INTENT_SIGNAL,
            SourceCapability.ENRICHMENT,
        ],
        hint="Apify API Token",
        url="https://console.apify.com/",
        default_confidence=0.85,
        half_life_days=60
    ),
    "apify_google_places": SourceDefinition(
        id="apify_google_places",
        name="Apify Google Places Scraper",
        tier=SourceTier.TIER_C_DIRECTORY,
        category="Local Business Scraping",
        description="Deep place crawler with website, phone, and owner extraction.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.ENRICHMENT],
        hint="Apify API Token",
        url="https://console.apify.com/",
        default_confidence=0.85,
        half_life_days=60
    ),
    "apify_instagram": SourceDefinition(
        id="apify_instagram",
        name="Apify Instagram Scraper",
        tier=SourceTier.TIER_A_SOCIAL,
        category="D2C & Social Discovery",
        description="Ecommerce, creator brands, and D2C storefront discovery.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Apify API Token",
        url="https://console.apify.com/",
        default_confidence=0.75,
        half_life_days=14
    ),
    "apify_linkedin": SourceDefinition(
        id="apify_linkedin",
        name="Apify LinkedIn Profile Scraper",
        tier=SourceTier.TIER_B_ENRICHMENT,
        category="Executive Discovery",
        description="Headcount, executive appointments, and decision-maker profile discovery.",
        capabilities=[SourceCapability.CONTACT_DISCOVERY, SourceCapability.ENRICHMENT],
        hint="Apify API Token",
        url="https://console.apify.com/",
        default_confidence=0.90,
        half_life_days=30
    ),
    "apify_crawler": SourceDefinition(
        id="apify_crawler",
        name="Apify Website Crawler",
        tier=SourceTier.TIER_A_TECH,
        category="Web Scraping & Tech Detection",
        description="Deep crawl for contact pages, pricing plans, and technological stack signals.",
        capabilities=[SourceCapability.ENRICHMENT, SourceCapability.INTENT_SIGNAL],
        hint="Apify API Token",
        url="https://console.apify.com/",
        default_confidence=0.85,
        half_life_days=30
    ),
    "zoominfo": SourceDefinition(
        id="zoominfo",
        name="ZoomInfo",
        tier=SourceTier.TIER_B_ENRICHMENT,
        category="Enterprise Contact Intelligence",
        description="Enterprise verified phone numbers, direct emails, and organizational charts.",
        capabilities=[SourceCapability.CONTACT_DISCOVERY, SourceCapability.ENRICHMENT, SourceCapability.VERIFICATION],
        hint="API Key",
        url="https://www.zoominfo.com/",
        default_confidence=0.94,
        half_life_days=60
    ),
    "cognism": SourceDefinition(
        id="cognism",
        name="Cognism",
        tier=SourceTier.TIER_B_ENRICHMENT,
        category="International Contact Enrichment",
        description="GDPR-compliant European and APAC mobile phone and email intelligence.",
        capabilities=[SourceCapability.CONTACT_DISCOVERY, SourceCapability.ENRICHMENT],
        hint="API Key",
        url="https://www.cognism.com/",
        default_confidence=0.92,
        half_life_days=60
    ),
    "people_data_labs": SourceDefinition(
        id="people_data_labs",
        name="People Data Labs",
        tier=SourceTier.TIER_B_ENRICHMENT,
        category="Person & Career Graph",
        description="Career history, skills taxonomy, and resume profile enrichment.",
        capabilities=[SourceCapability.CONTACT_DISCOVERY, SourceCapability.ENRICHMENT],
        hint="API Key",
        url="https://www.peopledatalabs.com/",
        default_confidence=0.88,
        half_life_days=45
    ),
    "clearbit": SourceDefinition(
        id="clearbit",
        name="Clearbit",
        tier=SourceTier.TIER_B_ENRICHMENT,
        category="Firmographic Intelligence",
        description="Company revenue range, employee bands, industry categorization, and tech tags.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.ENRICHMENT],
        hint="API Key",
        url="https://clearbit.com/",
        default_confidence=0.90,
        half_life_days=60
    ),
    "crunchbase": SourceDefinition(
        id="crunchbase",
        name="Crunchbase",
        tier=SourceTier.TIER_A_FUNDING,
        category="Funding & Venture Intelligence",
        description="Series A-D rounds, venture funding dates, investor networks, and acquisitions.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="API Key",
        url="https://data.crunchbase.com/",
        default_confidence=0.95,
        half_life_days=45
    ),
    "csv_json_bulk": SourceDefinition(
        id="csv_json_bulk",
        name="CSV / JSON Bulk Ingestion",
        tier=SourceTier.TIER_S,
        category="First-Party & Bulk Upload",
        description="First-party uploaded accounts, outbound target lists, and historical CRM dumps.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.FIRST_PARTY],
        hint="File Upload",
        url="",
        default_confidence=1.0,
        half_life_days=180,
        requires_key=False
    ),
    "direct_api": SourceDefinition(
        id="direct_api",
        name="Direct Inbound Webhook / API",
        tier=SourceTier.TIER_S,
        category="First-Party Inbound",
        description="Real-time website visitor forms, product signups, and demo request webhooks.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL, SourceCapability.FIRST_PARTY],
        hint="Webhook Secret",
        url="",
        default_confidence=1.0,
        half_life_days=30,
        requires_key=False
    ),

    # -------------------------------------------------------------
    # TIER A: HIRING INTELLIGENCE (A1 - A12)
    # -------------------------------------------------------------
    "greenhouse": SourceDefinition(
        id="greenhouse",
        name="Greenhouse Job Board Feeds",
        tier=SourceTier.TIER_A_HIRING,
        category="Hiring Intelligence",
        description="Job openings, hiring surges in SDR/RevOps/Engineering, technology requirements.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Board Token / Harvest API",
        url="https://www.greenhouse.io/",
        default_confidence=0.96,
        half_life_days=21
    ),
    "lever": SourceDefinition(
        id="lever",
        name="Lever Postings Feed",
        tier=SourceTier.TIER_A_HIRING,
        category="Hiring Intelligence",
        description="Real-time ATS openings and department expansion indicators.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Site Name / API Key",
        url="https://www.lever.co/",
        default_confidence=0.95,
        half_life_days=21
    ),
    "ashby": SourceDefinition(
        id="ashby",
        name="Ashby Job Board Scanner",
        tier=SourceTier.TIER_A_HIRING,
        category="Hiring Intelligence",
        description="High-growth tech startup hiring signals and compensation benchmarks.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="API Key / Feed URL",
        url="https://www.ashbyhq.com/",
        default_confidence=0.95,
        half_life_days=21
    ),
    "workable": SourceDefinition(
        id="workable",
        name="Workable API",
        tier=SourceTier.TIER_A_HIRING,
        category="Hiring Intelligence",
        description="Mid-market and international job requisitions.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="API Key",
        url="https://www.workable.com/",
        default_confidence=0.92,
        half_life_days=21
    ),
    "indeed": SourceDefinition(
        id="indeed",
        name="Indeed Job Feed",
        tier=SourceTier.TIER_A_HIRING,
        category="Hiring Intelligence",
        description="Volume hiring alerts and geographical workforce expansions.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Publisher ID / API Key",
        url="https://www.indeed.com/",
        default_confidence=0.88,
        half_life_days=14
    ),
    "linkedin_jobs": SourceDefinition(
        id="linkedin_jobs",
        name="LinkedIn Jobs Monitor",
        tier=SourceTier.TIER_A_HIRING,
        category="Hiring Intelligence",
        description="Executive and specialized enterprise role listings.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="API / Scraper Token",
        url="https://www.linkedin.com/",
        default_confidence=0.92,
        half_life_days=14
    ),
    "naukri": SourceDefinition(
        id="naukri",
        name="Naukri Enterprise Jobs",
        tier=SourceTier.TIER_A_HIRING,
        category="Hiring Intelligence",
        description="Indian enterprise & tech hiring signals across key metros.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Recruiter API Key",
        url="https://www.naukri.com/",
        default_confidence=0.88,
        half_life_days=21
    ),
    "foundit": SourceDefinition(
        id="foundit",
        name="Foundit (Monster India)",
        tier=SourceTier.TIER_A_HIRING,
        category="Hiring Intelligence",
        description="Regional India & Southeast Asia corporate hiring demand.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="API Key",
        url="https://www.foundit.in/",
        default_confidence=0.84,
        half_life_days=21
    ),
    "wellfound": SourceDefinition(
        id="wellfound",
        name="Wellfound (AngelList)",
        tier=SourceTier.TIER_A_HIRING,
        category="Hiring Intelligence",
        description="Seed to Series B startup hiring velocity and equity compensation.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="API Key / Token",
        url="https://wellfound.com/",
        default_confidence=0.90,
        half_life_days=21
    ),
    "hn_hiring": SourceDefinition(
        id="hn_hiring",
        name="Hacker News Who Is Hiring",
        tier=SourceTier.TIER_A_HIRING,
        category="Hiring Intelligence",
        description="Monthly monthly hiring threads from YC founders and technical leadership.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Public Algolia API",
        url="https://news.ycombinator.com/",
        default_confidence=0.92,
        half_life_days=28,
        requires_key=False
    ),
    "career_pages": SourceDefinition(
        id="career_pages",
        name="Company Career Pages Headless Monitor",
        tier=SourceTier.TIER_A_HIRING,
        category="Hiring Intelligence",
        description="Automated sitemap and DOM change detection on target company careers pages.",
        capabilities=[SourceCapability.INTENT_SIGNAL],
        hint="Firecrawl / Headless Crawler",
        url="",
        default_confidence=0.94,
        half_life_days=14,
        requires_key=False
    ),

    # -------------------------------------------------------------
    # TIER A: FUNDING & FINANCIAL INTELLIGENCE (A13 - A30)
    # -------------------------------------------------------------
    "dealroom": SourceDefinition(
        id="dealroom",
        name="Dealroom.co",
        tier=SourceTier.TIER_A_FUNDING,
        category="Funding Intelligence",
        description="European tech ecosystem venture rounds, growth metrics, and valuations.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="API Key",
        url="https://dealroom.co/",
        default_confidence=0.92,
        half_life_days=45
    ),
    "tracxn": SourceDefinition(
        id="tracxn",
        name="Tracxn Startup Data",
        tier=SourceTier.TIER_A_FUNDING,
        category="Funding Intelligence",
        description="Global private market intelligence with deep coverage of emerging markets.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="API Token",
        url="https://tracxn.com/",
        default_confidence=0.92,
        half_life_days=45
    ),
    "pitchbook": SourceDefinition(
        id="pitchbook",
        name="PitchBook",
        tier=SourceTier.TIER_A_FUNDING,
        category="Funding Intelligence",
        description="Private capital, institutional PE/VC funding, M&A and capitalization tables.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL, SourceCapability.ENRICHMENT],
        hint="Enterprise API Key",
        url="https://pitchbook.com/",
        default_confidence=0.98,
        half_life_days=60
    ),
    "sec_edgar": SourceDefinition(
        id="sec_edgar",
        name="SEC EDGAR & Form D Filings",
        tier=SourceTier.TIER_A_FUNDING,
        category="Regulatory Financials",
        description="Official US private placement Form D and public 8-K / 10-Q corporate disclosures.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="User-Agent Header",
        url="https://www.sec.gov/edgar",
        default_confidence=0.99,
        half_life_days=60,
        requires_key=False
    ),
    "techcrunch": SourceDefinition(
        id="techcrunch",
        name="TechCrunch Funding News",
        tier=SourceTier.TIER_A_FUNDING,
        category="Funding Intelligence",
        description="Venture financing announcements, seed rounds, and stealth launches.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="RSS / Scraper",
        url="https://techcrunch.com/",
        default_confidence=0.88,
        half_life_days=30,
        requires_key=False
    ),
    "entrackr": SourceDefinition(
        id="entrackr",
        name="Entrackr Venture Tracker",
        tier=SourceTier.TIER_A_FUNDING,
        category="Funding Intelligence",
        description="Indian startup cap table changes, regulatory filings, and funding rounds.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="RSS / Feed",
        url="https://entrackr.com/",
        default_confidence=0.90,
        half_life_days=30,
        requires_key=False
    ),
    "inc42": SourceDefinition(
        id="inc42",
        name="Inc42 Intelligence",
        tier=SourceTier.TIER_A_FUNDING,
        category="Funding Intelligence",
        description="Indian tech funding reports, startup acquisitions, and leadership additions.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="API / Feed",
        url="https://inc42.com/",
        default_confidence=0.90,
        half_life_days=30,
        requires_key=False
    ),
    "yourstory": SourceDefinition(
        id="yourstory",
        name="YourStory Startup Database",
        tier=SourceTier.TIER_A_FUNDING,
        category="Funding Intelligence",
        description="D2C and technology startup founding stories and funding announcements.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Feed / API",
        url="https://yourstory.com/",
        default_confidence=0.86,
        half_life_days=30,
        requires_key=False
    ),
    "startup_india": SourceDefinition(
        id="startup_india",
        name="Startup India Hub",
        tier=SourceTier.TIER_A_FUNDING,
        category="Government Registries",
        description="DPIIT recognized startups, state seed grants, and government incubations.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Portal API / Crawler",
        url="https://www.startupindia.gov.in/",
        default_confidence=0.95,
        half_life_days=60,
        requires_key=False
    ),
    "y_combinator": SourceDefinition(
        id="y_combinator",
        name="Y Combinator Directory & Launches",
        tier=SourceTier.TIER_A_FUNDING,
        category="Funding Intelligence",
        description="Current and alumni YC batch companies, Launch YC announcements, and founders.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Algolia Public Feed",
        url="https://www.ycombinator.com/companies",
        default_confidence=0.96,
        half_life_days=60,
        requires_key=False
    ),
    "product_hunt": SourceDefinition(
        id="product_hunt",
        name="Product Hunt API",
        tier=SourceTier.TIER_A_FUNDING,
        category="Product Launches",
        description="Daily software launches, upvote velocity, and founder introductions.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Developer Token",
        url="https://api.producthunt.com/v2/docs",
        default_confidence=0.88,
        half_life_days=14
    ),
    "pr_newswire": SourceDefinition(
        id="pr_newswire",
        name="PR Newswire & Business Wire",
        tier=SourceTier.TIER_A_FUNDING,
        category="Corporate Announcements",
        description="Commercial partnership releases, executive promotions, and regional expansions.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Newsfeed API Key",
        url="https://www.prnewswire.com/",
        default_confidence=0.92,
        half_life_days=30
    ),

    # -------------------------------------------------------------
    # TIER A: COMPANY FORMATION & REGISTRY (A31 - A41)
    # -------------------------------------------------------------
    "mca_roc": SourceDefinition(
        id="mca_roc",
        name="MCA / ROC India Company Registry",
        tier=SourceTier.TIER_A_REGISTRY,
        category="Company Registries",
        description="Newly incorporated private limited entities, director changes, authorized capital.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="MCA API / Data Service",
        url="https://www.mca.gov.in/",
        default_confidence=0.99,
        half_life_days=90
    ),
    "companies_house": SourceDefinition(
        id="companies_house",
        name="Companies House UK",
        tier=SourceTier.TIER_A_REGISTRY,
        category="Company Registries",
        description="UK official registry of incorporated companies, PSC registers, and annual returns.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="API Key",
        url="https://developer.company-information.service.gov.uk/",
        default_confidence=0.99,
        half_life_days=90
    ),
    "opencorporates": SourceDefinition(
        id="opencorporates",
        name="OpenCorporates Global Registry",
        tier=SourceTier.TIER_A_REGISTRY,
        category="Company Registries",
        description="Multi-jurisdiction cross-border corporate structure and subsidiary discovery.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.ENRICHMENT],
        hint="API Token",
        url="https://opencorporates.com/",
        default_confidence=0.98,
        half_life_days=90
    ),
    "trademark_patent": SourceDefinition(
        id="trademark_patent",
        name="USPTO & India IP Registry",
        tier=SourceTier.TIER_A_REGISTRY,
        category="Intellectual Property",
        description="New trademark registrations indicating new product launches and brand expansions.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Patent/TM Public API",
        url="https://www.uspto.gov/",
        default_confidence=0.97,
        half_life_days=90,
        requires_key=False
    ),

    # -------------------------------------------------------------
    # TIER A: TECHNOGRAPHIC INTELLIGENCE (A42 - A59)
    # -------------------------------------------------------------
    "builtwith": SourceDefinition(
        id="builtwith",
        name="BuiltWith Technographics",
        tier=SourceTier.TIER_A_TECH,
        category="Technographic Intelligence",
        description="Web technology installs, tracking pixels, payment processors, and hosting.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.ENRICHMENT, SourceCapability.INTENT_SIGNAL],
        hint="API Key",
        url="https://builtwith.com/",
        default_confidence=0.92,
        half_life_days=45
    ),
    "wappalyzer": SourceDefinition(
        id="wappalyzer",
        name="Wappalyzer API",
        tier=SourceTier.TIER_A_TECH,
        category="Technographic Intelligence",
        description="Instant software stack profiling: CRM, CMS, analytics, frontend frameworks.",
        capabilities=[SourceCapability.ENRICHMENT, SourceCapability.INTENT_SIGNAL],
        hint="API Key",
        url="https://www.wappalyzer.com/api/",
        default_confidence=0.90,
        half_life_days=45
    ),
    "storeleads": SourceDefinition(
        id="storeleads",
        name="StoreLeads Ecommerce Data",
        tier=SourceTier.TIER_A_TECH,
        category="Technographic Intelligence",
        description="Shopify, WooCommerce, and Magento merchant intelligence with GMV estimates.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.ENRICHMENT, SourceCapability.INTENT_SIGNAL],
        hint="API Token",
        url="https://storeleads.app/",
        default_confidence=0.94,
        half_life_days=30
    ),
    "hg_insights": SourceDefinition(
        id="hg_insights",
        name="HG Insights Enterprise Tech",
        tier=SourceTier.TIER_A_TECH,
        category="Technographic Intelligence",
        description="Enterprise IT install base, contract renewal dates, and cloud spend models.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.ENRICHMENT, SourceCapability.INTENT_SIGNAL],
        hint="Enterprise Key",
        url="https://hginsights.com/",
        default_confidence=0.96,
        half_life_days=60
    ),
    "dns_mx_inspect": SourceDefinition(
        id="dns_mx_inspect",
        name="DNS & MX Inspector",
        tier=SourceTier.TIER_A_TECH,
        category="Infrastructure Signals",
        description="Detects Google Workspace, Microsoft 365, Zendesk, SendGrid, and security gateways.",
        capabilities=[SourceCapability.ENRICHMENT, SourceCapability.INTENT_SIGNAL],
        hint="Native DNS Resolver",
        url="",
        default_confidence=0.98,
        half_life_days=60,
        requires_key=False
    ),
    "ssl_transparency": SourceDefinition(
        id="ssl_transparency",
        name="SSL Certificate Transparency Logs",
        tier=SourceTier.TIER_A_TECH,
        category="Infrastructure Signals",
        description="Monitors crt.sh logs to identify new subdomains indicating internal staging or products.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="crt.sh Public Query",
        url="https://crt.sh/",
        default_confidence=0.95,
        half_life_days=21,
        requires_key=False
    ),
    "github_ecosystem": SourceDefinition(
        id="github_ecosystem",
        name="GitHub / Open Source Activity",
        tier=SourceTier.TIER_A_TECH,
        category="Developer Intelligence",
        description="Detects organizational repos adopting specific SDKs, frameworks, or dependencies.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="GitHub Personal Access Token",
        url="https://github.com/",
        default_confidence=0.90,
        half_life_days=30
    ),

    # -------------------------------------------------------------
    # TIER A: REVIEW & DISSATISFACTION SIGNALS (A75 - A83)
    # -------------------------------------------------------------
    "g2": SourceDefinition(
        id="g2",
        name="G2 Buyer Intent & Reviews",
        tier=SourceTier.TIER_A_REVIEWS,
        category="Buyer Intent & Review Signals",
        description="In-market buyer accounts reading comparison grids and competitor review complaints.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="G2 Buyer Intent API Key",
        url="https://data.g2.com/",
        default_confidence=0.93,
        half_life_days=14
    ),
    "capterra": SourceDefinition(
        id="capterra",
        name="Capterra Review Monitor",
        tier=SourceTier.TIER_A_REVIEWS,
        category="Buyer Intent & Review Signals",
        description="Gartner Digital Markets review sentiment and competitor churn signals.",
        capabilities=[SourceCapability.INTENT_SIGNAL],
        hint="API / Scraper Key",
        url="https://www.capterra.com/",
        default_confidence=0.88,
        half_life_days=21
    ),
    "trustpilot": SourceDefinition(
        id="trustpilot",
        name="Trustpilot Reviews",
        tier=SourceTier.TIER_A_REVIEWS,
        category="Buyer Intent & Review Signals",
        description="Customer service breakdowns and software dissatisfaction signals.",
        capabilities=[SourceCapability.INTENT_SIGNAL],
        hint="Consumer API Key",
        url="https://business.trustpilot.com/",
        default_confidence=0.86,
        half_life_days=21
    ),
    "google_reviews": SourceDefinition(
        id="google_reviews",
        name="Google Business Reviews Monitor",
        tier=SourceTier.TIER_A_REVIEWS,
        category="Buyer Intent & Review Signals",
        description="Local store and agency customer sentiment and operational bottlenecks.",
        capabilities=[SourceCapability.INTENT_SIGNAL],
        hint="GCP Places API",
        url="https://cloud.google.com/maps-platform/places",
        default_confidence=0.85,
        half_life_days=30
    ),
    "app_store_reviews": SourceDefinition(
        id="app_store_reviews",
        name="Apple & Google App Store Reviews",
        tier=SourceTier.TIER_A_REVIEWS,
        category="Buyer Intent & Review Signals",
        description="Negative mobile app reviews indicating tech infrastructure or payment issues.",
        capabilities=[SourceCapability.INTENT_SIGNAL],
        hint="Public RSS Feeds",
        url="",
        default_confidence=0.82,
        half_life_days=14,
        requires_key=False
    ),

    # -------------------------------------------------------------
    # TIER A: SOCIAL & COMMUNITY INTENT (A84 - A94)
    # -------------------------------------------------------------
    "reddit_intent": SourceDefinition(
        id="reddit_intent",
        name="Reddit Buying Intent Monitor",
        tier=SourceTier.TIER_A_SOCIAL,
        category="Community Intent",
        description="Subreddit threads (r/sales, r/saas, r/sysadmin) asking for tool recommendations.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Reddit OAuth Credentials",
        url="https://www.reddit.com/dev/api/",
        default_confidence=0.80,
        half_life_days=7
    ),
    "twitter_intent": SourceDefinition(
        id="twitter_intent",
        name="X / Twitter B2B Intent Scanner",
        tier=SourceTier.TIER_A_SOCIAL,
        category="Community Intent",
        description="Mentions of competitor outages, vendor evaluations, and purchasing advice.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="X API Bearer Token",
        url="https://developer.x.com/",
        default_confidence=0.75,
        half_life_days=7
    ),
    "hn_intent": SourceDefinition(
        id="hn_intent",
        name="Hacker News Ask HN & Comments",
        tier=SourceTier.TIER_A_SOCIAL,
        category="Community Intent",
        description="'Ask HN: What do you use for X?' purchasing discussions.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Algolia Search API",
        url="https://hn.algolia.com/api",
        default_confidence=0.82,
        half_life_days=7,
        requires_key=False
    ),
    "quora_intent": SourceDefinition(
        id="quora_intent",
        name="Quora B2B Topic Research",
        tier=SourceTier.TIER_A_SOCIAL,
        category="Community Intent",
        description="Enterprise procurement and alternative-seeking questions.",
        capabilities=[SourceCapability.INTENT_SIGNAL],
        hint="Crawler / Scraper",
        url="",
        default_confidence=0.70,
        half_life_days=14,
        requires_key=False
    ),

    # -------------------------------------------------------------
    # TIER A: LEADERSHIP & ORG CHANGE (A95 - A105)
    # -------------------------------------------------------------
    "executive_moves": SourceDefinition(
        id="executive_moves",
        name="Executive Appointments & Job Changes",
        tier=SourceTier.TIER_A_LEADERSHIP,
        category="Leadership Changes",
        description="New CRO, CMO, VP Sales, or CTO appointments triggering first-90-days purchasing windows.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Press Feeds / Scraper",
        url="",
        default_confidence=0.95,
        half_life_days=30,
        requires_key=False
    ),

    # -------------------------------------------------------------
    # TIER A: PROCUREMENT & RFP INTELLIGENCE (A117 - A130)
    # -------------------------------------------------------------
    "gem_portal": SourceDefinition(
        id="gem_portal",
        name="GeM (Government e-Marketplace India)",
        tier=SourceTier.TIER_A_PROCUREMENT,
        category="Tenders & Procurement",
        description="Public sector and Indian government tenders, bid notices, and contract awards.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="GeM Portal Scraper",
        url="https://gem.gov.in/",
        default_confidence=0.99,
        half_life_days=10,
        requires_key=False
    ),
    "cppp_portal": SourceDefinition(
        id="cppp_portal",
        name="CPPP Central Public Procurement",
        tier=SourceTier.TIER_A_PROCUREMENT,
        category="Tenders & Procurement",
        description="India central government RFPs, high-value enterprise tenders, and PSU procurements.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="CPPP RSS / Parser",
        url="https://eprocure.gov.in/",
        default_confidence=0.99,
        half_life_days=10,
        requires_key=False
    ),
    "sam_gov": SourceDefinition(
        id="sam_gov",
        name="SAM.gov US Federal Contracting",
        tier=SourceTier.TIER_A_PROCUREMENT,
        category="Tenders & Procurement",
        description="United States federal contract opportunities, solicitations, and awards.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="SAM.gov API Key",
        url="https://sam.gov/",
        default_confidence=0.99,
        half_life_days=14
    ),
    "ted_procurement": SourceDefinition(
        id="ted_procurement",
        name="TED (Tenders Electronic Daily EU)",
        tier=SourceTier.TIER_A_PROCUREMENT,
        category="Tenders & Procurement",
        description="European Union public procurement notices, public tenders, and contract notices.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="TED Open Data API",
        url="https://ted.europa.eu/",
        default_confidence=0.99,
        half_life_days=14,
        requires_key=False
    ),
    "un_worldbank_tenders": SourceDefinition(
        id="un_worldbank_tenders",
        name="UN & World Bank Procurement",
        tier=SourceTier.TIER_A_PROCUREMENT,
        category="Tenders & Procurement",
        description="Global development agency RFPs, consulting contracts, and digital transformation bids.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Development Feeds",
        url="https://www.ungm.org/",
        default_confidence=0.98,
        half_life_days=14,
        requires_key=False
    ),

    # -------------------------------------------------------------
    # TIER A: EVENT & TRADE SHOW SOURCES (A131 - A139)
    # -------------------------------------------------------------
    "event_exhibitors": SourceDefinition(
        id="event_exhibitors",
        name="Conference Exhibitors & Sponsors",
        tier=SourceTier.TIER_A_EVENTS,
        category="Event Intelligence",
        description="Exhibitor lists and sponsor directories from SaaStr, Web Summit, Luma, Eventbrite.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL],
        hint="Event Scraper / URL",
        url="",
        default_confidence=0.90,
        half_life_days=30,
        requires_key=False
    ),

    # -------------------------------------------------------------
    # TIER B: ADDITIONAL WATERFALL ENRICHMENT PROVIDERS
    # -------------------------------------------------------------
    "lusha": SourceDefinition(
        id="lusha",
        name="Lusha Enterprise",
        tier=SourceTier.TIER_B_ENRICHMENT,
        category="Waterfall Contact Enrichment",
        description="B2B direct dial telephone numbers and executive contact coordinates.",
        capabilities=[SourceCapability.CONTACT_DISCOVERY, SourceCapability.ENRICHMENT],
        hint="API Key",
        url="https://www.lusha.com/",
        default_confidence=0.92,
        half_life_days=45
    ),
    "rocketreach": SourceDefinition(
        id="rocketreach",
        name="RocketReach",
        tier=SourceTier.TIER_B_ENRICHMENT,
        category="Waterfall Contact Enrichment",
        description="Deep person lookup across LinkedIn, professional associations, and emails.",
        capabilities=[SourceCapability.CONTACT_DISCOVERY, SourceCapability.ENRICHMENT],
        hint="API Key",
        url="https://rocketreach.co/",
        default_confidence=0.88,
        half_life_days=45
    ),
    "snov": SourceDefinition(
        id="snov",
        name="Snov.io",
        tier=SourceTier.TIER_B_ENRICHMENT,
        category="Waterfall Contact Enrichment",
        description="Domain email search and real-time SMTP inbox pinging.",
        capabilities=[SourceCapability.CONTACT_DISCOVERY, SourceCapability.VERIFICATION],
        hint="API User ID & Secret",
        url="https://snov.io/",
        default_confidence=0.85,
        half_life_days=30
    ),
    "prospeo": SourceDefinition(
        id="prospeo",
        name="Prospeo Email Finder",
        tier=SourceTier.TIER_B_ENRICHMENT,
        category="Waterfall Contact Enrichment",
        description="High-accuracy verified work email discovery with catch-all resolution.",
        capabilities=[SourceCapability.CONTACT_DISCOVERY, SourceCapability.VERIFICATION],
        hint="API Key",
        url="https://prospeo.io/",
        default_confidence=0.92,
        half_life_days=30
    ),
    "findymail": SourceDefinition(
        id="findymail",
        name="Findymail",
        tier=SourceTier.TIER_B_ENRICHMENT,
        category="Waterfall Contact Enrichment",
        description="Proprietary email scraping algorithm guaranteeing ultra-low bounce rates.",
        capabilities=[SourceCapability.CONTACT_DISCOVERY, SourceCapability.VERIFICATION],
        hint="API Key",
        url="https://findymail.com/",
        default_confidence=0.94,
        half_life_days=30
    ),
    "dropcontact": SourceDefinition(
        id="dropcontact",
        name="Dropcontact",
        tier=SourceTier.TIER_B_ENRICHMENT,
        category="Waterfall Contact Enrichment",
        description="GDPR-compliant algorithmic email generation and CRM deduplication.",
        capabilities=[SourceCapability.CONTACT_DISCOVERY, SourceCapability.ENRICHMENT],
        hint="API Key",
        url="https://www.dropcontact.com/",
        default_confidence=0.90,
        half_life_days=45
    ),
    "fullenrich": SourceDefinition(
        id="fullenrich",
        name="FullEnrich Waterfall",
        tier=SourceTier.TIER_B_ENRICHMENT,
        category="Waterfall Contact Enrichment",
        description="Multi-vendor automated waterfall aggregator querying 15+ vendors sequentially.",
        capabilities=[SourceCapability.CONTACT_DISCOVERY, SourceCapability.ENRICHMENT, SourceCapability.VERIFICATION],
        hint="API Key",
        url="https://www.fullenrich.com/",
        default_confidence=0.96,
        half_life_days=45
    ),

    # -------------------------------------------------------------
    # TIER C: FALLBACK DIRECTORY & VERTICAL SOURCES
    # -------------------------------------------------------------
    "indiamart": SourceDefinition(
        id="indiamart",
        name="IndiaMART B2B Directory",
        tier=SourceTier.TIER_C_DIRECTORY,
        category="Vertical & Regional Directories",
        description="Indian manufacturing, industrial, wholesale, and export suppliers.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY],
        hint="CRM Key / Scraper",
        url="https://www.indiamart.com/",
        default_confidence=0.82,
        half_life_days=60
    ),
    "tradeindia": SourceDefinition(
        id="tradeindia",
        name="TradeIndia Marketplace",
        tier=SourceTier.TIER_C_DIRECTORY,
        category="Vertical & Regional Directories",
        description="B2B buyers, distributors, and SME service providers in India.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY],
        hint="API Key / Scraper",
        url="https://www.tradeindia.com/",
        default_confidence=0.80,
        half_life_days=60
    ),
    "justdial": SourceDefinition(
        id="justdial",
        name="JustDial Local Search",
        tier=SourceTier.TIER_C_DIRECTORY,
        category="Vertical & Regional Directories",
        description="Hyperlocal service providers, retail merchants, and contractors.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY],
        hint="Scraper / Token",
        url="https://www.justdial.com/",
        default_confidence=0.75,
        half_life_days=60
    ),
    "clutch": SourceDefinition(
        id="clutch",
        name="Clutch.co Agency Directory",
        tier=SourceTier.TIER_C_DIRECTORY,
        category="Vertical & Regional Directories",
        description="Verified software development, marketing, and design agency ratings.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.ENRICHMENT],
        hint="API Key / Scraper",
        url="https://clutch.co/",
        default_confidence=0.90,
        half_life_days=60
    ),
    "goodfirms": SourceDefinition(
        id="goodfirms",
        name="GoodFirms B2B Directory",
        tier=SourceTier.TIER_C_DIRECTORY,
        category="Vertical & Regional Directories",
        description="IT services, mobile app developers, and SaaS product reviews.",
        capabilities=[SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.ENRICHMENT],
        hint="API Key / Scraper",
        url="https://www.goodfirms.co/",
        default_confidence=0.88,
        half_life_days=60
    ),
}


def get_all_sources() -> Dict[str, SourceDefinition]:
    return SOURCE_CATALOGUE


def get_source(source_id: str) -> Optional[SourceDefinition]:
    return SOURCE_CATALOGUE.get(source_id)


def get_sources_by_tier(tier: SourceTier) -> List[SourceDefinition]:
    return [s for s in SOURCE_CATALOGUE.values() if s.tier == tier]


def get_sources_by_capability(cap: SourceCapability) -> List[SourceDefinition]:
    return [s for s in SOURCE_CATALOGUE.values() if cap in s.capabilities]


def get_all_source_ids() -> List[str]:
    return list(SOURCE_CATALOGUE.keys())


# Every blueprint id resolves to one catalogue key. Duplicate provider names share a key.
BLUEPRINT_CANONICAL = {
    "C01": "apollo",
    "C02": "hunter",
    "C03": "clay",
    "C04": "crunchbase",
    "C05": "zoominfo",
    "C06": "google_places",
    "C07": "yelp",
    "C08": "builtwith",
    "C09": "storeleads",
    "C10": "indeed",
    "C11": "linkedin",
    "C12": "instagram",
    "C13": "direct_api",
    "N01": "greenhouse",
    "N02": "lever",
    "N03": "ashby",
    "N04": "workable",
    "N05": "wellfound",
    "N06": "hn_hiring",
    "N07": "techcrunch",
    "N08": "sec_edgar",
    "N09": "sam_gov",
    "N10": "gem_portal",
    "N11": "cppp_portal",
    "N12": "g2",
    "N13": "capterra",
    "N14": "trustpilot",
    "N15": "reddit_intent",
    "N16": "google_search_news",
    "N17": "google_business_profile",
    "N18": "wappalyzer",
    "N19": "dns_mx_inspect",
    "N20": "securitytrails",
    "N21": "builtwith",
    "N22": "wappalyzer",
    "N23": "clearbit",
    "N24": "rb2b",
    "N25": "people_data_labs",
    "N26": "cognism",
    "N27": "lusha",
    "N28": "rocketreach",
    "N29": "peoplefinders",
    "N30": "zerobounce",
    "N31": "bouncer",
    "N32": "neverbounce",
    "N33": "kickbox",
    "N34": "emailrep",
    "N35": "hunter_verifier",
    "N36": "github_ecosystem",
    "N37": "product_hunt",
    "N38": "hn_intent",
    "N39": "kaggle",
    "N40": "foursquare",
    "N41": "openstreetmap",
    "N42": "yelp",
    "N43": "tripadvisor",
    "N44": "glassdoor",
    "N45": "comparably",
    "N46": "the_org",
    "N47": "owler",
    "N48": "similarweb",
    "N49": "semrush",
    "N50": "ahrefs",
    "N51": "majestic",
    "N52": "serpapi",
    "N53": "google_ads_leads",
    "N54": "meta_lead_ads",
    "N55": "typeform",
    "N56": "tally",
    "N57": "hubspot",
    "N58": "salesforce",
    "N59": "pipedrive",
    "N60": "intercom",
    "N61": "zendesk",
    "N62": "gmail",
    "N63": "microsoft_graph",
    "N64": "google_calendar",
    "N65": "calendly",
    "N66": "stripe",
}


def _gap(source_id: str, name: str, tier: SourceTier, category: str, capabilities: List[SourceCapability], requires_key: bool = True) -> None:
    if source_id in SOURCE_CATALOGUE:
        return
    SOURCE_CATALOGUE[source_id] = SourceDefinition(
        id=source_id,
        name=name,
        tier=tier,
        category=category,
        description=f"{name} is registered. It stays inactive until an authorized adapter and credentials exist.",
        capabilities=capabilities,
        requires_key=requires_key,
        default_confidence=0.5,
        half_life_days=30,
    )


_gap("clay", "Clay", SourceTier.TIER_B_ENRICHMENT, "Enrichment orchestration", [SourceCapability.ENRICHMENT])
_gap("yelp", "Yelp Fusion", SourceTier.TIER_A_REVIEWS, "Local reviews", [SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.INTENT_SIGNAL])
_gap("linkedin", "LinkedIn official", SourceTier.TIER_A_HIRING, "Professional graph", [SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.CONTACT_DISCOVERY])
_gap("instagram", "Instagram / Meta Graph", SourceTier.TIER_A_SOCIAL, "Business profile", [SourceCapability.ACCOUNT_DISCOVERY])
_gap("google_search_news", "Google Search / News", SourceTier.TIER_A_NEWS, "Web and news", [SourceCapability.INTENT_SIGNAL])
_gap("google_business_profile", "Google Business Profile", SourceTier.TIER_A_REVIEWS, "Local profile", [SourceCapability.INTENT_SIGNAL])
_gap("securitytrails", "SecurityTrails", SourceTier.TIER_A_TECH, "DNS infrastructure", [SourceCapability.INTENT_SIGNAL])
_gap("rb2b", "RB2B", SourceTier.TIER_S, "Inbound visitor", [SourceCapability.ACCOUNT_DISCOVERY, SourceCapability.FIRST_PARTY])
_gap("peoplefinders", "Identity vendor review", SourceTier.TIER_B_ENRICHMENT, "Identity enrichment", [SourceCapability.ENRICHMENT])
_gap("zerobounce", "ZeroBounce", SourceTier.TIER_B_ENRICHMENT, "Email verification", [SourceCapability.VERIFICATION])
_gap("bouncer", "Bouncer", SourceTier.TIER_B_ENRICHMENT, "Email verification", [SourceCapability.VERIFICATION])
_gap("neverbounce", "NeverBounce", SourceTier.TIER_B_ENRICHMENT, "Email verification", [SourceCapability.VERIFICATION])
_gap("kickbox", "Kickbox", SourceTier.TIER_B_ENRICHMENT, "Email verification", [SourceCapability.VERIFICATION])
_gap("emailrep", "EmailRep", SourceTier.TIER_B_ENRICHMENT, "Email risk", [SourceCapability.VERIFICATION])
_gap("hunter_verifier", "Hunter Verifier", SourceTier.TIER_B_ENRICHMENT, "Email verification", [SourceCapability.VERIFICATION])
_gap("kaggle", "Kaggle", SourceTier.TIER_A_TECH, "Technical activity", [SourceCapability.INTENT_SIGNAL], False)
_gap("foursquare", "Foursquare Places", SourceTier.TIER_C_DIRECTORY, "Local business", [SourceCapability.ACCOUNT_DISCOVERY])
_gap("openstreetmap", "OpenStreetMap / Overpass", SourceTier.TIER_C_DIRECTORY, "Local business", [SourceCapability.ACCOUNT_DISCOVERY], False)
_gap("tripadvisor", "Tripadvisor", SourceTier.TIER_A_REVIEWS, "Hospitality reviews", [SourceCapability.INTENT_SIGNAL])
_gap("glassdoor", "Glassdoor", SourceTier.TIER_A_REVIEWS, "Employer reputation", [SourceCapability.INTENT_SIGNAL])
_gap("comparably", "Comparably", SourceTier.TIER_A_REVIEWS, "Workplace sentiment", [SourceCapability.INTENT_SIGNAL])
_gap("the_org", "The Org", SourceTier.TIER_A_LEADERSHIP, "Org structure", [SourceCapability.ENRICHMENT])
_gap("owler", "Owler", SourceTier.TIER_A_NEWS, "Company news", [SourceCapability.INTENT_SIGNAL])
_gap("similarweb", "Similarweb", SourceTier.TIER_A_NEWS, "Traffic", [SourceCapability.INTENT_SIGNAL])
_gap("semrush", "Semrush", SourceTier.TIER_A_NEWS, "Search demand", [SourceCapability.INTENT_SIGNAL])
_gap("ahrefs", "Ahrefs", SourceTier.TIER_A_NEWS, "Organic visibility", [SourceCapability.INTENT_SIGNAL])
_gap("majestic", "Majestic", SourceTier.TIER_A_TECH, "Backlinks", [SourceCapability.INTENT_SIGNAL])
_gap("serpapi", "SerpAPI", SourceTier.TIER_A_NEWS, "Search results", [SourceCapability.INTENT_SIGNAL])
_gap("google_ads_leads", "Google Ads Lead Forms", SourceTier.TIER_S, "Paid inbound", [SourceCapability.FIRST_PARTY, SourceCapability.ACCOUNT_DISCOVERY])
_gap("meta_lead_ads", "Meta Lead Ads", SourceTier.TIER_S, "Paid inbound", [SourceCapability.FIRST_PARTY, SourceCapability.ACCOUNT_DISCOVERY])
_gap("typeform", "Typeform", SourceTier.TIER_S, "First-party forms", [SourceCapability.FIRST_PARTY])
_gap("tally", "Tally", SourceTier.TIER_S, "First-party forms", [SourceCapability.FIRST_PARTY])
_gap("hubspot", "HubSpot", SourceTier.TIER_S, "CRM", [SourceCapability.FIRST_PARTY, SourceCapability.ACCOUNT_DISCOVERY])
_gap("salesforce", "Salesforce", SourceTier.TIER_S, "CRM", [SourceCapability.FIRST_PARTY, SourceCapability.ACCOUNT_DISCOVERY])
_gap("pipedrive", "Pipedrive", SourceTier.TIER_S, "CRM", [SourceCapability.FIRST_PARTY])
_gap("intercom", "Intercom", SourceTier.TIER_S, "Product intent", [SourceCapability.INTENT_SIGNAL, SourceCapability.FIRST_PARTY])
_gap("zendesk", "Zendesk", SourceTier.TIER_S, "Support intent", [SourceCapability.INTENT_SIGNAL, SourceCapability.FIRST_PARTY])
_gap("gmail", "Gmail", SourceTier.TIER_S, "Mailbox", [SourceCapability.FIRST_PARTY])
_gap("microsoft_graph", "Microsoft Graph / Outlook", SourceTier.TIER_S, "Mailbox", [SourceCapability.FIRST_PARTY])
_gap("google_calendar", "Google Calendar", SourceTier.TIER_S, "Meetings", [SourceCapability.FIRST_PARTY])
_gap("calendly", "Calendly", SourceTier.TIER_S, "Meetings", [SourceCapability.FIRST_PARTY])
_gap("stripe", "Stripe", SourceTier.TIER_S, "Revenue outcome", [SourceCapability.FIRST_PARTY])
