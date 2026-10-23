"""
Live Data Service: coordinates providers, persists snapshots, applies TTL cache,
and handles refresh triggers.
"""

from datetime import datetime, timezone, timedelta
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from backend.app.models.all_models import ExternalAlert, LiveSourceSnapshot
from backend.app.services.live_data.provider_base import (
    BaseLiveDataProvider,
    NormalizedAlert,
    SourceStatusResult,
)
from backend.app.services.live_data.sachet_provider import SachetCapProvider
from backend.app.services.live_data.imd_provider import ImdApiProvider

logger = logging.getLogger(__name__)

CACHE_TTL_MINUTES = 10


class LiveDataService:
    def __init__(self, db: Session, providers: Optional[List[BaseLiveDataProvider]] = None):
        self.db = db
        self.providers: Dict[str, BaseLiveDataProvider] = {}
        defaults = providers or [SachetCapProvider(), ImdApiProvider()]
        for p in defaults:
            self.providers[p.source_id] = p

    def get_sources_status(self) -> List[SourceStatusResult]:
        results: List[SourceStatusResult] = []
        for p in self.providers.values():
            status = p.check_status()
            # Overlay cached alert count from DB
            count = self.db.query(ExternalAlert).filter(
                ExternalAlert.source_id == p.source_id,
                ExternalAlert.is_expired == False,
            ).count()
            if status.status in ("live_ok", "live_empty"):
                status.item_count = count
            results.append(status)
        return results

    def refresh_source(self, source_id: str) -> Dict[str, int]:
        provider = self.providers.get(source_id)
        if not provider:
            raise ValueError(f"Unknown source: {source_id}")

        alerts = provider.fetch_alerts(force_refresh=True)
        now = datetime.now(timezone.utc)
        created_count = 0
        updated_count = 0

        for a in alerts:
            existing = self.db.query(ExternalAlert).filter(
                ExternalAlert.source_id == a.source_id,
                ExternalAlert.external_identifier == a.external_identifier,
                ExternalAlert.content_hash == a.content_hash,
            ).first()

            if not existing:
                alert_record = ExternalAlert(
                    source_id=a.source_id,
                    external_identifier=a.external_identifier,
                    headline=a.headline,
                    event=a.event,
                    severity=a.severity,
                    urgency=a.urgency,
                    certainty=a.certainty,
                    area_description=a.area_description,
                    language=a.language,
                    sender=a.sender,
                    sent_at=a.sent_at,
                    effective_at=a.effective_at,
                    expires_at=a.expires_at,
                    source_url=a.source_url,
                    centroid=a.centroid,
                    content_hash=a.content_hash,
                    raw_cap_xml=a.raw_cap_xml,
                    is_synthetic=a.is_synthetic,
                    is_expired=(a.freshness == "expired"),
                    retrieved_at=now,
                )
                self.db.add(alert_record)
                created_count += 1
            else:
                existing.retrieved_at = now
                existing.is_expired = (a.freshness == "expired")
                updated_count += 1

        # Record snapshot
        snapshot = LiveSourceSnapshot(
            source_id=source_id,
            url=getattr(provider, "index_url", "https://sachet.ndma.gov.in"),
            fetched_at=now,
            http_status=200,
            content_hash=f"snapshot_{now.timestamp()}",
            item_count=len(alerts),
            raw_payload_snippet=f"Ingested {len(alerts)} alerts ({created_count} new)",
        )
        self.db.add(snapshot)
        self.db.commit()

        return {"created": created_count, "updated": updated_count, "total_active": len(alerts)}

    def list_alerts(
        self,
        source_id: Optional[str] = None,
        severity: Optional[str] = None,
        state_or_district: Optional[str] = None,
        include_expired: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ExternalAlert]:
        query = self.db.query(ExternalAlert)
        if source_id:
            query = query.filter(ExternalAlert.source_id == source_id)
        if severity:
            query = query.filter(ExternalAlert.severity.ilike(f"%{severity}%"))
        if not include_expired:
            query = query.filter(ExternalAlert.is_expired == False)
        if state_or_district:
            pattern = f"%{state_or_district}%"
            query = query.filter(
                (ExternalAlert.area_description.ilike(pattern))
                | (ExternalAlert.headline.ilike(pattern))
            )

        return query.order_by(desc(ExternalAlert.retrieved_at)).offset(offset).limit(limit).all()
