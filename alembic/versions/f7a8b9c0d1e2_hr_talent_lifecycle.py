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
    from app.models import hr as hr_models  # noqa: F401
    from app.models import executive as executive_models  # noqa: F401
    from app.models import objectives as objectives_models  # noqa: F401
    from app.models import decision_cases as decision_cases_models  # noqa: F401
    from app.models import mcp as mcp_models  # noqa: F401
    from app.models.base import Base

    PREREQ_TABLES = [
        "business_objectives",
        "objective_metrics",
        "workflow_events",
        "capability_registry",
        "budget_envelopes",
        "budget_reservations",
        "kill_switches",
        "policy_rules",
        "suppression_list",
        "plan_versions",
        "plan_nodes",
        "executive_approval_requests",
        "approval_decisions",
        "side_effect_outbox",
        "evidence_sources",
        "claim_clusters",
        "claim_support",
        "playbook_post_mortems",
        "decision_cases",
        "decision_alternatives",
        "decision_grants",
        "decision_outcome_reviews",
        "system_mcp_credentials",
        "dynamic_connectors",
        "dynamic_object_definitions",
        "mcp_capability_grants",
    ]

    all_tables = [Base.metadata.tables[name] for name in (PREREQ_TABLES + NEW_TABLES) if name in Base.metadata.tables]
    Base.metadata.create_all(bind=bind, tables=all_tables, checkfirst=True)

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "candidates" in tables:
        existing_candidate_cols = {c["name"] for c in inspector.get_columns("candidates")}
        if "phone" not in existing_candidate_cols:
            op.add_column("candidates", sa.Column("phone", sa.String(), nullable=True))
        if "merged_into_candidate_id" not in existing_candidate_cols:
            op.add_column("candidates", sa.Column("merged_into_candidate_id", sa.String(), nullable=True))
        indexes = {idx["name"] for idx in inspector.get_indexes("candidates")}
        if "ix_candidates_tenant_id" not in indexes:
            op.create_index("ix_candidates_tenant_id", "candidates", ["tenant_id"])

    if "executive_approval_requests" in tables:
        approval_cols = {c["name"]: c for c in inspector.get_columns("executive_approval_requests")}
        if "idempotency_key" not in approval_cols:
            op.add_column("executive_approval_requests", sa.Column("idempotency_key", sa.String(length=64), nullable=True))
        if bind.dialect.name == "postgresql":
            if approval_cols.get("plan_version_id", {}).get("nullable") is False:
                op.alter_column("executive_approval_requests", "plan_version_id", existing_type=sa.String(), nullable=True)
            existing_constraints = {c["name"] for c in inspector.get_check_constraints("executive_approval_requests")}
            if "chk_hr_plan_version_nullable" not in existing_constraints:
                op.create_check_constraint(
                    "chk_hr_plan_version_nullable",
                    "executive_approval_requests",
                    "plan_version_id IS NOT NULL OR capability_id LIKE 'hr.%'",
                )
            if "chk_hr_idempotency_key" not in existing_constraints:
                op.create_check_constraint(
                    "chk_hr_idempotency_key",
                    "executive_approval_requests",
                    "capability_id NOT LIKE 'hr.%' OR idempotency_key IS NOT NULL",
                )

    if "provider_usage" in tables:
        usage_cols = {c["name"] for c in inspector.get_columns("provider_usage")}
        if "resource_id" not in usage_cols:
            op.add_column("provider_usage", sa.Column("resource_id", sa.String(), nullable=True))
        if "correlation_id" not in usage_cols:
            op.add_column("provider_usage", sa.Column("correlation_id", sa.String(), nullable=True))

    if "data_retention_policies" in tables:
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
