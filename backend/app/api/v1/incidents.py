"""
Phase 4: Incident management API — state machine, RBAC, pagination, timeline, optimistic concurrency.
"""

import math
from datetime import datetime, timezone
from typing import List, Optional

from backend.app.core.auth import get_current_user, get_current_user_optional, require_role
from backend.app.core.errors import (
    BadRequestError,
    ConflictError,
    EntityNotFoundError,
    InvalidStateTransitionError,
)
from backend.app.db.session import get_db
from backend.app.models.all_models import (
    AuditEvent,
    EvidenceItem,
    Incident,
    IncidentReportLink,
    IncidentStatusEnum,
    Report,
    RoleEnum,
    Task,
    User,
)
from backend.app.schemas.all_schemas import (
    EvidenceResponse,
    IncidentCreate,
    IncidentCreateFromReport,
    IncidentResponse,
    IncidentUpdate,
    LinkReviewRequest,
    PaginatedIncidentsResponse,
    TaskResponse,
    TimelineEvent,
)
from backend.app.services.audit.service import AuditService
from backend.app.services.incidents import (
    CLOSE_REQUIRES_REASON,
    OPEN_TASK_STATUSES,
    get_allowed_transitions,
    is_valid_transition,
)
from backend.app.services.matching.service import matching_service
from backend.app.services.prioritization.service import prioritization_service
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _validate_coordinates(lat: Optional[float], lng: Optional[float],
                          precision: Optional[str], source: Optional[str]) -> None:
    """Reject coordinates without precision/source; reject out-of-range lat/lng."""
    if lat is not None or lng is not None:
        if lat is None or lng is None:
            raise BadRequestError(
                message="Both latitude and longitude must be provided together",
                error_code="COORDS_INCOMPLETE",
            )
        if not (-90.0 <= lat <= 90.0):
            raise BadRequestError(
                message=f"Latitude {lat} is out of range [-90, 90]",
                error_code="COORDS_OUT_OF_RANGE",
            )
        if not (-180.0 <= lng <= 180.0):
            raise BadRequestError(
                message=f"Longitude {lng} is out of range [-180, 180]",
                error_code="COORDS_OUT_OF_RANGE",
            )
        if not precision:
            raise BadRequestError(
                message="location_precision is required when providing coordinates",
                error_code="COORDS_MISSING_PRECISION",
            )
        if not source:
            raise BadRequestError(
                message="coordinate_source is required when providing coordinates (coordinator_pinned or simulated_seed)",
                error_code="COORDS_MISSING_SOURCE",
            )
        if source not in ("coordinator_pinned", "simulated_seed"):
            raise BadRequestError(
                message=f"coordinate_source must be 'coordinator_pinned' or 'simulated_seed', got '{source}'",
                error_code="COORDS_INVALID_SOURCE",
            )


def _get_incident_or_404(db: Session, incident_id: str) -> Incident:
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise EntityNotFoundError(
            message=f"Incident '{incident_id}' not found",
            error_code="INCIDENT_NOT_FOUND",
        )
    return incident


# ──────────────────────────────────────────────────────────────────────────────
# LIST — with pagination, filters, sorting, text search, indexed
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/incidents", response_model=PaginatedIncidentsResponse)
def list_incidents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    evidence_status: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    search: Optional[str] = Query(None, max_length=200),
    sort_by: Optional[str] = Query("created_at", pattern=r"^(created_at|updated_at|approved_priority|status)$"),
    sort_order: Optional[str] = Query("desc", pattern=r"^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    query = db.query(Incident)

    if status:
        query = query.filter(Incident.status == status)
    if category:
        query = query.filter(Incident.category == category)
    if priority:
        query = query.filter(Incident.approved_priority == priority)
    if evidence_status:
        query = query.filter(Incident.evidence_status == evidence_status)
    if district:
        query = query.filter(Incident.district == district)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Incident.title.ilike(pattern),
                Incident.summary.ilike(pattern),
                Incident.location_name.ilike(pattern),
                Incident.district.ilike(pattern),
            )
        )

    total = query.count()

    sort_col = getattr(Incident, sort_by or "created_at", Incident.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    items = query.offset((page - 1) * limit).limit(limit).all()
    pages = max(1, math.ceil(total / limit))

    return PaginatedIncidentsResponse(
        items=[IncidentResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


# ──────────────────────────────────────────────────────────────────────────────
# CREATE
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/incidents", response_model=IncidentResponse)
def create_incident(
    payload: IncidentCreate,
    current_user: User = Depends(require_role(RoleEnum.COORDINATOR, RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    _validate_coordinates(payload.latitude, payload.longitude,
                          payload.location_precision, payload.coordinate_source)

    incident = Incident(
        title=payload.title,
        summary=payload.summary,
        category=payload.category,
        status="open",
        suggested_priority=payload.suggested_priority,
        approved_priority=payload.approved_priority or payload.suggested_priority,
        priority_rationale=payload.priority_rationale or "Initial coordinator assessment",
        location_name=payload.location_name,
        location_description=payload.location_description,
        district=payload.district,
        state=payload.state,
        district_source=payload.district_source,
        state_source=payload.state_source,
        latitude=payload.latitude,
        longitude=payload.longitude,
        location_precision=payload.location_precision,
        coordinate_source=payload.coordinate_source,
        has_grounded_coordinates=payload.has_grounded_coordinates,
        is_simulated=payload.is_simulated,
        source_report_id=payload.source_report_id,
        assigned_coordinator_id=current_user.id,
        version=1,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    AuditService.record(
        db=db,
        actor=current_user.email,
        action="INCIDENT_CREATED",
        entity_type="incident",
        entity_id=incident.id,
        after={"title": incident.title, "priority": incident.approved_priority.value
               if hasattr(incident.approved_priority, 'value') else str(incident.approved_priority)},
    )

    return incident


# ──────────────────────────────────────────────────────────────────────────────
# CREATE FROM REPORT (idempotent + audited)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/incidents/from-report", response_model=IncidentResponse)
def create_incident_from_report(
    payload: IncidentCreateFromReport,
    current_user: User = Depends(require_role(RoleEnum.COORDINATOR, RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == payload.report_id).first()
    if not report:
        raise EntityNotFoundError(
            message=f"Report '{payload.report_id}' not found",
            error_code="REPORT_NOT_FOUND",
        )

    # Idempotent: if incident already created from this report, return it
    existing = db.query(Incident).filter(Incident.source_report_id == payload.report_id).first()
    if existing:
        return existing

    extracted = report.extracted_json or {}
    category = payload.category or extracted.get("category", extracted.get("hazard_type", "unknown"))
    location = payload.location_name or extracted.get("reported_location_text") or report.location_claim or "Location not specified"

    incident = Incident(
        title=payload.title,
        summary=extracted.get("short_summary", extracted.get("summary", report.original_text[:200])),
        category=category,
        status="open",
        suggested_priority=payload.suggested_priority or "medium",
        approved_priority=payload.suggested_priority or "medium",
        priority_rationale="Created from citizen report extraction",
        location_name=location,
        district=payload.district,
        state=payload.state,
        district_source=payload.district_source,
        state_source=payload.state_source,
        is_simulated=False,
        source_report_id=report.id,
        assigned_coordinator_id=current_user.id,
        version=1,
    )
    db.add(incident)
    db.flush()

    # Automatically link the report
    link = IncidentReportLink(
        incident_id=incident.id,
        report_id=report.id,
        status="confirmed",
        similarity_score=1.0,
        match_rationale="Source report for incident creation",
        reviewed_by=current_user.email,
        reviewed_at=datetime.now(timezone.utc),
    )
    db.add(link)
    db.commit()
    db.refresh(incident)

    AuditService.record(
        db=db,
        actor=current_user.email,
        action="INCIDENT_CREATED_FROM_REPORT",
        entity_type="incident",
        entity_id=incident.id,
        after={"report_id": report.id, "title": incident.title},
    )

    return incident


# ──────────────────────────────────────────────────────────────────────────────
# GET DETAIL
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/incidents/{incident_id}")
def get_incident_detail(incident_id: str, db: Session = Depends(get_db)):
    incident = _get_incident_or_404(db, incident_id)

    links = (
        db.query(IncidentReportLink)
        .options(joinedload(IncidentReportLink.report))
        .filter(IncidentReportLink.incident_id == incident_id)
        .all()
    )
    evidence_items = db.query(EvidenceItem).filter(EvidenceItem.incident_id == incident_id).all()
    tasks = db.query(Task).filter(Task.incident_id == incident_id).all()
    audit_events = (
        db.query(AuditEvent)
        .filter(AuditEvent.entity_id == incident_id)
        .order_by(AuditEvent.timestamp.desc())
        .limit(50)
        .all()
    )

    return {
        "incident": IncidentResponse.model_validate(incident),
        "links": [
            {
                "id": lk.id,
                "incident_id": lk.incident_id,
                "report_id": lk.report_id,
                "status": lk.status.value if hasattr(lk.status, 'value') else lk.status,
                "similarity_score": lk.similarity_score,
                "match_rationale": lk.match_rationale,
                "reviewed_by": lk.reviewed_by,
                "reviewed_at": lk.reviewed_at,
                "report": lk.report,
            }
            for lk in links
        ],
        "evidence_items": [EvidenceResponse.model_validate(e) for e in evidence_items],
        "tasks": [TaskResponse.model_validate(t) for t in tasks],
        "audit_events": [
            {
                "id": a.id,
                "actor": a.actor,
                "action": a.action,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "before_state": a.before_state,
                "after_state": a.after_state,
                "timestamp": a.timestamp,
            }
            for a in audit_events
        ],
        "allowed_transitions": get_allowed_transitions(incident.status),
    }


# ──────────────────────────────────────────────────────────────────────────────
# TIMELINE — merges audit + evidence + link + task events chronologically
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/incidents/{incident_id}/timeline", response_model=List[TimelineEvent])
def get_incident_timeline(incident_id: str, db: Session = Depends(get_db)):
    _get_incident_or_404(db, incident_id)

    events: list[TimelineEvent] = []

    # 1. Audit events for this incident
    audit_rows = (
        db.query(AuditEvent)
        .filter(AuditEvent.entity_id == incident_id)
        .all()
    )
    for a in audit_rows:
        events.append(TimelineEvent(
            id=a.id,
            event_type="audit",
            action=a.action,
            actor=a.actor,
            summary=f"{a.actor} performed {a.action}",
            details=a.after_state,
            timestamp=a.timestamp,
        ))

    # 2. Evidence items
    evidence_rows = db.query(EvidenceItem).filter(EvidenceItem.incident_id == incident_id).all()
    for e in evidence_rows:
        events.append(TimelineEvent(
            id=e.id,
            event_type="evidence",
            action=f"evidence_{e.verification_status.value if hasattr(e.verification_status, 'value') else e.verification_status}",
            actor=e.source_name,
            summary=f"Evidence from {e.source_name}: {e.claim_summary[:120]}",
            details={"source_type": e.source_type, "verification_status":
                      e.verification_status.value if hasattr(e.verification_status, 'value') else str(e.verification_status)},
            timestamp=e.created_at,
        ))

    # 3. Report links
    link_rows = (
        db.query(IncidentReportLink)
        .filter(IncidentReportLink.incident_id == incident_id)
        .all()
    )
    for lk in link_rows:
        status_val = lk.status.value if hasattr(lk.status, 'value') else str(lk.status)
        events.append(TimelineEvent(
            id=lk.id,
            event_type="link",
            action=f"report_{status_val}",
            actor=lk.reviewed_by,
            summary=f"Report link {status_val} (score: {lk.similarity_score:.2f})",
            details={"report_id": lk.report_id, "rationale": lk.match_rationale},
            timestamp=lk.reviewed_at or lk.created_at,
        ))

    # 4. Tasks
    task_rows = db.query(Task).filter(Task.incident_id == incident_id).all()
    for t in task_rows:
        status_val = t.status.value if hasattr(t.status, 'value') else str(t.status)
        events.append(TimelineEvent(
            id=t.id,
            event_type="task",
            action=f"task_{status_val}",
            actor=t.assigned_to or t.approved_by,
            summary=f"Task '{t.title}' — {status_val}",
            details={"priority": t.priority.value if hasattr(t.priority, 'value') else str(t.priority)},
            timestamp=t.updated_at,
        ))

    events.sort(key=lambda e: e.timestamp, reverse=True)
    return events


# ──────────────────────────────────────────────────────────────────────────────
# PATCH — with state machine, optimistic concurrency, coordinate validation
# ──────────────────────────────────────────────────────────────────────────────

@router.patch("/incidents/{incident_id}", response_model=IncidentResponse)
def update_incident(
    incident_id: str,
    payload: IncidentUpdate,
    current_user: User = Depends(require_role(RoleEnum.COORDINATOR, RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    incident = _get_incident_or_404(db, incident_id)

    # Optimistic concurrency check
    if payload.version is not None and payload.version != incident.version:
        raise ConflictError(
            message=f"Concurrency conflict: expected version {payload.version}, current is {incident.version}. Reload and retry.",
            error_code="OPTIMISTIC_CONCURRENCY_CONFLICT",
        )

    before_state = {
        "status": incident.status.value if hasattr(incident.status, 'value') else str(incident.status),
        "priority": incident.approved_priority.value if hasattr(incident.approved_priority, 'value') else str(incident.approved_priority),
        "version": incident.version,
    }

    # Status transition with state machine enforcement
    if payload.status is not None:
        try:
            target_status = IncidentStatusEnum(payload.status)
        except ValueError:
            raise BadRequestError(
                message=f"Invalid incident status '{payload.status}'",
                error_code="INVALID_STATUS",
            )

        if not is_valid_transition(incident.status, target_status):
            raise InvalidStateTransitionError(
                message=f"Cannot transition from '{incident.status.value}' to '{payload.status}'. Allowed: {get_allowed_transitions(incident.status)}",
                error_code="INVALID_STATE_TRANSITION",
            )

        # Close requires reason and check for open tasks
        if target_status in CLOSE_REQUIRES_REASON:
            if not payload.close_reason:
                raise BadRequestError(
                    message="A close_reason is required when closing an incident",
                    error_code="CLOSE_REASON_REQUIRED",
                )
            open_tasks = (
                db.query(Task)
                .filter(Task.incident_id == incident_id)
                .filter(Task.status.in_(list(OPEN_TASK_STATUSES)))
                .count()
            )
            if open_tasks > 0:
                raise BadRequestError(
                    message=f"Cannot close incident: {open_tasks} task(s) still open. Complete or cancel them first.",
                    error_code="OPEN_TASKS_BLOCK_CLOSE",
                )

        incident.status = target_status
        if payload.close_reason:
            incident.close_reason = payload.close_reason

    # Coordinate validation
    new_lat = payload.latitude if payload.latitude is not None else incident.latitude
    new_lng = payload.longitude if payload.longitude is not None else incident.longitude
    new_precision = payload.location_precision or incident.location_precision
    new_source = payload.coordinate_source or incident.coordinate_source
    if payload.latitude is not None or payload.longitude is not None:
        _validate_coordinates(new_lat, new_lng, new_precision, new_source)

    # Apply all other fields
    simple_fields = [
        "title", "summary", "category", "evidence_status",
        "location_name", "location_description", "district", "state",
        "district_source", "state_source", "assigned_coordinator_id",
    ]
    for field_name in simple_fields:
        value = getattr(payload, field_name, None)
        if value is not None:
            setattr(incident, field_name, value)

    if payload.latitude is not None:
        incident.latitude = payload.latitude
    if payload.longitude is not None:
        incident.longitude = payload.longitude
    if payload.location_precision is not None:
        incident.location_precision = payload.location_precision
    if payload.coordinate_source is not None:
        incident.coordinate_source = payload.coordinate_source
    if payload.has_grounded_coordinates is not None:
        incident.has_grounded_coordinates = payload.has_grounded_coordinates

    # Priority override
    if payload.approved_priority is not None:
        current_suggested = incident.suggested_priority.value if hasattr(incident.suggested_priority, 'value') else str(incident.suggested_priority)
        if payload.approved_priority != current_suggested and not payload.priority_override_reason:
            raise BadRequestError(
                message="A priority_override_reason is required when overriding AI suggested priority",
                error_code="PRIORITY_OVERRIDE_REASON_REQUIRED",
            )
        incident.approved_priority = payload.approved_priority
        if payload.priority_override_reason:
            incident.priority_override_reason = payload.priority_override_reason

    # Bump version
    incident.version += 1
    incident.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(incident)

    AuditService.record(
        db=db,
        actor=current_user.email,
        action="INCIDENT_UPDATED",
        entity_type="incident",
        entity_id=incident.id,
        before=before_state,
        after={
            "status": incident.status.value if hasattr(incident.status, 'value') else str(incident.status),
            "priority": incident.approved_priority.value if hasattr(incident.approved_priority, 'value') else str(incident.approved_priority),
            "version": incident.version,
        },
    )

    return incident


# ──────────────────────────────────────────────────────────────────────────────
# LINK CONFIRM / REJECT (Coordinator RBAC, idempotent, audited, never deletes reports)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/incidents/{incident_id}/reports/{report_id}/confirm")
def confirm_report_match(
    incident_id: str,
    report_id: str,
    payload: Optional[LinkReviewRequest] = None,
    current_user: User = Depends(require_role(RoleEnum.COORDINATOR, RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    _get_incident_or_404(db, incident_id)
    notes = payload.reviewer_notes if payload else None
    link = matching_service.confirm_link(
        db=db,
        incident_id=incident_id,
        report_id=report_id,
        reviewer_email=current_user.email,
        notes=notes,
    )
    return {
        "status": "confirmed",
        "link_id": link.id,
        "reviewed_by": link.reviewed_by,
        "reviewed_at": link.reviewed_at.isoformat() if link.reviewed_at else None,
        "reviewer_notes": link.reviewer_notes,
    }


@router.post("/incidents/{incident_id}/reports/{report_id}/reject")
def reject_report_match(
    incident_id: str,
    report_id: str,
    payload: Optional[LinkReviewRequest] = None,
    current_user: User = Depends(require_role(RoleEnum.COORDINATOR, RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    _get_incident_or_404(db, incident_id)
    notes = payload.reviewer_notes if payload else None
    link = matching_service.reject_link(
        db=db,
        incident_id=incident_id,
        report_id=report_id,
        reviewer_email=current_user.email,
        notes=notes,
    )
    return {
        "status": "rejected",
        "link_id": link.id,
        "reviewed_by": link.reviewed_by,
        "reviewed_at": link.reviewed_at.isoformat() if link.reviewed_at else None,
        "reviewer_notes": link.reviewer_notes,
    }
