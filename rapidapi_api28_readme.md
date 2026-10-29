# DCAA Pre-Award Accounting System (SF 1408) & Indirect Rate Auditor API

Audits a government contractor's **Chart of Accounts**, **Indirect Cost Pools (Fringe, Overhead, G&A, B&P/IR&D)**, **Labor Distribution & Daily Timekeeping Policies**, and **FAR 31.205 Unallowable Cost Segregation** against the **18-point DCAA Standard Form 1408 (SF 1408) Pre-Award Accounting System Checklist**, **FAR 16.301-3**, **FAR Subpart 31.2**, and **DFARS 252.242-7006**.

## Key Capabilities
- **SF 1408 Executive Readiness Overview:** Computes a `0–100` SF 1408 compliance score, determines Cost-Reimbursable (`CPFF`/`CPIF`/`CPAF`) and `T&M` award eligibility under FAR 16.301-3(a)(3), and tallies passed criteria vs. critical deficiencies.
- **Line-by-Line SF 1408 Section II Checklist Audit:** Evaluates segregation of direct vs. indirect costs, accumulation of direct costs by contract/CLIN, logical and consistent indirect cost allocation, general ledger reconciliation, exclusion of unallowables, labor distribution, interim cost determination, and FAR 52.232-20/22 Limitation of Cost/Funds tracking.
- **Indirect Rate Pool & Allocation Base Analysis:** Audits Fringe, Overhead, G&A, and B&P/IR&D pools for causal/beneficial relationship validity under FAR 31.201-4 and CAS 418/410 (Total Labor Dollars, Direct Labor + Direct Fringe, Total Cost Input [TCI] vs. Value-Added base).
- **FAR 31.205 Unallowable Cost Segregation & Penalty Protection:** Evaluates 9000-series unallowable account setup and FAR 52.242-3 penalty exposure across Entertainment, Interest, Promotional Advertising, Alcohol, and Executive Compensation caps.
- **Labor Timekeeping & DCAA Floor-Check Controls:** Reviews daily recording, dual employee/supervisor electronic sign-offs, Total Time Accounting (TTA / uncompensated overtime under DCAA CAM 6-410), and unannounced DCAA floor-check readiness.

## Endpoint
`POST /v1/audit/dcaa-accounting-sf1408`

### Example Request
```json
{
  "chart_of_accounts_and_pools_text": "General Ledger & Chart of Accounts: 5000-series Direct Costs (5100 Direct Labor, 5200 Subcontractors, 5300 ODCs/Travel); 6000-series Fringe Pool (Payroll Taxes, 401k Match, Health Insurance, PTO — allocated on Total Labor Dollars at 29.5%); 7000-series Engineering Overhead Pool (allocated on Direct Labor + Direct Fringe at 24.0%); 8000-series G&A Pool (allocated on Total Cost Input [TCI] at 11.8%); 9000-series Unallowable Costs (9100 Interest, 9200 Entertainment, 9300 Non-Compliant Advertising). Timekeeping: Daily web timesheets with charge-code authorization, employee + supervisor electronic signoff, and audit trail.",
  "target_contract_type_and_solicitation": "Cost_Plus_Fixed_Fee_CPFF_And_T_And_M",
  "accounting_software_and_erp_stack": "QuickBooks_Online_With_GovCon_Timekeeping"
}
```

### Response Highlights
`status`, `sf1408_executive_overview`, `sf1408_18_point_checklist[]`, `indirect_rate_pool_and_base_analysis[]`, `far_31_205_unallowable_cost_segregation`, `labor_timekeeping_and_floor_check_controls`, `pre_award_survey_remediation_roadmap[]`.
