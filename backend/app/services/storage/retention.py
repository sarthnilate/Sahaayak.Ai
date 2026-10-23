"""
Phase 9: Data Lifecycle — Retention Job

Implements the image retention policy:
- Scans reports older than RETENTION_DAYS
- Deletes uploaded image file from disk
- Marks report with evidence_expired=True (report data preserved)
- Writes immutable audit event for each deletion

Usage (CLI):
    python -m backend.app.services.storage.retention --days 30
    
Usage (programmatic):
    from backend.app.services.storage.retention import run_retention
    result = run_retention(db=db, retention_days=30)
"""

import argparse
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.models.all_models import Report, ReportStatusEnum
from backend.app.services.audit.service import AuditService
from backend.app.services.storage.provider import storage_provider
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def run_retention(
    db: Session,
    retention_days: int = settings.RETENTION_DAYS,
) -> Dict[str, Any]:
    """
    Deletes uploaded image files for reports older than retention_days.
    
    Guarantees:
    - Report row is preserved (original_text, extracted_json, audit history)
    - evidence_expired flag set to True on the report
    - Immutable audit event written for each deletion
    - media_path cleared after successful file deletion
    
    Returns dict with: scanned, expired, files_deleted, files_missing, errors
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    
    # Find all reports with media files submitted before cutoff
    stmt = (
        select(Report)
        .where(Report.media_path.isnot(None))
        .where(Report.submitted_at < cutoff)
        .where(Report.evidence_expired.is_(False))
    )
    reports_with_media = db.execute(stmt).scalars().all()
    
    scanned = len(reports_with_media)
    expired = 0
    files_deleted = 0
    files_missing = 0
    errors = 0
    
    for report in reports_with_media:
        try:
            # Delete the file from disk (best-effort)
            file_deleted = False
            if report.media_path:
                file_deleted = storage_provider.delete_file(report.media_path)
                if file_deleted:
                    files_deleted += 1
                    logger.info(f"Deleted media file for report {report.id}: {report.media_path}")
                else:
                    files_missing += 1
                    logger.warning(
                        f"Media file not found for report {report.id}: {report.media_path}"
                    )
            
            # Mark report as evidence expired (preserve all other data)
            old_media_path = report.media_path
            report.media_path = None
            report.evidence_expired = True
            db.flush()
            
            # Write immutable audit event
            AuditService.record(
                db=db,
                actor="system:retention_job",
                action="MEDIA_EVIDENCE_EXPIRED",
                entity_type="report",
                entity_id=report.id,
                before={"media_path": old_media_path},
                after={
                    "evidence_expired": True,
                    "media_path": None,
                    "retention_days": retention_days,
                    "cutoff_date": cutoff.isoformat(),
                    "file_deleted": file_deleted,
                },
            )
            
            expired += 1
            
        except Exception as e:
            logger.error(f"Retention error for report {report.id}: {e}")
            errors += 1
    
    db.commit()
    
    result = {
        "scanned": scanned,
        "expired": expired,
        "files_deleted": files_deleted,
        "files_missing": files_missing,
        "errors": errors,
        "retention_days": retention_days,
        "cutoff_date": cutoff.isoformat(),
    }
    
    logger.info(
        f"Retention run complete: scanned={scanned}, expired={expired}, "
        f"files_deleted={files_deleted}, errors={errors}"
    )
    
    return result


def main():
    """CLI entry point for the retention job."""
    parser = argparse.ArgumentParser(
        description="Sahaayak AI — Media Retention Job"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=settings.RETENTION_DAYS,
        help=f"Retention period in days (default: {settings.RETENTION_DAYS})",
    )
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        result = run_retention(db=db, retention_days=args.days)
        print(f"✅ Retention complete: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
