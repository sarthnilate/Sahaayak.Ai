"""0006_phase6_evidence_fields

Revision ID: 0006_phase6_evidence
Revises: 0005_phase5_matching
Create Date: 2026-10-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_phase6_evidence"
down_revision: Union[str, None] = "0005_phase5_matching"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("evidence_items", schema=None) as batch_op:
        batch_op.add_column(sa.Column("evidence_type", sa.String(50), server_default="user_claim", nullable=False))
        batch_op.add_column(sa.Column("source_description", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("freshness", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("assessment", sa.String(50), server_default="unassessed", nullable=False))
        batch_op.add_column(sa.Column("excerpt", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("metadata_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("independence_group", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("created_by", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("reviewed_by", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_evidence_items_evidence_type", ["evidence_type"])
        batch_op.create_index("ix_evidence_items_assessment", ["assessment"])
        batch_op.create_index("ix_evidence_items_independence_group", ["independence_group"])


def downgrade() -> None:
    with op.batch_alter_table("evidence_items", schema=None) as batch_op:
        batch_op.drop_index("ix_evidence_items_independence_group")
        batch_op.drop_index("ix_evidence_items_assessment")
        batch_op.drop_index("ix_evidence_items_evidence_type")
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("reviewed_by")
        batch_op.drop_column("created_by")
        batch_op.drop_column("independence_group")
        batch_op.drop_column("metadata_json")
        batch_op.drop_column("excerpt")
        batch_op.drop_column("assessment")
        batch_op.drop_column("freshness")
        batch_op.drop_column("retrieved_at")
        batch_op.drop_column("source_timestamp")
        batch_op.drop_column("source_description")
        batch_op.drop_column("evidence_type")
