from datetime import datetime, timedelta

from backend.app.db.session import get_db
from backend.app.models.all_models import (
    AuditEvent,
    EvidenceItem,
    Incident,
    IncidentReportLink,
    Report,
    Task,
)
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/seed")
def seed_demo_data(db: Session = Depends(get_db)):
    """
    Clears existing demo records and populates the deterministic hackathon dataset
    strictly adhering to MASTER_PROMPT_ANTIGRAVITY.md specifications.
    All records are clearly flagged as simulated.
    """
    import os

    from backend.app.core.auth import hash_password
    from backend.app.models.all_models import RoleEnum, User
    from sqlalchemy import text

    # Clear existing demo records
    db.execute(text("DELETE FROM audit_events;"))
    db.query(Task).delete()
    db.query(EvidenceItem).delete()
    db.query(IncidentReportLink).delete()
    db.query(Report).delete()
    db.query(Incident).delete()
    db.query(User).delete()
    db.commit()

    now = datetime.utcnow()

    # 0. Seed Demo Accounts (Passwords from environment, with secure demo fallbacks)
    admin_pwd = os.getenv("ADMIN_PASSWORD", "AdminPass@2026")
    coord_pwd = os.getenv("COORDINATOR_PASSWORD", "CoordPass@2026")
    reporter_pwd = os.getenv("REPORTER_PASSWORD", "ReporterPass@2026")

    admin_user = User(
        id="usr-admin-001",
        username="admin",
        email="admin@sahaayak.ai",
        hashed_password=hash_password(admin_pwd),
        role=RoleEnum.ADMIN,
        full_name="Chief Municipal Officer (Admin)",
        failed_login_attempts=0,
        locked_until=None,
    )
    coord_user = User(
        id="usr-coord-001",
        username="coordinator",
        email="coordinator@sahaayak.ai",
        hashed_password=hash_password(coord_pwd),
        role=RoleEnum.COORDINATOR,
        full_name="Emergency Response Coordinator",
        failed_login_attempts=0,
        locked_until=None,
    )
    reporter_user = User(
        id="usr-reporter-001",
        username="reporter",
        email="reporter@sahaayak.ai",
        hashed_password=hash_password(reporter_pwd),
        role=RoleEnum.REPORTER,
        full_name="Verified Citizen Reporter",
        failed_login_attempts=0,
        locked_until=None,
    )
    db.add(admin_user)
    db.add(coord_user)
    db.add(reporter_user)
    db.commit()

    # 1. Main Incident: Hindmata Waterlogging (Simulated)
    inc_waterlogging = Incident(
        id="inc-hindmata-001",
        title="Severe Waterlogging at Hindmata Flyover & Dadar TT",
        summary="Extreme localized water accumulation (approx 90cm) following heavy rainfall downpour. Subway impassable, BEST bus routes diverted, stranded vehicles reported.",
        category="waterlogging",
        status="investigating",
        suggested_priority="critical",
        approved_priority="critical",
        priority_rationale="Depth exceeds 75cm threshold; critical arterial transit route obstructed; multiple community corroborations.",
        location_name="Hindmata Flyover Underpass, Dadar East, Mumbai",
        location_description="Low-lying underpass beneath Hindmata flyover, chronic flood-prone zone with inadequate drainage capacity",
        district="Mumbai City",
        state="Maharashtra",
        district_source="coordinator_set",
        state_source="coordinator_set",
        latitude=19.0178,
        longitude=72.8478,
        has_grounded_coordinates=True,
        location_precision="exact",
        coordinate_source="simulated_seed",
        evidence_status="partially_corroborated",
        assigned_coordinator_id="usr-coord-001",
        is_simulated=True,
        version=1,
        created_at=now - timedelta(hours=3),
        updated_at=now - timedelta(hours=1),
    )

    # 2. Unrelated Incident: WEH Fallen Tree (Simulated)
    inc_tree = Incident(
        id="inc-bandra-002",
        title="Fallen Banyan Tree Blocking Western Express Highway",
        summary="Large banyan tree fallen across Northbound lanes 1 & 2 near Bandra flyover ramp. Heavy vehicular gridlock forming towards airport.",
        category="tree_fall",
        status="open",
        suggested_priority="high",
        approved_priority="high",
        priority_rationale="Major arterial highway obstruction affecting airport transit corridor.",
        location_name="WEH Northbound Ramp near Bandra Flyover",
        location_description="Western Express Highway northbound ramp exit towards Bandra-Kurla Complex",
        district="Mumbai Suburban",
        state="Maharashtra",
        district_source="coordinator_set",
        state_source="coordinator_set",
        latitude=19.0596,
        longitude=72.8450,
        has_grounded_coordinates=True,
        location_precision="approximate",
        coordinate_source="simulated_seed",
        evidence_status="unverified",
        assigned_coordinator_id="usr-coord-001",
        is_simulated=True,
        version=1,
        created_at=now - timedelta(hours=2),
        updated_at=now - timedelta(hours=2),
    )

    db.add(inc_waterlogging)
    db.add(inc_tree)
    db.commit()

    # 3. Reports
    # Report 1 (English): Hindmata bus passenger (Citizen report)
    rep1 = Report(
        id="rep-hindmata-en",
        reference_code="SAH-2026-HIND01",
        user_id=None,
        source_fingerprint="fp-hindmata-en-001",
        original_text="Water is above knee level near Hindmata cinema flyover underpass. Buses are completely stuck and water is rising fast. Need help urgently!",
        media_path=None,
        media_type=None,
        input_language="en",
        reporter_name="Aarav Sharma",
        reporter_contact="+91-98200-XXXXX",
        location_claim="Hindmata cinema underpass, Dadar",
        coordinates_lat=19.0180,
        coordinates_lng=72.8480,
        processing_status="processed",
        extraction_source="deterministic-demo",
        extraction_metadata={
            "provider": "deterministic-demo",
            "mode": "demo",
            "model": "demo-script-v1",
            "latency_ms": 12,
            "attempt_count": 1,
            "schema_version": "1.0.0",
            "simulated": True,
            "processed_at": (now - timedelta(hours=2, minutes=49)).isoformat(),
        },
        extracted_json={
            "category": "waterlogging",
            "short_summary": "Critical waterlogging knee-deep near Hindmata cinema stalling transit buses.",
            "original_text_language": "en",
            "reported_location_text": "Hindmata Cinema Underpass, Dadar",
            "location_precision": "landmark",
            "location_source": "text",
            "incident_time": None,
            "claimed_severity": "critical",
            "safety_concern": True,
            "safety_concern_reason": "Rapidly rising water submerging transit buses with stranded commuters.",
            "people_or_infrastructure_affected": ["Dadar Roadway", "Bus Route 27"],
            "source_attribution": "commuter",
            "is_forwarded_message": False,
            "explicit_facts": ["Water is above knee level", "Hindmata cinema flyover underpass inundated", "Buses completely stuck"],
            "model_inferences": ["Water depth approx 85cm", "Transit corridor disabled"],
            "missing_information": ["Stranded passenger count", "Operating pump status"],
            "ambiguities": [],
            "contradictions": [],
            "follow_up_questions": ["Are municipal dewatering pumps active at the junction?", "Are passengers stranded inside buses?"],
            # Legacy aliases
            "hazard_type": "waterlogging",
            "severity": "critical",
            "water_depth_cm": 85,
            "location_name": "Hindmata Cinema Underpass, Dadar",
            "approximate_lat": 19.0180,
            "approximate_lng": 72.8480,
            "has_grounded_coordinates": True,
            "affected_infrastructure": ["Dadar Roadway", "Bus Route 27"],
            "urgent_needs": ["Industrial Dewatering Pumps", "Traffic Diversion"],
            "casualties_flag": False,
            "confidence_score": 0.95,
            "sentiment_urgency": "critical",
            "language_detected": "en",
            "summary": "Critical waterlogging knee-deep near Hindmata cinema stalling transit buses.",
        },
        submitted_at=now - timedelta(hours=2, minutes=50),
        processed_at=now - timedelta(hours=2, minutes=49),
    )

    # Report 2 (Hindi): Shopkeeper near Dadar TT
    rep2 = Report(
        id="rep-hindmata-hi",
        reference_code="SAH-2026-HIND02",
        user_id="usr-reporter-001",
        source_fingerprint="fp-hindmata-hi-002",
        original_text="दादर टीटी सर्कल और हिंदमाता के पास 3 फीट पानी भर गया है, दुकानें और गाड़ियां डूब रही हैं। लोग फंसे हैं। मदद चाहिए।",
        media_path=None,
        media_type=None,
        input_language="hi",
        reporter_name="राजेश गुप्ता (Rajesh Gupta)",
        reporter_contact="+91-98211-XXXXX",
        location_claim="दादर टीटी सर्कल (Dadar TT Circle)",
        coordinates_lat=19.0175,
        coordinates_lng=72.8475,
        processing_status="processed",
        extraction_source="deterministic-demo",
        extraction_metadata={
            "provider": "deterministic-demo",
            "mode": "demo",
            "model": "demo-script-v1",
            "latency_ms": 14,
            "attempt_count": 1,
            "schema_version": "1.0.0",
            "simulated": True,
            "processed_at": (now - timedelta(hours=2, minutes=29)).isoformat(),
        },
        extracted_json={
            "category": "waterlogging",
            "short_summary": "Hindmata and Dadar TT Circle inundated with ~3 feet water, submerging vehicles and trapping residents.",
            "original_text_language": "hi",
            "reported_location_text": "Dadar TT Circle / Hindmata",
            "location_precision": "landmark",
            "location_source": "text",
            "incident_time": None,
            "claimed_severity": "critical",
            "safety_concern": True,
            "safety_concern_reason": "Trapped civilians and submerging commercial vehicles in ~3ft deep water.",
            "people_or_infrastructure_affected": ["Commercial retail shops", "Dadar TT Intersection"],
            "source_attribution": "local shopkeeper",
            "is_forwarded_message": False,
            "explicit_facts": ["3 feet water accumulated", "Dadar TT Circle and Hindmata inundated", "Shops and vehicles submerging", "People trapped"],
            "model_inferences": ["Severe localized flash water accumulation requiring high-capacity pumps"],
            "missing_information": ["Number of trapped residents", "Power grid status in commercial row"],
            "ambiguities": [],
            "contradictions": [],
            "follow_up_questions": ["Has local electricity been isolated in the flooded shops?", "Are elderly or disabled people trapped?"],
            # Legacy aliases
            "hazard_type": "waterlogging",
            "severity": "critical",
            "water_depth_cm": 90,
            "location_name": "Dadar TT Circle / Hindmata",
            "approximate_lat": 19.0175,
            "approximate_lng": 72.8475,
            "has_grounded_coordinates": True,
            "affected_infrastructure": ["Commercial shops", "Dadar TT Intersection"],
            "urgent_needs": ["Rescue boat/truck", "High capacity pumps"],
            "casualties_flag": False,
            "confidence_score": 0.94,
            "sentiment_urgency": "critical",
            "language_detected": "hi",
            "summary": "Hindmata and Dadar TT Circle inundated with ~3 feet water, submerging vehicles and trapping residents.",
        },
        submitted_at=now - timedelta(hours=2, minutes=30),
        processed_at=now - timedelta(hours=2, minutes=29),
    )

    # Report 3 (Marathi): Local commuter
    rep3 = Report(
        id="rep-hindmata-mr",
        reference_code="SAH-2026-HIND03",
        user_id="usr-reporter-001",
        source_fingerprint="fp-hindmata-mr-003",
        original_text="हिंदमाता फ्लायओव्हरखाली पाणी साचल्यामुळे वाहतूक ठप्प झाली आहे. बेस्ट बसेस मार्ग बदलण्यात आले आहेत. तातडीने पाण्याचा उपसा आवश्यक आहे.",
        media_path=None,
        media_type=None,
        input_language="mr",
        reporter_name="सुनील कदम (Sunil Kadam)",
        reporter_contact="+91-98199-XXXXX",
        location_claim="हिंदमाता उड्डाणपूल (Hindmata Flyover)",
        coordinates_lat=19.0179,
        coordinates_lng=72.8477,
        processing_status="processed",
        extraction_source="deterministic-demo",
        extraction_metadata={
            "provider": "deterministic-demo",
            "mode": "demo",
            "model": "demo-script-v1",
            "latency_ms": 11,
            "attempt_count": 1,
            "schema_version": "1.0.0",
            "simulated": True,
            "processed_at": (now - timedelta(hours=2, minutes=9)).isoformat(),
        },
        extracted_json={
            "category": "waterlogging",
            "short_summary": "Hindmata flyover underpass waterlogged, halting traffic and forcing BEST bus diversions.",
            "original_text_language": "mr",
            "reported_location_text": "Hindmata Flyover, Dadar",
            "location_precision": "landmark",
            "location_source": "text",
            "incident_time": None,
            "claimed_severity": "high",
            "safety_concern": False,
            "safety_concern_reason": None,
            "people_or_infrastructure_affected": ["BEST Bus Routes", "Local traffic flow"],
            "source_attribution": "commuter",
            "is_forwarded_message": False,
            "explicit_facts": ["Traffic stopped under Hindmata flyover", "BEST bus routes diverted", "Water accumulation requiring immediate drainage"],
            "model_inferences": ["Water depth approx 80cm"],
            "missing_information": ["Status of dewatering operations"],
            "ambiguities": [],
            "contradictions": [],
            "follow_up_questions": ["Is upper deck flyover traffic flowing normally?"],
            # Legacy aliases
            "hazard_type": "waterlogging",
            "severity": "high",
            "water_depth_cm": 80,
            "location_name": "Hindmata Flyover, Dadar",
            "approximate_lat": 19.0179,
            "approximate_lng": 72.8477,
            "has_grounded_coordinates": True,
            "affected_infrastructure": ["BEST Bus Routes", "Local traffic flow"],
            "urgent_needs": ["Water pumping crew"],
            "casualties_flag": False,
            "confidence_score": 0.96,
            "sentiment_urgency": "urgent",
            "language_detected": "mr",
            "summary": "Hindmata flyover underpass waterlogged, halting traffic and forcing BEST bus diversions.",
        },
        submitted_at=now - timedelta(hours=2, minutes=10),
        processed_at=now - timedelta(hours=2, minutes=9),
    )

    # Report 4 (Unrelated): Bandra tree fall
    rep4 = Report(
        id="rep-bandra-tree",
        reference_code="SAH-2026-TREE04",
        user_id="usr-reporter-001",
        source_fingerprint="fp-bandra-tree-004",
        original_text="Huge tree has crashed on Western Express Highway right before Bandra flyover north side. Two lanes totally blocked, bumper-to-bumper traffic.",
        media_path=None,
        media_type=None,
        input_language="en",
        reporter_name="Karan Malhotra",
        location_claim="Western Express Highway near Bandra",
        coordinates_lat=19.0596,
        coordinates_lng=72.8450,
        processing_status="processed",
        extraction_source="deterministic-demo",
        extraction_metadata={
            "provider": "deterministic-demo",
            "mode": "demo",
            "model": "demo-script-v1",
            "latency_ms": 13,
            "attempt_count": 1,
            "schema_version": "1.0.0",
            "simulated": True,
            "processed_at": (now - timedelta(hours=1, minutes=44)).isoformat(),
        },
        extracted_json={
            "category": "tree_fall",
            "short_summary": "Large banyan tree fallen across two lanes of WEH near Bandra causing extensive highway congestion.",
            "original_text_language": "en",
            "reported_location_text": "Western Express Highway near Bandra Flyover",
            "location_precision": "landmark",
            "location_source": "text",
            "incident_time": None,
            "claimed_severity": "high",
            "safety_concern": True,
            "safety_concern_reason": "Major arterial highway obstruction affecting airport transit corridor.",
            "people_or_infrastructure_affected": ["WEH Northbound carriageway"],
            "source_attribution": "motorist",
            "is_forwarded_message": False,
            "explicit_facts": ["Huge tree crashed on WEH", "Two lanes totally blocked before Bandra flyover north side", "Bumper-to-bumper traffic"],
            "model_inferences": ["Severe arterial gridlock building"],
            "missing_information": ["Downed power cables or vehicle damage"],
            "ambiguities": [],
            "contradictions": [],
            "follow_up_questions": ["Are tree cutters or cranes dispatched?"],
            # Legacy aliases
            "hazard_type": "tree_fall",
            "severity": "high",
            "water_depth_cm": None,
            "location_name": "Western Express Highway near Bandra Flyover",
            "approximate_lat": 19.0596,
            "approximate_lng": 72.8450,
            "has_grounded_coordinates": True,
            "affected_infrastructure": ["WEH Northbound carriageway"],
            "urgent_needs": ["Disaster Management Tree Cutters", "Traffic Marshals"],
            "casualties_flag": False,
            "confidence_score": 0.93,
            "sentiment_urgency": "urgent",
            "language_detected": "en",
            "summary": "Large tree fallen across two lanes of WEH near Bandra causing extensive highway congestion.",
        },
        submitted_at=now - timedelta(hours=1, minutes=45),
        processed_at=now - timedelta(hours=1, minutes=44),
    )

    # Report 5: Unverified forwarded claim (Rumor)
    rep5 = Report(
        id="rep-rumor-forward",
        reference_code="SAH-2026-RUMR05",
        user_id="usr-reporter-001",
        source_fingerprint="fp-rumor-forward-005",
        original_text="FORWARDED AS RECEIVED: Vihar dam gates have collapsed and massive flood wave heading towards Powai and Kurla! Evacuate immediately!",
        media_path=None,
        media_type=None,
        input_language="en",
        reporter_name="Citizen via WhatsApp Forward",
        location_claim="Vihar Dam / Powai area (Unverified)",
        coordinates_lat=None,
        coordinates_lng=None,
        processing_status="needs_review",
        extraction_source="deterministic-demo",
        extraction_metadata={
            "provider": "deterministic-demo",
            "mode": "demo",
            "model": "demo-script-v1",
            "latency_ms": 10,
            "attempt_count": 1,
            "schema_version": "1.0.0",
            "simulated": True,
            "processed_at": (now - timedelta(hours=1, minutes=14)).isoformat(),
        },
        extracted_json={
            "category": "unknown",
            "short_summary": "Unverified panic viral message alleging dam gate collapse; zero sensory or telemetry corroboration.",
            "original_text_language": "en",
            "reported_location_text": "Vihar Dam / Powai area (Unverified)",
            "location_precision": "neighborhood",
            "location_source": "text",
            "incident_time": None,
            "claimed_severity": "medium",
            "safety_concern": False,
            "safety_concern_reason": "Unsubstantiated rumor with no official alert or sensor corroboration.",
            "people_or_infrastructure_affected": [],
            "source_attribution": "WhatsApp viral forward",
            "is_forwarded_message": True,
            "explicit_facts": ["Message is forwarded as received", "Alleges Vihar dam gates collapsed"],
            "model_inferences": ["High probability of panic hoax"],
            "missing_information": ["Official telemetry from MCGM Disaster Management"],
            "ambiguities": ["No source timestamp or authority attribution"],
            "contradictions": ["Dam collapse claim contradicts normal sensor telemetry"],
            "follow_up_questions": ["Has municipal disaster control issued an official clarification?"],
            # Legacy aliases
            "hazard_type": "unverified_rumor",
            "severity": "medium",
            "water_depth_cm": None,
            "location_name": "Vihar Dam / Powai",
            "approximate_lat": 19.1415,
            "approximate_lng": 72.9038,
            "has_grounded_coordinates": False,
            "affected_infrastructure": ["Unknown claim"],
            "urgent_needs": ["Official Authority Factcheck"],
            "casualties_flag": False,
            "confidence_score": 0.40,
            "sentiment_urgency": "moderate",
            "language_detected": "en",
            "summary": "Unverified panic viral message alleging dam gate collapse; zero sensory or telemetry corroboration.",
        },
        submitted_at=now - timedelta(hours=1, minutes=15),
        processed_at=now - timedelta(hours=1, minutes=14),
    )

    # Report 6: Incomplete or contradictory location details
    rep6 = Report(
        id="rep-ambiguous-loc",
        reference_code="SAH-2026-AMBG06",
        user_id="usr-reporter-001",
        source_fingerprint="fp-ambiguous-loc-006",
        original_text="Water is entering into our street near the old temple or railway bridge, not sure if its Dadar or Sion side, water is up to shin level.",
        media_path=None,
        media_type=None,
        input_language="en",
        reporter_name="Unknown Caller",
        location_claim="Somewhere near old temple between Dadar and Sion",
        coordinates_lat=None,
        coordinates_lng=None,
        processing_status="needs_review",
        extraction_source="deterministic-demo",
        extraction_metadata={
            "provider": "deterministic-demo",
            "mode": "demo",
            "model": "demo-script-v1",
            "latency_ms": 12,
            "attempt_count": 1,
            "schema_version": "1.0.0",
            "simulated": True,
            "processed_at": (now - timedelta(minutes=44)).isoformat(),
        },
        extracted_json={
            "category": "waterlogging",
            "short_summary": "Reported localized waterlogging with conflicting and incomplete landmark cues.",
            "original_text_language": "en",
            "reported_location_text": "Ambiguous Boundary (Dadar/Sion border)",
            "location_precision": "neighborhood",
            "location_source": "text",
            "incident_time": None,
            "claimed_severity": "medium",
            "safety_concern": False,
            "safety_concern_reason": None,
            "people_or_infrastructure_affected": ["Local residential lane"],
            "source_attribution": "unknown caller",
            "is_forwarded_message": False,
            "explicit_facts": ["Water entering street", "Water depth up to shin level (~35cm)"],
            "model_inferences": ["Localized lane drainage impediment"],
            "missing_information": ["Exact ward boundary (Dadar vs Sion)", "Specific street or landmark"],
            "ambiguities": ["Conflicting boundary landmarks reported"],
            "contradictions": [],
            "follow_up_questions": ["Can the reporter provide a specific cross street or shop name?"],
            # Legacy aliases
            "hazard_type": "waterlogging",
            "severity": "medium",
            "water_depth_cm": 35,
            "location_name": "Ambiguous Boundary (Dadar/Sion border)",
            "approximate_lat": None,
            "approximate_lng": None,
            "has_grounded_coordinates": False,
            "affected_infrastructure": ["Local lane"],
            "urgent_needs": ["Location triangulation", "Field officer check"],
            "casualties_flag": False,
            "confidence_score": 0.55,
            "sentiment_urgency": "moderate",
            "language_detected": "en",
            "summary": "Reported localized waterlogging with conflicting and incomplete landmark cues.",
        },
        submitted_at=now - timedelta(minutes=45),
        processed_at=now - timedelta(minutes=44),
    )

    db.add_all([rep1, rep2, rep3, rep4, rep5, rep6])
    db.commit()

    # 4. Association Links:
    # rep1, rep2, rep3 linked to Hindmata incident
    # rep1 is confirmed
    link1 = IncidentReportLink(
        incident_id=inc_waterlogging.id,
        report_id=rep1.id,
        status="confirmed",
        similarity_score=0.92,
        match_band="strong",
        match_rationale="Matching category: waterlogging | Very close spatial proximity: ~150m | Contextual keyword: Hindmata, underpass",
        signals_json=[
            {"name": "same_category", "weight": 0.35, "matched": True, "detail": "Matching hazard category: waterlogging"},
            {"name": "concept_overlap", "weight": 0.25, "matched": True, "detail": "Shared concept tokens: CONCEPT_WATER, CONCEPT_FLOOD, CONCEPT_BRIDGE"},
            {"name": "location_overlap", "weight": 0.20, "matched": True, "detail": "Shared landmark: Hindmata"},
            {"name": "geo_distance", "weight": 0.15, "matched": True, "detail": "Spatial proximity: ~150m"}
        ],
        reviewer_notes="Confirmed by coordinator via Dadar ward field feed",
        reviewed_by="coordinator@sahaayak.ai",
        reviewed_at=now - timedelta(hours=2, minutes=20),
    )
    # rep2 is confirmed
    link2 = IncidentReportLink(
        incident_id=inc_waterlogging.id,
        report_id=rep2.id,
        status="confirmed",
        similarity_score=0.90,
        match_band="strong",
        match_rationale="Matching category: waterlogging | Very close spatial proximity: ~200m | Shared landmark: Dadar TT Circle",
        signals_json=[
            {"name": "same_category", "weight": 0.35, "matched": True, "detail": "Matching hazard category: waterlogging"},
            {"name": "concept_overlap", "weight": 0.25, "matched": True, "detail": "Hindi concept equivalence: पानी/जलभराव"},
            {"name": "location_overlap", "weight": 0.20, "matched": True, "detail": "Shared landmark: Dadar TT Circle"},
            {"name": "geo_distance", "weight": 0.15, "matched": True, "detail": "Spatial proximity: ~200m"}
        ],
        reviewer_notes="Corroborated by Hindi commuter report",
        reviewed_by="coordinator@sahaayak.ai",
        reviewed_at=now - timedelta(hours=2),
    )
    # rep3 is suggested (awaiting coordinator review in demo)
    link3 = IncidentReportLink(
        incident_id=inc_waterlogging.id,
        report_id=rep3.id,
        status="suggested",
        similarity_score=0.89,
        match_band="strong",
        match_rationale="Matching category: waterlogging | High spatial overlap (~100m) | Marathi corroboration mentioning Hindmata flyover transit diversion",
        signals_json=[
            {"name": "same_category", "weight": 0.35, "matched": True, "detail": "Matching hazard category: waterlogging"},
            {"name": "concept_overlap", "weight": 0.25, "matched": True, "detail": "Marathi concept equivalence: पाणी/उड्डाणपूल"},
            {"name": "location_overlap", "weight": 0.20, "matched": True, "detail": "Shared landmark: Hindmata Flyover"},
            {"name": "geo_distance", "weight": 0.15, "matched": True, "detail": "Spatial proximity: ~100m"}
        ],
        reviewed_by=None,
        reviewed_at=None,
    )
    # rep4 linked to WEH tree fall
    link4 = IncidentReportLink(
        incident_id=inc_tree.id,
        report_id=rep4.id,
        status="confirmed",
        similarity_score=0.95,
        match_band="strong",
        match_rationale="Direct report describing tree fall blocking WEH near Bandra flyover.",
        signals_json=[
            {"name": "same_category", "weight": 0.35, "matched": True, "detail": "Matching hazard category: tree_fall"},
            {"name": "concept_overlap", "weight": 0.25, "matched": True, "detail": "Shared concepts: CONCEPT_TREE, CONCEPT_FALL, CONCEPT_ROAD"},
            {"name": "location_overlap", "weight": 0.20, "matched": True, "detail": "Shared landmark: WEH Bandra Flyover"}
        ],
        reviewer_notes="Verified via traffic police twitter update",
        reviewed_by="coordinator@sahaayak.ai",
        reviewed_at=now - timedelta(hours=1, minutes=30),
    )

    db.add_all([link1, link2, link3, link4])
    db.commit()

    # 5. Evidence Items explicitly marked as simulated (Phase 6: Transparent Evidence)
    ev1 = EvidenceItem(
        incident_id=inc_waterlogging.id,
        report_id=rep1.id,
        evidence_type="corroborating_report",
        source_type="field_report",
        source_name="Citizen Field Observation #001",
        source_description="On-the-ground citizen observation of underpass inundation",
        source_url=None,
        source_timestamp=now - timedelta(hours=2, minutes=30),
        retrieved_at=now - timedelta(hours=2, minutes=25),
        freshness="< 3h",
        assessment="supports",
        excerpt="Water reaching knee-level (~85cm) submerging underpass road surface and trapping sedans.",
        metadata_json={"depth_cm": 85, "water_level": "submerged"},
        independence_group=rep1.origin_group_id or rep1.id,
        is_simulated=True,
        claim_summary="Knee-deep water (~85cm) submerging underpass road surface.",
        verification_status="corroborating",
        reviewer_notes="Corroborated by secondary reports and drainage sensor gauges.",
        created_by="system-seed",
        reviewed_by="coordinator@sahaayak.ai",
        reviewed_at=now - timedelta(hours=2, minutes=20),
    )
    ev2 = EvidenceItem(
        incident_id=inc_waterlogging.id,
        report_id=None,
        evidence_type="synthetic_test",
        source_type="sensor_gauge",
        source_name="Automated Sump Telemetry (SYNTHETIC TEST)",
        source_description="Simulated ultrasonic gauge telemetry from Dadar culvert basin",
        source_url=None,  # Spec requirement: synthetic evidence carries null URL
        source_timestamp=now - timedelta(hours=1, minutes=45),
        retrieved_at=now - timedelta(hours=1, minutes=40),
        freshness="< 2h",
        assessment="supports",
        excerpt="Culvert intake flow rate saturated; sump reservoir level at 98% capacity.",
        metadata_json={"simulated": True, "sump_capacity_pct": 98},
        independence_group="simulated-sensor-dadar",
        is_simulated=True,
        claim_summary="Culvert intake flow rate saturated; sump reservoir level at 98% capacity.",
        verification_status="corroborating",
        reviewer_notes="Simulated telemetry confirms drainage saturation since 08:30 IST.",
        created_by="system-seed",
        reviewed_by="coordinator@sahaayak.ai",
        reviewed_at=now - timedelta(hours=1, minutes=30),
    )
    ev3 = EvidenceItem(
        incident_id=inc_waterlogging.id,
        report_id=None,
        evidence_type="manual_attachment",
        source_type="official_bulletin",
        source_name="Traffic Police Control Room Bulletin (Coordinator Logged)",
        source_description="Traffic police log entry on Dr. B.A. Road transit diversions",
        source_url=None,  # Null URL for demo seed
        source_timestamp=now - timedelta(hours=2),
        retrieved_at=now - timedelta(hours=1, minutes=50),
        freshness="< 2h",
        assessment="supports",
        excerpt="Dr. B.A. Road closed for small vehicular traffic between Dadar and Parel; transit diverted via flyover upper deck.",
        metadata_json={"bulletin_number": "442", "authority": "Mumbai Traffic Police"},
        independence_group="traffic-police-bulletin-442",
        is_simulated=True,
        claim_summary="Dr. B.A. Road closed for small vehicular traffic between Dadar and Parel; transit diverted via flyover upper deck.",
        verification_status="corroborating",
        reviewer_notes="Official diversion confirmation logged by response coordinator.",
        created_by="coordinator@sahaayak.ai",
        reviewed_by="coordinator@sahaayak.ai",
        reviewed_at=now - timedelta(hours=1, minutes=45),
    )
    ev4 = EvidenceItem(
        incident_id=inc_waterlogging.id,
        report_id=rep5.id,
        evidence_type="contradictory",
        source_type="community_claim",
        source_name="Social Media Forward (Culvert Breach Rumor)",
        source_description="Unverified forwarded claim alleging structural culvert collapse",
        source_url=None,
        source_timestamp=now - timedelta(hours=1),
        retrieved_at=now - timedelta(minutes=40),
        freshness="< 1h",
        assessment="contradicts",
        excerpt="Alleges structural culvert wall collapse under Dadar flyover with multiple trapped casualties.",
        metadata_json={"rumor_flag": True, "claim": "culvert wall collapse"},
        independence_group="social-forward-culvert-rumor",
        is_simulated=True,
        claim_summary="Alleges culvert wall collapse under Dadar flyover.",
        verification_status="conflicting",
        reviewer_notes="Conflicting claim refuted by MCGM ward engineer site visual inspection; retaining wall remains intact with zero structural failure.",
        created_by="system-seed",
        reviewed_by="coordinator@sahaayak.ai",
        reviewed_at=now - timedelta(minutes=30),
    )

    db.add_all([ev1, ev2, ev3, ev4])
    db.commit()

    # 6. Tasks in multiple states
    task1 = Task(
        incident_id=inc_waterlogging.id,
        title="Deploy 2x High-Capacity 500 GPM Dewatering Pumps",
        description="Position diesel dewatering pumps at low point beneath Hindmata flyover to discharge water toward Britannia storm-drain outfall.",
        priority="critical",
        status="in_progress",
        assigned_to="Ward F-South Drainage Team",
        approved_by="coordinator@sahaayak.ai",
        approved_at=now - timedelta(hours=2, minutes=10),
    )
    task2 = Task(
        incident_id=inc_waterlogging.id,
        title="Establish Traffic Police Diversion Cones at Dadar TT",
        description="Prevent two-wheelers and light motor vehicles from entering waterlogged underpass.",
        priority="high",
        status="completed",
        assigned_to="Matunga Traffic Division",
        approved_by="coordinator@sahaayak.ai",
        approved_at=now - timedelta(hours=2, minutes=30),
    )
    task3 = Task(
        incident_id=inc_waterlogging.id,
        title="Distribute Sandbags to At-Risk Groundfloor Retailers",
        description="Coordinate flood barriers with local commercial associations along Dr. B.A. Road.",
        priority="medium",
        status="suggested",
        assigned_to=None,
        approved_by=None,
    )
    task4 = Task(
        incident_id=inc_tree.id,
        title="Dispatch Hydraulic Crane and Chainsaw Squad",
        description="Cut and remove fallen banyan trunk from WEH Northbound lanes 1 & 2.",
        priority="high",
        status="pending",
        assigned_to="Garden Cell Emergency Unit #02",
        approved_by="coordinator@sahaayak.ai",
        approved_at=now - timedelta(hours=1, minutes=20),
    )

    db.add_all([task1, task2, task3, task4])
    db.commit()

    # 7. Audit Events
    audit1 = AuditEvent(
        actor="system",
        action="SYSTEM_INITIALIZED",
        entity_type="system",
        entity_id="init",
        before_state=None,
        after_state={"environment": "demo", "seed_time": now.isoformat()},
        timestamp=now - timedelta(hours=3),
    )
    audit2 = AuditEvent(
        actor="coordinator@sahaayak.ai",
        action="MATCH_CONFIRMED",
        entity_type="link",
        entity_id=link1.id,
        before_state={"status": "suggested"},
        after_state={
            "status": "confirmed",
            "incident_id": inc_waterlogging.id,
            "report_id": rep1.id,
        },
        timestamp=now - timedelta(hours=2, minutes=20),
    )
    audit3 = AuditEvent(
        actor="coordinator@sahaayak.ai",
        action="TASK_APPROVED",
        entity_type="task",
        entity_id=task1.id,
        before_state={"status": "suggested"},
        after_state={"status": "pending", "title": task1.title, "assignee": task1.assigned_to},
        timestamp=now - timedelta(hours=2, minutes=10),
    )

    db.add_all([audit1, audit2, audit3])
    db.commit()

    return {
        "status": "success",
        "message": "Deterministic demo dataset seeded successfully",
        "users_count": 3,
        "incidents_count": 2,
        "reports_count": 6,
        "links_count": 4,
        "evidence_count": 4,
        "tasks_count": 4,
    }
