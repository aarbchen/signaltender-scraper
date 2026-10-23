"""
SignalTender LinkedIn Company Page Asset Generator & Automated Promotional Post Engine (`linkedin_autoposter.py`).

1. Generates the official evergreen LinkedIn Company Cover Banner (`d:\\Daas\\linkedin_company_banner.png`,
   2256x382 2x retina for LinkedIn's 1128x191 company cover spec) and 500x500 Company Logo.
2. Pulls live, pre-vetted Federal (SAM.gov) and State SLED IT/Cybersecurity RFPs from Supabase
   and generates a rotating queue of high-converting LinkedIn Company Page promotional posts
   (`d:\\Daas\\linkedin_ready_posts.json`).
3. Supports zero-touch daily/cron publishing via the official LinkedIn Posts REST API
   (`LINKEDIN_ACCESS_TOKEN` + `LINKEDIN_ORG_URN` in `.env`) and integrates into `mainscraper.py`.
"""

from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()

import asyncio
import json
import os
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BANNER_PATH = os.path.join(BASE_DIR, "linkedin_company_banner.png")
POSTS_QUEUE_PATH = os.path.join(BASE_DIR, "linkedin_ready_posts.json")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
# Strictly locked to the official SignalTender Company Page (NEVER a personal urn:li:person profile)
LINKEDIN_ORG_URN = "urn:li:organization:146880945"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5").strip() or "claude-sonnet-5-5"

# Evergreen LinkedIn Company Profile Metadata (follows Evergreen Copy Rule)
LINKEDIN_COMPANY_PROFILE = {
    "name": "SignalTender",
    "slug": "signaltender",
    "public_url": "https://www.linkedin.com/company/signaltender/",
    "admin_url": "https://www.linkedin.com/company/146880945/admin/dashboard/",
    "organization_urn": "urn:li:organization:146880945",
    "website": "https://signaltender.net/",
    "industry": "Information Services",
    "company_size": "2-10 employees",
    "company_type": "Privately Held",
    "tagline": "Real-time Federal & State SLED IT/Cyber RFP intelligence, AI capture dossiers, and GovCon REST & MCP APIs.",
    "description": (
        "SignalTender is an autonomous Government Contracting (GovCon) and State/Local/Education (SLED) "
        "IT & Cybersecurity procurement intelligence platform and developer API ecosystem.\n\n"
        "Legacy GovCon bid aggregators charge $15,000+ per year for noisy keyword dumps filled with "
        "commodity office supplies, hardware part replacements, and maintenance renewals—leaving lean "
        "capture teams to spend 40+ hours manually shredding 150-page PDFs.\n\n"
        "SignalTender's 3-layer AI quality control engine monitors Federal (SAM.gov), municipal, and "
        "major State SLED procurement portals every 6 hours, stripping 99.4% of commodity noise and "
        "delivering actionable B2B software, cloud, data, and cybersecurity solicitations.\n\n"
        "WHAT SIGNALTENDER DELIVERS:\n"
        "• SignalWire Pro ($99/mo): Real-time 6-hour Federal & State SLED IT/Cyber RFP alerts routed directly "
        "to Discord, Slack, Microsoft Teams, or custom CRM webhooks.\n"
        "• CaptureDesk Autopilot ($399/mo): Pre-computed AI capture dossiers on every solicitation—including "
        "Shipley Section L/M Compliance Matrices, Bid/No-Bid Pwin (0-100) capability scoring, FAR/DFARS & "
        "CMMC 2.0 flow-down redlines, 13 CFR § 125.6 (50% Rule) small-business workshare plans, IGCE "
        "wrap-rate & Price-to-Win models, CPARS Volume III past performance citations, SF-30 amendment diffs, "
        "NIST 800-53 RMF / Continuous ATO (cATO) packages, FAR 15.102 Oral Presentation murder-board prep, "
        "FAR 15.506 Post-Award Debriefing & GAO Bid-Protest analysis, and GSA MAS Schedule SIN mapping.\n"
        "• GovCon REST APIs & Model Context Protocol (MCP) Server (@signaltender/mcp-server): Plug live "
        "government contract intelligence and proposal automation directly into Claude Desktop, Cursor, "
        "Windsurf, and custom AI capture agents.\n\n"
        "100% self-serve. Zero annual lock-ins or sales calls. Explore live open IT/Cyber RFPs and test "
        "the interactive API playground at https://signaltender.net"
    ),
    "specialties": [
        "Government Contracting (GovCon)",
        "State SLED Procurement",
        "SAM.gov RFP Intelligence",
        "Shipley Proposal Automation",
        "CMMC 2.0 & NIST 800-171 Compliance",
        "Model Context Protocol (MCP)",
        "AI Capture Management",
        "Price-to-Win & IGCE Modeling",
        "GSA MAS Schedule Compliance",
        "Cybersecurity Solicitations",
    ],
}

BANNER_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@600;700;800;900&family=JetBrains+Mono:wght@600;700;800&display=swap" rel="stylesheet">
<style>
  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    -webkit-font-smoothing: antialiased;
    text-rendering: geometricPrecision;
  }
  html, body {
    width: 1128px;
    height: 191px;
  }
  body {
    position: relative;
    overflow: hidden;
    font-family: 'Inter', sans-serif;
    color: #f8fafc;
    background:
      radial-gradient(ellipse 460px 230px at 84% 50%, rgba(56, 189, 248, 0.20) 0%, rgba(16, 185, 129, 0.08) 45%, rgba(7, 11, 22, 0) 75%),
      radial-gradient(ellipse 320px 190px at 10% 50%, rgba(56, 189, 248, 0.12) 0%, rgba(7, 11, 22, 0) 70%),
      linear-gradient(135deg, #050811 0%, #09101f 52%, #0d172a 100%);
    display: flex;
    align-items: center;
    justify-content: space-between;
    /* Left padding 202px keeps 100% of text & pills clear of LinkedIn's overlapping square logo (x: 24..168px) */
    padding: 4px 24px 0 202px;
  }
  .top-accent {
    position: absolute;
    top: 0; left: 0; right: 0; height: 4px;
    background: linear-gradient(90deg, #38bdf8 0%, #10b981 50%, #6366f1 100%);
  }
  /* Subtle vertical separator right after the LinkedIn logo docking zone */
  .logo-dock-line {
    position: absolute;
    left: 184px;
    top: 22px;
    bottom: 22px;
    width: 1.5px;
    background: linear-gradient(180deg, rgba(56, 189, 248, 0) 0%, rgba(56, 189, 248, 0.45) 50%, rgba(16, 185, 129, 0) 100%);
  }
  .left-col {
    position: relative;
    z-index: 2;
    display: flex;
    flex-direction: column;
    justify-content: center;
    max-width: 530px;
  }
  .status-pill {
    display: inline-flex;
    align-items: center;
    align-self: flex-start;
    gap: 8px;
    padding: 4px 12px;
    border-radius: 999px;
    background: rgba(16, 185, 129, 0.15);
    border: 1.5px solid rgba(52, 211, 153, 0.45);
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    font-weight: 700;
    color: #34d399;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 9px;
  }
  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
  }
  .main-title {
    font-size: 29px;
    font-weight: 800;
    letter-spacing: -0.025em;
    line-height: 1.16;
    color: #ffffff;
    margin-bottom: 12px;
  }
  .main-title .sky {
    color: #38bdf8;
  }
  .main-title .em {
    color: #34d399;
  }
  .pill-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    font-weight: 700;
  }
  .tag-pill {
    padding: 5px 11px;
    border-radius: 7px;
    background: rgba(15, 23, 42, 0.95);
    border: 1.5px solid rgba(71, 85, 105, 0.9);
    color: #f1f5f9;
    white-space: nowrap;
  }
  .tag-pill b {
    color: #38bdf8;
    font-weight: 800;
  }
  .tag-pill.url-pill {
    background: rgba(2, 132, 199, 0.22);
    border-color: rgba(56, 189, 248, 0.65);
    color: #38bdf8;
  }
  .hud-card {
    position: relative;
    z-index: 2;
    width: 364px;
    background: rgba(9, 14, 26, 0.96);
    border: 1.5px solid rgba(56, 189, 248, 0.5);
    border-radius: 12px;
    padding: 12px 16px;
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.7);
    font-family: 'JetBrains Mono', monospace;
  }
  .hud-hdr {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 7px;
    margin-bottom: 6px;
    border-bottom: 1.5px solid rgba(51, 65, 85, 0.9);
    font-size: 11px;
    font-weight: 700;
    color: #cbd5e1;
    letter-spacing: 0.03em;
  }
  .hud-hdr .live-badge {
    color: #34d399;
    background: rgba(16, 185, 129, 0.14);
    border: 1px solid rgba(52, 211, 153, 0.4);
    padding: 1.5px 7px;
    border-radius: 4px;
    font-size: 10.5px;
  }
  .hud-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    padding: 4.5px 0;
    border-bottom: 1px solid rgba(30, 41, 59, 0.95);
  }
  .hud-row:last-child {
    border-bottom: none;
    padding-bottom: 1px;
  }
  .hud-key {
    color: #94a3b8;
    font-weight: 600;
  }
  .hud-val {
    font-weight: 700;
    color: #ffffff;
  }
  .hud-val.sky { color: #38bdf8; }
  .hud-val.em  { color: #34d399; }
  .hud-val.ind { color: #a5b4fc; }
</style>
</head>
<body>
  <div class="top-accent"></div>
  <div class="logo-dock-line"></div>

  <div class="left-col">
    <div class="status-pill">
      <span class="status-dot"></span>
      <span>FEDERAL &amp; STATE SLED PROCUREMENT WIRE &bull; 99.4% NOISE STRIPPED</span>
    </div>
    <div class="main-title">
      Autonomous <span class="sky">SAM.gov &amp; State SLED</span><br>
      IT/Cyber RFPs &amp; <span class="em">AI Capture Dossiers</span>
    </div>
    <div class="pill-row">
      <div class="tag-pill"><b>6-HR</b> LIVE ALERTS</div>
      <div class="tag-pill"><b>SHIPLEY</b> L/M &amp; CMMC AI</div>
      <div class="tag-pill url-pill">signaltender.net &rarr;</div>
    </div>
  </div>

  <div class="hud-card">
    <div class="hud-hdr">
      <span>// CAPTUREDESK AI ENGINE</span>
      <span class="live-badge">● 200 OK LIVE</span>
    </div>
    <div class="hud-row">
      <span class="hud-key">PORTALS</span>
      <span class="hud-val sky">SAM.gov + State SLED</span>
    </div>
    <div class="hud-row">
      <span class="hud-key">SHREDDING</span>
      <span class="hud-val em">Sec L/M &bull; CPARS &bull; PTW</span>
    </div>
    <div class="hud-row">
      <span class="hud-key">COMPLIANCE</span>
      <span class="hud-val ind">CMMC 2.0 &bull; RMF &bull; GSA</span>
    </div>
    <div class="hud-row">
      <span class="hud-key">DEVELOPERS</span>
      <span class="hud-val sky">REST + @signaltender/mcp</span>
    </div>
  </div>
</body>
</html>
"""


async def render_linkedin_banner_async() -> str:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1128, "height": 191}, device_scale_factor=2)
        await page.set_content(BANNER_HTML, wait_until="networkidle")
        await page.evaluate("document.fonts.ready")
        await page.screenshot(path=BANNER_PATH, full_page=False)
        await browser.close()
    return BANNER_PATH


def generate_linkedin_banner() -> str:
    try:
        try:
            asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(lambda: asyncio.run(render_linkedin_banner_async())).result(timeout=30)
        except RuntimeError:
            asyncio.run(render_linkedin_banner_async())
        print(f"[+] Generated LinkedIn Company Banner (2256x382 2x retina): {BANNER_PATH}", flush=True)
    except Exception as err:
        report_error("linkedin_autoposter.py", f"Banner render warning: {err}")
    return BANNER_PATH


def build_promotional_posts() -> list[dict]:
    """Generate fresh, evergreen + live-RFP LinkedIn Company Page promotional posts."""
    live_rfps = []
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            from supabase import create_client
            import pseo_generator
            sb = create_client(SUPABASE_URL, SUPABASE_KEY)
            resp = (
                sb.table("contracts")
                .select("*")
                .in_("status", ["New Lead", "Delivered", "NEW"])
                .order("id", desc=True)
                .limit(60)
                .execute()
            )
            rows = resp.data if resp and getattr(resp, "data", None) else []
            today = datetime.now().date()
            for r in rows:
                t = str(r.get("title") or "").strip()
                if not t or pseo_generator.is_commodity_it_spam(t):
                    continue
                due_dt = pseo_generator.parse_due_date(r)
                if due_dt is not None and due_dt < today:
                    continue
                clean_t = pseo_generator.clean_display_title(t)
                slug = pseo_generator.slugify(t, fallback_id=str(r.get("id") or "rfp"))
                j_key = pseo_generator.classify_jurisdiction(r)
                j_short = pseo_generator.JURISDICTIONS.get(j_key, {}).get("short", "GovCon")
                live_rfps.append({
                    "title": clean_t,
                    "agency": str(r.get("agency") or "Government Agency").strip(),
                    "due": due_dt.strftime("%m/%d/%Y") if due_dt else "Open",
                    "jurisdiction": j_short,
                    "url": f"https://signaltender.net/contracts/rfp/{slug}.html",
                })
                if len(live_rfps) >= 6:
                    break
        except Exception as e:
            report_error("linkedin_autoposter.py", f"Supabase RFP fetch warning in linkedin_autoposter: {e}")

    rfp_1 = live_rfps[0] if len(live_rfps) > 0 else {
        "title": "Enterprise Cloud Migration & Zero-Trust Cybersecurity Architecture RFP",
        "agency": "Federal & State SLED Procurement",
        "due": "Active",
        "jurisdiction": "Federal / SLED",
        "url": "https://signaltender.net/contracts/",
    }
    rfp_2 = live_rfps[1] if len(live_rfps) > 1 else rfp_1
    rfp_3 = live_rfps[2] if len(live_rfps) > 2 else rfp_1

    posts = [
        {
            "id": "post_01_pinned_platform_launch",
            "category": "Pinned Platform Overview",
            "scheduled_slot": "PUBLISHED LIVE (https://www.linkedin.com/feed/update/urn:li:share:7518850401417297920?actorCompanyId=146880945)",
            "published": True,
            "post_url": "https://www.linkedin.com/feed/update/urn:li:share:7518850401417297920?actorCompanyId=146880945",
            "text": (
                "Why do lean GovCon and State SLED capture teams still pay $15,000+/year for legacy bid aggregators—only to spend 40 hours manually shredding 150-page PDFs?\n\n"
                "We built SignalTender to replace noisy keyword alerts and manual proposal prep with an autonomous 6-hour Federal & State SLED IT/Cybersecurity intelligence wire.\n\n"
                "What SignalTender delivers out of the box:\n"
                "1. 99.4% Commodity Noise Stripped: Our 3-layer AI filter automatically drops printer toner, hardware part replacements, sole-source notices, and maintenance renewals across SAM.gov, DemandStar, and major State SLED portals.\n"
                "2. Pre-Shredded CaptureDesk AI Dossiers: Every open solicitation includes NAICS & SBA size standards, Shipley Section L/M compliance matrices, FAR/DFARS & CMMC 2.0 redlines, 13 CFR 125.6 (50% Rule) teaming workshare math, IGCE wrap-rate & Price-to-Win bands, and CPARS Past Performance Volume III citations.\n"
                "3. Native REST APIs & MCP Server (@signaltender/mcp-server): Connect live government RFP intelligence and proposal shredding directly into Claude Desktop, Cursor, or your internal capture workflows.\n\n"
                "Zero annual lock-ins. Zero sales calls. Instant 60-second self-serve activation.\n\n"
                "Explore the live Federal & State SLED IT/Cyber contract directory or unlock 3 free pre-shredded dossiers for your state:\n"
                "https://signaltender.net/contracts/\n\n"
                "#GovCon #SLED #SAMgov #Cybersecurity #GovernmentContracting #CMMC #ProposalManagement #CaptureManagement #MCP"
            ),
        },
        {
            "id": "post_02_live_rfp_briefing",
            "category": "Live Federal & State SLED RFP Briefing",
            "scheduled_slot": "PUBLISHED LIVE (https://www.linkedin.com/feed/update/urn:li:share:7518850978813743104?actorCompanyId=146880945)",
            "published": True,
            "post_url": "https://www.linkedin.com/feed/update/urn:li:share:7518850978813743104?actorCompanyId=146880945",
            "text": (
                "LIVE GOVCON & STATE SLED IT/CYBER BRIEFING\n\n"
                "Here are 3 active, pre-vetted government software, cloud, and cybersecurity solicitations our autonomous scraper pipeline indexed and shredded today:\n\n"
                f"1. [{rfp_1['jurisdiction']}] {rfp_1['title']}\n"
                f"   • Issuing Agency: {rfp_1['agency']} (Due: {rfp_1['due']})\n"
                f"   • AI Capture Dossier: {rfp_1['url']}\n\n"
                f"2. [{rfp_2['jurisdiction']}] {rfp_2['title']}\n"
                f"   • Issuing Agency: {rfp_2['agency']} (Due: {rfp_2['due']})\n"
                f"   • AI Capture Dossier: {rfp_2['url']}\n\n"
                f"3. [{rfp_3['jurisdiction']}] {rfp_3['title']}\n"
                f"   • Issuing Agency: {rfp_3['agency']} (Due: {rfp_3['due']})\n"
                f"   • AI Capture Dossier: {rfp_3['url']}\n\n"
                "Every dossier includes pre-computed NAICS/SBA caps, CMMC 2.0 / NIST 800-171 / StateRAMP posture, 13 CFR 125.6 teaming workshare guardrails, and IGCE Price-to-Win bands.\n\n"
                "Browse all live open solicitations or route real-time alerts to your Discord, Slack, Teams, or CRM webhook:\n"
                "https://signaltender.net\n\n"
                "#GovCon #RFP #StateSLED #ITContracting #Cybersecurity #CloudComputing #SmallBusinessGovCon"
            ),
        },
        {
            "id": "post_03_mcp_and_developer_apis",
            "category": "AI Agents & MCP Developer Spotlight",
            "scheduled_slot": "SCHEDULED IN LINKEDIN (Sat, Oct 24, 2026 at 10:00 AM CDT)",
            "scheduled": True,
            "text": (
                "Your AI coding and capture assistants (Claude Desktop, Cursor, Windsurf) can now shred government RFPs, audit FAR/DFARS flow-downs, and model IGCE Price-to-Win natively via the Model Context Protocol (MCP).\n\n"
                "With @signaltender/mcp-server and the SignalTender GovCon API Suite, capture engineers and proposal teams can:\n"
                "• Shred raw Section L/M/C RFP text into a Shipley compliance matrix in seconds\n"
                "• Audit FAR 52.227-14 IP rights, DFARS 252.204-7012 / CMMC 2.0 flow-downs, and termination risks\n"
                "• Compute 13 CFR 125.6 (50% Rule) small-business workshare splits & ostensible subcontractor risk\n"
                "• Generate CPARS Volume III Past Performance narratives, NIST 800-53 RMF/cATO SSPs, FAR 15.102 Oral Presentation slides, and GSA MAS SIN mappings\n\n"
                "Test every endpoint live in our browser-based API Studio (zero login required):\n"
                "https://signaltender.net/apis.html\n\n"
                "#ModelContextProtocol #MCP #GovConAI #ProposalWriting #CMMC #FedRAMP #GSA #B2BAPIs"
            ),
        },
        {
            "id": "post_04_sled_moat_vs_sam_gov",
            "category": "Capture Strategy & SLED Moat",
            "scheduled_slot": "SCHEDULED IN LINKEDIN (Tue, Oct 27, 2026 at 10:00 AM CDT)",
            "scheduled": True,
            "text": (
                "90% of small-to-midsize IT & cybersecurity contractors fight over the exact same crowded SAM.gov task orders—while high-margin State SLED RFPs receive 70% fewer bids.\n\n"
                "Why? Because State SLED procurement is fragmented across dozens of separate portals (Virginia eVA, Texas SmartBuy ESBD, California Cal eProcure, Florida MFMP, Maryland eMMA, Illinois BidBuy, Pennsylvania eMarketplace, OhioBuys, Georgia GPR, North Carolina eVP, New York CROL/PASSPort, Massachusetts COMMBUYS, and municipal DemandStar).\n\n"
                "Checking those portals manually every morning takes hours. SignalTender unifies Federal and State SLED IT/Cyber monitoring into a single 6-hour feed—complete with state-specific MBE/HUB/SWaM/DVBE teaming posture and StateRAMP/TX-RAMP compliance checks.\n\n"
                "Unlock 3 free pre-shredded RFP dossiers for your target state in 10 seconds:\n"
                "https://signaltender.net/#inbound-lead-capture-box\n\n"
                "#SLED #StateProcurement #GovCon #ITServices #Cybersecurity #SmallBusiness #CaptureManagement"
            ),
        },
        {
            "id": "post_05_pricing_and_compliance_automation",
            "category": "Proposal & Pricing Engineering",
            "scheduled_slot": "SCHEDULED IN LINKEDIN (Fri, Oct 30, 2026 at 10:00 AM CDT)",
            "scheduled": True,
            "text": (
                "The 3 bottlenecks that kill GovCon proposal velocity before Red Team review:\n\n"
                "1. Missing a mandatory Requirement in Section L/M or an SF-30 Amendment change\n"
                "2. Guessing on Indirect Wrap-Rates (Fringe / Overhead / G&A) and Price-to-Win against GSA CALC+ ceilings\n"
                "3. Scrambling to map Key Personnel resumes, CPARS citations, and 13 CFR 125.6 workshare caps 48 hours before submission\n\n"
                "SignalTender CaptureDesk Autopilot pre-computes these deliverables automatically on every open solicitation—so your capture lead starts at 80% draft completion on Day 1.\n\n"
                "Compare SignalWire Pro ($99/mo) and CaptureDesk Autopilot ($399/mo) at:\n"
                "https://signaltender.net/#checkout\n\n"
                "#ProposalManagement #Shipley #PriceToWin #GovCon #FederalContracting #Cybersecurity #CaptureDesk"
            ),
        },
    ]
    return posts


def generate_claude_linkedin_post(live_rfps: list[dict]) -> str:
    """Use claude-sonnet-5-5 to draft a fresh, high-converting LinkedIn GovCon briefing from the newest open RFPs."""
    rfp_lines = []
    for i, r in enumerate(live_rfps[:3], 1):
        rfp_lines.append(
            f"{i}. [{r['jurisdiction']}] {r['title']}\n"
            f"   • Issuing Agency: {r['agency']} (Due: {r['due']})\n"
            f"   • Pre-Shredded Dossier: {r['url']}"
        )
    fallback_text = (
        "LIVE GOVCON & STATE SLED IT/CYBER PROCUREMENT BRIEFING\n\n"
        "Here are 3 open government software, cloud, and cybersecurity solicitations our autonomous 14-portal capture engine indexed and shredded today:\n\n"
        + "\n\n".join(rfp_lines)
        + "\n\nEach dossier includes NAICS/SBA size caps, CMMC 2.0 / NIST 800-171 / StateRAMP posture, 13 CFR 125.6 workshare math, and IGCE Price-to-Win benchmarks.\n\n"
        "Unlock 3 free pre-shredded dossiers for your state or route 6-hour alerts to your inbox, Slack, Teams, or Discord:\n"
        "https://signaltender.net/contracts/\n\n"
        "#GovCon #SLED #SAMgov #Cybersecurity #GovernmentContracting #CaptureManagement #ProposalWriting #ITContracting"
    )
    if not ANTHROPIC_API_KEY or not live_rfps:
        return fallback_text
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        prompt = (
            "You are the official SignalTender Company Page (https://www.linkedin.com/company/signaltender/ | https://signaltender.net). "
            "Write a sharp, executive-grade LinkedIn Company Page post "
            "(plain text, zero markdown bold `**`, zero emojis) highlighting these 3 newly indexed open Federal/State SLED IT & cybersecurity RFPs:\n\n"
            + "\n\n".join(rfp_lines)
            + "\n\nInclude the exact dossier URLs above, mention how SignalTender strips 99.4% of commodity noise across 14 Federal & State SLED portals "
            "and pre-computes Shipley Section L/M matrices, CMMC/NIST compliance, and IGCE Price-to-Win bands, and end with https://signaltender.net/contracts/ "
            "plus 6-8 relevant GovCon hashtags. Keep under 1,800 characters."
        )
        msg = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        for blk in msg.content:
            if blk.type == "text" and len(blk.text.strip()) > 200:
                return blk.text.strip().replace("**", "")
    except Exception as e:
        report_error("linkedin_autoposter.py", f"Claude post generation warning: {e}")
    return fallback_text


def publish_via_linkedin_api(post_text: str) -> tuple[bool, str]:
    """
    Publish ONLY to the official SignalTender LinkedIn Company Page (`urn:li:organization:146880945`).
    NEVER publishes to any personal member profile (`urn:li:person:...`).
    """
    token = os.getenv("LINKEDIN_ACCESS_TOKEN", LINKEDIN_ACCESS_TOKEN).strip()
    if not token:
        return False, "LINKEDIN_ACCESS_TOKEN not set in .env (staged in linkedin_ready_posts.json)"

    # Hard-locked strictly to the official SignalTender Company Page URN
    author_org = "urn:li:organization:146880945"
    if not author_org.startswith("urn:li:organization:"):
        return False, "Blocked: Only SignalTender Company Page (urn:li:organization:146880945) is permitted"

    # 1. Try LinkedIn REST Posts API for Organization Page (`urn:li:organization:146880945`)
    rest_headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202501",
        "Content-Type": "application/json",
    }
    org_payload = {
        "author": author_org,
        "commentary": post_text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    try:
        r_org = requests.post("https://api.linkedin.com/rest/posts", headers=rest_headers, json=org_payload, timeout=15)
        if r_org.status_code in (200, 201):
            post_id = r_org.headers.get("x-restli-id", "published")
            return True, f"Published to SignalTender Company Page ({post_id})"
    except Exception:
        pass

    # 2. Try LinkedIn UGC Posts API for Organization Page (`urn:li:organization:146880945` ONLY — never urn:li:person)
    ugc_headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }
    ugc_payload = {
        "author": author_org,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_text},
                "shareMediaCategory": "ARTICLE",
                "media": [
                    {
                        "status": "READY",
                        "description": {
                            "text": "Real-time Federal (SAM.gov) & 12-State SLED IT/Cyber RFP intelligence, pre-shredded Shipley Section L/M capture dossiers, and 20 GovCon REST & MCP APIs."
                        },
                        "originalUrl": "https://signaltender.net/contracts/",
                        "title": {"text": "SignalTender — Live Federal & State SLED IT/Cyber Contract Directory"},
                    }
                ],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    try:
        resp = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=ugc_headers, json=ugc_payload, timeout=15)
        if resp.status_code in (200, 201):
            post_id = resp.headers.get("x-restli-id") or resp.json().get("id", "published")
            return True, f"Published to SignalTender Company Page ({post_id})"
        return (
            False,
            f"Staged for SignalTender Company Page (urn:li:organization:146880945; awaiting w_organization_social scope — personal profile posting disabled)",
        )
    except Exception as e:
        return False, f"LinkedIn Organization API error: {e}"


def run_linkedin_autoposter(generate_banner: bool = False, force_post_now: bool = False) -> dict:
    if generate_banner:
        generate_linkedin_banner()

    posts = build_promotional_posts()
    existing_published_ids = set()
    last_api_post_ts = 0.0
    prev_dynamic_posts = []
    if os.path.exists(POSTS_QUEUE_PATH):
        try:
            with open(POSTS_QUEUE_PATH, "r", encoding="utf-8") as f:
                prev = json.load(f)
                last_api_post_ts = float(prev.get("last_api_post_ts") or 0.0)
                for p in prev.get("posts", []):
                    if p.get("published"):
                        existing_published_ids.add(p.get("id"))
                    if str(p.get("id", "")).startswith("post_auto_"):
                        prev_dynamic_posts.append(p)
        except Exception:
            pass

    for p in posts:
        if p["id"] in existing_published_ids:
            p["published"] = True

    posts.extend(prev_dynamic_posts[-10:])

    token = os.getenv("LINKEDIN_ACCESS_TOKEN", LINKEDIN_ACCESS_TOKEN).strip()
    api_status = "STAGED_FOR_LINKEDIN"
    now_ts = datetime.now(timezone.utc).timestamp()

    # Rate-limit automatic API posting to at most 1 post per 20 hours (unless force_post_now=True)
    if token and (force_post_now or (now_ts - last_api_post_ts) >= 72000):
        target_post = None
        for p in posts:
            if not p.get("published") and not p.get("scheduled"):
                target_post = p
                break
        if target_post is None:
            # Generate a brand-new live RFP briefing post using claude-sonnet-5-5
            live_rfps = []
            try:
                from supabase import create_client
                import pseo_generator
                if SUPABASE_URL and SUPABASE_KEY:
                    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
                    rows = (sb.table("contracts").select("*").in_("status", ["New Lead", "Delivered", "NEW"]).order("id", desc=True).limit(30).execute().data or [])
                    today = datetime.now().date()
                    for r in rows:
                        t = str(r.get("title") or "").strip()
                        if not t or pseo_generator.is_commodity_it_spam(t):
                            continue
                        due_dt = pseo_generator.parse_due_date(r)
                        if due_dt is not None and due_dt < today:
                            continue
                        slug = pseo_generator.slugify(t, fallback_id=str(r.get("id") or "rfp"))
                        j_key = pseo_generator.classify_jurisdiction(r)
                        j_short = pseo_generator.JURISDICTIONS.get(j_key, {}).get("short", "GovCon")
                        live_rfps.append({
                            "title": pseo_generator.clean_display_title(t),
                            "agency": str(r.get("agency") or "Government Agency").strip(),
                            "due": due_dt.strftime("%m/%d/%Y") if due_dt else "Open",
                            "jurisdiction": j_short,
                            "url": f"https://signaltender.net/contracts/rfp/{slug}.html",
                        })
                        if len(live_rfps) >= 3:
                            break
            except Exception:
                pass
            auto_id = f"post_auto_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"
            target_post = {
                "id": auto_id,
                "category": "Autonomous Claude Sonnet 5.5 Live RFP Briefing",
                "scheduled_slot": "AUTO_PUBLISHED_VIA_LINKEDIN_API",
                "published": False,
                "text": generate_claude_linkedin_post(live_rfps),
            }
            posts.append(target_post)

        ok, detail = publish_via_linkedin_api(target_post["text"])
        api_status = detail
        if ok:
            target_post["published"] = True
            target_post["published_at"] = datetime.now(timezone.utc).isoformat()
            target_post["api_result"] = detail
            last_api_post_ts = now_ts

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "last_api_post_ts": last_api_post_ts,
        "company_profile": LINKEDIN_COMPANY_PROFILE,
        "banner_path": BANNER_PATH,
        "api_status": api_status,
        "posts": posts,
    }
    with open(POSTS_QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"[+] LinkedIn Autoposter: {len(posts)} promotional posts synced in {POSTS_QUEUE_PATH} ({api_status}).", flush=True)
    return out


if __name__ == "__main__":
    run_linkedin_autoposter(generate_banner=False, force_post_now=True)
