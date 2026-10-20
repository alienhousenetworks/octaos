import io
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import deps
from app.models.base import Base, User, Tenant, APICredential
from app.models import verticals as models
import app.models.deal_room  # noqa: F401  # sales_companies FK target
from app.api.v1.endpoints.hr import router as hr_router

import os

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_hr.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables on engine
Base.metadata.create_all(bind=engine)
models.Candidate.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def override_get_current_tenant_id():
    return "test-tenant-123"

def override_get_current_user():
    return User(
        id="test-user-123",
        email="hr@test.com",
        tenant_id="test-tenant-123",
        role="admin",
        is_active=True,
        is_system_admin=True
    )

# Setup clean test app
test_app = FastAPI()
test_app.dependency_overrides[deps.get_db] = override_get_db
test_app.dependency_overrides[deps.get_current_tenant_id] = override_get_current_tenant_id
test_app.dependency_overrides[deps.get_current_user] = override_get_current_user
test_app.include_router(hr_router, prefix="/api/v1/hr")

# Seed tenant and mock user if not present
db = TestingSessionLocal()
tenant = db.query(Tenant).filter_by(id="test-tenant-123").first()
if not tenant:
    tenant = Tenant(id="test-tenant-123", name="Test Corp")
    db.add(tenant)

user = db.query(User).filter_by(id="test-user-123").first()
if not user:
    user = User(
        id="test-user-123",
        email="hr@test.com",
        hashed_password="test_hashed_pw",
        tenant_id="test-tenant-123",
        role="admin",
        is_active=True,
        is_system_admin=True
    )
    db.add(user)

db.commit()
db.close()

client = TestClient(test_app)

def test_get_contract_templates():
    response = client.get("/api/v1/hr/contract-templates")
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) >= 4
    template_ids = [t["id"] for t in templates]
    assert "full_time_standard" in template_ids
    assert "contractor_freelance" in template_ids
    assert "internship_offer" in template_ids
    assert "executive_senior" in template_ids

def test_batch_resume_upload_and_ranking():
    sample_resume = b"""
    David Miller
    david.miller@example.com | (555) 321-7654
    Senior Backend Software Engineer with 5+ years of experience in Python, FastAPI, Docker, and PostgreSQL.
    Education: B.S. in Computer Science
    """
    
    files = [
        ("files", ("David_Miller_Resume.txt", io.BytesIO(sample_resume), "text/plain"))
    ]
    data = {
        "role": "Senior Backend Engineer",
        "requirements": "Python, FastAPI, Docker, PostgreSQL, Kubernetes",
        "salary": "$140,000/year",
        "provider": "auto"
    }

    response = client.post("/api/v1/hr/resumes/upload-batch", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert res_data["processed_count"] == 1
    candidates = res_data["candidates"]
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand["name"] == "David Miller"
    assert cand["email"] == "david.miller@example.com"
    assert cand["scorecard"]["ats_score"] >= 60

def test_interview_email_dispatch():
    db = TestingSessionLocal()
    cand = models.Candidate(
        tenant_id="test-tenant-123",
        name="Elena Rostova",
        email="elena@example.com",
        role="Frontend Engineer",
        status="accepted",
        scorecard={"match_score": 85}
    )
    db.add(cand)
    db.commit()
    db.refresh(cand)
    candidate_id = cand.id
    db.close()

    payload = {
        "interview_date": "2026-10-15",
        "interview_time": "2:00 PM",
        "round_name": "Technical Architecture",
        "meeting_link": "https://meet.google.com/test-meet",
        "interviewer_name": "Chief Architect",
        "custom_notes": "Please prepare a diagram of your recent project.",
        "channel": "smtp"
    }

    response = client.post(f"/api/v1/hr/{candidate_id}/send-interview-email", json=payload)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] == "success"
    assert res_json["candidate"]["status"] == "interviewed"
    assert res_json["candidate"]["scorecard"]["calendar_booked"] is True

def test_generate_offer_and_send_email():
    db = TestingSessionLocal()
    cand = models.Candidate(
        tenant_id="test-tenant-123",
        name="Marcus Vance",
        email="marcus@example.com",
        role="Staff AI Engineer",
        status="interviewed",
        scorecard={"match_score": 92}
    )
    db.add(cand)
    db.commit()
    db.refresh(cand)
    candidate_id = cand.id
    db.close()

    # 1. Generate Offer Document Preview
    gen_payload = {
        "template_id": "full_time_standard",
        "variables": {
            "salary_amount": "180,000",
            "start_date": "December 1, 2026",
            "work_mode": "Remote (Global)"
        }
    }
    gen_res = client.post(f"/api/v1/hr/{candidate_id}/generate-offer", json=gen_payload)
    assert gen_res.status_code == 200
    doc = gen_res.json()["document"]
    assert "Marcus Vance" in doc["plain_text"]
    assert "180,000" in doc["plain_text"]
    assert "EMPLOYMENT AGREEMENT" in doc["html"]

    # 2. Dispatch Offer Email
    send_payload = {
        "template_id": "full_time_standard",
        "variables": {
            "salary_amount": "180,000",
            "start_date": "December 1, 2026",
            "work_mode": "Remote (Global)"
        },
        "channel": "smtp"
    }
    send_res = client.post(f"/api/v1/hr/{candidate_id}/send-offer-email", json=send_payload)
    assert send_res.status_code == 200
    send_json = send_res.json()
    assert send_json["status"] == "success"
    assert send_json["candidate"]["status"] == "offered"
    assert "offer_details" in send_json["candidate"]["scorecard"]

def test_batch_resume_upload_internship_and_phone_persistence():
    """Verify batch upload accurately classifies internship profiles and persists phone number."""
    intern_resume = b"""
    Aman Gupta
    Bengaluru, India | aman.gupta@example.com | +91 98765 43210
    GitHub: github.com/aman-dev

    CAREER OBJECTIVE
    Enthusiastic computer science graduate eager to apply skills in full stack development.

    TECHNICAL SKILLS
    Languages: Python, JavaScript, SQL
    Frameworks: FastAPI, React, Node.js
    Tools: Git, Docker, Postman

    INTERNSHIPS & EXPERIENCE
    Software Engineering Intern | NextGen Cloud Solutions | May 2023 - July 2023
    - Built REST APIs using FastAPI and PostgreSQL for internal dashboards.

    EDUCATION
    Bachelor of Technology in Computer Science (B.Tech) | 2020 - 2024
    Visvesvaraya Technological University, Bengaluru
    """

    files = [
        ("files", ("Aman_Gupta_CV.txt", io.BytesIO(intern_resume), "text/plain"))
    ]
    data = {
        "role": "Junior Full Stack Engineer",
        "requirements": "Python, FastAPI, React",
        "salary": "$70,000/year",
        "provider": "auto"
    }

    response = client.post("/api/v1/hr/resumes/upload-batch", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    cand = res_data["candidates"][0]
    assert cand["name"] == "Aman Gupta"
    assert cand["email"] == "aman.gupta@example.com"
    # Verify phone was saved to Candidate.phone column
    assert "98765" in (cand.get("phone") or "")
    assert cand["scorecard"]["is_internship_only"] is True
    assert cand["scorecard"]["experience_years"] == 0
    assert "Bengaluru" in cand["scorecard"]["address"]

def test_candidates_export_excel_with_accurate_intern_and_contact_data():
    """Verify Excel export produces valid .xlsx with accurate phone, email, and internship experience strings."""
    import openpyxl
    response = client.get("/api/v1/hr/candidates/export-excel")
    assert response.status_code == 200
    assert "openxmlformats" in response.headers.get("content-type", "")

    # Parse Excel binary in-memory
    wb = openpyxl.load_workbook(io.BytesIO(response.content), data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    assert len(rows) >= 2  # At least header + 1 candidate

    headers = [str(h) for h in rows[0]]
    assert "Rank" in headers
    assert "Name" in headers
    assert "Mobile No" in headers
    assert "Email" in headers
    assert "Address" in headers
    assert "Experiences" in headers

    # Find row for Aman Gupta (intern profile)
    aman_row = None
    for r in rows[1:]:
        if r[1] == "Aman Gupta":
            aman_row = r
            break

    if aman_row:
        exp_idx = headers.index("Experiences")
        phone_idx = headers.index("Mobile No")
        email_idx = headers.index("Email")
        addr_idx = headers.index("Address")

        assert "Internship" in str(aman_row[exp_idx])
        assert "98765" in str(aman_row[phone_idx])
        assert "aman.gupta@example.com" in str(aman_row[email_idx])
        assert "Bengaluru" in str(aman_row[addr_idx])

