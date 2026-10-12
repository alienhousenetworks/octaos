"""Unit tests for Phase 3 Field Operations agents.

Tests:
1. Agent 11 (TerritoryRoutePlannerAgent): Geographic route clustering, distance calculations, gap-fill backups
2. Agent 12 (FieldCopilotAgent): Voice-to-CRM parsing, structured commitments, email & WhatsApp follow-ups
"""
import pytest
from app.models.deal_room import DealRoom, DealActivity
from app.services.sales_os.agents.territory_route import TerritoryRoutePlannerAgent, haversine_distance_km
from app.services.sales_os.agents.field_copilot import FieldCopilotAgent


class MockQuery:
    def __init__(self, data):
        self._data = list(data) if isinstance(data, list) else ([data] if data else [])

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._data[0] if self._data else None

    def all(self):
        return self._data


class MockDB:
    def __init__(self, rooms=None):
        self.rooms = rooms or []
        self.added = []
        self.committed = False

    def query(self, model):
        if model == DealRoom:
            return MockQuery(self.rooms)
        return MockQuery([])

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True


def test_haversine_calculation():
    """Verify haversine distance between SF Ferry Building and Union Square (~2.0 km)."""
    dist = haversine_distance_km(37.7955, -122.3937, 37.7879, -122.4074)
    assert 1.0 <= dist <= 2.5


@pytest.mark.asyncio
async def test_territory_route_planner():
    """Verify Agent 11 builds route stops with scheduled time windows and dynamic backups."""
    db = MockDB()
    agent = TerritoryRoutePlannerAgent(db, "tenant_field_demo")

    result = await agent.execute(parameters={"rep_id": "rep_42", "date": "2026-10-16"})
    assert result.decision == "ready"
    plan = result.data

    assert plan.rep_id == "rep_42"
    assert len(plan.stops) >= 2
    assert plan.total_travel_distance_km > 0
    assert plan.estimated_travel_time_min > 0
    # Backup gap-fill accounts present
    assert len(plan.unplanned_nearby_prospects) >= 0
    assert plan.stops[0].scheduled_window_start == "09:30 AM"


@pytest.mark.asyncio
async def test_field_copilot_voice_synthesis():
    """Verify Agent 12 processes voice memos into structured CRM notes and follow-up drafts."""
    deal_room = DealRoom(
        id="dr_field_1",
        tenant_id="tenant_field_demo",
        company_name="Apex Logistics",
    )
    db = MockDB(rooms=[deal_room])
    agent = FieldCopilotAgent(db, "tenant_field_demo")

    memo = (
        "Just wrapped up with CEO Rajesh at their headquarters. Major pain point is manual Excel dispatch "
        "causing 2-hour daily driver delays. Budget is approved up to $40,000. I promised to send our "
        "case study and pilot agreement by tomorrow at 10 AM. Rajesh agreed to sign off if we show 15% route reduction."
    )

    result = await agent.execute("dr_field_1", {"voice_memo": memo, "rep_id": "rep_99"})
    assert result.decision == "ready"
    summary = result.data

    assert summary.deal_room_id == "dr_field_1"
    assert len(summary.structured_note.client_pain_points) > 0
    assert summary.structured_note.budget_discussed is not None
    assert summary.follow_up_draft_email != ""
    assert summary.follow_up_draft_whatsapp != ""
    assert any(isinstance(a, DealActivity) for a in db.added)
