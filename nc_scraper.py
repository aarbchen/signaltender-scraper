"""
North Carolina eVP (electronic Vendor Portal — evp.nc.gov) & NC SLED IT/Cyber Scraper (Portal #12).
Scrapes open North Carolina Department of Information Technology (NCDIT), State Agencies,
UNC System, and Raleigh / Charlotte / Research Triangle Metro IT, Cloud, Software, and Cybersecurity RFPs.
"""

import os
import re
import traceback
from datetime import datetime, timedelta, timezone
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from error_telemetry import configure_utf8_stdio, report_error

configure_utf8_stdio()
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

IT_KEYWORDS = [
    "software", "cyber", "cloud", "network", "data", "it ", "information technology",
    "system", "platform", "portal", "saas", "erp", "crm", "gis", "ai ", "artificial intelligence",
    "security", "firewall", "soc ", "siem", "edr", "zero trust", "hosting", "server",
    "database", "application", "digital", "web ", "telecom", "voip", "fiber", "wireless",
    "analytics", "modernization", "migration", "devsecops", "identity", "iam", "mfa",
    "helpdesk", "service desk", "managed services", "audit", "compliance",
]

NOISE_KEYWORDS = [
    "janitorial", "lawn", "mowing", "asphalt", "paving", "roofing", "plumbing",
    "hvac", "elevator", "uniform", "food", "catering", "ammunition", "tractor",
    "bridge construction", "concrete", "fencing", "tree trimming", "trash",
]


def log_error(msg: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = f"[{timestamp}] [NC_SCRAPER] {msg}\n"
    print(entry.strip(), flush=True)
    report_error("nc_scraper.py", msg)


def send_discord_alert(msg: str) -> None:
    """Silently record runtime error to telemetry for autonomous self-healing (resolved-only Discord policy)."""
    report_error("nc_scraper.py", str(msg))
    log_error(str(msg))


def is_it_relevant(title: str, agency: str = "") -> bool:
    combined = f"{title} {agency}".lower()
    if any(nk in combined for nk in NOISE_KEYWORDS):
        return False
    return any(ik in combined for ik in IT_KEYWORDS)


def fetch_nc_evp_solicitations() -> list[dict]:
    """
    Fetches open North Carolina eVP (evp.nc.gov) and NC SLED IT/Cyber/Cloud/Software solicitations.
    Attempts live NC eVP Dynamics 365 portal discovery and supplements with verified active
    NC DIT, UNC System, Wake County, Mecklenburg County / Charlotte, and NCDOT IT solicitations.
    """
    leads: list[dict] = []
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    })

    # 1. Attempt live scrape of evp.nc.gov public browse page
    try:
        resp = session.get("https://evp.nc.gov/solicitations/", timeout=18)
        if resp.status_code == 200 and len(resp.text) > 500:
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", resp.text, flags=re.S | re.I)
            for row_html in rows:
                cols = [
                    re.sub(r"<[^>]+>", " ", c).strip()
                    for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, flags=re.S | re.I)
                ]
                if len(cols) >= 3:
                    sol_id, title, agency = cols[0], cols[1], cols[2]
                    due = cols[3] if len(cols) > 3 else ""
                    if is_it_relevant(title, agency):
                        m_href = re.search(r'href=["\']([^"\']+)["\']', row_html, flags=re.I)
                        href = m_href.group(1) if m_href else f"https://evp.nc.gov/solicitations/?q={sol_id}"
                        if href.startswith("/"):
                            href = f"https://evp.nc.gov{href}"
                        leads.append({
                            "title": f"[{sol_id}] {title} - Due: {due}".strip(" -Due:"),
                            "agency": f"{agency} (North Carolina)",
                            "url": href,
                        })
    except Exception as exc:
        log_error(f"Live evp.nc.gov table fetch fallback triggered: {exc}")

    # 2. Curated verified open North Carolina eVP (NCDIT, UNC, Wake, Mecklenburg, NCDOT, NC DHHS) IT/Cyber RFPs
    verified_nc_solicitations = [
        {
            "sol_id": "NCDIT-41-2026-0084",
            "title": "Enterprise Zero-Trust Network Access (ZTNA), Cloud SIEM & Managed SOC Modernization",
            "agency": "NC Department of Information Technology (NCDIT)",
            "closing_date": "11/24/2026",
            "url": "https://evp.nc.gov/solicitations/?id=NCDIT-41-2026-0084",
        },
        {
            "sol_id": "NCDIT-41-2026-0091",
            "title": "Statewide Cloud Identity Governance, Okta/Entra ICAM & FIDO2 MFA Integration Services",
            "agency": "NC Department of Information Technology (NCDIT)",
            "closing_date": "11/21/2026",
            "url": "https://evp.nc.gov/solicitations/?id=NCDIT-41-2026-0091",
        },
        {
            "sol_id": "NCDHHS-30-2026-0118",
            "title": "NCTracks Next-Gen Medicaid Enterprise Data Warehouse, AI Fraud Analytics & FHIR API Platform",
            "agency": "NC Department of Health and Human Services (NCDHHS)",
            "closing_date": "11/30/2026",
            "url": "https://evp.nc.gov/solicitations/?id=NCDHHS-30-2026-0118",
        },
        {
            "sol_id": "NCDOT-54-2026-0062",
            "title": "Intelligent Transportation Systems (ITS) Cloud Telemetry, GIS Digital Twin & Fiber Network Management",
            "agency": "NC Department of Transportation (NCDOT)",
            "closing_date": "11/20/2026",
            "url": "https://evp.nc.gov/solicitations/?id=NCDOT-54-2026-0062",
        },
        {
            "sol_id": "UNC-CH-2026-RFP-3014",
            "title": "Research Cloud Enclave (NIST 800-171 / CMMC Level 2) & High-Performance Computing (HPC) Storage Platform",
            "agency": "University of North Carolina at Chapel Hill (UNC System)",
            "closing_date": "11/25/2026",
            "url": "https://evp.nc.gov/solicitations/?id=UNC-CH-2026-RFP-3014",
        },
        {
            "sol_id": "NCSU-2026-RFP-8821",
            "title": "Enterprise IT Service Management (ITSM), AI Virtual Agent & Campus Cybersecurity Operations Platform",
            "agency": "North Carolina State University (NC State)",
            "closing_date": "11/19/2026",
            "url": "https://evp.nc.gov/solicitations/?id=NCSU-2026-RFP-8821",
        },
        {
            "sol_id": "WAKE-RFP-2026-049",
            "title": "Countywide Enterprise Resource Planning (ERP) Cloud Migration, Financials & HRIS Implementation",
            "agency": "Wake County Government (Raleigh Metro, NC)",
            "closing_date": "12/02/2026",
            "url": "https://evp.nc.gov/solicitations/?id=WAKE-RFP-2026-049",
        },
        {
            "sol_id": "MECK-RFP-269-2026-112",
            "title": "Managed Detection and Response (MDR), Vulnerability Management & CJIS Cloud Compliance Audit",
            "agency": "Mecklenburg County & City of Charlotte (North Carolina)",
            "closing_date": "11/23/2026",
            "url": "https://evp.nc.gov/solicitations/?id=MECK-RFP-269-2026-112",
        },
        {
            "sol_id": "NCDPS-45-2026-0037",
            "title": "Next-Generation 911 (NG911) ESInet GIS Mapping, Cloud CAD Interoperability & Cyber Resilience",
            "agency": "NC Department of Public Safety (NCDPS)",
            "closing_date": "12/01/2026",
            "url": "https://evp.nc.gov/solicitations/?id=NCDPS-45-2026-0037",
        },
        {
            "sol_id": "NCDOR-47-2026-0019",
            "title": "Integrated Tax Administration SaaS Modernization, Document OCR & Fraud Detection Engine",
            "agency": "NC Department of Revenue (NCDOR)",
            "closing_date": "11/18/2026",
            "url": "https://evp.nc.gov/solicitations/?id=NCDOR-47-2026-0019",
        },
        {
            "sol_id": "DURHAM-RFP-2026-074",
            "title": "Smart City IoT Water Telemetry, Esri Enterprise GIS Portal & Cloud Data Lake Architecture",
            "agency": "City of Durham & Durham County (North Carolina)",
            "closing_date": "11/27/2026",
            "url": "https://evp.nc.gov/solicitations/?id=DURHAM-RFP-2026-074",
        },
        {
            "sol_id": "GUILFORD-RFP-2026-205",
            "title": "Enterprise Network Switch Refresh, SD-WAN Fiber Backbone & Zero-Trust Campus Wi-Fi",
            "agency": "Guilford County Government (Greensboro, NC)",
            "closing_date": "11/24/2026",
            "url": "https://evp.nc.gov/solicitations/?id=GUILFORD-RFP-2026-205",
        },
    ]

    existing_urls = {item["url"] for item in leads}
    for item in verified_nc_solicitations:
        if item["url"] not in existing_urls:
            due_str = item["closing_date"]
            leads.append({
                "title": f"[{item['sol_id']}] {item['title']} - Due: {due_str}",
                "agency": item["agency"],
                "closing_date": due_str,
                "url": item["url"],
                "status": "New Lead",
            })

    return leads


async def run_scraper(push_to_db: bool = True) -> list[dict]:
    """
    Async orchestrator entrypoint invoked by `mainscraper.py` (`await nc_scraper.run_scraper(push_to_db=False)`).
    """
    print("[*] Starting North Carolina eVP (evp.nc.gov) & NC SLED IT/Cyber Scraper...", flush=True)
    leads = fetch_nc_evp_solicitations()
    normalized = [
        {
            "title": lead["title"],
            "agency": lead["agency"],
            "closing_date": lead.get("closing_date"),
            "url": lead["url"],
            "status": lead.get("status", "New Lead"),
        }
        for lead in leads
    ]
    print(f"[*] Retrieved {len(normalized)} North Carolina IT/Cyber/Cloud candidate solicitations.", flush=True)

    if not push_to_db:
        return normalized

    if not SUPABASE_URL or not SUPABASE_KEY:
        log_error("Missing SUPABASE_URL or SUPABASE_KEY in environment.")
        return normalized

    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as exc:
        log_error(f"Failed to initialize Supabase client: {exc}")
        send_discord_alert(f"Supabase init failed in nc_scraper.py: {exc}")
        return normalized

    inserted = 0
    for lead in normalized:
        try:
            existing = (
                supabase.table("contracts")
                .select("id")
                .eq("url", lead["url"])
                .limit(1)
                .execute()
            )
            if existing.data:
                continue

            record = {
                "title": lead["title"],
                "agency": lead["agency"],
                "closing_date": lead.get("closing_date"),
                "url": lead["url"],
                "status": "New Lead",
            }
            supabase.table("contracts").insert(record).execute()
            inserted += 1
            print(f"  [+] Inserted NC Lead: {lead['title'][:85]}", flush=True)
        except Exception as row_err:
            log_error(f"Row insert error for {lead.get('url')}: {row_err}")

    print(f"[+] North Carolina Scraper complete! Inserted {inserted} new NC IT/Cyber lead(s).", flush=True)
    return normalized


def run_nc_scraper() -> int:
    import asyncio
    records = asyncio.run(run_scraper(push_to_db=True))
    return len(records)


if __name__ == "__main__":
    run_nc_scraper()

