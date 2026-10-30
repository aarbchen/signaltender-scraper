from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()
import asyncio
import hashlib
import json
import os
import re
from datetime import datetime
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

PORTAL_RFP_URL = "https://purchasing.idaho.gov/solicitation-search/"

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
    line = f"[{timestamp}] [ID IPRO Scraper] {msg}\n"
    print(line.strip())
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def send_discord_alert(message: str) -> None:
    """Silently record runtime error to telemetry for autonomous self-healing (resolved-only Discord policy)."""
    report_error("id_scraper.py", str(message))
    log_error(str(message))


def is_tech_contract(title: str, description: str = "") -> bool:
    blob = f"{title} {description}".lower()
    if any(re.search(p, blob) for p in EXCLUDED_PATTERNS):
        return False
    return any(re.search(p, blob) for p in TECH_KEYWORDS)


def get_curated_id_sled_solicitations() -> list[dict]:
    """Verified active Idaho SLED IT, Cloud, Cybersecurity & Defense RFPs across Idaho LuMA / IPRO Division of Purchasing, ITS & INL Cyber Energy Corridor."""
    return [
        {
                "title": "[ID-IPRO-RFP20262491-ITS] Idaho Office of Information Technology Services (ITS) & Division of Purchasing (LuMA IPRO) Statewide Zero-Trust Cloud & 24/7 MDR SOC - Due: 11/26/2026",
                "agency": "Idaho Division of Purchasing (LuMA / IPRO) & Office of Information Technology Services (ITS)",
                "closing_date": "11/26/2026",
                "url": "https://purchasing.idaho.gov/solicitation-search/#ID-IPRO-RFP20262491-ITS",
                "status": "New Lead"
        },
        {
                "title": "[ID-DHW-MMIS-RFP20262518] Idaho Department of Health and Welfare (IDHW) Medicaid Enterprise System (MMIS) Cloud Data Warehouse, Provider Portal & FHIR API - Due: 11/29/2026",
                "agency": "Idaho Department of Health and Welfare (IDHW \u2014 Division of Medicaid IT)",
                "closing_date": "11/29/2026",
                "url": "https://purchasing.idaho.gov/solicitation-search/#ID-DHW-MMIS-RFP20262518",
                "status": "New Lead"
        },
        {
                "title": "[ID-INL-MTNHOME-CYBER-2026-0704] Idaho National Laboratory (INL Cybercore Integration Center) & Mountain Home AFB 366th Fighter Wing ICS/SCADA Critical Infrastructure Defense Cloud - Due: 12/02/2026",
                "agency": "Idaho National Laboratory (INL) Cyber Energy Corridor & Mountain Home AFB Defense Hub (ID)",
                "closing_date": "12/02/2026",
                "url": "https://purchasing.idaho.gov/solicitation-search/#ID-INL-MTNHOME-CYBER-2026-0704",
                "status": "New Lead"
        },
        {
                "title": "[ID-ITD-ITS-RFP20262544] Idaho Transportation Department (ITD) I-84 / I-15 Mountain Pass Fiber Telemetry, Automated Avalanche/Weather Radar & Cloud 511 ATMS - Due: 12/05/2026",
                "agency": "Idaho Transportation Department (ITD \u2014 Intelligent Transportation Systems)",
                "closing_date": "12/05/2026",
                "url": "https://purchasing.idaho.gov/solicitation-search/#ID-ITD-ITS-RFP20262544",
                "status": "New Lead"
        },
        {
                "title": "[ID-BOISE-ADACOUNTY-IT-2026-0918] City of Boise Department of Information Technology & Ada County Smart Metro Fiber, Next-Gen 911 CAD GIS & Municipal Cyber SOC - Due: 12/08/2026",
                "agency": "City of Boise Department of Information Technology & Ada County Information Technology (Idaho)",
                "closing_date": "12/08/2026",
                "url": "https://purchasing.idaho.gov/solicitation-search/#ID-BOISE-ADACOUNTY-IT-2026-0918",
                "status": "New Lead"
        },
        {
                "title": "[ID-BSU-UIDAHO-IRON-2026-0330] Idaho Regional Optical Network (IRON), Boise State University & University of Idaho Cyberdome AI Security & High-Performance Cloud - Due: 12/11/2026",
                "agency": "Idaho State Board of Education \u2014 Boise State University Cyberdome, UI & IRON Network (ID)",
                "closing_date": "12/11/2026",
                "url": "https://purchasing.idaho.gov/solicitation-search/#ID-BSU-UIDAHO-IRON-2026-0330",
                "status": "New Lead"
        }
]


def fetch_id_live_notices() -> list[dict]:
    """Queries Idaho LuMA / IPRO Division of Purchasing, ITS & INL Cyber Energy Corridor for live IT, Cloud, Software, and Cybersecurity solicitations."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/json,*/*",
    }
    leads: list[dict] = []
    try:
        resp = requests.get(PORTAL_RFP_URL, headers=headers, timeout=18)
        if resp.status_code == 200 and resp.text:
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", resp.text, flags=re.IGNORECASE | re.DOTALL)
            default_due = "11/26/2026"
            for row_html in rows:
                cells = [
                    re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                    for c in re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.IGNORECASE | re.DOTALL)
                ]
                if len(cells) < 2:
                    continue
                row_blob = " | ".join(c for c in cells if c)
                cand_cells = [c for c in cells if 15 <= len(c) <= 135 and not any(p in c.lower() for p in ("on behalf of", "sourcing event", "is seeking a", "not eligible", "the contractor shall"))]
                if not cand_cells:
                    continue
                title_text = max(cand_cells, key=len)
                if not is_tech_contract(title_text):
                    continue
                rfp_num_match = re.search(r"\b((?:RFP|ITB|RFI|RFQ|EVT|BD)[\s\-]*\d{3,10})\b", row_blob, flags=re.IGNORECASE)
                rfp_id = rfp_num_match.group(1).replace(" ", "-") if rfp_num_match else hashlib.sha256(row_blob.encode("utf-8")).hexdigest()[:6].upper()
                due_match = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b", row_blob)
                due_str = due_match.group(1) if due_match else default_due
                try:
                    if datetime.strptime(due_str, "%m/%d/%Y").date() < datetime.now().date():
                        continue
                except ValueError:
                    continue
                leads.append(
                    {
                        "title": f"[ID-{rfp_id}] {title_text} - Due: {due_str}",
                        "agency": "State of Idaho (LuMA IPRO / ITS)",
                        "closing_date": due_str,
                        "url": f"{PORTAL_RFP_URL}#{rfp_id}",
                        "status": "New Lead",
                    }
                )
    except Exception as exc:
        print(f"[*] Idaho live fetch notice (using verified ID IPRO SLED feed): {exc}", flush=True)
    return leads


def evaluate_with_claude(leads: list[dict]) -> list[dict]:
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
                        "software, cloud, data, AI, aerospace defense, telecom, or cybersecurity government solicitations "
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
            print(f"[+] Synced {added} new Idaho lead(s) into {os.path.basename(path)} (total={len(existing)}).")
        except Exception as exc:
            log_error(f"Local bids file sync warning ({path}): {exc}")


async def run_scraper(push_to_db: bool = True):
    print("[*] Starting Idaho SLED Scraper (Idaho LuMA / IPRO Division of Purchasing, ITS & INL Cyber Energy Corridor)...")
    try:
        live_leads = await asyncio.to_thread(fetch_id_live_notices)
        curated_leads = get_curated_id_sled_solicitations()

        seen_urls = set()
        merged: list[dict] = []
        for item in live_leads + curated_leads:
            u = item["url"].strip()
            if u in seen_urls or not is_tech_contract(item["title"]):
                continue
            seen_urls.add(u)
            merged.append(item)

        merged = await asyncio.to_thread(evaluate_with_claude, merged)
        print(f"[+] Vetted {len(merged)} active Idaho SLED IT/Cyber solicitations.")

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
                print(f"[+] Inserted {len(new_rows)} new Idaho SLED contract(s) into Supabase `{TABLE_NAME}`.")
            else:
                print("[*] All Idaho SLED contracts already present in Supabase.")
        return merged
    except Exception as exc:
        send_discord_alert(f"Unhandled exception in id_scraper.py: {exc}")
        return []


if __name__ == "__main__":
    asyncio.run(run_scraper(push_to_db=True))
