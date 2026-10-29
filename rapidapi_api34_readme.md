# GovCon CPARS Self-Assessment, Interim Evaluation & 14-Day Rebuttal API

Transforms **Contract Performance Metrics** (SLA attainment, CDRL on-time delivery, cost variance, key personnel stability, small business utilization) and **Assessing Official (AO) draft CPAR narratives** into a **FAR 42.1503 Table 42-1 justified CPARS Self-Assessment Package** and a formal **14-Calendar-Day Reviewing Official (RO) Rebuttal Brief**.

## Key Capabilities
- **FAR 42.1503 & Table 42-1 Executive Overview:** Evaluates rating upgrade feasibility (`Exceptional` / `Very Good`), enforces the strict **14-calendar-day statutory response rule** under FAR 42.1503(d), and defends an affirmative *"would recommend for similar requirements"* determination.
- **Factor-by-Factor FAR Table 42-1 Narratives:** Drafts quantified, non-adversarial CPARS narratives across all 5 evaluation factors (**Quality**, **Schedule**, **Cost Control**, **Management / Key Personnel**, and **Small Business Subcontracting**) explicitly satisfying the two-pronged FAR Table 42-1 test (*exceeded contractual requirements to the Government's tangible benefit* + *no major problems*).
- **14-Calendar-Day Reviewing Official Rebuttal Brief:** Audits draft CPARs for factual omissions, uncredited SLA/CDRL achievements, and excusable **Government-Furnished Equipment/Information (GFE/GFI)** delays (FAR 52.249-14), and provides the formal Reviewing Official escalation protocol.
- **COR Evidence Binder Checklist:** Lists exact supporting tabs (DD Form 250 / WAWF CDRL receipts, SIEM/CloudWatch SLA reports, bilateral schedule logs, and eSRS ISR confirmations) to attach to the CPARS submission.

## Endpoint
`POST /v1/generate/post-award-cpar-rebuttal`

### Example Request
```json
{
  "contract_metrics_and_assessing_official_text": "Contract W52P1J-24-F-0188 (PoP: Oct 1, 2025 – Sep 30, 2026). Metrics: 99.97% Cloud Enclave Uptime (PWS SLA >= 99.5%); 48 of 48 CDRLs delivered on time (100% first-time COR acceptance); automated DevSecOps pipeline cut vulnerability remediation time by 64% saving 3,200 Government labor hours; Cost Variance: 2.8% under CPFF ceiling ($410K underrun); Small Business: 28.4% SB vs. 23.0% goal. Draft AO Issue: AO assigned 'Satisfactory' citing a 3-week Milestone 2 delay caused by a Government GFE SIPRNet circuit delay documented in COR Email 2026-03-14.",
  "cpar_submission_mode": "Proactive_Annual_CPARS_Self_Assessment_And_14_Day_Rebuttal_Package",
  "target_far_42_1503_rating_goal": "Upgrade_To_Exceptional_And_Very_Good_With_Positive_Rec"
}
```

### Response Highlights
`status`, `cpar_evaluation_overview`, `far_42_1503_factor_by_factor_narratives[]`, `fourteen_day_reviewing_official_rebuttal_brief`, `cor_evidence_binder_checklist[]`.
