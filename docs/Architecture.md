# Sahaayak AI --- Architecture

## 1. Architecture principles
Visual implementation must follow `Design.md`: dark-first jet black `#0B0B0B`, hot pink `#FF2DA8`, chartreuse `#D4FF3F`, white text, and concrete grey `#A7A7A7`, with restrained abstract halftone/fluid graphics. Do not substitute a white corporate, sage-green, or teal-dominated dashboard.

- Build a modular monolith first; avoid premature microservices.
- Keep AI-provider code behind an adapter (using Google Gemini API).
- Keep business rules deterministic where possible.
- Treat external and user-provided content as untrusted input.
- Preserve original evidence and audit history.
- Use human approval for consequential actions.
- Keep the demo functional without paid API credentials.

## 2. Technology stack

### Frontend
- React + TypeScript + Vite
- Tailwind CSS
- React Router (v6 / modern SPA routing)
- Lucide React icons
- Leaflet + React-Leaflet for grounded coordinates

### Backend
- Python 3.11+ with FastAPI
- Pydantic request/response schemas
- SQLAlchemy ORM with SQLite (persistent local storage file `sahaayak.db`) or PostgreSQL
- Alembic migrations
- Google GenAI SDK (`google-genai` / `google-generativeai`)

### AI and Integrations
- Google Gemini API through server-side adapter
- Deterministic demo adapter for guaranteed reproducible demo flows

## 3. High-level data flow
1. Reporter submits text/image.
2. Frontend calls FastAPI report endpoint (`/api/v1/reports`).
3. Backend validates content and persists the report.
4. Extraction service invokes Google Gemini adapter or Demo adapter.
5. Pydantic validates normalized extraction output.
6. Matching service identifies candidate related reports.
7. Verification service attaches available evidence and tracks unknown/conflicting claims.
8. Priority service produces an explainable suggestion.
9. Coordinator reviews report/incident and confirms or rejects associations.
10. Coordinator approves a recommended task.
11. Task service updates state and audit service records the transition.
12. Frontend reads current state through APIs; persisted data survives reloads.

## 4. Role-Based Access Control (RBAC) Matrix

The table below documents permission boundaries across all platform endpoints:

| Endpoint | Method | Public / Unauth | Reporter | Coordinator | Admin | Security & Scoping Rules |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/v1/health` | GET | Allowed | Allowed | Allowed | Allowed | Liveness probe; no auth required |
| `/api/v1/ready` | GET | Allowed | Allowed | Allowed | Allowed | Database connectivity probe |
| `/api/v1/auth/register` | POST | Allowed | Allowed | Allowed | Allowed | Creates role "reporter" ONLY (role payload ignored) |
| `/api/v1/auth/login` | POST | Allowed | Allowed | Allowed | Allowed | Argon2 + lockout throttling after 5 attempts |
| `/api/v1/auth/logout` | POST | Denied (401) | Allowed | Allowed | Allowed | Clears `access_token` and `csrf_token` cookies |
| `/api/v1/auth/me` | GET | Denied (401) | Allowed | Allowed | Allowed | Returns profile of caller |
| `/api/v1/reports` | POST | Allowed | Allowed | Allowed | Allowed | Public intake; rate-limited; links `user_id` if logged in |
| `/api/v1/reports` | GET | Demo Fallback | Own only | All | All | Scoped by `user_id == current_user.id` for reporters |
| `/api/v1/reports/{id}` | GET | Denied (401) | Own only | All | All | 403 Forbidden if reporter accesses another reporter's report |
| `/api/v1/reports/{id}/image`| GET | Denied (401) | Own only | All | All | Protected file streaming; prevents raw static access |
| `/api/v1/reports/lookup/{ref}`| GET | Allowed | Own/Public | All | All | Lookup status by human reference `SAH-2026-XXXXXX` |
| `/api/v1/reports/{id}/process`| POST | Denied (401) | Own only | Allowed | Allowed | Triggers AI extraction on unprocessed report |
| `/api/v1/reports/{id}/retry`| POST | Denied (401) | Own only (403 for others) | Allowed | Allowed | Re-run AI extraction; reporters can only retry own reports |
| `/api/v1/reports/{id}/correction`| POST | Denied (401) | Denied (403) | Allowed | Allowed | Coordinator annotation stored separately from AI extraction |
| `/api/v1/settings/ai-status`| GET | Allowed | Allowed | Allowed | Allowed | Returns mode, provider, model, key_configured — no secrets |
| `/api/v1/incidents` | GET | Allowed | Allowed | Allowed | Allowed | Crisis map & radar |
| `/api/v1/incidents/{id}` | GET | Allowed | Allowed | Allowed | Allowed | Incident details & telemetry |
| `/api/v1/incidents/{id}` | PATCH | Denied (401) | Denied (403) | Allowed | Allowed | Priority override with mandatory justification reason |
| `/api/v1/incidents/{id}/reports/{r_id}/confirm`| POST | Denied (401) | Denied (403) | Allowed | Allowed | Candidate link confirmation |
| `/api/v1/incidents/{id}/reports/{r_id}/reject` | POST | Denied (401) | Denied (403) | Allowed | Allowed | Candidate link rejection |
| `/api/v1/tasks` | GET | Allowed | Allowed | Allowed | Allowed | Task list |
| `/api/v1/tasks/{id}/approve` | POST | Denied (401) | Denied (403) | Allowed | Allowed | Squad dispatch approval |
| `/api/v1/tasks/{id}/status` | PATCH | Denied (401) | Denied (403) | Allowed | Allowed | Task lifecycle transitions |
| `/api/v1/audit` | GET | Denied (401) | Denied (403) | Allowed | Allowed | Immutable audit log trail |
| `/api/v1/seed` | POST | Allowed | Allowed | Allowed | Allowed | Populates deterministic demo data |

## 5. AI Extraction Architecture (Phase 3)

### Provider Interface
```
ExtractionProvider (abstract)
├── GeminiProvider    — server-side google-genai SDK, structured JSON output
└── DemoProvider      — deterministic scenarios keyed by content fingerprint
```

### Schema: `ReportExtractionSchema`
All fields are Pydantic-validated before database write. Unknown values stay `null`/`"unknown"` — validators reject invented placeholders.

| Field | Type | Description |
|:---|:---|:---|
| `category` | enum | waterlogging, tree_fall, traffic_congestion, structural_damage, power_outage, medical_emergency, fire, rumor, other, unknown |
| `short_summary` | str (required) | One-line factual summary |
| `original_text_language` | enum | en, hi, mr, mixed, unknown |
| `reported_location_text` | str \| null | Raw location as stated |
| `location_precision` | str | exact, neighborhood, city, unknown |
| `location_source` | str | Where location info was extracted from |
| `incident_time` | datetime \| null | Only if explicitly stated |
| `claimed_severity` | enum | critical, high, medium, low, unknown |
| `safety_concern` | bool | Whether a safety threat is detected |
| `safety_concern_reason` | str \| null | Justification for safety concern |
| `explicit_facts[]` | list[str] | Directly grounded from report text |
| `model_inferences[]` | list[str] | AI-derived predictions (separated from facts) |
| `missing_information[]` | list[str] | Required data not present in report |
| `ambiguities[]` | list[str] | Unclear claims |
| `contradictions[]` | list[str] | Conflicting statements |
| `follow_up_questions[]` | list[str] | Recommended inquiries |

### Coordinator Corrections
Stored in `coordinator_correction` (JSON column) alongside `correction_notes`, `corrected_by`, `corrected_at`. The original AI extraction is **never overwritten** — corrections are a separate audited layer.

### Metadata Stamping
Every extraction result carries `ExtractionMetadata`: `provider`, `mode` (demo\|gemini), `model`, `latency_ms`, `attempt_count`, `schema_version`, `simulated` (bool), `processed_at`.

