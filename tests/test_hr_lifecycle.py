"""Lifecycle behavior added beside the existing hiring API."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.api.v1.endpoints.hr import router as hr_router
from app.models.base import Base, Tenant, User
from app.models.executive import BudgetReservation, ExecutiveApprovalRequest, SideEffectOutbox
from app.models.hr import Application, Assessment, Employee, JobRequisition
from app.models.verticals import Candidate
import app.models.deal_room  # noqa: F401  # sales_companies FK target
import app.models.enterprise  # noqa: F401
import app.models.executive  # noqa: F401
import app.models.workflows  # noqa: F401

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Session = sessionmaker(bind=engine, expire_on_commit=False)
Base.metadata.create_all(bind=engine)

TENANT = "tenant-hr-life"
OTHER = "tenant-hr-other"
ACTOR = {"user": None}
_SESSION = {"current": None}


def _db():
    owned = _SESSION["current"] is None
    db = _SESSION["current"] or Session()
    try:
        yield db
    finally:
        if owned:
            db.close()


def _user():
    return ACTOR["user"]


def _tenant():
    return ACTOR["user"].tenant_id


app = FastAPI()
app.dependency_overrides[deps.get_db] = _db
app.dependency_overrides[deps.get_current_user] = _user
app.dependency_overrides[deps.get_current_tenant_id] = _tenant
app.include_router(hr_router, prefix="/api/v1/hr")
client = TestClient(app)


def _make_user(db, user_id, tenant_id, role, email):
    if db.query(Tenant).filter_by(id=tenant_id).first() is None:
        db.add(Tenant(id=tenant_id, name=tenant_id, subdomain=tenant_id))
        db.flush()
    user = User(id=user_id, tenant_id=tenant_id, email=email, hashed_password="x", role=role, is_active=True)
    db.add(user)
    db.commit()
    return user


@pytest.fixture()
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = Session()
    _SESSION["current"] = session
    ACTOR["user"] = None
    try:
        yield session
    finally:
        session.close()
        _SESSION["current"] = None


def test_case_variant_emails_become_one_application(db):
    from app.services.hr.migration_map import backfill_candidates

    db.add(Tenant(id=TENANT, name="T", subdomain="life"))
    db.add(Candidate(id="c1", tenant_id=TENANT, name="Jane", email="Jane@x.com", role="Engineer", status="sourced", scorecard={"skills": ["Python"], "match_score": 80}))
    db.add(Candidate(id="c2", tenant_id=TENANT, name="Jane Q", email="jane@x.com", role="Engineer", status="screened", scorecard={"skills": ["Go"], "match_score": 70}))
    db.commit()
    backfill_candidates(db)
    db.commit()
    apps = db.query(Application).filter_by(tenant_id=TENANT).all()
    assert len(apps) == 1
    versions = db.query(Assessment).filter_by(application_id=apps[0].id).count()
    assert versions == 2
    assert db.query(Candidate).filter_by(id="c1").one().scorecard["skills"] == ["Python"]
    assert db.query(Candidate).filter_by(id="c2").one().merged_into_candidate_id == "c1"


def test_stage_move_does_not_create_an_approval(db):
    admin = _make_user(db, "admin-1", TENANT, "admin", "admin@life.test")
    ACTOR["user"] = admin
    person = Candidate(id="p1", tenant_id=TENANT, name="Ada", email="ada@life.test", role="Engineer", status="sourced", scorecard={})
    db.add(person)
    db.commit()
    req = client.post("/api/v1/hr/requisitions", json={"title": "Engineer"})
    assert req.status_code == 200, req.text
    app_row = client.post("/api/v1/hr/applications", json={"candidate_id": "p1", "requisition_id": req.json()["id"], "lawful_basis": "application"})
    assert app_row.status_code == 200, app_row.text
    before = db.query(ExecutiveApprovalRequest).count()
    moved = client.post(f"/api/v1/hr/applications/{app_row.json()['id']}/transition", json={"to_stage": "screened"})
    assert moved.status_code == 200, moved.text
    assert db.query(ExecutiveApprovalRequest).count() == before
    assert db.query(Application).filter_by(id=app_row.json()["id"]).one().current_stage == "screened"


def test_rejection_approval_does_not_stage_mail(db):
    admin = _make_user(db, "admin-2", TENANT, "admin", "a2@life.test")
    approver = _make_user(db, "admin-3", TENANT, "hr_admin", "a3@life.test")
    ACTOR["user"] = admin
    db.add(Candidate(id="p2", tenant_id=TENANT, name="Bea", email="bea@life.test", role="Engineer", status="sourced", scorecard={}))
    db.commit()
    req = client.post("/api/v1/hr/requisitions", json={"title": "Engineer"})
    app_row = client.post("/api/v1/hr/applications", json={"candidate_id": "p2", "requisition_id": req.json()["id"]})
    requested = client.post(f"/api/v1/hr/applications/{app_row.json()['id']}/reject", json={"reason": "Role was filled"})
    assert requested.status_code == 200, requested.text
    assert db.query(Application).filter_by(id=app_row.json()["id"]).one().current_stage == "sourced"
    assert db.query(SideEffectOutbox).count() == 0
    ACTOR["user"] = approver
    decided = client.post(
        f"/api/v1/hr/approvals/{requested.json()['approval_id']}/decide",
        json={"decision": "APPROVE", "rationale": "Agreed", "payload": {}},
    )
    assert decided.status_code == 200, decided.text
    assert db.query(SideEffectOutbox).count() == 0
    assert db.query(Application).filter_by(id=app_row.json()["id"]).one().current_stage == "rejected"


def test_offer_draft_does_not_reserve_and_submit_uses_a_short_key(db):
    admin = _make_user(db, "admin-4", TENANT, "admin", "a4@life.test")
    ACTOR["user"] = admin
    db.add(Candidate(id="p3", tenant_id=TENANT, name="Cy", email="cy@life.test", role="Engineer", status="sourced", scorecard={}))
    db.commit()
    req = client.post("/api/v1/hr/requisitions", json={"title": "Engineer"})
    req_id = req.json()["id"]
    client.post(f"/api/v1/hr/requisitions/{req_id}/open")
    app_row = client.post("/api/v1/hr/applications", json={"candidate_id": "p3", "requisition_id": req_id, "lawful_basis": "application"})
    band = client.post("/api/v1/hr/salary-bands", json={
        "requisition_id": req_id, "currency": "USD", "min_amount": "100000", "mid_amount": "120000", "max_amount": "140000"
    })
    assert band.status_code == 200, band.text
    env = client.post("/api/v1/hr/budget-envelopes", json={"currency": "USD", "authorized_limit": "500000"})
    assert env.status_code == 200, env.text
    draft = client.post("/api/v1/hr/offers", json={"application_id": app_row.json()["id"], "base_amount": "120000", "currency": "USD"})
    assert draft.status_code == 200, draft.text
    assert draft.json()["reservations"] == 0
    submitted = client.post(f"/api/v1/hr/offers/{draft.json()['id']}/submit")
    assert submitted.status_code == 200, submitted.text
    assert len(submitted.json()["idempotency_key"]) == 33
    assert db.query(BudgetReservation).count() == 1


def test_legacy_requisition_time_to_fill_is_insufficient(db):
    admin = _make_user(db, "admin-5", TENANT, "admin", "a5@life.test")
    ACTOR["user"] = admin
    db.add(JobRequisition(tenant_id=TENANT, title="Old", status="open", opened_at_confirmed=False, headcount_approved=1))
    db.commit()
    response = client.get("/api/v1/hr/analytics?metric=time_to_fill")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "insufficient_data"
    assert body["value"] is None


def test_agent_cannot_see_salary_text(db):
    admin = _make_user(db, "admin-6", TENANT, "admin", "a6@life.test")
    agent = _make_user(db, "agent-6", TENANT, "agent", "agent@life.test")
    ACTOR["user"] = admin
    db.add(JobRequisition(tenant_id=TENANT, title="Paid", status="open", legacy_salary_text="$1", headcount_approved=1))
    db.commit()
    ACTOR["user"] = agent
    rows = client.get("/api/v1/hr/requisitions")
    assert rows.status_code == 200
    assert "legacy_salary_text" not in rows.json()[0]


def test_other_tenant_cannot_read_applications(db):
    admin = _make_user(db, "admin-7", TENANT, "admin", "a7@life.test")
    other = _make_user(db, "admin-8", OTHER, "admin", "a8@other.test")
    ACTOR["user"] = admin
    db.add(Candidate(id="p7", tenant_id=TENANT, name="Dee", email="dee@life.test", role="Engineer", status="sourced", scorecard={}))
    db.commit()
    req = client.post("/api/v1/hr/requisitions", json={"title": "Engineer"})
    client.post("/api/v1/hr/applications", json={"candidate_id": "p7", "requisition_id": req.json()["id"]})
    ACTOR["user"] = other
    rows = client.get("/api/v1/hr/applications")
    assert rows.json() == []


def test_hire_consumes_the_offer_hold_key(db):
    from app.models.hr import Offer
    from app.services.hr.onboarding_service import complete_hire

    db.add(Tenant(id=TENANT, name="T", subdomain="hire"))
    db.add(Candidate(id="p9", tenant_id=TENANT, name="Eve", email="eve@life.test", role="Engineer", status="offer", scorecard={}))
    req = JobRequisition(id="req-9", tenant_id=TENANT, title="Engineer", status="open", headcount_approved=1, opened_at_confirmed=True)
    db.add(req)
    db.flush()
    application = Application(id="app-9", tenant_id=TENANT, candidate_id="p9", requisition_id=req.id, current_stage="offer", status="active", consent_status="basis_recorded")
    db.add(application)
    db.flush()
    offer = Offer(
        id="offer-9",
        tenant_id=TENANT,
        application_id=application.id,
        base_amount=Decimal("1000.00"),
        currency="USD",
        signature_state="signed",
        status="accepted",
        expires_at=datetime.now(timezone.utc) + timedelta(days=2),
    )
    db.add(offer)
    from app.models.executive import BudgetEnvelope
    envelope = BudgetEnvelope(
        id="env-9", tenant_id=TENANT, department="hr", currency="USD",
        period_start=datetime.now(timezone.utc), period_end=datetime.now(timezone.utc) + timedelta(days=30),
        authorized_limit=Decimal("5000.00"), reserved_amount=Decimal("1000.00"), consumed_amount=Decimal("0"),
        is_active=True,
    )
    db.add(envelope)
    db.flush()
    db.add(BudgetReservation(
        tenant_id=TENANT, envelope_id=envelope.id, workflow_id="wf", task_id="task",
        amount=Decimal("1000.00"), status="RESERVED", idempotency_key="h" + "a" * 32,
        expires_at=offer.expires_at,
    ))
    db.commit()
    employee = complete_hire(db, TENANT, offer, application, "h" + "a" * 32)
    assert employee is not None
    assert db.query(Employee).count() == 1
    assert db.query(BudgetReservation).one().status == "COMMITTED"


def test_copilot_does_not_reject(db):
    admin = _make_user(db, "admin-10", TENANT, "admin", "a10@life.test")
    ACTOR["user"] = admin
    db.add(Candidate(id="p10", tenant_id=TENANT, name="Fay", email="fay@life.test", role="Engineer", status="sourced", scorecard={}))
    db.commit()
    req = client.post("/api/v1/hr/requisitions", json={"title": "Engineer"})
    app_row = client.post("/api/v1/hr/applications", json={"candidate_id": "p10", "requisition_id": req.json()["id"]})
    answer = client.post("/api/v1/hr/copilot", json={"message": "Reject the weakest candidate"})
    assert answer.status_code == 200
    assert answer.json()["tool"] is None
    assert db.query(Application).filter_by(id=app_row.json()["id"]).one().current_stage == "sourced"


def test_existing_contract_templates_still_list():
    db = Session()
    db.add(Tenant(id="tpl-tenant", name="Tpl", subdomain="tpl-tenant"))
    user = User(id="tpl-user", tenant_id="tpl-tenant", email="tpl@life.test", hashed_password="x", role="admin", is_active=True, is_system_admin=True)
    db.add(user)
    db.commit()
    ACTOR["user"] = user
    response = client.get("/api/v1/hr/contract-templates")
    db.close()
    assert response.status_code == 200
    assert len(response.json()) >= 4
