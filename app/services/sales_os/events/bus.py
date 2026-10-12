"""Asynchronous Sales Event Bus for the Autonomous Sales Organization (ASO).

Publishes and routes sales domain events across all 20 agents:
- Inbound replies, email opens, unsubscribes
- Call transcript uploads, proposal requests, redlines
- Field voice note commits, cancellations
- Usage dips, ticket escalations
"""
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Callable, Optional, Awaitable
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SalesEventType(str, Enum):
    # Discovery & Sourcing
    LEAD_DISCOVERED = "lead.discovered"
    SIGNAL_DETECTED = "signal.detected"
    COMMITTEE_MEMBER_ADDED = "committee.member.added"

    # Inbound / Outbound engagement
    PROSPECT_REPLIED = "prospect.replied"
    EMAIL_OPENED = "email.opened"
    LINK_CLICKED = "link.clicked"
    MEETING_SCHEDULED = "meeting.scheduled"
    UNSUBSCRIBE_REQUESTED = "unsubscribe.requested"

    # Account Executive events
    TRANSCRIPT_UPLOADED = "call.transcript.uploaded"
    PROPOSAL_REQUESTED = "proposal.requested"
    CONTRACT_REDLINE_RECEIVED = "contract.redline.received"
    STAGE_CHANGED = "deal.stage.changed"
    DEAL_STALLED = "deal.stalled"

    # Field Rep events
    VOICE_NOTE_SUBMITTED = "field.voice_note.submitted"
    MEETING_CANCELLED = "field.meeting.cancelled"

    # Customer Success / Expansion events
    SUPPORT_TICKET_ESCALATED = "cs.ticket.escalated"
    USAGE_DROPPED = "cs.usage.dropped"


class SalesEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    event_type: SalesEventType
    deal_room_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SalesEventBus:
    """Singleton in-process pub/sub event router for sales operations."""

    def __init__(self, max_history: int = 500):
        self._subscribers: Dict[SalesEventType, List[Callable[[SalesEvent], Awaitable[Any]]]] = {}
        self._global_subscribers: List[Callable[[SalesEvent], Awaitable[Any]]] = []
        self._history: List[SalesEvent] = []
        self._max_history = max_history

    def subscribe(
        self,
        event_type: SalesEventType,
        handler: Callable[[SalesEvent], Awaitable[Any]],
    ) -> None:
        """Register an async handler for a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: Callable[[SalesEvent], Awaitable[Any]]) -> None:
        """Register an async handler for all events (e.g. audit logging)."""
        self._global_subscribers.append(handler)

    async def publish(self, event: SalesEvent) -> List[Any]:
        """Publish an event to all registered subscribers."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        handlers = list(self._subscribers.get(event.event_type, []))
        handlers.extend(self._global_subscribers)

        results = []
        for handler in handlers:
            try:
                res = await handler(event)
                results.append(res)
            except Exception as e:
                logger.error(
                    "Error executing handler %s for event %s: %s",
                    getattr(handler, "__name__", str(handler)),
                    event.event_type,
                    str(e),
                    exc_info=True,
                )
                results.append({"error": str(e)})

        return results

    def get_recent_events(
        self, tenant_id: Optional[str] = None, event_type: Optional[SalesEventType] = None, limit: int = 50
    ) -> List[SalesEvent]:
        """Retrieve recent events filtered by tenant or event type."""
        events = self._history
        if tenant_id:
            events = [e for e in events if e.tenant_id == tenant_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def clear(self) -> None:
        """Clear subscriptions and history (useful for test isolation)."""
        self._subscribers.clear()
        self._global_subscribers.clear()
        self._history.clear()


# Default process-level bus singleton
sales_event_bus = SalesEventBus()
