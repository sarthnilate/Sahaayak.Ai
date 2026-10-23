# Sahaayak AI — From Chaos to Action

> **An AI-assisted community incident-intelligence platform for urban crisis coordination.**  
> Powered by **Google Gemini** (via official Google GenAI SDK) with deterministic fallback, human-in-the-loop task dispatch, and grounded evidence verification.

---

## ⚡ Quick Start

### 1. Prerequisites
- **Python 3.11+**
- **Node.js 18+ & npm**

### 2. Backend Setup
```bash
# 1. Create and activate virtual environment
python3 -m venv backend/venv
source backend/venv/bin/activate

# 2. Install backend dependencies
pip install -r backend/requirements.txt

# 3. (Optional) Set Google Gemini API Key
# If not provided, Sahaayak AI runs seamlessly using its Deterministic Demo Adapter
export GEMINI_API_KEY="your-gemini-api-key"

# 4. Start the FastAPI server (runs on port 8000)
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Frontend Setup
```bash
# 1. Navigate to frontend
cd frontend

# 2. Install npm dependencies
npm install

# 3. Start the Vite dev server (runs on port 5173)
npm run dev
```

Open your browser at **[http://localhost:5173](http://localhost:5173)**.

---

## 🎨 Visual Identity & Design System
Sahaayak AI follows a **dark-first cyber-editorial aesthetic**:
- **Jet Black (`#0B0B0B`)**: Deep operational background canvas.
- **Hot Pink (`#FF2DA8`)**: Brand highlight, primary interactive actions, and live accents.
- **Chartreuse (`#D4FF3F`)**: Secondary status highlights, grounded map pins, and radar blips.
- **Concrete Grey (`#A7A7A7`)**: Muted metadata and crisp borders.
- **White (`#FFFFFF`)**: High-contrast typography with native Devanagari font rendering (English, Hindi, Marathi).

---

## 🏛️ Architecture & Key Features

1. **Google Gemini AI Engine**:
   - Uses Google GenAI SDK (`google-genai`) with models like `gemini-2.5-flash`.
   - Structured JSON output validated through Pydantic schemas.
   - Preserves raw input on provider failure with instant retryability.
   - Built-in **Deterministic Demo Adapter** for zero-credential hackathon demonstrations.

2. **Multilingual Community Intake**:
   - Native support for **English**, **हिंदी (Hindi)**, and **मराठी (Marathi)** field reports.
   - One-click presets for quick evaluation.

3. **Multi-Signal Candidate Matching & Deduplication**:
   - Clusters incoming fragmented reports by category, spatial proximity (Haversine distance), temporal window, and contextual landmark tokens.
   - Provides explainable match rationale for coordinator review.

4. **Human-in-the-Loop Safeguards**:
   - AI generates suggested links and task recommendations; authorized human coordinators confirm/reject duplicate associations and approve squad dispatches.
   - Strict rule preventing autonomous 911/emergency authority alerts.

5. **Evidence & Truth Grounding**:
   - Grounded Leaflet map only displays confirmed coordinates.
   - Claims are categorized as *Corroborating*, *Conflicting*, or *Unverified Rumors*.

6. **Immutable Audit Trail**:
   - Every report intake, match confirmation, priority override, and task transition is persisted with actor and timestamp in SQLite (`sahaayak.db`).

---

## 🧪 Testing

Run backend test suite with Pytest:
```bash
PYTHONPATH=. ./backend/venv/bin/pytest backend/tests/test_api.py -v
```

Verify frontend build:
```bash
cd frontend && npm run build
```

---

## 📂 Repository Structure

```
Sahaayak.Ai/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Endpoints: health, reports, incidents, evidence, tasks, audit, seed
│   │   ├── core/            # Config & environment settings
│   │   ├── db/              # SQLAlchemy session & Base
│   │   ├── models/          # ORM models (Report, Incident, Task, Evidence, Audit)
│   │   ├── schemas/         # Pydantic schemas & Extraction contract
│   │   ├── services/        # AI Adapter (Gemini & Demo), Matching, Prioritization, Audit
│   │   └── main.py          # FastAPI application
│   ├── tests/               # Pytest suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Navbar, GroundedMap, Status/Priority badges, MetricCards
│   │   ├── components/views/# DashboardView, ReportsView, IncidentsView, TasksView, AuditView
│   │   ├── services/        # API client
│   │   ├── types/           # TypeScript interface definitions
│   │   ├── App.tsx          # Root SPA component
│   │   └── index.css        # Cyberpunk Tailwind theme & design tokens
│   └── package.json
├── docs/
│   ├── PRD.md
│   ├── Architecture.md
│   ├── Design.md
│   ├── Rules.md
│   ├── Phases.md
│   ├── DEMO_SCRIPT.md
│   └── Memory.md
└── README.md
```
