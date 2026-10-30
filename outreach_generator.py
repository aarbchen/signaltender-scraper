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
from urllib.parse import quote, quote_plus
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
    r"\bassorted\s+hardware\b",
    r"^\d{2}--",
    r"\baiphone\b",
    r"\bdc\s+and\s+ac\s+preferred\s+systems\b",
    r"\bmissile\s+warning\s+system\b",
    r"\bf-5\s+aircraft\s+award\b",
    r"sole\s*source",
    r"single\s*source",
    r"-ss-\d",
    r"\bss-\d",
    r"notice\s+of\s+intent",
    r"intent\s+to\s+award",
    r"sngl\s+board\s+computer",
    r"single\s+board\s+computer",
    r"computer\s+subassembl",
    r"server,\s*automatic\s*da",
    r"data\s+interface\s+unit",
    r"computer,\s*rackmount",
    r"synthetic\s+aperture\s+radar",
    r"\bdo\s+not\s+use\b",
    r"\btest\s+for\s+erp\b",
    r"state\s+pop\s+modernization",
    r"copiers?\s+lease",
    r"title:\s*line\s+",
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
    "ny": "ny", "new york": "ny", "new_york": "ny",
    "ma": "ma", "massachusetts": "ma",
    "nj": "nj", "new jersey": "nj", "new_jersey": "nj",
    "wa": "wa", "washington": "wa",
    "mi": "mi", "michigan": "mi",
    "co": "co", "colorado": "co",
    "az": "az", "arizona": "az",
    "mn": "mn", "minnesota": "mn",
    "tn": "tn", "tennessee": "tn",
    "in": "in", "indiana": "in",
    "mo": "mo", "missouri": "mo",
    "wi": "wi", "wisconsin": "wi",
    "sc": "sc", "south carolina": "sc", "south_carolina": "sc",
    "or": "or", "oregon": "or",
    "ct": "ct", "connecticut": "ct",
    "ut": "ut", "utah": "ut",
    "nv": "nv", "nevada": "nv",
    "al": "al", "alabama": "al",
    "la": "la", "louisiana": "la",
    "ky": "ky", "kentucky": "ky",
    "ok": "ok", "oklahoma": "ok",
}


def send_discord_alert(message: str):
    """Silently record runtime error to telemetry for autonomous self-healing (resolved-only Discord policy)."""
    report_error("outreach_generator.py", str(message))


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
    if "a856-cityrecord.nyc.gov" in url or "passport.cityofnewyork.us" in url or "panynj.bonfirehub.com" in url or "suffolkcountyny.bonfirehub.com" in url or "rocklandgov.bonfirehub.com" in url or "nyscr.ny.gov" in url or "ogs.ny.gov" in url:
        return "ny"
    if "commbuys.com" in url or "mass.gov" in url or "boston.gov" in url or "mbta.com" in url or "massport.com" in url or "masstech.org" in url:
        return "ma"
    if "njstart.gov" in url or "nj.gov" in url or "njtransit.com" in url or "rutgers.edu" in url:
        return "nj"
    if "pr-webs-vendor.des.wa.gov" in url or "des.wa.gov" in url or "watech.wa.gov" in url or "wsdot.wa.gov" in url or "hca.wa.gov" in url or "dshs.wa.gov" in url or "dol.wa.gov" in url or "wa.gov" in url:
        return "wa"
    if "sigma.michigan.gov" in url or "michigan.gov" in url:
        return "mi"
    if "colorado.gov" in url or "denvergov.org" in url or "coloradosprings.gov" in url or "cu.edu" in url:
        return "co"
    if ".az.gov" in url or "//az.gov" in url or "azdoa.gov" in url or "phoenix.gov" in url or "chandleraz.gov" in url or "tucsonaz.gov" in url or "maricopa.gov" in url:
        return "az"
    if "mn.gov" in url or "questcdn.com" in url or "metrocouncil.org" in url or "umn.edu" in url or "hennepin.us" in url or "minneapolismn.gov" in url or "stpaul.gov" in url:
        return "mn"
    if "tn.gov" in url or "tennessee.edu" in url or "utk.edu" in url or "tbr.edu" in url or "nashville.gov" in url or "memphistn.gov" in url or "shelbycountytn.gov" in url:
        return "tn"
    if "in.gov/idoa" in url or "iot.in.gov" in url or "fs.gmis.in.gov" in url or "in.gov" in url or "indy.gov" in url or "purdue.edu" in url or "indiana.edu" in url:
        return "in"
    if "missouribuys.mo.gov" in url or "oa.mo.gov" in url or "modot.org" in url or "mo.gov" in url or "stlouis-mo.gov" in url or "kcmo.gov" in url or "umsystem.edu" in url:
        return "mo"
    if "esupplier.wi.gov" in url or "vendornet.wi.gov" in url or "doa.wi.gov" in url or "wisconsindot.gov" in url or "dhs.wisconsin.gov" in url or "wi.gov" in url or "milwaukee.gov" in url or "cityofmadison.com" in url or "wisc.edu" in url:
        return "wi"
    if "scbo.sc.gov" in url or "procurement.sc.gov" in url or "admin.sc.gov" in url or "scdhhs.gov" in url or "scdot.org" in url or "sc.gov" in url or "charleston-sc.gov" in url or "clemson.edu" in url or "sc.edu" in url:
        return "sc"
    if "oregonbuys.gov" in url or "oregon.gov" in url or "portland.gov" in url or "multco.us" in url or "oregonstate.edu" in url or "ohsu.edu" in url:
        return "or"
    if "portal.ct.gov" in url or "biznet.ct.gov" in url or "ct.gov" in url or "hartfordct.gov" in url or "stamfordct.gov" in url or "uconn.edu" in url:
        return "ct"
    if "purchasing.utah.gov" in url or "dts.utah.gov" in url or "udot.utah.gov" in url or "dhhs.utah.gov" in url or "utah.gov" in url or "slc.gov" in url or "utah.edu" in url:
        return "ut"
    if "nevadaepro.com" in url or "purchasing.nv.gov" in url or "eits.nv.gov" in url or "nv.gov" in url or "clarkcountynv.gov" in url or "lasvegasnevada.gov" in url or "unlv.edu" in url or "unr.edu" in url:
        return "nv"
    if "alabamabuys.gov" in url or "purchasing.alabama.gov" in url or "oit.alabama.gov" in url or "alabama.gov" in url or "huntsvilleal.gov" in url or "birminghamal.gov" in url or "ua.edu" in url or "auburn.edu" in url:
        return "al"
    if "doa.louisiana.gov" in url or "lapac" in url or "louisiana.gov" in url or "la.gov" in url or "nola.gov" in url or "brla.gov" in url or "lsu.edu" in url:
        return "la"
    if "vss.ky.gov" in url or "finance.ky.gov" in url or "cot.ky.gov" in url or "ky.gov" in url or "louisvilleky.gov" in url or "lexingtonky.gov" in url or "uky.edu" in url or "louisville.edu" in url:
        return "ky"
    if "oklahoma.gov/omes" in url or "omes.ok.gov" in url or "oklahoma.gov" in url or "ok.gov" in url or "okc.gov" in url or "cityoftulsa.org" in url or "ou.edu" in url or "okstate.edu" in url:
        return "ok"
    if "emma.maryland.gov" in url or "maryland.gov" in url or "countymd.bonfirehub.com" in url:
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
    if title.startswith("[NY]") or "new york" in agency or "nyc " in agency or "panynj" in agency:
        return "ny"
    if title.startswith("[MA]") or "massachusetts" in agency or "commbuys" in agency or "city of boston" in agency or "mbta" in agency or "massport" in agency:
        return "ma"
    if title.startswith("[NJ]") or "new jersey" in agency or "(nj)" in agency or "njstart" in agency or "nj transit" in agency or "rutgers" in agency:
        return "nj"
    if title.startswith("[WA]") or "washington state" in agency or "state of washington" in agency or "(wa)" in agency or "watech" in agency or "wa des" in agency or "wsdot" in agency:
        return "wa"
    if title.startswith("[MI]") or title.lower().startswith("[mi-") or "michigan" in agency or "(mi)" in agency or "mi sigma" in agency or "dtmb" in agency or "mdhhs" in agency or "mdot" in agency or "msp" in agency:
        return "mi"
    if title.startswith("[CO]") or title.lower().startswith("[co-") or "colorado" in agency or "(co)" in agency or "co vss" in agency or "co oit" in agency or "cdot" in agency or "cdphe" in agency:
        return "co"
    if title.startswith("[AZ]") or title.lower().startswith("[az-") or "arizona" in agency or "(az)" in agency or "procure.az.gov" in agency or "adoa" in agency or "ahcccs" in agency:
        return "az"
    if title.startswith("[MN]") or title.lower().startswith("[mn-") or "minnesota" in agency or "(mn)" in agency or "mn swift" in agency or "mnit" in agency or "mndot" in agency or "hennepin" in agency or "minneapolis" in agency:
        return "mn"
    if title.startswith("[TN]") or title.lower().startswith("[tn-") or "tennessee" in agency or "(tn)" in agency or "tn cpo" in agency or "edison" in agency or "tenncare" in agency or "tdot" in agency or "nashville" in agency or "memphis" in agency:
        return "tn"
    if title.startswith("[IN]") or title.lower().startswith("[in-") or "indiana" in agency or "(in)" in agency or "idoa" in agency or "indianapolis" in agency or "fssa" in agency or "indot" in agency or "purdue" in agency or "nswc crane" in agency:
        return "in"
    if title.startswith("[MO]") or title.lower().startswith("[mo-") or "missouri" in agency or "(mo)" in agency or "missouribuys" in agency or "oa-itsd" in agency or "modot" in agency or "mo healthnet" in agency or "st. louis" in agency or "kansas city" in agency:
        return "mo"
    if title.startswith("[WI]") or title.lower().startswith("[wi-") or "wisconsin" in agency or "(wi)" in agency or "wi doa" in agency or "wisdot" in agency or "milwaukee" in agency or "uw-madison" in agency:
        return "wi"
    if title.startswith("[SC]") or title.lower().startswith("[sc-") or "south carolina" in agency or "(sc)" in agency or "scbo" in agency or "sfaa" in agency or "scdhhs" in agency or "scdot" in agency or "niwc atlantic" in agency or "clemson" in agency:
        return "sc"
    if title.startswith("[OR]") or title.lower().startswith("[or-") or "oregon" in agency or "(or)" in agency or "oregonbuys" in agency or "das eis" in agency or "odot" in agency or "city of portland" in agency or "multnomah" in agency or "ohsu" in agency:
        return "or"
    if title.startswith("[CT]") or title.lower().startswith("[ct-") or "connecticut" in agency or "(ct)" in agency or "ctsource" in agency or "das bits" in agency or "ctdot" in agency or "uconn" in agency:
        return "ct"
    if title.startswith("[UT]") or title.lower().startswith("[ut-") or "utah" in agency or "(ut)" in agency or "u3p" in agency or "ut dts" in agency or "udot" in agency or "hill afb" in agency or "salt lake city" in agency:
        return "ut"
    if title.startswith("[NV]") or title.lower().startswith("[nv-") or "nevada" in agency or "(nv)" in agency or "nevadaepro" in agency or "nv eits" in agency or "ndot" in agency or "nellis afb" in agency or "clark county" in agency or "las vegas" in agency:
        return "nv"
    if title.startswith("[AL]") or title.lower().startswith("[al-") or "alabama" in agency or "(al)" in agency or "alabama buys" in agency or "staars" in agency or "aldot" in agency or "redstone" in agency or "huntsville" in agency:
        return "al"
    if title.startswith("[LA]") or title.lower().startswith("[la-") or "louisiana" in agency or "(la)" in agency or "lapac" in agency or "la ots" in agency or "ldh" in agency or "dotd" in agency or "barksdale" in agency or "baton rouge" in agency:
        return "la"
    if title.startswith("[KY]") or title.lower().startswith("[ky-") or "kentucky" in agency or "(ky)" in agency or "ky vss" in agency or "ky cot" in agency or "chfs" in agency or "kytc" in agency or "fort knox" in agency or "louisville" in agency:
        return "ky"
    if title.startswith("[OK]") or title.lower().startswith("[ok-") or "oklahoma" in agency or "(ok)" in agency or "omes" in agency or "ohca" in agency or "soonercare" in agency or "tinker afb" in agency or "76th sweg" in agency:
        return "ok"
    if title.startswith("[MD]") or "maryland" in agency or "prince george" in agency or "howard county" in agency or "bonfirehub.com" in url:
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
    if cached.get("compliance_posture") and not (reg != "md" and "Maryland" in str(cached.get("compliance_posture"))):
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
    elif reg == "ny":
        compliance_posture = "NYC OTI Cyber Policies / NYS ITS-S14-003 • SOC 2 Type II • NIST 800-53"
    elif reg == "ma":
        compliance_posture = "MA EOTSS Enterprise Security (NIST 800-53) • SOC 2 Type II • MA VPAT"
    elif reg == "nj":
        compliance_posture = "NJ OIT Statewide Cyber Policy (NIST 800-53) • SOC 2 Type II • NJ Treasury DPP"
    elif reg == "wa":
        compliance_posture = "WaTech OCIO Sec 141.10 (NIST 800-53) • StateRAMP / SOC 2 Type II • WA DES"
    elif reg == "mi":
        compliance_posture = "MI DTMB 1340.00 Cyber Security (NIST 800-53) • StateRAMP / MiLogin • MI VPAT"
    elif reg == "co":
        compliance_posture = "Colorado OIT CIS Policies (NIST 800-53) • StateRAMP • CO HB 21-1110 VPAT"
    elif reg == "az":
        compliance_posture = "Arizona ADOA-ASET Statewide Policy P8120 (NIST 800-53) • StateRAMP • AZ 508"
    elif reg == "mn":
        compliance_posture = "MNIT Enterprise Security Standards (NIST 800-53) • StateRAMP • MN WCAG 2.1 AA"
    elif reg == "tn":
        compliance_posture = "Tennessee STS Enterprise Security Policy (NIST 800-53) • StateRAMP • TN Section 508"
    elif reg == "in":
        compliance_posture = "Indiana IOT InfoSec Framework (NIST 800-53 / IC 4-13.1) • StateRAMP • IN VPAT"
    elif reg == "mo":
        compliance_posture = "Missouri OA-ITSD InfoSec Standards (NIST 800-53 / RSMo Ch. 34) • StateRAMP • MO VPAT"
    elif reg == "wi":
        compliance_posture = "Wisconsin DOA-DET InfoSec Policies (NIST 800-53 / Wis. Stat. Ch. 16) • StateRAMP • WI VPAT"
    elif reg == "sc":
        compliance_posture = "SC SFAA DTO / OTIS Security Policies (NIST 800-53 / SC Code 11-35) • StateRAMP • SC VPAT"
    elif reg == "or":
        compliance_posture = "Oregon DAS EIS / CSS Statewide InfoSec Standards (NIST 800-53 / ORS 276A) • StateRAMP • OR VPAT"
    elif reg == "ct":
        compliance_posture = "Connecticut DAS BITS Security Policies (NIST 800-53 / CGS Sec 4d) • StateRAMP • CT OPM Accessibility"
    elif reg == "ut":
        compliance_posture = "Utah DTS Enterprise InfoSec Policy 5000-0002 (NIST 800-53 / Utah Code 63A-16) • StateRAMP • UT VPAT"
    elif reg == "nv":
        compliance_posture = "Nevada EITS InfoSec Program (NIST 800-53 / NRS 242) • StateRAMP / CJIS • NV WCAG 2.1 AA"
    elif reg == "al":
        compliance_posture = "Alabama OIT Enterprise Security Policies (NIST 800-53 / CMMC 2.0) • StateRAMP • AL VPAT"
    elif reg == "la":
        compliance_posture = "Louisiana OTS InfoSec Policy (NIST 800-53 / R.S. 39:15.1) • StateRAMP • LA Section 508"
    elif reg == "ky":
        compliance_posture = "Kentucky COT Security Standards CIO-091 (NIST 800-53 / CMMC 2.0) • StateRAMP • KY VPAT"
    elif reg == "ok":
        compliance_posture = "Oklahoma OMES Cyber Command Policy (NIST 800-53 / CMMC 2.0) • StateRAMP • OK VPAT"
    elif reg == "ca":
        compliance_posture = "CalCloud SIMM 5305-A • SOC 2 Type II • WCAG 2.1 AA"
    elif reg == "fed":
        if any(k in blob_low for k in ("dod", "defense", "army", "navy", "air force", "space force", "darpa", "disa")):
            compliance_posture = "CMMC 2.0 Level 2 • NIST 800-171 • DFARS 252.204-7012"
        else:
            compliance_posture = "FedRAMP Moderate • FAR 52.204-21 • Section 508 VPAT"
    else:
        compliance_posture = "SOC 2 Type II • NIST CSF 2.0 • Section 508 / WCAG 2.1 AA"

    if cached.get("teaming_posture") and not (reg != "md" and "Maryland" in str(cached.get("teaming_posture"))):
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


ACRONYM_TOKENS = {
    "IT", "AI", "ML", "RFP", "RFQ", "RFI", "ITN", "IFB", "IVR", "SAAS", "PAAS",
    "IAAS", "SOC", "SIEM", "EDR", "XDR", "MDR", "MFA", "SSO", "IAM", "PAM",
    "GIS", "ERP", "CRM", "LMS", "CMS", "CAD", "RMS", "EHR", "EMR", "HIPAA",
    "CJIS", "NIST", "CMMC", "RMF", "ATO", "FEDRAMP", "STATERAMP", "TX-RAMP",
    "SWAM", "DBE", "MBE", "WBE", "SDVOSB", "VOSB", "HUB", "SLED", "DOD", "DGS",
    "HSMV", "FLHSMV", "FDOT", "TXDOT", "VDOT", "CALTRANS", "DOAS", "NCDIT",
    "OIT", "DIR", "VIP", "MFMP", "EMMA", "EVA", "ESBD", "OGS", "PASSPORT",
    "NYC", "NYS", "MBTA", "CTA", "MARTA", "WMATA", "AWS", "VPN", "DNS", "WAN",
    "LAN", "SD-WAN", "VOIP", "PBX", "SIP", "API", "SQL", "ETL", "BI", "II",
    "III", "IV", "USA", "US", "VA", "TX", "CA", "FL", "MD", "IL", "PA", "OH",
    "GA", "NC", "NY", "MA", "NJ", "WA", "MI", "CO", "AZ", "MN", "TN", "IN", "MO", "WI", "SC", "OR", "CT", "UT", "NV", "AL", "LA", "KY", "OK",
    "MNIT", "SWIFT", "IDOA", "IOT", "ITSD", "WISDOT", "SCDOT", "ODOT", "CTDOT", "UDOT", "NDOT", "ALDOT", "DOTD", "KYTC", "OMES", "OHCA", "EITS", "STAARS", "LAPAC", "COT", "CHFS", "SCBO", "SFAA", "BITS", "DTS", "U3P", "OHSU",
}

LOWER_PARTICLES = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "via", "with"}


def format_human_title_for_email(raw_title: str) -> str:
    """
    Convert raw portal solicitation titles into clean, human-readable project titles for cold outreach:
      - Strips leading bracketed solicitation codes (`[0000040452]`, `[RFQ-007-26]`, `[BPM055148]`, `RFx `)
      - Strips cross-state cooperative parenthetical clutter like `(Florida State University ITN #6769-4)`
      - Smart Title-Cases screaming ALL-CAPS titles while preserving GovCon/IT acronyms (`IT`, `AI`, `CJIS`, `SaaS`, etc.)
    """
    s = clean_title_text(raw_title)
    # Strip leading bracketed IDs or state prefixes e.g. [0000040452], [RFQ-007-26], [TX], 26RFP1645291A-ST, RFP828 -
    while True:
        new_s = re.sub(r"^\s*\[[^\]]+\]\s*", "", s)
        new_s = re.sub(r"^\s*(?:RFx|RFP|RFQ|ITN|IFB|RFI)\s*[-:#]?\s*\d+[A-Za-z0-9_-]*\s*[-–—:]?\s*", "", new_s, flags=re.IGNORECASE)
        new_s = re.sub(r"^\s*\d{2,4}(?:RFP|RFQ|ITN|IFB|RFI)[A-Za-z0-9_-]*\s*[-–—:]?\s*", "", new_s, flags=re.IGNORECASE)
        new_s = re.sub(r"^\s*(?:RFx|RFP|RFQ|ITN|IFB|RFI)\s+(?=[A-Z0-9])", "", new_s, flags=re.IGNORECASE)
        if new_s == s:
            break
        s = new_s.strip()

    # Strip noisy cooperative cross-state parenthetical tags
    s = re.sub(r"\s*\([^)]*(?:ITN|RFP|RFQ|Solicitation|Contract)\s*#[^)]*\)", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"\s*—\s*Sourcewell.*$", "", s, flags=re.IGNORECASE).strip()

    # Check if title is predominantly screaming ALL-CAPS
    alpha_chars = [c for c in s if c.isalpha()]
    upper_ratio = (sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)) if alpha_chars else 0.0
    if upper_ratio > 0.68:
        words = s.split()
        out_words = []
        for idx, w in enumerate(words):
            m = re.match(r"^([^A-Za-z0-9]*)([A-Za-z0-9/-]+)([^A-Za-z0-9]*)$", w)
            if not m:
                out_words.append(w)
                continue
            pre, core, post = m.groups()
            core_up = core.upper()
            if core_up == "SAAS":
                fixed = "SaaS"
            elif core_up in ACRONYM_TOKENS:
                fixed = core_up
            elif idx > 0 and core_up.lower() in LOWER_PARTICLES:
                fixed = core_up.lower()
            elif "-" in core:
                fixed = "-".join(p.upper() if p.upper() in ACRONYM_TOKENS else p.capitalize() for p in core.split("-"))
            elif "/" in core:
                fixed = "/".join(p.upper() if p.upper() in ACRONYM_TOKENS else p.capitalize() for p in core.split("/"))
            else:
                fixed = core.capitalize()
            out_words.append(f"{pre}{fixed}{post}")
        s = " ".join(out_words)

    return s.strip(" -–—") or clean_title_text(raw_title)


def clean_agency_for_email(raw_agency: str) -> str:
    ag = str(raw_agency or "Public Agency").strip()
    if ag == "Federal Government (SAM)":
        return "Federal (SAM.gov)"
    if ag == "DGS - Statewide Procurement":
        return "California DGS Statewide Procurement"
    ag = re.sub(r"\s*\((?:Georgia|North Carolina|Ohio|New York|Massachusetts|Pennsylvania|Illinois|Maryland|Florida|California|Virginia|Texas)\)\s*$", "", ag, flags=re.IGNORECASE).strip()
    ag = re.sub(r"\bOf\b", "of", ag)
    return ag


def format_contract_line(index: int, rec: dict, dossiers: dict | None = None) -> str:
    """Format a single contract row with human-readable title, agency, NAICS & posture (zero '$' symbols in Step 1)."""
    info = resolve_contract_intelligence(rec, dossiers)
    human_title = format_human_title_for_email(info["clean_title"])
    agency = clean_agency_for_email(info["agency"])
    closing_date = info["closing_date"]
    naics_code = info["naics_code"]
    short_posture = info["compliance_posture"].split("•")[0].strip()

    if closing_date and closing_date.lower() not in ["n/a", "none", "null", "tbd", "open"]:
        return f"{index}. {human_title} — {agency} (Due: {closing_date} | NAICS {naics_code} • {short_posture})\n"
    return f"{index}. {human_title} — {agency} (NAICS {naics_code} • {short_posture})\n"


def _contract_runway_score(rec: dict, today: date | None = None) -> tuple[int, int]:
    """
    Rank contracts so outbound prospects always see solicitations with healthy response runway (>=5 days out)
    ahead of same-day/next-day expiring bids.
    """
    ref = today or datetime.now().date()
    dt = parse_contract_date(rec.get("closing_date") or "", rec.get("title") or "")
    rec_id = int(rec.get("id") or 0) if str(rec.get("id") or "").isdigit() else 0
    if dt is None:
        return (1, rec_id)
    days_left = (dt - ref).days
    if days_left >= 10:
        return (3, rec_id)
    if days_left >= 5:
        return (2, rec_id)
    if days_left >= 2:
        return (1, rec_id)
    return (0, rec_id)


def select_contracts_for_prospect(all_contracts: list[dict], prospect_state: str, max_count: int = 3) -> list[dict]:
    """
    Prioritize contracts matching the prospect's state + Federal (SAM.gov) contracts
    that have healthy response runway (>=5 days before closing), then backfill up to max_count.
    """
    today = datetime.now().date()
    norm_state = STATE_ALIASES.get(str(prospect_state or "").strip().lower(), "")
    if not norm_state:
        ranked_all = sorted(all_contracts, key=lambda c: _contract_runway_score(c, today), reverse=True)
        return ranked_all[:max_count]

    state_matches = sorted(
        [c for c in all_contracts if detect_contract_region(c) == norm_state],
        key=lambda c: _contract_runway_score(c, today),
        reverse=True,
    )
    fed_matches = sorted(
        [c for c in all_contracts if detect_contract_region(c) == "fed"],
        key=lambda c: _contract_runway_score(c, today),
        reverse=True,
    )
    other_matches = sorted(
        [c for c in all_contracts if detect_contract_region(c) not in (norm_state, "fed")],
        key=lambda c: _contract_runway_score(c, today),
        reverse=True,
    )

    # Prefer state contracts with >=2 days runway first; if a state only has same-day closing bids, blend in Federal SAM.gov bids
    fresh_state = [c for c in state_matches if _contract_runway_score(c, today)[0] >= 1]
    stale_state = [c for c in state_matches if _contract_runway_score(c, today)[0] == 0]

    combined = fresh_state + fed_matches + stale_state + other_matches
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
    "ny": "New York",
    "ma": "Massachusetts",
    "nj": "New Jersey",
    "wa": "Washington",
    "mi": "Michigan",
    "co": "Colorado",
    "az": "Arizona",
    "mn": "Minnesota",
    "tn": "Tennessee",
    "in": "Indiana",
    "mo": "Missouri",
    "wi": "Wisconsin",
    "sc": "South Carolina",
    "or": "Oregon",
    "ct": "Connecticut",
    "ut": "Utah",
    "nv": "Nevada",
    "al": "Alabama",
    "la": "Louisiana",
    "ky": "Kentucky",
    "ok": "Oklahoma",
}

STATE_PORTAL_LABELS = {
    "tx": "Texas ESBD/DIR, DemandStar, and SAM.gov",
    "va": "Virginia eVA, DemandStar, and SAM.gov",
    "ca": "California Cal eProcure, DemandStar, and SAM.gov",
    "fl": "Florida MFMP VIP, DemandStar, and SAM.gov",
    "md": "Maryland eMMA, county Bonfire portals, and SAM.gov",
    "il": "Illinois BidBuy, Chicago/Cook County portals, and SAM.gov",
    "pa": "PA DGS eMarketplace, PhilaPort, and SAM.gov",
    "oh": "OhioBuys, Columbus/Franklin County portals, and SAM.gov",
    "ga": "Georgia DOAS GPR, Atlanta metro portals, and SAM.gov",
    "nc": "North Carolina eVP, Wake/Mecklenburg portals, and SAM.gov",
    "ny": "NYS Contract Reporter, NYC PASSPort, and SAM.gov",
    "ma": "Massachusetts COMMBUYS, Boston/MBTA portals, and SAM.gov",
    "nj": "New Jersey NJSTART, Treasury DPP/OIT portals, and SAM.gov",
    "wa": "Washington WEBS, WaTech/DES portals, and SAM.gov",
    "mi": "Michigan SIGMA VSS, DTMB procurement portals, and SAM.gov",
    "co": "Colorado VSS, OIT/Denver procurement portals, and SAM.gov",
    "az": "Arizona APP (Procure.AZ.gov), ADOA-ASET portals, and SAM.gov",
    "mn": "Minnesota SWIFT Supplier Portal, MNIT Services, and SAM.gov",
    "tn": "Tennessee Edison Supplier Portal, CPO/STS, and SAM.gov",
    "in": "Indiana IDOA Procurement, IOT, and SAM.gov",
    "mo": "MissouriBUYS, OA-ITSD, and SAM.gov",
    "wi": "Wisconsin eSupplier/VendorNet, DOA-DET, and SAM.gov",
    "sc": "South Carolina SCBO, SFAA DTO/OTIS, and SAM.gov",
    "or": "OregonBuys eProcurement, DAS EIS, and SAM.gov",
    "ct": "Connecticut CTsource Bid Board, DAS BITS, and SAM.gov",
    "ut": "Utah U3P SciQuest, DTS/Hill AFB, and SAM.gov",
    "nv": "NevadaEPro, Nevada EITS/Nellis AFB, and SAM.gov",
    "al": "Alabama Buys STAARS, Alabama OIT/Redstone Arsenal, and SAM.gov",
    "la": "Louisiana LaPAC/LaGov, Louisiana OTS, and SAM.gov",
    "ky": "Kentucky eProcurement VSS, Kentucky COT, and SAM.gov",
    "ok": "Oklahoma OMES Central Purchasing, Tinker AFB, and SAM.gov",
}

GENERIC_PERSON_NAMES = {
    "capture", "team", "there", "info", "sales", "contact", "hello",
    "contracts", "contract", "partner", "partners", "partnerships", "growth",
    "bd", "bizdev", "admin", "procurement", "proposals", "rfp", "bids",
    "inquiries", "general", "office", "marketing", "support", "careers",
    "solutions", "services", "gov", "stars", "engage", "",
}


def clean_company_for_copy(raw_company: str) -> str:
    """Clean company name for natural, human-sounding email subject lines and body prose."""
    try:
        from govcon_lead_harvester import clean_company_display_name
        s = clean_company_display_name(raw_company)
    except Exception:
        s = str(raw_company or "").strip()
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
    s = re.sub(
        r",?\s*\b(L\.?L\.?C\.?|Inc\.?|Incorporated|Corporation|Corp\.?|Company|Co\.?|P\.?B\.?C\.?|Subsidiary)\b[\s,.]*$",
        "",
        s,
        flags=re.IGNORECASE,
    ).strip()
    s = re.sub(
        r",?\s*\b(L\.?L\.?C\.?|Inc\.?|Corporation|Corp\.?)\b[\s,.]*$",
        "",
        s,
        flags=re.IGNORECASE,
    ).strip(" ,.-!")
    if s.upper() == "INTERNATIONAL BUSINESS MACHINES":
        return "IBM"
    if s.upper() == "SCIENCE APPLICATIONS INTERNATIONAL":
        return "SAIC"
    if s.isupper() and len(s) > 4:
        acronyms = {"IT", "AI", "US", "USA", "IBM", "SAIC", "CACI", "DCCA", "ECS", "ICF", "CGI", "KBR", "VTG"}
        words = s.split()
        out_words = []
        for w in words:
            w_clean = w.strip(",.")
            if w_clean in acronyms:
                out_words.append(w_clean)
            elif w_clean == "OMNI":
                out_words.append("Omni")
            elif w_clean == "FED":
                out_words.append("Federal")
            elif w_clean == "VIVSOFT":
                out_words.append("VivSoft")
            else:
                out_words.append(w.capitalize())
        s = " ".join(out_words)
    return s or "your team"


def possessive_company(comp: str) -> str:
    """Return proper English possessive (`CivicActions'` vs `CloudHesive's`)."""
    c = str(comp or "your team").strip()
    if c.lower() == "your team":
        return "your team's"
    return f"{c}'" if c.endswith(("s", "S")) else f"{c}'s"


def _pick_variant(seed_str: str, slot: int, options: list[str]) -> str:
    """Deterministically select a phrase variant per prospect + slot to defeat bulk spam fingerprinting."""
    digest = hashlib.sha256(f"{seed_str}::slot_{slot}".encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(options)
    return options[idx]



OEM_OR_PLATFORM_DOMAINS = {
    "technomile.com", "ironbow.com", "thundercattech.com", "koniag-gs.com",
    "sada.com", "pantheon.io", "obsidiansecurity.com", "stackarmor.com",
    "defensestorm.com", "digitalhands.com", "kudelskisecurity.com",
    "expedient.com", "ntirety.com", "burwood.com", "improving.com",
    "b2gnow.com", "evogov.com", "kitware.com", "enveil.com", "cloudhesive.com",
}


def classify_prospect_target_segment(company: str, award_profile: dict | None = None, email: str = "") -> str:
    """
    Classify each GovCon prospect into one of 3 precision target segments so Step 1 and Step 2
    pitch the exact tier & moat that matches their scale and capture workflow:
      1. 'ENTERPRISE_OEM_FOIA' (Award >= $15M OR GovTech/Cyber/Cloud Platform Vendor -> Lead with Tier 4 $2,499/mo FOIA Vault & 50k OEM API + Tier 3 $1,499/mo Proposal .ZIP Compiler)
      2. 'PRIME_PROPOSAL_AUTOPILOT' ($1M <= Award < $15M OR Active Federal Prime -> Lead with Tier 3 $1,499/mo 1-Click 3-Volume Shipley Proposal .ZIP Compiler & Tier 2 $399/mo CaptureDesk)
      3. 'GROWTH_SLED_SUBCONTRACTOR' (Regional SLED & Small Business Subcontractors -> Lead with Free Explorer $0 + Tier 1 $99/mo + Tier 2 $399/mo + 13 CFR § 125.6 Teaming Slot & Tier 3 .ZIP Compiler)
    """
    dom = str(email or "").strip().lower().split("@")[-1] if "@" in str(email or "") else ""
    amt = 0.0
    if isinstance(award_profile, dict):
        try:
            amt = float(award_profile.get("award_amount") or 0.0)
        except Exception:
            amt = 0.0
    if amt >= 15_000_000 or dom in OEM_OR_PLATFORM_DOMAINS:
        return "ENTERPRISE_OEM_FOIA"
    if amt >= 1_000_000 or (isinstance(award_profile, dict) and award_profile.get("award_id")):
        return "PRIME_PROPOSAL_AUTOPILOT"
    return "GROWTH_SLED_SUBCONTRACTOR"


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
    award_profile: dict | None = None,
    recompete_item: dict | None = None,
    subcontract_item: dict | None = None,
) -> dict[str, str]:
    """
    Generate anti-spam rotated 2-step cold email copy (Step 1: Deliverability-Safe Value Drop
    with Prospect's Own USAspending Award ID + 90-180d Recompete & Prime-to-Sub Teaming Wire;
    Step 2: Self-Serve Tier 1 $99/mo SignalWire + Tier 2 $399/mo CaptureDesk Autopilot)
    plus native Instantly/Smartlead {{RANDOM | ...}} Spintax strings.
    """
    norm_state = STATE_ALIASES.get(str(prospect_state or "").strip().lower(), "")
    region_label = f"{STATE_DISPLAY_NAMES[norm_state]} & Federal" if norm_state in STATE_DISPLAY_NAMES else "Federal & State SLED"
    portal_focus = STATE_PORTAL_LABELS.get(norm_state, "SAM.gov, DemandStar, and 31 state SLED portals")
    clean_domain = site_base_url.replace("https://", "").replace("http://", "").strip("/")
    clean_comp = clean_company_for_copy(company)
    seed = f"{email.lower().strip()}::{clean_comp.lower().strip()}"
    comp_possessive = possessive_company(clean_comp)
    clean_fname = str(fname or "").strip()
    is_generic_name = clean_fname.lower() in GENERIC_PERSON_NAMES

    # -------------------------------------------------------------------------
    # STEP 1 (TOUCH 1): DELIVERABILITY-FIRST LIVE RFP DROP (Zero $ signs, 1 clean canonical URL)
    # -------------------------------------------------------------------------
    person_or_comp_subj = (
        f"{clean_comp} — {bid_count} open {region_label} IT RFPs"
        if is_generic_name
        else f"{clean_fname} — {bid_count} open {region_label} IT RFPs"
    )
    if award_profile and award_profile.get("award_id"):
        awd_id = str(award_profile["award_id"]).strip()
        awd_sub_short = str(award_profile.get("awarding_sub_agency_short") or "Federal").strip()
        awd_sub_full = str(award_profile.get("awarding_sub_agency") or awd_sub_short).strip()
        awd_amt_clean = str(award_profile.get("award_amount_clean") or "federal").strip()
        awd_end = str(award_profile.get("end_date") or "").strip()
        awd_active = bool(award_profile.get("is_active"))
        subject_variants = [
            f"{comp_possessive} {awd_sub_short} contract ({awd_id}) + {bid_count} {region_label} IT bids",
            f"{awd_id} ({awd_sub_short}) + {bid_count} open {region_label} IT RFPs for {clean_comp}",
            f"{clean_comp} ({awd_id}) — {bid_count} open {region_label} IT & cyber solicitations",
            f"{awd_sub_short} {awd_id} + new {region_label} IT bids for {clean_comp}",
        ]
        if awd_active and awd_end:
            relevance_lines = [
                f"Noticed {comp_possessive} {awd_amt_clean} contract with {awd_sub_full} ({awd_id}, PoP through {awd_end}) while indexing active IT primes, and pulled {bid_count} open solicitations from our latest crawl:",
                f"Saw {comp_possessive} active {awd_amt_clean} {awd_sub_short} award ({awd_id}, running through {awd_end}) and wanted to pass along {bid_count} live IT/cyber bids currently open for response:",
                f"While mapping {awd_sub_short} IT primes ({comp_possessive} {awd_amt_clean} contract {awd_id}, PoP ending {awd_end}), our classifier flagged {bid_count} open solicitations aligned with {clean_comp}:",
            ]
        else:
            relevance_lines = [
                f"Noticed {comp_possessive} {awd_amt_clean} contract with {awd_sub_full} ({awd_id}) while indexing proven IT primes, and pulled {bid_count} open solicitations from our latest crawl:",
                f"Saw {comp_possessive} {awd_amt_clean} {awd_sub_short} contract record ({awd_id}) and wanted to pass along {bid_count} live IT/cyber bids currently open for response:",
                f"While mapping {awd_sub_short} IT primes ({comp_possessive} {awd_amt_clean} contract {awd_id}), our classifier flagged {bid_count} open solicitations aligned with {clean_comp}:",
            ]
    else:
        subject_variants = [
            f"{bid_count} open {region_label} IT bids for {clean_comp}",
            f"{region_label} IT & cyber RFPs for {clean_comp}",
            f"Open {region_label} IT solicitations ({clean_comp})",
            person_or_comp_subj,
            f"New {region_label} tech & cyber solicitations for {clean_comp}",
            f"{clean_comp} / {bid_count} open public-sector IT contracts",
        ]
        relevance_lines = [
            f"Since {clean_comp} delivers public-sector technology, I pulled {bid_count} active solicitations from our latest crawl:",
            f"Noticed {comp_possessive} work in the space and wanted to pass along {bid_count} live IT/cyber bids currently open for response:",
            f"Thought these {bid_count} open solicitations from today's 6-hour crawl might fit {comp_possessive} capture pipeline:",
            f"Flagged {bid_count} open public-sector tech opportunities from today's wire that looked aligned with {clean_comp}:",
            f"Wanted to share {bid_count} newly posted IT & security contracts that just cleared our noise filter for {clean_comp}:",
        ]

    if is_generic_name:
        greetings = [
            f"Hi {clean_comp} team,",
            f"Hello {clean_comp} team,",
            f"Hey {clean_comp} team,",
        ]
    else:
        greetings = [
            f"Hi {clean_fname},",
            f"Hey {clean_fname},",
            f"Hello {clean_fname},",
            f"{clean_fname} —",
        ]

    openers = [
        f"I run an automated procurement monitor that tracks {portal_focus} (plus 30 other state SLED portals) every 6 hours.",
        f"We maintain a live public-sector RFP engine covering {portal_focus} and 30 additional state procurement portals every 6 hours.",
        f"I built a real-time government contract radar that pulls newly posted IT and cybersecurity bids across {portal_focus}.",
        f"Our ingestion pipeline monitors {portal_focus} every 6 hours for net-new IT, cloud, and cybersecurity solicitations.",
        f"I track newly released public-sector technology solicitations across {portal_focus} (33 federal and state portals total).",
    ]
    value_props = [
        "Our classifier strips out 99% of commodity hardware, toner, sole-source, and COTS renewal noise so capture teams only see net-new services and engineering scopes.",
        "Everything is pre-filtered to remove low-value maintenance renewals and hardware reselling so your team only sees actionable IT & cyber RFPs.",
        "Unlike legacy feeds cluttered with printer ink and license renewals, our pipeline isolates net-new software, cloud, and cybersecurity work.",
        "Each solicitation is de-duplicated every 6 hours and pre-shredded with NAICS, SBA size caps, compliance posture, and teaming requirements.",
    ]

    # Upgrade #2 & #3 Wire Snippet (Zero $ symbols in Step 1 for spam-filter safety)
    recompete_and_sub_step1 = ""
    if recompete_item and subcontract_item:
        rec_id = recompete_item["award_id"]
        rec_ag = recompete_item["awarding_sub_agency_short"]
        rec_inc = clean_company_for_copy(recompete_item["incumbent_recipient"])
        rec_amt_clean = str(recompete_item["award_amount_fmt"]).replace("$", "USD ")
        rec_end = recompete_item["end_date"]
        rec_days = recompete_item["days_until_expiration"]

        sub_id = subcontract_item["award_id"]
        sub_prime = clean_company_for_copy(subcontract_item["prime_recipient"])
        sub_ag = subcontract_item["awarding_sub_agency_short"]
        sub_amt_clean = str(subcontract_item["award_amount_fmt"]).replace("$", "USD ")

        recompete_and_sub_step1 = (
            f"\nPlus 2 pre-RFP & subcontracting signals from today's USAspending wire:\n"
            f"• [Recompete Radar — {rec_days}d to PoP End] {rec_ag} ({rec_id}): {rec_amt_clean} incumbent contract ({rec_inc}, PoP ending {rec_end}) entering FAR 19.502-2 Sources Sought shaping window\n"
            f"• [Prime-to-Sub Teaming Wire] {sub_prime} awarded {sub_amt_clean} at {sub_ag} ({sub_id}) -> ~30% FAR 52.219-9 Small-Business Subcontracting Pool\n"
        )

    target_segment = classify_prospect_target_segment(company, award_profile, email)
    try:
        from govcon_lead_harvester import compute_mailbox_pool_slot
        shard_meta = compute_mailbox_pool_slot(email, company)
    except Exception:
        shard_meta = {"mailbox_pool_slot": 1, "mailbox_shard_id": "MBX-01", "mailbox_pool_size": 50}

    # T3 Hybrid Mode: Optional env-guarded OUTBOUND_SHARD_DOMAINS (defaults safely to signaltender.net)
    raw_shard_domains = [
        d.strip().replace("https://", "").replace("http://", "").strip("/")
        for d in (os.getenv("OUTBOUND_SHARD_DOMAINS") or "").split(",")
        if d.strip()
    ]
    effective_domain = (
        raw_shard_domains[(int(shard_meta.get("mailbox_pool_slot") or 1) - 1) % len(raw_shard_domains)]
        if raw_shard_domains
        else clean_domain
    )

    # Use clean canonical URLs in Step 1 and 1-click `?sol_id=` pre-hydrated Proposal Compiler deep-links in Step 2
    clean_dossier_url = f"https://{effective_domain}/contracts"
    sol_slug_param = "fa8726-26-r-0042"
    if top_intel and top_intel.get("dossier_url"):
        raw_d_url = top_intel["dossier_url"].split("?")[0]
        if "/contracts/rfp/" in raw_d_url:
            sol_slug_param = raw_d_url.split("/contracts/rfp/", 1)[1].replace(".html", "").strip("/") or sol_slug_param
        clean_dossier_url = raw_d_url.replace(f"https://{clean_domain}", f"https://{effective_domain}")
    compiler_deeplink_url = f"https://{effective_domain}/?sol_id={sol_slug_param}&company={quote(company)}#proposal-autopilot"

    clean_checkout_url = f"https://{effective_domain}/#checkout"
    clean_portal_url = f"https://{effective_domain}/#signup"
    incumbent_hook_str = ""
    if award_profile and award_profile.get("award_id"):
        incumbent_hook_str = (
            f"{award_profile.get('award_id')} | {award_profile.get('matched_recipient_name') or company} | "
            f"{award_profile.get('award_amount_fmt', '$1.0M')} ({award_profile.get('awarding_sub_agency_short', 'Federal')})"
        )
    elif recompete_item and recompete_item.get("award_id"):
        incumbent_hook_str = (
            f"{recompete_item.get('award_id')} | {recompete_item.get('incumbent_recipient', 'Incumbent')} | "
            f"{recompete_item.get('award_amount_fmt', '$2.5M')} ({recompete_item.get('awarding_sub_agency_short', 'Federal')})"
        )

    if target_segment == "ENTERPRISE_OEM_FOIA":
        step1_ctas = [
            f"I posted the pre-shredded Section L/M breakdown, Post-Award FOIA Incumbent LCAT Rate Benchmark, and 1-Click 6-File Shipley Proposal .ZIP Compiler (.docx + live-formula .xlsx) for #1 here:\n{clean_dossier_url}\n\nYou can also launch the pre-loaded 6-File Proposal .ZIP Compiler ({compiler_deeplink_url}) or claim a Free Explorer Account ({clean_portal_url}) to save {comp_possessive} territory filters.\n\nAre you actively bidding {region_label} IT work right now (or reply 'ZIP' and I'll send the 6-file Shipley .DOCX/.XLSX package directly), or should I take you off my list?",
            f"You can inspect the pre-shredded capture dossier, FOIA incumbent labor rate vault, and 90-second 6-File Shipley Proposal .ZIP Compiler for #1 here:\n{clean_dossier_url}\n\nOr test the 1-Click 6-File Proposal .ZIP Compiler ({compiler_deeplink_url}) and Free Explorer Portal ({clean_portal_url}) anytime.\n\nIs {region_label} IT/cyber on {comp_possessive} radar this quarter (or reply 'ZIP' for the direct .DOCX/.XLSX compiler package)?",
            f"Here is the direct Section L/M breakdown, FOIA incumbent rate benchmark, and 1-Click 6-File .DOCX/.XLSX Proposal .ZIP Compiler for #1:\n{clean_dossier_url}\n\nPre-loaded 6-File Proposal .ZIP Compiler: {compiler_deeplink_url} | Free Explorer Portal: {clean_portal_url}\n\nWorth sending over future {region_label} IT scopes when they hit the wire (or reply 'ZIP' to grab the 6-file proposal package)?",
        ]
    elif target_segment == "PRIME_PROPOSAL_AUTOPILOT":
        step1_ctas = [
            f"I posted the pre-shredded Section L/M breakdown and 1-Click 6-File Shipley Proposal .ZIP Compiler (Vol I .docx + Vol II live-formula CLIN .xlsx + Vol III-V .docx) for #1 here:\n{clean_dossier_url}\n\nYou can also launch the pre-loaded 6-File Proposal .ZIP Compiler ({compiler_deeplink_url}) or claim a Free Explorer Account ({clean_portal_url}) to save {comp_possessive} territory filters.\n\nAre you actively bidding {region_label} IT work right now (or reply 'ZIP' and I'll send the 6-file Shipley .DOCX/.XLSX package directly), or should I take you off my list?",
            f"You can inspect the pre-shredded capture dossier and 90-second 6-File Shipley Proposal .ZIP Compiler (.docx + live-formula .xlsx) for #1 here:\n{clean_dossier_url}\n\nOr test the 1-Click 6-File Proposal .ZIP Compiler ({compiler_deeplink_url}) and Free Explorer Portal ({clean_portal_url}) anytime.\n\nIs {region_label} IT/cyber on {comp_possessive} radar this quarter (or reply 'ZIP' for the direct .DOCX/.XLSX compiler package)?",
            f"Here is the direct Section L/M breakdown, 13 CFR 125.6 Teaming Slot verifier, and 1-Click 6-File Shipley Proposal .ZIP Compiler for #1:\n{clean_dossier_url}\n\nPre-loaded 6-File Proposal .ZIP Compiler: {compiler_deeplink_url} | Free Explorer Portal: {clean_portal_url}\n\nWorth sending over future {region_label} IT scopes when they hit the wire (or reply 'ZIP' to grab the 6-file proposal package)?",
        ]
    else:
        step1_ctas = [
            f"I posted the pre-shredded Section L/M breakdown, 1-Click 13 CFR 125.6 Compliant Teaming Slot request, and 6-File Shipley Proposal .ZIP Compiler for #1 here:\n{clean_dossier_url}\n\nYou can also launch the pre-loaded 6-File Proposal .ZIP Compiler ({compiler_deeplink_url}) or claim a Free Explorer Account ({clean_portal_url}) to save {comp_possessive} state & NAICS filters.\n\nAre you actively bidding {region_label} IT work right now (or reply 'ZIP' and I'll send the 6-file Shipley .DOCX/.XLSX package directly), or should I take you off my list?",
            f"You can inspect the pre-shredded capture dossier, request a 13 CFR 125.6 subcontracting slot, or compile a 6-File Shipley .DOCX/.XLSX proposal draft for #1 here:\n{clean_dossier_url}\n\nOr test the 1-Click 6-File Proposal .ZIP Compiler ({compiler_deeplink_url}) and Free Explorer Portal ({clean_portal_url}) anytime.\n\nIs {region_label} IT/cyber on {comp_possessive} radar this quarter (or reply 'ZIP' for the direct .DOCX/.XLSX compiler package)?",
            f"Here is the direct Section L/M, NAICS, 13 CFR 125.6 Teaming Exchange & 6-File Proposal .ZIP breakdown for #1:\n{clean_dossier_url}\n\nPre-loaded 6-File Proposal .ZIP Compiler: {compiler_deeplink_url} | Free Explorer Portal: {clean_portal_url}\n\nWorth sending over future {region_label} IT scopes when they hit the wire (or reply 'ZIP' to grab the 6-file proposal package)?",
        ]

    signoffs = [
        "Best,\nAaron Chen\nFounder, SignalTender",
        "Regards,\nAaron Chen\nFounder, SignalTender",
        "Best regards,\nAaron Chen\nFounder, SignalTender",
    ]

    step1_subject = _pick_variant(seed, 1, subject_variants)
    step1_body = (
        f"{_pick_variant(seed, 2, greetings)}\n\n"
        f"{_pick_variant(seed, 3, openers)} "
        f"{_pick_variant(seed, 4, relevance_lines)}\n\n"
        f"{payload_text}"
        f"{recompete_and_sub_step1}\n"
        f"{_pick_variant(seed, 5, value_props).replace(',sole-source', ', sole-source')}\n\n"
        f"{_pick_variant(seed, 6, step1_ctas)}\n\n"
        f"{_pick_variant(seed, 7, signoffs)}"
    )

    # -------------------------------------------------------------------------
    # STEP 2 (TOUCH 2 - DAY +3): PERSONA-SEGMENTED 4-TIER PITCH
    # -------------------------------------------------------------------------
    step2_intros = [
        f"Quick follow-up in case {clean_comp} is expanding its {region_label} capture and proposal pipeline this quarter.",
        f"Following up briefly on the {region_label} IT solicitations and pre-shredded capture dossiers I sent over earlier this week.",
        f"Circling back with one quick note in case your team tracks Federal or State SLED IT & cybersecurity bids.",
        f"Wanted to follow up one last time regarding our automated 33-portal Federal and 31-State SLED capture & proposal suite.",
    ]
    intel_block = ""
    if top_intel:
        human_top_title = format_human_title_for_email(top_intel["clean_title"])
        human_top_agency = clean_agency_for_email(top_intel["agency"])
        recompete_step2_lines = ""
        if recompete_item and subcontract_item:
            recompete_step2_lines = (
                f"• 90-180d Recompete PTW & Shaping (API #16 + API #21): {recompete_item['awarding_sub_agency_short']} {recompete_item['award_id']} "
                f"({recompete_item['award_amount_fmt']} incumbent {clean_company_for_copy(recompete_item['incumbent_recipient'])}, PoP ends {recompete_item['end_date']}) -> "
                f"Challenger PTW Ceiling {recompete_item['api16_ptw_challenger_ceiling_fmt']} + FAR 19.502-2 Rule-of-Two Set-Aside Brief\n"
                f"• Fresh Prime Subcontracting Wire (API #11): {clean_company_for_copy(subcontract_item['prime_recipient'])} ({subcontract_item['award_amount_fmt']} at {subcontract_item['awarding_sub_agency_short']}, {subcontract_item['award_id']}) -> "
                f"{subcontract_item['api11_sb_subcontract_pool_fmt']}\n"
            )
        intel_block = (
            f"For example, on '{human_top_title}' ({human_top_agency}), our CaptureDesk engine already pre-computed:\n"
            f"• Classification: NAICS {top_intel['primary_naics']} (SBA Cap: {top_intel['sba_size_standard']})\n"
            f"• Cyber & Clause Posture: {top_intel['compliance_posture']}\n"
            f"• Teaming & Past Performance: {top_intel['teaming_posture']}\n"
            f"{recompete_step2_lines}"
            f"• Live Dossier & 1-Click 3-Volume Proposal .ZIP Compiler: {clean_dossier_url}\n"
            f"• Direct 1-Click Pre-Loaded .ZIP Proposal Compiler Link: {compiler_deeplink_url}\n\n"
        )

    if target_segment == "ENTERPRISE_OEM_FOIA":
        step2_tiers = [
            (
                f"{intel_block}"
                f"Because {clean_comp} operates at Prime/Enterprise scale, we built SignalTender to replace $25,000/RFP proposal consultants and $18,000+/yr legacy GovWin seats with four self-serve tiers (leading with our FOIA Rate Vault & 1-Click Proposal .ZIP Compiler):\n\n"
                f"• Tier 4 — Enterprise OEM & FOIA Winning-Bid Vault ($2,499/mo): Automated Post-Award FOIA / State PIA Incumbent Winning LCAT Rate Vault (verified awarded labor rates & expiring PoPs across Federal & 31 SLED states) + 50,000 REST/MCP API calls/mo (@signaltender/mcp-server) for internal Copilot/Claude capture workflows.\n"
                f"• Tier 3 — Proposal Autopilot Enterprise ($1,499/mo): 1-Click Complete 3-Volume Shipley Proposal Compiler (.ZIP containing editable Word .docx Volume I Technical + live-formula Excel .xlsx Volume II Cost/CLIN Model + Word .docx Volume III Past Performance/OCI in 90s) + 13 CFR § 125.6 Verified Teaming Clearinghouse.\n"
                f"• Tier 2 — CaptureDesk Autopilot ($399/mo): Automated 24-API Section L/M Compliance Matrices, Price-to-Win Recompete Models (API #16), Sources Sought Set-Aside Briefs (API #21), Shipley Black-Hat & Incumbent Ghosting (API #33), and CPARS Volume III citations across all 33 Federal & 31-State SLED portals.\n"
                f"• Tier 1 — SignalWire Pro ($99/mo): Real-time 6-hour SAM.gov, DemandStar & 31-State SLED (VA, TX, CA, FL, MD, IL, PA, OH, GA, NC, NY, MA, NJ, WA, MI, CO, AZ, MN, TN, IN, MO, WI, SC, OR, CT, UT, NV, AL, LA, KY, OK) IT/Cyber alert wire."
            ),
        ]
    elif target_segment == "PRIME_PROPOSAL_AUTOPILOT":
        step2_tiers = [
            (
                f"{intel_block}"
                f"Instead of paying $15,000–$35,000 per RFP to outside Shipley proposal consultants or $15,000+/yr for legacy GovWin seats, Prime capture teams plug into SignalTender completely self-serve:\n\n"
                f"• Tier 3 — Proposal Autopilot Enterprise ($1,499/mo — Most Popular for Primes): 1-Click Complete 3-Volume Shipley Proposal Compiler (.ZIP with editable Word .docx Volume I Technical/Management + live-formula Excel .xlsx Volume II CLIN Pricing & PTW + Word .docx Volume III CPARS/13 CFR § 125.6/OCI in 90 seconds) + Verified 13 CFR § 125.6 Teaming Clearinghouse.\n"
                f"• Tier 2 — CaptureDesk Autopilot ($399/mo): Automated 24-Engine AI Section L/M Compliance Matrices, Price-to-Win Recompete Models (API #16), Sources Sought Set-Aside Briefs (API #21), Shipley Black-Hat & Incumbent Ghosting (API #33), Prime-to-Sub Teaming Plans (API #11), CPARS Volume III citations, and 39 REST/MCP APIs (@signaltender/mcp-server).\n"
                f"• Tier 4 — Enterprise OEM & FOIA Winning-Bid Vault ($2,499/mo): Automated Post-Award FOIA/PIA Incumbent Winning LCAT Rate Vault + 50,000 REST/MCP API calls/mo OEM license.\n"
                f"• Tier 1 — SignalWire Pro ($99/mo): Real-time 6-hour SAM.gov, DemandStar & 31-State SLED (VA, TX, CA, FL, MD, IL, PA, OH, GA, NC, NY, MA, NJ, WA, MI, CO, AZ, MN, TN, IN, MO, WI, SC, OR, CT, UT, NV, AL, LA, KY, OK) IT/Cyber alerts + 90-180d Recompete Wire."
            ),
        ]
    else:
        step2_tiers = [
            (
                f"{intel_block}"
                f"Instead of paying $15,000+/yr for legacy GovWin seats or $25,000 per RFP for proposal consultants, capture teams plug into SignalTender completely self-serve (zero sales calls or demos):\n\n"
                f"• Tier 1 — SignalWire Pro ($99/mo): Real-time 6-hour SAM.gov, DemandStar & 31-State SLED (VA, TX, CA, FL, MD, IL, PA, OH, GA, NC, NY, MA, NJ, WA, MI, CO, AZ, MN, TN, IN, MO, WI, SC, OR, CT, UT, NV, AL, LA, KY, OK) IT/Cyber alerts + 90-180d Recompete & 30% Subcontracting Wire routed to Discord, Slack, MS Teams, or Webhook.\n"
                f"• Tier 2 — CaptureDesk Autopilot ($399/mo): Everything in Tier 1 + automated AI Section L/M Compliance Matrices, Price-to-Win Recompete Models (API #16), Sources Sought Set-Aside Briefs (API #21), Shipley Black-Hat & Incumbent Ghosting (API #33), Prime-to-Sub Teaming Plans (API #11), CPARS Volume III citations, SF-30 Amendment Diffs, and 39 REST/MCP APIs (@signaltender/mcp-server).\n"
                f"• Tier 3 — Proposal Autopilot Enterprise ($1,499/mo): 1-Click Complete 3-Volume Shipley Proposal Compiler (.ZIP containing native Word .docx Volume I/III + live-formula Excel .xlsx Volume II Cost Model in 90s) + 13 CFR § 125.6 Verified Teaming Clearinghouse.\n"
                f"• Tier 4 — Enterprise OEM & FOIA Winning-Bid Vault ($2,499/mo): Automated Post-Award FOIA/PIA Incumbent Winning LCAT Rate Vault + 50,000 REST/MCP API calls/mo OEM license."
            ),
        ]

    step2_closers = [
        f"You can create a Free Explorer Account ($0/mo — no credit card required) to save {comp_possessive} state & NAICS alert filters, Capture Vault, and Bid Board at:\n{clean_portal_url}\n\nOr activate any plan (Tier 1 $99/mo, Tier 2 $399/mo, Tier 3 Proposal .ZIP $1,499/mo, or Tier 4 FOIA/OEM $2,499/mo) in 60 seconds at:\n{clean_checkout_url}\n\nClassified as an allowable Bid & Proposal (B&P) market-research expense under FAR 31.205-18 (instant itemized PDF receipt for corporate P-Cards & 1-click auto-renew pause in #account).",
        f"Claim a Free Explorer Account ($0/mo) in our Client Portal to configure your territory filters and test all 39 AI Capture APIs:\n{clean_portal_url}\n\nOr start a month-to-month SignalWire ($99/mo), CaptureDesk ($399/mo), Proposal Autopilot ($1,499/mo), or Enterprise OEM & FOIA Vault ($2,499/mo) plan anytime at:\n{clean_checkout_url}\n\n100% self-serve, FAR 31.205-18 allowable B&P expense (corporate P-Card & DCAA PDF invoice ready), no demos required.",
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
    spintax_greeting = (
        f"{{{{RANDOM | Hi {clean_comp} team, | Hello {clean_comp} team,}}}}"
        if is_generic_name
        else f"{{{{RANDOM | Hi {clean_fname}, | Hey {clean_fname}, | Hello {clean_fname},}}}}"
    )
    if award_profile and award_profile.get("award_id"):
        awd_id = str(award_profile["award_id"]).strip()
        awd_sub_short = str(award_profile.get("awarding_sub_agency_short") or "Federal").strip()
        spintax_subject_1 = (
            f"{{{{RANDOM | {comp_possessive} {awd_sub_short} contract ({awd_id}) + {bid_count} {region_label} IT bids | "
            f"{awd_id} ({awd_sub_short}) + {bid_count} open {region_label} IT RFPs for {clean_comp} | "
            f"{clean_comp} ({awd_id}) — {bid_count} open {region_label} IT & cyber solicitations}}}}"
        )
        spintax_relevance_1 = (
            f"{{{{RANDOM | {relevance_lines[0]} | {relevance_lines[1]} | {relevance_lines[2]}}}}}"
        )
    else:
        spintax_subject_1 = (
            f"{{{{RANDOM | {bid_count} open {region_label} IT bids for {clean_comp} | "
            f"{region_label} IT & cyber RFPs for {clean_comp} | "
            f"Open {region_label} IT solicitations ({clean_comp}) | "
            f"{person_or_comp_subj}}}}}"
        )
        spintax_relevance_1 = (
            f"{{{{RANDOM | Since {clean_comp} delivers public-sector technology, I pulled {bid_count} active solicitations from our latest crawl: | "
            f"Noticed {comp_possessive} work in the space and wanted to pass along {bid_count} live IT/cyber bids currently open for response: | "
            f"Thought these {bid_count} open solicitations from today's 6-hour crawl might fit {comp_possessive} capture pipeline:}}}}"
        )

    spintax_body_1 = (
        f"{spintax_greeting}\n\n"
        f"{{{{RANDOM | I run an automated procurement monitor that tracks {portal_focus} (plus 30 other state SLED portals) every 6 hours. | "
        f"We maintain a live public-sector RFP engine covering {portal_focus} and 30 additional state procurement portals every 6 hours. | "
        f"I built a real-time government contract radar that pulls newly posted IT and cybersecurity bids across {portal_focus}.}}}} "
        f"{spintax_relevance_1}\n\n"
        f"{payload_text}"
        f"{recompete_and_sub_step1}\n"
        f"{{{{RANDOM | Our classifier strips out 99% of commodity hardware, toner, sole-source, and COTS renewal noise so capture teams only see net-new services and engineering scopes. | "
        f"Everything is pre-filtered to remove low-value maintenance renewals and hardware reselling so your team only sees actionable IT & cyber RFPs. | "
        f"Each solicitation is de-duplicated every 6 hours and pre-shredded with NAICS, SBA size caps, compliance posture, and teaming requirements.}}}}\n\n"
        f"{{{{RANDOM | {step1_ctas[0]} | {step1_ctas[1]} | {step1_ctas[2]}}}}}\n\n"
        f"{{{{RANDOM | Best, | Regards, | Best regards,}}}}\nAaron Chen\nFounder, SignalTender"
    )
    spintax_body_2 = (
        f"{spintax_greeting}\n\n"
        f"{{{{RANDOM | Quick follow-up in case {clean_comp} is expanding its {region_label} capture pipeline this quarter. | "
        f"Following up briefly on the {region_label} IT solicitations I sent over earlier this week. | "
        f"Circling back with one quick note in case your team tracks Federal or State SLED IT & cybersecurity bids.}}}}\n\n"
        f"{ step2_tiers[0] }\n\n"
        f"{{{{RANDOM | You can create a Free Explorer Account ($0/mo — no credit card required) to save your state/NAICS filters and Capture Vault at: | "
        f"Claim a Free Explorer Account ($0/mo) in our Client Portal to track bids and test all 39 AI APIs at:}}}}\n{clean_portal_url}\n\n"
        f"{{{{RANDOM | Or activate full 6-hour dispatches (Tier 1 $99/mo, Tier 2 $399/mo, Tier 3 Proposal .ZIP $1,499/mo, or Tier 4 FOIA/OEM $2,499/mo) in 60 seconds here: | "
        f"Or start a month-to-month Tier 1 ($99/mo), Tier 2 ($399/mo), Tier 3 ($1,499/mo), or Tier 4 ($2,499/mo) plan anytime at:}}}}\n{clean_checkout_url}\n\n"
        f"{{{{RANDOM | No contracts or onboarding calls—cancel anytime in 1 click. | 100% self-serve, FAR 31.205-18 allowable B&P expense, no demos required.}}}}\n\n"
        f"{{{{RANDOM | Best, | Regards, | Best regards,}}}}\nAaron Chen\nFounder, SignalTender"
    )

    step3_subject = f"Re: {step1_subject}"
    step3_bodies = [
        (
            f"{_pick_variant(seed, 13, greetings)}\n\n"
            f"Last note from me so I don't clutter your inbox.\n\n"
            f"If {clean_comp} has a live SAM.gov or {region_label} RFP on your desk this week, reply with the Solicitation Number (or 'ZIP' for #1 from my first note) and I'll run a complete 6-file Shipley .DOCX/.XLSX proposal + Section L/M compliance shred for your team on the house so you can benchmark it against your current process.\n\n"
            f"Otherwise, you can always use the pre-loaded 6-File Proposal .ZIP Compiler ({compiler_deeplink_url}) or Free Explorer Portal ({clean_portal_url}) anytime.\n\n"
            f"{_pick_variant(seed, 14, signoffs)}"
        ),
        (
            f"{_pick_variant(seed, 13, greetings)}\n\n"
            f"Closing the loop on this—I won't follow up again unless I hear from you.\n\n"
            f"If your capture team is evaluating any Federal or {region_label} IT solicitation right now, reply with the Solicitation ID (or 'ZIP') and I will generate the 6-file Shipley Proposal .ZIP (Word .docx Vol I/III + live-formula Excel .xlsx Vol II Cost Model) for {clean_comp} at no cost.\n\n"
            f"Direct pre-loaded compiler link: {compiler_deeplink_url} | Free Explorer Portal ($0/mo): {clean_portal_url}\n\n"
            f"{_pick_variant(seed, 14, signoffs)}"
        ),
    ]
    step3_body = _pick_variant(seed, 15, step3_bodies)

    return {
        "Subject Line": step1_subject,
        "Email Body": step1_body,
        "Followup Subject": step2_subject,
        "Followup Body": step2_body,
        "Breakup Subject": step3_subject,
        "Breakup Body": step3_body,
        "Spintax Subject 1": spintax_subject_1,
        "Spintax Body 1": spintax_body_1,
        "Spintax Body 2": spintax_body_2,
        "Matched State": region_label,
        "Top Contract Dossier URL": clean_dossier_url,
        "Compiler Deep-Link URL": compiler_deeplink_url,
        "Incumbent Award Hook": incumbent_hook_str,
        "Mailbox Pool Slot": str(shard_meta["mailbox_pool_slot"]),
        "Mailbox Shard ID": str(shard_meta["mailbox_shard_id"]),
        "Top Contract NAICS": (top_intel or {}).get("primary_naics", "541512 — Computer Systems Design Services"),
        "Top Contract Posture": f"{(top_intel or {}).get('compliance_posture', '')} | {(top_intel or {}).get('teaming_posture', '')}".strip(" |"),
        "Target Segment": target_segment,
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

    # 1. Instantly.ai V2 REST API Integration (Auto-Lead Sync + November Daily Limit Ramp + Oct 31 Auto-Activation)
    if INSTANTLY_API_KEY and INSTANTLY_CAMPAIGN_ID:
        try:
            from datetime import timezone
            import outbound_mailer

            inst_headers = {
                "Authorization": f"Bearer {INSTANTLY_API_KEY}",
                "Content-Type": "application/json",
            }
            now_utc = datetime.now(timezone.utc)
            daily_cap, _, ramp_label = outbound_mailer.compute_dynamic_daily_limit(now_utc)

            # Sync dynamic daily_limit, WARMED sending accounts only (>=14d & score>=85), start_date, and active status
            warmed_account_emails = []
            warming_only_emails = []
            graduated_to_disable_warmup = []
            premature_to_reenable_warmup = []
            try:
                acc_resp = requests.get(
                    "https://api.instantly.ai/api/v2/accounts?limit=100",
                    headers=inst_headers,
                    timeout=10,
                )
                if acc_resp.status_code == 200:
                    acc_items = (acc_resp.json() or {}).get("items") or []
                    for a in acc_items:
                        if not isinstance(a, dict) or not a.get("email"):
                            continue
                        em_addr = str(a.get("email") or "").strip()
                        if outbound_mailer.is_instantly_account_warmed(a):
                            warmed_account_emails.append(em_addr)
                            if int(a.get("warmup_status") or 0) == 1:
                                graduated_to_disable_warmup.append(em_addr)
                        else:
                            warming_only_emails.append(em_addr)
                            if int(a.get("warmup_status") or 0) == 0:
                                premature_to_reenable_warmup.append(em_addr)
                    if premature_to_reenable_warmup:
                        try:
                            requests.post(
                                "https://api.instantly.ai/api/v2/accounts/warmup/enable",
                                headers=inst_headers,
                                json={"emails": premature_to_reenable_warmup},
                                timeout=10,
                            )
                            print(
                                f"[+] Re-enabled warmup on {len(premature_to_reenable_warmup)} mailbox(es) under 14 days old ({', '.join(premature_to_reenable_warmup)}).",
                                flush=True,
                            )
                        except Exception:
                            pass
                    if False and graduated_to_disable_warmup:
                        try:
                            requests.post(
                                "https://api.instantly.ai/api/v2/accounts/warmup/enable",
                                headers=inst_headers,
                                json={"emails": graduated_to_disable_warmup},
                                timeout=10,
                            )
                            print(
                                f"[+] Auto-disabled warmup on {len(graduated_to_disable_warmup)} graduated mailbox(es) (>=14d & score>=85) ({', '.join(graduated_to_disable_warmup)}).",
                                flush=True,
                            )
                        except Exception:
                            pass
                    if warming_only_emails:
                        print(
                            f"[*] Warmup Guard: Keeping {len(warming_only_emails)} new mailbox(es) in Warmup-Only mode until >=14 days & score >= 85 ({', '.join(warming_only_emails)}).",
                            flush=True,
                        )
            except Exception:
                pass

            camp_resp = requests.get(
                f"https://api.instantly.ai/api/v2/campaigns/{INSTANTLY_CAMPAIGN_ID}",
                headers=inst_headers,
                timeout=15,
            )
            if camp_resp.status_code == 200:
                camp_data = camp_resp.json()
                patch_camp: dict = {}
                if int(camp_data.get("daily_limit") or 0) != daily_cap:
                    patch_camp["daily_limit"] = daily_cap
                if warmed_account_emails and set(camp_data.get("email_list") or []) != set(warmed_account_emails):
                    patch_camp["email_list"] = warmed_account_emails
                # Ensure 3-step sequence (Step 1 Day 0 -> Step 2 Day +3 -> Step 3 Day +7 Concierge Breakup) is wired
                seqs = camp_data.get("sequences") or []
                cur_steps = (seqs[0].get("steps") or []) if seqs and isinstance(seqs[0], dict) else []
                if len(cur_steps) < 3:
                    patch_camp["sequences"] = [
                        {
                            "steps": [
                                {
                                    "type": "email",
                                    "delay": 3,
                                    "delay_unit": "days",
                                    "pre_delay_unit": "days",
                                    "variants": [{"subject": "{{subject_line}}", "body": "{{email_body}}"}],
                                },
                                {
                                    "type": "email",
                                    "delay": 4,
                                    "delay_unit": "days",
                                    "pre_delay_unit": "days",
                                    "variants": [{"subject": "{{followup_subject}}", "body": "{{followup_body}}"}],
                                },
                                {
                                    "type": "email",
                                    "delay": 4,
                                    "delay_unit": "days",
                                    "pre_delay_unit": "days",
                                    "variants": [{"subject": "{{breakup_subject}}", "body": "{{breakup_body}}"}],
                                },
                            ]
                        }
                    ]
                sched = camp_data.get("campaign_schedule") or {}
                if str(sched.get("start_date") or "") > "2026-10-25":
                    sched["start_date"] = "2026-10-24"
                    for s_item in (sched.get("schedules") or []):
                        if isinstance(s_item, dict) and isinstance(s_item.get("days"), dict):
                            s_item["days"]["0"] = True
                            s_item["days"]["6"] = True
                    patch_camp["campaign_schedule"] = sched
                if patch_camp:
                    requests.patch(
                        f"https://api.instantly.ai/api/v2/campaigns/{INSTANTLY_CAMPAIGN_ID}",
                        headers=inst_headers,
                        json=patch_camp,
                        timeout=15,
                    )
                # Ensure campaign is Active (status == 1) now that domains are 100% warmed
                if int(camp_data.get("status") or 0) != 1:
                    act_resp = requests.post(
                        f"https://api.instantly.ai/api/v2/campaigns/{INSTANTLY_CAMPAIGN_ID}/activate",
                        headers=inst_headers,
                        json={},
                        timeout=15,
                    )
                    if 200 <= act_resp.status_code < 300:
                        print(f"[+] Activated Instantly.ai campaign {INSTANTLY_CAMPAIGN_ID} (status=ACTIVE, daily_limit={daily_cap})!", flush=True)

            # Fetch existing emails in campaign to avoid redundant uploads on 6-hour cron runs
            # CRITICAL: Never delete active in-flight leads (`has_started_sequence`) before they complete Step 2 & Step 3!
            import govcon_lead_harvester
            existing_inst_emails = set()
            existing_inst_ids = {}
            unsent_inst_ids = {}
            in_flight_inst_emails = set()
            replied_inst_emails = set()
            completed_non_responders: list[tuple[str, str]] = []
            non_it_or_invalid_to_purge: list[tuple[str, str]] = []
            starting_after = None
            for _ in range(10):
                list_body = {"campaign": INSTANTLY_CAMPAIGN_ID, "limit": 100}
                if starting_after:
                    list_body["starting_after"] = starting_after
                l_resp = requests.post(
                    "https://api.instantly.ai/api/v2/leads/list",
                    headers=inst_headers,
                    json=list_body,
                    timeout=15,
                )
                if l_resp.status_code != 200:
                    break
                l_json = l_resp.json()
                items = l_json.get("items") or []
                for it in items:
                    em = str(it.get("email") or "").strip().lower()
                    lid = str(it.get("id") or "").strip()
                    comp_it = str(it.get("company_name") or "").strip()
                    if em:
                        existing_inst_emails.add(em)
                        if lid:
                            existing_inst_ids[em] = lid
                            lead_status = int(it.get("status") or 0)
                            interest_status = int(it.get("lt_interest_status") or 0)
                            reply_cnt = int(it.get("email_reply_count") or 0)
                            last_step = (it.get("status_summary") or {}).get("lastStep")
                            has_started_sequence = bool(last_step) or int(it.get("email_open_count") or 0) > 0 or int(it.get("email_click_count") or 0) > 0
                            if interest_status < 0 or lead_status in (-1, -2, -3):
                                completed_non_responders.append((em, lid))
                            elif reply_cnt > 0 or interest_status > 0:
                                replied_inst_emails.add(em)
                            elif lead_status == 3:
                                completed_non_responders.append((em, lid))
                            elif not govcon_lead_harvester.is_verified_it_cyber_prospect(comp_it, em):
                                non_it_or_invalid_to_purge.append((em, lid))
                            elif has_started_sequence:
                                in_flight_inst_emails.add(em)
                            else:
                                unsent_inst_ids[em] = lid
                starting_after = l_json.get("next_starting_after")
                if not starting_after or len(items) < 100:
                    break

            from concurrent.futures import ThreadPoolExecutor
            auth_only_headers = {"Authorization": f"Bearer {INSTANTLY_API_KEY}"}
            valid_email_set = (
                {str(item.get("Email") or "").strip().lower() for item in leads_payload}
                | replied_inst_emails
                | in_flight_inst_emails
            )
            archive_to_save = {em for em, _ in completed_non_responders} | {em for em, _ in non_it_or_invalid_to_purge}
            if archive_to_save:
                try:
                    govcon_lead_harvester.save_completed_outreach_archive(archive_to_save)
                except Exception:
                    pass
                for c_em in archive_to_save:
                    valid_email_set.discard(c_em)

            # Only delete leads that: (a) completed all 3 steps / bounced / unsubscribed, (b) failed IT/Cyber verification,
            # or (c) are still unsent (`not_sent_yet`) and no longer in `valid_email_set`.
            # In-flight leads (`in_flight_inst_emails`) are NEVER deleted mid-sequence!
            stale_pairs_dict: dict[str, str] = {}
            for em, lid in completed_non_responders + non_it_or_invalid_to_purge:
                stale_pairs_dict[em] = lid
            for em, lid in unsent_inst_ids.items():
                if em not in valid_email_set:
                    stale_pairs_dict[em] = lid
            stale_pairs = list(stale_pairs_dict.items())
            if stale_pairs:
                def _del_stale(pair: tuple[str, str]) -> int:
                    s_em, s_id = pair
                    try:
                        r_del = requests.delete(
                            f"https://api.instantly.ai/api/v2/leads/{s_id}",
                            headers=auth_only_headers,
                            timeout=10,
                        )
                        if 200 <= r_del.status_code < 300:
                            existing_inst_emails.discard(s_em)
                            existing_inst_ids.pop(s_em, None)
                            unsent_inst_ids.pop(s_em, None)
                            return 1
                    except Exception:
                        pass
                    return 0

                with ThreadPoolExecutor(max_workers=10) as pool:
                    del_count = sum(pool.map(_del_stale, stale_pairs))
                print(
                    f"[+] Rotated/purged {del_count}/{len(stale_pairs)} completed, bounced, or non-IT leads from Instantly.ai V2 (preserved {len(in_flight_inst_emails)} active in-flight leads waiting for Step 2/Step 3).",
                    flush=True,
                )

            target_patch_ids = existing_inst_ids if os.getenv("OUTREACH_FORCE_INSTANTLY_RESYNC") == "1" else unsent_inst_ids
            if target_patch_ids:
                def _patch_one_lead(item_row: dict) -> int:
                    em_key = str(item_row.get("Email") or "").strip().lower()
                    lid = target_patch_ids.get(em_key)
                    if not lid:
                        return 0
                    patch_payload = {
                        "first_name": item_row["First Name"],
                        "company_name": clean_company_for_copy(item_row["Company"]),
                        "custom_variables": {
                            "subject_line": item_row["Subject Line"],
                            "email_body": item_row["Email Body"],
                            "followup_subject": item_row.get("Followup Subject", ""),
                            "followup_body": item_row.get("Followup Body", ""),
                            "breakup_subject": item_row.get("Breakup Subject", ""),
                            "breakup_body": item_row.get("Breakup Body", ""),
                            "spintax_subject_1": item_row.get("Spintax Subject 1", ""),
                            "spintax_body_1": item_row.get("Spintax Body 1", ""),
                            "spintax_body_2": item_row.get("Spintax Body 2", ""),
                            "matched_state": item_row.get("Matched State", ""),
                            "top_dossier_url": item_row.get("Top Contract Dossier URL", ""),
                            "target_segment": item_row.get("Target Segment", "PRIME_PROPOSAL_AUTOPILOT"),
                        },
                    }
                    try:
                        r_patch = requests.patch(
                            f"https://api.instantly.ai/api/v2/leads/{lid}",
                            headers=inst_headers,
                            json=patch_payload,
                            timeout=12,
                        )
                        return 1 if 200 <= r_patch.status_code < 300 else 0
                    except Exception:
                        return 0

                with ThreadPoolExecutor(max_workers=10) as pool:
                    updated_ok = sum(pool.map(_patch_one_lead, leads_payload))
                if updated_ok:
                    print(f"[+] Refreshed custom_variables on {updated_ok} unsent/existing leads in Instantly.ai V2.", flush=True)

            max_instantly_active_buffer = int(
                os.getenv("INSTANTLY_MAX_ACTIVE_BUFFER")
                or max(950, len(warmed_account_emails) * 150)
            )
            available_slots = max(0, max_instantly_active_buffer - len(existing_inst_emails))
            new_leads_to_push = [
                item for item in leads_payload
                if str(item.get("Email") or "").strip().lower() not in existing_inst_emails
                and str(item.get("Email") or "").strip().lower() in valid_email_set
            ][:available_slots]
            if new_leads_to_push:
                print(
                    f"[*] Pushing {len(new_leads_to_push)} new verified leads to Instantly.ai V2 campaign {INSTANTLY_CAMPAIGN_ID} ({ramp_label})...",
                    flush=True,
                )
                def _add_one_lead(item: dict) -> int:
                    lead_payload = {
                        "campaign": INSTANTLY_CAMPAIGN_ID,
                        "email": item["Email"].strip().lower(),
                        "first_name": item["First Name"],
                        "company_name": item["Company"],
                        "skip_if_in_workspace": True,
                        "custom_variables": {
                            "subject_line": item["Subject Line"],
                            "email_body": item["Email Body"],
                            "followup_subject": item.get("Followup Subject", ""),
                            "followup_body": item.get("Followup Body", ""),
                            "breakup_subject": item.get("Breakup Subject", ""),
                            "breakup_body": item.get("Breakup Body", ""),
                            "spintax_subject_1": item.get("Spintax Subject 1", ""),
                            "spintax_body_1": item.get("Spintax Body 1", ""),
                            "spintax_body_2": item.get("Spintax Body 2", ""),
                            "matched_state": item.get("Matched State", ""),
                            "top_dossier_url": item.get("Top Contract Dossier URL", ""),
                            "target_segment": item.get("Target Segment", "PRIME_PROPOSAL_AUTOPILOT"),
                        },
                    }
                    try:
                        r_add = requests.post(
                            "https://api.instantly.ai/api/v2/leads",
                            headers=inst_headers,
                            json=lead_payload,
                            timeout=12,
                        )
                        if r_add.status_code in (402, 403) or (r_add.status_code >= 400 and "limit" in (r_add.text or "").lower()):
                            return -1
                        return 1 if 200 <= r_add.status_code < 300 else 0
                    except Exception:
                        return 0

                with ThreadPoolExecutor(max_workers=10) as pool:
                    results_list = list(pool.map(_add_one_lead, new_leads_to_push))
                pushed_ok = sum(1 for x in results_list if x == 1)
                if any(x == -1 for x in results_list) and DISCORD_WEBHOOK_URL:
                    try:
                        requests.post(
                            DISCORD_WEBHOOK_URL,
                            json={
                                "content": (
                                    "**[ACTION REQUIRED // INSTANTLY.AI PLAN LIMIT REACHED — TIME TO UPGRADE]**\n"
                                    f"• **Status:** Instantly V2 rejected lead upload due to active-contact plan limit (`{len(existing_inst_emails)}` active leads).\n"
                                    "• **Action:** Upgrade to **Hypergrowth ($97/mo — 25,000 active contacts & 100,000 emails/mo)** at https://app.instantly.ai/app/settings/billing and set `INSTANTLY_PLAN_TIER=hypergrowth` + `INSTANTLY_MAX_ACTIVE_BUFFER=25000` in `.env`."
                                ),
                                "flags": 4,
                            },
                            timeout=10,
                        )
                    except Exception:
                        pass
                print(
                    f"[+] Synced {pushed_ok}/{len(new_leads_to_push)} new leads to Instantly.ai V2 (Total in campaign: {len(existing_inst_emails) + pushed_ok} | Daily Limit: {daily_cap}).",
                    flush=True,
                )
            else:
                print(
                    f"[+] Instantly.ai V2 campaign {INSTANTLY_CAMPAIGN_ID} already up to date ({len(existing_inst_emails)} leads | {ramp_label}).",
                    flush=True,
                )
        except Exception as inst_err:
            err_msg = f"Instantly.ai V2 API sync warning: {inst_err}"
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
            .limit(500)
            .execute()
        )
        records = response.data if response and getattr(response, "data", None) else []

        if not records:
            print("[!] No contracts found in Supabase.", flush=True)
            return

        today = datetime.now().date()
        tech_contracts = []
        expired_skipped = 0
        rfp_dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contracts", "rfp")
        has_local_rfp_dir = os.path.isdir(rfp_dir_path)

        for rec in records:
            if str(rec.get("url") or "").startswith(("subscriber://", "treasury://")) or str(rec.get("status") or "").startswith("SUBSCRIBER_"):
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
            if has_local_rfp_dir:
                cand_slug = slugify_contract(title, fallback_id=str(rec.get("id") or ""))
                if not os.path.exists(os.path.join(rfp_dir_path, f"{cand_slug}.html")):
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

        intel_summary = {}
        if os.getenv("OUTREACH_SKIP_HARVESTER") != "1":
            try:
                import govcon_lead_harvester
                intel_summary = govcon_lead_harvester.run_harvester() or {}
            except Exception as harv_err:
                print(f"[!] GovCon Lead Harvester warning: {harv_err}", flush=True)

        if not intel_summary and os.path.exists("govcon_prospect_intelligence.json"):
            try:
                with open("govcon_prospect_intelligence.json", "r", encoding="utf-8") as jf:
                    intel_summary = json.load(jf) or {}
            except Exception:
                intel_summary = {}

        company_award_profiles = intel_summary.get("company_award_profiles") or {}
        expiring_recompetes = intel_summary.get("expiring_recompete_wire") or []
        fresh_prime_sub_wire = intel_summary.get("fresh_prime_subcontracting_wire") or []

        contacts_file = "govcon_contacts.csv"
        output_file = "campaign_leads.csv"
        whop_checkout_url = os.getenv(
            "STRIPE_CHECKOUT_URL",
            f"{SITE_BASE_URL}/index.html#checkout",
        )

        if not os.path.exists(contacts_file):
            print(f"[!] Missing '{contacts_file}' in D:\\Daas", flush=True)
            return

        print("[*] Reading verified GovCon contacts and generating anti-spam Spintax 2-step sequences (Tier 1 $99/mo, Tier 2 $399/mo, Tier 3 $1,499/mo & Tier 4 $2,499/mo)...", flush=True)

        leads_for_api = []

        with open(contacts_file, mode="r", encoding="utf-8-sig") as infile, \
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
                "Breakup Subject",
                "Breakup Body",
                "Spintax Subject 1",
                "Spintax Body 1",
                "Spintax Body 2",
                "Matched State",
                "Top Contract Dossier URL",
                "Compiler Deep-Link URL",
                "Incumbent Award Hook",
                "Mailbox Pool Slot",
                "Mailbox Shard ID",
                "Top Contract NAICS",
                "Top Contract Posture",
                "Target Segment",
            ]
            writer = csv.DictWriter(outfile, fieldnames=out_fieldnames)
            writer.writeheader()

            raw_contact_rows = list(reader)

            def _resolve_comp_award(comp_str: str) -> dict | None:
                try:
                    from govcon_lead_harvester import _normalize_company_tokens
                    _, _, c_key = _normalize_company_tokens(comp_str)
                    return company_award_profiles.get(c_key)
                except Exception:
                    return None

            def _lead_priority_key(r: dict) -> tuple[int, int, int, int, int]:
                catchall_rank = 0 if str(r.get("Primary Email Catch-all Status") or "").strip().lower() == "not catch-all" else 1
                comp_val = str(r.get(company_key) or "").strip()
                awd_prof = _resolve_comp_award(comp_val)
                award_rank = 0 if (awd_prof and awd_prof.get("is_active")) else (1 if awd_prof else 2)
                naics_str = str(r.get("NAICS Codes") or "")
                pure_govcon_rank = 0 if "541715" not in naics_str else 1
                em_local = str(r.get(email_key) or "").strip().lower().split("@", 1)[0]
                fn_low = str(r.get(first_name_key) or "").strip().lower()
                # Rank 0: personal firstname.lastname@ or dedicated capture/contracts/BD/growth inbox
                if "." in em_local or any(k in em_local for k in ("contract", "capture", "bd", "bizdev", "growth", "partner", "stars", "gov", "engage")):
                    inbox_rank = 0
                elif any(k in em_local for k in ("sales", "hello", "contact")):
                    inbox_rank = 1
                else:
                    inbox_rank = 2
                person_rank = 1 if fn_low in GENERIC_PERSON_NAMES else 0
                return (catchall_rank, award_rank, pure_govcon_rank, inbox_rank, person_rank)

            # Prioritize "Not Catch-all" + Verified Active USAspending Award ID + pure GovCon IT/Cyber contractors + named/capture inboxes first
            raw_contact_rows.sort(key=_lead_priority_key)

            try:
                from govcon_lead_harvester import (
                    verify_email_domain_mx,
                    _load_mx_cache,
                    _save_mx_cache,
                    _is_strict_company_match,
                    is_verified_it_cyber_prospect,
                )
                mx_cache = _load_mx_cache()
            except Exception:
                verify_email_domain_mx = None
                _is_strict_company_match = None
                is_verified_it_cyber_prospect = None
                mx_cache = {}

            count = 0
            award_personalized_count = 0
            for row in raw_contact_rows:
                fname = (row.get(first_name_key) or "").strip() or "There"
                company = (row.get(company_key) or "").strip() or "your team"
                email = (row.get(email_key) or "").strip()
                prospect_state = (row.get(state_key) or "").strip() if state_key else ""

                if not email:
                    continue
                if is_verified_it_cyber_prospect is not None and not is_verified_it_cyber_prospect(
                    company, email, str(row.get("Keywords") or ""), str(row.get("NAICS Codes") or "")
                ):
                    continue
                if verify_email_domain_mx is not None and not verify_email_domain_mx(email, mx_cache):
                    continue

                matched_contracts = select_contracts_for_prospect(tech_contracts, prospect_state, max_count=3)
                bid_count = len(matched_contracts)
                payload_text = "".join(format_contract_line(i, r, cached_dossiers) for i, r in enumerate(matched_contracts, 1))
                top_intel = resolve_contract_intelligence(matched_contracts[0], cached_dossiers) if matched_contracts else None
                award_profile = _resolve_comp_award(company)
                if award_profile:
                    award_personalized_count += 1

                recompete_candidates = [
                    rc for rc in expiring_recompetes
                    if not (_is_strict_company_match and _is_strict_company_match(company, str(rc.get("incumbent_recipient") or "")))
                ]
                subcontract_candidates = [
                    sc for sc in fresh_prime_sub_wire
                    if not (_is_strict_company_match and _is_strict_company_match(company, str(sc.get("prime_recipient") or "")))
                ]
                row_seed = f"{email.lower().strip()}::{company.lower().strip()}"
                recompete_item = _pick_variant(row_seed, 21, recompete_candidates) if recompete_candidates else None
                subcontract_item = _pick_variant(row_seed, 22, subcontract_candidates) if subcontract_candidates else None

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
                    award_profile=award_profile,
                    recompete_item=recompete_item,
                    subcontract_item=subcontract_item,
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
            f"({award_personalized_count}/{count} with exact USAspending Award IDs + Recompete & Subcontracting Wire) in {output_file}.",
            flush=True,
        )

        # Trigger Option C Zero-Touch Cold Email API Sync if credentials are set in .env
        sync_leads_to_cold_email_api(leads_for_api)

        # Trigger Built-In Outbound Drip Mailer / Outbox Stager
        try:
            import outbound_mailer
            outbound_mailer.run_outbound_mailer()
        except Exception as mail_err:
            print(f"[!] Outbound Mailer warning: {mail_err}", flush=True)

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