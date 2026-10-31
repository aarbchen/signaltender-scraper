# `@signaltender/mcp-server` — Official SignalTender B2B & GovCon MCP Server

Equip **Claude Desktop**, **Cursor**, **Windsurf**, **Cline**, and autonomous AI agents with **production B2B, GovCon & LegalTech microservices** from [SignalTender](https://signaltender.net/apis.html).

---

## Included Tools

| # | MCP Tool Name | Underlying FastAPI Endpoint | What It Does |
| :--- | :--- | :--- | :--- |
| **01** | `parse_b2b_contract` | `POST /v1/parse/contract` | Extracts parties, dates, contract value, deliverables, and governing law from unstructured RFPs & SOWs. |
| **02** | `audit_contract_risks` | `POST /v1/parse/contract-risks` | Scores legal risk (`0-100`), quotes toxic clauses verbatim, and generates ready-to-paste fallback redlines. |
| **03** | `search_historical_awards` | `POST /v1/awards/search` | Queries federal contract awards, incumbent primes, and historical CLIN pricing benchmarks. |
| **04** | `get_live_solicitations` | `GET /v1/solicitations/live` | Streams live open IT, Cloud & Cybersecurity RFPs across SAM.gov, DemandStar, All 50 U.S. States (VA, TX, CA, FL, MD, IL, PA, OH, GA, NC, NY, MA, NJ, WA, MI, CO, AZ, MN, TN, IN, MO, WI, SC, OR, CT, UT, NV, AL, LA, KY, OK, IA, KS, AR, MS, NM, NE, ID, HI, NH, ME, RI, MT, DE, SD, ND, AK, VT, WV & WY). |
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
| **40** | `audit_itar_ear_export_control` | `POST /v1/audit/itar-ear-export-control` | Classifies defense/dual-use technical deliverables against USML Categories (ITAR) and CCL ECCNs (EAR), flags DFARS 252.225-7048 export obligations, and generates a facility Technology Control Plan (TCP). |
| **41** | `generate_cdrls_did_data_deliverables` | `POST /v1/generate/cdrls-did-data-deliverables` | Extracts all Contract Data Requirements List (CDRL / DD Form 1423) items from DoD RFPs, maps Data Item Descriptions (DIDs), Block 4 authority, submission frequencies, inspection/acceptance codes, and builds a WBS Data Delivery Calendar. |
| **42** | `generate_justification_ja_sole_source` | `POST /v1/generate/justification-ja-sole-source` | Drafts a complete 12-Part FAR 6.303-2 Justification & Approval (J&A), FAR 8.405-6 Limited Sources Justification (LSJ), or FAR 16.505(b)(2) Fair Opportunity Exception package for Contracting Officers. |
| **43** | `audit_cyber_incident_dfars_7012` | `POST /v1/audit/cyber-incident-dfars-7012` | Evaluates CUI/CDI security incidents against DFARS 252.204-7012, CISA CIRCIA, and FedRAMP incident SLAs, generating a structured 72-hour DoD DIBNet ICF report, 90-day forensic media preservation checklist, and subcontractor flow-down notifications. |
| **44** | `generate_doe_national_lab_mando_subcontract` | `POST /v1/generate/doe-national-lab-mando-subcontract` | Audits DOE/NNSA Management & Operating (M&O) National Laboratory solicitations (Sandia, LANL, ORNL, LLNL) for DEAR 48 CFR 952/970 clauses, Q-Clearance / L-Clearance requirements, Foreign National Unclassified Visits (DOE O 142.3B), and patent waivers. |
| **45** | `generate_gwac_task_order_fair_opportunity` | `POST /v1/generate/gwac-task-order-fair-opportunity` | Matches task order TORFPs across OASIS+, GSA Polaris, 8(a) STARS III, VETS 2, NASA SEWP, and NITAAC CIO-SP3/4 against vendor contract pools, scoring self-scoring scorecard matrices and drafting rapid 5-day TORFP responses. |
| **46** | `audit_govt_furnished_property_gfp` | `POST /v1/audit/govt-furnished-property-gfp` | Audits GFP/GFE/GFI attachments under FAR 52.245-1 and DFARS 252.245-7003/7005, generating a DCMA-ready Property Management System Plan (PMSP), PIEE GFP Module reporting workflow, and IUID marking checklist. |
| **47** | `generate_oconus_sofa_defense_logistics` | `POST /v1/generate/oconus-sofa-defense-logistics` | Evaluates Pacific/OCONUS defense IT solicitations for Status of Forces Agreement (SOFA) TESA/TDY accreditation, FAR 52.228-3 Defense Base Act (DBA) insurance wraps, DFARS 252.225-7040 SPOT synchronization, and COLA/Post Allowance rate structures. |
| **48** | `generate_cui_marking_distribution_plan` | `POST /v1/generate/cui-marking-distribution-plan` | Analyzes deliverables against the NARA CUI Registry, 32 CFR Part 2002, and DoDI 5200.48 to generate exact CUI banner/portion markings, DoD Distribution Statements (A–F), and a CUI Sanitization & Spill Response SOP. |
| **49** | `generate_state_local_cooperative_piggyback` | `POST /v1/generate/state-local-cooperative-piggyback` | Evaluates state and municipal IT procurements to identify eligible NASPO ValuePoint, Sourcewell, OMNIA Partners, TIPS, TX DIR, and GSA Cooperative Purchasing (SIN 54151S/HACS) piggyback vehicles that bypass a 6-month competitive RFP. |
| **50** | `generate_value_engineering_vecp` | `POST /v1/generate/value-engineering-vecp` | Transforms cloud FinOps, AI automation, or architecture optimizations on an active contract into a formal FAR 52.248-1 Value Engineering Change Proposal (VECP), calculating Instant/Concurrent/Future acquisition savings and the contractor's 50%–75% shared-savings royalty. |
| **51** | `audit_organizational_ethics_far_52_203_13` | `POST /v1/audit/organizational-ethics-far-52-203-13` | Audits compliance incidents, overpayments, and hiring of former government officials against FAR 52.203-13 (Mandatory Disclosure Rule), False Claims Act (31 U.S.C. 3729), and Procurement Integrity Act (FAR 3.104), generating an Internal Control System & Post-Government Employment opinion. |
| **52** | `generate_fedramp_equivalency_body_of_evidence` | `POST /v1/generate/fedramp-equivalency-body-of-evidence` | Audits cloud service offerings against the DoD CIO FedRAMP Moderate Equivalency Memorandum (100% 3PAO assessment, zero unmitigated high/moderate POA&Ms, KSIs) and generates a complete Cloud Equivalency Body of Evidence (BoE) checklist. |
| **53** | `generate_ai_governance_nist_ai_rmf_omb_m24` | `POST /v1/generate/ai-governance-nist-ai-rmf-omb-m24` | Evaluates AI/ML/LLM solutions proposed for federal and SLED agencies against OMB Memoranda M-24-10 & M-24-18, NIST AI RMF 1.0 (Govern, Map, Measure, Manage), and DoD Responsible AI (RAI) Toolkit, outputting a Safety-Impact Classification & Model Card. |
| **54** | `generate_termination_for_convenience_settlement` | `POST /v1/generate/termination-for-convenience-settlement` | Computes recoverable sunk costs, subcontractor termination claims, settlement expenses, and profit on work performed under FAR Part 49 and FAR 52.249-2, generating an Inventory Basis (SF 1435) or Total Cost Basis (SF 1436) T4C Settlement Proposal. |
| **55** | `generate_novated_merger_change_of_name_far_42` | `POST /v1/generate/novated-merger-change-of-name-far-42` | Generates a complete FAR 42.1204 Three-Party Novation Agreement package for GovCon asset/stock acquisitions, auditing anti-assignment exceptions (41 U.S.C. 6305), SAM.gov UEI/CAGE transfer checklists, and SBA recertification triggers under 13 CFR 121.404(g). |
| **56** | `generate_section_l_m_proposal_red_team_scorer` | `POST /v1/generate/section-l-m-proposal-red-team-scorer` | Simulates a Government Source Selection Evaluation Board (SSEB) under FAR 15.305, grading a draft proposal volume against RFP Section L/M into DoD Color/Adjectival Ratings (Blue/Outstanding to Red/Unacceptable) with exact Strengths, Weaknesses, Deficiencies, and page-level rewrites. |
| **57** | `generate_gsa_tdr_quarterly_sales_iff_reconciler` | `POST /v1/generate/gsa-tdr-quarterly-sales-iff-reconciler` | Audits commercial vs. GSA Schedule invoices to separate Open-Market vs. Schedule sales, calculate quarterly 0.75% IFF remittance, validate Transactional Data Reporting (TDR) 16-field data elements, and prepare for a GSA IOA Contractor Assistance Visit (CAV). |
| **58** | `generate_award_fee_plan_incentive_maximizer` | `POST /v1/generate/award-fee-plan-incentive-maximizer` | Models CPAF, CPIF, and FPIF share-ratio curves (overrun/underrun ceiling geometry under FAR 16.401) and transforms periodic performance metrics into an Award-Fee Evaluation Board (AFEB) self-assessment presentation to maximize unearned/rollover fee pools. |

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

