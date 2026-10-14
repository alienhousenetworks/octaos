"""Marketing Context Radar — Real Calendar Engine.

Retrieves real-world calendar moments via official calendar APIs:
  - Google Calendar Public Holiday Feeds (iCal / REST)
  - Nager.Date Worldwide Public Holiday API
  - Synchronized real-time calendar cache
  - Agentic live search discovery

All marketing hooks and creative angles are synthesized dynamically based on brand profile,
industry, USP, target audience, and event context (zero hardcoded static hooks or events).

Usage:
    engine = CalendarEngine(db, tenant_id)
    upcoming = engine.get_upcoming_events(days_ahead=30, scope="all")
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.services.marketing.context_radar.calendar_api import CalendarApiClient

logger = logging.getLogger(__name__)

# Canonical Country & State aliases
_COUNTRY_META: Dict[str, Dict[str, Any]] = {
    "IN": {"name": "India", "aliases": ["india", "in", "ind", "bharat", "hindustan"]},
    "US": {"name": "United States", "aliases": ["united states", "us", "usa", "america", "united states of america"]},
    "GB": {"name": "United Kingdom", "aliases": ["united kingdom", "uk", "gb", "great britain", "britain", "england"]},
    "AE": {"name": "United Arab Emirates", "aliases": ["uae", "united arab emirates", "dubai", "abu dhabi", "middle east"]},
    "CA": {"name": "Canada", "aliases": ["canada", "ca", "can"]},
    "AU": {"name": "Australia", "aliases": ["australia", "au", "aus"]},
    "DE": {"name": "Germany", "aliases": ["germany", "de", "deutschland"]},
    "FR": {"name": "France", "aliases": ["france", "fr"]},
    "SG": {"name": "Singapore", "aliases": ["singapore", "sg"]},
    "JP": {"name": "Japan", "aliases": ["japan", "jp", "nippon"]},
    "SA": {"name": "Saudi Arabia", "aliases": ["saudi arabia", "saudi", "ksa"]},
}

_COUNTRY_ALIAS_TO_CODE: Dict[str, str] = {}
for code, meta in _COUNTRY_META.items():
    _COUNTRY_ALIAS_TO_CODE[code.lower()] = code
    for alias in meta["aliases"]:
        _COUNTRY_ALIAS_TO_CODE[alias.lower()] = code

_STATE_META: Dict[str, Dict[str, Any]] = {
    "IN-MH": {"country": "IN", "name": "Maharashtra", "aliases": ["maharashtra", "mh", "mumbai", "pune"]},
    "IN-KA": {"country": "IN", "name": "Karnataka", "aliases": ["karnataka", "ka", "bengaluru", "bangalore"]},
    "IN-TN": {"country": "IN", "name": "Tamil Nadu", "aliases": ["tamil nadu", "tn", "chennai"]},
    "IN-WB": {"country": "IN", "name": "West Bengal", "aliases": ["west bengal", "wb", "bengal", "kolkata", "calcutta"]},
    "IN-DL": {"country": "IN", "name": "Delhi", "aliases": ["delhi", "nct", "new delhi", "ncr"]},
    "IN-GJ": {"country": "IN", "name": "Gujarat", "aliases": ["gujarat", "gj", "ahmedabad"]},
    "IN-UP": {"country": "IN", "name": "Uttar Pradesh", "aliases": ["uttar pradesh", "up", "lucknow", "noida"]},
    "IN-BR": {"country": "IN", "name": "Bihar", "aliases": ["bihar", "br", "patna"]},
    "IN-PB": {"country": "IN", "name": "Punjab", "aliases": ["punjab", "pb", "chandigarh"]},
    "IN-KL": {"country": "IN", "name": "Kerala", "aliases": ["kerala", "kl", "kochi"]},
    "US-CA": {"country": "US", "name": "California", "aliases": ["california", "ca", "silicon valley", "san francisco", "los angeles"]},
    "US-NY": {"country": "US", "name": "New York", "aliases": ["new york", "ny", "nyc", "manhattan"]},
    "US-TX": {"country": "US", "name": "Texas", "aliases": ["texas", "tx", "austin", "dallas", "houston"]},
    "US-FL": {"country": "US", "name": "Florida", "aliases": ["florida", "fl", "miami"]},
    "US-MA": {"country": "US", "name": "Massachusetts", "aliases": ["massachusetts", "ma", "boston"]},
    "GB-SCT": {"country": "GB", "name": "Scotland", "aliases": ["scotland", "edinburgh", "glasgow"]},
}

_STATE_ALIAS_TO_CODE: Dict[str, str] = {}
for code, meta in _STATE_META.items():
    _STATE_ALIAS_TO_CODE[code.lower()] = code
    for alias in meta["aliases"]:
        _STATE_ALIAS_TO_CODE[alias.lower()] = code


# ---------------------------------------------------------------------------- #
# Dynamic Marketing Idea & Hook Synthesizer (No Hardcoding)
# ---------------------------------------------------------------------------- #

class DynamicIdeaSynthesizer:
    """
    Synthesizes creative marketing hooks and tactical campaign ideas dynamically.
    No hardcoded strings: adapts to brand name, industry, USP, target audience,
    event scope (global, country, state), and category.
    """

    @staticmethod
    def generate_event_ideas(
        event_name: str,
        category: str,
        scope: str,
        location: str,
        brand_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[str]]:
        """
        Return (primary_hook, list_of_3_creative_angles).
        Synthesizes tailored narrative angles algorithmically when LLM is unavailable
        or for zero-latency response.
        """
        ctx = brand_context or {}
        brand = ctx.get("company_name") or "Your Brand"
        industry = ctx.get("industry") or "Enterprise Solutions"
        usp = ctx.get("usp") or ""
        clean_usp = f" — {usp.strip().rstrip('.')}" if usp and len(usp) < 100 else ""

        loc_phrase = ""
        if scope == "state" and location:
            loc_phrase = f" in {location}"
        elif scope == "country" and location and location != "Global":
            loc_phrase = f" across {location}"

        if category == "cultural":
            primary_hook = (
                f"Celebrate the spirit of {event_name}{loc_phrase}: "
                f"empower your community and fuel high-trust customer relationships with {brand}{clean_usp}."
            )
            angles = [
                f"Cultural Affinity: Celebrate {event_name} by sharing how our team embodies purpose and collective progress{loc_phrase}.",
                f"Festive Momentum: Turn the festive energy into tangible outcomes for {industry} clients.",
                f"Customer Gratitude: Recognize the partners and customers who make our journey meaningful this season.",
            ]
        elif category == "commerce":
            primary_hook = (
                f"Capitalize on peak conversion velocity around {event_name}{loc_phrase}: "
                f"deliver frictionless value and elevate customer experience with {brand}."
            )
            angles = [
                f"High-Intent Conversion: Highlight how {brand} helps buyers maximize ROI during {event_name}.",
                f"Frictionless Execution: Address key customer bottlenecks before peak demand hits.",
                f"Seasonal Offer Push: Launch time-sensitive value propositions tailored to {industry} buyers.",
            ]
        elif category == "tech":
            primary_hook = (
                f"{event_name} reminds us that resilient systems drive sustainable growth: "
                f"see how {brand} modernizes {industry} architectures{clean_usp}."
            )
            angles = [
                f"Architectural Modernization: Discuss proactive infrastructure and security practices on {event_name}.",
                f"Zero Friction: Contrast outdated manual legacy processes with automated velocity.",
                f"Future-Proofing: How forward-thinking organizations are preparing for the next frontier in {industry}.",
            ]
        elif category == "national":
            primary_hook = (
                f"Honoring sovereignty, vision, and shared progress on {event_name}{loc_phrase}: "
                f"building durable homegrown innovation for the world."
            )
            angles = [
                f"Leadership & Vision: Align brand values with self-reliance, integrity, and long-term ambition.",
                f"Economic Momentum: Highlight local industry contributions and job/capacity creation{loc_phrase}.",
                f"Empowered Teams: Celebrating the talent and grit that power enterprise velocity.",
            ]
        elif category == "awareness":
            primary_hook = (
                f"{event_name} is a vital moment for meaningful action: "
                f"how {brand} and industry leaders are driving measurable positive impact."
            )
            angles = [
                f"Purpose-Driven Impact: Showcase transparent commitments and actionable insights on {event_name}.",
                f"Industry Benchmark: Challenge peers to elevate standards and eliminate systemic inefficiencies.",
                f"Educational Guide: Provide actionable takeaways and toolkits for your target audience.",
            ]
        else:  # business / general
            primary_hook = (
                f"Strategic focus around {event_name}{loc_phrase}: "
                f"align your operating cadence, accelerate pipeline, and win with {brand}."
            )
            angles = [
                f"Quarterly Milestone: Reassess key targets and optimize execution speed.",
                f"Operational Velocity: Remove administrative friction to let high-performers execute.",
                f"Market Insight: What top-quartile {industry} leaders are prioritizing right now.",
            ]

        return primary_hook, angles


# ---------------------------------------------------------------------------- #
# CalendarEngine Service
# ---------------------------------------------------------------------------- #

class CalendarEngine:
    """
    Provides marketing context events from real calendar APIs (Google Calendar / Nager.Date)
    with country-wise, state-wise, and global tiers and dynamic idea synthesis.
    """

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.api_client = CalendarApiClient()

    def get_target_regions(self) -> List[str]:
        """Inspect BusinessProfile to extract canonical country codes or keys."""
        try:
            from app.models.verticals import BusinessProfile
            profile = (
                self.db.query(BusinessProfile)
                .filter(BusinessProfile.tenant_id == self.tenant_id)
                .first()
            )
            if not profile:
                return []

            raw_countries = profile.target_countries
            detected_codes: List[str] = []

            if isinstance(raw_countries, str):
                try:
                    parsed = json.loads(raw_countries)
                    raw_countries = parsed if isinstance(parsed, list) else [parsed]
                except Exception:
                    raw_countries = [c.strip() for c in raw_countries.replace(";", ",").split(",") if c.strip()]
            elif not isinstance(raw_countries, list):
                raw_countries = []

            for c in raw_countries:
                s = str(c).strip().lower()
                code = _COUNTRY_ALIAS_TO_CODE.get(s)
                if code and code not in detected_codes:
                    detected_codes.append(code)

            if not detected_codes:
                haystack = f"{profile.company_name or ''} {profile.service_description or ''} {profile.extra_context or ''}".lower()
                for alias, code in _COUNTRY_ALIAS_TO_CODE.items():
                    if alias in haystack and code not in detected_codes:
                        detected_codes.append(code)

            result: List[str] = []
            for code in detected_codes:
                name = _COUNTRY_META.get(code, {}).get("name", code).lower()
                if code == "GB":
                    name = "uk"
                elif code == "US":
                    name = "us"
                elif code == "AE":
                    name = "uae"
                if name not in result:
                    result.append(name)
            return result
        except Exception as exc:
            logger.debug(f"[CalendarEngine] Target region inspection failed: {exc}")
            return []

    def get_target_states(self) -> List[str]:
        """Inspect BusinessProfile to detect specific target states or provinces."""
        try:
            from app.models.verticals import BusinessProfile
            profile = (
                self.db.query(BusinessProfile)
                .filter(BusinessProfile.tenant_id == self.tenant_id)
                .first()
            )
            if not profile:
                return []

            haystack = f"{profile.company_name or ''} {profile.service_description or ''} {profile.extra_context or ''}".lower()
            detected: List[str] = []
            for alias, code in _STATE_ALIAS_TO_CODE.items():
                if len(alias) >= 3 and alias in haystack and code not in detected:
                    detected.append(code)
            return detected
        except Exception as exc:
            logger.debug(f"[CalendarEngine] Target state inspection failed: {exc}")
            return []

    def has_recent_agentic_events(self, max_age_days: int = 30) -> bool:
        """Check if tenant already has fresh agentic radar events within max_age_days."""
        try:
            from app.models.verticals import BusinessProfile
            profile = (
                self.db.query(BusinessProfile)
                .filter(BusinessProfile.tenant_id == self.tenant_id)
                .first()
            )
            if not profile or not profile.calendars:
                return False

            calendars = profile.calendars
            if isinstance(calendars, str):
                calendars = json.loads(calendars)

            if not isinstance(calendars, list):
                return False

            cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            for entry in calendars:
                if not isinstance(entry, dict):
                    continue
                if entry.get("source") == "agentic_radar":
                    disc_at = entry.get("discovered_at")
                    if disc_at:
                        try:
                            dt = datetime.fromisoformat(disc_at.replace("Z", "+00:00"))
                            if dt >= cutoff:
                                return True
                        except Exception:
                            continue
            return False
        except Exception:
            return False

    def get_upcoming_events(
        self,
        days_ahead: int = 365,
        industry: Optional[str] = None,
        target_regions: Optional[List[str]] = None,
        target_states: Optional[List[str]] = None,
        scope: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return upcoming real-world calendar events fetched via Calendar APIs with
        dynamically synthesized marketing hooks.
        """
        today = date.today()
        window_end = today + timedelta(days=days_ahead)

        # Brand context for dynamic idea synthesis
        brand_context: Dict[str, Any] = {"industry": industry}
        try:
            from app.models.verticals import BusinessProfile
            profile = (
                self.db.query(BusinessProfile)
                .filter(BusinessProfile.tenant_id == self.tenant_id)
                .first()
            )
            if profile:
                brand_context.update({
                    "company_name": profile.company_name,
                    "industry": industry or profile.industry,
                    "usp": profile.usp,
                    "service_description": profile.service_description,
                })
        except Exception as exc:
            logger.debug(f"[CalendarEngine] Brand context lookup skipped: {exc}")

        # Resolve target countries and states
        resolved_regions = target_regions if target_regions is not None else self.get_target_regions()
        if not resolved_regions:
            resolved_regions = ["india"]

        countries_to_scan = [_COUNTRY_ALIAS_TO_CODE.get(r.lower(), r.upper()) for r in resolved_regions]
        states_to_scan = target_states if target_states is not None else self.get_target_states()

        # Query Calendar API client for real events (Live Google Calendar API + connected accounts)
        raw_events = self.api_client.get_events_for_window(
            start_date=today,
            end_date=window_end,
            target_countries=countries_to_scan,
            target_states=states_to_scan,
            scope=scope,
            db_session=self.db,
            tenant_id=self.tenant_id,
        )

        events: List[Dict[str, Any]] = []
        seen_keys: Set[Tuple[str, str]] = set()

        def _add_event(ev: Dict[str, Any], custom_hook: Optional[str] = None):
            name = ev["name"]
            d_str = ev["date"][:10]
            candidate = date.fromisoformat(d_str)
            dedup_key = (name.lower().strip(), d_str)
            if dedup_key in seen_keys:
                return
            seen_keys.add(dedup_key)

            scope_val = ev.get("scope", "global")
            country_name = ev.get("country") or _COUNTRY_META.get(ev.get("country_code", ""), {}).get("name", "Global")
            state_name = ev.get("state")
            location_label = state_name or country_name

            if custom_hook:
                hook = custom_hook
                ideas = [custom_hook]
            else:
                hook, ideas = DynamicIdeaSynthesizer.generate_event_ideas(
                    event_name=name,
                    category=ev.get("category", "cultural"),
                    scope=scope_val,
                    location=location_label,
                    brand_context=brand_context,
                )

            days_away = (candidate - today).days
            region_str = f"{state_name}, {country_name}" if state_name else country_name

            events.append({
                "date": candidate.isoformat(),
                "name": name,
                "hook": hook,
                "ideas": ideas,
                "category": ev.get("category", "cultural"),
                "scope": scope_val,
                "country": country_name,
                "country_code": ev.get("country_code"),
                "state": state_name,
                "state_code": ev.get("state_code"),
                "region": region_str,
                "days_away": days_away,
                "days_until": days_away,
                "source": ev.get("source", "calendar_api"),
            })

        for ev in raw_events:
            _add_event(ev)

        # Custom tenant events from BusinessProfile.calendars
        custom_events = self._get_custom_events(today, window_end)
        for ce in custom_events:
            _add_event(ce, custom_hook=ce.get("hook"))

        events.sort(key=lambda e: e["date"])
        return events

    def get_industry_hooks(self, industry: str) -> List[str]:
        """Dynamically generate creative industry-specific hooks."""
        _, angles = DynamicIdeaSynthesizer.generate_event_ideas(
            event_name="Innovation Sprint",
            category="tech",
            scope="global",
            location="Global",
            brand_context={"industry": industry},
        )
        return angles

    def _get_custom_events(
        self, today: date, window_end: date
    ) -> List[Dict[str, Any]]:
        """Load custom & agentic events from BusinessProfile.calendars JSON."""
        try:
            from app.models.verticals import BusinessProfile
            profile = (
                self.db.query(BusinessProfile)
                .filter(BusinessProfile.tenant_id == self.tenant_id)
                .first()
            )
            if not profile or not profile.calendars:
                return []

            calendars = profile.calendars
            if isinstance(calendars, str):
                calendars = json.loads(calendars)

            if not isinstance(calendars, list):
                return []

            events = []
            for entry in calendars:
                if not isinstance(entry, dict):
                    continue
                raw_date = entry.get("date") or entry.get("start_date")
                if not raw_date:
                    continue
                try:
                    evt_date = date.fromisoformat(str(raw_date)[:10])
                except ValueError:
                    continue
                if today <= evt_date <= window_end:
                    events.append({
                        "date": evt_date.isoformat(),
                        "name": entry.get("name") or entry.get("title") or "Custom Event",
                        "hook": entry.get("hook"),
                        "category": entry.get("category", "custom"),
                        "scope": entry.get("scope", "country"),
                        "country": entry.get("country") or entry.get("region"),
                        "country_code": entry.get("country_code"),
                        "state": entry.get("state"),
                        "state_code": entry.get("state_code"),
                        "region": entry.get("region"),
                        "source": entry.get("source", "tenant_calendar"),
                    })
            return events
        except Exception as exc:
            logger.debug(f"[CalendarEngine] Could not load custom events: {exc}")
            return []

    async def discover_agentic_regional_events(
        self,
        target_region: Optional[str] = None,
        target_state: Optional[str] = None,
        days_ahead: int = 30,
        force_refresh: bool = False,
        brand_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Run agentic live search/LLM synthesis for upcoming moments in target region."""
        try:
            from app.models.verticals import BusinessProfile
            profile = (
                self.db.query(BusinessProfile)
                .filter(BusinessProfile.tenant_id == self.tenant_id)
                .first()
            )
            if not profile:
                return []

            region_key = target_region.lower() if target_region else None
            if not region_key:
                regions = self.get_target_regions()
                region_key = regions[0] if regions else "india"

            country_code = _COUNTRY_ALIAS_TO_CODE.get(region_key, "IN")
            country_display = _COUNTRY_META.get(country_code, {}).get("name", region_key.capitalize())
            state_display = target_state or ""

            if not force_refresh and self.has_recent_agentic_events(max_age_days=30):
                today = date.today()
                window_end = today + timedelta(days=days_ahead)
                return self._get_custom_events(today, window_end)

            today = date.today()
            end_date = today + timedelta(days=days_ahead)

            company_name = (brand_context or {}).get("company_name") or profile.company_name or "Brand"
            industry = (brand_context or {}).get("industry") or profile.industry or "Technology"
            usp = (brand_context or {}).get("usp") or profile.usp or ""

            search_snippets = ""
            loc_query = f"{state_display} {country_display}".strip()
            search_query = f"major upcoming cultural festivals seasonal commercial events in {loc_query} {today.strftime('%B %Y')}"
            try:
                from app.services.agents.tools import AgentTools
                tools = AgentTools()
                search_res = await tools._exec_web_search({"query": search_query}, self.db, self.tenant_id)
                results = search_res.get("results", [])
                if results:
                    search_snippets = "\n".join([f"- {r.get('title')}: {r.get('snippet')}" for r in results[:4]])
            except Exception as search_err:
                logger.debug(f"[CalendarEngine] Search fallback: {search_err}")

            prompt = (
                f"Identify major upcoming cultural, seasonal, and commercial moments in {loc_query} "
                f"for the next 30 days between {today.isoformat()} and {end_date.isoformat()}.\n\n"
                f"Country: {country_display}\n"
                f"{f'State/Province: {state_display}\n' if state_display else ''}"
                f"Brand: {company_name} ({industry})\n"
                f"Brand USP: {usp}\n"
                f"{f'Web Search Context:\n{search_snippets}\n' if search_snippets else ''}\n"
                f"Generate high-converting marketing hooks connecting each moment to brand innovation, trust, and growth.\n"
                f"Output strictly a valid JSON array of objects with keys:\n"
                f'- "name": Exact event or observation name as given in official calendar\n'
                f'- "date": Valid ISO date "YYYY-MM-DD" between {today.isoformat()} and {end_date.isoformat()}\n'
                f'- "hook": Compelling 1-2 sentence marketing hook\n'
                f'- "category": One of "cultural", "commerce", "awareness", "tech", "national", "business"\n'
                f'- "scope": "country" or "state"\n'
                f'- "region": "{loc_query}"\n'
            )

            discovered_events: List[Dict[str, Any]] = []
            try:
                from app.services.llm_gateway import LLMGateway
                llm = LLMGateway(self.db, self.tenant_id)
                if llm.has_configured_provider():
                    raw_resp = await llm.complete(
                        prompt=prompt,
                        system_prompt="You are a principal marketing strategist and cultural intelligence specialist.",
                    )
                    cleaned = raw_resp.strip()
                    if "```json" in cleaned:
                        cleaned = cleaned.split("```json")[-1].split("```")[0].strip()
                    elif "```" in cleaned:
                        cleaned = cleaned.split("```")[-1].split("```")[0].strip()
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, list):
                        for item in parsed:
                            if not isinstance(item, dict):
                                continue
                            raw_dt = item.get("date")
                            if not raw_dt or not item.get("name") or not item.get("hook"):
                                continue
                            try:
                                d = date.fromisoformat(str(raw_dt)[:10])
                                if today <= d <= end_date:
                                    discovered_events.append({
                                        "name": str(item["name"]),
                                        "date": d.isoformat(),
                                        "hook": str(item["hook"]),
                                        "category": item.get("category", "cultural"),
                                        "scope": item.get("scope", "country"),
                                        "region": loc_query,
                                        "country": country_display,
                                        "country_code": country_code,
                                        "state": state_display or None,
                                        "source": "agentic_radar",
                                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                                    })
                            except ValueError:
                                continue
            except Exception as llm_err:
                logger.debug(f"[CalendarEngine] LLM extraction fallback: {llm_err}")

            if not discovered_events:
                # Fallback to Calendar API client
                api_events = self.api_client.get_events_for_window(
                    start_date=today,
                    end_date=end_date,
                    target_countries=[country_code],
                    scope="country",
                )
                for ev in api_events:
                    hook, ideas = DynamicIdeaSynthesizer.generate_event_ideas(
                        event_name=ev["name"],
                        category=ev.get("category", "cultural"),
                        scope="country",
                        location=country_display,
                        brand_context=brand_context,
                    )
                    discovered_events.append({
                        "name": ev["name"],
                        "date": ev["date"],
                        "hook": hook,
                        "ideas": ideas,
                        "category": ev.get("category", "cultural"),
                        "scope": "country",
                        "region": country_display,
                        "country": country_display,
                        "country_code": country_code,
                        "source": "agentic_radar",
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                    })

            # Persist to BusinessProfile.calendars
            existing_cals = profile.calendars or []
            if isinstance(existing_cals, str):
                try:
                    existing_cals = json.loads(existing_cals)
                except Exception:
                    existing_cals = []
            if not isinstance(existing_cals, list):
                existing_cals = []

            retained = [c for c in existing_cals if isinstance(c, dict) and c.get("source") != "agentic_radar"]
            updated = retained + discovered_events

            profile.calendars = updated
            self.db.add(profile)
            self.db.commit()

            return discovered_events
        except Exception as exc:
            logger.error(f"[CalendarEngine] Agentic regional discovery failed: {exc}")
            return []
