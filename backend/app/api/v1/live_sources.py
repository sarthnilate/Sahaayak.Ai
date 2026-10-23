"""
FastAPI Router for Phase 6B: Live Official Emergency Data
Endpoints:
- GET  /api/v1/live-sources/status  (Status of all configured providers)
- GET  /api/v1/live-alerts          (Paginated, filterable alerts)
- POST /api/v1/live-sources/refresh (Coordinator/admin only, rate-limited manual trigger)
- GET  /api/v1/live-alerts/applicable (Find alerts applicable to an incident or coordinates)
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.core.auth import get_current_user
from backend.app.models.all_models import User, Incident
from backend.app.services.live_data.live_data_service import LiveDataService
from backend.app.services.live_data.applicability import check_alert_applicability
from backend.app.services.audit.service import AuditService

router = APIRouter(prefix="/live-sources", tags=["Live Official Sources"])


class SourceStatusResponse(BaseModel):
    source_id: str
    display_name: str
    status: str
    last_fetched_at: Optional[str] = None
    item_count: int = 0
    http_status: Optional[int] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = {}


class ExternalAlertResponse(BaseModel):
    id: str
    source_id: str
    external_identifier: str
    headline: str
    event: str
    severity: str
    urgency: Optional[str] = None
    certainty: Optional[str] = None
    area_description: str
    language: str
    sender: Optional[str] = None
    sent_at: Optional[str] = None
    effective_at: Optional[str] = None
    expires_at: Optional[str] = None
    source_url: Optional[str] = None
    centroid: Optional[str] = None
    is_synthetic: bool
    is_expired: bool
    retrieved_at: str

    class Config:
        from_attributes = True


class ApplicableAlertResult(BaseModel):
    alert: ExternalAlertResponse
    is_applicable: bool
    match_rationale: str
    distance_km: Optional[float] = None


@router.get("/status", response_model=List[SourceStatusResponse])
def get_sources_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve operational and connectivity status of all configured emergency data sources."""
    service = LiveDataService(db)
    statuses = service.get_sources_status()
    return [
        SourceStatusResponse(
            source_id=s.source_id,
            display_name=s.display_name,
            status=s.status,
            last_fetched_at=s.last_fetched_at.isoformat() if s.last_fetched_at else None,
            item_count=s.item_count,
            http_status=s.http_status,
            error_message=s.error_message,
            details=s.details,
        )
        for s in statuses
    ]


@router.post("/refresh/{source_id}")
def refresh_source(
    source_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually triggers upstream fetch for a specified source.
    Restricted to coordinators and admins to prevent rate abuse against government infrastructure.
    """
    if current_user.role not in ("coordinator", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coordinators and administrators can force refresh live government feeds.",
        )

    service = LiveDataService(db)
    try:
        result = service.refresh_source(source_id)
        
        # Log audit trail
        audit = AuditService(db)
        audit.log_event(
            user_id=current_user.id,
            action="live_source_refresh",
            resource_type="live_source",
            resource_id=source_id,
            details={"refresh_result": result},
        )
        return {"status": "success", "source_id": source_id, "summary": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to refresh source {source_id}: {str(e)}",
        )


alerts_router = APIRouter(prefix="/live-alerts", tags=["Live Official Alerts"])


@alerts_router.get("", response_model=List[ExternalAlertResponse])
def list_live_alerts(
    source_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Search area or headline"),
    include_expired: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List ingested alerts from official feeds with filtering."""
    service = LiveDataService(db)
    records = service.list_alerts(
        source_id=source_id,
        severity=severity,
        state_or_district=q,
        include_expired=include_expired,
        limit=limit,
        offset=offset,
    )
    return [
        ExternalAlertResponse(
            id=r.id,
            source_id=r.source_id,
            external_identifier=r.external_identifier,
            headline=r.headline,
            event=r.event,
            severity=r.severity,
            urgency=r.urgency,
            certainty=r.certainty,
            area_description=r.area_description,
            language=r.language,
            sender=r.sender,
            sent_at=r.sent_at.isoformat() if r.sent_at else None,
            effective_at=r.effective_at.isoformat() if r.effective_at else None,
            expires_at=r.expires_at.isoformat() if r.expires_at else None,
            source_url=r.source_url,
            centroid=r.centroid,
            is_synthetic=r.is_synthetic,
            is_expired=r.is_expired,
            retrieved_at=r.retrieved_at.isoformat(),
        )
        for r in records
    ]


@alerts_router.get("/for-incident/{incident_id}", response_model=List[ApplicableAlertResult])
def get_applicable_alerts_for_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Computes official advisories applicable to an incident without conflating with community claims.
    Uses district/state matching and coordinate proximity.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    service = LiveDataService(db)
    active_alerts = service.list_alerts(include_expired=False, limit=100)

    results: List[ApplicableAlertResult] = []
    for alert in active_alerts:
        is_app, rationale, dist = check_alert_applicability(
            alert_area=alert.area_description,
            alert_headline=alert.headline,
            incident_location_name=incident.location_name,
            incident_lat=incident.latitude,
            incident_lon=incident.longitude,
            alert_centroid=alert.centroid,
        )
        if is_app:
            alert_dto = ExternalAlertResponse(
                id=alert.id,
                source_id=alert.source_id,
                external_identifier=alert.external_identifier,
                headline=alert.headline,
                event=alert.event,
                severity=alert.severity,
                urgency=alert.urgency,
                certainty=alert.certainty,
                area_description=alert.area_description,
                language=alert.language,
                sender=alert.sender,
                sent_at=alert.sent_at.isoformat() if alert.sent_at else None,
                effective_at=alert.effective_at.isoformat() if alert.effective_at else None,
                expires_at=alert.expires_at.isoformat() if alert.expires_at else None,
                source_url=alert.source_url,
                centroid=alert.centroid,
                is_synthetic=alert.is_synthetic,
                is_expired=alert.is_expired,
                retrieved_at=alert.retrieved_at.isoformat(),
            )
            results.append(
                ApplicableAlertResult(
                    alert=alert_dto,
                    is_applicable=True,
                    match_rationale=rationale,
                    distance_km=dist,
                )
            )

    return results
