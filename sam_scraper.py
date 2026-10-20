import os
import asyncio
import re
import time
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Load environment variables
load_dotenv(dotenv_path=".env")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DISCORD_CONTENT_WEBHOOK_URL = os.getenv("DISCORD_CONTENT_WEBHOOK_URL")
ERROR_LOG_PATH = "error_log.txt"
ERROR_SCREENSHOT_PATH = "error_debug.png"

# Supabase Configuration
TABLE_NAME = "contracts"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

def send_discord_alert(message):
    if not DISCORD_WEBHOOK_URL:
        print(" -> ERROR: Webhook URL not found in .env file.", flush=True)
        return
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json={"content": f"**[ALERT] Federal Pipeline Alert:**\n{message}"})
        response.raise_for_status()
        print(" -> Discord alert sent successfully.", flush=True)
    except Exception as e:
        print(f" -> Failed to send Discord alert: {e}", flush=True)

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

# Base SAM.gov Active Opportunities URL
TARGET_URL = "https://sam.gov/search/?index=opp&page=1&sort=-modifiedDate&sfm%5Bstatus%5D%5Bis_active%5D=true"

# Tech filter used in SLED scraper
tech_keywords = [
    r"\bit\b", r"cyber(security)?", r"software", r"network", r"computer", 
    r"server", r"infosec", r"audio/visual", r"hardware", 
    r"technology", r"cloud", r"broadband", r"telecom", r"fiber",
    r"saas", r"data", r"system", r"digital", r"platform", r"web", r"infrastructure"
]

async def run_scraper(push_to_db: bool = True):
    import gc

    supabase_records = []
    valid_opps = []
    seen_links = set()
    MAX_PAGES = 3
    current_page = 1

    async with Stealth().use_async(async_playwright()) as p:
        print("[*] Launching browser (Direct connection)...")
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
                "--disk-cache-size=1",
                "--media-cache-size=1",
                "--js-flags=--max-old-space-size=128",
            ],
            ignore_default_args=["--enable-automation"],
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1024, "height": 600},
        )
        await context.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in ("image", "media", "font")
            else route.continue_(),
        )

        page = await context.new_page()

        print(f"[*] Navigating to SAM.gov...")
        try:
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for SAM.gov's heavy Angular frontend to settle
            await page.wait_for_timeout(5000)
            
            # DOM Manipulation: If we land on the "Set Your Search Criteria" screen, force the search
            try:
                # Look for the left-panel keyword search box using its unique placeholder text
                search_box = page.locator('input[placeholder*="W91QVN"]')
                if await search_box.is_visible(timeout=3000):
                    print("[*] Empty search state detected. Injecting keywords and hitting Enter...")
                    await search_box.fill("cybersecurity")
                    await search_box.press("Enter")
                    # Give it time to load the results after pressing enter
                    await page.wait_for_timeout(5000)
            except Exception:
                pass # If the box isn't there, it means results already loaded

            for current_page in range(1, MAX_PAGES + 1):
                print(f"[*] Scraping Page {current_page} of {MAX_PAGES}...")
                print("[*] Waiting for federal results to populate...")
                await page.wait_for_selector('a[href*="/opp/"]', timeout=45000)
                await page.wait_for_timeout(3000)

                opportunities = await page.locator('a[href*="/opp/"]').all()
                page_opps_count = 0

                for opp in opportunities:
                    text = await opp.inner_text()
                    text = text.strip()
                    if len(text) > 5 and text.lower() != "view":
                        link_path = await opp.get_attribute('href')
                        if link_path and link_path not in seen_links:
                            valid_opps.append((text, link_path))
                            seen_links.add(link_path)
                            page_opps_count += 1

                print(f"[+] Page {current_page}: Extracted {page_opps_count} opportunities. Total collected so far: {len(valid_opps)}")

                if current_page < MAX_PAGES:
                    next_button = page.locator('#bottomPagination-nextPage, button:has-text("Next Page"), [id*="nextPage"]').first
                    if await next_button.is_visible(timeout=5000):
                        print(f"[*] Clicking 'Next' button to navigate to page {current_page + 1}...")
                        await next_button.scroll_into_view_if_needed()
                        await next_button.click()
                        await page.wait_for_timeout(5000)
                    else:
                        print(f"[!] 'Next' button not visible on page {current_page}. Stopping pagination.")
                        break

        except Exception as e:
            print(f"\n[!] Error during extraction: {e}")
            send_discord_alert(f"SAM.gov scraper failed: {e}")
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] SAM.gov Error during extraction: {e}\n")
            except Exception:
                pass
            try:
                print("[*] Taking error screenshot for debugging...")
                await page.screenshot(path=ERROR_SCREENSHOT_PATH, full_page=True)
                print(f"[+] Saved {ERROR_SCREENSHOT_PATH}. Please upload this file so we can see what the browser is stuck on.")
            except Exception as ss_e:
                print(f"[!] Could not save screenshot: {ss_e}")
        finally:
            print("[*] Closing browser.")
            await browser.close()

    # Release Chromium + Playwright Node driver memory before processing
    gc.collect()

    print(f"[*] Extracted {len(valid_opps)} raw contracts across {min(current_page, MAX_PAGES)} pages. Filtering for tech validation...")

    supabase_records = []
    sam_exclusions = [
        r"^\s*\d{2,4}\s*--",
        r"^\s*assorted\s+hardware\s*$",
        r"interface\s+unit,\s*data",
        r"missile\s+warning",
        r"dc\s+and\s+ac\s+preferred\s+systems",
        r"circuit\s+card\s+assembly",
        r"cable\s+assembly",
        r"wiring\s+harness",
        r"\bink\b",
        r"\btoner\b",
        r"cartridge",
    ]
    for title, link_path in valid_opps:
        title_lower = title.lower()
        if any(re.search(ex, title_lower) for ex in sam_exclusions):
            continue

        # Double-check against our regex to ensure it's a valid IT/Cyber lead
        if any(re.search(pattern, title_lower) for pattern in tech_keywords):
            full_link = "https://sam.gov" + str(link_path)

            supabase_records.append({
                "title": title,
                "agency": "Federal Government (SAM)",
                "closing_date": None,
                "url": full_link,
                "status": "New Lead"
            })

    supabase_records = list({r["url"]: r for r in supabase_records}.values())

    if push_to_db:
        if supabase_records:
            if not SUPABASE_URL or not SUPABASE_KEY:
                print("[!] Found IT/Cyber contracts, but SUPABASE_URL or SUPABASE_KEY is missing. Cannot push data.")
            else:
                print(f"[*] Found {len(supabase_records)} tech contracts! Pushing to Supabase...")
                db_client = supabase or create_client(SUPABASE_URL, SUPABASE_KEY)
                response = db_client.table(TABLE_NAME).upsert(
                    supabase_records, on_conflict="url", ignore_duplicates=True
                ).execute()
                new_records = response.data if response and getattr(response, "data", None) else []
                skipped_count = len(supabase_records) - len(new_records)
                print(f"[+] Successfully synced Federal data to Supabase! Added {len(new_records)} new records (skipped {skipped_count} duplicates).")

                for rec in new_records:
                    send_discord_content(rec)
        else:
            print("[-] No IT/Cyber contracts found across scraped pages this run.")
    else:
        print(f"[+] Federal (SAM.gov) extraction complete: {len(supabase_records)} tech contracts ready for master orchestrator.")

    return supabase_records

if __name__ == "__main__":
    asyncio.run(run_scraper())