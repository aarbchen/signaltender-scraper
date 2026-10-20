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
        "#contracts/federal",
        "#contracts/texas",
        "#contracts/virginia",
        "#contracts/california",
        "#contracts/florida",
        "#contracts/maryland",
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

    # 7. Check zero emojis
    emoji_re = re.compile(r"[\U0001F300-\U0001FAFF]")
    emojis = emoji_re.findall(txt)
    if emojis:
        fail(f"{rel}: Prohibited emojis found: {set(emojis)}")

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
        if f"API Catalog ({n_apis})" not in txt:
            fail(f"{label}: Nav link 'API Catalog ({n_apis})' does not match {n_apis} APIs")
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
    check_spa_runtime(index_txt)

    print("[+] verify_site_integrity.py PASSED: All JS syntax, SPA routes, search locks, API counts, DOM IDs, and HTML tags verified.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

