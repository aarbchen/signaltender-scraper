import os
import json
import asyncio
import requests
import re
import time
from datetime import datetime
from difflib import SequenceMatcher
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

# Your Decodo residential proxy credentials
PROXY_HOST = "us.decodo.com"
PROXY_PORT = "10001"  # Sticky session port so authenticated DemandStar sessions do not drop mid-scrape
PROXY_USER = "sphmb5n9of"
PROXY_PASS = "y7x~OwTiQim03Ooh4p"

# Your free DemandStar credentials
DEMANDSTAR_USER = "jouanlychen12@gmail.com"
DEMANDSTAR_PASS = "7440131a"

LOGIN_URL = "https://www.demandstar.com/app/login"
TARGET_URL = "https://www.demandstar.com/app/suppliers/bids"
MAX_PAGES = 10  # 10 pages of PURE tech results (100 bids)

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
]

B2B_EXTRACTION_SYSTEM_PROMPT = (
    "You are a strict B2B government contract quality control filter and extractor.\n"
    "1. REJECT COMMODITY IT: Explicitly ignore and drop any solicitations for commodity software licenses, "
    "bulk mailers (e.g., Bulk Mailer, Mail Manager, postage/mailing software renewals), basic hardware renewals, "
    "ink/toner/printer supplies, and off-the-shelf SaaS renewals or seat/subscription/maintenance renewals.\n"
    "2. TARGET HIGH-VALUE ONLY: Return ONLY high-value, complex B2B IT contracts (e.g., custom software development, "
    "cloud migrations, cybersecurity architecture, network infrastructure, data center operations, enterprise systems integration).\n"
    "3. Strictly ignore unrelated non-IT contracts like HVAC, plumbing, construction, transit, or general municipal services.\n"
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
            f"[*] Fuzzy Deduplication: Dropped {dropped_count} near-duplicate spam record(s) "
            f"(>{int(threshold * 100)}% title similarity).",
            flush=True,
        )

    return deduped

def send_discord_alert(message: str):
    if not DISCORD_WEBHOOK_URL:
        print("[!] Webhook URL not found in .env file.", flush=True)
        return
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json={"content": f"🚨 **SLED Scraper Alert:**\n{message}"}, timeout=10)
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
    """Normalize extracted date strings into MM/DD/YYYY format, or empty if invalid."""
    if not date_str:
        return ""
    date_str = str(date_str).strip()
    if date_str.lower() in ["n/a", "tbd", "none", "null", "undefined", "tba", ""]:
        return ""
    for fmt in (
        "%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%b %d %Y",
        "%b %d, %Y %I:%M %p", "%b %d, %Y %H:%M", "%m/%d/%Y %I:%M %p"
    ):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            pass
    date_part = date_str.split(" ")[0] if ("/" in date_str or "-" in date_str) else " ".join(date_str.split(" ")[:3])
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%b %d %Y"):
        try:
            dt = datetime.strptime(date_part.strip(","), fmt)
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            pass
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{2,4})$', date_str)
    if m:
        month, day, year = m.groups()
        if len(year) == 2:
            year = "20" + year
        return f"{int(month):02d}/{int(day):02d}/{year}"
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
    clean_title = re.sub(r'[\s\-\(]*Due:?\s*N/A\)?', '', clean_title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r'[\s\-]+$', '', clean_title).strip()
    
    clean_date = format_date_clean(raw_date)
    if clean_date:
        return f"{clean_title} - Due: {clean_date}", clean_date
    else:
        return clean_title, ""


async def run_scraper(push_to_db: bool = True):
    supabase_records = []
    if push_to_db and (not SUPABASE_URL or not SUPABASE_KEY):
        print("[!] ERROR: SUPABASE_URL or SUPABASE_KEY not found in .env")
        return supabase_records

    proxy_config = {
        "server": f"http://{PROXY_HOST}:{PROXY_PORT}",
        "username": PROXY_USER,
        "password": PROXY_PASS,
    }

    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(
            headless=True,
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
                "--js-flags=--max-old-space-size=192",
            ],
            ignore_default_args=["--enable-automation"],
        )

        context = await browser.new_context(
            proxy=proxy_config,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )

        page = await context.new_page()
        all_bids_data = []

        print(f"[*] Navigating to {LOGIN_URL} via proxy ({PROXY_HOST}:{PROXY_PORT})...")
        try:
            proxy_login_ok = False
            try:
                await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=25000)
                print("[*] Waiting for login form to render...")
                username_input = page.locator("#userName")
                await username_input.wait_for(state="visible", timeout=15000)
                proxy_login_ok = True
            except Exception as proxy_err:
                print(
                    f"[!] Decodo proxy blocked or stalled on DemandStar login ({proxy_err}). "
                    "Falling back to direct connection...",
                    flush=True,
                )
                await context.close()
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                )
                page = await context.new_page()

            if not proxy_login_ok:
                await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=45000)
                print("[*] Waiting for login form to render (direct connection)...")
                username_input = page.locator("#userName")
                await username_input.wait_for(state="visible", timeout=45000)
            
            print("[*] Injecting credentials...")
            await username_input.fill(DEMANDSTAR_USER)
            await page.locator("#password").fill(DEMANDSTAR_PASS)
            
            print("[*] Submitting login form...")
            login_btn = page.locator("button[name='login'], button:has-text('Login')").first
            await login_btn.click()

            print("[*] Waiting for initial authentication routing...")
            for _ in range(10):
                await page.wait_for_timeout(2000)
                if "dashboard" in page.url or "suppliers" in page.url:
                    break

            for _ in range(3):
                try:
                    not_now_btn = page.locator("button:has-text('Not Now'), .modal-footer button").first
                    if await not_now_btn.is_visible(timeout=2000):
                        print("[*] Dismissing 'Not Now' prompt...")
                        await not_now_btn.click(force=True)
                        await page.wait_for_timeout(1000)
                    close_x = page.locator(".modal-header button.close, button[aria-label='Close']").first
                    if await close_x.is_visible(timeout=1000):
                        print("[*] Closing notification modal...")
                        await close_x.click(force=True)
                        await page.wait_for_timeout(1000)
                except Exception:
                    pass

            print("[*] Routing to 'Bids' tab...")
            bids_link = page.get_by_text("Bids", exact=True).first
            try:
                await bids_link.wait_for(state="visible", timeout=10000)
                await bids_link.click(force=True)
            except Exception:
                print("[*] Navigating directly to Bids tab...")
                await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)

            print("[*] Waiting for bid table to populate...")
            await page.wait_for_timeout(8000)

            try:
                close_tour_btn = page.locator(".reactour__close").first
                if await close_tour_btn.is_visible(timeout=5000):
                    await close_tour_btn.click(force=True)
                    await page.locator("#___reactour").wait_for(state="hidden", timeout=5000)
            except Exception:
                pass
            
            print("[*] Typing 'software' into the Bid Name filter to target IT/software municipal bids...")
            try:
                search_input = page.locator("input[name='bidName'], input[placeholder='Bid Name']").first
                if not await search_input.is_visible():
                    adv_toggle = page.get_by_text("Advanced Search").first
                    if await adv_toggle.is_visible(timeout=3000):
                        await adv_toggle.click(force=True)
                        await page.wait_for_timeout(1000)

                await search_input.wait_for(state="visible", timeout=10000)
                
                if await search_input.is_editable():
                    await search_input.click() 
                    await page.wait_for_timeout(500)
                    await search_input.fill("software")
                    await page.wait_for_timeout(500)
                    
                    search_btn = page.locator("button.bttn-primary:has-text('Search')").first
                    if await search_btn.is_visible(timeout=3000):
                        await search_btn.click(force=True)
                    else:
                        await search_input.press("Enter")

                    print("[*] Search submitted. Waiting 8 seconds for tech bids to load...")
                    await page.wait_for_timeout(8000)
                else:
                    print("[!] Editable Bid Name search bar not found, proceeding with default feed.")
            except Exception as e:
                err_msg = f"DemandStar keyword search error: {e}"
                print(f"[!] {err_msg}")
                try:
                    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                        f.write(f"\n[!] {err_msg}\n")
                except Exception:
                    pass
                send_discord_alert(err_msg)
            
            print(f"[*] Beginning extraction for up to {MAX_PAGES} pages...")
            
            for current_page in range(1, MAX_PAGES + 1):
                print(f"\n[*] Parsing Page {current_page}...")
                
                try:
                    await page.wait_for_selector(".listGroupWrapper", timeout=45000)
                except Exception as sel_err:
                    print(f"[!] Bids failed to render on Page {current_page}. Site glitch or end of results detected. Stopping extraction early to save existing data.")
                    if current_page == 1 and not all_bids_data:
                        err_msg = f"DemandStar fatal UI timeout on Page 1: {sel_err}"
                        try:
                            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                                f.write(f"\n[!] {err_msg}\n")
                        except Exception:
                            pass
                        send_discord_alert(err_msg)
                        try:
                            await page.screenshot(path=ERROR_SCREENSHOT_PATH, full_page=True)
                        except Exception:
                            pass
                    break 
                
                page_data = await page.evaluate(r'''() => {
                    const rows = document.querySelectorAll('.listGroupWrapper');
                    const data = [];
                    
                    rows.forEach(row => {
                        const h5El = row.querySelector('h5');
                        const titleEl = row.querySelector('h5 a');
                        
                        // Extract full untruncated title from title attribute if available, falling back to text
                        let title = '';
                        if (h5El && h5El.getAttribute('title')) {
                            title = h5El.getAttribute('title').trim();
                        } else if (titleEl && titleEl.getAttribute('title')) {
                            title = titleEl.getAttribute('title').trim();
                        } else if (titleEl) {
                            title = titleEl.innerText.trim();
                        } else if (h5El) {
                            title = h5El.innerText.trim();
                        }
                        
                        let link = titleEl ? titleEl.getAttribute('href') : '';
                        if (link && link.startsWith('/')) {
                            link = 'https://www.demandstar.com' + link;
                        }
                        
                        const agencyEl = row.querySelector('ul.d-flex p, .agencyText, p.text-muted');
                        const agency = agencyEl ? agencyEl.innerText.trim() : '';
                        
                        let bid_id = '', broadcast_date = '', due_date = '';
                        const metaItems = row.querySelectorAll('ul.list-inline li');
                        
                        metaItems.forEach(item => {
                            const text = (item.innerText || '').trim();
                            if (text.includes('ID:')) {
                                bid_id = text.replace(/.*ID:\s*/i, '').trim();
                            }
                            if (text.includes('Broadcast:')) {
                                broadcast_date = text.replace(/.*Broadcast:\s*/i, '').trim();
                            }
                            if (text.includes('Due:')) {
                                due_date = text.replace(/.*Due:\s*/i, '').trim();
                            }
                        });
                        
                        if (title) {
                            data.push({ 
                                title: title, 
                                agency: agency, 
                                bid_id: bid_id, 
                                broadcast_date: broadcast_date, 
                                due_date: due_date, 
                                link: link 
                            });
                        }
                    });
                    return data;
                }''')
                
                all_bids_data.extend(page_data)
                print(f"[+] Extracted {len(page_data)} bids from Page {current_page}.")

                if current_page == MAX_PAGES:
                    break

                next_button = page.locator(".pagingWrapper .mdi-chevron-right").first
                if await next_button.is_visible():
                    print(f"[*] Clicking 'Next Page'...")
                    await next_button.click(force=True)
                    await page.wait_for_timeout(6000)
                else:
                    break

            print(f"\n[*] Scrape complete. Formatting {len(all_bids_data)} records for Supabase...")
            
            candidate_records = []
            for item in all_bids_data:
                bid_id = item.get("bid_id", "").strip()
                if bid_id and bid_id.lower() != "n/a":
                    raw_title = item.get("title", "").strip()
                    if not raw_title or is_commodity_it_spam(raw_title):
                        continue
                    title_lower = raw_title.lower()
                    
                    if any(re.search(pattern, title_lower) for pattern in tech_keywords):
                        formatted_title, clean_due = format_title_and_due(raw_title, item.get("due_date", ""))
                        if not formatted_title or is_commodity_it_spam(formatted_title):
                            continue

                        contract_url = item.get("link", "").strip() or f"https://www.demandstar.com/app/suppliers/bids#{bid_id}"

                        candidate_records.append({
                            "title": formatted_title,
                            "agency": item.get("agency") or "Municipal / Local Agency",
                            "closing_date": clean_due if clean_due else None,
                            "url": contract_url,
                            "status": "New Lead"
                        })

            if candidate_records and client:
                try:
                    print(f"[*] Validating {len(candidate_records)} DemandStar candidates via Anthropic B2B quality filter...", flush=True)
                    snippet = json.dumps(
                        [{"title": r["title"], "closing_date": r["closing_date"] or "", "contact_email": ""} for r in candidate_records]
                    )
                    llm_resp = await client.messages.create(
                        model="claude-sonnet-5-5",
                        max_tokens=8000,
                        system=B2B_EXTRACTION_SYSTEM_PROMPT,
                        messages=[
                            {"role": "user", "content": f"Filter and return ONLY high-value B2B IT contracts from this candidate list:\n\n{snippet}"}
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
                    approved_norms = {_normalize_title_for_similarity(a.get("title", "")) for a in approved if a.get("title")}
                    supabase_records = [
                        r for r in candidate_records
                        if _normalize_title_for_similarity(r["title"]) in approved_norms
                    ]
                    print(f"[+] B2B LLM validation approved {len(supabase_records)} of {len(candidate_records)} DemandStar contracts.", flush=True)
                except Exception as llm_err:
                    err_msg = f"DemandStar Claude B2B validation error: {llm_err}"
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

            supabase_records = list({r["url"]: r for r in supabase_records}.values())
            # Programmatic 85% fuzzy title deduplication to prevent catalog-dump spam
            supabase_records = fuzzy_deduplicate_records(supabase_records, threshold=0.85)

            if push_to_db:
                if supabase_records:
                    print(f"[*] Pushing {len(supabase_records)} tech-verified records to Supabase -> {TABLE_NAME}...")
                    try:
                        db_client = supabase or create_client(SUPABASE_URL, SUPABASE_KEY)
                        response = db_client.table(TABLE_NAME).upsert(
                            supabase_records, on_conflict="url", ignore_duplicates=True
                        ).execute()
                        new_records = response.data if response and getattr(response, "data", None) else []
                        skipped_count = len(supabase_records) - len(new_records)
                        print(f"[+] Successfully synced data to Supabase! Added {len(new_records)} new records (skipped {skipped_count} duplicates).")

                        for rec in new_records:
                            send_discord_content(rec)
                    except Exception as supabase_err:
                        err_msg = f"DemandStar Supabase insert error: {supabase_err}"
                        print(f"[!] {err_msg}")
                        try:
                            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                                f.write(f"\n[!] {err_msg}\n")
                        except Exception:
                            pass
                        send_discord_alert(err_msg)
                else:
                    print("[!] No valid tech records found to push from this run.")
            else:
                print(f"[+] SLED (DemandStar) extraction complete: {len(supabase_records)} tech contracts ready for master orchestrator.")

        except PlaywrightTimeoutError as te:
            error_msg = f"DemandStar Playwright TimeoutError: {te}"
            print(f"[!] {error_msg}")
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {error_msg}\n")
            except Exception:
                pass
            send_discord_alert(error_msg)
            try:
                await page.screenshot(path=ERROR_SCREENSHOT_PATH, full_page=True)
                print("[+] Saved error_debug.png to root directory.")
            except Exception as ss_e:
                print(f"[!] Could not save screenshot: {ss_e}")
        except Exception as e:
            error_msg = f"DemandStar Error during extraction: {e}"
            print(f"[!] {error_msg}")
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {error_msg}\n")
            except Exception:
                pass
            send_discord_alert(error_msg)
            try:
                await page.screenshot(path=ERROR_SCREENSHOT_PATH, full_page=True)
                print("[+] Saved error_debug.png to root directory.")
            except Exception as ss_e:
                print(f"[!] Could not save screenshot: {ss_e}")
        finally:
            await browser.close()

    return supabase_records

if __name__ == "__main__":
    asyncio.run(run_scraper())