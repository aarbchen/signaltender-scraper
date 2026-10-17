import os
import re
import json
import html
from datetime import datetime, date
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
TABLE_NAME = "contracts"
ERROR_LOG_PATH = r"D:\Daas\error_log.txt"

SITE_BASE_URL = os.getenv("SIGNALTENDER_SITE_URL", "https://signaltender.net").rstrip("/")
WHOP_TIER1_URL = os.getenv(
    "WHOP_CHECKOUT_URL",
    "https://whop.com/signaltender-net/signaltender-private-alerts",
)
WHOP_TIER2_URL = os.getenv(
    "WHOP_TIER2_CHECKOUT_URL",
    "https://whop.com/signaltender-net/signaltender-private-alerts",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "contracts")
SITEMAP_PATH = os.path.join(BASE_DIR, "sitemap.xml")
ROBOTS_PATH = os.path.join(BASE_DIR, "robots.txt")

JURISDICTIONS = {
    "federal": {
        "name": "Federal (SAM.gov)",
        "short": "Federal",
        "portal": "SAM.gov Federal Contracting",
        "badge_class": "bg-sky-500/10 text-sky-400 border-sky-500/30",
        "headline": "Open Federal IT, Cloud & Cybersecurity Contracts (SAM.gov)",
        "description": "Live pre-vetted federal government IT, software, cloud migration, and cybersecurity solicitations extracted from SAM.gov.",
    },
    "texas": {
        "name": "Texas (ESBD / DIR)",
        "short": "Texas",
        "portal": "Texas SmartBuy ESBD",
        "badge_class": "bg-indigo-500/10 text-indigo-300 border-indigo-500/30",
        "headline": "Open Texas State & Local IT Contracts (ESBD / SmartBuy)",
        "description": "Live Texas SLED IT, software development, telecom, and cybersecurity RFPs from the Electronic State Business Daily (ESBD).",
    },
    "virginia": {
        "name": "Virginia (eVA)",
        "short": "Virginia",
        "portal": "Virginia eVA Portal",
        "badge_class": "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
        "headline": "Open Virginia State & Municipal IT Solicitations (eVA)",
        "description": "Live Virginia eVA procurement opportunities for enterprise software, cloud infrastructure, cybersecurity, and IT consulting.",
    },
    "california": {
        "name": "California (Cal eProcure)",
        "short": "California",
        "portal": "California Cal eProcure (CSCR)",
        "badge_class": "bg-amber-500/10 text-amber-300 border-amber-500/30",
        "headline": "Open California State IT & Cybersecurity RFPs (Cal eProcure)",
        "description": "Live California State Contracts Register (Cal eProcure) solicitations for enterprise IT, cloud, and cybersecurity vendors.",
    },
    "florida": {
        "name": "Florida (MFMP VIP)",
        "short": "Florida",
        "portal": "Florida MyFloridaMarketPlace VIP",
        "badge_class": "bg-cyan-500/10 text-cyan-300 border-cyan-500/30",
        "headline": "Open Florida State IT, Software & Cloud Bids (MFMP VIP)",
        "description": "Live Florida Vendor Information Portal (MFMP VIP) IT invitations to negotiate (ITNs), RFPs, and agency technology bids.",
    },
    "maryland": {
        "name": "Maryland (eMMA & Bonfire)",
        "short": "Maryland",
        "portal": "Maryland eMMA & Agency Bonfire Portals",
        "badge_class": "bg-rose-500/10 text-rose-300 border-rose-500/30",
        "headline": "Open Maryland State, Judiciary & County IT Solicitations",
        "description": "Live Maryland state, judiciary, and county technology, telecom, and systems integration contracts.",
    },
    "municipal": {
        "name": "National Municipal (DemandStar)",
        "short": "Municipal SLED",
        "portal": "DemandStar Municipal Network",
        "badge_class": "bg-purple-500/10 text-purple-300 border-purple-500/30",
        "headline": "Open City, County & School District IT RFPs (DemandStar)",
        "description": "Live municipal, county, and public university IT and software solicitations monitored across the DemandStar SLED network.",
    },
}

CATEGORIES = {
    "cybersecurity": {
        "name": "Cybersecurity & InfoSec",
        "patterns": [r"cyber", r"infosec", r"zero[\s\-]*trust", r"siem", r"soc\b", r"security", r"iam\b", r"pam\b", r"firewall", r"audit"],
        "tags": ["Cybersecurity", "Zero-Trust / SOC", "Compliance"],
    },
    "cloud-infrastructure": {
        "name": "Cloud, Data Center & Servers",
        "patterns": [r"cloud", r"saas", r"server", r"storage", r"data\s*center", r"aws", r"azure", r"hosting", r"backup"],
        "tags": ["Cloud Architecture", "Enterprise SaaS", "Data Center"],
    },
    "software-development": {
        "name": "Enterprise Software, Data & AI Platforms",
        "patterns": [r"software", r"platform", r"system", r"data", r"analytics", r"intelligence", r"portal", r"web", r"digital", r"erp", r"lms", r"application"],
        "tags": ["Enterprise Software", "Systems Integration", "Data Platform"],
    },
    "network-telecom": {
        "name": "Network, Fiber, Telecom & Hardware",
        "patterns": [r"network", r"fiber", r"broadband", r"telecom", r"audio/visual", r"hardware", r"computer", r"wireless", r"intercom", r"aiphone", r"alert"],
        "tags": ["Network Infrastructure", "Telecom / Fiber", "Enterprise Hardware"],
    },
}

COMMODITY_IT_EXCLUSIONS = [
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
    r"^50001",
    r"cor-(ent|off|pro|stp)",
    r"smart(-dt|-rti|-so|essential|mcms)",
    r"wts-mobile",
    r"software\s*support",
    r"software\s*subscription",
    r"software\s*synergy",
    r"25ecert",
    r"oms-500",
    r"virtual\s+printer\s+driver",
]


def is_commodity_it_spam(title: str) -> bool:
    if not title:
        return True
    t_lower = str(title).strip().lower()
    return any(re.search(pat, t_lower) for pat in COMMODITY_IT_EXCLUSIONS)



def send_discord_alert(message: str):
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": f"🚨 **pSEO Generator Alert:**\n{message}"},
            timeout=10,
        )
    except Exception as e:
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"Failed to send Discord alert in pseo_generator.py: {e}\n")
        except Exception:
            pass


def parse_due_date(rec: dict) -> date | None:
    candidates = [str(rec.get("closing_date") or "").strip()]
    m_title = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", str(rec.get("title") or ""), flags=re.IGNORECASE)
    if m_title:
        candidates.append(m_title.group(1))
    for cand in candidates:
        if not cand or cand.lower() in ["n/a", "tbd", "none", "null", ""]:
            continue
        if "T" in cand:
            cand = cand.split("T")[0].strip()
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
            try:
                return datetime.strptime(cand, fmt).date()
            except ValueError:
                pass
    return None


def clean_display_title(raw_title: str) -> str:
    """Strip trailing '- Due: MM/DD/YYYY' from title for cleaner heading display."""
    base = re.sub(r"\s*-\s*Due:\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$", "", str(raw_title or ""), flags=re.IGNORECASE)
    return base.strip()


def slugify(text: str, fallback_id: str = "rfp") -> str:
    s = clean_display_title(text).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if not s:
        return fallback_id
    return f"{s[:75].rstrip('-')}-{fallback_id}"


def classify_jurisdiction(rec: dict) -> str:
    url = str(rec.get("url") or "").lower()
    agency = str(rec.get("agency") or "").lower()
    if "sam.gov" in url or "federal government" in agency:
        return "federal"
    if "txsmartbuy.com" in url or "texas" in agency or "ut md anderson" in agency:
        return "texas"
    if "cgieva.com" in url or "virginia" in agency:
        return "virginia"
    if "caleprocure.ca.gov" in url or "california" in agency:
        return "california"
    if "myfloridamarketplace.com" in url or "florida" in agency:
        return "florida"
    if "maryland" in url or "bonfirehub.com" in url or "maryland" in agency or "prince george" in agency or "howard county" in agency:
        return "maryland"
    return "municipal"


def classify_categories(rec: dict) -> list[str]:
    title_lower = str(rec.get("title") or "").lower()
    matched = []
    for cat_key, cat_meta in CATEGORIES.items():
        if any(re.search(pat, title_lower) for pat in cat_meta["patterns"]):
            matched.append(cat_key)
    if not matched:
        matched.append("software-development")
    return matched


def mask_agency_preview(agency: str) -> str:
    """Provide enough agency context for SEO indexing while keeping exact buyer contact gated."""
    a = str(agency or "Government Agency").strip()
    if len(a) <= 18:
        return a
    words = a.split()
    if len(words) >= 3:
        return " ".join(words[:2]) + " [Verified Agency]"
    return a


def _render_layout(
    page_title: str,
    meta_desc: str,
    canonical_path: str,
    body_html: str,
    json_ld: dict | None = None,
    root_prefix: str = "../",
) -> str:
    escaped_title = html.escape(page_title)
    escaped_desc = html.escape(meta_desc)
    canonical_url = f"{SITE_BASE_URL}/{canonical_path.lstrip('/')}"
    ld_script = (
        f'<script type="application/ld+json">{json.dumps(json_ld)}</script>'
        if json_ld
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escaped_title}</title>
  <meta name="description" content="{escaped_desc}" />
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22cyan%22%3E%3Cpath%20d%3D%22M8%202h2v3h4V2h2v3h1a2%202%200%200%201%202%202v1h3v2h-3v4h3v2h-3v1a2%202%200%200%201-2%202h-1v3h-2v-3h-4v3H8v-3H7a2%202%200%200%201-2-2v-1H2v-2h3v-4H2V8h3V7a2%202%200%200%201%202-2h1V2zm-1%205v10h10V7H7zm2%202h6v6H9V9z%22%2F%3E%3C%2Fsvg%3E" />
  <link rel="icon" type="image/png" sizes="32x32" href="https://raw.githubusercontent.com/aarbchen/signaltender-scraper/main/favicon-32x32.png" />
  <link rel="icon" type="image/png" sizes="192x192" href="https://raw.githubusercontent.com/aarbchen/signaltender-scraper/main/favicon-192x192.png" />
  <link rel="apple-touch-icon" sizes="180x180" href="https://raw.githubusercontent.com/aarbchen/signaltender-scraper/main/apple-touch-icon.png" />
  <link rel="shortcut icon" href="https://raw.githubusercontent.com/aarbchen/signaltender-scraper/main/favicon.ico" />
  <link rel="canonical" href="{canonical_url}" />
  <meta property="og:site_name" content="SignalTender" />
  <meta property="og:title" content="{escaped_title}" />
  <meta property="og:description" content="{escaped_desc}" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="{canonical_url}" />
  <meta property="og:image" content="https://raw.githubusercontent.com/aarbchen/signaltender-scraper/main/og-banner.png" />
  <meta property="og:image:type" content="image/png" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{escaped_title}" />
  <meta name="twitter:description" content="{escaped_desc}" />
  <meta name="twitter:image" content="https://raw.githubusercontent.com/aarbchen/signaltender-scraper/main/og-banner.png" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      darkMode: 'class',
      theme: {{
        extend: {{
          fontFamily: {{
            sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
            mono: ['JetBrains Mono', 'monospace'],
          }},
          colors: {{
            navy: {{
              950: '#050811',
              900: '#090E1A',
              800: '#0F172A',
              700: '#1E293B',
            }}
          }}
        }}
      }}
    }}
  </script>
  <style>
    span[class*="border"],
    span[class*="rounded"]:not(.animate-ping) {{
      display: inline-flex;
      align-items: center;
      white-space: nowrap;
      line-height: 1.2;
    }}
  </style>
  {ld_script}
</head>
<body class="bg-navy-950 text-slate-100 font-sans antialiased selection:bg-sky-500/30 selection:text-sky-200 min-h-screen flex flex-col justify-between">
  <div>
    <div class="border-b border-slate-800/80 bg-navy-900/90 text-xs">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-9 flex items-center justify-between">
        <div class="flex items-center space-x-2.5">
          <span class="inline-block h-2 w-2 rounded-full bg-emerald-500"></span>
          <span class="font-mono text-slate-300">LIVE GOVCON INTELLIGENCE WIRE &bull; <span class="text-emerald-400">7 PORTALS ACTIVE</span></span>
        </div>
        <div class="flex items-center space-x-4 font-mono text-slate-400">
          <a href="{root_prefix}index.html" class="hover:text-sky-400 transition-colors">&larr; Main Platform</a>
          <span>|</span>
          <a href="{root_prefix}apis.html" class="hover:text-sky-400 transition-colors">Developer APIs</a>
        </div>
      </div>
    </div>

    <header class="sticky top-0 z-50 backdrop-blur-md bg-navy-950/85 border-b border-slate-800/80">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <a href="{root_prefix}index.html" class="flex items-center space-x-3 shrink-0">
          <div class="h-9 w-9 rounded-lg bg-gradient-to-br from-sky-500/20 to-blue-600/10 border border-sky-500/40 flex items-center justify-center shadow-inner shrink-0">
            <svg class="w-4 h-4 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
            </svg>
          </div>
          <span class="text-lg font-bold tracking-tight text-white whitespace-nowrap">SignalTender</span>
          <span class="inline-flex items-center whitespace-nowrap text-[10px] font-mono uppercase tracking-widest px-2 py-0.5 rounded bg-sky-500/15 text-sky-400 border border-sky-500/30">LIVE RFP INDEX</span>
        </a>
        <nav class="hidden md:flex items-center space-x-6 text-xs font-mono text-slate-300 whitespace-nowrap">
          <a href="{root_prefix}contracts/index.html" class="hover:text-sky-400 transition-colors">All Portals</a>
          <a href="{root_prefix}contracts/federal/index.html" class="hover:text-sky-400 transition-colors">Federal</a>
          <a href="{root_prefix}contracts/texas/index.html" class="hover:text-sky-400 transition-colors">Texas</a>
          <a href="{root_prefix}contracts/virginia/index.html" class="hover:text-sky-400 transition-colors">Virginia</a>
          <a href="{root_prefix}contracts/california/index.html" class="hover:text-sky-400 transition-colors">California</a>
          <a href="{root_prefix}contracts/florida/index.html" class="hover:text-sky-400 transition-colors">Florida</a>
          <a href="{root_prefix}contracts/maryland/index.html" class="hover:text-sky-400 transition-colors">Maryland</a>
        </nav>
        <a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center whitespace-nowrap px-4 py-2 text-xs font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg border border-sky-400/30 transition-all">
          Unlock All RFP Links &rarr;
        </a>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {body_html}
    </main>
  </div>

  <footer class="border-t border-slate-800/80 bg-navy-900/50 py-8 mt-16 text-xs font-mono text-slate-400">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
      <div>&copy; {datetime.now().year} SignalTender. Real-Time Federal &amp; SLED Procurement Intelligence.</div>
      <div class="flex items-center space-x-4">
        <a href="{root_prefix}index.html" class="hover:text-white">Home</a>
        <a href="{root_prefix}contracts/index.html" class="hover:text-white">RFP Directory</a>
        <a href="{root_prefix}apis.html" class="hover:text-white">RapidAPI Catalog</a>
        <a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="text-sky-400 hover:underline">Subscribe</a>
      </div>
    </div>
  </footer>
</body>
</html>
"""


def _render_contract_table_rows(contracts: list[dict], rfp_link_prefix: str) -> str:
    if not contracts:
        return """
        <tr>
          <td colspan="5" class="py-8 px-5 text-center font-mono text-slate-400">
            New solicitations for this segment are currently being indexed by the 6-hour scraper cycle.
          </td>
        </tr>
        """
    rows_html = []
    for c in contracts:
        j_meta = JURISDICTIONS[c["jurisdiction"]]
        cat_key = c["categories"][0]
        cat_tags = CATEGORIES[cat_key]["tags"]
        tag_spans = "".join(
            f'<span class="px-2 py-0.5 rounded bg-navy-900 border border-slate-800 text-slate-300">{html.escape(t)}</span>'
            for t in cat_tags[:2]
        )
        due_display = html.escape(c["due_str"] or "Open / Rolling")
        rows_html.append(f"""
        <tr class="hover:bg-navy-900/60 transition-colors border-b border-slate-800/70">
          <td class="py-4 px-5 font-mono whitespace-nowrap">
            <span class="px-2.5 py-1 rounded border text-[11px] font-semibold {j_meta['badge_class']}">
              {html.escape(j_meta['short'].upper())}
            </span>
          </td>
          <td class="py-4 px-5">
            <a href="{rfp_link_prefix}{c['slug']}.html" class="font-bold text-white hover:text-sky-400 text-sm transition-colors block">
              {html.escape(c['clean_title'])}
            </a>
            <div class="flex flex-wrap gap-1.5 mt-1.5 font-mono text-[10px]">
              {tag_spans}
            </div>
          </td>
          <td class="py-4 px-4 text-slate-300 font-mono text-xs">
            {html.escape(c['masked_agency'])}
          </td>
          <td class="py-4 px-4 font-mono text-amber-300 whitespace-nowrap text-xs">
            {due_display}
          </td>
          <td class="py-4 px-5 text-right font-mono whitespace-nowrap">
            <a href="{rfp_link_prefix}{c['slug']}.html" class="inline-flex items-center px-3 py-1.5 rounded bg-slate-900 hover:bg-sky-600 hover:text-white border border-slate-700 text-sky-400 text-xs transition-colors">
              View Dossier &rarr;
            </a>
          </td>
        </tr>
        """)
    return "\n".join(rows_html)


def generate_pseo_site() -> int:
    if not SUPABASE_URL or not SUPABASE_KEY:
        err = "SUPABASE_URL or SUPABASE_KEY missing in .env; cannot build pSEO pages."
        print(f"[!] {err}", flush=True)
        send_discord_alert(err)
        return 0

    try:
        print("[*] Connecting to Supabase to fetch live contracts for pSEO static generation...", flush=True)
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        resp = (
            supabase.table(TABLE_NAME)
            .select("*")
            .eq("status", "New Lead")
            .order("id", desc=True)
            .limit(500)
            .execute()
        )
        raw_records = resp.data if resp and getattr(resp, "data", None) else []

        today = datetime.now().date()
        enriched_contracts = []
        seen_slugs = set()
        spam_ids_to_purge = []

        for idx, rec in enumerate(raw_records, 1):
            raw_title = str(rec.get("title") or "").strip()
            if not raw_title:
                continue
            if is_commodity_it_spam(raw_title):
                if rec.get("id"):
                    spam_ids_to_purge.append(rec["id"])
                continue
            due_dt = parse_due_date(rec)
            if due_dt is not None and due_dt < today:
                continue

            rec_id = str(rec.get("id") or idx)
            slug = slugify(raw_title, fallback_id=rec_id)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            j_key = classify_jurisdiction(rec)
            cats = classify_categories(rec)
            due_str = due_dt.strftime("%Y-%m-%d") if due_dt else ""

            enriched_contracts.append({
                "id": rec_id,
                "slug": slug,
                "raw_title": raw_title,
                "clean_title": clean_display_title(raw_title),
                "agency": str(rec.get("agency") or "Government Agency").strip(),
                "masked_agency": mask_agency_preview(str(rec.get("agency") or "Government Agency")),
                "due_str": due_str,
                "url": str(rec.get("url") or ""),
                "jurisdiction": j_key,
                "categories": cats,
            })

        if spam_ids_to_purge:
            try:
                supabase.table(TABLE_NAME).delete().in_("id", spam_ids_to_purge).execute()
                print(f"[+] Purged {len(spam_ids_to_purge)} legacy pre-filter catalog/spam row(s) from Supabase.", flush=True)
            except Exception as del_err:
                print(f"[!] Could not delete legacy spam rows from Supabase: {del_err}", flush=True)

        # Prepare directories and remove any stale/expired RFP HTML files
        rfp_dir = os.path.join(OUTPUT_DIR, "rfp")
        os.makedirs(rfp_dir, exist_ok=True)
        for existing_file in os.listdir(rfp_dir):
            if existing_file.endswith(".html"):
                try:
                    os.remove(os.path.join(rfp_dir, existing_file))
                except Exception:
                    pass
        for j_key in JURISDICTIONS:
            os.makedirs(os.path.join(OUTPUT_DIR, j_key), exist_ok=True)

        sitemap_urls = [
            f"{SITE_BASE_URL}/index.html",
            f"{SITE_BASE_URL}/apis.html",
            f"{SITE_BASE_URL}/contracts/index.html",
        ]
        pages_built = 0

        # 1. Build Individual Solicitation Dossier Pages (/contracts/rfp/<slug>.html)
        for c in enriched_contracts:
            j_meta = JURISDICTIONS[c["jurisdiction"]]
            cat_meta = CATEGORIES[c["categories"][0]]
            page_title = f"{c['clean_title']} | {j_meta['short']} Government IT RFP | SignalTender"
            meta_desc = (
                f"Active {j_meta['name']} solicitation: {c['clean_title']}. "
                f"Issued by {c['masked_agency']}. Closing date: {c['due_str'] or 'Open'}. "
                f"Unlock direct government portal link and AI capture dossier on SignalTender."
            )
            canonical_path = f"contracts/rfp/{c['slug']}.html"
            sitemap_urls.append(f"{SITE_BASE_URL}/{canonical_path}")

            related = [
                other for other in enriched_contracts
                if other["jurisdiction"] == c["jurisdiction"] and other["slug"] != c["slug"]
            ][:5]
            related_links_html = "".join(
                f'<li class="py-2 border-b border-slate-800/70"><a href="{r["slug"]}.html" class="text-sky-400 hover:underline font-medium">{html.escape(r["clean_title"])}</a> <span class="text-slate-500 font-mono text-xs ml-2">({html.escape(r["due_str"] or "Open")})</span></li>'
                for r in related
            ) or '<li class="text-slate-400">View more opportunities in the portal hub above.</li>'

            body_html = f"""
            <div class="mb-6 text-xs font-mono text-slate-400 flex flex-wrap items-center gap-2">
              <a href="../index.html" class="hover:text-sky-400">All Contracts</a>
              <span>/</span>
              <a href="../{c['jurisdiction']}/index.html" class="hover:text-sky-400">{html.escape(j_meta['name'])}</a>
              <span>/</span>
              <span class="text-slate-200">{html.escape(c['slug'][:40])}</span>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
              <div class="lg:col-span-8 space-y-6">
                <div class="p-6 sm:p-8 rounded-2xl bg-navy-900 border border-slate-800 shadow-2xl space-y-5">
                  <div class="flex flex-wrap items-center gap-2.5 font-mono text-xs">
                    <span class="px-2.5 py-1 rounded border font-semibold {j_meta['badge_class']}">{html.escape(j_meta['name'].upper())}</span>
                    <span class="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">STATUS: OPEN LEAD</span>
                    <span class="px-2.5 py-1 rounded bg-slate-800 text-slate-300">{html.escape(cat_meta['name'])}</span>
                  </div>

                  <h1 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-snug">
                    {html.escape(c['clean_title'])}
                  </h1>

                  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 font-mono text-xs">
                    <div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800">
                      <div class="text-slate-400">ISSUING AGENCY</div>
                      <div class="text-white font-semibold mt-1">{html.escape(c['masked_agency'])}</div>
                    </div>
                    <div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800">
                      <div class="text-slate-400">CLOSING DEADLINE</div>
                      <div class="text-amber-300 font-semibold mt-1">{html.escape(c['due_str'] or 'Active / See Portal')}</div>
                    </div>
                    <div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800">
                      <div class="text-slate-400">SOURCE PORTAL</div>
                      <div class="text-sky-400 font-semibold mt-1">{html.escape(j_meta['portal'])}</div>
                    </div>
                  </div>

                  <!-- Gated Portal Link & AI Capture Dossier Box -->
                  <div class="mt-6 p-6 rounded-xl bg-navy-950 border-2 border-sky-500/40 space-y-4">
                    <div class="flex items-center justify-between">
                      <span class="text-xs font-mono uppercase tracking-wider text-sky-400 font-semibold">// SUBSCRIBER-ONLY PROCUREMENT DOSSIER</span>
                      <span class="text-xs font-mono text-emerald-400">INSTANT ACCESS</span>
                    </div>
                    <div class="space-y-2 text-xs font-mono text-slate-400">
                      <div><strong class="text-slate-200">Official Government Bid URL:</strong> <span class="blur-sm select-none">https://portal.government.gov/solicitation/view/{c['id']}98412</span></div>
                      <div><strong class="text-slate-200">Full Issuing Buyer &amp; Contracting Officer:</strong> <span class="blur-sm select-none">{html.escape(c['agency'])} - Procurement Division</span></div>
                      <div><strong class="text-slate-200">AI Compliance Matrix, Redline &amp; CLIN Pricing:</strong> <span class="blur-sm select-none">Included via SignalTender APIs</span></div>
                    </div>
                    <div class="pt-3 flex flex-col sm:flex-row gap-3">
                      <a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center justify-center px-6 py-3 text-sm font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg shadow-lg transition-all">
                        Unlock Direct RFP Link &amp; Discord Wire &rarr;
                      </a>
                      <a href="../../apis.html#product-compliance-matrix" class="inline-flex items-center justify-center px-5 py-3 text-xs font-mono text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 rounded-lg border border-amber-500/30 transition-colors">
                        Generate Compliance Matrix via API &rarr;
                      </a>
                    </div>
                    <p class="text-[11px] font-mono text-slate-400">Instant 60-second access via Whop. Flexible month-to-month—cancel anytime.</p>
                  </div>
                </div>

                <div class="p-6 rounded-2xl bg-navy-900/60 border border-slate-800">
                  <h2 class="text-base font-bold text-white font-mono uppercase tracking-wider mb-3">More Open {html.escape(j_meta['short'])} IT Solicitations</h2>
                  <ul class="text-sm space-y-1">
                    {related_links_html}
                  </ul>
                </div>
              </div>

              <div class="lg:col-span-4 space-y-6">
                <div class="p-6 rounded-2xl bg-navy-900 border border-slate-800 space-y-4">
                  <div class="text-xs font-mono text-sky-400 uppercase font-semibold">SIGNALWIRE PRO</div>
                  <div class="text-2xl font-extrabold text-white">Stop Hunting Portals Manually</div>
                  <p class="text-xs text-slate-300 leading-relaxed">
                    Get every pre-vetted Federal (SAM.gov), DemandStar, and 5-State SLED (TX, VA, CA, FL, MD) IT &amp; cybersecurity solicitation pushed directly to your team every 6 hours.
                  </p>
                  <ul class="text-xs font-mono text-slate-300 space-y-2 pt-2">
                    <li>&check; 99.4% Commodity &amp; Renewal Spam Stripped</li>
                    <li>&check; Direct One-Click Official Portal Links</li>
                    <li>&check; Instant Discord + Automated Feed Access</li>
                  </ul>
                  <a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="w-full inline-flex items-center justify-center px-5 py-3 text-xs font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg transition-all">
                    Start Getting Leads &rarr;
                  </a>
                </div>

                <div class="p-6 rounded-2xl bg-navy-900 border border-indigo-500/30 space-y-3">
                  <div class="text-xs font-mono text-indigo-400 uppercase font-semibold">DEVELOPER &amp; CAPTURE APIs (8 LIVE)</div>
                  <div class="text-lg font-bold text-white">Automate Your Bid Response</div>
                  <p class="text-xs text-slate-300 leading-relaxed">
                    Classify NAICS/SIC/PSC/UNSPSC codes, score Bid/No-Bid Pwin (0&ndash;100), audit FAR/DFARS &amp; CMMC 2.0 flow-downs, shred this RFP into a Shipley compliance matrix, extract SOW deliverables, audit legal clauses, or query historical CLIN pricing via our RapidAPI microservices.
                  </p>
                  <a href="../../apis.html#product-industry-classifier" class="w-full inline-flex items-center justify-center px-4 py-2.5 text-xs font-mono font-semibold text-indigo-300 bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/40 rounded-lg transition-all">
                    Explore 8 RapidAPI Microservices &rarr;
                  </a>
                </div>
              </div>
            </div>
            """

            json_ld = {
                "@context": "https://schema.org",
                "@type": "GovernmentService",
                "name": c["clean_title"],
                "serviceType": cat_meta["name"],
                "provider": {
                    "@type": "GovernmentOrganization",
                    "name": c["masked_agency"],
                },
                "areaServed": j_meta["short"],
                "url": f"{SITE_BASE_URL}/{canonical_path}",
            }

            full_html = _render_layout(
                page_title=page_title,
                meta_desc=meta_desc,
                canonical_path=canonical_path,
                body_html=body_html,
                json_ld=json_ld,
                root_prefix="../../",
            )
            with open(os.path.join(rfp_dir, f"{c['slug']}.html"), "w", encoding="utf-8") as f:
                f.write(full_html)
            pages_built += 1

        # 2. Build Jurisdiction Hub Pages (/contracts/<jurisdiction>/index.html)
        #    and State x Category Pages (/contracts/<jurisdiction>/<category>.html)
        for j_key, j_meta in JURISDICTIONS.items():
            j_contracts = [c for c in enriched_contracts if c["jurisdiction"] == j_key]
            canonical_path = f"contracts/{j_key}/index.html"
            sitemap_urls.append(f"{SITE_BASE_URL}/{canonical_path}")

            cat_pills_html = "".join(
                f'<a href="{cat_k}.html" class="px-3 py-1.5 rounded-lg bg-navy-900 hover:bg-slate-800 border border-slate-700 text-xs font-mono text-sky-400 transition-colors">{html.escape(cat_m["name"])}</a>'
                for cat_k, cat_m in CATEGORIES.items()
            )
            rows_html = _render_contract_table_rows(j_contracts, rfp_link_prefix="../rfp/")

            body_html = f"""
            <div class="mb-8 space-y-4">
              <div class="inline-flex items-center px-3 py-1 rounded border text-xs font-mono {j_meta['badge_class']}">
                // {html.escape(j_meta['portal'].upper())} &bull; {len(j_contracts)} ACTIVE IT SOLICITATIONS
              </div>
              <h1 class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
                {html.escape(j_meta['headline'])}
              </h1>
              <p class="text-slate-300 text-sm sm:text-base max-w-3xl">
                {html.escape(j_meta['description'])} Filtered automatically every 6 hours by SignalTender's 3-layer B2B quality control engine.
              </p>
              <div class="flex flex-wrap gap-2 pt-2">
                {cat_pills_html}
              </div>
            </div>

            <div class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">
              <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                  <thead>
                    <tr class="border-b border-slate-800 bg-slate-900/90 text-[11px] font-mono uppercase tracking-wider text-slate-400">
                      <th class="py-4 px-5">Jurisdiction</th>
                      <th class="py-4 px-5">Solicitation Title &amp; Scope</th>
                      <th class="py-4 px-4">Issuing Agency</th>
                      <th class="py-4 px-4">Closing Date</th>
                      <th class="py-4 px-5 text-right">Dossier</th>
                    </tr>
                  </thead>
                  <tbody class="text-xs">
                    {rows_html}
                  </tbody>
                </table>
              </div>
            </div>
            """

            full_html = _render_layout(
                page_title=f"{j_meta['headline']} | SignalTender",
                meta_desc=j_meta["description"],
                canonical_path=canonical_path,
                body_html=body_html,
                root_prefix="../../",
            )
            with open(os.path.join(OUTPUT_DIR, j_key, "index.html"), "w", encoding="utf-8") as f:
                f.write(full_html)
            pages_built += 1

            # State x Category pages
            for cat_key, cat_meta in CATEGORIES.items():
                jc_contracts = [c for c in j_contracts if cat_key in c["categories"]]
                jc_canonical = f"contracts/{j_key}/{cat_key}.html"
                sitemap_urls.append(f"{SITE_BASE_URL}/{jc_canonical}")
                jc_rows = _render_contract_table_rows(jc_contracts, rfp_link_prefix="../rfp/")

                jc_body = f"""
                <div class="mb-6 text-xs font-mono text-slate-400 flex items-center gap-2">
                  <a href="../index.html" class="hover:text-sky-400">All Contracts</a>
                  <span>/</span>
                  <a href="index.html" class="hover:text-sky-400">{html.escape(j_meta['name'])}</a>
                  <span>/</span>
                  <span class="text-white">{html.escape(cat_meta['name'])}</span>
                </div>
                <div class="mb-8 space-y-3">
                  <h1 class="text-3xl font-extrabold text-white tracking-tight">
                    {html.escape(j_meta['short'])} {html.escape(cat_meta['name'])} Government Contracts &amp; RFPs
                  </h1>
                  <p class="text-slate-300 text-sm max-w-3xl">
                    Browse {len(jc_contracts)} open {html.escape(cat_meta['name'].lower())} solicitations from {html.escape(j_meta['portal'])}.
                  </p>
                </div>
                <div class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">
                  <div class="overflow-x-auto">
                    <table class="w-full text-left border-collapse">
                      <thead>
                        <tr class="border-b border-slate-800 bg-slate-900/90 text-[11px] font-mono uppercase tracking-wider text-slate-400">
                          <th class="py-4 px-5">Jurisdiction</th>
                          <th class="py-4 px-5">Solicitation Title &amp; Scope</th>
                          <th class="py-4 px-4">Issuing Agency</th>
                          <th class="py-4 px-4">Closing Date</th>
                          <th class="py-4 px-5 text-right">Dossier</th>
                        </tr>
                      </thead>
                      <tbody class="text-xs">
                        {jc_rows}
                      </tbody>
                    </table>
                  </div>
                </div>
                """
                jc_html = _render_layout(
                    page_title=f"{j_meta['short']} {cat_meta['name']} RFPs & Government Contracts | SignalTender",
                    meta_desc=f"Live open {j_meta['short']} {cat_meta['name']} RFPs and government solicitations from {j_meta['portal']}.",
                    canonical_path=jc_canonical,
                    body_html=jc_body,
                    root_prefix="../../",
                )
                with open(os.path.join(OUTPUT_DIR, j_key, f"{cat_key}.html"), "w", encoding="utf-8") as f:
                    f.write(jc_html)
                pages_built += 1

        # 3. Build Master Directory Index (/contracts/index.html)
        jurisdiction_cards_html = ""
        for j_key, j_meta in JURISDICTIONS.items():
            cnt = sum(1 for c in enriched_contracts if c["jurisdiction"] == j_key)
            jurisdiction_cards_html += f"""
            <a href="{j_key}/index.html" class="p-5 rounded-xl bg-navy-900 hover:bg-slate-900 border border-slate-800 hover:border-sky-500/50 transition-all flex flex-col justify-between">
              <div>
                <span class="px-2.5 py-0.5 rounded border text-[10px] font-mono font-semibold {j_meta['badge_class']}">{html.escape(j_meta['short'].upper())}</span>
                <h2 class="text-lg font-bold text-white mt-3">{html.escape(j_meta['name'])}</h2>
                <p class="text-xs text-slate-400 mt-1">{html.escape(j_meta['description'])}</p>
              </div>
              <div class="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono">
                <span class="text-emerald-400">{cnt} Open Leads</span>
                <span class="text-sky-400">Browse Hub &rarr;</span>
              </div>
            </a>
            """

        all_rows_html = _render_contract_table_rows(enriched_contracts[:100], rfp_link_prefix="rfp/")
        hub_body = f"""
        <div class="mb-10 space-y-4">
          <div class="inline-flex items-center px-3 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-xs font-mono text-emerald-400">
            // LIVE GOVCON DIRECTORY &bull; {len(enriched_contracts)} VERIFIED OPEN IT SOLICITATIONS
          </div>
          <h1 class="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            Federal &amp; State SLED IT Contract Directory
          </h1>
          <p class="text-slate-300 text-base max-w-3xl">
            Explore {len(enriched_contracts)} live, AI-vetted government IT, software, cloud, and cybersecurity RFPs across SAM.gov, DemandStar, Texas, Virginia, California, Florida, and Maryland.
          </p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
          {jurisdiction_cards_html}
        </div>

        <h2 class="text-xl font-bold text-white font-mono uppercase tracking-wider mb-4">Latest Pre-Vetted Solicitations</h2>
        <div class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-slate-800 bg-slate-900/90 text-[11px] font-mono uppercase tracking-wider text-slate-400">
                  <th class="py-4 px-5">Jurisdiction</th>
                  <th class="py-4 px-5">Solicitation Title &amp; Scope</th>
                  <th class="py-4 px-4">Issuing Agency</th>
                  <th class="py-4 px-4">Closing Date</th>
                  <th class="py-4 px-5 text-right">Dossier</th>
                </tr>
              </thead>
              <tbody class="text-xs">
                {all_rows_html}
              </tbody>
            </table>
          </div>
        </div>
        """

        hub_html = _render_layout(
            page_title="Live Government IT & Cybersecurity Contracts Directory (Federal & SLED) | SignalTender",
            meta_desc="Browse live pre-vetted Federal (SAM.gov) and State SLED (TX, VA, CA, FL, MD) IT, software, cloud, and cybersecurity RFPs.",
            canonical_path="contracts/index.html",
            body_html=hub_body,
            root_prefix="../",
        )
        with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
            f.write(hub_html)
        pages_built += 1

        # 4. Generate sitemap.xml and robots.txt
        today_iso = today.strftime("%Y-%m-%d")
        sitemap_entries = "\n".join(
            f"  <url>\n    <loc>{html.escape(u)}</loc>\n    <lastmod>{today_iso}</lastmod>\n    <changefreq>daily</changefreq>\n  </url>"
            for u in sitemap_urls
        )
        sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{sitemap_entries}
</urlset>
"""
        with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
            f.write(sitemap_xml)

        robots_txt = f"""User-agent: *
Allow: /

Sitemap: {SITE_BASE_URL}/sitemap.xml
"""
        with open(ROBOTS_PATH, "w", encoding="utf-8") as f:
            f.write(robots_txt)

        # 5. Inject embedded SPA directory & dossier router into index.html
        #    so isolated single-HTML deployments (like signaltender.net on Render)
        #    serve all State Hubs, Category Filters, and RFP Dossiers with zero 404s.
        _inject_spa_directory_into_index(enriched_contracts)

        print(
            f"[+] Programmatic SEO build complete! Generated {pages_built} static HTML pages in /contracts "
            f"({len(enriched_contracts)} individual RFP dossiers + 36 state/category hubs), updated sitemap.xml, "
            f"and synced embedded SPA directory in index.html.",
            flush=True,
        )
        return pages_built

    except Exception as e:
        err_msg = f"pseo_generator.py error: {e}"
        print(f"[!] {err_msg}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n[!] {err_msg}\n")
        except Exception:
            pass
        send_discord_alert(err_msg)
        return 0


def _inject_spa_directory_into_index(enriched_contracts: list[dict]):
    index_path = os.path.join(BASE_DIR, "index.html")
    if not os.path.exists(index_path):
        return

    with open(index_path, "r", encoding="utf-8") as f:
        index_html = f.read()

    # 1. Update PSEO_HUB_BAR_START .. PSEO_HUB_BAR_END
    hub_bar_html = f"""<!-- PSEO_HUB_BAR_START -->
          <div class="px-6 py-4 bg-slate-900/90 border-t border-slate-800 flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
            <div class="flex flex-wrap items-center gap-2 text-slate-300">
              <span class="text-slate-400">BROWSE STATE HUBS:</span>
              <a href="#contracts/federal" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-sky-400">Federal (SAM)</a>
              <a href="#contracts/texas" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-indigo-300">Texas</a>
              <a href="#contracts/virginia" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-emerald-400">Virginia</a>
              <a href="#contracts/california" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-amber-300">California</a>
              <a href="#contracts/florida" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-cyan-300">Florida</a>
              <a href="#contracts/maryland" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-rose-300">Maryland</a>
              <a href="#contracts/municipal" class="px-2.5 py-1 rounded bg-navy-950 hover:bg-slate-800 border border-slate-800 text-purple-300">Municipal</a>
            </div>
            <a href="#contracts" class="text-sky-400 hover:text-sky-300 font-semibold">
              Explore All {len(enriched_contracts)} Live IT &amp; Cyber Solicitations &rarr;
            </a>
          </div>
          <!-- PSEO_HUB_BAR_END -->"""

    if "<!-- PSEO_HUB_BAR_START -->" in index_html and "<!-- PSEO_HUB_BAR_END -->" in index_html:
        index_html = re.sub(
            r"<!-- PSEO_HUB_BAR_START -->.*?<!-- PSEO_HUB_BAR_END -->",
            lambda _: hub_bar_html,
            index_html,
            flags=re.DOTALL,
        )

    # 2. Prepare JSON payload for embedded SPA directory
    spa_contracts = []
    for c in enriched_contracts:
        cat_key = c["categories"][0]
        tags = CATEGORIES.get(cat_key, CATEGORIES["software-development"])["tags"]
        spa_contracts.append({
            "id": c["id"],
            "slug": c["slug"],
            "clean_title": c["clean_title"],
            "raw_title": c["raw_title"],
            "agency": c["agency"],
            "masked_agency": c["masked_agency"],
            "due_str": c["due_str"] or "Open / See Portal",
            "jurisdiction": c["jurisdiction"],
            "categories": c["categories"],
            "tags": tags[:2],
        })

    contracts_json = json.dumps(spa_contracts)
    jurisdictions_json = json.dumps(JURISDICTIONS)
    categories_json = json.dumps({k: {"name": v["name"], "tags": v["tags"]} for k, v in CATEGORIES.items()})

    contracts_view_html = f"""<!-- PSEO_CONTRACTS_VIEW_START -->
  <div id="page-contracts" class="hidden">
    <div class="border-b border-slate-800/80 bg-navy-900/90 text-xs">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-9 flex items-center justify-between">
        <div class="flex items-center space-x-2.5">
          <span class="inline-block h-2 w-2 rounded-full bg-emerald-500"></span>
          <span class="font-mono text-slate-300">LIVE GOVCON INTELLIGENCE WIRE &bull; <span class="text-emerald-400">7 PORTALS ACTIVE</span></span>
        </div>
        <div class="flex items-center space-x-4 font-mono text-slate-400">
          <a href="#overview" class="hover:text-sky-400 transition-colors">&larr; Main Platform</a>
          <span>|</span>
          <a href="#apis" class="hover:text-sky-400 transition-colors">Developer APIs</a>
        </div>
      </div>
    </div>

    <header class="sticky top-0 z-50 backdrop-blur-md bg-navy-950/85 border-b border-slate-800/80">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <a href="#overview" class="flex items-center space-x-3 shrink-0">
          <span class="text-lg font-bold tracking-tight text-white">SignalTender</span>
          <span class="text-[10px] font-mono uppercase tracking-widest px-2 py-0.5 rounded bg-sky-500/15 text-sky-400 border border-sky-500/30">LIVE RFP INDEX</span>
        </a>
        <nav class="hidden md:flex items-center space-x-5 text-xs font-mono text-slate-300">
          <a href="#contracts" class="hover:text-sky-400 transition-colors">All Portals</a>
          <a href="#contracts/federal" class="hover:text-sky-400 transition-colors">Federal</a>
          <a href="#contracts/texas" class="hover:text-sky-400 transition-colors">Texas</a>
          <a href="#contracts/virginia" class="hover:text-sky-400 transition-colors">Virginia</a>
          <a href="#contracts/california" class="hover:text-sky-400 transition-colors">California</a>
          <a href="#contracts/florida" class="hover:text-sky-400 transition-colors">Florida</a>
          <a href="#contracts/maryland" class="hover:text-sky-400 transition-colors">Maryland</a>
          <a href="#contracts/municipal" class="hover:text-sky-400 transition-colors">Municipal</a>
        </nav>
        <a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center px-4 py-2 text-xs font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg border border-sky-400/30 transition-all shrink-0">
          Unlock All RFP Links &rarr;
        </a>
      </div>
    </header>

    <main id="contracts-dynamic-root" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 min-h-[65vh]"></main>
  </div>

  <script>
    window.SIGNALTENDER_CONTRACTS = {contracts_json};
    window.SIGNALTENDER_JURISDICTIONS = {jurisdictions_json};
    window.SIGNALTENDER_CATEGORIES = {categories_json};

    (function () {{
      function esc(str) {{
        return String(str || '')
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;');
      }}

      function renderRows(list) {{
        if (!list || !list.length) {{
          return '<tr><td colspan="5" class="py-8 px-5 text-center font-mono text-xs text-slate-400">No open solicitations currently in this view — our 6-hour scraper pipeline continuously indexes new bids across all 7 portals.</td></tr>';
        }}
        var J = window.SIGNALTENDER_JURISDICTIONS;
        return list.map(function (c) {{
          var jm = J[c.jurisdiction] || J.federal;
          var tagsHtml = (c.tags || []).map(function (t) {{
            return '<span class="inline-flex items-center whitespace-nowrap px-2 py-0.5 rounded bg-navy-900 border border-slate-800 text-slate-300">' + esc(t) + '</span>';
          }}).join(' ');
          return '<tr class="border-b border-slate-800/80 hover:bg-slate-900/60 transition-colors">' +
            '<td class="py-4 px-5 font-mono whitespace-nowrap align-top">' +
              '<a href="#contracts/' + esc(c.jurisdiction) + '" class="inline-flex items-center whitespace-nowrap px-2.5 py-0.5 rounded border text-[11px] ' + esc(jm.badge_class) + '">' + esc(jm.short.toUpperCase()) + '</a>' +
            '</td>' +
            '<td class="py-4 px-5 align-top">' +
              '<a href="#contracts/rfp/' + esc(c.slug) + '" class="font-semibold text-white hover:text-sky-400 transition-colors text-sm block">' + esc(c.clean_title) + '</a>' +
              '<div class="mt-1.5 flex flex-wrap gap-1.5 text-[11px] font-mono">' + tagsHtml + '</div>' +
            '</td>' +
            '<td class="py-4 px-4 text-slate-300 text-xs align-top">' + esc(c.masked_agency) + '</td>' +
            '<td class="py-4 px-4 font-mono text-amber-300 text-xs whitespace-nowrap align-top">' + esc(c.due_str) + '</td>' +
            '<td class="py-4 px-5 text-right font-mono whitespace-nowrap align-top">' +
              '<a href="#contracts/rfp/' + esc(c.slug) + '" class="inline-flex items-center whitespace-nowrap px-3 py-1.5 rounded bg-slate-900 hover:bg-sky-600 hover:text-white border border-slate-700 text-sky-400 text-xs transition-colors">' +
                '<span>View RFP Dossier</span><span class="ml-1.5">&rarr;</span>' +
              '</a>' +
            '</td>' +
          '</tr>';
        }}).join('');
      }}

      window.renderContractsRoute = function (rawHash) {{
        var root = document.getElementById('contracts-dynamic-root');
        if (!root) return;
        var clean = String(rawHash || '#contracts')
          .replace(/^#/, '')
          .replace(/\\/index\\.html$/, '')
          .replace(/\\.html$/, '')
          .replace(/\\/+$/, '');
        var parts = clean.split('/');
        var all = window.SIGNALTENDER_CONTRACTS || [];
        var J = window.SIGNALTENDER_JURISDICTIONS || {{}};
        var C = window.SIGNALTENDER_CATEGORIES || {{}};

        // Case 1: Individual RFP Dossier (#contracts/rfp/<slug>)
        if (parts[1] === 'rfp' && parts[2]) {{
          var slug = parts.slice(2).join('/');
          var item = null;
          for (var i = 0; i < all.length; i++) {{
            if (all[i].slug === slug) {{ item = all[i]; break; }}
          }}
          if (!item) {{
            root.innerHTML = '<div class="p-8 rounded-2xl bg-navy-900 border border-slate-800 text-center space-y-4">' +
              '<div class="text-lg font-bold text-white">Solicitation Dossier Archived or Expired</div>' +
              '<p class="text-xs text-slate-400 font-mono">This solicitation may have passed its closing date and been automatically purged.</p>' +
              '<a href="#contracts" class="inline-flex items-center px-4 py-2 rounded bg-sky-600 text-white text-xs font-mono">Browse All Active RFPs &rarr;</a>' +
            '</div>';
            return;
          }}
          var jm = J[item.jurisdiction] || J.federal;
          var catKey = (item.categories && item.categories[0]) || 'software-development';
          var cm = C[catKey] || {{ name: 'Enterprise IT & Software' }};
          document.title = item.clean_title + ' | ' + jm.short + ' Government IT RFP | SignalTender';

          var related = all.filter(function (o) {{ return o.jurisdiction === item.jurisdiction && o.slug !== item.slug; }}).slice(0, 5);
          var relatedHtml = related.length ? related.map(function (r) {{
            return '<li class="py-2 border-b border-slate-800/70"><a href="#contracts/rfp/' + esc(r.slug) + '" class="text-sky-400 hover:underline font-medium">' + esc(r.clean_title) + '</a> <span class="text-slate-500 font-mono text-xs ml-2">(' + esc(r.due_str) + ')</span></li>';
          }}).join('') : '<li class="text-slate-400 text-xs font-mono">Browse more opportunities in the portal hub above.</li>';

          root.innerHTML =
            '<div class="mb-6 text-xs font-mono text-slate-400 flex flex-wrap items-center gap-2">' +
              '<a href="#contracts" class="hover:text-sky-400">All Contracts</a><span>/</span>' +
              '<a href="#contracts/' + esc(item.jurisdiction) + '" class="hover:text-sky-400">' + esc(jm.name) + '</a><span>/</span>' +
              '<span class="text-slate-200">' + esc(item.slug.slice(0, 45)) + '</span>' +
            '</div>' +
            '<div class="grid grid-cols-1 lg:grid-cols-12 gap-8">' +
              '<div class="lg:col-span-8 space-y-6">' +
                '<div class="p-6 sm:p-8 rounded-2xl bg-navy-900 border border-slate-800 shadow-2xl space-y-5">' +
                  '<div class="flex flex-wrap items-center gap-2.5 font-mono text-xs">' +
                    '<span class="px-2.5 py-1 rounded border font-semibold ' + esc(jm.badge_class) + '">' + esc(jm.name.toUpperCase()) + '</span>' +
                    '<span class="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">STATUS: OPEN LEAD</span>' +
                    '<span class="px-2.5 py-1 rounded bg-slate-800 text-slate-300">' + esc(cm.name) + '</span>' +
                  '</div>' +
                  '<h1 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-snug">' + esc(item.clean_title) + '</h1>' +
                  '<p class="text-slate-300 text-sm leading-relaxed">' +
                    'Verified active government IT/cybersecurity solicitation monitored on <strong class="text-white">' + esc(jm.portal) + '</strong>. ' +
                    'Pre-vetted by SignalTender AI for B2B software, cloud, cybersecurity, or systems integration scope (all commodity office supply and maintenance renewal noise excluded).' +
                  '</p>' +
                  '<div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t border-slate-800/80 text-xs font-mono">' +
                    '<div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800/80">' +
                      '<div class="text-slate-400">ISSUING AGENCY</div>' +
                      '<div class="text-white font-semibold mt-1">' + esc(item.masked_agency) + '</div>' +
                    '</div>' +
                    '<div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800/80">' +
                      '<div class="text-slate-400">RESPONSE DEADLINE</div>' +
                      '<div class="text-amber-300 font-semibold mt-1">' + esc(item.due_str) + '</div>' +
                    '</div>' +
                    '<div class="p-3.5 rounded-xl bg-navy-950 border border-slate-800/80">' +
                      '<div class="text-slate-400">SOURCE PORTAL</div>' +
                      '<div class="text-sky-400 font-semibold mt-1">' + esc(jm.portal) + '</div>' +
                    '</div>' +
                  '</div>' +
                  '<div class="mt-6 p-6 rounded-xl bg-navy-950 border-2 border-sky-500/40 space-y-4">' +
                    '<div class="flex items-center justify-between">' +
                      '<span class="text-xs font-mono uppercase tracking-wider text-sky-400 font-semibold">// SUBSCRIBER-ONLY PROCUREMENT DOSSIER</span>' +
                      '<span class="text-xs font-mono text-emerald-400">INSTANT ACCESS</span>' +
                    '</div>' +
                    '<div class="space-y-2 text-xs font-mono text-slate-400">' +
                      '<div><strong class="text-slate-200">Official Government Bid URL:</strong> <span class="blur-sm select-none">https://portal.government.gov/solicitation/view/' + esc(item.id) + '98412</span></div>' +
                      '<div><strong class="text-slate-200">Full Issuing Buyer &amp; Contracting Officer:</strong> <span class="blur-sm select-none">' + esc(item.agency) + ' - Procurement Division</span></div>' +
                      '<div><strong class="text-slate-200">AI Compliance Matrix, Redline &amp; CLIN Pricing:</strong> <span class="blur-sm select-none">Included via SignalTender APIs</span></div>' +
                    '</div>' +
                    '<div class="pt-3 flex flex-col sm:flex-row gap-3">' +
                      '<a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center justify-center px-6 py-3 text-sm font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg shadow-lg transition-all">' +
                        'Unlock Direct RFP Link &amp; Discord Wire &rarr;' +
                      '</a>' +
                      '<a href="#product-compliance-matrix" class="inline-flex items-center justify-center px-5 py-3 text-xs font-mono text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 rounded-lg border border-amber-500/30 transition-colors">' +
                        'Generate Compliance Matrix via API &rarr;' +
                      '</a>' +
                    '</div>' +
                    '<p class="text-[11px] font-mono text-slate-400">Instant 60-second access via Whop. Flexible month-to-month—cancel anytime.</p>' +
                  '</div>' +
                '</div>' +
                '<div class="p-6 rounded-2xl bg-navy-900/60 border border-slate-800">' +
                  '<h2 class="text-base font-bold text-white font-mono uppercase tracking-wider mb-3">More Open ' + esc(jm.short) + ' IT Solicitations</h2>' +
                  '<ul class="text-sm space-y-1">' + relatedHtml + '</ul>' +
                '</div>' +
              '</div>' +
              '<div class="lg:col-span-4 space-y-6">' +
                '<div class="p-6 rounded-2xl bg-navy-900 border border-slate-800 space-y-4">' +
                  '<div class="text-xs font-mono text-sky-400 uppercase font-semibold">SIGNALWIRE PRO</div>' +
                  '<div class="text-2xl font-extrabold text-white">Stop Hunting Portals Manually</div>' +
                  '<p class="text-xs text-slate-300 leading-relaxed">' +
                    'Get every pre-vetted Federal (SAM.gov), DemandStar, and 5-State SLED (TX, VA, CA, FL, MD) IT &amp; cybersecurity solicitation pushed directly to your team every 6 hours.' +
                  '</p>' +
                  '<ul class="text-xs font-mono text-slate-300 space-y-2 pt-2">' +
                    '<li>&check; 99.4% Commodity &amp; Renewal Spam Stripped</li>' +
                    '<li>&check; Direct One-Click Official Portal Links</li>' +
                    '<li>&check; Instant Discord + Automated Feed Access</li>' +
                  '</ul>' +
                  '<a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="w-full inline-flex items-center justify-center px-5 py-3 text-xs font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg transition-all">' +
                    'Start Getting Leads &rarr;' +
                  '</a>' +
                '</div>' +
                '<div class="p-6 rounded-2xl bg-navy-900 border border-indigo-500/30 space-y-3">' +
                  '<div class="text-xs font-mono text-indigo-400 uppercase font-semibold">DEVELOPER &amp; CAPTURE APIs (8 LIVE)</div>' +
                  '<div class="text-lg font-bold text-white">Automate Your Bid Response</div>' +
                  '<p class="text-xs text-slate-300 leading-relaxed">' +
                    'Classify NAICS/SIC/PSC/UNSPSC codes, score Bid/No-Bid Pwin (0&ndash;100), audit FAR/DFARS &amp; CMMC 2.0 flow-downs, shred this RFP into a Shipley compliance matrix, extract SOW deliverables, audit legal clauses, or query historical CLIN pricing via our RapidAPI microservices.' +
                  '</p>' +
                  '<a href="#product-industry-classifier" class="w-full inline-flex items-center justify-center px-4 py-2.5 text-xs font-mono font-semibold text-indigo-300 bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/40 rounded-lg transition-all">' +
                    'Explore 8 RapidAPI Microservices &rarr;' +
                  '</a>' +
                '</div>' +
              '</div>' +
            '</div>';
          return;
        }}

        // Case 2: Jurisdiction Hub (#contracts/<jurisdiction> or #contracts/<jurisdiction>/<category>)
        var jKey = parts[1];
        if (jKey && J[jKey]) {{
          var jmHub = J[jKey];
          var activeCat = parts[2] && C[parts[2]] ? parts[2] : null;
          var jList = all.filter(function (c) {{
            if (c.jurisdiction !== jKey) return false;
            if (activeCat && (!c.categories || c.categories.indexOf(activeCat) === -1)) return false;
            return true;
          }});

          document.title = (activeCat ? (jmHub.short + ' ' + C[activeCat].name + ' RFPs | ') : (jmHub.headline + ' | ')) + 'SignalTender';

          var pills = '<a href="#contracts/' + esc(jKey) + '" class="px-3 py-1.5 rounded-lg border text-xs font-mono transition-colors ' +
            (!activeCat ? 'bg-sky-600 text-white border-sky-400' : 'bg-navy-900 hover:bg-slate-800 border-slate-700 text-slate-300') + '">All ' + esc(jmHub.short) + ' IT Bids</a>';
          Object.keys(C).forEach(function (ck) {{
            var isAct = activeCat === ck;
            pills += ' <a href="#contracts/' + esc(jKey) + '/' + esc(ck) + '" class="px-3 py-1.5 rounded-lg border text-xs font-mono transition-colors ' +
              (isAct ? 'bg-sky-600 text-white border-sky-400' : 'bg-navy-900 hover:bg-slate-800 border-slate-700 text-sky-400') + '">' + esc(C[ck].name) + '</a>';
          }});

          root.innerHTML =
            '<div class="mb-6 text-xs font-mono text-slate-400 flex items-center gap-2">' +
              '<a href="#contracts" class="hover:text-sky-400">&larr; All Portals Directory</a>' +
              '<span>/</span>' +
              '<span class="text-white">' + esc(jmHub.name) + '</span>' +
              (activeCat ? ('<span>/</span><span class="text-sky-400">' + esc(C[activeCat].name) + '</span>') : '') +
            '</div>' +
            '<div class="mb-8 space-y-4">' +
              '<div class="inline-flex items-center px-3 py-1 rounded border text-xs font-mono ' + esc(jmHub.badge_class) + '">' +
                '// ' + esc(jmHub.portal.toUpperCase()) + ' &bull; ' + jList.length + ' ACTIVE IT SOLICITATIONS' +
              '</div>' +
              '<h1 class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">' +
                esc(activeCat ? (jmHub.short + ' ' + C[activeCat].name + ' Government Contracts & RFPs') : jmHub.headline) +
              '</h1>' +
              '<p class="text-slate-300 text-sm sm:text-base max-w-3xl">' +
                esc(jmHub.description) + ' Filtered automatically every 6 hours by SignalTender\\'s 3-layer B2B quality control engine.' +
              '</p>' +
              '<div class="flex flex-wrap gap-2 pt-2">' + pills + '</div>' +
            '</div>' +
            '<div class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">' +
              '<div class="overflow-x-auto">' +
                '<table class="w-full text-left border-collapse">' +
                  '<thead>' +
                    '<tr class="border-b border-slate-800 bg-slate-900/90 text-[11px] font-mono uppercase tracking-wider text-slate-400">' +
                      '<th class="py-4 px-5">Jurisdiction</th>' +
                      '<th class="py-4 px-5">Solicitation Title &amp; Scope</th>' +
                      '<th class="py-4 px-4">Issuing Agency</th>' +
                      '<th class="py-4 px-4">Closing Date</th>' +
                      '<th class="py-4 px-5 text-right">Dossier</th>' +
                    '</tr>' +
                  '</thead>' +
                  '<tbody class="text-xs">' + renderRows(jList) + '</tbody>' +
                '</table>' +
              '</div>' +
            '</div>';
          return;
        }}

        // Case 3: Master Directory (#contracts)
        document.title = 'Live Government IT & Cybersecurity Contracts Directory (Federal & SLED) | SignalTender';
        var cardsHtml = Object.keys(J).map(function (jk) {{
          var jmCard = J[jk];
          var cnt = all.filter(function (c) {{ return c.jurisdiction === jk; }}).length;
          return '<a href="#contracts/' + esc(jk) + '" class="p-5 rounded-xl bg-navy-900 hover:bg-slate-900 border border-slate-800 hover:border-sky-500/50 transition-all flex flex-col justify-between">' +
            '<div>' +
              '<span class="px-2.5 py-0.5 rounded border text-[10px] font-mono font-semibold ' + esc(jmCard.badge_class) + '">' + esc(jmCard.short.toUpperCase()) + '</span>' +
              '<h2 class="text-lg font-bold text-white mt-3">' + esc(jmCard.name) + '</h2>' +
              '<p class="text-xs text-slate-400 mt-1">' + esc(jmCard.description) + '</p>' +
            '</div>' +
            '<div class="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono">' +
              '<span class="text-emerald-400">' + cnt + ' Open Leads</span>' +
              '<span class="text-sky-400">Browse Hub &rarr;</span>' +
            '</div>' +
          '</a>';
        }}).join('');

        root.innerHTML =
          '<div class="mb-10 space-y-4">' +
            '<div class="inline-flex items-center px-3 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-xs font-mono text-emerald-400">' +
              '// LIVE GOVCON DIRECTORY &bull; ' + all.length + ' VERIFIED OPEN IT SOLICITATIONS' +
            '</div>' +
            '<h1 class="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">' +
              'Federal &amp; State SLED IT Contract Directory' +
            '</h1>' +
            '<p class="text-slate-300 text-base max-w-3xl">' +
              'Explore ' + all.length + ' live, AI-vetted government IT, software, cloud, and cybersecurity RFPs across SAM.gov, DemandStar, Texas, Virginia, California, Florida, and Maryland.' +
            '</p>' +
          '</div>' +
          '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">' + cardsHtml + '</div>' +
          '<h2 class="text-xl font-bold text-white font-mono uppercase tracking-wider mb-4">All Verified Open IT &amp; Cybersecurity Solicitations</h2>' +
          '<div class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">' +
            '<div class="overflow-x-auto">' +
              '<table class="w-full text-left border-collapse">' +
                '<thead>' +
                  '<tr class="border-b border-slate-800 bg-slate-900/90 text-[11px] font-mono uppercase tracking-wider text-slate-400">' +
                    '<th class="py-4 px-5">Jurisdiction</th>' +
                    '<th class="py-4 px-5">Solicitation Title &amp; Scope</th>' +
                    '<th class="py-4 px-4">Issuing Agency</th>' +
                    '<th class="py-4 px-4">Closing Date</th>' +
                    '<th class="py-4 px-5 text-right">Dossier</th>' +
                  '</tr>' +
                '</thead>' +
                '<tbody class="text-xs">' + renderRows(all) + '</tbody>' +
              '</table>' +
            '</div>' +
          '</div>';
      }};
    }})();
  </script>
  <!-- PSEO_CONTRACTS_VIEW_END -->"""

    if "<!-- PSEO_CONTRACTS_VIEW_START -->" in index_html and "<!-- PSEO_CONTRACTS_VIEW_END -->" in index_html:
        index_html = re.sub(
            r"<!-- PSEO_CONTRACTS_VIEW_START -->.*?<!-- PSEO_CONTRACTS_VIEW_END -->",
            lambda _: contracts_view_html,
            index_html,
            flags=re.DOTALL,
        )

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)


if __name__ == "__main__":
    generate_pseo_site()

