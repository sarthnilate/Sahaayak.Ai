import pytest
from alembic.config import Config
from backend.app.core.config import Settings
from backend.app.core.errors import AuditMutationForbiddenError, make_error_envelope
from backend.app.main import app
from backend.app.models.all_models import AuditEvent, Base
from backend.app.repositories.audit_repository import AuditRepository
from backend.app.services.audit.service import AuditService, redact_metadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alembic import command

client = TestClient(app)

# ==============================================================================
# 1. Error Envelope and Request ID Tests
# ==============================================================================

def test_request_id_in_response_headers():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    # Valid UUID format
    val = response.headers["X-Request-ID"]
    assert len(val) >= 10

def test_custom_request_id_propagation():
    custom_id = "test-req-9999-alpha"
    response = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id

def test_domain_exception_error_envelope():
    # Calling non-existent report triggers domain error envelope
    response = client.get("/api/v1/reports/non-existent-report-id")
    assert response.status_code in [404, 400]
    data = response.json()
    assert "error" in data
    err = data["error"]
    assert "code" in err
    assert "message" in err
    assert "request_id" in err
    assert "traceback" not in err  # NEVER leak stack traces

def test_make_error_envelope_helper():
    env = make_error_envelope("STABLE_CODE", "An explanation", "req-123", {"field": "val"})
    assert env["error"]["code"] == "STABLE_CODE"
    assert env["error"]["message"] == "An explanation"
    assert env["error"]["request_id"] == "req-123"
    assert env["error"]["details"]["field"] == "val"

# ==============================================================================
# 2. Config Validation & Fail Fast Tests
# ==============================================================================

def test_config_fail_fast_on_invalid_db_url():
    with pytest.raises(ValueError, match="Invalid DATABASE_URL scheme"):
        Settings(
            DATABASE_URL="invalid_scheme://host/db",
            _env_file=None
        )

def test_config_fail_fast_on_missing_gemini_key_in_gemini_mode():
    with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
        Settings(
            AI_MODE="gemini",
            GEMINI_API_KEY="",
            _env_file=None
        )

def test_config_accepts_valid_demo_mode():
    cfg = Settings(AI_MODE="demo", GEMINI_API_KEY=None, _env_file=None)
    assert cfg.AI_MODE == "demo"
    assert cfg.LIVE_SOURCES_ENABLED is False

# ==============================================================================
# 3. Health & Readiness Probes
# ==============================================================================

def test_health_liveness_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "ai_provider" in data

def test_ready_readiness_endpoint():
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert "dialect" in data

# ==============================================================================
# 4. Audit Append-Only Immutability Enforcement
# ==============================================================================

def test_audit_append_only_event_listener():
    # Set up dedicated in-memory database with Base metadata
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # 1. Create audit event
    event = AuditService.record(
        db=db,
        actor="coordinator@sahaayak.ai",
        action="TEST_ACTION",
        entity_type="incident",
        entity_id="inc-100",
        before={"status": "open"},
        after={"status": "resolved"}
    )
    assert event.id is not None

    # 2. Attempt UPDATE -> MUST raise AuditMutationForbiddenError
    event.action = "TAMPERED_ACTION"
    with pytest.raises(AuditMutationForbiddenError) as exc_info:
        db.commit()
    assert "Audit events are immutable" in str(exc_info.value)
    db.rollback()

    # 3. Attempt DELETE -> MUST raise AuditMutationForbiddenError
    fresh_event = db.get(AuditEvent, event.id)
    assert fresh_event is not None
    db.delete(fresh_event)
    with pytest.raises(AuditMutationForbiddenError) as exc_info:
        db.commit()
    assert "Audit events are immutable" in str(exc_info.value)
    db.rollback()

    # 4. Attempt update/delete via repository methods
    repo = AuditRepository(db)
    with pytest.raises(AuditMutationForbiddenError):
        repo.update()
    with pytest.raises(AuditMutationForbiddenError):
        repo.delete()

def test_audit_metadata_redaction():
    unclean = {
        "user_email": "citizen@example.com",
        "secret": "my_top_secret_token",
        "password": "cleartextpassword123",
        "nested": {
            "gemini_api_key": "AIzaSyFakeKey123456789",
            "normal_field": "ok"
        },
        "original_text": "A" * 150
    }
    cleaned = redact_metadata(unclean)
    assert cleaned["secret"] == "***REDACTED***"
    assert cleaned["password"] == "***REDACTED***"
    assert cleaned["nested"]["gemini_api_key"] == "***REDACTED***"
    assert cleaned["nested"]["normal_field"] == "ok"
    assert "TRUNCATED_FOR_AUDIT" in cleaned["original_text"]

# ==============================================================================
# 5. Programmatic Alembic Migration Up / Down / Up Verification
# ==============================================================================

def test_alembic_migration_up_down_up(tmp_path):
    test_db = tmp_path / "migration_verify.db"
    test_db_url = f"sqlite:///{test_db}"

    # Configure alembic dynamically
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
    alembic_cfg.set_main_option("script_location", "backend/alembic")

    # 1. Upgrade to head
    command.upgrade(alembic_cfg, "head")

    # Verify tables created
    engine = create_engine(test_db_url)
    with engine.connect() as conn:
        tables = engine.dialect.get_table_names(conn)
        assert "users" in tables
        assert "reports" in tables
        assert "incidents" in tables
        assert "audit_events" in tables

    # 2. Downgrade to base
    command.downgrade(alembic_cfg, "base")
    with engine.connect() as conn:
        tables_after_down = engine.dialect.get_table_names(conn)
        assert "users" not in tables_after_down
        assert "incidents" not in tables_after_down

    # 3. Upgrade back to head
    command.upgrade(alembic_cfg, "head")
    with engine.connect() as conn:
        tables_reup = engine.dialect.get_table_names(conn)
        assert "users" in tables_reup
        assert "audit_events" in tables_reup
