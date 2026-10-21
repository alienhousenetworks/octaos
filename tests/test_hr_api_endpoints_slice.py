"""
Integration tests for HR People, Workforce, and Copilot API Endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.base import Base, Tenant, User
from app.models.hr_core import EmployeeProfile, Department
from app.models.hr_workforce import LeaveType, LeaveRequest
from app.api import deps


@pytest.fixture
def client_and_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()

    # Create dummy tenant and user
    t = Tenant(id="tenant-api-test", name="ApiTest Corp")
    u = User(id="user-api-test", tenant_id="tenant-api-test", email="hr@test.com", role="admin", hashed_password="fakehashpassword123")
    dept = Department(tenant_id="tenant-api-test", name="Product Engineering")
    db.add(t)
    db.add(u)
    db.add(dept)
    db.commit()

    # Pre-seed one employee
    emp = EmployeeProfile(
        tenant_id="tenant-api-test",
        employee_number="EMP-0100",
        first_name="Elena",
        last_name="Rostova",
        email="elena@test.com",
        job_title="Lead Architect",
        department_id=dept.id,
        department_name="Product Engineering"
    )
    ltype = LeaveType(
        tenant_id="tenant-api-test",
        name="Annual Leave",
        code="ANNUAL",
        annual_allowance_days=20.0
    )
    db.add(emp)
    db.add(ltype)
    db.commit()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_tenant_id():
        return "tenant-api-test"

    def override_get_current_user():
        return u

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_current_tenant_id] = override_get_current_tenant_id
    app.dependency_overrides[deps.get_current_user] = override_get_current_user

    client = TestClient(app)
    yield client, db, emp.id, ltype.id

    app.dependency_overrides.clear()
    db.close()


def test_people_api_list_and_create(client_and_db):
    client, db, emp_id, _ = client_and_db

    # 1. List employees
    res = client.get("/api/v1/hr/people/employees")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["first_name"] == "Elena"

    # 2. Create employee
    create_payload = {
        "first_name": "Marcus",
        "last_name": "Vance",
        "email": "marcus@test.com",
        "job_title": "Frontend Engineer",
        "department_name": "Product Engineering",
        "skills": ["React", "TypeScript"]
    }
    res_create = client.post("/api/v1/hr/people/employees", json=create_payload)
    assert res_create.status_code == 200
    created = res_create.json()
    assert created["full_name"] == "Marcus Vance"
    assert created["status"] == "active"

    # 3. Analytics summary
    res_analytics = client.get("/api/v1/hr/people/analytics/summary")
    assert res_analytics.status_code == 200
    analytics = res_analytics.json()
    assert analytics["headcount"]["total_active"] == 2


def test_workforce_leave_submit_and_approve(client_and_db):
    client, db, emp_id, _ = client_and_db

    # 1. Submit leave request
    leave_payload = {
        "employee_id": emp_id,
        "leave_type_code": "ANNUAL",
        "start_date": "2026-11-10",
        "end_date": "2026-11-14",
        "days_requested": 5.0,
        "reason": "Family vacation"
    }
    res_submit = client.post("/api/v1/hr/workforce/leaves", json=leave_payload)
    assert res_submit.status_code == 200
    submitted = res_submit.json()
    assert submitted["status"] == "pending"
    assert "coverage_score" in submitted
    leave_id = submitted["id"]

    # 2. Check impact assessment endpoint
    res_impact = client.post(f"/api/v1/hr/workforce/leaves/{leave_id}/impact-assessment")
    assert res_impact.status_code == 200
    assert res_impact.json()["employee_id"] == emp_id

    # 3. Approve leave request
    res_approve = client.post(f"/api/v1/hr/workforce/leaves/{leave_id}/approve")
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == "approved"

    # 4. Verify leave is marked approved in list
    res_list = client.get("/api/v1/hr/workforce/leaves")
    assert res_list.status_code == 200
    leaves = res_list.json()
    assert len(leaves) == 1
    assert leaves[0]["status"] == "approved"


def test_copilot_chat_and_approval_submission(client_and_db):
    client, db, emp_id, _ = client_and_db

    # 1. Chat with copilot
    chat_payload = {
        "message": "Check whether approving this leave request will create a staffing gap",
        "context_pillar": "compensation",
        "resource_id": emp_id
    }
    res_chat = client.post("/api/v1/hr/copilot/chat", json=chat_payload)
    assert res_chat.status_code == 200
    chat_resp = res_chat.json()
    assert "Coverage Assessment" in chat_resp["reply"]
    assert chat_resp["specialist_agent"] == "Leave & Workforce Impact Agent"

    # 2. Submit action to enterprise approvals
    approval_payload = {
        "action_type": "leave.approve",
        "title": "Approve annual leave for Elena",
        "resource_id": emp_id,
        "payload": {"employee_id": emp_id, "days": 5},
        "rationale": "Sufficient team coverage verified by Copilot",
        "risk_tier": "R3"
    }
    res_approval = client.post("/api/v1/hr/copilot/actions/submit-approval", json=approval_payload)
    assert res_approval.status_code == 200
    app_data = res_approval.json()
    assert "approval_request_id" in app_data
    assert app_data["status"] == "pending"
