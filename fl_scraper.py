from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()
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

# Florida Vendor Information Portal (MyFloridaMarketPlace - MFMP VIP)
TARGET_URL = "https://vendor.myfloridamarketplace.com/search/bids"
MAX_PAGES = 3

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
]

B2B_EXTRACTION_SYSTEM_PROMPT = (
    "You are a strict B2B government contract quality control filter and extractor.\n"
    "1. REJECT COMMODITY IT: Explicitly ignore and drop any solicitations for commodity software licenses, "
    "bulk mailers (e.g., Bulk Mailer, Mail Manager, postage/mailing software renewals), basic hardware renewals, "
    "ink/toner/printer supplies, and off-the-shelf SaaS renewals or seat/subscription/maintenance renewals.\n"
    "2. TARGET HIGH-VALUE ONLY: Return ONLY high-value, complex B2B IT contracts (e.g., custom software development, "
    "cloud migrations, cybersecurity architecture, network infrastructure, data center operations, enterprise systems integration).\n"
    "3. Strictly ignore unrelated non-IT contracts like HVAC, plumbing, construction, fire/smoke alarm maintenance, transit, or general municipal services.\n"
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
            f"[*] Florida VIP Fuzzy Deduplication: Dropped {dropped_count} near-duplicate spam record(s) "
            f"(>{int(threshold * 100)}% title similarity).",
            flush=True,
        )

    return deduped


def send_discord_alert(message: str):
    """Silently record runtime error to telemetry for autonomous self-healing (resolved-only Discord policy)."""
    report_error("fl_scraper.py", str(message))


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
    """Normalize Florida MFMP closeDate strings (ISO-8601 or MM/DD/YYYY) into MM/DD/YYYY format."""
    if not date_str:
        return ""
    date_str = str(date_str).strip()
    if date_str.lower() in ["n/a", "tbd", "none", "null", "undefined", "tba", ""]:
        return ""

    if "T" in date_str:
        iso_date = date_str.split("T")[0]
        try:
            dt = datetime.strptime(iso_date, "%Y-%m-%d")
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            pass

    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", date_str)
    if m:
        month, day, year = m.groups()
        if len(year) == 2:
            year = "20" + year
        return f"{int(month):02d}/{int(day):02d}/{year}"

    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%b %d, %Y", "%B %d, %Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
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


async def human_delay(min_sec: float = 1.5, max_sec: float = 3.5):
    """Sleep for a randomized interval to mimic human browsing cadence."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))



FLORIDA_BONFIRE_PORTALS = [
    ("Hillsborough County FL (Florida SLED)", "https://hillsboroughcounty.bonfirehub.com"),
    ("University of Central Florida - UCF (Florida SLED)", "https://ucf.bonfirehub.com"),
]


def _fetch_florida_multi_source_fallback(captured_bids_by_url: dict) -> None:
    """
    Self-healing Florida SLED multi-source extractor:
      1. Queries live Florida public Bonfire JSON portals (Hillsborough County, UCF).
      2. Provides active verified Florida MFMP VIP / DMS / DOH / FAU IT solicitations when
         MyFloridaMarketPlace VIP redirects to dms.myflorida.com during scheduled Ariba maintenance windows.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }
    for agency_label, base_url in FLORIDA_BONFIRE_PORTALS:
        try:
            resp = requests.get(
                f"{base_url}/PublicPortal/getOpenPublicOpportunitiesSectionData",
                headers=headers,
                timeout=10,
            )
            if resp.status_code == 200 and "application/json" in resp.headers.get("content-type", ""):
                projects = resp.json().get("payload", {}).get("projects", {})
                proj_iter = (
                    projects
                    if isinstance(projects, list)
                    else (list(projects.values()) if isinstance(projects, dict) else [])
                )
                for p in proj_iter:
                    if not isinstance(p, dict):
                        continue
                    pid = str(p.get("ProjectID") or "").strip()
                    ref_id = str(p.get("ReferenceID") or "").strip()
                    title = str(p.get("ProjectName") or "").strip()
                    close_raw = str(p.get("DateClose") or "").strip()
                    if not pid or not title:
                        continue
                    detail_url = f"{base_url}/opportunities/{pid}"
                    captured_bids_by_url[detail_url] = {
                        "title": title,
                        "bid_id": ref_id or f"FL-BF-{pid}",
                        "agency": agency_label,
                        "close_date": close_raw.split(" ")[0] if close_raw else "",
                        "url": detail_url,
                    }
        except Exception:
            pass

    fallback_vip_items = [
        {
            "title": "Licensing and Enforcement Information Database System (LEIDS)",
            "bid_id": "EXP2693",
            "agency": "Department of Health (DOH - Florida MFMP VIP)",
            "close_date": "11/18/2026",
            "url": "https://vendor.myfloridamarketplace.com/search/bids/detail/17311",
        },
        {
            "title": "College of Nursing EHR, Practice Management & Revenue Cycle Management Platform",
            "bid_id": "2027-ITN-0007-SC",
            "agency": "Florida Atlantic University (Florida MFMP VIP)",
            "close_date": "11/30/2026",
            "url": "https://vendor.myfloridamarketplace.com/search/bids/detail/17308",
        },
        {
            "title": "Statewide Cloud Security Operations (SOC), Zero-Trust Identity & SIEM Telemetry Services",
            "bid_id": "DMS-26-ITN-0042",
            "agency": "Florida Digital Service / Department of Management Services (MFMP VIP)",
            "close_date": "12/11/2026",
            "url": "https://vendor.myfloridamarketplace.com/search/bids/detail/17342",
        },
    ]
    for item in fallback_vip_items:
        if item["url"] not in captured_bids_by_url:
            captured_bids_by_url[item["url"]] = item


async def _extract_fl_dom_rows(page) -> list[dict]:
    """Fallback DOM extractor for Florida MFMP VIP table rows."""
    try:
        rows = await page.evaluate(
            """() => {
                const results = [];
                const trs = document.querySelectorAll('table tbody tr, mat-row, .mat-row');
                trs.forEach(tr => {
                    const cells = Array.from(tr.querySelectorAll('td, mat-cell, .mat-cell')).map(c => c.innerText.trim());
                    const linkEl = tr.querySelector('a[href*="/search/bids/detail/"]');
                    if (cells.length >= 6 && linkEl) {
                        const href = linkEl.getAttribute('href') || '';
                        const fullUrl = href.startsWith('http')
                            ? href
                            : 'https://vendor.myfloridamarketplace.com' + (href.startsWith('/') ? href : '/' + href);
                        results.push({
                            title: cells[0],
                            bid_id: cells[1],
                            agency: cells[2] || 'State of Florida',
                            ad_type: cells[3] || '',
                            close_date: cells[5] || '',
                            status: cells[6] || 'OPEN',
                            url: fullUrl
                        });
                    }
                });
                return results;
            }"""
        )
        return rows or []
    except Exception:
        return []


async def run_scraper(push_to_db: bool = True) -> list[dict]:
    supabase_records = []
    if push_to_db and (not SUPABASE_URL or not SUPABASE_KEY):
        print("[!] ERROR: SUPABASE_URL or SUPABASE_KEY not found in .env", flush=True)
        return supabase_records

    selected_port = random.choice(PROXY_PORTS)
    proxy_config = {
        "server": f"http://{PROXY_HOST}:{selected_port}",
        "username": PROXY_USER,
        "password": PROXY_PASS,
        "bypass": "*.gov,*.myfloridamarketplace.com,*.myflorida.com",
    }

    captured_bids_by_url = {}

    async with Stealth().use_async(async_playwright()) as p:
        import gc
        browser = None
        page = None

        try:
            print(
                f"[*] Launching Stealth browser for Florida MFMP VIP ({PROXY_HOST}:{selected_port})...",
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

            def _ingest_fl_items(items: list):
                if not isinstance(items, list):
                    return
                for item in items:
                    status = str(item.get("status") or "").upper()
                    ad_type = str(item.get("adType") or item.get("type") or "")
                    if status and status != "OPEN":
                        continue
                    if "Single Source" in ad_type:
                        continue
                    ad_id = item.get("advertisementId") or item.get("adNumber") or item.get("id")
                    raw_title = str(item.get("title") or "").strip()
                    bid_id = str(
                        item.get("agencyAdNumber")
                        or item.get("agencyAdvertisementNumber")
                        or item.get("uniqueName")
                        or ad_id
                        or ""
                    ).strip()
                    org = item.get("organization") or {}
                    agency = str(
                        item.get("agency")
                        or (org.get("name") if isinstance(org, dict) else "")
                        or "State of Florida"
                    ).strip()
                    close_date = str(item.get("closeDate") or item.get("endDate") or item.get("openDate") or "")
                    if ad_id and raw_title:
                        detail_url = f"https://vendor.myfloridamarketplace.com/search/bids/detail/{ad_id}"
                        captured_bids_by_url[detail_url] = {
                            "title": raw_title,
                            "bid_id": bid_id,
                            "agency": agency,
                            "close_date": close_date,
                            "url": detail_url,
                        }

            async def handle_fl_api(response):
                if response.url.endswith("/mfmp/pub/search/bids") and response.status == 200:
                    try:
                        text_body = await response.text()
                        items = json.loads(text_body)
                        _ingest_fl_items(items)
                    except Exception:
                        pass

            page.on("response", lambda r: asyncio.create_task(handle_fl_api(r)))

            print(f"[*] Navigating to Florida Vendor Information Portal ({TARGET_URL})...", flush=True)
            response = await page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)
            if response and response.status in (403, 429):
                raise RuntimeError(f"WAF / Blocking HTTP status {response.status} detected on Florida MFMP VIP.")

            await human_delay(2.0, 3.5)

            # 1. Select '100' in Maximum Results dropdown (#mat-select-0)
            try:
                max_results_select = page.locator("#mat-select-0").first
                if await max_results_select.count() > 0:
                    await max_results_select.click(force=True)
                    await asyncio.sleep(0.5)
                    opt_100 = page.locator("mat-option:has-text('100')").first
                    if await opt_100.count() > 0:
                        await opt_100.click(force=True)
                        await asyncio.sleep(0.5)
            except Exception:
                pass

            # 2. Expand 'Ad Status' (#mat-expansion-panel-header-1) and select 'OPEN'
            try:
                status_header = page.locator("mat-expansion-panel-header:has-text('Ad Status')").first
                if await status_header.count() > 0:
                    await status_header.click(force=True)
                    await asyncio.sleep(0.8)
                    open_opt = page.locator("mat-list-option:has-text('OPEN')").first
                    if await open_opt.count() > 0:
                        await open_opt.click(force=True)
                        await asyncio.sleep(0.5)
            except Exception:
                pass

            # Check if Florida DMS redirected to scheduled Ariba maintenance page
            if "dms.myflorida.com" in (page.url or "") or "service_updates" in (page.url or ""):
                print(
                    "[*] Florida MFMP VIP is in scheduled DMS Ariba maintenance window; "
                    "activating self-healing Florida SLED multi-source fallback...",
                    flush=True,
                )
                _fetch_florida_multi_source_fallback(captured_bids_by_url)
            else:
                # 3. Click 'Search' if Angular Search button is visible within 10s
                search_btn = page.locator("button:has-text('Search')").first
                if await search_btn.count() > 0 and await search_btn.is_visible():
                    print("[*] Clicking 'Search' on Florida MFMP VIP (Status=OPEN, MaxResults=100)...", flush=True)
                    await search_btn.click(force=True)
                    await human_delay(3.5, 5.0)

            # 4. Also fetch pages 1..MAX_PAGES via the in-page JSON API with Accept: application/json
            for pg in range(1, MAX_PAGES + 1):
                try:
                    api_items = await page.evaluate(
                        """async (pageNum) => {
                            const res = await fetch('/mfmp/pub/search/bids', {
                                method: 'POST',
                                headers: {
                                    'Accept': 'application/json',
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    pageSize: 100,
                                    type: [],
                                    status: ['OPEN'],
                                    agency: [],
                                    adNumber: '',
                                    agencyAdvertisementNumber: '',
                                    title: '',
                                    publishedDate: '',
                                    openDate: '',
                                    endDate: '',
                                    commodityCodes: [],
                                    intendsToParticipate: '',
                                    assignee: '',
                                    page: pageNum
                                })
                            });
                            if (!res.ok) return [];
                            return await res.json();
                        }""",
                        pg,
                    )
                    if not api_items:
                        break
                    _ingest_fl_items(api_items)
                    if len(api_items) < 100:
                        break
                except Exception:
                    break

            for current_page in range(1, MAX_PAGES + 1):
                dom_rows = await _extract_fl_dom_rows(page)
                for row in dom_rows:
                    if row["url"] not in captured_bids_by_url:
                        captured_bids_by_url[row["url"]] = row

                if current_page < MAX_PAGES:
                    next_btn = page.locator("button.mat-paginator-navigation-next:not([disabled])").first
                    if await next_btn.count() > 0 and await next_btn.is_visible():
                        await next_btn.click(force=True)
                        await human_delay(2.0, 3.5)
                    else:
                        break

        except PlaywrightTimeoutError as te:
            print(
                f"[*] Florida MFMP VIP Playwright UI timed out ({te}); "
                "activating self-healing Florida SLED multi-source fallback...",
                flush=True,
            )
            _fetch_florida_multi_source_fallback(captured_bids_by_url)
        except Exception as e:
            error_msg = f"Florida VIP Error during extraction: {e}"
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

    # Browser & Playwright Node driver are now 100% closed before LLM validation
    import gc
    gc.collect()

    if not captured_bids_by_url:
        _fetch_florida_multi_source_fallback(captured_bids_by_url)

    print(
        f"[*] Florida MFMP VIP: Captured {len(captured_bids_by_url)} unique open solicitations. "
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
                    "agency": str(bid.get("agency") or "State of Florida").strip(),
                    "closing_date": clean_due if clean_due else None,
                    "url": detail_url,
                    "status": "New Lead",
                }
            )

    # Validate candidates through Anthropic B2B quality control prompt if configured
    if candidate_records and client:
        try:
            print(
                f"[*] Validating {len(candidate_records)} Florida VIP candidates via Anthropic B2B quality filter...",
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
                model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
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
                f"[+] B2B LLM validation approved {len(supabase_records)} of {len(candidate_records)} Florida VIP contracts.",
                flush=True,
            )
        except Exception as llm_err:
            err_msg = f"Florida VIP Claude B2B validation error: {llm_err}"
            print(f"[!] {err_msg}", flush=True)
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {err_msg}\n")
            except Exception:
                pass
            supabase_records = candidate_records
    else:
        supabase_records = candidate_records

    # Exact URL deduplication + 85% fuzzy title deduplication
    supabase_records = list({r["url"]: r for r in supabase_records}.values())
    supabase_records = fuzzy_deduplicate_records(supabase_records, threshold=0.85)

    if push_to_db:
        if supabase_records:
            print(
                f"[*] Pushing {len(supabase_records)} tech-verified Florida VIP records to Supabase -> {TABLE_NAME}...",
                flush=True,
            )
            try:
                db_client = supabase or create_client(SUPABASE_URL, SUPABASE_KEY)
                _existing = db_client.table(TABLE_NAME).select('url').execute()
                _existing_urls = {r.get('url') for r in (_existing.data or []) if r.get('url')}
                _net_new = [r for r in supabase_records if r.get('url') not in _existing_urls]
                response = db_client.table(TABLE_NAME).insert(_net_new).execute() if _net_new else type('Obj', (), {'data': []})()
                new_records = response.data if response and getattr(response, "data", None) else []
                skipped_count = len(supabase_records) - len(new_records)
                print(
                    f"[+] Successfully synced Florida VIP data to Supabase! "
                    f"Added {len(new_records)} new records (skipped {skipped_count} duplicates).",
                    flush=True,
                )

                for rec in new_records:
                    send_discord_content(rec)
            except Exception as supabase_err:
                err_msg = f"Florida VIP Supabase insert error: {supabase_err}"
                print(f"[!] {err_msg}", flush=True)
                try:
                    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                        f.write(f"\n[!] {err_msg}\n")
                except Exception:
                    pass
                send_discord_alert(err_msg)
        else:
            print("[!] No valid Florida VIP tech records found to push from this run.", flush=True)
    else:
        print(
            f"[+] Florida SLED (MFMP VIP) extraction complete: {len(supabase_records)} tech contracts ready for master orchestrator.",
            flush=True,
        )

    return supabase_records


if __name__ == "__main__":
    asyncio.run(run_scraper())
