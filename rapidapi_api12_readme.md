# SOC 2, FedRAMP & NIST 800-171 Security Questionnaire Responder API (`POST /v1/audit/security-questionnaire`)

Automate **B2B Enterprise & Federal GovCon Security Questionnaire Responses (CAIQ, SIG, HECVAT, VSA, DD Form 254 / CUI Checklists), Multi-Framework Control Crosswalks (SOC 2 Type II, NIST SP 800-171 Rev 2/3, CMMC 2.0 Level 2, FedRAMP Rev 5, ISO 27001:2022), DoD SPRS Readiness Scoring, and Plan of Action & Milestones (POA&M) Generation** via a single stateless REST endpoint.

Built for **CISOs, GRC Engineers, B2B SaaS Sales Engineers, Defense Industrial Base (DIB) Contractors, and Procurement / Vendor Risk Management (TPRM) Platforms**.

---

## Key Capabilities

1. **CISO-Grade Security Questionnaire Responder**
   - Ingests numbered or raw security questions alongside your company's security architecture summary and drafts clear, accurate, audit-defensible narratives (`COMPLIANT`, `PARTIALLY_COMPLIANT`, `PLANNED_OR_IN_PROGRESS`, `COMPENSATING_CONTROL`, `NOT_APPLICABLE`, or `NON_COMPLIANT`) without over-promising unverified capabilities.

2. **4-Way Cross-Framework Control Mapping**
   - Automatically maps every question and response across:
     - **SOC 2 Type II** Trust Services Criteria (`CC6.1`, `CC7.2`, `A1.2`, etc.)
     - **NIST SP 800-171 Rev 2 & CMMC 2.0 Level 2** (`3.1.1`, `3.5.3`, `3.13.11`, etc.)
     - **FedRAMP / NIST SP 800-53 Rev 5** (`AC-2`, `IA-2(1)`, `SC-8`, `SC-28`, `AU-6`, etc.)
     - **ISO/IEC 27001:2022** Annex A Controls (`A.5.15`, `A.8.24`, etc.)

3. **DoD SPRS Readiness Estimation & Evidence Artifact Checklist**
   - Computes an overall compliance readiness score (`0–100`), estimates your **DoD Supplier Performance Risk System (SPRS)** score band (`-203` to `+110`), and lists the exact audit evidence artifacts (`SOC 2 Bridge Letter`, `KMS Key Rotation Policy`, `FIPS 140-3 Certificate`, `SSP Section`) needed to close buyer due diligence.

4. **Automated POA&M (Plan of Action & Milestones) Generator**
   - For any partial gap or unimplemented control, generates structured **POA&M items** with severity level, remediation milestone steps, compensating controls, and estimated completion timelines (`30/60/90 days`).

---

## Endpoint

### `POST /v1/audit/security-questionnaire`

#### Request Body (`application/json`)

```json
{
  "questionnaire_text": "1. Does your platform enforce phishing-resistant Multi-Factor Authentication (MFA) for all users accessing CUI? 2. How is customer data encrypted at rest and in transit (FIPS 140-2/140-3)? 3. Describe your SIEM audit log retention and DFARS 252.204-7012 incident reporting SLA.",
  "security_posture_summary": "AWS GovCloud & Commercial US-East, SOC 2 Type II certified, Okta FIDO2/WebAuthn MFA enforced, AES-256 KMS at rest, TLS 1.3 in transit, FIPS endpoints enabled on GovCloud ALB, Datadog SIEM 365-day retention.",
  "target_framework": "auto_detect"
}
```

---

## Stateless Zero-Retention Architecture & MCP Support
- **Stateless Processing:** All security questionnaires and architecture summaries are processed in-memory and never persisted.
- **Model Context Protocol (MCP) Ready:** Available natively in `@signaltender/mcp-server` (`respond_security_questionnaire`) and `https://b2b-contract-parser-api.onrender.com/mcp`.
