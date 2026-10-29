"""
Mandatory Pre-Push Website & SPA Integrity Verifier (`verify_site_integrity.py`).

Runs automated static + headless Node.js runtime checks across `d:\\Daas\\index.html`,
`d:\\Daas\\apis.html`, and generated `d:\\Daas\\contracts\\**\\*.html` files to ensure:
  1. Zero JavaScript syntax errors in any inline `<script>` block (`node --check`).
  2. Zero syntax errors in any HTML inline event handler (`onclick`, `oninput`, etc.).
  3. Headless Node.js runtime execution of all SPA routes (`#contracts`, `#contracts/federal`,
     `#contracts/rfp/<slug>`, `#apis`, `#checkout`) and all search/filter functions
     (`filterApiCatalog`, `filterContractsDirectory`, `filterMainRfpTable`, `openApiSandbox`).
  4. 100% API count, ordering, and layout parity between `index.html` and `apis.html`
     (Directory rows 01..N in ascending order, Pricing Matrix rows 01..N, `<article>` cards,
     `CATALOG`, `API_META`, nav badge counts, and 7-col/5-col layout with zero inner scrollbars).
  5. Zero duplicate HTML IDs, zero broken `#hash` links, zero structural tag imbalances,
     zero emojis, and non-overlapping search bar badges with scroll-anchor locks.
"""

import glob
import json
import os
import re
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}", flush=True)
    try:
        from error_telemetry import report_error
        report_error('verify_site_integrity.py', f'verify_site_integrity.py FAIL: {msg[:900]}')
    except Exception:
        pass
    raise SystemExit(1)


def check_html_file(fpath: str) -> str:
    if not os.path.exists(fpath):
        fail(f"Missing required file: {fpath}")
    import time
    lock_path = os.path.join(BASE_DIR, ".index_html_write.lock")
    txt = ""
    for _attempt in range(25):
        if os.path.exists(lock_path):
            time.sleep(0.15)
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            txt = f.read()
        if "</html>" in txt and txt.count("<main") == txt.count("</main>"):
            break
        time.sleep(0.15)

    rel = os.path.relpath(fpath, BASE_DIR)

    if '<script src="https://cdn.tailwindcss.com"></script>' not in txt:
        fail(f"{rel}: Missing required '<script src=\"https://cdn.tailwindcss.com\"></script>' tag (site will render unstyled)")

    # 1. Strip <script> blocks for HTML-only checks while collecting inline scripts
    scripts_to_check = []
    for idx, m in enumerate(re.finditer(r"<script([^>]*)>(.*?)</script>", txt, flags=re.S | re.I), 1):
        attrs, body = m.group(1), m.group(2)
        if "src=" in attrs or "application/ld+json" in attrs:
            continue
        scripts_to_check.append((f"<script> #{idx}", body))

    html_only = re.sub(r"<script[^>]*>.*?</script>", "", txt, flags=re.S | re.I)

    # 2. Collect all HTML inline event handlers (`onclick`, `oninput`, `onchange`, `onsubmit`)
    handlers = re.findall(r'\b(on(?:click|input|change|submit|keydown|keyup))="([^"]*)"', html_only)
    for h_type, h_code in handlers:
        js_code = h_code.replace("&quot;", '"').replace("&#39;", "'").replace("&amp;", "&")
        scripts_to_check.append((f'{h_type}="{h_code}"', f"(function(event){{\n{js_code}\n}})"))

    # 3. Validate all scripts + handlers in a single fast Node.js vm.Script pass
    import json
    checker_js = (
        "const vm = require('vm');\n"
        f"const items = {json.dumps(scripts_to_check)};\n"
        "for (const [label, code] of items) {\n"
        "  try {\n"
        "    new vm.Script(code, { filename: label });\n"
        "  } catch (err) {\n"
        "    console.error(label + ': ' + err.stack);\n"
        "    process.exit(1);\n"
        "  }\n"
        "}\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
        tf.write(checker_js)
        tname = tf.name
    r = subprocess.run(["node", tname], capture_output=True, text=True)
    os.remove(tname)
    if r.returncode != 0:
        fail(f"{rel}: JS SyntaxError:\n{r.stderr}")

    # 4. Check duplicate HTML IDs
    ids = re.findall(r'\bid="([^"]+)"', html_only)
    seen = set()
    dups = set()
    for i in ids:
        if i in seen:
            dups.add(i)
        seen.add(i)
    if dups:
        fail(f"{rel}: Duplicate HTML IDs found: {sorted(dups)}")

    # 5. Check all internal #hash links resolve to valid IDs or SPA routes
    hashes = set(re.findall(r'href="(#[a-zA-Z0-9_/-]+)"', html_only))
    spa_routes = {
        "#overview",
        "#apis",
        "#contracts",
        "#checkout",
        "#checkout-tier1",
        "#checkout-tier2",
        "#checkout-tier3",
        "#checkout-tier4",
        "#proposal-foia-moat",
        "#checkout-annual",
        "#account",
        "#signup",
        "#login",
        "#status",
        "#security",
        "#trust",
        "#contact",
        "#support",
        "#feedback",
        "#terms",
        "#privacy",
        "#dpa",
        "#sla",
        "#contracts/federal",
        "#contracts/texas",
        "#contracts/virginia",
        "#contracts/california",
        "#contracts/florida",
        "#contracts/maryland",
        "#contracts/illinois",
            "#contracts/pennsylvania",
            "#contracts/ohio",
            "#contracts/georgia",
            "#contracts/north_carolina",
            "#contracts/new_york",
            "#contracts/massachusetts",
            "#contracts/new_jersey",
            "#contracts/washington",
            "#contracts/michigan",
            "#contracts/colorado",
            "#contracts/arizona",
            "#contracts/mn",
            "#contracts/minnesota",
            "#contracts/tn",
            "#contracts/tennessee",
            "#contracts/in",
            "#contracts/indiana",
            "#contracts/mo",
            "#contracts/missouri",
            "#contracts/wi",
            "#contracts/wisconsin",
            "#contracts/sc",
            "#contracts/south_carolina",
            "#contracts/or",
            "#contracts/oregon",
            "#contracts/ct",
            "#contracts/connecticut",
            "#contracts/ut",
            "#contracts/utah",
        "#contracts/municipal",
    }
    for h in sorted(hashes):
        target_id = h[1:]
        if target_id not in seen and h not in spa_routes and not h.startswith("#contracts/"):
            fail(f"{rel}: Broken internal hash link {h} (no matching id='{target_id}' or SPA route)")

    # 6. Check structural HTML tag balance
    for tag in ["div", "section", "article", "header", "footer", "main", "table", "thead", "tbody", "tr", "td", "th", "button", "a"]:
        opens = len(re.findall(rf"<{tag}\b", html_only))
        closes = len(re.findall(rf"</{tag}>", html_only))
        if opens != closes:
            fail(f"{rel}: Tag imbalance for <{tag}>: open={opens}, close={closes}")

    # 7. Check dark scrollbar theme (`color-scheme: dark` + `*::-webkit-scrollbar`) so native white scrollbars never appear
    if "color-scheme: dark" not in txt or "*::-webkit-scrollbar" not in txt:
        fail(f"{rel}: Missing global dark scrollbar styling (`color-scheme: dark` and `*::-webkit-scrollbar`).")

    # 8. Check zero emojis and zero `data:` URI favicons (Google Search requires crawlable HTTP/HTTPS favicon URLs)
    emoji_re = re.compile(r"[\U0001F300-\U0001FAFF]")
    emojis = emoji_re.findall(txt)
    if emojis:
        fail(f"{rel}: Prohibited emojis found: {set(emojis)}")
    if re.search(r'<link[^>]+rel="icon"[^>]+href="data:', txt, flags=re.I):
        fail(f"{rel}: <link rel='icon'> uses a data: URI which Google Search rejects; use crawlable HTTPS URLs")
    if "apple-touch-icon.png?v=" not in txt or "favicon.svg?v=" not in txt:
        fail(f"{rel}: Favicon / apple-touch-icon links must include a ?v= cache-busting query parameter for mobile browsers")
    if re.search(r"Claude\s+Sonnet|Claude\s+Opus|Claude\s+Haiku|claude-sonnet-|claude-opus-|claude-haiku-|INSTANT-KB", txt, flags=re.I):
        fail(f"{rel}: Public HTML/JS must never expose internal LLM model names (e.g. Claude Sonnet) or internal INSTANT-KB labels")
    if re.search(r"page\s+clutter|organized\s+module\s+view|focused\s+tab\s+view|use\s+the\s+workspace\s+tabs|opengraph\s+clutter|workspace\s+modules:|api\s+catalog\s+workspace\s+view", txt, flags=re.I):
        fail(f"{rel}: Public HTML/JS must never contain self-referential, prompt-echoing, or internal UI meta-copy")

    # 8. Check compact 2-row mobile sticky <header> (no multi-row grid-cols-2 mobile nav, no flex-wrap or state bars inside sticky <header>)
    for hdr_m in re.finditer(r"<header\b[^>]*>(.*?)</header>", html_only, flags=re.S):
        hdr_inner = hdr_m.group(1)
        if "grid-cols-2" in hdr_inner:
            fail(f"{rel}: Sticky <header> uses 'grid-cols-2' in Mobile Site Navigation; must use single-row 'grid-cols-4'")
        if "All Portals" in hdr_inner or "flex-wrap" in hdr_inner:
            fail(f"{rel}: Sticky <header> must stay compact on mobile (no 'flex-wrap' or multi-line State Hub bar inside <header>)")

    return txt


def check_catalog_parity_and_ui(index_txt: str, apis_txt: str) -> None:
    for label, txt in [("index.html", index_txt), ("apis.html", apis_txt)]:
        # Count <article id="product-...">
        articles = re.findall(r'<article\s+id="(product-[a-z0-9-]+)"', txt)
        n_apis = len(articles)
        if n_apis < 13:
            fail(f"{label}: Expected at least 13 API <article> cards, found {n_apis}")

        # Verify Quick-Jump Directory rows are 01..N in ascending order
        dir_m = re.search(r'id="api-directory-list"[^>]*>(.*?)</div>\s*</div>', txt, flags=re.S)
        if not dir_m:
            fail(f"{label}: Missing #api-directory-list container")
        dir_rows = re.findall(r"<!-- Directory Row (\d+) -->", txt)
        expected_nums = [f"{i:02d}" for i in range(1, n_apis + 1)]
        if dir_rows != expected_nums:
            fail(f"{label}: Quick-Jump Directory rows out of order or missing: found {dir_rows}, expected {expected_nums}")

        # Verify Pricing Matrix rows match n_apis and thead has exactly 1 row
        thead_m = re.search(r'id="api-pricing-matrix".*?<thead[^>]*>(.*?)</thead>', txt, flags=re.S)
        if not thead_m or len(re.findall(r"<tr\b", thead_m.group(1))) != 1:
            fail(f"{label}: #api-pricing-matrix <thead> must have exactly 1 header row")
        matrix_m = re.search(r'id="api-pricing-matrix".*?<tbody[^>]*>(.*?)</tbody>', txt, flags=re.S)
        if not matrix_m:
            fail(f"{label}: Missing #api-pricing-matrix tbody")
        matrix_rows = re.findall(r"<tr\b", matrix_m.group(1))
        if len(matrix_rows) != n_apis:
            fail(f"{label}: #api-pricing-matrix has {len(matrix_rows)} rows, expected {n_apis}")

        # Verify badge counts match n_apis and top navigation bars use evergreen labels ('API Catalog' on desktop, 'APIs' on mobile)
        if ">API Catalog</a>" not in txt:
            fail(f"{label}: Desktop nav link '>API Catalog</a>' missing")
        if 'aria-label="Mobile Site Navigation"' not in txt or ">APIs</a>" not in txt:
            fail(f"{label}: Mobile nav link '>APIs</a>' inside Mobile Site Navigation missing")
        if re.search(r">\d+\s+APIs</a>", txt):
            fail(f"{label}: Navigation links must never contain a hardcoded API count (use '>APIs</a>' on mobile and '>API Catalog</a>' on desktop)")
        if f"{n_apis} LIVE ENDPOINTS" not in txt:
            fail(f"{label}: Directory badge '{n_apis} LIVE ENDPOINTS' does not match {n_apis} APIs")
        if f"{n_apis} MCP TOOLS" not in txt:
            fail(f"{label}: MCP badge '{n_apis} MCP TOOLS' does not match {n_apis} APIs")
        if f"{n_apis} / {n_apis} SHOWN" not in txt:
            fail(f"{label}: Modules counter badge '{n_apis} / {n_apis} SHOWN' does not match {n_apis} APIs")
        if f"Search {n_apis} APIs" not in txt:
            fail(f"{label}: Search input placeholder 'Search {n_apis} APIs' does not match {n_apis} APIs")
        if f"All ({n_apis})</button>" not in txt:
            fail(f"{label}: Category filter pill 'All ({n_apis})</button>' does not match {n_apis} APIs")
        if f"SELECT MICROSERVICE ({n_apis})" not in txt:
            fail(f"{label}: Studio Playground header 'SELECT MICROSERVICE ({n_apis})' does not match {n_apis} APIs")
        if f"Filter {n_apis} endpoints..." not in txt:
            fail(f"{label}: Studio Playground filter placeholder 'Filter {n_apis} endpoints...' does not match {n_apis} APIs")

        # Prohibit any stale catalog API count (from 10 up to n_apis - 1)
        for ka in range(10, n_apis):
            stale_api_phrases = [
                f"{ka} LIVE ENDPOINTS",
                f"{ka} MCP TOOLS",
                f"{ka} / {ka} SHOWN",
                f"All ({ka})</button>",
                f"Search {ka} APIs",
                f"Filter {ka} endpoints",
                f"SELECT MICROSERVICE ({ka})",
                f"{ka} REST &amp; MCP MICROSERVICES",
                f"All {ka} individual SignalTender microservices",
                f"Explore {ka} APIs",
                f"Test All {ka} APIs",
                f"test all {ka} AI APIs",
                f"test all {ka} APIs",
                f"{ka} Studio Playground APIs",
                f"FastAPI Microservice Gateway ({ka} APIs)",
                f"{ka} APIs, RapidAPI &amp; MCP Server",
                f"Exposes all {ka} SignalTender endpoints",
                f"for all {ka} REST",
                f"{ka} LIVE APIs &amp; MCP SERVER",
                f"SignalTender&apos;s {ka} APIs",
                f"submitted to our {ka} APIs",
                f"sent to our {ka} REST/MCP endpoints",
                f"connect all {ka} GovCon APIs",
                f"Open {ka}-API Catalog",
                f"Explore {ka}-API Catalog",
            ]
            for sap in stale_api_phrases:
                if sap in txt and re.search(rf"(?<![0-9]){re.escape(sap)}", txt):
                    fail(f"{label}: Found stale API count string '{sap}' (expected {n_apis} APIs)")

        # Verify #api-modules-count-badge is NOT inside the relative <input> wrapper (prevents text overlap)
        bad_overlap = re.search(
            r'<div class="relative flex-1 flex items-center">[^<]*<svg.*?</svg>\s*<input[^>]*id="api-modules-search"[^>]*>\s*<span id="api-modules-count-badge"',
            txt,
            flags=re.S,
        )
        if bad_overlap:
            fail(f"{label}: #api-modules-count-badge is inside the <input> wrapper and will overlap placeholder text")

        # Verify scroll-anchor protection on #catalog-modules
        if 'id="catalog-modules"' not in txt or "overflow-anchor: none" not in txt:
            fail(f"{label}: Missing overflow-anchor: none scroll-jump protection on #catalog-modules")

        # Verify 100% 1:1 RapidAPI URL & Host Uniqueness across all API Cards, Matrix Rows, and CATALOG entries
        verified_rapidapi_studio_slugs = {
            "b2b-contract-parsing-api",
            "ai-contract-risk-redline-auditor-api",
            "historical-procurement-pricing-api",
            "live-sled-federal-open-rfp-feed-api",
            "rfp-compliance-matrix-proposal-outline-api",
            "far-dfars-cmmc-clause-risk-scanner-api",
            "ai-bid-no-bid-capability-matcher-api",
            "naics-sic-psc-unspsc-industry-classifier-api",
            "ai-rfp-response-clarification-q-a-generator-api",
            "b2b-quote-invoice-clin-table-extractor-api",
            "govcon-teaming-partner-subcontracting-plan-api",
            "soc-2-fedramp-nist-800-171-security-questionnaire-api",
            "govcon-key-personnel-lcat-resume-tailoring-api",
            "rfp-amendment-q-a-change-impact-analyzer-api",
            "cpars-past-performance-volume-generator-api",
            "govcon-igce-wrap-rate-price-to-win-modeler-api",
            "govcon-oral-presentation-tech-demo-murder-board-prep-api",
            "govcon-rmf-continuous-ato-cato-ssp-poa-m-generator-api",
            "govcon-debriefing-far-15-506-gao-bid-protest-analyzer-api",
            "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api",
            "govcon-sources-sought-rfi-set-aside-shaping-responder-api",
            "govcon-oci-far-9-5-mitigation-plan-generator-api",
            "sbir-sttr-phase-i-iii-commercialization-plan-api",
            "govcon-section-508-wcag-2-2-aa-vpat-2-5-auditor-api",
            "govcon-supply-chain-scrm-ndaa-889-taa-sbom-auditor-api",
            "govcon-qasp-prs-sla-kpi-surveillance-matrix-api",
            "govcon-30-60-90-day-phase-in-transition-plan-api",
            "dcaa-pre-award-sf1408-accounting-system-auditor-api",
            "dod-ota-10-usc-4022-prototype-white-paper-api",
            "dcsa-fcl-dd254-foci-sf328-clearance-auditor-api",
            "far-52-219-9-subcontracting-plan-esrs-calculator-api",
            "dfars-252-227-7013-7014-7017-data-rights-assertion-api",
            "govcon-shipley-black-hat-incumbent-ghosting-api",
            "govcon-cpars-self-assessment-14-day-rebuttal-api",
        }
        for rslug in set(re.findall(r"https://rapidapi\.com/aarbchen/api/([a-z0-9-]+)", txt)):
            if rslug not in verified_rapidapi_studio_slugs:
                fail(
                    f"{label}: Unverified RapidAPI URL slug '{rslug}' found! "
                    "Every API must exist in RapidAPI Studio and be registered in verified_rapidapi_studio_slugs."
                )
        for hslug in set(re.findall(r"([a-z0-9-]+)\.p\.rapidapi\.com", txt)):
            if hslug not in verified_rapidapi_studio_slugs:
                fail(
                    f"{label}: Unverified RapidAPI host '{hslug}.p.rapidapi.com' found! "
                    "Every API must exist in RapidAPI Studio and be registered in verified_rapidapi_studio_slugs."
                )

        # Enforce strict 1:1 unique RapidAPI links per API Card, Matrix Row, and CATALOG entry (never point API N to API M!)
        article_blocks = re.findall(r'<article id="(product-[^"]+)"([\s\S]*?)</article>', txt)
        matrix_tr_blocks = re.findall(r"<tr\b[\s\S]*?</tr>", matrix_m.group(1))
        card_slug_by_pid = {}
        seen_card_slugs = {}
        for idx_art, (pid, abody) in enumerate(article_blocks):
            c_slugs = set(re.findall(r"https://rapidapi\.com/aarbchen/api/([a-z0-9-]+)", abody))
            c_hosts = set(re.findall(r"([a-z0-9-]+)\.p\.rapidapi\.com", abody))
            if len(c_slugs) != 1:
                fail(f"{label}: Card '{pid}' must link to exactly 1 RapidAPI slug, found: {c_slugs}")
            c_slug = next(iter(c_slugs))
            if c_hosts and c_hosts != {c_slug}:
                fail(f"{label}: Card '{pid}' host mismatch: hosts={c_hosts} vs url_slug={c_slug}")
            if c_slug in seen_card_slugs:
                fail(
                    f"{label}: Duplicate RapidAPI link '{c_slug}' on '{pid}' (already used by '{seen_card_slugs[c_slug]}')! "
                    "Every API must link 1:1 to its own dedicated RapidAPI page."
                )
            seen_card_slugs[c_slug] = pid
            card_slug_by_pid[pid] = c_slug

            # Verify matching Matrix Row links to the exact same 1:1 RapidAPI slug
            if idx_art >= len(matrix_tr_blocks):
                fail(f"{label}: Missing Cross-Catalog Pricing Matrix row for '{pid}'")
            m_slugs = set(re.findall(r"https://rapidapi\.com/aarbchen/api/([a-z0-9-]+)", matrix_tr_blocks[idx_art]))
            if m_slugs != {c_slug}:
                fail(f"{label}: Pricing Matrix row #{idx_art+1} ('{pid}') links to {m_slugs}, expected '{c_slug}'")

            # Verify matching CATALOG['pid'] entry uses the exact same 1:1 RapidAPI host and hubUrl
            cat_m = re.search(rf"'{re.escape(pid)}'\s*:\s*\{{([\s\S]*?)\n\s*\}}\s*\}}", txt)
            if not cat_m:
                fail(f"{label}: Missing CATALOG['{pid}'] entry")
            cat_slugs = set(re.findall(r"https://rapidapi\.com/aarbchen/api/([a-z0-9-]+)", cat_m.group(1)))
            cat_hosts = set(re.findall(r"([a-z0-9-]+)\.p\.rapidapi\.com", cat_m.group(1)))
            if cat_slugs != {c_slug} or cat_hosts != {c_slug}:
                fail(
                    f"{label}: CATALOG['{pid}'] mismatch: slugs={cat_slugs}, hosts={cat_hosts}, expected '{c_slug}'"
                )

        if "https://discord.gg/signaltender" in txt:
            fail(f"{label}: Contains dead vanity invite 'https://discord.gg/signaltender'; use permanent invite 'https://discord.gg/xtGXfQApRP'")

        # Verify 4-column Enterprise SaaS footer and zero legacy footer labels
        for req_footer in ("Procurement Platform", "Developer &amp; API Suite", "Account &amp; Plans"):
            if req_footer not in txt:
                fail(f"{label}: Missing 4-column Enterprise footer heading '{req_footer}'")
        for req_trust_link in ("System Status (99.95% SLA)", "Security &amp; Zero-Retention Trust", "Instant AI Support Concierge", "Submit Feedback / Request Portal", "Terms of Service", "Privacy Policy &amp; DPA"):
            if req_trust_link not in txt:
                fail(f"{label}: Missing footer trust/legal link '{req_trust_link}'")
        if "https://x.com/SignalTenderX" not in txt or "https://www.linkedin.com/company/signaltender/" not in txt:
            fail(f"{label}: Missing official LinkedIn or X (@SignalTenderX) link in footer")
        if "Main: Live Discord Alert Wire" in txt or "Page 2: Developer Data API Catalog" in txt or "Client Account Console" in txt:
            fail(f"{label}: Contains legacy or internal Client Account Console footer labels")

    if 'id="header-auth-user-label" class="truncate max-w-[110px]"' not in index_txt or "clearAutofilledSearchInputs" not in index_txt:
        fail("index.html: Missing bounded #header-auth-user-label width or clearAutofilledSearchInputs() protection")
    if 'id="overview-section-directory"' in index_txt:
        fail("index.html: Redundant inline #overview-section-directory must be removed in favor of #page-section-sidebar-root")
    if 'id="page-section-sidebar-root"' not in index_txt or 'id="page-section-sidebar-root"' not in apis_txt:
        fail("Missing collapsible #page-section-sidebar-root in index.html or apis.html")
    if re.search(r'class="(?:trust-tab-btn|dossier-demo-pill)[^"]*"[^>]*>\s*\d{2}\.', index_txt):
        fail("index.html: Tab/switcher buttons (.trust-tab-btn / .dossier-demo-pill) must never use '01.' numeric prefixes")
    if "num: '01', id:" in index_txt or "num: '01', id:" in apis_txt or "var SIDEBAR_ICONS =" not in index_txt or "var SIDEBAR_ICONS =" not in apis_txt:
        fail("Sidebar items must use clean SVG icons (SIDEBAR_ICONS / icon: '...'), never numeric '01'..'08' badges")


def check_portal_parity_and_telemetry(index_txt: str, apis_txt: str) -> None:
    import json

    jm = re.search(r"window\.SIGNALTENDER_JURISDICTIONS\s*=\s*(\{.*?\});", index_txt, flags=re.S)
    if not jm:
        fail("index.html: Missing window.SIGNALTENDER_JURISDICTIONS definition")
    jurisdictions = json.loads(jm.group(1))
    n_portals = len(jurisdictions)
    state_keys = [k for k in jurisdictions.keys() if k not in ("federal", "municipal")]
    n_states = len(state_keys)

    # 1. Verify Top Telemetry Bar on #page-main
    if f"{n_portals} GOVERNMENT PORTALS ACTIVE" not in index_txt:
        fail(f"index.html: Top telemetry bar does not show '{n_portals} GOVERNMENT PORTALS ACTIVE'")

    top_bar_m = re.search(
        r"LIVE MONITORING:.*?GOVERNMENT PORTALS ACTIVE.*?<span[^>]*>\s*(SAM\.GOV.*?)</span>",
        index_txt,
        flags=re.S,
    )
    if not top_bar_m:
        fail("index.html: Could not locate top telemetry bar portal ticker string")
    ticker_text = top_bar_m.group(1)

    state_abbrev_map = {
        "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
        "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
        "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
        "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
        "kentucky": "KT" if False else "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
        "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
        "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
        "new_hampshire": "NH", "new_jersey": "NJ", "new_mexico": "NM", "new_york": "NY",
        "north_carolina": "NC", "north_dakota": "ND", "ohio": "OH", "oklahoma": "OK",
        "oregon": "OR", "pennsylvania": "PA", "rhode_island": "RI", "south_carolina": "SC",
        "south_dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
        "vermont": "VT", "virginia": "VA", "washington": "WA", "west_virginia": "WV",
        "wisconsin": "WI", "wyoming": "WY",
    }
    for sk in state_keys:
        abbr = state_abbrev_map.get(sk, sk[:2].upper())
        if abbr not in ticker_text:
            fail(f"index.html: Top telemetry bar ticker '{ticker_text.strip()}' is missing portal abbreviation '{abbr}' for '{sk}'")
        if f'data-rfp-portal="{sk}"' not in index_txt:
            fail(f"index.html: Missing filter pill data-rfp-portal='{sk}' for active state portal '{sk}'")
        if f"STATE // {abbr}" not in index_txt:
            fail(f"index.html: Missing Section 4 portal card 'STATE // {abbr}' for active state portal '{sk}'")

    # 2. Verify all portal & state counts across index.html
    required_index_Phrases = [
        f"{n_portals} PORTALS DE-NOISED 24/7",
        f">{n_portals} Portals<",
        f"({n_portals} PORTALS LIVE)",
        f"All Portals ({n_portals})",
        f"{n_portals} PREVIEW LEADS SHOWN",
        f"// {n_portals} ACTIVE PROCUREMENT PORTALS",
        f"LIVE GOVCON INTELLIGENCE WIRE &bull; <span class=\"text-emerald-400\">{n_portals} PORTALS ACTIVE</span>",
        f"FEDERAL &amp; {n_states}-STATE SLED CONTRACT DIRECTORY",
        f"All {n_portals} Active Procurement Portals:",
        f"ALL {n_portals} FEDERAL &amp; SLED PORTAL MONITORS ACTIVE",
        f"{n_portals}-Portal Unified REST Feed",
        f"{n_portals} Federal, State SLED, and Municipal portals",
    ]
    for phrase in required_index_Phrases:
        if phrase not in index_txt:
            fail(f"index.html: Missing required portal-count phrase: '{phrase}'")

    # 3. Verify API 04 portal count parity in apis.html
    for phrase in (
        f"{n_portals}-Portal Unified REST Feed",
        f"{n_portals} Federal, State SLED, and Municipal portals",
        f"{n_portals}-Portal AI-Vetted Open IT/Cyber Solicitations",
        f"{n_portals}-Portal Filtered IT &amp; Cyber RFPs",
    ):
        if phrase not in apis_txt:
            fail(f"apis.html: Missing required portal-count phrase: '{phrase}'")

    # 4. Prohibit ANY stale portal or state count (from 3 up to n_portals-1 / n_states-1) across index.html, apis.html, and pseo_generator.py
    with open(os.path.join(BASE_DIR, "pseo_generator.py"), "r", encoding="utf-8") as f:
        pseo_txt = f.read()
    stale_patterns = []
    for kp in range(3, n_portals):
        stale_patterns.extend([
            f"{kp} GOVERNMENT PORTALS",
            f"{kp} PORTALS ACTIVE",
            f"{kp} PORTALS DE-NOISED",
            f">{kp} Portals<",
            f"({kp} PORTALS LIVE)",
            f"{kp} ACTIVE PROCUREMENT PORTALS",
            f"All Portals ({kp})",
            f"{kp} PREVIEW LEADS SHOWN",
            f"All {kp} Active Procurement Portals",
            f"ALL {kp} FEDERAL",
            f"{kp}-Portal",
            f"{kp}-portal",
            f"{kp}-PORTAL",
            f"{kp} portals",
            f"{kp} Portals Selected",
            f"Select All {kp}",
            f"{kp} / {kp} PORTALS SHOWN",
            f"{kp} / {kp} Active",
            f"{kp} Federal, State SLED, and Municipal portals",
            f'"portals_monitored"</span>: <span class="text-emerald-300">{kp}</span>',
        ])
    for ks in range(3, n_states):
        stale_patterns.extend([
            f"{ks}-State SLED",
            f"{ks}-STATE SLED",
            f"{ks} State SLED",
            f"{ks} major State SLED",
        ])

    for label, txt in (("index.html", index_txt), ("apis.html", apis_txt), ("pseo_generator.py", pseo_txt)):
        if "lg:top-[65px]" in txt:
            fail(f"{label}: Found 'lg:top-[65px]' sticky sub-bar offset; must be 'lg:top-[80px]' to clear the 80px header")
        for sp in stale_patterns:
            if sp in txt and re.search(rf"(?<![0-9]){re.escape(sp)}", txt):
                fail(f"{label}: Found stale portal/state count string '{sp}' (expected {n_portals} portals / {n_states} states)")

        # 5. Enforce that EVERY inline state-abbreviation list (e.g. "VA, TX, CA, FL..." or "TX, VA, CA, FL...") includes ALL active state abbreviations with zero duplicates
        expected_abbrs = [state_abbrev_map.get(sk, sk[:2].upper()) for sk in state_keys]
        for m in re.finditer(r"(?:VA,\s*TX,\s*CA,\s*FL|TX,\s*VA,\s*CA,\s*FL|SAM\.gov,\s*DemandStar,\s*VA,\s*TX)[^)<\n]{0,450}", txt):
            snippet = m.group(0)
            for abbr in expected_abbrs:
                occurrences = re.findall(rf"\b{abbr}\b", snippet)
                if not occurrences:
                    fail(f"{label}: State abbreviation list '{snippet.strip()}' is missing active state '{abbr}'")
                if len(occurrences) > 1:
                    fail(f"{label}: State abbreviation list '{snippet.strip()}' has duplicate state abbreviation '{abbr}'")

    # Verify all STATE // XX cards in Section 4 live INSIDE #coverage-portals-grid (never outside the grid container)
    cov_sec_m = re.search(r'<div id="coverage-portals-grid"[^>]*>([\s\S]*?)</section>', index_txt)
    if cov_sec_m:
        cov_body = cov_sec_m.group(1)
        # Split before any closing grid comments or verify zero "p-6 rounded-2xl" cards exist in #coverage
        if "p-6 rounded-2xl" in cov_body or "Browse WI RFPs" in cov_body:
            fail("index.html: #coverage contains non-standard 'p-6 rounded-2xl' cards outside #coverage-portals-grid")

        # 6. Enforce that every prose portal roll-call ("Virginia eVA, Texas ESBD, California Cal eProcure...") includes all active states
        for m in re.finditer(r"Virginia eVA,\s*Texas ESBD,\s*California Cal eProcure[^.<\n]{0,1400}", txt):
            snippet = m.group(0)
            for sk in state_keys:
                state_title = sk.replace("_", " ").title()
                if state_title not in snippet and state_abbrev_map.get(sk, "") not in snippet:
                    fail(f"{label}: Prose portal list '{snippet.strip()}' is missing active state '{state_title}'")


def check_tier_value_prop_and_capture_moat_parity(index_txt: str) -> None:
    """
    Enforces that:
      1. New Portals (1..P) are always reflected across Tier 1 and Tier 2 value propositions.
      2. ONLY APIs marked `connect_to_tier2_autopilot: true` in `daily_expansion_roadmap.json`
         (plus the baseline #01..#20 suite) are connected to `#capture-moat`, `#checkout-card-tier2`,
         and `pseo_generator.py` RFP dossiers.
      3. Specialized / post-award / niche APIs (`connect_to_tier2_autopilot: false`) MUST NOT
         be stuffed into `#capture-moat` or `#checkout-card-tier2` (preventing client feature bloat),
         and instead belong solely in the On-Demand Developer Catalog (`#page-apis` and `apis.html`).
    """
    import json
    import pseo_generator

    n_apis = len(re.findall(r'<article\s+id="product-[^"]+"', index_txt))
    jm = re.search(r"window\.SIGNALTENDER_JURISDICTIONS\s*=\s*(\{.*?\});", index_txt, flags=re.S)
    if jm:
        jurisdictions = json.loads(jm.group(1))
    else:
        jurisdictions = pseo_generator.JURISDICTIONS
    n_portals = len(jurisdictions)
    state_keys = [k for k in jurisdictions.keys() if k not in ("federal", "municipal")]
    n_states = len(state_keys)

    tier2_api_nums = list(range(1, 21))
    excluded_tier2_api_nums = []
    roadmap_path = os.path.join(BASE_DIR, "daily_expansion_roadmap.json")
    if os.path.exists(roadmap_path):
        with open(roadmap_path, "r", encoding="utf-8") as rf:
            rm_data = json.load(rf)
        for item in rm_data.get("items", []):
            api_num = item.get("api", {}).get("api_number")
            if not api_num or api_num > n_apis:
                continue
            if item.get("api", {}).get("connect_to_tier2_autopilot", False):
                if api_num not in tier2_api_nums:
                    tier2_api_nums.append(api_num)
            else:
                excluded_tier2_api_nums.append(api_num)

    n_tier2_apis = len(tier2_api_nums)

    # 1. Verify #capture-moat contains every Tier-2-relevant API number and excludes non-Tier-2 APIs
    m_moat = re.search(r'<section id="capture-moat".*?</section>', index_txt, flags=re.S)
    if not m_moat:
        fail("index.html: Missing <section id=\"capture-moat\">")
    moat_html = m_moat.group(0)
    for k in tier2_api_nums:
        tag = f"#{k:02d}"
        if tag not in moat_html:
            fail(f"index.html (#capture-moat): Missing reference to Tier-2-relevant API {tag}.")
    for k_ex in excluded_tier2_api_nums:
        tag_ex = f"#{k_ex:02d}"
        if tag_ex in moat_html:
            fail(f"index.html (#capture-moat): Found non-Tier-2 API {tag_ex} in #capture-moat! Do not bloat Tier 2 with connect_to_tier2_autopilot=false APIs.")
    for req_moat_phrase in (
        f"{n_portals}-PORTAL",
        f"{n_portals} PORTALS",
        f"{n_tier2_apis} AI ENGINES",
        f"{n_portals} Federal &amp; {n_states}-State SLED Portals",
    ):
        if req_moat_phrase not in moat_html:
            fail(f"index.html (#capture-moat): Missing required tier value-prop phrase '{req_moat_phrase}'")

    # 2. Verify Hero Tier 2 CTA card reflects N PORTALS + n_tier2_apis-API SUITE
    hero_phrase = f"TIER 2 // CAPTUREDESK AUTOPILOT ({n_portals} PORTALS + {n_tier2_apis}-API SUITE)"
    if hero_phrase not in index_txt:
        fail(f"index.html (Hero Tier 2 CTA): Missing '{hero_phrase}'")

    # 3. Verify #checkout-card-tier2 contains every Tier-2-relevant API number and excludes non-Tier-2 APIs
    m_t2 = re.search(r'<div id="checkout-card-tier2".*?(?:<div id="checkout-card-tier3"|<!-- \$0/mo Free Basic)', index_txt, flags=re.S)
    if not m_t2:
        fail("index.html: Missing #checkout-card-tier2")
    t2_html = m_t2.group(0)
    for k in tier2_api_nums:
        tag = f"#{k:02d}"
        if tag not in t2_html:
            fail(f"index.html (#checkout-card-tier2): Missing reference to Tier-2-relevant API {tag}.")
    for k_ex in excluded_tier2_api_nums:
        tag_ex = f"#{k_ex:02d}"
        if tag_ex in t2_html:
            fail(f"index.html (#checkout-card-tier2): Found non-Tier-2 API {tag_ex} in #checkout-card-tier2! Do not bloat Tier 2 with connect_to_tier2_autopilot=false APIs.")
    for req_t2_phrase in (
        f"{n_portals} PORTALS + {n_tier2_apis}-API CAPTURE SUITE",
        f"All-Access {n_portals}-Portal Wire + {n_tier2_apis}-Engine AI Capture Dossiers",
        f"Everything in Tier 1 (All {n_portals} Portals), Plus Full {n_tier2_apis}-Engine Capture Dossiers:",
    ):
        if req_t2_phrase not in t2_html:
            fail(f"index.html (#checkout-card-tier2): Missing required tier value-prop phrase '{req_t2_phrase}'")

    # 4. Verify #page-checkout Developer API Callout Banner & Deep-Dive Tier Panels (Tier 1, 2, 3, 4 & Matrix)
    callout_phrase = f"All {n_apis} individual SignalTender microservices"
    if callout_phrase not in index_txt:
        fail(f"index.html (#page-checkout API Callout): Missing '{callout_phrase}'")

    for deep_dive_phrase in (
        f"across {n_portals} government portals",
        f"{n_tier2_apis} specialized GovCon capture engines",
        f"// HOW THE {n_tier2_apis} PRE-AWARD CAPTURE ENGINES",
        f"across all {n_apis} SignalTender endpoints",
        f"{n_apis} deterministic GovCon microservices",
        f"across all {n_apis} GovCon microservices",
    ):
        if deep_dive_phrase not in index_txt:
            fail(f"index.html (#page-checkout Deep-Dive Tier Panels): Missing '{deep_dive_phrase}'")

    # 5. Verify pseo_generator.py RFP dossier box references the latest Tier-2-relevant API
    with open(os.path.join(BASE_DIR, "pseo_generator.py"), "r", encoding="utf-8") as f:
        pseo_src = f.read()
    latest_tier2_tag = f"#{max(tier2_api_nums):02d}"
    if latest_tier2_tag not in pseo_src:
        fail(f"pseo_generator.py: RFP Dossier preview is missing latest Tier-2-relevant API reference '{latest_tier2_tag}'")


def check_spa_runtime(index_txt: str) -> None:
    scripts = [
        m.group(2)
        for m in re.finditer(r"<script([^>]*)>(.*?)</script>", index_txt, flags=re.S | re.I)
        if "src=" not in m.group(1) and "application/ld+json" not in m.group(1)
    ]

    harness = (
        """
const elements = {};
function makeEl(id) {
  return {
    id: id || '',
    innerHTML: '',
    innerText: 'sample cybersecurity cmmc cloud lcat text',
    textContent: '',
    value: '',
    className: 'divide-y',
    offsetHeight: 600,
    style: {},
    dataset: {},
    tagName: 'DIV',
    classList: {
      _set: new Set(),
      add(...c) { c.forEach(x => this._set.add(x)); },
      remove(...c) { c.forEach(x => this._set.delete(x)); },
      contains(x) { return this._set.has(x); }
    },
    getAttribute(k) { return this[k] || null; },
    setAttribute(k, v) { this[k] = v; },
    getBoundingClientRect() { return { top: 120 }; },
    scrollIntoView() {},
    closest() { return makeEl('wrap'); },
    querySelector() { return makeEl('q'); },
    querySelectorAll() { return [makeEl('r1'), makeEl('r2')]; },
    appendChild() {},
    parentNode: { replaceChild() {}, insertBefore() {} },
    parentElement: { className: 'divide-y', offsetHeight: 500, style: {}, getAttribute(){return null;}, setAttribute(){} },
    addEventListener() {}
  };
}
global.window = global;
global.window.location = { hash: '#contracts' };
global.window.scrollTo = () => {};
global.window.scrollBy = () => {};
global.window.addEventListener = () => {};
global.fetch = () => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}), text: () => Promise.resolve('') });
global.localStorage = { getItem: () => '', setItem: () => {} };
global.document = {
  readyState: 'complete',
  title: '',
  body: makeEl('body'),
  documentElement: makeEl('html'),
  activeElement: makeEl('active'),
  getElementById(id) {
    if (!elements[id]) elements[id] = makeEl(id);
    return elements[id];
  },
  querySelector(sel) { return makeEl(sel); },
  querySelectorAll(sel) { return [makeEl(sel)]; },
  createElement(tag) { return makeEl(tag); },
  addEventListener() {}
};
global.tailwind = { config: {} };
"""
        + "\n;\n".join(scripts)
        + """
if (typeof window.renderContractsRoute !== 'function') {
  throw new Error('window.renderContractsRoute is undefined!');
}
window.renderContractsRoute('#contracts');
if (!document.getElementById('contracts-dynamic-root').innerHTML.includes('Federal &amp; State SLED IT Contract Directory')) {
  throw new Error('#contracts route rendered blank or invalid HTML!');
}
window.renderContractsRoute('#contracts/federal');
if (!document.getElementById('contracts-dynamic-root').innerHTML.includes('SAM.GOV')) {
  throw new Error('#contracts/federal route rendered blank or invalid HTML!');
}
if (!Array.isArray(window.SIGNALTENDER_CONTRACTS) || window.SIGNALTENDER_CONTRACTS.length === 0) {
  throw new Error('window.SIGNALTENDER_CONTRACTS is empty!');
}
const firstSlug = window.SIGNALTENDER_CONTRACTS[0].slug;
window.renderContractsRoute('#contracts/rfp/' + firstSlug);
if (!document.getElementById('contracts-dynamic-root').innerHTML.includes('CAPTUREDESK AI DOSSIER')) {
  throw new Error('#contracts/rfp/' + firstSlug + ' route failed to render dossier!');
}
window.filterContractsDirectory('cyber');
window.filterContractsDirectory('');
window.filterApiCatalog('cmmc', 'compliance');
window.filterApiCatalog('', 'all');
window.filterMainRfpTable('zero-trust', 'federal');
window.filterMainRfpTable('', 'all');
window.openApiSandbox('product-key-personnel');
window.closeApiSandbox();
window.setCheckoutBilling('annual');
window.setCheckoutBilling('monthly');
if (typeof window.selectInteractiveDossier !== 'function') {
  throw new Error('window.selectInteractiveDossier is undefined!');
}
window.selectInteractiveDossier('ohio');
window.selectInteractiveDossier('georgia');
window.selectInteractiveDossier('north_carolina');
window.selectInteractiveDossier('new_york');
window.selectInteractiveDossier('massachusetts');
window.selectInteractiveDossier('new_jersey');
window.selectInteractiveDossier('washington');
window.selectInteractiveDossier('michigan');
window.selectInteractiveDossier('colorado');
window.selectInteractiveDossier('federal');
if (typeof window.saveCompanyCaptureProfile !== 'function' || typeof window.shredRfpInStudio !== 'function') {
  throw new Error('Company Capture Profile Vault functions (saveCompanyCaptureProfile / shredRfpInStudio) are undefined!');
}
window.saveCompanyCaptureProfile();
window.applyCompanyProfileToSandbox();
window.shredRfpInStudio(firstSlug);
if (typeof window.updateCaptureRoiCalculator !== 'function') {
  throw new Error('window.updateCaptureRoiCalculator is undefined!');
}
window.updateCaptureRoiCalculator(6);
if (typeof window.submitInboundLeadCapture !== 'function') {
  throw new Error('window.submitInboundLeadCapture is undefined!');
}
const unlockedOk = window.submitInboundLeadCapture('capture@acmegovcyber.com', 'new_york', 'Acme GovCyber LLC');
if (!unlockedOk || !document.getElementById('inbound-lead-results').innerHTML.includes('DOSSIER #01 UNLOCKED')) {
  throw new Error('window.submitInboundLeadCapture failed to unlock and render 3 state RFP dossiers!');
}
if (typeof window.fireOutboundClickBeacon !== 'function') {
  throw new Error('window.fireOutboundClickBeacon is undefined!');
}
window.fireOutboundClickBeacon('dossier_view', 'https://signaltender.net/');
if (typeof window.switchAccountAuthTab !== 'function' || typeof window.renderAccountDashboard !== 'function') {
  throw new Error('Client Account Portal functions (switchAccountAuthTab / renderAccountDashboard) are undefined!');
}
window.switchAccountAuthTab('register');
window.switchAccountAuthTab('login');
window.renderAccountDashboard({
  email: 'capture@acmegovcyber.com',
  is_admin: false,
  full_name: 'Marcus Vance',
  company: 'Acme GovCyber LLC',
  subscription_status: 'active',
  active: true,
  tier: 'tier_2',
  tier_label: 'Tier 2 // CaptureDesk Autopilot ($399/mo)',
  api_key: 'st_live_test_key',
  discord_handle: 'marcus_vance',
  webhook_url: 'https://hooks.slack.com/services/T00/B00/X00',
  destination_type: 'slack',
  email_briefings_enabled: true
});
if (document.getElementById('account-admin-bar').innerHTML !== '') {
  throw new Error('Non-admin user must never have admin bar HTML rendered in DOM!');
}
if (window.switchAdminPortalPreview('tier_1') !== false) {
  throw new Error('Non-admin user must be blocked from calling switchAdminPortalPreview!');
}
window.renderAccountDashboard({
  email: 'admin@signaltender.net',
  is_admin: true,
  full_name: 'Aaron Chen (Founder & Admin)',
  company: 'SignalTender HQ',
  subscription_status: 'active',
  active: true,
  tier: 'tier_2',
  tier_label: 'Founder & Admin // Tier 2 CaptureDesk Autopilot ($399/mo)',
  api_key: 'st_live_admin_key',
  discord_handle: 'aarbchen',
  email_briefings_enabled: true
});
if (document.getElementById('account-admin-bar').innerHTML.indexOf('FOUNDER &amp; ADMIN CONSOLE') === -1 && document.getElementById('account-admin-bar').innerHTML.indexOf('FOUNDER & ADMIN CONSOLE') === -1) {
  throw new Error('Admin user did not receive #account-admin-bar switcher!');
}
window.switchAdminPortalPreview('tier_1');
if (document.getElementById('account-plan-badge').textContent.indexOf('Tier 1') === -1) {
  throw new Error('switchAdminPortalPreview(tier_1) did not update #account-plan-badge!');
}
window.switchAdminPortalPreview('free');
if (document.getElementById('account-plan-badge').textContent.indexOf('Free Explorer') === -1) {
  throw new Error('switchAdminPortalPreview(free) did not update #account-plan-badge!');
}
window.switchAdminPortalPreview('tier_2');
if (document.getElementById('account-plan-badge').textContent.indexOf('Tier 2') === -1) {
  throw new Error('switchAdminPortalPreview(tier_2) did not update #account-plan-badge!');
}
window.toggleAccountPortalFilter('virginia');
window.toggleAccountSetAsideFilter('sdvosb');
window.saveAccountAlertFilters();
window.saveAccountCompanyVault();
window.openStudioWithAccountVault();
window.openStudioWithAccountKey();
document.getElementById('account-team-cc-input').value = 'bd@acmegovcyber.com';
window.addAccountTeamCcEmail();
window.saveAccountDistribution({});
window.addAccountSavedRfp();
window.updateAccountSavedRfpStage(firstSlug, 'Writing Proposal');
window.triggerAccountDispatchNow();
window.setAccountBillingCycle('annual');
window.setAccountBillingCycle('monthly');
window.copyAccountMcpConfig();
document.getElementById('account-profile-name').value = 'Commander Alex Vance';
window.saveAccountProfile();
window.refreshClientAccount();
window.logoutClientAccount();
if (typeof window.switchOverviewProductTab !== 'function' || typeof window.switchCheckoutSectionTab !== 'function' || typeof window.switchAccountWorkspaceTab !== 'function' || typeof window.switchApiCatalogTab !== 'function') {
  throw new Error('Multi-tab workspace organization functions (switchOverviewProductTab / switchCheckoutSectionTab / switchAccountWorkspaceTab / switchApiCatalogTab) are undefined!');
}
window.switchOverviewProductTab('dossiers');
window.switchOverviewProductTab('proposal');
window.switchOverviewProductTab('coverage');
window.switchOverviewProductTab('integrations');
window.switchOverviewProductTab('all');
window.switchOverviewProductTab('wire');
window.switchCheckoutSectionTab('roi');
window.switchCheckoutSectionTab('benchmark');
window.switchCheckoutSectionTab('faq');
window.switchCheckoutSectionTab('all');
window.switchCheckoutSectionTab('preview');
window.switchAccountWorkspaceTab('filters');
window.switchAccountWorkspaceTab('pipeline');
window.switchAccountWorkspaceTab('all');
window.switchAccountWorkspaceTab('billing');
window.switchApiCatalogTab('directory');
window.switchApiCatalogTab('modules');
window.switchApiCatalogTab('matrix');
window.switchApiCatalogTab('all');
if (typeof window.jumpToPageSection !== 'function' || !window.jumpToPageSection('integrations') || !window.jumpToPageSection('capture-moat')) {
  throw new Error('window.jumpToPageSection failed to jump to in-page sections!');
}
if (typeof window.togglePageSectionSidebar !== 'function' || typeof window.renderPageSectionSidebar !== 'function') {
  throw new Error('Collapsible Page Section Sidebar functions (togglePageSectionSidebar / renderPageSectionSidebar) are undefined!');
}
document.getElementById('page-account').classList.add('hidden');
document.getElementById('page-checkout').classList.add('hidden');
document.getElementById('page-contracts').classList.add('hidden');
document.getElementById('page-apis').classList.add('hidden');
document.getElementById('page-main').classList.remove('hidden');
window.togglePageSectionSidebar(true);
window.renderPageSectionSidebar();
if (!document.getElementById('page-sidebar-items').innerHTML || document.getElementById('page-sidebar-items').innerHTML.length < 50) {
  throw new Error('Page Section Sidebar failed to populate sections!');
}
window.togglePageSectionSidebar(false);
if (typeof window.switchTrustTab !== 'function' || typeof window.submitAiConciergeContact !== 'function' || typeof window.submitHardenedFeedbackForm !== 'function') {
  throw new Error('Enterprise Trust, AI Concierge & Hardened Feedback functions are undefined!');
}
window.switchTrustTab('status');
window.switchTrustTab('security');
window.switchTrustTab('terms');
window.switchTrustTab('privacy');
window.switchTrustTab('contact');
window.prefillConciergeQuestion('plans_and_pricing', 'What is the difference between Tier 1 ($99), Tier 2 ($399), Tier 3 ($1,499), and Tier 4 ($2,499)?');
var conciergeText = (document.getElementById('concierge-answer-text') || {}).textContent || '';
if (!conciergeText || conciergeText.indexOf('Tier 1') === -1 || conciergeText.indexOf('Tier 3') === -1 || conciergeText.indexOf('Tier 4') === -1) {
  throw new Error('AI Support Concierge failed to render instant on-screen answer with all 4 tiers (Tier 1 - Tier 4)!');
}
document.getElementById('concierge-question').value = '<script>alert(1)</script>';
if (window.submitAiConciergeContact() !== false) {
  throw new Error('WAF sanitizer failed to block malicious <script> payload in AI Concierge!');
}
window.switchTrustTab('feedback');
document.getElementById('feedback-message').value = '<script>evil()</script>';
if (window.submitHardenedFeedbackForm() !== false) {
  throw new Error('WAF sanitizer failed to block malicious <script> payload in Feedback form!');
}
document.getElementById('feedback-message').value = 'Please add Washington WEBS and Michigan SIGMA state portals to the 6-hour SLED scraper.';
if (window.submitHardenedFeedbackForm() !== true) {
  throw new Error('Hardened Feedback form rejected clean plain-text portal request!');
}
if (
  typeof window.filterCoveragePortalGrid !== 'function' ||
  typeof window.toggleRfpBookmark !== 'function' ||
  typeof window.setSpaContractsQuickFilter !== 'function' ||
  typeof window.sortSpaContractsTable !== 'function' ||
  typeof window.toggleCheckoutDeliveryDrawer !== 'function' ||
  typeof window.highlightRecommendedTier !== 'function' ||
  typeof window.copyMcpServerConfig !== 'function' ||
  typeof window.toggleApiCatalogCompactView !== 'function'
) {
  throw new Error('User-friendliness UX upgrade functions are undefined!');
}
window.filterCoveragePortalGrid('east');
window.filterCoveragePortalGrid('all');
window.toggleRfpBookmark(firstSlug);
window.setSpaContractsQuickFilter('saved');
window.setSpaContractsQuickFilter('all');
window.sortSpaContractsTable('due_asc');
window.sortSpaContractsTable('default');
window.toggleCheckoutDeliveryDrawer();
window.highlightRecommendedTier('tier2');
if (typeof window.refreshCrowdWrapIndex !== 'function' || typeof window.confirmBilateralTeamingHandshake !== 'function' || typeof window.launchTier3ProposalAutopilot !== 'function') {
  throw new Error('M1/M2/ProposalAutopilot functions (refreshCrowdWrapIndex / confirmBilateralTeamingHandshake / launchTier3ProposalAutopilot) are undefined!');
}
window.launchTier3ProposalAutopilot(firstSlug);
window.refreshCrowdWrapIndex();
window.confirmBilateralTeamingHandshake();
window.toggleApiCatalogCompactView();
window.toggleApiCatalogCompactView();
process.exit(0);
"""
    )

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
        tf.write(harness)
        tname = tf.name
    r = subprocess.run(["node", tname], capture_output=True, text=True)
    os.remove(tname)
    if r.returncode != 0:
        fail(f"Headless SPA runtime check failed:\n{r.stderr}")


def check_conversion_and_distribution_surfaces(index_txt: str) -> None:
    """
    Enforces 100% portal (n_portals), state (n_states), and API (n_apis) parity across all
    customer-facing conversion, outbound cold email, reply responder, subscriber delivery,
    social distribution, and backend router surfaces so customers never see stale counts or missing states.
    """
    import pseo_generator

    n_apis = len(re.findall(r'<article\s+id="product-[^"]+"', index_txt))
    jm = re.search(r"window\.SIGNALTENDER_JURISDICTIONS\s*=\s*(\{.*?\});", index_txt, flags=re.S)
    if jm:
        jurisdictions = json.loads(jm.group(1))
    else:
        jurisdictions = pseo_generator.JURISDICTIONS
    n_portals = len(jurisdictions)
    state_keys = [k for k in jurisdictions.keys() if k not in ("federal", "municipal")]
    n_states = len(state_keys)

    stale_portal_tokens = []
    for kp in range(3, n_portals):
        stale_portal_tokens.extend([
            f"{kp}-Portal",
            f"{kp}-portal",
            f"{kp} Portals",
            f"{kp} portals",
            f"{kp} government portals",
            f"{kp} Federal &",
            f"{kp} federal and state portals",
        ])
    stale_state_tokens = []
    for ks in range(3, n_states):
        stale_state_tokens.extend([
            f"{ks}-State SLED",
            f"{ks}-STATE SLED",
            f"{ks} State SLED",
            f"{ks} state SLED",
        ])
    for ko in range(3, n_states - 1):
        stale_state_tokens.extend([
            f"plus {ko} other state SLED portals",
            f"and {ko} additional state procurement portals",
        ])
    stale_api_tokens = []
    for ka in range(10, n_apis):
        stale_api_tokens.extend([
            f"All {ka} REST APIs",
            f"test all {ka} AI",
            f"{ka} GovCon REST & MCP APIs",
            f"{ka}-Tool Official MCP",
            f"{ka} stateless GovCon",
        ])

    surfaces_to_audit = [
        ("outreach_generator.py", os.path.join(BASE_DIR, "outreach_generator.py")),
        ("outbound_reply_responder.py", os.path.join(BASE_DIR, "outbound_reply_responder.py")),
        ("client_delivery.py", os.path.join(BASE_DIR, "client_delivery.py")),
        ("linkedin_autoposter.py", os.path.join(BASE_DIR, "linkedin_autoposter.py")),
        ("x_autoposter.py", os.path.join(BASE_DIR, "x_autoposter.py")),
        ("social_distribution_kit.py", os.path.join(BASE_DIR, "social_distribution_kit.py")),
        ("campaign_leads.csv", os.path.join(BASE_DIR, "campaign_leads.csv")),
        ("outbox_ready_queue.json", os.path.join(BASE_DIR, "outbox_ready_queue.json")),
        ("mcp-server/index.js", os.path.join(BASE_DIR, "mcp-server", "index.js")),
        ("api/routers/leads.py", r"d:\Data API Ecosystem\api\routers\leads.py"),
        ("api/routers/stripe_webhook.py", r"d:\Data API Ecosystem\api\routers\stripe_webhook.py"),
        ("api/routers/solicitations.py", r"d:\Data API Ecosystem\api\routers\solicitations.py"),
        ("api/routers/proposal_compiler.py", r"d:\Data API Ecosystem\api\routers\proposal_compiler.py"),
        ("api/routers/mcp.py", r"d:\Data API Ecosystem\api\routers\mcp.py"),
        ("api/routers/support.py", r"d:\Data API Ecosystem\api\routers\support.py"),
    ]

    loaded_texts = {}
    for label, fpath in surfaces_to_audit:
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            txt = f.read()
        loaded_texts[label] = txt
        for tok in stale_portal_tokens + stale_state_tokens + stale_api_tokens:
            if tok in txt and re.search(rf"(?<![0-9]){re.escape(tok)}", txt):
                fail(
                    f"{label}: Found stale customer-facing count '{tok}' "
                    f"(expected {n_portals} portals / {n_states} states / {n_apis} APIs). "
                    f"Update {label} and regenerate campaign_leads.csv / outbox_ready_queue.json."
                )

    # Verify every active state key is registered in leads.py, stripe_webhook.py, solicitations.py, proposal_compiler.py, and x_autoposter.py
    for state_key in state_keys:
        for req_surface in ("api/routers/leads.py", "api/routers/stripe_webhook.py", "api/routers/solicitations.py", "api/routers/proposal_compiler.py", "x_autoposter.py"):
            if req_surface in loaded_texts and f'"{state_key}"' not in loaded_texts[req_surface] and f"'{state_key}'" not in loaded_texts[req_surface]:
                fail(f"{req_surface}: Missing active state key '{state_key}' in conversion/distribution map")

    # Verify MCP servers support st_live_ / X-SignalTender-Key routing
    if "api/routers/mcp.py" in loaded_texts and "X-SignalTender-Key" not in loaded_texts["api/routers/mcp.py"]:
        fail("api/routers/mcp.py: Missing direct X-SignalTender-Key routing for Tier 2 st_live_... API keys")
    if "mcp-server/index.js" in loaded_texts and "X-SignalTender-Key" not in loaded_texts["mcp-server/index.js"]:
        fail("mcp-server/index.js: Missing direct X-SignalTender-Key routing for Tier 2 st_live_... API keys")


def check_anti_regression_guardrails(index_txt: str, apis_txt: str) -> None:
    """
    Permanent anti-regression guardrails across all 4 tiers, scrapers, and APIs:
      1. Scraper Determinism & Zero SF-30 Duplicates:
         - Zero `timedelta(` or `abs(hash(` in any scraper file (`*_scraper.py`, `sled-scraper/sledscraper.py`).
         - Zero `sf-30-addendum-detected` static pages in `contracts/rfp/` and zero `#sf30-` or `[SF-30` in `index.html`.
      2. 4-Tier Billing, Webhook & Delivery Parity:
         - `stripe_webhook.py` exports `billing_router` (`/create-checkout-session`) and supports `tier_1`..`tier_4`.
         - `client_delivery.py` preserves `tier_3` and `tier_4` in email briefings and webhook payloads.
         - `support.py` registers both `/support/concierge` and `/support/chat`.
      3. Duplicate Badge & Stale Tier-2 Count Prevention + API_META Parity:
         - Zero duplicate `+ #XX + #XX` badges in `index.html` or `apis.html`.
         - `API_META['product-live-solicitations'].kw` in `index.html` matches `apis.html` and includes every active state.
      4. Dual MCP Server Count & 5/5 Glama TDQS Parity:
         - `d:\\Data API Ecosystem\\api\\routers\\mcp.py` and `d:\\Daas\\mcp-server\\index.js` both register `n_apis` tools
           with zero `"API #"` description prefixes.
    """
    import pseo_generator

    n_apis = len(re.findall(r'<article\s+id="product-[^"]+"', index_txt))
    jm = re.search(r"window\.SIGNALTENDER_JURISDICTIONS\s*=\s*(\{.*?\});", index_txt, flags=re.S)
    jurisdictions = json.loads(jm.group(1)) if jm else pseo_generator.JURISDICTIONS
    state_keys = [k for k in jurisdictions.keys() if k not in ("federal", "municipal")]

    # 1. Scraper Determinism & Zero SF-30 Duplicates
    scraper_files = sorted(glob.glob(os.path.join(BASE_DIR, "*_scraper.py")))
    sled_file = os.path.join(BASE_DIR, "sled-scraper", "sledscraper.py")
    if os.path.exists(sled_file):
        scraper_files.append(sled_file)
    for sf_path in scraper_files:
        sf_name = os.path.basename(sf_path)
        with open(sf_path, "r", encoding="utf-8", errors="replace") as sf:
            sf_src = sf.read()
        if "timedelta(" in sf_src:
            fail(f"{sf_name}: Uses rolling `timedelta(` date math! All scraper fallback dates must use deterministic anchored calendar dates.")
        if "abs(hash(" in sf_src:
            fail(f"{sf_name}: Uses process-salted `abs(hash(`! Use `hashlib.sha256(...).hexdigest()` for deterministic solicitation IDs.")

    sf30_html_files = glob.glob(os.path.join(BASE_DIR, "contracts", "rfp", "*sf-30-addendum-detected*.html"))
    if sf30_html_files:
        fail(f"Found {len(sf30_html_files)} synthetic SF-30 duplicate HTML files in contracts/rfp/ (e.g. {os.path.basename(sf30_html_files[0])})")
    if "sf-30-addendum-detected" in index_txt or "#sf30-" in index_txt or "[SF-30 / ADDENDUM" in index_txt or "[SF-30 ADDENDUM" in index_txt:
        fail("index.html: Found synthetic SF-30 addendum duplicate row in embedded contract directory!")

    # 2. 4-Tier Billing, Webhook & Delivery Parity
    sw_path = r"d:\Data API Ecosystem\api\routers\stripe_webhook.py"
    if os.path.exists(sw_path):
        with open(sw_path, "r", encoding="utf-8", errors="replace") as swf:
            sw_src = swf.read()
        if "billing_router" not in sw_src or "/create-checkout-session" not in sw_src:
            fail("api/routers/stripe_webhook.py: Missing `billing_router` (`POST /v1/billing/create-checkout-session`) for dynamic 4-tier checkout!")
        for t_key in ("tier_1", "tier_2", "tier_3", "tier_4"):
            if f'"{t_key}"' not in sw_src:
                fail(f"api/routers/stripe_webhook.py: Missing support for tier '{t_key}'")

    cd_path = os.path.join(BASE_DIR, "client_delivery.py")
    if os.path.exists(cd_path):
        with open(cd_path, "r", encoding="utf-8", errors="replace") as cdf:
            cd_src = cdf.read()
        for t_key in ("tier_1", "tier_2", "tier_3", "tier_4"):
            if f'"{t_key}"' not in cd_src:
                fail(f"client_delivery.py: Missing support for tier '{t_key}'")

    sup_path = r"d:\Data API Ecosystem\api\routers\support.py"
    if os.path.exists(sup_path):
        with open(sup_path, "r", encoding="utf-8", errors="replace") as supf:
            sup_src = supf.read()
        if '"/support/chat"' not in sup_src or '"/support/contact"' not in sup_src:
            fail("api/routers/support.py: Must register both `/support/contact` and `/support/chat` endpoints!")

    # 3. Duplicate Badge Prevention & API_META['product-live-solicitations'].kw Parity
    for label, txt in (("index.html", index_txt), ("apis.html", apis_txt)):
        dup_badge_m = re.search(r"\+\s*#(\d{2})\s+\+\s*#\1\b", txt)
        if dup_badge_m:
            fail(f"{label}: Found duplicate API badge '+ #{dup_badge_m.group(1)} + #{dup_badge_m.group(1)}'")

    m_kw_idx = re.search(r"'product-live-solicitations'\s*:\s*\{\s*cat\s*:\s*'[^']*'\s*,\s*kw\s*:\s*'([^']*)'", index_txt)
    m_kw_api = re.search(r"'product-live-solicitations'\s*:\s*\{\s*cat\s*:\s*'[^']*'\s*,\s*kw\s*:\s*'([^']*)'", apis_txt)
    if not m_kw_idx or not m_kw_api:
        fail("Missing API_META['product-live-solicitations'].kw in index.html or apis.html")
    if m_kw_idx.group(1) != m_kw_api.group(1):
        fail("API_META['product-live-solicitations'].kw in index.html does not match apis.html!")
    kw_live = m_kw_idx.group(1).lower()
    for sk in state_keys:
        st_words = sk.replace("_", " ").lower()
        if st_words not in kw_live:
            fail(f"API_META['product-live-solicitations'].kw is missing active state '{st_words}'")

    # 4. Dual MCP Server Count & Zero Catalog Prefixes
    mcp_py_path = r"d:\Data API Ecosystem\api\routers\mcp.py"
    if os.path.exists(mcp_py_path):
        with open(mcp_py_path, "r", encoding="utf-8", errors="replace") as mf:
            mcp_py_src = mf.read()
        py_routes = re.findall(r'"([a-z0-9_]+)"\s*:\s*\{\s*"method"\s*:\s*"(?:GET|POST)"', mcp_py_src)
        if len(py_routes) != n_apis:
            fail(f"api/routers/mcp.py: ENDPOINT_MAP has {len(py_routes)} tools, expected {n_apis}")
        if re.search(r'"description"\s*:\s*\(\s*"API\s*#', mcp_py_src):
            fail("api/routers/mcp.py: Found prohibited 'API #XX:' prefix in MCP tool description (violates 5/5 Glama TDQS)")

    mcp_js_path = os.path.join(BASE_DIR, "mcp-server", "index.js")
    if os.path.exists(mcp_js_path):
        with open(mcp_js_path, "r", encoding="utf-8", errors="replace") as jf:
            mcp_js_src = jf.read()
        js_routes = re.findall(r'^\s*([a-z0-9_]+)\s*:\s*\{\s*method\s*:\s*"(?:GET|POST)"', mcp_js_src, flags=re.M)
        if len(js_routes) != n_apis:
            fail(f"mcp-server/index.js: ENDPOINT_MAP has {len(js_routes)} tools, expected {n_apis}")
        if re.search(r'description\s*:\s*"API\s*#', mcp_js_src):
            fail("mcp-server/index.js: Found prohibited 'API #XX:' prefix in MCP tool description (violates 5/5 Glama TDQS)")


def check_acquisition_and_email_guardrails() -> None:
    """
    Permanent automated guardrails ensuring email & acquisition channel bugs can never regress:
      1. 100% 75-char Slug & `official_bid_url` Parity across `pseo_generator.py`, `client_delivery.py`,
         `capturedesk_autopilot.py`, and `d:\\Data API Ecosystem\\api\\routers\\solicitations.py`.
      2. Stateless Render Cron Supabase State Persistence (`subscriber://...`) across all 6 stateful
         cron jobs (`govcon_lead_harvester.py`, `outbound_reply_responder.py`, `x_autoposter.py`,
         `linkedin_autoposter.py`, `capturedesk_autopilot.py`, `autonomous_mailbox_scaler.py`).
      3. 14-Day Mailbox Warmup Age Gate (`outbound_mailer.is_instantly_account_warmed`) & Non-Destructive
         In-Flight Sequence Refresh (`outreach_generator.py` only deletes `status == 3`).
      4. Quoted-Footer Strip Before Opt-Out Classification (`outbound_reply_responder.classify_reply_intent`).
      5. Transactional Email Re-Send & `@signaltender.net` Bounce Protection (`client_delivery.py`,
         `leads.py`, `stripe_webhook.py`).
      6. Outbound Abandoned-Checkout Radar Instantly V2 Lookup (`leads.py`).
    """
    from datetime import datetime, timezone
    import pseo_generator
    import client_delivery
    import capturedesk_autopilot
    import outbound_mailer
    import outbound_reply_responder

    # 1. Cross-repo 75-char slug parity & official_bid_url verification
    test_title = "[SF-30 / ADDENDUM DETECTED] DISA Cybersecurity Service Provider (CSSP) / J34 External Vulnerability Scans and Web Vulnerability Scans - Due: 11/30/2026"
    expected_slug = "disa-cybersecurity-service-provider-cssp-j34-external-vulnerability-scans-200"
    s_pseo = pseo_generator.slugify(test_title, fallback_id="200")
    s_cd = client_delivery.slugify_contract(test_title, fallback_id="200")
    s_cap = capturedesk_autopilot.slugify_contract(test_title, fallback_id="200")
    if not (s_pseo == s_cd == s_cap == expected_slug):
        fail(f"Slug mismatch across Daas modules: pseo={s_pseo}, client_delivery={s_cd}, capturedesk={s_cap}, expected={expected_slug}")

    sol_router_path = r"d:\Data API Ecosystem\api\routers\solicitations.py"
    sol_schema_path = r"d:\Data API Ecosystem\schemas\solicitations.py"
    if os.path.exists(sol_router_path) and os.path.exists(sol_schema_path):
        with open(sol_router_path, "r", encoding="utf-8", errors="replace") as f:
            sol_src = f.read()
        with open(sol_schema_path, "r", encoding="utf-8", errors="replace") as f:
            schema_src = f.read()
        if "if len(s) > 75:" not in sol_src or "if len(s) > 65:" in sol_src:
            fail("api/routers/solicitations.py: `_slugify()` must use 75-char word-boundary truncation matching pseo_generator.py (never 65 chars)!")
        if "official_bid_url=" not in sol_src or "official_bid_url:" not in schema_src:
            fail("solicitations.py / schemas/solicitations.py: Missing `official_bid_url` field on LiveSolicitationRecord!")

    # 2. Stateless Render Cron Supabase State Persistence across all 6 stateful cron modules
    cron_state_contracts = [
        ("govcon_lead_harvester.py", "subscriber://outbound-archive/master"),
        ("outbound_reply_responder.py", "subscriber://outbound-replies/processed"),
        ("x_autoposter.py", "subscriber://social-x/posted-slugs"),
        ("linkedin_autoposter.py", "subscriber://social-linkedin/state"),
        ("capturedesk_autopilot.py", "subscriber://capturedesk/dossiers-cache"),
        ("autonomous_mailbox_scaler.py", "subscriber://treasury/mailbox-scaler-ledger"),
    ]
    for fname, state_uri in cron_state_contracts:
        fpath = os.path.join(BASE_DIR, fname)
        if not os.path.exists(fpath):
            fail(f"Missing required acquisition module: {fname}")
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            fsrc = f.read()
        if state_uri not in fsrc:
            fail(f"{fname}: Missing stateless Render Cron Supabase state sync (`{state_uri}`)!")

    mainscraper_path = os.path.join(BASE_DIR, "mainscraper.py")
    if os.path.exists(mainscraper_path):
        with open(mainscraper_path, "r", encoding="utf-8", errors="replace") as f:
            ms_src = f.read()
        if "autonomous_mailbox_scaler.run_autonomous_mailbox_scaler()" not in ms_src:
            fail("mainscraper.py: Missing `autonomous_mailbox_scaler.run_autonomous_mailbox_scaler()` in 6-hour cron orchestrator!")

    # 3. Mailbox Warmup Health Gate (score >= 85 active immediately, no artificial 14-day block) & Non-Destructive Sequence Refresh
    warmed_acct = {
        "email": "test@try-signaltender.com",
        "status": 1,
        "warmup_status": 1,
        "stat_warmup_score": 100,
        "timestamp_created": datetime.now(timezone.utc).isoformat(),
    }
    low_score_acct = {
        "email": "cold@try-signaltender.com",
        "status": 1,
        "warmup_status": 1,
        "stat_warmup_score": 50,
    }
    if outbound_mailer.is_instantly_account_warmed(warmed_acct) is not True:
        fail("outbound_mailer.is_instantly_account_warmed() erroneously blocked a warmed mailbox with stat_warmup_score=100!")
    if outbound_mailer.is_instantly_account_warmed(low_score_acct) is not False:
        fail("outbound_mailer.is_instantly_account_warmed() failed to block an unhealthy mailbox with stat_warmup_score=50!")

    og_path = os.path.join(BASE_DIR, "outreach_generator.py")
    if os.path.exists(og_path):
        with open(og_path, "r", encoding="utf-8", errors="replace") as f:
            og_src = f.read()
        if "lead_status == 3" not in og_src or "in_flight_inst_emails" not in og_src:
            fail("outreach_generator.py: Must only delete completed (`lead_status == 3`) leads in Instantly and preserve in-flight (`in_flight_inst_emails`) sequences!")
        if "accounts/warmup/disable" in og_src:
            fail("outreach_generator.py: Must NEVER call `accounts/warmup/disable` or detach active warmed mailboxes (`score >= 85`) from the campaign!")

    # 4. Quoted-Footer Strip Before Opt-Out Classification
    positive_reply_with_quoted_footer = (
        "Hi Aaron, yes please send over the Virginia eVA cybersecurity dossier for our capture team!\n\n"
        "On Thu, Oct 29, 2026 at 9:00 AM Aaron Chen <aaron.chen@get-signaltender.com> wrote:\n"
        "> Best,\n"
        "> Aaron Chen\n"
        "> Reply \"stop\" or \"unsubscribe\" anytime to opt out."
    )
    stripped_reply = outbound_reply_responder._strip_quoted_thread(positive_reply_with_quoted_footer).lower()
    if "unsubscribe" in stripped_reply or "stop" in stripped_reply:
        fail("outbound_reply_responder._strip_quoted_thread() failed to strip quoted footer text before opt-out classification!")

    # 5. Transactional Email Re-Send & Self-Domain Bounce Protection + 6. Outbound Abandoned-Checkout Radar
    transactional_files = [
        ("client_delivery.py", os.path.join(BASE_DIR, "client_delivery.py")),
        ("api/routers/leads.py", r"d:\Data API Ecosystem\api\routers\leads.py"),
        ("api/routers/stripe_webhook.py", r"d:\Data API Ecosystem\api\routers\stripe_webhook.py"),
    ]
    for label, tpath in transactional_files:
        if os.path.exists(tpath):
            with open(tpath, "r", encoding="utf-8", errors="replace") as f:
                tsrc = f.read()
            if "https://api.instantly.ai/api/v2/leads/list" not in tsrc:
                fail(f"{label}: Missing Instantly V2 existing-lead check (`leads/list`) before transactional re-insertion!")
            if "@signaltender.net" not in tsrc:
                fail(f"{label}: Missing `@signaltender.net` self-domain bounce filter!")

    leads_py_path = r"d:\Data API Ecosystem\api\routers\leads.py"
    if os.path.exists(leads_py_path):
        with open(leads_py_path, "r", encoding="utf-8", errors="replace") as f:
            lsrc = f.read()
        m_fn = re.search(r"async def _dispatch_abandoned_checkout_followup\(.*?\n(?=async def |\Z)", lsrc, flags=re.S)
        if not m_fn or "https://api.instantly.ai/api/v2/leads/list" not in m_fn.group(0):
            fail("api/routers/leads.py: `_dispatch_abandoned_checkout_followup()` is missing Instantly V2 outbound campaign lead lookup!")


def check_product_output_quality_controls() -> None:
    """
    RULE-008-PRODUCT-OUTPUT-QUALITY-GATE:
    Permanent end-to-end quality gate verifying that all customer-facing deliverables
    (6-file Shipley Proposal .ZIP packages, FOIA/CPRA/PIA statutory demand letters,
    USAspending corporate teaming partner matching, LCAT labor tables, wrap-rate telemetry,
    bilateral teaming handshakes, and live solicitation feeds) produce 100% jurisdiction-accurate,
    defect-free output with zero cross-state leakage, zero non-corporate pool names,
    zero broken LCAT splits, and zero internal `subscriber://*` state leakage.
    """
    import asyncio
    import io
    import types
    import zipfile

    # 1. Verify USAspending vault purity across both repos (zero synthetic SLED-* schedule rows)
    vault_daas = os.path.join(BASE_DIR, "usaspending_verified_vault.json")
    vault_eco = r"d:\Data API Ecosystem\api\routers\usaspending_verified_vault.json"
    for vlabel, vpath in (("Daas vault", vault_daas), ("Ecosystem vault", vault_eco)):
        if not os.path.exists(vpath):
            fail(f"Missing {vlabel} at {vpath}")
        with open(vpath, "r", encoding="utf-8", errors="replace") as vf:
            vdata = json.load(vf)
        awards = vdata if isinstance(vdata, list) else vdata.get("awards", [])
        if len(awards) < 200:
            fail(f"{vlabel}: Expected >= 200 verified USAspending awards, found {len(awards)}")
        for aw in awards:
            cid = str(aw.get("award_id") or aw.get("contract_id") or "")
            rec = str(aw.get("winning_vendor") or aw.get("recipient_name") or "")
            if cid.startswith("SLED-") or "Pool" in rec or "Schedule" in rec:
                fail(f"{vlabel}: Found synthetic/non-corporate row ({cid} / {rec}) in usaspending_verified_vault.json!")

    # 2. Verify solicitations.py and stripe_webhook.py exclude subscriber://* rows using PostgREST '*' wildcard
    for rlabel, rpath in (
        ("api/routers/solicitations.py", r"d:\Data API Ecosystem\api\routers\solicitations.py"),
        ("api/routers/stripe_webhook.py", r"d:\Data API Ecosystem\api\routers\stripe_webhook.py"),
    ):
        if os.path.exists(rpath):
            with open(rpath, "r", encoding="utf-8", errors="replace") as rf:
                rsrc = rf.read()
            if "not.like.subscriber://%" in rsrc:
                fail(f"{rlabel}: Uses SQL '%' wildcard `not.like.subscriber://%` instead of PostgREST '*' wildcard `not.like.subscriber://*`!")
            if "not.like.subscriber://*" not in rsrc:
                fail(f"{rlabel}: Missing `not.like.subscriber://*` filter to exclude internal state rows from live contract queries!")

    # 3. Execute end-to-end 6-file Shipley Proposal .ZIP & Vault/M1/M2 verification on proposal_compiler.py
    eco_root = r"d:\Data API Ecosystem"
    if eco_root not in sys.path:
        sys.path.insert(0, eco_root)

    try:
        import fastapi  # noqa: F401
    except ImportError:
        fa = types.ModuleType("fastapi")

        class _DummyRouter:
            def __init__(self, *a, **kw):
                pass

            def get(self, *a, **kw):
                return lambda fn: fn

            def post(self, *a, **kw):
                return lambda fn: fn

        class _DummyHTTPException(Exception):
            def __init__(self, status_code: int = 500, detail: str = ""):
                self.status_code = status_code
                self.detail = detail
                super().__init__(f"HTTP {status_code}: {detail}")

        fa.APIRouter = _DummyRouter
        fa.Header = lambda default=None, **kw: default
        fa.Query = lambda default=None, **kw: default
        fa.Response = object
        fa.status = types.SimpleNamespace(HTTP_200_OK=200, HTTP_400_BAD_REQUEST=400, HTTP_500_INTERNAL_SERVER_ERROR=500)
        fa.HTTPException = _DummyHTTPException
        sys.modules["fastapi"] = fa

    try:
        import core.config  # noqa: F401
    except Exception:
        core_mod = types.ModuleType("core")
        cfg_mod = types.ModuleType("core.config")

        class _DummySettings:
            anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
            anthropic_model = "claude-sonnet-5-5"
            rapidapi_proxy_secret = os.getenv("RAPIDAPI_PROXY_SECRET", "")

            def __getattr__(self, name: str) -> str:
                return os.getenv(name, "") or os.getenv(name.upper(), "")

        cfg_mod.settings = _DummySettings()
        core_mod.config = cfg_mod
        sys.modules["core"] = core_mod
        sys.modules["core.config"] = cfg_mod

    import importlib.util

    pc_spec = importlib.util.spec_from_file_location(
        "proposal_compiler_under_test",
        r"d:\Data API Ecosystem\api\routers\proposal_compiler.py",
    )
    pc = importlib.util.module_from_spec(pc_spec)
    assert pc_spec and pc_spec.loader
    pc_spec.loader.exec_module(pc)

    async def _run_compiler_suite() -> None:
        import html as _html

        def _extract_openxml_text(inner_bytes: bytes) -> str:
            with zipfile.ZipFile(io.BytesIO(inner_bytes)) as inner_zf:
                chunks = []
                for nm in inner_zf.namelist():
                    if nm.endswith(".xml"):
                        raw_xml = inner_zf.read(nm).decode("utf-8", errors="replace")
                        chunks.append(_html.unescape(re.sub(r"<[^>]+>", " ", raw_xml)))
                return "\n".join(chunks)

        # Scenario A: California Caltrans 0000034018 + Fuse Integration (Will Thomas scenario)
        req_ca = pc.ProposalCompileRequest(
            solicitation_id="0000034018",
            solicitation_title="[0000034018] CALIFORNIA DEPARTMENT OF TRANSPORTATION — Enterprise Traffic Management & Cloud Telemetry Modernization",
            agency="California Department of Transportation (Caltrans)",
            naics="541512",
            company_name="Fuse Integration",
            target_margin_pct=18.5,
            key_personnel_lcats="Cleared Cyber Program Manager (PMP/CISSP) • Lead Zero-Trust Cloud Architect • Senior DevSecOps Automation Engineer",
            past_performance_refs="",
            rfp_text="",
            download_zip=False,
            suppress_vault_persist=True,
        )
        res_ca = await pc.compile_full_proposal_package(req_ca)
        zf_ca = zipfile.ZipFile(io.BytesIO(pc.base64.b64decode(res_ca["zip_base64"])))
        names_ca = sorted(zf_ca.namelist())
        if len(names_ca) != 6:
            fail(f"proposal_compiler.py: Expected 6 files in .ZIP, got {len(names_ca)}: {names_ca}")
        vol1_ca = _extract_openxml_text(zf_ca.read("Volume_I_Technical_and_Management_Proposal.docx"))
        vol2_ca = _extract_openxml_text(zf_ca.read("Volume_II_CLIN_Cost_and_Price_to_Win_Model.xlsx"))
        vol3_ca = _extract_openxml_text(zf_ca.read("Volume_III_Past_Performance_Teaming_and_Compliance.docx"))
        vol4_ca = _extract_openxml_text(zf_ca.read("Volume_IV_FAR_Subpart_9_6_Teaming_Agreement_and_13_CFR_125_6_Exhibit_A.docx"))
        vol5_ca = _extract_openxml_text(zf_ca.read("Volume_V_Statutory_FOIA_and_State_PIA_Incumbent_Contract_Demand.docx"))
        manifest_ca = zf_ca.read("00_Shipley_Submission_Readiness_Manifest.json").decode("utf-8")
        combined_ca = "\n".join([vol1_ca, vol2_ca, vol3_ca, vol4_ca, vol5_ca, manifest_ca])

        if "DZZ3WVXGEHW8" not in vol1_ca or "N0042125F0484" not in vol3_ca:
            fail("proposal_compiler.py: Failed to auto-enrich known contractor 'Fuse Integration' with SAM UEI DZZ3WVXGEHW8 and Navy contract N0042125F0484!")
        for forbidden_ca in ("tn.gov", "tennessee", "tdot", "missouri", "south carolina", "5 u.s.c. § 552", "freedom of information act (5 u.s.c."):
            if forbidden_ca in combined_ca.lower():
                fail(f"proposal_compiler.py: Cross-jurisdiction or federal FOIA leak '{forbidden_ca}' found in California Caltrans package!")
        if "Cal. Gov't Code § 7920.000" not in vol5_ca or "CA-DGS-TDDC-2025-11" not in vol2_ca:
            fail("proposal_compiler.py: California Caltrans package missing CPRA citation (`Cal. Gov't Code § 7920.000`) or CA DGS benchmark (`CA-DGS-TDDC-2025-11`)!")
        if "(PMP:" in vol2_ca or "CISSP):" in vol2_ca:
            fail("proposal_compiler.py: Volume II LCAT parser split parenthetical `(PMP/CISSP)` across two rows!")
        for bad_corp_tok in ("Pool", "Schedule", "Statewide"):
            if bad_corp_tok in vol4_ca:
                fail(f"proposal_compiler.py: Non-corporate token '{bad_corp_tok}' found in Volume IV FAR 9.6 Teaming Agreement!")
        for bad_case_tok in ("22Nd", "Llc"):
            if bad_case_tok in vol3_ca or bad_case_tok in vol4_ca:
                fail(f"proposal_compiler.py: Mangled corporate suffix token '{bad_case_tok}' found in Volume III/IV!")

        # Scenario B: Texas DIR SLED solicitation
        req_tx = pc.ProposalCompileRequest(
            solicitation_id="TX-DIR-CPO-5194",
            solicitation_title="[TX-DIR-CPO-5194] Texas DIR Zero-Trust Cloud Security Operations",
            agency="Texas Department of Information Resources (DIR)",
            naics="541512",
            company_name="Apex Cyber Defense LLC",
            download_zip=False,
            suppress_vault_persist=True,
        )
        res_tx = await pc.compile_full_proposal_package(req_tx)
        zf_tx = zipfile.ZipFile(io.BytesIO(pc.base64.b64decode(res_tx["zip_base64"])))
        vol5_tx = _extract_openxml_text(zf_tx.read("Volume_V_Statutory_FOIA_and_State_PIA_Incumbent_Contract_Demand.docx"))
        if "Tex. Gov't Code Ch. 552" not in vol5_tx or "5 U.S.C. § 552" in vol5_tx:
            fail("proposal_compiler.py: Texas DIR package failed to cite Texas PIA (`Tex. Gov't Code Ch. 552`)!")

        # Scenario C: Federal DISA solicitation
        req_fed = pc.ProposalCompileRequest(
            solicitation_id="FA8726-26-R-0042",
            solicitation_title="DISA Enterprise Cloud DevSecOps & Zero-Trust Engineering",
            agency="Department of Defense — Defense Information Systems Agency (DISA)",
            naics="541512",
            company_name="Apex Cyber Defense LLC",
            download_zip=False,
            suppress_vault_persist=True,
        )
        res_fed = await pc.compile_full_proposal_package(req_fed)
        zf_fed = zipfile.ZipFile(io.BytesIO(pc.base64.b64decode(res_fed["zip_base64"])))
        vol5_fed = _extract_openxml_text(zf_fed.read("Volume_V_Statutory_FOIA_and_State_PIA_Incumbent_Contract_Demand.docx"))
        if "5 U.S.C. § 552" not in vol5_fed:
            fail("proposal_compiler.py: Federal DISA package failed to cite Federal FOIA (`5 U.S.C. § 552`)!")

        # Verify Vault, Wrap Index, and Bilateral Teaming Handshake endpoints & response schema keys
        inst_vault = await pc.get_institutional_bid_vault(company_name="Fuse Integration")
        if not (inst_vault.get("verified_company_profile") or {}).get("uei") == "DZZ3WVXGEHW8":
            fail("proposal_compiler.py: `get_institutional_bid_vault` failed to return verified UEI for Fuse Integration!")
        wrap_res = await pc.get_market_wrap_index(naics="541512", agency="Department of Defense (DISA)", offeror_wrap=1.82)
        for req_wk in ("sample_size", "sample_size_submissions", "p25_competitive_wrap", "p50_median_wrap", "p75_ceiling_wrap"):
            if req_wk not in wrap_res:
                fail(f"proposal_compiler.py: `get_market_wrap_index` missing required frontend/API key '{req_wk}'")
        hs_res = await pc.confirm_teaming_handshake(
            pc.TeamingHandshakeRequest(
                prime_company="Fuse Integration",
                sub_company="Decisive Instincts, LLC",
                sub_email="capture@decisiveinstincts.com",
                solicitation_id="0000034018",
                solicitation_title="Caltrans Enterprise Cloud Modernization",
                issuing_agency="California Department of Transportation (Caltrans)",
                suppress_alert=True,
            )
        )
        for req_hk in ("target_partner_name", "target_partner_uei", "solicitation_title", "nda_ta_reference_id"):
            if not hs_res.get(req_hk):
                fail(f"proposal_compiler.py: `confirm_teaming_handshake` missing required frontend/API key '{req_hk}'")

    asyncio.run(_run_compiler_suite())



def check_mobile_viewport_overflow() -> None:
    """
    Renders index.html (all SPA routes + RFP dossier + API Sandbox modal), apis.html,
    and /contracts/**/*.html in headless Chromium at 375x812 (iPhone viewport) and fails
    if any visible button, badge, pill, endpoint code, heading, or card extends past the
    mobile screen edge or clips button/badge text.
    """
    if os.getenv("RENDER"):
        return
    from pathlib import Path
    from playwright.sync_api import sync_playwright

    js_scan = """
    () => {
      const vw = window.innerWidth;
      const issues = [];
      const all = document.querySelectorAll('a, button, span, code, h1, h2, h3, h4, p, div, section, article, table, input, select');
      for (const el of all) {
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity) === 0) continue;
        if (style.pointerEvents === 'none' && el.tagName.toLowerCase() === 'div' && (el.className || '').includes('blur-')) continue;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) continue;

        const scrollParent = el.closest('.overflow-x-auto');
        if (scrollParent && scrollParent !== el) {
          const spRect = scrollParent.getBoundingClientRect();
          if (spRect.right <= vw + 1.5 && spRect.left >= -1.5) continue;
        }

        if (rect.right > vw + 1.5 || rect.left < -1.5) {
          const tag = el.tagName.toLowerCase();
          const cls = (el.className && typeof el.className === 'string') ? el.className : '';
          const txt = (el.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 70);
          issues.push(`${tag} [PAST_SCREEN left=${Math.round(rect.left)} right=${Math.round(rect.right)} vw=${vw}] "${txt}" (${cls.slice(0, 80)})`);
        } else if (['a', 'button', 'span', 'code', 'h1', 'h2', 'h3'].includes(el.tagName.toLowerCase())) {
          const cls = (el.className && typeof el.className === 'string') ? el.className : '';
          const txt = (el.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 70);
          if (txt && !cls.split(/\\s+/).includes('truncate') && el.scrollWidth > el.clientWidth + 3 && style.overflowX !== 'auto' && style.overflowX !== 'scroll') {
            const tag = el.tagName.toLowerCase();
            issues.push(`${tag} [CLIPPED_BOX scrollW=${el.scrollWidth} clientW=${el.clientWidth}] "${txt}" (${cls.slice(0, 80)})`);
          }
          const card = el.closest('.rounded-2xl, .rounded-xl, article, section');
          if (card && card !== el && !el.closest('.overflow-x-auto')) {
            const cRect = card.getBoundingClientRect();
            if (rect.right > cRect.right + 2 || rect.left < cRect.left - 2) {
              const tag = el.tagName.toLowerCase();
              const cls = (el.className && typeof el.className === 'string') ? el.className : '';
              const txt = (el.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 70);
              issues.push(`${tag} [OVERFLOWS_CARD elRight=${Math.round(rect.right)} cardRight=${Math.round(cRect.right)} vw=${vw}] "${txt}" (${cls.slice(0, 80)})`);
            }
          }
        }
      }
      return issues;
    }
    """

    import concurrent.futures

    base_p = Path(BASE_DIR)

    def _run_in_worker_thread() -> tuple[str, list[str]] | None:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True)
            page = context.new_page()
            page.set_default_navigation_timeout(60000)
            page.set_default_timeout(60000)

            index_uri = (base_p / "index.html").as_uri()
            page.goto(f"{index_uri}#contracts", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(150)
            first_slug = page.evaluate("window.SIGNALTENDER_CONTRACTS && window.SIGNALTENDER_CONTRACTS[0] ? window.SIGNALTENDER_CONTRACTS[0].slug : ''")

            routes = [
                "#overview",
                "#apis",
                "#contracts",
                "#contracts/federal",
                f"#contracts/rfp/{first_slug}",
                "#checkout",
                "#account",
                "#status",
                "#privacy",
            ]
            for route in routes:
                page.evaluate("(h) => { window.location.hash = h; }", route)
                page.wait_for_timeout(80)
                issues = page.evaluate(js_scan)
                if issues:
                    browser.close()
                    return (f"index.html{route}", issues[:3])

            for desk_w in (1024, 1280):
                page.set_viewport_size({"width": desk_w, "height": 900})
                for route in ["#overview", "#apis", "#contracts", f"#contracts/rfp/{first_slug}", "#checkout", "#account"]:
                    page.evaluate("(h) => { window.location.hash = h; }", route)
                    page.wait_for_timeout(60)
                    issues = page.evaluate(js_scan)
                    if issues:
                        browser.close()
                        return (f"index.html{route}@{desk_w}px", issues[:3])

            page.set_viewport_size({"width": 375, "height": 812})
            page.goto((base_p / "apis.html").as_uri(), wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(120)
            issues = page.evaluate(js_scan)
            if issues:
                browser.close()
                return ("apis.html", issues[:3])

            for desk_w in (1024, 1280):
                page.set_viewport_size({"width": desk_w, "height": 900})
                page.wait_for_timeout(60)
                issues = page.evaluate(js_scan)
                if issues:
                    browser.close()
                    return (f"apis.html@{desk_w}px", issues[:3])

            page.set_viewport_size({"width": 375, "height": 812})
            c_index = base_p / "contracts" / "index.html"
            if c_index.exists():
                page.goto(c_index.as_uri(), wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(100)
                issues = page.evaluate(js_scan)
                if issues:
                    browser.close()
                    return ("contracts/index.html", issues[:3])

            rfp_samples = glob.glob(str(base_p / "contracts" / "rfp" / "*.html"))
            if rfp_samples:
                page.goto(Path(rfp_samples[0]).as_uri(), wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(100)
                issues = page.evaluate(js_scan)
                if issues:
                    browser.close()
                    return ("contracts/rfp sample", issues[:3])

            browser.close()
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        res = pool.submit(_run_in_worker_thread).result()
    if res:
        fail(f"Mobile 375px viewport overflow on {res[0]}: {res[1]}")


def main() -> int:
    index_path = os.path.join(BASE_DIR, "index.html")
    apis_path = os.path.join(BASE_DIR, "apis.html")
    contracts_hub = os.path.join(BASE_DIR, "contracts", "index.html")
    federal_hub = os.path.join(BASE_DIR, "contracts", "federal", "index.html")

    index_txt = check_html_file(index_path)
    apis_txt = check_html_file(apis_path)
    if os.path.exists(contracts_hub):
        check_html_file(contracts_hub)
    if os.path.exists(federal_hub):
        check_html_file(federal_hub)
    rfp_samples = glob.glob(os.path.join(BASE_DIR, "contracts", "rfp", "*.html"))
    if rfp_samples:
        check_html_file(rfp_samples[0])

    check_catalog_parity_and_ui(index_txt, apis_txt)
    check_portal_parity_and_telemetry(index_txt, apis_txt)
    check_tier_value_prop_and_capture_moat_parity(index_txt)
    # Enforce that AI Concierge knowledge bases in index.html and support.py cover all 4 tiers
    for req_concierge_tier in ("Tier 1", "Tier 2", "Tier 3", "Tier 4", "$1,499", "$2,499"):
        if req_concierge_tier not in index_txt:
            fail(f"index.html: AI Concierge knowledge base missing required tier fact '{req_concierge_tier}'")
    support_py_path = r"d:\Data API Ecosystem\api\routers\support.py"
    if os.path.exists(support_py_path):
        with open(support_py_path, "r", encoding="utf-8") as sf:
            stxt = sf.read()
        for req_tier in ("Tier 1", "Tier 2", "Tier 3", "Tier 4", "$1,499", "$2,499", "1-Click 3-Volume Shipley Proposal", "Winning-Bid Rate Vault"):
            if req_tier not in stxt:
                fail(f"api/routers/support.py: AI Concierge knowledge base missing required tier fact '{req_tier}'")
    check_conversion_and_distribution_surfaces(index_txt)
    check_anti_regression_guardrails(index_txt, apis_txt)
    check_acquisition_and_email_guardrails()
    check_product_output_quality_controls()
    check_spa_runtime(index_txt)
    if not os.getenv("RENDER") and not os.getenv("CI"):
        import asyncio
        import concurrent.futures
        try:
            has_loop = asyncio._get_running_loop() is not None
        except Exception:
            has_loop = False
        if has_loop:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _pool:
                _pool.submit(check_mobile_viewport_overflow).result()
        else:
            check_mobile_viewport_overflow()

    import auto_error_healer
    if not os.getenv("RENDER") and auto_error_healer.run_healer(clear_resolved=True, run_smoke=False) != 0:
        fail("Autonomous Error Telemetry / Scraper Contract Audit reported unresolved errors! Run `python auto_error_healer.py` to inspect and fix.")

    print("[+] verify_site_integrity.py PASSED: All JS syntax, SPA routes, search locks, API/portal counts, telemetry bar, DOM IDs, and HTML tags verified.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

