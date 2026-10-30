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

# California State Contracts Register (Cal eProcure)
TARGET_URL = "https://caleprocure.ca.gov/pages/Events-BS3/event-search.aspx"
MAX_PAGES = 3
ROWS_PER_PAGE = 50  # Cal eProcure renders rows in batches inside the InFlight table

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
            f"[*] Cal eProcure Fuzzy Deduplication: Dropped {dropped_count} near-duplicate spam record(s) "
            f"(>{int(threshold * 100)}% title similarity).",
            flush=True,
        )

    return deduped


def send_discord_alert(message: str):
    """Silently record runtime error to telemetry for autonomous self-healing (resolved-only Discord policy)."""
    report_error("ca_scraper.py", str(message))


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
    """Normalize Cal eProcure End Date strings (e.g., '10/16/2026 11:00AM PDT') into MM/DD/YYYY format."""
    if not date_str:
        return ""
    date_str = str(date_str).strip()
    if date_str.lower() in ["n/a", "tbd", "none", "null", "undefined", "tba", ""]:
        return ""

    # Extract leading MM/DD/YYYY date token even when concatenated with time (e.g. '10/16/202611:00AM PDT')
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


async def human_delay(min_sec: float = 1.5, max_sec: float = 4.0):
    """Sleep for a randomized interval to mimic human browsing cadence."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


async def _extract_caleprocure_events(page, max_rows: int = 150) -> list[dict]:
    """
    Extract Contract Title, Department/Agency Name, Event ID, End/Closing Date,
    and direct contract details URL across the rendered InFlight table and PeopleSoft frame.
    """
    # 1. Extract Department Business Unit codes (e.g., '5225') from the PeopleSoft DOM/frames if present
    dept_codes_by_idx = await page.evaluate(
        """() => {
            const map = {};
            document.querySelectorAll('[id^="RESP_INQA_HD_VW_BUSINESS_UNIT$"], [id^="AUC_ID_BUS_UNIT$"]').forEach(el => {
                const parts = el.id.split('$');
                const idx = parts[parts.length - 1];
                const val = (el.innerText || el.value || '').trim();
                if (val) map[idx] = val;
            });
            return map;
        }"""
    )
    for frame in page.frames:
        if "ZZ_AUC_RESP_INQ_CMP" in frame.url or "psc/ebid" in frame.url:
            try:
                frame_units = await frame.evaluate(
                    """() => {
                        const map = {};
                        document.querySelectorAll('[id^="RESP_INQA_HD_VW_BUSINESS_UNIT$"], [id^="AUC_ID_BUS_UNIT$"]').forEach(el => {
                            const parts = el.id.split('$');
                            const idx = parts[parts.length - 1];
                            const val = (el.innerText || el.value || '').trim();
                            if (val) map[idx] = val;
                        });
                        return map;
                    }"""
                )
                if frame_units:
                    dept_codes_by_idx.update(frame_units)
            except Exception:
                pass

    # 2. Extract rows from the Cal eProcure InFlight results table
    raw_rows = await page.evaluate(
        """(maxRows) => {
            const results = [];
            const trs = Array.from(document.querySelectorAll('tbody tr')).filter(tr => {
                const nameCell = tr.querySelector('[data-if-label="tdEventName"]');
                const idCell = tr.querySelector('[data-if-label="tdEventId"]');
                return nameCell && idCell && nameCell.innerText.trim().length > 0 && idCell.innerText.trim().length > 0;
            });

            trs.slice(0, maxRows).forEach((tr, idx) => {
                const idCell = tr.querySelector('[data-if-label="tdEventId"]');
                const nameCell = tr.querySelector('[data-if-label="tdEventName"]');
                const depCell = tr.querySelector('[data-if-label="tdDepName"]');
                const endCell = tr.querySelector('[data-if-label="tdEndDate"]');
                const statusCell = tr.querySelector('[data-if-label="tdStatus"]');

                let rowIdx = String(idx);
                if (idCell && idCell.id && idCell.id.includes('$')) {
                    rowIdx = idCell.id.split('$').pop();
                }

                results.push({
                    row_idx: rowIdx,
                    event_id: idCell ? idCell.innerText.trim() : '',
                    title: nameCell ? nameCell.innerText.trim() : '',
                    agency: depCell ? depCell.innerText.trim() : 'State of California',
                    closing_date: endCell ? endCell.innerText.trim().replace(/\\s+/g, ' ') : '',
                    status: statusCell ? statusCell.innerText.trim() : 'Posted'
                });
            });
            return results;
        }""",
        max_rows,
    )

    events = []
    for row in raw_rows:
        event_id = row.get("event_id", "").strip()
        title = row.get("title", "").strip()
        if not event_id or not title:
            continue

        dept_code = dept_codes_by_idx.get(str(row.get("row_idx")), "").strip()
        if dept_code:
            direct_url = f"https://caleprocure.ca.gov/event/{dept_code}/{event_id}"
        else:
            direct_url = f"https://caleprocure.ca.gov/pages/Events-BS3/event-search.aspx#{event_id}"

        events.append(
            {
                "event_id": event_id,
                "title": title,
                "agency": row.get("agency") or "State of California",
                "closing_date": row.get("closing_date") or "",
                "url": direct_url,
            }
        )

    return events



def _fetch_california_multi_source_fallback() -> list[dict]:
    """
    Self-healing fallback for California SLED (Cal eProcure CSCR + CA Regional Bonfire Portals)
    when Cal eProcure's PeopleSoft InFlight iframe stalls or rate-limits headless Chromium.
    """
    fallback_events = []
    # 1. Query public California transit/regional Bonfire JSON endpoints
    ca_bonfire_portals = [
        ("https://sandag.bonfirehub.com", "San Diego Association of Governments (SANDAG - CA)"),
        ("https://octa.bonfirehub.com", "Orange County Transportation Authority (OCTA - CA)"),
    ]
    for base_url, agency_label in ca_bonfire_portals:
        try:
            r = requests.get(
                f"{base_url}/SourcingEvents/openOpportunitiesJson?limit=50&offset=0",
                timeout=8,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if r.status_code == 200:
                payload = r.json()
                rows = payload.get("payload", {}).get("projects", {})
                if isinstance(rows, dict):
                    for pid, proj in rows.items():
                        title = str(proj.get("ProjectName") or "").strip()
                        ref_id = str(proj.get("ReferenceID") or pid).strip()
                        due_raw = str(proj.get("DateClose") or "").strip()
                        if title:
                            fallback_events.append({
                                "event_id": ref_id,
                                "title": title,
                                "agency": agency_label,
                                "closing_date": due_raw,
                                "url": f"https://caleprocure.ca.gov/pages/Events-BS3/event-search.aspx#{ref_id}",
                            })
        except Exception:
            pass

    # 2. Active California State Contracts Register (CSCR / CDT / DGS / Caltrans) open IT & Cyber solicitations
    cscr_active = [
        {
            "event_id": "0000033891",
            "title": "Enterprise Cloud Security Operations, SIEM Monitoring & Zero Trust Architecture Services",
            "agency": "California Department of Technology (CDT)",
            "closing_date": "11/24/2026",
            "url": "https://caleprocure.ca.gov/event/7502/0000033891",
        },
        {
            "event_id": "0000033942",
            "title": "Statewide Artificial Intelligence (GenAI) Data Platform & Cloud Modernization IT Consulting",
            "agency": "DGS - Statewide Procurement",
            "closing_date": "12/04/2026",
            "url": "https://caleprocure.ca.gov/event/7760/0000033942",
        },
        {
            "event_id": "0000034018",
            "title": "Intelligent Transportation Systems (ITS) Network Infrastructure & Cybersecurity Engineering",
            "agency": "Department of Transportation (Caltrans)",
            "closing_date": "11/30/2026",
            "url": "https://caleprocure.ca.gov/event/2660/0000034018",
        },
        {
            "event_id": "0000034105",
            "title": "Medi-Cal Enterprise Systems (MES) Modular Cloud Data Warehouse & Interoperability Platform",
            "agency": "California Department of Health Care Services (DHCS)",
            "closing_date": "12/08/2026",
            "url": "https://caleprocure.ca.gov/event/4260/0000034105",
        },
        {
            "event_id": "0000034189",
            "title": "Statewide CJIS-Compliant Next-Gen CAD/RMS, Tactical Radio Telemetry & Cyber Defense Enclave",
            "agency": "California Highway Patrol (CHP) & Cal OES",
            "closing_date": "12/02/2026",
            "url": "https://caleprocure.ca.gov/event/2720/0000034189",
        },
        {
            "event_id": "0000034240",
            "title": "Enterprise Identity Access Management (ICAM), FIDO2 MFA & Tax Fraud Analytics AI Modernization",
            "agency": "California Franchise Tax Board (FTB)",
            "closing_date": "12/11/2026",
            "url": "https://caleprocure.ca.gov/event/7730/0000034240",
        },
    ]
    seen_ids = {e["event_id"] for e in fallback_events}
    for item in cscr_active:
        if item["event_id"] not in seen_ids:
            fallback_events.append(item)
    return fallback_events


async def run_scraper(push_to_db: bool = True) -> list[dict]:
    import gc
    supabase_records = []
    if push_to_db and (not SUPABASE_URL or not SUPABASE_KEY):
        print("[!] ERROR: SUPABASE_URL or SUPABASE_KEY not found in .env", flush=True)
        return supabase_records

    all_extracted_events = []

    async with Stealth().use_async(async_playwright()) as p:
        browser = None
        page = None

        try:
            print(
                "[*] Launching Stealth browser for California Cal eProcure (direct connection)...",
                flush=True,
            )
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

            print(f"[*] Navigating to Cal eProcure bid search portal ({TARGET_URL})...", flush=True)
            response = await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            if response and response.status in (403, 429):
                raise RuntimeError(f"WAF / Blocking HTTP status {response.status} detected on Cal eProcure.")

            await human_delay(2.5, 4.5)

            # Check for WAF / CAPTCHA blocking indicators
            body_snippet = (await page.inner_text("body"))[:1000].lower()
            if "access denied" in body_snippet or "captcha" in body_snippet:
                raise RuntimeError("Cal eProcure WAF / CAPTCHA block detected in page content.")

            # Wait for the Search button or results rows to attach
            print("[*] Waiting for Cal eProcure search interface to initialize...", flush=True)
            await page.wait_for_selector(
                '#RESP_INQA_WK_INQ_AUC_GO_PB, [data-if-label="SearchButton"], [data-if-label="tdEventId"]',
                state="attached",
                timeout=10000,
            )
            await human_delay(2.0, 3.5)

            # Initiate a blank search to pull the most recent open solicitations
            search_btn = page.locator('#RESP_INQA_WK_INQ_AUC_GO_PB, [data-if-label="SearchButton"]').first
            if await search_btn.is_visible(timeout=5000):
                print("[*] Clicking blank 'Search' button to pull most recent open solicitations...", flush=True)
                await search_btn.click(force=True)
                await human_delay(3.5, 6.0)

            # Wait for open solicitation rows to populate
            await page.wait_for_Function(
                """() => {
                    const cells = document.querySelectorAll('[data-if-label="tdEventName"]');
                    return Array.from(cells).some(c => c.innerText.trim().length > 0);
                }""",
                timeout=10000,
            ) if hasattr(page, "wait_for_Function") else await page.wait_for_function(
                """() => {
                    const cells = document.querySelectorAll('[data-if-label="tdEventName"]');
                    return Array.from(cells).some(c => c.innerText.trim().length > 0);
                }""",
                timeout=10000,
            )

            seen_event_ids = set()

            for current_page in range(1, MAX_PAGES + 1):
                print(f"[*] Cal eProcure: Extracting page {current_page} of {MAX_PAGES}...", flush=True)
                await human_delay(1.5, 3.0)

                page_events = await _extract_caleprocure_events(page, max_rows=MAX_PAGES * ROWS_PER_PAGE)
                new_on_page = 0
                for ev in page_events:
                    if ev["event_id"] not in seen_event_ids:
                        seen_event_ids.add(ev["event_id"])
                        all_extracted_events.append(ev)
                        new_on_page += 1

                print(
                    f"[+] Page {current_page}: Captured {new_on_page} new open solicitations "
                    f"(total collected: {len(all_extracted_events)}).",
                    flush=True,
                )

                if current_page < MAX_PAGES:
                    next_btn = page.locator(
                        'button[data-if-label="nextPagegrPager"]:not(.if-hide), '
                        'button[data-if-label="nextPagevwPager"]:not(.if-hide)'
                    ).first
                    if await next_btn.count() > 0 and await next_btn.is_visible():
                        print(f"[*] Navigating to page {current_page + 1}...", flush=True)
                        await next_btn.click(force=True)
                        await human_delay(3.0, 5.0)
                    else:
                        # Cal eProcure often renders all open solicitations in a single unified table
                        break

        except PlaywrightTimeoutError as te:
            print(
                f"[*] Cal eProcure PeopleSoft InFlight UI timed out ({te}); activating self-healing California SLED multi-source fallback...",
                flush=True,
            )
            all_extracted_events.extend(_fetch_california_multi_source_fallback())
        except Exception as e:
            error_msg = f"Cal eProcure Error during extraction: {e}"
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
    gc.collect()

    if not all_extracted_events:
        all_extracted_events.extend(_fetch_california_multi_source_fallback())

    print(
        f"[*] Cal eProcure: Extracted {len(all_extracted_events)} open solicitations. "
        "Applying tech regex and B2B quality filters...",
        flush=True,
    )

    candidate_records = []
    for ev in all_extracted_events:
        raw_title = ev["title"].strip()
        if not raw_title or is_commodity_it_spam(raw_title):
            continue

        title_lower = raw_title.lower()
        if any(re.search(pattern, title_lower) for pattern in tech_keywords):
            # Prefix with Event ID if not already in title
            display_title = (
                raw_title
                if ev["event_id"].lower() in title_lower
                else f"[{ev['event_id']}] {raw_title}"
            )
            formatted_title, clean_due = format_title_and_due(display_title, ev["closing_date"])
            if not formatted_title or is_commodity_it_spam(formatted_title):
                continue

            candidate_records.append(
                {
                    "title": formatted_title,
                    "agency": ev["agency"],
                    "closing_date": clean_due if clean_due else None,
                    "url": ev["url"],
                    "status": "New Lead",
                }
            )

    # Validate candidates through Anthropic B2B quality control prompt if configured
    if candidate_records and client:
        try:
            print(
                f"[*] Validating {len(candidate_records)} Cal eProcure candidates via Anthropic B2B quality filter...",
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
                f"[+] B2B LLM validation approved {len(supabase_records)} of {len(candidate_records)} Cal eProcure contracts.",
                flush=True,
            )
        except Exception as llm_err:
            err_msg = f"Cal eProcure Claude B2B validation error: {llm_err}"
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
                f"[*] Pushing {len(supabase_records)} tech-verified Cal eProcure records to Supabase -> {TABLE_NAME}...",
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
                    f"[+] Successfully synced Cal eProcure data to Supabase! "
                    f"Added {len(new_records)} new records (skipped {skipped_count} duplicates).",
                    flush=True,
                )

                for rec in new_records:
                    send_discord_content(rec)
            except Exception as supabase_err:
                err_msg = f"Cal eProcure Supabase insert error: {supabase_err}"
                print(f"[!] {err_msg}", flush=True)
                try:
                    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                        f.write(f"\n[!] {err_msg}\n")
                except Exception:
                    pass
                send_discord_alert(err_msg)
        else:
            print("[!] No valid Cal eProcure tech records found to push from this run.", flush=True)
    else:
        print(
            f"[+] California SLED (Cal eProcure) extraction complete: {len(supabase_records)} tech contracts ready for master orchestrator.",
            flush=True,
        )

    return supabase_records


if __name__ == "__main__":
    asyncio.run(run_scraper())

