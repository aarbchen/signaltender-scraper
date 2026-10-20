# Workspace Agent Rules (`AGENTS.md`)

## Mandatory Autonomous Integration & Website Sync Rule
Whenever any new API, scraper, or feature addition is created and finished, you **MUST** complete full end-to-end integration and add it to the website (`d:\Daas\index.html` and `d:\Daas\apis.html`) and both MCP servers automatically **without waiting for the user to ask**:

1. **If a New API is Built or Updated (in `d:\Data API Ecosystem` or `d:\Daas`):**
   - **FastAPI Gateway & Schemas (`d:\Data API Ecosystem`):** Wire the endpoint into the FastAPI gateway (`api/routers/` and `main.py` description), export Pydantic V2 schemas in `schemas/`, implement LLM extraction in `services/llm_parser.py`, and add live verification coverage in `test_live_api.py`.
   - **Dual Model Context Protocol (MCP) Servers (Remote HTTP + Local STDIO/NPM):**
     - `d:\Data API Ecosystem\api\routers\mcp.py`: Register the new tool in `MCP_TOOLS` and `TOOL_ROUTE_MAP` for the remote Streamable-HTTP MCP server (`/mcp`).
     - `d:\Daas\mcp-server\index.js` & `d:\Daas\mcp-server\README.md`: Register the new tool's RapidAPI host in `RAPIDAPI_HOSTS`, schema in `TOOLS`, route in `ENDPOINT_MAP`, and table row in `mcp-server/README.md` for the NPM/Glama/Smithery STDIO MCP server (`@signaltender/mcp-server`).
   - **Website, In-Page Studio Playground & pSEO (`d:\Daas`):** Immediately add the new API to **all** website & SEO surfaces in a single pass:
     - `d:\Daas\apis.html` (nav badge count, hero endpoint count, MCP tool count + tool list, Quick-Jump Directory row, full Product Module card, Cross-Catalog Pricing Matrix row, footer link, and In-Page RapidAPI Studio Playground `CATALOG['product-...']` + `API_META['product-...']` with exact Pydantic request schema fields).
     - `d:\Daas\index.html` (homepage API callout banner pill, `#page-apis` catalog view + Quick-Jump Directory row + full Product Module card + MCP tool count + Cross-Catalog Pricing Matrix row, `#product-...` hash in `apiPageHashes`, and In-Page RapidAPI Studio Playground `CATALOG['product-...']` + `API_META['product-...']`).
     - `d:\Daas\pseo_generator.py` (update the live API count & sidebar/CTA links, then execute `.\daas_env\Scripts\python.exe pseo_generator.py` to regenerate `/contracts/rfp/*.html` static pages and the embedded SPA dossier script in `index.html`).
     - `d:\Daas\signaltender_1m_business_plan.md` (mark the API as `(Live)`).
     - `d:\Daas\seed_rapidapi_telemetry.py` (register the new API's `rapid_host` and test payload, add its `X-RapidAPI-Proxy-Secret` to `.env` and Render `srv-db7c68a5b2lc73fce4vg`, and automatically run a live `200 OK` call through `https://<slug>.p.rapidapi.com` using `RAPIDAPI_KEY` from `.env` to seed the green `100% Service Level` telemetry badge on RapidAPI Hub).
   - **Mandatory RapidAPI Green-Badge & Health-Check Verification Rule:** Whenever creating or updating an API on RapidAPI Studio (`https://rapidapi.com/gateway/graphql`), you **MUST** always ensure it gets both green badges automatically:
     1. **Green Health Check Badge (`SUCCESS`):** Call `upsertApiHealthcheck(apiId, healthCheckUrl: "https://b2b-contract-parser-api.onrender.com/v1/health")` and verify that `apiHealthCheck.healthcheckStatus.status == "SUCCESS"`.
     2. **Green `100% Service Level` Telemetry Badge (`200 OK`):** Wire the API's `X-RapidAPI-Proxy-Secret` into `d:\Data API Ecosystem\.env` and Render (`RAPIDAPI_PROXY_SECRET`), wait for the Render deploy to go live, and execute `seed_rapidapi_telemetry.py` through `https://<slug>.p.rapidapi.com` until the endpoint returns `200 OK`.
     3. **Listing Completeness:** Ensure `visibility: "PUBLIC"`, 500x500 logo uploaded, Markdown `longDescription` populated, human-readable Title Case endpoint names (never `snake_case`), and all 4 pricing plans configured (`BASIC` `$0` `10/mo` hard limit + `10/hour` rate limit, `PRO` `$49` `200/mo`, `ULTRA` `$149` `1,000/mo` marked `recommended: true`, and `MEGA` `$399` `4,000/mo`).
   - **RapidAPI Studio Listing Assets:** Automatically generate and present all **3 RapidAPI Studio Listing Assets** in the same turn:
     1. OpenAPI 3.0.3 JSON specification file (`rapidapi_apiXX_openapi.json`).
     2. 500x500 PNG API Logo (`d:\Daas\apiXX_..._logo.png`).
     3. Full copy-pasteable RapidAPI Long Description / README (Markdown, saved to `d:\Daas\rapidapi_apiXX_readme.md`).
   - **Zero-Touch Git Push:** Run `.\daas_env\Scripts\python.exe verify_site_integrity.py`, then commit and push changes to GitHub (`origin main`) in **both** `d:\Data API Ecosystem` and `d:\Daas` so Render and `signaltender.net` deploy automatically.

2. **If a New Scraper, Portal, or Feature is Built (in `d:\Daas`):**
   - Immediately integrate it into `mainscraper.py`, `pseo_generator.py`, `client_delivery.py`, `outreach_generator.py`, `run_all.bat`, and `run_scraper.bat`.
   - Update portal counts, coverage sections, and navigation across `d:\Daas\index.html` and `d:\Daas\apis.html`.
   - Run `pseo_generator.py` to regenerate `/contracts` static pages, `sitemap.xml`, and the embedded SPA directory in `index.html`.
   - Run `.\daas_env\Scripts\python.exe verify_site_integrity.py`, then commit and push changes to GitHub (`origin main`) so Render deploys automatically.

3. **Core Engineering Guardrails & Evergreen Copy Rule:**
   - Never hardcode secrets or API keys; always load from `.env` via `os.getenv()`.
   - Log all caught exceptions to `error_log.txt` and alert via `send_discord_alert()`.
   - Never truncate existing working code when editing files.
   - **Evergreen Copy Rule:** Never hardcode exact API counts (e.g., "10 APIs") or exhaustive tool lists in external directory submissions (Glama, MCP registries, RapidAPI profile blurbs, `smithery.yaml`), MCP manifests (`glama.json`, `package.json`, `server.json`), or page `<title>` / `<meta>` tags so that adding future APIs never makes existing listings look outdated.

4. **Mandatory Frontend, SPA & UI Quality Gate (`verify_site_integrity.py`):**
   Before committing or pushing any change to `d:\Daas\index.html`, `d:\Daas\apis.html`, or `d:\Daas\pseo_generator.py`, you **MUST** run `.\daas_env\Scripts\python.exe verify_site_integrity.py` and enforce all of the following rules:
   - **Zero Unescaped Quotes in Generated `<script>` Blocks:** In `pseo_generator.py` (or any Python script generating HTML/JS), never place `\'` inside triple-quoted `f"""..."""` strings that emit single-quoted JavaScript strings (`'...'`). Always use HTML entities (`&quot;`, `&apos;`) inside embedded HTML attributes and verify every inline `<script>` block and `on*` attribute with `node --check`.
   - **Headless SPA Runtime Verification:** `window.renderContractsRoute('#contracts')`, `#contracts/federal`, and `#contracts/rfp/<slug>`, plus `filterContractsDirectory()`, `filterApiCatalog()`, `filterMainRfpTable()`, `openApiSandbox()`, and `setCheckoutBilling()` must execute in Node.js without throwing and must populate `#contracts-dynamic-root` with non-empty HTML.
   - **100% Catalog Parity & Sequential Ordering (`index.html` <-> `apis.html`):**
     - `index.html` and `apis.html` must always have the exact same number of `<article id="product-...">` cards, Quick-Jump Directory rows (`01`..`N` in strict ascending order), Cross-Catalog Pricing Matrix rows (`01`..`N` in strict ascending order), `CATALOG` entries, and `API_META` entries.
     - All numeric badges (`API Catalog (N)`, `N LIVE ENDPOINTS`, `N MCP TOOLS`, `N / N SHOWN`, `All (N)`) must match the exact `<article>` count.
     - Every `<article id="product-...">` card in both files must use the uniform 12-column (`lg:col-span-7` specs/tiers + `lg:col-span-5` response preview) layout with zero inner scrollbars (`max-h-*` is prohibited on card `<pre>` elements).
   - **Search & Navigation UX Stability (Zero Overlap & Zero Page Shifts):**
     - Counter badges (`#api-modules-count-badge`) must always sit outside the `<input>` wrapper as sibling flex elements (`shrink-0`), never `absolute` inside the input box where they can overlap placeholder or typed text.
     - Filtered containers (`#api-directory-list`, `#catalog-modules`, `#contract-directory`) must lock `minHeight` before hiding items, set `overflow-anchor: none`, and preserve `anchorEl.getBoundingClientRect().top` via `window.scrollBy(0, deltaY)` with `scrollBehavior = 'auto'` so typing in a search box never shifts the viewport up or down.
     - SPA view switches (`#overview`, `#apis`, `#contracts`, `#checkout`) must scroll to `(0, 0)` instantaneously (`scrollBehavior = 'auto'`), and clicking a `#product-...` hash while a search filter is active must automatically unhide the target card.
     - Links inside `#page-contracts` in `index.html` that point to checkout (`#checkout-tier1`, `#checkout-tier2`) or API modules (`#product-...`) must navigate in-page rather than opening duplicate browser tabs with `target="_blank"`.
   - **Visual & Brand Standards:**
     - **Zero Emojis:** Never use emojis (`[\U0001F300-\U0001FAFF]`) anywhere on the site; use clean SVG icons or typographic symbols.
     - **Consistent Header Lockup (2F-Tight):** Keep the borderless T3 radar-chevron SVG (`viewBox="6 5 52 54"`, `w-[21px] h-[21px] shrink-0 -translate-y-[1px]`, ring `stroke-width="5.6"`, chevron `stroke-width="6"`) inline with a `4px` gap (`inline-flex items-center gap-[4px]`) next to `<span class="text-[23px] font-semibold tracking-[-0.03em] text-white leading-none whitespace-nowrap">SignalTender</span>` with zero competing pill badges or subtitle lines across `#page-main`, `#page-apis`, `#page-contracts`, `#page-checkout`, `apis.html`, and generated `/contracts/**/*.html`.
     - **Checkout Hierarchy:** On `#page-checkout`, Tier 1 (`$99/mo`) and Tier 2 (`$399/mo`) plan cards must always remain at the top of the page above any developer API callouts.
