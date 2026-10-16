# Workspace Agent Rules (`AGENTS.md`)

## Mandatory Autonomous Integration & Website Sync Rule
Whenever any new API, scraper, or feature addition is created and finished, you **MUST** complete full end-to-end integration and add it to the website (`d:\Daas\index.html` and `d:\Daas\apis.html`) automatically **without waiting for the user to ask**:

1. **If a New API is Built or Updated (in `d:\Data API Ecosystem` or `d:\Daas`):**
   - Wire the endpoint into the FastAPI gateway (`d:\Data API Ecosystem`).
   - Immediately add the new API to **both** `d:\Daas\apis.html` and the `#page-apis` catalog + API banners inside `d:\Daas\index.html` (including module numbering, endpoint path, request/response preview, RapidAPI link, and pricing matrix).
   - Commit and push changes to GitHub (`origin main`) so Render deploys automatically.

2. **If a New Scraper, Portal, or Feature is Built (in `d:\Daas`):**
   - Immediately integrate it into `mainscraper.py`, `pseo_generator.py`, `client_delivery.py`, `outreach_generator.py`, `run_all.bat`, and `run_scraper.bat`.
   - Update portal counts, coverage sections, and navigation across `d:\Daas\index.html` and `d:\Daas\apis.html`.
   - Run `pseo_generator.py` to regenerate `/contracts` static pages, `sitemap.xml`, and the embedded SPA directory in `index.html`.
   - Commit and push changes to GitHub (`origin main`) so Render deploys automatically.

3. **Core Engineering Guardrails:**
   - Never hardcode secrets or API keys; always load from `.env` via `os.getenv()`.
   - Log all caught exceptions to `error_log.txt` and alert via `send_discord_alert()`.
   - Never truncate existing working code when editing files.
