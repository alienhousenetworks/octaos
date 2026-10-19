"""HR talent lifecycle tables and candidate backfill.

Revision ID: f7a8b9c0d1e2
Revises: e1a2b3c4d5f6
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa


revision = "f7a8b9c0d1e2"
down_revision = "e1a2b3c4d5f6"
branch_labels = None
depends_on = None


NEW_TABLES = [
    "job_requisitions",
    "applications",
    "application_legacy_sources",
    "stage_transitions",
    "assessments",
    "evidence_facts",
    "inferences",
    "assessment_overrides",
    "interview_kits",
    "interviews",
    "interview_panelists",
    "interview_feedback",
    "salary_bands",
    "offer_template_versions",
    "offers",
    "employees",
    "onboarding_tasks",
    "provisioning_requests",
    "hr_documents",
    "hr_cost_entries",
    "hr_agent_invocations",
    "hr_workflow_measures",
    "hr_reminders",
    "skill_terms",
    "skill_evidence",
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    from app.models import hr as hr_models
    from app.models.base import Base

    tables = [Base.metadata.tables[name] for name in NEW_TABLES if name in Base.metadata.tables]
    Base.metadata.create_all(bind=bind, tables=tables)

    existing_candidate_cols = {c["name"] for c in inspector.get_columns("candidates")} if "candidates" in inspector.get_table_names() else set()
    if "phone" not in existing_candidate_cols:
        op.add_column("candidates", sa.Column("phone", sa.String(), nullable=True))
    if "merged_into_candidate_id" not in existing_candidate_cols:
        op.add_column("candidates", sa.Column("merged_into_candidate_id", sa.String(), nullable=True))

    indexes = {idx["name"] for idx in inspector.get_indexes("candidates")} if "candidates" in inspector.get_table_names() else set()
    if "ix_candidates_tenant_id" not in indexes:
        op.create_index("ix_candidates_tenant_id", "candidates", ["tenant_id"])

    approval_cols = {c["name"] for c in inspector.get_columns("executive_approval_requests")} if "executive_approval_requests" in inspector.get_table_names() else set()
    if approval_cols and "idempotency_key" not in approval_cols:
        op.add_column("executive_approval_requests", sa.Column("idempotency_key", sa.String(length=64), nullable=True))
    if approval_cols and bind.dialect.name == "postgresql":
        op.alter_column("executive_approval_requests", "plan_version_id", existing_type=sa.String(), nullable=True)
        op.create_check_constraint(
            "chk_hr_plan_version_nullable",
            "executive_approval_requests",
            "plan_version_id IS NOT NULL OR capability_id LIKE 'hr.%'",
        )
        op.create_check_constraint(
            "chk_hr_idempotency_key",
            "executive_approval_requests",
            "capability_id NOT LIKE 'hr.%' OR idempotency_key IS NOT NULL",
        )

    if "provider_usage" in inspector.get_table_names():
        usage_cols = {c["name"] for c in inspector.get_columns("provider_usage")}
        if "resource_id" not in usage_cols:
            op.add_column("provider_usage", sa.Column("resource_id", sa.String(), nullable=True))
        if "correlation_id" not in usage_cols:
            op.add_column("provider_usage", sa.Column("correlation_id", sa.String(), nullable=True))

    if "data_retention_policies" in inspector.get_table_names():
        retention_cols = {c["name"] for c in inspector.get_columns("data_retention_policies")}
        for name in ("candidates_days", "applications_days", "recruiting_docs_days", "identity_docs_days"):
            if name not in retention_cols:
                op.add_column("data_retention_policies", sa.Column(name, sa.Integer(), nullable=True))

    from sqlalchemy.orm import Session
    from app.services.hr.migration_map import backfill_candidates
    session = Session(bind=bind)
    try:
        backfill_candidates(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for name in reversed(NEW_TABLES):
        if name in inspector.get_table_names():
            op.drop_table(name)
    if "candidates" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("candidates")}
        if "merged_into_candidate_id" in cols:
            op.drop_column("candidates", "merged_into_candidate_id")
        if "phone" in cols:
            op.drop_column("candidates", "phone")
