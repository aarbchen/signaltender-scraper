# `@signaltender/mcp-server` — Official SignalTender B2B & GovCon MCP Server

Equip **Claude Desktop**, **Cursor**, **Windsurf**, **Cline**, and autonomous AI agents with **production B2B, GovCon & LegalTech microservices** from [SignalTender](https://signaltender.net/apis.html).

---

## Included Tools

| # | MCP Tool Name | Underlying FastAPI Endpoint | What It Does |
| :--- | :--- | :--- | :--- |
| **01** | `parse_b2b_contract` | `POST /v1/parse/contract` | Extracts parties, dates, contract value, deliverables, and governing law from unstructured RFPs & SOWs. |
| **02** | `audit_contract_risks` | `POST /v1/parse/contract-risks` | Scores legal risk (`0-100`), quotes toxic clauses verbatim, and generates ready-to-paste fallback redlines. |
| **03** | `search_historical_awards` | `POST /v1/awards/search` | Queries federal contract awards, incumbent primes, and historical CLIN pricing benchmarks. |
| **04** | `get_live_solicitations` | `GET /v1/solicitations/live` | Streams live open IT, Cloud & Cybersecurity RFPs across SAM.gov, DemandStar, VA, TX, CA, FL, MD, IL, PA, OH, GA & NC. |
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

