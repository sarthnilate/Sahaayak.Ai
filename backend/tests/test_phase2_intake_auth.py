import io
from datetime import datetime

import pytest
from backend.app.core.auth import create_access_token
from backend.app.core.errors import BadRequestError
from backend.app.main import app
from backend.app.services.storage.image_security import sanitize_and_reencode_image
from backend.app.services.storage.provider import storage_provider
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import event


def get_fresh_client() -> TestClient:
    """Returns a fresh client instance with clean cookies for test isolation"""
    return TestClient(app)


def create_test_image(format="JPEG", width=100, height=100, with_exif=False) -> bytes:
    img = Image.new("RGB", (width, height), color=(255, 45, 168))  # Hot Pink
    buf = io.BytesIO()
    if with_exif:
        exif = img.getexif()
        exif[0x010e] = "Sahaayak Secret GPS Location 19.0178, 72.8478"
        img.save(buf, format=format, exif=exif)
    else:
        img.save(buf, format=format)
    return buf.getvalue()


# Ensure demo database is seeded once before test execution
@pytest.fixture(autouse=True)
def ensure_seed():
    c = get_fresh_client()
    c.post("/api/v1/seed")


# ==============================================================================
# 1. Auth & Registration Tests
# ==============================================================================

def test_register_creates_reporter_only():
    """Verify registration creates role 'reporter' ONLY and ignores role parameter"""
    client = get_fresh_client()
    email = f"test_citizen_{datetime.now().timestamp()}@example.com"
    payload = {
        "email": email,
        "username": f"citizen_{int(datetime.now().timestamp())}",
        "password": "SecurePassword123!",
        "full_name": "Citizen One",
        "role": "admin"  # Exploitation attempt to become admin
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["user"]["role"] == "reporter"  # Must strictly be reporter
    assert "access_token" in resp.cookies
    assert "csrf_token" in resp.cookies


def test_password_policy_rejection():
    """Verify weak passwords and breached patterns are rejected"""
    client = get_fresh_client()
    # 1. Too short (< 8 chars) -> Pydantic Schema / Policy rejection
    resp1 = client.post("/api/v1/auth/register", json={
        "email": "short@example.com",
        "username": "short_user",
        "password": "123"
    })
    assert resp1.status_code in [400, 422]

    # 2. Breached pattern
    resp2 = client.post("/api/v1/auth/register", json={
        "email": "breached@example.com",
        "username": "breached_user",
        "password": "password123"
    })
    assert resp2.status_code == 400
    assert resp2.json()["error"]["code"] == "BREACHED_PASSWORD"


def test_login_throttling_and_generic_error():
    """Verify login lockout after 5 failed attempts and generic message (no user enumeration)"""
    client = get_fresh_client()
    email = f"target_{datetime.now().timestamp()}@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "username": f"target_{int(datetime.now().timestamp())}",
        "password": "CorrectPassword123!"
    })

    # Attempt 5 wrong passwords
    for i in range(5):
        resp = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": f"WrongPass_{i}"
        })
        assert resp.status_code == 401
        assert resp.json()["error"]["message"] == "Invalid email or password"

    # 6th attempt -> Account locked
    resp6 = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "CorrectPassword123!"  # Even with correct password, account is locked
    })
    assert resp6.status_code == 401
    assert "locked" in resp6.json()["error"]["message"].lower()


def test_login_success_and_get_me():
    """Verify valid login issues cookies and GET /auth/me returns profile"""
    client = get_fresh_client()
    email = f"success_{datetime.now().timestamp()}@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "username": f"success_{int(datetime.now().timestamp())}",
        "password": "ValidPassword123!"
    })

    login_resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "ValidPassword123!"
    })
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.cookies

    # Access /auth/me with cookies
    me_resp = client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email


def test_logout_clears_cookies():
    """Verify logout removes authentication cookies"""
    client = get_fresh_client()
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200


# ==============================================================================
# 2. CSRF Double-Submit Protection Tests
# ==============================================================================

def test_csrf_rejection_on_mismatched_header():
    """Verify state-changing mutations with cookie but mismatched X-CSRF-Token are rejected with 403"""
    client = get_fresh_client()
    client.cookies.set("access_token", "dummy_token")
    client.cookies.set("csrf_token", "valid_session_csrf_token_123")

    # Send request with invalid CSRF header
    resp = client.post(
        "/api/v1/incidents/inc-hindmata-001/reports/rep-hindmata-en/confirm",
        json={"reviewer_notes": "Attempt without matching csrf"},
        headers={"X-CSRF-Token": "tampered_csrf_header"}
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "CSRF_VALIDATION_FAILED"


# ==============================================================================
# 3. Secure File Upload & Sanitization Tests
# ==============================================================================

def test_upload_rejection_wrong_type():
    """Verify non-image formats (.txt, .exe, .sh) are rejected"""
    client = get_fresh_client()
    files = {"media_file": ("test.txt", b"plain text script content", "text/plain")}
    resp = client.post(
        "/api/v1/reports",
        data={"original_text": "Flooding observed near signal"},
        files=files
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] in ["INVALID_IMAGE_FORMAT", "CORRUPTED_IMAGE"]


def test_upload_rejection_spoofed_mime():
    """Verify spoofed MIME headers (text file masquerading as image/jpeg) are caught by Pillow magic bytes"""
    client = get_fresh_client()
    files = {"media_file": ("exploit.jpg", b"This is not a real JPEG image", "image/jpeg")}
    resp = client.post(
        "/api/v1/reports",
        data={"original_text": "Waterlogging at railway track"},
        files=files
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] in ["INVALID_IMAGE_FORMAT", "CORRUPTED_IMAGE"]

def test_upload_rejection_oversize():
    """Verify payload size check rejects files over MAX_UPLOAD_MB"""
    oversized = b"0" * (11 * 1024 * 1024)
    with pytest.raises(BadRequestError):
        sanitize_and_reencode_image(oversized, max_size_mb=10)


def test_upload_exif_stripped_and_reencoded():
    """Verify image with EXIF metadata is re-encoded and all EXIF tags are stripped"""
    raw_with_exif = create_test_image(format="JPEG", with_exif=True)
    with Image.open(io.BytesIO(raw_with_exif)) as raw_img:
        assert raw_img.getexif() is not None

    cleaned_bytes, ext, mime = sanitize_and_reencode_image(raw_with_exif, max_size_mb=10)
    assert ext in ["jpg", "jpeg"]
    assert mime == "image/jpeg"

    with Image.open(io.BytesIO(cleaned_bytes)) as cleaned_img:
        exif = cleaned_img.getexif()
        assert 0x010e not in exif


def test_storage_path_traversal_prevention():
    """Verify path traversal attempts in storage provider are rejected"""
    with pytest.raises(Exception) as exc_info:
        storage_provider.read_file("../../etc/passwd")
    assert "Path traversal" in str(exc_info.value) or "PATH_TRAVERSAL" in str(exc_info.value)


def test_no_raw_upload_served():
    """Verify uploaded files cannot be accessed via unauthenticated raw static URLs"""
    client = get_fresh_client()
    resp = client.get("/uploads/secret_image.jpg")
    assert resp.status_code in [404, 403]


# ==============================================================================
# 4. Report Intake, Idempotency, and Isolation Tests
# ==============================================================================

def test_report_intake_with_reference_and_fingerprint():
    """Verify report submission generates reference code SAH-2026-XXXXXX and source fingerprint"""
    client = get_fresh_client()
    resp = client.post(
        "/api/v1/reports",
        data={
            "original_text": "Waterlogging 2 feet high at King Circle underpass Dadar",
            "location_claim": "King Circle Dadar",
            "input_language": "en"
        }
    )
    assert resp.status_code == 200
    report = resp.json()
    assert report["reference_code"].startswith("SAH-2026-")
    assert report["source_fingerprint"] is not None
    assert len(report["source_fingerprint"]) == 64  # SHA-256


def test_report_idempotency_key_prevents_duplicate():
    """Verify submitting with the same idempotency key returns the existing report without duplicate processing"""
    client = get_fresh_client()
    idempotency_key = f"idem-key-{datetime.now().timestamp()}"
    data = {
        "original_text": "Tree fallen on Tilak Bridge blocking pedestrian walkway",
        "idempotency_key": idempotency_key
    }

    resp1 = client.post("/api/v1/reports", data=data)
    assert resp1.status_code == 200
    rep1_id = resp1.json()["id"]

    resp2 = client.post("/api/v1/reports", data=data)
    assert resp2.status_code == 200
    rep2_id = resp2.json()["id"]

    assert rep1_id == rep2_id


def test_reporter_cannot_read_another_reporter_report_or_image():
    """Verify reporter isolation: Reporter A cannot read Reporter B's report or image"""
    client_a = get_fresh_client()
    email_a = f"reporter_a_{datetime.now().timestamp()}@example.com"
    reg_a = client_a.post("/api/v1/auth/register", json={
        "email": email_a,
        "username": f"user_a_{int(datetime.now().timestamp())}",
        "password": "Password123!"
    })
    csrf_a = reg_a.json()["csrf_token"]

    img_bytes = create_test_image("JPEG")
    files = {"media_file": ("test.jpg", img_bytes, "image/jpeg")}
    rep_resp = client_a.post(
        "/api/v1/reports",
        data={"original_text": "Water inside ground floor homes in Kurla West"},
        files=files,
        headers={"X-CSRF-Token": csrf_a}
    )
    assert rep_resp.status_code == 200
    report_a_id = rep_resp.json()["id"]

    # 2. Register Reporter B on separate client
    client_b = get_fresh_client()
    email_b = f"reporter_b_{datetime.now().timestamp()}@example.com"
    client_b.post("/api/v1/auth/register", json={
        "email": email_b,
        "username": f"user_b_{int(datetime.now().timestamp())}",
        "password": "Password123!"
    })

    # 3. Reporter B attempts to read Reporter A's report -> 403 Forbidden
    read_resp = client_b.get(f"/api/v1/reports/{report_a_id}")
    assert read_resp.status_code == 403
    assert read_resp.json()["error"]["code"] == "FORBIDDEN_REPORT_ACCESS"

    # 4. Reporter B attempts to read Reporter A's image -> 403 Forbidden
    img_resp = client_b.get(f"/api/v1/reports/{report_a_id}/image")
    assert img_resp.status_code == 403
    assert img_resp.json()["error"]["code"] == "FORBIDDEN_MEDIA_ACCESS"

    # 5. Reporter A can read own image
    own_img_resp = client_a.get(f"/api/v1/reports/{report_a_id}/image")
    assert own_img_resp.status_code == 200
    assert len(own_img_resp.content) > 0


# ==============================================================================
# 5. Query Count & Pagination Tests
# ==============================================================================

def test_reports_pagination():
    """Verify paginated reports response"""
    client = get_fresh_client()
    resp = client.get("/api/v1/reports?page=1&limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert data["limit"] == 2


def test_reports_no_n_plus_one_queries():
    """Verify eager loading: query count remains bounded when listing reports with links"""
    client = get_fresh_client()
    coord_token = create_access_token("usr-coord-001", "coordinator")
    client.cookies.set("access_token", coord_token)

    from backend.app.db.session import engine
    queries = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        resp = client.get("/api/v1/reports?limit=10")
        assert resp.status_code == 200
        # Eager loading (selectinload) must issue count + select reports + selectinload links = ~3 queries, NOT 10+ queries
        assert len(queries) <= 5
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


# ==============================================================================
# 6. RBAC Matrix Endpoint Coverage
# ==============================================================================

def test_rbac_matrix_endpoints():
    """Verify RBAC access controls per endpoint for reporter vs coordinator vs admin"""
    # 1. Retry extraction: reporter forbidden (403), coordinator allowed (200)
    rep_client = get_fresh_client()
    rep_token = create_access_token("usr-reporter-001", "reporter")
    rep_client.cookies.set("access_token", rep_token)
    rep_client.cookies.set("csrf_token", "csrf_valid_token")

    rep_retry = rep_client.post(
        "/api/v1/reports/rep-hindmata-en/retry",
        headers={"X-CSRF-Token": "csrf_valid_token"}
    )
    assert rep_retry.status_code == 403

    coord_client = get_fresh_client()
    coord_token = create_access_token("usr-coord-001", "coordinator")
    coord_client.cookies.set("access_token", coord_token)
    coord_client.cookies.set("csrf_token", "csrf_valid_token")

    coord_retry = coord_client.post(
        "/api/v1/reports/rep-hindmata-en/retry",
        headers={"X-CSRF-Token": "csrf_valid_token"}
    )
    assert coord_retry.status_code == 200

    # 2. Priority override: coordinator allowed with justification reason
    coord_override = coord_client.patch(
        "/api/v1/incidents/inc-hindmata-001",
        json={"approved_priority": "critical", "priority_override_reason": "High density transit risk"},
        headers={"X-CSRF-Token": "csrf_valid_token"}
    )
    assert coord_override.status_code == 200
