from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.app.schemas.extraction_schema import (
    CoordinatorCorrectionSchema,
    ExtractionMetadata,
    ExtractionResult,
    IncidentCategoryEnum,
    LanguageEnum,
    LocationPrecisionEnum,
    LocationSourceEnum,
    ReportExtractionSchema,
    SeverityEnum,
)
from pydantic import BaseModel, Field


# Extraction Structured Output Schema (Legacy alias maintained for backwards compatibility)
class ExtractionResultSchema(ReportExtractionSchema):
    pass


__all__ = [
    "ReportExtractionSchema",
    "ExtractionResultSchema",
    "CoordinatorCorrectionSchema",
    "ExtractionMetadata",
    "ExtractionResult",
    "IncidentCategoryEnum",
    "LanguageEnum",
    "LocationPrecisionEnum",
    "LocationSourceEnum",
    "SeverityEnum",
]


# User & Auth Schemas
class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)


class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    full_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    user: UserResponse
    message: str
    csrf_token: str


# Report Schemas
class ReportCreate(BaseModel):
    original_text: str = Field(..., min_length=3, max_length=2000)
    input_language: Optional[str] = "en"
    reporter_name: Optional[str] = "Anonymous Citizen"
    reporter_contact: Optional[str] = None
    location_claim: Optional[str] = None
    coordinates_lat: Optional[float] = None
    coordinates_lng: Optional[float] = None
    incident_time: Optional[datetime] = None
    idempotency_key: Optional[str] = None


class ReportResponse(BaseModel):
    id: str
    reference_code: Optional[str] = None
    user_id: Optional[str] = None
    original_text: str
    media_path: Optional[str] = None
    media_type: Optional[str] = None
    input_language: str
    reporter_name: Optional[str] = None
    reporter_contact: Optional[str] = None
    location_claim: Optional[str] = None
    coordinates_lat: Optional[float] = None
    coordinates_lng: Optional[float] = None
    location_precision: Optional[str] = "unknown"
    source_fingerprint: Optional[str] = None
    processing_status: str
    error_message: Optional[str] = None
    extraction_source: str
    extracted_json: Optional[Dict[str, Any]] = None
    extraction_metadata: Optional[Dict[str, Any]] = None
    coordinator_correction: Optional[Dict[str, Any]] = None
    correction_notes: Optional[str] = None
    corrected_by: Optional[str] = None
    corrected_at: Optional[datetime] = None
    submitted_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedReportsResponse(BaseModel):
    items: List[ReportResponse]
    total: int
    page: int
    limit: int
    pages: int


# Incident Schemas
class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    summary: str = Field(..., min_length=5)
    category: str = "waterlogging"
    suggested_priority: str = "medium"
    approved_priority: Optional[str] = "medium"
    priority_rationale: Optional[str] = None
    location_name: str = Field(..., min_length=1, max_length=255)
    location_description: Optional[str] = Field(None, max_length=500)
    district: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    district_source: Optional[str] = Field(None, pattern=r"^(reporter_stated|coordinator_set)$")
    state_source: Optional[str] = Field(None, pattern=r"^(reporter_stated|coordinator_set)$")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_precision: Optional[str] = Field(None, pattern=r"^(exact|approximate|area_only)$")
    coordinate_source: Optional[str] = Field(None, pattern=r"^(coordinator_pinned|simulated_seed)$")
    has_grounded_coordinates: bool = False
    is_simulated: bool = True
    source_report_id: Optional[str] = None


class IncidentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    summary: Optional[str] = Field(None, min_length=5)
    status: Optional[str] = None
    close_reason: Optional[str] = None
    approved_priority: Optional[str] = None
    priority_override_reason: Optional[str] = None
    evidence_status: Optional[str] = None
    location_name: Optional[str] = None
    location_description: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    district_source: Optional[str] = Field(None, pattern=r"^(reporter_stated|coordinator_set)$")
    state_source: Optional[str] = Field(None, pattern=r"^(reporter_stated|coordinator_set)$")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_precision: Optional[str] = Field(None, pattern=r"^(exact|approximate|area_only)$")
    coordinate_source: Optional[str] = Field(None, pattern=r"^(coordinator_pinned|simulated_seed)$")
    has_grounded_coordinates: Optional[bool] = None
    assigned_coordinator_id: Optional[str] = None
    category: Optional[str] = None
    version: Optional[int] = Field(None, description="Required for optimistic concurrency check")


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
    location_description: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    district_source: Optional[str] = None
    state_source: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    has_grounded_coordinates: bool
    location_precision: Optional[str] = None
    coordinate_source: Optional[str] = None
    evidence_status: str
    assigned_coordinator_id: Optional[str] = None
    close_reason: Optional[str] = None
    source_report_id: Optional[str] = None
    is_simulated: bool
    version: int = 1
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedIncidentsResponse(BaseModel):
    items: List[IncidentResponse]
    total: int
    page: int
    limit: int
    pages: int


class IncidentCreateFromReport(BaseModel):
    report_id: str
    title: str = Field(..., min_length=3, max_length=255)
    category: Optional[str] = None
    suggested_priority: Optional[str] = "medium"
    location_name: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    district_source: Optional[str] = None
    state_source: Optional[str] = None


class TimelineEvent(BaseModel):
    id: str
    event_type: str  # audit | evidence | link | task
    action: str
    actor: Optional[str] = None
    summary: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime


# Incident Report Link Schemas
class MatchSignalSchema(BaseModel):
    name: str
    weight: float
    matched: bool
    detail: str


class MatchCandidateResponse(BaseModel):
    incident_id: str
    incident_title: str
    incident_category: str
    incident_location: str
    incident_created_at: datetime
    band: str  # strong | possible | weak
    score: float
    rationale: str
    signals_for: List[MatchSignalSchema] = []
    signals_against: List[MatchSignalSchema] = []
    unknowns: List[str] = []
    is_same_origin: bool = False
    origin_fingerprint: Optional[str] = None
    existing_link_status: Optional[str] = None


class ReportMatchesResponse(BaseModel):
    report_id: str
    matches: List[MatchCandidateResponse]
    origin_group_id: Optional[str] = None
    total_candidates: int


class IncidentReportLinkResponse(BaseModel):
    id: str
    incident_id: str
    report_id: str
    status: str
    similarity_score: float
    match_band: Optional[str] = None
    signals_json: Optional[List[Dict[str, Any]]] = None
    match_rationale: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    report: Optional[ReportResponse] = None
    incident: Optional[IncidentResponse] = None

    class Config:
        from_attributes = True


class LinkReviewRequest(BaseModel):
    action: Optional[str] = Field("confirm", description="'confirm' or 'reject'")
    reviewer_notes: Optional[str] = None
    reviewed_by: Optional[str] = "coordinator@sahaayak.ai"


# Evidence Schemas
class EvidenceCreate(BaseModel):
    incident_id: Optional[str] = None
    report_id: Optional[str] = None
    evidence_type: str = "manual_attachment"
    source_type: str = "field_report"
    source_name: str = Field(..., min_length=2)
    source_description: Optional[str] = None
    source_url: Optional[str] = None
    source_timestamp: Optional[datetime] = None
    freshness: Optional[str] = None
    assessment: str = "supports"  # supports | contradicts | neutral | contextual | unassessed
    excerpt: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    reviewer_notes: Optional[str] = None
    independence_group: Optional[str] = None
    is_simulated: bool = False
    claim_summary: Optional[str] = None
    verification_status: Optional[str] = "unverified"


class EvidenceReviewRequest(BaseModel):
    assessment: Optional[str] = None
    verification_status: Optional[str] = None
    reviewer_notes: str = Field(..., min_length=1, description="Required coordinator review notes")


class IncidentEvidenceStatusOverrideRequest(BaseModel):
    status: str
    reviewer_notes: str = Field(..., min_length=1, description="Required coordinator review notes")


class EvidenceResponse(BaseModel):
    id: str
    incident_id: str
    report_id: Optional[str] = None
    evidence_type: str = "user_claim"
    source_type: str
    source_name: str
    source_description: Optional[str] = None
    source_url: Optional[str] = None
    source_timestamp: Optional[datetime] = None
    retrieved_at: Optional[datetime] = None
    freshness: Optional[str] = None
    assessment: str = "unassessed"
    excerpt: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    reviewer_notes: Optional[str] = None
    independence_group: Optional[str] = None
    is_simulated: bool
    claim_summary: str
    verification_status: str
    created_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MissingEvidenceGap(BaseModel):
    gap_type: str
    description: str
    severity: str  # high | medium | low


class VerificationState(BaseModel):
    verification_available: bool
    reason: str
    provider_name: Optional[str] = None


class IncidentEvidenceListResponse(BaseModel):
    incident_id: str
    items: List[EvidenceResponse]
    evidence_status: str
    suggested_status: str
    independent_source_count: int
    conflicts_count: int
    missing_evidence: List[MissingEvidenceGap]
    verification: VerificationState
    # Compatibility aliases
    evidence_items: Optional[List[EvidenceResponse]] = None
    independence_count: Optional[int] = None
    verification_available: Optional[bool] = None
    verification_unavailable_reason: Optional[str] = None


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
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
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
