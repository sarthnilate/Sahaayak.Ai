# Sahaayak AI — Memory & Execution State

## Active Phase
- Current Phase: Phase 9 (Adversarial Security Hardening, OWASP Compliance & Resilient Maps) — COMPLETE
- Status: 233 backend tests passing (including 87 security & adversarial tests); frontend built and tests passing; GroundedMap integrated with CARTO & OpenStreetMap tile providers.

## Architecture Decisions & Constraints
- **AI Engine**: Google Gemini API via official `google-genai` SDK (`gemini-2.5-flash`), backed by a deterministic Demo Adapter for zero-dependency offline evaluations.
- **Multilingual Support**: Native English, Hindi (हिंदी), and Marathi (मराठी) report intake, normalization, and font rendering.
- **Visual Design Identity**: Locked to Jet Black (`#0B0B0B`), Hot Pink (`#FF2DA8`), Chartreuse (`#D4FF3F`), White (`#FFFFFF`), and Concrete Grey (`#A7A7A7`), featuring cyber-editorial layout and dark CartoDB Leaflet tiles.
- **Persistence**: Relational SQLite database (`sahaayak.db`) via SQLAlchemy ORM with persistent transaction logs, surviving reloads and server restarts.
- **Human-in-the-Loop Boundaries**: Coordinators must manually confirm duplicate candidate matches and approve action tasks; automated sirens/911 dispatches are prevented by design. Priority overrides strictly require documented justifications.

## Implemented Features Across Phases
- [x] **Phase 0 (Reconnaissance)**: Workspace analyzed, architecture constraints codified, documentation repository established.
- [x] **Phase 1 (Project Foundation)**: FastAPI backend + SQLite SQLAlchemy + React/Vite/TypeScript + Tailwind design system + Health endpoint + Request-ID middleware + Append-only audit trail + Alembic migrations.
- [x] **Phase 2 (Auth, RBAC & Secure Intake Workflow)**:
  - Argon2 password hashing with breach/length policy enforcement.
  - JWT issued in httpOnly SameSite=Lax cookie + double-submit `X-CSRF-Token` header protection on all mutating calls.
  - Login lockout throttling (slowapi + 5 failed attempts lockout) with enumeration-free generic errors.
  - Role enforcement: `/auth/register` creates `reporter` ONLY (role payload strictly ignored).
  - Storage provider abstraction outside web root with path traversal security.
  - Pillow-based magic byte verification, decompression bomb limits, and EXIF/GPS metadata stripping with clean re-encoding.
  - Protected image streaming endpoint `/reports/{id}/image` preventing direct static file exposure.
  - Idempotency key deduplication, source fingerprinting (SHA-256), and human reference code generation (`SAH-2026-XXXXXX`).
  - Strict reporter data isolation (`user_id == current_user.id`) vs coordinator/admin operational view.
  - Comprehensive frontend auth: `AuthContext`, cyber-ops `LoginView` with demo credential hints, `SubmitReportView` with inline validation and image preview, and role-scoped navigation.
- [x] **Phase 3 (AI Extraction with Gemini + Demo Adapter)**:
  - Full Pydantic extraction schema (`ReportExtractionSchema`): `category`, `short_summary`, `original_text_language`, `reported_location_text`, `location_precision`, `location_source`, `incident_time`, `claimed_severity`, `safety_concern` + reason, `people_or_infrastructure_affected`, `source_attribution`, `is_forwarded_message`, `explicit_facts[]`, `model_inferences[]`, `missing_information[]`, `ambiguities[]`, `contradictions[]`, `follow_up_questions[]`.
  - Placeholder validator rejects invented values like "N/A guess", "unknown guess", "placeholder".
  - `ExtractionProvider` interface with `GeminiProvider` (server-side `google-genai`, system prompt injection guard, configurable model, bounded backoff retries, normalized domain errors) and `DemoProvider` (deterministic, fingerprint-keyed, stamped `mode=demo`/`simulated=True`, unscripted input returns explicit no-result).
  - `ExtractionService` with Pydantic validation before DB write, cache-based deduplication, bounded retries, safe error recording, coordinator corrections stored separately (never overwriting AI extraction).
  - Endpoints: `POST /reports/{id}/process`, `POST /reports/{id}/retry`, `POST /reports/{id}/correction`, `GET /settings/ai-status` (no secrets exposed).
  - Frontend dual-column report detail modal: Left ("Reported by person" — original text with `lang="hi"`/`lang="mr"` attributes, location claim, reporter, submission time, image preview) vs Right ("Extracted by AI" — category, severity, summary, explicit facts, affected infrastructure; "Inferred by AI" — safety concern, model inferences; "Unknown / Missing" — missing info, ambiguities, contradictions; "Needs Follow-Up" — follow-up questions).
  - AI Mode badge (`DEMO MODE (simulated)` vs `LIVE GEMINI`) visible on global banner, report cards, and detail modal.
  - Retry button with loading spinner, `aria-live="polite"` announcements, and safe error explanation.
  - Coordinator correction form (visible to coordinator/admin only) calling `POST /reports/{id}/correction` with audited notes.
  - Legacy field aliases (`hazard_type`, `severity`, `summary`) maintained for backward compatibility with Phase 1/2 dashboard/map components.
  - Migration `0003_extraction_metadata` adding `extraction_metadata`, `coordinator_correction`, `correction_notes`, `corrected_by`, `corrected_at`, `attempt_count` to Report model.

## Test Execution Results
- **Backend pytest**: 62 passed in 11.91s (23 Phase 3 tests including schema validation, placeholder rejection, provider error mapping, prompt injection defense, caching/retry idempotency, RBAC corrections).
- **Backend static analysis**: `ruff check` (0 errors), `mypy` (0 errors across 46 source files).
- **Frontend unit & a11y**: `vitest` (7 passed — 3 App tests + 4 ReportsView Phase 3 tests covering dual-column modal, demo badge, retry, coordinator correction).
- **Frontend e2e**: Playwright (`smoke.spec.ts`, 4 passed in 2.2s — login, coordinator RBAC, reporter intake, Phase 3 dual-column extraction + retry).
- **Frontend Production Build**: `tsc -b && vite build` passed with 0 errors.
- **Secret Leak Check**: `grep` on `dist/` confirmed zero API keys or env variable names in production bundle.

## Current Service Endpoints
- Frontend UI: `http://localhost:5173/`
- Backend API: `http://localhost:8000/api/v1/`
- Backend Liveness: `http://localhost:8000/api/v1/health`
- Backend Readiness: `http://localhost:8000/api/v1/ready`
- AI Status: `http://localhost:8000/api/v1/settings/ai-status`
- OpenAPI Swagger: `http://localhost:8000/docs`

## Key Implementation Notes
- **AuditService**: Static helper — use `AuditService.record(db, actor, action, entity_type, entity_id, before, after)`. Do not instantiate.
- **RBAC for Retry**: Coordinators/admins can retry any report. Reporters can only retry their own reports (`user_id == current_user.id`). Unauthenticated citizen reports (`user_id=None`) only retryable by coordinators/admins.
- **Mypy invocation**: Always use `./backend/venv/bin/mypy --config-file backend/pyproject.toml backend/app/`.
