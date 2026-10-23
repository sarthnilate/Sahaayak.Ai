"""
IMD API Provider (Secondary source).
Checks credentials against api.imd.gov.in.
If IMD_API_KEY is missing, gracefully transitions to 'not_configured' status.
If key is present, queries official endpoint with strict host and SSRF protection.
"""

from datetime import datetime, timezone
import hashlib
import logging
from typing import List, Optional

from backend.app.core.config import settings
from backend.app.services.live_data.provider_base import (
    BaseLiveDataProvider,
    NormalizedAlert,
    SafeLiveClient,
    SourceStatusResult,
    LiveDataFetchError,
)

logger = logging.getLogger(__name__)


class ImdApiProvider(BaseLiveDataProvider):
    """
    Integrates with India Meteorological Department (IMD) API gateway.
    Base URL: https://api.imd.gov.in/api/v1/
    Requires valid API key issued by IMD.
    """

    def __init__(self, client: Optional[SafeLiveClient] = None):
        self.client = client or SafeLiveClient()
        self.base_url = settings.IMD_API_BASE_URL.rstrip("/")
        self.api_key = getattr(settings, "IMD_API_KEY", None)

    @property
    def source_id(self) -> str:
        return "imd_api"

    @property
    def display_name(self) -> str:
        return "India Meteorological Department (IMD) API"

    def check_status(self) -> SourceStatusResult:
        if not self.api_key:
            return SourceStatusResult(
                source_id=self.source_id,
                display_name=self.display_name,
                status="not_configured",
                last_fetched_at=datetime.now(timezone.utc),
                error_message="IMD_API_KEY environment variable not configured. Requires official registration at api.imd.gov.in.",
            )

        try:
            url = f"{self.base_url}/alerts"
            headers = {"X-API-KEY": self.api_key}
            resp = self.client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("alerts", []) if isinstance(data, dict) else []
                return SourceStatusResult(
                    source_id=self.source_id,
                    display_name=self.display_name,
                    status="live_ok" if items else "live_empty",
                    last_fetched_at=datetime.now(timezone.utc),
                    item_count=len(items),
                    http_status=resp.status_code,
                )
            elif resp.status_code in (401, 403):
                return SourceStatusResult(
                    source_id=self.source_id,
                    display_name=self.display_name,
                    status="blocked",
                    last_fetched_at=datetime.now(timezone.utc),
                    http_status=resp.status_code,
                    error_message=f"Authentication rejected by IMD API (HTTP {resp.status_code}). Verify API key permissions.",
                )
            else:
                return SourceStatusResult(
                    source_id=self.source_id,
                    display_name=self.display_name,
                    status="error",
                    last_fetched_at=datetime.now(timezone.utc),
                    http_status=resp.status_code,
                    error_message=f"HTTP {resp.status_code} from IMD API.",
                )
        except Exception as e:
            return SourceStatusResult(
                source_id=self.source_id,
                display_name=self.display_name,
                status="error",
                last_fetched_at=datetime.now(timezone.utc),
                error_message=str(e),
            )

    def fetch_alerts(self, force_refresh: bool = False) -> List[NormalizedAlert]:
        if not self.api_key:
            logger.info("IMD API key not configured; skipping fetch.")
            return []

        try:
            url = f"{self.base_url}/alerts"
            headers = {"X-API-KEY": self.api_key}
            resp = self.client.get(url, headers=headers)
            if resp.status_code != 200:
                raise LiveDataFetchError(f"IMD API returned HTTP {resp.status_code}")

            data = resp.json()
            items = data.get("alerts", []) if isinstance(data, dict) else []
            alerts: List[NormalizedAlert] = []

            for item in items:
                alert_id = str(item.get("id") or item.get("alert_id") or "")
                headline = item.get("headline") or item.get("title") or "IMD Weather Warning"
                event = item.get("event") or "Weather Alert"
                severity = item.get("severity") or "Moderate"
                area = item.get("district") or item.get("state") or "India"

                content_hash = hashlib.sha256(
                    f"{self.source_id}|{alert_id}|{headline}|{severity}".encode("utf-8")
                ).hexdigest()

                alerts.append(
                    NormalizedAlert(
                        source_id=self.source_id,
                        external_identifier=alert_id,
                        headline=headline,
                        event=event,
                        severity=severity,
                        urgency=item.get("urgency"),
                        certainty=item.get("certainty"),
                        area_description=area,
                        sender="India Meteorological Department",
                        source_url=f"https://mausam.imd.gov.in/",
                        content_hash=content_hash,
                        is_synthetic=False,
                    )
                )

            return alerts
        except Exception as e:
            logger.error(f"Failed to fetch alerts from IMD API: {e}")
            raise LiveDataFetchError(f"IMD fetch failed: {e}") from e
