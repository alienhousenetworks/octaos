import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base, Tenant
from app.models.automations import AutomationExecution, AutomationWorkflow
from app.services.automation import event_bridge as bridge_module
from app.services.automation.event_bridge import AutomationEventBridge


class FakeAutomationAdapter:
    def __init__(self):
        self.calls = []

    async def trigger_workflow_manually(self, tenant_id, external_id, payload):
        self.calls.append({"tenant_id": tenant_id, "external_id": external_id, "payload": payload})
        return {"execution_id": f"external-{len(self.calls)}", "outputs": {"ok": True}}


def test_event_bridge_is_tenant_scoped_and_deduplicates_sequential_delivery(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        db.add_all([
            Tenant(id="tenant-a", name="Tenant A"),
            Tenant(id="tenant-b", name="Tenant B"),
        ])
        db.flush()
        db.add_all([
            AutomationWorkflow(
                id="workflow-a", tenant_id="tenant-a", name="A", slug="a",
                category="operations", status="active", trigger_type="octaos_event",
                trigger_event="lead.qualified", definition_ir={}, compiled_schema={},
                external_flow_id="external-a",
            ),
            AutomationWorkflow(
                id="workflow-b", tenant_id="tenant-b", name="B", slug="b",
                category="operations", status="active", trigger_type="octaos_event",
                trigger_event="lead.qualified", definition_ir={}, compiled_schema={},
                external_flow_id="external-b",
            ),
        ])
        db.commit()

        adapter = FakeAutomationAdapter()
        monkeypatch.setattr(bridge_module, "get_automation_engine", lambda tenant_id, db: adapter)
        bridge = AutomationEventBridge(db, "tenant-a")

        first = asyncio.run(bridge.dispatch_event(
            "lead.qualified", {"lead_ref": "lead-123"}, idempotency_key="provider-event-001"
        ))
        second = asyncio.run(bridge.dispatch_event(
            "lead.qualified", {"lead_ref": "lead-123"}, idempotency_key="provider-event-001"
        ))

        assert len(first) == 1
        assert first[0]["workflow_id"] == "workflow-a"
        assert len(second) == 1
        assert second[0]["deduplicated"] is True
        assert len(adapter.calls) == 1
        assert db.query(AutomationExecution).filter_by(tenant_id="tenant-b").count() == 0
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
