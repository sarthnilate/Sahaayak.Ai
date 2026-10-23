from typing import List, Optional

from backend.app.db.session import get_db
from backend.app.models.all_models import EvidenceItem, Incident
from backend.app.schemas.all_schemas import EvidenceCreate, EvidenceResponse
from backend.app.services.audit.service import audit_service
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter()


class ReviewEvidenceRequest(BaseModel):
    verification_status: str  # corroborating, conflicting, unverified, disproven
    reviewer_notes: Optional[str] = None
    reviewer_actor: Optional[str] = "coordinator@sahaayak.ai"


@router.get("/incidents/{incident_id}/evidence", response_model=List[EvidenceResponse])
def list_incident_evidence(incident_id: str, db: Session = Depends(get_db)):
    return db.query(EvidenceItem).filter(EvidenceItem.incident_id == incident_id).all()


@router.post("/incidents/{incident_id}/evidence", response_model=EvidenceResponse)
def add_evidence(incident_id: str, payload: EvidenceCreate, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    evidence = EvidenceItem(
        incident_id=incident_id,
        report_id=payload.report_id,
        source_type=payload.source_type,
        source_name=payload.source_name,
        source_url=payload.source_url,
        is_simulated=payload.is_simulated,
        claim_summary=payload.claim_summary,
        verification_status=payload.verification_status,
        reviewer_notes=payload.reviewer_notes,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    audit_service.log(
        db=db,
        actor="coordinator",
        action="EVIDENCE_ATTACHED",
        entity_type="evidence",
        entity_id=evidence.id,
        details={"source": evidence.source_name, "status": evidence.verification_status},
    )

    return evidence


@router.post("/evidence/{evidence_id}/review", response_model=EvidenceResponse)
def review_evidence(
    evidence_id: str, payload: ReviewEvidenceRequest, db: Session = Depends(get_db)
):
    evidence = db.query(EvidenceItem).filter(EvidenceItem.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence item not found")

    evidence.verification_status = payload.verification_status
    if payload.reviewer_notes:
        evidence.reviewer_notes = payload.reviewer_notes
    db.commit()
    db.refresh(evidence)

    # Update incident overall evidence_status if conflicting
    incident = db.query(Incident).filter(Incident.id == evidence.incident_id).first()
    if incident:
        has_conflicts = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.incident_id == incident.id,
                EvidenceItem.verification_status == "conflicting",
            )
            .count()
            > 0
        )
        incident.evidence_status = (
            "conflicting_evidence" if has_conflicts else "partially_corroborated"
        )
        db.commit()

    audit_service.log(
        db=db,
        actor=payload.reviewer_actor or "coordinator",
        action="EVIDENCE_REVIEWED",
        entity_type="evidence",
        entity_id=evidence.id,
        details={"new_status": evidence.verification_status},
    )

    return evidence
