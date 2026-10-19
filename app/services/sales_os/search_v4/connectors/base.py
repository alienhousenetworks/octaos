"""Provider calls return a status. They do not invent companies or contacts."""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Hit:
    url: str
    title: str = ""
    snippet: str = ""
    page_excerpt: str = ""
    published_at: datetime | None = None
    provider_native_id: str | None = None
    company_name: str = ""
    company_domain: str | None = None
    contact_name: str = ""
    contact_email: str = ""


@dataclass
class ConnectorResult:
    status: str
    reason: str = ""
    failure_class: str | None = None
    hits: list[Hit] = field(default_factory=list)
    actual_cost_inr: float = 0.0
    billable: bool = False


def failure_from_status(status: int) -> tuple[str, str]:
    if status in (401, 403):
        return "permission", "The provider denied access."
    if status in (400, 422):
        return "invalid", f"The provider rejected the query with HTTP {status}."
    if status == 429 or status >= 500:
        return "transient", f"The provider returned HTTP {status}."
    return "provider", f"The provider returned HTTP {status}."
