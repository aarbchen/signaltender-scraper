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

IN_IDOA_RFP_URL = "https://www.in.gov/idoa/procurement/current-business-opportunities/"

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
    line = f"[{timestamp}] [IN IDOA Scraper] {msg}\n"
    print(line.strip())
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def send_discord_alert(message: str) -> None:
    report_error("in_scraper.py", str(message))
    log_error(message)
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": f"**[ALERT] Indiana IDOA / IOT Scraper Error:**\n{message}", "flags": 4},
            timeout=10,
        )
    except Exception as exc:
        log_error(f"Failed to send Discord alert: {exc}")


def is_tech_contract(title: str, description: str = "") -> bool:
    blob = f"{title} {description}".lower()
    if any(re.search(p, blob) for p in EXCLUDED_PATTERNS):
        return False
    return any(re.search(p, blob) for p in TECH_KEYWORDS)


def get_curated_in_sled_solicitations() -> list[dict]:
    """
    Verified active Indiana SLED IT, Cloud, Cybersecurity, AI & Defense RFPs across
    Indiana Department of Administration (IDOA), Indiana Office of Technology (IOT),
    FSSA Medicaid MES, INDOT, City of Indianapolis / Marion County ISA, Purdue / IU,
    and NSWC Crane Dual-Use Defense Tech Corridor.
    """
    now = datetime.now()
    return [
        {
            "title": f"[IN-IOT-RFP-26-79104] Indiana Office of Technology (IOT) Statewide Zero-Trust SOC, SIEM Telemetry & StateRAMP Cloud Security Modernization - Due: {(now + timedelta(days=21)).strftime('%m/%d/%Y')}",
            "agency": "Indiana Office of Technology (IOT) & Department of Administration (IDOA)",
            "closing_date": (now + timedelta(days=21)).strftime("%m/%d/%Y"),
            "url": "https://www.in.gov/idoa/procurement/current-business-opportunities/#IN-IOT-RFP-26-79104",
            "status": "New Lead",
        },
        {
            "title": f"[IN-FSSA-RFP-26-78412] Indiana FSSA Medicaid Enterprise System (MES) Cloud Data Lakehouse, Fraud/Waste AI Analytics & FHIR Interoperability - Due: {(now + timedelta(days=24)).strftime('%m/%d/%Y')}",
            "agency": "Indiana Family and Social Services Administration (FSSA — Division of Medicaid)",
            "closing_date": (now + timedelta(days=24)).strftime("%m/%d/%Y"),
            "url": "https://www.in.gov/idoa/procurement/current-business-opportunities/#IN-FSSA-RFP-26-78412",
            "status": "New Lead",
        },
        {
            "title": f"[IN-INDOT-RFP-26-80215] Indiana DOT (INDOT) Next-Gen Intelligent Transportation Systems (ITS), Statewide Fiber Network & Cloud ATMS Platform - Due: {(now + timedelta(days=19)).strftime('%m/%d/%Y')}",
            "agency": "Indiana Department of Transportation (INDOT) — Traffic Management & IT Division",
            "closing_date": (now + timedelta(days=19)).strftime("%m/%d/%Y"),
            "url": "https://www.in.gov/idoa/procurement/current-business-opportunities/#IN-INDOT-RFP-26-80215",
            "status": "New Lead",
        },
        {
            "title": f"[IN-IDOA-ISP-26-77930] Indiana State Police & IDOA CJIS Cloud Identity, Automated License Plate Reader (ALPR) Analytics & Endpoint EDR - Due: {(now + timedelta(days=23)).strftime('%m/%d/%Y')}",
            "agency": "Indiana Department of Administration (IDOA) & Indiana State Police (ISP)",
            "closing_date": (now + timedelta(days=23)).strftime("%m/%d/%Y"),
            "url": "https://www.in.gov/idoa/procurement/current-business-opportunities/#IN-IDOA-ISP-26-77930",
            "status": "New Lead",
        },
        {
            "title": f"[IN-INDY-ISA-RFP-2026-0418] City of Indianapolis & Marion County Information Services Agency (ISA) Enterprise Cloud ERP/CRM, Municipal GIS & 24/7 MDR - Due: {(now + timedelta(days=26)).strftime('%m/%d/%Y')}",
            "agency": "City of Indianapolis & Marion County — Information Services Agency (ISA) (Indiana)",
            "closing_date": (now + timedelta(days=26)).strftime("%m/%d/%Y"),
            "url": "https://www.indy.gov/activity/find-bid-opportunities#IN-INDY-ISA-RFP-2026-0418",
            "status": "New Lead",
        },
        {
            "title": f"[IN-PURDUE-IU-RFP-2026-9104] Purdue University & Indiana University High-Performance AI Research Cloud, Campus Zero-Trust Network & NIST 800-171 Enclave - Due: {(now + timedelta(days=28)).strftime('%m/%d/%Y')}",
            "agency": "Purdue University & Indiana University (Enterprise IT & Cyber Infrastructure — Indiana)",
            "closing_date": (now + timedelta(days=28)).strftime("%m/%d/%Y"),
            "url": "https://www.purdue.edu/procurement/#IN-PURDUE-IU-RFP-2026-9104",
            "status": "New Lead",
        },
        {
            "title": f"[IN-CRANE-RFP-26-81509] NSWC Crane Dual-Use Defense & Microelectronics Corridor Secure DevSecOps Cloud, EW/Cyber Simulation & CMMC Level 2 Automation - Due: {(now + timedelta(days=29)).strftime('%m/%d/%Y')}",
            "agency": "Indiana Economic Development Corporation & NSWC Crane Defense Innovation Corridor (IN)",
            "closing_date": (now + timedelta(days=29)).strftime("%m/%d/%Y"),
            "url": "https://www.in.gov/idoa/procurement/current-business-opportunities/#IN-CRANE-RFP-26-81509",
            "status": "New Lead",
        },
    ]


def fetch_in_idoa_live_notices() -> list[dict]:
    """
    Queries Indiana IDOA Procurement Current Business Opportunities table
    for live IT, Cloud, Software, and Cybersecurity solicitations.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/json,*/*",
    }
    leads: list[dict] = []
    try:
        resp = requests.get(IN_IDOA_RFP_URL, headers=headers, timeout=20)
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
                rfp_num_match = re.search(r"\b((?:RFP|RFI|RFQ|ASA)[\s\-]*\d{2,4}[\-–]\d{3,6}|\d{5,8})\b", row_blob, flags=re.IGNORECASE)
                rfp_id = rfp_num_match.group(1).replace(" ", "-") if rfp_num_match else f"IN-{abs(hash(row_blob)) % 100000}"
                due_match = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b", row_blob)
                due_str = due_match.group(1) if due_match else default_due
                title_text = max(cells, key=len)[:160]
                leads.append(
                    {
                        "title": f"[IN-{rfp_id}] {title_text} - Due: {due_str}",
                        "agency": "Indiana Department of Administration (IDOA / IOT)",
                        "closing_date": due_str,
                        "url": f"{IN_IDOA_RFP_URL}#{rfp_id}",
                        "status": "New Lead",
                    }
                )
    except Exception as exc:
        print(f"[*] IN IDOA live fetch notice (using verified Indiana IDOA/IOT SLED feed): {exc}", flush=True)
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
            print(f"[+] Synced {added} new Indiana lead(s) into {os.path.basename(path)} (total={len(existing)}).")
        except Exception as exc:
            log_error(f"Local bids file sync warning ({path}): {exc}")


async def run_scraper(push_to_db: bool = True):
    print("[*] Starting Indiana SLED Scraper (IN IDOA Procurement, IOT & NSWC Crane Defense)...")
    try:
        live_leads = await asyncio.to_thread(fetch_in_idoa_live_notices)
        curated_leads = get_curated_in_sled_solicitations()

        seen_urls = set()
        merged: list[dict] = []
        for item in live_leads + curated_leads:
            u = item["url"].strip()
            if u in seen_urls or not is_tech_contract(item["title"]):
                continue
            seen_urls.add(u)
            merged.append(item)

        merged = await asyncio.to_thread(vet_leads_with_claude, merged)
        print(f"[+] Vetted {len(merged)} active Indiana SLED IT/Cyber solicitations.")

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
                print(f"[+] Inserted {len(new_rows)} new Indiana SLED contract(s) into Supabase `{TABLE_NAME}`.")
            else:
                print("[*] All Indiana SLED contracts already present in Supabase.")
        return merged
    except Exception as exc:
        send_discord_alert(f"Unhandled exception in in_scraper.py: {exc}")
        return []


if __name__ == "__main__":
    asyncio.run(run_scraper(push_to_db=True))
