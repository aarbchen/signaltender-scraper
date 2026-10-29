# GovCon Quality Assurance Surveillance Plan (QASP), PWS SLA & KPI Matrix API

Transforms **Performance Work Statement (PWS)**, **Statement of Work (SOW)**, or **Statement of Objectives (SOO)** deliverables into a **FAR Subpart 37.6 Performance-Based Acquisition (PBA) Quality Assurance Surveillance Plan (QASP)** and **Quality Control Plan (QCP)**. It outputs a **0–100 QASP Readiness Score**, a **Performance Requirements Summary (PRS) Table**, **Acceptable Quality Levels (AQLs)**, **automated SLA/KPI telemetry metrics**, **positive/negative incentive or invoice deduction formulas**, a **FAR 52.246 Non-Conformance & Corrective Action Report (CAR) workflow**, and a **ready-to-submit QASP/QCP proposal volume narrative**.

## Key Capabilities
- **FAR Subpart 37.6 Performance Requirements Summary (PRS) Matrix:** Maps every core PWS task section (`PRS-01`, `PRS-02`, ...) to an outcome-based performance objective, measurable KPI standard, Acceptable Quality Level (AQL), FAR 46.4 surveillance method (`100% Automated Telemetry Inspection`, `Periodic Sampling`, `Random Sampling`, `Validated Customer Complaint`), monitoring frequency, incentive/deduction formula, and accountable COR / Quality Assurance Manager role.
- **Contract-Type Calibrated Incentive & Deduction Formulas:** Tailors positive CPARS/Award-Fee incentives and invoice credit deduction formulas across `Firm_Fixed_Price_FFP`, `Time_and_Materials_TM`, `Cost_Plus_Award_Fee_CPAF`, `Cost_Plus_Incentive_Fee_CPIF`, and `Hybrid_IDIQ_Task_Order` structures.
- **Automated SLA & KPI Telemetry Architecture:** Defines real-time telemetry metrics, target thresholds, rolling measurement windows, authoritative systems of record (ServiceNow, Splunk, GitLab CI/CD, eMASS, CloudWatch), and COR breach escalation triggers.
- **Closed-Loop Non-Conformance, CAR & FAR 52.246 Inspection Workflow:** Specifies Level I–III Corrective Action Report (CAR) and Cure Notice thresholds (FAR 49.607), 5-Whys Root Cause Analysis (RCA) SLA hours, Corrective Action Plan (CAP) steps, and applicable FAR 52.246 inspection clauses (`FAR 52.246-4`, `FAR 52.246-5`, `FAR 52.246-6`, `FAR 52.212-4(a)`).
- **Paste-Ready Shipley QASP / QCP Proposal Volume:** Generates a complete Markdown Quality Assurance Surveillance Plan & ISO 9001 / CMMI-SVC Level 3 Quality Control narrative ready for Section L/M submission.

## Endpoint
`POST /v1/generate/quality-assurance-qasp`

### Example Request
```json
{
  "pws_or_sow_deliverables_text": "PWS Section C.3 (24x7 Zero-Trust SOC, Cloud Enclave Sustainment & Incident Response): (1) C.3.1 24x7 SOC Triage: Detect, triage, and contain Severity-1 cyber incidents within 30 minutes of SIEM alert generation with 99.95% monthly platform availability. (2) C.3.2 Continuous ATO & Vulnerability Management: Remediate 100% of Critical/CAT-I CISA KEV findings within 48 hours and High/CAT-II findings within 14 calendar days. (3) C.3.3 Key Personnel Continuity: Maintain >= 95% fill rate across 24 FTEs with <= 10 business days backfill.",
  "contract_type_and_incentive_structure": "Firm_Fixed_Price_FFP",
  "surveillance_rigor_and_mission_criticality": "Mission_Critical_24x7_Zero_Trust"
}
```

### Response Highlights
`status`, `qasp_readiness_score`, `executive_surveillance_summary`, `performance_requirements_summary_prs_table[]`, `sla_and_kpi_telemetry_metrics[]`, `non_conformance_and_cure_notice_workflow`, `ready_to_submit_qasp_narrative`.
