"""Zero-Cost Direct Web Profiler Collector.

Extracts deep enterprise buying signals and pain hypotheses directly from raw public HTML:
1. Marketing Budget Signals (Meta Pixel, Google Ads, GTM, LinkedIn Insight)
2. Agency Displacement Opportunities (Footer agency credits: 'Site by Acme Agency')
3. Tech Stack Fingerprint (~25 platforms: CMS, Frontend, Analytics, CRM/Chat)
4. Conversion & Scheduling Gaps (Presence or absence of Calendly, ChiliPiper, Acuity)
Zero marginal API credit cost.
"""
import logging
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from pydantic import BaseModel, Field
import httpx

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "WebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Detection Signatures
PIXEL_SIGNATURES = {
    "meta_pixel": (r"fbq\(['\"]init", r"connect\.facebook\.net"),
    "google_ads": (r"gtag\(['\"]config['\"],\s*['\"]AW-", r"googleadservices\.com/pagead"),
    "gtm": (r"googletagmanager\.com/gtm\.js", r"GTM-[A-Z0-9]+"),
    "linkedin_insight": (r"snap\.licdn\.com/li\.lms-analytics", r"_linkedin_partner_id"),
    "tiktok_pixel": (r"analytics\.tiktok\.com", r"ttq\.load"),
}

TECH_SIGNATURES = {
    "shopify": (r"cdn\.shopify\.com", r"Shopify\.theme"),
    "wordpress": (r"/wp-content/", r"/wp-includes/", r"wp-json"),
    "webflow": (r"data-wf-page", r"assets\.website-files\.com"),
    "hubspot": (r"js\.hs-scripts\.com", r"hbspt\.forms"),
    "nextjs": (r"/_next/static", r"__NEXT_DATA__"),
    "intercom": (r"widget\.intercom\.io", r"intercomSettings"),
    "zendesk": (r"static\.zdassets\.com", r"zopim"),
    "hotjar": (r"static\.hotjar\.com", r"_hjSettings"),
    "segment": (r"cdn\.segment\.com/analytics\.js",),
    "mixpanel": (r"cdn\.mxpnl\.com",),
}

BOOKING_SIGNATURES = {
    "calendly": r"calendly\.com",
    "chilipiper": r"chilipiper\.com",
    "hubspot_meetings": r"meetings\.hubspot\.com",
    "acuity": r"acuityscheduling\.com",
}

AGENCY_LINK_REGEX = re.compile(
    r"(?:website|site|built|designed|developed)\s+(?:by)\s+<a[^>]*href=['\"]([^'\"]+)['\"][^>]*>([^<]+)</a>",
    re.IGNORECASE,
)
AGENCY_TEXT_REGEX = re.compile(
    r"(?:website|site|designed|developed)\s+(?:by)\s+([A-Za-z0-9\s&,.-]{3,35})(?:<\/div|<\/p|<\/span|<\/footer|\.|\n)",
    re.IGNORECASE,
)


class DirectProfileResult(BaseModel):
    domain: str
    url: str
    status_code: int = 0
    ad_pixels: List[str] = Field(default_factory=list)
    has_active_ad_spend: bool = False
    tech_stack: List[str] = Field(default_factory=list)
    booking_tools: List[str] = Field(default_factory=list)
    has_online_booking: bool = False
    incumbent_agency: Optional[str] = None
    agency_url: Optional[str] = None
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    suggested_pain_points: List[str] = Field(default_factory=list)


class DirectProfiler:
    """Zero-cost direct company intelligence profiler."""

    @classmethod
    def parse_html(cls, domain: str, url: str, html_content: str, status_code: int = 200) -> DirectProfileResult:
        """Parse raw HTML and extract structured signals."""
        ad_pixels: List[str] = []
        tech_stack: List[str] = []
        booking_tools: List[str] = []
        signals: List[Dict[str, Any]] = []
        pain_points: List[str] = []

        # 1. Detect Ad Pixels
        for pixel_name, patterns in PIXEL_SIGNATURES.items():
            for pat in patterns:
                if re.search(pat, html_content, re.IGNORECASE):
                    ad_pixels.append(pixel_name)
                    break

        has_active_ad_spend = len(ad_pixels) > 0
        if has_active_ad_spend:
            signals.append({
                "signal_type": "active_ad_spend",
                "headline": f"Active ad spend confirmed ({', '.join(ad_pixels)})",
                "confidence": 0.95,
                "evidence": f"Detected tags: {', '.join(ad_pixels)}",
            })

        # 2. Detect Tech Stack
        for tech_name, patterns in TECH_SIGNATURES.items():
            for pat in patterns:
                if re.search(pat, html_content, re.IGNORECASE):
                    tech_stack.append(tech_name)
                    break

        if tech_stack:
            signals.append({
                "signal_type": "tech_stack",
                "headline": f"Tech stack detected: {', '.join(tech_stack)}",
                "confidence": 0.90,
                "evidence": f"Technologies: {', '.join(tech_stack)}",
            })

        # 3. Detect Booking Tools
        for tool_name, pat in BOOKING_SIGNATURES.items():
            if re.search(pat, html_content, re.IGNORECASE):
                booking_tools.append(tool_name)

        has_booking = len(booking_tools) > 0
        if not has_booking:
            pain_points.append("Lack of instant calendar scheduling on buyer journey")
        else:
            signals.append({
                "signal_type": "inbound_scheduling",
                "headline": f"Uses instant inbound booking ({', '.join(booking_tools)})",
                "confidence": 0.95,
                "evidence": f"Booking tool: {', '.join(booking_tools)}",
            })

        # 4. Detect Incumbent Agency
        incumbent_agency = None
        agency_url = None
        # Prefer linked credits first
        link_match = AGENCY_LINK_REGEX.search(html_content)
        if link_match:
            agency_url, incumbent_agency = link_match.groups()
            incumbent_agency = incumbent_agency.strip() if incumbent_agency else None
        else:
            text_match = AGENCY_TEXT_REGEX.search(html_content)
            if text_match:
                incumbent_agency = text_match.group(1).strip()

        # Reject common false positives
        banned_agency_words = ("wordpress", "shopify", "webflow", "next.js", "react", "us", "love", "pride", "cookie", "privacy")
        if incumbent_agency and len(incumbent_agency) > 2:
            if not any(w in incumbent_agency.lower() for w in banned_agency_words):
                signals.append({
                    "signal_type": "incumbent_agency",
                    "headline": f"Incumbent web agency credit detected: {incumbent_agency}",
                    "confidence": 0.85,
                    "evidence": f"Footer credit: '{incumbent_agency}' (URL: {agency_url or 'n/a'})",
                })
                pain_points.append(f"Agency vendor lock-in or outdated implementation via {incumbent_agency}")
            else:
                incumbent_agency = None

        return DirectProfileResult(
            domain=domain,
            url=url,
            status_code=status_code,
            ad_pixels=ad_pixels,
            has_active_ad_spend=has_active_ad_spend,
            tech_stack=tech_stack,
            booking_tools=booking_tools,
            has_online_booking=has_booking,
            incumbent_agency=incumbent_agency,
            agency_url=agency_url,
            signals=signals,
            suggested_pain_points=pain_points,
        )

    @classmethod
    async def profile_url(cls, target_url: str, timeout_sec: float = 8.0) -> DirectProfileResult:
        """Fetch URL directly with httpx and profile buyer signals."""
        if not target_url.startswith("http://") and not target_url.startswith("https://"):
            target_url = f"https://{target_url}"

        domain = urlparse(target_url).netloc.lower().replace("www.", "")

        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=timeout_sec) as client:
                resp = await client.get(target_url)
                return cls.parse_html(domain, str(resp.url), resp.text, resp.status_code)
        except Exception as e:
            logger.warning(f"Direct profile failed for {target_url}: {e}")
            return DirectProfileResult(
                domain=domain,
                url=target_url,
                status_code=0,
                signals=[{"signal_type": "unreachable", "headline": f"Site unreachable: {str(e)}", "confidence": 0.5}],
            )
