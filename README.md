# SignalTender — Autonomous GovCon & State SLED IT/Cybersecurity Intelligence Engine

[![Live Platform](https://img.shields.io/badge/Live_Platform-signaltender.net-0ea5e9?style=for-the-badge)](https://signaltender.net)
[![Live RFP Directory](https://img.shields.io/badge/Open_IT_%26_Cyber_RFPs-signaltender.net%2Fcontracts-10b981?style=for-the-badge)](https://signaltender.net/contracts/)
[![Enterprise API Suite](https://img.shields.io/badge/Developer_APIs_%26_MCP-signaltender.net%2Fapis.html-6366f1?style=for-the-badge)](https://signaltender.net/apis.html)
[![Remote MCP Endpoint](https://img.shields.io/badge/MCP_Streamable_HTTP-%2Fmcp-f59e0b?style=for-the-badge)](https://b2b-contract-parser-api.onrender.com/mcp)

**SignalTender** ([signaltender.net](https://signaltender.net)) continuously monitors Federal (`SAM.gov`), Municipal (`DemandStar`), and major State SLED procurement portals every 6 hours, stripping away 99.4% of facilities, construction, hardware part replacement, and sole-source noise to deliver **high-signal IT, Software Development, Cloud Infrastructure, AI/Data, and Cybersecurity RFPs** with pre-shredded Shipley capture dossiers.

---

## 1. Live Federal & State SLED IT/Cybersecurity RFP Directory

Browse live, open government IT and cybersecurity solicitations or unlock **3 pre-shredded state RFP dossiers free** at **[signaltender.net/contracts/](https://signaltender.net/contracts/)**:

- **[Federal (SAM.gov) IT & Cyber Contracts](https://signaltender.net/contracts/federal/index.html)** — DoD, Civilian, 8(a), SDVOSB, HUBZone, WOSB & SBIR/STTR solicitations
- **[Virginia (eVA) State & Municipal IT Bids](https://signaltender.net/contracts/virginia/index.html)** — VITA, agency cloud, cybersecurity & software RFPs
- **[Texas (SmartBuy ESBD / DIR) IT Solicitations](https://signaltender.net/contracts/texas/index.html)** — TX-RAMP, state agency & municipal technology procurements
- **[California (Cal eProcure) IT & Cloud RFPs](https://signaltender.net/contracts/california/index.html)** — CDT, Caltrans & state department software/cyber bids
- **[Florida (MyFloridaMarketPlace VIP) IT Solicitations](https://signaltender.net/contracts/florida/index.html)** — State ITNs, RFPs & cloud modernization bids
- **[Maryland (eMMA & Bonfire) IT & Cyber Contracts](https://signaltender.net/contracts/maryland/index.html)** — DoIT, judiciary, transit & county technology RFPs
- **[Illinois (BidBuy & Chicago) IT Contracts](https://signaltender.net/contracts/illinois/index.html)** — DoIT, CMS, CTA & municipal software/cyber solicitations
- **[Pennsylvania (DGS eMarketplace) IT Contracts](https://signaltender.net/contracts/pennsylvania/index.html)** — Commonwealth IT, SaaS, cloud & data RFPs
- **[Ohio (OhioBuys & Metro) IT Solicitations](https://signaltender.net/contracts/ohio/index.html)** — DAS, transit & municipal cybersecurity/cloud bids
- **[Georgia (GPR & Team Georgia) IT Contracts](https://signaltender.net/contracts/georgia/index.html)** — DOAS, GTA & municipal enterprise software RFPs
- **[North Carolina (NC eVP) IT & Cloud Bids](https://signaltender.net/contracts/north_carolina/index.html)** — NCDIT, university & state agency technology RFPs
- **[New York (NYC City Record Online & PASSPort) IT Bids](https://signaltender.net/contracts/new_york/index.html)** — OTI, MTA, H+H, DEP & state/city technology solicitations
- **[Massachusetts (COMMBUYS, Boston & MBTA) IT RFPs](https://signaltender.net/contracts/massachusetts/index.html)** — EOTSS, City of Boston, MBTA & Massport IT/cyber bids
- **[Municipal & County (DemandStar) IT Solicitations](https://signaltender.net/contracts/municipal/index.html)** — City, county, school district & utility technology RFPs

---

## 2. CaptureDesk Autopilot & Executive Wire Subscriptions

 Designed for 10–200 employee GovCon primes, 8(a) / SDVOSB / WOSB / HUBZone contractors, and SLED IT/MSSP capture teams who want actionable bid intelligence without `$15,000+/yr` legacy seats:

| Plan | Delivery Cadence | What You Receive | Get Started |
| :--- | :--- | :--- | :--- |
| **Tier 1 — SignalWire Pro (`$99/mo`)** | Every 6 Hours | Pre-vetted Federal & State SLED IT/Cyber leads with direct agency portal links, NAICS & SBA set-aside posture, and closing-date countdowns delivered via Discord/Webhook. | **[Activate Tier 1 &rarr;](https://signaltender.net/index.html#checkout-tier1)** |
| **Tier 2 — CaptureDesk Autopilot (`$399/mo`)** | Every 6 Hours + Full API Suite | Everything in Tier 1 **plus** automated `#capturedesk-autopilot` pre-shredded dossiers (Bid/No-Bid Pwin score, Shipley Section L/M compliance shred, FAR/DFARS/CMMC 2.0 audit, IGCE Wrap-Rate & Price-to-Win model, 13 CFR &sect; 125.6 workshare split, Key Personnel LCATs, CPARS benchmarks & GSA MAS mapping). | **[Activate Tier 2 &rarr;](https://signaltender.net/index.html#checkout-tier2)** |

---

## 3. Enterprise B2B & GovCon APIs + Model Context Protocol (`@signaltender/mcp-server`)

Every SignalTender capture engine is available as a stateless JSON microservice on **[signaltender.net/apis.html](https://signaltender.net/apis.html)** and via the **Model Context Protocol (MCP)** for Claude Desktop, Cursor, Windsurf, and autonomous GovCon agents.

### Connect via Remote Streamable-HTTP MCP (Zero Local Install)

```json
{
  "mcpServers": {
    "signaltender": {
      "url": "https://b2b-contract-parser-api.onrender.com/mcp"
    }
  }
}
```

### Or Run via Local STDIO (`npx`)

```json
{
  "mcpServers": {
    "signaltender": {
      "command": "npx",
      "args": ["-y", "@signaltender/mcp-server"],
      "env": {
        "RAPIDAPI_KEY": "YOUR_RAPIDAPI_KEY"
      }
    }
  }
}
```

### Core Capabilities Available via REST API & MCP
- **Live Federal & SLED Open IT/Cyber Solicitations Feed** (`/v1/solicitations/active`)
- **Shipley Section L/M/C RFP Shredder & Compliance Matrix Generator** (`/v1/rfp/compliance-matrix`)
- **FAR/DFARS Clause Risk, CMMC 2.0 & Flow-Down Auditor** (`/v1/govcon/clause-audit`)
- **Bid/No-Bid Pwin Scorer & Incumbent Recompete Analyzer** (`/v1/govcon/bid-no-bid-score`)
- **NAICS 2022, PSC, UNSPSC & SBA Set-Aside Classifier** (`/v1/govcon/naics-psc-classify`)
- **Shipley Proposal Section, Executive Summary & CO Q&A Drafter** (`/v1/govcon/proposal-section-draft`)
- **Section B CLIN Pricing Table & Labor Category Extractor** (`/v1/govcon/clin-pricing-extract`)
- **13 CFR &sect; 125.6 Workshare (50% Rule) & Teaming Agreement Generator** (`/v1/govcon/teaming-workshare-plan`)
- **SOC 2, FedRAMP, StateRAMP, CMMC & NIST 800-171 Security Questionnaire Auto-Responder** (`/v1/govcon/security-questionnaire-answer`)
- **Key Personnel Resume Tailor, GSA LCAT Mapper & Clearance Verifier** (`/v1/govcon/key-personnel-tailor`)
- **SF-30 RFP Amendment Diff, Section L/M Delta & Re-Work Estimator** (`/v1/govcon/amendment-diff`)
- **CPARS & Past Performance Volume III Citation Generator** (`/v1/govcon/past-performance-volume`)
- **IGCE, Wrap-Rate & Price-to-Win (PTW) Financial Modeler** (`/v1/govcon/price-to-win-model`)
- **FAR 15.102 Oral Presentation, Tech-Demo & Murder-Board Prep** (`/v1/govcon/oral-presentation-prep`)
- **NIST 800-53 Rev 5 RMF, Continuous ATO (cATO), SSP & POA&M Generator** (`/v1/govcon/ato-rmf-package`)
- **FAR 15.506 Post-Award Debriefing & GAO Bid-Protest Viability Analyzer** (`/v1/govcon/debriefing-protest-analyzer`)
- **GSA MAS Schedule SIN Mapper, 0.75% IFF Rate Card & PRC Compliance Generator** (`/v1/govcon/gsa-mas-offer-prep`)
- **B2B MSA/SOW Contract Risk Parser, Invoice Extractor & Pricing Page Intelligence** (`/v1/extract/contract`, `/v1/extract/invoice`, `/v1/extract/pricing`)

---

## Links
- **Main Platform & Free 3-RFP State Dossier Funnel:** [https://signaltender.net](https://signaltender.net)
- **Live Federal & SLED RFP Directory:** [https://signaltender.net/contracts/](https://signaltender.net/contracts/)
- **Interactive API Studio & Documentation:** [https://signaltender.net/apis.html](https://signaltender.net/apis.html)
- **Official MCP Registry ID:** `io.github.aarbchen/signaltender-mcp`

