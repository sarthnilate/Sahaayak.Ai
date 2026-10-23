# Live Data Blockers & Upstream Access Notes (Phase 6B)

## 1. India Meteorological Department (IMD) API Access

- **Endpoint**: `https://api.imd.gov.in/api/v1/`
- **Issue**: Requires registration and approval via the IMD Onboarding Portal (`https://api.imd.gov.in/`).
- **Access Restrictions**:
  1. Requests without `X-API-KEY` return `HTTP 401 Unauthorized` with `{"error": "API key missing"}`.
  2. Gateway registration requires government / verified disaster response institutional credentials and a captcha challenge.
- **Sahaayak AI Safe Handling**:
  - `ImdApiProvider` implements a zero-crash fallback.
  - If `IMD_API_KEY` is absent from `.env`, the source gracefully presents `not_configured` in the UI and health logs with remediation instructions.
  - When keys are supplied, queries are automatically guarded by the SSRF allowlist and timeout rules.

---

## 2. NDMA SACHET Polygon Feed Endpoint (FetchPolygonXMLFile)

- **Endpoint**: `https://sachet.ndma.gov.in/cap_public_website/FetchPolygonXMLFile`
- **Issue**: Returns `HTTP 403 Forbidden` for public unauthenticated consumer requests.
- **Mitigation**:
  - The alert index (`FetchAllAlertDetails`) and CAP XML document (`FetchXMLFile?identifier=...`) are fully accessible publicly (`HTTP 200`).
  - Spatial applicability therefore uses the official CAP `<areaDesc>` textual district boundaries and circle centroid coordinates instead of raw ESRI boundary shapes.
  - The deterministic `check_alert_applicability` engine ensures zero false-positive associations.
