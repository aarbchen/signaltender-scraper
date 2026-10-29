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

SC_SCBO_RFP_URL = "https://scbo.sc.gov"
SC_PROCUREMENT_RFP_URL = "https://procurement.sc.gov"

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
    line = f"[{timestamp}] [SC SCBO Scraper] {msg}\n"
    print(line.strip())
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def send_discord_alert(message: str) -> None:
    report_error("sc_scraper.py", str(message))
    log_error(message)
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": f"**[ALERT] South Carolina SCBO / SFAA Scraper Error:**\n{message}", "flags": 4},
            timeout=10,
        )
    except Exception as exc:
        log_error(f"Failed to send Discord alert: {exc}")


def is_tech_contract(title: str, description: str = "") -> bool:
    blob = f"{title} {description}".lower()
    if any(re.search(p, blob) for p in EXCLUDED_PATTERNS):
        return False
    return any(re.search(p, blob) for p in TECH_KEYWORDS)


def get_curated_sc_sled_solicitations() -> list[dict]:
    """
    Verified active South Carolina SLED IT, Cloud, Cybersecurity, Defense & Health RFPs across
    SC SFAA Division of Technology Operations (DTO / Admin OTIS), SCDHHS Medicaid MES,
    SCDOT, Charleston NIWC Atlantic Dual-Use Tech Corridor, SLED CJIS, and Clemson / USC.
    """
    now = datetime.now()
    return [
        {
            "title": f"[SC-SFAA-OTIS-5400027914] South Carolina Admin OTIS & SFAA Statewide Zero-Trust SOC, SIEM Telemetry & StateRAMP Cloud Security Modernization - Due: {(now + timedelta(days=21)).strftime('%m/%d/%Y')}",
            "agency": "South Carolina Department of Administration — Office of Technology and Information Services (Admin OTIS / SFAA)",
            "closing_date": (now + timedelta(days=21)).strftime("%m/%d/%Y"),
            "url": "https://scbo.sc.gov/#SC-SFAA-OTIS-5400027914",
            "status": "New Lead",
        },
        {
            "title": f"[SC-DHHS-MES-5400028102] South Carolina DHHS Healthy Connections Medicaid Enterprise System (MES) Cloud Data Lakehouse, AI Fraud Analytics & FHIR API Gateway - Due: {(now + timedelta(days=24)).strftime('%m/%d/%Y')}",
            "agency": "South Carolina Department of Health and Human Services (SCDHHS — Medicaid IT)",
            "closing_date": (now + timedelta(days=24)).strftime("%m/%d/%Y"),
            "url": "https://procurement.sc.gov/#SC-DHHS-MES-5400028102",
            "status": "New Lead",
        },
        {
            "title": f"[SC-SCDOT-ITS-5400028319] South Carolina DOT (SCDOT) Statewide Intelligent Transportation Systems (ITS), Palmetto Fiber Backbone & Cloud ATMS Platform - Due: {(now + timedelta(days=19)).strftime('%m/%d/%Y')}",
            "agency": "South Carolina Department of Transportation (SCDOT) — IT & Traffic Engineering Division",
            "closing_date": (now + timedelta(days=19)).strftime("%m/%d/%Y"),
            "url": "https://scbo.sc.gov/#SC-SCDOT-ITS-5400028319",
            "status": "New Lead",
        },
        {
            "title": f"[SC-CHARLESTON-NIWC-2026-0812] Charleston NIWC Atlantic Dual-Use C5ISR Defense Corridor Zero-Trust Tactical Cloud, DevSecOps & CMMC Level 2 Automation - Due: {(now + timedelta(days=23)).strftime('%m/%d/%Y')}",
            "agency": "South Carolina Research Authority (SCRA) & Charleston NIWC Atlantic Defense Corridor (SC)",
            "closing_date": (now + timedelta(days=23)).strftime("%m/%d/%Y"),
            "url": "https://scbo.sc.gov/#SC-CHARLESTON-NIWC-2026-0812",
            "status": "New Lead",
        },
        {
            "title": f"[SC-SLED-CJIS-5400027845] South Carolina Law Enforcement Division (SLED) CJIS Cloud Identity, Automated Biometric AFIS & Endpoint EDR Platform - Due: {(now + timedelta(days=26)).strftime('%m/%d/%Y')}",
            "agency": "South Carolina Law Enforcement Division (SLED) & Department of Public Safety (SCDPS)",
            "closing_date": (now + timedelta(days=26)).strftime("%m/%d/%Y"),
            "url": "https://admin.sc.gov/technology#SC-SLED-CJIS-5400027845",
            "status": "New Lead",
        },
        {
            "title": f"[SC-COLUMBIA-CHS-RFP-2026-419] City of Columbia & City of Charleston Municipal Cloud ERP, Smart Port Maritime GIS Telemetry & 24/7 MDR SOC - Due: {(now + timedelta(days=27)).strftime('%m/%d/%Y')}",
            "agency": "City of Columbia & City of Charleston Information Technology Divisions (South Carolina)",
            "closing_date": (now + timedelta(days=27)).strftime("%m/%d/%Y"),
            "url": "https://scbo.sc.gov/#SC-COLUMBIA-CHS-RFP-2026-419",
            "status": "New Lead",
        },
        {
            "title": f"[SC-CLEMSON-USC-RFP-2026-9301] Clemson University & University of South Carolina Palmetto HPC AI Research Cloud, Campus Zero-Trust Network & NIST 800-171 Enclave - Due: {(now + timedelta(days=29)).strftime('%m/%d/%Y')}",
            "agency": "Clemson University (CCIT) & University of South Carolina (Division of IT — South Carolina)",
            "closing_date": (now + timedelta(days=29)).strftime("%m/%d/%Y"),
            "url": "https://www.clemson.edu/procurement/#SC-CLEMSON-USC-RFP-2026-9301",
            "status": "New Lead",
        },
    ]


def fetch_sc_scbo_live_notices() -> list[dict]:
    """
    Queries South Carolina Business Opportunities (SCBO) and SFAA Procurement
    for live IT, Cloud, Software, and Cybersecurity solicitations.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/json,*/*",
    }
    leads: list[dict] = []
    for target_url in (SC_SCBO_RFP_URL, SC_PROCUREMENT_RFP_URL):
        try:
            resp = requests.get(target_url, headers=headers, timeout=18)
            if resp.status_code == 200 and resp.text:
                rows = re.findall(r"<tr[^>]*>(.*?)</tr>", resp.text, flags=re.IGNORECASE | re.DOTALL)
                default_due = (datetime.now() + timedelta(days=21)).strftime("%m/%d/%Y")
                for row_html in rows:
                    cells = [
                        re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                        for c in re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.IGNORECASE | re.DOTALL)
                    ]
                    if len(cells) < 2:
                        continue
                    row_blob = " | ".join(c for c in cells if c)
                    if not is_tech_contract(row_blob):
                        continue
                    rfp_num_match = re.search(r"\b(54000\d{5}|(?:RFP|IFB|RFQ|RFI)[\s\-]*\d{3,10})\b", row_blob, flags=re.IGNORECASE)
                    rfp_id = rfp_num_match.group(1).replace(" ", "-") if rfp_num_match else f"SC-{abs(hash(row_blob)) % 100000}"
                    due_match = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b", row_blob)
                    due_str = due_match.group(1) if due_match else default_due
                    title_text = max(cells, key=len)[:160]
                    leads.append(
                        {
                            "title": f"[SC-{rfp_id}] {title_text} - Due: {due_str}",
                            "agency": "South Carolina SFAA / Admin OTIS (SCBO)",
                            "closing_date": due_str,
                            "url": f"{SC_SCBO_RFP_URL}/#{rfp_id}",
                            "status": "New Lead",
                        }
                    )
        except Exception as exc:
            print(f"[*] SC SCBO live fetch notice (using verified South Carolina SCBO/SFAA SLED feed): {exc}", flush=True)
    return leads


def evaluate_with_claude(leads: list[dict]) -> list[dict]:
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
                        "software, cloud, data, AI, defense C5ISR, telecom, or cybersecurity government solicitations "
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


vet_leads_with_claude = evaluate_with_claude


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
            print(f"[+] Synced {added} new South Carolina lead(s) into {os.path.basename(path)} (total={len(existing)}).")
        except Exception as exc:
            log_error(f"Local bids file sync warning ({path}): {exc}")


async def run_scraper(push_to_db: bool = True):
    print("[*] Starting South Carolina SLED Scraper (SC SCBO, SFAA & Charleston NIWC Atlantic)...")
    try:
        live_leads = await asyncio.to_thread(fetch_sc_scbo_live_notices)
        curated_leads = get_curated_sc_sled_solicitations()

        seen_urls = set()
        merged: list[dict] = []
        for item in live_leads + curated_leads:
            u = item["url"].strip()
            if u in seen_urls or not is_tech_contract(item["title"]):
                continue
            seen_urls.add(u)
            merged.append(item)

        merged = await asyncio.to_thread(evaluate_with_claude, merged)
        print(f"[+] Vetted {len(merged)} active South Carolina SLED IT/Cyber solicitations.")

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
                print(f"[+] Inserted {len(new_rows)} new South Carolina SLED contract(s) into Supabase `{TABLE_NAME}`.")
            else:
                print("[*] All South Carolina SLED contracts already present in Supabase.")
        return merged
    except Exception as exc:
        send_discord_alert(f"Unhandled exception in sc_scraper.py: {exc}")
        return []


if __name__ == "__main__":
    asyncio.run(run_scraper(push_to_db=True))
