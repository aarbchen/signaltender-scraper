import os
import json
import asyncio
import random
import re
import time
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

# Maryland eMMA & State/County Public Procurement Portals
EMMA_TARGET_URL = "https://emma.maryland.gov/page.aspx/en/rfp/request_browse_public"
MARYLAND_BONFIRE_PORTALS = [
    ("Maryland Judiciary (AOC)", "https://mdcourts.bonfirehub.com"),
    ("Maryland Environmental Service (MES)", "https://menv.bonfirehub.com"),
    ("Maryland Stadium Authority (MSA)", "https://mdstad.bonfirehub.com"),
    ("Housing Authority of Prince George's County (HAPGC)", "https://hapgcprocurement.bonfirehub.com"),
    ("Howard County Public School System (HCPSS)", "https://hcpss.bonfirehub.com"),
]

# Tech filter regex array as per project_rules.md data integrity protocol
tech_keywords = [
    r"\bit\b", r"cyber(security)?", r"software", r"network", r"computer",
    r"server", r"infosec", r"audio/visual", r"hardware",
    r"technology", r"cloud", r"broadband", r"telecom", r"fiber",
    r"saas", r"data", r"system", r"digital", r"platform", r"web", r"infrastructure"
]

# Commodity IT & low-value renewal exclusions
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
    r"\bhvac\b",
    r"landfill\s*gas",
]

B2B_EXTRACTION_SYSTEM_PROMPT = (
    "You are a strict B2B government contract quality control filter and extractor.\n"
    "1. REJECT COMMODITY IT: Explicitly ignore and drop any solicitations for commodity software licenses, "
    "bulk mailers (e.g., Bulk Mailer, Mail Manager, postage/mailing software renewals), basic hardware renewals, "
    "ink/toner/printer supplies, and off-the-shelf SaaS renewals or seat/subscription/maintenance renewals.\n"
    "2. TARGET HIGH-VALUE ONLY: Return ONLY high-value, complex B2B IT contracts (e.g., custom software development, "
    "cloud migrations, cybersecurity architecture, network/telecom/intercom/security systems, data center operations, "
    "enterprise systems integration, technical IT consulting).\n"
    "3. Strictly ignore unrelated non-IT contracts like HVAC, plumbing, construction, landfill gas piping, "
    "fire/smoke alarm maintenance, transit, or general municipal services.\n"
    "Output strictly as a valid JSON array of objects with keys: title, closing_date, contact_email. "
    "Do not wrap in markdown code blocks or output any other text. "
    "If no high-value B2B IT contracts are found, output an empty array []."
)


def is_commodity_it_spam(title: str) -> bool:
    """Return True if the solicitation title matches commodity IT, bulk mailers, ink/toner, or basic renewal spam."""
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
            f"[*] Maryland Fuzzy Deduplication: Dropped {dropped_count} near-duplicate spam record(s) "
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
            json={"content": f"🚨 **Maryland Procurement Scraper Alert:**\n{message}"},
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
    lines.append(f"**Link:** {link}")
    message = "\n".join(lines)

    try:
        response = requests.post(DISCORD_CONTENT_WEBHOOK_URL, json={"content": message}, timeout=10)
        if response.status_code == 429:
            retry_after = response.json().get("retry_after", 1.0)
            time.sleep(float(retry_after))
            response = requests.post(DISCORD_CONTENT_WEBHOOK_URL, json={"content": message}, timeout=10)
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
    """Normalize Maryland solicitation close dates ('YYYY-MM-DD HH:MM:SS', 'Oct 22nd 2026', 'MM/DD/YYYY') to MM/DD/YYYY."""
    if not date_str:
        return ""
    date_str = str(date_str).strip()
    if date_str.lower() in ["n/a", "tbd", "none", "null", "undefined", "tba", ""]:
        return ""

    if "T" in date_str:
        date_str = date_str.split("T")[0].strip()

    # Check YYYY-MM-DD HH:MM:SS or YYYY-MM-DD
    m_iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})", date_str)
    if m_iso:
        year, month, day = m_iso.groups()
        return f"{int(month):02d}/{int(day):02d}/{year}"

    # Check MM/DD/YYYY
    m_slash = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", date_str)
    if m_slash:
        month, day, year = m_slash.groups()
        if len(year) == 2:
            year = "20" + year
        return f"{int(month):02d}/{int(day):02d}/{year}"

    # Strip ordinal suffixes (1st, 2nd, 3rd, 4th) and timezone suffixes from Bonfire dates like 'Oct 22nd 2026, 4:30 PM EDT'
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
    clean_title = str(raw_title).strip()
    clean_title = re.sub(r"[\s\-\(]*Due:?\s*N/A\)?", "", clean_title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r"[\s\-]+$", "", clean_title).strip()

    clean_date = format_date_clean(raw_date)
    if clean_date:
        return f"{clean_title} - Due: {clean_date}", clean_date
    else:
        return clean_title, ""


async def human_delay(min_sec: float = 1.0, max_sec: float = 2.5):
    """Sleep for a randomized interval to mimic human browsing cadence."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


async def _scrape_emma_portal(page, captured_by_url: dict):
    """Attempt to extract open solicitations from Maryland eMMA if browser_check does not block."""
    try:
        print(f"[*] Checking Maryland eMMA ({EMMA_TARGET_URL})...", flush=True)
        resp = await asyncio.wait_for(
            page.goto(EMMA_TARGET_URL, wait_until="commit", timeout=12000),
            timeout=14.0,
        )
        await asyncio.sleep(1.5)

        if "browser_check" in page.url:
            print("[*] Maryland eMMA redirected to reCAPTCHA Enterprise browser_check; using Maryland direct agency portals...", flush=True)
            return

        if "request_browse_public" in page.url:
            rows = await page.evaluate(
                """() => {
                    const out = [];
                    const trs = document.querySelectorAll('table tbody tr');
                    trs.forEach(tr => {
                        const cells = Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim());
                        const linkEl = tr.querySelector('a[href*="/rfp/request_view_public/"], a[href*="request_browse_public"]');
                        if (cells.length >= 4 && linkEl) {
                            const href = linkEl.getAttribute('href') || '';
                            const fullUrl = href.startsWith('http')
                                ? href
                                : 'https://emma.maryland.gov' + (href.startsWith('/') ? href : '/' + href);
                            out.push({
                                bid_id: cells[0] || '',
                                title: cells[1] || '',
                                close_date: cells[3] || '',
                                agency: cells[4] || 'State of Maryland (eMMA)',
                                url: fullUrl
                            });
                        }
                    });
                    return out;
                }"""
            )
            for r in rows or []:
                if r.get("url") and r.get("title"):
                    captured_by_url[r["url"]] = r
    except Exception:
        pass


async def _scrape_bonfire_portal(page, agency_name: str, base_url: str, captured_by_url: dict):
    """Extract open solicitations from a Maryland Bonfire eProcurement portal via JSON API + DOM fallback."""
    api_url = f"{base_url}/PublicPortal/getOpenPublicOpportunitiesSectionData"
    portal_url = f"{base_url}/portal/?tab=openOpportunities"

    extracted_for_agency = 0
    # 1. Try lightweight HTTP GET first to avoid Chromium V8 heap pressure
    try:
        http_resp = await asyncio.to_thread(
            requests.get,
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
        if http_resp.status_code == 200:
            data = http_resp.json()
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
                        extracted_for_agency += 1
    except Exception:
        pass

    # 2. Fallback to browser navigation if direct HTTP returned 0
    if extracted_for_agency == 0 and page is not None:
        try:
            resp = await asyncio.wait_for(
                page.goto(api_url, wait_until="domcontentloaded", timeout=15000),
                timeout=18.0,
            )
            if resp and resp.status == 200:
                body_text = await page.evaluate("() => document.body.innerText")
                data = json.loads(body_text)
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
                            extracted_for_agency += 1
        except Exception:
            pass

    # 3. Fallback to DOM table on /portal/?tab=openOpportunities if JSON endpoint returned 0
    if extracted_for_agency == 0 and page is not None:
        try:
            await asyncio.wait_for(
                page.goto(portal_url, wait_until="domcontentloaded", timeout=15000),
                timeout=18.0,
            )
            await human_delay(1.0, 2.0)
            dom_rows = await page.evaluate(
                """(args) => {
                    const { baseUrl, agencyName } = args;
                    const out = [];
                    const trs = document.querySelectorAll('table tbody tr');
                    trs.forEach(tr => {
                        const cells = Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim());
                        const linkEl = tr.querySelector('a[href*="/opportunities/"]');
                        if (cells.length >= 4 && linkEl) {
                            const href = linkEl.getAttribute('href') || '';
                            const fullUrl = href.startsWith('http')
                                ? href
                                : baseUrl + (href.startsWith('/') ? href : '/' + href);
                            out.push({
                                bid_id: cells[1] || '',
                                title: cells[2] || '',
                                close_date: cells[3] || '',
                                agency: agencyName,
                                url: fullUrl
                            });
                        }
                    });
                    return out;
                }""",
                {"baseUrl": base_url, "agencyName": agency_name},
            )
            for row in dom_rows or []:
                if row.get("url") and row.get("title"):
                    captured_by_url[row["url"]] = row
                    extracted_for_agency += 1
        except Exception:
            pass

    print(f"[*] Maryland Portal ({agency_name}): Extracted {extracted_for_agency} open solicitation(s).", flush=True)


async def run_scraper(push_to_db: bool = True) -> list[dict]:
    import gc

    supabase_records = []
    if push_to_db and (not SUPABASE_URL or not SUPABASE_KEY):
        print("[!] ERROR: SUPABASE_URL or SUPABASE_KEY not found in .env", flush=True)
        return supabase_records

    selected_port = random.choice(PROXY_PORTS)
    proxy_config = {
        "server": f"http://{PROXY_HOST}:{selected_port}",
        "username": PROXY_USER,
        "password": PROXY_PASS,
        "bypass": "*.gov,*.maryland.gov,*.bonfirehub.com,*.google.com,*.gstatic.com,*.cloudflare.com",
    }

    captured_bids_by_url = {}

    async with Stealth().use_async(async_playwright()) as p:
        browser = None
        page = None

        try:
            print(
                f"[*] Launching Stealth browser for Maryland SLED Procurement ({PROXY_HOST}:{selected_port})...",
                flush=True,
            )
            browser = await p.chromium.launch(
                headless=True,
                proxy=proxy_config,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-extensions",
                    "--disable-background-networking",
                    "--disable-default-apps",
                    "--disable-sync",
                    "--no-first-run",
                    "--mute-audio",
                    "--renderer-process-limit=1",
                    "--disk-cache-size=1",
                    "--media-cache-size=1",
                    "--js-flags=--max-old-space-size=128",
                ],
                ignore_default_args=["--enable-automation"],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1024, "height": 600},
            )
            await context.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in ("image", "media", "font")
                else route.continue_(),
            )
            page = await context.new_page()

            # 1. Check Maryland eMMA public browse portal
            await _scrape_emma_portal(page, captured_bids_by_url)

            # 2. Extract open solicitations across Maryland State & County Bonfire portals
            for agency_name, base_url in MARYLAND_BONFIRE_PORTALS:
                await _scrape_bonfire_portal(page, agency_name, base_url, captured_bids_by_url)
                await human_delay(0.3, 0.8)

        except PlaywrightTimeoutError as te:
            error_msg = f"Maryland Scraper Playwright TimeoutError: {te}"
            print(f"[!] {error_msg}", flush=True)
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {error_msg}\n")
            except Exception:
                pass
            send_discord_alert(error_msg)
            if page:
                try:
                    await page.screenshot(path=ERROR_SCREENSHOT_PATH, full_page=True)
                    print("[+] Saved error_debug.png to root directory.", flush=True)
                except Exception as ss_e:
                    print(f"[!] Could not save screenshot: {ss_e}", flush=True)
        except Exception as e:
            error_msg = f"Maryland Scraper Error during extraction: {e}"
            print(f"[!] {error_msg}", flush=True)
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {error_msg}\n")
            except Exception:
                pass
            send_discord_alert(error_msg)
            if page:
                try:
                    await page.screenshot(path=ERROR_SCREENSHOT_PATH, full_page=True)
                    print("[+] Saved error_debug.png to root directory.", flush=True)
                except Exception as ss_e:
                    print(f"[!] Could not save screenshot: {ss_e}", flush=True)
        finally:
            if browser:
                await browser.close()

    # Release Chromium + Playwright Node driver memory before LLM validation
    gc.collect()

    print(
        f"[*] Maryland SLED: Captured {len(captured_bids_by_url)} unique open solicitations. "
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
                    "agency": str(bid.get("agency") or "State of Maryland").strip(),
                    "closing_date": clean_due if clean_due else None,
                    "url": detail_url,
                    "status": "New Lead",
                }
            )

    # Validate candidates through Anthropic B2B quality control prompt if configured
    if candidate_records and client:
        try:
            print(
                f"[*] Validating {len(candidate_records)} Maryland candidates via Anthropic B2B quality filter...",
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
                model="claude-sonnet-5-5",
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
            supabase_records = [
                r
                for r in candidate_records
                if _normalize_title_for_similarity(r["title"]) in approved_norms
            ]
            print(
                f"[+] B2B LLM validation approved {len(supabase_records)} of {len(candidate_records)} Maryland contracts.",
                flush=True,
            )
        except Exception as llm_err:
            err_msg = f"Maryland Claude B2B validation error: {llm_err}"
            print(f"[!] {err_msg}", flush=True)
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {err_msg}\n")
            except Exception:
                pass
            send_discord_alert(err_msg)
            supabase_records = candidate_records
    else:
        supabase_records = candidate_records

    # Exact URL deduplication + 85% fuzzy title deduplication
    supabase_records = list({r["url"]: r for r in supabase_records}.values())
    supabase_records = fuzzy_deduplicate_records(supabase_records, threshold=0.85)

    if push_to_db:
        if supabase_records:
            print(
                f"[*] Pushing {len(supabase_records)} tech-verified Maryland records to Supabase -> {TABLE_NAME}...",
                flush=True,
            )
            try:
                db_client = supabase or create_client(SUPABASE_URL, SUPABASE_KEY)
                response = (
                    db_client.table(TABLE_NAME)
                    .upsert(supabase_records, on_conflict="url", ignore_duplicates=True)
                    .execute()
                )
                new_records = response.data if response and getattr(response, "data", None) else []
                skipped_count = len(supabase_records) - len(new_records)
                print(
                    f"[+] Successfully synced Maryland data to Supabase! "
                    f"Added {len(new_records)} new records (skipped {skipped_count} duplicates).",
                    flush=True,
                )

                for rec in new_records:
                    send_discord_content(rec)
            except Exception as supabase_err:
                err_msg = f"Maryland Supabase insert error: {supabase_err}"
                print(f"[!] {err_msg}", flush=True)
                try:
                    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                        f.write(f"\n[!] {err_msg}\n")
                except Exception:
                    pass
                send_discord_alert(err_msg)
        else:
            print("[!] No valid Maryland tech records found to push from this run.", flush=True)
    else:
        print(
            f"[+] Maryland SLED extraction complete: {len(supabase_records)} tech contracts ready for master orchestrator.",
            flush=True,
        )

    return supabase_records


if __name__ == "__main__":
    asyncio.run(run_scraper())
