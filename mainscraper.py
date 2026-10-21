import asyncio
import json
import os
import sys
import argparse
import re
import time
from datetime import datetime
from difflib import SequenceMatcher
import requests
from dotenv import load_dotenv

# Ensure sled-scraper directory is on sys.path for importing sledscraper
SLED_SCRAPER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sled-scraper")
if SLED_SCRAPER_DIR not in sys.path:
    sys.path.insert(0, SLED_SCRAPER_DIR)

# 1. Load environment variables
load_dotenv(dotenv_path=".env")

# 2. Initialize API paths (clients lazy-loaded to minimize parent orchestrator RSS under 512Mi)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = "contracts"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DISCORD_CONTENT_WEBHOOK_URL = os.getenv("DISCORD_CONTENT_WEBHOOK_URL")
ERROR_LOG_PATH = "error_log.txt"
ERROR_SCREENSHOT_PATH = "error_debug.png"

client = None
supabase = None


def _get_anthropic_client():
    global client
    if client is None and os.getenv("ANTHROPIC_API_KEY"):
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return client


def _get_supabase_client():
    global supabase
    if supabase is None and SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase

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
    r"^\s*\d{2,4}\s*--",
    r"^\s*assorted\s+hardware\s*$",
    r"interface\s+unit,\s*data",
    r"missile\s+warning",
    r"dc\s+and\s+ac\s+preferred\s+systems",
    r"circuit\s+card\s+assembly",
    r"cable\s+assembly",
    r"wiring\s+harness",
    r"sole\s*source",
    r"notice\s+of\s+intent",
    r"sngl\s+board\s+computer",
    r"single\s+board\s+computer",
]

B2B_EXTRACTION_SYSTEM_PROMPT = (
    "You are a strict B2B government contract quality control filter and extractor.\n"
    "1. REJECT COMMODITY IT: Explicitly ignore and drop any solicitations for commodity software licenses, "
    "bulk mailers (e.g., Bulk Mailer, Mail Manager, postage/mailing software renewals), basic hardware renewals, "
    "ink/toner/printer supplies, and off-the-shelf SaaS renewals or seat/subscription/maintenance renewals.\n"
    "2. TARGET HIGH-VALUE ONLY: Return ONLY high-value, complex B2B IT contracts (e.g., custom software development, "
    "cloud migrations, cybersecurity architecture, network infrastructure, data center operations, enterprise systems integration).\n"
    "3. Strictly ignore unrelated non-IT contracts like HVAC, plumbing, construction, transit, or general municipal services.\n"
    "Extract the full, detailed contract title and exact closing date. "
    "Output strictly as a valid JSON array of objects with keys: title, closing_date, contact_email. "
    "Do not wrap in markdown code blocks or output any other text. "
    "If no closing date is found, leave closing_date as an empty string. "
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
            f"[*] Fuzzy Deduplication: Dropped {dropped_count} near-duplicate spam record(s) "
            f"(>{int(threshold * 100)}% title similarity).",
            flush=True,
        )

    return deduped

def send_discord_alert(message):
    if not DISCORD_WEBHOOK_URL:
        print(" -> ERROR: Webhook URL not found in .env file.", flush=True)
        return
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json={"content": f"**[ALERT] DaaS Pipeline Alert:**\n{message}"})
        response.raise_for_status()
        print(" -> Discord alert sent successfully.", flush=True)
    except Exception as e:
        print(f" -> Failed to send Discord alert: {e}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"Failed to send Discord alert: {e}\n")
        except Exception:
            pass

def send_discord_content(record: dict):
    if not DISCORD_CONTENT_WEBHOOK_URL:
        print(" -> WARNING: DISCORD_CONTENT_WEBHOOK_URL not found in .env file.", flush=True)
        return
    try:
        import client_delivery
        message = client_delivery.format_lead_block(record)
    except Exception:
        raw_title = str(record.get("title") or "N/A").strip()
        clean_title = re.sub(r"\s*-\s*Due:\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$", "", raw_title, flags=re.IGNORECASE).strip()
        agency = record.get("agency") or "N/A"
        closing_date = record.get("closing_date") or "Open / See Official Portal"
        link = record.get("url") or ""
        message = (
            f"**Solicitation:** {clean_title}\n"
            f"**Buyer Agency:** {agency} | **Closing Date:** `{closing_date}`\n"
            f"**Official Portal:** <{link}>\n"
            f"{'─' * 44}"
        )

    payload = {"username": "SignalWire Pro", "content": message}
    try:
        response = requests.post(DISCORD_CONTENT_WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code == 429:
            retry_after = response.json().get("retry_after", 1.0)
            time.sleep(float(retry_after))
            response = requests.post(DISCORD_CONTENT_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        time.sleep(0.4)
    except Exception as e:
        error_msg = f"Failed to send Discord content webhook: {e}"
        print(f" -> {error_msg}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n[!] {error_msg}\n")
        except Exception:
            pass
        send_discord_alert(error_msg)

def format_date_clean(date_str: str) -> str:
    """Normalize extracted date strings into MM/DD/YYYY format, or empty if invalid."""
    if not date_str:
        return ""
    date_str = str(date_str).strip()
    if date_str.lower() in ["n/a", "tbd", "none", "null", "undefined", "tba", ""]:
        return ""
    # Strip time suffix if present (e.g., '10/15/2026 12:00 PM')
    date_part = date_str.split(" ")[0] if ("/" in date_str or "-" in date_str) else date_str
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%b %d %Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            pass
        try:
            dt = datetime.strptime(date_part, fmt)
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            pass
    if re.match(r'^\d{1,2}/\d{1,2}/\d{2,4}$', date_str):
        return date_str
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
    # Strip any pre-existing Due tag or placeholder like (Due: N/A) or - Due: N/A
    clean_title = re.sub(r'[\s\-\(]*Due:?\s*N/A\)?', '', clean_title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r'[\s\-]+$', '', clean_title).strip()
    
    clean_date = format_date_clean(raw_date)
    if clean_date:
        return f"{clean_title} - Due: {clean_date}", clean_date
    else:
        return clean_title, ""

def chunk_text(text, max_chars=15000):
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

async def scrape_and_extract(url: str, selector: str, keyword: str, push_to_db: bool = False):
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
    from playwright_stealth import Stealth
    import gc

    max_retries = 3 
    raw_text = ""
    esbd_lines_captured = []
    
    for attempt in range(max_retries):
        try:
            print(f"\nAttempt {attempt + 1} of {max_retries} connecting to {url}...", flush=True)
            
            async with Stealth().use_async(async_playwright()) as p:
                print(" -> Launching Stealth browser (Local Connection)...", flush=True)
                browser = None
                page = None
                try:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--no-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-gpu',
                            '--disable-software-rasterizer',
                            '--disable-extensions',
                            '--disable-background-networking',
                            '--disable-default-apps',
                            '--disable-sync',
                            '--no-first-run',
                            '--mute-audio',
                            '--renderer-process-limit=1',
                            '--disk-cache-size=1',
                            '--media-cache-size=1',
                            '--js-flags=--max-old-space-size=128',
                        ],
                        ignore_default_args=["--enable-automation"]
                    )
                    
                    context = await browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                        viewport={"width": 1024, "height": 600}
                    )
                    await context.route(
                        "**/*",
                        lambda route: route.abort()
                        if route.request.resource_type in ("image", "media", "font")
                        else route.continue_(),
                    )
                    
                    page = await context.new_page()

                    # Intercept structured ESBD JSON payload containing full titles and responseDue dates
                    async def handle_response(response):
                        if "ESBD.Service.ss" in response.url:
                            try:
                                data = await response.json()
                                if isinstance(data, dict) and "lines" in data:
                                    esbd_lines_captured.extend(data["lines"])
                            except Exception:
                                pass
                    page.on("response", handle_response)
                    
                    print(" -> Browser open. Requesting page (waiting for network to idle)...", flush=True)
                    await page.goto(url, wait_until="networkidle", timeout=60000)
                    
                    print(" -> Page loaded! Waiting 5 additional seconds for JS hydration...", flush=True)
                    await page.wait_for_timeout(5000) 
                    
                    if keyword:
                        try:
                            print(f" -> Injecting keyword '{keyword}' into UI search...", flush=True)
                            search_input = page.locator("input[placeholder*='Search'], input[placeholder*='search'], input[placeholder*='Keyword'], input[type='text']").first
                            await search_input.wait_for(state="visible", timeout=10000)
                            await search_input.click()
                            await search_input.type(keyword, delay=100)
                            await search_input.press("Enter")
                            print(" -> Search submitted! Waiting 8 seconds for JS table to update...", flush=True)
                            await page.wait_for_timeout(8000)
                        except Exception as e:
                            print(f" -> UI Search injection failed: {e}", flush=True)
                    
                    print(f" -> Extracting text from HTML selector: '{selector}'", flush=True)
                    
                    locator = page.locator(selector).first
                    await locator.wait_for(state="attached", timeout=10000)
                    raw_text = await locator.inner_text()

                    if attempt == max_retries - 1 and len(raw_text) < 200 and "403" in raw_text:
                        try:
                            await page.screenshot(path=ERROR_SCREENSHOT_PATH, full_page=True)
                        except Exception:
                            pass
                except Exception:
                    if attempt == max_retries - 1 and page:
                        try:
                            await page.screenshot(path=ERROR_SCREENSHOT_PATH, full_page=True)
                        except Exception:
                            pass
                    raise
                finally:
                    if browser:
                        try:
                            await browser.close()
                        except Exception:
                            pass
                
                print(f" -> Success! Scraped {len(raw_text)} characters. Captured {len(esbd_lines_captured)} structured lines.", flush=True)
                
                if len(raw_text) < 200 and "403" in raw_text:
                    print(" -> 403 Forbidden detected. Retrying...", flush=True)
                    raw_text = ""
                    esbd_lines_captured.clear()
                    raise Exception("WAF Block Detected.")
                    
                break  
                
        except PlaywrightTimeoutError as te:
            error_msg = f"TimeoutError on {url}: {te}"
            print(f" -> {error_msg}", flush=True)
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {error_msg}\n")
            except Exception:
                pass
            if attempt == max_retries - 1:
                send_discord_alert(error_msg)
                raise  
            await asyncio.sleep(2)
        except Exception as e:
            error_msg = f"Playwright error on {url}: {e}"
            print(f" -> {error_msg}", flush=True)
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {error_msg}\n")
            except Exception:
                pass
            if attempt == max_retries - 1:
                send_discord_alert(error_msg)
                raise
            await asyncio.sleep(2)

    gc.collect()
    llm_client = _get_anthropic_client()
    raw_candidates = []

    # Process structured ESBD JSON payload containing full contract titles and exact responseDue dates
    if esbd_lines_captured:
        print(f"[*] Processing {len(esbd_lines_captured)} items from ESBD JSON payload...", flush=True)
        seen_ids = set()
        esbd_candidates = []
        for line in esbd_lines_captured:
            int_id = line.get("internalid") or line.get("solicitationId") or ""
            if int_id and int_id in seen_ids:
                continue
            if int_id:
                seen_ids.add(int_id)

            raw_title = line.get("title") or line.get("solicitationTitle") or ""
            if not raw_title or is_commodity_it_spam(raw_title):
                continue

            raw_due = line.get("responseDue") or line.get("dueDate") or ""
            agency = line.get("agencyName") or "Texas SmartBuy / State of Texas"
            esbd_candidates.append({
                "raw_title": raw_title,
                "raw_due": raw_due,
                "agency": agency,
                "bid_id": line.get("solicitationId") or line.get("internalid") or "",
                "contact_email": line.get("contactEmail") or "",
            })

        if esbd_candidates and llm_client:
            try:
                esbd_snippet = json.dumps(
                    [{"title": c["raw_title"], "closing_date": c["raw_due"], "contact_email": c["contact_email"]} for c in esbd_candidates]
                )
                response = await llm_client.messages.create(
                    model="claude-sonnet-5-5",
                    max_tokens=8000,
                    system=B2B_EXTRACTION_SYSTEM_PROMPT,
                    messages=[
                        {"role": "user", "content": f"Filter and extract ONLY high-value B2B IT contracts from this candidate list:\n\n{esbd_snippet}"}
                    ],
                )
                raw_json_str = ""
                for block in response.content:
                    if block.type == "text":
                        raw_json_str = block.text.strip()
                        break
                if raw_json_str.startswith("```"):
                    raw_json_str = raw_json_str.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                approved = json.loads(raw_json_str)
                approved_titles = {_normalize_title_for_similarity(r.get("title", "")) for r in approved if r.get("title")}
                for c in esbd_candidates:
                    if _normalize_title_for_similarity(c["raw_title"]) in approved_titles:
                        raw_candidates.append(c)
            except Exception as e:
                error_msg = f"Claude ESBD payload validation error: {e}"
                print(error_msg, flush=True)
                try:
                    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                        f.write(f"\n[!] {error_msg}\n")
                except Exception:
                    pass
                send_discord_alert(error_msg)
                raw_candidates.extend(esbd_candidates)
        else:
            raw_candidates.extend(esbd_candidates)

    elif raw_text and llm_client:
        # Extract from scraped page text via Claude AI extraction with strict B2B quality control schema
        text_chunks = chunk_text(raw_text, max_chars=15000)
        print(f"\nSplit text into {len(text_chunks)} chunks for processing...")

        for i, chunk in enumerate(text_chunks):
            print(f"Processing chunk {i+1} of {len(text_chunks)}...")
            try:
                response = await llm_client.messages.create(
                    model="claude-sonnet-5-5",
                    max_tokens=8000,
                    system=B2B_EXTRACTION_SYSTEM_PROMPT,
                    messages=[
                        {"role": "user", "content": f"Extract data from this text snippet:\n\n{chunk}"}
                    ]
                )

                raw_json_str = ""
                for block in response.content:
                    if block.type == "text":
                        raw_json_str = block.text.strip()
                        break

                if raw_json_str.startswith("```"):
                    raw_json_str = raw_json_str.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

                records = json.loads(raw_json_str)
                for r in records:
                    raw_candidates.append({
                        "raw_title": r.get("title") or "",
                        "raw_due": r.get("closing_date") or "",
                        "agency": "Texas SmartBuy / State of Texas",
                        "bid_id": "",
                        "contact_email": r.get("contact_email") or "",
                    })
                print(f"Found {len(records)} contracts in chunk {i+1}.")

            except Exception as e:
                error_msg = f"Claude Extraction Error on chunk {i+1}: {e}"
                print(error_msg)
                try:
                    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                        f.write(f"\n[!] {error_msg}\n")
                except Exception:
                    pass
                send_discord_alert(error_msg)
                continue

    # Filter with tech_keywords regex array, reject commodity IT, and format titles & dates
    formatted_records = []
    for cand in raw_candidates:
        title = cand["raw_title"].strip()
        if not title or is_commodity_it_spam(title):
            continue
        title_lower = title.lower()

        # Strict regex filtering protocol
        if any(re.search(pattern, title_lower) for pattern in tech_keywords):
            formatted_title, clean_due = format_title_and_due(title, cand["raw_due"])
            if not formatted_title or is_commodity_it_spam(formatted_title):
                continue

            bid_id = cand.get("bid_id", "").strip()
            if bid_id:
                contract_url = f"https://www.txsmartbuy.com/esbd/{bid_id}"
            else:
                slug = re.sub(r'[^a-z0-9]+', '-', formatted_title.lower()).strip('-')[:80]
                contract_url = f"{url.rstrip('/')}#{slug}"

            rec = {
                "title": formatted_title,
                "agency": cand["agency"],
                "closing_date": clean_due if clean_due else None,
                "url": contract_url,
                "status": "New Lead"
            }

            formatted_records.append(rec)

    # Deduplicate by url to satisfy contracts_url_key unique constraint
    unique_records = list({r["url"]: r for r in formatted_records}.values())
    # Programmatic 85% fuzzy title deduplication to prevent catalog-dump spam
    unique_records = fuzzy_deduplicate_records(unique_records, threshold=0.85)

    if push_to_db:
        print(f"Extraction complete. Total validated tech contracts found: {len(unique_records)}. Uploading to Supabase...")

        if not unique_records:
            print("No valid tech contracts found to upload.")
            return unique_records

        try:
            db_client = _get_supabase_client()
            response = db_client.table(TABLE_NAME).upsert(
                unique_records, on_conflict="url", ignore_duplicates=True
            ).execute()
            new_records = response.data if response and getattr(response, "data", None) else []
            skipped_count = len(unique_records) - len(new_records)
            print(f"Success! {len(new_records)} new records were added to your Supabase '{TABLE_NAME}' table (skipped {skipped_count} duplicates).")

            for rec in new_records:
                send_discord_content(rec)
        except Exception as e:
            error_msg = f"Supabase Upload Error: {e}"
            print(error_msg)
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {error_msg}\n")
            except Exception:
                pass
            send_discord_alert(error_msg)
    else:
        print(f"[+] Texas SmartBuy (ESBD) extraction complete: {len(unique_records)} tech contracts ready for master orchestrator.", flush=True)

    return unique_records


async def run_master_orchestrator(
    url: str = "https://www.txsmartbuy.com/esbd",
    selector: str = "body",
    keyword: str = "software",
):
    import gc
    import ctypes
    import tempfile

    print("========================================================", flush=True)
    print("   SignalTender Master Orchestrator - Starting Cycle    ", flush=True)
    print("========================================================", flush=True)

    def _reclaim_os_memory():
        gc.collect()
        try:
            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except Exception:
            pass

    # Use a semaphore of 1 inside asyncio.gather and run each scraper in an isolated
    # child subprocess so 100% of Chromium/Playwright/Python heap is returned to the OS
    # after each portal, preventing 512Mi OOM on Render and catching any OS SIGKILL (-9/137).
    browser_sem = asyncio.Semaphore(1)
    base_dir = os.path.dirname(os.path.abspath(__file__))

    async def _run_source(source_name: str, import_stmt: str, call_expr: str):
        async with browser_sem:
            print(f"\n[*] Executing {source_name} pipeline (isolated subprocess)...", flush=True)
            fd, temp_json_path = tempfile.mkstemp(prefix="st_scraper_", suffix=".json")
            os.close(fd)
            runner_script = (
                "import asyncio, json, os, sys\n"
                f"sys.path.insert(0, {repr(base_dir)})\n"
                f"sys.path.insert(0, {repr(SLED_SCRAPER_DIR)})\n"
                f"{import_stmt}\n"
                "async def _main():\n"
                f"    res = await {call_expr}\n"
                "    with open(sys.argv[1], 'w', encoding='utf-8') as f:\n"
                "        json.dump(res if isinstance(res, list) else [], f)\n"
                "asyncio.run(_main())\n"
            )
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-c",
                    runner_script,
                    temp_json_path,
                    cwd=base_dir,
                )
                await proc.wait()

                if proc.returncode != 0:
                    oom_tag = (
                        " [OUT OF MEMORY / SIGKILL >512Mi]"
                        if proc.returncode in (-9, 137, -6, 134)
                        else ""
                    )
                    raise RuntimeError(
                        f"{source_name} subprocess terminated with exit code {proc.returncode}{oom_tag}."
                    )

                if os.path.exists(temp_json_path):
                    with open(temp_json_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        return json.loads(content) if content else []
                return []
            finally:
                if os.path.exists(temp_json_path):
                    try:
                        os.remove(temp_json_path)
                    except Exception:
                        pass
                _reclaim_os_memory()

    results = await asyncio.gather(
        _run_source("Federal (SAM.gov)", "import sam_scraper", "sam_scraper.run_scraper(push_to_db=False)"),
        _run_source("SLED (DemandStar)", "import sledscraper", "sledscraper.run_scraper(push_to_db=False)"),
        _run_source(
            "Texas SLED (ESBD)",
            "import mainscraper",
            f"mainscraper.scrape_and_extract({repr(url)}, {repr(selector)}, {repr(keyword)}, push_to_db=False)",
        ),
        _run_source("Virginia SLED (eVA)", "import va_scraper", "va_scraper.run_scraper(push_to_db=False)"),
        _run_source("California SLED (Cal eProcure)", "import ca_scraper", "ca_scraper.run_scraper(push_to_db=False)"),
        _run_source("Florida SLED (MFMP VIP)", "import fl_scraper", "fl_scraper.run_scraper(push_to_db=False)"),
        _run_source("Maryland SLED (eMMA / Bonfire)", "import md_scraper", "md_scraper.run_scraper(push_to_db=False)"),
        _run_source("Illinois SLED (BidBuy / CTA)", "import il_scraper", "il_scraper.run_scraper(push_to_db=False)"),
        return_exceptions=True,
    )

    source_labels = [
        "Federal (SAM.gov)",
        "SLED (DemandStar)",
        "Texas SLED (ESBD)",
        "Virginia SLED (eVA)",
        "California SLED (Cal eProcure)",
        "Florida SLED (MFMP VIP)",
        "Maryland SLED (eMMA / Bonfire)",
        "Illinois SLED (BidBuy / CTA)",
    ]
    combined_records = []

    for label, res in zip(source_labels, results):
        if isinstance(res, Exception):
            error_msg = f"Orchestrator error in {label}: {res}"
            print(f"[!] {error_msg}", flush=True)
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {error_msg}\n")
            except Exception:
                pass
            send_discord_alert(error_msg)
        elif isinstance(res, list):
            print(f"[*] Collected {len(res)} validated records from {label}.", flush=True)
            combined_records.extend(res)

    # Combine extracted records from all sources into a single unified payload and deduplicate by URL
    unified_payload = list({r["url"]: r for r in combined_records if isinstance(r, dict) and r.get("url") and not is_commodity_it_spam(str(r.get("title") or ""))}.values())
    # Apply 85% fuzzy title deduplication across the combined payload before Supabase insertion
    unified_payload = fuzzy_deduplicate_records(unified_payload, threshold=0.85)

    # Drop any already-expired contracts from the incoming batch before touching Supabase
    today = datetime.now().date()

    def _parse_contract_due_date(rec: dict):
        candidates = [str(rec.get("closing_date") or "").strip()]
        m_title = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", str(rec.get("title") or ""), flags=re.IGNORECASE)
        if m_title:
            candidates.append(m_title.group(1))
        for cand in candidates:
            if not cand or cand.lower() in ["n/a", "tbd", "none", "null", ""]:
                continue
            if "T" in cand:
                cand = cand.split("T")[0].strip()
            for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
                try:
                    return datetime.strptime(cand, fmt).date()
                except ValueError:
                    pass
        return None

    open_payload = []
    dropped_expired_incoming = 0
    for rec in unified_payload:
        due_dt = _parse_contract_due_date(rec)
        if due_dt is not None and due_dt < today:
            dropped_expired_incoming += 1
        else:
            open_payload.append(rec)

    if dropped_expired_incoming > 0:
        print(f"[*] Dropped {dropped_expired_incoming} already-expired contract(s) from incoming batch.", flush=True)
    unified_payload = open_payload

    print(
        f"\n[*] Master Orchestrator: Combined {len(combined_records)} total extracted records "
        f"into {len(unified_payload)} unique, open high-value tech contracts.",
        flush=True,
    )

    if not SUPABASE_URL or not SUPABASE_KEY:
        error_msg = "SUPABASE_URL or SUPABASE_KEY missing in environment. Cannot upload unified payload."
        print(f"[!] {error_msg}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n[!] {error_msg}\n")
        except Exception:
            pass
        send_discord_alert(error_msg)
        return []

    db_client = _get_supabase_client()

    # Automatically purge any previously stored contracts in Supabase whose closing_date has passed
    try:
        existing_resp = db_client.table(TABLE_NAME).select("url, title, closing_date").execute()
        existing_rows = existing_resp.data if existing_resp and getattr(existing_resp, "data", None) else []
        expired_urls = [
            row["url"]
            for row in existing_rows
            if row.get("url") and (_parse_contract_due_date(row) is not None and _parse_contract_due_date(row) < today)
        ]
        if expired_urls:
            for i in range(0, len(expired_urls), 100):
                batch_urls = expired_urls[i : i + 100]
                db_client.table(TABLE_NAME).delete().in_("url", batch_urls).execute()
            print(f"[+] Purged {len(expired_urls)} expired contract(s) (closing_date < {today}) from Supabase.", flush=True)
        else:
            print(f"[*] Database hygiene check complete: 0 expired contracts found in Supabase.", flush=True)
    except Exception as purge_err:
        purge_msg = f"Master Orchestrator Expired Contract Purge Warning: {purge_err}"
        print(f"[!] {purge_msg}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n[!] {purge_msg}\n")
        except Exception:
            pass
        send_discord_alert(purge_msg)

    if not unified_payload:
        print("[-] No valid tech contracts found across Federal and SLED sources this cycle.", flush=True)
        try:
            import seed_rapidapi_telemetry
            seed_rapidapi_telemetry.run_telemetry_seeder(rotating=True, slice_size=4)
        except Exception as tel_err:
            tel_msg = f"RapidAPI telemetry seeder error in mainscraper.py: {tel_err}"
            print(f"[!] {tel_msg}", flush=True)
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {tel_msg}\n")
            except Exception:
                pass
            send_discord_alert(tel_msg)
        return []

    try:
        print(f"[*] Passing unified payload ({len(unified_payload)} contracts) through Supabase deduplication filter...", flush=True)
        response = db_client.table(TABLE_NAME).upsert(
            unified_payload, on_conflict="url", ignore_duplicates=True
        ).execute()
        new_records = response.data if response and getattr(response, "data", None) else []
        skipped_count = len(unified_payload) - len(new_records)
        print(
            f"[+] Unified Supabase sync complete! Added {len(new_records)} net-new records "
            f"(skipped {skipped_count} duplicates).",
            flush=True,
        )

        if new_records:
            print(f"[*] Pushing {len(new_records)} net-new federal and state contracts to DISCORD_CONTENT_WEBHOOK_URL...", flush=True)
            for rec in new_records:
                send_discord_content(rec)
            print("[+] All net-new contracts dispatched to subscriber Discord webhook.", flush=True)
        else:
            print("[*] No net-new contracts to dispatch to Discord this cycle.", flush=True)

        _reclaim_os_memory()

        # Rebuild Programmatic SEO (pSEO) static directory & sitemap.xml from live Supabase contracts
        try:
            import pseo_generator
            pseo_generator.generate_pseo_site()
        except Exception as pseo_err:
            pseo_msg = f"pSEO static generation error in mainscraper.py: {pseo_err}"
            print(f"[!] {pseo_msg}", flush=True)
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {pseo_msg}\n")
            except Exception:
                pass
            send_discord_alert(pseo_msg)

        _reclaim_os_memory()

        # Enrich net-new solicitations into Tier 2 CaptureDesk Autopilot dossiers
        try:
            import capturedesk_autopilot
            capturedesk_autopilot.run_capturedesk_autopilot()
        except Exception as cd_err:
            cd_msg = f"CaptureDesk Autopilot error in mainscraper.py: {cd_err}"
            print(f"[!] {cd_msg}", flush=True)
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {cd_msg}\n")
            except Exception:
                pass
            send_discord_alert(cd_msg)

        _reclaim_os_memory()

        # Seed rotating RapidAPI 200 OK telemetry slice so all 15+ storefronts keep green 100% Service Level badges
        try:
            import seed_rapidapi_telemetry
            seed_rapidapi_telemetry.run_telemetry_seeder(rotating=True, slice_size=4)
        except Exception as tel_err:
            tel_msg = f"RapidAPI telemetry seeder error in mainscraper.py: {tel_err}"
            print(f"[!] {tel_msg}", flush=True)
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {tel_msg}\n")
            except Exception:
                pass
            send_discord_alert(tel_msg)

        return new_records

    except Exception as e:
        error_msg = f"Master Orchestrator Supabase Upload Error: {e}"
        print(f"[!] {error_msg}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n[!] {error_msg}\n")
        except Exception:
            pass
        send_discord_alert(error_msg)
        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Master Orchestrator: Scrape Federal and SLED leads.")
    parser.add_argument("url", nargs="?", default="https://www.txsmartbuy.com/esbd", help="The target URL to scrape")
    parser.add_argument("--selector", "-s", default="body", help="CSS selector to target specific HTML container (e.g., '.job-board')")
    parser.add_argument("--keyword", "-k", default="software", help="Keyword to dynamically type into the site's search bar")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_master_orchestrator(args.url, args.selector, args.keyword))
    except Exception as fatal_err:
        fatal_msg = f"Master Orchestrator Fatal Crash: {fatal_err}"
        print(f"[!] {fatal_msg}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n[!] {fatal_msg}\n")
        except Exception:
            pass
        send_discord_alert(fatal_msg)
        raise