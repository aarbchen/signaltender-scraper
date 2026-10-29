# FAR 52.219-9 Subcontracting Plan & eSRS Goal Calculator API

Calculates **Small Business Subcontracting Dollar & Percentage Goals** across **SB, SDB/8(a), WOSB, SDVOSB, and HUBZone** categories (under both **% of Total Subcontracted Dollars** and **% of Total Contract Value** baselines), drafts all **15 mandatory elements of a FAR 52.219-9 Small Business Subcontracting Plan** and **DFARS 252.219-7003 Small Business Participation Commitment Document (SBPCD)**, and structures **eSRS.gov ISR/SSR** reporting and **FAR 52.219-16 Liquidated Damages** good-faith effort controls.

## Key Capabilities
- **Dual-Baseline Financial & Goal Calculator:** Computes subcontracting goals simultaneously as a percentage of Total Planned Subcontracted Spend (FAR 52.219-9 baseline) and as a percentage of Total Contract Value (DFARS 252.219-7003 DoD Source Selection Section M baseline).
- **Socioeconomic Category Goal Table:** Breaks down planned dollars, percentages, named small business partners, NAICS codes, and SBA DSBS/VetCert verification methods across SB, SDB/8(a), WOSB/EDWOSB, SDVOSB, and HUBZone.
- **15-Element FAR 52.219-9(d) Compliance Narratives:** Generates paste-ready proposal narratives covering goal methodology, principal subcontracted supplies/services, indirect cost exclusion, Small Business Liaison Officer (SBLO) duties, FAR 52.219-8 flow-downs, and Net-15 prompt payment assurances.
- **eSRS ISR/SSR Reporting & Liquidated Damages Defense:** Provides semi-annual ISR and annual SSR filing schedules plus a FAR 19.705-7 / 13 CFR § 125.3 Good-Faith Effort audit trail insulating the prime contractor from FAR 52.219-16 Liquidated Damages.

## Endpoint
`POST /v1/generate/small-business-participation`

### Example Request
```json
{
  "solicitation_subcontracting_and_clin_text": "Total 5-Year IDIQ Task Order Ceiling: $50,000,000 (Base Year $10M + Four 1-Year Options at $10M/yr). Total Planned Subcontracted Spend: $20,000,000 (40.0% of Total Contract Value). Section M Small Business Participation Factor requires >= 25% of Total Contract Value ($12.5M) or >= 62.5% of Total Subcontracted Spend awarded to Small Businesses across SDB/8(a), SDVOSB, WOSB, and HUBZone.",
  "plan_type_and_regulatory_regime": "Individual_Subcontracting_Plan_FAR_52_219_9_And_DFARS_252_219_7003",
  "agency_socioeconomic_goal_benchmarks": "DoD_23Pct_SB_5Pct_SDB_5Pct_WOSB_5Pct_SDVOSB_3Pct_HUBZone"
}
```

### Response Highlights
`status`, `subcontracting_plan_overview`, `socioeconomic_category_goal_table[]`, `far_52_219_9_15_element_compliance_narratives[]`, `esrs_isr_ssr_reporting_and_good_faith_effort_controls`, `dfars_small_business_participation_commitment_summary[]`.
