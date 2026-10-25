"""
OctaOS HR Core Domain Models.
Defines stable employee identity, organizational structure, policy management, and HR service requests.
"""
import uuid
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Integer, Text, JSON,
    UniqueConstraint, Index, CheckConstraint, Numeric
)
from sqlalchemy.sql import func
from app.models.base import Base


def _id() -> str:
    return str(uuid.uuid4())


class Department(Base):
    __tablename__ = "hr_departments"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    parent_id = Column(String, ForeignKey("hr_departments.id"), nullable=True)
    head_employee_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_department_tenant_name"),
    )


class EmployeeProfile(Base):
    """Stable employee record for directory, hierarchy, and identity across all HR modules."""
    __tablename__ = "hr_employees"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    employee_number = Column(String, nullable=False, index=True)
    
    # Personal Details
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    email = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    
    # Organizational Placement
    department_id = Column(String, ForeignKey("hr_departments.id"), nullable=True, index=True)
    department_name = Column(String, nullable=True)
    job_title = Column(String, nullable=False)
    manager_id = Column(String, ForeignKey("hr_employees.id"), nullable=True, index=True)
    work_location = Column(String, nullable=True, default="Remote")  # "HQ", "Remote", "Branch"
    
    # Employment Status
    employment_type = Column(String, nullable=False, default="full_time")  # full_time, part_time, contractor, intern
    status = Column(String, nullable=False, default="active", index=True)  # onboarding, active, on_leave, probation, terminated
    hire_date = Column(DateTime(timezone=True), nullable=True)
    probation_end_date = Column(DateTime(timezone=True), nullable=True)
    termination_date = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata & Custom Attributes (skills, emergency contact, tags)
    skills = Column(JSON, nullable=False, default=list)
    metadata_fields = Column(JSON, nullable=False, default=dict)
    onboarding_instance_id = Column(String, nullable=True, unique=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_number", name="uq_emp_tenant_number"),
        UniqueConstraint("tenant_id", "email", name="uq_emp_tenant_email"),
    )

    @property
    def full_name(self) -> str:
        if self.display_name:
            return self.display_name
        return f"{self.first_name} {self.last_name}".strip()


class CompanyPolicy(Base):
    """Company policies (Leave, Code of Conduct, Travel, Remote Work) available for RAG."""
    __tablename__ = "hr_company_policies"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False, default="general")  # leave, conduct, benefits, compensation, remote
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    requires_acknowledgement = Column(Boolean, nullable=False, default=False)
    effective_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PolicyAcknowledgement(Base):
    """Audit log of employee policy acknowledgements."""
    __tablename__ = "hr_policy_acknowledgements"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    policy_id = Column(String, ForeignKey("hr_company_policies.id"), nullable=False, index=True)
    employee_id = Column(String, ForeignKey("hr_employees.id"), nullable=False, index=True)
    policy_version = Column(Integer, nullable=False, default=1)
    acknowledged_at = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "policy_id", "employee_id", "policy_version", name="uq_policy_ack"),
    )


class HRServiceRequest(Base):
    """Internal employee helpdesk / Request Desk tickets."""
    __tablename__ = "hr_service_requests"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    ticket_number = Column(String, nullable=False, index=True)
    employee_id = Column(String, ForeignKey("hr_employees.id"), nullable=False, index=True)
    category = Column(String, nullable=False)  # employment_verification, salary_certificate, benefits, policy_query, general
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String, nullable=False, default="medium")  # low, medium, high, urgent
    status = Column(String, nullable=False, default="open", index=True)  # open, in_progress, awaiting_employee, resolved, closed
    assigned_to_id = Column(String, nullable=True)  # user id or agent identifier
    sla_due_at = Column(DateTime(timezone=True), nullable=True)
    ai_resolution_draft = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class HRPerformanceReview(Base):
    """Structured review record; AI may assist drafting but cannot set employment outcomes."""
    __tablename__ = "hr_performance_reviews"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(String, ForeignKey("hr_employees.id"), nullable=False, index=True)
    reviewer_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    cycle = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft")  # draft, submitted, acknowledged
    goals = Column(JSON, nullable=False, default=list)
    strengths = Column(Text, nullable=True)
    development_areas = Column(Text, nullable=True)
    employee_comments = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", "reviewer_user_id", "cycle", name="uq_hr_review_cycle_reviewer"),
    )


class HRCompensationChange(Base):
    """Compensation proposal requiring a separate authorized human approval."""
    __tablename__ = "hr_compensation_changes"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(String, ForeignKey("hr_employees.id"), nullable=False, index=True)
    requested_by_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    currency = Column(String(3), nullable=False)
    current_amount = Column(Numeric(12, 2), nullable=True)
    proposed_amount = Column(Numeric(12, 2), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pending_approval")  # pending_approval, approved, rejected, applied
    approver_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("proposed_amount > 0", name="chk_hr_comp_proposed_positive"),
    )


class HRLifecycleTask(Base):
    """Auditable onboarding/offboarding checklist task attached to a stable employee profile."""
    __tablename__ = "hr_lifecycle_tasks"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(String, ForeignKey("hr_employees.id"), nullable=False, index=True)
    lifecycle = Column(String, nullable=False)  # onboarding, offboarding
    task_key = Column(String, nullable=False)
    title = Column(String, nullable=False)
    owner_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(String, nullable=False, default="open")  # open, in_progress, completed, blocked
    verification_required = Column(Boolean, nullable=False, default=True)
    verified_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_note = Column(Text, nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", "lifecycle", "task_key", name="uq_hr_lifecycle_task"),
    )


class HRLifecycleCase(Base):
    """Governed onboarding/offboarding case with explicit initiator and final approver."""
    __tablename__ = "hr_lifecycle_cases"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(String, ForeignKey("hr_employees.id"), nullable=False, index=True)
    lifecycle = Column(String, nullable=False)
    initiated_by_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False, default="in_progress")
    reason = Column(Text, nullable=True)
    finalized_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    finalized_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", "lifecycle", "status", name="uq_hr_lifecycle_case_status"),
    )
