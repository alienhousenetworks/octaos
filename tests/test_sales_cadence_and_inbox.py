"""Hermetic tests for Phase 2: Durable Cadence Runner and Omnichannel Unified Sales Inbox."""
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base, Tenant, User
from app.models.verticals import Lead
from app.models.deal_room import DealRoom, SalesOutboxItem
from app.models.agent_runtime import AgentRun, AgentTask
from app.services.sales.cadence_runner import DurableCadenceRunner


@pytest.fixture
def runtime_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    tenant = Tenant(id="test_inbox_tenant", name="Test Inbox Tenant", subdomain="inbox-test", is_active=True)
    session.add(tenant)
    session.commit()

    lead = Lead(
        id="lead_elena_123",
        tenant_id="test_inbox_tenant",
        name="Elena Rostova",
        email="elena.rostova@cloudscale.ai",
        phone="+14155552671",
        company="CloudScale AI",
        source="apollo",
        status="contacted",
        data={
            "outreach_sent_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
            "outreach_schedule": [
                {"day": 1, "channel": "Email", "content": "Day 1 intro email", "status": "sent"},
                {"day": 3, "channel": "LinkedIn", "content": "Day 3 LinkedIn note", "status": "pending"},
                {"day": 5, "channel": "Email", "content": "Day 5 follow-up email", "status": "pending"},
            ],
            "conversations": [
                {
                    "direction": "outbound",
                    "channel": "email",
                    "subject": "Partnership Opportunity",
                    "content": "Day 1 intro email",
                    "author": "Sales AI Agent",
                    "at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
                }
            ],
        },
    )
    session.add(lead)
    session.commit()

    yield session, tenant, lead
    session.close()


def test_durable_cadence_runner_stats(runtime_db):
    session, tenant, lead = runtime_db
    runner = DurableCadenceRunner(session, tenant.id)
    stats = runner.get_cadence_stats()

    assert stats["tenant_id"] == tenant.id
    assert stats["active_enrolled_leads"] == 1
    assert stats["pending_touches"] == 2
    assert "checked_at" in stats


def test_durable_cadence_runner_halts_on_reply(runtime_db):
    session, tenant, lead = runtime_db
    # Mark lead as replied
    lead.status = "replied"
    lead.data = {
        **lead.data,
        "conversations": [
            *lead.data.get("conversations", []),
            {
                "direction": "inbound",
                "channel": "email",
                "content": "Thanks, let's schedule a call next Tuesday.",
                "author": "Elena Rostova",
                "at": datetime.now(timezone.utc).isoformat(),
            },
        ],
    }
    session.commit()

    runner = DurableCadenceRunner(session, tenant.id)
    res = runner.run_tenant_cadence(max_touches=10)

    assert res["cadences_halted_on_reply"] == 1

    # Verify pending steps were halted
    session.refresh(lead)
    schedule = lead.data.get("outreach_schedule", [])
    for step in schedule:
        if step.get("day") in (3, 5):
            assert step.get("status") == "halted_reply_received"


def test_durable_cadence_runner_execution_logging(runtime_db):
    session, tenant, lead = runtime_db
    runner = DurableCadenceRunner(session, tenant.id)
    res = runner.run_tenant_cadence(max_touches=10)

    assert "run_id" in res
    run_record = session.query(AgentRun).filter(AgentRun.id == res["run_id"]).first()
    assert run_record is not None
    assert run_record.agent_id == "agent.cadence_optimizer"
    assert run_record.status == "completed"
