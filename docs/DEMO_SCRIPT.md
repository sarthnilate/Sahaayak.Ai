# Sahaayak AI — 5-Minute Hackathon Demo Script

## Overview
This script demonstrates the end-to-end capabilities of **Sahaayak AI ("From Chaos to Action")**, showcasing how fragmented, multilingual community reports are aggregated, structured via Google Gemini AI, matched to deduplicated incident clusters, verified against evidence, prioritized using explainable rules, and converted into human-approved emergency actions.

---

### Step 1: Open Application & Reset to Seed State (0:00 - 0:45)
1. Open the web application at `http://localhost:5173`.
2. Notice the **Cyber-Editorial Dark Design System**: Jet Black `#0B0B0B` background, Hot Pink `#FF2DA8` accents, and fluorescent Chartreuse `#D4FF3F` indicators.
3. Observe the top navigation bar:
   - Live AI Engine indicator: Shows **Google Gemini (gemini-2.5-flash)** when API key is provided, or **Deterministic Demo Adapter** with zero configuration.
   - Click the **"SEED DEMO"** button to guarantee a clean, reproducible state.
4. On the **Dashboard**, review:
   - Live Crisis Metric Cards (Active Incidents, Critical Hazards, Clustered Reports, Action Tasks).
   - The **Verification & Conflict Radar** detecting conflicting claims (e.g. social media rumors) and multi-lingual signals.

---

### Step 2: Citizen Multilingual Intake & Gemini AI Extraction (0:45 - 2:00)
1. Navigate to the **"Reports Intake"** tab.
2. Under "Fast Demo Injection Presets", click **"दादर टीटी सर्कल (Hindi)"** or **"हिंदमाता उड्डाणपूल (Marathi)"**.
3. Point out that the report is in native Devanagari script:
   - Hindi: *"दादर टीटी सर्कल और हिंदमाता के पास 3 फीट पानी भर गया है, गाड़ियां बंद पड़ गयी हैं और लोग फंसे हैं..."*
4. Click **"SUBMIT & NORMALIZE REPORT"**.
5. The backend immediately accepts and persists the raw input, runs the Google Gemini extraction pipeline, and displays:
   - Normalized Hazard Type: `waterlogging`
   - Inferred Water Depth: `90 cm`
   - Grounded Coordinates Flag: `True`
   - Affected Infrastructure & Urgent Needs (e.g., Dewatering pumps, transit diversion)
   - High Confidence Score: `94%+`
6. Click **"INSPECT EXTRACTION"** on any report to show the side-by-side comparison of raw citizen text vs Pydantic-validated JSON.
7. Point out the **"RETRY EXTRACTION"** capability: If an AI provider experiences a temporary outage, reports are never lost and can be re-run on demand.

---

### Step 3: Incident Intelligence & Grounded Leaflet Map (2:00 - 3:15)
1. Navigate to the **"Incidents & Map"** tab.
2. Explore the interactive **Grounded Map**:
   - Only confirmed, grounded geographic points are rendered on the map.
   - Ambiguous or conflicting location claims are kept in list view to prevent hallucinated coordinates.
3. Select the **"Severe Waterlogging at Hindmata Flyover & Dadar TT"** incident.
4. Explain the **Explainable AI Priority**:
   - Shows the exact rationale: *"Depth exceeds 75cm threshold; critical arterial transit route obstructed; multiple community corroborations."*
5. Demonstrate **Candidate Report Matching & Deduplication**:
   - Examine candidate links. Review the similarity score and match rationale.
   - Click **"CONFIRM MATCH"** on a suggested report. Notice how the priority dynamically recalculates and an audit event is logged.
6. Review the **Grounded Evidence Timeline**:
   - Corroborating automated sensor telemetry (`MCGM Automated Rain & Sump Gauge 04-Dadar`).
   - Refuted social media rumor (`Social Media Forward #9021`) marked as **Conflicting Evidence** based on ward engineer inspection.
7. Click **"OVERRIDE PRIORITY"**:
   - Show that overriding AI recommendations requires a mandatory coordinator justification before committing.

---

### Step 4: Coordinator Task Approval & Human-in-the-Loop Dispatch (3:15 - 4:15)
1. Navigate to the **"Tasks & Dispatch"** tab.
2. Note the safety protocol banner: AI only recommends tasks; authorized coordinators approve and dispatch squads. No autonomous 911 dispatch.
3. Locate a task with status **"SUGGESTED"** (e.g., *Distribute Sandbags to At-Risk Retailers*).
4. Select a squad from the dropdown (e.g., *Ward F-South Dewatering Squad*) and click **"APPROVE TASK"**.
5. Observe the task transition to **"PENDING"**, then click **"START EXECUTION"** (`IN_PROGRESS`), and finally **"MARK COMPLETED"**.

---

### Step 5: Audit Trail & Resilient Persistence (4:15 - 5:00)
1. Navigate to the **"Audit Trail"** tab.
2. Show the append-only immutable trace log:
   - Every report intake, AI extraction, coordinator match confirmation, priority override, and task transition is stamped with actor, timestamp, and details.
3. Refresh the browser page (`Cmd + R` or `F5`).
4. Point out that all confirmed matches, updated tasks, and new reports **persist intact** because data is stored in the persistent database, not transient local state.
