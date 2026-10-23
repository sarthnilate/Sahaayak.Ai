import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Float, Boolean, DateTime, ForeignKey, JSON, Integer
)
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(String(50), default="coordinator")  # coordinator, reporter, auditor
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    original_text = Column(Text, nullable=False)
    media_path = Column(String, nullable=True)
    media_type = Column(String, nullable=True)
    input_language = Column(String(10), default="en")  # en, hi, mr, unknown
    reporter_name = Column(String(100), nullable=True)
    reporter_contact = Column(String(100), nullable=True)
    location_claim = Column(String(255), nullable=True)
    coordinates_lat = Column(Float, nullable=True)
    coordinates_lng = Column(Float, nullable=True)
    processing_status = Column(String(50), default="received")  # received, processing, processed, needs_review, failed
    error_message = Column(Text, nullable=True)
    extraction_source = Column(String(50), default="demo")  # gemini, demo, manual
    extracted_json = Column(JSON, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    links = relationship("IncidentReportLink", back_populates="report", cascade="all, delete-orphan")

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    category = Column(String(50), default="waterlogging")  # waterlogging, tree_fall, road_blocked, power_outage, other
    status = Column(String(50), default="open")  # open, investigating, mitigating, resolved, closed
    suggested_priority = Column(String(20), default="medium")  # critical, high, medium, low
    approved_priority = Column(String(20), default="medium")  # critical, high, medium, low
    priority_rationale = Column(Text, nullable=True)
    priority_override_reason = Column(Text, nullable=True)
    location_name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    has_grounded_coordinates = Column(Boolean, default=False)
    evidence_status = Column(String(50), default="unverified")  # unverified, partially_corroborated, conflicting_evidence, corroborated
    is_simulated = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    links = relationship("IncidentReportLink", back_populates="incident", cascade="all, delete-orphan")
    evidence_items = relationship("EvidenceItem", back_populates="incident", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="incident", cascade="all, delete-orphan")

class IncidentReportLink(Base):
    __tablename__ = "incident_report_links"

    id = Column(String, primary_key=True, default=generate_uuid)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False)
    status = Column(String(50), default="suggested")  # suggested, confirmed, rejected
    similarity_score = Column(Float, default=0.0)
    match_rationale = Column(Text, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="links")
    report = relationship("Report", back_populates="links")

class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    report_id = Column(String, ForeignKey("reports.id"), nullable=True)
    source_type = Column(String(50), default="field_report")  # field_report, official_bulletin, sensor_gauge, community_claim
    source_name = Column(String(255), nullable=False)
    source_url = Column(String(500), nullable=True)
    is_simulated = Column(Boolean, default=True)
    claim_summary = Column(Text, nullable=False)
    verification_status = Column(String(50), default="unverified")  # corroborating, conflicting, unverified, disproven
    reviewer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="evidence_items")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), default="medium")  # critical, high, medium, low
    status = Column(String(50), default="suggested")  # suggested, pending, in_progress, completed, cancelled
    assigned_to = Column(String(100), nullable=True)
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    incident = relationship("Incident", back_populates="tasks")

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    actor = Column(String(100), default="system")
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)  # report, incident, task, link, evidence
    entity_id = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
