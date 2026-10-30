# `@signaltender/mcp-server` — Official SignalTender B2B & GovCon MCP Server

Equip **Claude Desktop**, **Cursor**, **Windsurf**, **Cline**, and autonomous AI agents with **production B2B, GovCon & LegalTech microservices** from [SignalTender](https://signaltender.net/apis.html).

---

## Included Tools

| # | MCP Tool Name | Underlying FastAPI Endpoint | What It Does |
| :--- | :--- | :--- | :--- |
| **01** | `parse_b2b_contract` | `POST /v1/parse/contract` | Extracts parties, dates, contract value, deliverables, and governing law from unstructured RFPs & SOWs. |
| **02** | `audit_contract_risks` | `POST /v1/parse/contract-risks` | Scores legal risk (`0-100`), quotes toxic clauses verbatim, and generates ready-to-paste fallback redlines. |
| **03** | `search_historical_awards` | `POST /v1/awards/search` | Queries federal contract awards, incumbent primes, and historical CLIN pricing benchmarks. |
| **04** | `get_live_solicitations` | `GET /v1/solicitations/live` | Streams live open IT, Cloud & Cybersecurity RFPs across SAM.gov, DemandStar, VA, TX, CA, FL, MD, IL, PA, OH, GA, NC, NY, MA, NJ, WA, MI, CO, AZ, MN, TN, IN, MO, WI, SC, OR, CT, UT, NV, AL, LA, KY & OK. |
| **05** | `generate_compliance_matrix` | `POST /v1/generate/compliance-matrix` | Builds a Shipley `shall`/`must` Compliance Checklist, Section L-to-M cross-reference, and Proposal Outline. |
| **06** | `scan_far_dfars_clauses` | `POST /v1/audit/far-dfars-clauses` | Detects `FAR 52.2xx` & `DFARS 252.2xx` clauses, flags mandatory flow-downs, and scores CMMC 2.0 burden. |
| **07** | `match_capability_statement` | `POST /v1/match/capability-statement` | Calculates a `0-100` Pwin (Probability of Win) score, Bid/No-Bid decision, gap analysis, and executive pitch. |
| **08** | `classify_naics_psc_nigp` | `POST /v1/classify/naics-psc-nigp` | Maps any SOW or vendor profile to 6-digit NAICS, 4-digit SIC, Federal PSC, and State NIGP/UNSPSC codes. |
| **09** | `generate_rfp_response` | `POST /v1/generate/rfp-response` | Drafts evaluator-ready Shipley Technical Proposal sections + strategic Contracting Officer Q&A questions. |
| **10** | `extract_pricing_schedule` | `POST /v1/extract/pricing-schedule` | Extracts multi-tier CLIN/SLIN schedules, GSA/T&M labor rate cards, and BOMs with line-item math audits. |
| **11** | `generate_teaming_strategy` | `POST /v1/generate/teaming-strategy` | Generates 13 CFR § 125.6 (50% Rule) workshare splits, partner archetypes, and FAR 9.6 Teaming Agreement clauses. |
| **12** | `answer_security_questionnaire` | `POST /v1/audit/security-questionnaire` | Auto-answers SOC 2, FedRAMP, NIST 800-171 & CAIQ/SIG security questionnaires with control citations & POA&Ms. |
| **13** | `match_key_personnel` | `POST /v1/match/key-personnel` | Audits candidate resumes against RFP Key Personnel & GSA LCAT requirements, rewrites Shipley bios, and drafts LOCs. |
| **14** | `analyze_rfp_amendment_diff` | `POST /v1/analyze/amendment-diff` | Diffs base RFPs against SF-30 Amendments & Q&A logs to flag altered mandates, CLIN changes & invalidated proposal sections. |
| **15** | `generate_cpars_past_performance` | `POST /v1/generate/past-performance` | Transforms raw project histories into Shipley Section L/M Past Performance Volume III citations, Scope/Magnitude/Complexity matrices & CPARS narratives. |
| **16** | `generate_igce_price_to_win` | `POST /v1/generate/price-to-win` | Builds Independent Government Cost Estimates (IGCE), Indirect Wrap-Rate calculators, GSA CALC+ LCAT rate cards & Price-to-Win (PTW) sensitivity models. |
| **17** | `generate_oral_presentation_prep` | `POST /v1/generate/oral-presentation-prep` | Generates FAR 15.102 Oral Presentation slide decks, Key Personnel speaker scripts, Live Tech-Demo runbooks & SSEB Murder-Board Q&A coaching matrices. |
| **18** | `generate_ato_rmf_package` | `POST /v1/generate/ato-rmf-package` | Generates NIST 800-53 Rev 5 RMF, Continuous ATO (cATO), FIPS 199 categorization, SSP control inheritance matrices & eMASS POA&M packages. |
| **19** | `analyze_debriefing_bid_protest` | `POST /v1/generate/debriefing-bid-protest` | Analyzes Unsuccessful Offeror Notices, SSEB scorecards & Section M criteria to generate FAR 15.506 Enhanced Debriefing Q&A, CICA stay deadlines & GAO Bid-Protest grounds. |
| **20** | `generate_gsa_mas_offer` | `POST /v1/generate/gsa-mas-offer` | Maps commercial rate cards & SKUs into GSA MAS Large Category F SINs (`54151S`, `54151HACS`, `518210C`), 0.75% IFF ceiling rates, GSAR 552.238-81 PRC guardrails & SCP-FSS-001 narratives. |
| **21** | `generate_sources_sought_response` | `POST /v1/generate/sources-sought-response` | Generates FAR Part 10 Sources Sought & RFI capability matrices, FAR 19.502-2 Rule-of-Two small business set-aside justifications, NAICS/PSC sizing & Contracting Officer shaping questions. |
| **22** | `generate_oci_mitigation_plan` | `POST /v1/generate/oci-mitigation-plan` | Audits existing prime/sub awards against a new solicitation for FAR Subpart 9.5 Unequal Access, Biased Ground Rules & Impaired Objectivity and outputs an OCI Mitigation Plan & Firewall matrix. |
| **23** | `generate_sbir_sttr_commercialization` | `POST /v1/generate/sbir-sttr-commercialization` | Converts R&D specs into a DoD/AFWERX/NSF SBIR/STTR Technical Work Plan, TRL 1–9 progression matrix, Phase III Dual-Use Commercialization Plan, and DFARS 252.227-7018 SBIR Data Rights assertions. |
| **24** | `audit_section_508_vpat` | `POST /v1/audit/section-508-vpat` | Audits software/SaaS products against Revised Section 508 (36 CFR 1194), WCAG 2.2 AA, and state accessibility mandates to generate a complete VPAT 2.5 Accessibility Conformance Report (ACR) table + remediation roadmap. |
| **25** | `audit_supply_chain_scrm` | `POST /v1/audit/supply-chain-scrm` | Evaluates BOMs and sub-tier suppliers against NIST SP 800-161 C-SCRM, FAR 52.204-25 (NDAA 889), FAR 52.204-30 (FASCSA), Buy American Act (BAA), and Trade Agreements Act (TAA), outputting a C-SCRM Plan & SBOM attestation. |
| **26** | `generate_quality_assurance_qasp` | `POST /v1/generate/quality-assurance-qasp` | Extracts PWS deliverables under FAR Subpart 37.6 and generates a Performance Requirements Summary (PRS) Table, QASP, Acceptable Quality Levels (AQLs), and SLA incentive/deduction formulas. |
| **27** | `generate_phase_in_transition_plan` | `POST /v1/generate/phase-in-transition-plan` | Generates a risk-mitigated 30/60/90-Day Phase-In/Out Transition Plan with WBS milestones, EO 14055 / SCA Incumbent Right-of-First-Refusal retention scripts, clearance crossover timelines, and FAR 52.237-3 checklists. |
| **28** | `audit_dcaa_accounting_sf1408` | `POST /v1/audit/dcaa-accounting-sf1408` | Audits contractor chart of accounts, Fringe/Overhead/G&A indirect pools, timekeeping controls, and FAR 31.205 unallowables against the 18-point DCAA Standard Form 1408 (SF 1408) Pre-Award Checklist. |
| **29** | `generate_ota_white_paper` | `POST /v1/generate/ota-white-paper` | Converts commercial dual-use technology specs and DoD Problem Statements (DIU, C5ISR, SOSSEC, SpEC, MTEC, NSTXL) into a 10 U.S.C. 4022 OTA Prototype White Paper, NDC Justification, Payable Milestone Schedule, and Phase 3 Follow-On Production Strategy. |
| **30** | `audit_foci_dd254_clearance` | `POST /v1/audit/foci-dd254-clearance` | Audits DD Form 254 (Blocks 10, 11, 13), SF 328 foreign interest triggers, and corporate cap-table structures under 32 CFR Part 117 (NISPOM) and DCSA FCL / FOCI mitigation standards. |
| **31** | `generate_small_business_participation` | `POST /v1/generate/small-business-participation` | Calculates FAR 52.219-9 & DFARS 252.219-7003 Small Business Subcontracting Plan goals across SB, SDB/8(a), WOSB, SDVOSB, and HUBZone, drafts all 15 FAR 52.219-9(d) elements, and structures eSRS ISR/SSR reporting. |
| **32** | `generate_data_rights_assertion_table` | `POST /v1/generate/data-rights-assertion-table` | Generates a 4-column DFARS 252.227-7017 / FAR 52.227-14 IP & Data Rights Assertion Table, verbatim restrictive marking legends, and a 10 U.S.C. 4401 MOSA boundary protection plan. |
| **33** | `generate_capture_black_hat_review` | `POST /v1/generate/capture-black-hat-review` | Simulates competitor bidding strategies, exposes incumbent recompete vulnerabilities, and generates Shipley ethical ghosting statements, CO shaping questions, and Red Team scoring triggers. |
| **34** | `generate_post_award_cpar_rebuttal` | `POST /v1/generate/post-award-cpar-rebuttal` | Transforms contract performance metrics and draft Assessing Official CPARs into a FAR 42.1503 Table 42-1 justified Self-Assessment Package and a 14-Calendar-Day Reviewing Official Rebuttal Brief. |
| **35** | `generate_rea_equitable_adjustment` | `POST /v1/generate/rea-equitable-adjustment` | Analyzes post-award scope creep, Government delay, or stop-work orders under FAR 52.243-1/2/3 and the Contract Disputes Act (41 U.S.C. 7101) to draft a legally structured REA with quantum cost breakdown and Eichleay overhead. |
| **36** | `generate_mentor_protege_jv_agreement` | `POST /v1/generate/mentor-protege-jv-agreement` | Audits and generates SBA All-Small Mentor-Protégé (13 CFR 125.9) and Joint Venture Operating Agreements (13 CFR 125.8 / 124.513 / 128.402), validating the mandatory 40% Protégé workshare, Managing Venturer controls, and affiliation safe harbors. |
| **37** | `audit_service_contract_act_wage` | `POST /v1/audit/service-contract-act-wage` | Maps RFP labor categories to DOL SAM.gov Wage Determination (WD) occupation codes, computes Health & Welfare (H&W) fringe obligations, Vacation/Holiday accruals, EO 14026 minimum wage floors, and FAR 52.222-43 price adjustment entitlements. |
| **38** | `generate_evms_ipmdr_variance_analysis` | `POST /v1/generate/evms-ipmdr-variance-analysis` | Calculates CPI, SPI, CV, SV, TCPI, and EAC across WBS control accounts under DFARS 252.234-7002 and EIA-748, generating ready-to-submit IPMDR Format 5 Root-Cause Variance Analysis & Corrective Action narratives. |
| **39** | `generate_cost_accounting_cas_ds2` | `POST /v1/generate/cost-accounting-cas-ds2` | Determines Modified vs. Full CAS applicability ($2M trigger / $50M threshold under FAR 52.230-1..6), audits CAS 401/402/405/406/410/418 compliance, and drafts CASB DS-1 Disclosure Statement sections. |

---

## Quick Setup (Claude Desktop / Cursor / Windsurf)

1. Get your API key (free `Basic` tier available on all SignalTender APIs) from the [SignalTender RapidAPI Hub](https://rapidapi.com/user/aarbchen) or [signaltender.net/apis.html](https://signaltender.net/apis.html).
2. Add the following to your `claude_desktop_config.json` or `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "signaltender": {
      "command": "npx",
      "args": ["-y", "@signaltender/mcp-server"],
      "env": {
        "RAPIDAPI_KEY": "YOUR_RAPIDAPI_KEY_HERE"
      }
    }
  }
}
```

