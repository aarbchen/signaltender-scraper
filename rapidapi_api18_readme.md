# GovCon RMF, Continuous ATO (cATO), SSP & POA&M Generator API

Transform raw RFP cybersecurity sections (`Section C`, `Section H`, `Section L/M`) and cloud architecture notes into a complete **DoD RMF / FedRAMP / StateRAMP Authority to Operate (ATO) & Continuous ATO (cATO) Readiness Package**, including **FIPS 199 / DISA Impact Level (IL2–IL6) boundary classification**, tailored **NIST SP 800-53 Rev 5 / NIST 800-171 System Security Plan (SSP) control implementation narratives**, an **automated DevSecOps cATO pipeline blueprint (OSCAL, CycloneDX SBOM, DISA STIGs)**, a **Plan of Action & Milestones (POA&M) remediation schedule**, and a copy-pasteable **Proposal Technical Volume ATO Approach narrative**.

---

## Why GovCon Capture, DevSecOps & ISSO Teams Use This API

Nearly every Federal (`DoD RMF / eMASS`, `DHS`, `VA`, `HHS`, `CMS`) and State SLED (`StateRAMP`, `TX-RAMP`, `Virginia VITA SEC-530`, `Ohio ITP-B.1`) cloud or software RFP requires offerors to prove how they will achieve **Authority to Operate (ATO)** within 45–90 days without delaying mission cutover. Information System Security Officers (ISSOs) and RMF consultants charge **$250–$350/hour** to draft SSP control narratives and POA&M schedules.

This stateless microservice generates the complete ATO / cATO proposal & onboarding package in seconds:

1. **FIPS 199 & DISA Impact Level Boundary Summary:** Classifies Confidentiality/Integrity/Availability (`HIGH / HIGH / MODERATE`), identifies the Authorizing Official system of record (`eMASS`, `Xacta 360`, `FedRAMP PMO`, `StateRAMP PMO`), and calculates inherited Cloud Service Provider (CSP) control percentages (`AWS GovCloud`, `Azure Government`, `Google Public Sector`).
2. **Tailored NIST SP 800-53 Rev 5 SSP Control Narratives:** Generates audit-ready control implementation statements across critical families (`AC-2`, `IA-2(1)`, `SC-8`, `SC-13`, `SC-28`, `AU-6`, `CM-6`, `SI-2`) with inheritance status (`Inherited`, `Hybrid`, `Customer-Implemented`) and exact SCA/C3PAO assessment evidence artifacts.
3. **Continuous ATO (cATO) DevSecOps Pipeline Blueprint:** Details automated CI/CD security gates (Iron Bank base containers, DISA STIG Ansible hardening, SAST/DAST, Trivy/Twistlock container scanning, CycloneDX SBOM generation, and machine-readable OSCAL SSP export).
4. **POA&M Remediation Schedule (`CAT I / CAT II / CAT III`):** Turns known architecture gaps into a compliant Plan of Action & Milestones with compensating controls and milestone completion days.
5. **6-Step RMF Milestone Schedule (`Step 1 Categorize` &rarr; `Step 6 Authorize`):** Maps exact day-by-day deliverables (`IATT`, `SAR`, `RAR`, `ATO Decision Letter`) to your target timeline (`e.g., 90 days`).

---

## Endpoint Summary

- **Method:** `POST`
- **Path:** `/v1/generate/ato-rmf-package`
- **Content-Type:** `application/json`

### Request Body Parameters

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `rfp_security_and_ato_requirements` | `string` | **Yes** | Raw text from RFP Section C/H/L/M detailing RMF, ATO, cATO, FedRAMP, StateRAMP, DISA IL4/IL5, or CMMC Level 2 mandates. |
| `system_architecture_and_boundary_context` | `string` | **Yes** | Description of your cloud hosting boundary, ICAM/MFA, encryption, SIEM logging, DevSecOps toolchain, and any known gaps. |
| `target_authorization_framework` | `string` | No | One of `dod_rmf_il4_il5_cato` (default), `fedramp_high_or_moderate`, `stateramp_or_state_cloud_sec`, or `cmmc_level_2_nist_800_171`. |
| `target_ato_timeline_days` | `integer` | No | Target calendar days from award to full ATO (default `90`, range `14..365`). |

---

## Example cURL Request

```bash
curl --request POST \
  --url 'https://govcon-rmf-continuous-ato-cato-ssp-poa-m-generator-api.p.rapidapi.com/v1/generate/ato-rmf-package' \
  --header 'Content-Type: application/json' \
  --header 'X-RapidAPI-Host: govcon-rmf-continuous-ato-cato-ssp-poa-m-generator-api.p.rapidapi.com' \
  --header 'X-RapidAPI-Key: YOUR_RAPIDAPI_KEY' \
  --data '{
    "rfp_security_and_ato_requirements": "SOLICITATION FA8732-26-R-0088: Contractor shall achieve IATT within 45 days and full DoD RMF Step 6 ATO in eMASS at DISA IL5 / FedRAMP High within 90 days. Deliver NIST SP 800-53 Rev 5 SSP, automated cATO DevSecOps pipeline with OSCAL/SBOM, and POA&M.",
    "system_architecture_and_boundary_context": "AWS GovCloud (US) FedRAMP High/IL5 inherited IaaS, EKS with DISA STIGs & Iron Bank images, Okta CAC/PIV FIDO2 MFA, AWS KMS FIPS 140-3 AES-256, Splunk Cloud SIEM. Gap: legacy reporting service uses TLS 1.2 non-FIPS OpenSSL scheduled for replacement in Sprint 2.",
    "target_authorization_framework": "dod_rmf_il4_il5_cato",
    "target_ato_timeline_days": 90
  }'
```

---

## Model Context Protocol (MCP) Integration

This API is natively available as the `generate_ato_rmf_package` tool in **`@signaltender/mcp-server`** (`io.github.aarbchen/signaltender-mcp`) and our remote Streamable-HTTP MCP server (`https://b2b-contract-parser-api.onrender.com/mcp`) for Claude Desktop, Cursor, Windsurf, and autonomous GovCon agents.

