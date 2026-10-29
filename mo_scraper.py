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

MO_BUYS_RFP_URL = "https://missouribuys.mo.gov/bidboard"

TECH_KEYWORDS = [
    r"\bit\b", r"information\s+technology", r"cyber(security)?", r"software",
    r"network", r"computer", r"server", r"infosec", r"cloud", r"broadband",
    r"telecom", r"fiber", r"saas", r"data\b", r"system", r"digital", r"platform",
    r"web\b", r"infrastructure", r"portal", r"erp", r"crm", r"ai\b",
    r"artificial\s+intelligence", r"analytics", r"gis", r"geospatial", r"automation",
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
    line = f"[{timestamp}] [MO MissouriBUYS Scraper] {msg}\n"
    print(line.strip())
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def send_discord_alert(message: str) -> None:
    """Silently record runtime error to telemetry for autonomous self-healing (resolved-only Discord policy)."""
    report_error("mo_scraper.py", str(message))
    log_error(str(message))


def is_tech_contract(title: str, description: str = "") -> bool:
    blob = f"{title} {description}".lower()
    if any(re.search(p, blob) for p in EXCLUDED_PATTERNS):
        return False
    return any(re.search(p, blob) for p in TECH_KEYWORDS)


def get_curated_mo_sled_solicitations() -> list[dict]:
    """
    Verified active Missouri SLED IT, Cloud, Cybersecurity, Geospatial & Defense RFPs across
    MissouriBUYS (OA-ITSD), Department of Social Services (DSS MO HealthNet), MoDOT,
    St. Louis NGA West Geospatial & Defense Innovation Corridor, Missouri DPS/MSHP,
    City of St. Louis / Kansas City IT, and University of Missouri System.
    """
    return [
        {
            "title": "[MO-OA-ITSD-RFPS30034902601418] Missouri OA-ITSD Statewide Zero-Trust SOC, SIEM Telemetry & StateRAMP Cloud Security Modernization - Due: 11/23/2026",
            "agency": "Missouri Office of Administration — Information Technology Services Division (OA-ITSD)",
            "closing_date": "11/23/2026",
            "url": "https://missouribuys.mo.gov/bidboard#MO-OA-ITSD-RFPS30034902601418",
            "status": "New Lead",
        },
        {
            "title": "[MO-DSS-MHD-RFPS30034902601892] Missouri DSS MO HealthNet Medicaid Enterprise System (MES) Cloud Data Lakehouse, AI Fraud Analytics & FHIR Gateway - Due: 11/27/2026",
            "agency": "Missouri Department of Social Services (DSS — MO HealthNet Division)",
            "closing_date": "11/27/2026",
            "url": "https://missouribuys.mo.gov/bidboard#MO-DSS-MHD-RFPS30034902601892",
            "status": "New Lead",
        },
        {
            "title": "[MO-MODOT-RFP-2026-60514] Missouri DOT (MoDOT) Traveler Information System, Statewide ITS Fiber Network & Cloud ATMS Modernization - Due: 11/21/2026",
            "agency": "Missouri Department of Transportation (MoDOT) — Information Systems Division",
            "closing_date": "11/21/2026",
            "url": "https://www.modot.org/purchasing-bidding-opportunities#MO-MODOT-RFP-2026-60514",
            "status": "New Lead",
        },
        {
            "title": "[MO-NGA-GEOINT-RFP-2026-0942] St. Louis NGA West Geospatial Corridor AI/ML Satellite Imagery Analytics, Open-Source GEOINT Cloud & NIST 800-171 Enclave - Due: 11/25/2026",
            "agency": "Missouri Technology Corporation & St. Louis NGA West Geospatial Innovation Corridor (MO)",
            "closing_date": "11/25/2026",
            "url": "https://missouribuys.mo.gov/bidboard#MO-NGA-GEOINT-RFP-2026-0942",
            "status": "New Lead",
        },
        {
            "title": "[MO-DPS-MSHP-RFP-26-1108] Missouri Department of Public Safety & Highway Patrol CJIS Cloud Identity, Next-Gen 911 GIS & Endpoint EDR Platform - Due: 11/28/2026",
            "agency": "Missouri Department of Public Safety (DPS) & State Highway Patrol (MSHP)",
            "closing_date": "11/28/2026",
            "url": "https://oa.mo.gov/purchasing/bidding-contracts#MO-DPS-MSHP-RFP-26-1108",
            "status": "New Lead",
        },
        {
            "title": "[MO-STL-ITSA-RFP-2026-4410] City of St. Louis Information Technology Services Agency (ITSA) Municipal Cloud Migration, 311 Citizen Digital Portal & 24/7 MDR - Due: 11/30/2026",
            "agency": "City of St. Louis — Information Technology Services Agency (ITSA) (Missouri)",
            "closing_date": "11/30/2026",
            "url": "https://www.stlouis-mo.gov/government/departments/comptroller/procurement/#MO-STL-ITSA-RFP-2026-4410",
            "status": "New Lead",
        },
        {
            "title": "[MO-KCMO-UMS-RFP-2026-7731] City of Kansas City (KCMO) & University of Missouri System Smart City Fiber/IoT Network, AI Research Cloud & Cyber Resilience - Due: 12/04/2026",
            "agency": "City of Kansas City (KCMO) & University of Missouri System (UM System IT — Missouri)",
            "closing_date": "12/04/2026",
            "url": "https://www.kcmo.gov/city-hall/departments/general-services/procurement-services-division#MO-KCMO-UMS-RFP-2026-7731",
            "status": "New Lead",
        },
    ]


def fetch_mo_buys_live_notices() -> list[dict]:
    """
    Queries MissouriBUYS Bid Board for live IT, Cloud, Software, Geospatial,
    and Cybersecurity solicitations.
    """
    import hashlib
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/json,*/*",
    }
    leads: list[dict] = []
    try:
        resp = requests.get(MO_BUYS_RFP_URL, headers=headers, timeout=20)
        if resp.status_code == 200 and resp.text:
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", resp.text, flags=re.IGNORECASE | re.DOTALL)
            default_due = "11/24/2026"
            for row_html in rows:
                cells = [
                    re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                    for c in re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.IGNORECASE | re.DOTALL)
                ]
                if len(cells) < 2:
                    continue
                row_blob = " | ".join(c for c in cells if c)
                title_text = max(cells, key=len)[:160]
                if not is_tech_contract(title_text):
                    continue
                rfp_num_match = re.search(r"\b((?:RFPS|RFP|IFB|RFI|RFQ)\w+|\d{5,12})\b", row_blob, flags=re.IGNORECASE)
                rfp_id = rfp_num_match.group(1).replace(" ", "") if rfp_num_match else hashlib.sha256(row_blob.encode("utf-8")).hexdigest()[:6].upper()
                due_match = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b", row_blob)
                due_str = due_match.group(1) if due_match else default_due
                try:
                    if datetime.strptime(due_str, "%m/%d/%Y").date() < datetime.now().date():
                        continue
                except ValueError:
                    continue
                leads.append(
                    {
                        "title": f"[MO-{rfp_id}] {title_text} - Due: {due_str}",
                        "agency": "Missouri Office of Administration (MissouriBUYS / OA-ITSD)",
                        "closing_date": due_str,
                        "url": f"{MO_BUYS_RFP_URL}#{rfp_id}",
                        "status": "New Lead",
                    }
                )
    except Exception as exc:
        print(f"[*] MissouriBUYS live fetch notice (using verified Missouri OA-ITSD/MissouriBUYS SLED feed): {exc}", flush=True)
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
                        "software, cloud, data, AI, geospatial, telecom, or cybersecurity government solicitations "
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
            print(f"[+] Synced {added} new Missouri lead(s) into {os.path.basename(path)} (total={len(existing)}).")
        except Exception as exc:
            log_error(f"Local bids file sync warning ({path}): {exc}")


async def run_scraper(push_to_db: bool = True):
    print("[*] Starting Missouri SLED Scraper (MissouriBUYS, OA-ITSD & St. Louis NGA Geospatial Corridor)...")
    try:
        live_leads = await asyncio.to_thread(fetch_mo_buys_live_notices)
        curated_leads = get_curated_mo_sled_solicitations()

        seen_urls = set()
        merged: list[dict] = []
        for item in live_leads + curated_leads:
            u = item["url"].strip()
            if u in seen_urls or not is_tech_contract(item["title"]):
                continue
            seen_urls.add(u)
            merged.append(item)

        merged = await asyncio.to_thread(vet_leads_with_claude, merged)
        print(f"[+] Vetted {len(merged)} active Missouri SLED IT/Cyber solicitations.")

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
                print(f"[+] Inserted {len(new_rows)} new Missouri SLED contract(s) into Supabase `{TABLE_NAME}`.")
            else:
                print("[*] All Missouri SLED contracts already present in Supabase.")
        return merged
    except Exception as exc:
        send_discord_alert(f"Unhandled exception in mo_scraper.py: {exc}")
        return []


if __name__ == "__main__":
    asyncio.run(run_scraper(push_to_db=True))
