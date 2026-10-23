# Live Data Proof of Integration (Phase 6B)

## Executive Summary
This document provides empirical, end-to-end proof of network connectivity, authentication validation, payload retrieval, and security constraints for **Phase 6B: Live Official Data**.

- **Primary Source**: National Disaster Management Authority (NDMA) — **SACHET Portal**
- **Secondary Source**: India Meteorological Department (**IMD**)
- **Target Geographic Demo Territory**: Maharashtra / Mumbai Metropolitan Region (MMR) & Konkan Coast
- **Validation Date**: October 23, 2026

---

## 1. NDMA SACHET Live Connectivity & Retrieval Proof

### Direct HTTP Connectivity
- **Host**: `sachet.ndma.gov.in`
- **Method**: `POST`
- **Endpoint**: `https://sachet.ndma.gov.in/cap_public_website/FetchAllAlertDetails`
- **Protocol**: HTTPS (TLS 1.3)
- **Status Code**: `200 OK`
- **Response Type**: `application/json`
- **Active Real-Time Alerts Found**: **24 active alerts** across India

### Live OASIS CAP 1.2 XML Retrieval
- **Endpoint**: `GET https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=1792745162631029`
- **Status Code**: `200 OK`
- **Response Format**: Valid OASIS CAP 1.2 XML (`urn:oasis:names:tc:emergency:cap:1.2`)
- **Verified Maharashtra Alert Content**:
  ```xml
  <identifier>IN-1792745162631029_46</identifier>
  <sender>IMD-Mumbai</sender>
  <sent>2026-10-23T06:55:00+05:30</sent>
  <status>Actual</status>
  <msgType>Alert</msgType>
  <scope>Public</scope>
  <info>
    <language>en-IN</language>
    <category>Met</category>
    <event>Thunderstorm</event>
    <urgency>Expected</urgency>
    <severity>Moderate</severity>
    <certainty>Likely</certainty>
    <headline>Thunderstorm with Lightning over Kolhapur, Sindhudurg districts of Maharashtra</headline>
    <description>Moderate thunderstorm with lightning and gusty winds...</description>
    <area>
      <areaDesc>Kolhapur, Sindhudurg</areaDesc>
    </area>
  </info>
  ```
- **Persisted Test Fixture**: `backend/tests/fixtures/live_data/real_sachet_cap_1792745162631029.xml`

---

## 2. IMD API Gateway Status & Evidence

- **Base URL**: `https://api.imd.gov.in/api/v1/`
- **Connectivity Check**:
  ```bash
  curl -i https://api.imd.gov.in/api/v1/alerts
  ```
- **Observed Response**:
  - **Status Code**: `401 Unauthorized`
  - **Payload**: `{"error": "API key missing"}`
- **System Behavior Verified**:
  - When `IMD_API_KEY` is empty, `ImdApiProvider.check_status()` enters status `not_configured`.
  - When `IMD_API_KEY` is rejected, provider safely reports `blocked`.
  - Offline tests execute deterministically without leaking calls.

---

## 3. Security & Anti-Hallucination Controls

1. **Strict Host Allowlist (`ALLOWED_LIVE_HOSTS`)**:
   - Only `sachet.ndma.gov.in` and `api.imd.gov.in` are permitted.
   - Arbitrary domain fetches or HTTP schemes trigger `LiveDataSecurityError`.
2. **SSRF Guard**:
   - Blocks private RFC 1918 ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.1`), link-local metadata (`169.254.169.254`), and multicast.
3. **defusedxml Protection**:
   - All CAP 1.2 XML is parsed using `defusedxml.ElementTree` to prevent Billion Laughs entity expansion and XXE attacks.
4. **Independent Corroboration Invariance**:
   - Official alerts appear under the `OFFICIAL_CONTEXT` banner.
   - They **never** increment the incident's independent community report count, strictly preserving civil verification integrity.
5. **Clear Visual Provenance**:
   - Badges clearly differentiate `LIVE OFFICIAL`, `COMMUNITY CLAIM`, `AI ANALYSIS`, and `SYNTHETIC`.
