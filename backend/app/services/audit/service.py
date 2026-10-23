from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from backend.app.models.all_models import AuditEvent

class AuditService:
    @staticmethod
    def log(
        db: Session,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        event = AuditEvent(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {}
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

audit_service = AuditService()
