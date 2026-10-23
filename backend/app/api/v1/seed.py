from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.all_models import (
    Report, Incident, IncidentReportLink, EvidenceItem, Task, AuditEvent
)

router = APIRouter()

@router.post("/seed")
def seed_demo_data(db: Session = Depends(get_db)):
    """
    Clears existing demo records and populates the deterministic hackathon dataset
    strictly adhering to MASTER_PROMPT_ANTIGRAVITY.md specifications.
    All records are clearly flagged as simulated.
    """
    # Clear existing data
    db.query(AuditEvent).delete()
    db.query(Task).delete()
    db.query(EvidenceItem).delete()
    db.query(IncidentReportLink).delete()
    db.query(Report).delete()
    db.query(Incident).delete()
    db.commit()

    now = datetime.utcnow()

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
        latitude=19.0178,
        longitude=72.8478,
        has_grounded_coordinates=True,
        evidence_status="partially_corroborated",
        is_simulated=True,
        created_at=now - timedelta(hours=3),
        updated_at=now - timedelta(hours=1)
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
        latitude=19.0596,
        longitude=72.8450,
        has_grounded_coordinates=True,
        evidence_status="unverified",
        is_simulated=True,
        created_at=now - timedelta(hours=2),
        updated_at=now - timedelta(hours=2)
    )

    db.add(inc_waterlogging)
    db.add(inc_tree)
    db.commit()

    # 3. Reports
    # Report 1 (English): Hindmata bus passenger
    rep1 = Report(
        id="rep-hindmata-en",
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
        extraction_source="demo",
        extracted_json={
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
            "summary": "Critical waterlogging knee-deep near Hindmata cinema stalling transit buses."
        },
        submitted_at=now - timedelta(hours=2, minutes=50),
        processed_at=now - timedelta(hours=2, minutes=49)
    )

    # Report 2 (Hindi): Shopkeeper near Dadar TT
    rep2 = Report(
        id="rep-hindmata-hi",
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
        extraction_source="demo",
        extracted_json={
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
            "summary": "Hindmata and Dadar TT Circle inundated with ~3 feet water, submerging vehicles and trapping residents."
        },
        submitted_at=now - timedelta(hours=2, minutes=30),
        processed_at=now - timedelta(hours=2, minutes=29)
    )

    # Report 3 (Marathi): Local commuter
    rep3 = Report(
        id="rep-hindmata-mr",
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
        extraction_source="demo",
        extracted_json={
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
            "summary": "Hindmata flyover underpass waterlogged, halting traffic and forcing BEST bus diversions."
        },
        submitted_at=now - timedelta(hours=2, minutes=10),
        processed_at=now - timedelta(hours=2, minutes=9)
    )

    # Report 4 (Unrelated): Bandra tree fall
    rep4 = Report(
        id="rep-bandra-tree",
        original_text="Huge tree has crashed on Western Express Highway right before Bandra flyover north side. Two lanes totally blocked, bumper-to-bumper traffic.",
        media_path=None,
        media_type=None,
        input_language="en",
        reporter_name="Karan Malhotra",
        location_claim="Western Express Highway near Bandra",
        coordinates_lat=19.0596,
        coordinates_lng=72.8450,
        processing_status="processed",
        extraction_source="demo",
        extracted_json={
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
            "summary": "Large tree fallen across two lanes of WEH near Bandra causing extensive highway congestion."
        },
        submitted_at=now - timedelta(hours=1, minutes=45),
        processed_at=now - timedelta(hours=1, minutes=44)
    )

    # Report 5: Unverified forwarded claim (Rumor)
    rep5 = Report(
        id="rep-rumor-forward",
        original_text="FORWARDED AS RECEIVED: Vihar dam gates have collapsed and massive flood wave heading towards Powai and Kurla! Evacuate immediately!",
        media_path=None,
        media_type=None,
        input_language="en",
        reporter_name="Citizen via WhatsApp Forward",
        location_claim="Vihar Dam / Powai area (Unverified)",
        coordinates_lat=None,
        coordinates_lng=None,
        processing_status="needs_review",
        extraction_source="demo",
        extracted_json={
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
            "summary": "Unverified panic viral message alleging dam gate collapse; zero sensory or telemetry corroboration."
        },
        submitted_at=now - timedelta(hours=1, minutes=15),
        processed_at=now - timedelta(hours=1, minutes=14)
    )

    # Report 6: Incomplete or contradictory location details
    rep6 = Report(
        id="rep-ambiguous-loc",
        original_text="Water is entering into our street near the old temple or railway bridge, not sure if its Dadar or Sion side, water is up to shin level.",
        media_path=None,
        media_type=None,
        input_language="en",
        reporter_name="Unknown Caller",
        location_claim="Somewhere near old temple between Dadar and Sion",
        coordinates_lat=None,
        coordinates_lng=None,
        processing_status="needs_review",
        extraction_source="demo",
        extracted_json={
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
            "summary": "Reported localized waterlogging with conflicting and incomplete landmark cues."
        },
        submitted_at=now - timedelta(minutes=45),
        processed_at=now - timedelta(minutes=44)
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
        match_rationale="Matching category: waterlogging | Very close spatial proximity: ~150m | Contextual keyword: Hindmata, underpass",
        reviewed_by="coordinator@sahaayak.ai",
        reviewed_at=now - timedelta(hours=2, minutes=20)
    )
    # rep2 is confirmed
    link2 = IncidentReportLink(
        incident_id=inc_waterlogging.id,
        report_id=rep2.id,
        status="confirmed",
        similarity_score=0.90,
        match_rationale="Matching category: waterlogging | Very close spatial proximity: ~200m | Shared landmark: Dadar TT Circle",
        reviewed_by="coordinator@sahaayak.ai",
        reviewed_at=now - timedelta(hours=2)
    )
    # rep3 is suggested (awaiting coordinator review in demo)
    link3 = IncidentReportLink(
        incident_id=inc_waterlogging.id,
        report_id=rep3.id,
        status="suggested",
        similarity_score=0.89,
        match_rationale="Matching category: waterlogging | High spatial overlap (~100m) | Marathi corroboration mentioning Hindmata flyover transit diversion",
        reviewed_by=None,
        reviewed_at=None
    )
    # rep4 linked to WEH tree fall
    link4 = IncidentReportLink(
        incident_id=inc_tree.id,
        report_id=rep4.id,
        status="confirmed",
        similarity_score=0.95,
        match_rationale="Direct report describing tree fall blocking WEH near Bandra flyover.",
        reviewed_by="coordinator@sahaayak.ai",
        reviewed_at=now - timedelta(hours=1, minutes=30)
    )

    db.add_all([link1, link2, link3, link4])
    db.commit()

    # 5. Evidence Items explicitly marked as simulated
    ev1 = EvidenceItem(
        incident_id=inc_waterlogging.id,
        report_id=rep1.id,
        source_type="field_report",
        source_name="Citizen Field Observation",
        source_url=None,
        is_simulated=True,
        claim_summary="Knee-deep water (~85cm) submerging underpass road surface.",
        verification_status="corroborating",
        reviewer_notes="Corroborated by secondary reports and drainage sensor gauges."
    )
    ev2 = EvidenceItem(
        incident_id=inc_waterlogging.id,
        report_id=None,
        source_type="sensor_gauge",
        source_name="MCGM Automated Rain & Sump Gauge 04-Dadar",
        source_url="https://disaster-demo.internal/gauges/dadar-04",
        is_simulated=True,
        claim_summary="Culvert intake flow rate saturated; sump reservoir level at 98% capacity.",
        verification_status="corroborating",
        reviewer_notes="Telemetry confirms drainage saturation since 08:30 IST."
    )
    ev3 = EvidenceItem(
        incident_id=inc_waterlogging.id,
        report_id=None,
        source_type="official_bulletin",
        source_name="Traffic Police Control Room Alert #442",
        source_url="https://traffic-demo.internal/bulletins/442",
        is_simulated=True,
        claim_summary="Dr. B.A. Road closed for small vehicular traffic between Dadar and Parel; transit diverted via flyover upper deck.",
        verification_status="corroborating",
        reviewer_notes="Official diversion confirmation."
    )
    ev4 = EvidenceItem(
        incident_id=inc_waterlogging.id,
        report_id=rep5.id,
        source_type="community_claim",
        source_name="Social Media Forward #9021",
        source_url=None,
        is_simulated=True,
        claim_summary="Alleges culvert wall collapse under Dadar flyover.",
        verification_status="conflicting",
        reviewer_notes="Conflicting claim refuted by MCGM ward engineer site visual inspection; retaining wall remains intact."
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
        approved_at=now - timedelta(hours=2, minutes=10)
    )
    task2 = Task(
        incident_id=inc_waterlogging.id,
        title="Establish Traffic Police Diversion Cones at Dadar TT",
        description="Prevent two-wheelers and light motor vehicles from entering waterlogged underpass.",
        priority="high",
        status="completed",
        assigned_to="Matunga Traffic Division",
        approved_by="coordinator@sahaayak.ai",
        approved_at=now - timedelta(hours=2, minutes=30)
    )
    task3 = Task(
        incident_id=inc_waterlogging.id,
        title="Distribute Sandbags to At-Risk Groundfloor Retailers",
        description="Coordinate flood barriers with local commercial associations along Dr. B.A. Road.",
        priority="medium",
        status="suggested",
        assigned_to=None,
        approved_by=None
    )
    task4 = Task(
        incident_id=inc_tree.id,
        title="Dispatch Hydraulic Crane and Chainsaw Squad",
        description="Cut and remove fallen banyan trunk from WEH Northbound lanes 1 & 2.",
        priority="high",
        status="pending",
        assigned_to="Garden Cell Emergency Unit #02",
        approved_by="coordinator@sahaayak.ai",
        approved_at=now - timedelta(hours=1, minutes=20)
    )

    db.add_all([task1, task2, task3, task4])
    db.commit()

    # 7. Audit Events
    audit1 = AuditEvent(
        actor="system",
        action="SYSTEM_INITIALIZED",
        entity_type="system",
        entity_id="init",
        details={"environment": "demo", "seed_time": now.isoformat()},
        timestamp=now - timedelta(hours=3)
    )
    audit2 = AuditEvent(
        actor="coordinator@sahaayak.ai",
        action="MATCH_CONFIRMED",
        entity_type="link",
        entity_id=link1.id,
        details={"incident_id": inc_waterlogging.id, "report_id": rep1.id},
        timestamp=now - timedelta(hours=2, minutes=20)
    )
    audit3 = AuditEvent(
        actor="coordinator@sahaayak.ai",
        action="TASK_APPROVED",
        entity_type="task",
        entity_id=task1.id,
        details={"title": task1.title, "assignee": task1.assigned_to},
        timestamp=now - timedelta(hours=2, minutes=10)
    )

    db.add_all([audit1, audit2, audit3])
    db.commit()

    return {
        "status": "success",
        "message": "Deterministic demo dataset seeded successfully",
        "incidents_count": 2,
        "reports_count": 6,
        "links_count": 4,
        "evidence_count": 4,
        "tasks_count": 4
    }
