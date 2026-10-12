"""Marketing Context Radar — Calendar Engine.

Manages a standard global marketing & awareness calendar (holidays, international
awareness days, industry peaks, Q-ends) plus custom tenant events loaded from
BusinessProfile.calendars.

Usage:
    engine = CalendarEngine(db, tenant_id)
    upcoming = engine.get_upcoming_events(days_ahead=7)
    # Returns list of MarketingEvent dicts with hook suggestions.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------- #
# Global Marketing Calendar (evergreen + rolling awareness dates)
# Month is 1-indexed, day 0 means "first occurrence" or handled specially.
# ---------------------------------------------------------------------------- #

_GLOBAL_CALENDAR: List[Dict[str, Any]] = [
    # Q-Start pushes
    {"month": 1,  "day": 1,  "name": "New Year — Goal-Setting Season",      "hook": "New year, new goals. How is your team preparing?",              "category": "cultural"},
    {"month": 1,  "day": 15, "name": "Martin Luther King Jr. Day",           "hook": "Leadership, equity, and vision drive meaningful change.",        "category": "awareness"},
    {"month": 2,  "day": 14, "name": "Valentine's Day — Customer Love Day",  "hook": "Show your customers some love this season.",                     "category": "cultural"},
    {"month": 3,  "day": 8,  "name": "International Women's Day",            "hook": "Celebrating the women shaping industries worldwide.",            "category": "awareness"},
    {"month": 3,  "day": 21, "name": "World Poetry Day / Creativity Day",    "hook": "Creativity is the engine of progress.",                          "category": "awareness"},
    {"month": 4,  "day": 1,  "name": "April Fools / Q2 Kickoff",             "hook": "No joke — Q2 is here. What's your growth play?",                "category": "business"},
    {"month": 4,  "day": 22, "name": "Earth Day — Sustainability Focus",     "hook": "Sustainability isn't optional — it's competitive advantage.",     "category": "awareness"},
    {"month": 5,  "day": 1,  "name": "International Workers' Day",           "hook": "The teams behind the product make all the difference.",          "category": "awareness"},
    {"month": 6,  "day": 5,  "name": "World Environment Day",                "hook": "What does responsible business look like in 2026?",              "category": "awareness"},
    {"month": 6,  "day": 15, "name": "Mid-Year Review Season",               "hook": "Half the year is gone. Are your systems scaling with you?",      "category": "business"},
    {"month": 7,  "day": 1,  "name": "Q3 Kickoff",                           "hook": "Q3 starts now. Where are you investing your momentum?",          "category": "business"},
    {"month": 8,  "day": 12, "name": "International Youth Day",              "hook": "The next generation of buyers thinks differently.",               "category": "awareness"},
    {"month": 9,  "day": 1,  "name": "Back to Business — September Sprint",  "hook": "September signals execution season. How prepared is your team?", "category": "business"},
    {"month": 9,  "day": 30, "name": "Q3-End / Q4 Planning Season",         "hook": "Q4 is the most competitive quarter. Start planning now.",        "category": "business"},
    {"month": 10, "day": 1,  "name": "Q4 Kickoff — Peak Season Begins",      "hook": "Q4 is live. Your biggest revenue window starts today.",          "category": "business"},
    {"month": 10, "day": 4,  "name": "World Space Week",                     "hook": "Aim higher — the ceiling is not the limit.",                     "category": "awareness"},
    {"month": 10, "day": 16, "name": "World Food Day — Sustainability",      "hook": "What we build today feeds the world of tomorrow.",               "category": "awareness"},
    {"month": 11, "day": 1,  "name": "World Quality Day",                    "hook": "Quality isn't a feature — it's a commitment.",                   "category": "business"},
    {"month": 11, "day": 11, "name": "Singles Day / Global Commerce Day",    "hook": "The biggest shopping moment of the year is approaching.",        "category": "commerce"},
    {"month": 11, "day": 29, "name": "Black Friday — Commerce Peak",         "hook": "Black Friday isn't just retail — it's peak conversion season.",  "category": "commerce"},
    {"month": 12, "day": 1,  "name": "World AIDS Day — Cause Marketing",     "hook": "Brands that stand for something stand out in a crowded market.", "category": "awareness"},
    {"month": 12, "day": 15, "name": "Year-End Push / Holiday Season",       "hook": "Close the year strong. Final decisions are being made now.",     "category": "business"},
    {"month": 12, "day": 31, "name": "Year-End Reflection",                  "hook": "What did you build this year? What will you build next?",        "category": "cultural"},
    # Tech-specific
    {"month": 1,  "day": 28, "name": "Data Privacy Day",                     "hook": "Privacy-first is not a feature — it's the foundation.",         "category": "tech"},
    {"month": 3,  "day": 31, "name": "World Backup Day",                     "hook": "Is your data protected as well as your ambitions?",              "category": "tech"},
    {"month": 10, "day": 15, "name": "Cybersecurity Awareness Month (Oct)", "hook": "In a connected world, security is the new brand promise.",       "category": "tech"},
    {"month": 11, "day": 30, "name": "Computer Security Day",                "hook": "Security isn't a department — it's everyone's job.",             "category": "tech"},
]

# ---------------------------------------------------------------------------- #
# Regional Marketing & Cultural Calendars
# Movable / lunisolar festivals use year-specific maps: {year: (month, day)}.
# Fixed solar dates use {"month": M, "day": D}.
# ---------------------------------------------------------------------------- #

_REGIONAL_CALENDARS: Dict[str, List[Dict[str, Any]]] = {
    "india": [
        # Major Lunisolar & Cultural Festivals
        {
            "name": "Navratri & Durga Puja (Maha Saptami / Ashtami)",
            "dates": {2025: (10, 9), 2026: (10, 18), 2027: (10, 7), 2028: (10, 25)},
            "hook": "Celebrating victory of innovation over inertia: festive momentum for your brand.",
            "category": "cultural",
            "region": "India",
        },
        {
            "name": "Dussehra (Vijayadashami)",
            "dates": {2025: (10, 12), 2026: (10, 21), 2027: (10, 11), 2028: (10, 28)},
            "hook": "Conquering inefficiency and celebrating breakthrough wins this festive season.",
            "category": "cultural",
            "region": "India",
        },
        {
            "name": "Karwa Chauth",
            "dates": {2025: (10, 10), 2026: (10, 29), 2027: (10, 19), 2028: (11, 6)},
            "hook": "Commitment and trust are the foundation of enduring partnerships.",
            "category": "cultural",
            "region": "India",
        },
        {
            "name": "Dhanteras — Auspicious Beginnings & Commerce",
            "dates": {2025: (10, 18), 2026: (11, 6), 2027: (10, 28), 2028: (11, 15)},
            "hook": "Invest in systems that compound: auspicious beginnings for technology and growth.",
            "category": "commerce",
            "region": "India",
        },
        {
            "name": "Diwali (Deepavali) — Festival of Lights",
            "dates": {2025: (10, 20), 2026: (11, 8), 2027: (10, 29), 2028: (11, 17)},
            "hook": "Lighting the way to transformation: bring clarity, trust, and festive warmth to customers.",
            "category": "cultural",
            "region": "India",
        },
        {
            "name": "Bhai Dooj",
            "dates": {2025: (10, 22), 2026: (11, 10), 2027: (10, 31), 2028: (11, 19)},
            "hook": "Strong bonds drive lasting success: celebrating loyalty and collaboration.",
            "category": "cultural",
            "region": "India",
        },
        {
            "name": "Chhath Puja",
            "dates": {2025: (10, 26), 2026: (11, 14), 2027: (11, 4), 2028: (11, 23)},
            "hook": "Dedication, discipline, and sustainable vision lead to true abundance.",
            "category": "cultural",
            "region": "India",
        },
        {
            "name": "Makar Sankranti / Pongal / Lohri",
            "month": 1, "day": 14,
            "hook": "Harvest season for growth: reap the returns of your strategic investments.",
            "category": "cultural",
            "region": "India",
        },
        {
            "name": "National Startup Day (India)",
            "month": 1, "day": 16,
            "hook": "Celebrating founders building the future: from zero to scale.",
            "category": "business",
            "region": "India",
        },
        {
            "name": "Republic Day (India)",
            "month": 1, "day": 26,
            "hook": "Sovereignty, vision, and building homegrown global champions.",
            "category": "national",
            "region": "India",
        },
        {
            "name": "Holi — Festival of Colours",
            "dates": {2025: (3, 14), 2026: (3, 3), 2027: (3, 22), 2028: (3, 11)},
            "hook": "Add vibrant color and fresh energy to your campaigns this festive season.",
            "category": "cultural",
            "region": "India",
        },
        {
            "name": "National Technology Day (India)",
            "month": 5, "day": 11,
            "hook": "Pioneering technological self-reliance: building high-impact engineering systems.",
            "category": "tech",
            "region": "India",
        },
        {
            "name": "Independence Day (India)",
            "month": 8, "day": 15,
            "hook": "Empowering autonomy: liberating teams from manual overhead to build the future.",
            "category": "national",
            "region": "India",
        },
        {
            "name": "Raksha Bandhan",
            "dates": {2025: (8, 9), 2026: (8, 28), 2027: (8, 17), 2028: (8, 5)},
            "hook": "Trust and protection are the ultimate competitive advantage.",
            "category": "cultural",
            "region": "India",
        },
        {
            "name": "Ganesh Chaturthi",
            "dates": {2025: (8, 27), 2026: (9, 14), 2027: (9, 4), 2028: (8, 24)},
            "hook": "Removing obstacles, initiating bold new beginnings.",
            "category": "cultural",
            "region": "India",
        },
        {
            "name": "Engineers Day (India)",
            "month": 9, "day": 15,
            "hook": "Engineers build the architectures that scale the modern world.",
            "category": "tech",
            "region": "India",
        },
        {
            "name": "Gandhi Jayanti",
            "month": 10, "day": 2,
            "hook": "Ethical leadership and purposeful innovation stand the test of time.",
            "category": "national",
            "region": "India",
        },
        {
            "name": "Guru Nanak Jayanti",
            "dates": {2025: (11, 5), 2026: (11, 24), 2027: (11, 14), 2028: (11, 2)},
            "hook": "Service, integrity, and shared prosperity guide high-trust brands.",
            "category": "cultural",
            "region": "India",
        },
    ],
    "us": [
        {
            "name": "Super Bowl Commercial Season",
            "dates": {2025: (2, 9), 2026: (2, 8), 2027: (2, 14), 2028: (2, 13)},
            "hook": "The biggest advertising stage of the year: high-stakes messaging that cuts through.",
            "category": "commerce",
            "region": "United States",
        },
        {
            "name": "Memorial Day Weekend",
            "dates": {2025: (5, 26), 2026: (5, 25), 2027: (5, 31), 2028: (5, 29)},
            "hook": "Summer kickoff: reset campaigns and align with peak seasonal consumer behavior.",
            "category": "national",
            "region": "United States",
        },
        {
            "name": "Juneteenth",
            "month": 6, "day": 19,
            "hook": "Celebrating freedom, resilience, and equitable innovation.",
            "category": "awareness",
            "region": "United States",
        },
        {
            "name": "4th of July — US Independence Day",
            "month": 7, "day": 4,
            "hook": "Freedom to innovate: celebrate bold independence and high-growth trajectories.",
            "category": "national",
            "region": "United States",
        },
        {
            "name": "Labor Day Weekend",
            "dates": {2025: (9, 1), 2026: (9, 7), 2027: (9, 6), 2028: (9, 4)},
            "hook": "Honoring the workforce that powers enterprise velocity.",
            "category": "national",
            "region": "United States",
        },
        {
            "name": "Halloween Marketing Peak",
            "month": 10, "day": 31,
            "hook": "Don't let manual inefficiencies haunt your business.",
            "category": "cultural",
            "region": "United States",
        },
        {
            "name": "Thanksgiving Day",
            "dates": {2025: (11, 27), 2026: (11, 26), 2027: (11, 25), 2028: (11, 23)},
            "hook": "Gratitude in business: celebrating the clients and partners who make growth possible.",
            "category": "cultural",
            "region": "United States",
        },
        {
            "name": "Cyber Monday",
            "dates": {2025: (12, 1), 2026: (11, 30), 2027: (11, 29), 2028: (11, 27)},
            "hook": "The biggest digital commerce day on the calendar: frictionless conversion wins.",
            "category": "commerce",
            "region": "United States",
        },
    ],
    "uk": [
        {
            "name": "St. Patrick's Day",
            "month": 3, "day": 17,
            "hook": "Luck is what happens when preparation meets opportunity.",
            "category": "cultural",
            "region": "United Kingdom",
        },
        {
            "name": "Spring Bank Holiday",
            "dates": {2025: (5, 26), 2026: (5, 25), 2027: (5, 31), 2028: (5, 29)},
            "hook": "Mid-spring momentum: refresh your narrative for Q2 execution.",
            "category": "cultural",
            "region": "United Kingdom",
        },
        {
            "name": "Guy Fawkes Night / Bonfire Night",
            "month": 11, "day": 5,
            "hook": "Sparking new ideas: ignite high-impact campaigns this autumn.",
            "category": "cultural",
            "region": "United Kingdom",
        },
        {
            "name": "Boxing Day Commerce",
            "month": 12, "day": 26,
            "hook": "The final consumer sprint of the year: close out with decisive value.",
            "category": "commerce",
            "region": "United Kingdom",
        },
    ],
    "uae": [
        {
            "name": "UAE National Day",
            "month": 12, "day": 2,
            "hook": "Celebrating visionary leadership and the spirit of union and innovation.",
            "category": "national",
            "region": "UAE",
        },
        {
            "name": "Saudi National Day",
            "month": 9, "day": 23,
            "hook": "Ambition and Vision 2030: pioneering transformation across the region.",
            "category": "national",
            "region": "Middle East",
        },
        {
            "name": "Ramadan Season",
            "dates": {2025: (3, 1), 2026: (2, 18), 2027: (2, 8), 2028: (1, 28)},
            "hook": "A month of reflection, generosity, and purposeful storytelling.",
            "category": "cultural",
            "region": "Middle East",
        },
        {
            "name": "Eid al-Fitr",
            "dates": {2025: (3, 31), 2026: (3, 20), 2027: (3, 10), 2028: (2, 27)},
            "hook": "Eid Mubarak: celebrating connection, gratitude, and shared milestones.",
            "category": "cultural",
            "region": "Middle East",
        },
    ],
}

_COUNTRY_ALIAS_MAP: Dict[str, str] = {
    "in": "india",
    "ind": "india",
    "india": "india",
    "bharat": "india",
    "us": "us",
    "usa": "us",
    "united states": "us",
    "united states of america": "us",
    "america": "us",
    "uk": "uk",
    "gb": "uk",
    "great britain": "uk",
    "united kingdom": "uk",
    "england": "uk",
    "uae": "uae",
    "united arab emirates": "uae",
    "dubai": "uae",
    "saudi arabia": "uae",
    "middle east": "uae",
}

# Industry-specific bonus hooks (applied by tag matching)
_INDUSTRY_HOOKS: Dict[str, List[str]] = {
    "fintech": [
        "The future of finance is programmable. Are you building for it?",
        "When data meets decision-making, the best finance teams win.",
    ],
    "saas": [
        "The best SaaS products solve real problems, not hypothetical ones.",
        "Churn is a product problem. Retention is a culture problem.",
    ],
    "health": [
        "Healthcare innovation starts with the people closest to care.",
        "The best health outcomes start with the best information.",
    ],
    "retail": [
        "Every touchpoint is an opportunity to earn trust.",
        "Great retail isn't about discounts — it's about experience.",
    ],
    "education": [
        "The best learners build the best companies.",
        "Continuous learning is the only durable competitive advantage.",
    ],
    "technology": [
        "Technology is only transformative when humans trust it.",
        "The best products disappear into workflows — they just work.",
    ],
    "real estate": [
        "Location is data. Great decisions are data-driven.",
        "The property market rewards speed and insight in equal measure.",
    ],
}


class CalendarEngine:
    """Provides upcoming marketing hooks from global + regional calendar and agentic discovery."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def get_target_regions(self) -> List[str]:
        """Inspect BusinessProfile to extract canonical target regions (e.g. 'india', 'us')."""
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
            detected: List[str] = []

            # Parse string or list
            if isinstance(raw_countries, str):
                import json
                try:
                    parsed = json.loads(raw_countries)
                    if isinstance(parsed, list):
                        raw_countries = parsed
                    else:
                        raw_countries = [c.strip() for c in raw_countries.replace(";", ",").split(",") if c.strip()]
                except Exception:
                    raw_countries = [c.strip() for c in raw_countries.replace(";", ",").split(",") if c.strip()]
            elif not isinstance(raw_countries, list):
                raw_countries = []

            for c in raw_countries:
                canonical = _COUNTRY_ALIAS_MAP.get(str(c).strip().lower())
                if canonical and canonical not in detected:
                    detected.append(canonical)

            # Fallback inspection of extra_context, service_description, or company_name
            if not detected:
                haystack = f"{profile.company_name or ''} {profile.service_description or ''} {profile.extra_context or ''}".lower()
                for alias, canonical in _COUNTRY_ALIAS_MAP.items():
                    if alias in haystack and canonical not in detected:
                        detected.append(canonical)

            return detected
        except Exception as exc:
            logger.debug(f"[CalendarEngine] Target region inspection failed: {exc}")
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
                import json
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
                            # Handle ISO timestamp
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
        days_ahead: int = 7,
        industry: Optional[str] = None,
        target_regions: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Return upcoming calendar events with marketing hook suggestions across global and regional calendars."""
        today = date.today()
        window_end = today + timedelta(days=days_ahead)
        events: List[Dict[str, Any]] = []
        seen_keys: set = set()

        def _add_event(candidate: date, name: str, hook: str, category: str, source: str, region: Optional[str] = None):
            dedup_key = (name.lower().strip(), candidate.isoformat())
            if dedup_key in seen_keys:
                return
            seen_keys.add(dedup_key)
            days_away = (candidate - today).days
            evt = {
                "date": candidate.isoformat(),
                "name": name,
                "hook": hook,
                "category": category,
                "days_away": days_away,
                "days_until": days_away,
                "source": source,
            }
            if region:
                evt["region"] = region
            events.append(evt)

        # 1. Global evergreen calendar
        for entry in _GLOBAL_CALENDAR:
            try:
                candidate = date(today.year, entry["month"], entry["day"])
                if candidate < today:
                    candidate = date(today.year + 1, entry["month"], entry["day"])
                if today <= candidate <= window_end:
                    _add_event(
                        candidate=candidate,
                        name=entry["name"],
                        hook=entry["hook"],
                        category=entry.get("category", "general"),
                        source="global_calendar",
                        region="Global",
                    )
            except ValueError:
                continue

        # 2. Regional / Cultural calendars (Country/Locale-Aware)
        regions_to_scan = target_regions if target_regions is not None else self.get_target_regions()
        for reg in regions_to_scan:
            reg_entries = _REGIONAL_CALENDARS.get(reg.lower(), [])
            for entry in reg_entries:
                candidate = None
                # Check for year-specific lunisolar dates
                if "dates" in entry and isinstance(entry["dates"], dict):
                    if today.year in entry["dates"]:
                        m, d = entry["dates"][today.year]
                        cand = date(today.year, m, d)
                        if cand >= today:
                            candidate = cand
                        elif (today.year + 1) in entry["dates"]:
                            m_next, d_next = entry["dates"][today.year + 1]
                            candidate = date(today.year + 1, m_next, d_next)
                # Check for fixed solar dates
                elif "month" in entry and "day" in entry:
                    try:
                        cand = date(today.year, entry["month"], entry["day"])
                        if cand < today:
                            cand = date(today.year + 1, entry["month"], entry["day"])
                        candidate = cand
                    except ValueError:
                        continue

                if candidate and today <= candidate <= window_end:
                    _add_event(
                        candidate=candidate,
                        name=entry["name"],
                        hook=entry["hook"],
                        category=entry.get("category", "cultural"),
                        source="regional_calendar",
                        region=entry.get("region", reg.capitalize()),
                    )

        # 3. Add industry-specific bonus hooks for events already detected
        if industry and events:
            industry_lower = industry.lower()
            extra_hooks = []
            for key, hooks in _INDUSTRY_HOOKS.items():
                if key in industry_lower:
                    extra_hooks = hooks
                    break
            if extra_hooks:
                events[0]["bonus_hook"] = extra_hooks[0]

        # 4. Add custom & agentic-discovered events from BusinessProfile.calendars
        custom_events = self._get_custom_events(today, window_end)
        for ce in custom_events:
            try:
                ce_date = date.fromisoformat(ce["date"])
                _add_event(
                    candidate=ce_date,
                    name=ce["name"],
                    hook=ce["hook"],
                    category=ce.get("category", "custom"),
                    source=ce.get("source", "tenant_calendar"),
                    region=ce.get("region"),
                )
            except Exception:
                continue

        # Sort by date ascending
        events.sort(key=lambda e: e["date"])
        return events

    def get_industry_hooks(self, industry: str) -> List[str]:
        """Return evergreen industry-specific creative hooks."""
        industry_lower = industry.lower()
        for key, hooks in _INDUSTRY_HOOKS.items():
            if key in industry_lower:
                return hooks
        return _INDUSTRY_HOOKS.get("technology", [])

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
                import json
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
                        "hook": entry.get("hook") or entry.get("description") or "An important milestone for our brand.",
                        "category": entry.get("category", "custom"),
                        "days_away": (evt_date - today).days,
                        "days_until": (evt_date - today).days,
                        "source": entry.get("source", "tenant_calendar"),
                        "region": entry.get("region"),
                    })
            return events
        except Exception as exc:
            logger.debug(f"[CalendarEngine] Could not load custom events: {exc}")
            return []

    # ------------------------------------------------------------------------ #
    # Agentic Live Context Search (Autonomous Discovery)
    # ------------------------------------------------------------------------ #

    async def discover_agentic_regional_events(
        self,
        target_region: Optional[str] = None,
        days_ahead: int = 30,
        force_refresh: bool = False,
        brand_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run agentic live search/LLM synthesis for upcoming cultural, seasonal,
        and commercial moments in target region for the next 30 days.

        Saves discovered events with tailored hooks to BusinessProfile.calendars
        with a 30-day freshness timestamp so manual maintenance is eliminated.
        """
        try:
            from app.models.verticals import BusinessProfile
            profile = (
                self.db.query(BusinessProfile)
                .filter(BusinessProfile.tenant_id == self.tenant_id)
                .first()
            )
            if not profile:
                return []

            # 1. Resolve Target Region
            region_key = target_region.lower() if target_region else None
            if not region_key:
                regions = self.get_target_regions()
                region_key = regions[0] if regions else "india"

            region_display_map = {"india": "India", "us": "United States", "uk": "United Kingdom", "uae": "UAE & Middle East"}
            region_display = region_display_map.get(region_key, region_key.capitalize())

            # 2. Check 30-day cache in BusinessProfile.calendars
            if not force_refresh and self.has_recent_agentic_events(max_age_days=30):
                today = date.today()
                window_end = today + timedelta(days=days_ahead)
                return self._get_custom_events(today, window_end)

            today = date.today()
            end_date = today + timedelta(days=days_ahead)

            company_name = (brand_context or {}).get("company_name") or profile.company_name or "Brand"
            industry = (brand_context or {}).get("industry") or profile.industry or "Technology"
            usp = (brand_context or {}).get("usp") or profile.usp or ""

            # 3. Web Search for Real-World Seasonal Moments
            search_snippets = ""
            search_query = f"major upcoming cultural festivals seasonal commercial events in {region_display} {today.strftime('%B %Y')}"
            try:
                from app.services.agents.tools import AgentTools
                tools = AgentTools()
                search_res = await tools._exec_web_search({"query": search_query}, self.db, self.tenant_id)
                results = search_res.get("results", [])
                if results:
                    search_snippets = "\n".join([f"- {r.get('title')}: {r.get('snippet')}" for r in results[:4]])
            except Exception as search_err:
                logger.debug(f"[CalendarEngine] Search fallback: {search_err}")

            # 4. LLM Extraction & Tailored Hook Synthesis
            prompt = (
                f"Identify major upcoming cultural, seasonal, and commercial moments in {region_display} "
                f"for the next 30 days between {today.isoformat()} and {end_date.isoformat()}.\n\n"
                f"Region: {region_display}\n"
                f"Brand Context: {company_name} ({industry})\n"
                f"Brand USP: {usp}\n"
                f"{f'Web Search Context:\n{search_snippets}\n' if search_snippets else ''}\n"
                f"Generate high-converting marketing hooks connecting each moment to brand innovation, trust, and growth.\n"
                f"Output strictly a valid JSON array of objects with keys:\n"
                f'- "name": Event or festival name (e.g. "Navratri & Durga Puja", "Dussehra", "Cybersecurity Awareness Month")\n'
                f'- "date": Valid ISO date "YYYY-MM-DD" between {today.isoformat()} and {end_date.isoformat()}\n'
                f'- "hook": Compelling 1-2 sentence marketing hook\n'
                f'- "category": One of "cultural", "commerce", "awareness", "tech", "national", "business"\n'
                f'- "region": "{region_display}"\n'
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
                    import json
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
                                        "region": region_display,
                                        "source": "agentic_radar",
                                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                                    })
                            except ValueError:
                                continue
            except Exception as llm_err:
                logger.debug(f"[CalendarEngine] LLM extraction fallback: {llm_err}")

            # 5. Graceful fallback to curated regional dates if LLM produced no items
            if not discovered_events:
                reg_curated = _REGIONAL_CALENDARS.get(region_key, [])
                for entry in reg_curated:
                    candidate = None
                    if "dates" in entry and today.year in entry["dates"]:
                        m, d = entry["dates"][today.year]
                        candidate = date(today.year, m, d)
                    elif "month" in entry and "day" in entry:
                        try:
                            candidate = date(today.year, entry["month"], entry["day"])
                        except ValueError:
                            pass
                    if candidate and today <= candidate <= end_date:
                        discovered_events.append({
                            "name": entry["name"],
                            "date": candidate.isoformat(),
                            "hook": entry["hook"],
                            "category": entry.get("category", "cultural"),
                            "region": entry.get("region", region_display),
                            "source": "agentic_radar",
                            "discovered_at": datetime.now(timezone.utc).isoformat(),
                        })

            # 6. Persist to BusinessProfile.calendars (retaining user custom events)
            existing_cals = profile.calendars or []
            if isinstance(existing_cals, str):
                import json
                try:
                    existing_cals = json.loads(existing_cals)
                except Exception:
                    existing_cals = []
            if not isinstance(existing_cals, list):
                existing_cals = []

            # Retain non-agentic custom events
            retained = [c for c in existing_cals if isinstance(c, dict) and c.get("source") != "agentic_radar"]
            updated = retained + discovered_events

            profile.calendars = updated
            self.db.add(profile)
            self.db.commit()

            return discovered_events
        except Exception as exc:
            logger.error(f"[CalendarEngine] Agentic regional discovery failed: {exc}")
            return []

