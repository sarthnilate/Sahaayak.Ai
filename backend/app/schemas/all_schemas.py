from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Extraction Structured Output Schema
class ExtractionResultSchema(BaseModel):
    hazard_type: str = Field(description="Primary category, e.g. waterlogging, tree_fall, road_blocked, power_outage, unknown")
    severity: str = Field(description="critical, high, medium, low, unknown")
    water_depth_cm: Optional[int] = Field(None, description="Reported or inferred water depth in cm if waterlogging")
    location_name: Optional[str] = Field(None, description="Landmarks or street/area name extracted from text")
    approximate_lat: Optional[float] = Field(None, description="Extracted approximate latitude if mentioned or recognized")
    approximate_lng: Optional[float] = Field(None, description="Extracted approximate longitude if mentioned or recognized")
    has_grounded_coordinates: bool = Field(False, description="Whether coordinates are grounded or approximate")
    affected_infrastructure: List[str] = Field(default_factory=list, description="Roads, hospitals, metro, power lines, etc.")
    urgent_needs: List[str] = Field(default_factory=list, description="Evacuation, water pump, ambulance, rescue boat, tree cutter")
    casualties_flag: bool = Field(False, description="Whether human distress or injury is mentioned")
    confidence_score: float = Field(0.85, ge=0.0, le=1.0)
    sentiment_urgency: str = Field("medium", description="critical, urgent, moderate, low")
    language_detected: str = Field("en", description="en, hi, mr, unknown")
    summary: str = Field(description="One-sentence objective summary")

# Report Schemas
class ReportCreate(BaseModel):
    original_text: str = Field(..., min_length=3)
    input_language: Optional[str] = "en"
    reporter_name: Optional[str] = "Anonymous Citizen"
    reporter_contact: Optional[str] = None
    location_claim: Optional[str] = None
    coordinates_lat: Optional[float] = None
    coordinates_lng: Optional[float] = None

class ReportResponse(BaseModel):
    id: str
    original_text: str
    media_path: Optional[str] = None
    media_type: Optional[str] = None
    input_language: str
    reporter_name: Optional[str] = None
    reporter_contact: Optional[str] = None
    location_claim: Optional[str] = None
    coordinates_lat: Optional[float] = None
    coordinates_lng: Optional[float] = None
    processing_status: str
    error_message: Optional[str] = None
    extraction_source: str
    extracted_json: Optional[Dict[str, Any]] = None
    submitted_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Incident Schemas
class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=3)
    summary: str = Field(..., min_length=5)
    category: str = "waterlogging"
    suggested_priority: str = "medium"
    approved_priority: Optional[str] = "medium"
    priority_rationale: Optional[str] = None
    location_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    has_grounded_coordinates: bool = False
    is_simulated: bool = True

class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    approved_priority: Optional[str] = None
    priority_override_reason: Optional[str] = None
    evidence_status: Optional[str] = None

class IncidentResponse(BaseModel):
    id: str
    title: str
    summary: str
    category: str
    status: str
    suggested_priority: str
    approved_priority: str
    priority_rationale: Optional[str] = None
    priority_override_reason: Optional[str] = None
    location_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    has_grounded_coordinates: bool
    evidence_status: str
    is_simulated: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Incident Report Link Schemas
class IncidentReportLinkResponse(BaseModel):
    id: str
    incident_id: str
    report_id: str
    status: str
    similarity_score: float
    match_rationale: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    report: Optional[ReportResponse] = None

    class Config:
        from_attributes = True

class LinkReviewRequest(BaseModel):
    action: Optional[str] = Field("confirm", description="'confirm' or 'reject'")
    reviewer_notes: Optional[str] = None
    reviewed_by: Optional[str] = "coordinator@sahaayak.ai"

# Evidence Schemas
class EvidenceCreate(BaseModel):
    incident_id: str
    report_id: Optional[str] = None
    source_type: str = "field_report"
    source_name: str
    source_url: Optional[str] = None
    is_simulated: bool = True
    claim_summary: str
    verification_status: str = "unverified"
    reviewer_notes: Optional[str] = None

class EvidenceResponse(BaseModel):
    id: str
    incident_id: str
    report_id: Optional[str] = None
    source_type: str
    source_name: str
    source_url: Optional[str] = None
    is_simulated: bool
    claim_summary: str
    verification_status: str
    reviewer_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Task Schemas
class TaskCreate(BaseModel):
    incident_id: str
    title: str = Field(..., min_length=3)
    description: str
    priority: str = "medium"
    status: str = "suggested"
    assigned_to: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    approved_by: Optional[str] = None

class TaskResponse(BaseModel):
    id: str
    incident_id: str
    title: str
    description: str
    priority: str
    status: str
    assigned_to: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Audit Event Schema
class AuditEventResponse(BaseModel):
    id: str
    actor: str
    action: str
    entity_type: str
    entity_id: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

    class Config:
        from_attributes = True

# Health Response
class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    environment: str
    ai_provider: str
    database: str
    is_demo_mode: bool
