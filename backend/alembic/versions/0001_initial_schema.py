"""Initial complete database schema with indexes, enums and audit immutability

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-23 10:27:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Users Table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='coordinator'),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_role', 'users', ['role'], unique=False)

    # 2. Reports Table
    op.create_table(
        'reports',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('original_text', sa.Text(), nullable=False),
        sa.Column('media_path', sa.String(length=500), nullable=True),
        sa.Column('media_type', sa.String(length=100), nullable=True),
        sa.Column('input_language', sa.String(length=10), nullable=False, server_default='en'),
        sa.Column('reporter_name', sa.String(length=100), nullable=True),
        sa.Column('reporter_contact', sa.String(length=100), nullable=True),
        sa.Column('location_claim', sa.String(length=255), nullable=True),
        sa.Column('location_precision', sa.String(length=50), nullable=False, server_default='unknown'),
        sa.Column('coordinates_lat', sa.Float(), nullable=True),
        sa.Column('coordinates_lng', sa.Float(), nullable=True),
        sa.Column('processing_status', sa.String(length=50), nullable=False, server_default='received'),
        sa.Column('source_fingerprint', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('extraction_source', sa.String(length=50), nullable=False, server_default='demo'),
        sa.Column('extracted_json', sa.JSON(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('ix_reports_processing_status', 'reports', ['processing_status'], unique=False)
    op.create_index('ix_reports_submitted_at', 'reports', ['submitted_at'], unique=False)
    op.create_index('ix_reports_input_language', 'reports', ['input_language'], unique=False)
    op.create_index('ix_reports_source_fingerprint', 'reports', ['source_fingerprint'], unique=False)
    op.create_index('ix_reports_status_submitted', 'reports', ['processing_status', 'submitted_at'], unique=False)

    # 3. Incidents Table
    op.create_table(
        'incidents',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='waterlogging'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='open'),
        sa.Column('suggested_priority', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('approved_priority', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('priority_rationale', sa.Text(), nullable=True),
        sa.Column('priority_override_reason', sa.Text(), nullable=True),
        sa.Column('location_name', sa.String(length=255), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('has_grounded_coordinates', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('evidence_status', sa.String(length=50), nullable=False, server_default='unverified'),
        sa.Column('is_simulated', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_incidents_category', 'incidents', ['category'], unique=False)
    op.create_index('ix_incidents_status', 'incidents', ['status'], unique=False)
    op.create_index('ix_incidents_suggested_priority', 'incidents', ['suggested_priority'], unique=False)
    op.create_index('ix_incidents_approved_priority', 'incidents', ['approved_priority'], unique=False)
    op.create_index('ix_incidents_evidence_status', 'incidents', ['evidence_status'], unique=False)
    op.create_index('ix_incidents_created_at', 'incidents', ['created_at'], unique=False)
    op.create_index('ix_incidents_status_priority', 'incidents', ['status', 'approved_priority'], unique=False)
    op.create_index('ix_incidents_category_created', 'incidents', ['category', 'created_at'], unique=False)

    # 4. Incident Report Links Table (with unique constraint and no destructive cascade)
    op.create_table(
        'incident_report_links',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('incident_id', sa.String(length=36), sa.ForeignKey('incidents.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('report_id', sa.String(length=36), sa.ForeignKey('reports.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='suggested'),
        sa.Column('similarity_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('match_rationale', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.String(length=100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('incident_id', 'report_id', name='uq_incident_report_link')
    )
    op.create_index('ix_incident_report_links_incident_id', 'incident_report_links', ['incident_id'], unique=False)
    op.create_index('ix_incident_report_links_report_id', 'incident_report_links', ['report_id'], unique=False)
    op.create_index('ix_incident_report_links_status', 'incident_report_links', ['status'], unique=False)
    op.create_index('ix_incident_report_links_created_at', 'incident_report_links', ['created_at'], unique=False)
    op.create_index('ix_links_incident_status', 'incident_report_links', ['incident_id', 'status'], unique=False)

    # 5. Evidence Items Table
    op.create_table(
        'evidence_items',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('incident_id', sa.String(length=36), sa.ForeignKey('incidents.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('report_id', sa.String(length=36), sa.ForeignKey('reports.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=False, server_default='field_report'),
        sa.Column('source_name', sa.String(length=255), nullable=False),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('is_simulated', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('claim_summary', sa.Text(), nullable=False),
        sa.Column('verification_status', sa.String(length=50), nullable=False, server_default='unverified'),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_evidence_items_incident_id', 'evidence_items', ['incident_id'], unique=False)
    op.create_index('ix_evidence_items_report_id', 'evidence_items', ['report_id'], unique=False)
    op.create_index('ix_evidence_items_verification_status', 'evidence_items', ['verification_status'], unique=False)
    op.create_index('ix_evidence_items_created_at', 'evidence_items', ['created_at'], unique=False)

    # 6. Tasks Table
    op.create_table(
        'tasks',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('incident_id', sa.String(length=36), sa.ForeignKey('incidents.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='suggested'),
        sa.Column('assigned_to', sa.String(length=100), nullable=True),
        sa.Column('approved_by', sa.String(length=100), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_tasks_incident_id', 'tasks', ['incident_id'], unique=False)
    op.create_index('ix_tasks_status', 'tasks', ['status'], unique=False)
    op.create_index('ix_tasks_priority', 'tasks', ['priority'], unique=False)
    op.create_index('ix_tasks_created_at', 'tasks', ['created_at'], unique=False)

    # 7. Task Recommendations Table
    op.create_table(
        'task_recommendations',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('incident_id', sa.String(length=36), sa.ForeignKey('incidents.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('recommended_title', sa.String(length=255), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.85'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='proposed'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_task_recommendations_incident_id', 'task_recommendations', ['incident_id'], unique=False)

    # 8. Audit Events Table (Append-Only)
    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('actor', sa.String(length=100), nullable=False, server_default='system'),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=36), nullable=False),
        sa.Column('before_state', sa.JSON(), nullable=True),
        sa.Column('after_state', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_audit_events_actor', 'audit_events', ['actor'], unique=False)
    op.create_index('ix_audit_events_action', 'audit_events', ['action'], unique=False)
    op.create_index('ix_audit_events_entity_type', 'audit_events', ['entity_type'], unique=False)
    op.create_index('ix_audit_events_entity_id', 'audit_events', ['entity_id'], unique=False)
    op.create_index('ix_audit_events_timestamp', 'audit_events', ['timestamp'], unique=False)
    op.create_index('ix_audit_entity_time', 'audit_events', ['entity_type', 'entity_id', 'timestamp'], unique=False)

    # Postgres Append-Only Trigger
    bind = op.get_bind()
    if bind and bind.dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION audit_events_immutable_trigger()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'Audit events are immutable and cannot be updated or deleted';
            END;
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER enforce_audit_events_immutable
            BEFORE UPDATE OR DELETE ON audit_events
            FOR EACH ROW EXECUTE FUNCTION audit_events_immutable_trigger();
        """)

def downgrade() -> None:
    bind = op.get_bind()
    if bind and bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS enforce_audit_events_immutable ON audit_events;")
        op.execute("DROP FUNCTION IF EXISTS audit_events_immutable_trigger();")

    op.drop_table('audit_events')
    op.drop_table('task_recommendations')
    op.drop_table('tasks')
    op.drop_table('evidence_items')
    op.drop_table('incident_report_links')
    op.drop_table('incidents')
    op.drop_table('reports')
    op.drop_table('users')
