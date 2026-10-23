from typing import List, Optional

from backend.app.core.errors import AuditMutationForbiddenError
from backend.app.models.all_models import AuditEvent
from backend.app.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.orm import Session


class AuditRepository(BaseRepository[AuditEvent]):
    def __init__(self, db: Session):
        super().__init__(AuditEvent, db)

    def list_events(self, entity_type: Optional[str] = None, limit: int = 50) -> List[AuditEvent]:
        stmt = select(AuditEvent).order_by(AuditEvent.timestamp.desc())
        if entity_type:
            stmt = stmt.where(AuditEvent.entity_type == entity_type)
        return list(self.db.scalars(stmt.limit(limit)).all())

    def update(self, *args, **kwargs):
        raise AuditMutationForbiddenError("UPDATE")

    def delete(self, *args, **kwargs):
        raise AuditMutationForbiddenError("DELETE")
