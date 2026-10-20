# RFP Amendment & Q&A Change-Impact Analyzer API (`POST /v1/analyze/amendment-diff`)

**Automate SF-30 Solicitation Amendment Diffing, Government Q&A De-Facto Requirement Detection, FAR 15.206 Acknowledgment Auditing, and Proposal Section Redrafting in a Single API Call.**

When bidding on Federal (`SAM.gov`, DoD, GSA) or State/Local SLED (`eVA`, `ESBD`, `Cal eProcure`, `MFMP`, `EMMA`, `DemandStar`) contracts, agencies routinely drop **SF-30 Solicitation Amendments (Mod 0001, 0002...)** and **100+ row Vendor Q&A Clarification Matrices** days before proposals are due. Missing a single buried Q&A ruling that alters a `shall` requirement, changes a CLIN from FFP to T&M, or shifts page limits causes **immediate technical non-compliance or FAR 15.206 rejection**.

The **RFP Amendment & Q&A Change-Impact Analyzer API** takes your base RFP/SOW text, the raw SF-30 Amendment / Government Q&A text, and your current proposal outline, and returns a strictly validated JSON impact audit.

---

## Key Capabilities

1. **Executive Amendment Impact & Rework Score (`amendment_impact_summary`):**
   - Calculates a `0–100` **Rework Risk Score** (`rework_risk_score`) and overall severity (`CRITICAL_REWRITE_REQUIRED`, `HIGH_SCOPE_OR_PRICING_SHIFT`, `MODERATE_COMPLIANCE_UPDATE`, `ADMINISTRATIVE_ONLY`).
   - Extracts original vs. extended proposal submission deadlines (`original_submission_deadline` -> `updated_submission_deadline`).
   - Generates mandatory **FAR 15.206 SF-30 Acknowledgment Instructions** (`sf30_acknowledgment_instruction`, e.g., signing Blocks 15A–15C on Standard Form 30) so your bid is never rejected on administrative grounds.
2. **Requirement, CLIN & Formatting Delta Matrix (`requirement_and_clin_deltas`):**
   - Pinpoints every modified `shall`/`must` obligation (`MODIFIED_SHALL_MANDATE`), newly added requirement (`ADDED_REQUIREMENT`), relaxed spec (`DELETED_OR_RELAXED_REQUIREMENT`), pricing model or ceiling shift (`CLIN_OR_PRICING_CHANGE`), page limit change (`PAGE_LIMIT_OR_FORMAT_CHANGE`), or Section M weight change (`EVALUATION_CRITERIA_SHIFT`).
   - Pairs `original_baseline_text` against `amended_requirement_text` with a concrete `proposal_action_required` directive.
3. **Government Q&A Clarification & De-Facto Requirement Detector (`qa_clarification_rulings`):**
   - Parses Q&A logs to flag when an official Government answer introduces a **hidden de-facto requirement** (`creates_de_facto_requirement: true`) or relaxes a restrictive specification (e.g., security clearance or LCAT degree substitution).
4. **Invalidated Proposal Section Redrafter (`invalidated_proposal_sections`):**
   - Cross-references the amendment deltas against your `current_proposal_outline`, flags which sections of your draft are now obsolete, and writes **ready-to-paste Shipley replacement paragraphs** (`recommended_redraft_text`).

---

## Endpoint & Request Schema

- **Method:** `POST`
- **Path:** `/v1/analyze/amendment-diff`
- **Content-Type:** `application/json`

### Request Body (`AmendmentDiffRequest`)

```json
{
  "base_solicitation_text": "RFP FA8732-26-R-0018 (Base Solicitation): Section L.4: Proposals are due November 10, 2026 at 14:00 EST. Volume I Technical Approach shall not exceed 25 pages. Section C.3.1: The Contractor shall deploy a FedRAMP Moderate cloud data platform supporting 5,000 concurrent users. Section C.4.2: Key Personnel Lead Cloud Architect must hold an active Top Secret clearance and AWS Solutions Architect Professional certification. Section B CLIN 0001: Base Year Cloud Migration Engineering (Firm-Fixed-Price).",
  "amendment_or_qa_text": "SF-30 AMENDMENT 0002 (Issued Oct 20, 2026): 1. Block 11: The proposal due date is hereby extended from November 10, 2026 to November 24, 2026 at 17:00 EST. 2. Section L.4 is revised to increase Volume I Technical Approach page limit from 25 pages to 35 pages. 3. Section C.3.1 is replaced in its entirety: The Contractor shall deploy a FedRAMP High and DoD IL5 authorized cloud data platform supporting 15,000 concurrent users with zero-trust microsegmentation. 4. Section B CLIN 0001 is converted from Firm-Fixed-Price (FFP) to Time-and-Materials (T&M) with a Not-to-Exceed (NTE) ceiling of $4,200,000. GOVERNMENT Q&A LOG — Q12: Will the Government accept a Secret clearance with an active Top Secret sponsorship for the Lead Cloud Architect? Answer Q12: Yes, an active Secret clearance with Top Secret adjudication in progress is acceptable at proposal submission. Q19: Does the Government require native SIEM telemetry forwarding into the agency's Splunk Cloud instance? Answer Q19: Yes, real-time STIG-compliant log forwarding to the agency Splunk Cloud environment is mandatory under Section C.3.1.",
  "current_proposal_outline": "Volume I Technical (25 pages max): Sec 1.0 Executive Summary; Sec 2.0 FedRAMP Moderate Architecture (5,000 users); Sec 3.0 Key Personnel (Top Secret required at submission); Volume III Pricing: CLIN 0001 FFP Milestone Schedule."
}
```

---

## Sample Response (`200 OK`)

```json
{
  "amendment_impact_summary": {
    "solicitation_and_amendment_id": "RFP FA8732-26-R-0018 — SF-30 Amendment 0002 & Q&A Log",
    "overall_change_severity": "CRITICAL_REWRITE_REQUIRED",
    "rework_risk_score": 82,
    "original_submission_deadline": "2026-11-10T14:00:00-05:00",
    "updated_submission_deadline": "2026-11-24T17:00:00-05:00",
    "sf30_acknowledgment_instruction": "Sign SF-30 Amendment 0002 Blocks 15A–15C and include signed copy in Volume I Cover Transmittal prior to Nov 24, 2026 at 17:00 EST.",
    "executive_delta_summary": "Amendment 0002 elevates security authorization from FedRAMP Moderate to FedRAMP High / DoD IL5 (3x user concurrency to 15,000), converts CLIN 0001 from FFP to T&M ($4.2M NTE), increases Volume I page limit from 25 to 35 pages, and relaxes Lead Cloud Architect clearance to Secret w/ TS in-progress via Q&A #12."
  },
  "requirement_and_clin_deltas": [
    {
      "delta_id": "DELTA-001",
      "change_type": "MODIFIED_SHALL_MANDATE",
      "severity": "CRITICAL",
      "affected_rfp_section": "Section C.3.1",
      "original_baseline_text": "Deploy a FedRAMP Moderate cloud data platform supporting 5,000 concurrent users.",
      "amended_requirement_text": "Deploy a FedRAMP High and DoD IL5 authorized cloud data platform supporting 15,000 concurrent users with zero-trust microsegmentation.",
      "proposal_action_required": "Replace FedRAMP Moderate diagrams in Vol I Sec 2.0 with AWS GovCloud (US) DoD IL5 / FedRAMP High boundary diagrams and scale load benchmarks to 15,000 concurrent users."
    }
  ],
  "qa_clarification_rulings": [
    {
      "qa_reference_id": "Q19",
      "vendor_question_summary": "Does the Government require native SIEM telemetry forwarding into the agency's Splunk Cloud instance?",
      "government_official_answer": "Yes, real-time STIG-compliant log forwarding to the agency Splunk Cloud environment is mandatory under Section C.3.1.",
      "creates_de_facto_requirement": true,
      "competitive_and_solution_impact": "Creates a binding integration requirement; add a dedicated Splunk HEC / STIG telemetry pipeline subsection to Volume I Section 2.0."
    }
  ],
  "invalidated_proposal_sections": [
    {
      "proposal_section_ref": "Volume I, Section 2.0: FedRAMP Moderate Architecture (5,000 Users)",
      "invalidation_reason": "Amendment 0002 elevated the authorization boundary to FedRAMP High / DoD IL5 and tripled concurrency to 15,000 users while Q19 mandated Splunk Cloud STIG telemetry forwarding.",
      "recommended_redraft_text": "Our Cloud Data Platform operates within an inherited FedRAMP High and DoD SRG IL5 enclave engineered to sustain 15,000+ concurrent users with zero-trust microsegmentation and native STIG-validated telemetry streaming into the agency's Splunk Cloud instance."
    }
  ]
}
```

---

## Model Context Protocol (MCP) Integration

This endpoint is natively exposed as the `analyze_rfp_amendment_diff` tool in the official SignalTender MCP server (`@signaltender/mcp-server` and `https://b2b-contract-parser-api.onrender.com/mcp`) for Claude Desktop, Cursor, Windsurf, and autonomous GovCon capture agents.

