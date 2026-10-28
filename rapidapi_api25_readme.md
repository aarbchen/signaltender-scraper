# GovCon Supply Chain Risk Management (SCRM), NDAA 889, TAA & SBOM Auditor API

Audits hardware **Bills of Materials (BOMs)**, sub-tier suppliers, and **Software Bills of Materials (SBOMs)** against **NIST SP 800-161 Rev. 1 Cybersecurity Supply Chain Risk Management (C-SCRM)**, **FAR 52.204-25 (NDAA FY2019 Section 889 Part A/B)** covered telecommunications & video surveillance prohibitions (Huawei, ZTE, Hytera, Hikvision, Dahua, and their affiliates), **FAR 52.204-30 (FASCSA exclusion & removal orders)**, the **Buy American Act (FAR Part 25 / DFARS 252.225-7001)**, and the **Trade Agreements Act (FAR 52.225-5)**. It returns a submission-ready **C-SCRM Plan**, an **NTIA minimum-elements SBOM review**, a **CISA Secure Software Self-Attestation** readiness check, and a **SCRM POA&M remediation roadmap**. It covers Federal (DoD and civilian) buyers as well as State SLED buyers with prohibited-vendor and domestic-preference rules, such as Arizona ADOA-ASET.

## Key Capabilities
- **0-100 Supply Chain Risk Score & Award-Eligibility Verdict:** Gives one of four verdicts: `LOW_RISK_AWARD_ELIGIBLE`, `MODERATE_RISK_MITIGATION_PLAN_REQUIRED`, `HIGH_RISK_REMEDIATION_BEFORE_SUBMISSION`, or `PROHIBITED_NDAA_889_OR_FASCSA_BLOCKING_AWARD`.
- **Per-Line NDAA Section 889 Screening:** Checks every BOM line for covered telecommunications and video surveillance equipment. Each finding cites FAR 52.204-25(b)(1) Part A or (b)(2) Part B, flags white-label OEM and affiliate matches, and lists the required action, such as an OEM substitution, a FAR 52.204-26 representation update, or the 1-business-day FAR 52.204-25(d) report.
- **FASCSA Exclusion Check:** Screens against FAR 52.204-30 / 52.204-29 and lists the authoritative sources to verify (SAM.gov FASCSA orders and FAR 4.2303 notices).
- **TAA & Buy American Act Determinations:** Makes a per-line FAR 52.225-5 designated-country call, flags lines that need substantial-transformation analysis, and estimates cost-weighted FAR 25.101 domestic content against the 65%/75% threshold. It also applies the FAR 25.103(e) COTS IT exception.
- **NIST SP 800-161 Rev. 1 Control Gap Analysis:** Grades gaps in the SR-family controls (`SR-3`, `SR-4 Provenance`, `SR-5`, `SR-6`, `SR-11 Component Authenticity`) as CRITICAL, HIGH, MODERATE, or LOW, with concrete implementation guidance for each.
- **SBOM & CISA Secure Software Attestation Review:** Checks all 7 NTIA minimum elements in CycloneDX 1.6, SPDX 2.3, or SPDX 3.0 SBOMs. It flags CISA KEV, end-of-life, and copyleft-license components, and rates readiness to sign the CISA Secure Software Development Attestation Common Form (OMB M-22-18 / M-23-16, NIST SP 800-218 SSDF).
- **Paste-Ready C-SCRM Plan & Proposal Narrative:** Writes NIST 800-161-aligned plan sections, a prioritized SCRM POA&M, and a Supply Chain Risk Management proposal volume narrative. The narrative includes NDAA 889 / FASCSA representations and TAA/BAA certification language.

## Endpoint
`POST /v1/audit/supply-chain-scrm`

### Example Request
```json
{
  "solicitation_or_contract_context": "Arizona ADOA-ASET Statewide Network Refresh & Public Safety Video Surveillance RFP. Section H requires FAR 52.204-25 (NDAA 889) compliance for grant-funded lines, TAA designated-country end products, NIST SP 800-161 C-SCRM, and a CycloneDX SBOM.",
  "offeror_name": "Sonoran Secure Networks LLC",
  "contracting_agency": "Arizona ADOA-ASET",
  "bom_line_items": [
    {"line_item_id": "BOM-001", "part_number": "C9300-48P-E", "manufacturer": "Cisco Systems", "country_of_origin": "Mexico", "item_category": "IT_Hardware_Or_Network_Equipment", "quantity": 24, "unit_cost_usd": 6850.0},
    {"line_item_id": "BOM-002", "part_number": "DS-2CD2143G2-I", "manufacturer": "Hikvision", "country_of_origin": "China", "item_category": "Telecommunications_Or_Video_Surveillance", "quantity": 180, "unit_cost_usd": 189.0}
  ],
  "software_components": [
    {"name": "log4j-core", "version": "2.14.1", "purl": "pkg:maven/org.apache.logging.log4j/log4j-core@2.14.1", "license": "Apache-2.0", "known_vulnerabilities": ["CVE-2021-44228"]}
  ],
  "sbom_format": "CycloneDX_1_6",
  "target_compliance_regime": "Auto_Detect_From_Clauses"
}
```

### Response Highlights
`supply_chain_risk_score`, `overall_scrm_verdict`, `executive_scrm_summary`, `ndaa_889_findings[]`, `fascsa_exclusion_check`, `taa_compliance_by_line[]`, `baa_domestic_content`, `nist_800_161_control_gaps[]`, `sbom_attestation`, `c_scrm_plan_sections[]`, `remediation_roadmap[]`, `ready_to_submit_scrm_narrative`.

## Who It's For
- Value-added resellers (VARs) and IT/telecom integrators bidding hardware, video surveillance, and network refreshes on federal, DoD, and State SLED vehicles.
- Capture and contracts teams that must sign FAR 52.204-24/26 representations and TAA/BAA certifications before submission.
- Software and SaaS vendors preparing SBOM deliverables and CISA Secure Software Self-Attestation forms.

## Behavior & Limits
Every call is stateless, read-only, and non-destructive, so repeating a request is safe. A request accepts 1 to 200 BOM lines, up to 500 SBOM components, and up to 45,000 characters of solicitation context. The output is decision-support analysis. Before you sign any representation, confirm the results against SAM.gov, the FASCSA orders, and CBP final determinations.
