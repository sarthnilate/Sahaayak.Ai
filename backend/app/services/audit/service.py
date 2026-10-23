import copy
from typing import Any, Dict, Optional

from backend.app.models.all_models import AuditEvent
from backend.app.repositories.audit_repository import AuditRepository
from sqlalchemy.orm import Session

SENSITIVE_KEYS = {
    "password",
    "token",
    "jwt",
    "secret",
    "gemini_api_key",
    "api_key",
    "authorization",
}


def redact_metadata(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not data or not isinstance(data, dict):
        return data

    cleaned = copy.deepcopy(data)
    for key, value in list(cleaned.items()):
        if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
            cleaned[key] = "***REDACTED***"
        elif isinstance(value, dict):
            cleaned[key] = redact_metadata(value)
        elif (
            key.lower() in {"original_text", "report_body", "raw_content"}
            and isinstance(value, str)
            and len(value) > 100
        ):
            # Keep snippet for audit identification while preserving user confidentiality
            cleaned[key] = f"{value[:80]}... [TRUNCATED_FOR_AUDIT]"
    return cleaned


class AuditService:
    @staticmethod
    def record(
        db: Session,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        repo = AuditRepository(db)
        event = AuditEvent(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            before_state=redact_metadata(before),
            after_state=redact_metadata(after),
        )
        repo.add(event)
        repo.commit()
        repo.refresh(event)
        return event

    @staticmethod
    def log(
        db: Session,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str,
        details: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        return AuditService.record(
            db=db,
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before=before,
            after=after or details,
        )


audit_service = AuditService()
