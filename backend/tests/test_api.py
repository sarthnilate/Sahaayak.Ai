from backend.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "ai_provider" in data

def test_seed_demo_data():
    response = client.post("/api/v1/seed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["incidents_count"] == 2
    assert data["reports_count"] == 6

def _coord_client():
    r = client.post("/api/v1/auth/login", json={"email": "coordinator@sahaayak.ai", "password": "CoordPass@2026"})
    c = TestClient(app, cookies=dict(r.cookies))
    c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return c


def test_list_incidents():
    response = client.get("/api/v1/incidents")
    assert response.status_code == 200
    data = response.json()
    incidents = data.get("items", data)
    assert len(incidents) >= 2
    assert any(inc["category"] == "waterlogging" for inc in incidents)

def test_incident_detail():
    response = client.get("/api/v1/incidents/inc-hindmata-001")
    assert response.status_code == 200
    data = response.json()
    assert data["incident"]["id"] == "inc-hindmata-001"
    assert len(data["links"]) >= 3
    assert len(data["evidence_items"]) >= 3
    assert len(data["tasks"]) >= 3

def test_report_submission_text():
    response = client.post(
        "/api/v1/reports",
        data={
            "original_text": "Water is 3 feet high near Hindmata Dadar, buses are blocked!",
            "input_language": "en",
            "reporter_name": "Test Reporter",
            "location_claim": "Hindmata"
        }
    )
    assert response.status_code == 200
    report = response.json()
    assert report["processing_status"] in ["processed", "needs_review"]
    assert report["extracted_json"] is not None
    assert report["extracted_json"]["hazard_type"] == "waterlogging"

def test_match_confirm():
    # Confirm suggested link from seed data
    c = _coord_client()
    response = c.post(
        "/api/v1/incidents/inc-hindmata-001/reports/rep-hindmata-mr/confirm",
        json={"reviewer_notes": "Confirmed Marathi commuter report"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"

def test_task_approve_and_update():
    # Approve task3
    c = _coord_client()
    tasks = c.get("/api/v1/tasks?incident_id=inc-hindmata-001").json()
    suggested_task = next((t for t in tasks if t["status"] == "suggested"), None)
    if suggested_task:
        resp = c.post(
            f"/api/v1/tasks/{suggested_task['id']}/approve",
            json={"approved_by": "coordinator@sahaayak.ai", "assigned_to": "Ward Squad"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

def test_priority_override():
    c = _coord_client()
    # Overriding priority without reason should fail (400)
    resp = c.patch(
        "/api/v1/incidents/inc-hindmata-001",
        json={"approved_priority": "low"}
    )
    assert resp.status_code == 400

    # Overriding priority with reason succeeds
    resp2 = c.patch(
        "/api/v1/incidents/inc-hindmata-001",
        json={"approved_priority": "high", "priority_override_reason": "Drainage clearing progressed faster than expected"}
    )
    assert resp2.status_code == 200
    assert resp2.json()["approved_priority"] == "high"

def test_audit_trail():
    response = client.get("/api/v1/audit")
    assert response.status_code == 200
    events = response.json()
    assert len(events) > 0
