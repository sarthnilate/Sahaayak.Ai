"""
Phase 6: Comprehensive Evidence Handling, SSRF Guard, and State Machine Tests.
Verifies:
- Deterministic independence grouping (ten forwards of one message = count 1)
- Evidence status suggestion rules and transition validation
- SSRF guard (private IPs, loopback, AWS metadata, non-HTTPS, mocked DNS rebinding)
- Synthetic evidence flags and LIVE_DATA_FALLBACK policy
- Unavailable verification reporting
- RBAC and before/after audit tracking
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.core.errors import InvalidStateTransitionError
from backend.app.main import app
from backend.app.models.all_models import (
    EvidenceItem,
    EvidenceStatusEnum,
    EvidenceTypeEnum,
    Incident,
    IncidentStatusEnum,
    Report,
    RoleEnum,
    User,
)
from backend.app.services.evidence.independence import (
    compute_independent_source_count,
    group_evidence_by_origin,
)
from backend.app.services.evidence.missing_evidence import compute_missing_evidence
from backend.app.services.evidence.providers import (
    SourceLookupQuery,
    SyntheticFallbackProvider,
    verification_service,
)
from backend.app.services.evidence.ssrf_guard import (
    SSRFSecurityError,
    validate_url_safety,
)
from backend.app.services.evidence.state_machine import (
    is_valid_evidence_transition,
    suggest_evidence_status,
    validate_evidence_transition,
)


class TestIndependenceLogic:
    """Tests that claims sharing an origin or forward lineage count as ONE independent source."""

    def test_ten_forwards_of_one_message_give_independence_count_one(self):
        # Create a single origin report
        origin_report = Report(
            id="rep-origin-001",
            original_text="Dadar culvert flooded",
            input_language="en",
            source_fingerprint="fp-viral-broadcast-001",
            origin_group_id="origin-grp-viral-001",
        )

        # 10 forwarded reports sharing the same origin group / fingerprint
        items = []
        for i in range(10):
            item = EvidenceItem(
                id=f"ev-fwd-{i}",
                incident_id="inc-test-001",
                report_id=origin_report.id,
                evidence_type="user_claim",
                source_type="field_report",
                source_name=f"Forwarded Message #{i}",
                assessment="supports",
                independence_group="origin-grp-viral-001",
                is_simulated=True,
                claim_summary="Knee deep water reported",
                verification_status=EvidenceStatusEnum.CORROBORATING,
            )
            item.report = origin_report
            items.append(item)

        count = compute_independent_source_count(items)
        assert count == 1, f"Expected 1 independent source from 10 forwards, got {count}"

        groups = group_evidence_by_origin(items)
        assert len(groups) == 1
        assert "origin-grp-viral-001" in groups
        assert len(groups["origin-grp-viral-001"]) == 10

    def test_multiple_distinct_sources_give_correct_independence_count(self):
        item1 = EvidenceItem(
            id="ev-distinct-1",
            incident_id="inc-test-001",
            assessment="supports",
            independence_group="citizen-source-A",
            is_simulated=False,
            claim_summary="Flooding under bridge",
            verification_status=EvidenceStatusEnum.CORROBORATING,
        )
        item2 = EvidenceItem(
            id="ev-distinct-2",
            incident_id="inc-test-001",
            assessment="supports",
            independence_group="sensor-gauge-B",
            is_simulated=False,
            claim_summary="Sump gauge reading 90cm",
            verification_status=EvidenceStatusEnum.CORROBORATING,
        )
        item3 = EvidenceItem(
            id="ev-distinct-3",
            incident_id="inc-test-001",
            assessment="neutral",  # Neutral items do not add to corroborating count
            independence_group="social-rumor-C",
            is_simulated=False,
            claim_summary="General rain comment",
            verification_status=EvidenceStatusEnum.UNVERIFIED,
        )

        count = compute_independent_source_count([item1, item2, item3])
        assert count == 2, f"Expected 2 independent corroborating sources, got {count}"


class TestEvidenceStateMachineAndRules:
    """Tests deterministic status suggestion rules and transition validation."""

    def test_contradictory_evidence_suggests_conflicting(self):
        ev_supp = EvidenceItem(
            id="ev-1",
            incident_id="inc-1",
            assessment="supports",
            independence_group="grp-1",
            verification_status=EvidenceStatusEnum.CORROBORATING,
            claim_summary="Water rising",
        )
        ev_contra = EvidenceItem(
            id="ev-2",
            incident_id="inc-1",
            assessment="contradicts",
            evidence_type="contradictory",
            independence_group="grp-2",
            verification_status=EvidenceStatusEnum.CONFLICTING,
            claim_summary="No water present, road dry",
        )

        suggested = suggest_evidence_status([ev_supp, ev_contra])
        assert suggested == EvidenceStatusEnum.CONFLICTING_EVIDENCE

    def test_two_independent_sources_suggest_corroborated(self):
        ev1 = EvidenceItem(
            id="ev-1",
            incident_id="inc-1",
            assessment="supports",
            independence_group="source-citizen-1",
            verification_status=EvidenceStatusEnum.CORROBORATING,
            claim_summary="Water rising",
        )
        ev2 = EvidenceItem(
            id="ev-2",
            incident_id="inc-1",
            assessment="supports",
            independence_group="source-gauge-2",
            verification_status=EvidenceStatusEnum.CORROBORATING,
            claim_summary="Water rising",
        )

        suggested = suggest_evidence_status([ev1, ev2])
        assert suggested == EvidenceStatusEnum.CORROBORATED

    def test_single_source_suggests_partially_corroborated(self):
        ev1 = EvidenceItem(
            id="ev-1",
            incident_id="inc-1",
            assessment="supports",
            independence_group="source-citizen-1",
            verification_status=EvidenceStatusEnum.CORROBORATING,
            claim_summary="Water rising",
        )

        suggested = suggest_evidence_status([ev1])
        assert suggested == EvidenceStatusEnum.PARTIALLY_CORROBORATED

    def test_valid_and_invalid_state_transitions(self):
        # unverified -> partially_corroborated is valid
        assert is_valid_evidence_transition(EvidenceStatusEnum.UNVERIFIED, EvidenceStatusEnum.PARTIALLY_CORROBORATED)
        assert is_valid_evidence_transition(EvidenceStatusEnum.PARTIALLY_CORROBORATED, EvidenceStatusEnum.CORROBORATED)
        assert is_valid_evidence_transition(EvidenceStatusEnum.CORROBORATED, EvidenceStatusEnum.CONFLICTING_EVIDENCE)

        # unassessed directly to closed_after_review is invalid without review
        assert not is_valid_evidence_transition(EvidenceStatusEnum.UNASSESSED, EvidenceStatusEnum.CLOSED_AFTER_REVIEW)
        with pytest.raises(InvalidStateTransitionError):
            validate_evidence_transition(EvidenceStatusEnum.UNASSESSED, EvidenceStatusEnum.CLOSED_AFTER_REVIEW)


class TestSSRFGuard:
    """Tests the server-side request forgery protection for external URLs."""

    def test_non_https_schemes_blocked(self):
        res_http = validate_url_safety("http://example.com/api")
        assert not res_http.is_safe
        assert res_http.error_code == "SSRF_INVALID_SCHEME"

        res_file = validate_url_safety("file:///etc/passwd")
        assert not res_file.is_safe
        assert res_file.error_code == "SSRF_INVALID_SCHEME"

        res_gopher = validate_url_safety("gopher://127.0.0.1:70")
        assert not res_gopher.is_safe

    def test_private_and_loopback_ips_blocked(self):
        blocked_urls = [
            "https://127.0.0.1/admin",
            "https://localhost/metrics",
            "https://10.0.0.1/status",
            "https://192.168.1.1/router",
            "https://172.16.0.5/internal",
            "https://169.254.169.254/latest/meta-data/",  # AWS metadata
            "https://[::1]/internal",
        ]
        for url in blocked_urls:
            res = validate_url_safety(url)
            assert not res.is_safe, f"Expected {url} to be blocked by SSRF guard"
            assert res.error_code in ("SSRF_PRIVATE_IP_BLOCKED", "SSRF_DNS_RESOLUTION_FAILED")

    def test_dns_rebinding_simulated_resolver(self):
        # Resolver mock that returns a private RFC1918 IP for an apparently harmless hostname
        def mock_dns_rebinder(host: str):
            return ["10.200.1.5"]

        res = validate_url_safety("https://innocent-looking-domain.com/feed", dns_resolver=mock_dns_rebinder)
        assert not res.is_safe
        assert res.error_code == "SSRF_PRIVATE_IP_BLOCKED"
        assert res.resolved_ip == "10.200.1.5"

    def test_valid_public_https_allowed(self):
        def mock_public_resolver(host: str):
            return ["93.184.216.34"]  # example.com public IP

        res = validate_url_safety("https://api.weather.gov.in/telemetry", dns_resolver=mock_public_resolver)
        assert res.is_safe
        assert res.resolved_ip == "93.184.216.34"


class TestSyntheticFallbackAndVerificationState:
    """Verifies synthetic evidence constraints and honest verification unavailable state."""

    def test_synthetic_fallback_disabled_by_default(self, monkeypatch):
        monkeypatch.setattr(settings, "LIVE_DATA_FALLBACK", "off")
        monkeypatch.setattr(settings, "LIVE_SOURCES_ENABLED", False)

        provider = SyntheticFallbackProvider()
        result = provider.lookup(SourceLookupQuery("Hindmata Dadar"))

        assert not result.verification_available
        assert "disabled by system policy" in (result.unavailable_reason or "")
        assert len(result.items) == 0

    def test_synthetic_fallback_when_explicitly_enabled(self, monkeypatch):
        monkeypatch.setattr(settings, "LIVE_DATA_FALLBACK", "labelled_demo")

        provider = SyntheticFallbackProvider()
        result = provider.lookup(SourceLookupQuery("Hindmata Dadar"))

        assert result.verification_available
        assert len(result.items) == 1
        item = result.items[0]
        # Never fabricate URLs
        assert item.source_url is None
        assert item.is_simulated is True
        assert item.evidence_type == "synthetic_test"

    def test_verification_unavailable_reporting_when_no_live_provider(self, monkeypatch):
        monkeypatch.setattr(settings, "LIVE_SOURCES_ENABLED", False)
        monkeypatch.setattr(settings, "LIVE_DATA_FALLBACK", "off")

        available, reason = verification_service.get_verification_availability()
        assert not available
        assert "Independent verification is unavailable" in (reason or "")


class TestEvidenceEndpoints:
    """Tests GET/POST endpoints, SSRF rejection in API, audit trail, and RBAC."""

    @pytest.fixture(autouse=True)
    def setup_seed(self):
        client = TestClient(app)
        client.post("/api/v1/seed")

    def _login(self, client: TestClient, email: str, password: str) -> str:
        res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert res.status_code == 200
        return res.json()["csrf_token"]

    def test_get_incident_evidence_endpoint(self):
        client = TestClient(app)
        csrf = self._login(client, "coordinator@sahaayak.ai", "CoordPass@2026")

        res = client.get("/api/v1/incidents/inc-hindmata-001/evidence")
        assert res.status_code == 200
        data = res.json()

        assert data["incident_id"] == "inc-hindmata-001"
        assert len(data["evidence_items"]) >= 4
        assert data["independence_count"] >= 2
        assert data["conflicts_count"] >= 1  # The culvert rumor
        assert "missing_evidence" in data
        assert isinstance(data["missing_evidence"], list)
        assert data["verification_available"] is False
        assert "Independent verification is unavailable" in (data["verification_unavailable_reason"] or "")

        # Verify synthetic item has null URL and is_simulated=True
        synth_items = [it for it in data["evidence_items"] if it["evidence_type"] == "synthetic_test"]
        assert len(synth_items) >= 1
        for s in synth_items:
            assert s["is_simulated"] is True
            assert s["source_url"] is None

    def test_post_evidence_with_ssrf_attempt_is_rejected(self):
        client = TestClient(app)
        csrf = self._login(client, "coordinator@sahaayak.ai", "CoordPass@2026")

        # Attempt to attach evidence with internal AWS metadata URL
        payload = {
            "source_name": "Malicious Metadata Probe",
            "source_url": "https://169.254.169.254/latest/meta-data/",
            "assessment": "supports",
            "claim_summary": "Testing SSRF",
        }
        res = client.post(
            "/api/v1/incidents/inc-hindmata-001/evidence",
            json=payload,
            headers={"X-CSRF-Token": csrf},
        )
        assert res.status_code == 400
        err = res.json()
        assert "SSRF" in err["error"]["message"] or err["error"]["code"].startswith("SSRF")

    def test_post_evidence_and_review_with_audit_trail(self):
        client = TestClient(app)
        csrf = self._login(client, "coordinator@sahaayak.ai", "CoordPass@2026")

        # 1. Attach manual evidence
        create_payload = {
            "source_name": "Field Officer Patil Inspection Log",
            "source_description": "On-site confirmation of culvert outflow rate",
            "source_url": None,
            "assessment": "supports",
            "freshness": "< 1h",
            "claim_summary": "Verified culvert operating at 90% intake with no structural failure.",
            "reviewer_notes": "Officer confirmed by visual probe at 10:15 IST",
        }
        res_create = client.post(
            "/api/v1/incidents/inc-hindmata-001/evidence",
            json=create_payload,
            headers={"X-CSRF-Token": csrf},
        )
        assert res_create.status_code == 201
        ev_id = res_create.json()["id"]

        # 2. Review evidence with required coordinator notes
        review_payload = {
            "assessment": "supports",
            "reviewer_notes": "Re-verified after second patrol visit. Fully corroborates drainage saturation.",
        }
        res_review = client.post(
            f"/api/v1/evidence/{ev_id}/review",
            json=review_payload,
            headers={"X-CSRF-Token": csrf},
        )
        assert res_review.status_code == 200
        assert res_review.json()["reviewed_by"] == "coordinator@sahaayak.ai"

        # 3. Check audit trail records before and after states
        res_audit = client.get("/api/v1/audit?limit=10")
        assert res_audit.status_code == 200
        audit_events = res_audit.json()
        reviewed_events = [e for e in audit_events if e["action"] == "EVIDENCE_REVIEWED" and e["entity_id"] == ev_id]
        assert len(reviewed_events) >= 1
        audit_entry = reviewed_events[0]
        assert audit_entry["before_state"] is not None, "Audit entry should have before_state"
        assert audit_entry["after_state"] is not None, "Audit entry should have after_state"
        assert audit_entry["after_state"]["reviewer_notes"] == review_payload["reviewer_notes"]

    def test_rbac_reporter_cannot_attach_or_review_evidence(self):
        client = TestClient(app)
        csrf = self._login(client, "reporter@sahaayak.ai", "ReporterPass@2026")

        # Reporter attempts to attach evidence
        res = client.post(
            "/api/v1/incidents/inc-hindmata-001/evidence",
            json={"source_name": "Citizen Hack", "claim_summary": "Test"},
            headers={"X-CSRF-Token": csrf},
        )
        assert res.status_code == 403

        # Reporter attempts to review evidence
        res2 = client.post(
            "/api/v1/evidence/some-id/review",
            json={"assessment": "supports", "reviewer_notes": "Hacked"},
            headers={"X-CSRF-Token": csrf},
        )
        assert res2.status_code == 403
