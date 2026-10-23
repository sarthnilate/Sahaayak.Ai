from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from backend.app.db.session import get_db
from backend.app.models.all_models import (
    Incident, Report, IncidentReportLink, EvidenceItem, Task, AuditEvent
)
from backend.app.schemas.all_schemas import (
    IncidentResponse, IncidentCreate, IncidentUpdate,
    IncidentReportLinkResponse, LinkReviewRequest,
    EvidenceResponse, TaskResponse
)
from backend.app.services.matching.service import matching_service
from backend.app.services.prioritization.service import prioritization_service
from backend.app.services.audit.service import audit_service

router = APIRouter()

@router.get("/incidents", response_model=List[IncidentResponse])
def list_incidents(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Incident).order_by(Incident.created_at.desc())
    if category:
        query = query.filter(Incident.category == category)
    if status:
        query = query.filter(Incident.status == status)
    if priority:
        query = query.filter(Incident.approved_priority == priority)
    return query.all()

@router.post("/incidents", response_model=IncidentResponse)
def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)):
    incident = Incident(
        title=payload.title,
        summary=payload.summary,
        category=payload.category,
        status="open",
        suggested_priority=payload.suggested_priority,
        approved_priority=payload.approved_priority or payload.suggested_priority,
        priority_rationale=payload.priority_rationale or "Initial coordinator assessment",
        location_name=payload.location_name,
        latitude=payload.latitude,
        longitude=payload.longitude,
        has_grounded_coordinates=payload.has_grounded_coordinates,
        is_simulated=payload.is_simulated
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    audit_service.log(
        db=db,
        actor="coordinator",
        action="INCIDENT_CREATED",
        entity_type="incident",
        entity_id=incident.id,
        details={"title": incident.title, "priority": incident.approved_priority}
    )

    return incident

@router.get("/incidents/{incident_id}")
def get_incident_detail(incident_id: str, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Fetch links with report detail
    links = (
        db.query(IncidentReportLink)
        .options(joinedload(IncidentReportLink.report))
        .filter(IncidentReportLink.incident_id == incident_id)
        .all()
    )
    evidence_items = db.query(EvidenceItem).filter(EvidenceItem.incident_id == incident_id).all()
    tasks = db.query(Task).filter(Task.incident_id == incident_id).all()
    # Query audit events related to incident
    all_events = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(100).all()
    audit_events = [
        a for a in all_events
        if a.entity_id == incident_id or (isinstance(a.details, dict) and a.details.get("incident_id") == incident_id)
    ][:20]

    return {
        "incident": IncidentResponse.model_validate(incident),
        "links": [
            {
                "id": l.id,
                "incident_id": l.incident_id,
                "report_id": l.report_id,
                "status": l.status,
                "similarity_score": l.similarity_score,
                "match_rationale": l.match_rationale,
                "reviewed_by": l.reviewed_by,
                "reviewed_at": l.reviewed_at,
                "report": l.report
            }
            for l in links
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
                "details": a.details,
                "timestamp": a.timestamp
            }
            for a in audit_events
        ]
    }

@router.patch("/incidents/{incident_id}", response_model=IncidentResponse)
def update_incident(incident_id: str, payload: IncidentUpdate, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    before_state = {
        "status": incident.status,
        "priority": incident.approved_priority
    }

    if payload.title is not None:
        incident.title = payload.title
    if payload.summary is not None:
        incident.summary = payload.summary
    if payload.status is not None:
        incident.status = payload.status
    if payload.approved_priority is not None:
        if payload.approved_priority != incident.suggested_priority and not payload.priority_override_reason:
            raise HTTPException(
                status_code=400,
                detail="A priority_override_reason is required when overriding AI suggested priority"
            )
        incident.approved_priority = payload.approved_priority
        incident.priority_override_reason = payload.priority_override_reason
    if payload.evidence_status is not None:
        incident.evidence_status = payload.evidence_status

    incident.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(incident)

    audit_service.log(
        db=db,
        actor="coordinator",
        action="INCIDENT_UPDATED",
        entity_type="incident",
        entity_id=incident.id,
        details={
            "before": before_state,
            "after": {
                "status": incident.status,
                "priority": incident.approved_priority,
                "reason": incident.priority_override_reason
            }
        }
    )

    return incident

@router.post("/incidents/{incident_id}/reports/{report_id}/confirm")
def confirm_report_match(
    incident_id: str,
    report_id: str,
    payload: Optional[LinkReviewRequest] = None,
    db: Session = Depends(get_db)
):
    link = db.query(IncidentReportLink).filter(
        IncidentReportLink.incident_id == incident_id,
        IncidentReportLink.report_id == report_id
    ).first()

    if not link:
        # Create confirmed link if not existing
        link = IncidentReportLink(
            incident_id=incident_id,
            report_id=report_id,
            status="confirmed",
            similarity_score=1.0,
            match_rationale="Manually linked and confirmed by coordinator"
        )
        db.add(link)
    else:
        link.status = "confirmed"

    link.reviewed_by = payload.reviewed_by if payload else "coordinator@sahaayak.ai"
    link.reviewed_at = datetime.utcnow()
    
    # Recalculate incident priority based on new confirmed evidence
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    confirmed_count = db.query(IncidentReportLink).filter(
        IncidentReportLink.incident_id == incident_id,
        IncidentReportLink.status == "confirmed"
    ).count()

    report = db.query(Report).filter(Report.id == report_id).first()
    extracted = (report.extracted_json or {}) if report else {}
    
    new_priority, rationale = prioritization_service.calculate_priority(
        category=incident.category,
        water_depth_cm=extracted.get("water_depth_cm"),
        affected_infrastructure=extracted.get("affected_infrastructure", []),
        casualties_flag=extracted.get("casualties_flag", False),
        linked_report_count=confirmed_count,
        conflicting_evidence=incident.evidence_status == "conflicting_evidence"
    )
    incident.suggested_priority = new_priority
    incident.priority_rationale = rationale
    if not incident.priority_override_reason:
        incident.approved_priority = new_priority

    db.commit()

    audit_service.log(
        db=db,
        actor=link.reviewed_by,
        action="MATCH_CONFIRMED",
        entity_type="link",
        entity_id=link.id,
        details={
            "incident_id": incident_id,
            "report_id": report_id,
            "new_suggested_priority": new_priority
        }
    )

    return {"status": "confirmed", "link_id": link.id, "new_suggested_priority": new_priority}

@router.post("/incidents/{incident_id}/reports/{report_id}/reject")
def reject_report_match(
    incident_id: str,
    report_id: str,
    payload: Optional[LinkReviewRequest] = None,
    db: Session = Depends(get_db)
):
    link = db.query(IncidentReportLink).filter(
        IncidentReportLink.incident_id == incident_id,
        IncidentReportLink.report_id == report_id
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="Association link not found")

    link.status = "rejected"
    link.reviewed_by = payload.reviewed_by if payload else "coordinator@sahaayak.ai"
    link.reviewed_at = datetime.utcnow()
    db.commit()

    audit_service.log(
        db=db,
        actor=link.reviewed_by,
        action="MATCH_REJECTED",
        entity_type="link",
        entity_id=link.id,
        details={"incident_id": incident_id, "report_id": report_id}
    )

    return {"status": "rejected", "link_id": link.id}
