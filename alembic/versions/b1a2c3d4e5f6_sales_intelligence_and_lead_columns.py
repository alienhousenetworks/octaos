"""Add sales intelligence tables and sync lead, content_post, and suppression columns.

Revision ID: b1a2c3d4e5f6
Revises: a9b8c7d6e5f4
Create Date: 2026-10-20
"""
from alembic import op
import sqlalchemy as sa


revision = "b1a2c3d4e5f6"
down_revision = "a9b8c7d6e5f4"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # 1. Create Sales Intelligence canonical tables if not already present
    from app.models.base import Base
    import app.models.sales_intelligence  # noqa: F401

    sales_tables = [
        "sales_companies",
        "sales_account_contacts",
        "sales_signal_evidence",
        "sales_signals",
        "sales_company_technologies",
        "sales_employment_records",
        "sales_contact_verifications",
        "sales_source_runs",
        "sales_source_records",
        "sales_opportunities",
        "sales_outreach_permissions",
        "sales_source_costs",
        "sales_source_outcomes",
    ]

    missing_tables = [
        Base.metadata.tables[name]
        for name in sales_tables
        if name in Base.metadata.tables and name not in tables
    ]
    if missing_tables:
        Base.metadata.create_all(bind=bind, tables=missing_tables, checkfirst=True)

    # 2. Add missing columns to leads
    inspector = sa.inspect(bind)
    current_tables = set(inspector.get_table_names())
    if "leads" in current_tables:
        lead_cols = {c["name"] for c in inspector.get_columns("leads")}
        with op.batch_alter_table("leads") as batch_op:
            if "sales_company_id" not in lead_cols:
                batch_op.add_column(sa.Column("sales_company_id", sa.String(), nullable=True))
                batch_op.create_index("ix_leads_sales_company_id", ["sales_company_id"], unique=False)
            if "sales_contact_id" not in lead_cols:
                batch_op.add_column(sa.Column("sales_contact_id", sa.String(), nullable=True))
            if "sales_opportunity_id" not in lead_cols:
                batch_op.add_column(sa.Column("sales_opportunity_id", sa.String(), nullable=True))

    # 3. Add missing columns to content_posts
    if "content_posts" in current_tables:
        post_cols = {c["name"] for c in inspector.get_columns("content_posts")}
        with op.batch_alter_table("content_posts") as batch_op:
            if "used_model" not in post_cols:
                batch_op.add_column(sa.Column("used_model", sa.String(), nullable=True))
            if "fallback_reason" not in post_cols:
                batch_op.add_column(sa.Column("fallback_reason", sa.Text(), nullable=True))
            if "cost_usd" not in post_cols:
                batch_op.add_column(sa.Column("cost_usd", sa.Float(), nullable=True, server_default="0"))

    # 4. Add missing columns to suppression_records
    if "suppression_records" in current_tables:
        supp_cols = {c["name"] for c in inspector.get_columns("suppression_records")}
        with op.batch_alter_table("suppression_records") as batch_op:
            if "channel" not in supp_cols:
                batch_op.add_column(sa.Column("channel", sa.String(), nullable=True))
            if "jurisdiction" not in supp_cols:
                batch_op.add_column(sa.Column("jurisdiction", sa.String(), nullable=True))
            if "scope" not in supp_cols:
                batch_op.add_column(sa.Column("scope", sa.String(), nullable=True, server_default="tenant"))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "suppression_records" in tables:
        with op.batch_alter_table("suppression_records") as batch_op:
            try:
                batch_op.drop_column("scope")
            except Exception:
                pass
            try:
                batch_op.drop_column("jurisdiction")
            except Exception:
                pass
            try:
                batch_op.drop_column("channel")
            except Exception:
                pass

    if "content_posts" in tables:
        with op.batch_alter_table("content_posts") as batch_op:
            try:
                batch_op.drop_column("cost_usd")
            except Exception:
                pass
            try:
                batch_op.drop_column("fallback_reason")
            except Exception:
                pass
            try:
                batch_op.drop_column("used_model")
            except Exception:
                pass

    if "leads" in tables:
        with op.batch_alter_table("leads") as batch_op:
            try:
                batch_op.drop_index("ix_leads_sales_company_id")
            except Exception:
                pass
            try:
                batch_op.drop_column("sales_opportunity_id")
            except Exception:
                pass
            try:
                batch_op.drop_column("sales_contact_id")
            except Exception:
                pass
            try:
                batch_op.drop_column("sales_company_id")
            except Exception:
                pass

    sales_tables = [
        "sales_source_outcomes",
        "sales_source_costs",
        "sales_outreach_permissions",
        "sales_opportunities",
        "sales_source_records",
        "sales_source_runs",
        "sales_contact_verifications",
        "sales_employment_records",
        "sales_company_technologies",
        "sales_signals",
        "sales_signal_evidence",
        "sales_account_contacts",
        "sales_companies",
    ]
    for tbl in sales_tables:
        if tbl in tables:
            try:
                op.drop_table(tbl)
            except Exception:
                pass
