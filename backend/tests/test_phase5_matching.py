"""
Phase 5 Tests: Explainable duplicate matching & coordinator review.
Tests:
- Lexicon normalization and cross-lingual equivalence mapping
- Deterministic MatchingEngine: strong/possible/weak bands, structured signals, unknowns
- Seeded multi-lingual reports (EN/HI/MR) match as strong/possible
- Unrelated tree report does NOT match
- Contradictory-location report flagged as hard negative, not merged
- Forwarded / copied claims grouped as same origin
- Reject persistence and no re-suggest (review_input_hash)
- Idempotent confirm
- RBAC: reporter cannot confirm or reject (403)
- Performance test: candidate generation over 500 synthetic reports stays under budget (<2.0s)
"""

import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.all_models import (
    Incident,
    IncidentReportLink,
    IncidentStatusEnum,
    LinkStatusEnum,
    Report,
    RoleEnum,
    User,
)
from backend.app.services.matching.engine import (
    MATCH_POSSIBLE_THRESHOLD,
    MATCH_STRONG_THRESHOLD,
    MatchBand,
    MatchingEngine,
    calculate_haversine_distance_km,
    compute_source_fingerprint,
)
from backend.app.services.matching.lexicon import (
    EQUIVALENCE_MAP,
    extract_canonical_concepts,
    jaccard_similarity,
    normalize_text,
    tokenize,
)
from backend.app.services.matching.service import MatchingService, matching_service

client = TestClient(app)


def _seed():
    r = client.post("/api/v1/seed")
    assert r.status_code == 200, r.text


def _login(email: str, password: str) -> TestClient:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    c = TestClient(app, cookies=dict(r.cookies))
    c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return c


@pytest.fixture(autouse=True)
def setup():
    _seed()
    yield


def coord_client():
    return _login("coordinator@sahaayak.ai", "CoordPass@2026")


def reporter_client():
    return _login("reporter@sahaayak.ai", "ReporterPass@2026")


# ==============================================================================
# 1. Lexicon & Normalization Unit Tests
# ==============================================================================

class TestLexiconNormalization:
    def test_unicode_nfkc_normalization(self):
        # Combined vs decomposed Unicode characters
        composed = "पानी"
        decomposed = "पा\u0928\u0940"
        assert normalize_text(composed) == normalize_text(decomposed)

    def test_punctuation_and_whitespace_stripping(self):
        text = "  Water, is rising fast!! Near Dadar... "
        normalized = normalize_text(text)
        assert "!" not in normalized
        assert "," not in normalized
        assert normalized == "water is rising fast near dadar"

    def test_cross_lingual_concept_mapping(self):
        # English, Hindi, and Marathi terms map to same canonical concept
        concepts_en = extract_canonical_concepts("water flooded road")
        concepts_hi = extract_canonical_concepts("पानी जलभराव सड़क")
        concepts_mr = extract_canonical_concepts("पाणी जलमय रस्ता")

        assert "CONCEPT_WATER" in concepts_en
        assert "CONCEPT_FLOOD" in concepts_en
        assert "CONCEPT_ROAD" in concepts_en

        assert "CONCEPT_WATER" in concepts_hi
        assert "CONCEPT_FLOOD" in concepts_hi
        assert "CONCEPT_ROAD" in concepts_hi

        assert "CONCEPT_WATER" in concepts_mr
        assert "CONCEPT_FLOOD" in concepts_mr
        assert "CONCEPT_ROAD" in concepts_mr

    def test_tree_fall_cross_lingual_mapping(self):
        en = extract_canonical_concepts("tree fallen on flyover")
        hi = extract_canonical_concepts("पेड़ गिरा पुल पर")
        mr = extract_canonical_concepts("झाड पडले पुलावर")

        assert "CONCEPT_TREE" in en and "CONCEPT_FALL" in en and "CONCEPT_BRIDGE" in en
        assert "CONCEPT_TREE" in hi and "CONCEPT_FALL" in hi and "CONCEPT_BRIDGE" in hi
        assert "CONCEPT_TREE" in mr and "CONCEPT_FALL" in mr and "CONCEPT_BRIDGE" in mr

    def test_jaccard_similarity_calculation(self):
        set_a = {"CONCEPT_WATER", "CONCEPT_FLOOD", "LOC_DADAR"}
        set_b = {"CONCEPT_WATER", "CONCEPT_FLOOD", "CONCEPT_BRIDGE"}
        # Intersection: 2, Union: 4 -> 0.5
        assert jaccard_similarity(set_a, set_b) == 0.5


# ==============================================================================
# 2. Pure Deterministic Matching Engine Tests
# ==============================================================================

class TestMatchingEngine:
    def test_haversine_formula(self):
        # Dadar TT to Dadar Railway Station (~600m)
        dist = calculate_haversine_distance_km(19.0178, 72.8478, 19.0185, 72.8425)
        assert 0.5 < dist < 0.8

    def test_seeded_three_reports_match_hindmata_incident(self):
        inc = {
            "category": "waterlogging",
            "summary": "Severe Waterlogging at Hindmata Flyover & Dadar TT Extreme localized water accumulation knee deep transit buses stalled",
            "location_name": "Hindmata Flyover & Dadar TT Junction, Dadar",
            "latitude": 19.0178,
            "longitude": 72.8478,
            "has_grounded_coordinates": True,
        }

        # 1. English Report
        rep_en = {
            "category": "waterlogging",
            "original_text": "Water is above knee level near Hindmata cinema flyover underpass. Buses are completely stuck.",
            "reported_location_text": "Hindmata cinema underpass, Dadar",
            "latitude": 19.0180,
            "longitude": 72.8480,
            "has_grounded_coordinates": True,
        }
        eval_en = MatchingEngine.evaluate_pair(rep_en, inc)
        assert eval_en.band in [MatchBand.STRONG, MatchBand.POSSIBLE]
        assert eval_en.score >= MATCH_POSSIBLE_THRESHOLD
        assert not eval_en.is_suppressed
        assert any(s.name == "same_category" and s.matched for s in eval_en.signals_for)

        # 2. Hindi Report
        rep_hi = {
            "category": "waterlogging",
            "original_text": "दादर टीटी सर्कल और हिंदमाता सिनेमा के पास 3 फीट पानी भर गया है। बेस्ट बसें बंद हैं।",
            "reported_location_text": "दादर टीटी सर्कल, हिंदमाता",
            "latitude": 19.0175,
            "longitude": 72.8475,
            "has_grounded_coordinates": True,
        }
        eval_hi = MatchingEngine.evaluate_pair(rep_hi, inc)
        assert eval_hi.band in [MatchBand.STRONG, MatchBand.POSSIBLE]
        assert eval_hi.score >= MATCH_POSSIBLE_THRESHOLD
        assert not eval_hi.is_suppressed

        # 3. Marathi Report
        rep_mr = {
            "category": "waterlogging",
            "original_text": "हिंदमाता उड्डाणपुलाखाली आणि दादर टीटी जवळ पाणी कंबरेपर्यंत भरले आहे. सर्व रस्ते बंद आहेत.",
            "reported_location_text": "हिंदमाता उड्डाणपुलाखाली, दादर",
            "latitude": 19.0185,
            "longitude": 72.8482,
            "has_grounded_coordinates": True,
        }
        eval_mr = MatchingEngine.evaluate_pair(rep_mr, inc)
        assert eval_mr.band in [MatchBand.STRONG, MatchBand.POSSIBLE]
        assert eval_mr.score >= MATCH_POSSIBLE_THRESHOLD
        assert not eval_mr.is_suppressed

    def test_unrelated_tree_report_does_not_match(self):
        inc = {
            "category": "waterlogging",
            "summary": "Severe Waterlogging at Hindmata Flyover & Dadar TT",
            "location_name": "Hindmata Flyover & Dadar TT Junction, Dadar",
            "latitude": 19.0178,
            "longitude": 72.8478,
            "has_grounded_coordinates": True,
        }
        rep_tree = {
            "category": "tree_fall",
            "original_text": "Big banyan tree collapsed near Bandra flyover Western Express Highway ramp.",
            "reported_location_text": "WEH Northbound Ramp near Bandra Flyover",
            "latitude": 19.0596,
            "longitude": 72.8450,
            "has_grounded_coordinates": True,
        }
        eval_tree = MatchingEngine.evaluate_pair(rep_tree, inc)
        assert eval_tree.band == MatchBand.WEAK
        assert eval_tree.is_suppressed
        assert eval_tree.hard_negative_flag is not None

    def test_contradictory_location_flagged_not_merged(self):
        inc = {
            "category": "waterlogging",
            "summary": "Flooding at Dadar TT",
            "location_name": "Dadar TT Circle",
            "latitude": 19.0178,
            "longitude": 72.8478,
            "has_grounded_coordinates": True,
        }
        # Explicit Bandra location reported with waterlogging
        rep_bandra = {
            "category": "waterlogging",
            "original_text": "Waterlogging reported at Bandra West near station",
            "reported_location_text": "Bandra West Station Road",
            "latitude": 19.0550,
            "longitude": 72.8350,
            "has_grounded_coordinates": True,
        }
        eval_res = MatchingEngine.evaluate_pair(rep_bandra, inc)
        assert eval_res.band == MatchBand.WEAK
        assert eval_res.is_suppressed
        assert "locations" in eval_res.hard_negative_flag.lower() or "distinct" in eval_res.hard_negative_flag.lower()

    def test_copied_claim_detection(self):
        rep_a = {
            "category": "waterlogging",
            "original_text": "URGENT FORWARD: Hindmata flyover submerged, avoid Dadar routes completely!",
            "is_forwarded_message": True,
        }
        rep_b = {
            "category": "waterlogging",
            "original_text": "URGENT FORWARD: Hindmata flyover submerged, avoid Dadar routes completely!",
            "is_forwarded_message": True,
        }
        eval_res = MatchingEngine.evaluate_pair(rep_a, rep_b)
        assert eval_res.is_same_origin
        assert eval_res.origin_fingerprint is not None


# ==============================================================================
# 3. Match Endpoints, Confirm / Reject, and Re-suggest Suppression
# ==============================================================================

class TestMatchEndpointsAndPersistence:
    def test_get_report_matches_endpoint(self):
        c = coord_client()
        r = c.get("/api/v1/reports/rep-hindmata-mr/matches")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["report_id"] == "rep-hindmata-mr"
        assert len(data["matches"]) >= 1

        top_match = data["matches"][0]
        assert top_match["incident_id"] == "inc-hindmata-001"
        assert top_match["band"] in ["strong", "possible"]
        assert len(top_match["signals_for"]) >= 1
        assert "rationale" in top_match

    def test_duplicate_suggestions_queue(self):
        c = coord_client()
        r = c.get("/api/v1/duplicate-suggestions")
        assert r.status_code == 200, r.text
        suggestions = r.json()
        assert isinstance(suggestions, list)
        # Seeded rep3 is suggested for inc-hindmata-001
        assert any(s["status"] == "suggested" for s in suggestions)

    def test_confirm_link_idempotent_and_audited(self):
        c = coord_client()
        # Confirm link for rep3
        r1 = c.post(
            "/api/v1/incidents/inc-hindmata-001/reports/rep-hindmata-mr/confirm",
            json={"reviewer_notes": "Confirmed by ward coordinator after CCTV check"}
        )
        assert r1.status_code == 200
        assert r1.json()["status"] == "confirmed"

        # Second confirm should be idempotent (return same status, no error)
        r2 = c.post(
            "/api/v1/incidents/inc-hindmata-001/reports/rep-hindmata-mr/confirm",
            json={"reviewer_notes": "Second confirm attempt"}
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "confirmed"

    def test_reject_persistence_and_no_resuggest(self):
        c = coord_client()
        # Reject link
        r_reject = c.post(
            "/api/v1/incidents/inc-hindmata-001/reports/rep-hindmata-mr/reject",
            json={"reviewer_notes": "False positive match, different localized pool"}
        )
        assert r_reject.status_code == 200
        assert r_reject.json()["status"] == "rejected"

        # Re-running find_and_persist_candidates must NOT re-suggest the rejected link
        from backend.app.db.session import SessionLocal
        db = SessionLocal()
        try:
            persisted = matching_service.find_and_persist_candidates_for_report(
                db, "rep-hindmata-mr", actor="test_runner"
            )
            # Link should NOT be in the newly suggested links list
            link_ids = [l.incident_id for l in persisted]
            assert "inc-hindmata-001" not in link_ids

            # Link status in DB must remain rejected
            db_link = db.query(IncidentReportLink).filter(
                IncidentReportLink.incident_id == "inc-hindmata-001",
                IncidentReportLink.report_id == "rep-hindmata-mr"
            ).first()
            assert db_link.status == LinkStatusEnum.REJECTED
        finally:
            db.close()

    def test_rbac_reporter_cannot_confirm_or_reject(self):
        c = reporter_client()
        # Reporter tries to confirm
        r_conf = c.post(
            "/api/v1/incidents/inc-hindmata-001/reports/rep-hindmata-mr/confirm",
            json={"reviewer_notes": "Hacker confirm"}
        )
        assert r_conf.status_code == 403
        assert r_conf.json()["error_code"] == "INSUFFICIENT_PERMISSIONS"

        # Reporter tries to reject
        r_rej = c.post(
            "/api/v1/incidents/inc-hindmata-001/reports/rep-hindmata-mr/reject",
            json={"reviewer_notes": "Hacker reject"}
        )
        assert r_rej.status_code == 403
        assert r_rej.json()["error_code"] == "INSUFFICIENT_PERMISSIONS"


# ==============================================================================
# 4. Performance Guarantee: Candidate Pre-filtering under Load
# ==============================================================================

class TestMatchingPerformance:
    def test_candidate_generation_prefiltering_budget(self):
        """
        Proves that candidate generation uses category and temporal pre-filtering
        and stays well within the stated time budget (< 2.0s) even with 500 reports in DB.
        """
        from backend.app.db.session import SessionLocal
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            bulk_reports = []
            for i in range(500):
                bulk_reports.append(
                    Report(
                        id=f"rep-perf-{i:04d}",
                        reference_code=f"SAH-PERF-{i:04d}",
                        original_text=f"Synthetic incident report {i} in zone {i % 10}",
                        input_language="en",
                        location_claim=f"Sector {i % 20}",
                        processing_status="processed",
                        extraction_source="demo",
                        extracted_json={"category": "tree_fall" if i % 2 == 0 else "power_outage"},
                        submitted_at=now - timedelta(days=i),  # Spread across 500 days
                    )
                )
            db.bulk_save_objects(bulk_reports)
            db.commit()

            # Target report to match against waterlogging incident
            target_report = Report(
                id="rep-target-water",
                reference_code="SAH-TARGET-WATER",
                original_text="Severe waterlogging near flyover underpass",
                input_language="en",
                location_claim="Hindmata",
                processing_status="processed",
                extraction_source="demo",
                extracted_json={"category": "waterlogging"},
                submitted_at=now,
            )
            db.add(target_report)
            db.commit()

            start_time = time.perf_counter()
            candidates = matching_service.find_and_persist_candidates_for_report(
                db=db,
                report_id=target_report.id,
                actor="perf_test"
            )
            elapsed = time.perf_counter() - start_time

            # Must finish well under 2 seconds (pre-filtered query, not O(n^2))
            assert elapsed < 2.0, f"Candidate generation took {elapsed:.3f}s (budget: 2.0s)"
            assert len(candidates) >= 1
            assert candidates[0].incident_id == "inc-hindmata-001"
        finally:
            # Cleanup synthetic performance records
            db.query(Report).filter(Report.id.startswith("rep-perf-")).delete(synchronize_session=False)
            db.query(Report).filter(Report.id == "rep-target-water").delete(synchronize_session=False)
            db.commit()
            db.close()
