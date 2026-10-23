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
