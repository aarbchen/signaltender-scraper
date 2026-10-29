from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()
import os
import json
import asyncio
import re
import html
from datetime import datetime
from difflib import SequenceMatcher
from urllib.parse import quote
import requests
from dotenv import load_dotenv
import anthropic
from supabase import create_client, Client

# Load environment variables
load_dotenv(dotenv_path=".env")
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DISCORD_CONTENT_WEBHOOK_URL = os.getenv("DISCORD_CONTENT_WEBHOOK_URL")

# Supabase & Anthropic Configuration
TABLE_NAME = "contracts"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY")) if os.getenv("ANTHROPIC_API_KEY") else None
ERROR_LOG_PATH = "error_log.txt"

# Pennsylvania DGS eMarketplace, PA JAGGAER SciQuest & PA Bonfire Public Portals
PA_EMARKETPLACE_SEARCH_URL = "https://www.emarketplace.state.pa.us/Search.aspx"
PA_EMARKETPLACE_DETAIL_BASE = "https://www.emarketplace.state.pa.us/Solicitations.aspx?SID="
PA_JAGGAER_URL = "https://bids.sciquest.com/apps/Router/PublicEvent?CustomerOrg=CommonwealthPA"
PA_BONFIRE_PORTALS = [
    ("Philadelphia Regional Port Authority (PhilaPort)", "https://philaport.bonfirehub.com"),
]

# Tech filter regex array as per project_rules.md data integrity protocol
tech_keywords = [
    r"\bit\b", r"cyber(security)?", r"software", r"network", r"computer",
    r"server", r"infosec", r"audio/visual", r"hardware",
    r"technology", r"cloud", r"broadband", r"telecom", r"fiber",
    r"saas", r"data", r"system", r"digital", r"platform", r"web", r"infrastructure",
    r"\berp\b", r"\bcmms\b", r"\blms\b", r"\bvrms\b", r"modernization", r"automation",
    r"ethernet", r"wireless", r"portal", r"database", r"analytics", r"telephonic",
]

# Commodity IT, non-bidding notices, construction, & low-value renewal exclusions
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
    r"fire\s*alarm\s*system",
    r"fire\s*system",
    r"fire\s*pump",
    r"\bhvac\b",
    r"plumbing",
    r"roof\s*replacement",
    r"rail\s*infrastructure",
    r"bridge\s*rehab",
    r"pvc\s*pipe",
    r"deer\s*fence",
    r"snow\s*removal",
    r"salting\s*services",
    r"electronic\s*waste",
    r"e-waste",
    r"recycling\s*services",
    r"modular\s*display",
    r"bakery\s*cafe",
    r"dining\s*hall",
    r"fitness\s*equipment",
    r"medical\s*incontinent",
    r"tattoo\s*artist",
    r"avian\s*flu",
    r"lead\s*service\s*lines",
    r"medium\s*voltage",
    r"cms\s*renovations",
    r"facilities\s*planning",
    r"change\s*order\s*notice",
    r"award\s*notice",
    r"not\s*a\s*bidding",
    r"emergency\s*final\s*cost",
    r"emergency\s*notice",
    r"sole\s*source",
    r"sole\s*economically\s*feasible",
    r"adobe\s*licensing",
    r"lexmark\s*printers",
]

B2B_EXTRACTION_SYSTEM_PROMPT = (
    "You are a strict B2B government contract quality control filter and extractor.\n"
    "1. REJECT COMMODITY IT & NON-COMPETITIVE NOTICES: Explicitly ignore and drop any solicitations for commodity software licenses, "
    "bulk mailers, basic hardware renewals, ink/toner/printer supplies, off-the-shelf SaaS renewals, sole-source notices, "
    "change order notices, e-waste recycling, or physical building/rail/HVAC/electrical construction.\n"
    "2. TARGET HIGH-VALUE ONLY: Return ONLY high-value, complex B2B IT, software, cloud, cybersecurity, data analytics, "
    "records/learning management systems (VRMS/LMS), managed IT services, network/wireless infrastructure, digital development, "
    "or technology consulting contracts.\n"
    "3. Strictly ignore unrelated non-IT contracts like HVAC, plumbing, roofing, rail track repair, snow removal, or general maintenance.\n"
    "Output strictly as a valid JSON array of objects with keys: title, closing_date, contact_email. "
    "Do not wrap in markdown code blocks or output any other text. "
    "If no high-value B2B IT contracts are found, output an empty array []."
)


def is_commodity_it_spam(title: str) -> bool:
    if not title:
        return True
    t_lower = title.lower()
    return any(re.search(pattern, t_lower) for pattern in commodity_it_exclusions)


def log_error(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [PA_SCRAPER] {message}\n"
    print(f"[!] {log_entry.strip()}", flush=True)
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        pass


def send_discord_alert(message: str) -> None:
    """Silently record runtime error to telemetry for autonomous self-healing (resolved-only Discord policy)."""
    report_error("pa_scraper.py", str(message))
    log_error(str(message))


def send_discord_content(record: dict) -> None:
    if not DISCORD_CONTENT_WEBHOOK_URL:
        return
    title = str(record.get("title") or "").strip()
    agency = str(record.get("agency") or "Commonwealth of Pennsylvania").strip()
    url = str(record.get("url") or PA_EMARKETPLACE_SEARCH_URL).strip()
    clean_title = title.split(" - Due:")[0].strip() if " - Due:" in title else title
    message = (
        f"**[GOVCON LEAD] New B2B GovCon Lead Detected!**\n"
        f"**Agency:** {agency}\n"
        f"**Title:** {clean_title}\n"
        f"**Link:** <{url}>\n\n"
        f"*Want all daily filtered IT & Cybersecurity RFPs delivered automatically? Check out the pinned link to subscribe!*"
    )
    try:
        requests.post(
            DISCORD_CONTENT_WEBHOOK_URL,
            json={"content": message, "flags": 4},
            timeout=10,
        )
    except Exception as e:
        log_error(f"Failed to post daily teaser to Discord: {e}")


def matches_tech_keywords(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in tech_keywords)


def _normalize_title_for_similarity(title: str) -> str:
    if not title:
        return ""
    base = re.sub(r"\s*-\s*Due:.*$", "", title, flags=re.IGNORECASE)
    base = re.sub(r"^\[[A-Z]{2}\]\s*", "", base, flags=re.IGNORECASE)
    base = re.sub(r"\([A-Z0-9\-\s_./]+\)\s*$", "", base)
    base = re.sub(r"[^a-z0-9]+", " ", base.lower()).strip()
    return base


def fuzzy_deduplicate_records(records: list[dict], threshold: float = 0.85) -> list[dict]:
    deduped = []
    seen_norms = []
    for rec in records:
        norm = _normalize_title_for_similarity(rec.get("title", ""))
        if not norm:
            continue
        if any(SequenceMatcher(None, norm, s).ratio() >= threshold for s in seen_norms):
            continue
        seen_norms.append(norm)
        deduped.append(rec)
    return deduped


def format_pa_agency(raw_agency: str) -> str:
    cleaned = re.sub(r'\s*"prior DPW"\s*', "", str(raw_agency or "")).strip()
    if not cleaned or cleaned.lower() == "all using agencies":
        return "Commonwealth of Pennsylvania (DGS Statewide)"
    if cleaned.lower().startswith("pa ") or "pennsylvania" in cleaned.lower() or "philadelphia" in cleaned.lower():
        return cleaned
    return f"PA {cleaned}"


def clean_pa_title(raw_title: str) -> str:
    t = re.sub(r"\s+", " ", str(raw_title or "")).strip()
    acronyms = {
        r"\bRfp\b": "RFP",
        r"\bRfi\b": "RFI",
        r"\bIfb\b": "IFB",
        r"\bItq\b": "ITQ",
        r"\bIt\b": "IT",
        r"\bPa\b": "PA",
        r"\bDhs\b": "DHS",
        r"\bDoc\b": "DOC",
        r"\bDoh\b": "DOH",
        r"\bDor\b": "DOR",
        r"\bOim\b": "OIM",
        r"\bBoo\b": "BOO",
        r"\bVrms\b": "VRMS",
        r"\bLms\b": "LMS",
        r"\bCms\b": "CMS",
        r"\bGis\b": "GIS",
        r"\bSaas\b": "SaaS",
    }
    for pat, repl in acronyms.items():
        t = re.sub(pat, repl, t)
    return t


def fetch_pa_jaggaer_email_map() -> dict[str, str]:
    email_map: dict[str, str] = {}
    try:
        r = requests.get(
            PA_JAGGAER_URL,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=15,
        )
        if r.status_code != 200:
            return email_map
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, flags=re.S | re.I)
        for tr in rows:
            txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", tr))).strip()
            m_num = re.search(r"Number\s+([A-Za-z0-9\-_]+)", txt)
            m_em = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", txt)
            if m_num and m_em:
                email_map[m_num.group(1).strip().upper()] = m_em.group(1).strip().lower()
    except Exception as exc:
        log_error(f"PA JAGGAER email map warning: {exc}")
    return email_map


def fetch_pa_emarketplace_candidates() -> list[dict]:
    candidates = []
    today = datetime.now().date()
    jaggaer_emails = fetch_pa_jaggaer_email_map()

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    try:
        print(" -> [PA eMarketplace] Fetching Search.aspx initial ViewState...", flush=True)
        r1 = session.get(PA_EMARKETPLACE_SEARCH_URL, timeout=25)
        r1.raise_for_status()

        form_data = {}
        for m in re.finditer(r'<input[^>]*type=["\']hidden["\'][^>]*>', r1.text, flags=re.I):
            tag = m.group(0)
            nm = re.search(r'name=["\']([^"\']+)["\']', tag, flags=re.I)
            vl = re.search(r'value=["\']([^"\']*)["\']', tag, flags=re.I)
            if nm:
                form_data[nm.group(1)] = html.unescape(vl.group(1)) if vl else ""

        form_data["__EVENTTARGET"] = "ctl00$MainBody$ddlRows"
        form_data["__EVENTARGUMENT"] = ""
        form_data["ctl00$MainBody$ddlRows"] = "32767"
        form_data["ctl00$MainBody$rblType"] = "rblCurrent"

        print(" -> [PA eMarketplace] Querying all active PA solicitations (ddlRows=32767)...", flush=True)
        r2 = session.post(PA_EMARKETPLACE_SEARCH_URL, data=form_data, timeout=35)
        r2.raise_for_status()

        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", r2.text, flags=re.S | re.I)
        seen_sids = set()

        for tr in rows:
            if "Solicitations.aspx?SID=" not in tr:
                continue
            cells = [
                re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S | re.I)
            ]
            if len(cells) < 11:
                continue

            sid = cells[0].strip()
            raw_title = clean_pa_title(cells[2].strip())
            desc = cells[3].strip()
            raw_agency = cells[4].strip()
            raw_due = cells[8].strip()
            status = cells[10].strip()
            contact_person = cells[11].strip() if len(cells) > 11 else ""

            if not sid or sid in seen_sids:
                continue
            seen_sids.add(sid)

            # Stage 1A: Active status check
            if status.lower() not in ("open", "active", "posted", "published", "extended"):
                continue

            # Stage 1B: Parse due date and filter out past deadlines or 2099/9999 open-enrollment catalogs
            m_date = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw_due)
            if not m_date:
                continue
            try:
                due_dt = datetime(int(m_date.group(3)), int(m_date.group(1)), int(m_date.group(2))).date()
                if due_dt < today or due_dt.year > 2027:
                    continue
                closing_str = due_dt.strftime("%m/%d/%Y")
            except ValueError:
                continue

            # Stage 2: Reject commodity IT, construction, snow removal, or sole-source spam
            if is_commodity_it_spam(raw_title) or is_commodity_it_spam(desc[:180]):
                continue

            # Stage 3: Must match tech_keywords in title
            if not matches_tech_keywords(raw_title):
                continue

            agency = format_pa_agency(raw_agency)
            source_url = f"{PA_EMARKETPLACE_DETAIL_BASE}{quote(sid)}"
            contact_email = jaggaer_emails.get(sid.upper(), "") or contact_person
            formatted_title = f"{raw_title} ({sid}) - Due: {closing_str}"

            candidates.append({
                "title": formatted_title,
                "agency": agency,
                "closing_date": closing_str,
                "contact_email": contact_email or None,
                "url": source_url,
                "description": desc[:380],
            })

        print(f" -> [PA eMarketplace] Found {len(candidates)} active tech candidate(s).", flush=True)
    except Exception as exc:
        log_error(f"PA eMarketplace fetch failed: {exc}")

    return candidates


def fetch_pa_bonfire_candidates() -> list[dict]:
    candidates = []
    today = datetime.now().date()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }

    for agency_label, base_url in PA_BONFIRE_PORTALS:
        api_url = f"{base_url}/PublicPortal/getOpenPublicOpportunitiesSectionData"
        try:
            resp = requests.get(api_url, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue
            payload = resp.json()
            projects = payload.get("payload", {}).get("projects", {})
            proj_iter = projects if isinstance(projects, list) else (list(projects.values()) if isinstance(projects, dict) else [])

            for p in proj_iter:
                if not isinstance(p, dict):
                    continue
                proj_id = str(p.get("ProjectID") or "").strip()
                ref_id = str(p.get("ReferenceID") or "").strip()
                proj_name = str(p.get("ProjectName") or "").strip()
                close_raw = str(p.get("DateClose") or "").strip()
                if not proj_name or not proj_id:
                    continue

                if is_commodity_it_spam(proj_name) or not matches_tech_keywords(proj_name):
                    continue

                closing_str = "N/A"
                if close_raw:
                    date_token = close_raw.split(" ")[0].strip()
                    try:
                        due_dt = datetime.strptime(date_token, "%Y-%m-%d").date()
                        if due_dt < today:
                            continue
                        closing_str = due_dt.strftime("%m/%d/%Y")
                    except ValueError:
                        closing_str = date_token

                detail_url = f"{base_url}/opportunities/{proj_id}"
                base_title = f"{proj_name} ({ref_id})" if ref_id and ref_id not in proj_name else proj_name
                formatted_title = f"{base_title} - Due: {closing_str}" if closing_str != "N/A" else base_title
                candidates.append({
                    "title": formatted_title,
                    "agency": agency_label,
                    "closing_date": closing_str,
                    "contact_email": None,
                    "url": detail_url,
                    "description": proj_name,
                })
        except Exception as exc:
            log_error(f"PA Bonfire portal ({agency_label}) error: {exc}")

    return candidates


async def run_scraper(push_to_db: bool = True) -> list[dict]:
    print("[*] Starting Pennsylvania (PA DGS eMarketplace + PA JAGGAER + PhilaPort) Scraper...", flush=True)
    if not SUPABASE_URL or not SUPABASE_KEY:
        send_discord_alert("Missing SUPABASE_URL or SUPABASE_KEY in environment.")
        return []

    pa_candidates = fetch_pa_emarketplace_candidates()
    bonfire_candidates = fetch_pa_bonfire_candidates()
    candidate_records = fuzzy_deduplicate_records(pa_candidates + bonfire_candidates, threshold=0.85)

    print(f"[*] Total deduplicated Pennsylvania tech candidates: {len(candidate_records)}", flush=True)
    if not candidate_records:
        return []

    # Stage 4: Anthropic Claude B2B Quality Validation
    supabase_records = []
    if client:
        try:
            prompt_lines = [
                f"- Title: {r['title']} | Agency: {r['agency']} | Scope: {r.get('description', '')}"
                for r in candidate_records
            ]
            llm_resp = await client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
                max_tokens=2048,
                system=B2B_EXTRACTION_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Filter the following active Pennsylvania eMarketplace solicitations and return ONLY "
                            "genuine B2B IT, software, cloud, cybersecurity, data analytics, or telecom contracts:\n\n"
                            + "\n".join(prompt_lines)
                        ),
                    }
                ],
            )
            raw_json_str = ""
            for block in llm_resp.content:
                if block.type == "text":
                    raw_json_str = block.text.strip()
                    break
            if raw_json_str.startswith("```"):
                raw_json_str = raw_json_str.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            approved = json.loads(raw_json_str)
            approved_norms = {
                _normalize_title_for_similarity(a.get("title", ""))
                for a in approved
                if a.get("title")
            }
            if approved_norms:
                supabase_records = [
                    {"title": r["title"], "agency": r["agency"], "closing_date": r.get("closing_date"), "url": r["url"], "status": "New Lead"}
                    for r in candidate_records
                    if _normalize_title_for_similarity(r["title"]) in approved_norms
                ]
            else:
                supabase_records = [
                    {"title": r["title"], "agency": r["agency"], "closing_date": r.get("closing_date"), "url": r["url"], "status": "New Lead"}
                    for r in candidate_records
                ]
            print(
                f"[+] B2B LLM validation approved {len(supabase_records)} of {len(candidate_records)} Pennsylvania contracts.",
                flush=True,
            )
        except Exception as llm_err:
            print(f"[!] Pennsylvania Claude B2B validation warning (using deterministic tech filter): {llm_err}", flush=True)
            supabase_records = [
                {"title": r["title"], "agency": r["agency"], "closing_date": r.get("closing_date"), "url": r["url"], "status": "New Lead"}
                for r in candidate_records
            ]
    else:
        supabase_records = [
            {"title": r["title"], "agency": r["agency"], "closing_date": r.get("closing_date"), "url": r["url"], "status": "New Lead"}
            for r in candidate_records
        ]

    # Stage 5: Exact URL deduplication + 85% fuzzy title deduplication
    supabase_records = list({r["url"]: r for r in supabase_records}.values())
    supabase_records = fuzzy_deduplicate_records(supabase_records, threshold=0.85)

    if push_to_db and supabase_records:
        try:
            db_client = supabase or create_client(SUPABASE_URL, SUPABASE_KEY)
            existing_resp = db_client.table(TABLE_NAME).select("title, url").execute()
            existing_rows = existing_resp.data if existing_resp and getattr(existing_resp, "data", None) else []
            existing_norms = [_normalize_title_for_similarity(r.get("title", "")) for r in existing_rows if r.get("title")]
            existing_urls = {str(r.get("url") or "").strip() for r in existing_rows if r.get("url")}

            filtered_to_insert = []
            for rec in supabase_records:
                if rec["url"] in existing_urls:
                    continue
                norm_t = _normalize_title_for_similarity(rec.get("title", ""))
                if any(SequenceMatcher(None, norm_t, ex_n).ratio() > 0.85 for ex_n in existing_norms):
                    continue
                filtered_to_insert.append(rec)

            new_records = []
            if filtered_to_insert:
                _existing = db_client.table(TABLE_NAME).select('url').execute()
                _existing_urls = {r.get('url') for r in (_existing.data or []) if r.get('url')}
                _net_new = [r for r in filtered_to_insert if r.get('url') not in _existing_urls]
                response = db_client.table(TABLE_NAME).insert(_net_new).execute() if _net_new else type('Obj', (), {'data': []})()
                new_records = response.data if response and getattr(response, "data", None) else []
            print(
                f"[+] Successfully synced Pennsylvania data to Supabase! "
                f"Added {len(new_records)} new records (skipped {len(supabase_records) - len(new_records)} duplicates).",
                flush=True,
            )
            for rec in new_records:
                send_discord_content(rec)
        except Exception as supabase_err:
            send_discord_alert(f"Pennsylvania Supabase insert error: {supabase_err}")

    return supabase_records


run_pa_scraper = run_scraper

if __name__ == "__main__":
    asyncio.run(run_scraper())
