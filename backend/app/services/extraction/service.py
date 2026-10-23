import logging
from datetime import datetime, timezone
from typing import Optional

from backend.app.core.errors import EntityNotFoundError
from backend.app.models.all_models import Report, ReportStatusEnum
from backend.app.schemas.extraction_schema import (
    CoordinatorCorrectionSchema,
    ExtractionResult,
    ReportExtractionSchema,
)
from backend.app.services.audit.service import AuditService
from backend.app.services.extraction.provider import (
    ExtractionProvider,
    get_extraction_provider,
)
from backend.app.services.storage.provider import storage_provider
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

MAX_EXTRACTION_ATTEMPTS = 5


class ExtractionService:
    def __init__(self, provider: Optional[ExtractionProvider] = None):
        self.provider = provider or get_extraction_provider()

    async def process_report(
        self,
        db: Session,
        report_id: str,
        actor: str = "system:ai_extraction",
        force_retry: bool = False,
    ) -> Report:
        """
        Orchestrates AI extraction for a report:
        1. Checks cache: if already processed and not force_retry, returns cached result.
        2. Sets status to 'processing'.
        3. Loads optional image bytes securely from storage provider.
        4. Invokes AI extraction provider.
        5. Validates extraction output with Pydantic BEFORE database write.
        6. Persists extraction, metadata, and status ('processed' or 'needs_review').
        7. On failure, preserves original report intact and records a safe error code.
        8. Writes immutable audit events for every attempt.
        """
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise EntityNotFoundError("Report", report_id)

        # 1. Cache check
        if (
            not force_retry
            and report.processing_status in [ReportStatusEnum.PROCESSED, ReportStatusEnum.NEEDS_REVIEW]
            and report.extracted_json is not None
        ):
            logger.info(f"Report {report_id} already has valid extraction; returning cached result.")
            return report

        # Check maximum retry attempts bound
        if report.attempt_count >= MAX_EXTRACTION_ATTEMPTS and not force_retry:
            logger.warning(f"Report {report_id} has exceeded maximum extraction attempts ({MAX_EXTRACTION_ATTEMPTS}).")
            return report

        # 2. Mark processing
        report.processing_status = ReportStatusEnum.PROCESSING
        report.attempt_count += 1
        db.commit()
        db.refresh(report)

        # 3. Read image bytes if media_path exists
        image_bytes: Optional[bytes] = None
        if report.media_path:
            try:
                image_bytes = storage_provider.get_file(report.media_path)
            except Exception as e:
                logger.warning(f"Could not load media for report {report_id}: {e}")

        # 4. Invoke Provider
        try:
            result: ExtractionResult = await self.provider.extract(
                text=report.original_text,
                image_bytes=image_bytes,
                mime_type=report.media_type,
                incident_time=report.incident_time,
            )

            if not result.extraction:
                raise ValueError("Extraction provider returned empty extraction schema")

            # 5. Pydantic validation before DB write
            validated = ReportExtractionSchema.model_validate(result.extraction)

            # Determine if report needs review
            needs_review = (
                validated.category == "unknown"
                or bool(validated.contradictions)
                or bool(validated.ambiguities)
                or bool(validated.missing_information)
                or validated.claimed_severity == "unknown"
            )

            # 6. Persist
            extracted_dict = validated.model_dump(mode="json")
            # Legacy compatibility aliases
            extracted_dict["hazard_type"] = validated.category
            extracted_dict["severity"] = validated.claimed_severity
            extracted_dict["summary"] = validated.short_summary

            report.extracted_json = extracted_dict
            report.extraction_metadata = result.metadata.model_dump(mode="json")
            report.processing_status = (
                ReportStatusEnum.NEEDS_REVIEW if needs_review else ReportStatusEnum.PROCESSED
            )
            report.extraction_source = result.metadata.provider
            report.processed_at = datetime.now(timezone.utc)
            report.error_message = None

            db.commit()
            db.refresh(report)

            # Audit event
            AuditService.record(
                db=db,
                actor=actor,
                action="REPORT_EXTRACTED",
                entity_type="report",
                entity_id=report.id,
                after={
                    "provider": result.metadata.provider,
                    "mode": result.metadata.mode,
                    "model": result.metadata.model,
                    "latency_ms": result.metadata.latency_ms,
                    "status": report.processing_status.value,
                    "category": validated.category,
                    "simulated": result.metadata.simulated,
                },
            )

            return report

        except Exception as exc:
            # 7. Preserve report on failure and record safe error code
            safe_code = getattr(exc, "code", "AI_EXTRACTION_FAILED")
            safe_msg = getattr(exc, "message", str(exc))

            # Strip any potential API key or sensitive data from error string
            safe_msg = safe_msg.replace(report.original_text, "[REDACTED_TEXT]")

            report.processing_status = ReportStatusEnum.FAILED
            report.error_message = f"[{safe_code}] {safe_msg[:200]}"
            db.commit()
            db.refresh(report)

            # Audit event on failure (no payload leakage)
            AuditService.record(
                db=db,
                actor=actor,
                action="REPORT_EXTRACTION_FAILED",
                entity_type="report",
                entity_id=report.id,
                after={
                    "error_code": safe_code,
                    "attempt_count": report.attempt_count,
                },
            )

            logger.error(f"AI extraction failed for report {report_id}: {safe_code} - {safe_msg}")
            return report

    def apply_coordinator_correction(
        self,
        db: Session,
        report_id: str,
        correction: CoordinatorCorrectionSchema,
        coordinator_name: str,
    ) -> Report:
        """
        Stores coordinator corrections separately from AI output.
        Does NOT overwrite original AI extraction (preserves audit integrity).
        """
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise EntityNotFoundError("Report", report_id)

        correction_dict = correction.model_dump(mode="json")
        report.coordinator_correction = correction_dict
        report.correction_notes = correction.correction_notes
        report.corrected_by = coordinator_name
        report.corrected_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(report)

        # Audit correction
        AuditService.record(
            db=db,
            actor=coordinator_name,
            action="REPORT_EXTRACTION_CORRECTED",
            entity_type="report",
            entity_id=report.id,
            after={
                "corrected_category": str(correction.corrected_category) if correction.corrected_category else None,
                "corrected_severity": str(correction.corrected_severity) if correction.corrected_severity else None,
                "notes_length": len(correction.correction_notes),
            },
        )

        return report
