# Sahaayak AI — Memory & Execution State

## Active Phase
- Current Phase: Phase 10 (Hackathon Demo Readiness)
- Status: Completed (End-to-End MVP Verified)

## Architecture Decisions & Constraints
- **AI Engine**: Google Gemini API via official `google-genai` SDK (`gemini-2.5-flash`), backed by a deterministic Demo Adapter for zero-dependency offline evaluations.
- **Multilingual Support**: Native English, Hindi (हिंदी), and Marathi (मराठी) report intake, normalization, and font rendering.
- **Visual Design Identity**: Locked to Jet Black (`#0B0B0B`), Hot Pink (`#FF2DA8`), Chartreuse (`#D4FF3F`), White (`#FFFFFF`), and Concrete Grey (`#A7A7A7`), featuring cyber-editorial layout and dark CartoDB Leaflet tiles.
- **Persistence**: Relational SQLite database (`sahaayak.db`) via SQLAlchemy ORM with persistent transaction logs, surviving reloads and server restarts.
- **Human-in-the-Loop Boundaries**: Coordinators must manually confirm duplicate candidate matches and approve action tasks; automated sirens/911 dispatches are prevented by design. Priority overrides strictly require documented justifications.

## Implemented Features Across Phases
- [x] **Phase 0 (Reconnaissance)**: Workspace analyzed, architecture constraints codified, documentation repository established.
- [x] **Phase 1 (Project Foundation)**: FastAPI backend + SQLite SQLAlchemy + React/Vite/TypeScript + Tailwind design system + Health endpoint.
- [x] **Phase 2 (Core Reporting Workflow)**: Multilingual text & image intake, file validation, storage in `./uploads`, report archive.
- [x] **Phase 3 (AI Extraction & Adapters)**: Pydantic extraction schema (`hazard_type`, `severity`, `water_depth_cm`, `infrastructure`, `urgent_needs`, `grounded_coordinates`), Google Gemini live adapter, deterministic demo adapter, failure preservation & retry endpoint.
- [x] **Phase 4 (Incident Management)**: Incident CRUD, grounded Leaflet map with coordinates, ungrounded landmark fallback, filter by category/priority.
- [x] **Phase 5 (Duplicate Detection & Review)**: Multi-signal similarity algorithm (category match, Haversine distance, landmark tokens, temporal delta), coordinator Confirm/Reject workflow, dynamic priority recalculation.
- [x] **Phase 6 (Evidence & Verification)**: Source attribution, verification states (*Corroborating*, *Conflicting*, *Unverified*), conflict radar on dashboard.
- [x] **Phase 7 (Priority & Action Workflow)**: Deterministic explainable priority calculation, coordinator priority override with mandatory justification, task recommendation lifecycle (`suggested -> pending -> in_progress -> completed`).
- [x] **Phase 8 (Dashboard Polish & Usability)**: Responsive navigation, live crisis metrics, real-time clock, status/priority badges.
- [x] **Phase 9 (Testing & Hardening)**: Full 9/9 pytest backend test suite passing, production Vite build passing with 0 errors.
- [x] **Phase 10 (Demo Readiness)**: Deterministic demo dataset seeded, `DEMO_SCRIPT.md` created, end-to-end browser walkthrough verified.

## Test Execution Results
- `pytest backend/tests/test_api.py -v`: 9 passed in 0.48s.
- `npm run build` in `frontend`: Vite v8.3.5 built client in 832ms with 0 errors.
- `browser_subagent`: Navigated and visually verified all 5 tabs (`http://127.0.0.1:5173/`), submitted preset reports, confirmed grounded map markers, inspected explainable AI priority, verified tasks, and checked audit events.

## Current Service Endpoints
- Frontend UI: `http://localhost:5173/`
- Backend API: `http://localhost:8000/api/v1/`
- OpenAPI Swagger: `http://localhost:8000/docs`
