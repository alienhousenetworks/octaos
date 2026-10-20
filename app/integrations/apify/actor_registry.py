"""Approved Actor Registry for OctaOS.
Enforces that AI agents cannot call arbitrary or unapproved scraping targets.
"""
from typing import Dict, List, Optional
from app.integrations.apify.schemas import (
    ActorCapability,
    ActorPricingModel,
    ApprovedActorDefinition,
)

_APPROVED_ACTORS: Dict[str, ApprovedActorDefinition] = {
    "company_discovery": ApprovedActorDefinition(
        actor_key="company_discovery",
        actor_id="compass/crawler-google-places",
        name="Google Places B2B & Local Business Discovery",
        description="Extracts verified public business profiles, domain websites, categories, addresses, and phone numbers.",
        capabilities=[ActorCapability.ACCOUNT_DISCOVERY],
        default_max_charge_usd=2.00,
        default_timeout_seconds=300,
        pricing_model=ActorPricingModel.USAGE_BASED,
        input_schema_template={
            "searchStringsArray": ["string"],
            "maxCrawledPlacesPerSearch": 25,
            "language": "en",
        },
    ),
    "market_news": ApprovedActorDefinition(
        actor_key="market_news",
        actor_id="apify/google-search-scraper",
        name="Google Search & News Intelligence Scraper",
        description="Collects public search snippets, news, industry trends, and announcements for market research.",
        capabilities=[ActorCapability.MARKET_RESEARCH, ActorCapability.SIGNAL_COLLECTION],
        default_max_charge_usd=1.00,
        default_timeout_seconds=180,
        pricing_model=ActorPricingModel.USAGE_BASED,
        input_schema_template={
            "queries": "string",
            "maxPagesPerQuery": 1,
            "resultsPerPage": 10,
            "countryCode": "us",
            "languageCode": "en",
        },
    ),
    "website_intelligence": ApprovedActorDefinition(
        actor_key="website_intelligence",
        actor_id="apify/website-content-crawler",
        name="Website Content & Signal Crawler",
        description="Crawls public corporate websites to identify buying signals, product updates, tech stack, and about pages.",
        capabilities=[ActorCapability.SIGNAL_COLLECTION, ActorCapability.CONTENT_CRAWL],
        default_max_charge_usd=2.50,
        default_timeout_seconds=300,
        pricing_model=ActorPricingModel.USAGE_BASED,
        input_schema_template={
            "startUrls": [{"url": "string"}],
            "maxCrawlPages": 5,
            "crawlerType": "cheerio",
        },
    ),
    "b2b_prospect_research": ApprovedActorDefinition(
        actor_key="b2b_prospect_research",
        actor_id="apify/google-maps-scraper",
        name="Google Maps B2B Lead Scraper",
        description="Alternative B2B lead discovery tool for finding companies, phone contacts, domains, and locations.",
        capabilities=[ActorCapability.ACCOUNT_DISCOVERY, ActorCapability.SIGNAL_COLLECTION],
        default_max_charge_usd=2.00,
        default_timeout_seconds=300,
        pricing_model=ActorPricingModel.USAGE_BASED,
        input_schema_template={
            "searchStringsArray": ["string"],
            "maxCrawledPlaces": 25,
        },
    ),
}


class ActorRegistry:
    @staticmethod
    def get(actor_key: str) -> Optional[ApprovedActorDefinition]:
        actor = _APPROVED_ACTORS.get(actor_key)
        if actor and actor.enabled:
            return actor
        return None

    @staticmethod
    def get_by_actor_id(actor_id: str) -> Optional[ApprovedActorDefinition]:
        for actor in _APPROVED_ACTORS.values():
            if actor.actor_id == actor_id and actor.enabled:
                return actor
        return None

    @staticmethod
    def list(capability: Optional[ActorCapability] = None) -> List[ApprovedActorDefinition]:
        results = [a for a in _APPROVED_ACTORS.values() if a.enabled]
        if capability:
            results = [a for a in results if capability in a.capabilities]
        return results

    @staticmethod
    def register(definition: ApprovedActorDefinition) -> None:
        _APPROVED_ACTORS[definition.actor_key] = definition

    @staticmethod
    def validate_and_build_input(actor_key: str, raw_input: dict) -> dict:
        actor = ActorRegistry.get(actor_key)
        if not actor:
            raise ValueError(f"Actor '{actor_key}' is not approved in the OctaOS registry.")

        # Sanitize and apply default bounded limits
        cleaned = dict(raw_input)
        if actor.actor_key in {"company_discovery", "b2b_prospect_research"}:
            # Ensure query or searchStringsArray exists
            if "searchStringsArray" not in cleaned:
                query = cleaned.pop("query", None) or cleaned.pop("search", None)
                if query:
                    cleaned["searchStringsArray"] = [str(query)]
                else:
                    cleaned["searchStringsArray"] = ["software companies"]
            # Enforce max places ceiling
            limit = int(cleaned.get("maxCrawledPlacesPerSearch") or cleaned.get("maxCrawledPlaces") or 25)
            cleaned["maxCrawledPlacesPerSearch"] = min(limit, 50)
            cleaned["maxCrawledPlaces"] = min(limit, 50)

        elif actor.actor_key == "market_news":
            query = cleaned.get("queries") or cleaned.get("query") or cleaned.get("search")
            if not query:
                query = "AI SaaS enterprise news 2026"
            cleaned["queries"] = str(query)
            cleaned["maxPagesPerQuery"] = min(int(cleaned.get("maxPagesPerQuery", 1)), 2)
            cleaned["resultsPerPage"] = min(int(cleaned.get("resultsPerPage", 10)), 20)

        elif actor.actor_key == "website_intelligence":
            start_urls = cleaned.get("startUrls")
            if not start_urls:
                url = cleaned.get("url") or cleaned.get("website")
                if url:
                    start_urls = [{"url": str(url) if str(url).startswith("http") else f"https://{url}"}]
                else:
                    start_urls = []
            cleaned["startUrls"] = start_urls
            cleaned["maxCrawlPages"] = min(int(cleaned.get("maxCrawlPages", 5)), 10)

        return cleaned
