"""Make company_email unique

Revision ID: 375b132b27a8
Revises: 8d96c17e522c
Create Date: 2026-06-16 18:44:00.501462

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '375b132b27a8'
down_revision: Union[str, None] = '8d96c17e522c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('tenants', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_tenants_company_email'), ['company_email'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('tenants', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tenants_company_email'))
