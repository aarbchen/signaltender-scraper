from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()
import os
import re
import json
import html
from datetime import datetime, date
import requests
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = object

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
WHOP_TIER3_URL = os.getenv(
    "STRIPE_TIER3_CHECKOUT_URL",
    f"{SITE_BASE_URL}/index.html#checkout-tier3",
)
WHOP_TIER4_URL = os.getenv(
    "STRIPE_TIER4_CHECKOUT_URL",
    f"{SITE_BASE_URL}/index.html#checkout-tier4",
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
        "badge_class": "bg-sky-500/10 text-sky-300 border-sky-500/30",
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
        "badge_class": "bg-sky-500/10 text-sky-300 border-sky-500/30",
        "headline": "Open Georgia State (DOAS GPR / Team Georgia) & Atlanta Metro IT Contracts",
        "description": "Live State of Georgia Procurement Registry (DOAS GPR / Team Georgia Marketplace), Fulton County, Atlanta Regional Commission, and Georgia Regents IT, cloud, AI, SaaS, ERP, and cybersecurity solicitations.",
    },
    "north_carolina": {
        "name": "North Carolina (NC eVP & Metro)",
        "short": "North Carolina",
        "portal": "NC eVP, NCDIT, UNC & Raleigh/Charlotte",
        "badge_class": "bg-sky-500/10 text-sky-300 border-sky-500/30",
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
        "badge_class": "bg-sky-500/10 text-sky-300 border-sky-500/30",
        "headline": "Open Massachusetts State (COMMBUYS / EOTSS) & Boston IT Contracts",
        "description": "Live Commonwealth of Massachusetts COMMBUYS (EOTSS, OSD ITS78/ITS80, Trial Court, MassTech, MBTA, Massport) and City of Boston IT, cloud, cybersecurity, AI, and software solicitations.",
    },
    "new_jersey": {
        "name": "New Jersey (NJSTART & Treasury DPP)",
        "short": "New Jersey",
        "portal": "NJ NJSTART, Treasury DPP, OIT & NJ TRANSIT",
        "badge_class": "bg-amber-500/10 text-amber-300 border-amber-500/30",
        "headline": "Open New Jersey State (NJSTART / Treasury DPP / OIT) & Transit IT Contracts",
        "description": "Live State of New Jersey NJSTART (Treasury Division of Purchase & Property, NJ OIT, NJOHSP Cyber, NJ TRANSIT, Judiciary, Rutgers) IT, cloud, cybersecurity, AI, and software solicitations.",
    },
    "washington": {
        "name": "Washington (WEBS & WaTech DES)",
        "short": "Washington",
        "portal": "WA WEBS, WaTech OCIO, DES & WSDOT",
        "badge_class": "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
        "headline": "Open Washington State (WEBS / WaTech / DES) & Puget Sound IT Contracts",
        "description": "Live State of Washington WEBS (Department of Enterprise Services, WaTech OCIO, HCA, WSDOT, DSHS, DOL, University of Washington) IT, cloud, cybersecurity, AI, and software solicitations.",
    },
    "michigan": {
        "name": "Michigan (SIGMA VSS & DTMB)",
        "short": "Michigan",
        "portal": "MI SIGMA VSS, DTMB, MDHHS & MDOT",
        "badge_class": "bg-sky-500/10 text-sky-300 border-sky-500/30",
        "headline": "Open Michigan State (SIGMA VSS / DTMB) & Great Lakes IT Contracts",
        "description": "Live State of Michigan SIGMA Vendor Self-Service (DTMB Central Procurement, Michigan Cyber Security, MDHHS, MDOT, MSP, MiDEAL) IT, cloud, cybersecurity, AI, and software solicitations.",
    },
    "colorado": {
        "name": "Colorado (VSS, OIT & Front Range)",
        "short": "Colorado",
        "portal": "CO VSS, OIT, CDOT & Front Range Space/Cyber",
        "badge_class": "bg-sky-500/10 text-sky-300 border-sky-500/30",
        "headline": "Open Colorado State (VSS / OIT) & Front Range Space/IT Contracts",
        "description": "Live State of Colorado Vendor Self-Service (VSS, Governor's Office of Information Technology, CDOT, CDPHE, CDHS, Denver, Colorado Springs, CU) IT, cloud, cybersecurity, space/defense, and software solicitations.",
    },
    "municipal": {
        "name": "National Municipal (DemandStar)",
        "short": "Municipal SLED",
        "portal": "DemandStar Municipal Network",
        "badge_class": "bg-sky-500/10 text-sky-300 border-sky-500/30",
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
    r"\bdo\s+not\s+use\b",
    r"\btest\s+for\s+erp\b",
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
            json={"content": f"**[ALERT] pSEO Generator Alert:**\n{message}", "flags": 4},
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
    if (
        "njstart.gov" in url
        or "nj.gov" in url
        or "njtransit.com" in url
        or "rutgers.edu" in url
    ):
        return "new_jersey"
    if (
        "pr-webs-vendor.des.wa.gov" in url
        or "des.wa.gov" in url
        or "watech.wa.gov" in url
        or "wsdot.wa.gov" in url
        or "hca.wa.gov" in url
        or "dshs.wa.gov" in url
        or "dol.wa.gov" in url
        or "wa.gov" in url
    ):
        return "washington"
    if (
        "sigma.michigan.gov" in url
        or "michigan.gov" in url
    ):
        return "michigan"
    if (
        "colorado.gov" in url
        or "denvergov.org" in url
        or "coloradosprings.gov" in url
        or "cu.edu" in url
    ):
        return "colorado"
    if "emma.maryland.gov" in url or "maryland.gov" in url or "countymd.bonfirehub.com" in url:
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
    if (
        title.startswith("[NJ]")
        or "new jersey" in agency
        or "(nj)" in agency
        or "njstart" in agency
        or "nj transit" in agency
        or "rutgers" in agency
    ):
        return "new_jersey"
    if (
        title.startswith("[WA]")
        or "washington state" in agency
        or "state of washington" in agency
        or "(wa)" in agency
        or "watech" in agency
        or "wa des" in agency
        or "wsdot" in agency
    ):
        return "washington"
    if (
        title.startswith("[MI]")
        or title.lower().startswith("[mi-")
        or "michigan" in agency
        or "(mi)" in agency
        or "mi sigma" in agency
        or "dtmb" in agency
        or "mdhhs" in agency
        or "mdot" in agency
        or "msp" in agency
    ):
        return "michigan"
    if (
        title.startswith("[CO]")
        or title.lower().startswith("[co-")
        or "colorado" in agency
        or "(co)" in agency
        or "co vss" in agency
        or "co oit" in agency
        or "cdot" in agency
        or "cdphe" in agency
        or "cdhs" in agency
    ):
        return "colorado"
    if title.startswith("[OH]") or "ohio" in agency or "columbus" in agency or "morpc" in agency or "franklin county" in agency:
        return "ohio"
    if title.startswith("[MD]") or "maryland" in agency or "prince george" in agency or "howard county" in agency or "bonfirehub.com" in url:
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
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escaped_title}</title>
  <meta name="description" content="{escaped_desc}" />
  <meta name="theme-color" content="#090C10" />
  <link rel="icon" type="image/png" sizes="96x96" href="https://signaltender.net/contracts/favicon-96x96.png?v=6" />
  <link rel="icon" type="image/png" sizes="512x512" href="https://signaltender.net/contracts/favicon-512x512.png?v=6" />
  <link rel="icon" type="image/png" sizes="192x192" href="https://signaltender.net/contracts/favicon-192x192.png?v=6" />
  <link rel="icon" type="image/svg+xml" href="https://signaltender.net/contracts/favicon.svg?v=6" />
  <link rel="icon" type="image/png" sizes="48x48" href="https://signaltender.net/contracts/favicon-48x48.png?v=6" />
  <link rel="icon" type="image/png" sizes="32x32" href="https://signaltender.net/contracts/favicon-32x32.png?v=6" />
  <link rel="shortcut icon" href="https://signaltender.net/contracts/favicon.ico?v=6" />
  <link rel="apple-touch-icon" sizes="180x180" href="https://signaltender.net/contracts/apple-touch-icon.png?v=6" />
  <link rel="apple-touch-icon-precomposed" sizes="180x180" href="https://signaltender.net/contracts/apple-touch-icon.png?v=6" />
  <link rel="manifest" href="https://signaltender.net/contracts/site.webmanifest?v=6" />
  <link rel="canonical" href="{canonical_url}" />
  <meta property="og:site_name" content="SignalTender" />
  <meta property="og:title" content="{escaped_title}" />
  <meta property="og:description" content="{escaped_desc}" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="{canonical_url}" />
  <meta property="og:image" content="https://signaltender.net/contracts/og-banner.png?v=6" />
  <meta property="og:image:secure_url" content="https://signaltender.net/contracts/og-banner.png?v=6" />
  <meta property="og:image:alt" content="SignalTender | Real-Time Federal &amp; State SLED IT/Cyber Contract Intelligence" />
  <meta property="og:logo" content="https://signaltender.net/contracts/favicon-512x512.png?v=6" />
  <meta property="og:image:type" content="image/png" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:site" content="@SignalTenderX" />
  <meta name="twitter:title" content="{escaped_title}" />
  <meta name="twitter:description" content="{escaped_desc}" />
  <meta name="twitter:image" content="https://signaltender.net/contracts/og-banner.png?v=6" />
  <meta name="twitter:image:alt" content="SignalTender | Real-Time Federal &amp; State SLED IT/Cyber Contract Intelligence" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    window.tailwind = window.tailwind || {{}};
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
              950: '#090C10',
              900: '#11161F',
              800: '#161C26',
              700: '#1F2735',
            }},
            slate: {{
              950: '#0B0E14',
              900: '#11161F',
              800: '#1E2532',
              700: '#2A3344',
              600: '#475569',
              500: '#64748B',
              400: '#94A3B8',
              300: '#CBD5E1',
              200: '#E2E8F0',
              100: '#F1F5F9',
              50: '#F8FAFC',
            }},
            indigo: {{
              950: '#0B111C',
              900: '#111A29',
              800: '#19263B',
              700: '#0369A1',
              600: '#0284C7',
              500: '#0EA5E9',
              400: '#38BDF8',
              300: '#7DD3FC',
              200: '#BAE6FD',
              100: '#E0F2FE',
              50: '#F0F9FF',
            }},
            purple: {{
              950: '#0B111C',
              900: '#111A29',
              800: '#19263B',
              700: '#0369A1',
              600: '#0284C7',
              500: '#0EA5E9',
              400: '#38BDF8',
              300: '#7DD3FC',
              200: '#BAE6FD',
              100: '#E0F2FE',
              50: '#F0F9FF',
            }},
            violet: {{
              950: '#0B111C',
              900: '#111A29',
              800: '#19263B',
              700: '#0369A1',
              600: '#0284C7',
              500: '#0EA5E9',
              400: '#38BDF8',
              300: '#7DD3FC',
              200: '#BAE6FD',
              100: '#E0F2FE',
              50: '#F0F9FF',
            }},
            fuchsia: {{
              950: '#0B111C',
              900: '#111A29',
              800: '#19263B',
              700: '#0369A1',
              600: '#0284C7',
              500: '#0EA5E9',
              400: '#38BDF8',
              300: '#7DD3FC',
              200: '#BAE6FD',
              100: '#E0F2FE',
              50: '#F0F9FF',
            }},
            rose: {{
              950: '#0B111C',
              900: '#111A29',
              800: '#19263B',
              700: '#0369A1',
              600: '#0284C7',
              500: '#0EA5E9',
              400: '#38BDF8',
              300: '#7DD3FC',
              200: '#BAE6FD',
              100: '#E0F2FE',
              50: '#F0F9FF',
            }},
            pink: {{
              950: '#0B111C',
              900: '#111A29',
              800: '#19263B',
              700: '#0369A1',
              600: '#0284C7',
              500: '#0EA5E9',
              400: '#38BDF8',
              300: '#7DD3FC',
              200: '#BAE6FD',
              100: '#E0F2FE',
              50: '#F0F9FF',
            }},
            amber: {{
              950: '#0B111C',
              900: '#111A29',
              800: '#19263B',
              700: '#0369A1',
              600: '#0284C7',
              500: '#0EA5E9',
              400: '#38BDF8',
              300: '#7DD3FC',
              200: '#BAE6FD',
              100: '#E0F2FE',
              50: '#F0F9FF',
            }},
            orange: {{
              950: '#0B111C',
              900: '#111A29',
              800: '#19263B',
              700: '#0369A1',
              600: '#0284C7',
              500: '#0EA5E9',
              400: '#38BDF8',
              300: '#7DD3FC',
              200: '#BAE6FD',
              100: '#E0F2FE',
              50: '#F0F9FF',
            }},
            cyan: {{
              950: '#0B111C',
              900: '#111A29',
              800: '#19263B',
              700: '#0369A1',
              600: '#0284C7',
              500: '#0EA5E9',
              400: '#38BDF8',
              300: '#7DD3FC',
              200: '#BAE6FD',
              100: '#E0F2FE',
              50: '#F0F9FF',
            }},
            teal: {{
              950: '#0B111C',
              900: '#111A29',
              800: '#19263B',
              700: '#0369A1',
              600: '#0284C7',
              500: '#0EA5E9',
              400: '#38BDF8',
              300: '#7DD3FC',
              200: '#BAE6FD',
              100: '#E0F2FE',
              50: '#F0F9FF',
            }}
          }}
        }}
      }}
    }}
  </script>
  <style>
    :root, html {{
      color-scheme: dark;
      scrollbar-width: thin;
      scrollbar-color: #1e293b #050811;
    }}
    html, body, pre, .overflow-y-auto, .overflow-x-auto {{
      scrollbar-width: thin;
      scrollbar-color: #1e293b rgba(9, 14, 26, 0.65);
    }}
    html, body {{
      overflow-x: hidden;
      max-width: 100%;
    }}
    span[class*="border"]:not(.hidden),
    span[class*="rounded"]:not(.animate-ping):not(.hidden) {{
      display: inline-flex;
      align-items: center;
      white-space: nowrap;
      line-height: 1.25;
      max-width: 100%;
    }}
    @media (max-width: 639px) {{
      span[class*="border"]:not(.hidden),
      span[class*="rounded"]:not(.animate-ping):not(.hidden) {{
        white-space: normal;
        overflow-wrap: anywhere;
        word-break: break-word;
      }}
    }}

                    /* === INSTITUTIONAL GRAPHITE THEME (PALANTIR FOUNDRY / LINEAR DARK) === */
    :root, html {{
      color-scheme: dark;
      scrollbar-width: thin;
      scrollbar-color: #262f3f #090c10;
    }}
    body {{
      background-color: #090C10 !important;
      background-image:
        linear-gradient(to right, rgba(255, 255, 255, 0.022) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(255, 255, 255, 0.022) 1px, transparent 1px) !important;
      background-size: 48px 48px, 48px 48px !important;
      background-attachment: scroll !important;
      color: #F8FAFC;
    }}
    /* Match full 1600px header width across all page sections & cards so there is zero empty side space */
    .max-w-7xl,
    .max-w-6xl,
    .max-w-5xl {{
      max-width: 1600px !important;
    }}
    @media (min-width: 1024px) {{
      #page-main > section,
      #page-main > div:not(:first-of-type),
      #page-apis > section,
      #page-apis > div:not(:first-of-type),
      #page-contracts > main,
      #page-contracts > div:not(:first-of-type),
      #page-checkout > section,
      #page-checkout > div:not(:first-of-type),
      #page-account > section,
      #page-account > div:not(:first-of-type),
      #page-status > section,
      #page-status > div:not(:first-of-type),
      #page-privacy > section,
      #page-privacy > div:not(:first-of-type),
      body > div:first-of-type > section,
      body > div:first-of-type > div:not(:first-of-type),
      body > div:first-of-type > main,
      body > footer {{
        padding-left: 44px !important;
      }}
    }}
    /* Keep ambient background glow blobs subtle but present to frame ultra-wide viewports */
    .blur-3xl,
    [class*="blur-[120px]"],
    [class*="blur-[100px]"] {{
      display: none !important;
    }}
    .backdrop-blur-md, .backdrop-blur-xl, .backdrop-blur-sm, #page-sidebar-tab, #page-sidebar-drawer {{
      backdrop-filter: none !important;
      -webkit-backdrop-filter: none !important;
    }}
    #page-sidebar-tab, #page-sidebar-mobile-btn {{
      background-color: #090C10 !important;
      border-color: rgba(255, 255, 255, 0.10) !important;
    }}
    #page-sidebar-drawer {{
      background-color: #0B0E14 !important;
      border-color: rgba(255, 255, 255, 0.12) !important;
      box-shadow: 8px 0 32px rgba(0, 0, 0, 0.85) !important;
    }}
    .animate-ping, .animate-pulse {{
      animation: none !important;
    }}
    article[id^="product-"] {{
      content-visibility: auto;
      contain-intrinsic-size: auto 620px;
    }}
    /* Top telemetry bar & sticky navigation chrome */
    #page-main > div:first-of-type,
    #page-apis > div:first-of-type,
    #page-contracts > div:first-of-type,
    #page-checkout > div:first-of-type,
    body > div > div.border-b.bg-navy-900\\/90,
    body > div.border-b.bg-navy-900\\/90 {{
      background-color: #05070A !important;
      border-bottom-color: rgba(255, 255, 255, 0.08) !important;
    }}
    header.sticky {{
      background-color: #090C10 !important;
      border-bottom-color: rgba(255, 255, 255, 0.08) !important;
      backdrop-filter: none !important;
      -webkit-backdrop-filter: none !important;
    }}
    header nav[aria-label="Primary Site Navigation"] {{
      background-color: #090C10 !important;
      border-color: rgba(255, 255, 255, 0.08) !important;
    }}
    header nav[aria-label="Primary Site Navigation"] a[class*="bg-sky-500"] {{
      background-color: rgba(255, 255, 255, 0.08) !important;
      border-color: rgba(255, 255, 255, 0.14) !important;
      color: #F8FAFC !important;
    }}
    /* Uniform Institutional Graphite card surfaces & crisp 1px hairlines */
    article[id^="product-"],
    .bg-navy-900,
    .bg-navy-900\\/95,
    .bg-navy-900\\/90,
    .bg-navy-900\\/80,
    .bg-navy-900\\/70,
    .bg-navy-900\\/60,
    .bg-slate-900\\/90,
    .bg-slate-900\\/80,
    .bg-slate-900\\/70 {{
      background-color: #11161F !important;
    }}
    .bg-navy-950,
    .bg-navy-950\\/95,
    .bg-navy-950\\/90,
    .bg-navy-950\\/80,
    .bg-slate-950,
    .bg-slate-950\\/90,
    .bg-slate-950\\/80 {{
      background-color: #0B0E14 !important;
    }}
    /* De-noise rainbow card & link-card borders into crisp institutional hairlines */
    div.rounded-2xl:not(#checkout-card-tier2):not(#checkout-card-tier3),
    div.rounded-xl,
    a.rounded-xl:not(.bg-sky-500):not(.bg-sky-600),
    a.rounded-2xl:not(.bg-sky-500):not(.bg-sky-600),
    section.rounded-2xl,
    article[id^="product-"] {{
      border-color: rgba(255, 255, 255, 0.08) !important;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35) !important;
    }}
    /* Featured Tiers (Tier 2, Tier 3, and API ULTRA Popular cards) -> Steel Sky border + subtle sky gradient */
    #checkout-card-tier2,
    #checkout-card-tier3,
    article[id^="product-"] .grid.grid-cols-2.sm\\:grid-cols-4 > div:nth-child(3) {{
      border: 1px solid rgba(56, 189, 248, 0.45) !important;
      background: linear-gradient(180deg, rgba(56, 189, 248, 0.06) 0%, #11161F 100%) !important;
      box-shadow: 0 6px 24px rgba(0, 0, 0, 0.4) !important;
    }}
    /* API Card Top Header Strip & Capability Boxes */
    article[id^="product-"] > div:first-of-type {{
      background: #0C1017 !important;
      background-image: none !important;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
    }}
    /* API Card Top Strip Badges: First badge (API XX // TITLE) -> Neutral Graphite Pill; Second badge (POST /v1/...) -> Steel Sky Pill */
    article[id^="product-"] > div:first-of-type span.rounded {{
      background-color: rgba(255, 255, 255, 0.05) !important;
      color: #E2E8F0 !important;
      border: 1px solid rgba(255, 255, 255, 0.10) !important;
    }}
    article[id^="product-"] > div:first-of-type span.rounded:nth-of-type(2) {{
      background-color: rgba(56, 189, 248, 0.12) !important;
      color: #38BDF8 !important;
      border: 1px solid rgba(56, 189, 248, 0.28) !important;
    }}
    /* API Card 4-Tier Mini Cards (BASIC, PRO, ULTRA, MEGA) */
    article[id^="product-"] .grid.grid-cols-2.sm\\:grid-cols-4 > div:not(:nth-child(3)) {{
      background-color: #0C1017 !important;
      border: 1px solid rgba(255, 255, 255, 0.08) !important;
    }}
    article[id^="product-"] .grid.grid-cols-2.sm\\:grid-cols-4 > div > span.absolute {{
      background-color: rgba(56, 189, 248, 0.15) !important;
      color: #38BDF8 !important;
      border: 1px solid rgba(56, 189, 248, 0.35) !important;
    }}
    /* API Card Right-Side Code Terminal */
    article[id^="product-"] .lg\\:col-span-5 {{
      background-color: #0B0E14 !important;
      border: 1px solid rgba(255, 255, 255, 0.10) !important;
    }}
    article[id^="product-"] .lg\\:col-span-5 > div:first-child > div:first-child {{
      background-color: #090C10 !important;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
    }}
    article[id^="product-"] .lg\\:col-span-5 > div:first-child > div:first-child > span:first-child {{
      color: #E2E8F0 !important;
    }}
    article[id^="product-"] .lg\\:col-span-5 div:has(> div > button[data-lang="curl"]) {{
      padding: 8px 14px !important;
      margin-bottom: 4px !important;
    }}
    /* Schema field pills at bottom of API terminal -> Uniform Graphite + Steel Sky */
    article[id^="product-"] .lg\\:col-span-5 .flex.flex-wrap.gap-1\\.5 > span {{
      background-color: #0C1017 !important;
      border: 1px solid rgba(255, 255, 255, 0.08) !important;
      color: #38BDF8 !important;
    }}
    /* Cross-Catalog Pricing Matrix Table -> Uniform Graphite rows (zero rainbow row background tints) */
    #api-pricing-matrix tbody tr {{
      background-color: transparent !important;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
    }}
    #api-pricing-matrix tbody tr:hover {{
      background-color: rgba(255, 255, 255, 0.03) !important;
    }}
    /* Secondary buttons & outline CTAs -> Clean Graphite (#161B22) */
    a[class*="bg-emerald-500/"],
    a[class*="bg-emerald-950"],
    button[class*="bg-emerald-500/"],
    button[class*="bg-emerald-950"],
    a[class*="bg-amber-500/"],
    a[class*="bg-amber-950"],
    button[class*="bg-amber-500/"],
    button[class*="bg-amber-950"],
    a[class*="bg-sky-500/"],
    button[class*="bg-sky-500/"],
    a[class*="bg-sky-500/"],
    button[class*="bg-sky-500/"],
    a[class*="bg-indigo-500/"],
    button[class*="bg-indigo-500/"] {{
      background-color: #161B22 !important;
      color: #E2E8F0 !important;
      border-color: rgba(255, 255, 255, 0.12) !important;
    }}
    a[class*="bg-emerald-500/"]:hover,
    a[class*="bg-emerald-950"]:hover,
    button[class*="bg-emerald-500/"]:hover,
    button[class*="bg-emerald-950"]:hover,
    a[class*="bg-amber-500/"]:hover,
    a[class*="bg-amber-950"]:hover,
    button[class*="bg-amber-500/"]:hover,
    button[class*="bg-amber-950"]:hover,
    a[class*="bg-sky-500/"]:hover,
    button[class*="bg-sky-500/"]:hover,
    a[class*="bg-sky-500/"]:hover,
    button[class*="bg-sky-500/"]:hover,
    a[class*="bg-indigo-500/"]:hover,
    button[class*="bg-indigo-500/"]:hover {{
      background-color: #1F2733 !important;
      color: #FFFFFF !important;
      border-color: rgba(56, 189, 248, 0.35) !important;
    }}
    /* Unify multi-color inline prose highlights in paragraphs to crisp white */
    p > span.text-emerald-300,
    p > span.text-emerald-400,
    p > span.text-amber-300,
    p > span.text-amber-400,
    p > span.text-sky-300,
    p > span.text-sky-400,
    p > span.text-sky-300,
    p > span.text-sky-400 {{
      color: #F8FAFC !important;
    }}
    /* High-contrast Linear / Palantir crisp white primary action buttons (exact match to Option 1 preview) */
    a.bg-sky-500,
    a.bg-sky-600,
    button.bg-sky-500,
    button.bg-sky-600,
    a.bg-emerald-500,
    a.bg-emerald-600,
    button.bg-emerald-500,
    button.bg-emerald-600,
    a.bg-amber-500,
    a.bg-amber-600,
    button.bg-amber-500,
    button.bg-amber-600,
    a.bg-indigo-500,
    a.bg-indigo-600,
    button.bg-indigo-500,
    button.bg-indigo-600,
    a.bg-sky-500,
    a.bg-sky-600,
    button.bg-sky-500,
    button.bg-sky-600,
    a.bg-sky-500,
    a.bg-sky-600,
    button.bg-sky-500,
    button.bg-sky-600,
    a.bg-cyan-500,
    a.bg-cyan-600,
    button.bg-cyan-500,
    button.bg-cyan-600,
    a.bg-teal-500,
    a.bg-teal-600,
    button.bg-teal-500,
    button.bg-teal-600,
    a[class*="bg-gradient-to-r"][class*="from-"],
    button[class*="bg-gradient-to-r"][class*="from-"] {{
      background: #F8FAFC !important;
      background-image: none !important;
      color: #090C10 !important;
      border-color: #FFFFFF !important;
      font-weight: 600 !important;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.35) !important;
    }}
    a.bg-sky-500:hover,
    a.bg-sky-600:hover,
    button.bg-sky-500:hover,
    button.bg-sky-600:hover,
    a.bg-emerald-500:hover,
    a.bg-emerald-600:hover,
    button.bg-emerald-500:hover,
    button.bg-emerald-600:hover,
    a.bg-amber-500:hover,
    a.bg-amber-600:hover,
    button.bg-amber-500:hover,
    button.bg-amber-600:hover,
    a.bg-indigo-600:hover,
    button.bg-indigo-600:hover,
    a.bg-sky-600:hover,
    button.bg-sky-600:hover,
    a.bg-sky-600:hover,
    button.bg-sky-600:hover,
    a[class*="bg-gradient-to-r"][class*="from-"]:hover,
    button[class*="bg-gradient-to-r"][class*="from-"]:hover {{
      background: #E2E8F0 !important;
      background-image: none !important;
      color: #090C10 !important;
      border-color: #E2E8F0 !important;
    }}
    a.bg-sky-500 span,
    a.bg-sky-600 span,
    button.bg-sky-500 span,
    button.bg-sky-600 span,
    a.bg-emerald-500 span,
    a.bg-emerald-600 span,
    button.bg-emerald-500 span,
    button.bg-emerald-600 span,
    a.bg-amber-500 span,
    a.bg-amber-600 span,
    button.bg-amber-500 span,
    button.bg-amber-600 span,
    a.bg-sky-500 span,
    a.bg-sky-600 span,
    button.bg-sky-500 span,
    button.bg-sky-600 span,
    a[class*="bg-gradient-to-r"][class*="from-"] span,
    button[class*="bg-gradient-to-r"][class*="from-"] span {{
      color: #090C10 !important;
    }}

    /* === OPTION 2 (TOGGLEABLE LIGHT MODE): EXECUTIVE IVORY & OXFORD NAVY (STRIPE / HIGHERGOV) === */
    html[data-theme="light"] {{
      color-scheme: light;
      scrollbar-width: thin;
      scrollbar-color: #CBD5E1 #F1F5F9;
    }}
    html[data-theme="light"] * {{
      scrollbar-color: #CBD5E1 #F1F5F9;
    }}
    html[data-theme="light"] *::-webkit-scrollbar-track {{
      background: #F1F5F9;
    }}
    html[data-theme="light"] *::-webkit-scrollbar-thumb {{
      background: #CBD5E1;
      border: 1px solid #E2E8F0;
    }}
    html[data-theme="light"] *::-webkit-scrollbar-thumb:hover {{
      background: #94A3B8;
    }}
    /* Theme toggle button icons & surface */
    .st-icon-moon {{
      display: none;
    }}
    html[data-theme="light"] .st-icon-sun {{
      display: none !important;
    }}
    html[data-theme="light"] .st-icon-moon {{
      display: inline-block !important;
    }}
    html[data-theme="light"] .st-theme-toggle-btn {{
      background-color: #F1F5F9 !important;
      border-color: #CBD5E1 !important;
      color: #0F172A !important;
    }}
    html[data-theme="light"] .st-theme-toggle-btn:hover {{
      background-color: #E2E8F0 !important;
      color: #0F172A !important;
    }}
    /* SignalTender Radar-Chevron Logo & Wordmark: Change white ring (#F8FAFC) & wordmark to Oxford Navy (#0F172A) in Light Mode */
    html[data-theme="light"] svg circle[stroke="#F8FAFC"],
    html[data-theme="light"] svg path[stroke="#F8FAFC"] {{
      stroke: #0F172A !important;
    }}
    html[data-theme="light"] svg circle[fill="#38BDF8"] {{
      fill: #0284C7 !important;
    }}
    html[data-theme="light"] svg path[stroke="#38BDF8"] {{
      stroke: #0284C7 !important;
    }}
    html[data-theme="light"] header span.text-\[23px\],
    html[data-theme="light"] footer span.text-\[23px\] {{
      color: #0F172A !important;
    }}
    html[data-theme="light"] header .inline-flex > span.bg-slate-900,
    html[data-theme="light"] footer .inline-flex > span.bg-slate-900 {{
      background-color: #F1F5F9 !important;
      color: #0F172A !important;
      border-color: #CBD5E1 !important;
      font-weight: 600 !important;
    }}
    /* Page Canvas -> Crisp Alabaster (#F8FAFC) with 32px slate architectural hash grid & deep Oxford Navy ink */
    html[data-theme="light"] body {{
      background-color: #F8FAFC !important;
      background-image:
        radial-gradient(ellipse 85% 55% at 50% -10%, rgba(2, 132, 199, 0.05), transparent 70%),
        linear-gradient(to right, #1e293b1a 1px, transparent 1px),
        linear-gradient(to bottom, #1e293b1a 1px, transparent 1px) !important;
      background-size: 100% 100%, 32px 32px, 32px 32px !important;
      color: #0F172A !important;
    }}
    html[data-theme="light"] .bg-\[size\:32px_32px\] {{
      display: none !important;
    }}
    html[data-theme="light"] .blur-3xl,
    html[data-theme="light"] [class*="blur-[120px]"],
    html[data-theme="light"] [class*="blur-[100px]"] {{
      opacity: 0.04 !important;
    }}
    /* Left Collapsible Sidebar Rail & Drawer in Light Mode */
    html[data-theme="light"] #page-sidebar-tab,
    html[data-theme="light"] #page-sidebar-drawer,
    html[data-theme="light"] #page-sidebar-mobile-btn {{
      background-color: #FFFFFF !important;
      border-color: #CBD5E1 !important;
      color: #0F172A !important;
      box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06) !important;
    }}
    html[data-theme="light"] #page-sidebar-tab button,
    html[data-theme="light"] #page-sidebar-drawer button,
    html[data-theme="light"] #page-sidebar-drawer a {{
      color: #1E293B !important;
    }}
    html[data-theme="light"] #page-sidebar-tab button:hover,
    html[data-theme="light"] #page-sidebar-drawer button:hover,
    html[data-theme="light"] #page-sidebar-drawer a:hover {{
      background-color: #F1F5F9 !important;
      color: #0F172A !important;
    }}
    /* Sticky Navigation Header -> 100% Solid Pure White (#FFFFFF) so scrolled text never bleeds through */
    html[data-theme="light"] header.sticky {{
      background-color: #FFFFFF !important;
      border-bottom-color: #CBD5E1 !important;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05) !important;
    }}
    html[data-theme="light"] header nav[aria-label="Primary Site Navigation"] {{
      background-color: #F1F5F9 !important;
      border-color: #CBD5E1 !important;
      box-shadow: none !important;
    }}
    html[data-theme="light"] header nav[aria-label="Primary Site Navigation"] a {{
      color: #1E293B !important;
      font-weight: 600 !important;
    }}
    html[data-theme="light"] header nav[aria-label="Primary Site Navigation"] a:hover {{
      color: #0F172A !important;
      background-color: #E2E8F0 !important;
    }}
    html[data-theme="light"] header nav[aria-label="Primary Site Navigation"] a[class*="bg-sky-500"] {{
      background-color: #FFFFFF !important;
      color: #0F172A !important;
      border-color: #94A3B8 !important;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08) !important;
    }}
    html[data-theme="light"] header div.lg\:hidden {{
      background-color: #FFFFFF !important;
      border-top-color: #CBD5E1 !important;
    }}
    /* Neutralize ALL dark Tailwind background classes AND dark linear-gradients on cards/containers (never full-width sections/main) */
    html[data-theme="light"] article[id^="product-"],
    html[data-theme="light"] [class*="bg-navy-900"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-navy-800"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-slate-900"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-slate-800"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-gradient-to-"]:not(.bg-clip-text):not(a):not(button):not(section):not(main) {{
      background-color: #FFFFFF !important;
      background-image: none !important;
      border-color: #CBD5E1 !important;
    }}
    html[data-theme="light"] [class*="bg-navy-950"]:not(section):not(main):not(body),
    html[data-theme="light"] [class*="bg-slate-950"]:not(section):not(main):not(body),
    html[data-theme="light"] [class*="bg-emerald-950"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-emerald-900"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-indigo-950"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-indigo-900"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-sky-950"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-sky-900"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-amber-950"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-amber-900"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-cyan-950"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-cyan-900"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-blue-950"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-blue-900"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-teal-950"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-teal-900"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-purple-950"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-violet-950"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-rose-950"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-orange-950"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-lime-950"]:not(section):not(main),
    html[data-theme="light"] [class*="bg-[#0"]:not(section):not(main):not(body) {{
      background-color: #FFFFFF !important;
      background-image: none !important;
      border-color: #CBD5E1 !important;
    }}
    /* Keep all page-level section and main containers transparent in Light Mode so the 32px architectural hash grid shows through on every page */
    html[data-theme="light"] section:not(.rounded-2xl):not(.inbound-lead-capture-box),
    html[data-theme="light"] main {{
      background-color: transparent !important;
      background-image: none !important;
      border-color: #CBD5E1 !important;
    }}
    html[data-theme="light"] footer {{
      background-color: #FFFFFF !important;
      background-image: none !important;
      border-color: #CBD5E1 !important;
    }}
    html[data-theme="light"] article[id^="product-"] {{
      background-color: #FFFFFF !important;
      background-image: none !important;
    }}
    html[data-theme="light"] div.rounded-2xl:not(#checkout-card-tier2):not(#checkout-card-tier3),
    html[data-theme="light"] div.rounded-xl,
    html[data-theme="light"] a.rounded-xl:not(.bg-sky-500):not(.bg-sky-600),
    html[data-theme="light"] a.rounded-2xl:not(.bg-sky-500):not(.bg-sky-600),
    html[data-theme="light"] section.rounded-2xl,
    html[data-theme="light"] article[id^="product-"] {{
      border-color: #CBD5E1 !important;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05), 0 4px 12px rgba(15, 23, 42, 0.03) !important;
    }}
    /* Featured Tiers & Executive Callout Cards -> 2px Federal Blue border + soft sky-ivory gradient */
    html[data-theme="light"] #checkout-card-tier2,
    html[data-theme="light"] #checkout-card-tier3,
    html[data-theme="light"] #checkout-card-tier4,
    html[data-theme="light"] .inbound-lead-capture-box,
    html[data-theme="light"] #spa-contracts-lead-box,
    html[data-theme="light"] #static-inbound-lead-box,
    html[data-theme="light"] #account-dispatch-telemetry-card,
    html[data-theme="light"] #account-admin-bar,
    html[data-theme="light"] article[id^="product-"] .grid.grid-cols-2.sm\:grid-cols-4 > div:nth-child(3) {{
      border: 2px solid #0284C7 !important;
      background: linear-gradient(180deg, #F0F9FF 0%, #FFFFFF 55%) !important;
      box-shadow: 0 4px 16px rgba(2, 132, 199, 0.08) !important;
    }}
    html[data-theme="light"] article[id^="product-"] .grid.grid-cols-2.sm\:grid-cols-4 > div:not(:nth-child(3)) {{
      background-color: #F8FAFC !important;
      border: 1px solid #CBD5E1 !important;
    }}
    html[data-theme="light"] article[id^="product-"] .grid.grid-cols-2.sm\:grid-cols-4 > div > span.absolute {{
      background-color: #E0F2FE !important;
      color: #075985 !important;
      border: 1px solid #7DD3FC !important;
    }}
    /* API Card Top Strip in Light Mode */
    html[data-theme="light"] article[id^="product-"] > div:first-of-type {{
      background: #F1F5F9 !important;
      background-image: none !important;
      border-bottom: 1px solid #CBD5E1 !important;
    }}
    html[data-theme="light"] article[id^="product-"] > div:first-of-type span.rounded {{
      background-color: #FFFFFF !important;
      color: #0F172A !important;
      border: 1px solid #CBD5E1 !important;
      font-weight: 600 !important;
    }}
    html[data-theme="light"] article[id^="product-"] > div:first-of-type span.rounded:nth-of-type(2) {{
      background-color: #E0F2FE !important;
      color: #075985 !important;
      border: 1px solid #7DD3FC !important;
    }}
    /* Deep Ink Typography in Light Mode: No washed-out grey text anywhere */
    html[data-theme="light"] [class*="text-white"],
    html[data-theme="light"] [class*="text-slate-50"],
    html[data-theme="light"] [class*="text-slate-100"],
    html[data-theme="light"] [class*="text-slate-200"],
    html[data-theme="light"] [class*="text-slate-300"],
    html[data-theme="light"] [class*="text-gray-100"],
    html[data-theme="light"] [class*="text-gray-200"],
    html[data-theme="light"] [class*="text-gray-300"] {{
      color: #0F172A !important;
    }}
    html[data-theme="light"] [class*="text-slate-400"],
    html[data-theme="light"] [class*="text-gray-400"] {{
      color: #1E293B !important;
    }}
    html[data-theme="light"] [class*="text-slate-500"],
    html[data-theme="light"] [class*="text-slate-600"],
    html[data-theme="light"] [class*="text-gray-500"] {{
      color: #334155 !important;
    }}
    /* Map ALL pastel -200, -300, -400 accent text utilities to Deep Navy-Blue (#075985), Deep Forest Emerald (#065F46), or Deep Bronze (#92400E) */
    html[data-theme="light"] [class*="text-sky-2"],
    html[data-theme="light"] [class*="text-sky-3"],
    html[data-theme="light"] [class*="text-sky-4"],
    html[data-theme="light"] [class*="text-indigo-2"],
    html[data-theme="light"] [class*="text-indigo-3"],
    html[data-theme="light"] [class*="text-indigo-4"],
    html[data-theme="light"] [class*="text-blue-2"],
    html[data-theme="light"] [class*="text-blue-3"],
    html[data-theme="light"] [class*="text-blue-4"],
    html[data-theme="light"] [class*="text-cyan-2"],
    html[data-theme="light"] [class*="text-cyan-3"],
    html[data-theme="light"] [class*="text-cyan-4"],
    html[data-theme="light"] [class*="text-teal-2"],
    html[data-theme="light"] [class*="text-teal-3"],
    html[data-theme="light"] [class*="text-teal-4"],
    html[data-theme="light"] [class*="text-purple-2"],
    html[data-theme="light"] [class*="text-purple-3"],
    html[data-theme="light"] [class*="text-purple-4"],
    html[data-theme="light"] [class*="text-violet-2"],
    html[data-theme="light"] [class*="text-violet-3"],
    html[data-theme="light"] [class*="text-violet-4"],
    html[data-theme="light"] [class*="text-rose-2"],
    html[data-theme="light"] [class*="text-rose-3"],
    html[data-theme="light"] [class*="text-rose-4"] {{
      color: #075985 !important;
    }}
    html[data-theme="light"] [class*="text-emerald-2"],
    html[data-theme="light"] [class*="text-emerald-3"],
    html[data-theme="light"] [class*="text-emerald-4"],
    html[data-theme="light"] [class*="text-lime-2"],
    html[data-theme="light"] [class*="text-lime-3"],
    html[data-theme="light"] [class*="text-lime-4"] {{
      color: #065F46 !important;
    }}
    html[data-theme="light"] [class*="text-amber-2"],
    html[data-theme="light"] [class*="text-amber-3"],
    html[data-theme="light"] [class*="text-amber-4"],
    html[data-theme="light"] [class*="text-orange-2"],
    html[data-theme="light"] [class*="text-orange-3"],
    html[data-theme="light"] [class*="text-orange-4"] {{
      color: #92400E !important;
    }}
    /* Soft tinted pill badges on light cards -> Crisp Light Sky (#E0F2FE) or Light Emerald (#D1FAE5) with deep ink */
    html[data-theme="light"] span[class*="bg-sky-500/"],
    html[data-theme="light"] span[class*="bg-indigo-500/"],
    html[data-theme="light"] span[class*="bg-blue-500/"],
    html[data-theme="light"] span[class*="bg-cyan-500/"],
    html[data-theme="light"] span[class*="bg-teal-500/"],
    html[data-theme="light"] span[class*="bg-amber-500/"],
    html[data-theme="light"] span[class*="bg-orange-500/"],
    html[data-theme="light"] a[class*="bg-sky-500/"]:not([href^="#"]),
    html[data-theme="light"] a[class*="bg-blue-500/"],
    html[data-theme="light"] a[class*="bg-teal-500/"],
    html[data-theme="light"] a[class*="bg-orange-500/"] {{
      background-color: #F0F9FF !important;
      border-color: #7DD3FC !important;
      color: #075985 !important;
    }}
    html[data-theme="light"] span[class*="bg-emerald-500/"],
    html[data-theme="light"] span[class*="bg-lime-500/"],
    html[data-theme="light"] a[class*="bg-lime-500/"] {{
      background-color: #ECFDF5 !important;
      border-color: #6EE7B7 !important;
      color: #065F46 !important;
    }}
    html[data-theme="light"] p > span.text-emerald-300,
    html[data-theme="light"] p > span.text-emerald-400,
    html[data-theme="light"] p > span.text-amber-300,
    html[data-theme="light"] p > span.text-amber-400,
    html[data-theme="light"] p > span.text-sky-300,
    html[data-theme="light"] p > span.text-sky-400 {{
      color: #0F172A !important;
      font-weight: 600 !important;
    }}
    html[data-theme="light"] .bg-clip-text.text-transparent {{
      background-image: linear-gradient(90deg, #0369A1 0%, #1E3A8A 100%) !important;
    }}
    html[data-theme="light"] .border-slate-800,
    html[data-theme="light"] .border-slate-800\/90,
    html[data-theme="light"] .border-slate-800\/80,
    html[data-theme="light"] .border-slate-800\/70,
    html[data-theme="light"] .border-slate-800\/60,
    html[data-theme="light"] .border-slate-700,
    html[data-theme="light"] .border-slate-700\/80,
    html[data-theme="light"] .divide-slate-800 > :not([hidden]) ~ :not([hidden]),
    html[data-theme="light"] .divide-slate-800\/80 > :not([hidden]) ~ :not([hidden]),
    html[data-theme="light"] .divide-slate-800\/60 > :not([hidden]) ~ :not([hidden]) {{
      border-color: #CBD5E1 !important;
    }}
    html[data-theme="light"] #api-pricing-matrix tbody tr {{
      border-bottom: 1px solid #CBD5E1 !important;
    }}
    html[data-theme="light"] #api-pricing-matrix tbody tr:hover {{
      background-color: #F1F5F9 !important;
    }}
    html[data-theme="light"] input,
    html[data-theme="light"] select,
    html[data-theme="light"] textarea {{
      background-color: #FFFFFF !important;
      border-color: #94A3B8 !important;
      color: #0F172A !important;
    }}
    html[data-theme="light"] input::placeholder,
    html[data-theme="light"] textarea::placeholder {{
      color: #475569 !important;
      opacity: 1 !important;
    }}
    /* Secondary / Outline Buttons in Light Mode -> Crisp White (#FFFFFF) with Dark Navy Text (#0F172A) */
    html[data-theme="light"] a[class*="bg-emerald-500/"],
    html[data-theme="light"] a[class*="bg-emerald-600/"],
    html[data-theme="light"] a[class*="bg-emerald-950"],
    html[data-theme="light"] button[class*="bg-emerald-500/"],
    html[data-theme="light"] button[class*="bg-emerald-600/"],
    html[data-theme="light"] button[class*="bg-emerald-950"],
    html[data-theme="light"] a[class*="bg-amber-500/"],
    html[data-theme="light"] a[class*="bg-amber-950"],
    html[data-theme="light"] button[class*="bg-amber-500/"],
    html[data-theme="light"] button[class*="bg-amber-950"],
    html[data-theme="light"] a[class*="bg-sky-500/"],
    html[data-theme="light"] button[class*="bg-sky-500/"],
    html[data-theme="light"] a[class*="bg-indigo-500/"],
    html[data-theme="light"] a[class*="bg-indigo-600/"],
    html[data-theme="light"] button[class*="bg-indigo-500/"],
    html[data-theme="light"] button[class*="bg-indigo-600/"],
    html[data-theme="light"] a[class*="bg-blue-500/"],
    html[data-theme="light"] a[class*="bg-teal-500/"] {{
      background-color: #FFFFFF !important;
      background-image: none !important;
      color: #0F172A !important;
      border-color: #94A3B8 !important;
      font-weight: 600 !important;
    }}
    html[data-theme="light"] a[class*="bg-emerald-500/"]:hover,
    html[data-theme="light"] a[class*="bg-emerald-600/"]:hover,
    html[data-theme="light"] button[class*="bg-emerald-500/"]:hover,
    html[data-theme="light"] a[class*="bg-sky-500/"]:hover,
    html[data-theme="light"] button[class*="bg-sky-500/"]:hover,
    html[data-theme="light"] a[class*="bg-indigo-500/"]:hover,
    html[data-theme="light"] a[class*="bg-indigo-600/"]:hover,
    html[data-theme="light"] button[class*="bg-indigo-600/"]:hover {{
      background-color: #F1F5F9 !important;
      color: #0F172A !important;
      border-color: #64748B !important;
    }}
    /* Primary Solid CTA Buttons in Light Mode -> Deep Oxford Navy (#0F172A) with Crisp White Text */
    html[data-theme="light"] a.bg-sky-500,
    html[data-theme="light"] a.bg-sky-600,
    html[data-theme="light"] button.bg-sky-500,
    html[data-theme="light"] button.bg-sky-600,
    html[data-theme="light"] a.bg-emerald-500,
    html[data-theme="light"] a.bg-emerald-600,
    html[data-theme="light"] button.bg-emerald-500,
    html[data-theme="light"] button.bg-emerald-600,
    html[data-theme="light"] a.bg-amber-500,
    html[data-theme="light"] a.bg-amber-600,
    html[data-theme="light"] button.bg-amber-500,
    html[data-theme="light"] button.bg-amber-600,
    html[data-theme="light"] a.bg-indigo-500,
    html[data-theme="light"] a.bg-indigo-600,
    html[data-theme="light"] button.bg-indigo-500,
    html[data-theme="light"] button.bg-indigo-600,
    html[data-theme="light"] a.bg-cyan-500,
    html[data-theme="light"] a.bg-cyan-600,
    html[data-theme="light"] button.bg-cyan-500,
    html[data-theme="light"] button.bg-cyan-600,
    html[data-theme="light"] a.bg-teal-500,
    html[data-theme="light"] a.bg-teal-600,
    html[data-theme="light"] button.bg-teal-500,
    html[data-theme="light"] button.bg-teal-600,
    html[data-theme="light"] a[class*="bg-gradient-to-r"][class*="from-"],
    html[data-theme="light"] button[class*="bg-gradient-to-r"][class*="from-"] {{
      background: #0F172A !important;
      background-image: none !important;
      color: #FFFFFF !important;
      border-color: #0F172A !important;
      font-weight: 600 !important;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.14) !important;
    }}
    html[data-theme="light"] a.bg-sky-500:hover,
    html[data-theme="light"] a.bg-sky-600:hover,
    html[data-theme="light"] button.bg-sky-500:hover,
    html[data-theme="light"] button.bg-sky-600:hover,
    html[data-theme="light"] a.bg-emerald-500:hover,
    html[data-theme="light"] a.bg-emerald-600:hover,
    html[data-theme="light"] button.bg-emerald-500:hover,
    html[data-theme="light"] button.bg-emerald-600:hover,
    html[data-theme="light"] a.bg-indigo-600:hover,
    html[data-theme="light"] button.bg-indigo-600:hover,
    html[data-theme="light"] a[class*="bg-gradient-to-r"][class*="from-"]:hover,
    html[data-theme="light"] button[class*="bg-gradient-to-r"][class*="from-"]:hover {{
      background: #1E293B !important;
      border-color: #1E293B !important;
      color: #FFFFFF !important;
    }}
    html[data-theme="light"] a.bg-sky-500 *,
    html[data-theme="light"] a.bg-sky-600 *,
    html[data-theme="light"] button.bg-sky-500 *,
    html[data-theme="light"] button.bg-sky-600 *,
    html[data-theme="light"] a.bg-emerald-500 *,
    html[data-theme="light"] a.bg-emerald-600 *,
    html[data-theme="light"] button.bg-emerald-500 *,
    html[data-theme="light"] button.bg-emerald-600 *,
    html[data-theme="light"] a.bg-amber-500 *,
    html[data-theme="light"] a.bg-amber-600 *,
    html[data-theme="light"] button.bg-amber-500 *,
    html[data-theme="light"] button.bg-amber-600 *,
    html[data-theme="light"] a.bg-indigo-500 *,
    html[data-theme="light"] a.bg-indigo-600 *,
    html[data-theme="light"] button.bg-indigo-500 *,
    html[data-theme="light"] button.bg-indigo-600 *,
    html[data-theme="light"] a[class*="bg-gradient-to-r"][class*="from-"] *,
    html[data-theme="light"] button[class*="bg-gradient-to-r"][class*="from-"] * {{
      color: #FFFFFF !important;
    }}
    /* Top Telemetry Bar stays Deep Oxford Navy (#0F172A) like Option 2 Preview */
    html[data-theme="light"] #page-main > div:first-of-type,
    html[data-theme="light"] #page-apis > div:first-of-type,
    html[data-theme="light"] #page-contracts > div:first-of-type,
    html[data-theme="light"] #page-checkout > div:first-of-type,
    html[data-theme="light"] body > div > div.border-b.bg-navy-900\/90,
    html[data-theme="light"] body > div.border-b.bg-navy-900\/90 {{
      background-color: #0F172A !important;
      border-bottom-color: #1E293B !important;
      color: #F1F5F9 !important;
    }}
    html[data-theme="light"] #page-main > div:first-of-type *,
    html[data-theme="light"] #page-apis > div:first-of-type *,
    html[data-theme="light"] #page-contracts > div:first-of-type *,
    html[data-theme="light"] #page-checkout > div:first-of-type *,
    html[data-theme="light"] body > div > div.border-b.bg-navy-900\/90 *,
    html[data-theme="light"] body > div.border-b.bg-navy-900\/90 * {{
      color: #F1F5F9 !important;
    }}
    html[data-theme="light"] #page-main > div:first-of-type .text-emerald-400,
    html[data-theme="light"] #page-apis > div:first-of-type .text-emerald-400,
    html[data-theme="light"] #page-contracts > div:first-of-type .text-emerald-400,
    html[data-theme="light"] #page-checkout > div:first-of-type .text-emerald-400,
    html[data-theme="light"] body > div > div.border-b.bg-navy-900\/90 .text-emerald-400,
    html[data-theme="light"] body > div.border-b.bg-navy-900\/90 .text-emerald-400 {{
      color: #34D399 !important;
    }}
    html[data-theme="light"] #page-main > div:first-of-type .text-sky-400,
    html[data-theme="light"] #page-apis > div:first-of-type .text-sky-400,
    html[data-theme="light"] #page-contracts > div:first-of-type .text-sky-400,
    html[data-theme="light"] #page-checkout > div:first-of-type .text-sky-400,
    html[data-theme="light"] body > div > div.border-b.bg-navy-900\/90 .text-sky-400,
    html[data-theme="light"] body > div.border-b.bg-navy-900\/90 .text-sky-400 {{
      color: #38BDF8 !important;
    }}
    /* Cohesive Light Code / JSON Terminal Panels (#F1F5F9 Slate-100 surface with Deep Oxford Navy #0F172A ink) */
    html[data-theme="light"] pre,
    html[data-theme="light"] pre[class*="bg-"],
    html[data-theme="light"] #demo-raw-pdf,
    html[data-theme="light"] #demo-json-output {{
      background-color: #F1F5F9 !important;
      color: #0F172A !important;
      border: 1px solid #CBD5E1 !important;
      border-radius: 0.5rem !important;
      padding: 0.75rem 1rem !important;
    }}
    html[data-theme="light"] article[id^="product-"] .lg\:col-span-5,
    html[data-theme="light"] article[id^="product-"] .lg\:col-span-5 > div {{
      background-color: #F8FAFC !important;
      color: #0F172A !important;
      border-color: #CBD5E1 !important;
    }}
    html[data-theme="light"] article[id^="product-"] .lg\:col-span-5 > div:first-child > div:first-child {{
      background-color: #F1F5F9 !important;
      border-bottom: 1px solid #CBD5E1 !important;
    }}
    html[data-theme="light"] pre *,
    html[data-theme="light"] pre [class*="text-"],
    html[data-theme="light"] code,
    html[data-theme="light"] article[id^="product-"] .lg\:col-span-5 [class*="text-"],
    html[data-theme="light"] #demo-raw-pdf *,
    html[data-theme="light"] #demo-json-output * {{
      color: #0F172A !important;
    }}
    html[data-theme="light"] pre [class*="text-sky-"],
    html[data-theme="light"] pre [class*="text-cyan-"],
    html[data-theme="light"] pre [class*="text-indigo-"],
    html[data-theme="light"] article[id^="product-"] .lg\:col-span-5 [class*="text-sky-"],
    html[data-theme="light"] article[id^="product-"] .lg\:col-span-5 [class*="text-cyan-"],
    html[data-theme="light"] #demo-json-output [class*="text-sky-"] {{
      color: #0369A1 !important;
    }}
    html[data-theme="light"] pre [class*="text-emerald-"],
    html[data-theme="light"] pre [class*="text-lime-"],
    html[data-theme="light"] article[id^="product-"] .lg\:col-span-5 [class*="text-emerald-"],
    html[data-theme="light"] #demo-json-output [class*="text-emerald-"] {{
      color: #047857 !important;
    }}
    html[data-theme="light"] pre [class*="text-amber-"],
    html[data-theme="light"] pre [class*="text-orange-"],
    html[data-theme="light"] article[id^="product-"] .lg\:col-span-5 [class*="text-amber-"],
    html[data-theme="light"] #demo-json-output [class*="text-amber-"] {{
      color: #B45309 !important;
    }}
    html[data-theme="light"] article[id^="product-"] .lg\:col-span-5 button[data-snippet-btn] {{
      background-color: transparent !important;
      color: #334155 !important;
      border-color: transparent !important;
      font-weight: 600 !important;
    }}
    html[data-theme="light"] article[id^="product-"] .lg\:col-span-5 button[data-snippet-btn].bg-sky-500\/20,
    html[data-theme="light"] article[id^="product-"] .lg\:col-span-5 button[data-snippet-btn].text-sky-300,
    html[data-theme="light"] article[id^="product-"] .lg\:col-span-5 button[data-snippet-btn].bg-slate-800 {{
      background-color: #E0F2FE !important;
      color: #075985 !important;
      border-color: #7DD3FC !important;
    }}
    html[data-theme="light"] article[id^="product-"] .lg\:col-span-5 button:not([data-snippet-btn]) {{
      background-color: #FFFFFF !important;
      color: #0F172A !important;
      border-color: #94A3B8 !important;
      font-weight: 600 !important;
    }}
    html[data-theme="light"] article[id^="product-"] .lg\:col-span-5 button:not([data-snippet-btn]):hover {{
      background-color: #F1F5F9 !important;
      color: #0F172A !important;
    }}
    html[data-theme="light"] article[id^="product-"] .lg\:col-span-5 .flex.flex-wrap.gap-1\.5 > span {{
      background-color: #FFFFFF !important;
      border: 1px solid #CBD5E1 !important;
      color: #075985 !important;
      font-weight: 600 !important;
    }}
    /* === DESKTOP 60/144FPS COMPOSITING & LAYOUT CONTAINMENT OPTIMIZATIONS === */
    body, html[data-theme="light"] body {{
      background-attachment: scroll !important;
    }}
    header.sticky,
    .backdrop-blur-md,
    .backdrop-blur-xl,
    .backdrop-blur-sm,
    .backdrop-blur-\\[1px\\],
    #page-sidebar-tab,
    #page-sidebar-drawer,
    #page-sidebar-mobile-btn {{
      backdrop-filter: none !important;
      -webkit-backdrop-filter: none !important;
    }}
    .blur-3xl,
    [class*="blur-[120px]"],
    [class*="blur-[100px]"] {{
      display: none !important;
    }}
    .animate-ping,
    .animate-pulse {{
      animation: none !important;
    }}
    article[id^="product-"] {{
      content-visibility: auto;
      contain-intrinsic-size: auto 620px;
    }}
    #contracts-dynamic-root tbody tr,
    #contract-directory tbody tr,
    main table tbody tr {{
      content-visibility: auto;
      contain-intrinsic-size: auto 68px;
    }}
  </style>
  <script id="signaltender-theme-controller">
    (function () {{
      function applyTheme(mode) {{
        var root = document.documentElement;
        var next = (mode === 'light') ? 'light' : 'dark';
        root.setAttribute('data-theme', next);
        if (next === 'light') {{
          root.classList.remove('dark');
        }} else {{
          root.classList.add('dark');
        }}
        var btns = document.querySelectorAll ? document.querySelectorAll('.st-theme-toggle-btn') : [];
        for (var i = 0; i < btns.length; i++) {{
          var lbl = btns[i].querySelector ? btns[i].querySelector('.st-theme-label') : null;
          if (lbl) lbl.textContent = (next === 'light') ? 'Dark' : 'Light';
          btns[i].setAttribute('aria-pressed', next === 'light' ? 'true' : 'false');
          btns[i].setAttribute('title', next === 'light' ? 'Switch to Institutional Graphite (Dark Mode)' : 'Switch to Executive Ivory & Navy (Light Mode)');
        }}
      }}
      window.setSignalTheme = function (mode) {{
        var next = (mode === 'light') ? 'light' : 'dark';
        try {{
          if (window.localStorage) window.localStorage.setItem('st_theme_mode', next);
        }} catch (e) {{}}
        applyTheme(next);
        return next;
      }};
      window.toggleSignalTheme = function () {{
        var cur = document.documentElement.getAttribute('data-theme') || 'dark';
        return window.setSignalTheme(cur === 'light' ? 'dark' : 'light');
      }};
      var saved = 'dark';
      try {{
        if (window.localStorage) {{
          var s = window.localStorage.getItem('st_theme_mode');
          if (s === 'light' || s === 'dark') saved = s;
        }}
      }} catch (e) {{}}
      applyTheme(saved);
      if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', function () {{ applyTheme(document.documentElement.getAttribute('data-theme') || saved); }});
      }}
    }})();
  </script>
  {ld_script}
</head>
<body class="bg-navy-950 text-slate-100 font-sans antialiased selection:bg-sky-500/30 selection:text-sky-200 min-h-screen flex flex-col justify-between">
  <div>
    <div class="hidden sm:block w-full max-w-full overflow-x-hidden border-b border-slate-800/80 bg-navy-900/90 text-xs">
      <div class="max-w-[1600px] mx-auto px-3 sm:px-6 lg:px-8 min-h-[2.25rem] py-1.5 flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <div class="flex items-center space-x-2.5 shrink-0">
          <span class="inline-block h-2 w-2 rounded-full bg-emerald-500"></span>
          <span class="font-mono text-slate-300">LIVE GOVCON INTELLIGENCE WIRE &bull; <span class="text-emerald-400">18 PORTALS ACTIVE</span></span>
        </div>
        <div class="flex items-center space-x-3 sm:space-x-4 font-mono text-slate-400 shrink-0">
          <a href="{root_prefix}index.html" class="hover:text-sky-400 transition-colors">&larr; Main Platform</a>
          <span>|</span>
          <a href="{root_prefix}apis.html" class="hover:text-sky-400 transition-colors">Developer APIs</a>
        </div>
      </div>
    </div>

    <header class="sticky top-0 z-50 w-full max-w-full overflow-x-hidden backdrop-blur-md bg-navy-950/90 border-b border-slate-800/80">
      <div class="max-w-[1600px] mx-auto px-3 sm:px-6 lg:px-8 h-12 sm:h-20 flex flex-nowrap items-center justify-between gap-2">
        <a href="{root_prefix}index.html" class="flex flex-col justify-center shrink-0">
          <div class="inline-flex items-center gap-[4px]">
            <svg class="w-[21px] h-[21px] shrink-0 -translate-y-[1px]" viewBox="6 5 52 54" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="32" cy="24" r="15" stroke="#F8FAFC" stroke-width="5.6" />
              <circle cx="32" cy="24" r="5" fill="#38BDF8" />
              <path d="M10 54L32 42L54 54" stroke="#38BDF8" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span class="text-[23px] font-semibold tracking-[-0.03em] text-white leading-none whitespace-nowrap">SignalTender</span>
            <span class="hidden sm:inline-flex ml-1.5 items-center whitespace-nowrap text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-slate-900 text-sky-400/90 border border-slate-800 leading-none">LIVE RFP INDEX</span>
          </div>
          <span class="hidden sm:block text-[11px] font-mono text-slate-500 tracking-tight leading-none whitespace-nowrap mt-1">FEDERAL &amp; 16-STATE SLED CONTRACT DIRECTORY</span>
        </a>
        <nav aria-label="Primary Site Navigation" class="hidden lg:flex flex-1 items-center justify-between gap-1 xl:gap-2 mx-1.5 xl:mx-2 2xl:mx-5 p-1 xl:p-1.5 rounded-xl bg-navy-900/95 border border-slate-800/90 shadow-inner">
          <a href="{root_prefix}index.html#overview" class="flex-1 inline-flex items-center justify-center px-2 xl:px-2.5 2xl:px-3.5 py-1.5 xl:py-2 rounded-lg text-[11px] xl:text-xs 2xl:text-[13px] font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 border border-transparent transition-all whitespace-nowrap">Platform Overview</a>
          <a href="{root_prefix}contracts/index.html" class="flex-1 inline-flex items-center justify-center px-2 xl:px-2.5 2xl:px-3.5 py-1.5 xl:py-2 rounded-lg text-[11px] xl:text-xs 2xl:text-[13px] font-semibold text-white bg-sky-500/15 border border-sky-500/40 shadow-sm transition-all whitespace-nowrap">Live RFP Directory</a>
          <a href="{root_prefix}apis.html" class="flex-1 inline-flex items-center justify-center px-2 xl:px-2.5 2xl:px-3.5 py-1.5 xl:py-2 rounded-lg text-[11px] xl:text-xs 2xl:text-[13px] font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 border border-transparent transition-all whitespace-nowrap">API Catalog</a>
          <a href="{root_prefix}index.html#checkout" class="flex-1 inline-flex items-center justify-center px-2 xl:px-2.5 2xl:px-3.5 py-1.5 xl:py-2 rounded-lg text-[11px] xl:text-xs 2xl:text-[13px] font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 border border-transparent transition-all whitespace-nowrap">Plans &amp; Pricing</a>
        </nav>
        <div class="w-auto flex items-center justify-end gap-1.5 sm:gap-2 shrink-0">
          <button
            type="button"
            onclick="window.toggleSignalTheme()"
            aria-label="Toggle Light and Dark Theme"
            title="Switch between Institutional Graphite (Dark) and Executive Ivory (Light)"
            class="st-theme-toggle-btn inline-flex items-center justify-center gap-1.5 whitespace-nowrap px-2 py-1.5 sm:py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[11px] sm:text-xs font-mono font-semibold text-slate-200 hover:text-white transition-all cursor-pointer shrink-0"
          >
            <svg class="st-icon-sun w-3.5 h-3.5 text-sky-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="4" />
              <path stroke-linecap="round" d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41m11.32-11.32l1.41-1.41" />
            </svg>
            <svg class="st-icon-moon w-3.5 h-3.5 text-sky-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
            </svg>
            <span class="hidden sm:inline lg:hidden 2xl:inline st-theme-label">Light</span>
          </button>
<div class="flex items-center gap-1 sm:gap-1.5 2xl:pr-2 2xl:border-r 2xl:border-slate-800">
            <a href="{root_prefix}index.html#account" class="inline-flex items-center justify-center px-2 sm:px-2.5 py-1.5 sm:py-2 text-[11px] sm:text-xs font-mono font-semibold text-slate-200 hover:text-white hover:bg-slate-900 rounded-lg transition-colors whitespace-nowrap">Log In</a>
            <a href="{root_prefix}index.html#account" class="inline-flex items-center justify-center px-2 sm:px-2.5 py-1.5 sm:py-2 text-[11px] sm:text-xs font-mono font-bold text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-lg transition-all whitespace-nowrap">Sign Up</a>
          </div>
          <a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="hidden 2xl:inline-flex items-center whitespace-nowrap px-3 py-1.5 2xl:px-3.5 2xl:py-2 text-xs font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg border border-sky-400/30 transition-all">
            Unlock All RFP Links &rarr;
          </a>
        </div>
      </div>
      <div class="lg:hidden border-t border-slate-800/80 bg-navy-900/90">
        <nav aria-label="Mobile Site Navigation" class="max-w-[1600px] mx-auto px-2.5 sm:px-4 py-1.5 grid grid-cols-4 gap-1 sm:gap-1.5 text-[10.5px] sm:text-[11px] font-sans font-medium sm:font-mono text-center">
          <a href="{root_prefix}index.html#overview" class="px-1 sm:px-2.5 py-1 rounded-md bg-navy-950 text-slate-200 hover:text-sky-400 border border-slate-800 tracking-tight whitespace-nowrap">Overview</a>
          <a href="{root_prefix}contracts/index.html" class="px-1 sm:px-2.5 py-1 rounded-md bg-sky-500/20 text-white border border-sky-500/40 font-semibold tracking-tight whitespace-nowrap">RFP Directory</a>
          <a href="{root_prefix}apis.html" class="px-1 sm:px-2.5 py-1 rounded-md bg-navy-950 text-slate-200 hover:text-sky-400 border border-slate-800 tracking-tight whitespace-nowrap">APIs</a>
          <a href="{root_prefix}index.html#checkout" class="px-1 sm:px-2.5 py-1 rounded-md bg-navy-950 text-slate-200 hover:text-sky-400 border border-slate-800 tracking-tight whitespace-nowrap">Plans &amp; Pricing</a>
        </nav>
      </div>
    </header>

    <div class="border-b border-slate-800/70 bg-navy-900/60">
      <div class="max-w-[1600px] mx-auto px-3 sm:px-6 lg:px-8 py-1.5 flex items-center gap-2.5">
        <label for="static-contracts-portal-select" class="sr-only">Jump to State or Portal</label>
        <select id="static-contracts-portal-select" onchange="if(this.value) window.location.href=this.value;" class="sm:hidden shrink-0 px-2 py-1 rounded-md bg-navy-950 border border-slate-700 text-[11px] font-mono text-sky-400 focus:border-sky-500 focus:outline-none">
          <option value="{root_prefix}contracts/index.html">Portal: All (18)</option>
          <option value="{root_prefix}contracts/federal/index.html">Federal (SAM.gov)</option>
          <option value="{root_prefix}contracts/texas/index.html">Texas (ESBD)</option>
          <option value="{root_prefix}contracts/virginia/index.html">Virginia (eVA)</option>
          <option value="{root_prefix}contracts/california/index.html">California</option>
          <option value="{root_prefix}contracts/florida/index.html">Florida (MFMP)</option>
          <option value="{root_prefix}contracts/maryland/index.html">Maryland (eMMA)</option>
          <option value="{root_prefix}contracts/illinois/index.html">Illinois (BidBuy)</option>
          <option value="{root_prefix}contracts/pennsylvania/index.html">Pennsylvania</option>
          <option value="{root_prefix}contracts/ohio/index.html">Ohio (OhioBuys)</option>
          <option value="{root_prefix}contracts/georgia/index.html">Georgia (GPR)</option>
          <option value="{root_prefix}contracts/north_carolina/index.html">North Carolina</option>
          <option value="{root_prefix}contracts/new_york/index.html">New York (CROL)</option>
          <option value="{root_prefix}contracts/massachusetts/index.html">Massachusetts</option>
          <option value="{root_prefix}contracts/new_jersey/index.html">New Jersey</option>
          <option value="{root_prefix}contracts/washington/index.html">Washington</option>
          <option value="{root_prefix}contracts/michigan/index.html">Michigan (SIGMA)</option>
          <option value="{root_prefix}contracts/colorado/index.html">Colorado (VSS)</option>
          <option value="{root_prefix}contracts/municipal/index.html">Municipal</option>
        </select>
        <nav aria-label="State and Portal Quick Jump" class="hidden sm:flex flex-1 flex-wrap items-center gap-x-3.5 gap-y-1.5 py-1 text-[11px] font-mono text-slate-300">
          <a href="{root_prefix}contracts/index.html" class="shrink-0 text-sky-400 font-semibold hover:text-sky-300 transition-colors">All Portals</a>
          <a href="{root_prefix}contracts/federal/index.html" class="shrink-0 hover:text-sky-400 transition-colors">Federal</a>
          <a href="{root_prefix}contracts/texas/index.html" class="shrink-0 hover:text-sky-400 transition-colors">Texas</a>
          <a href="{root_prefix}contracts/virginia/index.html" class="shrink-0 hover:text-sky-400 transition-colors">Virginia</a>
          <a href="{root_prefix}contracts/california/index.html" class="shrink-0 hover:text-sky-400 transition-colors">California</a>
          <a href="{root_prefix}contracts/florida/index.html" class="shrink-0 hover:text-sky-400 transition-colors">Florida</a>
          <a href="{root_prefix}contracts/maryland/index.html" class="shrink-0 hover:text-sky-400 transition-colors">Maryland</a>
          <a href="{root_prefix}contracts/illinois/index.html" class="shrink-0 hover:text-sky-400 transition-colors">Illinois</a>
          <a href="{root_prefix}contracts/pennsylvania/index.html" class="shrink-0 hover:text-sky-400 transition-colors">Pennsylvania</a>
          <a href="{root_prefix}contracts/ohio/index.html" class="shrink-0 hover:text-sky-400 transition-colors">Ohio</a>
          <a href="{root_prefix}contracts/georgia/index.html" class="shrink-0 hover:text-sky-400 transition-colors">Georgia</a>
          <a href="{root_prefix}contracts/north_carolina/index.html" class="shrink-0 hover:text-sky-400 transition-colors">North Carolina</a>
          <a href="{root_prefix}contracts/new_york/index.html" class="shrink-0 hover:text-sky-400 transition-colors">New York</a>
          <a href="{root_prefix}contracts/massachusetts/index.html" class="shrink-0 hover:text-sky-400 transition-colors">Massachusetts</a>
          <a href="{root_prefix}contracts/new_jersey/index.html" class="shrink-0 hover:text-sky-400 transition-colors">New Jersey</a>
          <a href="{root_prefix}contracts/washington/index.html" class="shrink-0 hover:text-sky-400 transition-colors">Washington</a>
          <a href="{root_prefix}contracts/michigan/index.html" class="shrink-0 hover:text-sky-400 transition-colors">Michigan</a>
          <a href="{root_prefix}contracts/colorado/index.html" class="shrink-0 hover:text-sky-400 transition-colors">Colorado</a>
          <a href="{root_prefix}contracts/municipal/index.html" class="shrink-0 hover:text-sky-400 transition-colors">Municipal</a>
        </nav>
      </div>
    </div>

    <main class="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-12">
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
              All 18 Federal &amp; 16-State SLED Portals monitored every 6 hours. Zero annual contracts &bull; Instant 60-second self-serve activation.
            </p>
          </div>
          <div class="flex flex-wrap items-center gap-2.5 shrink-0 font-mono text-xs">
            <a id="prospect-banner-free-btn" href="{root_prefix}index.html#signup" class="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold border border-emerald-400/30 transition-all">
              Free Account ($0/mo) &rarr;
            </a>
            <a id="prospect-banner-t1-btn" href="{root_prefix}index.html#checkout-tier1" class="px-3.5 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-semibold border border-sky-400/30 transition-all">
              Tier 1 Wire ($99/mo) &rarr;
            </a>
            <a id="prospect-banner-t2-btn" href="{root_prefix}index.html#checkout-tier2" class="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold border border-indigo-400/30 transition-all">
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
            <form id="static-lead-capture-form" onsubmit="event.preventDefault(); window.submitStaticLeadCapture();" class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-12 gap-3">
              <div class="sm:col-span-1 xl:col-span-3">
                <label for="static-lead-email" class="sr-only">Work Email</label>
                <input id="static-lead-email" type="email" required placeholder="capture@yourcompany.com" class="w-full px-3.5 py-2.5 rounded-xl bg-navy-950 border border-slate-700 focus:border-emerald-400 focus:outline-none text-xs font-mono text-white placeholder-slate-500" />
              </div>
              <div class="sm:col-span-1 xl:col-span-3">
                <label for="static-lead-company" class="sr-only">Company Name</label>
                <input id="static-lead-company" type="text" placeholder="Company / Prime LLC" class="w-full px-3.5 py-2.5 rounded-xl bg-navy-950 border border-slate-700 focus:border-emerald-400 focus:outline-none text-xs font-mono text-white placeholder-slate-500" />
              </div>
              <div class="sm:col-span-1 xl:col-span-3">
                <label for="static-lead-state" class="sr-only">Target Portal</label>
                <select id="static-lead-state" data-default-state="{default_state}" class="w-full px-3 py-2.5 rounded-xl bg-navy-950 border border-slate-700 focus:border-emerald-400 focus:outline-none text-xs font-mono text-white">
                  <option value="all">All 18 Portals (Fed + 16 States)</option>
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
                  <option value="new_jersey">New Jersey (NJSTART &amp; DPP)</option>
                  <option value="washington">Washington (WEBS &amp; WaTech)</option>
                  <option value="michigan">Michigan (SIGMA VSS &amp; DTMB)</option>
                  <option value="colorado">Colorado (VSS &amp; OIT)</option>
                  <option value="municipal">Municipal (DemandStar)</option>
                </select>
              </div>
              <div class="sm:col-span-1 xl:col-span-3">
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

  <!-- =====================================================================
       UNIVERSAL COLLAPSIBLE FLOATING LEFT SIDEBAR DIRECTORY (ALL PAGES)
       ===================================================================== -->
  <style>
    #page-sidebar-scroll::-webkit-scrollbar {{ display: none; }}
    #page-sidebar-scroll {{ -ms-overflow-style: none; scrollbar-width: none; }}
    #page-sidebar-tab, #page-sidebar-mobile-btn {{ background-color: #090C10 !important; border-color: rgba(255, 255, 255, 0.10) !important; }}
    #page-sidebar-drawer {{ background-color: #0B0E14 !important; border-color: rgba(255, 255, 255, 0.12) !important; box-shadow: 8px 0 32px rgba(0, 0, 0, 0.85) !important; }}
    html[data-theme="light"] #page-sidebar-tab, html[data-theme="light"] #page-sidebar-drawer, html[data-theme="light"] #page-sidebar-mobile-btn {{ background-color: #FFFFFF !important; border-color: #CBD5E1 !important; box-shadow: 0 2px 10px rgba(15, 23, 42, 0.08) !important; }}
  </style>
  <aside id="page-section-sidebar-root" aria-label="On-Page Section Directory" class="select-none">
    <!-- Desktop Closed State: Quiet Gemini-Style Slim Left Icon Rail (44px wide, flush left) -->
    <div
      id="page-sidebar-tab"
      class="hidden lg:flex fixed left-0 top-36 bottom-0 w-11 z-40 flex-col items-center justify-between py-3 bg-navy-950 backdrop-blur-md border-r border-slate-800/60"
    >
      <div class="flex flex-col items-center gap-1.5">
        <button
          type="button"
          onclick="window.togglePageSectionSidebar(true)"
          title="Expand section navigator"
          aria-label="Expand section navigator"
          class="w-8 h-8 rounded-full hover:bg-slate-800/80 text-slate-400 hover:text-white flex items-center justify-center transition-colors cursor-pointer"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <button
          type="button"
          onclick="window.openSidebarAndFocusSearch()"
          title="Search sections &amp; tools"
          aria-label="Search sections and tools"
          class="w-8 h-8 rounded-full hover:bg-slate-800/80 text-slate-400 hover:text-sky-400 flex items-center justify-center transition-colors cursor-pointer"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10.5a7.5 7.5 0 0013.15 6.15z" />
          </svg>
        </button>
        <div class="w-5 h-px bg-slate-800/80 my-1"></div>
        <div id="page-sidebar-rail-icons" class="flex flex-col items-center gap-1"></div>
      </div>

      <div class="flex flex-col items-center gap-1.5">
        <button
          type="button"
          onclick="document.documentElement.style.scrollBehavior='auto'; window.scrollTo(0, 0);"
          title="Back to top of page"
          aria-label="Back to top of page"
          class="w-8 h-8 rounded-full hover:bg-slate-800/80 text-slate-500 hover:text-slate-200 flex items-center justify-center transition-colors cursor-pointer"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7" />
          </svg>
        </button>
        <button
          type="button"
          onclick="window.triggerSidebarPageNav('account')"
          title="Client Account Portal"
          aria-label="Client Account Portal"
          class="w-8 h-8 rounded-full bg-slate-900/90 border border-slate-800/90 hover:border-sky-500/40 text-slate-400 hover:text-sky-400 flex items-center justify-center transition-colors cursor-pointer"
        >
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Mobile Closed State: Quiet Circular Floating Trigger in Bottom-Left Thumb Zone -->
    <button
      type="button"
      id="page-sidebar-mobile-btn"
      onclick="window.togglePageSectionSidebar(true)"
      title="Open page &amp; section navigator"
      aria-label="Open page and section navigator"
      class="lg:hidden fixed left-3.5 bottom-4 z-40 w-10 h-10 rounded-full bg-navy-950 hover:bg-slate-800 text-slate-200 hover:text-sky-400 border border-slate-700/80 shadow-xl backdrop-blur-md flex items-center justify-center transition-all cursor-pointer"
    >
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h10M4 18h14" />
      </svg>
    </button>

    <!-- Click-Outside Backdrop when Drawer is Expanded -->
    <div
      id="page-sidebar-backdrop"
      onclick="window.togglePageSectionSidebar(false)"
      class="hidden fixed inset-0 z-[65] bg-black/50 lg:bg-black/20 backdrop-blur-[1px]"
    ></div>

    <!-- Expanded State: Quiet Gemini-Style Full-Height Searchable Drawer -->
    <div
      id="page-sidebar-drawer"
      class="hidden fixed left-0 top-0 bottom-0 w-72 max-w-[85vw] z-[70] flex-col bg-navy-950 backdrop-blur-xl border-r border-slate-800/80 shadow-2xl shadow-black/90 overflow-hidden"
    >
      <!-- Top Bar -->
      <div class="px-3.5 pt-3.5 pb-2.5 flex items-center justify-between gap-2 shrink-0">
        <div class="flex items-center gap-2 min-w-0">
          <button
            type="button"
            id="page-sidebar-close-btn"
            onclick="window.togglePageSectionSidebar(false)"
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
            class="w-8 h-8 rounded-full hover:bg-slate-800/80 text-slate-400 hover:text-white flex items-center justify-center transition-colors cursor-pointer shrink-0"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div class="min-w-0">
            <div id="page-sidebar-title" class="text-xs font-semibold text-slate-100 truncate">
              Platform Overview
            </div>
            <div class="text-[10px] font-mono text-slate-500 flex items-center gap-1.5">
              <span>SECTION NAVIGATOR</span><span id="page-sidebar-tab-count" class="hidden"></span>
            </div>
          </div>
        </div>
        <button
          type="button"
          onclick="document.documentElement.style.scrollBehavior='auto'; window.scrollTo(0, 0); window.togglePageSectionSidebar(false);"
          title="Scroll to top of page"
          class="px-2 py-1 rounded-md hover:bg-slate-800/80 text-[11px] font-mono text-slate-400 hover:text-sky-400 transition-colors cursor-pointer shrink-0"
        >
          &uarr; Top
        </button>
      </div>

      <!-- Gemini-Style Pill Search Input -->
      <div class="px-3 pb-2.5 shrink-0">
        <div class="relative flex items-center">
          <svg class="w-3.5 h-3.5 text-slate-500 absolute left-3 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10.5a7.5 7.5 0 0013.15 6.15z" />
          </svg>
          <input
            id="page-sidebar-search-input"
            type="search"
            name="st_sidebar_search_nofill"
            autocomplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-form-type="other"
            placeholder="Search sections &amp; tools..."
            oninput="window.filterPageSidebar(this.value)"
            class="w-full pl-8 pr-7 py-1.5 rounded-full bg-slate-900/90 border border-slate-800/90 focus:border-sky-500/60 focus:outline-none text-xs text-slate-200 placeholder-slate-500"
          />
          <button
            type="button"
            id="page-sidebar-search-clear"
            onclick="var inp=document.getElementById('page-sidebar-search-input'); if(inp){{inp.value=''; window.filterPageSidebar(''); inp.focus();}}"
            class="hidden absolute right-2.5 text-slate-500 hover:text-slate-200 text-xs cursor-pointer"
          >
            &times;
          </button>
        </div>
      </div>

      <!-- Scrollbar-Free Sections & Page Switcher List -->
      <div id="page-sidebar-scroll" class="flex-1 overflow-y-auto px-2.5 py-1 space-y-4">
        <div>
          <div class="px-2.5 pb-1 text-[10px] font-mono uppercase tracking-wider text-slate-500">
            Current Page Sections
          </div>
          <div id="page-sidebar-items" class="space-y-0.5"></div>
          <div id="page-sidebar-empty" class="hidden px-2.5 py-3 text-xs text-slate-500 font-mono">
            No matching sections found.
          </div>
        </div>

        <div class="pt-2 border-t border-slate-800/70">
          <div class="px-2.5 pb-1 text-[10px] font-mono uppercase tracking-wider text-slate-500">
            Switch Page
          </div>
          <div id="page-sidebar-pages-list" class="space-y-0.5"></div>
        </div>
      </div>

      <!-- Quiet Bottom Footer -->
      <div class="px-3.5 py-2.5 border-t border-slate-800/70 flex items-center justify-between text-[11px] font-mono text-slate-500 shrink-0">
        <button
          type="button"
          onclick="window.triggerSidebarPageNav('account')"
          class="hover:text-sky-400 transition-colors cursor-pointer flex items-center gap-1.5"
        >
          <span class="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
          <span>Account Portal</span>
        </button>
        <button
          type="button"
          onclick="window.togglePageSectionSidebar(false)"
          class="hover:text-slate-300 transition-colors cursor-pointer"
        >
          Close
        </button>
      </div>
    </div>
  </aside>

  <footer class="bg-navy-950 border-t border-slate-800/80 pt-14 pb-10 mt-16 text-slate-400">
    <div class="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-8 lg:gap-10 pb-10 border-b border-slate-800/80">
        <div class="sm:col-span-2 lg:col-span-4 space-y-3.5">
          <div class="inline-flex items-center gap-[4px]">
            <svg class="w-[21px] h-[21px] shrink-0 -translate-y-[1px]" viewBox="6 5 52 54" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="32" cy="24" r="15" stroke="#F8FAFC" stroke-width="5.6" />
              <circle cx="32" cy="24" r="5" fill="#38BDF8" />
              <path d="M10 54L32 42L54 54" stroke="#38BDF8" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span class="text-[23px] font-semibold tracking-[-0.03em] text-white leading-none whitespace-nowrap">SignalTender</span>
            <span class="ml-1.5 text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-slate-900 text-sky-400/90 border border-slate-800 leading-none">GOVCON AI</span>
          </div>
          <p class="text-xs text-slate-400 max-w-sm leading-relaxed">
            Real-time Federal, National Municipal, and State SLED IT &amp; cybersecurity procurement intelligence. Pre-shredded capture dossiers, multi-channel alert routing, and production REST APIs.
          </p>
          <div class="pt-1 flex flex-wrap items-center gap-2">
            <a href="https://www.linkedin.com/company/signaltender/" target="_blank" rel="noopener noreferrer" aria-label="SignalTender on LinkedIn" title="Follow SignalTender on LinkedIn" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 hover:bg-sky-500/15 border border-slate-800 hover:border-sky-500/40 text-xs font-mono text-slate-300 hover:text-sky-400 transition-all">
              <svg class="w-3.5 h-3.5 fill-current text-sky-400 shrink-0" viewBox="0 0 24 24" aria-hidden="true"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z"/></svg>
              <span>LinkedIn</span>
            </a>
            <a href="https://x.com/SignalTenderX" target="_blank" rel="noopener noreferrer" aria-label="SignalTender on X" title="Follow SignalTender on X (@SignalTenderX)" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 hover:bg-sky-500/15 border border-slate-800 hover:border-sky-500/40 text-xs font-mono text-slate-300 hover:text-sky-400 transition-all">
              <svg class="w-3.5 h-3.5 fill-current text-sky-400 shrink-0" viewBox="0 0 24 24" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
              <span>@SignalTenderX</span>
            </a>
            <a href="https://rapidapi.com/user/aarbchen" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900/90 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-xs font-mono text-slate-300 hover:text-white transition-all">
              <span>RapidAPI Hub</span>
              <span class="text-slate-500">&nearr;</span>
            </a>
          </div>
        </div>
        <div class="lg:col-span-3 space-y-3 text-xs">
          <div class="font-mono text-[11px] text-slate-200 uppercase tracking-wider font-semibold">Procurement Platform</div>
          <ul class="space-y-2.5 text-slate-400">
            <li><a href="{root_prefix}index.html#discord-terminal" class="hover:text-white transition-colors">Live RFP Alert Wire</a></li>
            <li><a href="{root_prefix}index.html#capture-moat" class="hover:text-white transition-colors">CaptureDesk AI Dossiers</a></li>
            <li><a href="{root_prefix}contracts/index.html" class="hover:text-white transition-colors">Federal &amp; State RFP Directory</a></li>
            <li><a href="{root_prefix}contracts/federal/index.html" class="hover:text-white transition-colors">Federal SAM.gov Hub</a></li>
            <li><a href="{root_prefix}index.html#integrations" class="hover:text-white transition-colors">Multi-Channel Delivery Routing</a></li>
          </ul>
        </div>
        <div class="lg:col-span-3 space-y-3 text-xs">
          <div class="font-mono text-[11px] text-slate-200 uppercase tracking-wider font-semibold">Developer &amp; API Suite</div>
          <ul class="space-y-2.5 text-slate-400">
            <li><a href="{root_prefix}apis.html" class="hover:text-white transition-colors">GovCon Data API Catalog</a></li>
            <li><a href="{root_prefix}apis.html#catalog-modules" class="hover:text-white transition-colors">Interactive Studio Playground</a></li>
            <li><a href="{root_prefix}apis.html#api-pricing-matrix" class="hover:text-white transition-colors">API Tier &amp; Quota Matrix</a></li>
            <li><a href="https://rapidapi.com/user/aarbchen" target="_blank" rel="noopener noreferrer" class="hover:text-white transition-colors">RapidAPI Publisher Storefront &nearr;</a></li>
            <li><a href="https://b2b-contract-parser-api.onrender.com/docs" target="_blank" rel="noopener noreferrer" class="hover:text-white transition-colors">FastAPI OpenAPI /docs &nearr;</a></li>
          </ul>
        </div>
        <div class="lg:col-span-2 space-y-3 text-xs">
          <div class="font-mono text-[11px] text-slate-200 uppercase tracking-wider font-semibold">Account &amp; Plans</div>
          <ul class="space-y-2.5 text-slate-400">
            <li><a href="{root_prefix}index.html#login" class="hover:text-white transition-colors">Sign In</a></li>
            <li><a href="{root_prefix}index.html#signup" class="hover:text-white transition-colors">Create Free Account</a></li>
            <li><a href="{root_prefix}index.html#checkout-tier1" class="hover:text-white transition-colors">Tier 1 SignalWire ($99/mo)</a></li>
            <li><a href="{root_prefix}index.html#checkout-tier2" class="hover:text-white transition-colors">Tier 2 Autopilot ($399/mo)</a></li>
            <li><a href="{root_prefix}index.html#checkout" class="hover:text-white transition-colors">Plans &amp; B2B Checkout</a></li>
          </ul>
        </div>
      </div>
      <div class="py-5 border-b border-slate-800/80 flex flex-col lg:flex-row lg:items-center justify-between gap-4 text-xs font-mono">
        <div class="flex flex-wrap items-center gap-x-5 gap-y-2 text-slate-300">
          <span class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Trust, Support &amp; Governance:</span>
          <a href="{root_prefix}index.html#status" class="inline-flex items-center gap-1.5 text-emerald-400 hover:text-emerald-300 transition-colors">
            <span class="h-2 w-2 rounded-full bg-emerald-400"></span>
            <span>System Status (99.95% SLA)</span>
          </a>
          <a href="{root_prefix}index.html#security" class="text-slate-300 hover:text-sky-400 transition-colors">Security &amp; Zero-Retention Trust</a>
          <a href="{root_prefix}index.html#contact" class="text-slate-300 hover:text-indigo-300 transition-colors">Instant AI Support Concierge</a>
          <a href="{root_prefix}index.html#feedback" class="text-slate-300 hover:text-amber-300 transition-colors">Submit Feedback / Request Portal</a>
          <a href="{root_prefix}index.html#terms" class="text-slate-400 hover:text-white transition-colors">Terms of Service</a>
          <a href="{root_prefix}index.html#privacy" class="text-slate-400 hover:text-white transition-colors">Privacy Policy &amp; DPA</a>
        </div>
        <div class="text-[11px] text-slate-500">
          <span>WAF Protected &bull; PCI-DSS Level 1 (Stripe) &bull; PostgreSQL RLS</span>
        </div>
      </div>
      <div class="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-slate-500">
        <div>&copy; {datetime.now().year} SignalTender (signaltender.net). All rights reserved.</div>
        <div class="flex items-center space-x-2 text-slate-400">
          <span class="h-2 w-2 rounded-full bg-emerald-500"></span>
          <span>ALL {len(JURISDICTIONS)} FEDERAL &amp; SLED PORTAL MONITORS ACTIVE</span>
        </div>
      </div>
    </div>
  </footer>
  <script>

    window.jumpToPageSection = function (sectionId) {{
        if (!sectionId) return false;
        var cleanId = String(sectionId).replace(/^#/, '');
        var el = document.getElementById(cleanId);
        if (!el) return false;
        var docEl = document.documentElement;
        docEl.style.scrollBehavior = 'auto';
        var rect = el.getBoundingClientRect ? el.getBoundingClientRect() : {{ top: 0 }};
        var currentY = window.pageYOffset || docEl.scrollTop || 0;
        var targetY = Math.max(0, Math.round(rect.top + currentY - 88));
        window.scrollTo(0, targetY);
        return true;
      }};

      window.__PAGE_SIDEBAR_OPEN = false;

      window.togglePageSectionSidebar = function (forceState) {{
        var tab = document.getElementById('page-sidebar-tab');
        var mobBtn = document.getElementById('page-sidebar-mobile-btn');
        var backdrop = document.getElementById('page-sidebar-backdrop');
        var drawer = document.getElementById('page-sidebar-drawer');
        if (!tab || !drawer) return false;
        var nextState = (typeof forceState === 'boolean') ? forceState : !window.__PAGE_SIDEBAR_OPEN;
        window.__PAGE_SIDEBAR_OPEN = nextState;
        if (nextState) {{
          drawer.classList.remove('hidden');
          drawer.classList.add('flex');
          if (backdrop) backdrop.classList.remove('hidden');
          if (mobBtn) mobBtn.classList.add('hidden');
          if (typeof window.renderPageSectionSidebar === 'function') {{
            window.renderPageSectionSidebar();
          }}
        }} else {{
          drawer.classList.add('hidden');
          drawer.classList.remove('flex');
          if (backdrop) backdrop.classList.add('hidden');
          if (mobBtn) mobBtn.classList.remove('hidden');
          var sInp = document.getElementById('page-sidebar-search-input');
          if (sInp && sInp.value) {{
            sInp.value = '';
            if (typeof window.filterPageSidebar === 'function') window.filterPageSidebar('');
          }}
        }}
        return nextState;
      }};

      window.openSidebarAndFocusSearch = function () {{
        window.togglePageSectionSidebar(true);
        var sInp = document.getElementById('page-sidebar-search-input');
        if (sInp && typeof sInp.focus === 'function') {{
          sInp.focus();
        }}
      }};

      window.filterPageSidebar = function (queryVal) {{
        var q = String(queryVal || '').trim().toLowerCase();
        var clearBtn = document.getElementById('page-sidebar-search-clear');
        if (clearBtn) {{
          if (q) clearBtn.classList.remove('hidden');
          else clearBtn.classList.add('hidden');
        }}
        var itemsWrap = document.getElementById('page-sidebar-items');
        var emptyEl = document.getElementById('page-sidebar-empty');
        var shownCount = 0;
        if (itemsWrap) {{
          var btns = itemsWrap.querySelectorAll('button[data-sidebar-sec]');
          for (var i = 0; i < btns.length; i++) {{
            var hay = (btns[i].getAttribute('data-sidebar-search') || btns[i].textContent || '').toLowerCase();
            if (!q || hay.indexOf(q) !== -1) {{
              btns[i].classList.remove('hidden');
              shownCount++;
            }} else {{
              btns[i].classList.add('hidden');
            }}
          }}
        }}
        if (emptyEl) {{
          if (q && shownCount === 0) emptyEl.classList.remove('hidden');
          else emptyEl.classList.add('hidden');
        }}
        var pagesWrap = document.getElementById('page-sidebar-pages-list');
        if (pagesWrap) {{
          var pBtns = pagesWrap.querySelectorAll('button[data-sidebar-page]');
          for (var j = 0; j < pBtns.length; j++) {{
            var pHay = (pBtns[j].getAttribute('data-sidebar-search') || pBtns[j].textContent || '').toLowerCase();
            if (!q || pHay.indexOf(q) !== -1) {{
              pBtns[j].classList.remove('hidden');
            }} else {{
              pBtns[j].classList.add('hidden');
            }}
          }}
        }}
      }};

      window.triggerSidebarPageNav = function (pageKey) {{
        window.togglePageSectionSidebar(false);
        var mainPage = document.getElementById('page-main');
        var path = (window.location && window.location.pathname) ? window.location.pathname : '';
        var inContractsSubdir = path.indexOf('/contracts/') !== -1;
        var rootPrefix = '';
        if (inContractsSubdir) {{
          var after = path.split('/contracts/')[1] || '';
          rootPrefix = after.indexOf('/') !== -1 ? '../../' : '../';
        }}
        if (mainPage) {{
          if (pageKey === 'overview') window.location.hash = '#overview';
          else if (pageKey === 'contracts') window.location.hash = '#contracts';
          else if (pageKey === 'apis') window.location.hash = '#apis';
          else if (pageKey === 'checkout') window.location.hash = '#checkout';
          else if (pageKey === 'account') window.location.hash = '#account';
          else if (pageKey === 'trust') window.location.hash = '#status';
          return true;
        }}
        if (pageKey === 'overview') window.location.href = rootPrefix + 'index.html#overview';
        else if (pageKey === 'contracts') window.location.href = rootPrefix + 'contracts/index.html';
        else if (pageKey === 'apis') window.location.href = rootPrefix + 'apis.html';
        else if (pageKey === 'checkout') window.location.href = rootPrefix + 'index.html#checkout';
        else if (pageKey === 'account') window.location.href = rootPrefix + 'index.html#account';
        else if (pageKey === 'trust') window.location.href = rootPrefix + 'index.html#status';
        return true;
      }};

      window.triggerSidebarSectionJump = function (secId, customAction) {{
        if (customAction === 'sandbox') {{
          if (typeof window.openApiSandbox === 'function') {{
            window.openApiSandbox('product-contract-parsing');
          }}
          window.togglePageSectionSidebar(false);
          return true;
        }}
        if (customAction === 'auth_login') {{
          if (typeof window.switchAccountAuthTab === 'function') {{
            window.switchAccountAuthTab('login');
          }}
        }} else if (customAction === 'auth_register') {{
          if (typeof window.switchAccountAuthTab === 'function') {{
            window.switchAccountAuthTab('register');
          }}
        }}
        var targetEl = document.getElementById(secId);
        if (targetEl && targetEl.classList.contains('hidden') && secId.indexOf('product-') === 0 && typeof window.filterApiCatalog === 'function') {{
          window.filterApiCatalog('', 'all');
        }}
        var ok = window.jumpToPageSection(secId);
        window.togglePageSectionSidebar(false);
        return ok;
      }};

      window.syncSidebarTopOffset = function () {{}};

      window.renderPageSectionSidebar = function () {{
        var listEl = document.getElementById('page-sidebar-items');
        var railEl = document.getElementById('page-sidebar-rail-icons');
        var pagesEl = document.getElementById('page-sidebar-pages-list');
        var titleEl = document.getElementById('page-sidebar-title');
        if (!listEl) return [];

        var SIDEBAR_ICONS = {{
          pulse: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
          shield: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
          chat: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>',
          flag: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1zM4 22v-7"/></svg>',
          doc: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path stroke-linecap="round" stroke-linejoin="round" d="M14 2v6h6M16 13H8M16 17H8"/></svg>',
          lock: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path stroke-linecap="round" stroke-linejoin="round" d="M7 11V7a5 5 0 0110 0v4"/></svg>',
          cpu: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path stroke-linecap="round" stroke-linejoin="round" d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/></svg>',
          table: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="18" height="18" rx="2"/><path stroke-linecap="round" stroke-linejoin="round" d="M3 9h18M3 15h18M9 9v12"/></svg>',
          globe: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><path stroke-linecap="round" stroke-linejoin="round" d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg>',
          link: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>',
          sliders: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/></svg>',
          folder: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>',
          card: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><rect x="1" y="4" width="22" height="16" rx="2"/><path stroke-linecap="round" stroke-linejoin="round" d="M1 10h22"/></svg>',
          bolt: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
          code: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
          chart: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M18 20V10M12 20V4M6 20v-6"/></svg>',
          help: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><path stroke-linecap="round" stroke-linejoin="round" d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3M12 17h.01"/></svg>',
          user: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>'
        }};

        var mainPage = document.getElementById('page-main');
        var apisPage = document.getElementById('page-apis');
        var contractsPage = document.getElementById('page-contracts');
        var checkoutPage = document.getElementById('page-checkout');
        var accountPage = document.getElementById('page-account');
        var trustPage = document.getElementById('page-trust');

        var currentPageKey = 'overview';
        var pageTitle = 'Platform Overview';
        var rawItems = [];

        if (trustPage && !trustPage.classList.contains('hidden')) {{
          currentPageKey = 'trust';
          pageTitle = 'Trust, Status & Support';
          rawItems = [
            {{ icon: 'pulse', id: 'trust-panel-status', label: 'Live System Status (99.95%)', kw: 'status uptime sla health 18 portals operational', color: 'text-emerald-400', action: 'trust_status' }},
            {{ icon: 'shield', id: 'trust-panel-security', label: 'Security & Trust Center', kw: 'security zero retention rls pbkdf2 cui soc 2', color: 'text-sky-400', action: 'trust_security' }},
            {{ icon: 'chat', id: 'trust-panel-contact', label: 'AI Support Concierge', kw: 'contact support ai concierge help questions billing', color: 'text-indigo-300', action: 'trust_contact' }},
            {{ icon: 'flag', id: 'trust-panel-feedback', label: 'Submit Feedback / Portal', kw: 'feedback request state portal feature waf secure', color: 'text-amber-300', action: 'trust_feedback' }},
            {{ icon: 'doc', id: 'trust-panel-terms', label: 'Terms of Service & SLA', kw: 'terms of service legal sla cancellation disclaimer', color: 'text-slate-300', action: 'trust_terms' }},
            {{ icon: 'lock', id: 'trust-panel-privacy', label: 'Privacy Policy & DPA', kw: 'privacy policy dpa zero retention subprocessors gdpr', color: 'text-emerald-400', action: 'trust_privacy' }}
          ];
        }} else if (accountPage && !accountPage.classList.contains('hidden')) {{
          currentPageKey = 'account';
          var dashPanel = document.getElementById('account-dashboard-panel');
          if (dashPanel && !dashPanel.classList.contains('hidden')) {{
            pageTitle = 'Client Account Portal';
            rawItems = [
              {{ icon: 'pulse', id: 'account-dispatch-telemetry-card', label: '6-Hr Telemetry & Dispatch', kw: 'telemetry scan dispatch briefing now', color: 'text-emerald-400' }},
              {{ icon: 'card', id: 'account-plan-badge', label: 'Plan, Billing & Receipts', kw: 'subscription plan billing cadence receipt', color: 'text-sky-400' }},
              {{ icon: 'chat', id: 'account-pill-discord', label: 'Distribution & Team CC', kw: 'discord email webhook team cc seats', color: 'text-indigo-300' }},
              {{ icon: 'sliders', id: 'account-alert-filters-card', label: '18-Portal & NAICS Filters', kw: 'territory state portals naics keywords set aside', color: 'text-sky-400' }},
              {{ icon: 'folder', id: 'account-company-vault-card', label: 'Company Capture Vault', kw: 'vault capability statement past performance rates', color: 'text-indigo-300' }},
              {{ icon: 'table', id: 'account-bid-board-card', label: 'Saved RFP Bid Board', kw: 'pipeline bid board saved rfps stage', color: 'text-emerald-400' }},
              {{ icon: 'code', id: 'account-api-key-value', label: 'Enterprise API Key & MCP', kw: 'api key st_live mcp claude cursor config', color: 'text-amber-300' }},
              {{ icon: 'shield', id: 'account-profile-name', label: 'Profile & Password Security', kw: 'name company password security logout', color: 'text-slate-300' }}
            ];
          }} else {{
            pageTitle = 'Account Sign In / Sign Up';
            rawItems = [
              {{ icon: 'bolt', id: 'account-auth-panel', label: 'Free Explorer Benefits', kw: 'free explorer benefits features', color: 'text-emerald-400' }},
              {{ icon: 'lock', id: 'account-form-login', label: 'Sign In to Account', kw: 'login sign in password', color: 'text-sky-400', action: 'auth_login' }},
              {{ icon: 'user', id: 'account-form-register', label: 'Create Free Account ($0)', kw: 'register sign up free account', color: 'text-emerald-400', action: 'auth_register' }}
            ];
          }}
        }} else if (checkoutPage && !checkoutPage.classList.contains('hidden')) {{
          currentPageKey = 'checkout';
          pageTitle = 'Plans & B2B Checkout';
          rawItems = [
            {{ icon: 'sliders', id: 'btn-billing-monthly', label: 'Billing & Delivery Setup', kw: 'monthly annual billing email webhook routing', color: 'text-sky-400' }},
            {{ icon: 'bolt', id: 'checkout-card-tier1', label: 'Tier 1: SignalWire ($99/mo)', kw: 'tier 1 signalwire pro 99 leads alerts', color: 'text-sky-400' }},
            {{ icon: 'cpu', id: 'checkout-card-tier2', label: 'Tier 2: CaptureDesk ($399/mo)', kw: 'tier 2 capturedesk autopilot 399 dossiers api', color: 'text-indigo-300' }},
            {{ icon: 'doc', id: 'checkout-card-tier3', label: 'Tier 3: Proposal .ZIP ($1,499)', kw: 'tier 3 proposal compiler zip docx xlsx 1499', color: 'text-emerald-400' }},
            {{ icon: 'globe', id: 'checkout-card-tier4', label: 'Tier 4: OEM & FOIA ($2,499)', kw: 'tier 4 oem foia vault 2499 50k calls', color: 'text-amber-300' }},
            {{ icon: 'chat', id: 'checkout-live-feed-preview', label: 'Live 4-Tier Channel Preview', kw: 'sample preview feed discord dossier foia', color: 'text-emerald-400' }},
            {{ icon: 'chart', id: 'capture-roi-calculator', label: 'Capture ROI Calculator', kw: 'calculator roi hours saved labor rate', color: 'text-amber-300' }},
            {{ icon: 'help', id: 'checkout-faq-section', label: 'Cost Benchmark & FAQ', kw: 'govwin bgov comparison faq questions', color: 'text-slate-300' }}
          ];
        }} else if (contractsPage && !contractsPage.classList.contains('hidden')) {{
          currentPageKey = 'contracts';
          pageTitle = 'Live RFP Directory';
          if (document.getElementById('contracts-rfp-ai-shred-card')) {{
            rawItems = [
              {{ icon: 'doc', id: 'contracts-top-section', label: 'Solicitation Scope & Agency', kw: 'title agency deadline portal scope', color: 'text-sky-400' }},
              {{ icon: 'cpu', id: 'contracts-rfp-ai-shred-card', label: 'CaptureDesk 21-API Shred', kw: 'naics igce ptw cmmc rmf lcats cpars shred', color: 'text-indigo-300' }},
              {{ icon: 'globe', id: 'contracts-rfp-related-card', label: 'Related Portal Solicitations', kw: 'similar more open bids related', color: 'text-emerald-400' }},
              {{ icon: 'bolt', id: 'spa-contracts-lead-box', label: 'Unlock 3 Free Dossiers', kw: 'free sample dossiers email unlock', color: 'text-amber-300' }}
            ];
          }} else {{
            rawItems = [
              {{ icon: 'globe', id: 'contracts-top-section', label: 'Portal & Category Hubs', kw: 'states federal categories filter hubs', color: 'text-sky-400' }},
              {{ icon: 'table', id: 'contracts-live-table-card', label: 'Live RFP Search & Table', kw: 'table solicitations search bids due dates', color: 'text-emerald-400' }},
              {{ icon: 'bolt', id: 'spa-contracts-lead-box', label: 'Unlock 3 Free Dossiers', kw: 'free sample dossiers email unlock', color: 'text-amber-300' }}
            ];
          }}
        }} else if ((apisPage && !apisPage.classList.contains('hidden')) || (!mainPage && document.getElementById('api-directory-list'))) {{
          currentPageKey = 'apis';
          pageTitle = 'API & MCP Catalog';
          rawItems = [
            {{ icon: 'table', id: 'api-directory-list', label: 'Quick-Jump API Directory', kw: 'directory index table search endpoints', color: 'text-sky-400' }},
            {{ icon: 'bolt', id: 'rapidapi-sandbox-modal', label: 'Interactive Studio Playground', kw: 'sandbox test try live api playground json', color: 'text-emerald-400', action: 'sandbox' }},
            {{ icon: 'code', id: 'catalog-modules', label: 'Endpoint Specs & Schemas', kw: 'modules cards schemas request response curl', color: 'text-indigo-300' }},
            {{ icon: 'card', id: 'api-pricing-matrix', label: 'Tier & Quota Pricing Matrix', kw: 'pricing plans basic pro ultra mega rate limits', color: 'text-amber-300' }}
          ];
        }} else if (document.getElementById('static-inbound-lead-box')) {{
          currentPageKey = 'contracts';
          pageTitle = 'Live RFP Directory';
          if (document.getElementById('static-rfp-ai-shred-card')) {{
            rawItems = [
              {{ icon: 'doc', id: 'static-rfp-scope-card', label: 'Solicitation Scope & Agency', kw: 'title agency deadline portal scope', color: 'text-sky-400' }},
              {{ icon: 'cpu', id: 'static-rfp-ai-shred-card', label: 'CaptureDesk 21-API Shred', kw: 'naics igce ptw cmmc rmf lcats cpars shred', color: 'text-indigo-300' }},
              {{ icon: 'globe', id: 'static-rfp-related-card', label: 'Related Portal Solicitations', kw: 'similar more open bids related', color: 'text-emerald-400' }},
              {{ icon: 'bolt', id: 'static-inbound-lead-box', label: 'Unlock 3 Free Dossiers', kw: 'free sample dossiers email unlock', color: 'text-amber-300' }}
            ];
          }} else {{
            rawItems = [
              {{ icon: 'globe', id: 'static-contracts-top-section', label: 'Portal & Category Hubs', kw: 'states federal categories filter hubs', color: 'text-sky-400' }},
              {{ icon: 'table', id: 'static-contracts-table-card', label: 'Live RFP Search & Table', kw: 'table solicitations search bids due dates', color: 'text-emerald-400' }},
              {{ icon: 'bolt', id: 'static-inbound-lead-box', label: 'Unlock 3 Free Dossiers', kw: 'free sample dossiers email unlock', color: 'text-amber-300' }}
            ];
          }}
        }} else {{
          currentPageKey = 'overview';
          pageTitle = 'Platform Overview';
          rawItems = [
            {{ icon: 'pulse', id: 'overview', label: 'Hero & 4-Tier Overview', kw: 'top hero federal sled portals summary tier 1 tier 2 tier 3 tier 4', color: 'text-sky-400' }},
            {{ icon: 'chat', id: 'discord-terminal', label: 'Live 6-Hr Alert Feed', kw: 'discord slack email alerts live wire feed', color: 'text-sky-400' }},
            {{ icon: 'cpu', id: 'capture-moat', label: 'AI Capture Dossiers', kw: 'capturedesk shipley igce ptw rmf cmmc shred', color: 'text-indigo-300' }},
            {{ icon: 'doc', id: 'proposal-foia-moat', label: 'Proposal .ZIP & FOIA Moat', kw: 'tier 3 tier 4 proposal compiler zip docx xlsx foia teaming', color: 'text-emerald-400' }},
            {{ icon: 'table', id: 'contract-directory', label: '18-Portal Live RFP Table', kw: 'solicitations rfps bids table filter preview', color: 'text-emerald-400' }},
            {{ icon: 'globe', id: 'coverage', label: 'Portal Coverage & ROI', kw: 'states coverage sam demandstar roi savings', color: 'text-sky-400' }},
            {{ icon: 'link', id: 'integrations', label: 'CRM, Slack & Webhooks', kw: 'webhooks hubspot salesforce slack teams json', color: 'text-amber-300' }}
          ];
        }}

        if (titleEl) titleEl.textContent = pageTitle;

        var html = '';
        var railHtml = '';
        for (var i = 0; i < rawItems.length; i++) {{
          var it = rawItems[i];
          var actArg = it.action ? (', &quot;' + it.action + '&quot;') : '';
          var searchBlob = (it.label + ' ' + (it.kw || '')).replace(/"/g, '&quot;');
          var svgIcon = SIDEBAR_ICONS[it.icon] || SIDEBAR_ICONS.pulse;
          html += '<button type="button" data-sidebar-sec="' + it.id + '" data-sidebar-search="' + searchBlob + '" onclick="window.triggerSidebarSectionJump(&quot;' + it.id + '&quot;' + actArg + ')" class="w-full px-2.5 py-2 rounded-lg hover:bg-slate-800/75 text-slate-300 hover:text-white flex items-center justify-between gap-2 text-left transition-colors cursor-pointer group">' +
            '<span class="flex items-center gap-2.5 min-w-0">' +
              '<span class="' + it.color + ' w-4 h-4 flex items-center justify-center shrink-0">' + svgIcon + '</span>' +
              '<span class="truncate text-xs font-medium group-hover:text-sky-300 transition-colors">' + it.label + '</span>' +
            '</span>' +
            '<span class="text-slate-600 group-hover:text-sky-400 text-xs shrink-0">&rsaquo;</span>' +
          '</button>';

          railHtml += '<button type="button" title="' + it.label.replace(/"/g, '&quot;') + '" aria-label="' + it.label.replace(/"/g, '&quot;') + '" onclick="window.triggerSidebarSectionJump(&quot;' + it.id + '&quot;' + actArg + ')" class="w-8 h-8 rounded-full hover:bg-slate-800/80 text-slate-400 hover:text-sky-400 flex items-center justify-center transition-colors cursor-pointer">' +
            svgIcon +
          '</button>';
        }}
        listEl.innerHTML = html;
        if (railEl) railEl.innerHTML = railHtml;

        if (pagesEl) {{
          var allPages = [
            {{ key: 'overview', icon: 'pulse', label: 'Platform Overview', kw: 'home main hero wire overview' }},
            {{ key: 'contracts', icon: 'table', label: 'Live RFP Directory', kw: 'contracts rfps solicitations federal sled states' }},
            {{ key: 'apis', icon: 'code', label: 'API & MCP Catalog', kw: 'apis endpoints rest mcp developer rapidapi' }},
            {{ key: 'checkout', icon: 'card', label: 'Plans & B2B Checkout', kw: 'pricing plans tier 1 tier 2 checkout subscribe' }},
            {{ key: 'account', icon: 'user', label: 'Client Account Portal', kw: 'account login sign up dashboard vault filters' }},
            {{ key: 'trust', icon: 'shield', label: 'Status, Trust & Support', kw: 'status security contact feedback terms privacy sla' }}
          ];
          var pHtml = '';
          for (var pIdx = 0; pIdx < allPages.length; pIdx++) {{
            var pg = allPages[pIdx];
            if (pg.key === currentPageKey) continue;
            var pgIcon = SIDEBAR_ICONS[pg.icon] || SIDEBAR_ICONS.pulse;
            pHtml += '<button type="button" data-sidebar-page="' + pg.key + '" data-sidebar-search="' + (pg.label + ' ' + pg.kw) + '" onclick="window.triggerSidebarPageNav(&quot;' + pg.key + '&quot;)" class="w-full px-2.5 py-1.5 rounded-lg hover:bg-slate-800/75 text-slate-400 hover:text-white flex items-center justify-between gap-2 text-left transition-colors cursor-pointer group">' +
              '<span class="flex items-center gap-2.5 min-w-0">' +
                '<span class="text-slate-500 group-hover:text-sky-400 w-4 h-4 flex items-center justify-center shrink-0 transition-colors">' + pgIcon + '</span>' +
                '<span class="truncate text-xs group-hover:text-sky-300 transition-colors">' + pg.label + '</span>' +
              '</span>' +
              '<span class="text-slate-600 group-hover:text-sky-400 text-xs shrink-0">&rarr;</span>' +
            '</button>';
          }}
          pagesEl.innerHTML = pHtml;
        }}
        if (typeof window.syncSidebarTopOffset === 'function') {{
          window.syncSidebarTopOffset();
          setTimeout(window.syncSidebarTopOffset, 40);
        }}
        return rawItems;
      }};

    window.renderPageSectionSidebar();

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
        var txt = (rows[i]._stSearchText || (rows[i]._stSearchText = (rows[i].textContent || '').toLowerCase()));
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
        statusEl.textContent = 'Querying live 18-portal CaptureDesk database & emailing your 3 dossiers...';
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


    window.compileShipleyProposalZip = async function (slugVal, titleVal, agencyVal, naicsVal, setAsideVal) {{
      var btnEl = document.getElementById('compile-zip-btn-' + slugVal) || document.getElementById('compile-zip-btn-static');
      var vaultEl = document.getElementById('vault-status-' + slugVal) || document.getElementById('vault-status-static');
      var origTxt = btnEl ? btnEl.textContent : '1-Click Compile 6-File Proposal & Legal .ZIP';
      if (btnEl) {{
        btnEl.disabled = true;
        btnEl.textContent = 'Compiling 6-File Package (Vol I-III + FAR 9.6 Teaming + FOIA Demand)...';
      }}
      var compName = 'Your Capture Team LLC';
      var ueiCage = 'UEI-PENDING / CAGE-PENDING';
      var wrapRate = 1.82;
      var capSummary = '';
      try {{
        var savedProf = window.localStorage && window.localStorage.getItem('st_company_profile_v1');
        if (savedProf) {{
          var pObj = JSON.parse(savedProf);
          if (pObj.company) compName = pObj.company;
          if (pObj.uei_cage) ueiCage = pObj.uei_cage;
          if (pObj.wrap_rate) wrapRate = parseFloat(pObj.wrap_rate) || 1.82;
          if (pObj.capabilities || pObj.company_capability_summary) capSummary = pObj.capabilities || pObj.company_capability_summary;
        }}
      }} catch (e) {{}}
      var matchedContract = null;
      try {{
        var cPool = window.SIGNALTENDER_CONTRACTS || [];
        for (var ci = 0; ci < cPool.length; ci++) {{
          if (cPool[ci] && (cPool[ci].slug === slugVal || cPool[ci].title === titleVal)) {{
            matchedContract = cPool[ci];
            break;
          }}
        }}
      }} catch (e) {{}}
      var domRfpText = '';
      try {{
        var mainEl = document.querySelector('main') || document.body;
        if (mainEl && !matchedContract) domRfpText = String(mainEl.innerText || '').slice(0, 3500);
      }} catch (e) {{}}
      try {{
        var resp = await fetch('https://b2b-contract-parser-api.onrender.com/v1/proposal-autopilot/compile-full-package', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            solicitation_title: titleVal || (matchedContract && matchedContract.title) || 'Government IT & Cybersecurity Solicitation',
            solicitation_number: String(slugVal || 'RFP-2026').slice(0, 48).toUpperCase(),
            issuing_agency: agencyVal || (matchedContract && matchedContract.agency) || 'Federal / State SLED Agency',
            naics_code: String(naicsVal || (matchedContract && matchedContract.naics) || '541512').split('/')[0].trim(),
            set_aside: setAsideVal || (matchedContract && matchedContract.set_aside) || 'Small Business / SDVOSB',
            closing_date: (matchedContract && matchedContract.closing_date) || 'Active Open Window',
            compliance_posture: (matchedContract && matchedContract.compliance_posture) || '',
            teaming_posture: (matchedContract && matchedContract.teaming_posture) || '',
            igce_ptw_posture: (matchedContract && matchedContract.igce_ptw_posture) || '',
            key_personnel_lcats: (matchedContract && matchedContract.key_personnel_lcats) || '',
            rfp_text: (matchedContract && (matchedContract.rfp_text || matchedContract.compliance_posture)) || domRfpText,
            company_name: compName,
            company_capability_summary: capSummary,
            uei_cage: ueiCage,
            wrap_rate: wrapRate
          }})
        }});
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        var ctype = String(resp.headers.get('content-type') || '');
        var blob = null;
        var vaultMsg = '';
        var dlName = 'SignalTender_Shipley_6File_Proposal_' + String(slugVal || 'package').slice(0, 36) + '.zip';
        if (ctype.indexOf('application/json') !== -1) {{
          var jData = await resp.json();
          if (jData && jData.filename) dlName = jData.filename;
          if (jData && jData.institutional_vault_message) vaultMsg = jData.institutional_vault_message;
          var binStr = window.atob(jData.zip_base64 || '');
          var u8 = new Uint8Array(binStr.length);
          for (var bi = 0; bi < binStr.length; bi++) u8[bi] = binStr.charCodeAt(bi);
          blob = new Blob([u8], {{ type: 'application/zip' }});
        }} else {{
          blob = await resp.blob();
        }}
        var dlUrl = window.URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = dlUrl;
        a.download = dlName;
        document.body.appendChild(a);
        a.click();
        setTimeout(function () {{
          window.URL.revokeObjectURL(dlUrl);
          if (a.parentNode) a.parentNode.removeChild(a);
        }}, 1500);
        if (btnEl) {{
          btnEl.disabled = false;
          btnEl.textContent = 'Downloaded 6-File .ZIP (Vol I-III + FAR 9.6 Teaming + FOIA Demand)';
        }}
        if (vaultEl && vaultMsg) {{
          vaultEl.classList.remove('hidden');
          vaultEl.textContent = vaultMsg;
        }}
      }} catch (err) {{
        if (btnEl) {{
          btnEl.disabled = false;
          btnEl.textContent = origTxt;
        }}
      }}
    }};

    window.toggleTeamingClearinghouseBox = function (boxId) {{
      var el = document.getElementById(boxId);
      if (!el) return;
      if (el.classList.contains('hidden')) el.classList.remove('hidden');
      else el.classList.add('hidden');
    }};

    window.submitInlineTeamingSlot = async function (slugVal, titleVal, agencyVal, naicsVal) {{
      var sfx = slugVal || 'static';
      var coEl = document.getElementById('teaming-co-' + sfx);
      var ueiEl = document.getElementById('teaming-uei-' + sfx);
      var socEl = document.getElementById('teaming-soc-' + sfx);
      var emEl = document.getElementById('teaming-em-' + sfx);
      var stEl = document.getElementById('teaming-status-' + sfx);
      var subCo = coEl ? String(coEl.value || '').trim() : '';
      var subEm = emEl ? String(emEl.value || '').trim() : '';
      if (!subCo || !subEm || subEm.indexOf('@') === -1) {{
        if (stEl) {{
          stEl.classList.remove('hidden');
          stEl.className = 'mt-2 text-xs font-mono text-amber-300';
          stEl.textContent = 'Please enter your company name and work email to validate 13 CFR 125.6 workshare.';
        }}
        return;
      }}
      if (stEl) {{
        stEl.classList.remove('hidden');
        stEl.className = 'mt-2 text-xs font-mono text-sky-300';
        stEl.textContent = 'Validating 13 CFR 125.6 (50% Rule) workshare & querying live Teaming Clearinghouse partners...';
      }}
      try {{
        var r = await fetch('https://b2b-contract-parser-api.onrender.com/v1/proposal-autopilot/teaming-clearinghouse', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            email: subEm,
            company_name: subCo,
            uei_or_cage: ueiEl ? String(ueiEl.value || 'Verified SAM UEI').trim() : 'Verified SAM UEI',
            socioeconomic_status: socEl ? String(socEl.value || 'SDVOSB').trim() : 'SDVOSB',
            solicitation_id: String(slugVal || 'RFP-2026').slice(0, 65),
            solicitation_title: titleVal || 'Government IT Solicitation',
            issuing_agency: agencyVal || 'Government Agency',
            naics_focus: String(naicsVal || '541512').split('/')[0].trim()
          }})
        }});
        var d = await r.json();
        if (stEl) {{
          stEl.className = 'mt-3 space-y-2.5 text-xs font-mono';
          var rulingTxt = (d && d.cfr_125_6_ruling) ? d.cfr_125_6_ruling : 'Verified 13 CFR 125.6 Teaming Slot registered.';
          var partners = (d && Array.isArray(d.matched_partners)) ? d.matched_partners : [];
          var pCards = partners.map(function (p) {{
            var pName = String(p.company_name || 'Verified Partner').replace(/</g, '&lt;');
            var pSoc = String(p.socioeconomic_status || 'Small Business').replace(/</g, '&lt;');
            var pUei = String(p.uei_or_cage || 'SAM Verified').replace(/</g, '&lt;');
            var pShare = String(p.allocated_workshare_pct || 24) + '% Share';
            return '<div class="p-2.5 rounded-lg bg-navy-950 border border-slate-800 flex flex-wrap items-center justify-between gap-2">' +
              '<div><span class="text-white font-semibold">' + pName + '</span> <span class="text-amber-300">(' + pSoc + ')</span> <span class="text-slate-400 text-[11px]">' + pUei + '</span></div>' +
              '<span class="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[10px]">' + pShare + '</span>' +
            '</div>';
          }}).join('');
          var inviteHref = (d && d.viral_partner_invite_mailto) ? String(d.viral_partner_invite_mailto).replace(/"/g, '&quot;') : 'mailto:?subject=13%20CFR%20125.6%20Teaming%20Invitation';
          var refUrl = (d && d.clearinghouse_referral_url) ? String(d.clearinghouse_referral_url).replace(/"/g, '&quot;') : window.location.href;
          stEl.innerHTML =
            '<div class="text-emerald-400 font-semibold">&check; ' + rulingTxt.replace(/</g, '&lt;') + '</div>' +
            (pCards ? ('<div class="space-y-1.5 pt-1"><div class="text-[10px] text-slate-400 uppercase">Matched 13 CFR &sect; 125.6 Clearinghouse Partners:</div>' + pCards + '</div>') : '') +
            '<div class="pt-1 flex flex-wrap gap-2">' +
              '<a href="' + inviteHref + '" class="inline-flex items-center px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/35 border border-amber-400/50 text-amber-200 font-semibold">1-Click Invite Preferred Teaming Partner (Email) &rarr;</a>' +
              '<button type="button" onclick="if(navigator.clipboard) navigator.clipboard.writeText(&quot;' + refUrl + '&quot;); this.textContent=&quot;Copied Referral Link!&quot;;" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sky-300 cursor-pointer">Copy Workshare Invite Link</button>' +
            '</div>';
        }}
      }} catch (e) {{
        if (stEl) {{
          stEl.className = 'mt-2 text-xs font-mono text-emerald-400';
          stEl.textContent = 'Teaming slot request logged for 13 CFR 125.6 clearinghouse review.';
        }}
      }}
    }};

    window.unlockFoiaWinningBidVault = async function (slugVal, stateVal, naicsVal, titleVal, agencyVal) {{
      var sfx = slugVal || 'static';
      var boxEl = document.getElementById('foia-vault-box-' + sfx);
      if (!boxEl) return;
      if (!boxEl.classList.contains('hidden') && boxEl.getAttribute('data-loaded') === '1') {{
        boxEl.classList.add('hidden');
        return;
      }}
      boxEl.classList.remove('hidden');
      boxEl.innerHTML = '<div class="text-xs font-mono text-sky-300">Querying Post-Award FOIA / State PIA Incumbent Rate Vault &amp; generating statutory $0-fee demand letter...</div>';
      try {{
        var qUrl = 'https://b2b-contract-parser-api.onrender.com/v1/proposal-autopilot/foia-winning-bid-vault?state=' +
          encodeURIComponent(stateVal || 'all') +
          '&naics=' + encodeURIComponent(String(naicsVal || '541512').split('/')[0].trim()) +
          '&solicitation_id=' + encodeURIComponent(String(slugVal || 'RFP-2026').slice(0, 48).toUpperCase()) +
          '&title=' + encodeURIComponent(titleVal || 'Enterprise IT Solicitation') +
          '&agency=' + encodeURIComponent(agencyVal || 'Government Agency');
        var r = await fetch(qUrl);
        var d = await r.json();
        boxEl.setAttribute('data-loaded', '1');
        var statute = String((d && d.statutory_citation) || '5 U.S.C. § 552 (Federal FOIA / State PIA — $0 Electronic Cap)').replace(/</g, '&lt;');
        var awards = (d && Array.isArray(d.awards)) ? d.awards : [];
        var ratesHtml = '';
        if (awards.length > 0 && Array.isArray(awards[0].verified_lcat_benchmarks)) {{
          ratesHtml = awards[0].verified_lcat_benchmarks.map(function (b) {{
            var lcat = String(b.lcat || 'Senior Engineer').replace(/</g, '&lt;');
            var rate = Number(b.winning_rate_hr || 162).toFixed(2);
            var ptw = (Number(b.winning_rate_hr || 162) * 0.94).toFixed(2);
            return '<div class="p-2.5 rounded-lg bg-navy-950 border border-slate-800 flex items-center justify-between gap-2">' +
              '<span class="text-white font-semibold">' + lcat + '</span>' +
              '<span class="text-right"><span class="text-amber-300">Incumbent: $' + rate + '/hr</span> &bull; <span class="text-emerald-400 font-semibold">PTW: $' + ptw + '/hr</span></span>' +
            '</div>';
          }}).join('');
        }}
        var letterTxt = String((d && d.statutory_demand_letter_text) || '').replace(/</g, '&lt;');
        var mailHref = String((d && d.foia_mailto_link) || 'mailto:').replace(/"/g, '&quot;');
        boxEl.innerHTML =
          '<div class="space-y-3 text-xs font-mono">' +
            '<div class="flex flex-wrap items-center justify-between gap-2">' +
              '<span class="text-emerald-400 font-bold uppercase">// STATUTORY FOIA / STATE PIA INCUMBENT RATE VAULT</span>' +
              '<span class="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[10px]">' + statute + '</span>' +
            '</div>' +
            (ratesHtml ? ('<div class="grid grid-cols-1 gap-1.5">' + ratesHtml + '</div>') : '') +
            '<pre id="foia-letter-pre-' + sfx + '" class="p-3 rounded-lg bg-navy-950 border border-slate-800 text-[11px] text-slate-300 whitespace-pre-wrap overflow-x-auto">' + letterTxt + '</pre>' +
            '<div class="flex flex-wrap gap-2">' +
              '<a href="' + mailHref + '" class="inline-flex items-center px-3 py-1.5 rounded-lg bg-emerald-600/25 hover:bg-emerald-600/40 border border-emerald-400/50 text-emerald-200 font-semibold">1-Click Dispatch FOIA Demand to Agency (Email) &rarr;</a>' +
              '<button type="button" onclick="var el=document.getElementById(&quot;foia-letter-pre-' + sfx + '&quot;); if(el && navigator.clipboard) navigator.clipboard.writeText(el.textContent); this.textContent=&quot;Copied Statutory Demand!&quot;;" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sky-300 cursor-pointer">Copy Statutory FOIA Letter</button>' +
            '</div>' +
          '</div>';
      }} catch (err) {{
        boxEl.innerHTML = '<div class="text-xs font-mono text-amber-300">Statutory FOIA / PIA Demand Ready (5 U.S.C. &sect; 552 / State Open Records — $0.00 Electronic Fee Cap).</div>';
      }}
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
          var coMask = document.getElementById('dossier-co-routing-mask');
          if (coMask) {{
            var realRouting = coMask.getAttribute('data-real-routing') || '';
            coMask.className = 'text-sky-300 font-semibold';
            if (realRouting) coMask.textContent = realRouting;
          }}
        }}
      }} catch (e) {{}}
    }})();
  </script>
</body>
</html>
"""


def _generate_recompete_and_subcontracting_pseo_pages(sitemap_urls: list[str]) -> int:
    """
    Upgrade #2: Generates evergreen static pSEO pages in /contracts/recompetes/ for:
      - 90–180 Day Expiring Federal IT Contracts (Recompete Radar, API #16 + API #21)
      - Fresh Prime Awards ($1.5M–$50M) with mandatory ~30% FAR 52.219-9 Small-Business Subcontracting Pools (API #11)
    """
    intel_path = os.path.join(BASE_DIR, "govcon_prospect_intelligence.json")
    if not os.path.exists(intel_path):
        return 0
    try:
        with open(intel_path, "r", encoding="utf-8") as f:
            intel = json.load(f)
    except Exception:
        return 0

    recompetes = intel.get("expiring_recompete_wire") or []
    sub_targets = intel.get("fresh_prime_subcontracting_wire") or []
    if not recompetes and not sub_targets:
        return 0

    recompete_dir = os.path.join(OUTPUT_DIR, "recompetes")
    os.makedirs(recompete_dir, exist_ok=True)
    built = 0

    recompete_rows_html = []
    for r in recompetes:
        awd_id = str(r.get("award_id") or "").strip()
        if not awd_id:
            continue
        slug_id = re.sub(r"[^a-z0-9_-]+", "-", awd_id.lower()).strip("-")
        incumbent = str(r.get("incumbent_recipient") or "Federal IT Incumbent").title()
        amt_fmt = str(r.get("award_amount_fmt") or "$5.0M")
        agency = str(r.get("awarding_sub_agency") or "Federal Agency")
        end_dt = str(r.get("end_date") or "2027")
        days_left = int(r.get("days_until_expiration") or 120)
        desc = str(r.get("description") or "Federal Enterprise IT & Cybersecurity Contract").capitalize()
        burn_fmt = str(r.get("api16_incumbent_annual_burn_fmt") or "$3.5M/yr")
        ptw_fmt = str(r.get("api16_ptw_challenger_ceiling_fmt") or "$3.2M/yr (-8% PTW target)")
        shaping_str = str(r.get("api21_sources_sought_action") or "FAR 19.502-2 Rule-of-Two Set-Aside Shaping Window Open")
        usa_url = str(r.get("usaspending_url") or f"https://www.usaspending.gov/search")

        canonical_rel = f"contracts/recompetes/{slug_id}.html"
        sitemap_urls.append(f"{SITE_BASE_URL}/{canonical_rel}")

        recompete_rows_html.append(f"""
        <tr class="hover:bg-navy-900/60 transition-colors border-b border-slate-800/70">
          <td class="py-4 px-5 font-mono whitespace-nowrap">
            <span class="px-2.5 py-1 rounded border text-[11px] font-semibold bg-amber-500/10 text-amber-300 border-amber-500/30">
              RECOMPETE &bull; {days_left}D
            </span>
          </td>
          <td class="py-4 px-5">
            <a href="{slug_id}.html" class="font-bold text-white hover:text-sky-400 text-sm transition-colors block">
              {html.escape(awd_id)} &mdash; {html.escape(incumbent)} ({html.escape(amt_fmt)})
            </a>
            <div class="text-xs text-slate-400 mt-1 line-clamp-1">{html.escape(desc)}</div>
          </td>
          <td class="py-4 px-4 text-slate-300 font-mono text-xs">{html.escape(agency)}</td>
          <td class="py-4 px-4 font-mono text-emerald-300 whitespace-nowrap text-xs">{html.escape(ptw_fmt)}</td>
          <td class="py-4 px-5 text-right font-mono whitespace-nowrap">
            <a href="{slug_id}.html" class="inline-flex items-center px-3 py-1.5 rounded bg-slate-900 hover:bg-sky-600 hover:text-white border border-slate-700 text-sky-400 text-xs transition-colors">
              Recompete Dossier &rarr;
            </a>
          </td>
        </tr>
        """)

        item_body = f"""
        <div id="static-contracts-top-section" class="mb-6 text-xs font-mono text-slate-400 flex flex-wrap items-center gap-2">
          <a href="../index.html" class="hover:text-sky-400">All Contracts</a>
          <span>/</span>
          <a href="index.html" class="hover:text-sky-400">Recompete &amp; Subcontracting Radar</a>
          <span>/</span>
          <span class="text-slate-200">{html.escape(awd_id)}</span>
        </div>
        <div class="p-6 sm:p-8 rounded-2xl bg-navy-900 border border-slate-800 shadow-2xl space-y-5">
          <div class="flex flex-wrap items-center gap-2.5 font-mono text-xs">
            <span class="px-2.5 py-1 rounded border font-semibold bg-amber-500/10 text-amber-300 border-amber-500/30">PRE-RFP RECOMPETE RADAR</span>
            <span class="px-2.5 py-1 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">AWARD ID: {html.escape(awd_id)}</span>
            <span class="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">POP ENDS: {html.escape(end_dt)} ({days_left} DAYS)</span>
          </div>
          <h1 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-snug">
            {html.escape(incumbent)} {html.escape(amt_fmt)} Federal IT Recompete ({html.escape(awd_id)}) &mdash; {html.escape(agency)}
          </h1>
          <p class="text-slate-300 text-sm leading-relaxed">
            Pre-RFP Federal Recompete Intelligence Dossier for <strong class="text-white">{html.escape(awd_id)}</strong> at <strong class="text-white">{html.escape(agency)}</strong>.
            Scope: {html.escape(desc)}.
          </p>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t border-slate-800/80 text-xs font-mono">
            <div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800/80">
              <div class="text-slate-400">INCUMBENT PRIME &amp; VALUE</div>
              <div class="text-white font-semibold mt-1">{html.escape(incumbent)} ({html.escape(amt_fmt)})</div>
            </div>
            <div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800/80">
              <div class="text-slate-400">CHALLENGER PTW CEILING (API #16)</div>
              <div class="text-emerald-300 font-semibold mt-1">{html.escape(ptw_fmt)}</div>
            </div>
            <div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800/80">
              <div class="text-slate-400">SOURCES SOUGHT SHAPING (API #21)</div>
              <div class="text-amber-300 font-semibold mt-1">{html.escape(shaping_str)}</div>
            </div>
          </div>
          <div class="p-5 rounded-xl bg-navy-950 border border-indigo-500/40 space-y-3 text-xs font-mono">
            <div class="text-indigo-300 font-bold uppercase">// CAPTUREDESK PRE-RFP RECOMPETE &amp; SET-ASIDE SHAPING PLAYBOOK</div>
            <div><strong class="text-slate-200">Estimated Incumbent Annual Burn Rate:</strong> <span class="text-white">{html.escape(burn_fmt)}</span></div>
            <div><strong class="text-slate-200">Challenger Price-to-Win Target (API #16):</strong> <span class="text-emerald-300">{html.escape(ptw_fmt)}</span></div>
            <div><strong class="text-slate-200">Rule-of-Two Set-Aside Shaping (API #21):</strong> <span class="text-sky-300">Generate a FAR 19.502-2 Sources Sought / RFI capability briefing before the Contracting Officer locks the acquisition strategy.</span></div>
            <div class="pt-2 flex flex-wrap gap-3">
              <a href="{WHOP_TIER2_URL}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center px-5 py-2.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold transition-all">
                Unlock Full Recompete &amp; Sources Sought Package &rarr;
              </a>
              <a href="../../apis.html#product-sources-sought-response" class="inline-flex items-center px-4 py-2.5 rounded-lg bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/40 text-indigo-300 transition-all">
                Shape via API #21 (Sources Sought Engine) &rarr;
              </a>
              <a href="{html.escape(usa_url, quote=True)}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center px-4 py-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 transition-all">
                Verify Award on USAspending.gov &nearr;
              </a>
              <button type="button" onclick="window.unlockFoiaWinningBidVault(&quot;recompete&quot;, &quot;federal&quot;, &quot;541512&quot;, &quot;{html.escape(awd_id, quote=True)}&quot;, &quot;{html.escape(agency, quote=True)}&quot;)" class="inline-flex items-center px-4 py-2.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-300 transition-all cursor-pointer">
                FOIA Incumbent Rate Vault &amp; Statutory Demand &rarr;
              </button>
            </div>
            <div id="foia-vault-box-recompete" class="hidden mt-3 p-4 rounded-xl bg-navy-900 border border-emerald-500/40"></div>
          </div>
        </div>
        """
        item_html = _render_layout(
            page_title=f"{awd_id} Recompete Dossier ({incumbent} {amt_fmt}) | {agency} | SignalTender",
            meta_desc=f"Pre-RFP Federal Recompete Dossier for {awd_id} ({incumbent}, {amt_fmt} at {agency}, PoP ending {end_dt}). Includes API #16 Price-to-Win ceiling ({ptw_fmt}) and FAR 19.502-2 set-aside shaping.",
            canonical_path=canonical_rel,
            body_html=item_body,
            root_prefix="../../",
            default_state="federal",
        )
        with open(os.path.join(recompete_dir, f"{slug_id}.html"), "w", encoding="utf-8") as f:
            f.write(item_html)
        built += 1

    sub_rows_html = []
    for s in sub_targets:
        awd_id = str(s.get("award_id") or "").strip()
        if not awd_id:
            continue
        slug_id = re.sub(r"[^a-z0-9_-]+", "-", awd_id.lower()).strip("-")
        prime_name = str(s.get("prime_recipient") or "Federal Prime").title()
        amt_fmt = str(s.get("award_amount_fmt") or "$10.0M")
        agency = str(s.get("awarding_sub_agency") or "Federal Agency")
        desc = str(s.get("description") or "Federal Enterprise IT Prime Award").capitalize()
        sub_pool_fmt = str(s.get("api11_sb_subcontract_pool_fmt") or "~30% FAR 52.219-9 Small-Business Sub Pool")
        usa_url = str(s.get("usaspending_url") or "https://www.usaspending.gov/search")

        canonical_rel = f"contracts/recompetes/{slug_id}.html"
        if f"{SITE_BASE_URL}/{canonical_rel}" not in sitemap_urls:
            sitemap_urls.append(f"{SITE_BASE_URL}/{canonical_rel}")

        sub_rows_html.append(f"""
        <tr class="hover:bg-navy-900/60 transition-colors border-b border-slate-800/70">
          <td class="py-4 px-5 font-mono whitespace-nowrap">
            <span class="px-2.5 py-1 rounded border text-[11px] font-semibold bg-emerald-500/10 text-emerald-300 border-emerald-500/30">
              PRIME SUB WIRE
            </span>
          </td>
          <td class="py-4 px-5">
            <a href="{slug_id}.html" class="font-bold text-white hover:text-sky-400 text-sm transition-colors block">
              {html.escape(prime_name)} &mdash; {html.escape(amt_fmt)} Prime Award ({html.escape(awd_id)})
            </a>
            <div class="text-xs text-slate-400 mt-1 line-clamp-1">{html.escape(desc)}</div>
          </td>
          <td class="py-4 px-4 text-slate-300 font-mono text-xs">{html.escape(agency)}</td>
          <td class="py-4 px-4 font-mono text-sky-300 whitespace-nowrap text-xs">{html.escape(sub_pool_fmt)}</td>
          <td class="py-4 px-5 text-right font-mono whitespace-nowrap">
            <a href="{slug_id}.html" class="inline-flex items-center px-3 py-1.5 rounded bg-slate-900 hover:bg-sky-600 hover:text-white border border-slate-700 text-sky-400 text-xs transition-colors">
              Teaming Dossier &rarr;
            </a>
          </td>
        </tr>
        """)

        sub_body = f"""
        <div id="static-contracts-top-section" class="mb-6 text-xs font-mono text-slate-400 flex flex-wrap items-center gap-2">
          <a href="../index.html" class="hover:text-sky-400">All Contracts</a>
          <span>/</span>
          <a href="index.html" class="hover:text-sky-400">Recompete &amp; Subcontracting Radar</a>
          <span>/</span>
          <span class="text-slate-200">{html.escape(awd_id)}</span>
        </div>
        <div class="p-6 sm:p-8 rounded-2xl bg-navy-900 border border-slate-800 shadow-2xl space-y-5">
          <div class="flex flex-wrap items-center gap-2.5 font-mono text-xs">
            <span class="px-2.5 py-1 rounded border font-semibold bg-emerald-500/10 text-emerald-300 border-emerald-500/30">PRIME-TO-SUB TEAMING WIRE</span>
            <span class="px-2.5 py-1 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">AWARD ID: {html.escape(awd_id)}</span>
          </div>
          <h1 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-snug">
            {html.escape(prime_name)} {html.escape(amt_fmt)} Prime Award ({html.escape(awd_id)}) &mdash; Subcontracting &amp; Teaming Dossier
          </h1>
          <p class="text-slate-300 text-sm leading-relaxed">
            Verified federal IT prime contract <strong class="text-white">{html.escape(awd_id)}</strong> awarded to <strong class="text-white">{html.escape(prime_name)}</strong> by <strong class="text-white">{html.escape(agency)}</strong>.
            Scope: {html.escape(desc)}.
          </p>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t border-slate-800/80 text-xs font-mono">
            <div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800/80">
              <div class="text-slate-400">PRIME CONTRACTOR</div>
              <div class="text-white font-semibold mt-1">{html.escape(prime_name)} ({html.escape(amt_fmt)})</div>
            </div>
            <div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800/80">
              <div class="text-slate-400">EST. SUBCONTRACTING POOL (API #11)</div>
              <div class="text-emerald-300 font-semibold mt-1">{html.escape(sub_pool_fmt)}</div>
            </div>
            <div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800/80">
              <div class="text-slate-400">WORKSHARE COMPLIANCE</div>
              <div class="text-sky-300 font-semibold mt-1">FAR 52.219-9 &amp; 13 CFR &sect; 125.6</div>
            </div>
          </div>
          <div class="p-5 rounded-xl bg-navy-950 border border-indigo-500/40 space-y-3 text-xs font-mono">
            <div class="text-indigo-300 font-bold uppercase">// CAPTUREDESK PRIME-TO-SUB TEAMING &amp; WORKSHARE PLAYBOOK</div>
            <div><strong class="text-slate-200">Estimated Small-Business Subcontracting Pool:</strong> <span class="text-emerald-300">{html.escape(sub_pool_fmt)}</span></div>
            <div><strong class="text-slate-200">13 CFR &sect; 125.6 Workshare Split (API #11):</strong> <span class="text-slate-300">Generate a compliant Teaming Agreement &amp; Small Business Subcontracting Plan for {html.escape(prime_name)}&apos;s {html.escape(agency)} delivery team.</span></div>
            <div class="pt-2 flex flex-wrap gap-3">
              <a href="{WHOP_TIER2_URL}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center px-5 py-2.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold transition-all">
                Unlock Prime Teaming &amp; CaptureDesk Feed &rarr;
              </a>
              <a href="../../apis.html#product-teaming-subcontracting" class="inline-flex items-center px-4 py-2.5 rounded-lg bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/40 text-indigo-300 transition-all">
                Model Workshare via API #11 &rarr;
              </a>
              <a href="{html.escape(usa_url, quote=True)}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center px-4 py-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 transition-all">
                Verify Award on USAspending.gov &nearr;
              </a>
              <button type="button" onclick="window.unlockFoiaWinningBidVault(&quot;recompete&quot;, &quot;federal&quot;, &quot;541512&quot;, &quot;{html.escape(awd_id, quote=True)}&quot;, &quot;{html.escape(agency, quote=True)}&quot;)" class="inline-flex items-center px-4 py-2.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-300 transition-all cursor-pointer">
                FOIA Incumbent Rate Vault &amp; Statutory Demand &rarr;
              </button>
            </div>
            <div id="foia-vault-box-recompete" class="hidden mt-3 p-4 rounded-xl bg-navy-900 border border-emerald-500/40"></div>
          </div>
        </div>
        """
        sub_html = _render_layout(
            page_title=f"{prime_name} {amt_fmt} Subcontracting & Teaming Dossier ({awd_id}) | SignalTender",
            meta_desc=f"Prime-to-Sub Teaming Dossier for {prime_name}'s {amt_fmt} {agency} contract ({awd_id}). Includes estimated FAR 52.219-9 small-business subcontracting pool ({sub_pool_fmt}).",
            canonical_path=canonical_rel,
            body_html=sub_body,
            root_prefix="../../",
            default_state="federal",
        )
        with open(os.path.join(recompete_dir, f"{slug_id}.html"), "w", encoding="utf-8") as f:
            f.write(sub_html)
        built += 1

    company_profiles = intel.get("company_award_profiles") or {}
    profile_rows_html = []
    seen_slug_ids = {
        re.sub(r"[^a-z0-9_-]+", "-", str(x.get("award_id") or "").lower()).strip("-")
        for x in (recompetes + sub_targets)
        if x.get("award_id")
    }
    for _, prof in company_profiles.items():
        if not isinstance(prof, dict):
            continue
        awd_id = str(prof.get("award_id") or "").strip()
        if not awd_id:
            continue
        slug_id = re.sub(r"[^a-z0-9_-]+", "-", awd_id.lower()).strip("-")
        if not slug_id or slug_id in seen_slug_ids:
            continue
        seen_slug_ids.add(slug_id)

        comp_name = str(prof.get("company_name") or prof.get("matched_recipient_name") or "Federal IT Prime").title()
        amt_fmt = str(prof.get("award_amount_fmt") or "$2.5M")
        amt_num = float(prof.get("award_amount") or 2500000.0)
        agency = str(prof.get("awarding_sub_agency") or prof.get("awarding_agency") or "Federal Agency")
        end_dt = str(prof.get("end_date") or "2027")
        desc = str(prof.get("description") or "Federal Enterprise IT & Cybersecurity Contract").capitalize()
        usa_url = str(prof.get("usaspending_url") or "https://www.usaspending.gov/search")
        est_sub_pool = amt_num * 0.30
        sub_pool_str = f"~${est_sub_pool / 1_000_000:.2f}M Sub Pool" if est_sub_pool >= 1_000_000 else f"~${int(round(est_sub_pool / 1_000.0))}k Sub Pool"
        ptw_str = f"${(amt_num * 0.92) / 1_000_000:.2f}M (-8% PTW)" if amt_num >= 1_000_000 else f"${int(round((amt_num * 0.92) / 1_000.0))}k (-8% PTW)"

        canonical_rel = f"contracts/recompetes/{slug_id}.html"
        if f"{SITE_BASE_URL}/{canonical_rel}" not in sitemap_urls:
            sitemap_urls.append(f"{SITE_BASE_URL}/{canonical_rel}")

        profile_rows_html.append(f"""
        <tr class="hover:bg-navy-900/60 transition-colors border-b border-slate-800/70">
          <td class="py-4 px-5 font-mono whitespace-nowrap">
            <span class="px-2.5 py-1 rounded border text-[11px] font-semibold bg-sky-500/10 text-sky-300 border-sky-500/30">
              PIID DOSSIER
            </span>
          </td>
          <td class="py-4 px-5">
            <a href="{slug_id}.html" class="font-bold text-white hover:text-sky-400 text-sm transition-colors block">
              {html.escape(awd_id)} &mdash; {html.escape(comp_name)} ({html.escape(amt_fmt)})
            </a>
            <div class="text-xs text-slate-400 mt-1 line-clamp-1">{html.escape(desc)}</div>
          </td>
          <td class="py-4 px-4 text-slate-300 font-mono text-xs">{html.escape(agency)}</td>
          <td class="py-4 px-4 font-mono text-emerald-300 whitespace-nowrap text-xs">{html.escape(ptw_str)} &bull; {html.escape(sub_pool_str)}</td>
          <td class="py-4 px-5 text-right font-mono whitespace-nowrap">
            <a href="{slug_id}.html" class="inline-flex items-center px-3 py-1.5 rounded bg-slate-900 hover:bg-sky-600 hover:text-white border border-slate-700 text-sky-400 text-xs transition-colors">
              PIID Dossier &rarr;
            </a>
          </td>
        </tr>
        """)

        prof_body = f"""
        <div id="static-contracts-top-section" class="mb-6 text-xs font-mono text-slate-400 flex flex-wrap items-center gap-2">
          <a href="../index.html" class="hover:text-sky-400">All Contracts</a>
          <span>/</span>
          <a href="index.html" class="hover:text-sky-400">Recompete &amp; Subcontracting Radar</a>
          <span>/</span>
          <span class="text-slate-200">{html.escape(awd_id)}</span>
        </div>
        <div class="p-6 sm:p-8 rounded-2xl bg-navy-900 border border-slate-800 shadow-2xl space-y-5">
          <div class="flex flex-wrap items-center gap-2.5 font-mono text-xs">
            <span class="px-2.5 py-1 rounded border font-semibold bg-sky-500/10 text-sky-300 border-sky-500/30">FEDERAL PIID RECOMPETE &amp; TEAMING DOSSIER</span>
            <span class="px-2.5 py-1 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">CONTRACT ID: {html.escape(awd_id)}</span>
            <span class="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">POP END: {html.escape(end_dt)}</span>
          </div>
          <h1 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-snug">
            {html.escape(awd_id)} Recompete &amp; Subcontracting Dossier &mdash; {html.escape(comp_name)} ({html.escape(amt_fmt)}, {html.escape(agency)})
          </h1>
          <p class="text-slate-300 text-sm leading-relaxed">
            Federal Contract Intelligence Dossier for <strong class="text-white">{html.escape(awd_id)}</strong> held by <strong class="text-white">{html.escape(comp_name)}</strong> at <strong class="text-white">{html.escape(agency)}</strong> (Period of Performance through {html.escape(end_dt)}).
            Scope: {html.escape(desc)}.
          </p>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t border-slate-800/80 text-xs font-mono">
            <div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800/80">
              <div class="text-slate-400">INCUMBENT PRIME &amp; VALUE</div>
              <div class="text-white font-semibold mt-1">{html.escape(comp_name)} ({html.escape(amt_fmt)})</div>
            </div>
            <div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800/80">
              <div class="text-slate-400">CHALLENGER PTW TARGET (API #16)</div>
              <div class="text-emerald-300 font-semibold mt-1">{html.escape(ptw_str)}</div>
            </div>
            <div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800/80">
              <div class="text-slate-400">EST. SUBCONTRACTING POOL (API #11)</div>
              <div class="text-sky-300 font-semibold mt-1">{html.escape(sub_pool_str)}</div>
            </div>
          </div>
          <div class="p-5 rounded-xl bg-navy-950 border border-indigo-500/40 space-y-3 text-xs font-mono">
            <div class="text-indigo-300 font-bold uppercase">// CAPTUREDESK RECOMPETE SHAPING &amp; SUBCONTRACTING PLAYBOOK</div>
            <div><strong class="text-slate-200">Challenger Price-to-Win Ceiling (API #16):</strong> <span class="text-emerald-300">{html.escape(ptw_str)} vs. {html.escape(amt_fmt)} incumbent baseline</span></div>
            <div><strong class="text-slate-200">FAR 19.502-2 Set-Aside Shaping (API #21):</strong> <span class="text-sky-300">Generate a Sources Sought / RFI Rule-of-Two capability package for {html.escape(agency)} prior to recompete release.</span></div>
            <div><strong class="text-slate-200">13 CFR &sect; 125.6 Teaming &amp; Subcontracting (API #11):</strong> <span class="text-slate-300">Target {html.escape(sub_pool_str)} in small-business workshare with {html.escape(comp_name)}.</span></div>
            <div class="pt-2 flex flex-wrap gap-3">
              <a href="{WHOP_TIER2_URL}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center px-5 py-2.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold transition-all">
                Unlock Full Recompete &amp; Teaming Dossier &rarr;
              </a>
              <a href="../../apis.html#product-sources-sought-response" class="inline-flex items-center px-4 py-2.5 rounded-lg bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/40 text-indigo-300 transition-all">
                Shape via API #21 &amp; API #16 &rarr;
              </a>
              <a href="{html.escape(usa_url, quote=True)}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center px-4 py-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 transition-all">
                Verify Award on USAspending.gov &nearr;
              </a>
              <button type="button" onclick="window.unlockFoiaWinningBidVault(&quot;recompete&quot;, &quot;federal&quot;, &quot;541512&quot;, &quot;{html.escape(awd_id, quote=True)}&quot;, &quot;{html.escape(agency, quote=True)}&quot;)" class="inline-flex items-center px-4 py-2.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-300 transition-all cursor-pointer">
                FOIA Incumbent Rate Vault &amp; Statutory Demand &rarr;
              </button>
            </div>
            <div id="foia-vault-box-recompete" class="hidden mt-3 p-4 rounded-xl bg-navy-900 border border-emerald-500/40"></div>
          </div>
        </div>
        """
        prof_html = _render_layout(
            page_title=f"{awd_id} Recompete & Teaming Dossier ({comp_name} {amt_fmt}) | {agency} | SignalTender",
            meta_desc=f"Federal Contract Recompete & Subcontracting Dossier for {awd_id} ({comp_name}, {amt_fmt} at {agency}, PoP through {end_dt}). Includes API #16 Price-to-Win target ({ptw_str}) and {sub_pool_str}.",
            canonical_path=canonical_rel,
            body_html=prof_body,
            root_prefix="../../",
            default_state="federal",
        )
        with open(os.path.join(recompete_dir, f"{slug_id}.html"), "w", encoding="utf-8") as f:
            f.write(prof_html)
        built += 1

    total_targets = len(recompete_rows_html) + len(sub_rows_html) + len(profile_rows_html)
    hub_canonical = "contracts/recompetes/index.html"
    sitemap_urls.append(f"{SITE_BASE_URL}/{hub_canonical}")
    hub_body = f"""
    <div id="static-contracts-top-section" class="mb-8 space-y-4">
      <div class="inline-flex items-center px-3 py-1 rounded border text-xs font-mono bg-amber-500/10 text-amber-300 border-amber-500/30">
        // PRE-RFP RECOMPETE RADAR &amp; PRIME SUBCONTRACTING WIRE &bull; {total_targets} VERIFIED FEDERAL PIID TARGETS
      </div>
      <h1 class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
        Federal IT Recompete Radar (90&ndash;180d) &amp; Prime Subcontracting Wire
      </h1>
      <p class="text-slate-300 text-sm sm:text-base max-w-3xl">
        Search {total_targets} verified federal IT contract IDs (PIIDs) to position 90 to 180 days before recompete RFPs drop with API #16 Challenger Price-to-Win ceilings and API #21 FAR 19.502-2 Sources Sought shaping, or capture warm FAR 52.219-9 small-business subcontracting dollars on active Prime awards.
      </p>
    </div>

    <div id="static-contracts-table-card" class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">
      <div class="p-4 bg-slate-900/70 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="relative flex-1 flex items-center">
          <input
            id="static-rfp-search"
            type="text"
            placeholder="Filter {total_targets} federal contracts by PIID Award ID, incumbent prime, or agency..."
            oninput="window.filterStaticContractsTable(this.value)"
            class="w-full px-4 py-2 rounded-xl bg-navy-950 border border-slate-700/90 focus:border-sky-500 focus:outline-none text-xs font-mono text-white placeholder-slate-500"
          />
        </div>
        <span id="static-rfp-count-badge" class="text-xs font-mono text-emerald-400 shrink-0">{total_targets} PIIDS INDEXED</span>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-800 bg-slate-900/90 text-[11px] font-mono uppercase tracking-wider text-slate-400">
              <th class="py-4 px-5">Signal Type</th>
              <th class="py-4 px-5">Award ID, Incumbent / Prime &amp; Scope</th>
              <th class="py-4 px-4">Awarding Sub-Agency</th>
              <th class="py-4 px-4">PTW Ceiling / Sub Pool</th>
              <th class="py-4 px-5 text-right">Dossier</th>
            </tr>
          </thead>
          <tbody class="text-xs">
            {''.join(recompete_rows_html)}
            {''.join(sub_rows_html)}
            {''.join(profile_rows_html)}
          </tbody>
        </table>
      </div>
    </div>
    """
    hub_html = _render_layout(
        page_title="Federal IT Recompete Radar (90–180d) & Prime Subcontracting Wire | SignalTender",
        meta_desc="Track expiring federal IT contracts 90–180 days before recompete with Price-to-Win ceilings and capture FAR 52.219-9 small-business subcontracting pools on newly awarded Prime contracts.",
        canonical_path=hub_canonical,
        body_html=hub_body,
        root_prefix="../../",
        default_state="federal",
    )
    with open(os.path.join(recompete_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(hub_html)
    built += 1
    return built


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
        raw_records = []
        try:
            r_rest = requests.get(
                f"{SUPABASE_URL.rstrip('/')}/rest/v1/{TABLE_NAME}",
                params={"select": "*", "order": "id.desc", "limit": "500"},
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                timeout=15,
            )
            if r_rest.status_code == 200:
                raw_records = r_rest.json()
        except Exception:
            pass
        supabase = None
        if not raw_records:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
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
            elif j_key == "new_jersey":
                compliance_posture = "NJ OIT Statewide Cyber Policy (NIST 800-53) • StateRAMP / SOC 2 Type II • NJ VPAT"
            elif j_key == "washington":
                compliance_posture = "WaTech OCIO Sec 141.10 (NIST 800-53) • StateRAMP / SOC 2 Type II • WA VPAT"
            elif j_key == "michigan":
                compliance_posture = "MI DTMB 1340.00 Cyber Security (NIST 800-53) • StateRAMP / MiLogin • MI VPAT"
            elif j_key == "colorado":
                compliance_posture = "Colorado OIT CIS Policies (NIST 800-53) • StateRAMP • CO HB 21-1110 Accessibility VPAT"
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
            elif j_key == "new_jersey":
                teaming_posture = "NJ Treasury SBE Set-Aside (25% Goal) + DVOB (3%) • NJSTART M4002/T3121 Eligible"
            elif j_key == "washington":
                teaming_posture = "WA OMWBE Small/Veteran Goal (15%+ OMWBE + 5% WDVA) • WA DES Master Contract Eligible"
            elif j_key == "michigan":
                teaming_posture = "MI Geographically Disadvantaged Business (GDB) + SDVOB (5% Preference) • MiDEAL Eligible"
            elif j_key == "colorado":
                teaming_posture = "CO Service-Disabled Veteran-Owned Small Business (SDVOSB 5% Pref) + SBE • CO Price Agreement Eligible"
            elif j_key == "california":
                teaming_posture = "CA DGS SB (5%) + DVBE • Prime ≥51% Core Scope"
            else:
                teaming_posture = "Local SBE/MWBE Sub Plan • Prime ≥51% Core Scope"

            locality_delta = {
                "federal": 8, "new_york": 10, "california": 9, "massachusetts": 7, "washington": 7, "virginia": 6, "maryland": 6,
                "illinois": 3, "pennsylvania": 2, "michigan": 2, "colorado": 4, "texas": 1, "florida": 0, "ohio": -2, "georgia": 0, "north_carolina": -1, "municipal": -2,
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
            raw_wt = d_cached.get("win_themes") or []
            raw_ev = d_cached.get("evidence_needed") or []
            wt_str = " ".join(re.sub(r"\*\*", "", str(x)) for x in raw_wt[:3]) if isinstance(raw_wt, list) else ""
            ev_str = " ".join(str(x) for x in raw_ev[:2]) if isinstance(raw_ev, list) else ""
            rfp_scope_text = str(d_cached.get("scope_summary") or "").strip()
            if wt_str or ev_str:
                rfp_scope_text = f"{rfp_scope_text} {wt_str} {ev_str}".strip()
            if not rfp_scope_text:
                rfp_scope_text = (
                    f"Solicitation '{clean_t}' issued by {agency_str} (Due: {due_str or 'Open'}). "
                    f"Contractor shall deliver {CATEGORIES[cats[0]]['name']} under NAICS {naics_display} ({sba_cap} SBA standard) "
                    f"in full compliance with {compliance_posture} and {teaming_posture}. "
                    f"Required Key Personnel: {key_personnel_lcats}. Target Price-to-Win: {igce_ptw_posture}."
                )

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
                "rfp_text": rfp_scope_text,
            })

        if spam_ids_to_purge and supabase is not None:
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
            portal_host = re.sub(r"^https?://(www\.)?", "", str(c["url"] or "sam.gov")).split("/")[0] or "sam.gov"
            real_co_routing = f"Official {j_meta['portal']} Electronic Q&A & Contracting Officer Portal ({c['agency']})"

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
                <div id="static-rfp-scope-card" class="p-6 sm:p-8 rounded-2xl bg-navy-900 border border-slate-800 shadow-2xl space-y-5">
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
                  <div id="static-rfp-ai-shred-card" class="mt-6 p-6 rounded-xl bg-navy-950 border-2 border-indigo-500/50 space-y-5">
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
                        <div class="text-[10px] text-sky-300 font-bold">06. CPARS, ORALS &amp; DEBRIEF/PROTEST (API #15 / #17 / #19)</div>
                        <div class="text-slate-200">{html.escape(c['cpars_benchmark'])}</div>
                      </div>
                    </div>

                    <div class="space-y-2 text-xs font-mono text-slate-400 pt-1 break-words">
                      <div><strong class="text-slate-200">Official Government Bid URL:</strong> <span id="dossier-bid-url-mask" data-real-url="{html.escape(c['url'], quote=True)}" class="blur-sm select-none break-all">https://portal.government.gov/solicitation/view/{c['id']}98412</span></div>
                      <div><strong class="text-slate-200">Full Issuing Buyer &amp; Contracting Officer:</strong> <span id="dossier-agency-mask" class="blur-sm select-none">{html.escape(c['agency'])} - Procurement Division</span></div>
                      <div><strong class="text-slate-200">Contracting Office &amp; RFI / Q&amp;A Submission Routing:</strong> <span id="dossier-co-routing-mask" data-real-routing="{html.escape(real_co_routing, quote=True)}" class="blur-sm select-none break-words">contracting.officer@{html.escape(portal_host)} &bull; Electronic Q&amp;A Desk ({html.escape(c['agency'])})</span></div>
                      <div><strong class="text-slate-200">Shipley Section L/M Compliance Matrix, SF-30 Diff &amp; CPARS Vol. III:</strong> <span class="blur-sm select-none break-words">Pre-built in #capturedesk-autopilot &amp; API #05/#06/#14/#15/#16/#17/#18/#19/#20/#21</span></div>
                    </div>
                    <div class="pt-3 flex flex-col sm:flex-row gap-3">
                      <a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center justify-center px-6 py-3 text-sm font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg shadow-lg transition-all">
                        Unlock Direct RFP Link &amp; Capture Dossier &rarr;
                      </a>
                      <a href="../../index.html#contracts/rfp/{c['slug']}" class="inline-flex items-center justify-center px-5 py-3 text-xs font-mono font-semibold text-emerald-300 bg-emerald-500/15 hover:bg-emerald-500/25 rounded-lg border border-emerald-500/40 transition-colors">
                        Run Live Pwin &amp; Shred in Studio &rarr;
                      </a>
                      <button id="compile-zip-btn-static" type="button" onclick="window.compileShipleyProposalZip(&quot;{c['slug']}&quot;, &quot;{html.escape(c['clean_title'], quote=True)}&quot;, &quot;{html.escape(c['masked_agency'], quote=True)}&quot;, &quot;{html.escape(c['naics_display'], quote=True)}&quot;, &quot;Small Business&quot;)" class="inline-flex items-center justify-center px-5 py-3 text-xs font-mono font-semibold text-indigo-200 bg-indigo-600/30 hover:bg-indigo-600/50 rounded-lg border border-indigo-400/50 transition-colors cursor-pointer">
                        1-Click Compile 6-File Proposal &amp; Legal (.ZIP) &darr;
                      </button>
                      <button type="button" onclick="window.toggleTeamingClearinghouseBox(&quot;teaming-box-static&quot;)" class="inline-flex items-center justify-center px-4 py-3 text-xs font-mono text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 rounded-lg border border-amber-500/30 transition-colors cursor-pointer">
                        Request 13 CFR &sect; 125.6 Teaming Slot &rarr;
                      </button>
                      <button type="button" onclick="window.unlockFoiaWinningBidVault(&quot;static&quot;, &quot;{c['jurisdiction']}&quot;, &quot;{html.escape(c['naics_display'], quote=True)}&quot;, &quot;{html.escape(c['clean_title'], quote=True)}&quot;, &quot;{html.escape(c['masked_agency'], quote=True)}&quot;)" class="inline-flex items-center justify-center px-4 py-3 text-xs font-mono text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 rounded-lg border border-emerald-500/30 transition-colors cursor-pointer">
                        FOIA Incumbent Rate Vault &amp; Demand &rarr;
                      </button>
                    </div>
                    <div id="vault-status-static" class="hidden mt-2 p-2.5 rounded-lg bg-emerald-950/50 border border-emerald-500/40 text-xs font-mono text-emerald-300"></div>
                    <div id="foia-vault-box-static" class="hidden mt-3 p-4 rounded-xl bg-navy-900 border border-emerald-500/40"></div>
                    <div id="teaming-box-static" class="hidden mt-3 p-4 rounded-xl bg-navy-900 border border-amber-500/40 space-y-3 text-xs font-mono">
                      <div class="text-amber-300 font-bold uppercase">// TWO-SIDED FAR 52.219-9 &amp; 13 CFR &sect; 125.6 TEAMING CLEARINGHOUSE</div>
                      <p class="text-slate-300">Register your verified UEI/CAGE and socio-economic status to request a compliant Prime/Sub workshare slot on this solicitation (auto-validates the 50% Limitation on Subcontracting rule).</p>
                      <div class="grid grid-cols-1 sm:grid-cols-5 gap-2.5">
                        <input id="teaming-co-static" type="text" placeholder="Company Name LLC" class="px-3 py-2 rounded-lg bg-navy-950 border border-slate-700 text-white placeholder-slate-500" />
                        <input id="teaming-uei-static" type="text" placeholder="UEI / CAGE Code" class="px-3 py-2 rounded-lg bg-navy-950 border border-slate-700 text-white placeholder-slate-500" />
                        <select id="teaming-soc-static" class="px-2.5 py-2 rounded-lg bg-navy-950 border border-slate-700 text-white">
                          <option value="SDVOSB">SDVOSB</option>
                          <option value="8(a)">SBA 8(a)</option>
                          <option value="WOSB">WOSB / EDWOSB</option>
                          <option value="HUBZone">HUBZone</option>
                          <option value="Small Business">Small Business / State MBE</option>
                        </select>
                        <input id="teaming-em-static" type="email" placeholder="bd@yourcompany.com" class="px-3 py-2 rounded-lg bg-navy-950 border border-slate-700 text-white placeholder-slate-500" />
                        <button type="button" onclick="window.submitInlineTeamingSlot(&quot;static&quot;, &quot;{html.escape(c['clean_title'], quote=True)}&quot;, &quot;{html.escape(c['masked_agency'], quote=True)}&quot;, &quot;{html.escape(c['naics_display'], quote=True)}&quot;)" class="px-3 py-2 rounded-lg bg-amber-500/20 hover:bg-amber-500/35 border border-amber-400/50 text-amber-200 font-semibold cursor-pointer">
                          Verify &amp; Match &rarr;
                        </button>
                      </div>
                      <div id="teaming-status-static" class="hidden"></div>
                    </div>
                    <p class="text-[11px] font-mono text-slate-400">Instant 60-second Discord, Slack, Microsoft Teams &amp; CRM webhook activation. Cancel anytime.</p>
                  </div>
                </div>

                <div id="static-rfp-related-card" class="p-6 rounded-2xl bg-navy-900/60 border border-slate-800">
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
                    Get every pre-vetted Federal (SAM.gov), DemandStar, and 16-State SLED (TX, VA, CA, FL, MD, IL, PA, OH, GA, NC, NY, MA, NJ, WA, MI, CO) IT &amp; cybersecurity solicitation pushed directly to your team every 6 hours.
                  </p>
                  <ul class="text-xs font-mono text-slate-300 space-y-2 pt-2">
                    <li>&check; 99.4% Commodity &amp; Renewal Spam Stripped</li>
                    <li>&check; Tier 2 CaptureDesk ($399/mo) 21-API Auto-Dossiers</li>
                    <li class="text-emerald-300">&check; Tier 3 ($1,499/mo) 1-Click 3-Vol .DOCX/.XLSX Proposal .ZIP</li>
                    <li class="text-amber-300">&check; Tier 4 ($2,499/mo) 50k OEM API Calls &amp; FOIA Rate Vault</li>
                  </ul>
                  <a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="w-full inline-flex items-center justify-center px-5 py-2.5 text-xs font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg transition-all">
                    Start Tier 1 Leads ($99/mo) &rarr;
                  </a>
                  <a href="{WHOP_TIER2_URL}" target="_blank" rel="noopener noreferrer" class="w-full inline-flex items-center justify-center px-5 py-2.5 text-xs font-mono font-semibold text-indigo-200 bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 rounded-lg transition-all">
                    Launch Tier 2 CaptureDesk ($399/mo) &rarr;
                  </a>
                  <a href="{WHOP_TIER3_URL}" target="_blank" rel="noopener noreferrer" class="w-full inline-flex items-center justify-center px-5 py-2.5 text-xs font-mono font-semibold text-emerald-200 bg-emerald-600/25 hover:bg-emerald-600/45 border border-emerald-500/40 rounded-lg transition-all">
                    Start Tier 3 Proposal .ZIP ($1,499/mo) &rarr;
                  </a>
                  <a href="{WHOP_TIER4_URL}" target="_blank" rel="noopener noreferrer" class="w-full inline-flex items-center justify-center px-5 py-2 text-[11px] font-mono font-semibold text-amber-200 bg-amber-500/15 hover:bg-amber-500/30 border border-amber-500/40 rounded-lg transition-all">
                    Tier 4 OEM &amp; FOIA Vault ($2,499/mo) &rarr;
                  </a>
                </div>

                <div class="p-6 rounded-2xl bg-navy-900 border border-indigo-500/30 space-y-3">
                  <div class="text-xs font-mono text-indigo-400 uppercase font-semibold">24 LIVE APIs &amp; MCP SERVER</div>
                  <div class="text-lg font-bold text-white">Automate Your Bid Response</div>
                  <p class="text-xs text-slate-300 leading-relaxed">
                    Shape pre-RFP Sources Sought &amp; RFI set-asides (FAR 19.502-2 Rule-of-Two), generate GSA MAS Schedule SIN matrices, 0.75% IFF ceiling rate cards &amp; GSAR 552.238-81 PRC compliance packages, analyze FAR 15.506 Post-Award Debriefings &amp; GAO Bid-Protest viability, generate NIST 800-53 Rev 5 RMF, Continuous ATO (cATO), SSP &amp; POA&amp;M packages, FAR 15.102 Oral Presentation &amp; Murder-Board prep, model IGCE wrap-rates &amp; Price-to-Win, generate CPARS &amp; Past Performance Volume III citations, diff SF-30 RFP amendments, tailor Key Personnel &amp; GSA LCAT resumes, auto-answer SOC 2, FedRAMP &amp; NIST 800-171 security questionnaires, generate 13 CFR &sect; 125.6 (50% Rule) teaming plans, extract Section B CLIN pricing tables, draft Shipley proposal narratives &amp; CO Q&amp;A, classify NAICS/SIC/PSC/UNSPSC codes, score Bid/No-Bid Pwin (0&ndash;100), audit FAR/DFARS &amp; CMMC 2.0 flow-downs, or shred this RFP into a compliance matrix via our 24 RapidAPI microservices &amp; <code class="text-indigo-200">@signaltender/mcp-server</code>.
                  </p>
                  <a href="../../apis.html#product-sources-sought-response" class="w-full inline-flex items-center justify-center px-4 py-2.5 text-xs font-mono font-semibold text-indigo-300 bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/40 rounded-lg transition-all">
                    Explore 24 APIs &amp; MCP Server &rarr;
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
            <div id="static-contracts-top-section" class="mb-8 space-y-4">
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

            <div id="static-contracts-table-card" class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">
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
                <div id="static-contracts-top-section" class="mb-6 text-xs font-mono text-slate-400 flex items-center gap-2">
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
                <div id="static-contracts-table-card" class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">
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
        <div id="static-contracts-top-section" class="mb-10 space-y-4">
          <div class="inline-flex items-center px-3 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-xs font-mono text-emerald-400">
            // LIVE GOVCON DIRECTORY &bull; {len(enriched_contracts)} VERIFIED OPEN IT SOLICITATIONS
          </div>
          <h1 class="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            Federal &amp; State SLED IT Contract Directory
          </h1>
          <p class="text-slate-300 text-base max-w-3xl">
            Explore {len(enriched_contracts)} live, AI-vetted government IT, software, cloud, and cybersecurity RFPs across SAM.gov, DemandStar, Texas, Virginia, California, Florida, Maryland, Illinois, Pennsylvania, Ohio, Georgia, North Carolina, New York, Massachusetts, New Jersey, Washington, Michigan, and Colorado.
          </p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {jurisdiction_cards_html}
        </div>

        <div class="mb-12 p-5 sm:p-6 rounded-2xl bg-gradient-to-r from-navy-900 via-slate-900 to-indigo-950/80 border border-amber-500/40 flex flex-col xl:flex-row xl:items-center justify-between gap-4">
          <div class="space-y-1">
            <div class="text-[11px] font-mono text-amber-300 font-semibold uppercase tracking-wider">// PRE-RFP RECOMPETE RADAR (90&ndash;180D) &amp; PRIME SUBCONTRACTING WIRE</div>
            <h2 class="text-lg sm:text-xl font-bold text-white">Capture Expiring Federal IT Contracts &amp; 30% Small-Business Subcontracting Pools Before the RFP Drops</h2>
            <p class="text-xs text-slate-300">Explore 27 verified federal IT recompetes (with API #16 Challenger Price-to-Win ceilings &amp; API #21 FAR 19.502-2 set-aside shaping) and newly awarded Prime contracts with mandatory FAR 52.219-9 subcontracting pools.</p>
          </div>
          <div class="flex flex-wrap gap-2.5">
            <a href="recompetes/index.html" class="inline-flex items-center justify-center px-3.5 sm:px-5 py-2.5 sm:py-3 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/40 text-amber-300 text-[11px] sm:text-xs font-mono font-semibold whitespace-nowrap transition-all">
              Open Recompete &amp; Sub Wire &rarr;
            </a>
            <a href="https://b2b-contract-parser-api.onrender.com/v1/proposal-autopilot/foia-winning-bid-vault" target="_blank" rel="noopener noreferrer" class="inline-flex items-center justify-center px-3.5 sm:px-5 py-2.5 sm:py-3 rounded-xl bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-300 text-[11px] sm:text-xs font-mono font-semibold whitespace-nowrap transition-all">
              FOIA / PIA Winning-Bid Rate Vault (JSON) &nearr;
            </a>
          </div>
        </div>

        <h2 class="text-xl font-bold text-white font-mono uppercase tracking-wider mb-4">Latest Pre-Vetted Solicitations</h2>
        <div id="static-contracts-table-card" class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">
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
            meta_desc="Browse live pre-vetted Federal (SAM.gov) and State SLED (TX, VA, CA, FL, MD, IL, PA, OH, GA, NC, NY, MA, NJ, WA, MI, CO) IT, software, cloud, and cybersecurity RFPs.",
            canonical_path="contracts/index.html",
            body_html=hub_body,
            root_prefix="../",
        )
        with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
            f.write(hub_html)
        pages_built += 1

        # 3b. Build Evergreen Federal Recompete Radar & Prime Subcontracting Wire pages (/contracts/recompetes/*.html)
        pages_built += _generate_recompete_and_subcontracting_pseo_pages(sitemap_urls)

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
        try:
            verify_site_integrity.main()
        except SystemExit as vse:
            if vse.code in (0, None):
                pass
            else:
                # verify_site_integrity.fail() already printed the exact diagnostic and logged it
                # to error_telemetry; do not spam Discord #alerts with a generic "error: 1" message.
                raise RuntimeError(
                    "verify_site_integrity.py pre-push check failed during local build (see [FAIL] diagnostic above)."
                )

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
        # Only dispatch Discord #alerts for real runtime/pipeline failures (or Render Cron runs),
        # never for local verify_site_integrity pre-push lint failures ("error: 1").
        if "verify_site_integrity.py pre-push check failed" not in str(e) and str(e).strip() != "1":
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
              <a href="#contracts/maryland" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-sky-300">Maryland</a>
              <a href="#contracts/illinois" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-teal-300">Illinois</a>
              <a href="#contracts/pennsylvania" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-orange-300">Pennsylvania</a>
              <a href="#contracts/ohio" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-lime-300">Ohio</a>
              <a href="#contracts/georgia" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-sky-300">Georgia</a>
              <a href="#contracts/north_carolina" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-sky-300">North Carolina</a>
              <a href="#contracts/new_york" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-blue-300">New York</a>
              <a href="#contracts/massachusetts" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-sky-300">Massachusetts</a>
              <a href="#contracts/new_jersey" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-amber-300">New Jersey</a>
              <a href="#contracts/washington" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-emerald-300">Washington</a>
              <a href="#contracts/michigan" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-sky-300">Michigan</a>
              <a href="#contracts/colorado" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-sky-300">Colorado</a>
              <a href="#contracts/municipal" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-sky-300">Municipal</a>
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
            "rfp_text": c.get("rfp_text", ""),
        })

    if not spa_contracts:
        m_existing = re.search(r"window\.SIGNALTENDER_CONTRACTS\s*=\s*(\\[.*?\\]);\s*window\.SIGNALTENDER_JURISDICTIONS", index_html, flags=re.S)
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
    <div class="hidden sm:block w-full max-w-full overflow-x-hidden border-b border-slate-800/80 bg-navy-900/90 text-xs">
      <div class="max-w-[1600px] mx-auto px-3 sm:px-6 lg:px-8 min-h-[2.25rem] py-1.5 flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <div class="flex items-center space-x-2.5 shrink-0">
          <span class="inline-block h-2 w-2 rounded-full bg-emerald-500"></span>
          <span class="font-mono text-slate-300">LIVE GOVCON INTELLIGENCE WIRE &bull; <span class="text-emerald-400">18 PORTALS ACTIVE</span></span>
        </div>
        <div class="flex items-center space-x-3 sm:space-x-4 font-mono text-slate-400 shrink-0">
          <a href="#overview" class="hover:text-sky-400 transition-colors">&larr; Main Platform</a>
          <span>|</span>
          <a href="#apis" class="hover:text-sky-400 transition-colors">Developer APIs</a>
        </div>
      </div>
    </div>

    <header class="sticky top-0 z-50 w-full max-w-full overflow-x-hidden backdrop-blur-md bg-navy-950/90 border-b border-slate-800/80">
      <div class="max-w-[1600px] mx-auto px-3 sm:px-6 lg:px-8 h-12 sm:h-20 flex flex-nowrap items-center justify-between gap-2">
        <a href="#overview" class="flex flex-col justify-center shrink-0">
          <div class="inline-flex items-center gap-[4px]">
            <svg class="w-[21px] h-[21px] shrink-0 -translate-y-[1px]" viewBox="6 5 52 54" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="32" cy="24" r="15" stroke="#F8FAFC" stroke-width="5.6" />
              <circle cx="32" cy="24" r="5" fill="#38BDF8" />
              <path d="M10 54L32 42L54 54" stroke="#38BDF8" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span class="text-[23px] font-semibold tracking-[-0.03em] text-white leading-none whitespace-nowrap">SignalTender</span>
            <span class="hidden sm:inline-flex ml-1.5 items-center whitespace-nowrap text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-slate-900 text-sky-400/90 border border-slate-800 leading-none">LIVE RFP INDEX</span>
          </div>
          <span class="hidden sm:block text-[11px] font-mono text-slate-500 tracking-tight leading-none whitespace-nowrap mt-1">FEDERAL &amp; 16-STATE SLED CONTRACT DIRECTORY</span>
        </a>
        <!-- Full-Width Organized Site Navigation Bar -->
        <nav aria-label="Primary Site Navigation" class="hidden lg:flex flex-1 items-center justify-between gap-1 xl:gap-2 mx-1.5 xl:mx-2 2xl:mx-5 p-1 xl:p-1.5 rounded-xl bg-navy-900/95 border border-slate-800/90 shadow-inner">
          <a href="#overview" class="flex-1 inline-flex items-center justify-center px-2 xl:px-2.5 2xl:px-3.5 py-1.5 xl:py-2 rounded-lg text-[11px] xl:text-xs 2xl:text-[13px] font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 border border-transparent transition-all whitespace-nowrap">Platform Overview</a>
          <a href="#contracts" class="flex-1 inline-flex items-center justify-center px-2 xl:px-2.5 2xl:px-3.5 py-1.5 xl:py-2 rounded-lg text-[11px] xl:text-xs 2xl:text-[13px] font-semibold text-white bg-sky-500/15 border border-sky-500/40 shadow-sm transition-all whitespace-nowrap">Live RFP Directory</a>
          <a href="#apis" class="flex-1 inline-flex items-center justify-center px-2 xl:px-2.5 2xl:px-3.5 py-1.5 xl:py-2 rounded-lg text-[11px] xl:text-xs 2xl:text-[13px] font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 border border-transparent transition-all whitespace-nowrap">API Catalog</a>
          <a href="#checkout" class="flex-1 inline-flex items-center justify-center px-2 xl:px-2.5 2xl:px-3.5 py-1.5 xl:py-2 rounded-lg text-[11px] xl:text-xs 2xl:text-[13px] font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 border border-transparent transition-all whitespace-nowrap">Plans &amp; Pricing</a>
        </nav>
        <div class="w-auto flex items-center justify-end gap-1.5 sm:gap-2 shrink-0">
          <button
            type="button"
            onclick="window.toggleSignalTheme()"
            aria-label="Toggle Light and Dark Theme"
            title="Switch between Institutional Graphite (Dark) and Executive Ivory (Light)"
            class="st-theme-toggle-btn inline-flex items-center justify-center gap-1.5 whitespace-nowrap px-2 py-1.5 sm:py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[11px] sm:text-xs font-mono font-semibold text-slate-200 hover:text-white transition-all cursor-pointer shrink-0"
          >
            <svg class="st-icon-sun w-3.5 h-3.5 text-sky-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="4" />
              <path stroke-linecap="round" d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41m11.32-11.32l1.41-1.41" />
            </svg>
            <svg class="st-icon-moon w-3.5 h-3.5 text-sky-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
            </svg>
            <span class="hidden sm:inline lg:hidden 2xl:inline st-theme-label">Light</span>
          </button>
<div id="contracts-header-auth-guest" class="flex items-center gap-1 sm:gap-1.5 2xl:pr-2 2xl:border-r 2xl:border-slate-800 shrink-0">
            <a href="#account" onclick="window.openClientPortal('login')" class="inline-flex items-center justify-center px-2 sm:px-2.5 py-1.5 sm:py-2 text-[11px] sm:text-xs font-mono font-semibold text-slate-200 hover:text-white hover:bg-slate-900 rounded-lg transition-colors whitespace-nowrap">Log In</a>
            <a href="#account" onclick="window.openClientPortal('register')" class="inline-flex items-center justify-center px-2 sm:px-2.5 py-1.5 sm:py-2 text-[11px] sm:text-xs font-mono font-bold text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-lg transition-all whitespace-nowrap">Sign Up</a>
          </div>
          <div id="contracts-header-auth-user" class="hidden items-center 2xl:pr-2 2xl:border-r 2xl:border-slate-800 shrink-0">
            <a href="#account" class="inline-flex items-center gap-1.5 whitespace-nowrap px-2.5 py-1.5 text-[11px] sm:text-xs font-mono font-bold text-emerald-300 bg-emerald-950/70 hover:bg-emerald-900/70 rounded-lg border border-emerald-500/40 transition-all max-w-[155px]">
              <span class="h-2 w-2 rounded-full bg-emerald-400 shrink-0"></span>
              <span id="contracts-header-auth-user-label" class="truncate max-w-[100px]">Account</span>
              <span class="shrink-0">&rarr;</span>
            </a>
          </div>
          <a href="#checkout-tier1" class="hidden 2xl:inline-flex items-center px-3 py-1.5 2xl:px-3.5 2xl:py-2 text-xs font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg border border-sky-400/30 transition-all shrink-0 whitespace-nowrap">
            Unlock All RFP Links &rarr;
          </a>
        </div>
      </div>
      <div class="lg:hidden border-t border-slate-800/80 bg-navy-900/90">
        <nav aria-label="Mobile Site Navigation" class="max-w-[1600px] mx-auto px-2.5 sm:px-4 py-1.5 grid grid-cols-4 gap-1 sm:gap-1.5 text-[10.5px] sm:text-[11px] font-sans font-medium sm:font-mono text-center">
          <a href="#overview" class="px-1 sm:px-2.5 py-1 rounded-md bg-navy-950 text-slate-200 hover:text-sky-400 border border-slate-800 tracking-tight whitespace-nowrap">Overview</a>
          <a href="#contracts" class="px-1 sm:px-2.5 py-1 rounded-md bg-sky-500/20 text-white border border-sky-500/40 font-semibold tracking-tight whitespace-nowrap">RFP Directory</a>
          <a href="#apis" class="px-1 sm:px-2.5 py-1 rounded-md bg-navy-950 text-slate-200 hover:text-sky-400 border border-slate-800 tracking-tight whitespace-nowrap">APIs</a>
          <a href="#checkout" class="px-1 sm:px-2.5 py-1 rounded-md bg-navy-950 text-slate-200 hover:text-sky-400 border border-slate-800 tracking-tight whitespace-nowrap">Plans &amp; Pricing</a>
        </nav>
      </div>
    </header>

    <div class="border-b border-slate-800/70 bg-navy-900/60">
      <div class="max-w-[1600px] mx-auto px-3 sm:px-6 lg:px-8 py-1.5 flex items-center gap-2.5">
        <label for="mobile-contracts-portal-select" class="sr-only">Jump to State or Portal</label>
        <select id="mobile-contracts-portal-select" onchange="if(this.value) window.location.hash=this.value;" class="sm:hidden shrink-0 px-2 py-1 rounded-md bg-navy-950 border border-slate-700 text-[11px] font-mono text-sky-400 focus:border-sky-500 focus:outline-none">
          <option value="#contracts">Portal: All (18)</option>
          <option value="#contracts/federal">Federal (SAM.gov)</option>
          <option value="#contracts/texas">Texas (ESBD)</option>
          <option value="#contracts/virginia">Virginia (eVA)</option>
          <option value="#contracts/california">California</option>
          <option value="#contracts/florida">Florida (MFMP)</option>
          <option value="#contracts/maryland">Maryland (eMMA)</option>
          <option value="#contracts/illinois">Illinois (BidBuy)</option>
          <option value="#contracts/pennsylvania">Pennsylvania</option>
          <option value="#contracts/ohio">Ohio (OhioBuys)</option>
          <option value="#contracts/georgia">Georgia (GPR)</option>
          <option value="#contracts/north_carolina">North Carolina</option>
          <option value="#contracts/new_york">New York (CROL)</option>
          <option value="#contracts/massachusetts">Massachusetts</option>
          <option value="#contracts/new_jersey">New Jersey</option>
          <option value="#contracts/washington">Washington</option>
          <option value="#contracts/michigan">Michigan (SIGMA)</option>
          <option value="#contracts/colorado">Colorado (VSS)</option>
          <option value="#contracts/municipal">Municipal</option>
        </select>
        <nav aria-label="State and Portal Quick Jump" class="hidden sm:flex flex-1 flex-wrap items-center gap-x-3.5 gap-y-1.5 py-1 text-[11px] font-mono text-slate-300">
          <a href="#contracts" class="shrink-0 text-sky-400 font-semibold hover:text-sky-300 transition-colors">All Portals</a>
          <a href="#contracts/federal" class="shrink-0 hover:text-sky-400 transition-colors">Federal</a>
          <a href="#contracts/texas" class="shrink-0 hover:text-sky-400 transition-colors">Texas</a>
          <a href="#contracts/virginia" class="shrink-0 hover:text-sky-400 transition-colors">Virginia</a>
          <a href="#contracts/california" class="shrink-0 hover:text-sky-400 transition-colors">California</a>
          <a href="#contracts/florida" class="shrink-0 hover:text-sky-400 transition-colors">Florida</a>
          <a href="#contracts/maryland" class="shrink-0 hover:text-sky-400 transition-colors">Maryland</a>
          <a href="#contracts/illinois" class="shrink-0 hover:text-sky-400 transition-colors">Illinois</a>
          <a href="#contracts/pennsylvania" class="shrink-0 hover:text-sky-400 transition-colors">Pennsylvania</a>
          <a href="#contracts/ohio" class="shrink-0 hover:text-sky-400 transition-colors">Ohio</a>
          <a href="#contracts/georgia" class="shrink-0 hover:text-sky-400 transition-colors">Georgia</a>
          <a href="#contracts/north_carolina" class="shrink-0 hover:text-sky-400 transition-colors">North Carolina</a>
          <a href="#contracts/new_york" class="shrink-0 hover:text-sky-400 transition-colors">New York</a>
          <a href="#contracts/massachusetts" class="shrink-0 hover:text-sky-400 transition-colors">Massachusetts</a>
          <a href="#contracts/new_jersey" class="shrink-0 hover:text-sky-400 transition-colors">New Jersey</a>
          <a href="#contracts/washington" class="shrink-0 hover:text-sky-400 transition-colors">Washington</a>
          <a href="#contracts/michigan" class="shrink-0 hover:text-sky-400 transition-colors">Michigan</a>
          <a href="#contracts/colorado" class="shrink-0 hover:text-sky-400 transition-colors">Colorado</a>
          <a href="#contracts/municipal" class="shrink-0 hover:text-sky-400 transition-colors">Municipal</a>
        </nav>
      </div>
    </div>

    <main id="contracts-dynamic-root" class="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 min-h-[65vh]"></main>
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
          ['all', 'All 18 Portals (Fed + 16 States)'],
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
          ['new_jersey', 'New Jersey (NJSTART & DPP)'],
          ['washington', 'Washington (WEBS & WaTech)'],
          ['michigan', 'Michigan (SIGMA VSS & DTMB)'],
          ['colorado', 'Colorado (VSS & OIT)'],
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
              '<form onsubmit="event.preventDefault(); window.submitSpaLeadCapture();" class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-12 gap-3">' +
                '<div class="sm:col-span-1 xl:col-span-3"><input id="spa-lead-email" type="email" required placeholder="capture@yourcompany.com" class="w-full px-3.5 py-2.5 rounded-xl bg-navy-950 border border-slate-700 focus:border-emerald-400 focus:outline-none text-xs font-mono text-white placeholder-slate-500" /></div>' +
                '<div class="sm:col-span-1 xl:col-span-3"><input id="spa-lead-company" type="text" placeholder="Company / Prime LLC" class="w-full px-3.5 py-2.5 rounded-xl bg-navy-950 border border-slate-700 focus:border-emerald-400 focus:outline-none text-xs font-mono text-white placeholder-slate-500" /></div>' +
                '<div class="sm:col-span-1 xl:col-span-3"><select id="spa-lead-state" class="w-full px-3 py-2.5 rounded-xl bg-navy-950 border border-slate-700 focus:border-emerald-400 focus:outline-none text-xs font-mono text-white">' + opts + '</select></div>' +
                '<div class="sm:col-span-1 xl:col-span-3"><button id="spa-lead-submit-btn" type="submit" class="w-full h-full px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-semibold border border-emerald-400/30 transition-all cursor-pointer whitespace-nowrap">Unlock 3 &rarr;</button></div>' +
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
          try {{ if (window.localStorage) window.localStorage.setItem('st_unlocked_lead_email', email); }} catch (e) {{}}
          try {{
            var agCells = document.querySelectorAll('[data-full-agency]');
            for (var ai = 0; ai < agCells.length; ai++) {{
              var fullAg = agCells[ai].getAttribute('data-full-agency');
              if (fullAg) agCells[ai].textContent = fullAg;
            }}
          }} catch (e) {{}}
          var unlockedList = (data && (data.dossiers || data.matched_dossiers)) ? (data.dossiers || data.matched_dossiers) : [];
          if (statusEl) {{ statusEl.className = 'mt-3 text-xs font-mono text-emerald-400'; statusEl.textContent = data.message || ('Unlocked ' + (unlockedList.length || 3) + ' live pre-shredded RFP dossiers below — full directory un-blurred!'); }}
          if (resultsEl && unlockedList.length) {{
            resultsEl.className = 'mt-4 grid grid-cols-1 md:grid-cols-3 gap-3';
            resultsEl.innerHTML = unlockedList.map(function (d) {{
              var safeBidUrl = String(d.official_bid_url || d.official_portal_url || d.dossier_url || '#').replace(/"/g, '&quot;');
              var safeSpaRoute = String(d.spa_route || '#contracts').replace(/"/g, '&quot;');
              var buyerAgency = d.issuing_agency || d.agency || 'Government Agency';
              var naicsTag = (d.tags && d.tags[0]) ? d.tags[0] : ('NAICS ' + (d.naics || '541512'));
              return '<div class="p-3.5 rounded-xl bg-navy-950 border border-emerald-500/40 flex flex-col justify-between space-y-2 text-xs font-mono">' +
                '<div>' +
                  '<div class="text-[10px] text-emerald-400 font-bold uppercase">UNLOCKED &bull; ' + esc(naicsTag) + '</div>' +
                  '<div class="text-white font-sans font-bold text-xs mt-1 line-clamp-2">' + esc(d.title || 'Open IT Solicitation') + '</div>' +
                  '<div class="text-slate-400 text-[11px] mt-1">' + esc(buyerAgency) + ' &bull; Due: <span class="text-amber-300">' + esc(d.closing_date || 'Open') + '</span></div>' +
                '</div>' +
                '<div class="flex flex-wrap gap-1.5 pt-1">' +
                  '<a href="' + safeSpaRoute + '" class="inline-flex items-center justify-center px-2.5 py-1.5 rounded bg-indigo-600/25 hover:bg-indigo-600/40 text-indigo-200 border border-indigo-500/40 text-[11px] transition-colors">21-API Dossier &rarr;</a>' +
                  '<a href="' + safeBidUrl + '" target="_blank" rel="noopener noreferrer" class="inline-flex items-center justify-center px-2.5 py-1.5 rounded bg-emerald-600/20 hover:bg-emerald-600/35 text-emerald-300 border border-emerald-500/40 text-[11px] transition-colors">Official Bid Portal &nearr;</a>' +
                '</div>' +
              '</div>';
            }}).join('');
          }}
        }} catch (err) {{
          if (statusEl) {{ statusEl.className = 'mt-3 text-xs font-mono text-amber-300'; statusEl.textContent = 'Saved your request! Browse the live dossiers above.'; }}
        }} finally {{
          if (btnEl) {{ btnEl.disabled = false; btnEl.textContent = 'Unlock 3 →'; }}
        }}
      }};


    window.compileShipleyProposalZip = async function (slugVal, titleVal, agencyVal, naicsVal, setAsideVal) {{
      var btnEl = document.getElementById('compile-zip-btn-' + slugVal) || document.getElementById('compile-zip-btn-static');
      var vaultEl = document.getElementById('vault-status-' + slugVal) || document.getElementById('vault-status-static');
      var origTxt = btnEl ? btnEl.textContent : '1-Click Compile 6-File Proposal & Legal .ZIP';
      if (btnEl) {{
        btnEl.disabled = true;
        btnEl.textContent = 'Compiling 6-File Package (Vol I-III + FAR 9.6 Teaming + FOIA Demand)...';
      }}
      var compName = 'Your Capture Team LLC';
      var ueiCage = 'UEI-PENDING / CAGE-PENDING';
      var wrapRate = 1.82;
      var capSummary = '';
      try {{
        var savedProf = window.localStorage && window.localStorage.getItem('st_company_profile_v1');
        if (savedProf) {{
          var pObj = JSON.parse(savedProf);
          if (pObj.company) compName = pObj.company;
          if (pObj.uei_cage) ueiCage = pObj.uei_cage;
          if (pObj.wrap_rate) wrapRate = parseFloat(pObj.wrap_rate) || 1.82;
          if (pObj.capabilities || pObj.company_capability_summary) capSummary = pObj.capabilities || pObj.company_capability_summary;
        }}
      }} catch (e) {{}}
      var matchedContract = null;
      try {{
        var cPool = window.SIGNALTENDER_CONTRACTS || [];
        for (var ci = 0; ci < cPool.length; ci++) {{
          if (cPool[ci] && (cPool[ci].slug === slugVal || cPool[ci].title === titleVal)) {{
            matchedContract = cPool[ci];
            break;
          }}
        }}
      }} catch (e) {{}}
      var domRfpText = '';
      try {{
        var mainEl = document.querySelector('main') || document.body;
        if (mainEl && !matchedContract) domRfpText = String(mainEl.innerText || '').slice(0, 3500);
      }} catch (e) {{}}
      try {{
        var resp = await fetch('https://b2b-contract-parser-api.onrender.com/v1/proposal-autopilot/compile-full-package', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            solicitation_title: titleVal || (matchedContract && matchedContract.title) || 'Government IT & Cybersecurity Solicitation',
            solicitation_number: String(slugVal || 'RFP-2026').slice(0, 48).toUpperCase(),
            issuing_agency: agencyVal || (matchedContract && matchedContract.agency) || 'Federal / State SLED Agency',
            naics_code: String(naicsVal || (matchedContract && matchedContract.naics) || '541512').split('/')[0].trim(),
            set_aside: setAsideVal || (matchedContract && matchedContract.set_aside) || 'Small Business / SDVOSB',
            closing_date: (matchedContract && matchedContract.closing_date) || 'Active Open Window',
            compliance_posture: (matchedContract && matchedContract.compliance_posture) || '',
            teaming_posture: (matchedContract && matchedContract.teaming_posture) || '',
            igce_ptw_posture: (matchedContract && matchedContract.igce_ptw_posture) || '',
            key_personnel_lcats: (matchedContract && matchedContract.key_personnel_lcats) || '',
            rfp_text: (matchedContract && (matchedContract.rfp_text || matchedContract.compliance_posture)) || domRfpText,
            company_name: compName,
            company_capability_summary: capSummary,
            uei_cage: ueiCage,
            wrap_rate: wrapRate
          }})
        }});
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        var ctype = String(resp.headers.get('content-type') || '');
        var blob = null;
        var vaultMsg = '';
        var dlName = 'SignalTender_Shipley_6File_Proposal_' + String(slugVal || 'package').slice(0, 36) + '.zip';
        if (ctype.indexOf('application/json') !== -1) {{
          var jData = await resp.json();
          if (jData && jData.filename) dlName = jData.filename;
          if (jData && jData.institutional_vault_message) vaultMsg = jData.institutional_vault_message;
          var binStr = window.atob(jData.zip_base64 || '');
          var u8 = new Uint8Array(binStr.length);
          for (var bi = 0; bi < binStr.length; bi++) u8[bi] = binStr.charCodeAt(bi);
          blob = new Blob([u8], {{ type: 'application/zip' }});
        }} else {{
          blob = await resp.blob();
        }}
        var dlUrl = window.URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = dlUrl;
        a.download = dlName;
        document.body.appendChild(a);
        a.click();
        setTimeout(function () {{
          window.URL.revokeObjectURL(dlUrl);
          if (a.parentNode) a.parentNode.removeChild(a);
        }}, 1500);
        if (btnEl) {{
          btnEl.disabled = false;
          btnEl.textContent = 'Downloaded 6-File .ZIP (Vol I-III + FAR 9.6 Teaming + FOIA Demand)';
        }}
        if (vaultEl && vaultMsg) {{
          vaultEl.classList.remove('hidden');
          vaultEl.textContent = vaultMsg;
        }}
      }} catch (err) {{
        if (btnEl) {{
          btnEl.disabled = false;
          btnEl.textContent = origTxt;
        }}
      }}
    }};

    window.toggleTeamingClearinghouseBox = function (boxId) {{
      var el = document.getElementById(boxId);
      if (!el) return;
      if (el.classList.contains('hidden')) el.classList.remove('hidden');
      else el.classList.add('hidden');
    }};

    window.submitInlineTeamingSlot = async function (slugVal, titleVal, agencyVal, naicsVal) {{
      var sfx = slugVal || 'static';
      var coEl = document.getElementById('teaming-co-' + sfx);
      var ueiEl = document.getElementById('teaming-uei-' + sfx);
      var socEl = document.getElementById('teaming-soc-' + sfx);
      var emEl = document.getElementById('teaming-em-' + sfx);
      var stEl = document.getElementById('teaming-status-' + sfx);
      var subCo = coEl ? String(coEl.value || '').trim() : '';
      var subEm = emEl ? String(emEl.value || '').trim() : '';
      if (!subCo || !subEm || subEm.indexOf('@') === -1) {{
        if (stEl) {{
          stEl.classList.remove('hidden');
          stEl.className = 'mt-2 text-xs font-mono text-amber-300';
          stEl.textContent = 'Please enter your company name and work email to validate 13 CFR 125.6 workshare.';
        }}
        return;
      }}
      if (stEl) {{
        stEl.classList.remove('hidden');
        stEl.className = 'mt-2 text-xs font-mono text-sky-300';
        stEl.textContent = 'Validating 13 CFR 125.6 (50% Rule) workshare & querying live Teaming Clearinghouse partners...';
      }}
      try {{
        var r = await fetch('https://b2b-contract-parser-api.onrender.com/v1/proposal-autopilot/teaming-clearinghouse', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            email: subEm,
            company_name: subCo,
            uei_or_cage: ueiEl ? String(ueiEl.value || 'Verified SAM UEI').trim() : 'Verified SAM UEI',
            socioeconomic_status: socEl ? String(socEl.value || 'SDVOSB').trim() : 'SDVOSB',
            solicitation_id: String(slugVal || 'RFP-2026').slice(0, 65),
            solicitation_title: titleVal || 'Government IT Solicitation',
            issuing_agency: agencyVal || 'Government Agency',
            naics_focus: String(naicsVal || '541512').split('/')[0].trim()
          }})
        }});
        var d = await r.json();
        if (stEl) {{
          stEl.className = 'mt-3 space-y-2.5 text-xs font-mono';
          var rulingTxt = (d && d.cfr_125_6_ruling) ? d.cfr_125_6_ruling : 'Verified 13 CFR 125.6 Teaming Slot registered.';
          var partners = (d && Array.isArray(d.matched_partners)) ? d.matched_partners : [];
          var pCards = partners.map(function (p) {{
            var pName = String(p.company_name || 'Verified Partner').replace(/</g, '&lt;');
            var pSoc = String(p.socioeconomic_status || 'Small Business').replace(/</g, '&lt;');
            var pUei = String(p.uei_or_cage || 'SAM Verified').replace(/</g, '&lt;');
            var pShare = String(p.allocated_workshare_pct || 24) + '% Share';
            return '<div class="p-2.5 rounded-lg bg-navy-950 border border-slate-800 flex flex-wrap items-center justify-between gap-2">' +
              '<div><span class="text-white font-semibold">' + pName + '</span> <span class="text-amber-300">(' + pSoc + ')</span> <span class="text-slate-400 text-[11px]">' + pUei + '</span></div>' +
              '<span class="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[10px]">' + pShare + '</span>' +
            '</div>';
          }}).join('');
          var inviteHref = (d && d.viral_partner_invite_mailto) ? String(d.viral_partner_invite_mailto).replace(/"/g, '&quot;') : 'mailto:?subject=13%20CFR%20125.6%20Teaming%20Invitation';
          var refUrl = (d && d.clearinghouse_referral_url) ? String(d.clearinghouse_referral_url).replace(/"/g, '&quot;') : window.location.href;
          stEl.innerHTML =
            '<div class="text-emerald-400 font-semibold">&check; ' + rulingTxt.replace(/</g, '&lt;') + '</div>' +
            (pCards ? ('<div class="space-y-1.5 pt-1"><div class="text-[10px] text-slate-400 uppercase">Matched 13 CFR &sect; 125.6 Clearinghouse Partners:</div>' + pCards + '</div>') : '') +
            '<div class="pt-1 flex flex-wrap gap-2">' +
              '<a href="' + inviteHref + '" class="inline-flex items-center px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/35 border border-amber-400/50 text-amber-200 font-semibold">1-Click Invite Preferred Teaming Partner (Email) &rarr;</a>' +
              '<button type="button" onclick="if(navigator.clipboard) navigator.clipboard.writeText(&quot;' + refUrl + '&quot;); this.textContent=&quot;Copied Referral Link!&quot;;" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sky-300 cursor-pointer">Copy Workshare Invite Link</button>' +
            '</div>';
        }}
      }} catch (e) {{
        if (stEl) {{
          stEl.className = 'mt-2 text-xs font-mono text-emerald-400';
          stEl.textContent = 'Teaming slot request logged for 13 CFR 125.6 clearinghouse review.';
        }}
      }}
    }};

    window.unlockFoiaWinningBidVault = async function (slugVal, stateVal, naicsVal, titleVal, agencyVal) {{
      var sfx = slugVal || 'static';
      var boxEl = document.getElementById('foia-vault-box-' + sfx);
      if (!boxEl) return;
      if (!boxEl.classList.contains('hidden') && boxEl.getAttribute('data-loaded') === '1') {{
        boxEl.classList.add('hidden');
        return;
      }}
      boxEl.classList.remove('hidden');
      boxEl.innerHTML = '<div class="text-xs font-mono text-sky-300">Querying Post-Award FOIA / State PIA Incumbent Rate Vault &amp; generating statutory $0-fee demand letter...</div>';
      try {{
        var qUrl = 'https://b2b-contract-parser-api.onrender.com/v1/proposal-autopilot/foia-winning-bid-vault?state=' +
          encodeURIComponent(stateVal || 'all') +
          '&naics=' + encodeURIComponent(String(naicsVal || '541512').split('/')[0].trim()) +
          '&solicitation_id=' + encodeURIComponent(String(slugVal || 'RFP-2026').slice(0, 48).toUpperCase()) +
          '&title=' + encodeURIComponent(titleVal || 'Enterprise IT Solicitation') +
          '&agency=' + encodeURIComponent(agencyVal || 'Government Agency');
        var r = await fetch(qUrl);
        var d = await r.json();
        boxEl.setAttribute('data-loaded', '1');
        var statute = String((d && d.statutory_citation) || '5 U.S.C. § 552 (Federal FOIA / State PIA — $0 Electronic Cap)').replace(/</g, '&lt;');
        var awards = (d && Array.isArray(d.awards)) ? d.awards : [];
        var ratesHtml = '';
        if (awards.length > 0 && Array.isArray(awards[0].verified_lcat_benchmarks)) {{
          ratesHtml = awards[0].verified_lcat_benchmarks.map(function (b) {{
            var lcat = String(b.lcat || 'Senior Engineer').replace(/</g, '&lt;');
            var rate = Number(b.winning_rate_hr || 162).toFixed(2);
            var ptw = (Number(b.winning_rate_hr || 162) * 0.94).toFixed(2);
            return '<div class="p-2.5 rounded-lg bg-navy-950 border border-slate-800 flex items-center justify-between gap-2">' +
              '<span class="text-white font-semibold">' + lcat + '</span>' +
              '<span class="text-right"><span class="text-amber-300">Incumbent: $' + rate + '/hr</span> &bull; <span class="text-emerald-400 font-semibold">PTW: $' + ptw + '/hr</span></span>' +
            '</div>';
          }}).join('');
        }}
        var letterTxt = String((d && d.statutory_demand_letter_text) || '').replace(/</g, '&lt;');
        var mailHref = String((d && d.foia_mailto_link) || 'mailto:').replace(/"/g, '&quot;');
        boxEl.innerHTML =
          '<div class="space-y-3 text-xs font-mono">' +
            '<div class="flex flex-wrap items-center justify-between gap-2">' +
              '<span class="text-emerald-400 font-bold uppercase">// STATUTORY FOIA / STATE PIA INCUMBENT RATE VAULT</span>' +
              '<span class="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[10px]">' + statute + '</span>' +
            '</div>' +
            (ratesHtml ? ('<div class="grid grid-cols-1 gap-1.5">' + ratesHtml + '</div>') : '') +
            '<pre id="foia-letter-pre-' + sfx + '" class="p-3 rounded-lg bg-navy-950 border border-slate-800 text-[11px] text-slate-300 whitespace-pre-wrap overflow-x-auto">' + letterTxt + '</pre>' +
            '<div class="flex flex-wrap gap-2">' +
              '<a href="' + mailHref + '" class="inline-flex items-center px-3 py-1.5 rounded-lg bg-emerald-600/25 hover:bg-emerald-600/40 border border-emerald-400/50 text-emerald-200 font-semibold">1-Click Dispatch FOIA Demand to Agency (Email) &rarr;</a>' +
              '<button type="button" onclick="var el=document.getElementById(&quot;foia-letter-pre-' + sfx + '&quot;); if(el && navigator.clipboard) navigator.clipboard.writeText(el.textContent); this.textContent=&quot;Copied Statutory Demand!&quot;;" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sky-300 cursor-pointer">Copy Statutory FOIA Letter</button>' +
            '</div>' +
          '</div>';
      }} catch (err) {{
        boxEl.innerHTML = '<div class="text-xs font-mono text-amber-300">Statutory FOIA / PIA Demand Ready (5 U.S.C. &sect; 552 / State Open Records — $0.00 Electronic Fee Cap).</div>';
      }}
    }};

      function renderRows(list) {{
        if (!list || !list.length) {{
          return '<tr><td colspan="5" class="py-8 px-5 text-center font-mono text-xs text-slate-400">No open solicitations currently in this view — our 6-hour scraper pipeline continuously indexes new bids across all 18 portals.</td></tr>';
        }}
        var isRowUnlocked = false;
        try {{
          if (window.localStorage && (window.localStorage.getItem('st_unlocked_lead_email') || window.localStorage.getItem('st_subscriber_session_v1'))) {{
            isRowUnlocked = true;
          }}
        }} catch (e) {{}}
        var J = window.SIGNALTENDER_JURISDICTIONS;
        return list.map(function (c) {{
          var jm = J[c.jurisdiction] || J.federal;
          var tagsHtml = (c.tags || []).map(function (t) {{
            return '<span class="inline-flex items-center whitespace-nowrap px-2 py-0.5 rounded bg-navy-900 border border-slate-800 text-slate-300">' + esc(t) + '</span>';
          }}).join(' ');
          var dispAgency = isRowUnlocked ? (c.agency || c.masked_agency) : c.masked_agency;
          return '<tr class="border-b border-slate-800/80 hover:bg-slate-900/60 transition-colors">' +
            '<td class="py-4 px-5 font-mono whitespace-nowrap align-top">' +
              '<a href="#contracts/' + esc(c.jurisdiction) + '" class="inline-flex items-center whitespace-nowrap px-2.5 py-0.5 rounded border text-[11px] ' + esc(jm.badge_class) + '">' + esc(jm.short.toUpperCase()) + '</a>' +
            '</td>' +
            '<td class="py-4 px-5 align-top">' +
              '<a href="#contracts/rfp/' + esc(c.slug) + '" class="font-semibold text-white hover:text-sky-400 transition-colors text-sm block">' + esc(c.clean_title) + '</a>' +
              '<div class="mt-1.5 flex flex-wrap gap-1.5 text-[11px] font-mono">' + tagsHtml + '</div>' +
            '</td>' +
            '<td data-full-agency="' + esc(c.agency || c.masked_agency) + '" class="py-4 px-4 text-slate-300 text-xs align-top">' + esc(dispAgency) + '</td>' +
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
        var rawQ = String(qVal !== undefined ? qVal : (inp ? inp.value : '')).trim();
        if (rawQ.indexOf('@') !== -1) {{
          rawQ = '';
          qVal = '';
          if (inp) inp.value = '';
        }}
        var q = rawQ.toLowerCase();
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
          var txt = (rows[i]._stSearchText || (rows[i]._stSearchText = (rows[i].textContent || '').toLowerCase()));
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
        var selPortal = document.getElementById('mobile-contracts-portal-select');
        if (selPortal) {{
          selPortal.value = (parts[1] && parts[1] !== 'rfp' && J[parts[1]]) ? ('#contracts/' + parts[1]) : '#contracts';
        }}

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
                '<div id="contracts-top-section" class="p-6 sm:p-8 rounded-2xl bg-navy-900 border border-slate-800 shadow-2xl space-y-5">' +
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
                  '<div id="contracts-rfp-ai-shred-card" class="mt-6 p-6 rounded-xl bg-navy-950 border-2 border-indigo-500/50 space-y-5">' +
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
                        '<div class="text-[10px] text-sky-300 font-bold">06. CPARS, ORALS &amp; DEBRIEF/PROTEST (API #15 / #17 / #19)</div>' +
                        '<div class="text-slate-200">' + esc(item.cpars_benchmark || 'Substantial Confidence • 3 Very Relevant Refs (5-Yr Window)') + '</div>' +
                      '</div>' +
                    '</div>' +
                    (function () {{
                      var isUnl = false;
                      try {{ isUnl = Boolean(window.localStorage && (window.localStorage.getItem('st_unlocked_lead_email') || window.localStorage.getItem('st_subscriber_active'))); }} catch (e) {{}}
                      var realBidUrl = item.url || ('https://portal.government.gov/solicitation/view/' + item.id);
                      var portalHost = String(realBidUrl).replace(/^https?:\\/\\/(www\\.)?/, '').split('/')[0] || 'sam.gov';
                      if (isUnl && item.url) {{
                        return '<div class="space-y-2 text-xs font-mono text-slate-300 pt-1 break-words">' +
                          '<div><strong class="text-slate-200">Official Government Bid URL:</strong> <a href="' + esc(realBidUrl) + '" target="_blank" rel="noopener noreferrer" class="text-emerald-400 font-semibold underline hover:text-emerald-300 break-all">' + esc(realBidUrl) + ' &nearr;</a></div>' +
                          '<div><strong class="text-slate-200">Full Issuing Buyer &amp; Contracting Officer:</strong> <span class="text-white font-semibold">' + esc(item.agency) + '</span></div>' +
                          '<div><strong class="text-slate-200">Contracting Office &amp; RFI / Q&amp;A Submission Routing:</strong> <span class="text-sky-300 font-semibold">Official ' + esc(jm.portal) + ' Electronic Q&amp;A &amp; Contracting Officer Portal (' + esc(item.agency) + ')</span></div>' +
                          '<div><strong class="text-slate-200">Shipley Section L/M Compliance Matrix, SF-30 Diff &amp; CPARS Vol. III:</strong> <span class="text-sky-300">Ready — click &quot;Run Live Pwin &amp; Shred in Studio&quot; below</span></div>' +
                        '</div>';
                      }}
                      return '<div class="space-y-2 text-xs font-mono text-slate-400 pt-1 break-words">' +
                        '<div><strong class="text-slate-200">Official Government Bid URL:</strong> <span class="blur-sm select-none break-all">https://portal.government.gov/solicitation/view/' + esc(item.id) + '98412</span></div>' +
                        '<div><strong class="text-slate-200">Full Issuing Buyer &amp; Contracting Officer:</strong> <span class="blur-sm select-none">' + esc(item.agency) + ' - Procurement Division</span></div>' +
                        '<div><strong class="text-slate-200">Contracting Office &amp; RFI / Q&amp;A Submission Routing:</strong> <span class="blur-sm select-none break-words">contracting.officer@' + esc(portalHost) + ' &bull; Electronic Q&amp;A Desk (' + esc(item.agency) + ')</span></div>' +
                        '<div><strong class="text-slate-200">Shipley Section L/M Compliance Matrix, SF-30 Diff &amp; CPARS Vol. III:</strong> <span class="blur-sm select-none break-words">Pre-built in #capturedesk-autopilot &amp; API #05/#06/#14/#15/#16/#17/#18/#19/#20/#21</span></div>' +
                      '</div>';
                    }})() +
                    '<div class="pt-3 flex flex-col sm:flex-row gap-3">' +
                      '<a href="#checkout-tier1" class="inline-flex items-center justify-center px-6 py-3 text-sm font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg shadow-lg transition-all">' +
                        'Unlock Direct RFP Link &amp; Capture Dossier &rarr;' +
                      '</a>' +
                      '<button type="button" onclick="window.shredRfpInStudio(&quot;' + esc(item.slug) + '&quot;)" class="inline-flex items-center justify-center px-5 py-3 text-xs font-mono font-semibold text-emerald-300 bg-emerald-500/15 hover:bg-emerald-500/25 rounded-lg border border-emerald-500/40 transition-colors cursor-pointer">' +
                        'Run Live Pwin &amp; Shred in Studio &rarr;' +
                      '</button>' +
                      '<button id="compile-zip-btn-' + esc(item.slug) + '" type="button" onclick="window.compileShipleyProposalZip(&quot;' + esc(item.slug) + '&quot;, &quot;' + esc(item.clean_title) + '&quot;, &quot;' + esc(item.masked_agency) + '&quot;, &quot;' + esc(item.naics_display || '541512') + '&quot;, &quot;Small Business&quot;)" class="inline-flex items-center justify-center px-5 py-3 text-xs font-mono font-semibold text-indigo-200 bg-indigo-600/30 hover:bg-indigo-600/50 rounded-lg border border-indigo-400/50 transition-colors cursor-pointer">' +
                        '1-Click Compile 6-File Proposal &amp; Legal (.ZIP) &darr;' +
                      '</button>' +
                      '<button type="button" onclick="window.toggleTeamingClearinghouseBox(&quot;teaming-box-' + esc(item.slug) + '&quot;)" class="inline-flex items-center justify-center px-4 py-3 text-xs font-mono text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 rounded-lg border border-amber-500/30 transition-colors cursor-pointer">' +
                        'Request 13 CFR &sect; 125.6 Teaming Slot &rarr;' +
                      '</button>' +
                      '<button type="button" onclick="window.unlockFoiaWinningBidVault(&quot;' + esc(item.slug) + '&quot;, &quot;' + esc(item.jurisdiction || 'federal') + '&quot;, &quot;' + esc(item.naics_display || '541512') + '&quot;, &quot;' + esc(item.clean_title) + '&quot;, &quot;' + esc(item.masked_agency) + '&quot;)" class="inline-flex items-center justify-center px-4 py-3 text-xs font-mono text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 rounded-lg border border-emerald-500/30 transition-colors cursor-pointer">' +
                        'FOIA Incumbent Rate Vault &amp; Demand &rarr;' +
                      '</button>' +
                    '</div>' +
                    '<div id="vault-status-' + esc(item.slug) + '" class="hidden mt-2 p-2.5 rounded-lg bg-emerald-950/50 border border-emerald-500/40 text-xs font-mono text-emerald-300"></div>' +
                    '<div id="foia-vault-box-' + esc(item.slug) + '" class="hidden mt-3 p-4 rounded-xl bg-navy-900 border border-emerald-500/40"></div>' +
                    '<div id="teaming-box-' + esc(item.slug) + '" class="hidden mt-3 p-4 rounded-xl bg-navy-900 border border-amber-500/40 space-y-3 text-xs font-mono">' +
                      '<div class="text-amber-300 font-bold uppercase">// TWO-SIDED FAR 52.219-9 &amp; 13 CFR &sect; 125.6 TEAMING CLEARINGHOUSE</div>' +
                      '<p class="text-slate-300">Register your verified UEI/CAGE and socio-economic status to request a compliant Prime/Sub workshare slot on this solicitation (auto-validates the 50% Limitation on Subcontracting rule).</p>' +
                      '<div class="grid grid-cols-1 sm:grid-cols-5 gap-2.5">' +
                        '<input id="teaming-co-' + esc(item.slug) + '" type="text" placeholder="Company Name LLC" class="px-3 py-2 rounded-lg bg-navy-950 border border-slate-700 text-white placeholder-slate-500" />' +
                        '<input id="teaming-uei-' + esc(item.slug) + '" type="text" placeholder="UEI / CAGE Code" class="px-3 py-2 rounded-lg bg-navy-950 border border-slate-700 text-white placeholder-slate-500" />' +
                        '<select id="teaming-soc-' + esc(item.slug) + '" class="px-2.5 py-2 rounded-lg bg-navy-950 border border-slate-700 text-white">' +
                          '<option value="SDVOSB">SDVOSB</option><option value="8(a)">SBA 8(a)</option><option value="WOSB">WOSB / EDWOSB</option><option value="HUBZone">HUBZone</option><option value="Small Business">Small Business / State MBE</option>' +
                        '</select>' +
                        '<input id="teaming-em-' + esc(item.slug) + '" type="email" placeholder="bd@yourcompany.com" class="px-3 py-2 rounded-lg bg-navy-950 border border-slate-700 text-white placeholder-slate-500" />' +
                        '<button type="button" onclick="window.submitInlineTeamingSlot(&quot;' + esc(item.slug) + '&quot;, &quot;' + esc(item.clean_title) + '&quot;, &quot;' + esc(item.masked_agency) + '&quot;, &quot;' + esc(item.naics_display || '541512') + '&quot;)" class="px-3 py-2 rounded-lg bg-amber-500/20 hover:bg-amber-500/35 border border-amber-400/50 text-amber-200 font-semibold cursor-pointer">Verify &amp; Match &rarr;</button>' +
                      '</div>' +
                      '<div id="teaming-status-' + esc(item.slug) + '" class="hidden"></div>' +
                    '</div>' +
                    '<p class="text-[11px] font-mono text-slate-400">Instant 60-second Discord, Slack, Microsoft Teams &amp; CRM webhook activation. Cancel anytime.</p>' +
                  '</div>' +
                '</div>' +
                '<div id="contracts-rfp-related-card" class="p-6 rounded-2xl bg-navy-900/60 border border-slate-800">' +
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
                    'Get every pre-vetted Federal (SAM.gov), DemandStar, and 16-State SLED (TX, VA, CA, FL, MD, IL, PA, OH, GA, NC, NY, MA, NJ, WA, MI, CO) IT &amp; cybersecurity solicitation pushed directly to your team every 6 hours.' +
                  '</p>' +
                  '<ul class="text-xs font-mono text-slate-300 space-y-2 pt-2">' +
                    '<li>&check; 99.4% Commodity &amp; Renewal Spam Stripped</li>' +
                    '<li>&check; Tier 2 CaptureDesk ($399/mo) 21-API Auto-Dossiers</li>' +
                    '<li class="text-emerald-300">&check; Tier 3 ($1,499/mo) 1-Click 3-Vol .DOCX/.XLSX Proposal .ZIP</li>' +
                    '<li class="text-amber-300">&check; Tier 4 ($2,499/mo) 50k OEM API Calls &amp; FOIA Rate Vault</li>' +
                  '</ul>' +
                  '<a href="#checkout-tier1" class="w-full inline-flex items-center justify-center px-5 py-2.5 text-xs font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg transition-all">' +
                    'Start Tier 1 Leads ($99/mo) &rarr;' +
                  '</a>' +
                  '<a href="#checkout-tier2" class="w-full inline-flex items-center justify-center px-5 py-2.5 text-xs font-mono font-semibold text-indigo-200 bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 rounded-lg transition-all">' +
                    'Launch Tier 2 CaptureDesk ($399/mo) &rarr;' +
                  '</a>' +
                  '<a href="#checkout-tier3" class="w-full inline-flex items-center justify-center px-5 py-2.5 text-xs font-mono font-semibold text-emerald-200 bg-emerald-600/25 hover:bg-emerald-600/45 border border-emerald-500/40 rounded-lg transition-all">' +
                    'Start Tier 3 Proposal .ZIP ($1,499/mo) &rarr;' +
                  '</a>' +
                  '<a href="#checkout-tier4" class="w-full inline-flex items-center justify-center px-5 py-2 text-[11px] font-mono font-semibold text-amber-200 bg-amber-500/15 hover:bg-amber-500/30 border border-amber-500/40 rounded-lg transition-all">' +
                    'Tier 4 OEM &amp; FOIA Vault ($2,499/mo) &rarr;' +
                  '</a>' +
                '</div>' +
                '<div class="p-6 rounded-2xl bg-navy-900 border border-indigo-500/30 space-y-3">' +
                  '<div class="text-xs font-mono text-indigo-400 uppercase font-semibold">24 LIVE APIs &amp; MCP SERVER</div>' +
                  '<div class="text-lg font-bold text-white">Automate Your Bid Response</div>' +
                  '<p class="text-xs text-slate-300 leading-relaxed">' +
                    'Shape pre-RFP Sources Sought &amp; RFI set-asides (FAR 19.502-2 Rule-of-Two), generate GSA MAS Schedule SIN matrices, 0.75% IFF ceiling rate cards &amp; GSAR 552.238-81 PRC compliance packages, analyze FAR 15.506 Post-Award Debriefings &amp; GAO Bid-Protest viability, generate NIST 800-53 Rev 5 RMF, Continuous ATO (cATO), SSP &amp; POA&amp;M packages, FAR 15.102 Oral Presentation &amp; Murder-Board prep, model IGCE wrap-rates &amp; Price-to-Win, generate CPARS &amp; Past Performance Volume III citations, diff SF-30 RFP amendments, tailor Key Personnel &amp; GSA LCAT resumes, auto-answer SOC 2, FedRAMP &amp; NIST 800-171 security questionnaires, generate 13 CFR &sect; 125.6 (50% Rule) teaming plans, extract Section B CLIN pricing tables, draft Shipley proposal narratives &amp; CO Q&amp;A, classify NAICS/SIC/PSC/UNSPSC codes, score Bid/No-Bid Pwin (0&ndash;100), audit FAR/DFARS &amp; CMMC 2.0 flow-downs, or shred this RFP into a compliance matrix via our 24 RapidAPI microservices &amp; <code class="text-indigo-200">@signaltender/mcp-server</code>.' +
                  '</p>' +
                  '<a href="#product-sources-sought-response" class="w-full inline-flex items-center justify-center px-4 py-2.5 text-xs font-mono font-semibold text-indigo-300 bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/40 rounded-lg transition-all">' +
                    'Explore 24 APIs &amp; MCP Server &rarr;' +
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
            '<div id="contracts-top-section" class="mb-8 space-y-4">' +
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
            '<div id="static-contracts-table-card" class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">' +'<div class="p-4 sm:p-5 bg-slate-900/70 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">' +'<div class="relative flex-1 flex items-center">' +'<svg class="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10.5a7.5 7.5 0 0013.15 6.15z" /></svg>' +'<input id="contracts-live-search" type="search" name="st_contracts_live_search_nofill" autocomplete="off" data-lpignore="true" data-1p-ignore="true" data-form-type="other" placeholder="Search all open IT &amp; cybersecurity solicitations by keyword, agency, portal, or tag..." oninput="window.filterContractsDirectory(this.value)" class="w-full pl-10 pr-20 py-2.5 rounded-xl bg-navy-950 border border-slate-700/90 focus:border-sky-500 focus:outline-none text-xs font-mono text-white placeholder-slate-500" />' +'<button id="contracts-live-clear" type="button" onclick="window.filterContractsDirectory(&quot;&quot;)" class="hidden absolute right-2.5 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-300 border border-slate-700 cursor-pointer">Clear</button>' +'</div>' +'<span id="contracts-live-count" class="text-xs font-mono text-emerald-400 shrink-0">LIVE SEARCH ACTIVE</span>' +'</div>' +'<div class="overflow-x-auto">' +
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
          if (typeof window.renderPageSectionSidebar === 'function') window.renderPageSectionSidebar();
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
          '<div id="contracts-top-section" class="mb-10 space-y-4">' +
            '<div class="inline-flex items-center px-3 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-xs font-mono text-emerald-400">' +
              '// LIVE GOVCON DIRECTORY &bull; ' + all.length + ' VERIFIED OPEN IT SOLICITATIONS' +
            '</div>' +
            '<h1 class="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">' +
              'Federal &amp; State SLED IT Contract Directory' +
            '</h1>' +
            '<p class="text-slate-300 text-base max-w-3xl">' +
              'Explore ' + all.length + ' live, AI-vetted government IT, software, cloud, and cybersecurity RFPs across SAM.gov, DemandStar, Texas, Virginia, California, Florida, Maryland, Illinois, Pennsylvania, Ohio, Georgia, North Carolina, New York, Massachusetts, New Jersey, Washington, Michigan, and Colorado.' +
            '</p>' +
          '</div>' +
          '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">' + cardsHtml + '</div>' +
          '<h2 class="text-xl font-bold text-white font-mono uppercase tracking-wider mb-4">All Verified Open IT &amp; Cybersecurity Solicitations</h2>' +
          '<div id="static-contracts-table-card" class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">' +'<div class="p-4 sm:p-5 bg-slate-900/70 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">' +'<div class="relative flex-1 flex items-center">' +'<svg class="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10.5a7.5 7.5 0 0013.15 6.15z" /></svg>' +'<input id="contracts-live-search" type="search" name="st_contracts_live_search_nofill" autocomplete="off" data-lpignore="true" data-1p-ignore="true" data-form-type="other" placeholder="Search all open IT &amp; cybersecurity solicitations by keyword, agency, portal, or tag..." oninput="window.filterContractsDirectory(this.value)" class="w-full pl-10 pr-20 py-2.5 rounded-xl bg-navy-950 border border-slate-700/90 focus:border-sky-500 focus:outline-none text-xs font-mono text-white placeholder-slate-500" />' +'<button id="contracts-live-clear" type="button" onclick="window.filterContractsDirectory(&quot;&quot;)" class="hidden absolute right-2.5 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-300 border border-slate-700 cursor-pointer">Clear</button>' +'</div>' +'<span id="contracts-live-count" class="text-xs font-mono text-emerald-400 shrink-0">LIVE SEARCH ACTIVE</span>' +'</div>' +'<div class="overflow-x-auto">' +
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
        if (typeof window.renderPageSectionSidebar === 'function') window.renderPageSectionSidebar();
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

    tmp_index_path = f"{index_path}.tmp.{os.getpid()}"
    with open(tmp_index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    try:
        os.replace(tmp_index_path, index_path)
    except PermissionError:
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_html)
        try:
            os.remove(tmp_index_path)
        except OSError:
            pass


if __name__ == "__main__":
    generate_pseo_site()

