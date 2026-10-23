"""0005_phase5_matching_fields

Revision ID: 0005_phase5_matching
Revises: 0004_incident_phase4
Create Date: 2026-10-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_phase5_matching"
down_revision: Union[str, None] = "0004_incident_phase4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("incident_report_links", schema=None) as batch_op:
        batch_op.add_column(sa.Column("match_band", sa.String(20), nullable=True))
        batch_op.add_column(sa.Column("signals_json", sa.JSON, nullable=True))
        batch_op.add_column(sa.Column("review_input_hash", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("reviewer_notes", sa.Text, nullable=True))
        batch_op.create_index("ix_links_match_band", ["match_band"])

    with op.batch_alter_table("reports", schema=None) as batch_op:
        batch_op.add_column(sa.Column("origin_group_id", sa.String(36), nullable=True))
        batch_op.create_index("ix_reports_origin_group", ["origin_group_id"])


def downgrade() -> None:
    with op.batch_alter_table("reports", schema=None) as batch_op:
        batch_op.drop_index("ix_reports_origin_group")
        batch_op.drop_column("origin_group_id")

    with op.batch_alter_table("incident_report_links", schema=None) as batch_op:
        batch_op.drop_index("ix_links_match_band")
        batch_op.drop_column("reviewer_notes")
        batch_op.drop_column("review_input_hash")
        batch_op.drop_column("signals_json")
        batch_op.drop_column("match_band")
