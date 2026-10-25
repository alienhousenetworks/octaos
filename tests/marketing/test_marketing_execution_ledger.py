import pytest

from app.models.verticals import MarketingExecution, MarketingExecutionStep
from app.services.marketing.autonomy.execution_ledger import MarketingExecutionLedger


class Query:
    def __init__(self, rows=None):
        # A query owns its result set; filtering/limiting must not mutate FakeDB.
        self.rows = list(rows or [])

    def filter_by(self, **kwargs):
        self.rows = [
            row for row in self.rows
            if all(getattr(row, key, None) == value for key, value in kwargs.items())
        ]
        return self

    def with_for_update(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def order_by(self, *args):
        return self

    def limit(self, n):
        self.rows = self.rows[:n]
        return self

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self):
        self.rows = {MarketingExecution: [], MarketingExecutionStep: []}
        self.added = []

    def query(self, model):
        return Query(self.rows[model])

    def add(self, obj):
        self.added.append(obj)
        self.rows[type(obj)].append(obj)

    def commit(self):
        pass

    def refresh(self, obj):
        pass

    def rollback(self):
        pass


def test_execution_is_tenant_scoped_and_payload_hashed():
    db = FakeDB()
    ledger = MarketingExecutionLedger(db, "tenant-A")
    run = ledger.start_or_resume("campaign", "request-1", {"topic": "launch"})
    assert run.tenant_id == "tenant-A"
    assert len(run.request_hash) == 64
    assert run.status == "running"
    assert run.attempts == 1


def test_same_idempotency_key_cannot_be_reused_for_different_payload():
    db = FakeDB()
    ledger = MarketingExecutionLedger(db, "tenant-A")
    run = ledger.start_or_resume("campaign", "request-1", {"topic": "launch"})
    # The second query sees the persisted row.
    with pytest.raises(ValueError, match="different request"):
        ledger.start_or_resume("campaign", "request-1", {"topic": "discount"})


def test_step_history_and_completion_are_persisted():
    db = FakeDB()
    ledger = MarketingExecutionLedger(db, "tenant-A")
    run = ledger.start_or_resume("campaign", "request-1", {"topic": "launch"})
    step = ledger.begin_step(run.id, "strategy", {"topic": "launch"})
    assert step.status == "running"
    ledger.finish_step(run.id, "strategy", output_payload={"summary": "draft"})
    assert step.status == "completed"
    ledger.complete(run.id, {"status": "success"})
    assert run.status == "completed"
    assert run.result_payload["status"] == "success"


def test_run_and_step_history_queries_are_tenant_scoped():
    db = FakeDB()
    ledger = MarketingExecutionLedger(db, "tenant-A")
    run = ledger.start_or_resume("campaign", "request-1", {"topic": "launch"})
    ledger.begin_step(run.id, "strategy", {"topic": "launch"})
    assert [item.id for item in ledger.list_recent(limit=10)] == [run.id]
    assert len(ledger.list_steps(run.id)) == 1
    with pytest.raises(LookupError, match="not found for this tenant"):
        MarketingExecutionLedger(db, "tenant-B").list_steps(run.id)


def test_execution_cannot_be_loaded_across_tenants():
    db = FakeDB()
    run = MarketingExecution(
        id="r1", tenant_id="tenant-B", workflow_type="campaign",
        idempotency_key="k", request_hash="x", status="running", attempts=1,
    )
    db.rows[MarketingExecution] = [run]
    assert MarketingExecutionLedger(db, "tenant-A").get("r1") is None
