# Workspace Agent Rules (`AGENTS.md`)

## Mandatory Autonomous Integration & Website Sync Rule
Whenever any new API, scraper, or feature addition is created and finished, you **MUST** complete full end-to-end integration and add it to the website (`d:\Daas\index.html` and `d:\Daas\apis.html`) automatically **without waiting for the user to ask**:

1. **If a New API is Built or Updated (in `d:\Data API Ecosystem` or `d:\Daas`):**
   - Wire the endpoint into the FastAPI gateway (`d:\Data API Ecosystem`), export Pydantic V2 schemas in `schemas/`, and add verification coverage in `test_live_api.py`.
   - Immediately add the new API to **all** website & SEO surfaces in a single pass:
     - `d:\Daas\apis.html` (nav badge count, hero endpoint count, Quick-Jump Directory row, full Product Module card, Cross-Catalog Pricing Matrix row, and footer link).
     - `d:\Daas\index.html` (homepage API callout banner pill, `#page-apis` catalog view + pricing matrix, and `#product-...` hash in `apiPageHashes`).
     - `d:\Daas\pseo_generator.py` (update the live API count & sidebar/CTA links, then execute `.\daas_env\Scripts\python.exe pseo_generator.py` to regenerate `/contracts/rfp/*.html` static pages and the embedded SPA dossier script in `index.html`).
     - `d:\Daas\signaltender_1m_business_plan.md` (mark the API as `(Live)`).
   - Automatically generate and present all **3 RapidAPI Studio Listing Assets** in the same turn:
     1. OpenAPI 3.0.3 JSON specification file (`rapidapi_apiXX_openapi.json`).
     2. 500x500 PNG API Logo (`d:\Daas\apiXX_..._logo.png`).
     3. Full copy-pasteable RapidAPI Long Description / README (Markdown).
   - Commit and push changes to GitHub (`origin main`) in **both** `d:\Data API Ecosystem` and `d:\Daas` so Render and `signaltender.net` deploy automatically.

2. **If a New Scraper, Portal, or Feature is Built (in `d:\Daas`):**
   - Immediately integrate it into `mainscraper.py`, `pseo_generator.py`, `client_delivery.py`, `outreach_generator.py`, `run_all.bat`, and `run_scraper.bat`.
   - Update portal counts, coverage sections, and navigation across `d:\Daas\index.html` and `d:\Daas\apis.html`.
   - Run `pseo_generator.py` to regenerate `/contracts` static pages, `sitemap.xml`, and the embedded SPA directory in `index.html`.
   - Commit and push changes to GitHub (`origin main`) so Render deploys automatically.

3. **Core Engineering Guardrails & Evergreen Copy Rule:**
   - Never hardcode secrets or API keys; always load from `.env` via `os.getenv()`.
   - Log all caught exceptions to `error_log.txt` and alert via `send_discord_alert()`.
   - Never truncate existing working code when editing files.
   - **Evergreen Copy Rule:** Never hardcode exact API counts (e.g., "10 APIs") or exhaustive tool lists in external directory submissions (Glama, MCP registries, RapidAPI profile blurbs), MCP manifests (`glama.json`, `package.json`), or page `<title>` / `<meta>` tags so that adding future APIs never makes existing listings look outdated.

