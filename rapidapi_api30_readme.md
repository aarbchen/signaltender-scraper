# DCSA Facility Clearance (FCL), DD Form 254 & FOCI Mitigation Analyzer API

Audits **DD Form 254 Contract Security Classification Specifications (Blocks 10, 11, 13)**, **Standard Form 328 (SF 328 — Certificate Pertaining to Foreign Interests)**, and **corporate cap-table / offshore LP structures** against **32 CFR Part 117 (NISPOM)** and **Defense Counterintelligence and Security Agency (DCSA)** Facility Clearance (FCL) and Foreign Ownership, Control, or Influence (FOCI) mitigation standards.

## Key Capabilities
- **FCL & FOCI Executive Overview:** Evaluates Facility Clearance eligibility (`Confidential`, `Secret`, `Top Secret`, `TS/SCI`), classifies 32 CFR § 117.11 FOCI severity, and recommends the appropriate DCSA mitigation instrument.
- **DD Form 254 Block 10 & 11 Safeguarding Matrix:** Maps checked DD-254 items (`COMSEC`, `SCI`, `SIPRNet`, `CUI / NIST SP 800-171`, subcontractor flow-downs) to exact 32 CFR Part 117, ICD 705, and DCSA RMF DAAPM actions.
- **SF 328 Foreign Interest Factor Audit:** Audits Questions 1–10 of Standard Form 328 across foreign equity >= 5%, Cayman/offshore LP venture feeders, non-U.S. board seats/observers, foreign debt covenants, and foreign revenue/IP ties.
- **DCSA FOCI Mitigation Agreement Blueprint:** Structures Board Resolutions, Security Control Agreements (SCAs), Special Security Agreements (SSAs with National Interest Determinations), or Proxy/Voting Trusts with Outside Director, Electronic Communications Plan (ECP), and Technology Control Plan (TCP) controls.
- **KMP Exclusion Resolution & NISP eMASS Checklist:** Provides a step-by-step Key Management Personnel (KMP) List, Board Exclusion Resolution, DISS, and NISP eMASS submission checklist.

## Endpoint
`POST /v1/audit/foci-dd254-clearance`

### Example Request
```json
{
  "dd254_and_ownership_cap_table_text": "DD Form 254 Block 6/7: Top Secret Facility Clearance Required; Safeguarding Level: Secret. Block 10 Checked: (a) COMSEC, (e)(1) SCI, (j) CUI, (k) SIPRNet. Corporate Cap Table & SF 328 Context: Delaware C-Corp (82% U.S. citizen founders; 14% held via Cayman Islands LP feeder in Series B VC fund; 4% held by UK/NATO strategic minority investor with 1 non-voting board observer seat; zero foreign debt).",
  "target_facility_clearance_level": "Top_Secret_FCL_With_SCI_And_SIPRNet",
  "foreign_ownership_and_board_context": "Minority_Foreign_LP_Or_Board_Seat_Under_Review"
}
```

### Response Highlights
`status`, `fcl_and_foci_executive_overview`, `dd254_block10_and_11_safeguarding_matrix[]`, `sf328_foreign_interest_factor_audit[]`, `dcsa_foci_mitigation_agreement_blueprint`, `kmp_exclusion_resolution_and_nisp_emass_checklist[]`.
