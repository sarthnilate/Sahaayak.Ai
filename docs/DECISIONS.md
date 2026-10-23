# Sahaayak AI — Design Decisions

## D-001: Incident Close Blocked While Tasks Are Open

**Decision**: Closing an incident is **blocked** if any associated tasks have status `suggested`, `pending`, or `in_progress`.

**Rationale**: Closing an incident with open tasks would leave orphaned work items. Coordinators must explicitly complete or cancel all tasks before closing. This prevents oversight errors and ensures audit trail completeness.

**Error Code**: `OPEN_TASKS_BLOCK_CLOSE` (HTTP 400)

**Alternatives Considered**:
1. Allow close with confirmation prompt — rejected because the backend is stateless per request and cannot prompt.
2. Auto-cancel tasks on close — rejected because it removes coordinator agency over task lifecycle.

**Test Coverage**: `test_close_blocked_while_tasks_open` in `test_phase4_incidents.py`

---

## D-002: Optimistic Concurrency on Incident PATCH

**Decision**: PATCH `/incidents/{id}` accepts an optional `version` field. If provided and it doesn't match the current DB version, the request is rejected with `OPTIMISTIC_CONCURRENCY_CONFLICT` (HTTP 409).

**Rationale**: Two coordinators editing the same incident simultaneously could silently overwrite each other's changes. The version check prevents this. The version is bumped on every successful PATCH.

**Test Coverage**: `test_concurrency_conflict` in `test_phase4_incidents.py`

---

## D-003: Coordinates Require Precision and Source

**Decision**: Providing `latitude`/`longitude` on an incident requires both `location_precision` (exact|approximate|area_only) and `coordinate_source` (coordinator_pinned|simulated_seed). Auto-geocoding is explicitly forbidden.

**Rationale**: Unattributed coordinates create false precision. By requiring source attribution, the system maintains epistemic honesty about location data quality.

**Error Codes**: `COORDS_MISSING_PRECISION`, `COORDS_MISSING_SOURCE`, `COORDS_OUT_OF_RANGE`

---

## D-004: Incident Status State Machine

**Decision**: Status transitions are enforced by a single-source-of-truth state machine in `backend/app/services/incidents/__init__.py`.

**Allowed transitions**:
```
open -> investigating, mitigating, closed (with reason + no open tasks)
investigating -> mitigating, resolved, open
mitigating -> resolved, investigating
resolved -> closed, investigating
closed -> (terminal, no transitions out)
```

**Error Code**: `INVALID_STATE_TRANSITION` (HTTP 400)

---

## D-005: District/State Are Text Fields with Source Attribution

**Decision**: `district` and `state` are free-text fields (not auto-geocoded). Each has a `_source` field tracking whether the value was `reporter_stated` or `coordinator_set`. These fields support Phase 6B official alert matching by area.

---

## D-006: Create Incident from Report Is Idempotent

**Decision**: `POST /incidents/from-report` checks if an incident with `source_report_id == report_id` already exists. If so, it returns the existing incident (HTTP 200) instead of creating a duplicate. This makes the operation safe to retry.

---

## D-007: Pure, Deterministic Duplicate Matching & Bands (No Raw Probabilities)

**Decision**: The baseline duplicate matching engine (`backend/app/services/matching/engine.py`) is completely pure and deterministic with zero DB or network calls. It computes structured signals (`same_category`, `concept_overlap`, `location_overlap`, `geo_distance`, `time_window`) and returns a categorical **BAND** (`strong`, `possible`, `weak`) derived from explicit thresholds, accompanied by human-readable explanations of signals *for*, signals *against*, and *unknowns*. Raw floating-point probabilities are strictly prohibited from presentation as "truth" to coordinators.

**Rationale**: Probabilistic similarity scores mislead emergency coordinators into assuming algorithmic infallibility. Structured, inspectable evidence with explicit unknowns (e.g., "coordinates ungrounded on report") empowers human-in-the-loop decisions.

---

## D-008: Re-Suggest Suppression via Review Input Hash

**Decision**: When a coordinator rejects a suggested link between an incident and a report, the link status is set to `rejected` and a SHA-256 `review_input_hash` is computed from the report's text, extracted JSON, and location claim. On subsequent matching passes, the pair will **not** be re-suggested unless the underlying report or incident has changed (producing a different input hash).

**Rationale**: Prevents repetitive alert fatigue for coordinators while ensuring that genuine updates or corrections to a report re-trigger evaluation.

---

## D-009: Pre-Filtering Strategy for Candidate Generation ($O(N^2)$ Avoidance)

**Decision**: Candidate generation queries the DB using indexed filters: (1) incident category matching report category (unless category is "other"/"unknown"), (2) incident status not in `closed`, and (3) incident creation or update time within a bounded temporal window ($\pm 48$ hours). Only surviving candidates are passed into the pure scoring engine.

**Rationale**: An unbounded Cartesian product over all historical reports and incidents grows as $O(N^2)$. Pre-filtering ensures sub-second evaluation even across hundreds or thousands of historical records.

---

## D-010: Preserving Integrity on Confirm / Reject (No Silent Merging or Deletions)

**Decision**: Confirming a match links the report to the incident via an `IncidentReportLink` record with status `confirmed`, and sets the report status to `linked_to_incident`. The original report text, media, metadata, and extraction results remain 100% unaltered. No database records are ever deleted or merged into a single row.

**Rationale**: Legal and operational defensibility requires an immutable record of what each citizen reported and when. Incident summaries aggregate evidence without erasing individual reports.


---

## D-011: SSRF Guard — Allowlist HTTPS, Block Private & Metadata Ranges After DNS Resolution

**Decision**: Every externally-supplied URL submitted via the evidence API is validated by `ssrf_guard.py` before any HTTP fetch is attempted. Validation steps: (1) scheme must be `https`; (2) the hostname is resolved via `socket.getaddrinfo`; (3) every resolved IPv4/IPv6 address is checked against blocked CIDR ranges (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `::1/128`, `fc00::/7`); (4) a second DNS check after establishing the connection guards against rebinding attacks. The resolver is dependency-injectable for unit testing. Private/loopback/link-local/metadata IP ranges are permanently blocked regardless of the supplied hostname.

**Rationale**: Any user-controlled URL field is a vector for Server-Side Request Forgery — attackers could exfiltrate cloud instance metadata (`169.254.169.254`), scan internal services, or pivot into internal infrastructure. Defense must occur after DNS resolution, not only on the raw hostname, because DNS can map public-looking hostnames to internal IPs.

---

## D-012: Independence Grouping — Origin-Based Deduplication (Ten Forwards ≠ Ten Sources)

**Decision**: The `independence.py` service computes an `independence_group` key from each evidence item. Priority order: (1) explicit `independence_group` field; (2) `origin_group_id` on the linked report; (3) `source_fingerprint` on the linked report; (4) item's own `id`. Items sharing the same key count as **one** independent source. The independence count (displayed to coordinators) is the number of distinct keys — not the total item count.

**Rationale**: A WhatsApp broadcast forwarded to 50 residents produces 50 reports but only 1 independent piece of information. Treating forwards as independent sources would create false confidence in corroboration. Unit tests assert that 10 forwards of one message produce independence count = 1.

---

## D-013: Two Distinct Status Machines — Operational vs. Epistemic

**Decision**: Two entirely separate state machines coexist. (1) **Operational status** (`IncidentStatusEnum`: `open → investigating → mitigating → resolved → closed`) tracks response progress and is managed by coordinators. (2) **Epistemic verification status** (`EvidenceStatusEnum`: `unassessed → unverified → partially_corroborated → conflicting_evidence → corroborated → closed_after_review`) tracks what is actually known about the truth of reports. Transitions in both machines are enforced by allow-lists; invalid transitions return `INVALID_STATE_TRANSITION` error code.

**Rationale**: Conflating "we've responded to this" with "we've verified this is true" is epistemically dishonest and operationally dangerous. An incident can be `closed` (response complete) while its evidence remains `conflicting_evidence` (disputed accounts).

---

## D-014: Terminology Enforcement — No "Verified True" or "Fake"

**Decision**: The words "verified true" and "fake" are prohibited in all UI strings, code constants, test assertions, log messages, and API response values. Allowed substitutes: `corroborated by available evidence`, `partially corroborated`, `conflicting evidence`, `unverified`, `contradicts`, `supports`. Model confidence scores are never displayed as raw probabilities.

**Rationale**: In the context of disaster response, labelling information as "verified true" implies certainty that no AI or algorithmic system can guarantee. Calling reports "fake" risks defaming community members acting in good faith. Using calibrated language preserves epistemic honesty and legal defensibility.

---

## D-015: SyntheticFallbackProvider — OFF by Default, Null URLs, Visible Badge

**Decision**: The `SyntheticFallbackProvider` is inactive unless `LIVE_DATA_FALLBACK=labelled_demo` is set explicitly in the environment. When active, all generated evidence items have `source_url = None` (never fabricated), `is_simulated = True`, and carry a visible `SYNTHETIC` badge in the UI. When no live provider is configured, the API returns `verification_available=false` with an honest human-readable reason: "No live official feeds configured". The `ManualEvidenceProvider` is always active and allows coordinators to attach real evidence.

**Rationale**: Demo data that is indistinguishable from live data destroys trust. Coordinators in a real deployment must never mistake synthetic alerts for live official alerts. The labelled_demo guard and null URL rule enforce this at the system level, not as a UI convention.

