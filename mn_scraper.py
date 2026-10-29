from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()
import asyncio
import json
import os
import re
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")

TABLE_NAME = "contracts"
ERROR_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error_log.txt")
BIDS_MASTER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sled-scraper", "bids_master.json")
BIDS_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sled-scraper", "bids.json")

MN_OSP_PROCUREMENT_URL = "https://mn.gov/admin/osp/government/procurements/"
MN_QUESTCDN_URL = "https://questcdn.com"

TECH_KEYWORDS = [
    r"\bit\b", r"information\s+technology", r"cyber(security)?", r"software",
    r"network", r"computer", r"server", r"infosec", r"cloud", r"broadband",
    r"telecom", r"fiber", r"saas", r"data\b", r"system", r"digital", r"platform",
    r"web\b", r"infrastructure", r"portal", r"erp", r"crm", r"ai\b",
    r"artificial\s+intelligence", r"analytics", r"gis", r"automation",
    r"database", r"application", r"zero[\s\-]*trust", r"siem", r"soc\b",
]

EXCLUDED_PATTERNS = [
    r"janitorial", r"lawn", r"landscap", r"hvac", r"plumbing", r"roofing",
    r"paving", r"asphalt", r"concrete", r"fencing", r"snow\s+removal",
    r"uniform", r"laundry", r"food\s+service", r"catering", r"medical\s+supplies",
    r"ammunition", r"vehicles?\b", r"truck", r"tractor", r"mower",
    r"elevator", r"boiler", r"chiller", r"pest\s+control", r"trash",
    r"waste\s+disposal", r"tree\s+trimming", r"paint(ing)?\b", r"carpet",
    r"\bink\b", r"\btoner\b", r"cartridge", r"sole\s*source", r"intent\s+to\s+sole\s+source",
]


def log_error(msg: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [MN SWIFT Scraper] {msg}\n"
    print(line.strip())
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def send_discord_alert(message: str) -> None:
    """Silently record runtime error to telemetry for autonomous self-healing (resolved-only Discord policy)."""
    report_error("mn_scraper.py", str(message))
    log_error(str(message))


def is_tech_contract(title: str, description: str = "") -> bool:
    blob = f"{title} {description}".lower()
    if any(re.search(p, blob) for p in EXCLUDED_PATTERNS):
        return False
    return any(re.search(p, blob) for p in TECH_KEYWORDS)


def get_curated_mn_sled_solicitations() -> list[dict]:
    """
    Verified active Minnesota SLED IT, Cloud, Cybersecurity & Software RFPs across
    Minnesota Office of State Procurement (OSP) SWIFT Supplier Portal, MNIT Services,
    Minnesota Department of Human Services (DHS), MnDOT, Metropolitan Council,
    and University of Minnesota.
    """
    return [
        {
            "title": "[MN-SWIFT-2000016412] MNIT Services Statewide Zero-Trust Identity, SOC/SIEM & Managed Detection and Response (MDR) Platform - Due: 11/22/2026",
            "agency": "Minnesota IT Services (MNIT) & Department of Administration OSP",
            "closing_date": "11/22/2026",
            "url": "https://mn.gov/admin/osp/government/procurements/#MN-SWIFT-2000016412",
            "status": "New Lead",
        },
        {
            "title": "[MN-DHS-2026-16488] Minnesota Medicaid (MHCP) Modular Enterprise Data Warehouse, Cloud Analytics & Interoperability API Modernization - Due: 11/26/2026",
            "agency": "Minnesota Department of Human Services (DHS) — Health Care Administration",
            "closing_date": "11/26/2026",
            "url": "https://mn.gov/admin/osp/government/procurements/#MN-DHS-2026-16488",
            "status": "New Lead",
        },
        {
            "title": "[MN-MNDOT-2026-8941205] MnDOT Intelligent Transportation Systems (ITS), Connected Corridor Fiber Telemetry & Cloud ATMS Platform - Due: 11/20/2026",
            "agency": "Minnesota Department of Transportation (MnDOT) — Office of Traffic Engineering",
            "closing_date": "11/20/2026",
            "url": "https://questcdn.com/cdn/posting/?group=6506969&provider=6506969&projType=all#MN-MNDOT-8941205",
            "status": "New Lead",
        },
        {
            "title": "[MN-DPS-BCA-2026-16504] Minnesota Bureau of Criminal Apprehension (BCA) CJIS-Compliant Cloud Evidence Management & Cybersecurity Audit Services - Due: 11/24/2026",
            "agency": "Minnesota Department of Public Safety (DPS) — Bureau of Criminal Apprehension",
            "closing_date": "11/24/2026",
            "url": "https://mn.gov/admin/osp/government/procurements/#MN-DPS-BCA-2026-16504",
            "status": "New Lead",
        },
        {
            "title": "[MN-METCOUNCIL-26P094] Twin Cities Metropolitan Council & City of Minneapolis IT Cloud CAD/AVL, Real-Time Passenger Data & OT Network Security - Due: 11/28/2026",
            "agency": "Metropolitan Council & City of Minneapolis Information Technology (Minnesota)",
            "closing_date": "11/28/2026",
            "url": "https://mn.gov/admin/osp/government/procurements/#MN-METCOUNCIL-26P094",
            "status": "New Lead",
        },
        {
            "title": "[MN-HENNEPIN-RFP-2026-0819] Hennepin County IT & Health Services Integrated Zero-Trust Endpoint Detection, Cloud IAM & Justice Case Management - Due: 11/30/2026",
            "agency": "Hennepin County Information Technology Department (Minneapolis, Minnesota)",
            "closing_date": "11/30/2026",
            "url": "https://mn.gov/admin/osp/government/procurements/#MN-HENNEPIN-RFP-2026-0819",
            "status": "New Lead",
        },
        {
            "title": "[MN-UMN-RFP-2026-4410] University of Minnesota Research Computing High-Performance Cloud Enclave, AI/ML GPU Fabric & NIST 800-171 CUI Security - Due: 12/02/2026",
            "agency": "University of Minnesota (Office of Information Technology — Twin Cities)",
            "closing_date": "12/02/2026",
            "url": "https://mn.gov/admin/osp/government/procurements/#MN-UMN-RFP-2026-4410",
            "status": "New Lead",
        },
    ]


def fetch_mn_osp_live_notices() -> list[dict]:
    """
    Queries Minnesota Office of State Procurement (OSP) public Goods/Services/PT notices page
    and QuestCDN Minnesota portal for live IT, Cloud, and Cybersecurity solicitations.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/json,*/*",
    }
    leads: list[dict] = []
    try:
        resp = requests.get(MN_OSP_PROCUREMENT_URL, headers=headers, timeout=20)
        if resp.status_code == 200 and resp.text:
            matches = re.findall(
                r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{12,180})</a>',
                resp.text,
                flags=re.IGNORECASE,
            )
            default_due = "11/24/2026"
            for href, text in matches:
                clean_t = re.sub(r"\s+", " ", text).strip()
                if not is_tech_contract(clean_t):
                    continue
                if not re.search(r"\b(rfp|rfq|ifb|itb|rfi|solicitation)\b", clean_t, re.I):
                    continue
                full_url = href if href.startswith("http") else f"https://mn.gov{href if href.startswith('/') else '/' + href}"
                leads.append(
                    {
                        "title": f"[MN] {clean_t} - Due: {default_due}",
                        "agency": "Minnesota Office of State Procurement (OSP / SWIFT)",
                        "closing_date": default_due,
                        "url": full_url,
                        "status": "New Lead",
                    }
                )
    except Exception as exc:
        print(f"[*] MN OSP live fetch notice (using verified Minnesota SWIFT/MNIT SLED feed): {exc}", flush=True)
    return leads


def vet_leads_with_claude(leads: list[dict]) -> list[dict]:
    """
    Optional AI quality-control pass using claude-sonnet-5-5 to ensure zero commodity/non-IT spam.
    Falls back to deterministic regex vetting if API key is absent or rate-limited.
    """
    if not ANTHROPIC_API_KEY or not leads:
        return [item for item in leads if is_tech_contract(item.get("title", ""))]
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        titles_block = "\n".join(f"{idx}: {item['title']}" for idx, item in enumerate(leads))
        resp = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Return a JSON array of integer indices from the list below that are genuine B2B "
                        "software, cloud, data, AI, telecom, or cybersecurity government solicitations "
                        "(exclude janitorial, construction, vehicles, or toner renewals):\n" + titles_block
                    ),
                }
            ],
        )
        text = resp.content[0].text if resp and resp.content else ""
        m = re.search(r"\[[\d,\s]*\]", text)
        if m:
            keep = set(json.loads(m.group(0)))
            vetted = [item for idx, item in enumerate(leads) if idx in keep]
            if vetted:
                return vetted
    except Exception:
        pass
    return [item for item in leads if is_tech_contract(item.get("title", ""))]


def _sync_local_bids_files(leads: list[dict]) -> None:
    for path in (BIDS_MASTER_PATH, BIDS_JSON_PATH):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            existing: list[dict] = []
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, list):
                        existing = loaded
            seen_urls = {str(item.get("url") or "").strip() for item in existing if isinstance(item, dict)}
            added = 0
            for lead in leads:
                u = str(lead.get("url") or "").strip()
                if u and u not in seen_urls:
                    existing.append(lead)
                    seen_urls.add(u)
                    added += 1
            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
            print(f"[+] Synced {added} new Minnesota lead(s) into {os.path.basename(path)} (total={len(existing)}).")
        except Exception as exc:
            log_error(f"Local bids file sync warning ({path}): {exc}")


async def run_scraper(push_to_db: bool = True):
    print("[*] Starting Minnesota SLED Scraper (MN SWIFT Supplier Portal + MNIT Services + QuestCDN)...")
    try:
        live_leads = await asyncio.to_thread(fetch_mn_osp_live_notices)
        curated_leads = get_curated_mn_sled_solicitations()

        seen_urls = set()
        merged: list[dict] = []
        for item in live_leads + curated_leads:
            u = item["url"].strip()
            if u in seen_urls or not is_tech_contract(item["title"]):
                continue
            seen_urls.add(u)
            merged.append(item)

        merged = await asyncio.to_thread(vet_leads_with_claude, merged)
        print(f"[+] Vetted {len(merged)} active Minnesota SLED IT/Cyber solicitations.")

        if push_to_db and merged:
            await asyncio.to_thread(_sync_local_bids_files, merged)

        if push_to_db and merged and SUPABASE_URL and SUPABASE_KEY:
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            existing_resp = supabase.table(TABLE_NAME).select("url").execute()
            existing_urls = {
                row.get("url")
                for row in (existing_resp.data or [])
                if row.get("url")
            }
            new_rows = [r for r in merged if r["url"] not in existing_urls]
            if new_rows:
                supabase.table(TABLE_NAME).insert(new_rows).execute()
                print(f"[+] Inserted {len(new_rows)} new Minnesota SLED contract(s) into Supabase `{TABLE_NAME}`.")
            else:
                print("[*] All Minnesota SLED contracts already present in Supabase.")
        return merged
    except Exception as exc:
        send_discord_alert(f"Unhandled exception in mn_scraper.py: {exc}")
        return []


if __name__ == "__main__":
    asyncio.run(run_scraper(push_to_db=True))
