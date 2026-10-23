import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from backend.app.services.live_data.provider_base import (
    validate_live_url,
    LiveDataSecurityError,
    NormalizedAlert,
    SafeLiveClient,
)
from backend.app.services.live_data.sachet_provider import SachetCapProvider
from backend.app.services.live_data.imd_provider import ImdApiProvider
from backend.app.services.live_data.applicability import check_alert_applicability, haversine_km
from backend.app.services.live_data.live_data_service import LiveDataService
from backend.app.models.all_models import ExternalAlert, Incident, User


def test_ssrf_host_allowlist_enforcement():
    """Ensure host allowlist blocks arbitrary external domains and loopback."""
    # Allowed hosts
    validate_live_url("https://sachet.ndma.gov.in/cap_public_website/FetchAllAlertDetails")
    validate_live_url("https://api.imd.gov.in/api/v1/alerts")

    # Disallowed hosts
    with pytest.raises(LiveDataSecurityError, match="not in ALLOWED_LIVE_HOSTS"):
        validate_live_url("https://evil.com/leak")

    with pytest.raises(LiveDataSecurityError, match="not in ALLOWED_LIVE_HOSTS"):
        validate_live_url("https://google.com")

    # Insecure HTTP
    with pytest.raises(LiveDataSecurityError, match="Only HTTPS allowed"):
        validate_live_url("http://sachet.ndma.gov.in/feed")


def test_defusedxml_xxe_protection():
    """Ensure billion-laughs and external entity injections are defused without executing."""
    xxe_payload = """<?xml version="1.0"?>
    <!DOCTYPE alert [
      <!ENTITY xxe SYSTEM "file:///etc/passwd">
    ]>
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
      <identifier>XXE-TEST</identifier>
      <info>
        <headline>&xxe;</headline>
        <event>Test</event>
      </info>
    </alert>"""

    # defusedxml will refuse entity expansion or return safe text
    parsed = SachetCapProvider.parse_cap_xml(xxe_payload)
    if parsed:
        # Should NOT contain contents of /etc/passwd (e.g. "root:")
        assert "root:" not in (parsed.headline or "")


def test_real_sachet_xml_fixture_parsing():
    """Parse real NDMA SACHET CAP 1.2 XML captured from production endpoint."""
    with open("backend/tests/fixtures/live_data/real_sachet_cap_1792745162631029.xml", "r") as f:
        xml_data = f.read()

    alert = SachetCapProvider.parse_cap_xml(xml_data)
    assert alert is not None
    assert "1792745162631029" in alert.external_identifier
    assert "Thunderstorm with Lightning" in alert.headline
    assert "Kolhapur" in alert.area_description or "Kolhapur" in alert.headline
    assert alert.source_id == "ndma_sachet"
    assert alert.is_synthetic is False
    assert alert.severity.lower() in ("moderate", "severe", "extreme", "unknown")


def test_imd_provider_unconfigured_state():
    """IMD provider must return 'not_configured' status when IMD_API_KEY is not set."""
    provider = ImdApiProvider()
    provider.api_key = None
    status = provider.check_status()
    assert status.status == "not_configured"
    assert "not configured" in status.error_message.lower()
    assert provider.fetch_alerts() == []


def test_alert_freshness_calculation():
    """Test fresh vs expired status based on expires_at timestamp."""
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    future = datetime.now(timezone.utc) + timedelta(hours=2)

    stale_alert = NormalizedAlert(
        source_id="test",
        external_identifier="stale-1",
        headline="Old Flood Warning",
        event="Flood",
        severity="Severe",
        urgency="Past",
        certainty="Observed",
        area_description="Pune",
        expires_at=past,
    )
    assert stale_alert.freshness == "expired"

    active_alert = NormalizedAlert(
        source_id="test",
        external_identifier="active-1",
        headline="Active Flood Warning",
        event="Flood",
        severity="Severe",
        urgency="Immediate",
        certainty="Observed",
        area_description="Pune",
        expires_at=future,
    )
    assert active_alert.freshness == "fresh"


def test_applicability_engine_district_matching():
    """Verify deterministic token boundary matching for districts and states."""
    headline = "Flash Flood warning issued for Mumbai Suburban and Thane districts"
    area = "Mumbai Suburban, Thane, Palghar"

    # Match in area
    is_app, rationale, dist = check_alert_applicability(
        alert_area=area,
        alert_headline=headline,
        incident_location_name="Bandra Kurla Complex, Mumbai Suburban",
    )
    assert is_app is True
    assert "Mumbai" in rationale

    # Non-match
    is_app_neg, _, _ = check_alert_applicability(
        alert_area=area,
        alert_headline=headline,
        incident_location_name="Nagpur Central Railway Colony",
    )
    assert is_app_neg is False


def test_applicability_engine_centroid_distance():
    """Verify coordinate proximity match using centroid lat,lon."""
    # Alert centered near Mumbai (19.0760, 72.8777)
    alert_centroid = "19.0760,72.8777"

    # Incident 15km away in Navi Mumbai (19.0330, 73.0297)
    is_app, rationale, dist = check_alert_applicability(
        alert_area="Konkan Region",
        alert_headline="Heavy Rainfall Warning",
        incident_location_name="Sector 17 Vashi",
        incident_lat=19.0330,
        incident_lon=73.0297,
        alert_centroid=alert_centroid,
        max_distance_km=50.0,
    )
    assert is_app is True
    assert dist is not None
    assert dist < 30.0
    assert "centroid" in rationale


from backend.app.db.session import SessionLocal

def test_live_data_service_db_persistence():
    """Test ingesting mock alerts and querying them through LiveDataService."""
    db_session = SessionLocal()
    try:
        mock_provider = MagicMock(spec=SachetCapProvider)
        mock_provider.source_id = "mock_source"
        mock_provider.display_name = "Mock Provider"
        mock_provider.index_url = "https://sachet.ndma.gov.in/test"
        mock_provider.fetch_alerts.return_value = [
            NormalizedAlert(
                source_id="mock_source",
                external_identifier="MOCK-001",
                headline="Severe Coastal Inundation Advisory",
                event="Flood",
                severity="Severe",
                urgency="Immediate",
                certainty="Observed",
                area_description="Ratnagiri Coastal Zone",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=4),
            )
        ]
        mock_provider.check_status.return_value = MagicMock(
            source_id="mock_source", display_name="Mock Provider", status="live_ok", item_count=1, http_status=200, details={}, error_message=None
        )

        service = LiveDataService(db_session, providers=[mock_provider])
        res = service.refresh_source("mock_source")
        assert res["created"] == 1

        alerts = service.list_alerts(source_id="mock_source")
        assert len(alerts) >= 1
        assert any(a.external_identifier == "MOCK-001" for a in alerts)

        # Re-running refresh does not duplicate due to hash check
        res2 = service.refresh_source("mock_source")
        assert res2["created"] == 0
        assert res2["updated"] == 1
    finally:
        db_session.close()


class TestLiveSourcesApiEndpoints:
    @pytest.fixture(autouse=True)
    def setup_seed(self):
        from fastapi.testclient import TestClient
        from backend.app.main import app
        client = TestClient(app)
        client.post("/api/v1/seed")

    def _login(self, client, email: str, password: str) -> str:
        res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert res.status_code == 200
        return res.json()["csrf_token"]

    def test_sources_status_endpoint(self):
        from fastapi.testclient import TestClient
        from backend.app.main import app
        client = TestClient(app)
        csrf = self._login(client, "coordinator@sahaayak.ai", "CoordPass@2026")

        res = client.get("/api/v1/live-sources/status", headers={"X-CSRF-Token": csrf})
        assert res.status_code == 200
        sources = res.json()
        assert len(sources) >= 2
        source_ids = [s["source_id"] for s in sources]
        assert "ndma_sachet" in source_ids
        assert "imd_api" in source_ids

    def test_refresh_rbac_restrictions(self):
        from fastapi.testclient import TestClient
        from backend.app.main import app
        client = TestClient(app)

        # Reporter cannot force refresh government feeds
        csrf_rep = self._login(client, "reporter@sahaayak.ai", "ReporterPass@2026")
        res = client.post("/api/v1/live-sources/refresh/ndma_sachet", headers={"X-CSRF-Token": csrf_rep})
        assert res.status_code == 403

    def test_live_alerts_list_and_applicability(self):
        from fastapi.testclient import TestClient
        from backend.app.main import app
        client = TestClient(app)
        csrf = self._login(client, "coordinator@sahaayak.ai", "CoordPass@2026")

        # Ingest mock alert directly
        from backend.app.db.session import SessionLocal
        db = SessionLocal()
        try:
            alert = ExternalAlert(
                source_id="ndma_sachet",
                external_identifier="TEST-APP-001",
                headline="Severe Flood Warning for Dadar and Hindmata",
                event="Flood",
                severity="Severe",
                urgency="Immediate",
                certainty="Observed",
                area_description="Hindmata, Dadar, Mumbai",
                language="en",
                content_hash="test_app_hash_123",
                is_synthetic=False,
                is_expired=False,
                retrieved_at=datetime.now(timezone.utc),
            )
            db.merge(alert)
            db.commit()
        finally:
            db.close()

        # Query alerts list
        res_list = client.get("/api/v1/live-alerts?q=Hindmata", headers={"X-CSRF-Token": csrf})
        assert res_list.status_code == 200
        alerts = res_list.json()
        assert len(alerts) >= 1
        assert alerts[0]["external_identifier"] == "TEST-APP-001"

        # Check applicability for Hindmata incident
        res_app = client.get("/api/v1/live-alerts/for-incident/inc-hindmata-001", headers={"X-CSRF-Token": csrf})
        assert res_app.status_code == 200
        app_list = res_app.json()
        assert len(app_list) >= 1
        assert app_list[0]["is_applicable"] is True
        assert "Dadar" in app_list[0]["match_rationale"] or "Hindmata" in app_list[0]["match_rationale"]


@pytest.mark.live
def test_live_sachet_real_network_connectivity():
    """Opt-in live network connectivity test against official NDMA SACHET."""
    provider = SachetCapProvider()
    status = provider.check_status()
    assert status.status in ("live_ok", "live_empty")
    assert status.http_status == 200
