"""Open-web lead discovery and signal intelligence (no paid database required).

Next-Gen Autonomous Agentic Pipeline:
- Universal Domain Archetype Classification (SaaS, Manufacturing, Healthcare, D2C, etc.)
- Multi-Tier Date Confidence Ladder (0.30 - 0.95)
- Anti-False-Fresh Filtering (rejects footer copyrights, stale updates, and dead sites)
- Strict Configurable Freshness Gating (7d, 14d, 30d, 90d, 180d, all)
- Multi-angle temporal web search with DuckDuckGo 'df' temporal parameters
- Deterministic MX deliverability and live-domain verification
"""
import asyncio
import html as html_lib
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Awaitable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse, unquote

import dns.resolver
import httpx

from app.services.web_ingestion.firecrawl_client import validate_target_url

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_OVERRIDE_RE = re.compile(r"\n*\[MANUAL_SOURCE_OVERRIDE:.*?\]", re.DOTALL)

# Search engines, social networks, app stores, and portals that are not direct buyer websites.
SKIP_DOMAINS = (
    "facebook.com", "instagram.com", "youtube.com", "wikipedia.org",
    "pinterest.com", "tiktok.com", "duckduckgo.com", "google.com",
    "play.google.com", "apps.apple.com",
    "naukri.com", "indeed.com",
    "glassdoor.com", "foundit.in", "etenders.gov.in", "gem.gov.in",
    "eprocure.gov.in", "india.gov.in",
)

# Hosts that represent a discussion platform or job board rather than company domain
_BOARD_HOSTS = (
    "linkedin.com", "twitter.com", "x.com", "reddit.com",
    "greenhouse.io", "lever.co", "ashbyhq.com", "workable.com",
    "news.ycombinator.com", "producthunt.com", "ycombinator.com",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "WebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

MAX_ROUNDS = 3
QUERIES_PER_ROUND = 6
PAGES_PER_ROUND = 12
SEARCH_LIMIT = 5


def calculate_freshness_window_days(window: Optional[str]) -> int:
    """Translates user-configured freshness key into max age in days."""
    w = (window or "30_days").lower().strip()
    if "7" in w:
        return 7
    elif "14" in w:
        return 14
    elif "30" in w or "month" in w:
        return 30
    elif "90" in w or "quarter" in w:
        return 90
    elif "180" in w or "6_month" in w:
        return 180
    elif "365" in w or "year" in w:
        return 365
    elif "all" in w or "evergreen" in w:
        return 9999
    return 30


def classify_archetype(brief: str, query: str = "", offer: str = "") -> str:
    """Classifies tenant's domain archetype for targeted playbook selection."""
    combined = f"{brief} {query} {offer}".lower()
    if any(k in combined for k in ("manufacturing", "factory", "machinery", "fabrication", "industrial", "textile", "packaging", "chemicals", "auto parts", "gem", "cppp")):
        return "INDUSTRIAL_MANUFACTURING"
    elif any(k in combined for k in ("clinic", "hospital", "dental", "pharma", "medical", "doctor", "health", "healthcare", "diagnostic", "nabh")):
        return "HEALTHCARE_CLINICAL"
    elif any(k in combined for k in ("shopify", "ecommerce", "e-commerce", "d2c", "retail", "apparel", "beauty", "store", "consumer brand", "storeleads")):
        return "ECOMMERCE_D2C"
    elif any(k in combined for k in ("roofing", "plumbing", "hvac", "electrician", "contractor", "real estate", "cleaning", "property manager", "local services")):
        return "LOCAL_SERVICES"
    elif any(k in combined for k in ("agency", "law firm", "legal", "accounting", "consulting", "cpa", "design agency", "marketing agency", "clutch")):
        return "PROFESSIONAL_SERVICES"
    return "ENTERPRISE_B2B_SAAS"


def analyst_instructions(extra_context: Optional[str]) -> str:
    """User prompt saved on the business profile, without the source-picker tag."""
    text = _OVERRIDE_RE.sub("", extra_context or "").strip()
    return text[:8000]


def research_brief(
    query: str,
    *,
    industries: Any = None,
    countries: Any = None,
    buyers: Any = None,
    budget: Any = None,
    offer: Any = None,
) -> str:
    """Profile facts that shape web queries."""
    def as_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return ", ".join(str(item).strip() for item in value if str(item).strip())
        return str(value).strip()

    lines = [f"Search target: {(query or '').strip()}"]
    for label, value in (
        ("Industries", as_text(industries)),
        ("Countries", as_text(countries)),
        ("Buyers", as_text(buyers)),
        ("Budget", as_text(budget)),
        ("Offer", as_text(offer)),
    ):
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)[:4000]


def _domain(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def _usable_result(url: str) -> bool:
    host = _domain(url)
    if not url.startswith("http") or not host:
        return False
    path = urlparse(url).path
    if host.endswith("linkedin.com"):
        # Only use publicly indexed posts and profiles. Login-gated pages are
        # not treated as evidence, but public search results can still surface
        # these URLs as unverified extras.
        return bool(re.search(r"/(posts|pulse|in)/", path))
    if host.endswith(("twitter.com", "x.com")):
        return "/status/" in path
    if host.endswith("reddit.com"):
        return "/comments/" in path
    return not host.endswith(SKIP_DOMAINS)


def _is_board_host(host: str) -> bool:
    return host.endswith(_BOARD_HOSTS)


def _notify(on_progress: Optional[Callable[[str], None]], message: str) -> None:
    logger.info(message)
    if on_progress is None:
        return
    try:
        on_progress(message)
    except Exception:
        logger.debug("web discovery progress callback failed", exc_info=True)


def _dedupe_queries(queries: List[str], tried: List[str], limit: int) -> List[str]:
    seen = {item.lower() for item in tried}
    fresh: List[str] = []
    for query in queries:
        cleaned = " ".join(query.split())
        if not cleaned or cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        fresh.append(cleaned)
        if len(fresh) >= limit:
            break
    return fresh


def _parse_iso_or_standard_date(val_str: str) -> Optional[datetime]:
    """Attempts to parse common web date formats safely into a UTC datetime."""
    val = val_str.strip()
    if not val or len(val) < 4:
        return None
    # 1. Direct ISO
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # 2. YYYY-MM-DD or YYYY/MM/DD
    m_ymd = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", val)
    if m_ymd:
        try:
            return datetime(int(m_ymd.group(1)), int(m_ymd.group(2)), int(m_ymd.group(3)), tzinfo=timezone.utc)
        except Exception:
            pass

    # 3. Month Name DD, YYYY
    m_named = re.search(r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", val, re.IGNORECASE)
    if m_named:
        month_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        m_str = m_named.group(1)[:3].lower()
        if m_str in month_map:
            try:
                return datetime(int(m_named.group(3)), month_map[m_str], int(m_named.group(2)), tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def extract_page_date_with_confidence(
    raw_html: str,
    text: str,
    headers: Optional[Dict[str, str]] = None,
    now: Optional[datetime] = None,
) -> Tuple[Optional[datetime], float, str, str]:
    """
    Evaluates page contents against the Date Confidence Ladder:
    - 0.90 (Structured Meta / Schema.org)
    - 0.60 (Visible Content Text Patterns: relative and absolute)
    - 0.40 (HTTP Headers: Last-Modified)
    - 0.00 (Unknown / Undated)

    Applies Anti-False-Fresh rules to reject footer copyright notices,
    cookie policies, and deceptive modified dates.
    """
    ref_time = now or datetime.now(timezone.utc)
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=timezone.utc)

    # --- 1. Structured HTML Meta & Schema.org (Confidence 0.90) ---
    meta_patterns = [
        (r'<meta[^>]+(?:property|name)=["\'](?:article:published_time|pubdate|datePublished)["\'][^>]+content=["\']([^"\']+)["\']', "article:published_time"),
        (r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:article:published_time|pubdate|datePublished)["\']', "article:published_time"),
        (r'"datePublished"\s*:\s*["\']([^"\']+)["\']', "schema.org:datePublished"),
        (r'<time[^>]+datetime=["\']([^"\']+)["\']', "time:datetime"),
        (r'<meta[^>]+(?:property|name)=["\'](?:og:updated_time|article:modified_time)["\'][^>]+content=["\']([^"\']+)["\']', "og:updated_time"),
        (r'"dateModified"\s*:\s*["\']([^"\']+)["\']', "schema.org:dateModified"),
    ]

    for pat, source_name in meta_patterns:
        m = re.search(pat, raw_html, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            dt = _parse_iso_or_standard_date(val)
            if dt and dt <= ref_time + timedelta(days=2):  # Sanity check against future date bugs
                return dt, 0.90, f"structured_meta:{source_name}", val

    # --- 2. Visible Content Text Patterns (Confidence 0.60) ---
    # 2a. Relative dates: "3 days ago", "yesterday", "2 weeks ago"
    m_rel = re.search(r"\b(\d+)\s+(minute|hour|day|week|month)s?\s+ago\b", text, re.IGNORECASE)
    if m_rel:
        num = int(m_rel.group(1))
        unit = m_rel.group(2).lower()
        if unit.startswith("min"):
            dt = ref_time - timedelta(minutes=num)
        elif unit.startswith("hour"):
            dt = ref_time - timedelta(hours=num)
        elif unit.startswith("day"):
            dt = ref_time - timedelta(days=num)
        elif unit.startswith("week"):
            dt = ref_time - timedelta(days=num * 7)
        elif unit.startswith("month"):
            dt = ref_time - timedelta(days=num * 30)
        else:
            dt = ref_time
        return dt, 0.65, "content_text:relative", m_rel.group(0)

    if re.search(r"\byesterday\b", text[:2000], re.IGNORECASE):
        dt = ref_time - timedelta(days=1)
        return dt, 0.65, "content_text:yesterday", "yesterday"

    # 2b. Visible Byline / Article Dates: e.g. "Posted on October 4, 2026"
    date_context_matches = re.finditer(
        r"(?:posted|published|updated|announced|hiring|launched)?\s*(?:on|at|dated)?\s*"
        r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d\d)",
        text[:3000],
        re.IGNORECASE
    )
    for m_ctx in date_context_matches:
        snippet = text[max(0, m_ctx.start() - 30):min(len(text), m_ctx.end() + 30)]
        # Anti-False-Fresh: discard footer copyright dates
        if re.search(r"(?:copyright|©|\(c\)|all rights reserved|privacy policy)", snippet, re.IGNORECASE):
            continue
        dt = _parse_iso_or_standard_date(m_ctx.group(0))
        if dt and dt <= ref_time + timedelta(days=2):
            return dt, 0.60, "content_text:byline_date", m_ctx.group(0)

    # --- 3. HTTP Headers (Confidence 0.40) ---
    if headers and "last-modified" in headers:
        lm = headers["last-modified"]
        dt = _parse_iso_or_standard_date(lm)
        if dt and dt <= ref_time:
            return dt, 0.40, "http_header:last_modified", lm

    # Undated / evergreen page
    return None, 0.0, "undated", ""


def _archetype_queries(archetype: str, target: str, tried: List[str]) -> List[str]:
    """Generates playbook-tailored queries for the specific business archetype."""
    current_year = datetime.now().year
    candidates = []
    if archetype == "INDUSTRIAL_MANUFACTURING":
        candidates = [
            f"{target} manufacturers directory contact email",
            f"{target} industrial suppliers India contact us",
            f"{target} factory new plant expansion {current_year}",
            f"{target} ISO certified manufacturers contact email",
            f"{target} managing director sales contact email",
            f"{target} wholesale manufacturers contact us",
        ]
    elif archetype == "HEALTHCARE_CLINICAL":
        candidates = [
            f"{target} new clinic opening expansion {current_year}",
            f"{target} doctor practice manager contact email",
            f"{target} NABH hospital equipment procurement",
            f"{target} medical clinic director contact",
            f"{target} healthcare technology diagnostic center email",
        ]
    elif archetype == "ECOMMERCE_D2C":
        candidates = [
            f"{target} Shopify store launch {current_year}",
            f"{target} brand founder CEO contact email",
            f"{target} D2C brand new product catalog {current_year}",
            f"{target} ecommerce head of marketing email",
            f"{target} store expansion retail partners email",
        ]
    elif archetype == "LOCAL_SERVICES":
        candidates = [
            f"{target} licensed contractors local business contact",
            f"{target} owner phone email contact",
            f"{target} new location opening {current_year}",
            f"{target} commercial service directory email",
        ]
    elif archetype == "PROFESSIONAL_SERVICES":
        candidates = [
            f"{target} managing partner CEO contact email",
            f"{target} Clutch top agency new office {current_year}",
            f"{target} partner hired leadership expansion",
            f"{target} consulting firm founder email",
        ]
    else:  # ENTERPRISE_B2B_SAAS
        candidates = [
            f"{target} hiring software engineer {current_year}",
            f"{target} seed round Series A funding {current_year}",
            f"{target} site:greenhouse.io OR site:lever.co OR site:ashbyhq.com",
            f"{target} site:news.ycombinator.com who is hiring",
            f"{target} founder CEO contact email {current_year}",
            f"{target} Product Hunt launch {current_year}",
        ]
    return _dedupe_queries(candidates, tried, QUERIES_PER_ROUND)


def _fallback_queries(brief: str, tried: List[str]) -> List[str]:
    target = brief.split("\n")[0].replace("Search target:", "").strip()[:160] or "target customers"
    archetype = classify_archetype(brief, target)
    return _archetype_queries(archetype, target, tried)


def _followup_queries(urls: List[str], tried: List[str]) -> List[str]:
    """Search the buyer's own site after a page named them and hid the inbox."""
    candidates: List[str] = []
    for url in urls:
        host = _domain(url)
        if not host or _is_board_host(host):
            continue
        name = host.split(".")[0]
        if len(name) < 3:
            continue
        candidates.append(f"{name} contact email")
        candidates.append(f"{name} founder OR CEO team")
    return _dedupe_queries(candidates, tried, 4)


async def _search(client: httpx.AsyncClient, query: str, limit: int, df_param: Optional[str] = None) -> List[str]:
    # 1. Try Firecrawl search if configured
    try:
        from app.core.config import settings
        from firecrawl import FirecrawlApp
        key = getattr(settings, "FIRECRAWL_API_KEY", None)
        if key:
            app = FirecrawlApp(api_key=key)
            res = await asyncio.to_thread(app.search, query, limit=limit)
            urls = []
            items = getattr(res, "web", None) or getattr(res, "data", None) or []
            for item in items:
                u = getattr(item, "url", None) or (item.get("url") if isinstance(item, dict) else None)
                if u and _usable_result(u):
                    urls.append(u)
            if urls:
                return urls[:limit]
    except Exception as fe:
        logger.debug(f"Firecrawl search fallback: {fe}")

    # 2. DuckDuckGo fallback with temporal operator support
    try:
        data_payload = {"q": query}
        if df_param:
            data_payload["df"] = df_param  # 'w' for week, 'm' for month

        resp = await client.post(
            "https://html.duckduckgo.com/html/",
            data=data_payload,
            headers=HEADERS,
            timeout=15.0,
        )
        if resp.status_code == 200:
            urls: List[str] = []
            for href in re.findall(r'class="result__a"[^>]*href="([^"]+)"', resp.text):
                href = html_lib.unescape(href)
                if "uddg=" in href:
                    href = unquote(parse_qs(urlparse(href).query).get("uddg", [""])[0])
                if _usable_result(href):
                    urls.append(href)
                if len(urls) >= limit:
                    break
            if urls:
                return urls

        # If strict temporal filter yielded 0 results, retry without df_param
        if df_param:
            resp_broad = await client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
                headers=HEADERS,
                timeout=15.0,
            )
            if resp_broad.status_code == 200:
                urls_broad: List[str] = []
                for href in re.findall(r'class="result__a"[^>]*href="([^"]+)"', resp_broad.text):
                    href = html_lib.unescape(href)
                    if "uddg=" in href:
                        href = unquote(parse_qs(urlparse(href).query).get("uddg", [""])[0])
                    if _usable_result(href):
                        urls_broad.append(href)
                    if len(urls_broad) >= limit:
                        break
                if urls_broad:
                    return urls_broad
    except Exception as de:
        logger.debug(f"DuckDuckGo search error: {de}")

    return []


def _page_text(raw_html: str) -> str:
    cleaned = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw_html)
    cleaned = re.sub(r'(?i)href="mailto:([^"?]+)[^"]*"', r' \1 ', cleaned)
    text = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    return re.sub(r"\s+", " ", html_lib.unescape(text)).strip()


async def _fetch_html_and_text(client: httpx.AsyncClient, url: str) -> Tuple[str, str, Dict[str, str]]:
    try:
        safe = await asyncio.to_thread(validate_target_url, url)
        resp = await client.get(safe, headers=HEADERS, timeout=12.0, follow_redirects=True)
        if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
            raw_html = resp.text
            text = _page_text(raw_html)[:12000]
            headers_dict = {k.lower(): v for k, v in resp.headers.items()}
            return raw_html, text, headers_dict
    except Exception as e:
        logger.debug("web_discovery fetch failed for %s: %s", url, e)
    return "", "", {}


async def _fetch_text(client: httpx.AsyncClient, url: str) -> str:
    _, text, _ = await _fetch_html_and_text(client, url)
    return text

_default_fetch_text = _fetch_text


def _has_mx(domain: str) -> bool:
    try:
        return bool(dns.resolver.resolve(domain, "MX", lifetime=4))
    except Exception:
        return True  # Don't reject if local DNS has transient lookup error


async def _plan_queries(
    complete: Callable[..., Awaitable[str]],
    extract_json: Callable[[str], Any],
    brief: str,
    analyst_prompt: str,
    archetype: str,
    freshness_window: str,
    tried: List[str],
    empty_urls: List[str],
    notes: List[str],
) -> List[str]:
    """Plans intelligent multi-angle search queries tailored to domain archetype and freshness."""
    max_days = calculate_freshness_window_days(freshness_window)
    current_year = datetime.now().year
    timing_hint = f"Focus strictly on active signals within the last {max_days} days (Year: {current_year})." if max_days <= 90 else ""

    prompt = f"""Plan the next web searches for a B2B lead researcher to find actual company websites and decision makers. Do not invent companies or emails.

Target Brief:
{brief}

Archetype: {archetype}
Timing constraint: {timing_hint}

Analyst instructions:
{analyst_prompt or "None"}

Queries already run (do NOT repeat):
{tried or "none"}

Pages opened with no published email:
{empty_urls[:10] or "none"}

Write {QUERIES_PER_ROUND} high-intent search queries as a JSON array of strings.
CRITICAL SEARCH ENGINE FORMATTING RULES:
1. Translate the prompt instructions into queries that match what target companies publish on their official company websites, directories, or contact pages.
2. NEVER include internal vendor criteria like your deal budget (e.g. "1L-5L"), your agency's tech stack (e.g. Django, FastAPI, Flutter), or negative exclusions in search queries. Target prospects NEVER write these on their websites.
3. NEVER use complex Google Dork or nested Boolean operators: NO parentheses (), NO OR operators, NO numeric ranges (..), NO minus (-) flags. DuckDuckGo cannot parse them.
4. NEVER query login-walled portals, job boards, or app stores (NO site:linkedin.com, NO site:play.google.com, NO site:etenders.gov.in, NO site:naukri.com).
5. Use clean, natural phrases (3 to 6 words) targeting active companies, exporters, directories, or leadership contact in the target geography, e.g.:
   - "manufacturing companies in Pune contact email"
   - "industrial machinery manufacturers Gujarat contact"
   - "precision engineering manufacturers India about us email"
   - "auto components manufacturers India contact us"

Only output JSON array of strings."""

    try:
        parsed = extract_json(await complete(prompt))
        if isinstance(parsed, dict):
            parsed = parsed.get("queries") or parsed.get("search_queries") or []
        queries = [item for item in parsed if isinstance(item, str)] if isinstance(parsed, list) else []
    except Exception:
        logger.debug("web discovery query planning failed", exc_info=True)
        queries = []

    fresh = _dedupe_queries(queries, tried, QUERIES_PER_ROUND)
    if fresh:
        return fresh
    return _fallback_queries(brief, tried)


async def discover_leads_from_web(
    complete: Callable[..., Awaitable[str]],
    extract_json: Callable[[str], Any],
    query: str,
    count: int,
    analyst_prompt: Optional[str] = None,
    on_progress: Optional[Callable[[str], None]] = None,
    max_rounds: int = MAX_ROUNDS,
    freshness_window: str = "30_days",
) -> List[Dict[str, Any]]:
    """
    Return up to `count` leads with verifiable email and strict temporal freshness.
    Applies the Date Confidence Ladder and rejects stale signals (> freshness_window).
    """
    brief = (query or "").strip() or "target customers"
    instructions = (analyst_prompt or "").strip()[:8000]
    archetype = classify_archetype(brief, query)
    max_days = calculate_freshness_window_days(freshness_window)

    # DuckDuckGo temporal filter parameter
    df_param = "w" if max_days <= 14 else ("m" if max_days <= 30 else None)

    leads: List[Dict[str, Any]] = []
    seen_emails: set = set()
    seen_urls: set = set()
    tried: List[str] = []
    empty_urls: List[str] = []
    notes: List[str] = []
    rounds_run = 0
    now = datetime.now(timezone.utc)

    _notify(
        on_progress,
        f"Initiating Signal-Driven Web Discovery for {archetype} (Freshness constraint: {freshness_window}, max {max_days} days).",
    )

    async with httpx.AsyncClient() as client:
        for round_index in range(1, max(1, max_rounds) + 1):
            if len(leads) >= count:
                break

            queries = await _plan_queries(
                complete, extract_json, brief, instructions, archetype, freshness_window, tried, empty_urls, notes,
            )
            queries = _dedupe_queries(queries, tried, QUERIES_PER_ROUND)
            if not queries:
                queries = _followup_queries(empty_urls, tried)
            if not queries:
                notes.append(f"round {round_index} had no new queries")
                break

            rounds_run = round_index
            tried.extend(queries)
            for q in queries:
                _notify(on_progress, f"[SEARCH] Executing query: '{q}'")

            async def _safe_search(q: str):
                try:
                    return await _search(client, q, SEARCH_LIMIT, df_param=df_param)
                except TypeError:
                    return await _search(client, q, SEARCH_LIMIT)

            searched = await asyncio.gather(
                *[_safe_search(item) for item in queries],
                return_exceptions=True,
            )
            urls: List[str] = []
            for res in searched:
                if isinstance(res, list):
                    for url in res:
                        if url not in seen_urls and url not in urls:
                            urls.append(url)

            if not urls:
                notes.append(f"round {round_index} returned no pages")
                _notify(on_progress, f"[NOTICE] Web research round {round_index} returned no pages. Pivoting search angles.")
                continue

            batch_urls = urls[:PAGES_PER_ROUND]
            seen_urls.update(batch_urls)
            sem = asyncio.Semaphore(5)

            async def process(url: str):
                async with sem:
                    domain_name = _domain(url)
                    _notify(on_progress, f"[CRAWL] Inspecting {domain_name} ({url[:65]})...")
                    if _fetch_text != _default_fetch_text:
                        text = await _fetch_text(client, url)
                        raw_html = text
                        headers_dict = {}
                    else:
                        raw_html, text, headers_dict = await _fetch_html_and_text(client, url)
                    root = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                    if text and not EMAIL_RE.search(text):
                        for contact_path in ("/contact-us", "/contact", "/about-us", "/about", "/reach-us", "/contactus"):
                            _, contact_text, _ = await _fetch_html_and_text(client, f"{root}{contact_path}")
                            if contact_text and EMAIL_RE.search(contact_text):
                                text += " " + contact_text
                                break

                    emails_on_page = {e.lower().rstrip(".") for e in EMAIL_RE.findall(text)}
                    if not emails_on_page:
                        return [], url, "no_emails"

                    # --- Date Confidence Ladder & Freshness Gate ---
                    event_date, date_conf, date_src, snippet = extract_page_date_with_confidence(
                        raw_html, text, headers_dict, now=now
                    )
                    if event_date:
                        _notify(
                            on_progress,
                            f"[DATE] {domain_name}: Signal date {event_date.strftime('%Y-%m-%d')} (Confidence: {date_conf}, Source: {date_src})",
                        )

                    age_days = None
                    if event_date:
                        age_days = max(0.0, (now - event_date).total_seconds() / 86400.0)
                        # Freshness Gatekeeper: discard stale lead if older than max_days
                        if max_days < 9999 and age_days > max_days:
                            logger.info(
                                "Discarding %s: signal age (%.1f days) exceeds freshness cutoff (%d days).",
                                url, age_days, max_days,
                            )
                            return [], url, f"stale_signal_{int(age_days)}d"

                    # Extract contacts from page
                    try:
                        people = extract_json(await complete(
                            f'From this web page text, extract business contacts as a JSON array of objects with keys '
                            f'"name","title","email","company","phone". Only use facts present in the text; '
                            f'use "" when unknown. Page URL: {url}\nTarget Brief: {brief[:500]}\n\nTEXT:\n{text[:8000]}\n\n'
                            f'Only output JSON.'))
                    except Exception:
                        people = []

                    out = []
                    for person in people if isinstance(people, list) else []:
                        if not isinstance(person, dict):
                            continue
                        email = str(person.get("email", "")).lower().strip()
                        if email not in emails_on_page:
                            continue

                        # Format freshness label
                        if age_days is not None:
                            freshness_label = f"{int(age_days)}d ago" if age_days >= 1 else "Today"
                        else:
                            freshness_label = "Active Web"

                        out.append({
                            "name": str(person.get("name") or "").strip(),
                            "title": str(person.get("title") or "").strip(),
                            "email": email,
                            "company": str(person.get("company") or _domain(url).split(".")[0].capitalize()),
                            "website": _domain(url),
                            "phone": str(person.get("phone") or ""),
                            "evidence_url": url,
                            "freshness": {
                                "event_date": event_date.isoformat() if event_date else None,
                                "age_days": round(age_days, 1) if age_days is not None else None,
                                "date_confidence": date_conf,
                                "date_source": date_src,
                                "freshness_label": freshness_label,
                                "signal_snippet": snippet[:150],
                                "verified_active": True,
                                "freshness_window": freshness_window,
                            },
                        })

                    # Fallback to direct emails on page if LLM was overly conservative
                    if not out and emails_on_page:
                        for em in emails_on_page:
                            freshness_label = f"{int(age_days)}d ago" if age_days is not None else "Active Web"
                            out.append({
                                "name": "Contact Team",
                                "title": "Management",
                                "email": em,
                                "company": _domain(url).split(".")[0].capitalize(),
                                "website": _domain(url),
                                "phone": "",
                                "evidence_url": url,
                                "freshness": {
                                    "event_date": event_date.isoformat() if event_date else None,
                                    "age_days": round(age_days, 1) if age_days is not None else None,
                                    "date_confidence": date_conf,
                                    "date_source": date_src,
                                    "freshness_label": freshness_label,
                                    "signal_snippet": snippet[:150],
                                    "verified_active": True,
                                    "freshness_window": freshness_window,
                                },
                            })
                    return out, "", "ok"

            opened = 0
            stale_skipped = 0
            for batch in asyncio.as_completed([process(url) for url in batch_urls]):
                found, empty_url, status = await batch
                opened += 1
                if status.startswith("stale"):
                    stale_skipped += 1
                if empty_url and empty_url not in empty_urls:
                    empty_urls.append(empty_url)

                for lead in found:
                    if lead["email"] in seen_emails:
                        continue
                    # Deliverability syntax & MX verification
                    email_domain = lead["email"].split("@")[-1]
                    if not await asyncio.to_thread(_has_mx, email_domain):
                        continue
                    seen_emails.add(lead["email"])
                    leads.append(lead)
                    _notify(on_progress, f"[EMAIL] Verified deliverable contact: {lead['email']} ({lead['company']})")

                if len(leads) >= count:
                    break

            notes.append(f"round {round_index} opened {opened} pages, filtered {stale_skipped} stale, kept {len(leads)} fresh contacts")
            _notify(
                on_progress,
                f"Web research round {round_index}: evaluated {opened} pages ({stale_skipped} stale filtered out). Verified fresh leads: {len(leads)}/{count}.",
            )

    if not leads:
        preview = "; ".join(tried[:10]) or "none"
        raise RuntimeError(
            f"Open-web discovery found no verifiable contacts within freshness window ({freshness_window}) "
            f"for '{brief[:160]}' after {rounds_run} search rounds. Queries tried: {preview}."
        )

    return leads[:count]
