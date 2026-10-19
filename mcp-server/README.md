# `@signaltender/mcp-server` — Official SignalTender B2B & GovCon MCP Server

Equip **Claude Desktop**, **Cursor**, **Windsurf**, **Cline**, and autonomous AI agents with **11 production B2B, GovCon & LegalTech microservices** from [SignalTender](https://signaltender.net/apis.html).

---

## Included Tools (11 Live Endpoints)

| # | MCP Tool Name | Underlying FastAPI Endpoint | What It Does |
| :--- | :--- | :--- | :--- |
| **01** | `parse_b2b_contract` | `POST /v1/parse/contract` | Extracts parties, dates, contract value, deliverables, and governing law from unstructured RFPs & SOWs. |
| **02** | `audit_contract_risks` | `POST /v1/parse/contract-risks` | Scores legal risk (`0-100`), quotes toxic clauses verbatim, and generates ready-to-paste fallback redlines. |
| **03** | `search_historical_awards` | `POST /v1/awards/search` | Queries federal contract awards, incumbent primes, and historical CLIN pricing benchmarks. |
| **04** | `get_live_solicitations` | `GET /v1/solicitations/live` | Streams live open IT, Cloud & Cybersecurity RFPs across SAM.gov, DemandStar, VA, TX, CA, FL & MD. |
| **05** | `generate_compliance_matrix` | `POST /v1/generate/compliance-matrix` | Builds a Shipley `shall`/`must` Compliance Checklist, Section L-to-M cross-reference, and Proposal Outline. |
| **06** | `scan_far_dfars_clauses` | `POST /v1/audit/far-dfars-clauses` | Detects `FAR 52.2xx` & `DFARS 252.2xx` clauses, flags mandatory flow-downs, and scores CMMC 2.0 burden. |
| **07** | `match_capability_statement` | `POST /v1/match/capability-statement` | Calculates a `0-100` Pwin (Probability of Win) score, Bid/No-Bid decision, gap analysis, and executive pitch. |
| **08** | `classify_naics_psc_nigp` | `POST /v1/classify/naics-psc-nigp` | Maps any SOW or vendor profile to 6-digit NAICS, 4-digit SIC, Federal PSC, and State NIGP/UNSPSC codes. |
| **09** | `generate_rfp_response` | `POST /v1/generate/rfp-response` | Drafts evaluator-ready Shipley Technical Proposal sections + strategic Contracting Officer Q&A questions. |
| **10** | `extract_pricing_schedule` | `POST /v1/extract/pricing-schedule` | Extracts multi-tier CLIN/SLIN schedules, GSA/T&M labor rate cards, and BOMs with line-item math audits. |
| **11** | `generate_teaming_strategy` | `POST /v1/generate/teaming-strategy` | Generates 13 CFR § 125.6 (50% Rule) workshare splits, partner archetypes, and FAR 9.6 Teaming Agreement clauses. |

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

