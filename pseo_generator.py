from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()
import os
import re
import json
import html
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
TABLE_NAME = "contracts"
ERROR_LOG_PATH = r"D:\Daas\error_log.txt"

SITE_BASE_URL = os.getenv("SIGNALTENDER_SITE_URL", "https://signaltender.net").rstrip("/")
WHOP_TIER1_URL = os.getenv(
    "STRIPE_TIER1_CHECKOUT_URL",
    f"{SITE_BASE_URL}/index.html#checkout-tier1",
)
WHOP_TIER2_URL = os.getenv(
    "STRIPE_TIER2_CHECKOUT_URL",
    f"{SITE_BASE_URL}/index.html#checkout-tier2",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "contracts")
SITEMAP_PATH = os.path.join(BASE_DIR, "sitemap.xml")
ROBOTS_PATH = os.path.join(BASE_DIR, "robots.txt")

JURISDICTIONS = {
    "federal": {
        "name": "Federal (SAM.gov)",
        "short": "Federal",
        "portal": "SAM.gov Federal Contracting",
        "badge_class": "bg-sky-500/10 text-sky-400 border-sky-500/30",
        "headline": "Open Federal IT, Cloud & Cybersecurity Contracts (SAM.gov)",
        "description": "Live pre-vetted federal government IT, software, cloud migration, and cybersecurity solicitations extracted from SAM.gov.",
    },
    "texas": {
        "name": "Texas (ESBD / DIR)",
        "short": "Texas",
        "portal": "Texas SmartBuy ESBD",
        "badge_class": "bg-indigo-500/10 text-indigo-300 border-indigo-500/30",
        "headline": "Open Texas State & Local IT Contracts (ESBD / SmartBuy)",
        "description": "Live Texas SLED IT, software development, telecom, and cybersecurity RFPs from the Electronic State Business Daily (ESBD).",
    },
    "virginia": {
        "name": "Virginia (eVA)",
        "short": "Virginia",
        "portal": "Virginia eVA Portal",
        "badge_class": "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
        "headline": "Open Virginia State & Municipal IT Solicitations (eVA)",
        "description": "Live Virginia eVA procurement opportunities for enterprise software, cloud infrastructure, cybersecurity, and IT consulting.",
    },
    "california": {
        "name": "California (Cal eProcure)",
        "short": "California",
        "portal": "California Cal eProcure (CSCR)",
        "badge_class": "bg-amber-500/10 text-amber-300 border-amber-500/30",
        "headline": "Open California State IT & Cybersecurity RFPs (Cal eProcure)",
        "description": "Live California State Contracts Register (Cal eProcure) solicitations for enterprise IT, cloud, and cybersecurity vendors.",
    },
    "florida": {
        "name": "Florida (MFMP VIP)",
        "short": "Florida",
        "portal": "Florida MyFloridaMarketPlace VIP",
        "badge_class": "bg-cyan-500/10 text-cyan-300 border-cyan-500/30",
        "headline": "Open Florida State IT, Software & Cloud Bids (MFMP VIP)",
        "description": "Live Florida Vendor Information Portal (MFMP VIP) IT invitations to negotiate (ITNs), RFPs, and agency technology bids.",
    },
    "maryland": {
        "name": "Maryland (eMMA & Bonfire)",
        "short": "Maryland",
        "portal": "Maryland eMMA & Agency Bonfire Portals",
        "badge_class": "bg-rose-500/10 text-rose-300 border-rose-500/30",
        "headline": "Open Maryland State, Judiciary & County IT Solicitations",
        "description": "Live Maryland state, judiciary, and county technology, telecom, and systems integration contracts.",
    },
    "illinois": {
        "name": "Illinois (BidBuy & CTA)",
        "short": "Illinois",
        "portal": "Illinois BidBuy & Chicago/Cook County",
        "badge_class": "bg-teal-500/10 text-teal-300 border-teal-500/30",
        "headline": "Open Illinois State, DoIT & Chicago IT Contracts (BidBuy)",
        "description": "Live Illinois BidBuy (DoIT, IDOT, CMS) and Chicago/Cook County solicitations for enterprise software, ERP, cloud, and telecom.",
    },
    "pennsylvania": {
        "name": "Pennsylvania (PA eMarketplace)",
        "short": "Pennsylvania",
        "portal": "PA DGS eMarketplace & PhilaPort",
        "badge_class": "bg-orange-500/10 text-orange-300 border-orange-500/30",
        "headline": "Open Pennsylvania State (DGS eMarketplace) & PhilaPort IT Contracts",
        "description": "Live Commonwealth of Pennsylvania DGS eMarketplace, PA JAGGAER, and Philadelphia Regional Port Authority IT, SaaS, cloud, and data solicitations.",
    },
    "ohio": {
        "name": "Ohio (OhioBuys & Metro)",
        "short": "Ohio",
        "portal": "OhioBuys, Auditor of State & Columbus/MORPC",
        "badge_class": "bg-lime-500/10 text-lime-300 border-lime-500/30",
        "headline": "Open Ohio State (OhioBuys / Auditor) & Columbus Metro IT Contracts",
        "description": "Live State of Ohio (OhioBuys / Auditor of State), MORPC (OARC), and Columbus/Franklin County IT, cloud, SaaS, data audit, and telecom solicitations.",
    },
    "georgia": {
        "name": "Georgia (GPR & Team GA)",
        "short": "Georgia",
        "portal": "Georgia Procurement Registry (GPR) & Metro",
        "badge_class": "bg-fuchsia-500/10 text-fuchsia-300 border-fuchsia-500/30",
        "headline": "Open Georgia State (DOAS GPR / Team Georgia) & Atlanta Metro IT Contracts",
        "description": "Live State of Georgia Procurement Registry (DOAS GPR / Team Georgia Marketplace), Fulton County, Atlanta Regional Commission, and Georgia Regents IT, cloud, AI, SaaS, ERP, and cybersecurity solicitations.",
    },
    "north_carolina": {
        "name": "North Carolina (NC eVP & Metro)",
        "short": "North Carolina",
        "portal": "NC eVP, NCDIT, UNC & Raleigh/Charlotte",
        "badge_class": "bg-violet-500/10 text-violet-300 border-violet-500/30",
        "headline": "Open North Carolina State (NC eVP / NCDIT), UNC & Raleigh/Charlotte IT Contracts",
        "description": "Live State of North Carolina electronic Vendor Portal (eVP / NCDIT), UNC System, Wake County (Raleigh), and Mecklenburg County (Charlotte) IT, cloud, SaaS, ERP, and cybersecurity solicitations.",
    },
    "new_york": {
        "name": "New York (NYC CROL, PASSPort & PANYNJ)",
        "short": "New York",
        "portal": "NYC CROL, PASSPort, Port Authority & NY Metro",
        "badge_class": "bg-blue-500/10 text-blue-300 border-blue-500/30",
        "headline": "Open New York State, NYC (CROL / PASSPort) & Port Authority IT Contracts",
        "description": "Live New York City (City Record Online / PASSPort / OTI / H+H), Port Authority of NY & NJ (PANYNJ), Suffolk County, and Rockland County IT, cloud, cybersecurity, data analytics, and GIS solicitations.",
    },
    "massachusetts": {
        "name": "Massachusetts (COMMBUYS & Boston)",
        "short": "Massachusetts",
        "portal": "MA COMMBUYS, EOTSS, OSD & City of Boston",
        "badge_class": "bg-pink-500/10 text-pink-300 border-pink-500/30",
        "headline": "Open Massachusetts State (COMMBUYS / EOTSS) & Boston IT Contracts",
        "description": "Live Commonwealth of Massachusetts COMMBUYS (EOTSS, OSD ITS78/ITS80, Trial Court, MassTech, MBTA, Massport) and City of Boston IT, cloud, cybersecurity, AI, and software solicitations.",
    },
    "municipal": {
        "name": "National Municipal (DemandStar)",
        "short": "Municipal SLED",
        "portal": "DemandStar Municipal Network",
        "badge_class": "bg-purple-500/10 text-purple-300 border-purple-500/30",
        "headline": "Open City, County & School District IT RFPs (DemandStar)",
        "description": "Live municipal, county, and public university IT and software solicitations monitored across the DemandStar SLED network.",
    },
}

CATEGORIES = {
    "cybersecurity": {
        "name": "Cybersecurity & InfoSec",
        "patterns": [r"cyber", r"infosec", r"zero[\s\-]*trust", r"siem", r"soc\b", r"security", r"iam\b", r"pam\b", r"firewall", r"audit"],
        "tags": ["Cybersecurity", "Zero-Trust / SOC", "Compliance"],
    },
    "cloud-infrastructure": {
        "name": "Cloud, Data Center & Servers",
        "patterns": [r"cloud", r"saas", r"server", r"storage", r"data\s*center", r"aws", r"azure", r"hosting", r"backup"],
        "tags": ["Cloud Architecture", "Enterprise SaaS", "Data Center"],
    },
    "software-development": {
        "name": "Enterprise Software, Data & AI Platforms",
        "patterns": [r"software", r"platform", r"system", r"data", r"analytics", r"intelligence", r"portal", r"web", r"digital", r"erp", r"lms", r"application"],
        "tags": ["Enterprise Software", "Systems Integration", "Data Platform"],
    },
    "network-telecom": {
        "name": "Network, Fiber, Telecom & Hardware",
        "patterns": [r"network", r"fiber", r"broadband", r"telecom", r"audio/visual", r"hardware", r"computer", r"wireless", r"intercom", r"aiphone", r"alert"],
        "tags": ["Network Infrastructure", "Telecom / Fiber", "Enterprise Hardware"],
    },
}

COMMODITY_IT_EXCLUSIONS = [
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
    r"software:?\s*synergy",
    r"25ecert",
    r"oms-500",
    r"virtual\s+printer\s+driver",
    r"\bassorted\s+hardware\b",
    r"^\d{2}--",
    r"\baiphone\b",
    r"\bdc\s+and\s+ac\s+preferred\s+systems\b",
    r"\bmissile\s+warning\s+system\b",
    r"\bf-5\s+aircraft\s+award\b",
    r"sole\s*source",
    r"notice\s+of\s+intent",
    r"sngl\s+board\s+computer",
    r"single\s+board\s+computer",
    r"computer\s+subassembl",
    r"server,\s*automatic\s*da",
    r"data\s+interface\s+unit",
    r"computer,\s*rackmount",
    r"synthetic\s+aperture\s+radar",
]


def is_commodity_it_spam(title: str) -> bool:
    if not title:
        return True
    t_lower = str(title).strip().lower()
    return any(re.search(pat, t_lower) for pat in COMMODITY_IT_EXCLUSIONS)



def send_discord_alert(message: str):
    report_error("pseo_generator.py", str(message))
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": f"**[ALERT] pSEO Generator Alert:**\n{message}"},
            timeout=10,
        )
    except Exception as e:
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"Failed to send Discord alert in pseo_generator.py: {e}\n")
        except Exception:
            pass


def parse_due_date(rec: dict) -> date | None:
    candidates = [str(rec.get("closing_date") or "").strip()]
    m_title = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", str(rec.get("title") or ""), flags=re.IGNORECASE)
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


def clean_display_title(raw_title: str) -> str:
    """Strip trailing '- Due: MM/DD/YYYY' and normalize encoding/spacing artifacts."""
    base = str(raw_title or "").replace("\ufffd", "–")
    base = re.sub(r"\bWeb-\s+Based\b", "Web-Based", base, flags=re.IGNORECASE)
    base = re.sub(r"\s*-\s*Due:\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$", "", base, flags=re.IGNORECASE)
    base = re.sub(r"\s{2,}", " ", base)
    return base.strip()


def slugify(text: str, fallback_id: str = "rfp") -> str:
    s = clean_display_title(text).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    if len(s) > 75:
        s = s[:75].rsplit("-", 1)[0].strip("-")
    if not s:
        return fallback_id
    return f"{s}-{fallback_id}"


def classify_jurisdiction(rec: dict) -> str:
    title = str(rec.get("title") or "").strip()
    agency = str(rec.get("agency") or "").strip().lower()
    url = str(rec.get("url") or rec.get("source_url") or "").strip().lower()

    if "demandstar.com" in url:
        return "municipal"
    if "sam.gov" in url or "sbir.gov" in url:
        return "federal"
    if "txsmartbuy.com" in url:
        return "texas"
    if "eva.virginia.gov" in url or "cgieva.com" in url:
        return "virginia"
    if "caleprocure.ca.gov" in url:
        return "california"
    if "myfloridamarketplace.com" in url:
        return "florida"
    if "bidbuy.illinois.gov" in url or "transitchicago.bonfirehub.com" in url or "cookcountyil.bonfirehub.com" in url:
        return "illinois"
    if "emarketplace.state.pa.us" in url or "dgs.pa.gov" in url or "philaport.bonfirehub.com" in url:
        return "pennsylvania"
    if (
        "ohiobuys.ohio.gov" in url
        or "ohioauditor.gov" in url
        or "morpc.org" in url
        or "franklincountyohio.gov" in url
        or "columbus.bonfirehub.com" in url
        or "cincinnati-oh.bonfirehub.com" in url
        or "westerville.bonfirehub.com" in url
        or "dps.bonfirehub.com" in url
        or "akronohio.bonfirehub.com" in url
    ):
        return "ohio"
    if (
        "doas.state.ga.us" in url
        or "georgia.gov" in url
        or "ga.gov" in url
        or "forsythco.bonfirehub.com" in url
        or "fultonschools.bonfirehub.com" in url
        or "cobbk12.bonfirehub.com" in url
        or "itsmarta.com" in url
    ):
        return "georgia"
    if (
        "evp.nc.gov" in url
        or "nc.gov" in url
        or "unc.edu" in url
        or "ncsu.edu" in url
        or "wake.gov" in url
        or "mecknc.gov" in url
        or "charlottenc.gov" in url
        or "durhamnc.gov" in url
        or "guilfordcountync.gov" in url
    ):
        return "north_carolina"
    if (
        "a856-cityrecord.nyc.gov" in url
        or "passport.cityofnewyork.us" in url
        or "cityofnewyork.us" in url
        or "panynj.bonfirehub.com" in url
        or "suffolkcountyny.bonfirehub.com" in url
        or "rocklandgov.bonfirehub.com" in url
        or "nyscr.ny.gov" in url
        or "ogs.ny.gov" in url
    ):
        return "new_york"
    if (
        "commbuys.com" in url
        or "mass.gov" in url
        or "boston.gov" in url
        or "mbta.com" in url
        or "massport.com" in url
        or "masstech.org" in url
    ):
        return "massachusetts"
    if "emma.maryland.gov" in url or "bonfirehub.com" in url:
        return "maryland"

    if title.startswith("[TX]") or "texas" in agency or ", tx" in agency or "ut md anderson" in agency:
        return "texas"
    if title.startswith("[VA]") or "virginia" in agency or "arlington county" in agency:
        return "virginia"
    if title.startswith("[CA]") or "california" in agency:
        return "california"
    if title.startswith("[FL]") or "florida" in agency:
        return "florida"
    if title.startswith("[IL]") or "state of illinois" in agency or "chicago transit authority" in agency or "cook county" in agency:
        return "illinois"
    if title.startswith("[PA]") or "pennsylvania" in agency or "philadelphia" in agency or agency.startswith("pa "):
        return "pennsylvania"
    if title.startswith("[GA]") or "georgia" in agency or "(ga)" in agency or "fulton county" in agency or "atlanta" in agency or "cobb county" in agency or "gwinnett" in agency or "dekalb" in agency:
        return "georgia"
    if title.startswith("[NC]") or "north carolina" in agency or "(nc)" in agency or "nc " in agency or "wake county" in agency or "mecklenburg" in agency or "charlotte" in agency or "raleigh" in agency or "durham" in agency or "guilford" in agency:
        return "north_carolina"
    if (
        title.startswith("[NY]")
        or "new york" in agency
        or "nyc " in agency
        or "(ny)" in agency
        or "panynj" in agency
        or "port authority of new york" in agency
        or "suffolk county" in agency
        or "rockland county" in agency
    ):
        return "new_york"
    if (
        title.startswith("[MA]")
        or "massachusetts" in agency
        or "(ma)" in agency
        or "commbuys" in agency
        or "city of boston" in agency
        or "boston public" in agency
        or "mbta" in agency
        or "massport" in agency
        or "eotss" in agency
    ):
        return "massachusetts"
    if title.startswith("[OH]") or "ohio" in agency or "columbus" in agency or "morpc" in agency or "franklin county" in agency:
        return "ohio"
    if title.startswith("[MD]") or "maryland" in agency or "prince george" in agency or "howard county" in agency:
        return "maryland"
    if "federal government" in agency:
        return "federal"
    return "municipal"

def classify_categories(rec: dict) -> list[str]:
    title_lower = str(rec.get("title") or "").lower()
    matched = []
    for cat_key, cat_meta in CATEGORIES.items():
        if any(re.search(pat, title_lower) for pat in cat_meta["patterns"]):
            matched.append(cat_key)
    if not matched:
        matched.append("software-development")
    return matched


def mask_agency_preview(agency: str) -> str:
    """Provide enough agency context for SEO indexing while keeping exact buyer contact gated."""
    a = str(agency or "Government Agency").strip()
    if len(a) <= 18:
        return a
    words = a.split()
    if len(words) >= 3:
        return " ".join(words[:2]) + " [Verified Agency]"
    return a


def _render_layout(
    page_title: str,
    meta_desc: str,
    canonical_path: str,
    body_html: str,
    json_ld: dict | None = None,
    root_prefix: str = "../",
    default_state: str = "all",
) -> str:
    escaped_title = html.escape(page_title)
    escaped_desc = html.escape(meta_desc)
    canonical_url = f"{SITE_BASE_URL}/{canonical_path.lstrip('/')}"
    ld_script = (
        f'<script type="application/ld+json">{json.dumps(json_ld)}</script>'
        if json_ld
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escaped_title}</title>
  <meta name="description" content="{escaped_desc}" />
  <link rel="icon" type="image/png" sizes="96x96" href="https://signaltender.net/contracts/favicon-96x96.png" />
  <link rel="icon" type="image/png" sizes="192x192" href="https://signaltender.net/contracts/favicon-192x192.png" />
  <link rel="icon" type="image/png" sizes="48x48" href="https://signaltender.net/contracts/favicon-48x48.png" />
  <link rel="icon" type="image/png" sizes="32x32" href="https://signaltender.net/contracts/favicon-32x32.png" />
  <link rel="icon" type="image/svg+xml" href="https://signaltender.net/contracts/favicon.svg" />
  <link rel="shortcut icon" href="https://signaltender.net/contracts/favicon.ico" />
  <link rel="apple-touch-icon" sizes="180x180" href="https://signaltender.net/contracts/apple-touch-icon.png" />
  <link rel="canonical" href="{canonical_url}" />
  <meta property="og:site_name" content="SignalTender" />
  <meta property="og:title" content="{escaped_title}" />
  <meta property="og:description" content="{escaped_desc}" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="{canonical_url}" />
  <meta property="og:image" content="https://raw.githubusercontent.com/aarbchen/signaltender-scraper/main/og-banner.png" />
  <meta property="og:image:type" content="image/png" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{escaped_title}" />
  <meta name="twitter:description" content="{escaped_desc}" />
  <meta name="twitter:image" content="https://raw.githubusercontent.com/aarbchen/signaltender-scraper/main/og-banner.png" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      darkMode: 'class',
      theme: {{
        extend: {{
          fontFamily: {{
            sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
            mono: ['JetBrains Mono', 'monospace'],
          }},
          colors: {{
            navy: {{
              950: '#050811',
              900: '#090E1A',
              800: '#0F172A',
              700: '#1E293B',
            }}
          }}
        }}
      }}
    }}
  </script>
  <style>
    span[class*="border"],
    span[class*="rounded"]:not(.animate-ping) {{
      display: inline-flex;
      align-items: center;
      white-space: nowrap;
      line-height: 1.2;
    }}
  </style>
  {ld_script}
</head>
<body class="bg-navy-950 text-slate-100 font-sans antialiased selection:bg-sky-500/30 selection:text-sky-200 min-h-screen flex flex-col justify-between">
  <div>
    <div class="border-b border-slate-800/80 bg-navy-900/90 text-xs">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-9 flex items-center justify-between">
        <div class="flex items-center space-x-2.5">
          <span class="inline-block h-2 w-2 rounded-full bg-emerald-500"></span>
          <span class="font-mono text-slate-300">LIVE GOVCON INTELLIGENCE WIRE &bull; <span class="text-emerald-400">14 PORTALS ACTIVE</span></span>
        </div>
        <div class="flex items-center space-x-4 font-mono text-slate-400">
          <a href="{root_prefix}index.html" class="hover:text-sky-400 transition-colors">&larr; Main Platform</a>
          <span>|</span>
          <a href="{root_prefix}apis.html" class="hover:text-sky-400 transition-colors">Developer APIs</a>
        </div>
      </div>
    </div>

    <header class="sticky top-0 z-50 backdrop-blur-md bg-navy-950/85 border-b border-slate-800/80">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <a href="{root_prefix}index.html" class="flex flex-col justify-center shrink-0">
          <div class="inline-flex items-center gap-[4px]">
            <svg class="w-[21px] h-[21px] shrink-0 -translate-y-[1px]" viewBox="6 5 52 54" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="32" cy="24" r="15" stroke="#F8FAFC" stroke-width="5.6" />
              <circle cx="32" cy="24" r="5" fill="#38BDF8" />
              <path d="M10 54L32 42L54 54" stroke="#38BDF8" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span class="text-[23px] font-semibold tracking-[-0.03em] text-white leading-none whitespace-nowrap">SignalTender</span>
            <span class="ml-1.5 inline-flex items-center whitespace-nowrap text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-slate-900 text-sky-400/90 border border-slate-800 leading-none">LIVE RFP INDEX</span>
          </div>
          <span class="text-[11px] font-mono text-slate-500 tracking-tight leading-none whitespace-nowrap mt-1">FEDERAL &amp; 12-STATE SLED CONTRACT DIRECTORY</span>
        </a>
        <nav class="hidden md:flex items-center space-x-6 text-xs font-mono text-slate-300 whitespace-nowrap">
          <a href="{root_prefix}contracts/index.html" class="hover:text-sky-400 transition-colors">All Portals</a>
          <a href="{root_prefix}contracts/federal/index.html" class="hover:text-sky-400 transition-colors">Federal</a>
          <a href="{root_prefix}contracts/texas/index.html" class="hover:text-sky-400 transition-colors">Texas</a>
          <a href="{root_prefix}contracts/virginia/index.html" class="hover:text-sky-400 transition-colors">Virginia</a>
          <a href="{root_prefix}contracts/california/index.html" class="hover:text-sky-400 transition-colors">California</a>
          <a href="{root_prefix}contracts/florida/index.html" class="hover:text-sky-400 transition-colors">Florida</a>
          <a href="{root_prefix}contracts/maryland/index.html" class="hover:text-sky-400 transition-colors">Maryland</a>
          <a href="{root_prefix}contracts/illinois/index.html" class="hover:text-sky-400 transition-colors">Illinois</a>
          <a href="{root_prefix}contracts/pennsylvania/index.html" class="hover:text-sky-400 transition-colors">Pennsylvania</a>
          <a href="{root_prefix}contracts/ohio/index.html" class="hover:text-sky-400 transition-colors">Ohio</a>
          <a href="{root_prefix}contracts/georgia/index.html" class="hover:text-sky-400 transition-colors">Georgia</a>
          <a href="{root_prefix}contracts/north_carolina/index.html" class="hover:text-sky-400 transition-colors">North Carolina</a>
          <a href="{root_prefix}contracts/new_york/index.html" class="hover:text-sky-400 transition-colors">New York</a>
          <a href="{root_prefix}contracts/massachusetts/index.html" class="hover:text-sky-400 transition-colors">Massachusetts</a>
        </nav>
        <a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center whitespace-nowrap px-4 py-2 text-xs font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg border border-sky-400/30 transition-all">
          Unlock All RFP Links &rarr;
        </a>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div id="outbound-prospect-banner" class="hidden mb-8 rounded-2xl bg-gradient-to-r from-emerald-950/90 via-navy-900 to-sky-950/90 border-2 border-emerald-500/50 p-4 sm:p-5 shadow-2xl">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div class="space-y-1">
            <div class="inline-flex items-center gap-2 text-[11px] font-mono text-emerald-300 uppercase tracking-wider">
              <span class="h-2 w-2 rounded-full bg-emerald-400"></span>
              <span id="prospect-banner-kicker">CUSTOM GOVCON CAPTURE BRIEFING</span>
            </div>
            <div id="prospect-banner-headline" class="text-base sm:text-lg font-extrabold text-white tracking-tight">
              Prepared for Your Capture Team &mdash; Live Pre-Shredded IT &amp; Cybersecurity Dossier
            </div>
            <p class="text-xs text-slate-300">
              All 14 Federal &amp; 12-State SLED Portals monitored every 6 hours. Zero annual contracts &bull; Instant 60-second self-serve activation.
            </p>
          </div>
          <div class="flex flex-wrap items-center gap-2.5 shrink-0 font-mono text-xs">
            <a id="prospect-banner-t1-btn" href="{root_prefix}index.html#checkout-tier1" class="px-3.5 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-semibold border border-sky-400/30 transition-all">
              Tier 1 Wire ($99/mo) &rarr;
            </a>
            <a id="prospect-banner-t2-btn" href="{root_prefix}index.html#checkout-tier2" class="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold border border-emerald-400/30 transition-all">
              Tier 2 Autopilot ($399/mo) &rarr;
            </a>
          </div>
        </div>
      </div>
      {body_html}

      <!-- Deliverable 2: State-Preselected Inbound Lead-Capture Funnel on All Static /contracts Pages -->
      <section id="static-inbound-lead-box" class="mt-12 rounded-2xl bg-gradient-to-r from-navy-900 via-slate-900/95 to-indigo-950/80 border-2 border-emerald-500/40 p-6 sm:p-8 shadow-2xl">
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          <div class="lg:col-span-5 space-y-2">
            <div class="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-[11px] font-mono text-emerald-300 uppercase tracking-wider">
              <span class="h-2 w-2 rounded-full bg-emerald-400"></span>
              Instant State RFP Dossier Drop &bull; Zero Credit Card
            </div>
            <h2 class="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
              Unlock 3 Live Pre-Shredded IT &amp; Cyber RFP Dossiers Free
            </h2>
            <p class="text-xs text-slate-300 leading-relaxed">
              Enter your work email and target jurisdiction. Our CaptureDesk engine will immediately unlock and email you <strong class="text-white">3 currently open IT/Cyber solicitations</strong> with pre-computed NAICS/SBA size caps, CMMC/NIST/StateRAMP posture, IGCE Price-to-Win bands, and direct official agency links.
            </p>
          </div>
          <div class="lg:col-span-7">
            <form id="static-lead-capture-form" onsubmit="event.preventDefault(); window.submitStaticLeadCapture();" class="grid grid-cols-1 sm:grid-cols-12 gap-3">
              <div class="sm:col-span-4">
                <label for="static-lead-email" class="sr-only">Work Email</label>
                <input id="static-lead-email" type="email" required placeholder="capture@yourcompany.com" class="w-full px-3.5 py-2.5 rounded-xl bg-navy-950 border border-slate-700 focus:border-emerald-400 focus:outline-none text-xs font-mono text-white placeholder-slate-500" />
              </div>
              <div class="sm:col-span-3">
                <label for="static-lead-company" class="sr-only">Company Name</label>
                <input id="static-lead-company" type="text" placeholder="Company / Prime LLC" class="w-full px-3.5 py-2.5 rounded-xl bg-navy-950 border border-slate-700 focus:border-emerald-400 focus:outline-none text-xs font-mono text-white placeholder-slate-500" />
              </div>
              <div class="sm:col-span-3">
                <label for="static-lead-state" class="sr-only">Target Portal</label>
                <select id="static-lead-state" data-default-state="{default_state}" class="w-full px-3 py-2.5 rounded-xl bg-navy-950 border border-slate-700 focus:border-emerald-400 focus:outline-none text-xs font-mono text-white">
                  <option value="all">All 14 Portals (Fed + 12 States)</option>
                  <option value="federal">Federal (SAM.gov)</option>
                  <option value="virginia">Virginia (eVA)</option>
                  <option value="texas">Texas (SmartBuy ESBD)</option>
                  <option value="california">California (Cal eProcure)</option>
                  <option value="florida">Florida (MFMP VIP)</option>
                  <option value="maryland">Maryland (eMMA &amp; Bonfire)</option>
                  <option value="illinois">Illinois (BidBuy)</option>
                  <option value="pennsylvania">Pennsylvania (eMarketplace)</option>
                  <option value="ohio">Ohio (OhioBuys)</option>
                  <option value="georgia">Georgia (GPR &amp; Team GA)</option>
                  <option value="north_carolina">North Carolina (NC eVP)</option>
                  <option value="new_york">New York (NYC CROL &amp; PASSPort)</option>
                  <option value="massachusetts">Massachusetts (COMMBUYS &amp; Boston)</option>
                  <option value="municipal">Municipal (DemandStar)</option>
                </select>
              </div>
              <div class="sm:col-span-2">
                <button id="static-lead-submit-btn" type="submit" class="w-full h-full px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-semibold border border-emerald-400/30 transition-all cursor-pointer whitespace-nowrap">
                  Unlock 3 &rarr;
                </button>
              </div>
            </form>
            <div id="static-lead-status" class="hidden mt-3 text-xs font-mono"></div>
            <div id="static-lead-results" class="hidden mt-4 grid grid-cols-1 md:grid-cols-3 gap-3"></div>
          </div>
        </div>
      </section>
    </main>
  </div>

  <footer class="border-t border-slate-800/80 bg-navy-900/50 py-8 mt-16 text-xs font-mono text-slate-400">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
      <div>&copy; {datetime.now().year} SignalTender. Real-Time Federal &amp; SLED Procurement Intelligence.</div>
      <div class="flex items-center space-x-4">
        <a href="{root_prefix}index.html" class="hover:text-white">Home</a>
        <a href="{root_prefix}contracts/index.html" class="hover:text-white">RFP Directory</a>
        <a href="{root_prefix}apis.html" class="hover:text-white">RapidAPI Catalog</a>
        <a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="text-sky-400 hover:underline">Subscribe</a>
        <a href="https://www.linkedin.com/company/signaltender/" target="_blank" rel="noopener noreferrer" aria-label="SignalTender on LinkedIn" title="SignalTender on LinkedIn" class="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-slate-900 hover:bg-sky-500/15 border border-slate-800 hover:border-sky-500/40 text-slate-400 hover:text-sky-400 transition-all">
          <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24" aria-hidden="true"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z"/></svg>
        </a>
      </div>
    </div>
  </footer>
  <script>
    window.filterStaticContractsTable = function (qVal) {{
      var anchorEl = document.getElementById('static-rfp-search') || document.activeElement;
      var anchorTopBefore = (anchorEl && anchorEl.getBoundingClientRect) ? anchorEl.getBoundingClientRect().top : null;
      var q = String(qVal || '').trim().toLowerCase();
      var tbody = document.querySelector('main table tbody');
      if (!tbody) return;
      var tblWrap = tbody.closest('.overflow-x-auto') || tbody.parentElement;
      if (tblWrap && !tblWrap.getAttribute('data-locked-min-h') && tblWrap.offsetHeight > 0) {{
        tblWrap.style.minHeight = tblWrap.offsetHeight + 'px';
        tblWrap.style.overflowAnchor = 'none';
        tblWrap.setAttribute('data-locked-min-h', '1');
      }}
      var rows = tbody.querySelectorAll('tr:not(#static-rfp-empty-row)');
      var shown = 0;
      for (var i = 0; i < rows.length; i++) {{
        var txt = (rows[i].innerText || '').toLowerCase();
        if (!q || txt.indexOf(q) !== -1) {{
          rows[i].classList.remove('hidden');
          shown++;
        }} else {{
          rows[i].classList.add('hidden');
        }}
      }}
      var badge = document.getElementById('static-rfp-count-badge');
      if (badge) {{
        badge.textContent = shown + ' OF ' + rows.length + ' SHOWN';
      }}
      var clearBtn = document.getElementById('static-rfp-clear-btn');
      if (clearBtn) {{
        if (q) clearBtn.classList.remove('hidden');
        else clearBtn.classList.add('hidden');
      }}
      var emptyRow = document.getElementById('static-rfp-empty-row');
      if (!emptyRow) {{
        emptyRow = document.createElement('tr');
        emptyRow.id = 'static-rfp-empty-row';
        emptyRow.className = 'hidden';
        emptyRow.innerHTML = '<td colspan="5" class="py-8 px-5 text-center font-mono text-xs text-slate-400">No solicitations matched that search query.</td>';
        tbody.appendChild(emptyRow);
      }}
      if (shown === 0 && rows.length > 0) emptyRow.classList.remove('hidden');
      else emptyRow.classList.add('hidden');
      if (anchorEl && anchorTopBefore !== null && anchorEl.getBoundingClientRect) {{
        var deltaY = anchorEl.getBoundingClientRect().top - anchorTopBefore;
        if (Math.abs(deltaY) > 0.5) {{
          var docEl = document.documentElement;
          var prevB = docEl.style.scrollBehavior;
          docEl.style.scrollBehavior = 'auto';
          window.scrollBy(0, deltaY);
          docEl.style.scrollBehavior = prevB;
        }}
      }}
    }};

    window.submitStaticLeadCapture = function () {{
      var emailEl = document.getElementById('static-lead-email');
      var compEl = document.getElementById('static-lead-company');
      var stateEl = document.getElementById('static-lead-state');
      var btnEl = document.getElementById('static-lead-submit-btn');
      var statusEl = document.getElementById('static-lead-status');
      var resultsEl = document.getElementById('static-lead-results');
      if (!emailEl || !stateEl) return;
      var email = String(emailEl.value || '').trim();
      var company = compEl ? String(compEl.value || '').trim() : '';
      var targetState = String(stateEl.value || 'all').trim();
      if (!email || email.indexOf('@') === -1) return;
      if (btnEl) {{
        btnEl.disabled = true;
        btnEl.textContent = 'Unlocking...';
      }}
      if (statusEl) {{
        statusEl.classList.remove('hidden');
        statusEl.className = 'mt-3 text-xs font-mono text-sky-300';
        statusEl.textContent = 'Querying live 14-portal CaptureDesk database & emailing your 3 dossiers...';
      }}
      fetch('https://b2b-contract-parser-api.onrender.com/v1/leads/capture', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          email: email,
          company: company,
          target_state: targetState,
          source_page: window.location.href
        }})
      }})
        .then(function (r) {{ return r.json(); }})
        .then(function (data) {{
          if (btnEl) {{
            btnEl.disabled = false;
            btnEl.textContent = 'Unlocked';
          }}
          var list = (data && data.dossiers) ? data.dossiers : [];
          if (statusEl) {{
            statusEl.className = 'mt-3 text-xs font-mono text-emerald-400';
            statusEl.textContent = 'Unlocked ' + list.length + ' live pre-shredded RFP dossiers (and queued your email copy):';
          }}
          try {{ if (window.localStorage) window.localStorage.setItem('st_unlocked_lead_email', email); }} catch (e) {{}}
          if (resultsEl && list.length > 0) {{
            resultsEl.classList.remove('hidden');
            resultsEl.innerHTML = list.map(function (d) {{
              var titleSafe = String(d.title || 'Open Solicitation').replace(/</g, '&lt;').replace(/>/g, '&gt;');
              var agencySafe = String(d.issuing_agency || 'Government Agency').replace(/</g, '&lt;').replace(/>/g, '&gt;');
              var dueSafe = String(d.closing_date || 'Open').replace(/</g, '&lt;').replace(/>/g, '&gt;');
              var rawDossier = String(d.dossier_url || '{root_prefix}contracts/index.html');
              var sep = rawDossier.indexOf('?') === -1 ? '?unlocked=1' : '&unlocked=1';
              var urlSafe = (rawDossier + sep).replace(/"/g, '&quot;');
              var bidUrlSafe = String(d.official_bid_url || rawDossier).replace(/"/g, '&quot;');
              return '<div class="p-3.5 rounded-xl bg-navy-950 hover:bg-slate-900 border border-emerald-500/40 transition-all flex flex-col justify-between">' +
                '<div>' +
                  '<div class="text-[10px] font-mono text-emerald-400 uppercase">' + agencySafe + '</div>' +
                  '<a href="' + urlSafe + '" class="text-xs font-bold text-white hover:text-sky-400 mt-1 line-clamp-2 block">' + titleSafe + '</a>' +
                '</div>' +
                '<div class="mt-2.5 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono">' +
                  '<span class="text-amber-300">Due: ' + dueSafe + '</span>' +
                  '<span class="flex items-center gap-2">' +
                    '<a href="' + bidUrlSafe + '" target="_blank" rel="noopener noreferrer" class="text-emerald-400 hover:underline">Portal &nearr;</a>' +
                    '<a href="' + urlSafe + '" class="text-sky-400 hover:underline">Dossier &rarr;</a>' +
                  '</span>' +
                '</div>' +
              '</div>';
            }}).join('');
          }}
        }})
        .catch(function () {{
          if (btnEl) {{
            btnEl.disabled = false;
            btnEl.textContent = 'Unlock 3';
          }}
        }});
    }};

    (function initStaticLeadAndAttribution() {{
      var sel = document.getElementById('static-lead-state');
      if (sel) {{
        var defSt = sel.getAttribute('data-default-state');
        if (defSt) sel.value = defSt;
      }}
      try {{
        var params = new URLSearchParams(window.location.search || '');
        var co = (params.get('co') || params.get('company') || '').trim();
        var fn = (params.get('fn') || params.get('first_name') || '').trim();
        var st = (params.get('st') || params.get('state') || '').trim();
        var utm = (params.get('utm_source') || 'outbound').trim();
        if (co && window.sessionStorage) {{
          window.sessionStorage.setItem('st_outbound_attrib', JSON.stringify({{ co: co, fn: fn, st: st, utm: utm }}));
        }} else if (!co && window.sessionStorage) {{
          var saved = window.sessionStorage.getItem('st_outbound_attrib');
          if (saved) {{
            var parsed = JSON.parse(saved);
            co = parsed.co || '';
            fn = parsed.fn || '';
            st = parsed.st || '';
            utm = parsed.utm || 'outbound';
          }}
        }}
        if (co) {{
          var banner = document.getElementById('outbound-prospect-banner');
          var kicker = document.getElementById('prospect-banner-kicker');
          var headline = document.getElementById('prospect-banner-headline');
          if (banner && headline) {{
            banner.classList.remove('hidden');
            var stUpper = st ? st.replace(/_/g, ' ').toUpperCase() : 'FEDERAL & SLED';
            if (kicker) kicker.textContent = 'PREPARED FOR ' + co.toUpperCase() + ' // ' + stUpper + ' CAPTURE BRIEFING';
            headline.textContent = (fn ? (fn + ' (' + co + ')') : co) + ' — Pre-Shredded Government IT & Cybersecurity RFP Dossier';
          }}
          var compInput = document.getElementById('static-lead-company');
          if (compInput && !compInput.value) compInput.value = co;
          fetch('https://b2b-contract-parser-api.onrender.com/v1/leads/track-click', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{
              company: co,
              first_name: fn,
              target_state: st || 'federal',
              event_type: 'dossier_view',
              page_url: window.location.href,
              utm_source: utm
            }})
          }}).catch(function () {{}});
        }}
        var isUnlocked = params.get('unlocked') === '1' || Boolean(window.localStorage && (window.localStorage.getItem('st_unlocked_lead_email') || window.localStorage.getItem('st_subscriber_active')));
        if (isUnlocked) {{
          var urlMask = document.getElementById('dossier-bid-url-mask');
          var agMask = document.getElementById('dossier-agency-mask');
          if (urlMask) {{
            var realU = urlMask.getAttribute('data-real-url') || '';
            urlMask.className = 'text-emerald-400 font-semibold';
            if (realU && realU.indexOf('http') === 0) {{
              urlMask.innerHTML = '<a href="' + realU.replace(/"/g, '&quot;') + '" target="_blank" rel="noopener noreferrer" class="underline hover:text-emerald-300">' + realU.replace(/</g, '&lt;') + ' &nearr;</a>';
            }}
          }}
          if (agMask) {{
            agMask.className = 'text-white font-semibold';
          }}
        }}
      }} catch (e) {{}}
    }})();
  </script>
</body>
</html>
"""


def _render_contract_table_rows(contracts: list[dict], rfp_link_prefix: str) -> str:
    if not contracts:
        return """
        <tr>
          <td colspan="5" class="py-8 px-5 text-center font-mono text-slate-400">
            New solicitations for this segment are currently being indexed by the 6-hour scraper cycle.
          </td>
        </tr>
        """
    rows_html = []
    for c in contracts:
        j_meta = JURISDICTIONS[c["jurisdiction"]]
        cat_key = c["categories"][0]
        cat_tags = CATEGORIES[cat_key]["tags"]
        tag_spans = "".join(
            f'<span class="px-2 py-0.5 rounded bg-navy-900 border border-slate-800 text-slate-300">{html.escape(t)}</span>'
            for t in cat_tags[:2]
        )
        due_display = html.escape(c["due_str"] or "Open / Rolling")
        rows_html.append(f"""
        <tr class="hover:bg-navy-900/60 transition-colors border-b border-slate-800/70">
          <td class="py-4 px-5 font-mono whitespace-nowrap">
            <span class="px-2.5 py-1 rounded border text-[11px] font-semibold {j_meta['badge_class']}">
              {html.escape(j_meta['short'].upper())}
            </span>
          </td>
          <td class="py-4 px-5">
            <a href="{rfp_link_prefix}{c['slug']}.html" class="font-bold text-white hover:text-sky-400 text-sm transition-colors block">
              {html.escape(c['clean_title'])}
            </a>
            <div class="flex flex-wrap gap-1.5 mt-1.5 font-mono text-[10px]">
              {tag_spans}
            </div>
          </td>
          <td class="py-4 px-4 text-slate-300 font-mono text-xs">
            {html.escape(c['masked_agency'])}
          </td>
          <td class="py-4 px-4 font-mono text-amber-300 whitespace-nowrap text-xs">
            {due_display}
          </td>
          <td class="py-4 px-5 text-right font-mono whitespace-nowrap">
            <a href="{rfp_link_prefix}{c['slug']}.html" class="inline-flex items-center px-3 py-1.5 rounded bg-slate-900 hover:bg-sky-600 hover:text-white border border-slate-700 text-sky-400 text-xs transition-colors">
              View Dossier &rarr;
            </a>
          </td>
        </tr>
        """)
    return "\n".join(rows_html)


def generate_pseo_site() -> int:
    if not SUPABASE_URL or not SUPABASE_KEY:
        err = "SUPABASE_URL or SUPABASE_KEY missing in .env; cannot build pSEO pages."
        print(f"[!] {err}", flush=True)
        send_discord_alert(err)
        return 0

    try:
        print("[*] Connecting to Supabase to fetch live contracts for pSEO static generation...", flush=True)
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        resp = (
            supabase.table(TABLE_NAME)
            .select("*")
            .in_("status", ["New Lead", "Delivered", "NEW"])
            .order("id", desc=True)
            .limit(500)
            .execute()
        )
        raw_records = resp.data if resp and getattr(resp, "data", None) else []
        if not raw_records:
            resp_fallback = (
                supabase.table(TABLE_NAME)
                .select("*")
                .order("id", desc=True)
                .limit(500)
                .execute()
            )
            raw_records = resp_fallback.data if resp_fallback and getattr(resp_fallback, "data", None) else []

        today = datetime.now().date()
        enriched_contracts = []
        seen_slugs = set()
        seen_titles = set()
        spam_ids_to_purge = []

        cached_dossiers = {}
        dossier_cache_path = os.path.join(BASE_DIR, "capturedesk_dossiers.json")
        if os.path.exists(dossier_cache_path):
            try:
                with open(dossier_cache_path, "r", encoding="utf-8") as df:
                    loaded_d = json.load(df)
                    if isinstance(loaded_d, dict):
                        cached_dossiers = loaded_d
            except Exception:
                cached_dossiers = {}

        for idx, rec in enumerate(raw_records, 1):
            if str(rec.get("url") or "").startswith("subscriber://") or str(rec.get("status") or "").startswith("SUBSCRIBER_"):
                continue
            raw_title = str(rec.get("title") or "").strip()
            if not raw_title:
                continue
            if is_commodity_it_spam(raw_title):
                if rec.get("id"):
                    spam_ids_to_purge.append(rec["id"])
                continue
            due_dt = parse_due_date(rec)
            if due_dt is not None and due_dt < today:
                continue

            rec_id = str(rec.get("id") or idx)
            norm_title = re.sub(r"[^a-z0-9]+", " ", clean_display_title(raw_title).lower()).strip()
            if norm_title in seen_titles:
                if rec.get("id"):
                    spam_ids_to_purge.append(rec["id"])
                continue
            seen_titles.add(norm_title)
            slug = slugify(raw_title, fallback_id=rec_id)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            j_key = classify_jurisdiction(rec)
            cats = classify_categories(rec)
            due_str = due_dt.strftime("%Y-%m-%d") if due_dt else ""
            clean_t = clean_display_title(raw_title)
            agency_str = str(rec.get("agency") or "Government Agency").strip()

            d_cached = cached_dossiers.get(rec_id, {}) if isinstance(cached_dossiers, dict) else {}
            if d_cached.get("primary_naics"):
                naics_display = str(d_cached["primary_naics"]).split("—")[0].strip() + " / 541512"
            elif "cloud-infrastructure" in cats:
                naics_display = "518210 / 541512"
            elif "cybersecurity" in cats:
                naics_display = "541519 / 541512"
            else:
                naics_display = "541512 / 541511"

            raw_sba = str(d_cached.get("sba_size_standard") or "$34.0M")
            sba_cap = raw_sba.split()[0] if raw_sba else "$34.0M"

            blob_low = f"{clean_t} {agency_str}".lower()
            if d_cached.get("compliance_posture"):
                compliance_posture = str(d_cached["compliance_posture"])
            elif j_key == "federal":
                if any(k in blob_low for k in ("dod", "defense", "army", "navy", "air force", "space force", "darpa", "disa")):
                    compliance_posture = "CMMC 2.0 L2 • NIST 800-171 • DFARS 252.204-7012"
                else:
                    compliance_posture = "FedRAMP Mod • FAR 52.204-21 • Section 508 VPAT"
            elif j_key == "texas":
                compliance_posture = "TX-RAMP Level 2 • DIR Security • TAC 206 VPAT"
            elif j_key == "virginia":
                compliance_posture = "VITA SEC 530 Cloud • SOC 2 Type II • VA VPAT"
            elif j_key == "florida":
                compliance_posture = "FL 60GG-2 / CJIS Security • SOC 2 Type II • VPAT"
            elif j_key == "maryland":
                compliance_posture = "MD DoIT Security • NIST 800-53 • MD NVA VPAT"
            elif j_key == "illinois":
                compliance_posture = "IL DoIT Security • SOC 2 Type II • IITAA 2.1 VPAT"
            elif j_key == "pennsylvania":
                compliance_posture = "PA OA-ITB Security • SOC 2 Type II • PA EIT VPAT"
            elif j_key == "ohio":
                compliance_posture = "Ohio DAS OIT Cloud Security • StateRAMP / NIST 800-53 • OH VPAT"
            elif j_key == "georgia":
                compliance_posture = "Georgia GTA SSG Security • StateRAMP / NIST 800-53 • GA VPAT"
            elif j_key == "north_carolina":
                compliance_posture = "NCDIT Statewide Security (NIST 800-53) • StateRAMP / SOC 2 Type II • NC VPAT"
            elif j_key == "new_york":
                compliance_posture = "NYC OTI Cyber Policies / NYS ITS-S14-003 • SOC 2 Type II • NIST 800-53"
            elif j_key == "massachusetts":
                compliance_posture = "MA EOTSS Enterprise Security (IS.000 / NIST 800-53) • SOC 2 Type II • MA VPAT"
            elif j_key == "california":
                compliance_posture = "CalCloud SIMM 5305-A • SOC 2 Type II • WCAG 2.1 AA"
            else:
                compliance_posture = "SOC 2 Type II • NIST CSF 2.0 • WCAG 2.1 AA VPAT"

            if d_cached.get("teaming_posture"):
                teaming_posture = str(d_cached["teaming_posture"])
            elif j_key == "federal":
                teaming_posture = "13 CFR § 125.6 (50% Rule) • Low Ostensible Sub Risk"
            elif j_key == "texas":
                teaming_posture = "TX HUB Plan (26.0% Goal) • Prime ≥51% Core Scope"
            elif j_key == "virginia":
                teaming_posture = "VA DSBSD SWaM (42% Goal) • Prime ≥51% Core Scope"
            elif j_key == "florida":
                teaming_posture = "FL OSD CMBE/VBE Teaming • Prime ≥51% Core Scope"
            elif j_key == "maryland":
                teaming_posture = "MD MBE (15–29%) + VSBE • Prime ≥51% Core Scope"
            elif j_key == "illinois":
                teaming_posture = "IL CEI BEP (20–30%) + VBP • Prime ≥51% Core Scope"
            elif j_key == "pennsylvania":
                teaming_posture = "PA BDISBO SDB/VBE (15–25%) • COSTARS/ITQ Eligible"
            elif j_key == "ohio":
                teaming_posture = "Ohio MBE (15% Goal) + EDGE (5%) • Ohio STS / MBE Set-Aside Eligible"
            elif j_key == "georgia":
                teaming_posture = "Georgia DOAS Small Business / MBE Sub Plan • GTA GETS Eligible"
            elif j_key == "north_carolina":
                teaming_posture = "NC DOA HUB (10%+ Minority/Small Goal) • NCDIT ITSTC Eligible"
            elif j_key == "new_york":
                teaming_posture = "NYS Art. 15-A MWBE (30% Goal) + SDVOB (6%) • NYC M/WBE Local Law 1"
            elif j_key == "massachusetts":
                teaming_posture = "MA OSD SDP (1%–15% MBE/WBE/SDVOBE Commitment) • ITS78/ITS80 Eligible"
            elif j_key == "california":
                teaming_posture = "CA DGS SB (5%) + DVBE • Prime ≥51% Core Scope"
            else:
                teaming_posture = "Local SBE/MWBE Sub Plan • Prime ≥51% Core Scope"

            locality_delta = {
                "federal": 8, "new_york": 10, "california": 9, "massachusetts": 7, "virginia": 6, "maryland": 6,
                "illinois": 3, "pennsylvania": 2, "texas": 1, "florida": 0, "ohio": -2, "georgia": 0, "north_carolina": -1, "municipal": -2,
            }.get(j_key, 0)
            id_jitter = (sum(ord(ch) for ch in rec_id) % 5) - 2
            if d_cached.get("igce_ptw_posture"):
                igce_ptw_posture = str(d_cached["igce_ptw_posture"])
            elif any(w in blob_low for w in ("servicenow", "itsm", "help desk", "service desk")):
                r1, r2 = 158 + locality_delta + id_jitter, 134 + locality_delta + id_jitter
                igce_ptw_posture = f"Wrap 1.79x • PTW -5.4% vs IGCE • ITSM Arch ${r1}/hr | Platform Eng ${r2}/hr"
            elif any(w in blob_low for w in ("siem", "soc", "vulnerability", "penetration", "zero trust", "cmmc", "edr", "firewall", "cyber")):
                r1, r2 = 172 + locality_delta + id_jitter, 151 + locality_delta + id_jitter
                igce_ptw_posture = f"Wrap 1.85x • PTW -4.2% vs IGCE • SecArch ${r1}/hr | Sr. SOC Eng ${r2}/hr"
            elif any(w in blob_low for w in ("gis", "geospatial", "esri", "mapping")):
                r1, r2 = 152 + locality_delta + id_jitter, 132 + locality_delta + id_jitter
                igce_ptw_posture = f"Wrap 1.77x • PTW -5.8% vs IGCE • GIS Solutions Arch ${r1}/hr | Spatial Dev ${r2}/hr"
            elif any(w in blob_low for w in ("erp", "peoplesoft", "workday", "oracle", "sap", "financial", "modernization")):
                r1, r2 = 169 + locality_delta + id_jitter, 149 + locality_delta + id_jitter
                igce_ptw_posture = f"Wrap 1.83x • PTW -4.8% vs IGCE • Principal ERP Arch ${r1}/hr | Functional Lead ${r2}/hr"
            elif any(w in blob_low for w in ("network", "cisco", "sd-wan", "broadband", "fiber", "wireless", "telecom")):
                r1, r2 = 156 + locality_delta + id_jitter, 136 + locality_delta + id_jitter
                igce_ptw_posture = f"Wrap 1.78x • PTW -5.6% vs IGCE • Sr. Network Arch ${r1}/hr | CCIE Lead ${r2}/hr"
            elif "cloud-infrastructure" in cats or any(w in blob_low for w in ("cloud", "aws", "azure", "hosting", "datacenter")):
                r1, r2 = 166 + locality_delta + id_jitter, 147 + locality_delta + id_jitter
                igce_ptw_posture = f"Wrap 1.82x • PTW -5.0% vs IGCE • Cloud Arch ${r1}/hr | DevSecOps Lead ${r2}/hr"
            else:
                r1, r2 = 161 + locality_delta + id_jitter, 142 + locality_delta + id_jitter
                igce_ptw_posture = f"Wrap 1.80x • PTW -5.3% vs IGCE • Solutions Arch ${r1}/hr | Lead Software Eng ${r2}/hr"

            if d_cached.get("key_personnel_lcats"):
                key_personnel_lcats = str(d_cached["key_personnel_lcats"])
            elif any(w in blob_low for w in ("servicenow", "itsm", "help desk", "service desk")):
                key_personnel_lcats = "ITSM Program Manager (ITIL v4/PMP) • Lead Platform Architect"
            elif any(w in blob_low for w in ("siem", "soc", "vulnerability", "penetration", "zero trust", "cmmc", "edr", "cyber")):
                key_personnel_lcats = "Cyber Program Manager (PMP/CISSP) • Lead SecOps / Zero-Trust Architect (CISSP)"
            elif any(w in blob_low for w in ("gis", "geospatial", "esri", "mapping")):
                key_personnel_lcats = "Geospatial Program Lead (GISP/PMP) • Principal Enterprise GIS Architect"
            elif any(w in blob_low for w in ("erp", "peoplesoft", "workday", "oracle", "sap", "modernization")):
                key_personnel_lcats = "ERP Transformation Director (PMP) • Lead Enterprise Integration Architect"
            elif any(w in blob_low for w in ("network", "cisco", "sd-wan", "broadband", "wireless", "telecom")):
                key_personnel_lcats = "Infrastructure PM (PMP) • Principal Network Security Engineer (CCIE/CCNP)"
            elif "cloud-infrastructure" in cats:
                key_personnel_lcats = "Cloud Delivery PM (PMP) • Principal Cloud & DevSecOps Architect (AWS/Azure)"
            else:
                key_personnel_lcats = "Engagement Program Manager (PMP/CSM) • Lead Enterprise Systems Architect"

            cpars_benchmark = str(d_cached.get("cpars_relevance_benchmark") or "Substantial Confidence • 3 Very Relevant Refs (5-Yr Window)")

            enriched_contracts.append({
                "id": rec_id,
                "slug": slug,
                "raw_title": raw_title,
                "clean_title": clean_t,
                "agency": agency_str,
                "masked_agency": mask_agency_preview(agency_str),
                "due_str": due_str,
                "url": str(rec.get("url") or ""),
                "jurisdiction": j_key,
                "categories": cats,
                "naics_display": naics_display,
                "sba_cap": sba_cap,
                "compliance_posture": compliance_posture,
                "teaming_posture": teaming_posture,
                "igce_ptw_posture": igce_ptw_posture,
                "key_personnel_lcats": key_personnel_lcats,
                "cpars_benchmark": cpars_benchmark,
            })

        if spam_ids_to_purge:
            try:
                supabase.table(TABLE_NAME).delete().in_("id", spam_ids_to_purge).execute()
                print(f"[+] Purged {len(spam_ids_to_purge)} legacy pre-filter catalog/spam row(s) from Supabase.", flush=True)
            except Exception as del_err:
                print(f"[!] Could not delete legacy spam rows from Supabase: {del_err}", flush=True)

        # Prepare directories and remove any stale/expired RFP HTML files
        rfp_dir = os.path.join(OUTPUT_DIR, "rfp")
        os.makedirs(rfp_dir, exist_ok=True)
        for existing_file in os.listdir(rfp_dir):
            if existing_file.endswith(".html"):
                try:
                    os.remove(os.path.join(rfp_dir, existing_file))
                except Exception:
                    pass
        for j_key in JURISDICTIONS:
            os.makedirs(os.path.join(OUTPUT_DIR, j_key), exist_ok=True)

        sitemap_urls = [
            f"{SITE_BASE_URL}/index.html",
            f"{SITE_BASE_URL}/apis.html",
            f"{SITE_BASE_URL}/contracts/index.html",
        ]
        pages_built = 0

        # 1. Build Individual Solicitation Dossier Pages (/contracts/rfp/<slug>.html)
        for c in enriched_contracts:
            j_meta = JURISDICTIONS[c["jurisdiction"]]
            cat_meta = CATEGORIES[c["categories"][0]]
            page_title = f"{c['clean_title']} | {j_meta['short']} Government IT RFP | SignalTender"
            meta_desc = (
                f"Active {j_meta['name']} solicitation: {c['clean_title']}. "
                f"Issued by {c['masked_agency']}. Closing date: {c['due_str'] or 'Open'}. "
                f"Unlock direct government portal link and AI capture dossier on SignalTender."
            )
            canonical_path = f"contracts/rfp/{c['slug']}.html"
            sitemap_urls.append(f"{SITE_BASE_URL}/{canonical_path}")

            related = [
                other for other in enriched_contracts
                if other["jurisdiction"] == c["jurisdiction"] and other["slug"] != c["slug"]
            ][:5]
            related_links_html = "".join(
                f'<li class="py-2 border-b border-slate-800/70"><a href="{r["slug"]}.html" class="text-sky-400 hover:underline font-medium">{html.escape(r["clean_title"])}</a> <span class="text-slate-500 font-mono text-xs ml-2">({html.escape(r["due_str"] or "Open")})</span></li>'
                for r in related
            ) or '<li class="text-slate-400">View more opportunities in the portal hub above.</li>'

            body_html = f"""
            <div class="mb-6 text-xs font-mono text-slate-400 flex flex-wrap items-center gap-2">
              <a href="../index.html" class="hover:text-sky-400">All Contracts</a>
              <span>/</span>
              <a href="../{c['jurisdiction']}/index.html" class="hover:text-sky-400">{html.escape(j_meta['name'])}</a>
              <span>/</span>
              <span class="text-slate-200">{html.escape(c['slug'][:40])}</span>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
              <div class="lg:col-span-8 space-y-6">
                <div class="p-6 sm:p-8 rounded-2xl bg-navy-900 border border-slate-800 shadow-2xl space-y-5">
                  <div class="flex flex-wrap items-center gap-2.5 font-mono text-xs">
                    <span class="px-2.5 py-1 rounded border font-semibold {j_meta['badge_class']}">{html.escape(j_meta['name'].upper())}</span>
                    <span class="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">STATUS: OPEN LEAD</span>
                    <span class="px-2.5 py-1 rounded bg-slate-800 text-slate-300">{html.escape(cat_meta['name'])}</span>
                  </div>

                  <h1 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-snug">
                    {html.escape(c['clean_title'])}
                  </h1>

                  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 font-mono text-xs">
                    <div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800">
                      <div class="text-slate-400">ISSUING AGENCY</div>
                      <div class="text-white font-semibold mt-1">{html.escape(c['masked_agency'])}</div>
                    </div>
                    <div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800">
                      <div class="text-slate-400">CLOSING DEADLINE</div>
                      <div class="text-amber-300 font-semibold mt-1">{html.escape(c['due_str'] or 'Active / See Portal')}</div>
                    </div>
                    <div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800">
                      <div class="text-slate-400">SOURCE PORTAL</div>
                      <div class="text-sky-400 font-semibold mt-1">{html.escape(j_meta['portal'])}</div>
                    </div>
                  </div>

                  <!-- Pre-Computed AI Capture Dossier & Gated Portal Link Box -->
                  <div class="mt-6 p-6 rounded-xl bg-navy-950 border-2 border-indigo-500/50 space-y-5">
                    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
                      <span class="text-xs font-mono uppercase tracking-wider text-indigo-300 font-bold">// CAPTUREDESK AI DOSSIER &amp; SOURCE PORTAL ACCESS</span>
                      <span class="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[10px] font-mono">AI-ENRICHED</span>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
                      <div class="p-3 rounded-lg bg-navy-900 border border-slate-800 space-y-1">
                        <div class="text-[10px] text-sky-400 font-bold">01. AI CLASSIFICATION (API #08)</div>
                        <div class="text-slate-200">NAICS <span class="text-white font-semibold">{html.escape(c['naics_display'])}</span> &bull; SBA Cap: <span class="text-emerald-400">{html.escape(c['sba_cap'])}</span></div>
                      </div>
                      <div class="p-3 rounded-lg bg-navy-900 border border-slate-800 space-y-1">
                        <div class="text-[10px] text-emerald-400 font-bold">02. IGCE, WRAP-RATE, PTW &amp; GSA MAS (API #03 / #16 / #20)</div>
                        <div class="text-slate-200">{html.escape(c['igce_ptw_posture'])}</div>
                      </div>
                      <div class="p-3 rounded-lg bg-navy-900 border border-slate-800 space-y-1">
                        <div class="text-[10px] text-indigo-400 font-bold">03. CYBER, CMMC, SPRS &amp; RMF/cATO (API #06 / #12 / #18)</div>
                        <div class="text-slate-200">{html.escape(c['compliance_posture'])}</div>
                      </div>
                      <div class="p-3 rounded-lg bg-navy-900 border border-slate-800 space-y-1">
                        <div class="text-[10px] text-amber-400 font-bold">04. 13 CFR &sect; 125.6 WORKSHARE &amp; TEAMING (API #11)</div>
                        <div class="text-slate-200">{html.escape(c['teaming_posture'])}</div>
                      </div>
                      <div class="p-3 rounded-lg bg-navy-900 border border-slate-800 space-y-1">
                        <div class="text-[10px] text-cyan-400 font-bold">05. KEY PERSONNEL LCATs (API #13)</div>
                        <div class="text-slate-200">{html.escape(c['key_personnel_lcats'])}</div>
                      </div>
                      <div class="p-3 rounded-lg bg-navy-900 border border-slate-800 space-y-1">
                        <div class="text-[10px] text-purple-300 font-bold">06. CPARS, ORALS &amp; DEBRIEF/PROTEST (API #15 / #17 / #19)</div>
                        <div class="text-slate-200">{html.escape(c['cpars_benchmark'])}</div>
                      </div>
                    </div>

                    <div class="space-y-2 text-xs font-mono text-slate-400 pt-1">
                      <div><strong class="text-slate-200">Official Government Bid URL:</strong> <span id="dossier-bid-url-mask" data-real-url="{html.escape(c['url'], quote=True)}" class="blur-sm select-none">https://portal.government.gov/solicitation/view/{c['id']}98412</span></div>
                      <div><strong class="text-slate-200">Full Issuing Buyer &amp; Contracting Officer:</strong> <span id="dossier-agency-mask" class="blur-sm select-none">{html.escape(c['agency'])} - Procurement Division</span></div>
                      <div><strong class="text-slate-200">Shipley Section L/M Compliance Matrix, SF-30 Diff &amp; CPARS Vol. III:</strong> <span class="blur-sm select-none">Pre-built in #capturedesk-autopilot &amp; API #05/#06/#14/#15/#16/#17/#18/#19/#20</span></div>
                    </div>
                    <div class="pt-3 flex flex-col sm:flex-row gap-3">
                      <a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center justify-center px-6 py-3 text-sm font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg shadow-lg transition-all">
                        Unlock Direct RFP Link &amp; Capture Dossier &rarr;
                      </a>
                      <a href="../../index.html#contracts/rfp/{c['slug']}" class="inline-flex items-center justify-center px-5 py-3 text-xs font-mono font-semibold text-emerald-300 bg-emerald-500/15 hover:bg-emerald-500/25 rounded-lg border border-emerald-500/40 transition-colors">
                        Run Live Pwin &amp; Shred in Studio &rarr;
                      </a>
                      <a href="../../apis.html#product-compliance-matrix" class="inline-flex items-center justify-center px-5 py-3 text-xs font-mono text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 rounded-lg border border-amber-500/30 transition-colors">
                        Shred via Shipley Compliance API &rarr;
                      </a>
                    </div>
                    <p class="text-[11px] font-mono text-slate-400">Instant 60-second Discord, Slack, Microsoft Teams &amp; CRM webhook activation. Cancel anytime.</p>
                  </div>
                </div>

                <div class="p-6 rounded-2xl bg-navy-900/60 border border-slate-800">
                  <h2 class="text-base font-bold text-white font-mono uppercase tracking-wider mb-3">More Open {html.escape(j_meta['short'])} IT Solicitations</h2>
                  <ul class="text-sm space-y-1">
                    {related_links_html}
                  </ul>
                </div>
              </div>

              <div class="lg:col-span-4 space-y-6">
                <div class="p-6 rounded-2xl bg-navy-900 border border-slate-800 space-y-4">
                  <div class="flex items-center justify-between">
                    <span class="text-xs font-mono text-sky-400 uppercase font-semibold">SIGNALWIRE PRO &bull; $99/MO</span>
                    <span class="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">$990/YR</span>
                  </div>
                  <div class="text-2xl font-extrabold text-white">Stop Hunting Portals Manually</div>
                  <p class="text-xs text-slate-300 leading-relaxed">
                    Get every pre-vetted Federal (SAM.gov), DemandStar, and 12-State SLED (TX, VA, CA, FL, MD, IL, PA, OH, GA, NC, NY, MA) IT &amp; cybersecurity solicitation pushed directly to your team every 6 hours.
                  </p>
                  <ul class="text-xs font-mono text-slate-300 space-y-2 pt-2">
                    <li>&check; 99.4% Commodity &amp; Renewal Spam Stripped</li>
                    <li>&check; Direct One-Click Official Portal Links</li>
                    <li>&check; Tier 2 CaptureDesk ($399/mo | $3,490/yr) Auto-Dossiers</li>
                  </ul>
                  <a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="w-full inline-flex items-center justify-center px-5 py-3 text-xs font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg transition-all">
                    Start Tier 1 Leads ($99/mo) &rarr;
                  </a>
                  <a href="{WHOP_TIER2_URL}" target="_blank" rel="noopener noreferrer" class="w-full inline-flex items-center justify-center px-5 py-2.5 text-xs font-mono font-semibold text-indigo-200 bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 rounded-lg transition-all">
                    Launch Tier 2 CaptureDesk ($399/mo) &rarr;
                  </a>
                </div>

                <div class="p-6 rounded-2xl bg-navy-900 border border-indigo-500/30 space-y-3">
                  <div class="text-xs font-mono text-indigo-400 uppercase font-semibold">20 LIVE APIs &amp; MCP SERVER</div>
                  <div class="text-lg font-bold text-white">Automate Your Bid Response</div>
                  <p class="text-xs text-slate-300 leading-relaxed">
                    Generate GSA MAS Schedule SIN matrices, 0.75% IFF ceiling rate cards &amp; GSAR 552.238-81 PRC compliance packages, analyze FAR 15.506 Post-Award Debriefings &amp; GAO Bid-Protest viability, generate NIST 800-53 Rev 5 RMF, Continuous ATO (cATO), SSP &amp; POA&amp;M packages, FAR 15.102 Oral Presentation &amp; Murder-Board prep, model IGCE wrap-rates &amp; Price-to-Win, generate CPARS &amp; Past Performance Volume III citations, diff SF-30 RFP amendments, tailor Key Personnel &amp; GSA LCAT resumes, auto-answer SOC 2, FedRAMP &amp; NIST 800-171 security questionnaires, generate 13 CFR &sect; 125.6 (50% Rule) teaming plans, extract Section B CLIN pricing tables, draft Shipley proposal narratives &amp; CO Q&amp;A, classify NAICS/SIC/PSC/UNSPSC codes, score Bid/No-Bid Pwin (0&ndash;100), audit FAR/DFARS &amp; CMMC 2.0 flow-downs, or shred this RFP into a compliance matrix via our 20 RapidAPI microservices &amp; <code class="text-indigo-200">@signaltender/mcp-server</code>.
                  </p>
                  <a href="../../apis.html#product-gsa-mas-offer" class="w-full inline-flex items-center justify-center px-4 py-2.5 text-xs font-mono font-semibold text-indigo-300 bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/40 rounded-lg transition-all">
                    Explore 20 APIs &amp; MCP Server &rarr;
                  </a>
                </div>
              </div>
            </div>
            """

            json_ld = {
                "@context": "https://schema.org",
                "@type": "GovernmentService",
                "name": c["clean_title"],
                "serviceType": cat_meta["name"],
                "provider": {
                    "@type": "GovernmentOrganization",
                    "name": c["masked_agency"],
                },
                "areaServed": j_meta["short"],
                "url": f"{SITE_BASE_URL}/{canonical_path}",
            }

            full_html = _render_layout(
                page_title=page_title,
                meta_desc=meta_desc,
                canonical_path=canonical_path,
                body_html=body_html,
                json_ld=json_ld,
                root_prefix="../../",
                default_state=c["jurisdiction"],
            )
            with open(os.path.join(rfp_dir, f"{c['slug']}.html"), "w", encoding="utf-8") as f:
                f.write(full_html)
            pages_built += 1

        # 2. Build Jurisdiction Hub Pages (/contracts/<jurisdiction>/index.html)
        #    and State x Category Pages (/contracts/<jurisdiction>/<category>.html)
        for j_key, j_meta in JURISDICTIONS.items():
            j_contracts = [c for c in enriched_contracts if c["jurisdiction"] == j_key]
            canonical_path = f"contracts/{j_key}/index.html"
            sitemap_urls.append(f"{SITE_BASE_URL}/{canonical_path}")

            cat_pills_html = "".join(
                f'<a href="{cat_k}.html" class="px-3 py-1.5 rounded-lg bg-navy-900 hover:bg-slate-800 border border-slate-700 text-xs font-mono text-sky-400 transition-colors">{html.escape(cat_m["name"])}</a>'
                for cat_k, cat_m in CATEGORIES.items()
            )
            rows_html = _render_contract_table_rows(j_contracts, rfp_link_prefix="../rfp/")

            body_html = f"""
            <div class="mb-8 space-y-4">
              <div class="inline-flex items-center px-3 py-1 rounded border text-xs font-mono {j_meta['badge_class']}">
                // {html.escape(j_meta['portal'].upper())} &bull; {len(j_contracts)} ACTIVE IT SOLICITATIONS
              </div>
              <h1 class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
                {html.escape(j_meta['headline'])}
              </h1>
              <p class="text-slate-300 text-sm sm:text-base max-w-3xl">
                {html.escape(j_meta['description'])} Filtered automatically every 6 hours by SignalTender&apos;s 3-layer B2B quality control engine.
              </p>
              <div class="flex flex-wrap gap-2 pt-2">
                {cat_pills_html}
              </div>
            </div>

            <div class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">
              <div class="p-4 bg-slate-900/70 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div class="relative flex-1 flex items-center">
                  <svg class="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10.5a7.5 7.5 0 0013.15 6.15z" />
                  </svg>
                  <input
                    id="static-rfp-search"
                    type="text"
                    placeholder="Filter solicitations by keyword, agency, technology, or due date..."
                    oninput="window.filterStaticContractsTable(this.value)"
                    class="w-full pl-10 pr-20 py-2 rounded-xl bg-navy-950 border border-slate-700/90 focus:border-sky-500 focus:outline-none text-xs font-mono text-white placeholder-slate-500"
                  />
                  <button
                    id="static-rfp-clear-btn"
                    type="button"
                    onclick="document.getElementById('static-rfp-search').value=''; window.filterStaticContractsTable('');"
                    class="hidden absolute right-2.5 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-300 border border-slate-700 cursor-pointer"
                  >
                    Clear
                  </button>
                </div>
                <span id="static-rfp-count-badge" class="text-xs font-mono text-emerald-400 shrink-0">LIVE FILTER READY</span>
              </div>
              <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                  <thead>
                    <tr class="border-b border-slate-800 bg-slate-900/90 text-[11px] font-mono uppercase tracking-wider text-slate-400">
                      <th class="py-4 px-5">Jurisdiction</th>
                      <th class="py-4 px-5">Solicitation Title &amp; Scope</th>
                      <th class="py-4 px-4">Issuing Agency</th>
                      <th class="py-4 px-4">Closing Date</th>
                      <th class="py-4 px-5 text-right">Dossier</th>
                    </tr>
                  </thead>
                  <tbody class="text-xs">
                    {rows_html}
                  </tbody>
                </table>
              </div>
            </div>
            """

            full_html = _render_layout(
                page_title=f"{j_meta['headline']} | SignalTender",
                meta_desc=j_meta["description"],
                canonical_path=canonical_path,
                body_html=body_html,
                root_prefix="../../",
                default_state=j_key,
            )
            with open(os.path.join(OUTPUT_DIR, j_key, "index.html"), "w", encoding="utf-8") as f:
                f.write(full_html)
            pages_built += 1

            # State x Category pages
            for cat_key, cat_meta in CATEGORIES.items():
                jc_contracts = [c for c in j_contracts if cat_key in c["categories"]]
                jc_canonical = f"contracts/{j_key}/{cat_key}.html"
                sitemap_urls.append(f"{SITE_BASE_URL}/{jc_canonical}")
                jc_rows = _render_contract_table_rows(jc_contracts, rfp_link_prefix="../rfp/")

                jc_body = f"""
                <div class="mb-6 text-xs font-mono text-slate-400 flex items-center gap-2">
                  <a href="../index.html" class="hover:text-sky-400">All Contracts</a>
                  <span>/</span>
                  <a href="index.html" class="hover:text-sky-400">{html.escape(j_meta['name'])}</a>
                  <span>/</span>
                  <span class="text-white">{html.escape(cat_meta['name'])}</span>
                </div>
                <div class="mb-8 space-y-3">
                  <h1 class="text-3xl font-extrabold text-white tracking-tight">
                    {html.escape(j_meta['short'])} {html.escape(cat_meta['name'])} Government Contracts &amp; RFPs
                  </h1>
                  <p class="text-slate-300 text-sm max-w-3xl">
                    Browse {len(jc_contracts)} open {html.escape(cat_meta['name'].lower())} solicitations from {html.escape(j_meta['portal'])}.
                  </p>
                </div>
                <div class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">
              <div class="p-4 bg-slate-900/70 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div class="relative flex-1 flex items-center">
                  <svg class="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10.5a7.5 7.5 0 0013.15 6.15z" />
                  </svg>
                  <input
                    id="static-rfp-search"
                    type="text"
                    placeholder="Filter solicitations by keyword, agency, technology, or due date..."
                    oninput="window.filterStaticContractsTable(this.value)"
                    class="w-full pl-10 pr-20 py-2 rounded-xl bg-navy-950 border border-slate-700/90 focus:border-sky-500 focus:outline-none text-xs font-mono text-white placeholder-slate-500"
                  />
                  <button
                    id="static-rfp-clear-btn"
                    type="button"
                    onclick="document.getElementById('static-rfp-search').value=''; window.filterStaticContractsTable('');"
                    class="hidden absolute right-2.5 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-300 border border-slate-700 cursor-pointer"
                  >
                    Clear
                  </button>
                </div>
                <span id="static-rfp-count-badge" class="text-xs font-mono text-emerald-400 shrink-0">LIVE FILTER READY</span>
              </div>
              <div class="overflow-x-auto">
                    <table class="w-full text-left border-collapse">
                      <thead>
                        <tr class="border-b border-slate-800 bg-slate-900/90 text-[11px] font-mono uppercase tracking-wider text-slate-400">
                          <th class="py-4 px-5">Jurisdiction</th>
                          <th class="py-4 px-5">Solicitation Title &amp; Scope</th>
                          <th class="py-4 px-4">Issuing Agency</th>
                          <th class="py-4 px-4">Closing Date</th>
                          <th class="py-4 px-5 text-right">Dossier</th>
                        </tr>
                      </thead>
                      <tbody class="text-xs">
                        {jc_rows}
                      </tbody>
                    </table>
                  </div>
                </div>
                """
                jc_html = _render_layout(
                    page_title=f"{j_meta['short']} {cat_meta['name']} RFPs & Government Contracts | SignalTender",
                    meta_desc=f"Live open {j_meta['short']} {cat_meta['name']} RFPs and government solicitations from {j_meta['portal']}.",
                    canonical_path=jc_canonical,
                    body_html=jc_body,
                    root_prefix="../../",
                    default_state=j_key,
                )
                with open(os.path.join(OUTPUT_DIR, j_key, f"{cat_key}.html"), "w", encoding="utf-8") as f:
                    f.write(jc_html)
                pages_built += 1

        # 3. Build Master Directory Index (/contracts/index.html)
        jurisdiction_cards_html = ""
        for j_key, j_meta in JURISDICTIONS.items():
            cnt = sum(1 for c in enriched_contracts if c["jurisdiction"] == j_key)
            jurisdiction_cards_html += f"""
            <a href="{j_key}/index.html" class="p-5 rounded-xl bg-navy-900 hover:bg-slate-900 border border-slate-800 hover:border-sky-500/50 transition-all flex flex-col justify-between">
              <div>
                <span class="px-2.5 py-0.5 rounded border text-[10px] font-mono font-semibold {j_meta['badge_class']}">{html.escape(j_meta['short'].upper())}</span>
                <h2 class="text-lg font-bold text-white mt-3">{html.escape(j_meta['name'])}</h2>
                <p class="text-xs text-slate-400 mt-1">{html.escape(j_meta['description'])}</p>
              </div>
              <div class="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono">
                <span class="text-emerald-400">{cnt} Open Leads</span>
                <span class="text-sky-400">Browse Hub &rarr;</span>
              </div>
            </a>
            """

        all_rows_html = _render_contract_table_rows(enriched_contracts[:100], rfp_link_prefix="rfp/")
        hub_body = f"""
        <div class="mb-10 space-y-4">
          <div class="inline-flex items-center px-3 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-xs font-mono text-emerald-400">
            // LIVE GOVCON DIRECTORY &bull; {len(enriched_contracts)} VERIFIED OPEN IT SOLICITATIONS
          </div>
          <h1 class="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            Federal &amp; State SLED IT Contract Directory
          </h1>
          <p class="text-slate-300 text-base max-w-3xl">
            Explore {len(enriched_contracts)} live, AI-vetted government IT, software, cloud, and cybersecurity RFPs across SAM.gov, DemandStar, Texas, Virginia, California, Florida, Maryland, Illinois, Pennsylvania, Ohio, Georgia, North Carolina, New York, and Massachusetts.
          </p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
          {jurisdiction_cards_html}
        </div>

        <h2 class="text-xl font-bold text-white font-mono uppercase tracking-wider mb-4">Latest Pre-Vetted Solicitations</h2>
        <div class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">
              <div class="p-4 bg-slate-900/70 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div class="relative flex-1 flex items-center">
                  <svg class="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10.5a7.5 7.5 0 0013.15 6.15z" />
                  </svg>
                  <input
                    id="static-rfp-search"
                    type="text"
                    placeholder="Filter solicitations by keyword, agency, technology, or due date..."
                    oninput="window.filterStaticContractsTable(this.value)"
                    class="w-full pl-10 pr-20 py-2 rounded-xl bg-navy-950 border border-slate-700/90 focus:border-sky-500 focus:outline-none text-xs font-mono text-white placeholder-slate-500"
                  />
                  <button
                    id="static-rfp-clear-btn"
                    type="button"
                    onclick="document.getElementById('static-rfp-search').value=''; window.filterStaticContractsTable('');"
                    class="hidden absolute right-2.5 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-300 border border-slate-700 cursor-pointer"
                  >
                    Clear
                  </button>
                </div>
                <span id="static-rfp-count-badge" class="text-xs font-mono text-emerald-400 shrink-0">LIVE FILTER READY</span>
              </div>
              <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-slate-800 bg-slate-900/90 text-[11px] font-mono uppercase tracking-wider text-slate-400">
                  <th class="py-4 px-5">Jurisdiction</th>
                  <th class="py-4 px-5">Solicitation Title &amp; Scope</th>
                  <th class="py-4 px-4">Issuing Agency</th>
                  <th class="py-4 px-4">Closing Date</th>
                  <th class="py-4 px-5 text-right">Dossier</th>
                </tr>
              </thead>
              <tbody class="text-xs">
                {all_rows_html}
              </tbody>
            </table>
          </div>
        </div>
        """

        hub_html = _render_layout(
            page_title="Live Government IT & Cybersecurity Contracts Directory (Federal & SLED) | SignalTender",
            meta_desc="Browse live pre-vetted Federal (SAM.gov) and State SLED (TX, VA, CA, FL, MD, IL, PA, OH, GA, NC, NY, MA) IT, software, cloud, and cybersecurity RFPs.",
            canonical_path="contracts/index.html",
            body_html=hub_body,
            root_prefix="../",
        )
        with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
            f.write(hub_html)
        pages_built += 1

        # 4. Generate sitemap.xml and robots.txt
        today_iso = today.strftime("%Y-%m-%d")
        sitemap_entries = "\n".join(
            f"  <url>\n    <loc>{html.escape(u)}</loc>\n    <lastmod>{today_iso}</lastmod>\n    <changefreq>daily</changefreq>\n  </url>"
            for u in sitemap_urls
        )
        sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{sitemap_entries}
</urlset>
"""
        with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
            f.write(sitemap_xml)

        robots_txt = f"""User-agent: *
Allow: /

Sitemap: {SITE_BASE_URL}/sitemap.xml
"""
        with open(ROBOTS_PATH, "w", encoding="utf-8") as f:
            f.write(robots_txt)

        indexnow_key = "8f9d2a4c6e1b3f5a7d0c9e2b4a6f8d1c"
        with open(os.path.join(OUTPUT_DIR, f"{indexnow_key}.txt"), "w", encoding="utf-8") as f:
            f.write(indexnow_key)

        # 5. Inject embedded SPA directory & dossier router into index.html
        #    so isolated single-HTML deployments (like signaltender.net on Render)
        #    serve all State Hubs, Category Filters, and RFP Dossiers with zero 404s.
        _inject_spa_directory_into_index(enriched_contracts)

        # 6. Run automated JS syntax, SPA runtime, and DOM parity verification
        import verify_site_integrity
        verify_site_integrity.main()

        # 7. Ping IndexNow (Bing, Copilot, DuckDuckGo, Yandex, Perplexity, ChatGPT Search)
        try:
            import indexnow_ping
            indexnow_ping.submit_indexnow_urls()
        except Exception as _ix_err:
            print(f"[IndexNow] Warning: {_ix_err}", flush=True)

        print(
            f"[+] Programmatic SEO build complete! Generated {pages_built} static HTML pages in /contracts "
            f"({len(enriched_contracts)} individual RFP dossiers + 36 state/category hubs), updated sitemap.xml, "
            f"and synced embedded SPA directory in index.html.",
            flush=True,
        )
        return pages_built

    except (Exception, SystemExit) as e:
        if isinstance(e, SystemExit) and e.code in (0, None):
            return pages_built
        err_msg = f"pseo_generator.py error: {e}"
        print(f"[!] {err_msg}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n[!] {err_msg}\n")
        except Exception:
            pass
        send_discord_alert(err_msg)
        return 0


def _inject_spa_directory_into_index(enriched_contracts: list[dict]):
    index_path = os.path.join(BASE_DIR, "index.html")
    if not os.path.exists(index_path):
        return

    with open(index_path, "r", encoding="utf-8") as f:
        index_html = f.read()

    # 1. Update PSEO_HUB_BAR_START .. PSEO_HUB_BAR_END
    hub_bar_html = f"""<!-- PSEO_HUB_BAR_START -->
          <div class="px-6 py-4 bg-slate-900/90 border-t border-slate-800 flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
            <div class="flex flex-wrap items-center gap-2 text-slate-300">
              <span class="text-slate-400">BROWSE STATE HUBS:</span>
              <a href="#contracts/federal" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-sky-400">Federal (SAM)</a>
              <a href="#contracts/texas" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-indigo-300">Texas</a>
              <a href="#contracts/virginia" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-emerald-400">Virginia</a>
              <a href="#contracts/california" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-amber-300">California</a>
              <a href="#contracts/florida" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-cyan-300">Florida</a>
              <a href="#contracts/maryland" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-rose-300">Maryland</a>
              <a href="#contracts/illinois" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-teal-300">Illinois</a>
              <a href="#contracts/pennsylvania" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-orange-300">Pennsylvania</a>
              <a href="#contracts/ohio" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-lime-300">Ohio</a>
              <a href="#contracts/georgia" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-fuchsia-300">Georgia</a>
              <a href="#contracts/north_carolina" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-violet-300">North Carolina</a>
              <a href="#contracts/new_york" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-blue-300">New York</a>
              <a href="#contracts/massachusetts" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-pink-300">Massachusetts</a>
              <a href="#contracts/municipal" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-purple-300">Municipal</a>
            </div>
            <a href="#contracts" class="text-sky-400 hover:text-sky-300 font-semibold">
              Explore All {len(enriched_contracts)} Live IT &amp; Cyber Solicitations &rarr;
            </a>
          </div>
          <!-- PSEO_HUB_BAR_END -->"""

    if "<!-- PSEO_HUB_BAR_START -->" in index_html and "<!-- PSEO_HUB_BAR_END -->" in index_html:
        index_html = re.sub(
            r"<!-- PSEO_HUB_BAR_START -->.*?<!-- PSEO_HUB_BAR_END -->",
            lambda _: hub_bar_html,
            index_html,
            flags=re.DOTALL,
        )

    # 2. Prepare JSON payload for embedded SPA directory
    spa_contracts = []
    for c in enriched_contracts:
        cat_key = c["categories"][0]
        tags = CATEGORIES.get(cat_key, CATEGORIES["software-development"])["tags"]
        spa_contracts.append({
            "id": c["id"],
            "slug": c["slug"],
            "clean_title": c["clean_title"],
            "raw_title": c["raw_title"],
            "agency": c["agency"],
            "masked_agency": c["masked_agency"],
            "url": c["url"],
            "due_str": c["due_str"] or "Open / See Portal",
            "jurisdiction": c["jurisdiction"],
            "categories": c["categories"],
            "tags": tags[:2],
            "naics_display": c["naics_display"],
            "sba_cap": c["sba_cap"],
            "compliance_posture": c["compliance_posture"],
            "teaming_posture": c["teaming_posture"],
            "igce_ptw_posture": c["igce_ptw_posture"],
            "key_personnel_lcats": c["key_personnel_lcats"],
            "cpars_benchmark": c["cpars_benchmark"],
        })

    if not spa_contracts:
        m_existing = re.search(r"window\.SIGNALTENDER_CONTRACTS\s*=\s*(\[.*?\]);\s*window\.SIGNALTENDER_JURISDICTIONS", index_html, flags=re.S)
        if m_existing:
            try:
                existing_list = json.loads(m_existing.group(1))
                if isinstance(existing_list, list) and existing_list:
                    print(f"[!] Warning: Supabase returned 0 enriched contracts; preserving {len(existing_list)} embedded SPA contracts in index.html.", flush=True)
                    spa_contracts = existing_list
            except Exception:
                pass

    contracts_json = json.dumps(spa_contracts)
    jurisdictions_json = json.dumps(JURISDICTIONS)
    categories_json = json.dumps({k: {"name": v["name"], "tags": v["tags"]} for k, v in CATEGORIES.items()})

    contracts_view_html = f"""<!-- PSEO_CONTRACTS_VIEW_START -->
  <div id="page-contracts" class="hidden">
    <div class="border-b border-slate-800/80 bg-navy-900/90 text-xs">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-9 flex items-center justify-between">
        <div class="flex items-center space-x-2.5">
          <span class="inline-block h-2 w-2 rounded-full bg-emerald-500"></span>
          <span class="font-mono text-slate-300">LIVE GOVCON INTELLIGENCE WIRE &bull; <span class="text-emerald-400">14 PORTALS ACTIVE</span></span>
        </div>
        <div class="flex items-center space-x-4 font-mono text-slate-400">
          <a href="#overview" class="hover:text-sky-400 transition-colors">&larr; Main Platform</a>
          <span>|</span>
          <a href="#apis" class="hover:text-sky-400 transition-colors">Developer APIs</a>
        </div>
      </div>
    </div>

    <header class="sticky top-0 z-50 backdrop-blur-md bg-navy-950/85 border-b border-slate-800/80">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between gap-4">
        <a href="#overview" class="flex flex-col justify-center shrink-0">
          <div class="inline-flex items-center gap-[4px]">
            <svg class="w-[21px] h-[21px] shrink-0 -translate-y-[1px]" viewBox="6 5 52 54" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="32" cy="24" r="15" stroke="#F8FAFC" stroke-width="5.6" />
              <circle cx="32" cy="24" r="5" fill="#38BDF8" />
              <path d="M10 54L32 42L54 54" stroke="#38BDF8" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span class="text-[23px] font-semibold tracking-[-0.03em] text-white leading-none whitespace-nowrap">SignalTender</span>
            <span class="ml-1.5 inline-flex items-center whitespace-nowrap text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-slate-900 text-sky-400/90 border border-slate-800 leading-none">LIVE RFP INDEX</span>
          </div>
          <span class="text-[11px] font-mono text-slate-500 tracking-tight leading-none whitespace-nowrap mt-1">FEDERAL &amp; 12-STATE SLED CONTRACT DIRECTORY</span>
        </a>
        <nav class="hidden md:flex items-center space-x-5 text-xs font-mono text-slate-300">
          <a href="#contracts" class="hover:text-sky-400 transition-colors">All Portals</a>
          <a href="#contracts/federal" class="hover:text-sky-400 transition-colors">Federal</a>
          <a href="#contracts/texas" class="hover:text-sky-400 transition-colors">Texas</a>
          <a href="#contracts/virginia" class="hover:text-sky-400 transition-colors">Virginia</a>
          <a href="#contracts/california" class="hover:text-sky-400 transition-colors">California</a>
          <a href="#contracts/florida" class="hover:text-sky-400 transition-colors">Florida</a>
          <a href="#contracts/maryland" class="hover:text-sky-400 transition-colors">Maryland</a>
          <a href="#contracts/illinois" class="hover:text-sky-400 transition-colors">Illinois</a>
          <a href="#contracts/pennsylvania" class="hover:text-sky-400 transition-colors">Pennsylvania</a>
          <a href="#contracts/ohio" class="hover:text-sky-400 transition-colors">Ohio</a>
          <a href="#contracts/georgia" class="hover:text-sky-400 transition-colors">Georgia</a>
          <a href="#contracts/north_carolina" class="hover:text-sky-400 transition-colors">North Carolina</a>
          <a href="#contracts/new_york" class="hover:text-sky-400 transition-colors">New York</a>
          <a href="#contracts/massachusetts" class="hover:text-sky-400 transition-colors">Massachusetts</a>
          <a href="#contracts/municipal" class="hover:text-sky-400 transition-colors">Municipal</a>
        </nav>
        <a href="#checkout-tier1" class="inline-flex items-center px-4 py-2.5 text-xs font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg border border-sky-400/30 transition-all shrink-0">
          Unlock All RFP Links &rarr;
        </a>
      </div>
    </header>

    <main id="contracts-dynamic-root" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 min-h-[65vh]"></main>
  </div>

  <script>
    window.SIGNALTENDER_CONTRACTS = {contracts_json};
    window.SIGNALTENDER_JURISDICTIONS = {jurisdictions_json};
    window.SIGNALTENDER_CATEGORIES = {categories_json};

    (function () {{
      function esc(str) {{
        return String(str || '')
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;');
      }}

      function renderLeadBox(prefState, prefLabel) {{
        var stVal = prefState || 'all';
        var stTitle = prefLabel ? ('Unlock 3 Live Pre-Shredded ' + esc(prefLabel) + ' IT/Cyber RFP Dossiers Free') : 'Unlock 3 Live Pre-Shredded IT &amp; Cyber RFP Dossiers Free';
        var opts = [
          ['all', 'All 14 Portals (Fed + 12 States)'],
          ['federal', 'Federal (SAM.gov)'],
          ['virginia', 'Virginia (eVA)'],
          ['texas', 'Texas (SmartBuy ESBD)'],
          ['california', 'California (Cal eProcure)'],
          ['florida', 'Florida (MFMP VIP)'],
          ['maryland', 'Maryland (eMMA & Bonfire)'],
          ['illinois', 'Illinois (BidBuy)'],
          ['pennsylvania', 'Pennsylvania (eMarketplace)'],
          ['ohio', 'Ohio (OhioBuys)'],
          ['georgia', 'Georgia (GPR & Team GA)'],
          ['north_carolina', 'North Carolina (NC eVP)'],
          ['new_york', 'New York (NYC CROL & PASSPort)'],
          ['massachusetts', 'Massachusetts (COMMBUYS & Boston)'],
          ['municipal', 'Municipal (DemandStar)']
        ].map(function (pair) {{
          var selAttr = pair[0] === stVal ? ' selected' : '';
          return '<option value="' + pair[0] + '"' + selAttr + '>' + esc(pair[1]) + '</option>';
        }}).join('');
        return '<section id="spa-contracts-lead-box" class="mt-10 rounded-2xl bg-gradient-to-r from-navy-900 via-slate-900/95 to-indigo-950/80 border-2 border-emerald-500/40 p-6 sm:p-8 shadow-2xl">' +
          '<div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">' +
            '<div class="lg:col-span-5 space-y-2">' +
              '<div class="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-[11px] font-mono text-emerald-300 uppercase tracking-wider">' +
                '<span class="h-2 w-2 rounded-full bg-emerald-400"></span>Instant State RFP Dossier Drop &bull; Zero Credit Card' +
              '</div>' +
              '<h2 class="text-xl sm:text-2xl font-extrabold text-white tracking-tight">' + stTitle + '</h2>' +
              '<p class="text-xs text-slate-300 leading-relaxed">Enter your work email and target jurisdiction to immediately unlock <strong class="text-white">3 open IT/Cyber solicitations</strong> with NAICS/SBA caps, CMMC/NIST/StateRAMP posture, IGCE Price-to-Win bands, and direct official agency links.</p>' +
            '</div>' +
            '<div class="lg:col-span-7">' +
              '<form onsubmit="event.preventDefault(); window.submitSpaLeadCapture();" class="grid grid-cols-1 sm:grid-cols-12 gap-3">' +
                '<div class="sm:col-span-4"><input id="spa-lead-email" type="email" required placeholder="capture@yourcompany.com" class="w-full px-3.5 py-2.5 rounded-xl bg-navy-950 border border-slate-700 focus:border-emerald-400 focus:outline-none text-xs font-mono text-white placeholder-slate-500" /></div>' +
                '<div class="sm:col-span-3"><input id="spa-lead-company" type="text" placeholder="Company / Prime LLC" class="w-full px-3.5 py-2.5 rounded-xl bg-navy-950 border border-slate-700 focus:border-emerald-400 focus:outline-none text-xs font-mono text-white placeholder-slate-500" /></div>' +
                '<div class="sm:col-span-3"><select id="spa-lead-state" class="w-full px-3 py-2.5 rounded-xl bg-navy-950 border border-slate-700 focus:border-emerald-400 focus:outline-none text-xs font-mono text-white">' + opts + '</select></div>' +
                '<div class="sm:col-span-2"><button id="spa-lead-submit-btn" type="submit" class="w-full h-full px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-semibold border border-emerald-400/30 transition-all cursor-pointer whitespace-nowrap">Unlock 3 &rarr;</button></div>' +
              '</form>' +
              '<div id="spa-lead-status" class="hidden mt-3 text-xs font-mono"></div>' +
              '<div id="spa-lead-results" class="hidden mt-4 grid grid-cols-1 md:grid-cols-3 gap-3"></div>' +
            '</div>' +
          '</div>' +
        '</section>';
      }}

      window.submitSpaLeadCapture = async function () {{
        var emailEl = document.getElementById('spa-lead-email');
        var compEl = document.getElementById('spa-lead-company');
        var stateEl = document.getElementById('spa-lead-state');
        var btnEl = document.getElementById('spa-lead-submit-btn');
        var statusEl = document.getElementById('spa-lead-status');
        var resultsEl = document.getElementById('spa-lead-results');
        var email = (emailEl ? emailEl.value : '').trim();
        var company = (compEl ? compEl.value : '').trim() || 'GovCon Capture Team';
        var st = (stateEl ? stateEl.value : 'all').trim() || 'all';
        if (!email || email.indexOf('@') === -1) {{
          if (statusEl) {{ statusEl.className = 'mt-3 text-xs font-mono text-amber-300'; statusEl.textContent = 'Please enter a valid work email address.'; }}
          return;
        }}
        if (btnEl) {{ btnEl.disabled = true; btnEl.textContent = 'Unlocking...'; }}
        if (statusEl) {{ statusEl.className = 'mt-3 text-xs font-mono text-sky-400'; statusEl.textContent = 'Matching 3 live open solicitations & computing CaptureDesk dossiers...'; }}
        try {{
          var resp = await fetch('https://b2b-contract-parser-api.onrender.com/v1/leads/capture', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json', 'Accept': 'application/json' }},
            body: JSON.stringify({{ email: email, first_name: email.split('@')[0], company: company, target_state: st }})
          }});
          var data = await resp.json();
          if (statusEl) {{ statusEl.className = 'mt-3 text-xs font-mono text-emerald-400'; statusEl.textContent = data.message || 'Unlocked 3 live RFP dossiers below!'; }}
          if (resultsEl && data.matched_dossiers && data.matched_dossiers.length) {{
            resultsEl.className = 'mt-4 grid grid-cols-1 md:grid-cols-3 gap-3';
            resultsEl.innerHTML = data.matched_dossiers.map(function (d) {{
              var safeUrl = String(d.official_portal_url || d.dossier_url || '#').replace(/"/g, '&quot;');
              return '<div class="p-3.5 rounded-xl bg-navy-950 border border-emerald-500/40 flex flex-col justify-between space-y-2 text-xs font-mono">' +
                '<div>' +
                  '<div class="text-[10px] text-emerald-400 font-bold uppercase">UNLOCKED &bull; NAICS ' + esc(d.naics || '541512') + '</div>' +
                  '<div class="text-white font-sans font-bold text-xs mt-1 line-clamp-2">' + esc(d.title || 'Open IT Solicitation') + '</div>' +
                  '<div class="text-slate-400 text-[11px] mt-1">' + esc(d.agency || 'Government Agency') + ' &bull; Due: <span class="text-amber-300">' + esc(d.closing_date || 'Open') + '</span></div>' +
                '</div>' +
                '<a href="' + safeUrl + '" target="_blank" rel="noopener noreferrer" class="inline-flex items-center justify-center px-3 py-1.5 rounded bg-emerald-600/20 hover:bg-emerald-600/35 text-emerald-300 border border-emerald-500/40 text-[11px] transition-colors">Open Official Bid Portal &rarr;</a>' +
              '</div>';
            }}).join('');
          }}
        }} catch (err) {{
          if (statusEl) {{ statusEl.className = 'mt-3 text-xs font-mono text-amber-300'; statusEl.textContent = 'Saved your request! Browse the live dossiers above.'; }}
        }} finally {{
          if (btnEl) {{ btnEl.disabled = false; btnEl.textContent = 'Unlock 3 →'; }}
        }}
      }};

      function renderRows(list) {{
        if (!list || !list.length) {{
          return '<tr><td colspan="5" class="py-8 px-5 text-center font-mono text-xs text-slate-400">No open solicitations currently in this view — our 6-hour scraper pipeline continuously indexes new bids across all 14 portals.</td></tr>';
        }}
        var J = window.SIGNALTENDER_JURISDICTIONS;
        return list.map(function (c) {{
          var jm = J[c.jurisdiction] || J.federal;
          var tagsHtml = (c.tags || []).map(function (t) {{
            return '<span class="inline-flex items-center whitespace-nowrap px-2 py-0.5 rounded bg-navy-900 border border-slate-800 text-slate-300">' + esc(t) + '</span>';
          }}).join(' ');
          return '<tr class="border-b border-slate-800/80 hover:bg-slate-900/60 transition-colors">' +
            '<td class="py-4 px-5 font-mono whitespace-nowrap align-top">' +
              '<a href="#contracts/' + esc(c.jurisdiction) + '" class="inline-flex items-center whitespace-nowrap px-2.5 py-0.5 rounded border text-[11px] ' + esc(jm.badge_class) + '">' + esc(jm.short.toUpperCase()) + '</a>' +
            '</td>' +
            '<td class="py-4 px-5 align-top">' +
              '<a href="#contracts/rfp/' + esc(c.slug) + '" class="font-semibold text-white hover:text-sky-400 transition-colors text-sm block">' + esc(c.clean_title) + '</a>' +
              '<div class="mt-1.5 flex flex-wrap gap-1.5 text-[11px] font-mono">' + tagsHtml + '</div>' +
            '</td>' +
            '<td class="py-4 px-4 text-slate-300 text-xs align-top">' + esc(c.masked_agency) + '</td>' +
            '<td class="py-4 px-4 font-mono text-amber-300 text-xs whitespace-nowrap align-top">' + esc(c.due_str) + '</td>' +
            '<td class="py-4 px-5 text-right font-mono whitespace-nowrap align-top">' +
              '<a href="#contracts/rfp/' + esc(c.slug) + '" class="inline-flex items-center whitespace-nowrap px-3 py-1.5 rounded bg-slate-900 hover:bg-sky-600 hover:text-white border border-slate-700 text-sky-400 text-xs transition-colors">' +
                '<span>View RFP Dossier</span><span class="ml-1.5">&rarr;</span>' +
              '</a>' +
            '</td>' +
          '</tr>';
        }}).join('');
      }}

      window.filterContractsDirectory = function (qVal) {{
        var inp = document.getElementById('contracts-live-search');
        var anchorEl = inp || document.activeElement;
        var anchorTopBefore = (anchorEl && anchorEl.getBoundingClientRect) ? anchorEl.getBoundingClientRect().top : null;
        var q = String(qVal !== undefined ? qVal : (inp ? inp.value : '')).trim().toLowerCase();
        if (inp && inp.value !== qVal && qVal !== undefined) inp.value = qVal;
        var clearBtn = document.getElementById('contracts-live-clear');
        if (clearBtn) {{
          if (q) clearBtn.classList.remove('hidden');
          else clearBtn.classList.add('hidden');
        }}
        var root = document.getElementById('contracts-dynamic-root');
        if (!root) return;
        var tbody = root.querySelector('table tbody');
        if (!tbody) return;
        var tblWrap = tbody.closest('.overflow-x-auto') || tbody.parentElement;
        if (tblWrap && !tblWrap.getAttribute('data-locked-min-h') && tblWrap.offsetHeight > 0) {{
          tblWrap.style.minHeight = tblWrap.offsetHeight + 'px';
          tblWrap.style.overflowAnchor = 'none';
          tblWrap.setAttribute('data-locked-min-h', '1');
        }}
        var rows = tbody.querySelectorAll('tr:not(#contracts-live-empty)');
        var shown = 0;
        for (var i = 0; i < rows.length; i++) {{
          var txt = (rows[i].innerText || '').toLowerCase();
          if (!q || txt.indexOf(q) !== -1) {{
            rows[i].classList.remove('hidden');
            shown++;
          }} else {{
            rows[i].classList.add('hidden');
          }}
        }}
        var cntEl = document.getElementById('contracts-live-count');
        if (cntEl) {{
          cntEl.textContent = shown + ' OF ' + rows.length + ' SOLICITATIONS SHOWN';
        }}
        var emptyRow = document.getElementById('contracts-live-empty');
        if (!emptyRow) {{
          emptyRow = document.createElement('tr');
          emptyRow.id = 'contracts-live-empty';
          emptyRow.className = 'hidden';
          emptyRow.innerHTML = '<td colspan="5" class="py-8 px-5 text-center font-mono text-xs text-slate-400">No solicitations matched that search query. <button type="button" onclick="window.filterContractsDirectory(&quot;&quot;)" class="text-sky-400 underline ml-1 cursor-pointer">Reset filter</button></td>';
          tbody.appendChild(emptyRow);
        }}
        if (shown === 0 && rows.length > 0) emptyRow.classList.remove('hidden');
        else emptyRow.classList.add('hidden');
        if (anchorEl && anchorTopBefore !== null && anchorEl.getBoundingClientRect) {{
          var deltaY = anchorEl.getBoundingClientRect().top - anchorTopBefore;
          if (Math.abs(deltaY) > 0.5) {{
            var docEl = document.documentElement;
            var prevB = docEl.style.scrollBehavior;
            docEl.style.scrollBehavior = 'auto';
            window.scrollBy(0, deltaY);
            docEl.style.scrollBehavior = prevB;
          }}
        }}
      }};

      window.renderContractsRoute = function (rawHash) {{
        var root = document.getElementById('contracts-dynamic-root');
        if (!root) return;
        var clean = String(rawHash || '#contracts')
          .replace(/^#/, '')
          .replace(/\\/index\\.html$/, '')
          .replace(/\\.html$/, '')
          .replace(/\\/+$/, '');
        var parts = clean.split('/');
        var all = window.SIGNALTENDER_CONTRACTS || [];
        var J = window.SIGNALTENDER_JURISDICTIONS || {{}};
        var C = window.SIGNALTENDER_CATEGORIES || {{}};

        // Case 1: Individual RFP Dossier (#contracts/rfp/<slug>)
        if (parts[1] === 'rfp' && parts[2]) {{
          var slug = parts.slice(2).join('/');
          var item = null;
          for (var i = 0; i < all.length; i++) {{
            if (all[i].slug === slug) {{ item = all[i]; break; }}
          }}
          if (!item) {{
            root.innerHTML = '<div class="p-8 rounded-2xl bg-navy-900 border border-slate-800 text-center space-y-4">' +
              '<div class="text-lg font-bold text-white">Solicitation Dossier Archived or Expired</div>' +
              '<p class="text-xs text-slate-400 font-mono">This solicitation may have passed its closing date and been automatically purged.</p>' +
              '<a href="#contracts" class="inline-flex items-center px-4 py-2 rounded bg-sky-600 text-white text-xs font-mono">Browse All Active RFPs &rarr;</a>' +
            '</div>';
            return;
          }}
          var jm = J[item.jurisdiction] || J.federal;
          var catKey = (item.categories && item.categories[0]) || 'software-development';
          var cm = C[catKey] || {{ name: 'Enterprise IT & Software' }};
          document.title = item.clean_title + ' | ' + jm.short + ' Government IT RFP | SignalTender';

          var related = all.filter(function (o) {{ return o.jurisdiction === item.jurisdiction && o.slug !== item.slug; }}).slice(0, 5);
          var relatedHtml = related.length ? related.map(function (r) {{
            return '<li class="py-2 border-b border-slate-800/70"><a href="#contracts/rfp/' + esc(r.slug) + '" class="text-sky-400 hover:underline font-medium">' + esc(r.clean_title) + '</a> <span class="text-slate-500 font-mono text-xs ml-2">(' + esc(r.due_str) + ')</span></li>';
          }}).join('') : '<li class="text-slate-400 text-xs font-mono">Browse more opportunities in the portal hub above.</li>';

          root.innerHTML =
            '<div class="mb-6 text-xs font-mono text-slate-400 flex flex-wrap items-center gap-2">' +
              '<a href="#contracts" class="hover:text-sky-400">All Contracts</a><span>/</span>' +
              '<a href="#contracts/' + esc(item.jurisdiction) + '" class="hover:text-sky-400">' + esc(jm.name) + '</a><span>/</span>' +
              '<span class="text-slate-200">' + esc(item.slug.slice(0, 45)) + '</span>' +
            '</div>' +
            '<div class="grid grid-cols-1 lg:grid-cols-12 gap-8">' +
              '<div class="lg:col-span-8 space-y-6">' +
                '<div class="p-6 sm:p-8 rounded-2xl bg-navy-900 border border-slate-800 shadow-2xl space-y-5">' +
                  '<div class="flex flex-wrap items-center gap-2.5 font-mono text-xs">' +
                    '<span class="px-2.5 py-1 rounded border font-semibold ' + esc(jm.badge_class) + '">' + esc(jm.name.toUpperCase()) + '</span>' +
                    '<span class="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">STATUS: OPEN LEAD</span>' +
                    '<span class="px-2.5 py-1 rounded bg-slate-800 text-slate-300">' + esc(cm.name) + '</span>' +
                  '</div>' +
                  '<h1 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-snug">' + esc(item.clean_title) + '</h1>' +
                  '<p class="text-slate-300 text-sm leading-relaxed">' +
                    'Verified active government IT/cybersecurity solicitation monitored on <strong class="text-white">' + esc(jm.portal) + '</strong>. ' +
                    'Pre-vetted by SignalTender AI for B2B software, cloud, cybersecurity, or systems integration scope (all commodity office supply and maintenance renewal noise excluded).' +
                  '</p>' +
                  '<div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t border-slate-800/80 text-xs font-mono">' +
                    '<div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800/80">' +
                      '<div class="text-slate-400">ISSUING AGENCY</div>' +
                      '<div class="text-white font-semibold mt-1">' + esc(item.masked_agency) + '</div>' +
                    '</div>' +
                    '<div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800/80">' +
                      '<div class="text-slate-400">RESPONSE DEADLINE</div>' +
                      '<div class="text-amber-300 font-semibold mt-1">' + esc(item.due_str) + '</div>' +
                    '</div>' +
                    '<div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800/80">' +
                      '<div class="text-slate-400">SOURCE PORTAL</div>' +
                      '<div class="text-sky-400 font-semibold mt-1">' + esc(jm.portal) + '</div>' +
                    '</div>' +
                  '</div>' +
                  '<div class="mt-6 p-6 rounded-xl bg-navy-950 border-2 border-indigo-500/50 space-y-5">' +
                    '<div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">' +
                      '<span class="text-xs font-mono uppercase tracking-wider text-indigo-300 font-bold">// CAPTUREDESK AI DOSSIER &amp; SOURCE PORTAL ACCESS</span>' +
                      '<span class="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[10px] font-mono">AI-ENRICHED</span>' +
                    '</div>' +
                    '<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">' +
                      '<div class="p-3 rounded-lg bg-navy-900 border border-slate-800 space-y-1">' +
                        '<div class="text-[10px] text-sky-400 font-bold">01. AI CLASSIFICATION (API #08)</div>' +
                        '<div class="text-slate-200">NAICS <span class="text-white font-semibold">' + esc(item.naics_display || '541512 / 541519') + '</span> &bull; SBA Cap: <span class="text-emerald-400">' + esc(item.sba_cap || '$34.0M') + '</span></div>' +
                      '</div>' +
                      '<div class="p-3 rounded-lg bg-navy-900 border border-slate-800 space-y-1">' +
                        '<div class="text-[10px] text-emerald-400 font-bold">02. IGCE, WRAP-RATE, PTW &amp; GSA MAS (API #03 / #16 / #20)</div>' +
                        '<div class="text-slate-200">' + esc(item.igce_ptw_posture || 'Wrap 1.80x • PTW -5.5% vs IGCE • Sr. Arch $162/hr | Lead Eng $146/hr') + '</div>' +
                      '</div>' +
                      '<div class="p-3 rounded-lg bg-navy-900 border border-slate-800 space-y-1">' +
                        '<div class="text-[10px] text-indigo-400 font-bold">03. CYBER, CMMC, SPRS &amp; RMF/cATO (API #06 / #12 / #18)</div>' +
                        '<div class="text-slate-200">' + esc(item.compliance_posture || 'SOC 2 Type II • NIST 800-171 • Section 508 VPAT') + '</div>' +
                      '</div>' +
                      '<div class="p-3 rounded-lg bg-navy-900 border border-slate-800 space-y-1">' +
                        '<div class="text-[10px] text-amber-400 font-bold">04. 13 CFR &sect; 125.6 WORKSHARE &amp; TEAMING (API #11)</div>' +
                        '<div class="text-slate-200">' + esc(item.teaming_posture || '13 CFR § 125.6 (50% Rule) • Low Ostensible Sub Risk') + '</div>' +
                      '</div>' +
                      '<div class="p-3 rounded-lg bg-navy-900 border border-slate-800 space-y-1">' +
                        '<div class="text-[10px] text-cyan-400 font-bold">05. KEY PERSONNEL LCATs (API #13)</div>' +
                        '<div class="text-slate-200">' + esc(item.key_personnel_lcats || 'Engagement PM (PMP) • Lead Enterprise Systems Architect') + '</div>' +
                      '</div>' +
                      '<div class="p-3 rounded-lg bg-navy-900 border border-slate-800 space-y-1">' +
                        '<div class="text-[10px] text-purple-300 font-bold">06. CPARS, ORALS &amp; DEBRIEF/PROTEST (API #15 / #17 / #19)</div>' +
                        '<div class="text-slate-200">' + esc(item.cpars_benchmark || 'Substantial Confidence • 3 Very Relevant Refs (5-Yr Window)') + '</div>' +
                      '</div>' +
                    '</div>' +
                    (function () {{
                      var isUnl = false;
                      try {{ isUnl = Boolean(window.localStorage && (window.localStorage.getItem('st_unlocked_lead_email') || window.localStorage.getItem('st_subscriber_active'))); }} catch (e) {{}}
                      var realBidUrl = item.url || ('https://portal.government.gov/solicitation/view/' + item.id);
                      if (isUnl && item.url) {{
                        return '<div class="space-y-2 text-xs font-mono text-slate-300 pt-1">' +
                          '<div><strong class="text-slate-200">Official Government Bid URL:</strong> <a href="' + esc(realBidUrl) + '" target="_blank" rel="noopener noreferrer" class="text-emerald-400 font-semibold underline hover:text-emerald-300">' + esc(realBidUrl) + ' &nearr;</a></div>' +
                          '<div><strong class="text-slate-200">Full Issuing Buyer &amp; Contracting Officer:</strong> <span class="text-white font-semibold">' + esc(item.agency) + '</span></div>' +
                          '<div><strong class="text-slate-200">Shipley Section L/M Compliance Matrix, SF-30 Diff &amp; CPARS Vol. III:</strong> <span class="text-sky-300">Ready — click &quot;Run Live Pwin &amp; Shred in Studio&quot; below</span></div>' +
                        '</div>';
                      }}
                      return '<div class="space-y-2 text-xs font-mono text-slate-400 pt-1">' +
                        '<div><strong class="text-slate-200">Official Government Bid URL:</strong> <span class="blur-sm select-none">https://portal.government.gov/solicitation/view/' + esc(item.id) + '98412</span></div>' +
                        '<div><strong class="text-slate-200">Full Issuing Buyer &amp; Contracting Officer:</strong> <span class="blur-sm select-none">' + esc(item.agency) + ' - Procurement Division</span></div>' +
                        '<div><strong class="text-slate-200">Shipley Section L/M Compliance Matrix, SF-30 Diff &amp; CPARS Vol. III:</strong> <span class="blur-sm select-none">Pre-built in #capturedesk-autopilot &amp; API #05/#06/#14/#15/#16/#17/#18/#19/#20</span></div>' +
                      '</div>';
                    }})() +
                    '<div class="pt-3 flex flex-col sm:flex-row gap-3">' +
                      '<a href="#checkout-tier1" class="inline-flex items-center justify-center px-6 py-3 text-sm font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg shadow-lg transition-all">' +
                        'Unlock Direct RFP Link &amp; Capture Dossier &rarr;' +
                      '</a>' +
                      '<button type="button" onclick="window.shredRfpInStudio(&quot;' + esc(item.slug) + '&quot;)" class="inline-flex items-center justify-center px-5 py-3 text-xs font-mono font-semibold text-emerald-300 bg-emerald-500/15 hover:bg-emerald-500/25 rounded-lg border border-emerald-500/40 transition-colors cursor-pointer">' +
                        'Run Live Pwin &amp; Shred in Studio &rarr;' +
                      '</button>' +
                      '<a href="#product-compliance-matrix" class="inline-flex items-center justify-center px-5 py-3 text-xs font-mono text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 rounded-lg border border-amber-500/30 transition-colors">' +
                        'Shred via Shipley Compliance API &rarr;' +
                      '</a>' +
                    '</div>' +
                    '<p class="text-[11px] font-mono text-slate-400">Instant 60-second Discord, Slack, Microsoft Teams &amp; CRM webhook activation. Cancel anytime.</p>' +
                  '</div>' +
                '</div>' +
                '<div class="p-6 rounded-2xl bg-navy-900/60 border border-slate-800">' +
                  '<h2 class="text-base font-bold text-white font-mono uppercase tracking-wider mb-3">More Open ' + esc(jm.short) + ' IT Solicitations</h2>' +
                  '<ul class="text-sm space-y-1">' + relatedHtml + '</ul>' +
                '</div>' +
              '</div>' +
              '<div class="lg:col-span-4 space-y-6">' +
                '<div class="p-6 rounded-2xl bg-navy-900 border border-slate-800 space-y-4">' +
                  '<div class="flex items-center justify-between">' +
                    '<span class="text-xs font-mono text-sky-400 uppercase font-semibold">SIGNALWIRE PRO &bull; $99/MO</span>' +
                    '<span class="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">$990/YR</span>' +
                  '</div>' +
                  '<div class="text-2xl font-extrabold text-white">Stop Hunting Portals Manually</div>' +
                  '<p class="text-xs text-slate-300 leading-relaxed">' +
                    'Get every pre-vetted Federal (SAM.gov), DemandStar, and 12-State SLED (TX, VA, CA, FL, MD, IL, PA, OH, GA, NC, NY, MA) IT &amp; cybersecurity solicitation pushed directly to your team every 6 hours.' +
                  '</p>' +
                  '<ul class="text-xs font-mono text-slate-300 space-y-2 pt-2">' +
                    '<li>&check; 99.4% Commodity &amp; Renewal Spam Stripped</li>' +
                    '<li>&check; Direct One-Click Official Portal Links</li>' +
                    '<li>&check; Tier 2 CaptureDesk ($399/mo | $3,490/yr) Auto-Dossiers</li>' +
                  '</ul>' +
                  '<a href="#checkout-tier1" class="w-full inline-flex items-center justify-center px-5 py-3 text-xs font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg transition-all">' +
                    'Start Tier 1 Leads ($99/mo) &rarr;' +
                  '</a>' +
                  '<a href="#checkout-tier2" class="w-full inline-flex items-center justify-center px-5 py-2.5 text-xs font-mono font-semibold text-indigo-200 bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 rounded-lg transition-all">' +
                    'Launch Tier 2 CaptureDesk ($399/mo) &rarr;' +
                  '</a>' +
                '</div>' +
                '<div class="p-6 rounded-2xl bg-navy-900 border border-indigo-500/30 space-y-3">' +
                  '<div class="text-xs font-mono text-indigo-400 uppercase font-semibold">20 LIVE APIs &amp; MCP SERVER</div>' +
                  '<div class="text-lg font-bold text-white">Automate Your Bid Response</div>' +
                  '<p class="text-xs text-slate-300 leading-relaxed">' +
                    'Generate GSA MAS Schedule SIN matrices, 0.75% IFF ceiling rate cards &amp; GSAR 552.238-81 PRC compliance packages, analyze FAR 15.506 Post-Award Debriefings &amp; GAO Bid-Protest viability, generate NIST 800-53 Rev 5 RMF, Continuous ATO (cATO), SSP &amp; POA&amp;M packages, FAR 15.102 Oral Presentation &amp; Murder-Board prep, model IGCE wrap-rates &amp; Price-to-Win, generate CPARS &amp; Past Performance Volume III citations, diff SF-30 RFP amendments, tailor Key Personnel &amp; GSA LCAT resumes, auto-answer SOC 2, FedRAMP &amp; NIST 800-171 security questionnaires, generate 13 CFR &sect; 125.6 (50% Rule) teaming plans, extract Section B CLIN pricing tables, draft Shipley proposal narratives &amp; CO Q&amp;A, classify NAICS/SIC/PSC/UNSPSC codes, score Bid/No-Bid Pwin (0&ndash;100), audit FAR/DFARS &amp; CMMC 2.0 flow-downs, or shred this RFP into a compliance matrix via our 20 RapidAPI microservices &amp; <code class="text-indigo-200">@signaltender/mcp-server</code>.' +
                  '</p>' +
                  '<a href="#product-gsa-mas-offer" class="w-full inline-flex items-center justify-center px-4 py-2.5 text-xs font-mono font-semibold text-indigo-300 bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/40 rounded-lg transition-all">' +
                    'Explore 20 APIs &amp; MCP Server &rarr;' +
                  '</a>' +
                '</div>' +
              '</div>' +
            '</div>' + renderLeadBox(item.jurisdiction, jm.short);
          return;
        }}

        // Case 2: Jurisdiction Hub (#contracts/<jurisdiction> or #contracts/<jurisdiction>/<category>)
        var jKey = parts[1];
        if (jKey && J[jKey]) {{
          var jmHub = J[jKey];
          var activeCat = parts[2] && C[parts[2]] ? parts[2] : null;
          var jList = all.filter(function (c) {{
            if (c.jurisdiction !== jKey) return false;
            if (activeCat && (!c.categories || c.categories.indexOf(activeCat) === -1)) return false;
            return true;
          }});

          document.title = (activeCat ? (jmHub.short + ' ' + C[activeCat].name + ' RFPs | ') : (jmHub.headline + ' | ')) + 'SignalTender';

          var pills = '<a href="#contracts/' + esc(jKey) + '" class="px-3 py-1.5 rounded-lg border text-xs font-mono transition-colors ' +
            (!activeCat ? 'bg-sky-600 text-white border-sky-400' : 'bg-navy-900 hover:bg-slate-800 border-slate-700 text-slate-300') + '">All ' + esc(jmHub.short) + ' IT Bids</a>';
          Object.keys(C).forEach(function (ck) {{
            var isAct = activeCat === ck;
            pills += ' <a href="#contracts/' + esc(jKey) + '/' + esc(ck) + '" class="px-3 py-1.5 rounded-lg border text-xs font-mono transition-colors ' +
              (isAct ? 'bg-sky-600 text-white border-sky-400' : 'bg-navy-900 hover:bg-slate-800 border-slate-700 text-sky-400') + '">' + esc(C[ck].name) + '</a>';
          }});

          root.innerHTML =
            '<div class="mb-6 text-xs font-mono text-slate-400 flex items-center gap-2">' +
              '<a href="#contracts" class="hover:text-sky-400">&larr; All Portals Directory</a>' +
              '<span>/</span>' +
              '<span class="text-white">' + esc(jmHub.name) + '</span>' +
              (activeCat ? ('<span>/</span><span class="text-sky-400">' + esc(C[activeCat].name) + '</span>') : '') +
            '</div>' +
            '<div class="mb-8 space-y-4">' +
              '<div class="inline-flex items-center px-3 py-1 rounded border text-xs font-mono ' + esc(jmHub.badge_class) + '">' +
                '// ' + esc(jmHub.portal.toUpperCase()) + ' &bull; ' + jList.length + ' ACTIVE IT SOLICITATIONS' +
              '</div>' +
              '<h1 class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">' +
                esc(activeCat ? (jmHub.short + ' ' + C[activeCat].name + ' Government Contracts & RFPs') : jmHub.headline) +
              '</h1>' +
              '<p class="text-slate-300 text-sm sm:text-base max-w-3xl">' +
                esc(jmHub.description) + ' Filtered automatically every 6 hours by SignalTender\\'s 3-layer B2B quality control engine.' +
              '</p>' +
              '<div class="flex flex-wrap gap-2 pt-2">' + pills + '</div>' +
            '</div>' +
            '<div class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">' +'<div class="p-4 sm:p-5 bg-slate-900/70 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">' +'<div class="relative flex-1 flex items-center">' +'<svg class="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10.5a7.5 7.5 0 0013.15 6.15z" /></svg>' +'<input id="contracts-live-search" type="text" placeholder="Search all open IT &amp; cybersecurity solicitations by keyword, agency, portal, or tag..." oninput="window.filterContractsDirectory(this.value)" class="w-full pl-10 pr-20 py-2.5 rounded-xl bg-navy-950 border border-slate-700/90 focus:border-sky-500 focus:outline-none text-xs font-mono text-white placeholder-slate-500" />' +'<button id="contracts-live-clear" type="button" onclick="window.filterContractsDirectory(&quot;&quot;)" class="hidden absolute right-2.5 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-300 border border-slate-700 cursor-pointer">Clear</button>' +'</div>' +'<span id="contracts-live-count" class="text-xs font-mono text-emerald-400 shrink-0">LIVE SEARCH ACTIVE</span>' +'</div>' +'<div class="overflow-x-auto">' +
                '<table class="w-full text-left border-collapse">' +
                  '<thead>' +
                    '<tr class="border-b border-slate-800 bg-slate-900/90 text-[11px] font-mono uppercase tracking-wider text-slate-400">' +
                      '<th class="py-4 px-5">Jurisdiction</th>' +
                      '<th class="py-4 px-5">Solicitation Title &amp; Scope</th>' +
                      '<th class="py-4 px-4">Issuing Agency</th>' +
                      '<th class="py-4 px-4">Closing Date</th>' +
                      '<th class="py-4 px-5 text-right">Dossier</th>' +
                    '</tr>' +
                  '</thead>' +
                  '<tbody class="text-xs">' + renderRows(jList) + '</tbody>' +
                '</table>' +
              '</div>' +
            '</div>' + renderLeadBox(jKey, jmHub.short);
          return;
        }}

        // Case 3: Master Directory (#contracts)
        document.title = 'Live Government IT & Cybersecurity Contracts Directory (Federal & SLED) | SignalTender';
        var cardsHtml = Object.keys(J).map(function (jk) {{
          var jmCard = J[jk];
          var cnt = all.filter(function (c) {{ return c.jurisdiction === jk; }}).length;
          return '<a href="#contracts/' + esc(jk) + '" class="p-5 rounded-xl bg-navy-900 hover:bg-slate-900 border border-slate-800 hover:border-sky-500/50 transition-all flex flex-col justify-between">' +
            '<div>' +
              '<span class="px-2.5 py-0.5 rounded border text-[10px] font-mono font-semibold ' + esc(jmCard.badge_class) + '">' + esc(jmCard.short.toUpperCase()) + '</span>' +
              '<h2 class="text-lg font-bold text-white mt-3">' + esc(jmCard.name) + '</h2>' +
              '<p class="text-xs text-slate-400 mt-1">' + esc(jmCard.description) + '</p>' +
            '</div>' +
            '<div class="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono">' +
              '<span class="text-emerald-400">' + cnt + ' Open Leads</span>' +
              '<span class="text-sky-400">Browse Hub &rarr;</span>' +
            '</div>' +
          '</a>';
        }}).join('');

        root.innerHTML =
          '<div class="mb-10 space-y-4">' +
            '<div class="inline-flex items-center px-3 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-xs font-mono text-emerald-400">' +
              '// LIVE GOVCON DIRECTORY &bull; ' + all.length + ' VERIFIED OPEN IT SOLICITATIONS' +
            '</div>' +
            '<h1 class="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">' +
              'Federal &amp; State SLED IT Contract Directory' +
            '</h1>' +
            '<p class="text-slate-300 text-base max-w-3xl">' +
              'Explore ' + all.length + ' live, AI-vetted government IT, software, cloud, and cybersecurity RFPs across SAM.gov, DemandStar, Texas, Virginia, California, Florida, Maryland, Illinois, Pennsylvania, Ohio, Georgia, North Carolina, New York, and Massachusetts.' +
            '</p>' +
          '</div>' +
          '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">' + cardsHtml + '</div>' +
          '<h2 class="text-xl font-bold text-white font-mono uppercase tracking-wider mb-4">All Verified Open IT &amp; Cybersecurity Solicitations</h2>' +
          '<div class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">' +'<div class="p-4 sm:p-5 bg-slate-900/70 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">' +'<div class="relative flex-1 flex items-center">' +'<svg class="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10.5a7.5 7.5 0 0013.15 6.15z" /></svg>' +'<input id="contracts-live-search" type="text" placeholder="Search all open IT &amp; cybersecurity solicitations by keyword, agency, portal, or tag..." oninput="window.filterContractsDirectory(this.value)" class="w-full pl-10 pr-20 py-2.5 rounded-xl bg-navy-950 border border-slate-700/90 focus:border-sky-500 focus:outline-none text-xs font-mono text-white placeholder-slate-500" />' +'<button id="contracts-live-clear" type="button" onclick="window.filterContractsDirectory(&quot;&quot;)" class="hidden absolute right-2.5 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-300 border border-slate-700 cursor-pointer">Clear</button>' +'</div>' +'<span id="contracts-live-count" class="text-xs font-mono text-emerald-400 shrink-0">LIVE SEARCH ACTIVE</span>' +'</div>' +'<div class="overflow-x-auto">' +
              '<table class="w-full text-left border-collapse">' +
                '<thead>' +
                  '<tr class="border-b border-slate-800 bg-slate-900/90 text-[11px] font-mono uppercase tracking-wider text-slate-400">' +
                    '<th class="py-4 px-5">Jurisdiction</th>' +
                    '<th class="py-4 px-5">Solicitation Title &amp; Scope</th>' +
                    '<th class="py-4 px-4">Issuing Agency</th>' +
                    '<th class="py-4 px-4">Closing Date</th>' +
                    '<th class="py-4 px-5 text-right">Dossier</th>' +
                  '</tr>' +
                '</thead>' +
                '<tbody class="text-xs">' + renderRows(all) + '</tbody>' +
              '</table>' +
            '</div>' +
          '</div>' + renderLeadBox('all', '');
        if (window.__PENDING_CONTRACTS_SEARCH) {{
          var pq = window.__PENDING_CONTRACTS_SEARCH;
          window.__PENDING_CONTRACTS_SEARCH = '';
          window.filterContractsDirectory(pq);
        }}
      }};
    }})();
  </script>
  <!-- PSEO_CONTRACTS_VIEW_END -->"""

    if "<!-- PSEO_CONTRACTS_VIEW_START -->" in index_html and "<!-- PSEO_CONTRACTS_VIEW_END -->" in index_html:
        index_html = re.sub(
            r"<!-- PSEO_CONTRACTS_VIEW_START -->.*?<!-- PSEO_CONTRACTS_VIEW_END -->",
            lambda _: contracts_view_html,
            index_html,
            flags=re.DOTALL,
        )

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)


if __name__ == "__main__":
    generate_pseo_site()

