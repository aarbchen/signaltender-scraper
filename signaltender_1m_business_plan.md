# SignalTender $1M ARR Autonomous DaaS Master Plan
**Operating Constraint:** `< 2 hours/week` of human oversight (100% compatible with full-time day job & academic studies)  
**Target Scale:** `$1,020,000+ ARR` (`$85,000+ MRR`)  
**Sales Motion:** `0% Synchronous` (Zero demos, zero discovery calls, zero custom enterprise retainers, zero manual onboarding)

---

## 1. Critique of the Previous AI Business Plan (Why It Would Cap Out at ~$5k–$10k MRR)

1. **The $99/mo High-Churn Treadmill:** Needing **500 active low-ticket customers** ($99–$149/mo) means fighting an 8%–12% monthly SMB churn rate. At 10% monthly churn, you must acquire **50 brand-new paying customers every single month** just to stay flat.
2. **Mispriced API Model ($0.01/call vs. Tiered Multi-API Portfolio):** Projecting **2,500,000 API calls/month at $0.01/call** on a single endpoint is unrealistic in niche B2B and destroys LLM token margins. Instead, scaling a **portfolio of 10+ specialized B2B/GovCon APIs** on `$49–$299/mo` RapidAPI subscription tiers creates compounding recurring revenue with 90%+ gross margins.
3. **Underpricing in a High-Ticket Vertical:** Legacy GovCon platforms (GovWin IQ / Deltek, HigherGov, Bloomberg Gov) charge **$12,000 to $35,000/year**. Charging $99/mo for a single global Discord channel leaves 80% of corporate-card willingness-to-pay on the table.
4. **Hidden Manual Labor:** Exporting CSVs from Apollo by hand and maintaining brittle DOM scrapers would turn into a 20-hour/week job during midterms or work sprints unless the pipeline is built on **stateless API microservices** and **autonomous outbound**.

---

## 2. The New $1M ARR Equation: Multi-API Portfolio + Self-Serve Capture Tiers

Because all of your FastAPI microservices run on **one unified Render gateway** (`b2b-contract-parser-api.onrender.com`), every new API you launch costs **$0 in extra hosting** while acting as a brand-new organic storefront on RapidAPI and MCP registries.

| Revenue Pillar | Self-Serve Product | Price Point | Target Active Volume | Monthly Recurring Revenue (MRR) | Annualized Run Rate (ARR) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1: SignalWire Pro** | Real-Time Multi-State SLED + Federal Discord/Email Alert Wire (via Stripe + Discord Bot) | **$99 / mo** *(or $990/yr)* | **180 seats** | **$17,820** | **$213,840** |
| **Tier 2: CaptureDesk Autopilot** | `#capturedesk-autopilot` + **Automated Multi-API Capture Dossiers** per RFP (via Stripe + Discord Bot) | **$399 / mo** *(or $3,490/yr)* | **85 teams** | **$33,915** | **$406,980** |
| **Tier 3: 10+ API & MCP Portfolio** | **10+ Stateless B2B/GovCon APIs** on RapidAPI (`Pro` $49, `Ultra` $149, `Mega` $299–$399) | **~$150 / mo avg** *(~23 subs per API)* | **230 API subscriptions** *(across 10+ APIs)* | **$34,500** | **$414,000** |
| **TOTAL** | **100% Self-Serve (Stripe + RapidAPI + Official MCP Registry)** | **~$198 Blended ARPU** | **495 Total Subscriptions** | **$86,235 / mo** | **$1,034,820 / yr** |

---

## 3. The 15-API Portfolio Roadmap (One FastAPI Gateway, 12+ RapidAPI Storefronts Live)

| API # | Endpoint & RapidAPI Product Name | What It Does (Stateless Input -> Output) | Target RapidAPI Buyer |
| :--- | :--- | :--- | :--- |
| **01 (Live)** | `POST /v1/parse/contract`<br>**B2B Contract Parsing API** | Converts raw RFP/SOW text into structured `ContractExtraction` JSON (budget, deadline, deliverables, clearances). | CRM & GovCon SaaS developers |
| **02 (Live)** | `POST /v1/parse/contract-risks`<br>**AI Contract Risk & Redline Auditor API** | Audits MSAs/NDAs/Subcontracts for toxic clauses and outputs verbatim quotes + ready-to-paste legal redlines. | LegalTech, CLM tools, Deal Desks |
| **03 (Live)** | `POST /v1/awards/search`<br>**Historical Procurement Pricing API** | Queries federal contract awards, prime contractor win histories, and CLIN unit pricing by NAICS/UEI/keyword. | Price-to-Win (PTW) & BI analysts |
| **04 (Live)** | `GET /v1/solicitations/live`<br>**Live SLED & Federal Open RFP Feed API** | Exposes your live, AI-vetted 9-portal Supabase `contracts` table via REST filters (`state`, `category`, `closing_after`). | AI sales agents & GovCon dashboards |
| **05 (Live)** | `POST /v1/generate/compliance-matrix`<br>**RFP Compliance Matrix & Proposal Outline API** | Takes raw RFP Section C/L/M or SOW text and outputs a Shipley-aligned **`shall`/`must` Compliance Checklist**, Section L-to-M cross-reference mapping, and hierarchical **Proposal Outline** with page allocations & win themes. | Proposal automation software & bid writers |
| **06 (Live)** | `POST /v1/audit/far-dfars-clauses`<br>**FAR / DFARS & CMMC Clause Risk Scanner API** | Detects every Federal Acquisition Regulation (`FAR 52.2xx` / `DFARS 252.2xx`) clause in a solicitation, flags flow-down mandates, and scores CMMC/FedRAMP compliance burden. | Defense contractors & compliance platforms |
| **07 (Live)** | `POST /v1/match/capability-statement`<br>**AI Bid/No-Bid & Capability Matcher API** | Accepts `(rfp_text, company_past_performance)` and outputs a **0–100 Pwin (Probability of Win) Score**, gap analysis, and tailored executive summary pitch. | GovCon capture teams & AI SDRs |
| **08 (Live)** | `POST /v1/classify/naics-psc-nigp`<br>**NAICS, SIC, PSC & UNSPSC Industry Classifier API** | Maps any product description, SOW, or company website text to exact 6-digit **NAICS**, **SIC** (for KYB/FinTech lending), Federal **PSC**, and State **NIGP/UNSPSC** codes with confidence scores & SBA size standard thresholds. | FinTech KYB, ERP, and vendor-onboarding platforms |
| **09 (Live)** | `POST /v1/generate/rfp-response`<br>**AI RFP Response & Clarification Q&A Generator API** | Drafts a Shipley-compliant **Technical Proposal Section** from company context AND generates **strategic vendor clarification Q&A** to expose ambiguous or competitor-wired specs. | Proposal teams, capture managers & AI bid platforms |
| **10 (Live)** | `POST /v1/extract/pricing-schedule`<br>**B2B Quote, Invoice & CLIN Table Extractor API** | Extracts messy multi-tier pricing tables, labor rate cards (LPTA/T&M), and BOM spreadsheets from unstructured vendor quotes into normalized JSON. | FinOps, procurement teams & ERP integrators |
| **11 (Live)** | `POST /v1/generate/teaming-strategy`<br>**GovCon Teaming Partner & Subcontracting Plan API** | Audits RFP requirements against a bidder's capability statement, calculates a legally compliant Prime/Sub workshare split under **13 CFR § 125.6 & FAR 52.219-14 (50% Rule)**, flags Ostensible Subcontractor risk, and drafts **FAR Subpart 9.6 Teaming Agreement clauses** + BD outreach emails. | GovCon capture teams, 8(a)/SDVOSB primes & teaming platforms |
| **12 (Live)** | `POST /v1/audit/security-questionnaire`<br>**SOC 2, FedRAMP & NIST 800-171 Security Questionnaire Responder API** | Maps vendor security posture to NIST 800-171 / CMMC 2.0 / FedRAMP / SIG Lite controls, calculates a **DoD SPRS Score (-203 to 110)**, and drafts audit-ready security questionnaire responses + POA&Ms. | GRC platforms, SaaS deal desks & Defense DIB vendors |
| **13 (Live)** | `POST /v1/match/key-personnel`<br>**GovCon Key Personnel & LCAT Resume Tailoring API** | Scores candidate resumes against RFP Section L/M Key Personnel & GSA Labor Category (LCAT) requirements, rewrites experience into Shipley past-performance blocks, and generates a Letter of Commitment (LOC). | GovCon staffing agencies, HRTech & proposal writers |
| **14 (Live)** | `POST /v1/analyze/amendment-diff`<br>**RFP Amendment & Q&A Change-Impact Analyzer API** | Diffs base RFP text against SF-30 Amendments & Q&A logs to flag altered `shall`/`must` mandates, deadline extensions, CLIN updates, and invalidated proposal sections. | Proposal management platforms & capture teams |
| **15 (Live)** | `POST /v1/generate/past-performance`<br>**CPARS & Past Performance Volume Generator API** | Transforms raw project histories into Shipley Section L/M Past Performance citations with Relevance ratings (`Very Relevant`), Scope/Magnitude/Complexity matrices, and CPARS-aligned narratives. | Proposal consultants, GovCon primes & bid platforms |

---

## 4. How the Flywheel Connects All 3 Tiers Automatically

```mermaid
flowchart LR
    subgraph DataLake["1. Autonomous 6-Hr Scraper Engine"]
        A["9 Live Portals<br/>(SAM, DemandStar, TX, VA, CA, FL, MD, IL, PA)"] --> B[("Supabase PostgreSQL<br/>contracts table")]
    end

    subgraph FastAPIGateway["2. Unified FastAPI Microservice Gateway (12 Live APIs + /mcp)"]
        B --> C["API 04: Live Open RFP Feed<br/>(GET /v1/solicitations/live)"]
        D["APIs 01-03 (Live):<br/>Parser • Risk Redliner • CLIN Pricing"]
        E["APIs 05-12 (Live):<br/>Compliance • FAR/DFARS • Pwin • NAICS • RFP Draft • Quote/CLIN • Teaming • SecQuest"]
    end

    subgraph RevenueStreams["3. Three Compounding Zero-Touch Revenue Streams"]
        B --> F["Tier 1: SignalWire ($99/mo | $990/yr)<br/>Stripe + Discord Bot + 72 pSEO Pages"]
        C & D & E --> G["Tier 2: CaptureDesk ($399/mo | $3,490/yr)<br/>Auto-Enriched RFP Dossiers in #capturedesk-autopilot"]
        C & D & E --> H["Tier 3: RapidAPI + Official MCP Registry ($34.5k MRR)<br/>12+ Developer Storefronts + Remote /mcp Server"]
    end
```

---

## 5. Phased Execution Plan (< 2 Hours/Week Effort)

| Phase | Timeline | Primary Milestone | Weekly Time | Target MRR |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1: Foundation, pSEO & 11-API Portfolio** | **COMPLETED** | • **DONE:** 9 State/Federal scrapers live & memory-isolated in `mainscraper.py`<br>• **DONE:** `pseo_generator.py` building static SEO pages + `sitemap.xml` (verified in Google Search Console)<br>• **DONE:** **11 Stateless FastAPI Microservices (APIs 01–11)** live on Render, verified `200 OK` on RapidAPI, with automated daily telemetry seeding (`seed_rapidapi_telemetry.py`) | **~0.5 hrs/week** | **$0 – $2,500** |
| **Phase 2: CaptureDesk Autopilot + Stripe Checkout + Cold Email** | **ENGINE BUILT (Cold Email Launching Nov)** | • **DONE:** Native on-site Stripe checkout (`#checkout-tier1` & `#checkout-tier2`) with monthly (`$99`/`$399`) and annual (`$990`/`$3,490`) plans + automated `/v1/webhooks/stripe` Discord Bot role provisioning & revocation<br>• **DONE:** `capturedesk_autopilot.py` chaining APIs internally and dispatching Tier 2 dossiers to `#capturedesk-autopilot`<br>• **NEXT (Nov):** Cold email domains finish warmup; launch `outreach_generator.py` campaigns | **~1.5 hrs/week** | **$5,000 – $25,000** |
| **Phase 3: MCP Server Registry Distribution** | **COMPLETED** | • **DONE:** Built `@signaltender/mcp-server` (both local stdio and 24/7 remote Streamable HTTP at `https://b2b-contract-parser-api.onrender.com/mcp`)<br>• **DONE:** Submitted to Glama.ai and published (`status: active`) on the **Official MCP Registry (`io.github.aarbchen/signaltender-mcp`)** | **~0.5 hrs/week** | **$25,000 – $50,000** |
| **Phase 4: Compounding Scale & Expansion** | **Months 6 – 18** | • Scale cold outbound volume + organic pSEO/RapidAPI/MCP traffic + additional SLED state portals & vertical APIs (APIs 12–15) | **< 1 hr/week** | **$86,000+ ($1M+ ARR)** |


- **API #17 (Live):** GovCon Oral Presentation, Tech-Demo & Murder-Board Prep API (`POST /v1/generate/oral-presentation-prep`) + Portal #10 Ohio Buys (`oh_scraper.py`).
- **API #18 (Live):** GovCon RMF, Continuous ATO (cATO), SSP & POA&M Generator API (`POST /v1/generate/ato-rmf-package`) + Portal #11 Georgia Procurement Registry (`ga_scraper.py`).
