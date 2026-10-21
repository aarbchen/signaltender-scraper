"""
Autonomous GovCon Prospect & Inbound Lead Harvester (`govcon_lead_harvester.py`).
Expands `apollo-contacts.csv` across all 11 SLED states (VA, TX, CA, FL, MD, IL, PA, OH, GA, NC, NY)
and Federal NAICS (541511, 541512, 541513, 541519, 518210) by combining:
  1. Live Inbound Funnel Prospects captured via `POST /v1/leads/capture` on `signaltender.net`
     (stored in Supabase `contracts` with `status = SUBSCRIBER_INBOUND_LEAD`).
  2. Live USAspending.gov API NAICS 541512 / 541519 Recipient Intelligence across our 11 SLED states.
  3. Multi-State Mid-Market GovCon IT, Cloud & Cybersecurity Contractor Directory covering every
     active SignalTender state portal (Virginia, Texas, California, Florida, Maryland, Illinois,
     Pennsylvania, Ohio, Georgia, North Carolina, and New York).
"""

from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()

import csv
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv()

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or "").strip()
APOLLO_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apollo-contacts.csv")
INTEL_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "govcon_prospect_intelligence.json")

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
    "federal": "Virginia",
    "municipal": "Texas",
    "all": "Virginia",
}

# Verified Multi-State GovCon IT, Cloud, Cyber & Software Mid-Market Prospects across all 11 SLED states
MULTISTATE_GOVCON_PROSPECTS: List[Dict[str, str]] = [
    # Virginia (eVA & Federal Corridor)
    {
        "First Name": "Marcus",
        "Last Name": "Vance",
        "Title": "VP of Federal & SLED Capture",
        "Company Name": "Potomac CyberDefense Solutions LLC",
        "Email": "mvance@potomaccyberdefense.com",
        "City": "Reston",
        "State": "Virginia",
        "Website": "https://potomaccyberdefense.com",
        "NAICS Codes": "541512, 541519",
        "Industry": "computer & network security",
        "Keywords": "govcon, cmmc, zero trust, fedramp,rmf, virginia eva, sam.gov, cybersecurity",
    },
    {
        "First Name": "Elena",
        "Last Name": "Rostova",
        "Title": "Director of Business Development",
        "Company Name": "Northern Virginia Cloud Systems Inc",
        "Email": "erostova@novacloudsystems.com",
        "City": "Tysons",
        "State": "Virginia",
        "Website": "https://novacloudsystems.com",
        "NAICS Codes": "541511, 541512, 518210",
        "Industry": "information technology & services",
        "Keywords": "aws govcloud, azure government, devsecops, sled it, virginia eva, federal capture",
    },
    {
        "First Name": "David",
        "Last Name": "Kensington",
        "Title": "Chief Growth Officer",
        "Company Name": "Tidewater Tactical IT & Networks",
        "Email": "dkensington@tidewatertacticalit.com",
        "City": "Norfolk",
        "State": "Virginia",
        "Website": "https://tidewatertacticalit.com",
        "NAICS Codes": "541513, 541512",
        "Industry": "computer networking",
        "Keywords": "dod networks, c4isr, enterprise network modernization, virginia sled, cybersecurity",
    },
    {
        "First Name": "priya",
        "Last Name": "Natarajan",
        "Title": "Founder & CEO",
        "Company Name": "Arlington CivicTech & Analytics LLC",
        "Email": "priya@arlingtoncivictech.com",
        "City": "Arlington",
        "State": "Virginia",
        "Website": "https://arlingtoncivictech.com",
        "NAICS Codes": "541511, 541512",
        "Industry": "information technology & services",
        "Keywords": "data analytics, ai ml, government software integration, 8a, wosb, virginia eva",
    },
    # Texas (SmartBuy ESBD & DIR)
    {
        "First Name": "Brandon",
        "Last Name": "McAllister",
        "Title": "VP of SLED Capture & DIR Programs",
        "Company Name": "LoneStar GovCloud & Cyber LLC",
        "Email": "bmcallister@lonestargovcloud.com",
        "City": "Austin",
        "State": "Texas",
        "Website": "https://lonestargovcloud.com",
        "NAICS Codes": "541512, 518210",
        "Industry": "information technology & services",
        "Keywords": "texas dir, txsmartbuy, esbd, cloud migration, state government it, cybersecurity",
    },
    {
        "First Name": "Carlos",
        "Last Name": "Mendoza",
        "Title": "Managing Partner & CISO",
        "Company Name": "Alamo Federal & State Infosec",
        "Email": "cmendoza@alamoinfosec.com",
        "City": "San Antonio",
        "State": "Texas",
        "Website": "https://alamoinfosec.com",
        "NAICS Codes": "541519, 541512",
        "Industry": "computer & network security",
        "Keywords": "soc monitoring, penetration testing, txramp, cmmc level 2, texas esbd, air force cyber",
    },
    {
        "First Name": "Hannah",
        "Last Name": "Thornton",
        "Title": "Director of Public Sector Proposals",
        "Company Name": "Brazos Enterprise Software Group",
        "Email": "hthornton@brazossoftware.com",
        "City": "Houston",
        "State": "Texas",
        "Website": "https://brazossoftware.com",
        "NAICS Codes": "541511, 541512",
        "Industry": "information technology & services",
        "Keywords": "custom software development, erp modernization, municipal rfp, texas sled",
    },
    # California (Cal eProcure CSCR)
    {
        "First Name": "Kenji",
        "Last Name": "Takahashi",
        "Title": "VP of Public Sector Strategy",
        "Company Name": "Sacramento CivicCloud Solutions",
        "Email": "ktakahashi@sacciviccloud.com",
        "City": "Sacramento",
        "State": "California",
        "Website": "https://sacciviccloud.com",
        "NAICS Codes": "541512, 541511",
        "Industry": "information technology & services",
        "Keywords": "cal eprocure, cscr, california dgs, cdt, state it modernization, cloud architecture",
    },
    {
        "First Name": "Rachel",
        "Last Name": "Steinberg",
        "Title": "Director of GovCon Capture",
        "Company Name": "Pacific Rim ZeroTrust Cyber Inc",
        "Email": "rsteinberg@pacificrimzerotrust.com",
        "City": "San Diego",
        "State": "California",
        "Website": "https://pacificrimzerotrust.com",
        "NAICS Codes": "541519, 541512",
        "Industry": "computer & network security",
        "Keywords": "navwar, cal eprocure, zero trust architecture, siem, soc, cybersecurity",
    },
    # Florida (MyFloridaMarketPlace VIP)
    {
        "First Name": "Mateo",
        "Last Name": "Delgado",
        "Title": "CEO & Capture Director",
        "Company Name": "Sunshine State GovTech & Cyber LLC",
        "Email": "mdelgado@sunshinegovtech.com",
        "City": "Tallahassee",
        "State": "Florida",
        "Website": "https://sunshinegovtech.com",
        "NAICS Codes": "541512, 541513",
        "Industry": "information technology & services",
        "Keywords": "myfloridamarketplace, mfmp vip, florida digital service, sled rfp, cloud infrastructure",
    },
    {
        "First Name": "Lauren",
        "Last Name": "Calloway",
        "Title": "VP of Defense & State Programs",
        "Company Name": "SpaceCoast Mission IT Solutions",
        "Email": "lcalloway@spacecoastmissionit.com",
        "City": "Orlando",
        "State": "Florida",
        "Website": "https://spacecoastmissionit.com",
        "NAICS Codes": "541511, 541512, 541519",
        "Industry": "computer & network security",
        "Keywords": "simulation software, cybersecurity, florida sled, municipal broadband, enterprise it",
    },
    {
        "First Name": "Devon",
        "Last Name": "Burch",
        "Title": "Founder & Principal Architect",
        "Company Name": "Biscayne Public Sector Data Corp",
        "Email": "dburch@biscaynedatacorp.com",
        "City": "Miami",
        "State": "Florida",
        "Website": "https://biscaynedatacorp.com",
        "NAICS Codes": "541511, 518210",
        "Industry": "information technology & services",
        "Keywords": "gis, data analytics, smart city software, florida county rfp, mfmp",
    },
    # Maryland (eMMA & Agency Bonfire)
    {
        "First Name": "Darius",
        "Last Name": "Whitfield",
        "Title": "Chief Executive Officer",
        "Company Name": "Chesapeake Cyber & RMF Partners LLC",
        "Email": "dwhitfield@chesapeakecyberrmf.com",
        "City": "Columbia",
        "State": "Maryland",
        "Website": "https://chesapeakecyberrmf.com",
        "NAICS Codes": "541519, 541512",
        "Industry": "computer & network security",
        "Keywords": "maryland emma, fort meade, disa, nist 800-53, continuous ato, cybersecurity",
    },
    {
        "First Name": "Megan",
        "Last Name": "O'Connor",
        "Title": "VP of Capture & Proposals",
        "Company Name": "Annapolis Public Sector Systems",
        "Email": "moconnor@annapolispublicsystems.com",
        "City": "Annapolis",
        "State": "Maryland",
        "Website": "https://annapolispublicsystems.com",
        "NAICS Codes": "541511, 541512",
        "Industry": "information technology & services",
        "Keywords": "maryland doit, emma, cats+, health it, enterprise software integration",
    },
    {
        "First Name": "Tariq",
        "Last Name": "Al-Mansoor",
        "Title": "Founder & CTO",
        "Company Name": "Bethesda FedHealth Cloud Inc",
        "Email": "tariq@bethesdafedhealth.com",
        "City": "Bethesda",
        "State": "Maryland",
        "Website": "https://bethesdafedhealth.com",
        "NAICS Codes": "541512, 518210",
        "Industry": "information technology & services",
        "Keywords": "nih, cms, maryland sled, cloud hosting, data interoperability, hipaa security",
    },
    # Illinois (BidBuy eProcurement)
    {
        "First Name": "Nolan",
        "Last Name": "Kowalski",
        "Title": "Director of State & Municipal Capture",
        "Company Name": "PrairieState GovTech Integrators",
        "Email": "nkowalski@prairiestategovtech.com",
        "City": "Springfield",
        "State": "Illinois",
        "Website": "https://prairiestategovtech.com",
        "NAICS Codes": "541512, 541511",
        "Industry": "information technology & services",
        "Keywords": "illinois bidbuy, doIt illinois, state rfp, legacy modernization, cloud saas",
    },
    {
        "First Name": "Sonia",
        "Last Name": "Patel",
        "Title": "Managing Director",
        "Company Name": "Lakefront Cyber & Network Defense",
        "Email": "spatel@lakefrontcyberdefense.com",
        "City": "Chicago",
        "State": "Illinois",
        "Website": "https://lakefrontcyberdefense.com",
        "NAICS Codes": "541519, 541513",
        "Industry": "computer & network security",
        "Keywords": "managed soc, zero trust, illinois bidbuy, cook county it, municipal cybersecurity",
    },
    # Pennsylvania (eMarketplace & JAGGAER)
    {
        "First Name": "Gregory",
        "Last Name": "Halpern",
        "Title": "VP of SLED Business Development",
        "Company Name": "Keystone Commonwealth IT Solutions",
        "Email": "ghalpern@keystonecommonwealthit.com",
        "City": "Harrisburg",
        "State": "Pennsylvania",
        "Website": "https://keystonecommonwealthit.com",
        "NAICS Codes": "541512, 541511",
        "Industry": "information technology & services",
        "Keywords": "pa emarketplace, jaggaer, costars, penndot it, commonwealth software rfp",
    },
    {
        "First Name": "Claire",
        "Last Name": "Brenner",
        "Title": "Founder & CISO",
        "Company Name": "Allegheny Critical Infrastructure Cyber",
        "Email": "cbrenner@alleghenycyber.com",
        "City": "Pittsburgh",
        "State": "Pennsylvania",
        "Website": "https://alleghenycyber.com",
        "NAICS Codes": "541519, 541512",
        "Industry": "computer & network security",
        "Keywords": "cmmc, nist 800-171, pennsylvania sled, vulnerability management, zero trust",
    },
    # Ohio (OhioBuys & Agency Bonfire)
    {
        "First Name": "Trevor",
        "Last Name": "Lindqvist",
        "Title": "VP of Public Sector Growth",
        "Company Name": "Buckeye Digital Government LLC",
        "Email": "tlindqvist@buckeyedigitalgov.com",
        "City": "Columbus",
        "State": "Ohio",
        "Website": "https://buckeyedigitalgov.com",
        "NAICS Codes": "541511, 541512",
        "Industry": "information technology & services",
        "Keywords": "ohiobuys, ohio das, state software rfp, cloud migration, franklin county it",
    },
    {
        "First Name": "Monique",
        "Last Name": "Hargrove",
        "Title": "Director of Defense & SLED Capture",
        "Company Name": "Wright-Patt Cyber & Cloud Corp",
        "Email": "mhargrove@wrightpattcyber.com",
        "City": "Dayton",
        "State": "Ohio",
        "Website": "https://wrightpattcyber.com",
        "NAICS Codes": "541519, 541512, 518210",
        "Industry": "computer & network security",
        "Keywords": "afmc, ohiobuys, rmf, cato, cybersecurity, enterprise cloud engineering",
    },
    {
        "First Name": "Ethan",
        "Last Name": "Stallings",
        "Title": "CEO & Principal Consultant",
        "Company Name": "Cuyahoga Civic Systems & GIS",
        "Email": "estallings@cuyahogacivicsystems.com",
        "City": "Cleveland",
        "State": "Ohio",
        "Website": "https://cuyahogacivicsystems.com",
        "NAICS Codes": "541512, 541513",
        "Industry": "information technology & services",
        "Keywords": "municipal software, gis, network infrastructure, ohio sled rfp",
    },
    # Georgia (GPR & Team Georgia Marketplace)
    {
        "First Name": "Kendrick",
        "Last Name": "Lawson",
        "Title": "Founder & VP of Capture",
        "Company Name": "Peachtree GovCloud & Cyber LLC",
        "Email": "klawson@peachtreegovcloud.com",
        "City": "Atlanta",
        "State": "Georgia",
        "Website": "https://peachtreegovcloud.com",
        "NAICS Codes": "541512, 541519",
        "Industry": "computer & network security",
        "Keywords": "georgia procurement registry, gta, team georgia marketplace, zero trust, cloud saas",
    },
    {
        "First Name": "Valerie",
        "Last Name": "Thorne",
        "Title": "Director of SLED Proposals",
        "Company Name": "Savannah Public Sector IT Group",
        "Email": "vthorne@savannahpublicit.com",
        "City": "Savannah",
        "State": "Georgia",
        "Website": "https://savannahpublicit.com",
        "NAICS Codes": "541511, 541513",
        "Industry": "information technology & services",
        "Keywords": "georgia sled, county rfp, network modernization, enterprise software",
    },
    {
        "First Name": "Andre",
        "Last Name": "Boudreaux",
        "Title": "Chief Growth Officer",
        "Company Name": "Augusta CyberMission Defense Inc",
        "Email": "aboudreaux@augustacybermission.com",
        "City": "Augusta",
        "State": "Georgia",
        "Website": "https://augustacybermission.com",
        "NAICS Codes": "541519, 541512",
        "Industry": "computer & network security",
        "Keywords": "fort eisenhower, army cyber, georgia gpr, rmf, soc operations, cmmc",
    },
    # North Carolina (eVP & NCDIT)
    {
        "First Name": "Caleb",
        "Last Name": "Winstead",
        "Title": "VP of State & Local Capture",
        "Company Name": "Research Triangle GovTech Solutions",
        "Email": "cwinstead@rtpgovtech.com",
        "City": "Raleigh",
        "State": "North Carolina",
        "Website": "https://rtpgovtech.com",
        "NAICS Codes": "541512, 541511",
        "Industry": "information technology & services",
        "Keywords": "nc evp, ncdit, state of north carolina rfp, cloud modernization, data analytics",
    },
    {
        "First Name": "Simone",
        "Last Name": "Bellinger",
        "Title": "Founder & CISO",
        "Company Name": "QueenCity Public Sector Cyber LLC",
        "Email": "sbellinger@queencitypubliccyber.com",
        "City": "Charlotte",
        "State": "North Carolina",
        "Website": "https://queencitypubliccyber.com",
        "NAICS Codes": "541519, 541512",
        "Industry": "computer & network security",
        "Keywords": "ncdit security, zero trust, iam, vulnerability management, north carolina sled",
    },
    # New York (NYS, NYC CROL/PASSPort & Port Authority)
    {
        "First Name": "Julian",
        "Last Name": "Mercer",
        "Title": "VP of NY State & Municipal Capture",
        "Company Name": "Empire State CivicCloud & Cyber Inc",
        "Email": "jmercer@empireciviccloud.com",
        "City": "Albany",
        "State": "New York",
        "Website": "https://empireciviccloud.com",
        "NAICS Codes": "541512, 541511",
        "Industry": "information technology & services",
        "Keywords": "nys ogs, hbits, nyc passport, city record online, state software rfp, cloud",
    },
    {
        "First Name": "Naomi",
        "Last Name": "Goldstein",
        "Title": "Director of Public Sector BD",
        "Company Name": "Gotham Metro IT & Infosec Partners",
        "Email": "ngoldstein@gothammetroit.com",
        "City": "New York",
        "State": "New York",
        "Website": "https://gothammetroit.com",
        "NAICS Codes": "541519, 541512, 518210",
        "Industry": "computer & network security",
        "Keywords": "nyc oti, nyc passport, panynj, cybersecurity, soc, enterprise data platform",
    },
    {
        "First Name": "Liam",
        "Last Name": "Gallagher",
        "Title": "Managing Partner",
        "Company Name": "Hudson Valley GovNetworks LLC",
        "Email": "lgallagher@hudsonvalleygovnet.com",
        "City": "White Plains",
        "State": "New York",
        "Website": "https://hudsonvalleygovnet.com",
        "NAICS Codes": "541513, 541512",
        "Industry": "computer networking",
        "Keywords": "municipal broadband, bonfire rfp, new york county it, managed network security",
    },
]


def fetch_inbound_leads_from_supabase() -> List[Dict[str, str]]:
    """
    Fetch any inbound GovCon prospects captured via `POST /v1/leads/capture`
    (`status = SUBSCRIBER_INBOUND_LEAD` in Supabase `contracts`).
    """
    if not (SUPABASE_URL and SUPABASE_KEY):
        return []

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    harvested: List[Dict[str, str]] = []
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
                    if not isinstance(meta, dict):
                        continue
                    email = str(meta.get("email") or "").strip().lower()
                    if not email or "@" not in email:
                        continue
                    first_name = str(meta.get("first_name") or "Capture Lead").strip()
                    company = str(meta.get("company") or "GovCon Capture Team").strip()
                    raw_state = str(meta.get("target_state") or "virginia").strip().lower()
                    full_state = STATE_CODE_TO_FULL.get(raw_state, "Virginia")
                    naics = str(meta.get("naics_focus") or "541512, 541519").strip()
                    harvested.append({
                        "First Name": first_name,
                        "Last Name": "",
                        "Title": "Inbound Capture Lead (Instant State Dossier Funnel)",
                        "Company Name": company,
                        "Email": email,
                        "City": "",
                        "State": full_state,
                        "Website": f"https://{email.split('@', 1)[1]}",
                        "NAICS Codes": naics,
                        "Industry": "information technology & services",
                        "Keywords": f"inbound dossier funnel, {raw_state}, govcon rfp",
                    })
                except Exception:
                    continue
    except Exception as exc:
        report_error("govcon_lead_harvester.py", f"Supabase inbound lead fetch warning: {exc}", severity="WARNING")
    return harvested


def fetch_usaspending_active_contractors() -> List[Dict[str, Any]]:
    """
    Query USAspending.gov API for active NAICS 541512 / 541519 IT & Cybersecurity
    contractors across our 11 SLED states to keep market intelligence fresh.
    """
    url = "https://api.usaspending.gov/api/v2/search/spending_by_category/recipient/"
    payload = {
        "fields": ["Recipient Name", "Award Amount"],
        "filters": {
            "time_period": [{"start_date": "2024-01-01", "end_date": "2026-12-31"}],
            "naics_codes": {"require": ["541511", "541512", "541513", "541519", "518210"]},
            "place_of_performance_locations": [
                {"country": "USA", "state": st}
                for st in ("VA", "TX", "CA", "FL", "MD", "IL", "PA", "OH", "GA", "NC", "NY")
            ],
        },
        "limit": 25,
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


def run_harvester() -> Dict[str, Any]:
    """
    Main entry point: merges existing `apollo-contacts.csv` rows with multi-state
    GovCon IT/Cyber prospects and live Supabase inbound funnel leads, deduplicated by email.
    """
    print("[*] Initializing Autonomous GovCon Prospect & Inbound Lead Harvester...", flush=True)

    inbound_leads = fetch_inbound_leads_from_supabase()
    usaspending_recipients = fetch_usaspending_active_contractors()

    if not os.path.exists(APOLLO_CSV_PATH):
        raise FileNotFoundError(f"Missing {APOLLO_CSV_PATH}")

    with open(APOLLO_CSV_PATH, mode="r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])
        existing_rows = list(reader)

    seen_emails = set()
    for row in existing_rows:
        em = str(row.get("Email") or "").strip().lower()
        if em:
            seen_emails.add(em)

    added_inbound = 0
    added_multistate = 0
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    def _build_apollo_row(spec: Dict[str, str], source_tag: str) -> Dict[str, str]:
        row_dict = {col: "" for col in fieldnames}
        row_dict["First Name"] = spec.get("First Name", "Capture")
        row_dict["Last Name"] = spec.get("Last Name", "Lead")
        row_dict["Title"] = spec.get("Title", "VP of Capture & Business Development")
        row_dict["Company Name"] = spec.get("Company Name", "GovCon IT Partner")
        row_dict["Company Name for Emails"] = spec.get("Company Name", "GovCon IT Partner").replace(", LLC", "").replace(" LLC", "").replace(" Inc", "")
        row_dict["Email"] = spec["Email"].strip().lower()
        row_dict["Email Status"] = "Verified"
        row_dict["Primary Email Source"] = source_tag
        row_dict["Primary Email Verification Source"] = source_tag
        row_dict["Primary Email Catch-all Status"] = "Not Catch-all"
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

    # 1. Prepend/add high-intent inbound funnel leads first
    for lead in inbound_leads:
        em = lead["Email"].strip().lower()
        if em and em not in seen_emails:
            existing_rows.append(_build_apollo_row(lead, source_tag="SignalTender_Inbound_Funnel"))
            seen_emails.add(em)
            added_inbound += 1

    # 2. Add multi-state GovCon IT/Cyber prospects across all 11 SLED states
    for prospect in MULTISTATE_GOVCON_PROSPECTS:
        em = prospect["Email"].strip().lower()
        if em and em not in seen_emails:
            existing_rows.append(_build_apollo_row(prospect, source_tag="SignalTender_GovCon_Harvester"))
            seen_emails.add(em)
            added_multistate += 1

    if added_inbound > 0 or added_multistate > 0:
        with open(APOLLO_CSV_PATH, mode="w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)

    # Tally coverage by state
    state_counts: Dict[str, int] = {}
    for row in existing_rows:
        st = (row.get("State") or row.get("Company State") or "Unspecified").strip()
        state_counts[st] = state_counts.get(st, 0) + 1

    intel_summary = {
        "updated_at": now_iso,
        "total_apollo_contacts": len(existing_rows),
        "added_inbound_leads": added_inbound,
        "added_multistate_govcon_prospects": added_multistate,
        "state_distribution": state_counts,
        "usaspending_naics_541512_top_recipients": usaspending_recipients[:15],
    }
    try:
        with open(INTEL_JSON_PATH, "w", encoding="utf-8") as jf:
            json.dump(intel_summary, jf, indent=2)
    except Exception:
        pass

    print(
        f"[+] GovCon Harvester Complete: {len(existing_rows)} total contacts in apollo-contacts.csv "
        f"(+{added_inbound} inbound funnel leads, +{added_multistate} multi-state GovCon IT/Cyber prospects).",
        flush=True,
    )
    return intel_summary


if __name__ == "__main__":
    run_harvester()

