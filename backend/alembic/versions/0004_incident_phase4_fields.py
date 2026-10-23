"""0004_incident_phase4_fields

Revision ID: 0004_incident_phase4
Revises: 0003_extraction_metadata
Create Date: 2026-10-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_incident_phase4"
down_revision: Union[str, None] = "0003_extraction_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("incidents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("location_description", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("district", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("state", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("district_source", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("state_source", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("location_precision", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("coordinate_source", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("assigned_coordinator_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("close_reason", sa.Text, nullable=True))
        batch_op.add_column(sa.Column("source_report_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("version", sa.Integer, nullable=False, server_default="1"))
        batch_op.create_index("ix_incidents_district", ["district"])
        batch_op.create_index("ix_incidents_state", ["state"])
        batch_op.create_index("ix_incidents_assigned", ["assigned_coordinator_id"])


def downgrade() -> None:
    with op.batch_alter_table("incidents", schema=None) as batch_op:
        batch_op.drop_index("ix_incidents_assigned")
        batch_op.drop_index("ix_incidents_state")
        batch_op.drop_index("ix_incidents_district")
        batch_op.drop_column("version")
        batch_op.drop_column("source_report_id")
        batch_op.drop_column("close_reason")
        batch_op.drop_column("assigned_coordinator_id")
        batch_op.drop_column("coordinate_source")
        batch_op.drop_column("location_precision")
        batch_op.drop_column("state_source")
        batch_op.drop_column("district_source")
        batch_op.drop_column("state")
        batch_op.drop_column("district")
        batch_op.drop_column("location_description")
