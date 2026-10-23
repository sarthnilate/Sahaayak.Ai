"""
NDMA SACHET CAP 1.2 Feed Provider.
Fetches active alert index from sachet.ndma.gov.in and retrieves individual alert CAP 1.2 XML.
Parses XML securely using defusedxml to prevent XML Entity Expansion (Billion Laughs) and XXE.
"""

from datetime import datetime, timezone
import hashlib
import logging
from typing import Any, Dict, List, Optional
import defusedxml.ElementTree as ET

from backend.app.core.config import settings
from backend.app.services.live_data.provider_base import (
    BaseLiveDataProvider,
    NormalizedAlert,
    SafeLiveClient,
    SourceStatusResult,
    LiveDataFetchError,
)

logger = logging.getLogger(__name__)

# CAP 1.2 namespace
CAP_NS = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}


class SachetCapProvider(BaseLiveDataProvider):
    """
    Integrates with NDMA SACHET Public Portal.
    Primary endpoint: POST https://sachet.ndma.gov.in/cap_public_website/FetchAllAlertDetails
    Detail endpoint:  GET  https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier={id}
    """

    def __init__(self, client: Optional[SafeLiveClient] = None):
        self.client = client or SafeLiveClient()
        self.index_url = "https://sachet.ndma.gov.in/cap_public_website/FetchAllAlertDetails"
        self.detail_url_base = "https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile"

    @property
    def source_id(self) -> str:
        return "ndma_sachet"

    @property
    def display_name(self) -> str:
        return "NDMA SACHET CAP Feed"

    def check_status(self) -> SourceStatusResult:
        try:
            resp = self.client.post(self.index_url, json_data={})
            if resp.status_code == 200:
                data = resp.json()
                items = []
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("alert_details") or data.get("alerts") or []

                return SourceStatusResult(
                    source_id=self.source_id,
                    display_name=self.display_name,
                    status="live_ok" if items else "live_empty",
                    last_fetched_at=datetime.now(timezone.utc),
                    item_count=len(items),
                    http_status=resp.status_code,
                    details={"total_alerts": len(items)},
                )
            return SourceStatusResult(
                source_id=self.source_id,
                display_name=self.display_name,
                status="error",
                last_fetched_at=datetime.now(timezone.utc),
                http_status=resp.status_code,
                error_message=f"HTTP {resp.status_code}: {resp.text[:100]}",
            )
        except Exception as e:
            logger.warning(f"SACHET status check failed: {e}")
            return SourceStatusResult(
                source_id=self.source_id,
                display_name=self.display_name,
                status="error",
                last_fetched_at=datetime.now(timezone.utc),
                error_message=str(e),
            )

    def fetch_alerts(self, force_refresh: bool = False) -> List[NormalizedAlert]:
        """Fetch alert index and fetch CAP XML for top alerts."""
        try:
            resp = self.client.post(self.index_url, json_data={})
            if resp.status_code != 200:
                raise LiveDataFetchError(f"SACHET returned HTTP {resp.status_code}")
            
            data = resp.json()
            raw_alerts = []
            if isinstance(data, list):
                raw_alerts = data
            elif isinstance(data, dict):
                raw_alerts = data.get("alert_details") or data.get("alerts") or []

            normalized_list: List[NormalizedAlert] = []

            for item in raw_alerts:
                identifier = str(item.get("identifier") or item.get("alert_id") or "")
                if not identifier:
                    continue

                # Attempt to retrieve full CAP 1.2 XML for complete detail
                cap_xml_text: Optional[str] = None
                try:
                    xml_url = f"{self.detail_url_base}?identifier={identifier}"
                    xml_resp = self.client.get(xml_url)
                    if xml_resp.status_code == 200 and xml_resp.text:
                        cap_xml_text = xml_resp.text
                except Exception as ex:
                    logger.debug(f"Could not fetch XML for alert {identifier}: {ex}")

                if cap_xml_text:
                    parsed_alert = self.parse_cap_xml(cap_xml_text, identifier=identifier)
                    if parsed_alert:
                        normalized_list.append(parsed_alert)
                        continue

                # Fallback to fields present in JSON index if XML cannot be fetched
                headline = item.get("headline") or item.get("event") or "Emergency Alert"
                event = item.get("event") or item.get("hazard_name") or "Weather Event"
                severity = item.get("severity") or "Moderate"
                area_desc = item.get("area_description") or item.get("disaster_area") or item.get("district_name") or "India"
                urgency = item.get("urgency") or "Expected"
                certainty = item.get("certainty") or "Observed"
                sender = item.get("sender_name") or item.get("sender") or "NDMA"

                content_hash = hashlib.sha256(
                    f"{self.source_id}|{identifier}|{headline}|{severity}".encode("utf-8")
                ).hexdigest()

                normalized_list.append(
                    NormalizedAlert(
                        source_id=self.source_id,
                        external_identifier=identifier,
                        headline=headline,
                        event=event,
                        severity=severity,
                        urgency=urgency,
                        certainty=certainty,
                        area_description=area_desc,
                        sender=sender,
                        source_url=f"https://sachet.ndma.gov.in/public_alert/{identifier}",
                        content_hash=content_hash,
                        is_synthetic=False,
                    )
                )

            return normalized_list

        except Exception as e:
            logger.error(f"Failed to fetch alerts from SACHET: {e}")
            raise LiveDataFetchError(f"SACHET fetch failed: {e}") from e

    @classmethod
    def parse_cap_xml(cls, xml_content: str, identifier: str = "") -> Optional[NormalizedAlert]:
        """
        Parses CAP 1.2 XML string safely using defusedxml.
        Extracts all standard OASIS CAP 1.2 elements.
        """
        if not xml_content or not xml_content.strip():
            return None

        try:
            root = ET.fromstring(xml_content.strip())
        except Exception as e:
            logger.warning(f"defusedxml failed to parse CAP XML: {e}")
            return None

        def find_text(elem, tag: str) -> Optional[str]:
            # Try with namespace first, then unqualified
            ns_tag = f"{{urn:oasis:names:tc:emergency:cap:1.2}}{tag}"
            node = elem.find(ns_tag)
            if node is None or node.text is None:
                node = elem.find(tag)
            return node.text.strip() if (node is not None and node.text) else None

        alert_id = find_text(root, "identifier") or identifier or "UNKNOWN_ID"
        sender = find_text(root, "sender")
        sent_str = find_text(root, "sent")
        sent_at = cls._parse_iso_datetime(sent_str)

        info = root.find("{urn:oasis:names:tc:emergency:cap:1.2}info")
        if info is None:
            info = root.find("info")

        if info is None:
            return None

        language = find_text(info, "language") or "en"
        event = find_text(info, "event") or "Emergency Alert"
        urgency = find_text(info, "urgency") or "Unknown"
        severity = find_text(info, "severity") or "Unknown"
        certainty = find_text(info, "certainty") or "Unknown"
        headline = find_text(info, "headline") or event
        desc = find_text(info, "description") or headline

        effective_str = find_text(info, "effective")
        effective_at = cls._parse_iso_datetime(effective_str)
        expires_str = find_text(info, "expires")
        expires_at = cls._parse_iso_datetime(expires_str)

        # Area
        area = info.find("{urn:oasis:names:tc:emergency:cap:1.2}area")
        if area is None:
            area = info.find("area")

        area_desc = "Specified Area"
        centroid = None
        if area is not None:
            area_desc = find_text(area, "areaDesc") or desc
            circle = find_text(area, "circle")
            if circle:
                # circle is in format "lat,lon radius"
                parts = circle.split(" ")
                if parts:
                    centroid = parts[0]

        content_hash = hashlib.sha256(
            f"ndma_sachet|{alert_id}|{headline}|{severity}|{expires_str}".encode("utf-8")
        ).hexdigest()

        return NormalizedAlert(
            source_id="ndma_sachet",
            external_identifier=alert_id,
            headline=headline,
            event=event,
            severity=severity,
            urgency=urgency,
            certainty=certainty,
            area_description=area_desc,
            language=language,
            sender=sender,
            sent_at=sent_at,
            effective_at=effective_at,
            expires_at=expires_at,
            source_url=f"https://sachet.ndma.gov.in/public_alert/{alert_id}",
            centroid=centroid,
            raw_cap_xml=xml_content,
            content_hash=content_hash,
            is_synthetic=False,
        )

    @staticmethod
    def _parse_iso_datetime(val: Optional[str]) -> Optional[datetime]:
        if not val:
            return None
        try:
            return datetime.fromisoformat(val)
        except Exception:
            return None
