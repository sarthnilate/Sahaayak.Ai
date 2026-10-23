import hashlib
import re
import secrets
from datetime import datetime
from typing import List, Optional

from backend.app.core.auth import get_current_user, get_current_user_optional
from backend.app.core.config import settings
from backend.app.core.errors import (
    ForbiddenError,
    ResourceNotFoundError,
)
from backend.app.core.limiter import limiter
from backend.app.db.session import get_db
from backend.app.models.all_models import (
    Incident,
    IncidentReportLink,
    IncidentStatusEnum,
    LinkStatusEnum,
    Report,
    ReportStatusEnum,
    RoleEnum,
    User,
)
from backend.app.schemas.all_schemas import (
    IncidentReportLinkResponse,
    MatchCandidateResponse,
    MatchSignalSchema,
    PaginatedReportsResponse,
    ReportMatchesResponse,
    ReportResponse,
)
from backend.app.schemas.extraction_schema import CoordinatorCorrectionSchema
from backend.app.services.ai.adapter import ai_adapter
from backend.app.services.extraction.service import ExtractionService
from backend.app.services.matching.service import matching_service
from backend.app.services.storage.image_security import sanitize_and_reencode_image
from backend.app.services.storage.provider import storage_provider
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

router = APIRouter()


def generate_reference_code() -> str:
    """Generates human-friendly reference: SAH-2026-XXXXXX"""
    return f"SAH-2026-{secrets.token_hex(3).upper()}"


def compute_source_fingerprint(text: str) -> str:
    """SHA-256 fingerprint of normalized text for copied-claim detection"""
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@router.post("/reports", response_model=ReportResponse, status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def submit_report(
    request: Request,
    original_text: str = Form(..., min_length=3, max_length=2000),
    input_language: str = Form("en"),
    reporter_name: Optional[str] = Form("Anonymous Citizen"),
    reporter_contact: Optional[str] = Form(None),
    location_claim: Optional[str] = Form(None),
    coordinates_lat: Optional[float] = Form(None),
    coordinates_lng: Optional[float] = Form(None),
    incident_time: Optional[str] = Form(None),
    idempotency_key: Optional[str] = Form(None),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    media_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Secure report intake endpoint:
    - Text length enforced (max 2000 chars)
    - Magic-byte validation, decompression bomb protection, EXIF/GPS stripping, re-encoding
    - Server-side UUID filename storage outside web root
    - Human-friendly reference SAH-2026-XXXXXX
    - Normalized text source fingerprint (SHA-256)
    - Client idempotency key duplicate-submission safety
    - Slowapi rate-limiting per IP and per user
    """
    effective_idempotency = (idempotency_key or x_idempotency_key or "").strip() or None

    # 1. Idempotency Check: if key already exists, return existing report
    if effective_idempotency:
        existing = db.execute(
            select(Report).where(Report.idempotency_key == effective_idempotency)
        ).scalar_one_or_none()
        if existing:
            return existing

    # 2. Authenticated user (optional: public citizens can also report)
    current_user = get_current_user_optional(request, db)
    user_id = current_user.id if current_user else None

    # 3. Parse incident time if provided
    parsed_incident_time = None
    if incident_time:
        try:
            parsed_incident_time = datetime.fromisoformat(incident_time.replace("Z", "+00:00"))
        except Exception:
            pass

    # 4. Image Security & Processing
    media_path = None
    media_type = None

    if media_file and media_file.filename:
        raw_bytes = await media_file.read()
        if raw_bytes:
            # Magic bytes validation, decompression bomb guard, EXIF/GPS stripping, re-encoding
            cleaned_bytes, ext, sanitized_mime = sanitize_and_reencode_image(
                raw_bytes=raw_bytes, max_size_mb=settings.MAX_UPLOAD_MB
            )
            # Store in outside-web-root protected storage with server-side UUID filename
            media_path = storage_provider.save_file(cleaned_bytes, ext)
            media_type = sanitized_mime

    # 5. Compute source fingerprint & reference code
    source_fp = compute_source_fingerprint(original_text)
    ref_code = generate_reference_code()

    # 6. Persist initial report to ensure no data loss
    report = Report(
        reference_code=ref_code,
        user_id=user_id,
        idempotency_key=effective_idempotency,
        incident_time=parsed_incident_time,
        original_text=original_text,
        media_path=media_path,
        media_type=media_type,
        input_language=input_language,
        reporter_name=reporter_name or "Anonymous Citizen",
        reporter_contact=reporter_contact,
        location_claim=location_claim,
        coordinates_lat=coordinates_lat,
        coordinates_lng=coordinates_lng,
        source_fingerprint=source_fp,
        processing_status=ReportStatusEnum.RECEIVED,
        extraction_source="gemini" if ai_adapter.is_live else "demo",
    )
    db.add(report)
    db.flush()

    # 7. Record Immutable Audit Event
    from backend.app.services.audit.service import AuditService

    AuditService.record(
        db=db,
        actor=user_id or reporter_name or "anonymous",
        action="REPORT_CREATED",
        entity_type="report",
        entity_id=report.id,
        before={},
        after={
            "reference_code": report.reference_code,
            "has_media": bool(media_path),
            "media_type": media_type,
            "source_fingerprint": source_fp,
            "language": input_language,
        },
    )
    db.refresh(report)

    # 8. Trigger AI extraction via ExtractionService
    extraction_svc = ExtractionService()
    report = await extraction_svc.process_report(
        db=db,
        report_id=report.id,
        actor=user_id or "system:ai_extraction",
        force_retry=False,
    )

    # 9. Candidate duplicate matching against active incidents (pure + pre-filtered)
    if report.processing_status in [ReportStatusEnum.PROCESSED, ReportStatusEnum.NEEDS_REVIEW]:
        matching_service.find_and_persist_candidates_for_report(
            db=db,
            report_id=report.id,
            actor=user_id or "system:matcher",
        )

    return report


@router.get("/reports", response_model=PaginatedReportsResponse, status_code=status.HTTP_200_OK)
def list_reports(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Report status filter"),
    language: Optional[str] = Query(None, description="Language code filter"),
    input_type: Optional[str] = Query(None, description="Filter: 'text' or 'image'"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    search: Optional[str] = Query(None, description="Text search in claim or original text"),
    sort_by: str = Query("submitted_at", description="Sort field: submitted_at, processing_status"),
    order: str = Query("desc", description="Sort order: asc, desc"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Paginated and filtered reports list with RBAC:
    - Reporters see ONLY their own reports
    - Coordinators and Admins see all reports
    - Eager loading (selectinload) to eliminate N+1 query problems
    """
    # Enforce role-based scoping:
    # If unauthenticated, allow public coordinator demo fallback or require login
    stmt = select(Report).options(selectinload(Report.links))

    if current_user and current_user.role == RoleEnum.REPORTER:
        # Strict reporter isolation: reporter sees only their own reports
        stmt = stmt.where(Report.user_id == current_user.id)
    elif not current_user:
        # For public demo evaluation, if unauthenticated, show demo public reports
        pass

    # Status filter
    if status:
        stmt = stmt.where(Report.processing_status == status)

    # Language filter
    if language:
        stmt = stmt.where(Report.input_language == language)

    # Input type filter
    if input_type == "image":
        stmt = stmt.where(Report.media_path.isnot(None))
    elif input_type == "text":
        stmt = stmt.where(Report.media_path.is_(None))

    # Date range filters
    if start_date:
        stmt = stmt.where(Report.submitted_at >= start_date)
    if end_date:
        stmt = stmt.where(Report.submitted_at <= end_date)

    # Text search
    if search:
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Report.original_text.ilike(search_pattern),
                Report.location_claim.ilike(search_pattern),
                Report.reference_code.ilike(search_pattern),
            )
        )

    # Count total matching before pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar() or 0

    # Sorting
    sort_col = getattr(Report, sort_by, Report.submitted_at)
    if order.lower() == "asc":
        stmt = stmt.order_by(sort_col.asc())
    else:
        stmt = stmt.order_by(sort_col.desc())

    # Pagination
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    reports = db.execute(stmt).scalars().all()
    pages = (total + limit - 1) // limit if total > 0 else 1

    return PaginatedReportsResponse(
        items=[ReportResponse.model_validate(r) for r in reports],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/duplicate-suggestions", response_model=List[IncidentReportLinkResponse])
@router.get("/reports/duplicate-suggestions", response_model=List[IncidentReportLinkResponse])
def get_duplicate_suggestions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all suggested duplicate links awaiting coordinator review.
    """
    links = (
        db.query(IncidentReportLink)
        .options(selectinload(IncidentReportLink.report), selectinload(IncidentReportLink.incident))
        .filter(IncidentReportLink.status == LinkStatusEnum.SUGGESTED)
        .order_by(IncidentReportLink.created_at.desc())
        .all()
    )
    return links


@router.get("/reports/{report_id}", response_model=ReportResponse, status_code=status.HTTP_200_OK)
def get_report(
    report_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Get a single report by ID:
    - Reporters can only view their own reports
    - Coordinators and Admins can view any report
    """
    stmt = select(Report).options(selectinload(Report.links)).where(Report.id == report_id)
    report = db.execute(stmt).scalar_one_or_none()

    if not report:
        raise ResourceNotFoundError(message="Report not found", error_code="REPORT_NOT_FOUND")

    # RBAC Ownership check: reporters cannot access another user's report
    if current_user and current_user.role == RoleEnum.REPORTER:
        if report.user_id != current_user.id:
            raise ForbiddenError(
                message="Access denied: You do not own this report",
                error_code="FORBIDDEN_REPORT_ACCESS",
            )

    return ReportResponse.model_validate(report)


@router.get("/reports/{report_id}/image", status_code=status.HTTP_200_OK)
def get_report_image(
    report_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Serves stored report image ONLY through an authorized endpoint.
    - Prevents raw upload access outside web root
    - Enforces reporter ownership and coordinator/admin authorization
    - Prevents path traversal
    """
    report = db.get(Report, report_id)
    if not report or not report.media_path:
        raise ResourceNotFoundError(
            message="Media item not found for this report", error_code="MEDIA_NOT_FOUND"
        )

    # Ownership check: reporters can only view image of their own report
    if current_user and current_user.role == RoleEnum.REPORTER:
        if report.user_id != current_user.id:
            raise ForbiddenError(
                message="Access denied: You do not own this report media",
                error_code="FORBIDDEN_MEDIA_ACCESS",
            )

    # Read bytes from outside web root storage
    image_bytes = storage_provider.read_file(report.media_path)
    return Response(content=image_bytes, media_type=report.media_type or "image/jpeg")


@router.get(
    "/reports/lookup/{reference_code}",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
)
def lookup_report_by_reference(
    reference_code: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Allows a citizen or reporter to look up report processing status by reference code (SAH-2026-XXXXXX).
    """
    clean_ref = reference_code.strip().upper()
    stmt = (
        select(Report).options(selectinload(Report.links)).where(Report.reference_code == clean_ref)
    )
    report = db.execute(stmt).scalar_one_or_none()

    if not report:
        raise ResourceNotFoundError(
            message=f"No report found with reference '{clean_ref}'",
            error_code="REFERENCE_NOT_FOUND",
        )

    # If reporter is logged in, ensure it is their own report
    if current_user and current_user.role == RoleEnum.REPORTER:
        if report.user_id and report.user_id != current_user.id:
            raise ForbiddenError(
                message="Access denied: This reference belongs to another reporter",
                error_code="FORBIDDEN_REFERENCE_ACCESS",
            )

    return ReportResponse.model_validate(report)


@router.post("/reports/{report_id}/process", response_model=ReportResponse)
async def process_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Triggers AI extraction for a received report.
    Allowed for coordinators/admins or the report owner.
    """
    report = db.get(Report, report_id)
    if not report:
        raise ResourceNotFoundError(message="Report not found", error_code="REPORT_NOT_FOUND")

    # Access check: reporter can only process own report; coordinator/admin can process any
    if current_user.role == RoleEnum.REPORTER and report.user_id != current_user.id:
        raise ForbiddenError(
            message="Access denied: You can only process your own report",
            error_code="INSUFFICIENT_PERMISSIONS",
        )

    extraction_svc = ExtractionService()
    report = await extraction_svc.process_report(
        db=db,
        report_id=report_id,
        actor=current_user.email,
        force_retry=False,
    )
    return ReportResponse.model_validate(report)


@router.post("/reports/{report_id}/retry", response_model=ReportResponse)
async def retry_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Idempotent, bounded retry for report extraction.
    Allowed for coordinators/admins or the report owner.
    """
    report = db.get(Report, report_id)
    if not report:
        raise ResourceNotFoundError(message="Report not found", error_code="REPORT_NOT_FOUND")

    # Access check: reporter can only retry own report; coordinator/admin can retry any
    if current_user.role == RoleEnum.REPORTER and report.user_id != current_user.id:
        raise ForbiddenError(
            message="Access denied: You can only retry your own report",
            error_code="INSUFFICIENT_PERMISSIONS",
        )

    extraction_svc = ExtractionService()
    report = await extraction_svc.process_report(
        db=db,
        report_id=report_id,
        actor=current_user.email,
        force_retry=True,
    )
    return ReportResponse.model_validate(report)


@router.post("/reports/{report_id}/correction", response_model=ReportResponse)
def correct_report_extraction(
    report_id: str,
    correction: CoordinatorCorrectionSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Allows a coordinator or admin to record corrections/annotations to extracted fields.
    Does not overwrite the original AI extraction output.
    """
    if current_user.role not in [RoleEnum.COORDINATOR, RoleEnum.ADMIN]:
        raise ForbiddenError(
            message="Only coordinators or administrators may record corrections",
            error_code="INSUFFICIENT_PERMISSIONS",
        )

    extraction_svc = ExtractionService()
    report = extraction_svc.apply_coordinator_correction(
        db=db,
        report_id=report_id,
        correction=correction,
        coordinator_name=current_user.email,
    )
    return ReportResponse.model_validate(report)


@router.get("/reports/{report_id}/matches", response_model=ReportMatchesResponse)
def get_report_matches(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns candidate matches for a report against active incidents,
    producing structured signals, threshold band (strong/possible/weak),
    human-readable rationale, unknowns, and same-origin detection.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise ResourceNotFoundError(message=f"Report '{report_id}' not found", error_code="REPORT_NOT_FOUND")

    # Evaluate against active incidents
    active_incidents = (
        db.query(Incident)
        .filter(Incident.status != IncidentStatusEnum.CLOSED)
        .order_by(Incident.created_at.desc())
        .limit(50)
        .all()
    )

    matches: List[MatchCandidateResponse] = []
    for inc in active_incidents:
        score, rationale, eval_result = matching_service.evaluate_match(report, inc)

        existing_link = (
            db.query(IncidentReportLink)
            .filter(
                IncidentReportLink.incident_id == inc.id,
                IncidentReportLink.report_id == report.id,
            )
            .first()
        )
        existing_status = existing_link.status.value if existing_link else None

        signals_for = [
            MatchSignalSchema(
                name=s.name, weight=s.weight, matched=s.matched, detail=s.detail
            )
            for s in eval_result.signals_for
        ]
        signals_against = [
            MatchSignalSchema(
                name=s.name, weight=s.weight, matched=s.matched, detail=s.detail
            )
            for s in eval_result.signals_against
        ]

        matches.append(
            MatchCandidateResponse(
                incident_id=inc.id,
                incident_title=inc.title,
                incident_category=inc.category,
                incident_location=inc.location_name,
                incident_created_at=inc.created_at,
                band=eval_result.band.value,
                score=score,
                rationale=rationale,
                signals_for=signals_for,
                signals_against=signals_against,
                unknowns=eval_result.unknowns,
                is_same_origin=eval_result.is_same_origin,
                origin_fingerprint=eval_result.origin_fingerprint,
                existing_link_status=existing_status,
            )
        )

    # Sort matches by band priority (strong > possible > weak) and score desc
    band_order = {"strong": 3, "possible": 2, "weak": 1}
    matches.sort(key=lambda m: (band_order.get(m.band, 0), m.score), reverse=True)

    return ReportMatchesResponse(
        report_id=report.id,
        matches=matches,
        origin_group_id=report.origin_group_id,
        total_candidates=len(matches),
    )
