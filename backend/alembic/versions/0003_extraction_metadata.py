"""Add extraction metadata and coordinator correction fields to reports

Revision ID: 0003_extraction_metadata
Revises: 0002_auth_and_report_intake
Create Date: 2026-10-23 11:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0003_extraction_metadata'
down_revision: Union[str, None] = '0002_auth_and_report_intake'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('reports') as batch_op:
        batch_op.add_column(sa.Column('extraction_metadata', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('coordinator_correction', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('correction_notes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('corrected_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('corrected_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    with op.batch_alter_table('reports') as batch_op:
        batch_op.drop_column('attempt_count')
        batch_op.drop_column('corrected_at')
        batch_op.drop_column('corrected_by')
        batch_op.drop_column('correction_notes')
        batch_op.drop_column('coordinator_correction')
        batch_op.drop_column('extraction_metadata')
