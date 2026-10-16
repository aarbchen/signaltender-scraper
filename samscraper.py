import os
import asyncio
import re
import requests
from dotenv import load_dotenv
from pyairtable import Api
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Load environment variables
load_dotenv(dotenv_path=r"D:\Daas\.env")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_PAT")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Airtable Configuration
BASE_ID = "appRtnHZ9HeDcr0hu"
TABLE_NAME = "Contracts"

def send_discord_alert(message):
    if not DISCORD_WEBHOOK_URL:
        print(" -> ERROR: Webhook URL not found in .env file.", flush=True)
        return
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json={"content": f"🚨 **Federal Pipeline Alert:**\n{message}"})
        response.raise_for_status()
        print(" -> Discord alert sent successfully.", flush=True)
    except Exception as e:
        print(f" -> Failed to send Discord alert: {e}", flush=True)

# Base SAM.gov Active Opportunities URL
TARGET_URL = "https://sam.gov/search/?index=opp&page=1&sort=-modifiedDate&sfm%5Bstatus%5D%5Bis_active%5D=true"

# Tech filter used in SLED scraper
tech_keywords = [
    r"\bit\b", r"cyber(security)?", r"software", r"network", r"computer", 
    r"server", r"infosec", r"audio/visual", r"hardware", 
    r"technology", r"cloud", r"broadband", r"telecom", r"fiber",
    r"saas", r"data", r"system", r"digital", r"platform", r"web", r"infrastructure"
]

async def run_scraper():
    async with Stealth().use_async(async_playwright()) as p:
        print("[*] Launching browser (Direct connection)...")
        browser = await p.chromium.launch(
            channel="msedge",
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            ignore_default_args=["--enable-automation"],
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
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
            
            valid_opps = []
            seen_links = set()
            MAX_PAGES = 3

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

            print(f"[*] Extracted {len(valid_opps)} raw contracts across {min(current_page, MAX_PAGES)} pages. Filtering for tech validation...")

            airtable_records = []
            for title, link_path in valid_opps:
                title_lower = title.lower()

                # Double-check against our regex to ensure it's a valid IT/Cyber lead
                if any(re.search(pattern, title_lower) for pattern in tech_keywords):
                    full_link = "https://sam.gov" + str(link_path)

                    bid_id_match = re.search(r'/opp/([a-f0-9]+)/', link_path)
                    bid_id = bid_id_match.group(1) if bid_id_match else "SAM-UNKNOWN"

                    airtable_records.append({
                        "fields": {
                            "Bid ID": bid_id,
                            "Title": title,
                            "Agency": "Federal Government (SAM)",
                            "Source URL": full_link,
                            "Status": "New Lead"
                        }
                    })

            if airtable_records:
                if not AIRTABLE_API_KEY:
                     print("[!] Found IT/Cyber contracts, but AIRTABLE_API_KEY is missing. Cannot push data.")
                else:
                    print(f"[*] Found {len(airtable_records)} tech contracts! Pushing to Airtable...")
                    api = Api(AIRTABLE_API_KEY)
                    table = api.table(BASE_ID, TABLE_NAME)
                    table.batch_upsert(airtable_records, key_fields=["Bid ID"])
                    print("[+] Successfully synced Federal data to Airtable!")
            else:
                print("[-] No IT/Cyber contracts found across scraped pages this run.")

        except Exception as e:
            print(f"\n[!] Error during extraction: {e}")
            send_discord_alert(f"SAM.gov scraper failed: {e}")
            try:
                with open(r"D:\Daas\error_log.txt", "a", encoding="utf-8") as f:
                    f.write(f"\n[!] SAM.gov Error during extraction: {e}\n")
            except Exception:
                pass
            try:
                print("[*] Taking error screenshot for debugging...")
                await page.screenshot(path="sam_gov_error.png", full_page=True)
                print("[+] Saved sam_gov_error.png. Please upload this file so we can see what the browser is stuck on.")
            except Exception as ss_e:
                print(f"[!] Could not save screenshot: {ss_e}")
        finally:
            print("[*] Closing browser.")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_scraper())