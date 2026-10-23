"""
Phase 5: Candidate duplicate matching service.
Coordinates database pre-filtering, evaluation via pure MatchingEngine,
persistence of suggested links with review_input_hash for re-suggest suppression,
and idempotent coordinator confirm/reject workflows with full audit logging.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.core.errors import EntityNotFoundError, SahaayakException
from backend.app.models.all_models import (
    AuditEvent,
    Incident,
    IncidentReportLink,
    IncidentStatusEnum,
    LinkStatusEnum,
    Report,
)
from backend.app.services.audit.service import AuditService
from backend.app.services.matching.engine import (
    MATCH_POSSIBLE_THRESHOLD,
    MATCH_STRONG_THRESHOLD,
    MatchBand,
    MatchEvaluation,
    MatchingEngine,
)


def compute_report_input_hash(report: Report) -> str:
    """Computes a hash of the report content and extraction to detect new evidence."""
    ext_str = json.dumps(report.extracted_json or {}, sort_keys=True)
    raw = f"{report.original_text}:::{ext_str}:::{report.location_claim or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


class MatchingService:
    @staticmethod
    def evaluate_match(report: Report, incident: Incident) -> Tuple[float, str, MatchEvaluation]:
        """
        Evaluates similarity score (0.0 to 1.0), human-readable rationale, and structured MatchEvaluation.
        Pure deterministic delegation to MatchingEngine.
        """
        rep_dict = {
            "category": (report.extracted_json or {}).get("category")
            or (report.extracted_json or {}).get("hazard_type")
            or "unknown",
            "original_text": report.original_text,
            "reported_location_text": (report.extracted_json or {}).get("reported_location_text")
            or report.location_claim,
            "latitude": report.coordinates_lat
            or (report.extracted_json or {}).get("approximate_lat"),
            "longitude": report.coordinates_lng
            or (report.extracted_json or {}).get("approximate_lng"),
            "has_grounded_coordinates": bool(
                report.coordinates_lat and report.coordinates_lng
            ),
            "submitted_at": report.submitted_at,
            "incident_time": report.incident_time,
            "source_fingerprint": report.source_fingerprint,
            "is_forwarded_message": (report.extracted_json or {}).get("is_forwarded_message"),
        }

        inc_dict = {
            "category": incident.category,
            "summary": incident.summary + " " + incident.title,
            "location_name": incident.location_name,
            "latitude": incident.latitude,
            "longitude": incident.longitude,
            "has_grounded_coordinates": incident.has_grounded_coordinates,
            "created_at": incident.created_at,
        }

        evaluation = MatchingEngine.evaluate_pair(rep_dict, inc_dict)
        return evaluation.score, evaluation.rationale, evaluation

    @staticmethod
    def find_and_persist_candidates_for_report(
        db: Session,
        report_id: str,
        actor: str = "system_matcher"
    ) -> List[IncidentReportLink]:
        """
        Finds matching incidents for a report using pre-filtering to avoid O(n^2) scans.
        Persists suggestions while respecting rejection input hashes (no re-suggest without new evidence).
        """
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise EntityNotFoundError(entity_name="Report", entity_id=report_id)

        rep_cat = (report.extracted_json or {}).get("category") or (report.extracted_json or {}).get("hazard_type")
        current_input_hash = compute_report_input_hash(report)

        # Copied-claim origin grouping
        if report.source_fingerprint:
            copied_reports = (
                db.query(Report)
                .filter(
                    Report.source_fingerprint == report.source_fingerprint,
                    Report.id != report.id,
                )
                .all()
            )
            if copied_reports:
                # Use existing origin_group_id or create one
                existing_group = next((r.origin_group_id for r in copied_reports if r.origin_group_id), None)
                group_id = existing_group or f"group-{report.source_fingerprint[:12]}"
                report.origin_group_id = group_id
                for cr in copied_reports:
                    if not cr.origin_group_id:
                        cr.origin_group_id = group_id

        # 1. SQL Pre-filtering by Category and Non-Closed status
        # This prevents O(n^2) over the entire database
        query = db.query(Incident).filter(
            Incident.status != IncidentStatusEnum.CLOSED
        )
        if rep_cat and rep_cat != "unknown":
            # Broad category filter (same category or general)
            query = query.filter(Incident.category == rep_cat)

        # Time window pre-filter (within 48 hours of report submission)
        if report.submitted_at:
            window_start = report.submitted_at - timedelta(hours=48)
            window_end = report.submitted_at + timedelta(hours=48)
            query = query.filter(Incident.created_at >= window_start, Incident.created_at <= window_end)

        candidates = query.limit(50).all()
        created_or_updated_links: List[IncidentReportLink] = []

        for incident in candidates:
            # Check existing link
            existing_link = (
                db.query(IncidentReportLink)
                .filter(
                    IncidentReportLink.incident_id == incident.id,
                    IncidentReportLink.report_id == report.id,
                )
                .first()
            )

            # Re-suggest suppression:
            # If coordinator rejected this pair AND the report's input_hash hasn't changed, DO NOT re-suggest!
            if existing_link and existing_link.status == LinkStatusEnum.REJECTED:
                if existing_link.review_input_hash == current_input_hash:
                    continue  # Suppressed: no new evidence

            score, rationale, evaluation = MatchingService.evaluate_match(report, incident)

            # Only suggest if match band is possible or strong
            if evaluation.band in [MatchBand.POSSIBLE, MatchBand.STRONG] and not evaluation.is_suppressed:
                signals_data = [s.model_dump() for s in evaluation.signals_for + evaluation.signals_against]

                if existing_link:
                    # Update existing suggestion if inputs changed
                    existing_link.similarity_score = score
                    existing_link.match_band = evaluation.band.value
                    existing_link.match_rationale = rationale
                    existing_link.signals_json = signals_data
                    existing_link.status = LinkStatusEnum.SUGGESTED
                    created_or_updated_links.append(existing_link)
                else:
                    new_link = IncidentReportLink(
                        incident_id=incident.id,
                        report_id=report.id,
                        status=LinkStatusEnum.SUGGESTED,
                        similarity_score=score,
                        match_band=evaluation.band.value,
                        match_rationale=rationale,
                        signals_json=signals_data,
                        review_input_hash=current_input_hash,
                    )
                    db.add(new_link)
                    created_or_updated_links.append(new_link)

                    AuditService.record(
                        db=db,
                        actor=actor,
                        action="MATCH_SUGGESTION_CREATED",
                        entity_type="incident_report_link",
                        entity_id=f"{incident.id}:{report.id}",
                        after={
                            "incident_id": incident.id,
                            "report_id": report.id,
                            "score": score,
                            "band": evaluation.band.value,
                            "rationale": rationale,
                        },
                    )

        db.commit()
        return created_or_updated_links

    @staticmethod
    def confirm_link(
        db: Session,
        incident_id: str,
        report_id: str,
        reviewer_email: str,
        notes: Optional[str] = None
    ) -> IncidentReportLink:
        """
        Idempotent confirmation of an incident-report match.
        Never modifies, overwrites, or deletes original report data.
        """
        link = (
            db.query(IncidentReportLink)
            .filter(
                IncidentReportLink.incident_id == incident_id,
                IncidentReportLink.report_id == report_id,
            )
            .first()
        )

        if not link:
            raise EntityNotFoundError(
                entity_name="IncidentReportLink", entity_id=f"{incident_id}:{report_id}"
            )

        if link.status == LinkStatusEnum.CONFIRMED:
            return link  # Idempotent

        before_state = {
            "status": link.status.value,
            "reviewed_by": link.reviewed_by,
            "reviewed_at": link.reviewed_at.isoformat() if link.reviewed_at else None,
        }

        link.status = LinkStatusEnum.CONFIRMED
        link.reviewed_by = reviewer_email
        link.reviewed_at = datetime.now(timezone.utc)
        if notes:
            link.reviewer_notes = notes

        db.commit()
        db.refresh(link)

        AuditService.record(
            db=db,
            actor=reviewer_email,
            action="REPORT_MATCH_CONFIRMED",
            entity_type="incident_report_link",
            entity_id=link.id,
            before=before_state,
            after={
                "status": link.status.value,
                "reviewed_by": link.reviewed_by,
                "reviewed_at": link.reviewed_at.isoformat(),
                "reviewer_notes": link.reviewer_notes,
            },
        )

        return link

    @staticmethod
    def reject_link(
        db: Session,
        incident_id: str,
        report_id: str,
        reviewer_email: str,
        notes: Optional[str] = None
    ) -> IncidentReportLink:
        """
        Idempotent rejection of an incident-report match.
        Records current review_input_hash so link is not re-suggested unless evidence changes.
        """
        link = (
            db.query(IncidentReportLink)
            .filter(
                IncidentReportLink.incident_id == incident_id,
                IncidentReportLink.report_id == report_id,
            )
            .first()
        )

        if not link:
            raise EntityNotFoundError(
                entity_name="IncidentReportLink", entity_id=f"{incident_id}:{report_id}"
            )

        if link.status == LinkStatusEnum.REJECTED:
            return link  # Idempotent

        report = db.query(Report).filter(Report.id == report_id).first()
        current_hash = compute_report_input_hash(report) if report else None

        before_state = {
            "status": link.status.value,
            "reviewed_by": link.reviewed_by,
            "reviewed_at": link.reviewed_at.isoformat() if link.reviewed_at else None,
        }

        link.status = LinkStatusEnum.REJECTED
        link.reviewed_by = reviewer_email
        link.reviewed_at = datetime.now(timezone.utc)
        link.review_input_hash = current_hash
        if notes:
            link.reviewer_notes = notes

        db.commit()
        db.refresh(link)

        AuditService.record(
            db=db,
            actor=reviewer_email,
            action="REPORT_MATCH_REJECTED",
            entity_type="incident_report_link",
            entity_id=link.id,
            before=before_state,
            after={
                "status": link.status.value,
                "reviewed_by": link.reviewed_by,
                "reviewed_at": link.reviewed_at.isoformat(),
                "review_input_hash": link.review_input_hash,
                "reviewer_notes": link.reviewer_notes,
            },
        )

        return link


matching_service = MatchingService()
