"""
Unit and integration tests for Universal HR Copilot Task Execution and Live DB Answering.
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.hr_core import EmployeeProfile, Department, CompanyPolicy
from app.models.hr_workforce import LeaveRequest, LeaveType
from app.models.hr import JobRequisition
from app.models.verticals import Candidate
from app.services.agents.hr.orchestrator import HREnterpriseOrchestrator
from app.services.agents.hr.schemas import CopilotChatRequest, AutonomyLevel


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.mark.asyncio
async def test_hr_copilot_task_execution_and_db_answering(test_db):
    tenant_id = "tenant-test-hr"
    user_id = "user-test-admin"

    # Seed base department
    dept = Department(tenant_id=tenant_id, name="Engineering", code="ENG")
    test_db.add(dept)
    test_db.commit()

    orchestrator = HREnterpriseOrchestrator(test_db, tenant_id, user_id)

    # 1. TEST: Add Employee
    res1 = await orchestrator.handle_message(
        CopilotChatRequest(message="Add an employee named John Doe, Senior Backend Engineer, Engineering department, email john.doe@octaos.com")
    )
    assert "Employee Created Successfully" in res1.reply
    assert "John Doe" in res1.reply
    assert res1.task_result is not None
    assert res1.task_result.proposed_actions[0].executed is True

    # Verify DB persistence
    emp = test_db.query(EmployeeProfile).filter_by(tenant_id=tenant_id, email="john.doe@octaos.com").first()
    assert emp is not None
    assert emp.full_name == "John Doe"
    assert emp.job_title == "Senior Backend Engineer"
    assert emp.department_name == "Engineering"

    # 2. TEST: Answering headcount from DB
    res2 = await orchestrator.handle_message(CopilotChatRequest(message="how many employees are there"))
    assert "1 active employee" in res2.reply
    assert "John Doe" in res2.reply

    # 3. TEST: Lookup specific employee
    res3 = await orchestrator.handle_message(CopilotChatRequest(message="who is John Doe"))
    assert "John Doe" in res3.reply
    assert "Senior Backend Engineer" in res3.reply
    assert "Engineering" in res3.reply

    # 4. TEST: Create Job Requisition
    res4 = await orchestrator.handle_message(
        CopilotChatRequest(message="Create a job requisition for Frontend Developer with 2 openings")
    )
    assert "Job Requisition Opened Successfully" in res4.reply
    assert "Frontend Developer" in res4.reply

    req = test_db.query(JobRequisition).filter_by(tenant_id=tenant_id, title="Frontend Developer").first()
    assert req is not None
    assert req.headcount_approved == 2
    assert req.status == "open"

    # 5. TEST: Add Candidate
    res5 = await orchestrator.handle_message(
        CopilotChatRequest(message="Add candidate Alice Smith for Frontend Developer, email alice@smith.com")
    )
    assert "Candidate Added to Talent Pipeline" in res5.reply
    assert "Alice Smith" in res5.reply

    cand = test_db.query(Candidate).filter_by(tenant_id=tenant_id, email="alice@smith.com").first()
    assert cand is not None
    assert cand.name == "Alice Smith"
    assert cand.role == "Frontend Developer"

    # 6. TEST: Move Candidate Stage
    res6 = await orchestrator.handle_message(
        CopilotChatRequest(message="Move candidate Alice Smith to interviewed")
    )
    assert "Candidate Stage Updated" in res6.reply
    assert "INTERVIEWED" in res6.reply
    assert cand.status == "interviewed"

    # 7. TEST: Submit Leave Request
    res7 = await orchestrator.handle_message(
        CopilotChatRequest(message="Submit leave for John Doe for 3 days for Vacation")
    )
    assert "Leave Request Submitted for Review" in res7.reply
    assert "3.0 day(s)" in res7.reply

    leave = test_db.query(LeaveRequest).filter_by(tenant_id=tenant_id, employee_id=emp.id).first()
    assert leave is not None
    assert leave.days_requested == 3.0
    assert leave.status == "pending"

    # 8. TEST: Approve Leave
    res8 = await orchestrator.handle_message(
        CopilotChatRequest(message="Approve leave for John Doe")
    )
    assert "Leave Request Approved" in res8.reply
    assert leave.status == "approved"

    # 9. TEST: Create Department
    res9 = await orchestrator.handle_message(
        CopilotChatRequest(message="Create department Marketing with code MKT")
    )
    assert "Department Created Successfully" in res9.reply
    mkt = test_db.query(Department).filter_by(tenant_id=tenant_id, name="Marketing").first()
    assert mkt is not None
    assert mkt.code == "MKT"
