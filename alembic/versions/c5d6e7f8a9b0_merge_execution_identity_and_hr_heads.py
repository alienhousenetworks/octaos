"""Merge the HR lifecycle and canonical execution identity migration heads.

Revision ID: c5d6e7f8a9b0
Revises: f7a8b9c0d1e2, b3c4d5e6f7a8
"""
revision = "c5d6e7f8a9b0"
down_revision = ("f7a8b9c0d1e2", "b3c4d5e6f7a8")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision: both parent branches have already applied their schema changes.
    pass


def downgrade() -> None:
    # Keep this merge reversible without dropping either branch's schema.
    pass
