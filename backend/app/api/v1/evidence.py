"""
Phase 6: Transparent Evidence Handling and Verification States API.
Provides endpoints for incident evidence listing, SSRF-guarded manual attachment,
audited coordinator review with before/after tracking, and status transitions.
"""

from datetime import datetime, timezone
from typing import List, Optional

from backend.app.core.auth import get_current_user_optional, require_role
from backend.app.core.errors import (
    BadRequestError,
    EntityNotFoundError,
    ForbiddenError,
    InvalidStateTransitionError,
)
from backend.app.db.session import get_db
from backend.app.models.all_models import (
    AssessmentEnum,
    AuditEvent,
    EvidenceItem,
    EvidenceStatusEnum,
    EvidenceTypeEnum,
    Incident,
    IncidentReportLink,
    Report,
    RoleEnum,
    User,
)
from backend.app.schemas.all_schemas import (
    EvidenceCreate,
    EvidenceResponse,
    EvidenceReviewRequest,
    IncidentEvidenceListResponse,
    IncidentEvidenceStatusOverrideRequest,
)
from backend.app.services.audit.service import audit_service
from backend.app.services.evidence.independence import compute_independent_source_count
from backend.app.services.evidence.missing_evidence import compute_missing_evidence
from backend.app.services.evidence.providers import verification_service
from backend.app.services.evidence.ssrf_guard import SSRFSecurityError, check_safe_url_or_raise
from backend.app.services.evidence.state_machine import (
    normalize_evidence_status,
    suggest_evidence_status,
    validate_evidence_transition,
)
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session, joinedload, selectinload

router = APIRouter()


def _get_incident_or_404(db: Session, incident_id: str) -> Incident:
    incident = (
        db.query(Incident)
        .options(
            selectinload(Incident.evidence_items),
            selectinload(Incident.links).selectinload(IncidentReportLink.report),
        )
        .filter(Incident.id == incident_id)
        .first()
    )
    if not incident:
        raise EntityNotFoundError(
            entity_type="incident",
            entity_id=incident_id,
            message=f"Incident '{incident_id}' not found.",
        )
    return incident


@router.get("/incidents/{incident_id}/evidence", response_model=IncidentEvidenceListResponse)
def list_incident_evidence(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Returns all evidence items for an incident along with:
    - Deterministic independent source count (deduplicating forwards/origins)
    - Current vs Suggested evidence status
    - Missing evidence facet gaps
    - Verification availability status from live feeds
    """
    incident = _get_incident_or_404(db, incident_id)

    items = (
        db.query(EvidenceItem)
        .options(joinedload(EvidenceItem.report))
        .filter(EvidenceItem.incident_id == incident_id)
        .order_by(EvidenceItem.created_at.asc())
        .all()
    )

    # Get linked reports for missing evidence computation
    linked_reports = [link.report for link in (incident.links or []) if link and link.report]

    independence_count = compute_independent_source_count(items)
    suggested_status = suggest_evidence_status(items)
    missing_evidence = compute_missing_evidence(incident, items, linked_reports)

    conflicts_count = sum(
        1
        for item in items
        if item.assessment == AssessmentEnum.CONTRADICTS.value
        or item.evidence_type == EvidenceTypeEnum.CONTRADICTORY.value
        or (hasattr(item.verification_status, "value") and item.verification_status.value in ("conflicting", "conflicting_evidence", "disproven"))
    )

    verification_available, unavail_reason = verification_service.get_verification_availability()
    curr_status_val = incident.evidence_status.value if hasattr(incident.evidence_status, "value") else str(incident.evidence_status)

    from backend.app.schemas.all_schemas import MissingEvidenceGap, VerificationState
    structured_gaps = [MissingEvidenceGap(**g) for g in missing_evidence]
    verification_state = VerificationState(
        verification_available=verification_available,
        reason=unavail_reason or ("Live official feeds active" if verification_available else "No live official feeds configured"),
        provider_name=None,
    )

    evidence_out = [EvidenceResponse.model_validate(it) for it in items]
    return IncidentEvidenceListResponse(
        incident_id=incident.id,
        items=evidence_out,
        evidence_status=curr_status_val,
        suggested_status=suggested_status.value,
        independent_source_count=independence_count,
        conflicts_count=conflicts_count,
        missing_evidence=structured_gaps,
        verification=verification_state,
        evidence_items=evidence_out,
        independence_count=independence_count,
        verification_available=verification_available,
        verification_unavailable_reason=unavail_reason,
    )


@router.post(
    "/incidents/{incident_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_incident_evidence(
    incident_id: str,
    payload: EvidenceCreate,
    current_user: User = Depends(require_role(RoleEnum.COORDINATOR, RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Coordinator attaches an evidence item to an incident.
    Validates source_url with the SSRF guard (blocking private/loopback/link-local IPs and non-HTTPS schemes).
    Audited with before and after states.
    """
    incident = _get_incident_or_404(db, incident_id)

    # 1. SSRF Guard Check on source_url if provided
    if payload.source_url:
        try:
            check_safe_url_or_raise(payload.source_url)
        except SSRFSecurityError as err:
            raise BadRequestError(
                message=f"SSRF validation failed: {err.message}",
                error_code=err.code,
                details={"url": payload.source_url},
            )

    # 2. Derive independence group if not explicitly set
    independence_grp = payload.independence_group
    if not independence_grp:
        if payload.report_id:
            rep = db.query(Report).filter(Report.id == payload.report_id).first()
            if rep:
                independence_grp = rep.origin_group_id or rep.source_fingerprint or rep.id
        else:
            independence_grp = f"manual-{current_user.id}"

    # 3. Create EvidenceItem
    evidence = EvidenceItem(
        incident_id=incident.id,
        report_id=payload.report_id,
        evidence_type=payload.evidence_type or "manual_attachment",
        source_type=payload.source_type or "field_report",
        source_name=payload.source_name,
        source_description=payload.source_description or payload.claim_summary or "",
        source_url=payload.source_url,
        source_timestamp=payload.source_timestamp,
        retrieved_at=datetime.now(timezone.utc),
        freshness=payload.freshness or "< 1h",
        assessment=payload.assessment or "unassessed",
        excerpt=payload.excerpt,
        metadata_json=payload.metadata_json or {},
        reviewer_notes=payload.reviewer_notes,
        independence_group=independence_grp,
        is_simulated=payload.is_simulated,
        claim_summary=payload.claim_summary or payload.source_description or payload.source_name,
        verification_status=payload.verification_status or "unverified",
        created_by=current_user.email,
        reviewed_by=current_user.email if payload.reviewer_notes else None,
        reviewed_at=datetime.now(timezone.utc) if payload.reviewer_notes else None,
    )

    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    # 4. Audit Event
    audit_service.log(
        db=db,
        actor=current_user.email,
        action="EVIDENCE_ATTACHED",
        entity_type="evidence_item",
        entity_id=evidence.id,
        details={
            "incident_id": incident.id,
            "source_name": evidence.source_name,
            "evidence_type": evidence.evidence_type,
            "assessment": evidence.assessment,
            "source_url": evidence.source_url,
            "is_simulated": evidence.is_simulated,
            "independence_group": evidence.independence_group,
        },
    )

    return evidence


@router.post("/evidence/{evidence_id}/review", response_model=EvidenceResponse)
def review_evidence(
    evidence_id: str,
    payload: EvidenceReviewRequest,
    current_user: User = Depends(require_role(RoleEnum.COORDINATOR, RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Coordinator reviews an individual evidence item.
    Requires coordinator reviewer_notes.
    Records before and after states in the audit trail.
    """
    evidence = db.query(EvidenceItem).filter(EvidenceItem.id == evidence_id).first()
    if not evidence:
        raise EntityNotFoundError(
            entity_type="evidence_item",
            entity_id=evidence_id,
            message=f"Evidence item '{evidence_id}' not found.",
        )

    before_state = {
        "assessment": evidence.assessment,
        "verification_status": evidence.verification_status.value if hasattr(evidence.verification_status, "value") else str(evidence.verification_status),
        "reviewer_notes": evidence.reviewer_notes,
        "reviewed_by": evidence.reviewed_by,
        "reviewed_at": evidence.reviewed_at.isoformat() if evidence.reviewed_at else None,
    }

    if payload.assessment:
        evidence.assessment = payload.assessment
    if payload.verification_status:
        evidence.verification_status = payload.verification_status

    evidence.reviewer_notes = payload.reviewer_notes
    evidence.reviewed_by = current_user.email
    evidence.reviewed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(evidence)

    after_state = {
        "assessment": evidence.assessment,
        "verification_status": evidence.verification_status.value if hasattr(evidence.verification_status, "value") else str(evidence.verification_status),
        "reviewer_notes": evidence.reviewer_notes,
        "reviewed_by": evidence.reviewed_by,
        "reviewed_at": evidence.reviewed_at.isoformat() if evidence.reviewed_at else None,
    }

    # Audit before and after
    audit_service.log(
        db=db,
        actor=current_user.email,
        action="EVIDENCE_REVIEWED",
        entity_type="evidence_item",
        entity_id=evidence.id,
        before={**before_state, "incident_id": evidence.incident_id},
        after={**after_state, "incident_id": evidence.incident_id},
    )

    return evidence


@router.post("/incidents/{incident_id}/evidence-status", response_model=IncidentEvidenceListResponse)
def override_incident_evidence_status(
    incident_id: str,
    payload: IncidentEvidenceStatusOverrideRequest,
    current_user: User = Depends(require_role(RoleEnum.COORDINATOR, RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Coordinator explicitly sets or overrides an incident's overall evidence verification status.
    Requires reviewer notes explaining the decision.
    Enforces valid state machine transitions.
    Audited with before and after state.
    """
    incident = _get_incident_or_404(db, incident_id)

    curr_status = incident.evidence_status
    target_status = normalize_evidence_status(payload.status)

    # Validate state transition
    validate_evidence_transition(curr_status, target_status)

    before_val = curr_status.value if hasattr(curr_status, "value") else str(curr_status)
    after_val = target_status.value

    incident.evidence_status = target_status
    incident.version = (incident.version or 1) + 1
    incident.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(incident)

    audit_service.log(
        db=db,
        actor=current_user.email,
        action="EVIDENCE_STATUS_OVERRIDDEN",
        entity_type="incident",
        entity_id=incident.id,
        details={
            "before_status": before_val,
            "after_status": after_val,
            "coordinator_notes": payload.reviewer_notes,
            "version": incident.version,
        },
    )

    return list_incident_evidence(incident_id=incident.id, db=db, current_user=current_user)
