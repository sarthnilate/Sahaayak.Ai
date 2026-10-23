"""Add authentication and report intake fields

Revision ID: 0002_auth_and_report_intake
Revises: 0001_initial_schema
Create Date: 2026-10-23 10:48:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002_auth_and_report_intake'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update users table with password & lockout tracking
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('hashed_password', sa.String(length=255), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))

    # 2. Update reports table with reference code, user ownership, and idempotency
    with op.batch_alter_table('reports') as batch_op:
        batch_op.add_column(sa.Column('reference_code', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('user_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('idempotency_key', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('incident_time', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_reports_reference_code', ['reference_code'], unique=False)
        batch_op.create_index('ix_reports_user_id', ['user_id'], unique=False)
        batch_op.create_index('ix_reports_idempotency_key', ['idempotency_key'], unique=True)
        batch_op.create_index('ix_reports_user_submitted', ['user_id', 'submitted_at'], unique=False)
        batch_op.create_foreign_key('fk_reports_user_id_users', 'users', ['user_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    with op.batch_alter_table('reports') as batch_op:
        batch_op.drop_constraint('fk_reports_user_id_users', type_='foreignkey')
        batch_op.drop_index('ix_reports_user_submitted')
        batch_op.drop_index('ix_reports_idempotency_key')
        batch_op.drop_index('ix_reports_user_id')
        batch_op.drop_index('ix_reports_reference_code')
        batch_op.drop_column('incident_time')
        batch_op.drop_column('idempotency_key')
        batch_op.drop_column('user_id')
        batch_op.drop_column('reference_code')

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('locked_until')
        batch_op.drop_column('failed_login_attempts')
        batch_op.drop_column('hashed_password')
