from typing import List, Optional

from backend.app.db.session import get_db
from backend.app.models.all_models import AuditEvent
from backend.app.schemas.all_schemas import AuditEventResponse
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/audit", response_model=List[AuditEventResponse])
def list_audit_events(
    entity_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc())
    if entity_type:
        query = query.filter(AuditEvent.entity_type == entity_type)
    return query.limit(limit).all()
