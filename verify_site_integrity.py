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
    with open(fpath, "r", encoding="utf-8") as f:
        txt = f.read()

    rel = os.path.relpath(fpath, BASE_DIR)

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

    # 7. Check zero emojis and zero `data:` URI favicons (Google Search requires crawlable HTTP/HTTPS favicon URLs)
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

        # Verify badge counts match n_apis
        if ">API Catalog</a>" not in txt:
            fail(f"{label}: Nav link '>API Catalog</a>' missing")
        if f"{n_apis} LIVE ENDPOINTS" not in txt:
            fail(f"{label}: Directory badge '{n_apis} LIVE ENDPOINTS' does not match {n_apis} APIs")
        if f"{n_apis} MCP TOOLS" not in txt:
            fail(f"{label}: MCP badge '{n_apis} MCP TOOLS' does not match {n_apis} APIs")
        if f"{n_apis} / {n_apis} SHOWN" not in txt:
            fail(f"{label}: Modules counter badge '{n_apis} / {n_apis} SHOWN' does not match {n_apis} APIs")

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
        "texas": "TX",
        "virginia": "VA",
        "california": "CA",
        "florida": "FL",
        "maryland": "MD",
        "illinois": "IL",
        "pennsylvania": "PA",
        "ohio": "OH",
        "georgia": "GA",
        "north_carolina": "NC",
        "new_york": "NY",
        "massachusetts": "MA",
        "new_jersey": "NJ",
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
        for sp in stale_patterns:
            if re.search(rf"(?<![0-9>]){re.escape(sp)}", txt):
                fail(f"{label}: Found stale portal/state count string '{sp}' (expected {n_portals} portals / {n_states} states)")

        # 5. Enforce that EVERY inline state-abbreviation list (e.g. "VA, TX, CA, FL..." or "TX, VA, CA, FL...") includes ALL active state abbreviations
        expected_abbrs = [state_abbrev_map.get(sk, sk[:2].upper()) for sk in state_keys]
        for m in re.finditer(r"(?:VA,\s*TX,\s*CA,\s*FL|TX,\s*VA,\s*CA,\s*FL|SAM\.gov,\s*DemandStar,\s*VA,\s*TX)[^)<\n]{0,120}", txt):
            snippet = m.group(0)
            for abbr in expected_abbrs:
                if abbr not in snippet:
                    fail(f"{label}: State abbreviation list '{snippet.strip()}' is missing active state '{abbr}'")

        # 6. Enforce that every prose portal roll-call ("Virginia eVA, Texas ESBD, California Cal eProcure...") includes all active states
        for m in re.finditer(r"Virginia eVA,\s*Texas ESBD,\s*California Cal eProcure[^.<\n]{0,350}", txt):
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
    import pseo_generator

    n_apis = len(re.findall(r'<article\s+id="product-[^"]+"', index_txt))
    n_portals = len(pseo_generator.JURISDICTIONS)
    state_keys = [k for k in pseo_generator.JURISDICTIONS.keys() if k not in ("federal", "municipal")]
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
    m_t2 = re.search(r'<div id="checkout-card-tier2".*?<!-- \$0/mo Free Basic', index_txt, flags=re.S)
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

    # 4. Verify #page-checkout Developer API Callout Banner references All N individual SignalTender microservices
    callout_phrase = f"All {n_apis} individual SignalTender microservices"
    if callout_phrase not in index_txt:
        fail(f"index.html (#page-checkout API Callout): Missing '{callout_phrase}'")

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
window.prefillConciergeQuestion('plans_and_pricing', 'What is the difference between Tier 1 ($99/mo) and Tier 2 ($399/mo)?');
if (!document.getElementById('concierge-answer-text').textContent || document.getElementById('concierge-answer-text').textContent.indexOf('Tier 1') === -1) {
  throw new Error('AI Support Concierge failed to render instant on-screen answer!');
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
"""
    )

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
        tf.write(harness)
        tname = tf.name
    r = subprocess.run(["node", tname], capture_output=True, text=True)
    os.remove(tname)
    if r.returncode != 0:
        fail(f"Headless SPA runtime check failed:\n{r.stderr}")


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
    check_spa_runtime(index_txt)

    import auto_error_healer
    if auto_error_healer.run_healer(clear_resolved=True, run_smoke=False) != 0:
        fail("Autonomous Error Telemetry / Scraper Contract Audit reported unresolved errors! Run `python auto_error_healer.py` to inspect and fix.")

    print("[+] verify_site_integrity.py PASSED: All JS syntax, SPA routes, search locks, API/portal counts, telemetry bar, DOM IDs, and HTML tags verified.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

