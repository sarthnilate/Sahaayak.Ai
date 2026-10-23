# Sahaayak AI — Security Architecture & Threat Model

**Version**: 1.0.0 (Phase 9 Hardening)  
**Security Standard**: OWASP Top 10 (2021) + OWASP Top 10 for LLM Applications (2025)  
**Test Suite**: `backend/tests/test_phase9_security.py` (87 tests, 100% passing)

---

## 1. Executive Summary & Defense-in-Depth Architecture

Sahaayak AI operates in high-stress disaster response environments (heavy monsoon inundation, urban flash flooding, falling trees). Malicious interference, rumor amplification, denial of service, and access violation present critical risks.

The application implements defense-in-depth across 5 layers:
1. **Network & Protocol**: Content Security Policy (CSP), strict CORS whitelist, Secure/HttpOnly/SameSite cookies, CSRF double-submit protection.
2. **Authentication & RBAC**: Argon2id password hashing, JWT stateless access tokens, strict role segregation (`admin`, `coordinator`, `reporter`, `auditor`).
3. **Input Validation & Anti-Abuse**: Pydantic schema validation, Slowapi rate limiting, EXIF stripping, Pillow decompression-bomb defense, SSRF guard with private IP / DNS rebinding rejection.
4. **AI Safety & Structured Guardrails**: Schema-enforced deterministic JSON extraction, adversarial prompt injection containment, audit trails of all corrections.
5. **Data Lifecycle & Privacy**: Automated image retention job, immutable audit logs, credential-free logging and error envelopes.

---

## 2. OWASP Top 10 (2021) Security Matrix

| OWASP Category | Control Description | Enforcement Location | Automated Test in `test_phase9_security.py` |
| :--- | :--- | :--- | :--- |
| **A01: Broken Access Control** | • Reporter cannot approve tasks or manage incidents<br>• IDOR: User cannot view another reporter's private report or image<br>• Registration strictly enforces `reporter` role (mass assignment blocked) | `backend/app/core/auth.py`<br>`backend/app/api/v1/incidents.py`<br>`backend/app/api/v1/tasks.py`<br>`backend/app/api/v1/reports.py` | `TestBrokenAccessControl::test_reporter_cannot_approve_task`<br>`TestBrokenAccessControl::test_reporter_cannot_read_other_reporter_report`<br>`TestBrokenAccessControl::test_reporter_cannot_get_other_reporter_image`<br>`TestBrokenAccessControl::test_mass_assignment_role_register` |
| **A02: Cryptographic Failures** | • Passwords hashed with Argon2id (`time_cost=2, memory_cost=65536`)<br>• Secure token generation via `secrets.token_hex`<br>• JWT signed with HS256 and secret rotation support<br>• No plain passwords or credentials in DB | `backend/app/core/auth.py`<br>`backend/app/core/config.py` | `test_password_strength_and_hashing`<br>`TestSecretsNotLeaked::test_health_endpoint_no_secrets` |
| **A03: Injection (SQL & Command)** | • ORM parameterization via SQLAlchemy prevents SQL injection<br>• Zero dynamic SQL formatting or shell execution<br>• Fuzzing with SQL metacharacters across all filter endpoints | `backend/app/db/session.py`<br>`backend/app/repositories/`<br>`backend/app/api/v1/` | `TestInjection::test_sql_injection_in_search_param`<br>`TestInjection::test_sql_injection_in_status_filter`<br>`TestInjection::test_sql_injection_in_language_filter`<br>`TestInjection::test_sql_injection_in_report_text` |
| **A04: Insecure Design (Rate Limiting & Anti-Bruteforce)** | • Rate limiting per IP and user (Slowapi)<br>• Lockout threshold after 5 consecutive failures<br>• Generic error responses to eliminate username/email enumeration | `backend/app/api/v1/auth.py`<br>`backend/app/api/v1/reports.py` | `TestRateLimitingAndThrottling::test_login_wrong_password_returns_generic_error`<br>`TestRateLimitingAndThrottling::test_login_nonexistent_user_returns_same_error` |
| **A05: Security Misconfiguration** | • Strict Content Security Policy (CSP)<br>• `X-Content-Type-Options: nosniff`<br>• `X-Frame-Options: DENY` (anti-clickjacking)<br>• `Referrer-Policy: strict-origin-when-cross-origin`<br>• Detailed stack traces concealed in standard error envelope | `backend/app/core/security.py`<br>`backend/app/core/errors.py` | `TestSecurityHeaders::test_referrer_policy_set`<br>`TestSecurityHeaders::test_permissions_policy_set`<br>`TestXSS::test_csp_header_present_on_api_response`<br>`TestErrorResponseLeakage::test_404_error_envelope_no_stack_trace` |
| **A06: Vulnerable & Outdated Components** | • Automated dependency vulnerability scanning with `pip-audit` & `npm audit`<br>• Pillow upgraded to >= 13.0.0 to remediate CVEs<br>• Minimal, pinned dependencies | `pyproject.toml`<br>`frontend/package.json` | Validated by CI pipeline and `pip-audit` |
| **A07: Identification & Auth Failures** | • Double-submit CSRF protection on mutating requests (`X-CSRF-Token`)<br>• Secure, HttpOnly cookie flags on production<br>• Session timeout and token expiration | `backend/app/core/security.py`<br>`backend/app/core/auth.py` | `TestCSRFProtection::test_csrf_missing_header_rejected`<br>`TestCSRFProtection::test_csrf_wrong_token_rejected` |
| **A08: Software & Data Integrity Failures** | • EXIF data stripped (privacy leak / GPS tracking protection)<br>• Decompression bomb guards (max 4096x4096px, 10MB limit)<br>• Magic byte inspection (disallowing polyglot executables)<br>• Server-side UUID filenames outside web root | `backend/app/services/storage/image_security.py`<br>`backend/app/services/storage/provider.py` | `TestUploadAbuse::test_upload_oversize_file_rejected`<br>`TestUploadAbuse::test_upload_polyglot_file_rejected`<br>`TestUploadAbuse::test_upload_exif_stripped`<br>`TestUploadAbuse::test_path_traversal_in_storage_provider_blocked` |
| **A09: Security Logging & Monitoring Failures** | • Immutable audit log trail (`AuditEvent`) for all operational transitions<br>• Actor, timestamp, before/after diff tracking<br>• Redaction of PII and report texts from system failure logs | `backend/app/services/audit/service.py`<br>`backend/app/core/logging.py` | `TestLogRedaction::test_extraction_failure_redacts_report_text`<br>`test_audit_trail_recorded` |
| **A10: Server-Side Request Forgery (SSRF)** | • Dedicated `SSRFGuard` for external feeds / live feeds<br>• Scheme whitelist (`https://` only)<br>• Loopback, AWS/GCP metadata (`169.254.169.254`), and RFC 1918 private IP blocking<br>• DNS rebinding prevention | `backend/app/services/evidence/ssrf_guard.py` | `TestSSRFGuard::test_ssrf_localhost_blocked`<br>`TestSSRFGuard::test_ssrf_aws_metadata_blocked`<br>`TestSSRFGuard::test_ssrf_rfc1918_10_blocked`<br>`TestSSRFGuard::test_ssrf_dns_rebinding_simulation` |

---

## 3. OWASP Top 10 for LLM Applications (2025)

| LLM Vulnerability | Mitigation in Sahaayak AI | Automated Verification |
| :--- | :--- | :--- |
| **LLM01: Prompt Injection** | Structured JSON extraction only; user report text treated strictly as untrusted input data, never executed as instruction. Schema parser discards instructions to alter roles or incident attributes. | `TestPromptInjection::test_prompt_injection_does_not_break_schema` |
| **LLM02: Sensitive Information Disclosure** | API keys and connection strings never rendered in API responses, health endpoints, or error payloads. Sensitive PII stripped before audit logging. | `TestSecretsNotLeaked::test_ai_status_endpoint_no_key_leak`<br>`TestSecretsNotLeaked::test_error_envelope_no_db_url_leak` |
| **LLM04: Model Denial of Service** | Extraction timeouts (configurable `AI_TIMEOUT_SECONDS`), retry caps with exponential backoff, circuit-breaker fallback to deterministic demo adapter when quotas are hit. | Tested in AI resilience & extraction service test suite |
| **LLM09: Overreliance / Hallucination** | Human-in-the-loop review workflow. Uncorroborated reports flagged as `NEEDS_REVIEW`. Unclear coordinates isolated from Grounded Coordinate Surface to prevent hallucinated pin placement. | `TestBrokenAccessControl::test_mass_assignment_approved_priority_report` |

---

## 4. Map Integration & Tile API Security

- **Providers Supported**:
  1. **CARTO Dark Matter** (`https://*.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`)
  2. **CARTO Voyager** (`https://*.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png`)
  3. **OpenStreetMap** (`https://*.tile.openstreetmap.org/{z}/{x}/{y}.png`)
- **CSP Compliance**:
  - `img-src` allows CARTO and OpenStreetMap tiles.
  - Zero external JavaScript loaded; Leaflet bundle is self-hosted and packaged by Vite.
- **Failover & Invalidation**:
  - Live switcher UI allows one-click provider fallback.
  - Automatic `invalidateSize()` recalculation on container mount ensures no blank tiles.

---

## 5. Security Maintenance & Verification

To run the complete Phase 9 security regression suite:

```bash
# Security & Adversarial tests (87 tests)
pytest backend/tests/test_phase9_security.py -v

# Full application regression suite (233 tests)
pytest backend/tests/ -v

# Frontend unit & component test suite (14 tests)
npm test --prefix frontend
```
