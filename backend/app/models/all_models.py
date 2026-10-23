import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.app.core.errors import AuditMutationForbiddenError
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ==============================================================================
# Enumerations
# ==============================================================================


class RoleEnum(str, enum.Enum):
    ADMIN = "admin"
    COORDINATOR = "coordinator"
    REPORTER = "reporter"
    AUDITOR = "auditor"


class ReportStatusEnum(str, enum.Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class LocationPrecisionEnum(str, enum.Enum):
    EXACT = "exact"
    APPROXIMATE = "approximate"
    AREA_ONLY = "area_only"
    UNKNOWN = "unknown"


class IncidentStatusEnum(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class PriorityEnum(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EvidenceStatusEnum(str, enum.Enum):
    UNVERIFIED = "unverified"
    PARTIALLY_CORROBORATED = "partially_corroborated"
    CONFLICTING = "conflicting"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    CORROBORATING = "corroborating"
    CORROBORATED = "corroborated"
    DISPROVEN = "disproven"


class LinkStatusEnum(str, enum.Enum):
    SUGGESTED = "suggested"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class TaskStatusEnum(str, enum.Enum):
    SUGGESTED = "suggested"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ==============================================================================
# Models
# ==============================================================================


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role: Mapped[RoleEnum] = mapped_column(
        SQLEnum(RoleEnum), default=RoleEnum.REPORTER, nullable=False, index=True
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    reports = relationship("Report", back_populates="user", passive_deletes=True)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    reference_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    incident_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    media_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    input_language: Mapped[str] = mapped_column(
        String(10), default="en", nullable=False, index=True
    )
    reporter_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reporter_contact: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location_claim: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location_precision: Mapped[LocationPrecisionEnum] = mapped_column(
        SQLEnum(LocationPrecisionEnum), default=LocationPrecisionEnum.UNKNOWN, nullable=False
    )
    coordinates_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    coordinates_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    processing_status: Mapped[ReportStatusEnum] = mapped_column(
        SQLEnum(ReportStatusEnum), default=ReportStatusEnum.RECEIVED, nullable=False, index=True
    )
    source_fingerprint: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True, doc="SHA-256 fingerprint for copied-claim detection"
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extraction_source: Mapped[str] = mapped_column(String(50), default="demo", nullable=False)
    extracted_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    extraction_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    coordinator_correction: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    correction_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    corrected_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    corrected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False, index=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="reports")
    links = relationship("IncidentReportLink", back_populates="report", passive_deletes=True)

    __table_args__ = (
        Index("ix_reports_status_submitted", "processing_status", "submitted_at"),
        Index("ix_reports_user_submitted", "user_id", "submitted_at"),
    )


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), default="waterlogging", nullable=False, index=True
    )
    status: Mapped[IncidentStatusEnum] = mapped_column(
        SQLEnum(IncidentStatusEnum), default=IncidentStatusEnum.OPEN, nullable=False, index=True
    )
    suggested_priority: Mapped[PriorityEnum] = mapped_column(
        SQLEnum(PriorityEnum), default=PriorityEnum.MEDIUM, nullable=False, index=True
    )
    approved_priority: Mapped[PriorityEnum] = mapped_column(
        SQLEnum(PriorityEnum), default=PriorityEnum.MEDIUM, nullable=False, index=True
    )
    priority_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority_override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location_name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    has_grounded_coordinates: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidence_status: Mapped[EvidenceStatusEnum] = mapped_column(
        SQLEnum(EvidenceStatusEnum),
        default=EvidenceStatusEnum.UNVERIFIED,
        nullable=False,
        index=True,
    )
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False
    )

    # Relationships with explicit NO-action foreign keys
    links = relationship("IncidentReportLink", back_populates="incident", passive_deletes=True)
    evidence_items = relationship("EvidenceItem", back_populates="incident", passive_deletes=True)
    tasks = relationship("Task", back_populates="incident", passive_deletes=True)
    recommendations = relationship(
        "TaskRecommendation", back_populates="incident", passive_deletes=True
    )

    __table_args__ = (
        Index("ix_incidents_status_priority", "status", "approved_priority"),
        Index("ix_incidents_category_created", "category", "created_at"),
    )


class IncidentReportLink(Base):
    __tablename__ = "incident_report_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    # Foreign keys without destructive cascades
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[LinkStatusEnum] = mapped_column(
        SQLEnum(LinkStatusEnum), default=LinkStatusEnum.SUGGESTED, nullable=False, index=True
    )
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    match_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False, index=True
    )

    incident = relationship("Incident", back_populates="links")
    report = relationship("Report", back_populates="links")

    __table_args__ = (
        UniqueConstraint("incident_id", "report_id", name="uq_incident_report_link"),
        Index("ix_links_incident_status", "incident_id", "status"),
    )


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    report_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_type: Mapped[str] = mapped_column(String(50), default="field_report", nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    claim_summary: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[EvidenceStatusEnum] = mapped_column(
        SQLEnum(EvidenceStatusEnum),
        default=EvidenceStatusEnum.UNVERIFIED,
        nullable=False,
        index=True,
    )
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False, index=True
    )

    incident = relationship("Incident", back_populates="evidence_items")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[PriorityEnum] = mapped_column(
        SQLEnum(PriorityEnum), default=PriorityEnum.MEDIUM, nullable=False, index=True
    )
    status: Mapped[TaskStatusEnum] = mapped_column(
        SQLEnum(TaskStatusEnum), default=TaskStatusEnum.SUGGESTED, nullable=False, index=True
    )
    assigned_to: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False
    )

    incident = relationship("Incident", back_populates="tasks")


class TaskRecommendation(Base):
    __tablename__ = "task_recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    recommended_title: Mapped[str] = mapped_column(String(255), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.85, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="proposed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    incident = relationship("Incident", back_populates="recommendations")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    actor: Mapped[str] = mapped_column(String(100), default="system", nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    before_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    after_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False, index=True
    )

    __table_args__ = (Index("ix_audit_entity_time", "entity_type", "entity_id", "timestamp"),)


# ==============================================================================
# Append-Only Immutability Enforcement for AuditEvent (SQLAlchemy Event Listeners)
# ==============================================================================


@event.listens_for(AuditEvent, "before_update")
def block_audit_update(mapper, connection, target):
    raise AuditMutationForbiddenError("UPDATE")


@event.listens_for(AuditEvent, "before_delete")
def block_audit_delete(mapper, connection, target):
    raise AuditMutationForbiddenError("DELETE")
