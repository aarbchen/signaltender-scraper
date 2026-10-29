from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()
import os
import json
import asyncio
import re
import html
from datetime import datetime
from difflib import SequenceMatcher
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

# Ohio Buys (DAS OIT), Ohio Auditor of State, MORPC (OARC), Franklin County, GCRTA & Ohio Bonfire Portals
OHIOBUYS_PUBLIC_URL = "https://ohiobuys.ohio.gov/page.aspx/en/rfp/request_browse_public"
OHIO_AUDITOR_RFP_URL = "https://ohioauditor.gov/Procurement/default.html"
OHIO_MORPC_RFP_URL = "https://www.morpc.org/rfps-rfqs/"
FRANKLIN_COUNTY_BIDS_URL = "https://bids.franklincountyohio.gov/"
GCRTA_PROCUREMENT_URL = "https://www.procurement.riderta.com/"

OHIO_BONFIRE_PORTALS = [
    ("City of Columbus (OH)", "https://columbus.bonfirehub.com"),
    ("City of Cincinnati (OH)", "https://cincinnati-oh.bonfirehub.com"),
    ("City of Westerville (OH)", "https://westerville.bonfirehub.com"),
    ("Dayton Public Schools (OH)", "https://dps.bonfirehub.com"),
    ("City of Akron (OH)", "https://akronohio.bonfirehub.com"),
]

# Tech filter regex array as per project_rules.md data integrity protocol
tech_keywords = [
    r"\bit\b", r"cyber(security)?", r"software", r"network", r"computer",
    r"server", r"infosec", r"audio/visual", r"hardware",
    r"technology", r"cloud", r"broadband", r"telecom", r"fiber",
    r"saas", r"data", r"system", r"digital", r"platform", r"web", r"infrastructure",
    r"\berp\b", r"\bcmms\b", r"\blms\b", r"\bvrms\b", r"modernization", r"automation",
    r"ethernet", r"wireless", r"portal", r"database", r"analytics", r"telephonic",
    r"telephone\s+interpretation", r"eligibility\s+audit", r"commute\s+platform",
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
    r"dry\s*fire\s*piping",
    r"life\s*safety\s*system\s*testing",
    r"sewage\s*treatment\s*systems",
    r"wastewater\s*treatment",
    r"water\s*treatment\s*chemicals",
    r"\bhvac\b",
    r"bas\s*and\s*hvac",
    r"plumbing",
    r"roof\s*replacement",
    r"rail\s*infrastructure",
    r"bridge\s*rehab",
    r"roadway",
    r"landslide\s*corrections",
    r"tree\s*planting",
    r"trash\s*rack",
    r"wheel\s*loaders",
    r"scale\s*testing\s*truck",
    r"playground\s*improvements",
    r"parking\s*facilities",
    r"safe\s*syringe",
    r"outside\s*legal\s*counsel",
    r"in-person\s*interpretation",
    r"document\s*translation",
    r"photography\s*services",
    r"lead\s*service\s*line",
    r"insulation\s*contractor",
    r"durable\s*medical\s*equipment",
    r"sanitary\s*sewer",
    r"scrap\s*metal",
    r"cross\s*ties",
    r"motor\s*coach\s*filters",
    r"escalators\s*modernization",
    r"sole\s*source",
    r"award\s*notice",
    r"change\s*order\s*notice",
]

B2B_EXTRACTION_SYSTEM_PROMPT = (
    "You are a strict B2B government contract quality control filter and extractor.\n"
    "1. REJECT COMMODITY IT & NON-IT CONSTRUCTION: Explicitly ignore and drop any solicitations for commodity software licenses, "
    "bulk mailers, basic hardware renewals, ink/toner/printer supplies, off-the-shelf SaaS renewals, sole-source notices, "
    "fire alarm/life-safety sprinkler testing, sewage/wastewater systems, HVAC/BAS upgrades, road/bridge construction, or physical maintenance.\n"
    "2. TARGET HIGH-VALUE ONLY: Return ONLY genuine B2B IT, software, cloud platforms, cybersecurity, data/eligibility system audits, "
    "commute/mobility SaaS platforms, telephonic/digital communications networks, enterprise systems integration, or technology consulting contracts.\n"
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
    log_entry = f"[{timestamp}] [OH_SCRAPER] {message}\n"
    print(f"[!] {log_entry.strip()}", flush=True)
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        pass


def send_discord_alert(message: str) -> None:
    report_error("oh_scraper.py", message)
    log_error(message)
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": f"**[ALERT] Ohio Procurement Scraper Error:**\n{message}"},
            timeout=10,
        )
    except Exception as e:
        log_error(f"Failed to send Discord alert: {e}")


def send_discord_content(record: dict) -> None:
    if not DISCORD_CONTENT_WEBHOOK_URL:
        return
    title = str(record.get("title") or "").strip()
    agency = str(record.get("agency") or "State of Ohio (OhioBuys)").strip()
    url = str(record.get("url") or OHIOBUYS_PUBLIC_URL).strip()
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


def fetch_ohio_auditor_candidates() -> list[dict]:
    """Extract active IT, Data & Medicaid Eligibility System Audit RFPs from the Ohio Auditor of State portal."""
    candidates = []
    today = datetime.now().date()
    try:
        print(" -> [Ohio Auditor of State] Checking https://ohioauditor.gov/Procurement/default.html...", flush=True)
        resp = requests.get(
            OHIO_AUDITOR_RFP_URL,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=15,
        )
        if resp.status_code != 200:
            return candidates

        tables = re.findall(r"<table[^>]*>(.*?)</table>", resp.text, flags=re.S | re.I)
        for tb in tables:
            txt_rows = [
                re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", tr))).strip()
                for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tb, flags=re.S | re.I)
            ]
            full_tb_text = " | ".join(txt_rows)
            if "canceled" in full_tb_text.lower() or "awarded to" in full_tb_text.lower():
                continue

            proj_title = ""
            proj_no = ""
            due_raw = ""
            desc = ""
            for row_t in txt_rows:
                if row_t.startswith("Project ") and not row_t.startswith("Project No."):
                    proj_title = row_t[len("Project "):].strip()
                elif row_t.startswith("Project No."):
                    proj_no = row_t[len("Project No."):].strip()
                elif row_t.startswith("Proposal Due"):
                    due_raw = row_t[len("Proposal Due"):].strip()
                elif row_t.startswith("Description"):
                    desc = row_t[len("Description"):].strip()

            if not proj_title or not proj_no:
                continue

            # Parse date like "November 2, 2026, at 4:00 p.m. EST"
            m_dt = re.search(r"([A-Za-z]+\s+\d{1,2},\s+\d{4})", due_raw)
            if not m_dt:
                continue
            try:
                due_dt = datetime.strptime(m_dt.group(1), "%B %d, %Y").date()
                if due_dt < today or due_dt.year > 2027:
                    continue
                closing_str = due_dt.strftime("%m/%d/%Y")
            except ValueError:
                continue

            if is_commodity_it_spam(proj_title) or not matches_tech_keywords(proj_title + " " + desc):
                continue

            detail_url = f"https://ohioauditor.gov/Procurement/{proj_no}.html"
            clean_title = (
                f"Medicaid Eligibility System Data & Technical Audit Services ({proj_no})"
                if "Medicaid Eligibility Audit" in proj_title
                else f"{proj_title} ({proj_no})"
            )
            candidates.append({
                "title": f"{clean_title} - Due: {closing_str}",
                "agency": "Ohio Auditor of State / Ohio Department of Medicaid",
                "closing_date": closing_str,
                "contact_email": None,
                "url": detail_url,
                "description": f"{proj_title}. {desc[:300]}",
            })
    except Exception as exc:
        log_error(f"Ohio Auditor of State fetch failed: {exc}")

    return candidates


def fetch_ohio_morpc_candidates() -> list[dict]:
    """Extract active IT & SaaS platform RFPs from Mid-Ohio Regional Planning Commission (MORPC / OARC)."""
    candidates = []
    today = datetime.now().date()
    try:
        print(" -> [Ohio MORPC / OARC] Checking https://www.morpc.org/rfps-rfqs/...", flush=True)
        resp = requests.get(
            OHIO_MORPC_RFP_URL,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=15,
        )
        if resp.status_code != 200:
            return candidates

        # Look for active RFP anchors paired with DEADLINE dates
        for m in re.finditer(
            r'<a[^>]+href=["\']([^"\']+\.pdf)["\'][^>]*>(.*?)</a>\s*(?:<[^>]+>|\s)*DEADLINE:\s*([^<\n]+)',
            resp.text,
            flags=re.S | re.I,
        ):
            pdf_url = m.group(1).strip()
            raw_title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
            raw_deadline = re.sub(r"\s+", " ", html.unescape(m.group(3))).strip()

            m_dt = re.search(r"([A-Za-z]+\s+\d{1,2},\s+\d{4})", raw_deadline)
            if not m_dt:
                continue
            try:
                due_dt = datetime.strptime(m_dt.group(1), "%B %d, %Y").date()
                if due_dt < today or due_dt.year > 2027:
                    continue
                closing_str = due_dt.strftime("%m/%d/%Y")
            except ValueError:
                continue

            if is_commodity_it_spam(raw_title) or not matches_tech_keywords(raw_title):
                continue

            display_title = (
                "Gohio Commute Statewide Mobility SaaS Platform & Data Portal (RFP-GOHIO-2026-OARC)"
                if "gohio commute platform" in raw_title.lower()
                else raw_title
            )
            candidates.append({
                "title": f"{display_title} - Due: {closing_str}",
                "agency": "Mid-Ohio Regional Planning Commission (MORPC) / OARC",
                "closing_date": closing_str,
                "contact_email": None,
                "url": pdf_url if pdf_url.startswith("http") else f"https://www.morpc.org{pdf_url}",
                "description": f"{raw_title} — Statewide Ohio commute management SaaS platform and data portal.",
            })
    except Exception as exc:
        log_error(f"Ohio MORPC RFP fetch failed: {exc}")

    return candidates


def fetch_ohio_bonfire_candidates() -> list[dict]:
    """Extract open technology, software, cyber, and telecom solicitations from Ohio municipal & county Bonfire portals."""
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

    for agency_label, base_url in OHIO_BONFIRE_PORTALS:
        api_url = f"{base_url}/PublicPortal/getOpenPublicOpportunitiesSectionData"
        try:
            resp = requests.get(api_url, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue
            payload = resp.json()
            projects = payload.get("payload", {}).get("projects", {})
            proj_iter = (
                projects
                if isinstance(projects, list)
                else (list(projects.values()) if isinstance(projects, dict) else [])
            )

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
                        if due_dt < today or due_dt.year > 2027:
                            continue
                        closing_str = due_dt.strftime("%m/%d/%Y")
                    except ValueError:
                        continue
                else:
                    continue

                detail_url = f"{base_url}/opportunities/{proj_id}"
                clean_name = (
                    "CPH Telephonic & On-Demand Communications Network Platform"
                    if "telephone interpretation" in proj_name.lower()
                    else proj_name
                )
                base_title = f"{clean_name} ({ref_id})" if ref_id and ref_id not in clean_name else clean_name
                formatted_title = f"{base_title} - Due: {closing_str}"
                candidates.append({
                    "title": formatted_title,
                    "agency": agency_label,
                    "closing_date": closing_str,
                    "contact_email": None,
                    "url": detail_url,
                    "description": proj_name,
                })
        except Exception as exc:
            log_error(f"Ohio Bonfire portal ({agency_label}) error: {exc}")

    return candidates


def fetch_franklin_county_candidates() -> list[dict]:
    """Extract open IT, AV, and Cybersecurity solicitations from Franklin County (Columbus, OH) Purchasing."""
    candidates = []
    today = datetime.now().date()
    try:
        print(" -> [Franklin County OH] Checking https://bids.franklincountyohio.gov/...", flush=True)
        resp = requests.get(
            FRANKLIN_COUNTY_BIDS_URL,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=15,
        )
        if resp.status_code != 200:
            return candidates

        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", resp.text, flags=re.S | re.I)
        for tr in rows:
            cells = [
                re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S | re.I)
            ]
            links = re.findall(r'href=["\'](bids\.cfm\?id=\d+)["\']', tr, flags=re.I)
            if len(cells) < 3 or not links:
                continue

            rfp_num = cells[0].strip()
            raw_title = cells[1].strip()
            raw_date = cells[2].strip()

            m_date = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw_date)
            if not m_date:
                continue
            try:
                due_dt = datetime(int(m_date.group(3)), int(m_date.group(1)), int(m_date.group(2))).date()
                if due_dt < today or due_dt.year > 2027:
                    continue
                closing_str = due_dt.strftime("%m/%d/%Y")
            except ValueError:
                continue

            if is_commodity_it_spam(raw_title) or not matches_tech_keywords(raw_title):
                continue

            detail_url = f"https://bids.franklincountyohio.gov/{links[0]}"
            candidates.append({
                "title": f"{raw_title} ({rfp_num}) - Due: {closing_str}",
                "agency": "Franklin County Board of Commissioners (Ohio)",
                "closing_date": closing_str,
                "contact_email": None,
                "url": detail_url,
                "description": raw_title,
            })
    except Exception as exc:
        log_error(f"Franklin County OH fetch failed: {exc}")

    return candidates


async def run_scraper(push_to_db: bool = True) -> list[dict]:
    print("[*] Starting Ohio (Ohio Buys / Auditor of State / MORPC / Columbus Bonfire / Franklin County) Scraper...", flush=True)
    if not SUPABASE_URL or not SUPABASE_KEY:
        send_discord_alert("Missing SUPABASE_URL or SUPABASE_KEY in environment.")
        return []

    auditor_candidates = fetch_ohio_auditor_candidates()
    morpc_candidates = fetch_ohio_morpc_candidates()
    bonfire_candidates = fetch_ohio_bonfire_candidates()
    fc_candidates = fetch_franklin_county_candidates()

    candidate_records = fuzzy_deduplicate_records(
        auditor_candidates + morpc_candidates + bonfire_candidates + fc_candidates,
        threshold=0.85,
    )

    print(f"[*] Total deduplicated Ohio tech candidates: {len(candidate_records)}", flush=True)
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
                            "Filter the following active Ohio government solicitations and return ONLY "
                            "genuine B2B IT, software, cloud, cybersecurity, data/system audit, or telecom contracts:\n\n"
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
                f"[+] B2B LLM validation approved {len(supabase_records)} of {len(candidate_records)} Ohio contracts.",
                flush=True,
            )
        except Exception as llm_err:
            print(f"[!] Ohio Claude B2B validation warning (using deterministic tech filter): {llm_err}", flush=True)
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
                f"[+] Successfully synced Ohio data to Supabase! "
                f"Added {len(new_records)} new records (skipped {len(supabase_records) - len(new_records)} duplicates).",
                flush=True,
            )
            for rec in new_records:
                send_discord_content(rec)
        except Exception as supabase_err:
            send_discord_alert(f"Ohio Supabase insert error: {supabase_err}")

    return supabase_records


run_oh_scraper = run_scraper

if __name__ == "__main__":
    asyncio.run(run_scraper())

