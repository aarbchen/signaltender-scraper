from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()
import os
import json
import asyncio
import random
import re
import time
import html
from datetime import datetime
from difflib import SequenceMatcher
import requests
from dotenv import load_dotenv
import anthropic
from supabase import create_client, Client
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

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
ERROR_SCREENSHOT_PATH = "error_debug.png"

# Decodo rotating residential proxy configuration (ports 10000 / 10001)
PROXY_HOST = os.getenv("DECODO_PROXY_HOST", "us.decodo.com")
PROXY_PORTS = ["10000", "10001"]
PROXY_USER = os.getenv("DECODO_PROXY_USER", "sphmb5n9of")
PROXY_PASS = os.getenv("DECODO_PROXY_PASS", "y7x~OwTiQim03Ooh4p")

# Illinois State (BidBuy) & Chicago / Cook County Public Procurement Portals
BIDBUY_SEARCH_URL = "https://www.bidbuy.illinois.gov/bso/view/search/external/advancedSearchBid.xhtml?openBids=true"
BIDBUY_AJAX_URL = "https://www.bidbuy.illinois.gov/bso/view/search/external/advancedSearchBid.xhtml"
ILLINOIS_BONFIRE_PORTALS = [
    ("Chicago Transit Authority (CTA)", "https://transitchicago.bonfirehub.com"),
    ("Cook County Government (IL)", "https://cookcountyil.bonfirehub.com"),
]

# Tech filter regex array as per project_rules.md data integrity protocol
tech_keywords = [
    r"\bit\b", r"cyber(security)?", r"software", r"network", r"computer",
    r"server", r"infosec", r"audio/visual", r"hardware",
    r"technology", r"cloud", r"broadband", r"telecom", r"fiber",
    r"saas", r"data", r"system", r"digital", r"platform", r"web", r"infrastructure",
    r"\berp\b", r"\bcmms\b", r"modernization", r"automation", r"ethernet", r"screening\s+tool",
]

# Commodity IT, non-bidding notices, & low-value renewal exclusions
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
    r"fire\s*pump",
    r"\bhvac\b",
    r"landfill\s*gas",
    r"farm\s*lease",
    r"change\s*order\s*notice",
    r"changeordernotice",
    r"award\s*notice",
    r"not\s*a\s*bidding",
    r"emergency\s*final\s*cost",
    r"emergency\s*notice",
    r"sole\s*source",
    r"sole\s*economically\s*feasible",
    r"adobe\s*licensing",
    r"lexmark\s*printers",
    r"snowplow",
    r"roadway\s*appurtenance",
    r"door\s*locks",
    r"enterprise\s*subscription",
    r"\belevators?\b",
    r"hardware\s*for\s*traffic",
]

B2B_EXTRACTION_SYSTEM_PROMPT = (
    "You are a strict B2B government contract quality control filter and extractor.\n"
    "1. REJECT COMMODITY IT & NON-COMPETITIVE NOTICES: Explicitly ignore and drop any solicitations for commodity software licenses, "
    "bulk mailers, basic hardware renewals, ink/toner/printer supplies, off-the-shelf SaaS renewals, sole-source notices, "
    "change order notices, emergency notices, or award notices.\n"
    "2. TARGET HIGH-VALUE ONLY: Return ONLY high-value, complex B2B IT contracts (e.g., custom software development, "
    "ERP/CMMS/automation systems, cloud migrations, cybersecurity architecture, network/telecom/Metro Ethernet/digital systems, "
    "data analytics & forecasting, enterprise systems integration, technical IT consulting).\n"
    "3. Strictly ignore unrelated non-IT contracts like HVAC, fire pumps, farm leases, construction, vehicles, or general municipal maintenance.\n"
    "Output strictly as a valid JSON array of objects with keys: title, closing_date, contact_email. "
    "Do not wrap in markdown code blocks or output any other text. "
    "If no high-value B2B IT contracts are found, output an empty array []."
)


def is_commodity_it_spam(title: str) -> bool:
    """Return True if the solicitation title matches commodity IT, sole-source/award notices, or basic renewal spam."""
    if not title:
        return True
    t_lower = title.lower()
    return any(re.search(pattern, t_lower) for pattern in commodity_it_exclusions)


def _normalize_title_for_similarity(title: str) -> str:
    """Strip trailing '- Due: MM/DD/YYYY' and normalize whitespace/case for fuzzy similarity comparison."""
    base = re.sub(r"\s*-\s*Due:\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$", "", str(title or ""), flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", base).strip().lower()


def fuzzy_deduplicate_records(records: list[dict], threshold: float = 0.85) -> list[dict]:
    """
    Programmatic check before Supabase insertion: drop records if the Title is more than
    85% similar (ratio > threshold) to a record already processed in the current batch,
    preventing catalog-dump spam.
    """
    deduped = []
    seen_titles = []
    dropped_count = 0

    for rec in records:
        raw_title = str(rec.get("title") or "").strip()
        norm_title = _normalize_title_for_similarity(raw_title)
        if not norm_title:
            continue

        is_near_duplicate = False
        for existing_norm, existing_raw in seen_titles:
            ratio_norm = SequenceMatcher(None, norm_title, existing_norm).ratio()
            ratio_raw = SequenceMatcher(None, raw_title.lower(), existing_raw).ratio()
            if ratio_norm > threshold or ratio_raw > threshold:
                is_near_duplicate = True
                dropped_count += 1
                break

        if not is_near_duplicate:
            deduped.append(rec)
            seen_titles.append((norm_title, raw_title.lower()))

    if dropped_count > 0:
        print(
            f"[*] Illinois Fuzzy Deduplication: Dropped {dropped_count} near-duplicate spam record(s) "
            f"(>{int(threshold * 100)}% title similarity).",
            flush=True,
        )

    return deduped


def send_discord_alert(message: str):
    if not DISCORD_WEBHOOK_URL:
        print("[!] Webhook URL not found in .env file.", flush=True)
        return
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": f"**[ALERT] Illinois Procurement Scraper Alert:**\n{message}"},
            timeout=10,
        )
        response.raise_for_status()
        print("[+] Discord alert sent successfully.", flush=True)
    except Exception as discord_err:
        print(f"[!] Failed to send Discord alert: {discord_err}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"Failed to send Discord alert: {discord_err}\n")
        except Exception:
            pass


def send_discord_content(record: dict):
    if not DISCORD_CONTENT_WEBHOOK_URL:
        print("[!] WARNING: DISCORD_CONTENT_WEBHOOK_URL not found in .env file.", flush=True)
        return
    try:
        import client_delivery
        message = client_delivery.format_lead_block(record)
    except Exception:
        title = record.get("title") or ""
        agency = record.get("agency") or ""
        closing_date = record.get("closing_date")
        link = record.get("url") or ""
        lines = [
            f"**Title:** {title}",
            f"**Agency:** {agency}",
        ]
        if closing_date:
            lines.append(f"**Closing Date:** {closing_date}")
        lines.append(f"**Link:** <{link}>")
        message = "\n".join(lines)

    try:
        response = requests.post(
            DISCORD_CONTENT_WEBHOOK_URL,
            json={"username": "SignalWire Pro", "content": message, "flags": 4},
            timeout=10,
        )
        if response.status_code == 429:
            retry_after = response.json().get("retry_after", 1.0)
            time.sleep(float(retry_after))
            response = requests.post(
                DISCORD_CONTENT_WEBHOOK_URL,
                json={"username": "SignalWire Pro", "content": message, "flags": 4},
                timeout=10,
            )
        response.raise_for_status()
        time.sleep(0.4)
    except Exception as e:
        error_msg = f"Failed to send Discord content webhook: {e}"
        print(f"[!] {error_msg}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n[!] {error_msg}\n")
        except Exception:
            pass
        send_discord_alert(error_msg)


def format_date_clean(date_str: str) -> str:
    """Normalize Illinois solicitation close dates ('MM/DD/YYYY HH:MM PM', 'YYYY-MM-DD HH:MM:SS') to MM/DD/YYYY."""
    if not date_str:
        return ""
    date_str = str(date_str).strip()
    if date_str.lower() in ["n/a", "tbd", "none", "null", "undefined", "tba", ""]:
        return ""

    if "T" in date_str:
        date_str = date_str.split("T")[0].strip()

    m_iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})", date_str)
    if m_iso:
        year, month, day = m_iso.groups()
        return f"{int(month):02d}/{int(day):02d}/{year}"

    m_slash = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", date_str)
    if m_slash:
        month, day, year = m_slash.groups()
        if len(year) == 2:
            year = "20" + year
        return f"{int(month):02d}/{int(day):02d}/{year}"

    cleaned_human = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", date_str)
    cleaned_human = cleaned_human.split(",")[0].strip()
    for fmt in ("%b %d %Y", "%B %d %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(cleaned_human, fmt)
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            pass

    return date_str


def format_title_and_due(raw_title: str, raw_date: str) -> tuple[str, str]:
    """
    Format contract title and closing date:
    - If a closing date is successfully extracted, append it cleanly (e.g., 'Title - Due: MM/DD/YYYY').
    - If a closing date cannot be found, drop the 'Due:' tag entirely. Never output 'N/A' or placeholder text.
    """
    if not raw_title or str(raw_title).strip().lower() in ["n/a", "none", "null", ""]:
        return "", ""
    clean_title = html.unescape(str(raw_title)).replace("\ufffd", "-").strip()
    clean_title = re.sub(r"\bWeb-\s+Based\b", "Web-Based", clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r"[\s\-\(]*Due:?\s*N/A\)?", "", clean_title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r"[\s\-]+$", "", clean_title).strip()
    clean_title = re.sub(r"\s{2,}", " ", clean_title).strip()

    clean_date = format_date_clean(raw_date)
    if clean_date:
        return f"{clean_title} - Due: {clean_date}", clean_date
    else:
        return clean_title, ""


def _parse_bidbuy_rows_from_html(html_text: str, captured_by_url: dict) -> int:
    """Parse table rows from Illinois BidBuy HTML or PrimeFaces partial-response XML."""
    added = 0
    trs = re.findall(r"<tr[^>]*>(.*?)</tr>", html_text, flags=re.S)
    for tr in trs:
        if "bidDetail" not in tr and "data-ri=" not in tr:
            continue
        tds = [
            html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", td)).strip())
            for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)
        ]
        if len(tds) < 8:
            continue
        bid_id = tds[0].strip()
        agency_raw = tds[2].strip()
        desc = tds[6].strip()
        due_raw = tds[7].strip()
        awarded_or_status = tds[8].strip() if len(tds) > 8 else ""

        if not bid_id or not desc:
            continue
        # Skip bids already in "Award in Process" or awarded to a vendor
        if awarded_or_status:
            continue

        agency_clean = (
            f"State of Illinois ({agency_raw})"
            if agency_raw and "illinois" not in agency_raw.lower()
            else (agency_raw or "State of Illinois (BidBuy)")
        )
        detail_url = (
            f"https://www.bidbuy.illinois.gov/bso/external/bidDetail.sda"
            f"?docId={bid_id}&external=true&parentUrl=close"
        )
        captured_by_url[detail_url] = {
            "title": desc,
            "bid_id": bid_id,
            "agency": agency_clean,
            "close_date": due_raw,
            "url": detail_url,
        }
        added += 1
    return added


def _scrape_bidbuy_http(captured_by_url: dict) -> int:
    """Fast HTTP + PrimeFaces AJAX session scraper for Illinois BidBuy (openBids=true)."""
    total_added = 0
    try:
        sess = requests.Session()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        resp = sess.get(BIDBUY_SEARCH_URL, headers=headers, timeout=18)
        if resp.status_code != 200:
            return 0

        total_added += _parse_bidbuy_rows_from_html(resp.text, captured_by_url)

        form_m = re.search(r'<form id="bidSearchResultsForm".*?</form>', resp.text, flags=re.S)
        if not form_m:
            return total_added

        form_html = form_m.group(0)
        vs_m = re.search(r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"', form_html)
        csrf_m = re.search(r'name="_csrf"[^>]*value="([^"]+)"', form_html)
        if not vs_m or not csrf_m:
            return total_added

        view_state = vs_m.group(1)
        csrf_token = csrf_m.group(1)

        # Determine total records from paginator (e.g. '1-25 of 187')
        total_records = 200
        pag_m = re.search(r"of\s+(\d+)", resp.text)
        if pag_m:
            total_records = min(int(pag_m.group(1)), 300)

        ajax_headers = {
            **headers,
            "Faces-Request": "partial/ajax",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": BIDBUY_SEARCH_URL,
        }

        for offset in range(25, total_records, 25):
            payload = {
                "javax.faces.partial.ajax": "true",
                "javax.faces.source": "bidSearchResultsForm:bidResultId",
                "javax.faces.partial.execute": "bidSearchResultsForm:bidResultId",
                "javax.faces.partial.render": "bidSearchResultsForm:bidResultId",
                "bidSearchResultsForm:bidResultId": "bidSearchResultsForm:bidResultId",
                "bidSearchResultsForm:bidResultId_pagination": "true",
                "bidSearchResultsForm:bidResultId_first": str(offset),
                "bidSearchResultsForm:bidResultId_rows": "25",
                "bidSearchResultsForm:bidResultId_encodeFeature": "true",
                "bidSearchResultsForm": "bidSearchResultsForm",
                "openBids": "true",
                "_csrf": csrf_token,
                "javax.faces.ViewState": view_state,
            }
            page_resp = sess.post(BIDBUY_AJAX_URL, data=payload, headers=ajax_headers, timeout=15)
            if page_resp.status_code != 200:
                break
            rows_added = _parse_bidbuy_rows_from_html(page_resp.text, captured_by_url)
            total_added += rows_added
            if rows_added == 0:
                break
    except Exception as e:
        print(f"[!] Illinois BidBuy HTTP pagination warning: {e}", flush=True)

    return total_added


def _scrape_bonfire_http(agency_name: str, base_url: str, captured_by_url: dict) -> int:
    """Extract open solicitations from an Illinois Bonfire portal via JSON endpoint."""
    api_url = f"{base_url}/PublicPortal/getOpenPublicOpportunitiesSectionData"
    extracted = 0
    try:
        resp = requests.get(
            api_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
            },
            timeout=12,
        )
        if resp.status_code == 200:
            data = resp.json()
            projects = data.get("payload", {}).get("projects", {})
            if isinstance(projects, dict):
                for proj_id, proj in projects.items():
                    if not isinstance(proj, dict):
                        continue
                    pid = str(proj.get("ProjectID") or proj_id).strip()
                    ref_id = str(proj.get("ReferenceID") or "").strip()
                    proj_name = str(proj.get("ProjectName") or "").strip()
                    close_date = str(proj.get("DateClose") or "").strip()
                    if pid and proj_name:
                        detail_url = f"{base_url}/opportunities/{pid}"
                        captured_by_url[detail_url] = {
                            "title": proj_name,
                            "bid_id": ref_id,
                            "agency": agency_name,
                            "close_date": close_date,
                            "url": detail_url,
                        }
                        extracted += 1
    except Exception:
        pass
    print(f"[*] Illinois Portal ({agency_name}): Extracted {extracted} open solicitation(s).", flush=True)
    return extracted


async def _scrape_bidbuy_playwright_fallback(captured_by_url: dict):
    """Fallback to Playwright Stealth if direct HTTP to Illinois BidBuy returned 0 rows."""
    selected_port = random.choice(PROXY_PORTS)
    proxy_config = {
        "server": f"http://{PROXY_HOST}:{selected_port}",
        "username": PROXY_USER,
        "password": PROXY_PASS,
        "bypass": "*.gov,*.illinois.gov,*.bonfirehub.com,*.google.com,*.gstatic.com",
    }
    async with Stealth().use_async(async_playwright()) as p:
        browser = None
        page = None
        try:
            print("[*] Launching Stealth browser fallback for Illinois BidBuy...", flush=True)
            browser = await p.chromium.launch(
                headless=True,
                proxy=proxy_config,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--renderer-process-limit=1",
                    "--js-flags=--max-old-space-size=128",
                ],
                ignore_default_args=["--enable-automation"],
            )
            context = await browser.new_context(viewport={"width": 1024, "height": 600})
            page = await context.new_page()
            await page.goto(BIDBUY_SEARCH_URL, wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(2.0)
            content = await page.content()
            _parse_bidbuy_rows_from_html(content, captured_by_url)
        except PlaywrightTimeoutError as te:
            err_msg = f"Illinois Scraper Playwright TimeoutError: {te}"
            print(f"[!] {err_msg}", flush=True)
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {err_msg}\n")
            except Exception:
                pass
            send_discord_alert(err_msg)
        except Exception as e:
            err_msg = f"Illinois Scraper Playwright Error: {e}"
            print(f"[!] {err_msg}", flush=True)
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {err_msg}\n")
            except Exception:
                pass
            send_discord_alert(err_msg)
        finally:
            if browser:
                await browser.close()


async def run_scraper(push_to_db: bool = True) -> list[dict]:
    import gc

    supabase_records = []
    if push_to_db and (not SUPABASE_URL or not SUPABASE_KEY):
        print("[!] ERROR: SUPABASE_URL or SUPABASE_KEY not found in .env", flush=True)
        return supabase_records

    captured_bids_by_url = {}

    try:
        print("[*] Querying Illinois BidBuy (bidbuy.illinois.gov) open solicitations...", flush=True)
        bidbuy_count = await asyncio.to_thread(_scrape_bidbuy_http, captured_bids_by_url)
        print(f"[*] Illinois BidBuy (eProcurement): Extracted {bidbuy_count} active open bid(s).", flush=True)

        if bidbuy_count == 0:
            await _scrape_bidbuy_playwright_fallback(captured_bids_by_url)

        for agency_name, base_url in ILLINOIS_BONFIRE_PORTALS:
            await asyncio.to_thread(_scrape_bonfire_http, agency_name, base_url, captured_bids_by_url)
    except Exception as e:
        error_msg = f"Illinois Scraper Error during extraction: {e}"
        print(f"[!] {error_msg}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n[!] {error_msg}\n")
        except Exception:
            pass
        send_discord_alert(error_msg)

    gc.collect()

    print(
        f"[*] Illinois SLED: Captured {len(captured_bids_by_url)} unique open solicitations. "
        "Applying tech regex and B2B quality filters...",
        flush=True,
    )

    candidate_records = []
    for detail_url, bid in captured_bids_by_url.items():
        raw_title = str(bid.get("title") or "").strip()
        if not raw_title or is_commodity_it_spam(raw_title):
            continue

        title_lower = raw_title.lower()
        if any(re.search(pattern, title_lower) for pattern in tech_keywords):
            bid_id = str(bid.get("bid_id") or "").strip()
            display_title = (
                raw_title
                if not bid_id or bid_id.lower() in title_lower
                else f"[{bid_id}] {raw_title}"
            )
            formatted_title, clean_due = format_title_and_due(display_title, str(bid.get("close_date") or ""))
            if not formatted_title or is_commodity_it_spam(formatted_title):
                continue

            candidate_records.append(
                {
                    "title": formatted_title,
                    "agency": str(bid.get("agency") or "State of Illinois (BidBuy)").strip(),
                    "closing_date": clean_due if clean_due else None,
                    "url": detail_url,
                    "status": "New Lead",
                }
            )

    # Validate candidates through Anthropic B2B quality control prompt if configured
    if candidate_records and client:
        try:
            print(
                f"[*] Validating {len(candidate_records)} Illinois candidates via Anthropic B2B quality filter...",
                flush=True,
            )
            snippet = json.dumps(
                [
                    {
                        "title": r["title"],
                        "closing_date": r["closing_date"] or "",
                        "contact_email": "",
                    }
                    for r in candidate_records
                ]
            )
            llm_resp = await client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
                max_tokens=8000,
                system=B2B_EXTRACTION_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Filter and return ONLY high-value B2B IT contracts from this candidate list:\n\n{snippet}",
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
                    r
                    for r in candidate_records
                    if _normalize_title_for_similarity(r["title"]) in approved_norms
                ]
            else:
                supabase_records = candidate_records
            print(
                f"[+] B2B LLM validation approved {len(supabase_records)} of {len(candidate_records)} Illinois contracts.",
                flush=True,
            )
        except Exception as llm_err:
            err_msg = f"Illinois Claude B2B validation warning (using deterministic tech filter): {llm_err}"
            print(f"[!] {err_msg}", flush=True)
            supabase_records = candidate_records
    else:
        supabase_records = candidate_records

    # Exact URL deduplication + 85% fuzzy title deduplication
    supabase_records = list({r["url"]: r for r in supabase_records}.values())
    supabase_records = fuzzy_deduplicate_records(supabase_records, threshold=0.85)

    if push_to_db:
        if supabase_records:
            print(
                f"[*] Pushing {len(supabase_records)} tech-verified Illinois records to Supabase -> {TABLE_NAME}...",
                flush=True,
            )
            try:
                db_client = supabase or create_client(SUPABASE_URL, SUPABASE_KEY)
                existing_resp = db_client.table(TABLE_NAME).select("title, url").execute()
                existing_rows = existing_resp.data if existing_resp and getattr(existing_resp, "data", None) else []
                existing_norms = [_normalize_title_for_similarity(r.get("title", "")) for r in existing_rows if r.get("title")]
                filtered_to_insert = []
                for rec in supabase_records:
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
                skipped_count = len(supabase_records) - len(new_records)
                print(
                    f"[+] Successfully synced Illinois data to Supabase! "
                    f"Added {len(new_records)} new records (skipped {skipped_count} duplicates).",
                    flush=True,
                )

                for rec in new_records:
                    send_discord_content(rec)
            except Exception as supabase_err:
                err_msg = f"Illinois Supabase insert error: {supabase_err}"
                print(f"[!] {err_msg}", flush=True)
                try:
                    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                        f.write(f"\n[!] {err_msg}\n")
                except Exception:
                    pass
                send_discord_alert(err_msg)
        else:
            print("[!] No valid Illinois tech records found to push from this run.", flush=True)
    else:
        print(
            f"[+] Illinois SLED extraction complete: {len(supabase_records)} tech contracts ready for master orchestrator.",
            flush=True,
        )

    return supabase_records


if __name__ == "__main__":
    asyncio.run(run_scraper())
