import pytest
from datetime import datetime
from decimal import Decimal
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.api.v1.endpoints.hr import router as hr_router
from app.models.base import Base, Tenant, User
from app.models.hr import (
    JobRequisition,
    SalaryBand,
    Application,
    TenantDocumentTemplate,
    TemplateVersion,
    HRDocumentPacket,
    HRDocumentArtifact,
    HRArtifactApproval,
    CandidateAcceptanceRecord,
    Employee,
)
from app.models.verticals import Candidate
import app.models.deal_room  # noqa: F401
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

TENANT_A = "tenant-alpha"
TENANT_B = "tenant-bravo"
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


@pytest.fixture(autouse=True)
def setup_tenants_and_users():
    db = Session()
    for tid in (TENANT_A, TENANT_B):
        if not db.query(Tenant).filter_by(id=tid).first():
            db.add(Tenant(id=tid, name=tid))

    admin_a = db.query(User).filter_by(id="user-a-admin").first()
    if not admin_a:
        admin_a = User(
            id="user-a-admin",
            tenant_id=TENANT_A,
            email="admin@alpha.com",
            role="hr_admin",
            hashed_password="x",
        )
        db.add(admin_a)


    admin_b = db.query(User).filter_by(id="user-b-admin").first()
    if not admin_b:
        admin_b = User(
            id="user-b-admin",
            tenant_id=TENANT_B,
            email="admin@bravo.com",
            role="hr_admin",
            hashed_password="x",
        )
        db.add(admin_b)

    db.commit()
    db.close()


def test_template_registration_token_detection_and_publication():
    db = Session()
    ACTOR["user"] = db.query(User).filter_by(id="user-a-admin").first()

    raw_template = """# ACME CORP OFFER LETTER
Dear {{candidate_name}},
We are excited to offer you the role of {{job_title}} at {{company_name}}!
Compensation: {{salary_currency}} {{salary_amount}}
Start Date: {{start_date}}
Confidentiality & intellectual property terms apply.
Notice period: 30 days.
"""

    # 1. Register template
    res = client.post(
        "/api/v1/hr/templates/register",
        json={
            "document_type": "offer_letter",
            "name": "Standard Corporate Offer",
            "format": "markdown",
            "raw_content": raw_template,
        }
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "success"
    tpl_id = data["template_id"]
    assert data["version"] == 1
    assert data["content_sha256"]

    # 2. List templates
    list_res = client.get("/api/v1/hr/templates/list")
    assert list_res.status_code == 200
    templates = list_res.json()
    assert any(t["id"] == tpl_id for t in templates)

    # 3. Publish template (passes synthetic validation)
    pub_res = client.post(f"/api/v1/hr/templates/{tpl_id}/publish?version_num=1")
    assert pub_res.status_code == 200, pub_res.text
    assert pub_res.json()["status"] == "success"

    db.close()


def test_dual_agent_packet_generation_and_assurance_audit():
    db = Session()
    ACTOR["user"] = db.query(User).filter_by(id="user-a-admin").first()

    # Create requisition and salary band
    req = JobRequisition(
        id="req-eng-101",
        tenant_id=TENANT_A,
        title="Staff Systems Architect",
        status="open",
        headcount_approved=1,
    )
    band = SalaryBand(
        id="band-eng-101",
        tenant_id=TENANT_A,
        requisition_id="req-eng-101",
        currency="USD",
        min_amount=Decimal("130000.00"),
        mid_amount=Decimal("160000.00"),
        max_amount=Decimal("190000.00"),
        effective_from=datetime.utcnow(),
    )
    cand = Candidate(
        id="cand-dev-202",
        tenant_id=TENANT_A,
        name="Jordan Lee",
        email="jordan.lee@example.com",
        role="Staff Systems Architect",
        status="interviewing",
    )
    db.add(req)
    db.add(band)
    db.add(cand)
    db.commit()

    # Generate document packet with salary within band ($150,000)
    gen_res = client.post(
        "/api/v1/hr/document-packets/generate",
        json={
            "candidate_id": "cand-dev-202",
            "requisition_id": "req-eng-101",
            "override_variables": {
                "salary_amount": "150000",
                "salary_currency": "USD",
            }
        }
    )
    assert gen_res.status_code == 200, gen_res.text
    packet_data = gen_res.json()
    packet_id = packet_data["packet_id"]
    assert packet_id
    assert packet_data["packet_eligibility"] in ("ELIGIBLE_FOR_APPROVAL", "REVIEW_REQUIRED")
    assert len(packet_data["artifacts"]) == 3  # Offer, Appointment, Contract

    # Inspect findings: salary within band
    findings = packet_data["findings"]
    salary_findings = [f for f in findings if f["category"] == "salary_band"]
    assert any(sf["status"] == "pass" for sf in salary_findings)

    # Now generate with out-of-band salary ($250,000 exceeds max $190,000)
    gen_bad = client.post(
        "/api/v1/hr/document-packets/generate",
        json={
            "candidate_id": "cand-dev-202",
            "requisition_id": "req-eng-101",
            "override_variables": {
                "salary_amount": "250000",
                "salary_currency": "USD",
            }
        }
    )
    bad_data = gen_bad.json()
    assert bad_data["packet_eligibility"] == "BLOCKED"
    bad_findings = bad_data["findings"]
    assert any(f["severity"] == "critical" and f["status"] == "fail" for f in bad_findings)

    db.close()


def test_cryptographic_approval_binding_and_invalidation():
    db = Session()
    ACTOR["user"] = db.query(User).filter_by(id="user-a-admin").first()

    cand = db.query(Candidate).filter_by(id="cand-dev-202").first()
    gen_res = client.post(
        "/api/v1/hr/document-packets/generate",
        json={
            "candidate_id": cand.id,
            "requisition_id": "req-eng-101",
            "override_variables": {"salary_amount": "150000"}
        }
    )
    packet_data = gen_res.json()
    packet_id = packet_data["packet_id"]
    offer_artifact = next(a for a in packet_data["artifacts"] if a["document_type"] == "offer_letter")
    art_id = offer_artifact["artifact_id"]
    correct_sha256 = offer_artifact["artifact_sha256"]

    # Try approving with wrong/tampered SHA-256
    bad_appr = client.post(
        f"/api/v1/hr/document-packets/{packet_id}/approve",
        json={
            "packet_id": packet_id,
            "artifact_id": art_id,
            "expected_artifact_sha256": "tampered_fake_sha256_hash",
            "decision": "approved",
            "rationale": "Testing hash mismatch",
        }
    )
    assert bad_appr.status_code == 400
    assert "mismatch" in bad_appr.text.lower()

    # Approve with exact matching SHA-256
    good_appr = client.post(
        f"/api/v1/hr/document-packets/{packet_id}/approve",
        json={
            "packet_id": packet_id,
            "artifact_id": art_id,
            "expected_artifact_sha256": correct_sha256,
            "decision": "approved",
            "rationale": "Verified by HR Admin",
        }
    )
    assert good_appr.status_code == 200, good_appr.text
    assert good_appr.json()["bound_sha256"] == correct_sha256

    db.close()


def test_sequential_lifecycle_offer_acceptance_appointment_and_hiring():
    db = Session()
    ACTOR["user"] = db.query(User).filter_by(id="user-a-admin").first()

    cand = db.query(Candidate).filter_by(id="cand-dev-202").first()
    gen_res = client.post(
        "/api/v1/hr/document-packets/generate",
        json={
            "candidate_id": cand.id,
            "requisition_id": "req-eng-101",
            "override_variables": {"salary_amount": "150000"}
        }
    )
    packet_data = gen_res.json()
    packet_id = packet_data["packet_id"]
    offer_artifact = next(a for a in packet_data["artifacts"] if a["document_type"] == "offer_letter")

    # Step 1: Approve offer artifact
    client.post(
        f"/api/v1/hr/document-packets/{packet_id}/approve",
        json={
            "packet_id": packet_id,
            "artifact_id": offer_artifact["artifact_id"],
            "expected_artifact_sha256": offer_artifact["artifact_sha256"],
            "decision": "approved",
        }
    )

    # Step 2: Dispatch offer
    dispatch_res = client.post(f"/api/v1/hr/document-packets/{packet_id}/dispatch-offer")
    assert dispatch_res.status_code == 200, dispatch_res.text
    d_data = dispatch_res.json()
    assert d_data["status"] == "success"
    assert "token=" in d_data["acceptance_url"]
    raw_token = d_data["acceptance_url"].split("token=")[1]

    # Step 3: Candidate accepts offer via public portal
    accept_res = client.post(
        "/api/v1/hr/public/accept-offer",
        json={"token": raw_token, "confirmed": True}
    )
    assert accept_res.status_code == 200, accept_res.text
    assert accept_res.json()["status"] == "success"

    # Verify idempotency of acceptance
    dup_accept = client.post(
        "/api/v1/hr/public/accept-offer",
        json={"token": raw_token, "confirmed": True}
    )
    assert dup_accept.status_code == 200
    assert dup_accept.json()["status"] == "already_accepted"

    # Step 4: Dispatch appointment / joining letter
    appt_res = client.post(f"/api/v1/hr/document-packets/{packet_id}/dispatch-appointment")
    assert appt_res.status_code == 200, appt_res.text
    assert appt_res.json()["status"] == "success"

    # Step 5: Execute contract and provision employee
    contract_res = client.post(f"/api/v1/hr/document-packets/{packet_id}/execute-contract")
    assert contract_res.status_code == 200, contract_res.text
    assert contract_res.json()["status"] == "success"

    # Verify employee and candidate state
    emp = db.query(Employee).filter_by(tenant_id=TENANT_A, candidate_id=cand.id).first()
    assert emp is not None
    assert emp.status == "active"
    db.refresh(cand)
    assert cand.status == "hired"

    db.close()


def test_tenant_isolation_guardrail():
    """Ensure Tenant B cannot access or approve Tenant A's document packets."""
    db = Session()
    ACTOR["user"] = db.query(User).filter_by(id="user-b-admin").first()

    # Tenant B tries to approve Tenant A's packet
    packet_a = db.query(HRDocumentPacket).filter_by(tenant_id=TENANT_A).first()
    assert packet_a is not None

    res = client.post(
        f"/api/v1/hr/document-packets/{packet_a.id}/approve",
        json={
            "packet_id": packet_a.id,
            "artifact_id": "art-fake",
            "expected_artifact_sha256": "fake",
            "decision": "approved"
        }
    )
    assert res.status_code == 400
    assert "not found" in res.text.lower()

    db.close()
