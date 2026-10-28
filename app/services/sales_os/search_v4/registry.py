"""Search methods that run beside the existing lead connectors.

The catalogue connectors (Apollo, Hunter, the open-web lead search, and the
other source ids) stay on the Sales AI provider loop. This registry only
chooses providers for the additional search methods.
"""
from dataclasses import dataclass, field

# Methods implemented by this pipeline. They do not replace catalogue ids.
SEARCH_METHODS = ("web", "news", "jobs", "company", "social_reddit", "social_x")

# Paid web providers. DuckDuckGo remains the free path already used by web_search.
BRAVE_INR = 0.45
TAVILY_INR = 0.80
FIRECRAWL_INR = 0.50

PARALLEL_EXISTING_NOTE = (
    "Existing lead connectors keep running on the Sales AI provider loop. "
    "search_v4 adds web, news, jobs, company-page, and permitted social methods beside them."
)


@dataclass
class ProviderStats:
    samples: dict[str, int] = field(default_factory=dict)
    qualified: dict[str, int] = field(default_factory=dict)

    def sample(self, provider: str) -> int:
        return int(self.samples.get(provider) or 0)

    def yield_of(self, provider: str) -> float:
        sample = self.sample(provider)
        if sample <= 0:
            return 0.0
        return float(self.qualified.get(provider) or 0) / sample


@dataclass
class ProviderHealth:
    failures: dict[str, int] = field(default_factory=dict)

    def allows(self, provider: str) -> bool:
        return self.failures.get(provider, 0) < 3

    def record_failure(self, provider: str) -> None:
        self.failures[provider] = self.failures.get(provider, 0) + 1

    def record_success(self, provider: str) -> None:
        self.failures[provider] = 0


def web_cost(provider: str) -> float:
    if provider == "brave":
        return BRAVE_INR
    if provider == "tavily":
        return TAVILY_INR
    if provider == "firecrawl":
        return FIRECRAWL_INR
    return 0.0


def choose_web_provider(
    credentials: dict[str, str],
    stats: ProviderStats,
    health: ProviderHealth,
) -> tuple[str, str, float]:
    """Deterministic provider choice. The planner does not pick from an LLM opinion."""
    options: list[tuple[str, float]] = []
    if credentials.get("brave_search") and health.allows("brave"):
        options.append(("brave", BRAVE_INR))
    if credentials.get("tavily") and health.allows("tavily"):
        options.append(("tavily", TAVILY_INR))
    if credentials.get("firecrawl") and health.allows("firecrawl"):
        options.append(("firecrawl", FIRECRAWL_INR))
    if not options:
        return (
            "duckduckgo",
            "No healthy paid web provider is configured. Using the existing DuckDuckGo search path.",
            0.0,
        )
    cheapest = sorted(options, key=lambda item: item[1])[0]
    for provider, cost in options:
        if provider == cheapest[0]:
            continue
        if (
            stats.sample(provider) >= 3
            and stats.sample(cheapest[0]) >= 3
            and stats.yield_of(provider) >= stats.yield_of(cheapest[0]) * 1.5
            and stats.yield_of(provider) > 0
        ):
            return (
                provider,
                f"{provider} qualified yield is at least 1.5 times {cheapest[0]} across at least 3 measured tasks.",
                cost,
            )
    return (
        cheapest[0],
        f"{cheapest[0]} is the cheapest healthy web provider at INR {cheapest[1]:.2f} per request.",
        cheapest[1],
    )


def credential_map(overrides: dict[str, str] | None = None) -> dict[str, str]:
    """Tenant credentials win. Server env fills only the search providers."""
    import os

    merged = {
        "brave_search": os.getenv("BRAVE_SEARCH_API_KEY") or "",
        "tavily": os.getenv("TAVILY_API_KEY") or "",
        "firecrawl": os.getenv("FIRECRAWL_API_KEY") or "",
        "reddit": os.getenv("REDDIT_CLIENT_CREDENTIALS") or "",
        "x_search": os.getenv("X_BEARER_TOKEN") or "",
    }
    for key, value in (overrides or {}).items():
        if value:
            merged[key] = value
    alias_reddit = merged.get("reddit_intent") or merged.get("reddit")
    if alias_reddit:
        merged["reddit"] = alias_reddit
    alias_x = merged.get("x") or merged.get("x_search")
    if alias_x:
        merged["x_search"] = alias_x
    return {key: value for key, value in merged.items() if value}
