"""Signal families and default half-lives. Values are configuration, not observed facts."""

SIGNAL_FAMILIES = {
    "funding": {"half_life_days": 45, "types": ["funding_round", "grant", "debt", "acquisition"]},
    "hiring": {"half_life_days": 21, "types": ["job_opening", "hiring_velocity", "department_expansion"]},
    "leadership": {"half_life_days": 30, "types": ["executive_joined", "executive_left", "promotion"]},
    "technographic": {"half_life_days": 30, "types": ["tech_added", "tech_removed", "migration"]},
    "rfp": {"half_life_days": 10, "types": ["tender", "procurement_notice", "rfi", "rfp"]},
    "reviews": {"half_life_days": 14, "types": ["complaint_spike", "competitor_dissatisfaction", "low_rating"]},
    "web_change": {"half_life_days": 14, "types": ["pricing_change", "product_launch", "hiring_page_change", "positioning_change"]},
    "traffic_growth": {"half_life_days": 21, "types": ["traffic_growth", "channel_shift", "search_demand"]},
    "community": {"half_life_days": 7, "types": ["pain_point", "vendor_complaint", "buying_question"]},
    "inbound": {"half_life_days": 7, "types": ["form_submit", "demo_request", "pricing_request", "visitor_identification"]},
    "engagement": {"half_life_days": 7, "types": ["reply", "click", "meeting", "no_show", "re_engagement"]},
    "firmographic": {"half_life_days": 90, "types": ["new_location", "size_change", "industry_change"]},
}

_TYPE_TO_FAMILY = {
    signal_type: family
    for family, spec in SIGNAL_FAMILIES.items()
    for signal_type in spec["types"]
}


def family_for(signal_type: str) -> str:
    if signal_type in SIGNAL_FAMILIES:
        return signal_type
    return _TYPE_TO_FAMILY.get(signal_type, "")


def half_life_for(signal_type: str, override: int | None = None) -> int | None:
    if override is not None:
        return override
    family = family_for(signal_type)
    if not family:
        return None
    return SIGNAL_FAMILIES[family]["half_life_days"]
