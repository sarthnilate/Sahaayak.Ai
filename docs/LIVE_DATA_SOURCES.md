# Official Live Data Sources Specification & Verification Record

**Document Version**: 1.0.0 (Phase 6B Research)  
**Verification Date**: 2026-10-23 14:57 IST  
**Environment**: Local Developer Environment (Internet Egress Verified)  

---

## 1. Official Source Verification Matrix

| Source Name | Official URL / Base URL | Access Mechanism & Auth | Rate Limits & Terms | Data Format | Verification Status & Timestamp |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **NDMA SACHET (Alert Index)** | `https://sachet.ndma.gov.in/cap_public_website/FetchAllAlertDetails` | HTTP POST/GET (Open Public). No API key required. | Official public disaster portal; max recommended polling interval: 5–15 mins. | JSON array of active CAP alert references. | **VERIFIED BY CALLING**<br>Date: 2026-10-23 14:47 IST<br>Status: `200 OK`<br>Content-Type: `application/json;charset=UTF-8`<br>Payload: 24 active alerts returned. |
| **NDMA SACHET (CAP 1.2 XML per Item)** | `https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier={identifier}` | HTTP GET per alert item identifier. No API key required. | OASIS CAP 1.2 Standard compliance. Subject to IP throttling if flooded. | XML (OASIS Common Alerting Protocol v1.2, namespace `urn:oasis:names:tc:emergency:cap:1.2`). | **VERIFIED BY CALLING**<br>Date: 2026-10-23 14:56 IST<br>Status: `200 OK`<br>Content-Type: `text/xml;charset=UTF-8`<br>Tested Identifier: `1792745162631029` (IMD Mumbai Kolhapur/Sindhudurg alert). |
| **NDMA SACHET (Polygon XML)** | `https://sachet.ndma.gov.in/cap_public_website/FetchPolygonXMLFile?identifier={identifier}` | HTTP GET with alert identifier. | Restricted to authorized agency IPs or CORS origin. | XML polygon coordinates. | **VERIFIED BY CALLING**<br>Date: 2026-10-23 14:57 IST<br>Status: `403 Forbidden` (Restricted).<br>Fallback to alert centroid / district LGD matching. |
| **IMD API Gateway (Current Wx & Warnings)** | `https://api.imd.gov.in/api/v1/` (`districtwarning`, `districtnowcast`, `current_wx`) | HTTP GET with `X-Api-Key` or token header. Requires formal registration on `register.php`. | Restricted; requires verified government/agency account approval. Rate limited per key. | JSON | **VERIFIED BY CALLING**<br>Date: 2026-10-23 14:55 IST<br>Status: `401 Unauthorized`<br>Response: `{"error":"API key missing"}`<br>Docs at `https://api.imd.gov.in/public/api_reference.html`. |
| **NDMA SACHET Web RSS Feed (UI Header)** | `https://sachet.ndma.gov.in/CapFeed` | Next.js SPA interface displaying integration guide. | Direct static RSS index URL is not published; portal delegates to `/cap_public_website/FetchAllAlertDetails`. | HTML / PDF (`/docs/Integration_Guide_For_Agencies.pdf`). | **VERIFIED BY CALLING**<br>Date: 2026-10-23 14:56 IST<br>Status: `200 OK`. PDF guide explicitly directs agencies to `FetchXMLFile`. |

---

## 2. Real Live Payload Sample (Verified CAP 1.2 XML)

Retrieved live from `https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=1792745162631029` on 2026-10-23:

```xml
<cap:alert xmlns:cap="urn:oasis:names:tc:emergency:cap:1.2">
  <cap:identifier>IN-1792745162631029_46</cap:identifier>
  <cap:sender>IMD-Mumbai</cap:sender>
  <cap:sent>2026-10-23T14:15:33+05:30</cap:sent>
  <cap:status>Actual</cap:status>
  <cap:msgType>Alert</cap:msgType>
  <cap:scope>Public</cap:scope>
  <cap:info>
    <cap:language>en-IN</cap:language>
    <cap:category>Met</cap:category>
    <cap:event>Thunderstorm with Lightning</cap:event>
    <cap:urgency>Expected</cap:urgency>
    <cap:severity>Moderate</cap:severity>
    <cap:certainty>Likely</cap:certainty>
    <cap:effective>2026-10-23T14:14:00+05:30</cap:effective>
    <cap:onset>2026-10-23T14:16:02+05:30</cap:onset>
    <cap:expires>2026-10-23T17:14:00+05:30</cap:expires>
    <cap:headline>Thunderstorm with Lightning , light to moderate spell of rain , gusty winds reaching 30 -40 kmph is very likely to occur at isolated places over Kolhapur, Sindhudurg in next 3 hours.</cap:headline>
    <cap:instruction>Please follow SDMA guidelines.</cap:instruction>
    <cap:area>
      <cap:areaDesc>Kolhapur, Sindhudurg districts of Maharashtra</cap:areaDesc>
      <cap:geocode>
        <cap:valueName>LGD District Code</cap:valueName>
        <cap:value>480</cap:value>
      </cap:geocode>
      <cap:geocode>
        <cap:valueName>LGD District Code</cap:valueName>
        <cap:value>495</cap:value>
      </cap:geocode>
    </cap:area>
  </cap:info>
</cap:alert>
```

---

## 3. Implementation Plan & Provider Architecture

1. **`SachetCapProvider` (Primary Live Provider)**:
   - Polls `https://sachet.ndma.gov.in/cap_public_website/FetchAllAlertDetails` (cached according to `LIVE_REFRESH_MINUTES`).
   - For newly discovered alert identifiers, fetches CAP 1.2 XML from `https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier={identifier}`.
   - Parses XML with `defusedxml` to block all XXE / Billion Laughs attacks.
   - Extracts OASIS CAP fields, LGD district codes, language variants (en/hi/mr/te), severity, validity window, and centroid coordinates.

2. **`ImdApiProvider` (Secondary Provider)**:
   - Evaluates `IMD_API_KEY` configuration.
   - If key is missing or calls return `401 Unauthorized`, gracefully reports status as `not_configured` or `blocked` with explicit user-facing explanation in accordance with Phase 6B requirements.

3. **Grounded Applicability Matching**:
   - Matches district/state text against incident location claims.
   - Stamped as `area_match`, `possibly_applicable`, `different_area`, or `unknown`.
   - Injected into incident official context strictly as regional background advisory with disclaimer: *"Official advisory for <area>, valid <from>-<until>. This is regional context and does not by itself confirm this incident."*
