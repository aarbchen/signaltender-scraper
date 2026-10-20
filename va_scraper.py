import os
import json
import asyncio
import re
import time
from datetime import datetime
from difflib import SequenceMatcher
from urllib.parse import quote
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

# Virginia eVA Public Procurement Portal (VBO - Virginia Business Opportunities)
EVA_BASE_URL = "https://mvendor.cgieva.com/Vendor/public/AllOpportunities.jsp"
EVA_TECH_CATEGORIES = [
    "Non-professional Services - Technology",
    "Equipment - Technology",
    "Supplies - Technology",
]
EVA_SEARCH_KEYWORDS = ["IT", "software", "cybersecurity"]

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
            f"[*] Virginia eVA Fuzzy Deduplication: Dropped {dropped_count} near-duplicate spam record(s) "
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
            json={"content": f"**[ALERT] Virginia eVA Scraper Alert:**\n{message}"},
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
    """Normalize extracted date strings into MM/DD/YYYY format, or empty if invalid."""
    if not date_str:
        return ""
    date_str = str(date_str).strip()
    if date_str.lower() in ["n/a", "tbd", "none", "null", "undefined", "tba", ""]:
        return ""

    # Handle ISO-8601 timestamps from eVA Solr (e.g., '2026-10-23T10:00:00Z')
    if "T" in date_str:
        iso_date = date_str.split("T")[0]
        try:
            dt = datetime.strptime(iso_date, "%Y-%m-%d")
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            pass

    for fmt in (
        "%m/%d/%y %I:%M %p",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%y",
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%b %d, %Y",
        "%B %d, %Y",
    ):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            pass

    date_part = date_str.split(" ")[0]
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", date_part)
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
    clean_title = re.sub(r"[\s\-\(]*Due:?\s*N/A\)?", "", clean_title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r"[\s\-]+$", "", clean_title).strip()

    clean_date = format_date_clean(raw_date)
    if clean_date:
        return f"{clean_title} - Due: {clean_date}", clean_date
    else:
        return clean_title, ""


def build_eva_opportunity_url(doc: dict) -> str:
    """Construct the direct Virginia eVA solicitation detail URL matching AllOpportunitiesapp.js."""
    app = str(doc.get("app") or "IV").strip()
    doccd = str(doc.get("doccd") or "").strip()
    dept = str(doc.get("docdeptcd") or doc.get("agency") or "").strip()
    ext_id = str(doc.get("externalid") or "").strip()
    int_id = str(doc.get("internalid") or ext_id).strip()
    version = str(doc.get("version") or "0").strip()

    if app == "QQ" and ext_id:
        return f"https://mvendor.cgieva.com/Vendor/public/QQDetails.jsp?PageTitle=QQ%20Details&REQUEST_ID={quote(ext_id)}"
    elif app == "ADV" and ext_id:
        return (
            f"https://mvendor.cgieva.com/Vendor/public/ADVSODetails.jsp?PageTitle=SO%20Details"
            f"&DOC_CD={quote(doccd)}&Details_Page=ADVSODetails.jsp&DEPT_CD={quote(dept)}"
            f"&BID_INTRNL_NO={quote(ext_id)}&BID_NO={quote(ext_id)}&BID_VERS_NO={quote(version)}"
        )
    elif app == "VBO" and ext_id:
        return (
            f"https://mvendor.cgieva.com/Vendor/public/VBODetails.jsp?PageTitle=SO%20Details"
            f"&DOC_CD={quote(doccd)}&Details_Page=VBOSODetails.jsp&DEPT_CD={quote(dept)}"
            f"&BID_INTRNL_NO={quote(ext_id)}&BID_NO={quote(ext_id)}&BID_VERS_NO={quote(version)}"
        )
    elif ext_id:
        return (
            f"https://mvendor.cgieva.com/Vendor/public/IVDetails.jsp?PageTitle=SO%20Details"
            f"&rfp_id_lot={quote(ext_id)}&rfp_id_round={quote(int_id)}"
        )
    return EVA_BASE_URL


async def _extract_dom_cards(page) -> list[dict]:
    """Fallback DOM extractor for Virginia eVA opportunity cards rendered inside #alloppsearcharea."""
    try:
        cards = await page.evaluate(
            """() => {
                const results = [];
                const cardEls = document.querySelectorAll('#alloppsearcharea .card.text-center');
                cardEls.forEach(card => {
                    const headerTitleEl = card.querySelector('.card-header h5.card-title');
                    const solIdEl = card.querySelector('.card-body h6.card-title');
                    const agencyEl = card.querySelector('.card-body p.card-text.text-muted');
                    const longDescEl = card.querySelector('.card-body p#longdescription');

                    let rawTitle = headerTitleEl ? headerTitleEl.innerText.trim() : '';
                    const solId = solIdEl ? solIdEl.innerText.trim() : '';
                    const agency = agencyEl ? agencyEl.innerText.trim() : 'Commonwealth of Virginia';
                    const longDesc = longDescEl ? longDescEl.innerText.trim() : '';

                    // If card header title is truncated with '...' and longDesc starts with title/purpose, preserve clean title
                    if (rawTitle.endsWith('...') && longDesc && longDesc.length < 180) {
                        rawTitle = longDesc;
                    }

                    let dueDate = '';
                    const bodyText = card.innerText || '';
                    const dueMatch = bodyText.match(/Closing On:\\s*([^\\n\\r]+)/i);
                    if (dueMatch && dueMatch[1]) {
                        dueDate = dueMatch[1].trim();
                    }

                    // Extract numeric external ID from solicitation string (e.g., 'RFP 130041' or 'IFB 128866-7')
                    let extId = '';
                    const idMatch = solId.match(/(\\d+)/);
                    if (idMatch) {
                        extId = idMatch[1];
                    }

                    if (rawTitle && extId) {
                        results.push({
                            shortdesc: rawTitle,
                            agencyname: agency,
                            closedate: dueDate,
                            externalid: extId,
                            internalid: extId,
                            app: 'IV',
                            longdesc: longDesc
                        });
                    }
                });
                return results;
            }"""
        )
        return cards or []
    except Exception:
        return []


async def run_scraper(push_to_db: bool = True) -> list[dict]:
    import gc
    supabase_records = []
    if push_to_db and (not SUPABASE_URL or not SUPABASE_KEY):
        print("[!] ERROR: SUPABASE_URL or SUPABASE_KEY not found in .env", flush=True)
        return supabase_records

    captured_docs_by_id = {}

    async with Stealth().use_async(async_playwright()) as p:
        print("[*] Launching Stealth browser for Virginia eVA (VBO)...", flush=True)
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

        async def handle_solr_response(response):
            if "solrconnect.jsp" in response.url and response.status == 200:
                try:
                    text_body = await response.text()
                    payload = json.loads(text_body)
                    docs = payload.get("response", {}).get("docs", [])
                    for doc in docs:
                        if str(doc.get("status", "Open")).lower() != "open":
                            continue
                        uid = str(doc.get("id") or doc.get("externalid") or "")
                        if uid:
                            captured_docs_by_id[uid] = doc
                except Exception:
                    pass

        page.on("response", lambda r: asyncio.create_task(handle_solr_response(r)))

        try:
            # 1. Navigate to Virginia eVA VBO Technology Categories
            for category in EVA_TECH_CATEGORIES:
                cat_url = f"{EVA_BASE_URL}?status=Open&category={quote(category)}"
                print(f"[*] Virginia eVA: Navigating to category '{category}'...", flush=True)
                await page.goto(cat_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_selector("#alloppsearcharea", timeout=30000)
                await page.wait_for_timeout(4000)

                # Scroll down to trigger additional cursor-paginated batches in eVA VBO
                for _ in range(2):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)

                dom_cards = await _extract_dom_cards(page)
                for dc in dom_cards:
                    uid = f"DOM-{dc['externalid']}"
                    if uid not in captured_docs_by_id and f"IV{dc['externalid']}" not in captured_docs_by_id:
                        captured_docs_by_id[uid] = dc

            # 2. Navigate to Open Opportunities and run keyword searches for IT, software, cybersecurity
            open_url = f"{EVA_BASE_URL}?status=Open"
            print("[*] Virginia eVA: Navigating to Open Opportunities for keyword filtering...", flush=True)
            await page.goto(open_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_selector("#topNavInputField input", timeout=30000)
            await page.wait_for_timeout(3000)

            for kw in EVA_SEARCH_KEYWORDS:
                print(f"[*] Virginia eVA: Searching keyword '{kw}'...", flush=True)
                search_input = page.locator("#topNavInputField input").first
                search_btn = page.locator("#topNavInputField button").first

                if await search_input.is_visible(timeout=5000):
                    await search_input.fill(kw)
                    await search_btn.click()
                    await page.wait_for_timeout(4000)

                    # Scroll once to load additional results for the keyword
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)

                    dom_cards = await _extract_dom_cards(page)
                    for dc in dom_cards:
                        uid = f"DOM-{dc['externalid']}"
                        if uid not in captured_docs_by_id and f"IV{dc['externalid']}" not in captured_docs_by_id:
                            captured_docs_by_id[uid] = dc

        except PlaywrightTimeoutError as te:
            error_msg = f"Virginia eVA Playwright TimeoutError: {te}"
            print(f"[!] {error_msg}", flush=True)
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {error_msg}\n")
            except Exception:
                pass
            send_discord_alert(error_msg)
            try:
                await page.screenshot(path=ERROR_SCREENSHOT_PATH, full_page=True)
                print("[+] Saved error_debug.png to root directory.", flush=True)
            except Exception as ss_e:
                print(f"[!] Could not save screenshot: {ss_e}", flush=True)
        except Exception as e:
            error_msg = f"Virginia eVA Error during extraction: {e}"
            print(f"[!] {error_msg}", flush=True)
            try:
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n[!] {error_msg}\n")
            except Exception:
                pass
            send_discord_alert(error_msg)
            try:
                await page.screenshot(path=ERROR_SCREENSHOT_PATH, full_page=True)
                print("[+] Saved error_debug.png to root directory.", flush=True)
            except Exception as ss_e:
                print(f"[!] Could not save screenshot: {ss_e}", flush=True)
        finally:
            await browser.close()

    # Browser & Playwright Node driver are now 100% closed before LLM validation
    gc.collect()

    print(
        f"[*] Virginia eVA: Captured {len(captured_docs_by_id)} unique open solicitation(s). "
        "Applying tech regex and B2B quality filters...",
        flush=True,
    )

    candidate_records = []
    for uid, doc in captured_docs_by_id.items():
        raw_title = str(doc.get("shortdesc") or "").strip()
        if not raw_title or is_commodity_it_spam(raw_title):
            continue

        long_desc = str(doc.get("longdesc") or "").strip()
        category_str = str(doc.get("category") or "").strip()
        combined_text = f"{raw_title} {category_str} {long_desc}".lower()

        # Strict regex filtering protocol from project_rules.md
        if any(re.search(pattern, combined_text) for pattern in tech_keywords):
            formatted_title, clean_due = format_title_and_due(raw_title, str(doc.get("closedate") or ""))
            if not formatted_title or is_commodity_it_spam(formatted_title):
                continue

            agency_name = str(doc.get("agencyname") or "").strip() or "Commonwealth of Virginia"
            contract_url = build_eva_opportunity_url(doc)

            candidate_records.append(
                {
                    "title": formatted_title,
                    "agency": agency_name,
                    "closing_date": clean_due if clean_due else None,
                    "url": contract_url,
                    "status": "New Lead",
                }
            )

    # Validate candidates through Anthropic B2B quality control prompt if client is configured
    if candidate_records and client:
        try:
            print(
                f"[*] Validating {len(candidate_records)} Virginia eVA candidates via Anthropic B2B quality filter...",
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
                f"[+] B2B LLM validation approved {len(supabase_records)} of {len(candidate_records)} Virginia eVA contracts.",
                flush=True,
            )
        except Exception as llm_err:
            err_msg = f"Virginia eVA Claude B2B validation error: {llm_err}"
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
                f"[*] Pushing {len(supabase_records)} tech-verified Virginia eVA records to Supabase -> {TABLE_NAME}...",
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
                    f"[+] Successfully synced Virginia eVA data to Supabase! "
                    f"Added {len(new_records)} new records (skipped {skipped_count} duplicates).",
                    flush=True,
                )

                for rec in new_records:
                    send_discord_content(rec)
            except Exception as supabase_err:
                err_msg = f"Virginia eVA Supabase insert error: {supabase_err}"
                print(f"[!] {err_msg}", flush=True)
                try:
                    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                        f.write(f"\n[!] {err_msg}\n")
                except Exception:
                    pass
                send_discord_alert(err_msg)
        else:
            print("[!] No valid Virginia eVA tech records found to push from this run.", flush=True)
    else:
        print(
            f"[+] Virginia SLED (eVA) extraction complete: {len(supabase_records)} tech contracts ready for master orchestrator.",
            flush=True,
        )

    return supabase_records


if __name__ == "__main__":
    asyncio.run(run_scraper())

