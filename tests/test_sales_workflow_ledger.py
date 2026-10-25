"""Durable Sales AI lifecycle invariants: tenant isolation, idempotency, safe retries."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, Tenant
from app.models.sales_workflow import SalesWorkflowRun, SalesWorkflowStep
from app.services.sales_os.workflow_ledger import (
    WorkflowConflict, create_or_get_run, get_run, record_step,
    transition_run, transition_step,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all([Tenant(id="tenant-a", name="A"), Tenant(id="tenant-b", name="B")])
    session.commit()
    yield session
    session.close()
    engine.dispose()


def test_run_creation_is_idempotent_within_tenant(db):
    one = create_or_get_run(db, tenant_id="tenant-a", campaign_id="c1", idempotency_key="request-1", input_payload={"query": "crm"})
    two = create_or_get_run(db, tenant_id="tenant-a", campaign_id="c1", idempotency_key="request-1", input_payload={"query": "different"})
    assert one.id == two.id
    assert two.input_payload == {"query": "crm"}


def test_tenant_cannot_read_another_tenants_run(db):
    run = create_or_get_run(db, tenant_id="tenant-a", campaign_id="c1", idempotency_key="request-1", input_payload={})
    assert get_run(db, tenant_id="tenant-b", run_id=run.id) is None


def test_run_state_machine_blocks_invalid_terminal_transition(db):
    run = create_or_get_run(db, tenant_id="tenant-a", campaign_id="c1", idempotency_key="request-1", input_payload={})
    transition_run(db, tenant_id="tenant-a", run_id=run.id, status="running")
    transition_run(db, tenant_id="tenant-a", run_id=run.id, status="completed", result_payload={"ok": True})
    with pytest.raises(WorkflowConflict):
        transition_run(db, tenant_id="tenant-a", run_id=run.id, status="running")


def test_completed_step_is_not_reexecuted_by_repeated_recording(db):
    run = create_or_get_run(db, tenant_id="tenant-a", campaign_id="c1", idempotency_key="request-1", input_payload={})
    step = record_step(db, tenant_id="tenant-a", run_id=run.id, step_key="discovery:0", stage="discovery", idempotency_key="discover-1")
    transition_step(db, tenant_id="tenant-a", run_id=run.id, step_key=step.step_key, status="running")
    done = transition_step(db, tenant_id="tenant-a", run_id=run.id, step_key=step.step_key, status="succeeded", result_payload={"records": 3})
    again = record_step(db, tenant_id="tenant-a", run_id=run.id, step_key=step.step_key, stage="discovery", idempotency_key="discover-1")
    assert again.id == done.id
    assert again.status == "succeeded"


def test_step_idempotency_mismatch_is_rejected(db):
    run = create_or_get_run(db, tenant_id="tenant-a", campaign_id="c1", idempotency_key="request-1", input_payload={})
    record_step(db, tenant_id="tenant-a", run_id=run.id, step_key="delivery:0", stage="delivery", idempotency_key="dispatch-1")
    with pytest.raises(WorkflowConflict):
        record_step(db, tenant_id="tenant-a", run_id=run.id, step_key="delivery:0", stage="delivery", idempotency_key="dispatch-2")


def test_source_quote_must_exist_in_source_text():
    from app.services.sales_os.source_verification import verify_quote
    match = verify_quote("https://example.com/news", "Acme announced a new sales office in Pune.", "announced a new sales office")
    assert match.verified is True
    assert match.content_sha256
    miss = verify_quote("https://example.com/news", "Acme announced a new sales office in Pune.", "Acme is actively buying CRM")
    assert miss.verified is False
    assert miss.reason == "quote_not_found_in_source"


def test_source_url_rejects_local_and_non_http_targets():
    from app.services.sales_os.source_verification import validate_public_source_url
    def resolver(host, port, type):
        return [(None, None, None, None, ("127.0.0.1", port))]
    assert validate_public_source_url("http://localhost/admin")[0] is False
    assert validate_public_source_url("https://public.example/path", resolver=resolver) == (False, "non_public_address_blocked")
    assert validate_public_source_url("file:///etc/passwd")[0] is False


@pytest.mark.asyncio
async def test_fetch_and_verify_source_checks_actual_response_body(monkeypatch):
    from app.services.sales_os import source_verification

    def fake_fetch(parsed, host, address, port, target):
        return 200, {
            "content-type": "text/html; charset=utf-8",
            "content-encoding": "identity",
            "charset": "utf-8",
        }, b"<html><body><h1>Acme announcement</h1><p>Acme announced a new sales office in Pune.</p><script>fake claim</script></body></html>"

    def resolver(host, port, type):
        return [(None, None, None, None, ("93.184.216.34", port))]

    monkeypatch.setattr(source_verification, "_fetch_pinned_source", fake_fetch)
    receipt = await source_verification.fetch_and_verify_source(
        "https://public.example/news",
        "Acme announced a new sales office in Pune.",
        resolver=resolver,
    )
    assert receipt.verified is True
    assert receipt.reason == "exact_quote_match"
    assert receipt.content_sha256


@pytest.mark.asyncio
async def test_fetch_and_verify_source_does_not_follow_redirects(monkeypatch):
    from app.services.sales_os import source_verification

    def fake_fetch(parsed, host, address, port, target):
        return 302, {"content-type": "text/html"}, b""

    def resolver(host, port, type):
        return [(None, None, None, None, ("93.184.216.34", port))]

    monkeypatch.setattr(source_verification, "_fetch_pinned_source", fake_fetch)
    receipt = await source_verification.fetch_and_verify_source(
        "https://public.example/redirect",
        "claim",
        resolver=resolver,
    )
    assert receipt.verified is False
    assert receipt.reason == "redirect_not_followed"
