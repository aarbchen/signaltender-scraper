# Project Rules (`project_rules.md`)

## 1. Core Stack & Architecture
- **Stack:** Python 3, `playwright.async_api`, `playwright_stealth`, `supabase-py`, FastAPI (`d:\Data API Ecosystem`), Static Web & pSEO (`d:\Daas\index.html`, `d:\Daas\apis.html`, `d:\Daas\contracts\`).

## 2. Autonomous End-to-End Integration & Site Sync Protocol (MANDATORY)
Whenever a new API endpoint, scraper, or feature addition is built and finished, you **MUST** automatically integrate it end-to-end and add it to the live website **without waiting for the user to give a separate integration command**:
1. **Pipeline & Backend Integration:**
   - **New Scrapers / Data Sources (`d:\Daas`):** Automatically integrate into `mainscraper.py` (`asyncio.gather()`), `pseo_generator.py` (`JURISDICTIONS` & static hub generation), `client_delivery.py` (Discord badges & channel routing), `outreach_generator.py` (state/region matching), `run_all.bat`, and `run_scraper.bat`.
   - **New FastAPI Endpoints (`d:\Data API Ecosystem`):** Automatically register routes in the FastAPI app, verify Pydantic V2 schemas, and push to the FastAPI repository.
2. **Automatic Website & Catalog Updates (`d:\Daas\index.html` & `d:\Daas\apis.html`):**
   - **When a New API is Built:** Automatically add the new API module card, endpoint schema preview, RapidAPI link/placeholder, and pricing matrix entry to **both** `d:\Daas\apis.html` and the `#page-apis` view + homepage API callouts inside `d:\Daas\index.html`.
   - **When a New Scraper / Feature is Built:** Automatically update portal counts, coverage cards, header telemetry bars, and embedded pSEO views in `d:\Daas\index.html` and `d:\Daas\apis.html`, and run `pseo_generator.py`.
3. **Zero-Touch Deployment:**
   - Automatically stage, commit, and `git push origin main` in `d:\Daas` (and `d:\Data API Ecosystem` when API code changes) so `signaltender.net` and `b2b-contract-parser-api.onrender.com` update automatically on Render.

## 3. Scraping Protocols
- All scrapers must use `asyncio`.
- SLED/Commercial sites use the Decodo residential proxy (`us.decodo.com:10001`) or direct fallback when required.
- Federal (`.gov`) sites strictly bypass proxies and use a direct connection to avoid Akamai/Cloudflare tarpitting.

## 4. Error Handling
- Every `try/except` block must write to `error_log.txt` and execute the `send_discord_alert()` function.
- Fatal UI timeouts must trigger a Playwright full-page screenshot saved to the root directory.

## 5. Data Integrity
- All extracted text must pass through the `tech_keywords` regex array and `commodity_it_exclusions` filter before touching Supabase (`contracts` table). Never push raw, unvetted firehose data.

## 6. Editing Rules
- Never truncate existing working code, and never hardcode API keys (always use `os.getenv`).
