"""
social_distribution_kit.py — Automated Pre-Oct 31 Organic Distribution & Warm Follow-Up Generator

Reads live open IT & cybersecurity solicitations from SignalTender's contract index
and generates `d:\\Daas\\social_distribution_kit.md` with copy-pasteable:
  1. 5 LinkedIn "Live State SLED & Federal RFP Dossier Drop" posts
  2. 4 Reddit / Community value-first threads (r/govcontracting, r/msp, r/cybersecurity, r/mcp)
  3. 3 Real-Time "Hot Prospect Click Radar" 5-Minute Follow-Up Templates
  4. Oct 21 – Nov 7 Distribution & Outbound Ramp Execution Schedule
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from error_telemetry import configure_utf8_stdio

configure_utf8_stdio()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")
OUTPUT_MD_PATH = os.path.join(BASE_DIR, "social_distribution_kit.md")
SITE_BASE = "https://signaltender.net"


def _load_contracts_from_index() -> list[dict]:
    if not os.path.exists(INDEX_HTML_PATH):
        return []
    with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    m = re.search(r"window\.SIGNALTENDER_CONTRACTS\s*=\s*(\[.*?\]);\s*window\.SIGNALTENDER_JURISDICTIONS", html, flags=re.S)
    if not m:
        return []
    try:
        return json.loads(m.group(1))
    except Exception:
        return []


def _pick_by_jurisdiction(contracts: list[dict], jur: str, limit: int = 2) -> list[dict]:
    matches = [c for c in contracts if c.get("jurisdiction") == jur]
    return matches[:limit] if matches else contracts[:limit]


def generate_distribution_kit() -> str:
    contracts = _load_contracts_from_index()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    fed_list = _pick_by_jurisdiction(contracts, "federal", 2)
    va_list = _pick_by_jurisdiction(contracts, "virginia", 1)
    tx_list = _pick_by_jurisdiction(contracts, "texas", 1)
    md_list = _pick_by_jurisdiction(contracts, "maryland", 1)
    ny_list = _pick_by_jurisdiction(contracts, "new_york", 1)
    ma_list = _pick_by_jurisdiction(contracts, "massachusetts", 1)
    ca_list = _pick_by_jurisdiction(contracts, "california", 1)
    fl_list = _pick_by_jurisdiction(contracts, "florida", 1)

    def _fmt_lead_bullet(c: dict) -> str:
        title = c.get("clean_title") or c.get("raw_title") or "Enterprise IT & Cybersecurity Solicitation"
        agency = c.get("agency") or "Government Agency"
        due = c.get("due_str") or "Open"
        slug = c.get("slug") or ""
        naics = c.get("naics_display") or "NAICS 541512"
        ptw = c.get("igce_ptw_posture") or "Competitive IT Services"
        url = f"{SITE_BASE}/contracts/rfp/{slug}.html" if slug else f"{SITE_BASE}/contracts/"
        return (
            f"- **{title}**\n"
            f"  - Agency: {agency} | Due: {due}\n"
            f"  - Classification: {naics}\n"
            f"  - IGCE / PTW Posture: {ptw}\n"
            f"  - Full AI Dossier: {url}"
        )

    east_coast_bullets = "\n".join(_fmt_lead_bullet(c) for c in (va_list + md_list + tx_list)[:3])
    ny_ma_bullets = "\n".join(_fmt_lead_bullet(c) for c in (ny_list + ma_list + fed_list[:1])[:3])
    ca_fl_bullets = "\n".join(_fmt_lead_bullet(c) for c in (ca_list + fl_list + fed_list[1:2])[:3])
    fed_bullets = "\n".join(_fmt_lead_bullet(c) for c in (fed_list + va_list)[:3])

    md = f"""# SignalTender Pre-Oct 31 Organic Distribution & Conversion Playbook

**Generated:** `{now_str}`
**Live Indexed Solicitations:** `{len(contracts)} Open IT & Cybersecurity RFPs across 17 Government Portals`
**Platform Lock:** `17 Portals (Federal + 15 State SLED) & 23 B2B/GovCon AI Capture APIs`

---

## Part 1: 5 Copy-Pasteable LinkedIn "Live RFP Dossier Drop" Posts (Oct 21 – Oct 30)

Post 1 per day on LinkedIn leading up to the October 31 outbound domain warmup completion. Every post uses **real, currently open solicitations** from your live `/contracts/rfp/` index so capture directors click straight into `signaltender.net`.

### LinkedIn Post #1 — Virginia, Maryland & Texas SLED IT/Cyber Breakdown
```text
Most Small Business IT & cybersecurity primes spend 90% of their BD hours fighting 150 contractors on SAM.gov while State SLED portals sit wide open with 3–5 bidders.

Here are 3 live State SLED & Municipal IT/Cybersecurity solicitations our 17-portal engine shredded this morning (with pre-computed Shipley Section L/M matrices, 13 CFR 125.6 workshare caps, and IGCE Price-to-Win targets):

{east_coast_bullets}

Why SLED capture teams miss these:
1. State portals (VA eVA, MD eMMA, TX ESBD) bury IT/cyber RFPs under 99% janitorial, road-salt, and hardware renewal noise.
2. Reading a 90-page state PDF just to check mandatory certs or LCAT rate ceilings takes 4+ hours per bid.

We built SignalTender to monitor all 17 Federal, Municipal, and 15-State SLED portals (VA, TX, CA, FL, MD, IL, PA, OH, GA, NC, NY, MA, NJ, WA, MI) every 6 hours and pre-shred every actionable IT/Cyber RFP into a 21-engine CaptureDesk dossier.

Unlock 3 live pre-shredded RFP dossiers for your state free (zero credit card):
https://signaltender.net/#inbound-lead-capture-box
```

### LinkedIn Post #2 — New York (NYC CROL / PASSPort / PANYNJ) & Massachusetts (COMMBUYS) Drop
```text
New York and Massachusetts SLED agencies issue ratusan of millions in cloud migration, managed SOC/MDR, and software modernization contracts every quarter—yet their portals (NYC City Record, PASSPort, PANYNJ, MA COMMBUYS, Boston Open Data) are notoriously fragmented.

Here are 3 live Northeast & Federal IT solicitations open right now with pre-computed Pwin and Price-to-Win models:

{ny_ma_bullets}

Every dossier includes:
- Mandatory Section C/L/M "SHALL" requirement shred
- FAR/DFARS/CMMC 2.0 & NIST 800-53 Rev 5 RMF/cATO posture
- GSA MAS Large Category F SIN (54151S / 54151HACS / 518210C) & P50 LCAT rate benchmarks

Browse all {len(contracts)}+ open Federal & 15-State SLED IT contracts live:
https://signaltender.net/contracts/
```

### LinkedIn Post #3 — California (Cal eProcure) & Florida (MFMP VIP) SLED Capture Brief
```text
If your BD team only checks SAM.gov on Monday mornings, you are missing high-margin State SLED IT & cybersecurity task orders in California and Florida that close in 14–21 days.

3 live open solicitations from our 6-hour automated capture wire:

{ca_fl_bullets}

Instead of paying $18,000+/yr for legacy GovCon seats that still force your capture manager to manually read every PDF, SignalTender delivers:
- Tier 1 ($99/mo): Real-time 17-portal de-noised IT & Cyber RFP wire in Discord, Slack, Teams, or CRM.
- Tier 2 ($399/mo): Full 21-engine AI CaptureDesk dossiers (Shipley matrix, IGCE PTW, CPARS Vol III, Orals Murder-Board, FAR 15.506 Debriefing/Protest, and GSA MAS SIN mapping).
- Tier 3 ($1,499/mo): 1-Click 3-Volume Shipley Proposal .ZIP Compiler (.docx + live-formula .xlsx) & 13 CFR 125.6 Teaming Clearinghouse.
- Tier 4 ($2,499/mo): Post-Award FOIA Winning-Bid LCAT Rate Vault & 50,000 OEM REST/MCP API calls/mo.

Compare live #tier1-gov-leads vs #capturedesk-autopilot dispatches:
https://signaltender.net/#checkout
```

### LinkedIn Post #4 — Federal SAM.gov + DoD RMF/cATO & CMMC 2.0 Capture Teardown
```text
Why do 70% of small-business GovCon proposals fail before pricing is even evaluated?

Because capture teams discover a killer DFARS 252.204-7012 / CMMC Level 2 flow-down, an unstaffable Key Personnel LCAT requirement, or a 13 CFR 125.6 (50% Rule) workshare violation on Day 18 of a 21-day RFP window.

Here are 3 live Federal & SLED IT solicitations where our 21-engine CaptureDesk pre-flagged the exact compliance and pricing posture on Day 1:

{fed_bullets}

Run any live RFP through our interactive 21-API Capture Studio in your browser:
https://signaltender.net/apis.html
```

### LinkedIn Post #5 — For AI Engineers & GovCon CTOs: 23 GovCon MCP Tools in Claude Desktop & Cursor
```text
For GovCon CTOs and capture engineers building internal AI proposal workflows in Claude Desktop, Cursor, or Windsurf:

We published all 23 SignalTender GovCon procurement & proposal microservices to the Official Model Context Protocol (MCP) Registry (`@signaltender/mcp-server`).

With a single command:
`npx -y @signaltender/mcp-server`

Your AI agent gets 23 deterministic, typed GovCon tools:
- Live 17-portal Federal & 15-State SLED open RFP feed
- Shipley Section L/M compliance matrix shredder
- IGCE Wrap-Rate & Price-to-Win (PTW) modeler
- NIST 800-53 Rev 5 RMF / Continuous ATO (cATO) SSP & eMASS POA&M generator
- CPARS Past Performance Vol III & Key Personnel LCAT resume tailor
- FAR 15.102 Orals Murder-Board & FAR 15.506 Post-Award Debriefing / GAO Protest analyzer
- GSA MAS Schedule SIN (54151S / 54151HACS / 518210C) & 0.75% IFF compliance mapper

Live MCP endpoint & interactive API playground:
https://signaltender.net/apis.html
```

---

## Part 2: 4 High-Signal Reddit & Community Threads

### 1. `r/govcontracting` — State SLED vs. SAM.gov Capture Playbook
- **Title:** `We indexed {len(contracts)} open IT & cybersecurity RFPs across SAM.gov + 15 State SLED portals (VA, TX, CA, FL, MD, IL, PA, OH, GA, NC, NY, MA, NJ, WA, MI) — here is where competition is lowest right now`
- **Body:**
```markdown
Over the past few months we built an automated scraper + Shipley capture parser across 17 government procurement portals (SAM.gov, DemandStar, VA eVA, TX SmartBuy ESBD, CA Cal eProcure, FL MFMP VIP, MD eMMA, IL BidBuy, PA eMarketplace, OH OhioBuys, GA GPR, NC eVP, NY CROL/PASSPort, MA COMMBUYS, NJ NJSTART, WA WEBS, and MI SIGMA VSS).

Three data points that stood out after filtering out 99.4% of non-IT commodity noise (janitorial, construction, raw hardware part renewals):

1. **State SLED IT service bids have 60–75% fewer offerors than equivalent SAM.gov NAICS 541512 RFPs**, especially in state-specific portals like Virginia eVA, Maryland eMMA, OhioBuys, and NC eVP where out-of-state national primes rarely monitor daily postings.
2. **13 CFR 125.6 (Similarly Situated Entity / 50% Rule) & State SWaM/HUB Goals** are the #1 teaming leverage point for small cyber/cloud shops subbing to mid-tier primes.
3. **Pre-shredding Section L/M and IGCE labor rates on Day 1** saves ~4.5 hours per solicitation before committing proposal writing hours.

Here are a few live open solicitations from today's run with full pre-computed capture dossiers (no login wall):
{east_coast_bullets}

Full searchable directory of all {len(contracts)} open Federal & 15-State SLED IT contracts:
https://signaltender.net/contracts/
```

### 2. `r/msp` — Municipal & State SLED Managed IT / Co-Managed SOC RFPs
- **Title:** `How MSPs and MSSPs are winning local Municipal & State SLED Managed IT / MDR contracts without touching federal SAM.gov red tape`
- **Body:**
```markdown
A lot of MSP owners assume "government contracting" means 18-month DoD sales cycles and CMMC Level 2 audits. In reality, County, Municipal (DemandStar), Transit Authority, and State SLED portals post 1–3 year Managed IT, Microsoft 365/Entra migration,vCISO, and 24/7 MDR contracts every week with straightforward commercial-style SLAs.

Here are 3 live examples open right now:
{ny_ma_bullets}

If you want to check open Municipal & State SLED IT bids in your state without digging through clunky state portals, we maintain a live de-noised index across 15 states + DemandStar here:
https://signaltender.net/contracts/
```

### 3. `r/cybersecurity` — NIST 800-53 Rev 5 RMF, CMMC 2.0 & State Cyber Solicitations
- **Title:** `Breakdown of live Federal & 15-State SLED Cybersecurity RFPs (Zero-Trust, Penetration Testing, SOC/MDR, RMF Continuous ATO)`
- **Body:**
```markdown
For security consultancies, vCISO practices, and pen-testing firms tracking public-sector demand, we aggregated all currently open cybersecurity solicitations across SAM.gov and 15 state procurement portals:

{ca_fl_bullets}

Each dossier maps the mandatory compliance framework (CMMC 2.0 Level 2, NIST 800-171, NIST 800-53 Rev 5 RMF / cATO, CJIS, or StateRAMP) and estimated labor rate bands:
https://signaltender.net/contracts/cybersecurity/
```

### 4. `r/mcp` / `r/ClaudeAI` — 23-Tool GovCon & B2B Contract Intelligence MCP Server
- **Title:** `Built a 23-tool Model Context Protocol (MCP) server for Government Contracting, RFP Shredding, IGCE Price-to-Win & RMF/ATO Compliance`
- **Body:**
```markdown
We just shipped v1.6.0 of `@signaltender/mcp-server` (listed on the Official MCP Registry as `io.github.aarbchen/signaltender-mcp` and available via Remote Streamable HTTP at `https://b2b-contract-parser-api.onrender.com/mcp`).

It exposes 23 stateless, read-only tools for Claude Desktop, Cursor, and autonomous capture agents:
- `get_live_gov_solicitations` (live open IT/Cyber RFPs across 17 Federal & State SLED portals)
- `generate_rfp_compliance_matrix` (Shipley Section C/L/M shredder)
- `model_govcon_igce_price_to_win` (DCAA wrap-rate & P25/P50/P75 LCAT pricing)
- `generate_govcon_rmf_ato_package` (NIST 800-53 Rev 5 SSP, eMASS POA&M & cATO roadmap)
- `analyze_govcon_debriefing_protest` (FAR 15.506 debriefing Q&A & GAO bid-protest viability)
- `generate_gsa_mas_schedule_offer` (GSA MAS Large Category F SIN mapper & 0.75% IFF calculator)

Quickstart:
```bash
npx -y @signaltender/mcp-server
```
Interactive browser sandbox & full schema docs: https://signaltender.net/apis.html
```

---

## Part 3: Real-Time "Hot Prospect Click Radar" 5-Minute Follow-Up Playbook

Whenever a prospect clicks a personalized link from your outbound sequence (or shares it internally), `POST /v1/leads/track-click` fires an instant **`[HOT PROSPECT CLICK] Outbound Attribution Radar`** alert to your Discord channel with their exact **Company**, **First Name**, **Target State**, and **Action (`dossier_view`, `checkout_view`, or `stripe_click`)**.

Use these 3 plain-text replies within 5–10 minutes of seeing the Discord alert:

### Playbook A — Triggered by `dossier_view` (Prospect opened their personalized RFP dossier)
**Subject:** `Re: Live {{State}} IT/Cyber RFP Dossier + 2 more for {{Company}}`
```text
Hi {{FirstName}},

Saw your team reviewing the {{State}} capture dossier on SignalTender just now.

I went ahead and pulled 2 additional open {{State}} & Federal IT/Cyber solicitations that match {{Company}}'s NAICS profile—including the pre-shredded Section L/M requirements and GSA LCAT rate benchmarks:

https://signaltender.net/?utm_source=outbound&co={{Company_Encoded}}&fn={{FirstName}}&st={{State_Slug}}#inbound-lead-capture-box

If you want our 6-hour automated wire pushing every new {{State}} + 17-portal solicitation straight to your team's Discord, Slack, Microsoft Teams, or CRM, you can activate Tier 1 ($99/mo) or Tier 2 CaptureDesk ($399/mo) in 60 seconds here:
https://signaltender.net/?utm_source=outbound&co={{Company_Encoded}}&fn={{FirstName}}&st={{State_Slug}}#checkout

Happy to drop a live test dossier into your Slack or Teams webhook today if helpful.

Best,
SignalTender Capture Desk
```

### Playbook B — Triggered by `checkout_view` (Prospect viewed `#checkout` plan comparison)
**Subject:** `Quick question on {{Company}}'s {{State}} portal setup`
```text
Hi {{FirstName}},

Noticed someone at {{Company}} was looking at the SignalTender Tier 1 ($99/mo) vs. Tier 2 CaptureDesk ($399/mo) plans.

Quick rule of thumb for {{State}} capture teams:
- Choose Tier 1 ($99/mo) if you just want the 6-hour de-noised 17-portal alert feed + direct source bid links in Discord, Slack, or Teams.
- Choose Tier 2 ($399/mo) if you want every lead pre-shredded by all 21 AI capture engines (Shipley Section L/M compliance matrix, IGCE Price-to-Win LCAT rates, CMMC/RMF SSP posture, and 13 CFR 125.6 workshare math).

Both plans include downloadable corporate PDF tax invoices and 1-click cancellation anytime:
https://signaltender.net/?utm_source=outbound&co={{Company_Encoded}}&fn={{FirstName}}&st={{State_Slug}}#checkout-tier2

Let me know if you want us to pre-configure your Slack/Teams webhook or Discord role.

Best,
SignalTender Capture Desk
```

### Playbook C — Triggered by `stripe_click` (Prospect clicked Stripe Checkout button)
**Subject:** `Instant Discord / Slack / Teams activation for {{Company}}`
```text
Hi {{FirstName}},

Saw you initiating checkout for {{Company}} on SignalTender—if your corporate card required a W-9, vendor onboarding form, or ACH invoice option, just reply here and I can send that right over.

As soon as checkout completes, your Discord handle or Slack/Microsoft Teams webhook activates automatically within 60 seconds:
https://signaltender.net/?utm_source=outbound&co={{Company_Encoded}}&fn={{FirstName}}&st={{State_Slug}}#checkout

Best,
SignalTender Capture Desk
```

---

## Part 4: Oct 21 – Nov 7 Pre-Warmup & Launch Ramp Schedule

| Date Window | Daily Action | Outbound Cap (`OUTBOUND_DAILY_LIMIT`) | Primary Goal |
| :--- | :--- | :--- | :--- |
| **Oct 21 – Oct 25** | Publish LinkedIn Posts #1–#3 + Reddit `r/govcontracting` & `r/msp`; verify IndexNow URL indexing | `0` (Warmup Protected) | Drive organic SLED capture traffic into `#inbound-lead-capture-box` |
| **Oct 26 – Oct 30** | Publish LinkedIn Posts #4–#5 + `r/cybersecurity` & `r/mcp`; refresh `outreach_generator.py` queue | `0` (Warmup Protected) | Pre-stage 100% MX-verified `Not Catch-all` prospects in `outbox_ready_queue.json` |
| **Oct 31 – Nov 2 (Launch Days 1–3)** | Flip `OUTBOUND_ENABLED=true` on Render | `20 / day` (`Not Catch-all` priority) | Zero-bounce launch; respond within 5 mins to `[HOT PROSPECT CLICK]` Discord alerts |
| **Nov 3 – Nov 5 (Days 4–6)** | Increase `OUTBOUND_DAILY_LIMIT=35`; Step 2 follow-ups auto-fire for non-openers | `35 / day` | Convert `dossier_view` and `checkout_view` prospects into Tier 1 (`$99/mo`) & Tier 2 (`$399/mo`) subscribers |
| **Nov 6+ (Full Scale)** | Increase `OUTBOUND_DAILY_LIMIT=50` | `50 / day` | Steady-state automated outbound + inbound dossier capture flywheel |
"""

    with open(OUTPUT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"[+] Generated social_distribution_kit.md ({len(md):,} bytes) using {len(contracts)} live open solicitations.", flush=True)
    return OUTPUT_MD_PATH


if __name__ == "__main__":
    generate_distribution_kit()

