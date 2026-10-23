import os
import shutil
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.models.all_models import Report, Incident, IncidentReportLink, AuditEvent
from backend.app.schemas.all_schemas import ReportResponse, ReportCreate
from backend.app.services.ai.adapter import ai_adapter
from backend.app.services.matching.service import matching_service
from backend.app.services.audit.service import audit_service

router = APIRouter()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

@router.post("/reports", response_model=ReportResponse)
async def submit_report(
    original_text: str = Form(...),
    input_language: str = Form("en"),
    reporter_name: Optional[str] = Form("Anonymous Citizen"),
    reporter_contact: Optional[str] = Form(None),
    location_claim: Optional[str] = Form(None),
    coordinates_lat: Optional[float] = Form(None),
    coordinates_lng: Optional[float] = Form(None),
    media_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    media_path = None
    media_type = None

    if media_file and media_file.filename:
        if media_file.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type '{media_file.content_type}'. Allowed types: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
            )
        
        # Read file with size check
        content = await media_file.read()
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB"
            )
        
        filename = f"{int(datetime.utcnow().timestamp())}_{media_file.filename}"
        saved_path = os.path.join(settings.UPLOAD_DIR, filename)
        with open(saved_path, "wb") as f:
            f.write(content)
        media_path = saved_path
        media_type = media_file.content_type

    # 1. Persist initial report to ensure no data is lost
    report = Report(
        original_text=original_text,
        media_path=media_path,
        media_type=media_type,
        input_language=input_language,
        reporter_name=reporter_name,
        reporter_contact=reporter_contact,
        location_claim=location_claim,
        coordinates_lat=coordinates_lat,
        coordinates_lng=coordinates_lng,
        processing_status="processing",
        extraction_source="gemini" if ai_adapter.is_live else "demo"
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # 2. Run extraction
    try:
        extracted = await ai_adapter.extract_incident_data(
            text=original_text,
            media_path=media_path,
            language=input_language
        )
        report.extracted_json = extracted
        report.processing_status = "processed"
        report.processed_at = datetime.utcnow()
        if extracted.get("language_detected"):
            report.input_language = extracted["language_detected"]

        # If report coordinates were empty, use extracted approximate ones if available
        if not report.coordinates_lat and extracted.get("approximate_lat"):
            report.coordinates_lat = extracted["approximate_lat"]
            report.coordinates_lng = extracted["approximate_lng"]

    except Exception as e:
        report.processing_status = "failed"
        report.error_message = str(e)

    db.commit()
    db.refresh(report)

    # 3. Candidate duplicate matching against open incidents
    if report.processing_status == "processed":
        active_incidents = db.query(Incident).filter(Incident.status != "closed").all()
        for inc in active_incidents:
            score, rationale = matching_service.evaluate_match(report, inc)
            if score >= 0.40:  # Candidate match threshold
                link = IncidentReportLink(
                    incident_id=inc.id,
                    report_id=report.id,
                    status="suggested",
                    similarity_score=score,
                    match_rationale=rationale
                )
                db.add(link)
        db.commit()

    # 4. Audit event
    audit_service.log(
        db=db,
        actor=reporter_name or "citizen",
        action="REPORT_SUBMITTED",
        entity_type="report",
        entity_id=report.id,
        details={
            "status": report.processing_status,
            "extraction_source": report.extraction_source,
            "has_media": bool(media_path)
        }
    )

    return report

@router.get("/reports", response_model=List[ReportResponse])
def list_reports(
    status: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Report).order_by(Report.submitted_at.desc())
    if status:
        query = query.filter(Report.processing_status == status)
    if language:
        query = query.filter(Report.input_language == language)
    return query.all()

@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(report_id: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@router.post("/reports/{report_id}/retry", response_model=ReportResponse)
async def retry_report(report_id: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.processing_status = "processing"
    report.error_message = None
    db.commit()

    try:
        extracted = await ai_adapter.extract_incident_data(
            text=report.original_text,
            media_path=report.media_path,
            language=report.input_language
        )
        report.extracted_json = extracted
        report.processing_status = "processed"
        report.processed_at = datetime.utcnow()
    except Exception as e:
        report.processing_status = "failed"
        report.error_message = str(e)

    db.commit()
    db.refresh(report)

    audit_service.log(
        db=db,
        actor="coordinator",
        action="REPORT_EXTRACTION_RETRIED",
        entity_type="report",
        entity_id=report.id,
        details={"result": report.processing_status}
    )

    return report
