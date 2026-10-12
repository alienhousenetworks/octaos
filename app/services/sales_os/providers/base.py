"""Connector contract. Adapters return envelopes and never fill unknown contact fields."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


@dataclass
class AccountCandidate:
    display_name: str | None = None
    canonical_domain: str | None = None
    website: str | None = None
    industry: str | None = None
    employee_count: int | None = None
    hq_country: str | None = None
    hq_city: str | None = None
    confidence: float | None = None
    external_id: str | None = None


@dataclass
class ContactCandidate:
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    department: str | None = None
    linkedin_url: str | None = None
    provider_id: str | None = None
    confidence: float | None = None
    company_domain: str | None = None
    company_name: str | None = None


@dataclass
class RawSignal:
    signal_type: str
    summary: str | None
    source_url: str | None = None
    observed_at: datetime | None = None
    base_strength: float | None = None
    source_confidence: float | None = None
    payload: dict = field(default_factory=dict)
    independent_key: str | None = None
    excerpt: str | None = None


@dataclass
class ConnectorEnvelope:
    provider_key: str
    request_id: str
    status: str
    reason: str | None = None
    accounts: list[AccountCandidate] = field(default_factory=list)
    contacts: list[ContactCandidate] = field(default_factory=list)
    signals: list[RawSignal] = field(default_factory=list)
    estimated_cost: float | None = None
    actual_cost: float | None = None
    credits: float | None = None
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    license_class: str | None = None
    http_status: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider_key": self.provider_key,
            "request_id": self.request_id,
            "status": self.status,
            "reason": self.reason,
            "accounts": [item.__dict__ for item in self.accounts],
            "contacts": [item.__dict__ for item in self.contacts],
            "signals": [
                {
                    "signal_type": item.signal_type,
                    "summary": item.summary,
                    "source_url": item.source_url,
                    "observed_at": item.observed_at.isoformat() if item.observed_at else None,
                    "base_strength": item.base_strength,
                    "source_confidence": item.source_confidence,
                    "independent_key": item.independent_key,
                }
                for item in self.signals
            ],
            "estimated_cost": self.estimated_cost,
            "actual_cost": self.actual_cost,
            "credits": self.credits,
            "retrieved_at": self.retrieved_at.isoformat(),
            "license_class": self.license_class,
            "http_status": self.http_status,
        }


class ConnectorUnavailable(Exception):
    def __init__(self, provider: str, reason: str):
        self.provider = provider
        self.reason = reason
        super().__init__(f"{provider} is unavailable: {reason}")


def empty_envelope(provider_key: str, status: str, reason: str, estimated_cost: float | None = None) -> ConnectorEnvelope:
    return ConnectorEnvelope(
        provider_key=provider_key,
        request_id=str(uuid.uuid4()),
        status=status,
        reason=reason,
        estimated_cost=estimated_cost,
    )


class ProviderAdapter(Protocol):
    provider_key: str
    paid: bool

    def capabilities(self) -> set[str]:
        ...

    def health(self, has_credentials: bool) -> dict:
        ...

    async def discover_accounts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        ...

    async def discover_contacts(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        ...

    async def fetch_signals(self, query: str, api_key: str | None, count: int = 5) -> ConnectorEnvelope:
        ...

    def estimate_cost(self, operation: str) -> float | None:
        ...
