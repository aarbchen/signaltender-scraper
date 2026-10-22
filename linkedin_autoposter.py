"""
SignalTender LinkedIn Company Page Asset Generator & Automated Promotional Post Engine (`linkedin_autoposter.py`).

1. Generates the official evergreen LinkedIn Company Cover Banner (`d:\\Daas\\linkedin_company_banner.png`,
   4512x764 4x retina for LinkedIn's 1128x191 company cover spec) and 500x500 Company Logo.
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
LINKEDIN_ORG_URN = os.getenv("LINKEDIN_ORG_URN", "urn:li:organization:146880945").strip()  # Official SignalTender LinkedIn Org URN

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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800;900&family=JetBrains+Mono:wght@600;700&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { width: 1128px; height: 191px; }
  body {
    position: relative;
    overflow: hidden;
    font-family: 'Inter', sans-serif;
    color: #ffffff;
    background:
      radial-gradient(ellipse 520px 260px at 92% 50%, rgba(56, 189, 248, 0.22) 0%, rgba(56, 189, 248, 0) 70%),
      radial-gradient(ellipse 420px 220px at 38% 120%, rgba(16, 185, 129, 0.14) 0%, rgba(16, 185, 129, 0) 70%),
      linear-gradient(120deg, #050912 0%, #0a1222 55%, #0d1a30 100%);
  }
  .accent {
    position: absolute; top: 0; left: 0; right: 0; height: 4px;
    background: linear-gradient(90deg, #38bdf8 0%, #10b981 55%, #38bdf8 100%);
  }
  /* Large, low-contrast radar mark on the right: thick strokes survive LinkedIn JPEG compression */
  .radar {
    position: absolute;
    right: -40px;
    top: 50%;
    transform: translateY(-50%);
    opacity: 0.16;
  }
  /* Content starts at x=300 to stay clear of the company logo, which overlaps the lower-left corner */
  .content {
    position: absolute;
    left: 300px;
    top: 0;
    bottom: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  .kicker {
    display: flex;
    align-items: center;
    gap: 9px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: #34d399;
    margin-bottom: 10px;
  }
  .dot { width: 10px; height: 10px; border-radius: 50%; background: #10b981; }
  h1 {
    font-size: 40px;
    font-weight: 900;
    letter-spacing: -0.025em;
    line-height: 1.08;
  }
  h1 .hl { color: #38bdf8; }
  .sub {
    margin-top: 12px;
    font-size: 19px;
    font-weight: 600;
    color: #cbd5e1;
    letter-spacing: -0.005em;
  }
  .sub .sep { color: #38bdf8; padding: 0 7px; }
  .cta {
    position: absolute;
    right: 36px;
    bottom: 28px;
    padding: 10px 18px;
    border-radius: 12px;
    background: #0284c7;
    border: 2px solid #38bdf8;
    font-size: 18px;
    font-weight: 800;
    letter-spacing: -0.01em;
    color: #ffffff;
  }
</style>
</head>
<body>
  <div class="accent"></div>
  <svg class="radar" width="300" height="300" viewBox="6 5 52 54" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="32" cy="24" r="15" stroke="#F8FAFC" stroke-width="5.6" />
    <circle cx="32" cy="24" r="5" fill="#38BDF8" />
    <path d="M10 54L32 42L54 54" stroke="#38BDF8" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
  <div class="content">
    <div class="kicker"><span class="dot"></span>LIVE &middot; SAM.GOV + STATE SLED &middot; EVERY 6 HOURS</div>
    <h1>Government IT &amp; Cyber RFPs,<br><span class="hl">Pre-Shredded by AI.</span></h1>
    <div class="sub">AI Capture Dossiers<span class="sep">&bull;</span>CMMC<span class="sep">&bull;</span>GovCon APIs &amp; MCP</div>
  </div>
  <div class="cta">signaltender.net &rarr;</div>
</body>
</html>
"""


async def render_linkedin_banner_async() -> str:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1128, "height": 191}, device_scale_factor=4)
        await page.set_content(BANNER_HTML, wait_until="networkidle")
        await page.evaluate("document.fonts.ready")
        await page.screenshot(path=BANNER_PATH, full_page=False)
        await browser.close()
    return BANNER_PATH


def generate_linkedin_banner() -> str:
    try:
        asyncio.run(render_linkedin_banner_async())
        print(f"[+] Generated LinkedIn Company Banner (4512x764 4x retina): {BANNER_PATH}", flush=True)
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


def publish_via_linkedin_api(post_text: str) -> tuple[bool, str]:
    """Publish a company update directly to LinkedIn if LINKEDIN_ACCESS_TOKEN and LINKEDIN_ORG_URN are configured."""
    if not LINKEDIN_ACCESS_TOKEN or not LINKEDIN_ORG_URN:
        return False, "LINKEDIN_ACCESS_TOKEN / LINKEDIN_ORG_URN not set in .env (staged in linkedin_ready_posts.json)"
    author_urn = LINKEDIN_ORG_URN if LINKEDIN_ORG_URN.startswith("urn:li:") else f"urn:li:organization:{LINKEDIN_ORG_URN}"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202405",
        "Content-Type": "application/json",
    }
    payload = {
        "author": author_urn,
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
        resp = requests.post("https://api.linkedin.com/rest/posts", headers=headers, json=payload, timeout=15)
        if resp.status_code in (200, 201):
            post_id = resp.headers.get("x-restli-id", "published")
            return True, f"Published to LinkedIn Organization Feed ({post_id})"
        return False, f"LinkedIn API HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, f"LinkedIn API error: {e}"


def run_linkedin_autoposter(generate_banner: bool = False) -> dict:
    if generate_banner or not os.path.exists(BANNER_PATH):
        generate_linkedin_banner()

    posts = build_promotional_posts()
    existing_published_ids = set()
    if os.path.exists(POSTS_QUEUE_PATH):
        try:
            with open(POSTS_QUEUE_PATH, "r", encoding="utf-8") as f:
                prev = json.load(f)
                for p in prev.get("posts", []):
                    if p.get("published"):
                        existing_published_ids.add(p.get("id"))
        except Exception:
            pass

    for p in posts:
        if p["id"] in existing_published_ids:
            p["published"] = True

    # If LinkedIn API token is configured, auto-publish next unpublished post (max 1 per day)
    api_status = "STAGED_FOR_LINKEDIN"
    if LINKEDIN_ACCESS_TOKEN and LINKEDIN_ORG_URN:
        for p in posts:
            if not p.get("published"):
                ok, detail = publish_via_linkedin_api(p["text"])
                if ok:
                    p["published"] = True
                    p["published_at"] = datetime.now(timezone.utc).isoformat()
                    api_status = detail
                else:
                    api_status = detail
                break

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
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
    run_linkedin_autoposter(generate_banner=True)

