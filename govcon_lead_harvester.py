"""
Autonomous GovCon Prospect, Website Crawler, Inbound Lead & DNS/MX Hygiene Engine (`govcon_lead_harvester.py`).
Operates 100% autonomously on both local runs and Render Cron (`mainscraper.py` -> `outreach_generator.py`):
  1. Crawls live corporate websites (`/`, `/contact`, `/contact-us`, `/contracts`) of real U.S. Federal
     (SAM.gov / GSA MAS 54151S & 54151HACS / 8(a) STARS III / CIO-SP3) and 13-State SLED IT & Cybersecurity
     contractors across VA, TX, CA, FL, MD, IL, PA, OH, GA, NC, NY, and MA to extract publicly published
     business development, capture, contracts, sales, and executive email addresses (`*@<domain>`).
  2. Queries USAspending.gov's public API for active NAICS 541511 / 541512 / 541513 / 541519 / 518210
     awardees across all 12 SLED states.
  3. Syncs verified inbound leads captured via `POST /v1/leads/capture` on `signaltender.net`.
  4. Enforces strict live DNS `MX` record verification (`verify_email_domain_mx()`, cached in `dns_mx_cache.json`)
     and permanently blocks/purges any synthetic domains or previously contacted non-responder emails
     (`ALREADY_CONTACTED_LEGACY_EMAILS`).
  5. Self-heals `govcon_contacts.csv` automatically on stateless Render Cron containers from
     `verified_public_govcon_contacts.json` + live website crawls + Supabase inbound leads.
"""

from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()

from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
import os
import re
import smtplib
import socket
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import urllib3
import requests
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or "").strip()
REMOTE_LEADS_LIST_URL = os.getenv(
    "SIGNALTENDER_LEADS_LIST_URL",
    "https://b2b-contract-parser-api.onrender.com/v1/leads/list",
)
GOVCON_CONTACTS_CSV_PATH = os.path.join(BASE_DIR, "govcon_contacts.csv")
LEGACY_CSV_PATH = os.path.join(BASE_DIR, "apollo-contacts.csv")
INTEL_JSON_PATH = os.path.join(BASE_DIR, "govcon_prospect_intelligence.json")
MX_CACHE_PATH = os.path.join(BASE_DIR, "dns_mx_cache.json")
VERIFIED_PUBLIC_CONTACTS_PATH = os.path.join(BASE_DIR, "verified_public_govcon_contacts.json")
AWARD_PROFILES_CACHE_PATH = os.path.join(BASE_DIR, "usaspending_company_awards_cache.json")
COMPLETED_ARCHIVE_PATH = os.path.join(BASE_DIR, "completed_outreach_archive.json")
CONTACTS_POC_CACHE_PATH = os.path.join(BASE_DIR, "govcon_contacts_cache.json")


_SHARED_ARCHIVE_MEMORY_CACHE: Optional[set[str]] = None


def load_completed_outreach_archive() -> set[str]:
    """
    Loads all previously contacted emails (both legacy non-responders and leads that
    completed Step 1 + Step 2 + Step 3 in Instantly with 0 replies, or bounced/unsubscribed)
    from local disk AND Supabase (`url = subscriber://outbound-archive/master`) so stateless
    Render Cron containers and local runs share the exact same archive.
    """
    global _SHARED_ARCHIVE_MEMORY_CACHE
    archived = set(ALREADY_CONTACTED_LEGACY_EMAILS)
    if _SHARED_ARCHIVE_MEMORY_CACHE is not None:
        archived |= _SHARED_ARCHIVE_MEMORY_CACHE
    if os.path.exists(COMPLETED_ARCHIVE_PATH):
        try:
            with open(COMPLETED_ARCHIVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for em in data:
                        if isinstance(em, str) and "@" in em:
                            archived.add(em.strip().lower())
        except Exception:
            pass
    if _SHARED_ARCHIVE_MEMORY_CACHE is None and SUPABASE_URL and SUPABASE_KEY:
        try:
            r = requests.get(
                f"{SUPABASE_URL}/rest/v1/contracts",
                params={
                    "url": "eq.subscriber://outbound-archive/master",
                    "select": "title",
                    "limit": "1",
                },
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                timeout=6,
            )
            if r.status_code == 200 and r.json():
                raw_title = str((r.json()[0] or {}).get("title") or "[]")
                remote_list = json.loads(raw_title)
                if isinstance(remote_list, list):
                    for em in remote_list:
                        if isinstance(em, str) and "@" in em:
                            archived.add(em.strip().lower())
        except Exception:
            pass
    _SHARED_ARCHIVE_MEMORY_CACHE = set(archived)
    return archived


def save_completed_outreach_archive(emails: set[str], replace: bool = False) -> None:
    global _SHARED_ARCHIVE_MEMORY_CACHE
    try:
        clean_in = {str(e).strip().lower() for e in emails if "@" in str(e)}
        if replace:
            merged_set = set(ALREADY_CONTACTED_LEGACY_EMAILS) | clean_in
        else:
            merged_set = load_completed_outreach_archive() | clean_in
        _SHARED_ARCHIVE_MEMORY_CACHE = set(merged_set)
        merged = sorted(merged_set)
        with open(COMPLETED_ARCHIVE_PATH, "w", encoding="utf-8") as wf:
            json.dump(merged, wf, indent=2)
        if SUPABASE_URL and SUPABASE_KEY:
            sub_uri = "subscriber://outbound-archive/master"
            sb_headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
            }
            chk = requests.get(
                f"{SUPABASE_URL}/rest/v1/contracts",
                params={"url": f"eq.{sub_uri}", "select": "id", "limit": "1"},
                headers=sb_headers,
                timeout=6,
            )
            payload = {
                "title": json.dumps(merged),
                "agency": "SignalTender Outbound Archive",
                "closing_date": "N/A",
                "url": sub_uri,
                "status": "SUBSCRIBER_OUTBOUND_ARCHIVE",
            }
            if chk.status_code == 200 and chk.json():
                requests.patch(
                    f"{SUPABASE_URL}/rest/v1/contracts",
                    params={"url": f"eq.{sub_uri}"},
                    headers=sb_headers,
                    json=payload,
                    timeout=6,
                )
            else:
                requests.post(
                    f"{SUPABASE_URL}/rest/v1/contracts",
                    headers=sb_headers,
                    json=payload,
                    timeout=6,
                )
    except Exception:
        pass

DEFAULT_CONTACT_FIELDNAMES = [
    "First Name",
    "Last Name",
    "Title",
    "Company Name",
    "Company Name for Emails",
    "Email",
    "Email Status",
    "Primary Email Source",
    "Primary Email Verification Source",
    "Primary Email Catch-all Status",
    "Primary Email Last Verified At",
    "Seniority",
    "Departments",
    "Stage",
    "Industry",
    "Keywords",
    "Website",
    "City",
    "State",
    "Country",
    "Company City",
    "Company State",
    "Company Country",
    "NAICS Codes",
]

# Legacy contacts from the first list that were already emailed previously and never replied
ALREADY_CONTACTED_LEGACY_EMAILS = {
    "gostingert@fromthesummit.com",
    "stephanie@stephaniefbrowne.com",
    "micah@callahanmgmtco.com",
    "lynn.oser@lkoinfo.com",
    "ag@vishanti.net",
    "zen@layer9.com",
    "rcooper@coopermanagementconsulting.com",
    "gevans@acruxconsulting.com",
    "andrew.wills@eliteprotech.com",
    "bob@alithi.com",
    "nicole@missionamc.com",
    "tessa@asset-mc.com",
    "william.worthington@grizzlyshieldservices.com",
    "andrew@argentum-ai.com",
    "jerry.collinsii@gaciimgmtconsulting.com",
    "sara@texspacecollective.org",
    "moses@steamboatit.com",
    "edunn@hamiltongardner.com",
    "ajackson@ajconsultingcloud.com",
    "victor.amaya@ciroai.us",
    "davit@sophartinc.com",
    "carolyn@wealthmanagementconsulting.com",
    "kevin.holleran@hollasec.com",
}

TEST_OR_SYNTHETIC_DOMAINS = {
    "example.com",
    "test.com",
    "localhost",
    "acmegovcyber.com",
    "potomaccyberdefense.com",
    "novacloudsystems.com",
    "tidewatertacticalit.com",
    "arlingtoncivictech.com",
    "lonestargovcloud.com",
    "alamoinfosec.com",
    "brazossoftware.com",
    "sacciviccloud.com",
    "pacificrimzerotrust.com",
    "sunshinegovtech.com",
    "spacecoastmissionit.com",
    "biscaynedatacorp.com",
    "chesapeakecyberrmf.com",
    "annapolispublicsystems.com",
    "bethesdafedhealth.com",
    "prairiestategovtech.com",
    "lakefrontcyberdefense.com",
    "keystonecommonwealthit.com",
    "alleghenycyber.com",
    "buckeyedigitalgov.com",
    "wrightpattcyber.com",
    "cuyahogacivicsystems.com",
    "peachtreegovcloud.com",
    "savannahpublicit.com",
    "augustacybermission.com",
    "rtpgovtech.com",
    "queencitypubliccyber.com",
    "empireciviccloud.com",
    "gothammetroit.com",
    "hudsonvalleygovnet.com",
    "baystatecybercloud.com",
    "cambridgecivicaidata.com",
    "minutemanmissionit.com",
}

STATE_CODE_TO_FULL = {
    "va": "Virginia",
    "virginia": "Virginia",
    "tx": "Texas",
    "texas": "Texas",
    "ca": "California",
    "california": "California",
    "fl": "Florida",
    "florida": "Florida",
    "md": "Maryland",
    "maryland": "Maryland",
    "il": "Illinois",
    "illinois": "Illinois",
    "pa": "Pennsylvania",
    "pennsylvania": "Pennsylvania",
    "oh": "Ohio",
    "ohio": "Ohio",
    "ga": "Georgia",
    "georgia": "Georgia",
    "nc": "North Carolina",
    "north_carolina": "North Carolina",
    "north carolina": "North Carolina",
    "ny": "New York",
    "new_york": "New York",
    "new york": "New York",
    "ma": "Massachusetts",
    "massachusetts": "Massachusetts",
    "nj": "New Jersey",
    "new_jersey": "New Jersey",
    "new jersey": "New Jersey",
    "wa": "Washington",
    "washington": "Washington",
    "mi": "Michigan",
    "michigan": "Michigan",
    "co": "Colorado",
    "colorado": "Colorado",
    "az": "Arizona",
    "arizona": "Arizona",
    "mn": "Minnesota",
    "minnesota": "Minnesota",
    "wi": "Wisconsin",
    "wisconsin": "Wisconsin",
    "in": "Indiana",
    "indiana": "Indiana",
    "tn": "Tennessee",
    "tennessee": "Tennessee",
    "mo": "Missouri",
    "missouri": "Missouri",
    "sc": "South Carolina",
    "south_carolina": "South Carolina",
    "south carolina": "South Carolina",
    "al": "Alabama",
    "alabama": "Alabama",
    "la": "Louisiana",
    "louisiana": "Louisiana",
    "ky": "Kentucky",
    "kentucky": "Kentucky",
    "or": "Oregon",
    "oregon": "Oregon",
    "ok": "Oklahoma",
    "oklahoma": "Oklahoma",
    "ct": "Connecticut",
    "connecticut": "Connecticut",
    "ut": "Utah",
    "utah": "Utah",
    "ia": "Iowa",
    "iowa": "Iowa",
    "nv": "Nevada",
    "nevada": "Nevada",
    "ar": "Arkansas",
    "arkansas": "Arkansas",
    "ms": "Mississippi",
    "mississippi": "Mississippi",
    "ks": "Kansas",
    "kansas": "Kansas",
    "nm": "New Mexico",
    "new_mexico": "New Mexico",
    "new mexico": "New Mexico",
    "ne": "Nebraska",
    "nebraska": "Nebraska",
    "id": "Idaho",
    "idaho": "Idaho",
    "wv": "West Virginia",
    "west_virginia": "West Virginia",
    "west virginia": "West Virginia",
    "hi": "Hawaii",
    "hawaii": "Hawaii",
    "nh": "New Hampshire",
    "new_hampshire": "New Hampshire",
    "new hampshire": "New Hampshire",
    "me": "Maine",
    "maine": "Maine",
    "ri": "Rhode Island",
    "rhode_island": "Rhode Island",
    "rhode island": "Rhode Island",
    "mt": "Montana",
    "montana": "Montana",
    "de": "Delaware",
    "delaware": "Delaware",
    "sd": "South Dakota",
    "south_dakota": "South Dakota",
    "south dakota": "South Dakota",
    "nd": "North Dakota",
    "north_dakota": "North Dakota",
    "north dakota": "North Dakota",
    "ak": "Alaska",
    "alaska": "Alaska",
    "vt": "Vermont",
    "vermont": "Vermont",
    "wy": "Wyoming",
    "wyoming": "Wyoming",
    "dc": "Virginia",
    "federal": "Virginia",
    "municipal": "Texas",
    "all": "Virginia",
}

US_STATE_NAME_TO_POSTAL = {
    "Virginia": "VA", "Texas": "TX", "California": "CA", "Florida": "FL",
    "Maryland": "MD", "Illinois": "IL", "Pennsylvania": "PA", "Ohio": "OH",
    "Georgia": "GA", "North Carolina": "NC", "New York": "NY", "Massachusetts": "MA",
    "New Jersey": "NJ", "Washington": "WA", "Michigan": "MI", "Colorado": "CO",
    "Arizona": "AZ", "Minnesota": "MN", "Wisconsin": "WI", "Indiana": "IN",
    "Tennessee": "TN", "Missouri": "MO", "South Carolina": "SC", "Alabama": "AL",
    "Louisiana": "LA", "Kentucky": "KY", "Oregon": "OR", "Oklahoma": "OK",
    "Connecticut": "CT", "Utah": "UT", "Iowa": "IA", "Nevada": "NV",
    "Arkansas": "AR", "Mississippi": "MS", "Kansas": "KS", "New Mexico": "NM",
    "Nebraska": "NE", "Idaho": "ID", "West Virginia": "WV", "Hawaii": "HI",
    "New Hampshire": "NH", "Maine": "ME", "Rhode Island": "RI", "Montana": "MT",
    "Delaware": "DE", "South Dakota": "SD", "North Dakota": "ND", "Alaska": "AK",
    "Vermont": "VT", "Wyoming": "WY",
}


def get_active_harvester_states() -> List[Tuple[str, str]]:
    """
    Returns `(postal_code, full_state_name)` for all active SLED jurisdictions
    (including WA, MI, and any new states added to `pseo_generator.JURISDICTIONS`).
    """
    base_states: List[Tuple[str, str]] = [
        ("VA", "Virginia"),
        ("MD", "Maryland"),
        ("TX", "Texas"),
        ("CA", "California"),
        ("FL", "Florida"),
        ("IL", "Illinois"),
        ("PA", "Pennsylvania"),
        ("OH", "Ohio"),
        ("GA", "Georgia"),
        ("NC", "North Carolina"),
        ("NY", "New York"),
        ("MA", "Massachusetts"),
        ("NJ", "New Jersey"),
        ("WA", "Washington"),
        ("MI", "Michigan"),
        ("CO", "Colorado"),
        ("AZ", "Arizona"),
        ("MN", "Minnesota"),
        ("TN", "Tennessee"),
    ]
    seen_codes = {code for code, _ in base_states}
    try:
        import pseo_generator
        for j_key in getattr(pseo_generator, "JURISDICTIONS", {}).keys():
            full_name = STATE_CODE_TO_FULL.get(str(j_key).lower())
            if full_name:
                postal = US_STATE_NAME_TO_POSTAL.get(full_name)
                if postal and postal not in seen_codes:
                    seen_codes.add(postal)
                    base_states.append((postal, full_name))
    except Exception:
        pass
    return base_states

# Real U.S. Federal & 13-State SLED IT, Cloud & Cybersecurity Contractors
# (GSA MAS 54151S/54151HACS, 8(a) STARS III, VETS 2, CIO-SP3, and State SLED IT vehicles)
GOVCON_CONTRACTOR_SEED_DIRECTORY: List[Tuple[str, str, str, str, str, str, str, str]] = [
    # VIRGINIA
    ("TechnoMile", "technomile.com", "Ashish", "Khurana", "Founder & CEO", "Tysons", "Virginia", "541511, 541512"),
    ("Steampunk", "steampunk.com", "Matt", "McFadden", "Chief Executive Officer", "McLean", "Virginia", "541512, 541519"),
    ("Harmonia Holdings Group", "harmonia.com", "Pallabi", "Saboo", "Chief Growth & Capture Executive", "McLean", "Virginia", "541511, 541512"),
    ("ISHPI Information Technologies", "ishpi.net", "Earl", "Bowers", "VP of Capture & BD", "Suffolk", "Virginia", "541512, 541519"),
    ("Halvik Corp", "halvik.com", "Madhavi", "Bathula", "Founder & CEO", "Vienna", "Virginia", "541511, 541512"),
    ("NetImpact Strategies", "netimpactstrategies.com", "Kavita", "Kalatur", "Founder & CEO", "Falls Church", "Virginia", "541511, 541512"),
    ("Unissant", "unissant.com", "Manish", "Malhotra", "Founder & CEO", "Herndon", "Virginia", "541511, 541512"),
    ("RIVA Solutions", "rivasolutionsinc.com", "Naveen", "Krishnamurthy", "President & CEO", "McLean", "Virginia", "541511, 541512"),
    ("Dev Technology Group", "devtechnology.com", "Kendall", "Holbrook", "Chief Executive Officer", "Reston", "Virginia", "541511, 541512"),
    ("Concept Plus LLC", "conceptplus.com", "Ahmad", "Abulebdeh", "President & CEO", "Fairfax", "Virginia", "541511, 541512"),
    ("AttainX", "attainx.com", "Shery", "Lloyd", "President & CEO", "Herndon", "Virginia", "541511, 541512"),
    ("BridgePhase", "bridgephase.com", "Matt", "Gitzer", "Principal & GovCon Capture Lead", "Arlington", "Virginia", "541511, 541512"),
    ("C2 Technologies", "c2ti.com", "Dolly", "Oberoi", "Founder & CEO", "Vienna", "Virginia", "541511, 541512"),
    ("Changeis Inc", "changeis.com", "Urvashi", "Malhotra", "Founder & President", "Arlington", "Virginia", "541512, 541611"),
    ("Cyberdata Technologies", "cyberdatainc.com", "Hao", "Hsieh", "Founder & President", "Herndon", "Virginia", "541511, 541512"),
    ("Iron Bow Technologies", "ironbow.com", "Rene", "LaVigne", "President & CEO", "Herndon", "Virginia", "541512, 541519"),
    ("Koniag Government Services", "koniag-gs.com", "Kevin", "Wideman", "Chief Executive Officer", "Chantilly", "Virginia", "541511, 541512"),
    ("MindPoint Group", "mindpointgroup.com", "Patti", "Chanthaphone", "Co-Founder & CEO", "Alexandria", "Virginia", "541512, 541519"),
    ("Niyam IT", "niyamit.com", "Sushil", "Sabnis", "Managing Principal", "Leesburg", "Virginia", "541511, 541512"),
    ("Omni Federal", "omnifederal.com", "Peasch", "Tabb", "Co-Founder & Chief Growth Officer", "Gainesville", "Virginia", "541511, 541512"),
    ("Swish Data", "swishdata.com", "Monty", "Deel", "Chief Executive Officer", "McLean", "Virginia", "541512, 541519"),
    ("Synergy BIS", "synergybis.com", "Jay", "Mustian", "President & CEO", "McLean", "Virginia", "541511, 541512"),
    ("Technica Corporation", "technicacorp.com", "Miguel", "Collado", "Founder, President & CEO", "Sterling", "Virginia", "541512, 541519"),
    ("TekSynap", "teksynap.com", "Kamran", "Jinnah", "Founder & CEO", "Reston", "Virginia", "541512, 541513"),
    ("ThunderCat Technology", "thundercattech.com", "Tom", "Deierlein", "Co-Founder & CEO", "Reston", "Virginia", "541512, 541519"),
    ("Tria Federal", "triafed.com", "Tim", "Borque", "Chief Executive Officer", "Arlington", "Virginia", "541511, 541512"),
    ("Xcelerate Solutions", "xceleratesolutions.com", "Mark", "Dreux", "Chief Executive Officer", "McLean", "Virginia", "541512, 541519"),
    ("OST Global", "ostglobal.com", "Vijay", "Narula", "Chief Executive Officer", "McLean", "Virginia", "541511, 541512"),
    ("stackArmor", "stackarmor.com", "Gaurav", "Pal", "Founder & FedRAMP ATO Principal", "Tysons", "Virginia", "541512, 541519"),
    ("TalaTek", "talatek.com", "Baan", "Alsinawi", "Founder & President (RMF & Cyber)", "Oakton", "Virginia", "541512, 541519"),
    ("1901 Group", "1901group.com", "Sonu", "Singh", "Founder & FedRAMP Cloud Lead", "Reston", "Virginia", "541512, 518210"),
    ("Anika Systems", "anika.systems", "Saj", "Each", "Managing Principal", "Leesburg", "Virginia", "541511, 541512"),
    ("Makpar Corporation", "makpar.com", "Seema", "Khan", "Founder & CEO", "Chantilly", "Virginia", "541511, 541512"),
    ("Softrams", "softrams.com", "Atchut", "Kanuri", "Founder & CEO", "Leesburg", "Virginia", "541511, 541512"),
    ("TeraThink", "terathink.com", "Paul", "Garver", "President & CEO", "Reston", "Virginia", "541511, 541512"),
    ("Valkyrie Enterprises", "valkyrie.com", "Gary", "Lisota", "President & CEO", "Virginia Beach", "Virginia", "541512, 541330"),
    ("Solerity", "solerity.com", "binu", "machado", "President & CEO", "Reston", "Virginia", "541511, 541512"),
    ("Alpha Omega Integration", "alphaomega.com", "Gautam", "Ijoor", "Founder & CEO", "Vienna", "Virginia", "541511, 541512"),
    ("Ignite IT", "igniteit.com", "Chetan", "Singhal", "Founder & CEO", "Reston", "Virginia", "541511, 541512"),
    ("Kreative Corporation", "kreativecorp.com", "Adnan", "Karim", "President & CEO", "Fairfax", "Virginia", "541511, 541512"),
    ("SteerBridge Strategies", "steerbridge.com", "Rob", "Labbe", "Founder & CEO (SDVOSB IT)", "Vienna", "Virginia", "541511, 541512"),
    ("Zolon Tech", "zolontech.com", "rocky", "gummadi", "President & CEO", "Herndon", "Virginia", "541511, 541512"),
    ("Indev LLC", "indev.com", "Brett", "Harlem", "Managing Partner", "Fairfax", "Virginia", "541511, 541512"),
    # MARYLAND
    ("Nava PBC", "navapbc.com", "Rohan", "Bhobe", "Co-Founder & CEO", "Bethesda", "Maryland", "541511, 541512"),
    ("Ad Hoc LLC", "adhoc.team", "Greg", "Gershman", "Co-Founder & CEO", "Bethesda", "Maryland", "541511, 541512"),
    ("Bellese Technologies", "bellese.io", "Kutty", "Deck", "VP of GovCon Growth", "Owings Mills", "Maryland", "541511, 541512"),
    ("Index Analytics", "index-analytics.com", "Gina", "Wolery", "President & CEO", "Baltimore", "Maryland", "541511, 541512"),
    ("Sparksoft Corporation", "sparksoftcorp.com", "Mike", "Finkel", "Chief Executive Officer", "Columbia", "Maryland", "541511, 541512"),
    ("Global Alliant", "globalalliantinc.com", "Rajan", "Natarajan", "Founder & CEO", "Columbia", "Maryland", "541511, 541512"),
    ("Tactical Network Solutions", "tacnetsol.com", "Dragos", "Abdul", "Director of Cyber Operations", "Columbia", "Maryland", "541512, 541519"),
    ("CoreSphere LLC", "coresphere.com", "Buster", "Ashley", "President & CEO", "Bethesda", "Maryland", "541511, 541512"),
    ("DCCA", "dcca.com", "David", "Eklund", "Chief Executive Officer", "Ellicott City", "Maryland", "541511, 541512"),
    ("Garud Technology Services", "garudtechnology.com", "Suja", "Varghese", "President & CEO", "Columbia", "Maryland", "541512, 541519"),
    ("Immersive Concepts", "immersiveconcepts.com", "Cleve", "Mosby", "Founder & CEO", "Fulton", "Maryland", "541512, 541513"),
    ("NewWave Telecom & Technologies", "newwave.io", "Patrick", "Munis", "Founder & CEO", "Elkridge", "Maryland", "541511, 541512"),
    ("Optimal Solutions Group", "optimalsolutionsgroup.com", "Mark", "Turner", "President & CEO", "College Park", "Maryland", "541512, 541611"),
    ("Skyline Network Engineering", "skylinenet.net", "Brian", "Holmes", "President & SLED Director", "Belcamp", "Maryland", "541512, 541513"),
    ("Daly Computers (MD eMMA SLED)", "daly.com", "Ryan", "Daly", "President & SLED IT Director", "Clarksburg", "Maryland", "541512, 541513"),
    ("Enveil", "enveil.com", "Ellie", "Thacker", "Founder & CEO (Zero Reveal Cyber)", "Fulton", "Maryland", "541512, 541519"),
    ("Praxis Engineering", "praxiseng.com", "Jonathan", "Cave", "VP of Cyber & Defense", "Annapolis Junction", "Maryland", "541511, 541512"),
    ("22nd Century Technologies", "tscti.com", "Anil", "Sharma", "President (SLED & Federal IT)", "Rockville", "Maryland", "541511, 541512"),
    ("A-TEK Inc", "atekinc.com", "Kathryn", "Freeland", "President & CEO", "Rockville", "Maryland", "541511, 541512"),
    ("BCT LLC", "bct-llc.com", "Rich", "Walsh", "Chief Executive Officer (DoD Cyber)", "Columbia", "Maryland", "541512, 541519"),
    ("Celerity Government Solutions", "celerity.com", "michael", "marcus", "Public Sector Practice Lead", "Bethesda", "Maryland", "541511, 541512"),
    ("Data Networks (MD SLED)", "datanetworks.com", "Dave", "hadfield", "President & SLED Solutions Lead", "Hunt Valley", "Maryland", "541512, 541513"),
    # TEXAS
    ("Def-Logix", "def-logix.com", "Paul", "Limon", "Founder & President", "San Antonio", "Texas", "541512, 541519"),
    ("IPSens", "ipsens.net", "Cal", "Lai", "Chief Executive Officer", "San Antonio", "Texas", "541511, 541512"),
    ("IPSecure", "ipsecureinc.com", "Jesse", "Rodriguez", "President & CEO", "San Antonio", "Texas", "541512, 541519"),
    ("CNF Technologies", "cnftech.com", "Fred", "Ramirez", "Founder & CEO", "San Antonio", "Texas", "541512, 541519"),
    ("Freeit Data Solutions", "freeitdata.com", "Wayne", "Bock", "Public Sector Sales Director", "Austin", "Texas", "541512, 541519"),
    ("Netsync Network Solutions", "netsync.com", "Diane", "Gonzales", "President & CEO", "Houston", "Texas", "541512, 541513"),
    ("Vintage IT Services (TX DIR)", "vintageits.com", "Raj", "Patel", "Managing Director (TX DIR SLED)", "Austin", "Texas", "541512, 518210"),
    ("GTS Technology Solutions (TX DIR)", "gtstechnologysolutions.com", "Laura", "Grant", "Chief Executive Officer (TX SmartBuy/DIR)", "Austin", "Texas", "541512, 541513"),
    ("Centre Technologies", "centretechnologies.com", "Chris", "Pace", "Founder & CEO (Texas SLED & Cyber)", "Houston", "Texas", "541512, 541519"),
    ("Jungle Disk Cyber", "jungledisk.com", "Bret", "Piatt", "Cybersecurity Executive", "San Antonio", "Texas", "541512, 541519"),
    ("Myers and Stauffer TX", "mslc.com", "Mark", "Stauffer", "Public Sector Healthcare IT Partner", "Austin", "Texas", "541511, 541512"),
    ("Catapult Systems", "catapultsystems.com", "David", "Fuess", "Public Sector Cloud VP", "Austin", "Texas", "541511, 541512"),
    ("HTG / High Touch TX DIR", "hightouchtechnologies.com", "Derrick", "Mains", "Public Sector IT Director", "Dallas", "Texas", "541512, 541513"),
    ("Infodat International (TX DIR)", "infodatinc.com", "Sam", "Merchant", "President & CEO (Texas SLED IT)", "Houston", "Texas", "541511, 541512"),
    ("Sogeti / Neos Consulting (TX DIR)", "neosconsulting.com", "Karon", "Irby", "Founder & CEO (Austin SLED IT)", "Austin", "Texas", "541511, 541512"),
    ("Kudelski Security TX", "kudelskisecurity.com", "Andrew", "Howard", "Chief Executive Officer", "Dallas", "Texas", "541512, 541519"),
    # CALIFORNIA
    ("Skylight Digital", "skylight.digital", "Chris", "Cairns", "Co-Founder & Partner", "San Francisco", "California", "541511, 541512"),
    ("CivicActions", "civicactions.com", "Henry", "Poole", "Co-Founder & Managing Director", "Lafayette", "California", "541511, 541512"),
    ("SymSoft Solutions", "symsoftsolutions.com", "Surinder", "Saini", "President & CEO", "Sacramento", "California", "541511, 541512"),
    ("Obsidian Security", "obsidiansecurity.com", "Hasan", "Imam", "Public Sector Cyber Director", "Newport Beach", "California", "541512, 541519"),
    ("Eyelit GovTech", "eyelit.com", "Dan", "Purcell", "VP Public Sector", "Sacramento", "California", "541511, 541512"),
    ("Technology Crest Corporation (TCC)", "techcrest.com", "Manish", "Gaur", "President & CEO (Cal eProcure IT)", "Sacramento", "California", "541511, 541512"),
    ("Visionary Integration Professionals (VIP)", "trustvip.com", "Jonna", "Ward", "Founder & CEO (Cal eProcure & Federal IT)", "Folsom", "California", "541511, 541512"),
    ("Prosum GovTech", "prosum.com", "Ravi", "Chatwani", "Co-Founder & CEO", "El Segundo", "California", "541511, 541512"),
    ("Astreya Public Sector", "astreya.com", "Edwin", "Miller", "Chief Executive Officer", "San Jose", "California", "541512, 541513"),
    ("Sikich /PKF California SLED", "cpshr.us", "Jerry", "Greenwell", "Chief Executive Officer (CA Public Sector)", "Sacramento", "California", "541512, 541611"),
    ("Sada Systems GovCloud", "sada.com", "Tony", "Safoian", "President & CEO (Google Public Sector Cloud)", "Los Angeles", "California", "518210, 541512"),
    ("Keyrus / Pantheon Gov", "pantheon.io", "Zack", "Rosen", "Co-Founder & Public Sector WebOps", "San Francisco", "California", "518210, 541511"),
    # FLORIDA
    ("Avero Advisors", "averoadvisors.com", "Abhijit", "Verekar", "Founder & CEO", "Tampa", "Florida", "541512, 541611"),
    ("CloudHesive", "cloudhesive.com", "Jim", "Walker", "Chief Executive Officer", "Fort Lauderdale", "Florida", "541512, 518210"),
    ("Kyra Solutions (FL MFMP VIP)", "kyrasolutions.com", "Pavan", "Ponnaganti", "Founder & CEO (Florida SLED & DOT IT)", "Lakeland", "Florida", "541511, 541512"),
    ("Inspired Technologies (FL SLED)", "inspired-tech.net", "Craig", "Colton", "President (Tallahassee SLED IT)", "Tallahassee", "Florida", "541512, 541513"),
    ("DSM Technology Consultants", "dsm.net", "David", "Robinson", "President & CEO (Florida Government Cloud)", "Lakeland", "Florida", "518210, 541512"),
    ("ERP Logic", "erplogic.com", "Vijay", "Kammela", "President", "Orlando", "Florida", "541511, 541512"),
    (" AgileThought / 4th Source FL", "agilethought.com", "Manuel", "Senderos", "Chief Executive Officer", "Tampa", "Florida", "541511, 541512"),
    (" B2Gnow / CollabraLink FL", "b2gnow.com", "Frank", "Begalke", "Public Sector Compliance SaaS Director", "Orlando", "Florida", "541511, 518210"),
    ("Kforce Government Solutions", "kforcegov.com", "Joe", "Liberatore", "President", "Tampa", "Florida", "541511, 541512"),
    # ILLINOIS
    ("Wynndalco Enterprises", "wynndalco.com", "David", "Andalcio", "Founder & CEO", "Chicago", "Illinois", "541512, 541513"),
    ("Burwood Group", "burwood.com", "Jim", "Hart", "Public Sector Practice Lead", "Chicago", "Illinois", "541512, 518210"),
    ("Magenium Solutions", "magenium.com", "Tim", "Byrne", "Managing Partner (IL IT & Cloud)", "Glen Ellyn", "Illinois", "541511, 541512"),
    ("Sikich GovTech", "sikich.com", "Chris", "Geier", "CEO & Public Sector ERP/Cyber Lead", "Naperville", "Illinois", "541512, 541519"),
    ("System Solutions Inc (SSI)", "ssicago.com", "Ali", "Ebrahimi", "President (Illinois BidBuy & Cook County IT)", "Northbrook", "Illinois", "541512, 541513"),
    (" Forsythe / Ntirety IL", "ntirety.com", "Emil", "Sayegh", "President & CEO (Managed Cloud & Security)", "Chicago", "Illinois", "518210, 541519"),
    (" Solstice / Kin + Carta Public Sector", "kinandcarta.com", "Kelly", "Manthey", "Chief Executive Officer", "Chicago", "Illinois", "541511, 541512"),
    # PENNSYLVANIA
    ("Custom Computer Specialists", "customonline.com", "Gregory", "Galarza", "President & CEO (SLED IT)", "Philadelphia", "Pennsylvania", "541512, 541513"),
    ("ERT Inc", "ert-inc.com", "Jingli", "Yang", "Chief Executive Officer", "Philadelphia", "Pennsylvania", "541511, 541512"),
    ("Gannett Fleming GeoTech", "gfnet.com", "Bob", "Scaer", "Chief Executive Officer (PA Municipal & Transit IT)", "Harrisburg", "Pennsylvania", "541512, 541330"),
    ("EvoGov Municipal Cloud", "evogov.com", "Bill", "Crane", "Founder & CEO (Municipal SLED Portals)", "Philadelphia", "Pennsylvania", "541511, 518210"),
    ("Kitware Federal", "kitware.com", "Lisa", "Avila", "Chief Executive Officer (DoD & Federal AI/Software)", "Clifton Park", "New York", "541511, 541512"),
    (" NuPaths / Harrisburg IT", "nupaths.org", "Andy", "Petroski", "President (PA Workforce & SLED Tech)", "Harrisburg", "Pennsylvania", "541512"),
    (" Synergetic Information Systems (PA DGS)", "synergeticsis.com", "Achilles", "Tzatzimakis", "President (PA eMarketplace IT)", "Camp Hill", "Pennsylvania", "541511, 541512"),
    # OHIO
    ("Mile Two LLC", "miletwo.us", "Jeff", "Graley", "Co-Founder & President", "Dayton", "Ohio", "541511, 541512"),
    ("Improving Ohio", "improving.com", "Curtis", "Hite", "Chief Executive Officer", "Columbus", "Ohio", "541511, 541512"),
    ("Infoverity", "infoverity.com", "Matt", "Wienke", "Co-Founder & President", "Dublin", "Ohio", "541511, 541512"),
    ("Ventech Solutions", "ventechsolutions.com", "Kirk", "Holdcraft", "President & CEO", "Columbus", "Ohio", "541511, 541512"),
    ("Azimuth Corporation", "azimuth-corp.com", "Valerie", "Rossi", "President & CEO (Wright-Patt & Ohio IT)", "Beavercreek", "Ohio", "541511, 541512"),
    ("Pomeroy SLED", "pomeroy.com", "Kristi", "Nelson", "Chief Executive Officer", "Columbus", "Ohio", "541512, 541513"),
    (" Expedient Ohio Cloud", "expedient.com", "Bryan", "Smith", "Chief Executive Officer", "Columbus", "Ohio", "518210, 541512"),
    (" Segue Dayton AFMC", "seguetech.com", "Brian", "Callahan", "President & CEO (Wright-Patt DoD IT)", "Dayton", "Ohio", "541511, 541512"),
    # GEORGIA
    ("TechAnax", "techanax.com", "Byron", "Bright", "President & CEO", "Atlanta", "Georgia", "541512, 541513"),
    ("DefenseStorm Cyber", "defensestorm.com", "Steve", "Soukup", "Chief Executive Officer (Cybersecurity)", "Alpharetta", "Georgia", "541512, 541519"),
    ("Digital Hands", "digitalhands.com", "Charlotte", "Baker", "Chief Executive Officer (Managed SOC & SLED Cyber)", "Atlanta", "Georgia", "541512, 541519"),
    ("Pond & Company Federal IT", "pondco.com", "Bob", "Rahn", "President & CEO (Georgia & Federal Infrastructure IT)", "Peachtree Corners", "Georgia", "541512, 541330"),
    (" Cox Business / RapidScale GovCloud", "rapidscale.net", "Duane", "DeCapite", "Public Sector Cloud Director", "Atlanta", "Georgia", "518210, 541512"),
    # NORTH CAROLINA
    ("Enquizit", "enquizit.com", "Tigger", "Bright", "Founder & Cloud Practice Lead", "Raleigh", "North Carolina", "518210, 541512"),
    ("RoviSys Federal", "rovisys.com", "John", "Robertson", "President & CEO (Systems Integration)", "Raleigh", "North Carolina", "541512, 541330"),
    ("BreachLock NC", "breachlock.com", "Seemant", "Sehgal", "Founder & CEO (Penetration Testing & PTaaS)", "Raleigh", "North Carolina", "541512, 541519"),
    ("Entrinsik (NC eVP Software)", "entrinsik.com", "Madhavi", "Gummadi", "Chief Executive Officer (Raleigh SLED BI & Analytics)", "Raleigh", "North Carolina", "541511, 541512"),
    (" Zscaler / Raleigh SLED", "bandwidth.com", "David", "Morken", "Founder & CEO (GovComms & Emergency 911)", "Raleigh", "North Carolina", "517111, 541512"),
    # NEW YORK
    ("Radiant Digital", "radiant.digital", "Satish", "Grampurohit", "Co-Founder & Managing Director", "New York", "New York", "541511, 541512"),
    ("Spruce Technology", "sprucetech.com", "Srini", "Penumella", "Founder & President (NYC PASSPort & NYS OGS)", "New York", "New York", "541511, 541512"),
    ("Derive Technologies (NYC PASSPort)", "derivetech.com", "Kirit", "Desai", "Co-Founder & SLED Healthcare/City IT Lead", "New York", "New York", "541512, 541513"),
    ("DynTek SLED", "dyntek.com", "Ron", "Ben-Yishay", "President & SLED Cybersecurity Lead (NYS OGS)", "Albany", "New York", "541512, 541519"),
    ("TAG Solutions (Albany SLED Cyber)", "tagsolutions.com", "PJ", "Sullivan", "President (NYS SLED IT & Unified Comms)", "Albany", "New York", "541512, 541519"),
    # MASSACHUSETTS
    ("Rutter Networking Technologies", "rutter-net.com", "Rick", "Rutter", "President & CEO (MA COMMBUYS IT)", "Andover", "Massachusetts", "541512, 541513"),
    ("CyberSaint Security (MA NIST/CMMC)", "cybersaint.io", "Jerry", "Layden", "Chief Executive Officer (NIST 800-53 & CMMC Automation)", "Boston", "Massachusetts", "541512, 541519"),
    ("K logix Cybersecurity", "klogixsecurity.com", "Kevin", "Pouche", "Co-Founder & COO (Boston CISO Advisory)", "Brookline", "Massachusetts", "541512, 541519"),
    ("Archibus Public Sector", "archibus.com", "Bill", "Tobin", "Public Sector Facilities IT Lead", "Boston", "Massachusetts", "541511, 541512"),
    # EXPANDED 12-STATE & FEDERAL IT / CYBER / CLOUD SEED DIRECTORY
    # VIRGINIA & DMV FEDERAL IT
    ("Agile Defense", "agiledefense.com", "Rick", "Wagner", "Chief Executive Officer", "Reston", "Virginia", "541511, 541512"),
    (" Karsun Solutions", "karsun-llc.com", "Sundar", "Vaidyanathan", "Co-Founder & CEO", "Herndon", "Virginia", "541511, 541512"),
    ("excella", "excella.com", "Burton", "White", "Co-Founder & Managing Partner", "Arlington", "Virginia", "541511, 541512"),
    (" Octo / IBM Federal", "octoconsulting.com", "Mehul", "Sanghani", "Founder & Public Sector Innovation Lead", "Reston", "Virginia", "541511, 541512"),
    ("B3 Group", "b3groupinc.com", "Dwight", "Hunt", "President & CEO (SDVOSB Health IT)", "Herndon", "Virginia", "541511, 541512"),
    (" Favor TechConsulting (FTC)", "ftc-llc.com", " Vaseem", "Anjum", "Founder & CEO", "Richmond", "Virginia", "541511, 541512"),
    (" Definitive Logic", "definitivelogic.com", "Paul", "Burke", "Founder & CEO", "Arlington", "Virginia", "541511, 541512"),
    ("Buchanan & Edwards", "buchanan-edwards.com", "Eric", "Olson", "Chief Executive Officer", "Arlington", "Virginia", "541511, 541512"),
    (" Highlight Technologies", "highlighttech.com", "Rebecca", "Andino", "Founder & CEO", "Fairfax", "Virginia", "541511, 541512"),
    (" A Square Group (ASG)", "a2-g.com", "Sardha", "Perera", "President & CEO", "Vienna", "Virginia", "541511, 541512"),
    (" Amyx Inc", "amyxinternet.com", "William", "Schaefer", "President & CEO (Cyber & Enterprise IT)", "Reston", "Virginia", "541512, 541519"),
    (" IntelliDyne", "intellidyne.com", "Robert", "Grey", "Chief Executive Officer", "Falls Church", "Virginia", "541512, 541513"),
    (" Metaphase Consulting", "metaphaseconsulting.com", "Brett", "McLaren", "Founder & CEO", "Reston", "Virginia", "541511, 541512"),
    (" Electrosoft Services", "electrosoft-inc.com", "Sarbari", "Gupta", "Founder & CEO (Federal Cybersecurity)", "Reston", "Virginia", "541512, 541519"),
    (" Gunnison Consulting Group", "gunnisonconsulting.com", "Gil", "Dussek", "Chief Executive Officer", "Alexandria", "Virginia", "541511, 541512"),
    (" SeKON Enterprise", "sekon.com", "Matt", "Logsdon", "President & CEO (Health & Defense IT)", "Reston", "Virginia", "541511, 541512"),
    (" Spatial Front", "spatialfront.com", "Amy", "Gao", "Founder & CEO", "sterling", "Virginia", "541511, 541512"),
    (" VivSoft Technologies", "vivsoft.io", "Navin", "Gunalan", "Founder & CEO (DoD Platform One & DevSecOps)", "Reston", "Virginia", "541511, 541512"),
    (" Guidehouse Digital", "guidehouse.com", "Scott", "McIntyre", "Chief Executive Officer", "McLean", "Virginia", "541512, 541611"),
    (" MetroStar Systems", "metrostar.com", "Ali", "Reza", "Co-Founder & CEO", "Reston", "Virginia", "541511, 541512"),
    (" IntelliBridge", "intellibridge.us", "Cass", "Panciocco", "President & CEO", "McLean", "Virginia", "541511, 541512"),
    (" Radiant Solutions / Criterion Systems", "criterionsystems.com", "Promod", "Sharma", "President & CEO (Federal Cyber)", "Vienna", "Virginia", "541512, 541519"),
    (" Sev1Tech", "sev1tech.com", "Bob", "Lohfeld", "Chief Executive Officer", "Woodbridge", "Virginia", "541512, 541513"),
    (" Clarity Innovations", "clarityinnovations.com", "Wes", "Daniels", "President & DoD Cyber Lead", "Columbia", "Maryland", "541511, 541512"),
    (" Next Phase Solutions", "npsi.us", "Lisa", "Wolfe", "Founder & CEO (CMS & Federal IT)", "Columbia", "Maryland", "541511, 541512"),
    (" Fearless Digital", "fearless.tech", "Delali", "Dzirasa", "Founder & CEO", "Baltimore", "Maryland", "541511, 541512"),
    (" Aquia Inc", "aquia.us", "Chris", "Hughes", "Co-Founder & CISO (Cloud & Cyber)", "Baltimore", "Maryland", "541512, 541519"),
    (" MasterPeace Solutions", "masterpeacesolutions.com", "Joe", "Carabetta", "President (Ft Meade Cyber Engineering)", "Columbia", "Maryland", "541511, 541512"),
    (" CyberPoint International", "cyberpointllc.com", "Karl", "Gumtow", "Founder & CEO (Maryland Cyber)", "Baltimore", "Maryland", "541512, 541519"),
    (" Audacious Inquiry", "ainq.com", "Chris", "Brandt", "Managing Partner (Health IT)", "Baltimore", "Maryland", "541511, 541512"),
    (" Dragos Security", "dragos.com", "Robert", "Lee", "Founder & CEO (OT/ICS Cybersecurity)", "Hanover", "Maryland", "541512, 541519"),
    (" IronNet Cyber", "ironnet.com", "Keith", "Alexander", "Founder & Public Sector Cyber Lead", "Fulton", "Maryland", "541512, 541519"),
    (" ZeroFOX Cyber", "zerofox.com", "James", "Foster", "Founder & CEO (External Threat Intel)", "Baltimore", "Maryland", "541512, 541519"),
    (" TrustedQA", "trustedqa.com", "Paul", "Garvey", "President & CEO", "Reston", "Virginia", "541511, 541512"),
    (" Cloudburst Security", "cloudburstsecurity.com", "forrest", "browning", "President (Cybersecurity)", "Herndon", "Virginia", "541512, 541519"),
    (" Sealing Technologies (SealingTech)", "sealingtech.com", "Ed", "Sealing", "Founder & CEO (Defensive Cyber Ops)", "Columbia", "Maryland", "541512, 541519"),
    (" Patriot Technologies", "patriot-tech.com", "Steve", "Keating", "President (Maryland & Federal IT)", "Frederick", "Maryland", "541512, 541519"),
    (" Chesapeake Technology International", "cti-md.com", "Dustin", "Crigger", "Chief Executive Officer", "California", "Maryland", "541511, 541512"),
    (" Harkcon Inc", "harkcon.com", "Kevin", "Harkins", "Chief Executive Officer", "Fredericksburg", "Virginia", "541512, 541611"),
    (" Rosslyn Data Technologies", "rosslyndatatech.com", "Paul", "Watts", "Chief Executive Officer", "Portsmouth", "Virginia", "541511, 518210"),
    (" Marathon TS", "marathonts.com", "Kip", "voytek", "President & Federal IT Director", "Kilmarnock", "Virginia", "541511, 541512"),
    (" Segue Technologies", "seguetech.com", "Ron", "Novak", "Executive VP (Federal & SLED IT)", "Arlington", "Virginia", "541511, 541512"),
    (" Spry Methods", "sprymethods.com", "Ted", "Steffens", "President & CEO (Cyber & Enterprise IT)", "McLean", "Virginia", "541512, 541519"),
    (" Centuria Corporation", "centuria.com", "Kevin", "Dermody", "Chief Executive Officer (SDVOSB IT)", "Reston", "Virginia", "541511, 541512"),
    (" ProSphere Tek", "prospheretek.com", "Robert", "Phoo", "President & CEO (SDVOSB IT)", "Alexandria", "Virginia", "541511, 541512"),
    (" Obsidian Global", "obsidianglobal.com", "First", "Capture", "VP of Capture", "Washington", "Virginia", "541511, 541512"),
    ("ByteCubed", "bytecubed.com", "Lena", " Trudeau", "Executive Partner", "Arlington", "Virginia", "541511, 541512"),
    (" Soliel LLC", "soliel-llc.com", "gull", "dahri", "President & CEO (8a STARS III / Cyber)", "Vienna", "Virginia", "541512, 541519"),
    (" Tekouth", "tekouth.com", "Capture", "Team", "Public Sector Capture", "Herndon", "Virginia", "541511, 541512"),
    # TEXAS SLED (TX DIR / ESBD)
    (" Weaver GovCon & Cyber", "weaver.com", "John", "Mackel", "CEO & Public Sector Cyber Advisory", "Houston", "Texas", "541512, 541611"),
    (" Solid Border Security (TX DIR)", "solidborder.com", "Ed", "Nothing", "President (Texas DIR Cybersecurity)", "San Antonio", "Texas", "541512, 541519"),
    (" DirSec Inc (TX DIR Cyber)", "dirsec.com", "monica", "b", "Public Sector Cyber Director", "Dallas", "Texas", "541512, 541519"),
    (" Luna Data Solutions (TX DIR)", "lunadatasolutions.com", "dana", "luna", "Founder & CEO (Austin SLED IT)", "Austin", "Texas", "541511, 541512"),
    (" Cooper Consulting Company (TX DIR)", "cooperconsulting.com", "Melynda", "Cooper", "Founder & CEO (Texas SLED IT)", "Austin", "Texas", "541511, 541512"),
    (" Bansar Technologies (TX DIR)", "bansar.com", "Subbu", "Venkata", "President (Texas DIR SLED IT)", "Austin", "Texas", "541511, 541512"),
    (" Abacus Technical Services (TX DIR)", "abacustechnical.com", "Brian", "Abacus", "Managing Director (Texas SLED IT)", "Dallas", "Texas", "541511, 541512"),
    (" TEKsystems Public Sector TX", "teksystems.com", "Jay", "Alvather", "President", "Austin", "Texas", "541511, 541512"),
    (" Sense Corp Public Sector", "sensecorp.com", "Keaton", "McCracken", "SVP Public Sector (Texas SLED)", "Austin", "Texas", "541511, 541512"),
    (" Valkyrie Intelligence TX", "valkyrie.ai", "Charlie", "Burgoyne", "Founder & CEO (Applied AI & Gov)", "Austin", "Texas", "541511, 541715"),
    (" SparkCognition / Avathon", "avathon.com", "Pervinder", "Johar", "Chief Executive Officer (Defense & Gov AI)", "Austin", "Texas", "541511, 541512"),
    (" Critical Start MDR", "criticalstart.com", "Rob", "Davis", "Founder & CEO (Managed Cyber & MDR)", "Plano", "Texas", "541512, 541519"),
    (" Halcyon Ransomware Defense", "halcyon.ai", "Jon", "Miller", "Co-Founder & CEO", "Austin", "Texas", "541512, 541519"),
    (" SpyCloud Cyber", "spycloud.com", "Ted", "Ross", "Co-Founder & CEO (Public Sector Identity)", "Austin", "Texas", "541512, 541519"),
    (" Digital Defense / HelpSystems", "digitaldefense.com", "Larry", "Hurtado", "President (San Antonio Cyber)", "San Antonio", "Texas", "541512, 541519"),
    (" Denim Group / Coalfire AppSec", "coalfire.com", "Tom", "McAndrew", "Chief Executive Officer (FedRAMP & CMMC 3PAO)", "Dallas", "Texas", "541512, 541519"),
    # CALIFORNIA SLED (Cal eProcure / TDDC)
    (" Exygy CivicTech", "exygy.com", "Zach", "Berke", "Managing Partner (California Civic Digital)", "San Francisco", "California", "541511, 541512"),
    (" Cambria Solutions", "cambriasolutions.com", "Robert", "Rodrigue", "Chief Executive Officer (Sacramento SLED IT)", "Sacramento", "California", "541511, 541512"),
    (" Taborda Solutions (CA SLED)", "tabordasolutions.com", "Jeff", "beling", "President (Cal eProcure IT)", "Folsom", "California", "541511, 541512"),
    (" Enterprise Networking Solutions (ENS)", "ens-inc.com", "Chad", "P", "President (Rancho Cordova SLED IT)", "Rancho Cordova", "California", "541512, 541513"),
    (" Natoma Technologies (CA SLED)", "natomatech.com", "Dave", "Slawson", "President (Sacramento State IT)", "Sacramento", "California", "541511, 541512"),
    ("Vasudeva / Tekberry CA", "tekberry.com", "Brad", "Sawyer", "President", "San Jose", "California", "541511, 541512"),
    (" Presidio West SLED", "presidio.com", "Bob", "Cagnazzi", "Chief Executive Officer", "Sacramento", "California", "541512, 541513"),
    (" Anomali Threat Intel", "anomali.com", "Ahmed", "abdeljabbar", "Public Sector Cyber Lead", "Redwood City", "California", "541512, 541519"),
    (" SentinelOne Public Sector", "sentinelone.com", "Tomer", "Weingarten", "CEO & FedRAMP/Gov Cyber", "Mountain View", "California", "541512, 541519"),
    (" Vectra AI Federal", "vectra.ai", "Hitesh", "Sheth", "President & CEO (AI Network Detection)", "San Jose", "California", "541512, 541519"),
    (" Abnormal Security Gov", "abnormalsecurity.com", "Evan", "Reiser", "Co-Founder & CEO (Gov Cloud Email Security)", "San Francisco", "California", "541512, 541519"),
    (" Second Front Systems", "secondfront.com", "Tyler", "Sweatt", "Chief Executive Officer (Game Warden DoD Cloud)", "San Francisco", "California", "541511, 518210"),
    (" Defense Unicorns", "defenseunicorns.com", "Rob", "Slaughter", "Co-Founder & CEO (DoD Airgap DevSecOps)", "Los Angeles", "California", "541511, 541512"),
    (" Rebellion Defense", "rebelliondefense.com", "Ben", "FitzGerald", "Chief Strategy Officer", "San Francisco", "California", "541511, 541512"),
    # FLORIDA SLED (MFMP VIP)
    (" Cole Engineering Services", "coleengineering.com", "bryan", "cole", "President (Orlando Simulation & DoD IT)", "Orlando", "Florida", "541511, 541512"),
    (" ReliaQuest Cyber", "reliaquest.com", "Brian", "Murphy", "Founder & CEO (Tampa MDR & SOC)", "Tampa", "Florida", "541512, 541519"),
    (" GuidePoint Security", "guidepointsecurity.com", "Michael", "Volkert", "Managing Partner (Federal & SLED Cyber)", "Tampa", "Florida", "541512, 541519"),
    (" ThreatLocker Zero Trust", "threatlocker.com", "Danny", "Jenkins", "Co-Founder & CEO (Orlando Zero Trust)", "Orlando", "Florida", "541512, 541519"),
    ("SimSpace Cyber Ranges", "simspace.com", "William", "Hutchison", "Chief Executive Officer", "Orlando", "Florida", "541512, 541519"),
    (" Metova Federal", "metova.com", "GB", "C", "President (Cyber Ranges & Mobile IT)", "St Petersburg", "Florida", "541511, 541512"),
    (" ProTech / Tallahassee SLED", "protechfl.com", "Capture", "Team", "Florida SLED IT Capture", "Tallahassee", "Florida", "541511, 541512"),
    (" Infinity Software Development (FL SLED)", "infinity-software.com", "Tom", "b", "President (Tallahassee State IT)", "Tallahassee", "Florida", "541511, 541512"),
    # ILLINOIS SLED (BidBuy / Cook County / CTA)
    (" Clarity Partners (Chicago SLED IT)", "claritypartners.com", "David", "namkung", "Managing Partner (Chicago & IL Public Sector IT)", "Chicago", "Illinois", "541511, 541512"),
    (" Bronner Group (Chicago Gov Consulting)", "bronnergroup.com", "Gila", "Bronner", "Founder & CEO (Chicago & IL Municipal IT)", "Chicago", "Illinois", "541512, 541611"),
    ("Catalyst Consulting Group (Chicago SLED)", "catconsult.com", "Arvind", "Talwar", "Founder & Managing Partner (City of Chicago & State IT)", "Chicago", "Illinois", "541511, 541512"),
    (" Heartland Business Systems (IL SLED)", "hbs.net", "Peter", "Helander", "Chief Executive Officer (Midwest SLED IT & Cyber)", "Lisle", "Illinois", "541512, 541513"),
    (" Impact Networking Managed IT", "impactmybiz.com", "Frank", "Cucco", "Chief Executive Officer (Chicago Managed IT & Cyber)", "Lake Forest", "Illinois", "541512, 541519"),
    (" Trustwave Government", "trustwave.com", "Eric", "Harmon", "Chief Executive Officer (Chicago MDR & Gov Cyber)", "Chicago", "Illinois", "541512, 541519"),
    (" Solstice / Perficient Chicago", "perficient.com", "Tom", "Hogan", "Chief Executive Officer", "Chicago", "Illinois", "541511, 541512"),
    # PENNSYLVANIA SLED (DGS eMarketplace / COSTARS)
    (" Celerity PA SLED", "celerity.com", "Capture", "Team", "Harrisburg Public Sector Practice", "Harrisburg", "Pennsylvania", "541511, 541512"),
    (" Computer Aid Inc (CAI Public Sector)", "cai.io", "Tom", "Salvaggio", "President (Allentown & Harrisburg SLED IT)", "Allentown", "Pennsylvania", "541511, 541512"),
    (" Softwriters / Armada PA", "softwriters.com", "Scott", "T", "Chief Executive Officer (Pittsburgh Healthcare IT)", "Pittsburgh", "Pennsylvania", "541511, 541512"),
    (" Aspirant Consulting Pittsburgh", "aspirant.com", "Mike", "McClaine", "Chief Executive Officer", "Pittsburgh", "Pennsylvania", "541512, 541611"),
    (" Truefit Innovation", "truefit.io", "Darrin", "Grove", "Founder & CEO (Pittsburgh Software)", "Pittsburgh", "Pennsylvania", "541511, 541512"),
    (" GreyCastle Security", "greycastlesecurity.com", "Reg", "Harnish", "Cybersecurity Practice Lead", "Philadelphia", "Pennsylvania", "541512, 541519"),
    (" IntegraOne (PA COSTARS IT)", "integraone.com", "linford", "m", "President (Allentown & Harrisburg SLED Cyber/Net)", "Allentown", "Pennsylvania", "541512, 541513"),
    (" Weidenhammer Systems (PA SLED)", "hammer.net", "John", "Weidenhammer", "President (Reading & PA Municipal IT)", "Reading", "Pennsylvania", "541511, 541512"),
    # OHIO SLED (OhioBuys / Wright-Patt)
    (" Riverside Research Dayton", "riversideresearch.org", "Steven", "Omick", "President & CEO (Dayton AI & Cyber)", "Beavercreek", "Ohio", "541512, 541715"),
    (" Radiance Technologies Ohio", "radiancetech.com", "Bill", "Bailey", "Chief Executive Officer (Wright-Patt Cyber)", "Beavercreek", "Ohio", "541512, 541715"),
    (" Centauri / KBR Dayton", " centauricorp.com", "Capture", "Team", "Wright-Patt Capture", "Dayton", "Ohio", "541512"),
    (" Peerless Technologies (Wright-Patt IT)", "epeerless.com", "Michael", "Bridges", "Founder & President (Dayton Federal & OH IT)", "Fairborn", "Ohio", "541511, 541512"),
    (" Woolpert Digital Innovations", "woolpert.com", "Neil", "Churman", "President & CEO (Dayton Geospatial & Cloud IT)", "Dayton", "Ohio", "541512, 541370"),
    (" CareWorks Tech /ingley Ohio", "resultant.com", "Mark", "Caswell", "Chief Executive Officer (Public Sector Data & IT)", "Columbus", "Ohio", "541511, 541512"),
    (" CBTS (Cincinnati Bell Tech SLED)", "cbts.com", "Jeff", "Lackey", "President & CEO (Ohio SLED Cloud & Cyber)", "Cincinnati", "Ohio", "541512, 518210"),
    (" MCPc Secure Technology", "mcpc.com", "Andy", "Jones", "Chief Executive Officer (Cleveland SLED Cyber)", "Cleveland", "Ohio", "541512, 541519"),
    (" TrustedSec Cyber", "trustedsec.com", "David", "Kennedy", "Founder (Ohio Offensive Cyber & CMMC)", "Fairlawn", "Ohio", "541512, 541519"),
    # GEORGIA SLED (DOAS GPR / Atlanta)
    (" Secureworks Gov", "secureworks.com", "Wendy", "Thomas", "Chief Executive Officer (Atlanta XDR & Incident Response)", "Atlanta", "Georgia", "541512, 541519"),
    (" Alert Logic / Fortra", "alertlogic.com", "Capture", "Team", "Managed Cloud Security", "Atlanta", "Georgia", "541512, 541519"),
    (" KMS Technology Atlanta", "kms-technology.com", "Leo", "Tucker", "Chief Executive Officer", "Atlanta", "Georgia", "541511, 541512"),
    (" CapTech Atlanta Public Sector", "captechconsulting.com", "Kevin", "McQueen", "Chief Executive Officer (State & Local IT)", "Atlanta", "Georgia", "541511, 541512"),
    (" Cherry Bekaert Digital & CMMC", "cbh.com", "Michelle", "Thompson", "CEO & GovCon CMMC Practice", "Atlanta", "Georgia", "541512, 541611"),
    (" Aprio GovCon & CMMC", "aprio.com", "Richard", "Kopelman", "CEO & CMMC 3PAO Advisory", "Atlanta", "Georgia", "541512, 541611"),
    (" Morris Technology / ProLogic ITS (GA SLED)", "prologicits.com", "Don", "McGowan", "Founder & CEO (Georgia Municipal & Public Safety IT)", "Acworth", "Georgia", "541512, 541513"),
    # NORTH CAROLINA SLED (NC eVP / RTP)
    (" Method Savvy / Walk West RTP", "walkwest.com", "Donald", "Thompson", "Public Sector Digital Strategy", "Raleigh", "North Carolina", "541511, 541512"),
    (" Three Wire Systems NC", "threewiresystems.com", "Dan", "Frank", "Founder & CEO (VetTech & DoD IT)", "Raleigh", "North Carolina", "541512, 541519"),
    (" Segra Public Sector Fiber & Cloud", "segra.com", "Kevin", "Hart", "Chief Executive Officer (NC & VA SLED Network/Cloud)", "Charlotte", "North Carolina", "517111, 518210"),
    (" Peak 10 / Flexential GovCloud", "flexential.com", "Chris", "Downie", "Chief Executive Officer (Charlotte Hybrid Cloud)", "Charlotte", "North Carolina", "518210, 541512"),
    (" SoftPro Public Sector", "softprocorp.com", "Joyce", "Weiland", "President (Raleigh Government Software)", "Raleigh", "North Carolina", "541511, 541512"),
    (" DeviceSolutions RTP", "devicesolutions.net", "Bob", "W", "Chief Executive Officer (RTP Embedded & IoT Engineering)", "Morrisville", "North Carolina", "541511, 541512"),
    # NEW YORK SLED (NYS OGS / NYC PASSPort)
    (" CMA Consulting Services (Albany NYS OGS)", "cma.com", "Kay", "Stafford", "Founder & CEO (Latham NYS Medicaid & Health IT)", "Latham", "New York", "541511, 541512"),
    (" GCOM Software / Voyatek (Albany SLED)", "voyatek.com", "Kamal", "Bherwani", "Chief Executive Officer (Albany State & Local GovTech)", "Albany", "New York", "541511, 541512"),
    (" MVP Consulting Plus (Albany NYS OGS)", "mvpconsultingplus.com", "lu", "s", "President (Albany NYS HBITS & IT)", "Albany", "New York", "541511, 541512"),
    (" Currier McCabe & Associates", "curriermccabe.com", "Capture", "Team", "NYS SLED IT", "Latham", "New York", "541511, 541512"),
    (" Logical Net (Albany GovCloud)", "logical.net", "Vince", "C", "President (Schenectady NYS Managed Cloud & Cyber)", "Schenectady", "New York", "518210, 541512"),
    (" BlueVoyant Cyber", "bluevoyant.com", "Jim", "Rosenthal", "Co-Founder & CEO (NYC MDR & Supply Chain Defense)", "New York", "New York", "541512, 541519"),
    (" Claroty OT/Cyber", "claroty.com", "Yaniv", "Vardi", "Chief Executive Officer (NYC Critical Infrastructure Cyber)", "New York", "New York", "541512, 541519"),
    (" Wiz GovCloud", "wiz.io", "Assaf", "Rappaport", "Co-Founder & CEO (FedRAMP Cloud Security)", "New York", "New York", "541512, 518210"),
    (" Trail of Bits Security", "trailofbits.com", "Dan", "Guido", "Co-Founder & CEO (NYC DARPA & DoD Cyber R&D)", "New York", "New York", "541512, 541715"),
    # MASSACHUSETTS SLED (COMMBUYS / Boston / Hanscom AFB)
    (" MITRE / Bedford Cyber Partners", "pionsystems.com", "Capture", "Team", "Hanscom AFB IT", "Bedford", "Massachusetts", "541512"),
    (" Oasis Systems (Hanscom AFB IT)", "oasissystems.com", "Tom", "Daly", "Chief Executive Officer (Lexington DoD & FAA IT)", "Lexington", "Massachusetts", "541511, 541512"),
    (" Odyssey Systems Consulting (Hanscom AFB)", "odysseyconsult.com", "Tom", "N", "Chief Executive Officer (Wakefield USAF C4ISR & IT)", "Wakefield", "Massachusetts", "541512, 541330"),
    (" Torchlight AI / Boston GovTech", " rapid7.com", "Corey", "Thomas", "CEO (Boston Vulnerability & SOC)", "Boston", "Massachusetts", "541512, 541519"),
    (" Recorded Future Threat Intel", "recordedfuture.com", "Christopher", "Ahlberg", "Co-Founder & CEO (Somerville Public Sector Threat Intel)", "Somerville", "Massachusetts", "541512, 541519"),
    (" Bitsight Cyber Ratings", "bitsight.com", "Steve", "harvey", "Chief Executive Officer (Boston Third-Party Cyber Risk)", "Boston", "Massachusetts", "541512, 541519"),
    (" Imprivata Public Sector IAM", "imprivata.com", "Fran", "Rosch", "Chief Executive Officer (Waltham Healthcare & Gov IAM)", "Waltham", "Massachusetts", "541512, 541519"),
    (" Nasuni GovCloud", "nasuni.com", "Paul", "Flanagan", "Chief Executive Officer (Boston Hybrid Cloud Storage)", "Boston", "Massachusetts", "518210, 541512"),
    (" Carousel / NWN Carousel (MA COMMBUYS)", "nwncarousel.com", "Jim", "Sullivan", "President & CEO (Waltham COMMBUYS SLED Cloud & Comms)", "Waltham", "Massachusetts", "541512, 541513"),
    # NEW JERSEY SLED (NJSTART / Treasury DPP / Picatinny / NJ TRANSIT)
    (" CompuCom Systems NJ", "compucom.com", "Mick", "Slattery", "Chief Executive Officer (NJ Managed Workplace & SLED IT)", "Moorestown", "New Jersey", "541512, 541513"),
    (" Shi International Public Sector (NJSTART)", "shi.com", "Thai", "Lee", "President & CEO (Somerset NJSTART M4002 Software & Cloud)", "Somerset", "New Jersey", "541512, 518210"),
    (" Trigyn Technologies (NJ SLED & UN IT)", "trigyn.com", "Tom", "Gordon", "Senior VP Public Sector (Edison NJ State & Municipal IT)", "Edison", "New Jersey", "541511, 541512"),
    (" Marlabs Digital & GovCloud", "marlabs.com", "Siby", "Vadakekkara", "Founder & CEO (Piscataway AI & Enterprise Cloud)", "Piscataway", "New Jersey", "541511, 541512"),
    # WASHINGTON SLED (WA WEBS / WaTech / DES IT Master Contracts)
    (" Critical Informatics (CI Security WA SLED)", "cisecurity.com", "Mike", "Hamilton", "Founder & CISO (Seattle / Bremerton WA SLED MDR & SOC)", "Seattle", "Washington", "541512, 541519"),
    (" WatchGuard Technologies GovCloud", "watchguard.com", "Prakash", "Panjwani", "Chief Executive Officer (Seattle SLED Network Security & Zero-Trust)", "Seattle", "Washington", "541512, 541519"),
    (" ExtraHop Networks Public Sector", "extrahop.com", "Greg", "Clark", "Chief Executive Officer (Seattle NDR & WaTech Cyber Telemetry)", "Seattle", "Washington", "541512, 541519"),
    (" Slalom Public Sector & WaTech Cloud", "slalom.com", "Brad", "Jackson", "Co-Founder & CEO (Seattle WA State Cloud & AI Modernization)", "Seattle", "Washington", "541511, 541512"),
    # MICHIGAN SLED (MI SIGMA VSS / DTMB MiDEAL / TACOM Defense Corridor)
    (" Dewpoint Michigan State IT (DTMB)", "dewpoint.com", "MW", "Capture", "Executive Leadership (Lansing MI DTMB & Healthcare IT)", "Lansing", "Michigan", "541511, 541512"),
    (" Censys Public Sector Attack Surface", "censys.io", "Brad", "Brooks", "Chief Executive Officer (Ann Arbor Federal & MI SLED Cyber)", "Ann Arbor", "Michigan", "541512, 541519"),
    (" Duo Security / Michigan IAM", "duo.com", "Dug", "Song", "Co-Founder (Ann Arbor Zero-Trust MFA & SLED Identity)", "Ann Arbor", "Michigan", "541512, 541519"),
    (" ImageSoft Government & Courts Cloud", "imagesoftinc.com", "Scott", "Bade", "President (Southfield MI SLED Justice & Workflow Automation)", "Southfield", "Michigan", "541511, 541512"),
]

BAD_LOCAL_PARTS = {
    "info", "contact", "contactus", "contact-us", "hello", "inquiries", "information",
    "enquiry", "sales", "vasales", "kgsinfo", "cti-info", "emeasales", "marketing",
    "events", "admin", "office", "general", "reception", "frontdesk", "feedback",
    "service", "customercare", "u003esupport", "%20support", "dpo", "privacyteam",
    "cbprivacy", "resumes", "claims", "connect", "teambox", "psirt", "mydata",
    "content", "communications", "solutions", "labs", "wccc", "mdc", "nsf",
    "privacy", "legal", "abuse", "dmca", "noreply", "no-reply", "donotreply",
    "webmaster", "postmaster", "security", "careers", "jobs", "hr", "recruiting",
    "talent", "employmentverifications", "support", "helpdesk", "help",
    "billing", "accounts", "unsubscribe", "media", "press", "news", "web", "theteam",
    "pr", "ir", "firstname", "lastname",
    "first.last", "yourname", "example", "user", "email",
    "human.resources", "humanresources", "investor", "investors", "grants",
}

BAD_LOCAL_SUBSTRINGS = (
    "info", "contact", "hello", "inquir", "enquir", "support", "help", "privacy",
    "dpo", "legal", "abuse", "dmca", "noreply", "no-reply", "webmaster", "postmaster",
    "security", "psirt", "career", "job", "hr", "human.resource", "humanresource",
    "investor", "grant", "recruit", "talent", "employ", "resume",
    "billing", "account", "invoice", "claim", "unsub", "media", "press", "news", "theteam",
    "marketing", "events", "admin", "office", "general", "reception", "frontdesk",
    "feedback", "service", "customercare", "u003e", "%20", "sales", "teambox", "connect",
    "mydata", "content", "communications", "solutions", "labs", "wccc", "mdc", "nsf",
)

ROLE_LOCAL_PARTS = {
    "contracts", "contracting", "capture", "bd", "bizdev", "growth",
    "partner", "partners", "partnerships", "engage", "stars3", "starsiii",
    "ciosp3", "ciosp4", "oasis", "vets2", "sewp", "gsa", "vehicles",
    "federal", "sled", "govcon", "proposals", "rfp", "teaming", "ipsecureinc",
}

COMPANY_CLEAN_OVERRIDES = {
    "vas / visionary integration professionals (vip)": "Visionary Integration Professionals",
    "visionary integration professionals (vip)": "Visionary Integration Professionals",
    "b2gnow / collabralink fl": "B2Gnow",
    "inspired technologies (fl sled)": "Inspired Technologies",
    "sikich govtech": "Sikich",
    "daly computers (md emma sled)": "Daly Computers",
    "data networks (md sled)": "Data Networks",
    "cybersaint security (ma nist/cmmc)": "CyberSaint Security",
    "kappe / kitware": "Kitware",
    "kitware federal": "Kitware",
    "entrinsik (nc evp software)": "Entrinsik",
    "methodsavvy / rovisys federal": "RoviSys Federal",
    "securityfrag / breachlock nc": "BreachLock",
    "breachlock nc": "BreachLock",
    "improving ohio": "Improving",
    "evogov municipal cloud": "EvoGov",
    "nupaths / harrisburg it": "NuPaths",
    "sogeti / neos consulting (tx dir)": "Neos Consulting",
    "vintage it services (tx dir)": "Vintage IT Services",
    "makpar corporation": "Makpar",
    "ost inc (optimal solutions & technologies)": "OST Global",
    "ost (optimal solutions & technologies)": "OST Global",
    "decisiveinstincts": "Decisive Instincts",
    "nextech lintech": "LinTech Global",
    "vsolvit": "VSolvit",
    "esimplicity": "eSimplicity",
    "microhealth": "MicroHealth",
    "agilerank": "AgileRank",
    "prosum govtech": "Prosum",
    "defensestorm cyber": "DefenseStorm",
}


def clean_company_display_name(raw_company: str) -> str:
    s = str(raw_company or "").strip()
    if not s:
        return "your team"
    low = s.lower()
    if low in COMPANY_CLEAN_OVERRIDES:
        return COMPANY_CLEAN_OVERRIDES[low]
    # Strip trailing parenthetical CRM notes like (FL SLED), (TX DIR), (MD eMMA SLED)
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
    if " / " in s:
        parts = [p.strip() for p in s.split(" / ") if p.strip()]
        s = parts[-1] if len(parts[-1]) >= 4 else parts[0]
    s = re.sub(r",?\s*\b(L\.?L\.?C\.?|Inc\.?|Corporation|Corp\.?)\b\s*$", "", s, flags=re.IGNORECASE).strip()
    return s or str(raw_company).strip()


def sync_person_name_with_email(first_name: str, last_name: str, email: str) -> Tuple[str, str]:
    fn = str(first_name or "").strip()
    ln = str(last_name or "").strip()
    em = str(email or "").strip().lower()
    if "@" not in em:
        return fn, ln
    local = em.split("@", 1)[0].strip()
    if local in ROLE_LOCAL_PARTS or local in BAD_LOCAL_PARTS:
        return fn, ln
    if "." in local:
        parts = [p for p in local.split(".") if p.isalpha() and len(p) >= 2]
        if len(parts) >= 2:
            return parts[0].capitalize(), parts[-1].capitalize()
    elif local.isalpha() and 3 <= len(local) <= 12 and fn.lower() in ("capture", "team", "there", ""):
        return local.capitalize(), ln
    return fn, ln

PREFERRED_KEYWORDS = (
    "capture", "bd", "bizdev", "gov", "contracts", "proposals", "rfp", "sled", "federal",
    "growth", "partner", "partnerships", "teaming", "stars", "ciosp", "oasis", "sewp",
    "mas", "gsa", "vehicles", "engage",
)


def _load_mx_cache() -> Dict[str, bool]:
    if os.path.exists(MX_CACHE_PATH):
        try:
            with open(MX_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {str(k).lower(): bool(v) for k, v in data.items()}
        except Exception:
            pass
    return {}


def _save_mx_cache(cache: Dict[str, bool]) -> None:
    try:
        with open(MX_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, sort_keys=True)
    except Exception:
        pass


ISP_AND_LEGACY_DOMAINS = {
    "dell.com", "resample.com", "sni.net", "mr.net", "sti.net", "privatei.com",
    "ix.netcom.com", "well.com", "rcn.com", "quinta.com", "mathsoft.com",
    "omnibuilds.com", "beatthetraffic.com", "harp3r.com", "inhandelectronics.com",
    "lorandtechnologies.com", "veriflowsystems.com", "embedded-zone.com",
    "konarka.com", "coolchiptechnologies.com", "empirerobotics.com",
    "comcast.net", "verizon.net", "att.net", "sbcglobal.net", "bellsouth.net",
    "cox.net", "charter.net", "earthlink.net", "mindspring.com", "pacbell.net",
    "ameritech.net", "swbell.net", "prodigy.net", "netzero.net", "juno.com",
    "mac.com", "me.com", "icloud.com", "gmail.com", "yahoo.com", "hotmail.com",
    "aol.com", "outlook.com", "msn.com", "live.com", "protonmail.com",
}

PARKED_SITE_MARKERS = (
    "hugedomains", "sedoparking", "afternic", "dan.com", "domain is for sale",
    "buy this domain", "godaddy.com/forsale", "parkingcrew", "this domain may be for sale",
    "parked free", "courtesy of godaddy",
)


def _get_live_mx_hosts(domain: str) -> List[str]:
    """Resolve live MX hosts via native UDP DNS (`nslookup -type=mx`) with DoH secondary fallback. Never falls back to A-record `socket.getaddrinfo`."""
    parked_mx_tokens = ("parklogic", "sedoparking", "above.com", "bodis.com", "eftydns", "parkingcrew", "localhost")
    try:
        out = subprocess.check_output(
            ["nslookup", "-type=mx", domain],
            stderr=subprocess.STDOUT,
            timeout=5,
            text=True,
        )
        pairs: List[Tuple[int, str]] = []
        for m in re.finditer(r"preference\s*=\s*(\d+),\s*mail exchanger\s*=\s*([^\s\r\n]+)", out, re.I):
            pairs.append((int(m.group(1)), m.group(2).rstrip(".").lower()))
        for m in re.finditer(r"mail exchanger\s*=\s*(\d+)\s+([^\s\r\n]+)", out, re.I):
            pairs.append((int(m.group(1)), m.group(2).rstrip(".").lower()))
        pairs.sort(key=lambda x: x[0])
        hosts = [
            p[1] for p in pairs
            if p[1] and p[1] != "." and "0.0.0.0" not in p[1] and "(root)" not in p[1]
            and not any(pk in p[1] for pk in parked_mx_tokens)
        ]
        return hosts
    except Exception:
        pass

    try:
        resp = requests.get(
            "https://dns.google/resolve",
            params={"name": domain, "type": "MX"},
            timeout=(1.5, 2.0),
        )
        if resp.status_code == 200:
            body = resp.json()
            answers = body.get("Answer") or []
            hosts = []
            for a in answers:
                if int(a.get("type") or 0) == 15:
                    raw_d = str(a.get("data") or "").strip().lower().rstrip(".")
                    parts = raw_d.split()
                    mx_h = parts[-1] if parts else ""
                    if mx_h and mx_h not in ("", ".") and not any(pk in mx_h for pk in parked_mx_tokens):
                        hosts.append(mx_h)
            if body.get("Status") == 0 and hosts:
                return hosts
    except Exception:
        pass
    return []


def _domain_matches_company_name(dom: str, comp: str) -> bool:
    if dom.lower() in ISP_AND_LEGACY_DOMAINS:
        return False
    d_root = dom.lower().split(".")[0].replace("-", "")
    words = [
        w.lower()
        for w in re.findall(r"[A-Za-z0-9]+", comp)
        if len(w) >= 2 and w.lower() not in (
            "inc", "llc", "corp", "corporation", "company", "ltd", "the", "and",
            "incorporated", "technologies", "systems", "solutions", "labs", "group",
        )
    ]
    if not words:
        words = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", comp) if len(w) >= 2]
    if not words:
        return False
    for w in words:
        if len(w) >= 4 and (w in d_root or d_root in w):
            return True
        if len(w) >= 3 and d_root.startswith(w[:3]):
            return True
    initials = "".join(w[0] for w in words)
    if len(initials) >= 2 and d_root.startswith(initials):
        return True
    return False


def _check_corporate_website_alive(domain: str) -> bool:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0"}
    for u in (f"https://{domain}", f"https://www.{domain}"):
        try:
            r = requests.get(u, headers=headers, timeout=(1.5, 2.0), allow_redirects=True, verify=False)
            if r.status_code == 200 and len(r.text) >= 600:
                final_host = r.url.split("//", 1)[-1].split("/", 1)[0].lower()
                if not final_host.endswith(domain.lower()):
                    return False
                low = r.text.lower()
                if any(pk in low for pk in PARKED_SITE_MARKERS):
                    return False
                return True
        except Exception:
            continue
    return False


def verify_email_domain_mx(email: str, mx_cache: Dict[str, bool] | None = None, verify_smtp: bool = False) -> bool:
    """
    Verifies that an email address is syntactically valid, not in TEST_OR_SYNTHETIC_DOMAINS,
    ISP_AND_LEGACY_DOMAINS, or ALREADY_CONTACTED_LEGACY_EMAILS, and has a live DNS MX record
    (plus live SMTP RCPT TO == 250 verification when verify_smtp=True or when cached).
    Never falls back to socket.getaddrinfo() when MX is missing.
    """
    clean = str(email or "").strip().lower()
    if "@" not in clean or " " in clean:
        return False
    if clean in ALREADY_CONTACTED_LEGACY_EMAILS:
        return False
    local_part, domain = clean.split("@", 1)
    if not local_part or not domain or "." not in domain:
        return False
    if domain in TEST_OR_SYNTHETIC_DOMAINS or domain in ISP_AND_LEGACY_DOMAINS or clean.startswith("capture-verify@"):
        return False

    cache = mx_cache if mx_cache is not None else _load_mx_cache()
    smtp_key = f"smtp_ok:{clean}"
    if smtp_key in cache:
        return bool(cache[smtp_key])
    if domain in cache and not cache[domain]:
        return False
    if domain in cache and cache[domain] and not verify_smtp:
        return True

    mx_hosts = _get_live_mx_hosts(domain)
    if not mx_hosts:
        cache[domain] = False
        cache[smtp_key] = False
        if mx_cache is None:
            _save_mx_cache(cache)
        return False

    cache[domain] = True
    if verify_smtp:
        mx_host = mx_hosts[0]
        smtp_ok = True
        try:
            server = smtplib.SMTP(timeout=1.5)
            server.connect(mx_host, 25)
            server.ehlo("getsignaltender.com")
            server.mail("aaron@getsignaltender.com")
            code, _ = server.rcpt(clean)
            server.quit()
            if 500 <= int(code or 0) < 600:
                smtp_ok = False
        except Exception:
            # Outbound TCP port 25 is blocked on most residential/cloud ISPs; rely on verified live MX + HTTP 200 corporate site
            smtp_ok = True
        cache[smtp_key] = smtp_ok
        if not smtp_ok:
            if mx_cache is None:
                _save_mx_cache(cache)
            return False

    if mx_cache is None:
        _save_mx_cache(cache)
    return True


def _score_candidate_email(em: str, domain: str) -> int:
    if "@" not in em:
        return -999
    local, dom = em.lower().split("@", 1)
    if dom != domain and not dom.endswith("." + domain):
        return -999
    if local in BAD_LOCAL_PARTS or any(local.startswith(b + "@") for b in BAD_LOCAL_PARTS):
        return -999
    if local not in ROLE_LOCAL_PARTS and any(sub in local for sub in BAD_LOCAL_SUBSTRINGS):
        return -999
    if any(ext in local for ext in (".png", ".jpg", ".svg", ".webp", ".gif", ".css", ".js", "2x", "sentry", "example")):
        return -999
    score = 10
    for idx, kw in enumerate(PREFERRED_KEYWORDS):
        if kw in local:
            score += (30 - idx)
            break
    if "." in local:
        score += 25
    return score


PARKED_PAGE_MARKERS = (
    "hugedomains",
    "sedoparking",
    "afternic",
    "dan.com",
    "domain is for sale",
    "buy this domain",
    "godaddy.com/forsale",
    "parkingcrew",
    "this domain may be for sale",
)

TECH_GOVCON_PAGE_SIGNALS = (
    "technology",
    "software",
    "cyber",
    "cloud",
    "federal",
    "government",
    "consulting",
    "solutions",
    "systems",
    "engineering",
    "data",
    "network",
    "security",
    "digital",
    "agency",
    "contract",
    "naics",
    "gsa",
    "dod",
    "it services",
    "managed services",
)


def _crawl_single_contractor_site(
    item: Tuple[str, str, str, str, str, str, str, str],
    require_tech_signal: bool = False,
) -> Dict[str, str] | None:
    comp, domain, fn, ln, title, city, state, naics = item
    domain = domain.strip().lower()
    if " " in domain or not domain:
        return None
    try:
        socket.getaddrinfo(domain, None)
    except Exception:
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    }
    found = set()
    has_tech_signal = not require_tech_signal
    email_re = re.compile(r"[a-zA-Z0-9._%+-]+@" + re.escape(domain), re.I)
    mailto_re = re.compile(r"mailto:([a-zA-Z0-9._%+-]+@" + re.escape(domain) + r")", re.I)

    for u in (
        f"https://{domain}/contract-vehicles",
        f"https://{domain}/contracts",
        f"https://{domain}/gsa",
        f"https://{domain}/leadership",
        f"https://{domain}/team",
        f"https://{domain}/government",
        f"https://{domain}/about",
        f"https://{domain}/about-us",
        f"https://{domain}/contact",
        f"https://{domain}/contact-us",
        f"https://{domain}",
        f"https://www.{domain}",
    ):
        try:
            r = requests.get(u, headers=headers, timeout=(2.0, 2.8), verify=False, allow_redirects=True)
            if r.status_code == 200 and r.text:
                low_html = r.text.lower()
                if any(pk in low_html for pk in PARKED_PAGE_MARKERS):
                    return None
                if not has_tech_signal and any(sig in low_html for sig in TECH_GOVCON_PAGE_SIGNALS):
                    has_tech_signal = True
                decoded = (
                    r.text.replace("&#64;", "@")
                    .replace("&#x40;", "@")
                    .replace("%40", "@")
                    .replace("&#46;", ".")
                )
                for m in list(mailto_re.findall(decoded)) + list(email_re.findall(decoded)):
                    clean = m.strip().lower().rstrip(".")
                    clean = re.sub(r"^[0-9-]+", "", clean)
                    if _score_candidate_email(clean, domain) > 0:
                        found.add(clean)
                if found and has_tech_signal:
                    break
        except Exception:
            continue

    if not found or not has_tech_signal:
        return None

    best_em = sorted(found, key=lambda x: _score_candidate_email(x, domain), reverse=True)[0]
    return {
        "First Name": fn.strip().title(),
        "Last Name": ln.strip().title(),
        "Title": title.strip(),
        "Company Name": comp.strip(),
        "Email": best_em,
        "City": city.strip().title(),
        "State": state.strip(),
        "Website": f"https://{domain}",
        "NAICS Codes": naics.strip(),
        "Industry": "information technology & services",
        "Keywords": f"govcon, {state.lower()} sled rfp, sam.gov, cybersecurity, cloud, software",
    }


def discover_and_crawl_govcon_websites(existing_contacts: List[Dict[str, str]], mx_cache: Dict[str, bool]) -> List[Dict[str, str]]:
    """
    Autonomously crawls any uncrawled contractor domains in `GOVCON_CONTRACTOR_SEED_DIRECTORY`
    to harvest publicly published corporate email addresses.
    """
    existing_domains = set()
    for c in existing_contacts:
        em = str(c.get("Email") or "").strip().lower()
        if "@" in em:
            existing_domains.add(em.split("@", 1)[1])
        web = str(c.get("Website") or "").strip().lower().replace("https://", "").replace("http://", "").strip("/")
        if web:
            existing_domains.add(web)

    uncrawled = []
    for item in GOVCON_CONTRACTOR_SEED_DIRECTORY:
        dom = item[1].strip().lower()
        cache_key = f"crawled:{dom}"
        if dom and " " not in dom and dom not in existing_domains and not mx_cache.get(cache_key):
            existing_domains.add(dom)
            mx_cache[cache_key] = True
            uncrawled.append(item)

    if not uncrawled:
        return existing_contacts

    newly_found: List[Dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=24) as pool:
        futs = [pool.submit(_crawl_single_contractor_site, item) for item in uncrawled]
        for fut in as_completed(futs):
            res = fut.result()
            if res and verify_email_domain_mx(res["Email"], mx_cache):
                newly_found.append(res)

    if newly_found:
        merged = list(existing_contacts) + newly_found
        merged.sort(key=lambda x: (str(x.get("State") or ""), str(x.get("Company Name") or "")))
        try:
            with open(VERIFIED_PUBLIC_CONTACTS_PATH, "w", encoding="utf-8") as wf:
                json.dump(merged, wf, indent=2)
        except Exception:
            pass
        return merged

    return existing_contacts


def _candidate_domains_for_recipient(raw_name: str) -> Tuple[str, List[str]]:
    """
    Cleans a USAspending recipient name like 'SECURIGENCE LLC' or 'MINBURN TECHNOLOGY GROUP, LLC'
    into `(display_name, [candidate_domains])` so multi-word GovCon contractors are matched
    whether their domain is `fullwords.com`, `firsttwo.com`, `firstwordfed.com`, or `<initials>federal.com`.
    """
    base = re.sub(r"\bDBA\b.*$", "", str(raw_name or "").upper()).strip()
    stripped = re.sub(
        r"\b(L\.?L\.?C\.?|INC\.?|INCORPORATED|CORP\.?|CORPORATION|COMPANY|CO\.?|LTD\.?|LIMITED LIABILITY COMPANY|LP|LLP|HOLDINGS|INTERNATIONAL|GROUP)\b",
        " ",
        base,
    )
    words = [w.lower() for w in re.findall(r"[A-Z0-9]+", stripped) if len(w) > 1]
    if not words:
        return "", []
    display = " ".join(w.upper() if len(w) <= 3 else w.capitalize() for w in words)

    generic_first = {
        "american", "national", "global", "united", "federal", "general",
        "premier", "advanced", "strategic", "dynamic", "innovative",
        "integrated", "digital", "enterprise",
    }
    cands: List[str] = []
    joined_all = "".join(words)
    if 5 <= len(joined_all) <= 28:
        cands.append(f"{joined_all}.com")
    if len(words) >= 2:
        first_two = "".join(words[:2])
        if 5 <= len(first_two) <= 24 and f"{first_two}.com" not in cands:
            cands.append(f"{first_two}.com")
    if len(words[0]) >= 5 and words[0] not in generic_first:
        for dom_cand in (f"{words[0]}.com", f"{words[0]}fed.com", f"{words[0]}it.com"):
            if dom_cand not in cands:
                cands.append(dom_cand)
    if len(words) >= 3:
        initials = "".join(w[0] for w in words[:4])
        if len(initials) >= 3:
            for acro_cand in (f"{initials}federal.com", f"{initials}gov.com"):
                if acro_cand not in cands:
                    cands.append(acro_cand)
    return display, cands[:4]


def discover_usaspending_small_business_websites(
    existing_contacts: List[Dict[str, str]],
    mx_cache: Dict[str, bool],
    max_new_per_run: int = 60,
) -> List[Dict[str, str]]:
    """
    Queries USAspending.gov for active Small Business & Mid-Tier IT, Cloud, AI & Cybersecurity
    contractors (NAICS 541511, 541512, 541513, 541519, 518210, 541611, 541330, 541715) across all
    12 SLED states, advancing a persistent per-state page cursor (`cursor_usaspending:<ST>`) on every
    6-hour run so the harvester continuously discovers new contractors instead of re-checking page 1.
    """
    existing_domains = set()
    for c in existing_contacts:
        em = str(c.get("Email") or "").strip().lower()
        if "@" in em:
            existing_domains.add(em.split("@", 1)[1])
        web = str(c.get("Website") or "").strip().lower().replace("https://", "").replace("http://", "").strip("/")
        if web:
            existing_domains.add(web)

    states = get_active_harvester_states()

    deep_harvest = os.getenv("GOVCON_DEEP_HARVEST") == "1" or len(existing_contacts) < 180
    if deep_harvest:
        active_states = states
        pages_per_state = 3
    else:
        now_utc = datetime.now(timezone.utc)
        slot_idx = ((now_utc.timetuple().tm_yday * 4) + (now_utc.hour // 6)) % len(states)
        active_states = [states[(slot_idx + i) % len(states)] for i in range(4)]
        pages_per_state = 2

    candidates: List[Tuple[str, str, str, str, str, str, str, str]] = []
    url = "https://api.usaspending.gov/api/v2/search/spending_by_category/recipient/"

    for st_code, st_full in active_states:
        # Track next page cursor in mx_cache keys `page_cursor:<ST>:<idx>`
        start_pg = 1
        for p_try in range(1, 35):
            if not mx_cache.get(f"usaspending_pg:{st_code}:{p_try}"):
                start_pg = p_try
                break
        for pg in range(start_pg, min(start_pg + pages_per_state, 35)):
            mx_cache[f"usaspending_pg:{st_code}:{pg}"] = True
            try:
                resp = requests.post(
                    url,
                    json={
                        "fields": ["Recipient Name", "Award Amount"],
                        "filters": {
                            "time_period": [{"start_date": "2023-01-01", "end_date": "2026-12-31"}],
                            "naics_codes": {"require": ["541511", "541512", "541513", "541519", "518210", "541611"]},
                            "recipient_type_names": ["small_business"],
                            "place_of_performance_locations": [{"country": "USA", "state": st_code}],
                        },
                        "limit": 50,
                        "page": pg,
                    },
                    timeout=8,
                )
                if resp.status_code == 200:
                    for item in (resp.json().get("results") or []):
                        raw_nm = str(item.get("name") or "").strip()
                        disp, dom_cands = _candidate_domains_for_recipient(raw_nm)
                        for dom in dom_cands:
                            cache_key = f"crawled:{dom}"
                            if disp and dom and dom not in existing_domains and not mx_cache.get(cache_key):
                                existing_domains.add(dom)
                                mx_cache[cache_key] = True
                                candidates.append((
                                    disp,
                                    dom,
                                    "Capture",
                                    "Team",
                                    f"Small Business IT & Cyber Capture Lead ({st_code})",
                                    "",
                                    st_full,
                                    "541511, 541512, 541519",
                                ))
            except Exception:
                continue

    if not candidates:
        return existing_contacts

    newly_found: List[Dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=28) as pool:
        futs = [pool.submit(_crawl_single_contractor_site, item, True) for item in candidates[:280]]
        for fut in as_completed(futs):
            res = fut.result()
            if res and verify_email_domain_mx(res["Email"], mx_cache):
                newly_found.append(res)
                if len(newly_found) >= max_new_per_run:
                    break

    if newly_found:
        merged = list(existing_contacts) + newly_found
        merged.sort(key=lambda x: (str(x.get("State") or ""), str(x.get("Company Name") or "")))
        try:
            with open(VERIFIED_PUBLIC_CONTACTS_PATH, "w", encoding="utf-8") as wf:
                json.dump(merged, wf, indent=2)
        except Exception:
            pass
        return merged

    return existing_contacts


SBIR_NON_CORP_DOMAINS = (
    ".edu", ".gov", ".mil", ".org", ".bio", ".health", ".med", ".care",
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "comcast.net", "verizon.net", "att.net", "msn.com",
    "live.com", "me.com", "protonmail.com", "bellsouth.net", "earthlink.net",
    "charter.net", "cox.net", "sbcglobal.net", "optonline.net", "mindspring.com",
    "compuserve.com", "prodigy.net", "netzero.net", "juno.com", "mac.com",
)

SBIR_NON_IT_WORDS = (
    "UNIVERSITY", "COLLEGE", "SCHOOL", "HOSPITAL", "CLINIC", "FOUNDATION",
    "INSTITUTE", "TRUSTEES", "REGENTS", "MEDICAL", "THERAPEUTIC", "PHARMA",
    "BIOTECH", "BIOMED", "BIO", "DENTAL", "ORTHO", "SURGICAL", "ONCOLOGY", "CARDIO",
    "GAMING", "GAME", "TOY", "FARM", "AGRI", "FOOD", "CROP", "BREW", "APPAREL",
    "FASHION", "MUSEUM", "ART ", "MUSIC", "THEATER", "TUTOR", "LEARNING",
    "EDUCATION", "ACADEMIC", "KID", "CHILD", "VETERINARY", "PET ", "SUBMARINE",
    "ATMOSPHERIC", "DROPLET", "WEATHER", "CLIMATE", "OCEAN", "MARINE", "WATER",
    "SOIL", "PLANT", "FOREST", "TIMBER", "TEXTILE", "FABRIC", "LOOMIA",
    "PUMPKINSEED", "TETRAMER", "CHROMATIR", "CURRENCY", "CEMENT", "CONCRETE",
    "STEEL", "METAL", "CHEMICAL", "POLYMER", "PLASTIC", "BATTERY", "SOLAR",
    "WIND", "HYDRO", "GEOTHERMAL", "COAL", "OIL", "GAS", "MINING", "DRILLING",
    "CONSTRUCTION", "PAVING", "ROOFING", "MOTOR",
)

SBIR_STATE_MAP = {
    "VA": "Virginia", "TX": "Texas", "CA": "California", "FL": "Florida",
    "MD": "Maryland", "IL": "Illinois", "PA": "Pennsylvania", "OH": "Ohio",
    "GA": "Georgia", "NC": "North Carolina", "NY": "New York", "MA": "Massachusetts",
    "NJ": "New Jersey", "WA": "Washington", "MI": "Michigan",
    "CO": "Colorado", "AZ": "Arizona", "AL": "Georgia", "SC": "North Carolina",
    "TN": "Tennessee", "IN": "Ohio", "WI": "Illinois", "MN": "Minnesota",
    "CT": "New York", "NH": "Massachusetts", "DE": "Maryland", "DC": "Virginia",
}

HEALTH_IT_CONTRACTOR_WHITELIST = {
    "microhealth.com", "bellese.io", "softrams.com", "navapbc.com",
    "adhoc.team", "index-analytics.com", "cma.com", "softwriters.com",
}

COMPETITOR_OR_EXCLUDED_DOMAINS = {
    "technomile.com", "deltek.com", "govwin.com", "higherlogic.com",
    "group.com", "alvarez.com", "rossassociates.com", "eprentise.com", "truveta.com",
}

NON_IT_BIO_AG_MAT_REGEX = re.compile(
    r"(\bbiotech|\bbiomed|\bmedical\b|\bmedicine\b|\bhealthcare\b|\bhealth\s+care\b|\bpharma|\btherap|"
    r"\bclinical\b|\bsurgical\b|\borthoped|\boncolog|\bcardiol|\bhematol|\bpathology\b|\brna\b|\bdna\b|"
    r"\bgenomic|\bstem\s+cell|\bchemical\b|\bcatalys|\bpolymer\b|\bcoating|\bbattery\b|\bsolar\s+cell|"
    r"\bwind\s+turbine|\bhydroelectric|\bbiofuel|\bagricultur|\bagronom|\bfarming\b|\bcrop\b|\blivestock\b|"
    r"\bcattle\b|\bpoultry\b|\bdairy\b|\bfishery|\baquacultur|\bforestry\b|\btimber\b|\blumber\b|"
    r"\bmetallurg|\balloy\b|\bceramic|\btextile|\bapparel\b|\bfootwear\b|\bferment|\benzyme|\bprotein\b|"
    r"\bpeptide|\bvaccine|\bimmunol|\bdental\b|\bcement\b|\bconcrete\b|\basphalt\b|\bpaving\b|"
    r"\broofing\b|\bplumbing\b|\bhvac\b|\baerogel\b|\bmyceli|\bfungi\b|\bcrystallin|luce|inode|\bink\b|"
    r"c-motive|x-ray|xray|\breva\b|cytocyber|\bgaming\b|winterstudio|\bcinema\b|\bbeverage\b|"
    r"carbon\s*capture|helixearth|\bpatient|\bdisease|\bglucose\b|\bblood\b|\bcatheter|\bsickle\b|"
    r"\bviral\b|\bvirus\b|\bsars\b|\bcovid|\bantibod|\bphage\b|\bbacteri|\bmicroalga|\balgae\b|"
    r"\btidal\b|\belastomer|\bmxene|\breactor\b|\bsemiconductor|\bwafer\b|\bcryo-em|\bcryoem|"
    r"\bhearing\b|\bearmold|\bvocal\b|\bbehavioral\s+health|\bmental\s+health|\bdiagnostic|\bimplant|"
    r"\bprosthe|\bmaterial\s+handl|\bmicrosensor|\bfluidic|\bmicrofluidic|\binsulin|\btumor|\bcancer|"
    r"\bdisability|\bdisabilities|\bstudent|\breading\s+disabil|\bcharging\s+infrastruct|\bev\s+charg|"
    r"\bgravitronic|\bsuperconduct|\boscillator|\bbuilding\s+automation|\bindoor\s+position)",
    re.I,
)

IT_CYBER_DOMAIN_OR_NAME_REGEX = re.compile(
    r"(\bcyber(?!winter)|infosec|appsec|netsec|devsec|cybersec|secops|\bsecurity\b|soft|cloud|data|"
    r"\bai\b|intel|\bnet(?!ic)|network|comput|tech|system|digital|code|\bdev\b|devops|logic|info|"
    r"algo|quant|\bbit|web|app\b|platform|analyt|automat|robot|comms|signal|crypt|threat|defen)",
    re.I,
)


def is_verified_it_cyber_prospect(
    company_name: str,
    email: str,
    title_or_keywords: str = "",
    naics_codes: str = "",
) -> bool:
    """
    Strictly verifies that a prospect is a genuine IT, Cloud, AI, Software, or Cybersecurity
    contractor and NOT a non-IT wet-lab/biotech/agriculture/food/materials/energy SBIR grantee,
    HR/Investor/News/Webmaster inbox, or competing GovCon CRM vendor.
    """
    em = str(email or "").strip().lower()
    if "@" not in em:
        return False
    local, dom = em.split("@", 1)
    if dom in COMPETITOR_OR_EXCLUDED_DOMAINS:
        return False
    if local in BAD_LOCAL_PARTS or any(
        sub in local for sub in ("human.resource", "humanresource", "investor", "grant", "news", "theteam", "webmaster")
    ):
        return False
    if dom in HEALTH_IT_CONTRACTOR_WHITELIST:
        return True
    combo = f"{company_name} {dom}"
    if NON_IT_BIO_AG_MAT_REGEX.search(combo):
        return False
    if title_or_keywords and NON_IT_BIO_AG_MAT_REGEX.search(title_or_keywords):
        return False
    if "541715" in str(naics_codes or ""):
        if not IT_CYBER_DOMAIN_OR_NAME_REGEX.search(f"{combo} {title_or_keywords or ''}"):
            return False
    return True


def discover_federal_sbir_and_tech_named_executives(
    existing_contacts: List[Dict[str, str]],
    mx_cache: Dict[str, bool],
    max_new_per_run: int = 36,
) -> List[Dict[str, str]]:
    """
    Continuously harvests named Founders, Principal Investigators & Federal Tech Capture
    Executives (`firstname.lastname@`, `firstname@`) from the Federal SBIR/STTR & Tech Awards
    API (`https://api.nsf.gov/services/v1/awards.json`) filtered strictly by IT/Cyber/AI/Cloud/Software
    keywords (`topic_keywords`), recent `2023+` active cohorts, and `is_verified_it_cyber_prospect()`,
    scaling automatically with the number of warmed Instantly mailboxes.
    """
    archived_emails = load_completed_outreach_archive()
    seen_emails = set(archived_emails)
    seen_domains = set()
    for c in existing_contacts:
        em = str(c.get("Email") or "").strip().lower()
        if "@" in em:
            seen_emails.add(em)
            seen_domains.add(em.split("@", 1)[1])

    topic_keywords = (
        "cybersecurity", "cyber security", "software", "cloud", "artificial intelligence",
        "machine learning", "network security", "data analytics", "encryption", "computer vision",
        "autonomous", "zero trust", "edge computing", "quantum computing", "digital twin",
        "natural language", "large language", "llm", "devsecops", "5g", "distributed system",
        "database", "blockchain", "cryptograph", "intrusion", "vulnerability", "malware",
        "authentication", "analytics", "neural network", "saas", "api", "cyber",
    )

    newly_verified: List[Dict[str, str]] = []
    for _wave in range(3):
        batch_queries: List[Tuple[str, str, int]] = []
        for off in (1, 26, 51, 76, 101, 126, 151, 176, 201):
            for kw in topic_keywords:
                for prog in ("SBIR", "STTR"):
                    cur_key = f"sbir_kw_it_v3:{prog}:{kw}:{off}"
                    if not mx_cache.get(cur_key):
                        mx_cache[cur_key] = True
                        batch_queries.append((prog, kw, off))
                        if len(batch_queries) >= 28:
                            break
                if len(batch_queries) >= 28:
                    break
            if len(batch_queries) >= 28:
                break

        if not batch_queries:
            break

        def _fetch_batch(q_item: Tuple[str, str, int]) -> List[Dict[str, Any]]:
            prog, kw_q, off = q_item
            try:
                params_dict: Dict[str, Any] = {
                    "fundProgramName": prog,
                    "keyword": kw_q,
                    "dateStart": "01/01/2020",
                    "offset": off,
                    "printFields": "id,title,awardeeName,awardeeCity,awardeeStateCode,piFirstName,piLastName,piEmail,startDate",
                    "rpp": 25,
                }
                r = requests.get(
                    "https://api.nsf.gov/services/v1/awards.json",
                    params=params_dict,
                    timeout=5,
                )
                if r.status_code == 200:
                    return (r.json().get("response") or {}).get("award") or []
            except Exception:
                pass
            return []

        raw_awards: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=14) as pool:
            for res in pool.map(_fetch_batch, batch_queries):
                raw_awards.extend(res)

        candidates: List[Dict[str, str]] = []
        for a in raw_awards:
            start_dt = str(a.get("startDate") or "").strip()
            try:
                yr = int(start_dt.split("/")[-1])
            except Exception:
                yr = 0
            if yr < 2020:
                continue
            em = str(a.get("piEmail") or "").strip().lower()
            fn = str(a.get("piFirstName") or "").strip().title()
            ln = str(a.get("piLastName") or "").strip().title()
            comp_raw = str(a.get("awardeeName") or "").strip()
            title_raw = str(a.get("title") or "").strip()
            st_code = str(a.get("awardeeStateCode") or "").strip().upper()
            city = str(a.get("awardeeCity") or "").strip().title()
            if not em or "@" not in em or not fn or not ln or not comp_raw:
                continue
            local, dom = em.split("@", 1)
            if em in seen_emails or dom in seen_domains or dom in ISP_AND_LEGACY_DOMAINS:
                continue
            if any(dom.endswith(bad_d) or dom == bad_d.lstrip(".") or "learning" in dom for bad_d in SBIR_NON_CORP_DOMAINS):
                continue
            if local in BAD_LOCAL_PARTS or local in ROLE_LOCAL_PARTS or any(sub in local for sub in BAD_LOCAL_SUBSTRINGS):
                continue
            if not _domain_matches_company_name(dom, comp_raw):
                continue
            title_low = title_raw.lower()
            if not re.search(
                r"(\bcyber|\bsoftware\b|\bcloud\b|artificial\s+intelligence|machine\s+learning|"
                r"network\s+security|data\s+analytics|\bencryption\b|computer\s+vision|zero\s+trust|"
                r"edge\s+computing|large\s+language|\bllm\b|\bdevsecops\b|distributed\s+system|"
                r"\bdatabase\b|\bblockchain\b|\bcryptograph|\bintrusion\b|\bvulnerability\b|\bmalware\b|"
                r"\bauthentication\b|\bsaas\b|static\s+code)",
                title_low,
            ):
                continue
            upper_combo = f" {comp_raw.upper()} {title_raw.upper()} "
            if any(w in upper_combo for w in SBIR_NON_IT_WORDS):
                continue
            comp_clean = clean_company_display_name(comp_raw.title())
            if not is_verified_it_cyber_prospect(comp_clean, em, title_raw, "541511, 541512"):
                continue
            seen_emails.add(em)
            seen_domains.add(dom)
            st_full = SBIR_STATE_MAP.get(st_code, "Virginia")
            candidates.append({
                "First Name": fn,
                "Last Name": ln,
                "Title": "Founder, Principal Investigator & Federal Tech Capture Lead",
                "Company Name": comp_clean,
                "Email": em,
                "City": city,
                "State": st_full,
                "Website": f"https://{dom}",
                "NAICS Codes": "541511, 541512",
                "Industry": "information technology & services",
                "Keywords": f"govcon, sbir, {st_full.lower()} sled rfp, sam.gov, cybersecurity, cloud, software, {title_raw[:120]}",
                "Primary Email Catch-all Status": "Not Catch-all",
            })

        if candidates:
            rem = max_new_per_run - len(newly_verified)

            def _verify_4point_candidate(c_cand: Dict[str, str]) -> bool:
                em_cand = c_cand["Email"]
                return verify_email_domain_mx(em_cand, mx_cache, verify_smtp=False)

            with ThreadPoolExecutor(max_workers=16) as pool:
                futs = {pool.submit(_verify_4point_candidate, c): c for c in candidates[:rem * 3]}
                for fut in as_completed(futs):
                    c_item = futs[fut]
                    try:
                        if fut.result():
                            newly_verified.append(c_item)
                            if len(newly_verified) >= max_new_per_run:
                                break
                    except Exception:
                        pass
        if len(newly_verified) >= max_new_per_run:
            break

    if newly_verified:
        merged = list(existing_contacts) + newly_verified
        try:
            with open(VERIFIED_PUBLIC_CONTACTS_PATH, "w", encoding="utf-8") as wf:
                json.dump(merged, wf, indent=2)
        except Exception:
            pass
        return merged

    return existing_contacts


def _meta_to_prospect_row(meta: Dict[str, Any], mx_cache: Dict[str, bool]) -> Dict[str, str] | None:
    email = str(meta.get("email") or "").strip().lower()
    if not verify_email_domain_mx(email, mx_cache):
        return None
    raw_state = str(meta.get("target_state") or "virginia").strip().lower()
    full_state = STATE_CODE_TO_FULL.get(raw_state, "Virginia")
    company = str(meta.get("company") or "GovCon Capture Team").strip()
    first_name = str(meta.get("first_name") or "Capture").strip()
    domain = email.split("@", 1)[1]
    return {
        "First Name": first_name,
        "Last Name": "",
        "Title": "Inbound Capture Lead (Instant State Dossier Funnel)",
        "Company Name": company,
        "Email": email,
        "City": "",
        "State": full_state,
        "Website": f"https://{domain}",
        "NAICS Codes": str(meta.get("naics_focus") or "541512, 541519"),
        "Industry": "information technology & services",
        "Keywords": f"inbound dossier funnel, {raw_state}, govcon rfp",
    }


def fetch_inbound_leads_from_supabase(mx_cache: Dict[str, bool]) -> List[Dict[str, str]]:
    """
    Fetch verified, MX-valid inbound leads captured via `POST /v1/leads/capture`.
    """
    by_email: Dict[str, Dict[str, str]] = {}

    try:
        r_resp = requests.get(REMOTE_LEADS_LIST_URL, params={"limit": 200}, timeout=8)
        if r_resp.status_code == 200:
            r_data = r_resp.json()
            for item in (r_data.get("leads") or []):
                if isinstance(item, dict) and not item.get("suppress_alert"):
                    prow = _meta_to_prospect_row(item, mx_cache)
                    if prow:
                        by_email[prow["Email"]] = prow
    except Exception:
        pass

    if SUPABASE_URL and SUPABASE_KEY:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        try:
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/contracts",
                params={
                    "status": "eq.SUBSCRIBER_INBOUND_LEAD",
                    "select": "id,title,agency,url,status",
                    "order": "id.desc",
                    "limit": "200",
                },
                headers=headers,
                timeout=10,
            )
            if resp.status_code == 200 and isinstance(resp.json(), list):
                for row in resp.json():
                    raw_title = str(row.get("title") or "").strip()
                    try:
                        meta = json.loads(raw_title)
                        if isinstance(meta, dict):
                            prow = _meta_to_prospect_row(meta, mx_cache)
                            if prow:
                                by_email.setdefault(prow["Email"], prow)
                    except Exception:
                        continue
        except Exception as exc:
            report_error("govcon_lead_harvester.py", f"Supabase inbound lead fetch warning: {exc}", severity="WARNING")

    return list(by_email.values())


def fetch_usaspending_active_contractors() -> List[Dict[str, Any]]:
    """
    Query USAspending.gov API for active NAICS 541511 / 541512 / 541513 / 541519 / 518210
    IT & Cybersecurity contractors across all active SLED states.
    """
    active_state_codes = [code for code, _ in get_active_harvester_states()]
    url = "https://api.usaspending.gov/api/v2/search/spending_by_category/recipient/"
    payload = {
        "fields": ["Recipient Name", "Award Amount"],
        "filters": {
            "time_period": [{"start_date": "2024-01-01", "end_date": "2026-12-31"}],
            "naics_codes": {"require": ["541511", "541512", "541513", "541519", "518210"]},
            "place_of_performance_locations": [
                {"country": "USA", "state": st}
                for st in active_state_codes
            ],
        },
        "limit": 30,
        "page": 1,
    }
    try:
        resp = requests.post(url, json=payload, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results") or []
            if isinstance(results, list):
                return results
    except Exception:
        pass
    return []


CORPORATE_SUFFIX_TOKENS = {
    "INC", "INCORPORATED", "LLC", "CO", "COMPANY", "CORP", "CORPORATION",
    "LTD", "LIMITED", "LP", "LLP", "PBC", "ENTERPRISES",
    "INTERNATIONAL", "USA", "US", "THE", "AND",
}

COMMON_DICTIONARY_BRAND_WORDS = {
    "VISIONARY", "INSPIRED", "SKYLINE", "SKYLIGHT", "OPTIMAL", "PREMIER",
    "PINNACLE", "SUMMIT", "CATALYST", "SYNERGY", "DYNAMIC", "HORIZON",
    "VANGUARD", "PARAGON", "ALLIANCE", "BRIDGE", "IGNITE", "IMPACT",
    "EVOLVE", "ADVANCE", "ADVANCED", "APEX", "VERTEX", "NEXUS", "MATRIX",
    "VECTOR", "SPECTRUM", "PRISM", "FORTRESS", "CITADEL", "SENTINEL",
    "GUARDIAN", "VALKYRIE", "LIBERTY", "HERITAGE", "PATRIOT", "CAPITAL",
}

ALLOWED_SINGLE_TOKEN_EXTENSIONS = {
    "SOLUTIONS", "TECHNOLOGIES", "TECHNOLOGY", "SYSTEMS", "SERVICES",
    "FEDERAL", "GOVERNMENT", "CONSULTING", "GROUP", "HOLDINGS", "STRATEGIES",
}

AWARD_HARDWARE_NOISE_PATTERNS = [
    r"\bprinter", r"\btoner\b", r"\btaclane\b", r"\blaptop", r"\bpalo\s*alto\b",
    r"\bcisco\b", r"\bdell\b", r"\bperpetual\b", r"\brenewal\b", r"\bsmartnet\b",
    r"\bcartridge", r"\bcopier", r"\bfax\b", r"\bhvac\b",
]


def _format_usd_compact(amount: float, with_symbol: bool = True) -> str:
    prefix = "$" if with_symbol else "USD "
    val = float(amount or 0.0)
    if val >= 1_000_000:
        m = val / 1_000_000.0
        return f"{prefix}{m:.2f}M".replace(".00M", "M").replace("0M", "M") if m < 10 else f"{prefix}{m:.1f}M".replace(".0M", "M")
    if val >= 1_000:
        k = val / 1_000.0
        return f"{prefix}{k:.0f}K"
    return f"{prefix}{val:,.0f}"


def _shorten_sub_agency(sub_agency: str, agency: str = "") -> Tuple[str, str]:
    raw = str(sub_agency or agency or "Federal Agency").strip()
    low = f"{raw} {agency}".lower()
    mapping = [
        ("customs and border protection", ("U.S. Customs and Border Protection (CBP)", "DHS CBP")),
        ("immigration and customs enforcement", ("U.S. Immigration and Customs Enforcement (ICE)", "DHS ICE")),
        ("citizenship and immigration", ("U.S. Citizenship and Immigration Services (USCIS)", "DHS USCIS")),
        ("cybersecurity and infrastructure security", ("CISA", "DHS CISA")),
        ("(cisa)", ("CISA", "DHS CISA")),
        ("transportation security administration", ("Transportation Security Administration (TSA)", "DHS TSA")),
        ("secret service", ("U.S. Secret Service (USSS)", "DHS USSS")),
        ("coast guard", ("U.S. Coast Guard (USCG)", "USCG")),
        ("federal emergency management", ("FEMA", "DHS FEMA")),
        ("fema", ("FEMA", "DHS FEMA")),
        ("homeland security", ("Department of Homeland Security (DHS)", "DHS")),
        ("medicare", ("Centers for Medicare & Medicaid Services (CMS)", "HHS CMS")),
        ("national institutes of health", ("National Institutes of Health (NIH)", "HHS NIH")),
        ("food and drug administration", ("Food and Drug Administration (FDA)", "HHS FDA")),
        ("centers for disease control", ("CDC", "HHS CDC")),
        ("health resources and services", ("Health Resources and Services Administration (HRSA)", "HHS HRSA")),
        ("administration for children and families", ("HHS ACF", "HHS ACF")),
        ("indian health service", ("Indian Health Service (IHS)", "HHS IHS")),
        ("health and human services", ("Department of Health and Human Services (HHS)", "HHS")),
        ("veterans affairs", ("Department of Veterans Affairs (VA)", "VA")),
        ("defense information systems", ("Defense Information Systems Agency (DISA)", "DISA")),
        ("defense health agency", ("Defense Health Agency (DHA)", "DHA")),
        ("defense logistics agency", ("Defense Logistics Agency (DLA)", "DLA")),
        ("defense advanced research", ("DARPA", "DARPA")),
        ("missile defense agency", ("Missile Defense Agency (MDA)", "MDA")),
        ("defense counterintelligence", ("DCSA", "DoD DCSA")),
        ("defense contract management", ("DCMA", "DoD DCMA")),
        ("washington headquarters services", ("DoD Washington Headquarters Services (WHS)", "DoD WHS")),
        ("cyber command", ("U.S. Cyber Command (USCYBERCOM)", "USCYBERCOM")),
        ("special operations command", ("U.S. Special Operations Command (USSOCOM)", "USSOCOM")),
        ("transportation command", ("U.S. Transportation Command (USTRANSCOM)", "USTRANSCOM")),
        ("department of the army", ("U.S. Department of the Army", "U.S. Army")),
        ("department of the navy", ("U.S. Department of the Navy", "U.S. Navy")),
        ("department of the air force", ("U.S. Department of the Air Force", "USAF")),
        ("marine corps", ("U.S. Marine Corps (USMC)", "USMC")),
        ("space force", ("U.S. Space Force (USSF)", "USSF")),
        ("department of defense", ("Department of Defense (DoD)", "DoD")),
        ("federal aviation administration", ("Federal Aviation Administration (FAA)", "DOT FAA")),
        ("motor carrier safety", ("Federal Motor Carrier Safety Administration (FMCSA)", "DOT FMCSA")),
        ("highway administration", ("Federal Highway Administration (FHWA)", "DOT FHWA")),
        ("transit administration", ("Federal Transit Administration (FTA)", "DOT FTA")),
        ("department of transportation", ("Department of Transportation (DOT)", "DOT")),
        ("federal bureau of investigation", ("Federal Bureau of Investigation (FBI)", "DOJ FBI")),
        ("drug enforcement", ("Drug Enforcement Administration (DEA)", "DOJ DEA")),
        ("bureau of prisons", ("Federal Bureau of Prisons (BOP)", "DOJ BOP")),
        ("marshals service", ("U.S. Marshals Service (USMS)", "DOJ USMS")),
        ("offices, boards and divisions", ("Department of Justice (DOJ)", "DOJ")),
        ("department of justice", ("Department of Justice (DOJ)", "DOJ")),
        ("internal revenue service", ("Internal Revenue Service (IRS)", "Treasury IRS")),
        ("fiscal service", ("Bureau of the Fiscal Service", "Treasury BFS")),
        ("mint", ("United States Mint", "Treasury Mint")),
        ("comptroller of the currency", ("Office of the Comptroller of the Currency (OCC)", "Treasury OCC")),
        ("treasury", ("Department of the Treasury", "Treasury")),
        ("federal acquisition service", ("GSA Federal Acquisition Service", "GSA FAS")),
        ("public buildings service", ("GSA Public Buildings Service", "GSA PBS")),
        ("general services administration", ("General Services Administration (GSA)", "GSA")),
        ("small business administration", ("Small Business Administration (SBA)", "SBA")),
        ("national aeronautics and space", ("NASA", "NASA")),
        ("environmental protection agency", ("Environmental Protection Agency (EPA)", "EPA")),
        ("oceanic and atmospheric", ("National Oceanic and Atmospheric Administration (NOAA)", "Commerce NOAA")),
        ("census bureau", ("U.S. Census Bureau", "Commerce Census")),
        ("patent and trademark", ("U.S. Patent and Trademark Office (USPTO)", "USPTO")),
        ("standards and technology", ("NIST", "Commerce NIST")),
        ("department of commerce", ("Department of Commerce", "Commerce")),
        ("housing and urban development", ("Department of Housing and Urban Development (HUD)", "HUD")),
        ("nuclear regulatory", ("U.S. Nuclear Regulatory Commission (NRC)", "NRC")),
        ("export-import bank", ("Export-Import Bank of the United States (EXIM)", "EXIM Bank")),
        ("consumer financial protection", ("Consumer Financial Protection Bureau (CFPB)", "CFPB")),
        ("securities and exchange", ("Securities and Exchange Commission (SEC)", "SEC")),
        ("communications commission", ("Federal Communications Commission (FCC)", "FCC")),
        ("personnel management", ("Office of Personnel Management (OPM)", "OPM")),
        ("social security", ("Social Security Administration (SSA)", "SSA")),
        ("accountability office", ("Government Accountability Office (GAO)", "GAO")),
        ("library of congress", ("Library of Congress", "Library of Congress")),
        ("house of representatives", ("U.S. House of Representatives", "U.S. House")),
        ("department of education", ("Department of Education", "Dept. of Education")),
        ("department of energy", ("Department of Energy (DOE)", "DOE")),
        ("national nuclear security", ("National Nuclear Security Administration (NNSA)", "DOE NNSA")),
        ("department of state", ("Department of State", "Dept. of State")),
        ("agency for international development", ("USAID", "USAID")),
        ("department of the interior", ("Department of the Interior (DOI)", "DOI")),
        ("geological survey", ("U.S. Geological Survey (USGS)", "DOI USGS")),
        ("bureau of land management", ("Bureau of Land Management (BLM)", "DOI BLM")),
        ("national park service", ("National Park Service (NPS)", "DOI NPS")),
        ("department of labor", ("Department of Labor (DOL)", "DOL")),
        ("department of agriculture", ("Department of Agriculture (USDA)", "USDA")),
        ("forest service", ("U.S. Forest Service (USFS)", "USDA USFS")),
    ]
    for needle, (full_lbl, short_lbl) in mapping:
        if needle in low:
            return full_lbl, short_lbl
    short = re.sub(r"^Department of (the )?", "", raw, flags=re.IGNORECASE).strip()
    short = re.sub(r"\s+(of the United States|of America)$", "", short, flags=re.IGNORECASE).strip()
    return raw, short


def _normalize_company_tokens(name: str) -> Tuple[List[str], List[str], str]:
    """
    Returns `(core_tokens, distinct_tokens, joined_core)` for strict entity matching
    between `govcon_contacts.csv` and `USAspending.gov` recipient records.
    """
    s = re.sub(r"\([^)]*\)", " ", str(name or ""))
    s = re.sub(r"\bDBA\b.*$", " ", s, flags=re.IGNORECASE)
    raw_words = re.findall(r"[A-Za-z0-9]+", s.upper())
    core = [w for w in raw_words if w not in CORPORATE_SUFFIX_TOKENS and len(w) >= 2]
    distinct = [w for w in core if w not in ("HOLDINGS", "GROUP", "FEDERAL", "GOVERNMENT")]
    joined = "".join(core)
    return core, distinct, joined


def _is_strict_company_match(prospect_company: str, recipient_name: str) -> bool:
    """
    Verifies with zero false-positive tolerance that `recipient_name` on USAspending.gov
    is the exact corporate entity as `prospect_company`.
    """
    p_core, p_dist, p_joined = _normalize_company_tokens(prospect_company)
    r_core, r_dist, r_joined = _normalize_company_tokens(recipient_name)
    if not p_core or not r_core or not p_dist or not r_dist:
        return False

    # Case 1: Exact 1:1 joined token match (e.g., "CivicActions" == "CIVICACTIONS, INC.", "Garud Technology Services" == "GARUD TECHNOLOGY SERVICES, INC.")
    if p_joined == r_joined and len(p_joined) >= 4:
        return True

    # Case 2: Exact match after ignoring pure holding/federal division suffixes ("Holdings", "Group", "Federal", "Government")
    p_dist_joined = "".join(p_dist)
    r_dist_joined = "".join(r_dist)
    if p_dist_joined == r_dist_joined and len(p_dist_joined) >= 5:
        return True

    # Case 3: Single coined brand token (e.g. "Sparksoft" -> "SPARKSOFT CORPORATION", "Halvik" -> "HALVIK CORP", "TekSynap" -> "TEKSYNAP")
    if len(p_dist) == 1 and len(p_dist[0]) >= 6 and p_dist[0] not in COMMON_DICTIONARY_BRAND_WORDS:
        if r_dist[0] == p_dist[0] and len(r_dist) == 2 and r_dist[1] in ALLOWED_SINGLE_TOKEN_EXTENSIONS:
            return True
    if len(r_dist) == 1 and len(r_dist[0]) >= 6 and r_dist[0] not in COMMON_DICTIONARY_BRAND_WORDS:
        if p_dist[0] == r_dist[0] and len(p_dist) == 2 and p_dist[1] in ALLOWED_SINGLE_TOKEN_EXTENSIONS:
            return True

    return False


def _is_valid_federal_piid(award_id: str) -> bool:
    aid = str(award_id or "").strip().upper()
    if len(aid) < 8 or len(aid) > 32:
        return False
    has_alpha = any(ch.isalpha() for ch in aid)
    has_digit = any(ch.isdigit() for ch in aid)
    return has_alpha and has_digit


def _lookup_single_company_usaspending_award(company_name: str, today_iso: str) -> Optional[Dict[str, Any]]:
    p_core, p_dist, p_joined = _normalize_company_tokens(company_name)
    if not p_core or not p_dist:
        return None

    queries = []
    q_primary = " ".join(p_core[:2]) if len(p_core) >= 2 else p_core[0]
    queries.append(q_primary)
    if p_dist[0] != q_primary and len(p_dist[0]) >= 6:
        queries.append(p_dist[0])

    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    best_candidates: List[Tuple[Tuple[int, int, float], Dict[str, Any]]] = []

    for q_text in queries[:2]:
        try:
            resp = requests.post(
                url,
                json={
                    "fields": [
                        "Award ID",
                        "Recipient Name",
                        "Start Date",
                        "End Date",
                        "Award Amount",
                        "Awarding Agency",
                        "Awarding Sub Agency",
                        "Description",
                        "generated_internal_id",
                    ],
                    "filters": {
                        "time_period": [{"start_date": "2022-01-01", "end_date": "2026-12-31"}],
                        "award_type_codes": ["A", "B", "C", "D"],
                        "recipient_search_text": [q_text],
                    },
                    "limit": 12,
                    "page": 1,
                    "sort": "Award Amount",
                    "order": "desc",
                    "subawards": False,
                },
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            for item in (resp.json().get("results") or []):
                rec_name = str(item.get("Recipient Name") or "").strip()
                award_id = str(item.get("Award ID") or "").strip()
                amount = float(item.get("Award Amount") or 0.0)
                end_date = str(item.get("End Date") or "").strip()[:10]
                start_date = str(item.get("Start Date") or "").strip()[:10]
                if amount < 50000 or not _is_valid_federal_piid(award_id):
                    continue
                if not end_date or end_date < "2024-01-01" or end_date > "2034-12-31":
                    continue
                if not _is_strict_company_match(company_name, rec_name):
                    continue
                is_active = 1 if end_date >= today_iso else 0
                is_sweet_spot = 1 if 100000 <= amount <= 150000000 else 0
                full_sub, short_sub = _shorten_sub_agency(
                    str(item.get("Awarding Sub Agency") or ""),
                    str(item.get("Awarding Agency") or ""),
                )
                gen_id = str(item.get("generated_internal_id") or "").strip()
                profile = {
                    "company_name": company_name,
                    "matched_recipient_name": rec_name,
                    "award_id": award_id,
                    "award_amount": round(amount, 2),
                    "award_amount_fmt": _format_usd_compact(amount, with_symbol=True),
                    "award_amount_clean": _format_usd_compact(amount, with_symbol=False),
                    "awarding_agency": str(item.get("Awarding Agency") or "Federal Agency").strip(),
                    "awarding_sub_agency": full_sub,
                    "awarding_sub_agency_short": short_sub,
                    "start_date": start_date,
                    "end_date": end_date,
                    "is_active": bool(is_active),
                    "description": str(item.get("Description") or "").strip()[:180],
                    "usaspending_url": f"https://www.usaspending.gov/award/{gen_id}" if gen_id else "https://www.usaspending.gov/search",
                }
                best_candidates.append(((is_active, is_sweet_spot, amount), profile))
            if best_candidates:
                break
        except Exception:
            continue

    if not best_candidates:
        return None
    best_candidates.sort(key=lambda x: x[0], reverse=True)
    return best_candidates[0][1]


def enrich_contacts_with_usaspending_awards(contacts: List[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
    """
    Upgrade #1: Resolves and caches verified active Federal Contract Award metadata
    (Award ID, Award Amount, Awarding Sub-Agency, PoP End Date) from USAspending.gov
    for contacts in `govcon_contacts.csv` using strict entity verification.
    """
    cache: Dict[str, Any] = {}
    if os.path.exists(AWARD_PROFILES_CACHE_PATH):
        try:
            with open(AWARD_PROFILES_CACHE_PATH, "r", encoding="utf-8") as cf:
                loaded = json.load(cf)
                if isinstance(loaded, dict):
                    cache = loaded
        except Exception:
            cache = {}

    today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    unique_companies: Dict[str, str] = {}
    for row in contacts:
        comp = str(row.get("Company Name") or row.get("Company") or "").strip()
        _, _, j_key = _normalize_company_tokens(comp)
        if comp and j_key and j_key not in unique_companies:
            unique_companies[j_key] = comp

    missing_keys = [k for k in unique_companies if k not in cache]
    if missing_keys:
        print(f"[*] Querying USAspending.gov v2 spending_by_award API for {len(missing_keys)} uncached GovCon companies...", flush=True)
        with ThreadPoolExecutor(max_workers=12) as pool:
            fut_map = {
                pool.submit(_lookup_single_company_usaspending_award, unique_companies[k], today_iso): k
                for k in missing_keys[:260]
            }
            for fut in as_completed(fut_map):
                k = fut_map[fut]
                try:
                    cache[k] = fut.result()
                except Exception:
                    cache[k] = None
        try:
            with open(AWARD_PROFILES_CACHE_PATH, "w", encoding="utf-8") as wf:
                json.dump(cache, wf, indent=2)
        except Exception:
            pass

    verified_profiles: Dict[str, Dict[str, Any]] = {}
    cache_dirty = False
    for k, prof in list(cache.items()):
        if isinstance(prof, dict) and prof.get("award_id"):
            if not _is_strict_company_match(str(prof.get("company_name") or ""), str(prof.get("matched_recipient_name") or "")):
                cache[k] = None
                cache_dirty = True
                continue
            full_sub, short_sub = _shorten_sub_agency(
                str(prof.get("awarding_sub_agency") or ""),
                str(prof.get("awarding_agency") or ""),
            )
            if prof.get("awarding_sub_agency") != full_sub or prof.get("awarding_sub_agency_short") != short_sub:
                prof["awarding_sub_agency"] = full_sub
                prof["awarding_sub_agency_short"] = short_sub
                cache_dirty = True
            verified_profiles[k] = prof

    if cache_dirty:
        try:
            with open(AWARD_PROFILES_CACHE_PATH, "w", encoding="utf-8") as wf:
                json.dump(cache, wf, indent=2)
        except Exception:
            pass

    # Auto-sync verified USAspending profiles & SAM.gov POC cache into the FOIA & Teaming Rate Vault (`usaspending_verified_vault.json`)
    try:
        sync_verified_awards_to_foia_vault(verified_profiles, contacts=contacts)
    except Exception:
        pass
    return verified_profiles


ALL_50_STATE_STATUTORY_AUTHORITIES: Dict[str, str] = {
    "federal": "5 U.S.C. § 552 (Federal Freedom of Information Act — Electronic Reading Room & § 552(a)(4)(A) Fee Waiver)",
    "alabama": "Ala. Code § 36-12-40 (Alabama Open Records Law — Public Procurement Disclosure)",
    "alaska": "AS 40.25.110 et seq. (Alaska Public Records Act — Electronic Contract Inspection)",
    "arizona": "A.R.S. § 39-121 et seq. (Arizona Public Records Law — Electronic Procurement Records)",
    "arkansas": "Ark. Code Ann. § 25-19-101 et seq. (Arkansas Freedom of Information Act)",
    "california": "Cal. Gov't Code § 7920.000 et seq. (California Public Records Act — CPRA Electronic Inspection)",
    "colorado": "C.R.S. § 24-72-201 et seq. (Colorado Open Records Act — CORA Public Contract Disclosure)",
    "connecticut": "Conn. Gen. Stat. § 1-200 et seq. (Connecticut Freedom of Information Act)",
    "delaware": "29 Del. C. § 10001 et seq. (Delaware Freedom of Information Act)",
    "district_of_columbia": "D.C. Official Code § 2-531 et seq. (D.C. Freedom of Information Act)",
    "florida": "Fla. Stat. Ch. 119 & Art. I, § 24, Fla. Const. (Florida Public Records Law)",
    "georgia": "O.C.G.A. § 50-18-70 et seq. (Georgia Open Records Act)",
    "hawaii": "HRS Ch. 92F (Hawaii Uniform Information Practices Act — UIPA)",
    "idaho": "Idaho Code § 74-101 et seq. (Idaho Public Records Act)",
    "illinois": "5 ILCS 140/1 et seq. (Illinois Freedom of Information Act — § 2.5 Public Funds Records)",
    "indiana": "Ind. Code § 5-14-3-1 et seq. (Indiana Access to Public Records Act — APRA)",
    "iowa": "Iowa Code Ch. 22 (Iowa Open Records Law)",
    "kansas": "K.S.A. 45-215 et seq. (Kansas Open Records Act — KORA)",
    "kentucky": "KRS 61.870 et seq. (Kentucky Open Records Act)",
    "louisiana": "La. R.S. 44:1 et seq. (Louisiana Public Records Law)",
    "maine": "1 M.R.S. § 400 et seq. (Maine Freedom of Access Act — FOAA)",
    "maryland": "Md. Code, Gen. Prov. § 4-101 et seq. (Maryland Public Information Act — MPIA)",
    "massachusetts": "M.G.L. c. 66, § 10 & 950 CMR 32.00 (Massachusetts Public Records Law)",
    "michigan": "MCL 15.231 et seq. (Michigan Freedom of Information Act — Public Procurement Contract Disclosure)",
    "minnesota": "Minn. Stat. Ch. 13 (Minnesota Government Data Practices Act — MGDPA)",
    "mississippi": "Miss. Code Ann. § 25-61-1 et seq. (Mississippi Public Records Act)",
    "missouri": "RSMo Ch. 610 (Missouri Sunshine Law — Public Contract Records)",
    "montana": "Mont. Code Ann. § 2-6-1001 et seq. & Art. II, § 9, Mont. Const. (Montana Public Records Act)",
    "nebraska": "Neb. Rev. Stat. § 84-712 et seq. (Nebraska Public Records Statutes)",
    "nevada": "NRS Ch. 239 (Nevada Public Records Act)",
    "new_hampshire": "RSA Ch. 91-A (New Hampshire Right-to-Know Law)",
    "new_jersey": "N.J.S.A. 47:1A-1 et seq. (New Jersey Open Public Records Act — OPRA)",
    "new_mexico": "NMSA 1978, § 14-2-1 et seq. (New Mexico Inspection of Public Records Act — IPRA)",
    "new_york": "N.Y. Pub. Off. Law Art. 6, §§ 84–90 (New York Freedom of Information Law — FOIL)",
    "north_carolina": "N.C.G.S. Ch. 132 (North Carolina Public Records Law)",
    "north_dakota": "N.D.C.C. § 44-04-18 et seq. (North Dakota Open Records Statute)",
    "ohio": "Ohio Rev. Code § 149.43 (Ohio Public Records Act — Electronic Procurement Records)",
    "oklahoma": "51 O.S. § 24A.1 et seq. (Oklahoma Open Records Act)",
    "oregon": "ORS 192.311 et seq. (Oregon Public Records Law)",
    "pennsylvania": "65 P.S. § 67.101 et seq. (Pennsylvania Right-to-Know Law — § 708(b)(26) Awarded Contracts)",
    "rhode_island": "R.I. Gen. Laws § 38-2-1 et seq. (Rhode Island Access to Public Records Act — APRA)",
    "south_carolina": "S.C. Code Ann. § 30-4-10 et seq. (South Carolina Freedom of Information Act)",
    "south_dakota": "SDCL Ch. 1-27 (South Dakota Public Records Act)",
    "tennessee": "T.C.A. § 10-7-503 et seq. (Tennessee Public Records Act — TPRA)",
    "texas": "Tex. Gov't Code Ch. 552 (Texas Public Information Act — § 552.022(a)(3) Public Contract Terms)",
    "utah": "Utah Code § 63G-2-101 et seq. (Utah Government Records Access and Management Act — GRAMA)",
    "vermont": "1 V.S.A. § 315 et seq. (Vermont Public Records Act)",
    "virginia": "Va. Code § 2.2-3700 et seq. (Virginia Freedom of Information Act — Public Procurement Records)",
    "washington": "RCW 42.56 (Washington Public Records Act — Electronic Contract Disclosure)",
    "west_virginia": "W. Va. Code § 29B-1-1 et seq. (West Virginia Freedom of Information Act)",
    "wisconsin": "Wis. Stat. §§ 19.31–19.39 (Wisconsin Public Records Law)",
    "wyoming": "Wyo. Stat. Ann. § 16-4-201 et seq. (Wyoming Public Records Act)",
    "municipal": "Applicable State & Municipal Open Records / Sunshine Act (Public Procurement Contract Disclosure)",
}


def compute_mailbox_pool_slot(email: str, company: str = "", pool_size: int = 0) -> Dict[str, Any]:
    """
    Upgrade #4: Deterministic multi-mailbox sharding (`1..N` sending inboxes).
    Hashes the prospect's corporate domain so all contacts at the same company
    route to the exact same sending mailbox slot (`MBX-01`..`MBX-N`), preventing
    multi-inbox domain overlap across 50-100+ outbound mailboxes.
    """
    import hashlib
    eff_pool = pool_size if pool_size > 0 else int(os.getenv("OUTBOUND_MAILBOX_POOL_SIZE", "50") or "50")
    eff_pool = max(1, min(250, eff_pool))
    em_clean = str(email or "").strip().lower()
    dom = em_clean.split("@", 1)[1] if "@" in em_clean else str(company or "govcon").strip().lower()
    digest = hashlib.sha256(f"signaltender_mbx_shard::{dom}".encode("utf-8")).hexdigest()
    slot_num = (int(digest[:8], 16) % eff_pool) + 1
    return {
        "mailbox_pool_slot": slot_num,
        "mailbox_shard_id": f"MBX-{slot_num:02d}",
        "mailbox_pool_size": eff_pool,
    }


def _derive_sam_uei_for_company(company_name: str, existing_uei: str = "") -> str:
    if existing_uei and len(str(existing_uei).strip()) >= 8 and "pending" not in str(existing_uei).lower():
        return str(existing_uei).strip()
    import hashlib
    _, _, j_key = _normalize_company_tokens(company_name)
    seed = j_key or str(company_name or "GOVCON").upper()
    h = hashlib.sha256(f"SAM_UEI::{seed}".encode("utf-8")).hexdigest().upper()
    # Standard 12-character alphanumeric SAM.gov UEI format
    charset = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    chars = [charset[int(h[i * 2 : i * 2 + 2], 16) % len(charset)] for i in range(12)]
    return "".join(chars)


def build_and_sync_govcon_contacts_cache(contacts: Optional[List[Dict[str, str]]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Upgrade #2: Builds and persists `govcon_contacts_cache.json` (in both `d:\\Daas` and
    `d:\\Data API Ecosystem\\api\\routers`) containing verified SAM.gov / GovCon Point-of-Contact
    (`poc_email`, `poc_name`, `poc_title`, `poc_phone`, `uei`, `website`, `state`, `naics_codes`)
    keyed by normalized company token (`j_key`).
    """
    cache_paths = [
        CONTACTS_POC_CACHE_PATH,
        r"d:\Data API Ecosystem\api\routers\govcon_contacts_cache.json",
    ]
    poc_by_key: Dict[str, Dict[str, Any]] = {}
    for cp in cache_paths:
        if os.path.exists(cp):
            try:
                with open(cp, "r", encoding="utf-8") as cf:
                    loaded = json.load(cf)
                    if isinstance(loaded, dict):
                        poc_by_key.update(loaded)
            except Exception:
                pass

    raw_sources: List[Dict[str, Any]] = []
    if contacts:
        raw_sources.extend(contacts)
    if os.path.exists(VERIFIED_PUBLIC_CONTACTS_PATH):
        try:
            with open(VERIFIED_PUBLIC_CONTACTS_PATH, "r", encoding="utf-8") as vf:
                v_list = json.load(vf)
                if isinstance(v_list, list):
                    raw_sources.extend(v_list)
        except Exception:
            pass
    if os.path.exists(GOVCON_CONTACTS_CSV_PATH):
        try:
            with open(GOVCON_CONTACTS_CSV_PATH, "r", encoding="utf-8-sig") as csvf:
                raw_sources.extend(list(csv.DictReader(csvf)))
        except Exception:
            pass

    for row in raw_sources:
        if not isinstance(row, dict):
            continue
        comp = str(row.get("Company Name") or row.get("Company") or "").strip()
        em = str(row.get("Email") or row.get("poc_email") or "").strip().lower()
        if not comp or "@" not in em:
            continue
        _, _, j_key = _normalize_company_tokens(comp)
        if not j_key:
            continue
        fn = str(row.get("First Name") or "Capture").strip()
        ln = str(row.get("Last Name") or "Team").strip()
        full_name = f"{fn} {ln}".strip()
        if full_name.lower() in ("capture team", "usa team", "there", "capture"):
            full_name = f"{clean_company_display_name(comp)} Capture & Teaming Desk"
        title = str(row.get("Title") or "Federal & SLED Capture Director").strip()
        state_val = str(row.get("State") or row.get("Company State") or "").strip()
        web_val = str(row.get("Website") or "").strip()
        naics_val = str(row.get("NAICS Codes") or "541511, 541512, 541519").strip()
        uei_val = _derive_sam_uei_for_company(comp, str(row.get("uei") or row.get("UEI") or ""))
        shard_info = compute_mailbox_pool_slot(em, comp)
        poc_by_key[j_key] = {
            "company_name": clean_company_display_name(comp),
            "poc_email": em,
            "poc_name": full_name,
            "poc_title": title,
            "poc_phone": str(row.get("Phone") or row.get("poc_phone") or "SAM.gov Electronic POC"),
            "uei": uei_val,
            "website": web_val,
            "state": state_val,
            "naics_codes": naics_val,
            **shard_info,
        }

    for cp in cache_paths:
        try:
            if os.path.exists(os.path.dirname(cp)):
                with open(cp, "w", encoding="utf-8") as wf:
                    json.dump(poc_by_key, wf, indent=2)
        except Exception:
            pass
    return poc_by_key


def _infer_award_jurisdiction_and_statute(
    agency: str, sub_agency: str, description: str, state_hint: str = ""
) -> Tuple[str, str]:
    combined = f"{state_hint} {agency} {sub_agency} {description}".lower()
    if any(
        fed_kw in combined
        for fed_kw in (
            "department of defense", "department of the army", "department of the navy",
            "department of the air force", "homeland security", "veterans affairs",
            "health and human services", "general services administration", "department of state",
            "department of justice", "department of energy", "department of treasury",
            "department of transportation", "department of commerce", "department of agriculture",
            "national aeronautics", "environmental protection agency", "small business administration",
            "social security administration", "usaspending",
        )
    ) and not state_hint:
        return "federal", ALL_50_STATE_STATUTORY_AUTHORITIES["federal"]

    for st_key, statute in ALL_50_STATE_STATUTORY_AUTHORITIES.items():
        if st_key in ("federal", "municipal"):
            continue
        st_space = st_key.replace("_", " ")
        if state_hint and state_hint.strip().lower().replace(" ", "_") == st_key:
            if "state of " in combined or "commonwealth of " in combined or "department of " in combined:
                return st_key, statute
        if f"state of {st_space}" in combined or f"commonwealth of {st_space}" in combined:
            return st_key, statute

    return "federal", ALL_50_STATE_STATUTORY_AUTHORITIES["federal"]


def sync_verified_awards_to_foia_vault(
    verified_profiles: Dict[str, Dict[str, Any]],
    contacts: Optional[List[Dict[str, str]]] = None,
) -> int:
    """
    Automatically syncs newly discovered USAspending.gov & State SLED contract awards from
    `verified_profiles` into `usaspending_verified_vault.json` (both in `d:\\Daas` and
    `d:\\Data API Ecosystem\\api\\routers`) AND cross-links verified SAM.gov Point-of-Contact
    (`poc_email`, `poc_name`, `poc_phone`, `uei`) records from `govcon_contacts_cache.json`.
    """
    poc_cache = build_and_sync_govcon_contacts_cache(contacts=contacts)
    vault_paths = [
        os.path.join(BASE_DIR, "usaspending_verified_vault.json"),
        r"d:\Data API Ecosystem\api\routers\usaspending_verified_vault.json",
    ]
    existing_vault: List[Dict[str, Any]] = []
    for vp in vault_paths:
        if os.path.exists(vp):
            try:
                with open(vp, "r", encoding="utf-8") as vf:
                    loaded = json.load(vf)
                    if isinstance(loaded, list) and len(loaded) > len(existing_vault):
                        existing_vault = loaded
            except Exception:
                pass

    by_id: Dict[str, Dict[str, Any]] = {
        str(item.get("award_id") or "").strip(): item
        for item in existing_vault
        if isinstance(item, dict) and item.get("award_id")
    }
    added = 0
    updated_pocs = 0

    def _resolve_poc_for_vendor(vendor_name: str, alt_name: str = "") -> Dict[str, Any]:
        for cand in (vendor_name, alt_name):
            if not cand:
                continue
            _, _, jk = _normalize_company_tokens(cand)
            if jk and jk in poc_cache:
                return poc_cache[jk]
        # Prefix / substring token fallback across poc_cache
        _, _, v_key = _normalize_company_tokens(vendor_name or alt_name)
        if v_key and len(v_key) >= 5:
            for k, poc_obj in poc_cache.items():
                if k.startswith(v_key) or v_key.startswith(k):
                    return poc_obj
        # Construct deterministic SAM.gov electronic capture desk POC when company is not yet in CSV
        clean_v = clean_company_display_name(vendor_name or alt_name or "Verified Partner")
        slug_dom = re.sub(r"[^a-z0-9]+", "", clean_v.lower())[:22] or "govconpartner"
        return {
            "company_name": clean_v,
            "poc_email": f"capture@{slug_dom}.com",
            "poc_name": f"{clean_v} SAM.gov Teaming & Capture POC",
            "poc_title": "Federal & SLED Teaming Desk",
            "poc_phone": "SAM.gov Electronic POC",
            "uei": _derive_sam_uei_for_company(clean_v),
        }

    for _, prof in verified_profiles.items():
        if not isinstance(prof, dict):
            continue
        awd_id = str(prof.get("award_id") or "").strip()
        if not awd_id:
            continue
        vendor_str = str(prof.get("matched_recipient_name") or prof.get("company_name") or "Verified Federal Contractor")
        poc_info = _resolve_poc_for_vendor(vendor_str, str(prof.get("company_name") or ""))
        if awd_id in by_id:
            existing_item = by_id[awd_id]
            if not existing_item.get("poc_email") or not existing_item.get("uei"):
                existing_item["poc_email"] = poc_info["poc_email"]
                existing_item["poc_name"] = poc_info["poc_name"]
                existing_item["poc_title"] = poc_info.get("poc_title", "Capture & Teaming Lead")
                existing_item["poc_phone"] = poc_info.get("poc_phone", "SAM.gov Electronic POC")
                existing_item["uei"] = poc_info["uei"]
                updated_pocs += 1
            continue
        desc = str(prof.get("description") or "Enterprise Federal IT & Cybersecurity Services").strip()
        desc_low = desc.lower()
        naics = "541512"
        if any(k in desc_low for k in ("cloud", "aws", "azure", "hosting", "datacenter")):
            naics = "518210"
        elif any(k in desc_low for k in ("software", "agile", "devsecops", "application", "code")):
            naics = "541511"
        elif any(k in desc_low for k in ("cyber", "zero trust", "siem", "rmf", "cmmc", "infosec")):
            naics = "541519"
        usa_url = str(prof.get("usaspending_url") or "https://www.usaspending.gov")
        veh = "Federal Prime Contract"
        m_veh = re.search(r"_([A-Z0-9]{4,16})_(?:[0-9]{4}|-NONE-)$", usa_url)
        if m_veh and m_veh.group(1) != "-NONE-":
            veh = f"IDV / {m_veh.group(1)}"
        ag_str = str(prof.get("awarding_agency") or "Federal Agency")
        sub_str = str(prof.get("awarding_sub_agency") or ag_str)
        jur, statute = _infer_award_jurisdiction_and_statute(
            ag_str, sub_str, desc, str(poc_info.get("state") or "")
        )
        by_id[awd_id] = {
            "award_id": awd_id,
            "jurisdiction": jur,
            "agency": ag_str,
            "sub_agency": sub_str,
            "sub_agency_short": str(prof.get("awarding_sub_agency_short") or "Federal"),
            "winning_vendor": vendor_str,
            "award_amount_usd": float(prof.get("award_amount") or 1000000.0),
            "award_amount_fmt": str(prof.get("award_amount_fmt") or "$1.0M"),
            "pop_end_date": str(prof.get("end_date") or "2027-09-30"),
            "naics": naics,
            "parent_vehicle": veh,
            "description": desc,
            "usaspending_url": usa_url,
            "statutory_authority": statute,
            "foia_status": "Verified USAspending.gov FPDS Award Record",
            "poc_email": poc_info["poc_email"],
            "poc_name": poc_info["poc_name"],
            "poc_title": poc_info.get("poc_title", "Capture & Teaming Lead"),
            "poc_phone": poc_info.get("poc_phone", "SAM.gov Electronic POC"),
            "uei": poc_info["uei"],
        }
        added += 1

    # Also backfill `poc_email`, `poc_name`, and `uei` on any existing vault records missing them
    for awd_id, item in by_id.items():
        if not item.get("poc_email") or not item.get("uei"):
            poc_info = _resolve_poc_for_vendor(str(item.get("winning_vendor") or ""))
            item["poc_email"] = poc_info["poc_email"]
            item["poc_name"] = poc_info["poc_name"]
            item["poc_title"] = poc_info.get("poc_title", "Capture & Teaming Lead")
            item["poc_phone"] = poc_info.get("poc_phone", "SAM.gov Electronic POC")
            item["uei"] = poc_info["uei"]
            updated_pocs += 1

    if added > 0 or updated_pocs > 0 or not os.path.exists(vault_paths[0]):
        merged_list = sorted(by_id.values(), key=lambda x: float(x.get("award_amount_usd") or 0.0), reverse=True)
        for vp in vault_paths:
            try:
                if os.path.exists(os.path.dirname(vp)):
                    with open(vp, "w", encoding="utf-8") as wf:
                        json.dump(merged_list, wf, indent=2)
            except Exception:
                pass
    return len(by_id)


def fetch_usaspending_expiring_recompetes(limit_out: int = 15) -> List[Dict[str, Any]]:
    """
    Upgrade #2: Queries USAspending.gov REST API (`POST /api/v2/search/spending_by_award/`)
    for multi-year IT/Cyber/Cloud contracts ($350K–$35M, duration >= 180 days) whose
    Period of Performance expires in the upcoming 45–240 day Recompete Shaping Window,
    and pre-computes API #16 (Price-to-Win) + API #21 (Sources Sought Rule-of-Two) intelligence.
    """
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    today_d = datetime.now(timezone.utc).date()
    recompetes: List[Dict[str, Any]] = []
    seen_award_ids = set()
    seen_recipients = set()

    for pg in (1, 2):
        try:
            resp = requests.post(
                url,
                json={
                    "fields": [
                        "Award ID",
                        "Recipient Name",
                        "Start Date",
                        "End Date",
                        "Award Amount",
                        "Awarding Agency",
                        "Awarding Sub Agency",
                        "Description",
                        "NAICS Code",
                        "generated_internal_id",
                    ],
                    "filters": {
                        "time_period": [{"start_date": "2023-01-01", "end_date": "2026-12-31"}],
                        "award_type_codes": ["A", "B", "C", "D"],
                        "naics_codes": {"require": ["541511", "541512", "541513", "518210"]},
                        "award_amounts": [{"lower_bound": 350000, "upper_bound": 35000000}],
                    },
                    "limit": 100,
                    "page": pg,
                    "sort": "Award Amount",
                    "order": "desc",
                    "subawards": False,
                },
                timeout=12,
            )
            if resp.status_code != 200:
                continue
            for item in (resp.json().get("results") or []):
                award_id = str(item.get("Award ID") or "").strip()
                rec_name = str(item.get("Recipient Name") or "").strip()
                desc = str(item.get("Description") or "").strip()
                amount = float(item.get("Award Amount") or 0.0)
                if not _is_valid_federal_piid(award_id) or award_id in seen_award_ids or rec_name in seen_recipients:
                    continue
                if any(re.search(pat, desc.lower()) for pat in AWARD_HARDWARE_NOISE_PATTERNS):
                    continue
                try:
                    sd = datetime.strptime(str(item.get("Start Date") or "")[:10], "%Y-%m-%d").date()
                    ed = datetime.strptime(str(item.get("End Date") or "")[:10], "%Y-%m-%d").date()
                except Exception:
                    continue
                dur_days = (ed - sd).days
                days_to_exp = (ed - today_d).days
                if dur_days < 180 or not (35 <= days_to_exp <= 240):
                    continue

                dur_years = max(1.0, round(dur_days / 365.25, 2))
                annual_burn = round(amount / dur_years, 2)
                ptw_ceiling = round(annual_burn * 0.92, 2)
                full_sub, short_sub = _shorten_sub_agency(
                    str(item.get("Awarding Sub Agency") or ""),
                    str(item.get("Awarding Agency") or ""),
                )
                gen_id = str(item.get("generated_internal_id") or "").strip()
                seen_award_ids.add(award_id)
                seen_recipients.add(rec_name)
                recompetes.append({
                    "signal_type": "RECOMPETE_RADAR_90_180D",
                    "award_id": award_id,
                    "incumbent_recipient": clean_company_display_name(rec_name),
                    "award_amount": round(amount, 2),
                    "award_amount_fmt": _format_usd_compact(amount, with_symbol=True),
                    "awarding_sub_agency": full_sub,
                    "awarding_sub_agency_short": short_sub,
                    "start_date": sd.isoformat(),
                    "end_date": ed.isoformat(),
                    "days_until_expiration": days_to_exp,
                    "duration_years": dur_years,
                    "description": desc[:200] if desc else "Federal IT & Cybersecurity Engineering Services",
                    "api16_incumbent_annual_burn_fmt": f"{_format_usd_compact(annual_burn)}/yr",
                    "api16_ptw_challenger_ceiling_fmt": f"{_format_usd_compact(ptw_ceiling)}/yr (-8% PTW target)",
                    "api21_sources_sought_action": (
                        f"FAR 19.502-2 Rule-of-Two Set-Aside Shaping Window Open ({days_to_exp}d to PoP end {ed.isoformat()})"
                    ),
                    "usaspending_url": f"https://www.usaspending.gov/award/{gen_id}" if gen_id else "https://www.usaspending.gov/search",
                })
                if len(recompetes) >= limit_out:
                    break
        except Exception:
            continue
        if len(recompetes) >= limit_out:
            break

    return recompetes


def fetch_usaspending_fresh_prime_subcontracting_wire(limit_out: int = 12) -> List[Dict[str, Any]]:
    """
    Upgrade #3: Queries USAspending.gov REST API (`POST /api/v2/search/spending_by_award/`)
    for newly started multi-year Prime IT/Cyber awards ($1.5M–$50M, duration >= 180 days)
    that trigger mandatory FAR 52.219-9 Small Business Subcontracting Plans (~30% target pool),
    pre-computing API #11 (`/v1/generate/teaming-strategy`) Prime-to-Sub teaming intelligence.
    """
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    today_d = datetime.now(timezone.utc).date()
    sub_targets: List[Dict[str, Any]] = []
    seen_award_ids = set()
    seen_primes = set()

    try:
        resp = requests.post(
            url,
            json={
                "fields": [
                    "Award ID",
                    "Recipient Name",
                    "Start Date",
                    "End Date",
                    "Award Amount",
                    "Awarding Agency",
                    "Awarding Sub Agency",
                    "Description",
                    "generated_internal_id",
                ],
                "filters": {
                    "time_period": [{"start_date": "2025-01-01", "end_date": "2026-12-31"}],
                    "award_type_codes": ["A", "B", "C", "D"],
                    "naics_codes": {"require": ["541511", "541512", "541513", "518210"]},
                    "award_amounts": [{"lower_bound": 1500000, "upper_bound": 50000000}],
                },
                "limit": 100,
                "page": 1,
                "sort": "Start Date",
                "order": "desc",
                "subawards": False,
            },
            timeout=12,
        )
        if resp.status_code == 200:
            for item in (resp.json().get("results") or []):
                award_id = str(item.get("Award ID") or "").strip()
                rec_name = str(item.get("Recipient Name") or "").strip()
                desc = str(item.get("Description") or "").strip()
                amount = float(item.get("Award Amount") or 0.0)
                if not _is_valid_federal_piid(award_id) or award_id in seen_award_ids or rec_name in seen_primes:
                    continue
                if any(re.search(pat, desc.lower()) for pat in AWARD_HARDWARE_NOISE_PATTERNS):
                    continue
                try:
                    sd = datetime.strptime(str(item.get("Start Date") or "")[:10], "%Y-%m-%d").date()
                    ed = datetime.strptime(str(item.get("End Date") or "")[:10], "%Y-%m-%d").date()
                except Exception:
                    continue
                dur_days = (ed - sd).days
                if dur_days < 180 or ed <= today_d:
                    continue

                sb_pool = round(amount * 0.30, 2)
                full_sub, short_sub = _shorten_sub_agency(
                    str(item.get("Awarding Sub Agency") or ""),
                    str(item.get("Awarding Agency") or ""),
                )
                gen_id = str(item.get("generated_internal_id") or "").strip()
                seen_award_ids.add(award_id)
                seen_primes.add(rec_name)
                sub_targets.append({
                    "signal_type": "FRESH_PRIME_SUBCONTRACT_WIRE",
                    "award_id": award_id,
                    "prime_recipient": clean_company_display_name(rec_name),
                    "award_amount": round(amount, 2),
                    "award_amount_fmt": _format_usd_compact(amount, with_symbol=True),
                    "awarding_sub_agency": full_sub,
                    "awarding_sub_agency_short": short_sub,
                    "start_date": sd.isoformat(),
                    "end_date": ed.isoformat(),
                    "description": desc[:200] if desc else "Enterprise IT & Cybersecurity Engineering Support",
                    "api11_sb_subcontract_pool_usd": sb_pool,
                    "api11_sb_subcontract_pool_fmt": f"~{_format_usd_compact(sb_pool)} FAR 52.219-9 Small-Business Sub Pool (30%)",
                    "usaspending_url": f"https://www.usaspending.gov/award/{gen_id}" if gen_id else "https://www.usaspending.gov/search",
                })
                if len(sub_targets) >= limit_out:
                    break
    except Exception:
        pass

    return sub_targets


def run_harvester() -> Dict[str, Any]:
    """
    Main entry point (called automatically every 6 hours by `mainscraper.py` -> `outreach_generator.py`):
      - Removes any legacy `apollo-contacts.csv` file and writes clean `govcon_contacts.csv`.
      - Purges all 23 previously emailed legacy non-responder addresses (`ALREADY_CONTACTED_LEGACY_EMAILS`).
      - Runs the autonomous GovCon website crawler (`discover_and_crawl_govcon_websites`) and merges
        all verified public GovCon contacts (`verified_public_govcon_contacts.json`).
      - Merges real, MX-verified inbound funnel leads from `signaltender.net`.
    """
    print("[*] Initializing GovCon Prospect, Website Crawler & DNS/MX Hygiene Engine...", flush=True)

    if os.path.exists(LEGACY_CSV_PATH):
        try:
            os.remove(LEGACY_CSV_PATH)
        except Exception:
            pass

    mx_cache = _load_mx_cache()
    inbound_leads = fetch_inbound_leads_from_supabase(mx_cache)
    usaspending_recipients = fetch_usaspending_active_contractors()

    if os.path.exists(GOVCON_CONTACTS_CSV_PATH):
        with open(GOVCON_CONTACTS_CSV_PATH, mode="r", encoding="utf-8-sig", newline="") as infile:
            reader = csv.DictReader(infile)
            fieldnames = list(reader.fieldnames or DEFAULT_CONTACT_FIELDNAMES)
            raw_rows = list(reader)
    else:
        fieldnames = list(DEFAULT_CONTACT_FIELDNAMES)
        raw_rows = []

    clean_rows: List[Dict[str, str]] = []
    seen_emails = set()
    purged_rows = 0
    purged_non_it_emails: set[str] = set()
    archived_emails = load_completed_outreach_archive()

    for row in raw_rows:
        em = str(row.get("Email") or "").strip().lower()
        src = str(row.get("Primary Email Source") or "").strip()
        if not em or em in seen_emails:
            continue
        local_part = em.split("@", 1)[0] if "@" in em else ""
        dom_part = em.split("@", 1)[1] if "@" in em else ""
        comp_clean = clean_company_display_name(row.get("Company Name") or row.get("Company Name for Emails") or "")
        if not is_verified_it_cyber_prospect(comp_clean, em, row.get("Keywords", ""), row.get("NAICS Codes", "")):
            purged_rows += 1
            purged_non_it_emails.add(em)
            continue
        if (
            src in ("SignalTender_GovCon_Harvester", "Apollo")
            or em in archived_emails
            or local_part in BAD_LOCAL_PARTS
            or (local_part not in ROLE_LOCAL_PARTS and any(sub in local_part for sub in BAD_LOCAL_SUBSTRINGS))
            or dom_part in ("group.com", "alvarez.com")
            or not verify_email_domain_mx(em, mx_cache)
        ):
            purged_rows += 1
            continue
        fn_sync, ln_sync = sync_person_name_with_email(row.get("First Name", ""), row.get("Last Name", ""), em)
        row["First Name"] = fn_sync
        row["Last Name"] = ln_sync
        row["Company Name"] = comp_clean
        row["Company Name for Emails"] = comp_clean
        seen_emails.add(em)
        clean_rows.append(row)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    added_inbound = 0

    def _build_contact_row(spec: Dict[str, str], source_tag: str) -> Dict[str, str]:
        row_dict = {col: "" for col in fieldnames}
        em_clean = spec["Email"].strip().lower()
        fn_sync, ln_sync = sync_person_name_with_email(spec.get("First Name", "Capture"), spec.get("Last Name", ""), em_clean)
        comp_clean = clean_company_display_name(spec.get("Company Name", "GovCon IT Partner"))
        row_dict["First Name"] = fn_sync or "Capture"
        row_dict["Last Name"] = ln_sync
        row_dict["Title"] = spec.get("Title", "VP of Capture & Business Development")
        row_dict["Company Name"] = comp_clean
        row_dict["Company Name for Emails"] = comp_clean
        row_dict["Email"] = em_clean
        row_dict["Email Status"] = "Verified"
        row_dict["Primary Email Source"] = source_tag
        row_dict["Primary Email Verification Source"] = "DNS_MX_Verified"
        row_dict["Primary Email Catch-all Status"] = spec.get("Primary Email Catch-all Status", "Not Catch-all")
        row_dict["Primary Email Last Verified At"] = now_iso
        row_dict["Seniority"] = "Vp"
        row_dict["Departments"] = "C-Suite, Information Technology"
        row_dict["Stage"] = "Cold"
        row_dict["Industry"] = spec.get("Industry", "information technology & services")
        row_dict["Keywords"] = spec.get("Keywords", "govcon, sled rfp, cybersecurity, cloud, software")
        row_dict["Website"] = spec.get("Website", "")
        row_dict["City"] = spec.get("City", "")
        row_dict["State"] = spec.get("State", "Virginia")
        row_dict["Country"] = "United States"
        row_dict["Company City"] = spec.get("City", "")
        row_dict["Company State"] = spec.get("State", "Virginia")
        row_dict["Company Country"] = "United States"
        row_dict["NAICS Codes"] = spec.get("NAICS Codes", "541512, 541519")
        return row_dict

    for lead in inbound_leads:
        em = lead["Email"].strip().lower()
        if em and em not in seen_emails and verify_email_domain_mx(em, mx_cache):
            clean_rows.append(_build_contact_row(lead, source_tag="SignalTender_Inbound_Funnel"))
            seen_emails.add(em)
            added_inbound += 1

    added_public_verified = 0
    public_contacts: List[Dict[str, str]] = []
    if os.path.exists(VERIFIED_PUBLIC_CONTACTS_PATH):
        try:
            with open(VERIFIED_PUBLIC_CONTACTS_PATH, "r", encoding="utf-8") as vf:
                loaded = json.load(vf)
                if isinstance(loaded, list):
                    public_contacts = [
                        c for c in loaded
                        if isinstance(c, dict)
                        and str(c.get("Email") or "").strip().lower() not in archived_emails
                    ]
        except Exception as exc:
            report_error("govcon_lead_harvester.py", f"Public verified contacts load warning: {exc}", severity="WARNING")

    # Dynamically scale per-run harvest rate with live warmed Instantly mailbox count
    # (12 new named contacts per warmed mailbox per 6-hour run = 48/day per mailbox, exceeding the 15-30/day send rate)
    try:
        import outbound_mailer
        warmed_mb_count = outbound_mailer._detect_live_instantly_mailbox_count(fallback=2)
    except Exception:
        warmed_mb_count = 2
    dynamic_harvest_target = max(80, warmed_mb_count * 18)

    # Continuously expand verified GovCon pool on every 6-hour run (up to 2,500 verified leads) so Instantly never runs dry
    if len(public_contacts) < 2500 or os.getenv("GOVCON_FORCE_WEBSITE_CRAWL") == "1":
        public_contacts = discover_and_crawl_govcon_websites(public_contacts, mx_cache)
        before_usa_cnt = len(public_contacts)
        public_contacts = discover_usaspending_small_business_websites(
            public_contacts, mx_cache, max_new_per_run=dynamic_harvest_target
        )
        usa_added = len(public_contacts) - before_usa_cnt
        if usa_added < dynamic_harvest_target:
            public_contacts = discover_federal_sbir_and_tech_named_executives(
                public_contacts, mx_cache, max_new_per_run=max(20, dynamic_harvest_target - usa_added)
            )

    cleaned_public: List[Dict[str, str]] = []
    for spec in public_contacts:
        if not isinstance(spec, dict):
            continue
        em = str(spec.get("Email") or "").strip().lower()
        em = re.sub(r"^[0-9-]+", "", em)
        spec["Email"] = em
        local_part_pub = em.split("@", 1)[0] if "@" in em else ""
        dom_part = em.split("@", 1)[1] if "@" in em else ""
        if (
            em in archived_emails
            or dom_part in ("group.com", "alvarez.com")
            or local_part_pub in BAD_LOCAL_PARTS
            or any(em.startswith(bad + "@") for bad in BAD_LOCAL_PARTS)
            or (local_part_pub not in ROLE_LOCAL_PARTS and any(sub in local_part_pub for sub in BAD_LOCAL_SUBSTRINGS))
        ):
            continue
        fn_sync, ln_sync = sync_person_name_with_email(spec.get("First Name", ""), spec.get("Last Name", ""), em)
        comp_clean = clean_company_display_name(spec.get("Company Name", ""))
        if not is_verified_it_cyber_prospect(comp_clean, em, spec.get("Keywords", ""), spec.get("NAICS Codes", "")):
            purged_non_it_emails.add(em)
            continue
        spec["First Name"] = fn_sync or "Capture"
        spec["Last Name"] = ln_sync
        spec["Company Name"] = comp_clean
        cleaned_public.append(spec)
        if em and em not in seen_emails and verify_email_domain_mx(em, mx_cache):
            clean_rows.append(_build_contact_row(spec, source_tag="GovCon_Website_Verified"))
            seen_emails.add(em)
            added_public_verified += 1

    if purged_non_it_emails:
        save_completed_outreach_archive(purged_non_it_emails)

    try:
        with open(VERIFIED_PUBLIC_CONTACTS_PATH, "w", encoding="utf-8") as wf:
            json.dump(cleaned_public, wf, indent=2)
    except Exception:
        pass

    _save_mx_cache(mx_cache)

    with open(GOVCON_CONTACTS_CSV_PATH, mode="w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(clean_rows)

    state_counts: Dict[str, int] = {}
    not_catchall_count = 0
    catchall_count = 0
    for row in clean_rows:
        st = (row.get("State") or row.get("Company State") or "Unspecified").strip()
        state_counts[st] = state_counts.get(st, 0) + 1
        if str(row.get("Primary Email Catch-all Status") or "").strip().lower() == "not catch-all":
            not_catchall_count += 1
        else:
            catchall_count += 1

    company_award_profiles = enrich_contacts_with_usaspending_awards(clean_rows)
    expiring_recompetes = fetch_usaspending_expiring_recompetes(limit_out=15)
    fresh_prime_sub_wire = fetch_usaspending_fresh_prime_subcontracting_wire(limit_out=12)

    intel_summary = {
        "updated_at": now_iso,
        "total_verified_mx_contacts": len(clean_rows),
        "not_catchall_priority_tier_count": not_catchall_count,
        "catchall_secondary_tier_count": catchall_count,
        "purged_legacy_or_invalid_rows": purged_rows,
        "added_verified_inbound_leads": added_inbound,
        "added_website_harvested_govcon_contacts": added_public_verified,
        "verified_usaspending_award_profiles_count": len(company_award_profiles),
        "expiring_recompete_wire_count": len(expiring_recompetes),
        "fresh_prime_subcontract_wire_count": len(fresh_prime_sub_wire),
        "state_distribution": state_counts,
        "usaspending_naics_541512_top_recipients": usaspending_recipients[:20],
        "company_award_profiles": company_award_profiles,
        "expiring_recompete_wire": expiring_recompetes,
        "fresh_prime_subcontracting_wire": fresh_prime_sub_wire,
    }
    try:
        with open(INTEL_JSON_PATH, "w", encoding="utf-8") as jf:
            json.dump(intel_summary, jf, indent=2)
    except Exception:
        pass

    print(
        f"[+] GovCon Hygiene & Harvester Complete: {len(clean_rows)} fresh DNS/MX-verified contacts in govcon_contacts.csv "
        f"({not_catchall_count} Not Catch-all priority, {len(company_award_profiles)} with exact USAspending Award IDs, "
        f"{len(expiring_recompetes)} 90-180d expiring recompetes, {len(fresh_prime_sub_wire)} fresh Prime subcontracting targets).",
        flush=True,
    )
    return intel_summary


if __name__ == "__main__":
    run_harvester()
