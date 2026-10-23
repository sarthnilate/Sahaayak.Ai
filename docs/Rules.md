# Sahaayak AI --- Operational Rules and Safety Boundaries

1. **Safety & Real-World Boundaries**:
   - Sahaayak AI is a demonstration and coordination decision-support tool.
   - Do NOT automatically dispatch emergency responders, send external alerts, or claim authorities were contacted.
   - All simulated data must be explicitly marked as simulated or demonstration content.
   - Never present unverified reports as verified facts.

2. **Human Authorization**:
   - Report-to-incident associations require coordinator confirmation.
   - Task approvals require coordinator action.
   - Priority overrides must require a documented rationale.

3. **Data Integrity & Evidence**:
   - Original user reports, raw text, and uploaded photos must never be overwritten or deleted during processing.
   - If AI processing fails or times out, the report must remain preserved with status `failed` or `needs_review` and be eligible for retry.
   - Never invent coordinates or external source URLs. Approximate locations must be marked as user-reported approximations.

4. **Security & Secrets**:
   - Never expose API keys (e.g., GEMINI_API_KEY) to the frontend or commit them to source control.
   - Validate and sanitize all uploads (restrict MIME types to JPEG, PNG, WebP; limit size to 10MB).
   - Use CORS allowlists and backend role-based checks.

5. **AI Provider Policy**:
   - Use Google Gemini through the server-side adapter as the primary AI engine.
   - Provide a deterministic offline demo adapter so testing and demonstrations run smoothly without internet or paid API keys.
   - Never fail silently; return transparent structured error codes.
