from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()
import os
import sys
import csv

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import json
import re
from datetime import datetime, date
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
SITE_BASE_URL = os.getenv("SIGNALTENDER_SITE_URL", "https://signaltender.net").rstrip("/")

# Optional Zero-Touch Cold Email API Credentials (Option C)
INSTANTLY_API_KEY = os.getenv("INSTANTLY_API_KEY")
INSTANTLY_CAMPAIGN_ID = os.getenv("INSTANTLY_CAMPAIGN_ID")
SMARTLEAD_API_KEY = os.getenv("SMARTLEAD_API_KEY")
SMARTLEAD_CAMPAIGN_ID = os.getenv("SMARTLEAD_CAMPAIGN_ID")

TABLE_NAME = "contracts"
ERROR_LOG_PATH = r"D:\Daas\error_log.txt"
DOSSIER_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturedesk_dossiers.json")

# Tech filter regex array as per project_rules.md data integrity protocol
tech_keywords = [
    r"\bit\b", r"cyber(security)?", r"software", r"network", r"computer",
    r"server", r"infosec", r"audio/visual", r"hardware",
    r"technology", r"cloud", r"broadband", r"telecom", r"fiber",
    r"saas", r"data", r"system", r"digital", r"platform", r"web", r"infrastructure"
]

# Commodity IT & low-value renewal exclusions
commodity_it_exclusions = [
    r"bulk\s*mail(er)?",
    r"mail\s*manager",
    r"\bink\b",
    r"\btoner\b",
    r"cartridge",
    r"license\s*renewal",
    r"software\s*renewal",
    r"subscription\s*renewal",
    r"maintenance\s*renewal",
    r"support\s*renewal",
    r"seats?\s*renewal",
    r"saas\s*renewal",
    r"hardware\s*renewal",
    r"off-the-shelf",
    r"\bcots\b.*renewal",
    r"smartnet\s*renewal",
    r"smoke\s*and\s*fire",
    r"fire\s*detection\s*alarm",
    r"\bhvac\b",
    r"^50001",
    r"cor-(ent|off|pro|stp)",
    r"smart(-dt|-rti|-so|essential|mcms)",
    r"wts-mobile",
    r"software\s*support",
    r"software\s*subscription",
    r"software\s*synergy",
    r"25ecert",
    r"oms-500",
    r"virtual\s+printer\s+driver",
    r"sole\s*source",
    r"notice\s+of\s+intent",
    r"sngl\s+board\s+computer",
    r"single\s+board\s+computer",
]

STATE_ALIASES = {
    "tx": "tx", "texas": "tx",
    "va": "va", "virginia": "va",
    "ca": "ca", "california": "ca",
    "fl": "fl", "florida": "fl",
    "md": "md", "maryland": "md",
    "il": "il", "illinois": "il",
    "pa": "pa", "pennsylvania": "pa",
    "oh": "oh", "ohio": "oh",
    "ga": "ga", "georgia": "ga",
    "nc": "nc", "north carolina": "nc", "north_carolina": "nc",
}


def send_discord_alert(message: str):
    report_error("outreach_generator.py", str(message))
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": f"**[ALERT] Outreach Generator Alert:**\n{message}"},
            timeout=10,
        )
        response.raise_for_status()
    except Exception as e:
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"Failed to send Discord alert in outreach_generator.py: {e}\n")
        except Exception:
            pass


def parse_contract_date(date_str: str, title: str = "") -> date | None:
    """Parse MM/DD/YYYY or YYYY-MM-DD from closing_date or '- Due: MM/DD/YYYY' in title."""
    candidates = [str(date_str or "").strip()]
    m_title = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", str(title or ""), flags=re.IGNORECASE)
    if m_title:
        candidates.append(m_title.group(1))

    for cand in candidates:
        if not cand or cand.lower() in ["n/a", "tbd", "none", "null", ""]:
            continue
        if "T" in cand:
            cand = cand.split("T")[0].strip()
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
            try:
                return datetime.strptime(cand, fmt).date()
            except ValueError:
                pass
    return None


def is_contract_open(rec: dict, today: date | None = None) -> bool:
    """Return True if the contract has no closing date or its closing date is >= today."""
    ref_date = today or datetime.now().date()
    dt = parse_contract_date(rec.get("closing_date") or "", rec.get("title") or "")
    if dt is None:
        return True
    return dt >= ref_date


def clean_title_text(raw_title: str) -> str:
    s = str(raw_title or "").replace("\ufffd", "–").replace("\u202f", " ").replace("\u00a0", " ")
    s = re.sub(r"\bWeb-\s+Based\b", "Web-Based", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*-\s*Due:\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def slugify_contract(title: str, fallback_id: str = "") -> str:
    clean = clean_title_text(title).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", clean).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if len(slug) > 75:
        slug = slug[:75].rsplit("-", 1)[0].strip("-")
    if not slug:
        slug = "government-it-contract"
    return f"{slug}-{fallback_id}" if fallback_id else slug


def detect_contract_region(rec: dict) -> str:
    """Classify a Supabase contract record into 'tx', 'va', 'ca', 'fl', 'md', 'fed', or 'other'."""
    url = str(rec.get("url") or "").lower()
    agency = str(rec.get("agency") or "").lower()
    title = str(rec.get("title") or "")
    if "sam.gov" in url:
        return "fed"
    if "txsmartbuy.com" in url:
        return "tx"
    if "cgieva.com" in url or "eva.virginia.gov" in url:
        return "va"
    if "caleprocure.ca.gov" in url:
        return "ca"
    if "myfloridamarketplace.com" in url:
        return "fl"
    if "bidbuy.illinois.gov" in url or "transitchicago.bonfirehub.com" in url or "cookcountyil.bonfirehub.com" in url:
        return "il"
    if "emarketplace.state.pa.us" in url or "dgs.pa.gov" in url or "philaport.bonfirehub.com" in url:
        return "pa"
    if "doas.state.ga.us" in url or "georgia.gov" in url or "ga.gov" in url or "forsythco.bonfirehub.com" in url or "fultonschools.bonfirehub.com" in url or "cobbk12.bonfirehub.com" in url or "itsmarta.com" in url:
        return "ga"
    if "evp.nc.gov" in url or "nc.gov" in url or "unc.edu" in url or "ncsu.edu" in url or "wake.gov" in url or "mecknc.gov" in url or "charlottenc.gov" in url or "durhamnc.gov" in url or "guilfordcountync.gov" in url:
        return "nc"
    if "ohiobuys.ohio.gov" in url or "ohioauditor.gov" in url or "morpc.org" in url or "franklincountyohio.gov" in url or "columbus.bonfirehub.com" in url:
        return "oh"
    if "emma.maryland.gov" in url or "bonfirehub.com" in url:
        return "md"
    if "demandstar.com" in url:
        return "other"
    if title.startswith("[TX]") or "texas" in agency:
        return "tx"
    if title.startswith("[VA]") or "virginia" in agency:
        return "va"
    if title.startswith("[CA]") or "california" in agency:
        return "ca"
    if title.startswith("[FL]") or "florida" in agency:
        return "fl"
    if title.startswith("[IL]") or "state of illinois" in agency or "chicago transit authority" in agency or "cook county" in agency:
        return "il"
    if title.startswith("[PA]") or "pennsylvania" in agency or "philadelphia" in agency or agency.startswith("pa "):
        return "pa"
    if title.startswith("[GA]") or "georgia" in agency or "(ga)" in agency or "fulton county" in agency or "atlanta" in agency:
        return "ga"
    if title.startswith("[NC]") or "north carolina" in agency or "(nc)" in agency or "nc " in agency or "wake county" in agency or "mecklenburg" in agency or "charlotte" in agency:
        return "nc"
    if title.startswith("[OH]") or "ohio" in agency or "columbus" in agency or "morpc" in agency:
        return "oh"
    if title.startswith("[MD]") or "maryland" in agency or "prince george" in agency or "howard county" in agency:
        return "md"
    return "fed"


def resolve_contract_intelligence(rec: dict, dossiers: dict | None = None) -> dict:
    rec_id = str(rec.get("id") or "")
    raw_title = str(rec.get("title") or "Government IT Solicitation").strip()
    clean_t = clean_title_text(raw_title)
    agency = str(rec.get("agency") or "Public Agency").strip()
    closing_date = str(rec.get("closing_date") or "").strip()
    if not closing_date:
        m_due = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", raw_title, flags=re.IGNORECASE)
        closing_date = m_due.group(1) if m_due else "Open"
    slug = slugify_contract(raw_title, fallback_id=rec_id)
    dossier_url = f"{SITE_BASE_URL}/contracts/rfp/{slug}.html"

    cached = (dossiers or {}).get(rec_id, {}) if isinstance(dossiers, dict) else {}
    primary_naics = str(cached.get("primary_naics") or "541512 — Computer Systems Design Services")
    naics_code = primary_naics.split("—")[0].strip()
    sba_cap = str(cached.get("sba_size_standard") or "$34.0M annual receipts")

    reg = detect_contract_region(rec)
    blob_low = f"{clean_t} {agency}".lower()
    if cached.get("compliance_posture"):
        compliance_posture = str(cached["compliance_posture"])
    elif reg == "tx":
        compliance_posture = "TX-RAMP Level 2 • Texas DIR Security • TAC 206 VPAT"
    elif reg == "va":
        compliance_posture = "VITA SEC 530 Cloud Standard • SOC 2 Type II • VA VPAT"
    elif reg == "fl":
        compliance_posture = "FL FAC 60GG-2 / CJIS Security • SOC 2 Type II • VPAT"
    elif reg == "md":
        compliance_posture = "Maryland DoIT Security • NIST 800-53 • MD NVA VPAT"
    elif reg == "il":
        compliance_posture = "Illinois DoIT Security • SOC 2 Type II • IITAA 2.1 VPAT"
    elif reg == "pa":
        compliance_posture = "PA OA-ITB Security Policy • SOC 2 Type II • PA EIT VPAT"
    elif reg == "oh":
        compliance_posture = "Ohio DAS OIT Cloud Security • StateRAMP / NIST 800-53 • OH VPAT"
    elif reg == "ga":
        compliance_posture = "Georgia GTA SSG Security • StateRAMP / NIST 800-53 • GA VPAT"
    elif reg == "nc":
        compliance_posture = "NCDIT Statewide Security (NIST 800-53) • StateRAMP / SOC 2 Type II • NC VPAT"
    elif reg == "ca":
        compliance_posture = "CalCloud SIMM 5305-A • SOC 2 Type II • WCAG 2.1 AA"
    elif reg == "fed":
        if any(k in blob_low for k in ("dod", "defense", "army", "navy", "air force", "space force", "darpa", "disa")):
            compliance_posture = "CMMC 2.0 Level 2 • NIST 800-171 • DFARS 252.204-7012"
        else:
            compliance_posture = "FedRAMP Moderate • FAR 52.204-21 • Section 508 VPAT"
    else:
        compliance_posture = "SOC 2 Type II • NIST CSF 2.0 • Section 508 / WCAG 2.1 AA"

    if cached.get("teaming_posture"):
        teaming_posture = str(cached["teaming_posture"])
    elif reg == "tx":
        teaming_posture = "TX HUB Subcontracting Plan (26.0% Goal) + 3 TX/SLED Refs"
    elif reg == "va":
        teaming_posture = "Virginia DSBSD SWaM Plan (42% Goal) + 3 Public-Sector Refs"
    elif reg == "fl":
        teaming_posture = "FL OSD CMBE/VBE Teaming + 3 SLED Past Performance Refs"
    elif reg == "md":
        teaming_posture = "Maryland MBE (15%–29% Goal) + VSBE + 3 Public-Sector Refs"
    elif reg == "ca":
        teaming_posture = "CA DGS Small Business (5% Pref) + DVBE + 3 State Refs"
    else:
        teaming_posture = "13 CFR § 125.6 (50% Rule) + 3 CPARS Vol. III Past Perf Refs"

    win_themes = cached.get("win_themes") or []
    if win_themes and isinstance(win_themes, list):
        win_theme = re.sub(r"\*\*", "", str(win_themes[0])).strip()
    else:
        win_theme = f"Align phased implementation milestones, {compliance_posture.split('•')[0].strip()} readiness, and verifiable public-sector past performance directly with {agency}."

    return {
        "clean_title": clean_t,
        "agency": agency,
        "closing_date": closing_date,
        "slug": slug,
        "dossier_url": dossier_url,
        "naics_code": naics_code,
        "primary_naics": primary_naics,
        "sba_size_standard": sba_cap,
        "compliance_posture": compliance_posture,
        "teaming_posture": teaming_posture,
        "win_theme": win_theme,
    }


def format_contract_line(index: int, rec: dict, dossiers: dict | None = None) -> str:
    """Format a single contract row with NAICS & posture (deliverability-safe: zero '$' symbols in Step 1)."""
    info = resolve_contract_intelligence(rec, dossiers)
    clean_t = info["clean_title"]
    agency = info["agency"]
    closing_date = info["closing_date"]
    naics_code = info["naics_code"]
    short_posture = info["compliance_posture"].split("•")[0].strip()

    if closing_date and closing_date.lower() not in ["n/a", "none", "null", "tbd", "open"]:
        return f"{index}. {clean_t} — {agency} (Due: {closing_date} | NAICS {naics_code} • {short_posture})\n"
    return f"{index}. {clean_t} — {agency} (NAICS {naics_code} • {short_posture})\n"


def select_contracts_for_prospect(all_contracts: list[dict], prospect_state: str, max_count: int = 3) -> list[dict]:
    """
    Prioritize contracts matching the prospect's state + Federal (SAM.gov) contracts,
    then backfill with the freshest remaining B2B IT contracts up to max_count.
    """
    norm_state = STATE_ALIASES.get(str(prospect_state or "").strip().lower(), "")
    if not norm_state:
        return all_contracts[:max_count]

    state_matches = [c for c in all_contracts if detect_contract_region(c) == norm_state]
    fed_matches = [c for c in all_contracts if detect_contract_region(c) == "fed"]
    other_matches = [c for c in all_contracts if detect_contract_region(c) not in (norm_state, "fed")]

    combined = state_matches + fed_matches + other_matches
    return combined[:max_count]


import hashlib


STATE_DISPLAY_NAMES = {
    "tx": "Texas",
    "va": "Virginia",
    "ca": "California",
    "fl": "Florida",
    "md": "Maryland",
    "il": "Illinois",
    "pa": "Pennsylvania",
    "oh": "Ohio",
    "ga": "Georgia",
    "nc": "North Carolina",
}


def _pick_variant(seed_str: str, slot: int, options: list[str]) -> str:
    """Deterministically select a phrase variant per prospect + slot to defeat bulk spam fingerprinting."""
    digest = hashlib.sha256(f"{seed_str}::slot_{slot}".encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(options)
    return options[idx]


def build_two_step_outreach(
    fname: str,
    company: str,
    email: str,
    prospect_state: str,
    bid_count: int,
    payload_text: str,
    site_base_url: str,
    checkout_url: str,
    top_intel: dict | None = None,
) -> dict[str, str]:
    """
    Generate anti-spam rotated 2-step cold email copy (Step 1: Deliverability-Safe Value Drop;
    Step 2: Self-Serve Tier 1 $99/mo SignalWire + Tier 2 $399/mo CaptureDesk Autopilot)
    plus native Instantly/Smartlead {{RANDOM | ...}} Spintax strings.
    """
    norm_state = STATE_ALIASES.get(str(prospect_state or "").strip().lower(), "")
    region_label = f"{STATE_DISPLAY_NAMES[norm_state]} & Federal" if norm_state in STATE_DISPLAY_NAMES else "Federal & State SLED"
    clean_domain = site_base_url.replace("https://", "").replace("http://", "").strip("/")
    seed = f"{email.lower().strip()}::{datetime.now().strftime('%Y-%m-%d')}"

    # -------------------------------------------------------------------------
    # STEP 1 (TOUCH 1): DELIVERABILITY-FIRST LIVE RFP DROP (Zero $ signs, 1 clean domain ref)
    # -------------------------------------------------------------------------
    subject_variants = [
        f"{bid_count} open {region_label} IT bids for {company}",
        f"{region_label} IT & cyber RFPs for {company}",
        f"Active IT solicitations on the wire ({company})",
        f"{fname} - {bid_count} open public-sector IT RFPs",
        f"New {region_label} tech & cyber solicitations",
        f"Saw {company} / {bid_count} open IT contracts",
    ]
    greetings = [
        f"Hi {fname},",
        f"Hey {fname},",
        f"Hello {fname},",
        f"{fname} -",
    ]
    openers = [
        f"I run an automated procurement monitor that tracks SAM.gov, DemandStar, and 5 state SLED portals (TX, VA, CA, FL, MD) every 6 hours.",
        f"We maintain a live public-sector RFP engine covering Federal (SAM.gov), municipal (DemandStar), and 5 state procurement portals (TX, VA, CA, FL, MD).",
        f"I built a real-time government contract radar that pulls newly posted IT and cybersecurity bids across SAM.gov, DemandStar, and state SLED portals.",
        f"Our ingestion pipeline monitors Federal and 5 state procurement portals (TX, VA, CA, FL, MD) every 6 hours for high-signal IT & cyber solicitations.",
        f"I track newly released Federal and state SLED technology solicitations across SAM.gov, DemandStar, TX, VA, CA, FL, and MD.",
    ]
    relevance_lines = [
        f"Since {company} operates in the technology space, I pulled {bid_count} active solicitations that just hit the wire:",
        f"Noticed {company}'s work in the space and wanted to pass along {bid_count} live IT/cyber bids currently open for response:",
        f"Thought these {bid_count} open solicitations from our latest 6-hour crawl might be relevant to {company}'s pipeline:",
        f"Flagged {bid_count} open public-sector tech opportunities from today's feed that looked aligned with {company}:",
        f"Wanted to share {bid_count} newly posted IT & security contracts that just cleared our noise filter for {company}:",
    ]
    value_props = [
        f"Our classifier strips out 99% of commodity hardware, toner, and COTS renewal noise so capture teams only see net-new services and engineering scopes.",
        f"Everything is pre-filtered to remove low-value maintenance renewals and hardware reselling so your team only sees actionable IT & cyber RFPs.",
        f"We automatically filter out COTS renewals and non-technical clutter, indexing the clean solicitation dossiers on {clean_domain}.",
        f"Unlike legacy feeds cluttered with printer ink and license renewals, our pipeline isolates net-new software, cloud, and cybersecurity work on {clean_domain}.",
        f"Each solicitation is de-duplicated every 6 hours and published with direct agency source links on {clean_domain}.",
    ]
    step1_ctas = [
        f"You can view the full open directory at {clean_domain}/contracts — are you guys actively bidding public-sector IT right now, or should I take you off my radar?",
        f"The live dossiers are indexed at {clean_domain}/contracts — is public-sector IT/cyber on {company}'s radar this quarter?",
        f"You can inspect all open bids on {clean_domain} — worth sending over the direct agency links when new {region_label} IT scopes drop?",
        f"All open solicitations are posted on {clean_domain}/contracts — let me know if {company} is pursuing state or federal IT work right now.",
        f"You can browse the live wire at {clean_domain} — happy to point you to the raw RFP packages if any of these 3 fit your stack.",
    ]
    signoffs = [
        "Best,\nSignalTender Procurement Desk",
        "Regards,\nSignalTender Capture Intelligence",
        "Cheers,\nSignalTender Procurement Wire",
        "Best regards,\nSignalTender Intelligence Team",
    ]

    step1_subject = _pick_variant(seed, 1, subject_variants)
    step1_body = (
        f"{_pick_variant(seed, 2, greetings)}\n\n"
        f"{_pick_variant(seed, 3, openers)} "
        f"{_pick_variant(seed, 4, relevance_lines)}\n\n"
        f"{payload_text}\n"
        f"{_pick_variant(seed, 5, value_props)}\n\n"
        f"{_pick_variant(seed, 6, step1_ctas)}\n\n"
        f"{_pick_variant(seed, 7, signoffs)}"
    )

    # -------------------------------------------------------------------------
    # STEP 2 (TOUCH 2 - DAY +3): SELF-SERVE TIER 1 ($99/mo) & TIER 2 ($399/mo) PITCH
    # -------------------------------------------------------------------------
    step2_intros = [
        f"Quick follow-up in case {company} is building out its Federal or State SLED capture pipeline this quarter.",
        f"Following up briefly on the {region_label} IT solicitations I sent over earlier this week.",
        f"Circling back with one quick note in case your team tracks government IT & cybersecurity bids.",
        f"Wanted to follow up one last time regarding our automated Federal and 5-State SLED procurement wire.",
    ]
    intel_block = ""
    if top_intel:
        intel_block = (
            f"For example, on '{top_intel['clean_title']}' ({top_intel['agency']}), our CaptureDesk engine already pre-computed:\n"
            f"• Classification: NAICS {top_intel['primary_naics']} (SBA Cap: {top_intel['sba_size_standard']})\n"
            f"• Cyber & Clause Posture: {top_intel['compliance_posture']}\n"
            f"• Teaming & Past Performance: {top_intel['teaming_posture']}\n"
            f"• Dossier Preview: {top_intel['dossier_url']}\n\n"
        )

    step2_tiers = [
        (
            f"{intel_block}"
            f"Instead of paying $15,000+/yr for legacy GovWin or HigherGov seats, teams plug into SignalTender completely self-serve (zero sales calls or demos):\n\n"
            f"• Tier 1 — SignalWire Pro ($99/mo): Real-time 6-hour SAM.gov, DemandStar & 5-State SLED (TX, VA, CA, FL, MD) IT/Cyber alerts routed to Discord, Slack, MS Teams, or Webhook.\n"
            f"• Tier 2 — CaptureDesk Autopilot ($399/mo): Everything in Tier 1 + automated AI Section L/M Compliance Matrices, CPARS Past Performance Volume III citations, SF-30 Amendment Diffs, 13 CFR § 125.6 (50% Rule) Teaming Plans, FAR/DFARS/CMMC redlines, and 15 REST/MCP APIs (@signaltender/mcp-server)."
        ),
        (
            f"{intel_block}"
            f"We built SignalTender for lean capture teams and IT vendors that want real-time RFP intelligence at 90% less than legacy platforms:\n\n"
            f"1. SignalWire Pro ($99/mo): Instant 6-hour Federal + 5-State SLED IT/Cyber contract alerts delivered to your Discord, Slack, Teams, or CRM webhook.\n"
            f"2. CaptureDesk Autopilot ($399/mo): Full AI capture dossiers per RFP—including automated Shipley compliance matrices, CPARS Volume III past performance generators, SF-30 amendment diffs, security questionnaire responders, and 15 developer REST/MCP APIs."
        ),
        (
            f"{intel_block}"
            f"If {company} wants to automate bid discovery and proposal prep without annual lock-ins, we offer two instant self-serve tiers:\n\n"
            f"- SignalWire Pro ($99/mo): Live 7-portal Federal & SLED IT/Cyber RFP feed via Discord, Slack, Teams, or custom webhook.\n"
            f"- CaptureDesk Autopilot ($399/mo): Automated AI proposal outlines, Section L/M compliance matrices, CPARS past performance citations, 13 CFR § 125.6 teaming calculators, and Pwin capability matching on every solicitation."
        ),
    ]
    step2_closers = [
        f"You can test our interactive API playground or activate instant access in 60 seconds here:\n{checkout_url}\n\nNo contracts or onboarding calls—cancel anytime in 1 click.",
        f"Explore the live contract directory or start a month-to-month plan anytime at:\n{checkout_url}\n\n100% self-serve, no demos required.",
        f"Check out the live platform and instant checkout options right here:\n{checkout_url}\n\nIf public-sector IT isn't a focus for {company}, no worries at all—I won't follow up again.",
    ]

    step2_subject = f"Re: {step1_subject}"
    step2_body = (
        f"{_pick_variant(seed, 8, greetings)}\n\n"
        f"{_pick_variant(seed, 9, step2_intros)}\n\n"
        f"{_pick_variant(seed, 10, step2_tiers)}\n\n"
        f"{_pick_variant(seed, 11, step2_closers)}\n\n"
        f"{_pick_variant(seed, 12, signoffs)}"
    )

    # -------------------------------------------------------------------------
    # NATIVE INSTANTLY / SMARTLEAD {{RANDOM | ...}} SPINTAX TEMPLATES
    # -------------------------------------------------------------------------
    spintax_subject_1 = (
        f"{{{{RANDOM | {bid_count} open {region_label} IT bids for {company} | "
        f"{region_label} IT & cyber RFPs for {company} | "
        f"Active IT solicitations on the wire ({company}) | "
        f"{fname} - {bid_count} open public-sector IT RFPs}}}}"
    )
    spintax_body_1 = (
        f"{{{{RANDOM | Hi {fname}, | Hey {fname}, | Hello {fname},}}}}\n\n"
        f"{{{{RANDOM | I run an automated procurement monitor that tracks SAM.gov, DemandStar, and 5 state SLED portals (TX, VA, CA, FL, MD) every 6 hours. | "
        f"We maintain a live public-sector RFP engine covering Federal (SAM.gov), municipal (DemandStar), and 5 state procurement portals (TX, VA, CA, FL, MD). | "
        f"I built a real-time government contract radar that pulls newly posted IT and cybersecurity bids across SAM.gov, DemandStar, and state SLED portals.}}}} "
        f"{{{{RANDOM | Since {company} operates in the technology space, I pulled {bid_count} active solicitations that just hit the wire: | "
        f"Noticed {company}'s work in the space and wanted to pass along {bid_count} live IT/cyber bids currently open for response: | "
        f"Thought these {bid_count} open solicitations from our latest 6-hour crawl might be relevant to {company}'s pipeline:}}}}\n\n"
        f"{payload_text}\n"
        f"{{{{RANDOM | Our classifier strips out 99% of commodity hardware, toner, and COTS renewal noise so capture teams only see net-new services and engineering scopes. | "
        f"Everything is pre-filtered to remove low-value maintenance renewals and hardware reselling so your team only sees actionable IT & cyber RFPs. | "
        f"We automatically filter out COTS renewals and non-technical clutter, indexing the clean solicitation dossiers on {clean_domain}.}}}}\n\n"
        f"{{{{RANDOM | You can view the full open directory at {clean_domain}/contracts — are you guys actively bidding public-sector IT right now, or should I take you off my radar? | "
        f"The live dossiers are indexed at {clean_domain}/contracts — is public-sector IT/cyber on {company}'s radar this quarter? | "
        f"You can inspect all open bids on {clean_domain} — worth sending over the direct agency links when new {region_label} IT scopes drop?}}}}\n\n"
        f"{{{{RANDOM | Best, | Regards, | Cheers,}}}}\nSignalTender Procurement Desk"
    )
    spintax_body_2 = (
        f"{{{{RANDOM | Hi {fname}, | Hey {fname},}}}}\n\n"
        f"{{{{RANDOM | Quick follow-up in case {company} is building out its Federal or State SLED capture pipeline this quarter. | "
        f"Following up briefly on the {region_label} IT solicitations I sent over earlier this week. | "
        f"Circling back with one quick note in case your team tracks government IT & cybersecurity bids.}}}}\n\n"
        f"Instead of paying $15,000+/yr for legacy GovWin or HigherGov seats, teams plug into SignalTender completely self-serve (zero sales calls or demos):\n\n"
        f"• Tier 1 — SignalWire Pro ($99/mo): Real-time 6-hour SAM.gov, DemandStar & 5-State SLED (TX, VA, CA, FL, MD) IT/Cyber alerts routed to Discord, Slack, MS Teams, or Webhook.\n"
        f"• Tier 2 — CaptureDesk Autopilot ($399/mo): Everything in Tier 1 + automated AI Section L/M Compliance Matrices, CPARS Past Performance Volume III citations, SF-30 Amendment Diffs, 13 CFR § 125.6 (50% Rule) Teaming Plans, FAR/DFARS/CMMC redlines, and 15 REST/MCP APIs (@signaltender/mcp-server).\n\n"
        f"{intel_block}"
        f"{{{{RANDOM | You can test our interactive API playground or activate instant access in 60 seconds here: | "
        f"Explore the live contract directory or start a month-to-month plan anytime at:}}}}\n{checkout_url}\n\n"
        f"{{{{RANDOM | No contracts or onboarding calls—cancel anytime in 1 click. | 100% self-serve, no demos required.}}}}"
    )

    return {
        "Subject Line": step1_subject,
        "Email Body": step1_body,
        "Followup Subject": step2_subject,
        "Followup Body": step2_body,
        "Spintax Subject 1": spintax_subject_1,
        "Spintax Body 1": spintax_body_1,
        "Spintax Body 2": spintax_body_2,
        "Matched State": region_label,
        "Top Contract Dossier URL": (top_intel or {}).get("dossier_url", f"{site_base_url}/contracts"),
        "Top Contract NAICS": (top_intel or {}).get("primary_naics", "541512 — Computer Systems Design Services"),
        "Top Contract Posture": f"{(top_intel or {}).get('compliance_posture', '')} | {(top_intel or {}).get('teaming_posture', '')}".strip(" |"),
    }


def sync_leads_to_cold_email_api(leads_payload: list[dict]) -> None:
    """
    Option C: Zero-Touch Cold Email API Sync.
    Automatically pushes generated leads (including Step 1 + Step 2 + Spintax variables)
    directly to Instantly.ai or Smartlead.ai when INSTANTLY_API_KEY/INSTANTLY_CAMPAIGN_ID
    or SMARTLEAD_API_KEY/SMARTLEAD_CAMPAIGN_ID are configured in .env.
    """
    if not leads_payload:
        return

    # 1. Instantly.ai REST API Integration
    if INSTANTLY_API_KEY and INSTANTLY_CAMPAIGN_ID:
        try:
            print(f"[*] Pushing {len(leads_payload)} leads directly to Instantly.ai campaign {INSTANTLY_CAMPAIGN_ID}...", flush=True)
            instantly_leads = [
                {
                    "email": item["Email"],
                    "first_name": item["First Name"],
                    "company_name": item["Company"],
                    "custom_variables": {
                        "subject_line": item["Subject Line"],
                        "email_body": item["Email Body"],
                        "followup_subject": item.get("Followup Subject", ""),
                        "followup_body": item.get("Followup Body", ""),
                        "spintax_subject_1": item.get("Spintax Subject 1", ""),
                        "spintax_body_1": item.get("Spintax Body 1", ""),
                        "spintax_body_2": item.get("Spintax Body 2", ""),
                        "matched_state": item.get("Matched State", ""),
                    },
                }
                for item in leads_payload
            ]
            resp = requests.post(
                "https://api.instantly.ai/api/v1/lead/add",
                json={
                    "api_key": INSTANTLY_API_KEY,
                    "campaign_id": INSTANTLY_CAMPAIGN_ID,
                    "skip_if_in_workspace": True,
                    "leads": instantly_leads,
                },
                timeout=30,
            )
            resp.raise_for_status()
            print(f"[+] Successfully synced {len(instantly_leads)} leads (with 2-step + Spintax variables) to Instantly.ai!", flush=True)
        except Exception as inst_err:
            err_msg = f"Instantly.ai API sync warning: {inst_err}"
            print(f"[!] {err_msg}", flush=True)
            send_discord_alert(err_msg)

    # 2. Smartlead.ai REST API Integration
    if SMARTLEAD_API_KEY and SMARTLEAD_CAMPAIGN_ID:
        try:
            print(f"[*] Pushing {len(leads_payload)} leads directly to Smartlead.ai campaign {SMARTLEAD_CAMPAIGN_ID}...", flush=True)
            smartlead_leads = [
                {
                    "email": item["Email"],
                    "first_name": item["First Name"],
                    "company_name": item["Company"],
                    "custom_fields": {
                        "subject_line": item["Subject Line"],
                        "email_body": item["Email Body"],
                        "followup_subject": item.get("Followup Subject", ""),
                        "followup_body": item.get("Followup Body", ""),
                        "spintax_subject_1": item.get("Spintax Subject 1", ""),
                        "spintax_body_1": item.get("Spintax Body 1", ""),
                        "spintax_body_2": item.get("Spintax Body 2", ""),
                        "matched_state": item.get("Matched State", ""),
                    },
                }
                for item in leads_payload
            ]
            resp = requests.post(
                f"https://server.smartlead.ai/api/v1/campaigns/{SMARTLEAD_CAMPAIGN_ID}/leads?api_key={SMARTLEAD_API_KEY}",
                json={
                    "lead_list": smartlead_leads,
                    "settings": {
                        "ignore_global_block_list": False,
                        "ignore_unsubscribe_list": False,
                        "ignore_duplicate_leads_in_other_campaign": True,
                    },
                },
                timeout=30,
            )
            resp.raise_for_status()
            print(f"[+] Successfully synced {len(smartlead_leads)} leads (with 2-step + Spintax variables) to Smartlead.ai!", flush=True)
        except Exception as sl_err:
            err_msg = f"Smartlead.ai API sync warning: {sl_err}"
            print(f"[!] {err_msg}", flush=True)
            send_discord_alert(err_msg)


def generate_outreach():
    if not SUPABASE_URL or not SUPABASE_KEY:
        err = "SUPABASE_URL or SUPABASE_KEY not found in .env"
        print(f"[!] ERROR: {err}", flush=True)
        send_discord_alert(err)
        return

    try:
        print("[*] Connecting to Supabase to fetch active B2B IT contracts...", flush=True)
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        response = (
            supabase.table(TABLE_NAME)
            .select("*")
            .order("id", desc=True)
            .limit(200)
            .execute()
        )
        records = response.data if response and getattr(response, "data", None) else []

        if not records:
            print("[!] No contracts found in Supabase.", flush=True)
            return

        today = datetime.now().date()
        tech_contracts = []
        expired_skipped = 0

        for rec in records:
            if str(rec.get("url") or "").startswith("subscriber://") or str(rec.get("status") or "").startswith("SUBSCRIBER_"):
                continue
            title = str(rec.get("title") or "").strip()
            title_lower = title.lower()
            if not title:
                continue
            if any(re.search(pattern, title_lower) for pattern in commodity_it_exclusions):
                continue
            if not is_contract_open(rec, today=today):
                expired_skipped += 1
                continue
            if any(re.search(pattern, title_lower) for pattern in tech_keywords):
                tech_contracts.append(rec)

        if expired_skipped > 0:
            print(f"[*] Filtered out {expired_skipped} expired contract(s) with closing_date < {today}.", flush=True)

        if not tech_contracts:
            print("[!] FATAL: Zero open IT/Cyber contracts found in Supabase. Run mainscraper.py first.", flush=True)
            return

        cached_dossiers = {}
        if os.path.exists(DOSSIER_CACHE_PATH):
            try:
                with open(DOSSIER_CACHE_PATH, "r", encoding="utf-8") as df:
                    loaded_d = json.load(df)
                    if isinstance(loaded_d, dict):
                        cached_dossiers = loaded_d
            except Exception:
                cached_dossiers = {}

        default_top = tech_contracts[:3]
        default_payload_text = "".join(format_contract_line(i, r, cached_dossiers) for i, r in enumerate(default_top, 1))
        print(
            f"[+] Loaded {len(tech_contracts)} open, verified B2B IT contracts from Supabase.\n"
            f"Default Top {len(default_top)} Payload Preview:\n{default_payload_text}",
            flush=True,
        )

        apollo_file = "apollo-contacts.csv"
        output_file = "campaign_leads.csv"
        whop_checkout_url = os.getenv(
            "STRIPE_CHECKOUT_URL",
            f"{SITE_BASE_URL}/index.html#checkout",
        )

        if not os.path.exists(apollo_file):
            print(f"[!] Please ensure your exported Apollo file is named '{apollo_file}' and is in D:\\Daas", flush=True)
            return

        print("[*] Reading Apollo contacts and generating anti-spam Spintax 2-step sequences (Tier 1 $99/mo + Tier 2 $399/mo)...", flush=True)

        leads_for_api = []

        with open(apollo_file, mode="r", encoding="utf-8-sig") as infile, \
             open(output_file, mode="w", newline="", encoding="utf-8") as outfile:

            reader = csv.DictReader(infile)
            headers = reader.fieldnames or []

            first_name_key = "First Name"
            company_key = "Company" if "Company" in headers else ("Company Name" if "Company Name" in headers else "Company")
            email_key = "Email" if "Email" in headers else "Person Primary Email"
            state_key = next((h for h in ("State", "Company State", "Person State") if h in headers), None)

            out_fieldnames = [
                "First Name",
                "Email",
                "Company",
                "Subject Line",
                "Email Body",
                "Followup Subject",
                "Followup Body",
                "Spintax Subject 1",
                "Spintax Body 1",
                "Spintax Body 2",
                "Matched State",
                "Top Contract Dossier URL",
                "Top Contract NAICS",
                "Top Contract Posture",
            ]
            writer = csv.DictWriter(outfile, fieldnames=out_fieldnames)
            writer.writeheader()

            count = 0
            for row in reader:
                fname = (row.get(first_name_key) or "").strip() or "There"
                company = (row.get(company_key) or "").strip() or "your team"
                email = (row.get(email_key) or "").strip()
                prospect_state = (row.get(state_key) or "").strip() if state_key else ""

                if not email:
                    continue

                matched_contracts = select_contracts_for_prospect(tech_contracts, prospect_state, max_count=3)
                bid_count = len(matched_contracts)
                payload_text = "".join(format_contract_line(i, r, cached_dossiers) for i, r in enumerate(matched_contracts, 1))
                top_intel = resolve_contract_intelligence(matched_contracts[0], cached_dossiers) if matched_contracts else None

                sequence_data = build_two_step_outreach(
                    fname=fname,
                    company=company,
                    email=email,
                    prospect_state=prospect_state,
                    bid_count=bid_count,
                    payload_text=payload_text,
                    site_base_url=SITE_BASE_URL,
                    checkout_url=whop_checkout_url,
                    top_intel=top_intel,
                )

                lead_item = {
                    "First Name": fname,
                    "Email": email,
                    "Company": company,
                    **sequence_data,
                }
                writer.writerow(lead_item)
                leads_for_api.append(lead_item)
                count += 1

        print(
            f"[+] Success! Generated {count} anti-spam rotated 2-step sequences "
            f"(Step 1 Value Drop + Step 2 Tier 1 $99 / Tier 2 $399 Pitch) in {output_file}.",
            flush=True,
        )

        # Trigger Option C Zero-Touch Cold Email API Sync if credentials are set in .env
        sync_leads_to_cold_email_api(leads_for_api)

    except Exception as e:
        err_msg = f"outreach_generator.py error: {e}"
        print(f"[!] {err_msg}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n[!] {err_msg}\n")
        except Exception:
            pass
        send_discord_alert(err_msg)


if __name__ == "__main__":
    generate_outreach()