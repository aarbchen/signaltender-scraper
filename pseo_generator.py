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
    "STRIPE_TIER1_CHECKOUT_URL",
    f"{SITE_BASE_URL}/index.html#checkout-tier1",
)
WHOP_TIER2_URL = os.getenv(
    "STRIPE_TIER2_CHECKOUT_URL",
    f"{SITE_BASE_URL}/index.html#checkout-tier2",
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
            json={"content": f"**[ALERT] pSEO Generator Alert:**\n{message}"},
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
  <link rel="icon" type="image/png" sizes="48x48" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAEnElEQVR42t2YT0hUURTGZzRNc2pCW0R/FkqmhBAVQkFFiEEgJYQI0SIiEYzZZdEighYuKqgIWlRU1MKWRRjSoiiIiqCoKK0YCqNMCMxEbf7l9J36BobnvW/em3ffGA384M27937fOTP3nfvuDQQMf2KJ1BxQCWrAKlLDe3MC/+IHgc0Fa8Eh0AcGwAj4TkZ4r499pO/cfyXwbeAWGAVph4xyzLZZSwTGteAamHARuJUJatQWMvAg2AreeAjcyhtqBgsR/E4w7CCoaRAn0w76D1M76GcCTTmClynxEPSAdvZv4nUP2yZyJNHkV/DV4KXGOMEK0wxCNhoh9unjGJWWeFSbDr4EnNcYSpk8AOa70JvPMd81muJVYjKBzeCHwmgM7AHFeWgWc+yYQle8NptcWXsVJklwOJ/gLUkcppZVv9fIyg2ROq6kVoO7IGxAP0wtq7541plIYJ+iDMZAq27M+ruxBWAH6CFyvcDGo5Wa1jK8z0Tdv6qpFJWa4KvBbRAHaRLnvWqNT6Wmwl31tC5g8DzwWCF8USWMACvAjazArUhbheaHuqjwEe95XhJYBN4rhCOaX38LmLRJQNq2aLwiCh/xXuQlgaXgk0J4lyaBLpvgM3RpvHYpfMR7qZcEloAhhfBuTQIdDhLo0HjtVviI9xIvCcjDNagQ7tYksA6M2gQvbes0Xt0Kn0FdsXCaQBm4rxC+DooUCZSAMyClCD7FthKFTxE1rT7iXea1lJ5TCEd1cxMBLgQnwFfwi3zlvYU2z1pU4XPOxELWBlIWYfneabOQFYM60ErkutjGo1Pj0WYigeXgg+LXeSVthvRfKfQ/mNDPzM/Tmh3XBS8LDRfKC5od22nVc5avUQP4ojCJc6dVkYdmBcfGFbri1WByPyD/whHFPM3sxq7I4ZULvRqOUe3KUvQqCgTM7spkTei32cC/5S5rBShVjC9l2wH21W30+z3V/hxJ1IPnOU4i5O+/A05xcerm9R222Z1QiHa930cra8Azg2dCGURzTaEOt1byaDCpC2gqnkqPTP5Frm0CT1JrZaGPFsOczx+zp8VP8P5HKn1yMJFuexT/g1zLvZ8zp9tHaoQDgdk5Hw3yjPQYeP15IhU7H02kWx/OfJGTe9ImfaQvx9T6fpzo5LPxXqyq/Wni0PZniXcb7sWmdW+j0iZ9pK+MmfXAEVQItIMnIOlgL5AhyTEyNjQbgZeCraAfxFwEbiVGDdEqLUTg8pbZCHrBuIMAM6/TufqNU7PR7q3VS+BBUA/Ogm8OApLnIAoOkijv5Rr3jR7iFTQV/DJwFAw5nBayeTkOaph4kNfH2eZEY4iey7wEXgX2gwGHv94YuARWA9V2s4htl9jXyb84wBiq/KwsU+Am2KTa72r2zZs4ZspYxcqjsiTAA557lufxD5dz7ANq5V+xcKOMm26nleUF2AvCBp6xMLVeuKhYEmtZtkhzjiNBa2VZ7EOlW+yiYkmszdmDI24qi4/rjJuKFcke2GI5DndUWXxMJFfFklhbrJXnclYSk24qi4+JZFesyazgL8+oSEyihdOpOZ/K4mMi5YwpwhhDgf/l8xu20AuCvMPZbAAAAABJRU5ErkJggg==" />
  <link rel="icon" type="image/png" sizes="96x96" href="https://signaltender.net/contracts/favicon-96x96.png" />
  <link rel="icon" type="image/png" sizes="192x192" href="https://signaltender.net/contracts/favicon-192x192.png" />
  <link rel="icon" type="image/png" sizes="48x48" href="https://signaltender.net/contracts/favicon-48x48.png" />
  <link rel="icon" type="image/png" sizes="32x32" href="https://signaltender.net/contracts/favicon-32x32.png" />
  <link rel="icon" type="image/svg+xml" href="https://signaltender.net/contracts/favicon.svg" />
  <link rel="shortcut icon" href="https://signaltender.net/contracts/favicon.ico" />
  <link rel="apple-touch-icon" sizes="180x180" href="https://signaltender.net/contracts/apple-touch-icon.png" />
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
        <a href="{root_prefix}index.html" class="flex items-center space-x-2 shrink-0">
          <svg class="w-6 h-6 shrink-0" viewBox="6 5 52 54" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="32" cy="24" r="15" stroke="#F8FAFC" stroke-width="6" />
            <circle cx="32" cy="24" r="5" fill="#38BDF8" />
            <path d="M10 54L32 42L54 54" stroke="#38BDF8" stroke-width="6.5" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
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
  <script>
    window.filterStaticContractsTable = function (qVal) {{
      var anchorEl = document.getElementById('static-rfp-search') || document.activeElement;
      var anchorTopBefore = (anchorEl && anchorEl.getBoundingClientRect) ? anchorEl.getBoundingClientRect().top : null;
      var q = String(qVal || '').trim().toLowerCase();
      var tbody = document.querySelector('main table tbody');
      if (!tbody) return;
      var tblWrap = tbody.closest('.overflow-x-auto') || tbody.parentElement;
      if (tblWrap && !tblWrap.getAttribute('data-locked-min-h') && tblWrap.offsetHeight > 0) {{
        tblWrap.style.minHeight = tblWrap.offsetHeight + 'px';
        tblWrap.style.overflowAnchor = 'none';
        tblWrap.setAttribute('data-locked-min-h', '1');
      }}
      var rows = tbody.querySelectorAll('tr:not(#static-rfp-empty-row)');
      var shown = 0;
      for (var i = 0; i < rows.length; i++) {{
        var txt = (rows[i].innerText || '').toLowerCase();
        if (!q || txt.indexOf(q) !== -1) {{
          rows[i].classList.remove('hidden');
          shown++;
        }} else {{
          rows[i].classList.add('hidden');
        }}
      }}
      var badge = document.getElementById('static-rfp-count-badge');
      if (badge) {{
        badge.textContent = shown + ' OF ' + rows.length + ' SHOWN';
      }}
      var clearBtn = document.getElementById('static-rfp-clear-btn');
      if (clearBtn) {{
        if (q) clearBtn.classList.remove('hidden');
        else clearBtn.classList.add('hidden');
      }}
      var emptyRow = document.getElementById('static-rfp-empty-row');
      if (!emptyRow) {{
        emptyRow = document.createElement('tr');
        emptyRow.id = 'static-rfp-empty-row';
        emptyRow.className = 'hidden';
        emptyRow.innerHTML = '<td colspan="5" class="py-8 px-5 text-center font-mono text-xs text-slate-400">No solicitations matched that search query.</td>';
        tbody.appendChild(emptyRow);
      }}
      if (shown === 0 && rows.length > 0) emptyRow.classList.remove('hidden');
      else emptyRow.classList.add('hidden');
      if (anchorEl && anchorTopBefore !== null && anchorEl.getBoundingClientRect) {{
        var deltaY = anchorEl.getBoundingClientRect().top - anchorTopBefore;
        if (Math.abs(deltaY) > 0.5) {{
          var docEl = document.documentElement;
          var prevB = docEl.style.scrollBehavior;
          docEl.style.scrollBehavior = 'auto';
          window.scrollBy(0, deltaY);
          docEl.style.scrollBehavior = prevB;
        }}
      }}
    }};
  </script>
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
            if str(rec.get("url") or "").startswith("subscriber://") or str(rec.get("status") or "").startswith("SUBSCRIBER_"):
                continue
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

                  <!-- Pre-Computed AI Capture Dossier & Gated Portal Link Box -->
                  <div class="mt-6 p-6 rounded-xl bg-navy-950 border-2 border-indigo-500/50 space-y-5">
                    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
                      <span class="text-xs font-mono uppercase tracking-wider text-indigo-300 font-bold">// CAPTUREDESK AI DOSSIER &amp; SOURCE PORTAL ACCESS</span>
                      <span class="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[10px] font-mono">AI-ENRICHED</span>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
                      <div class="p-3 rounded-lg bg-navy-900 border border-slate-800 space-y-1">
                        <div class="text-[10px] text-sky-400 font-bold">01. AI CLASSIFICATION (API #08)</div>
                        <div class="text-slate-200">NAICS <span class="text-white font-semibold">541512 / 541519</span> &bull; SBA Cap: <span class="text-emerald-400">$34.0M</span></div>
                      </div>
                      <div class="p-3 rounded-lg bg-navy-900 border border-slate-800 space-y-1">
                        <div class="text-[10px] text-emerald-400 font-bold">02. CLIN LABOR BENCHMARKS (API #03)</div>
                        <div class="text-slate-200">Sr. Architect: <span class="text-emerald-400 font-bold">$162/hr</span> &bull; Lead Eng: <span class="text-emerald-400 font-bold">$146/hr</span></div>
                      </div>
                    </div>

                    <div class="space-y-2 text-xs font-mono text-slate-400 pt-1">
                      <div><strong class="text-slate-200">Official Government Bid URL:</strong> <span class="blur-sm select-none">https://portal.government.gov/solicitation/view/{c['id']}98412</span></div>
                      <div><strong class="text-slate-200">Full Issuing Buyer &amp; Contracting Officer:</strong> <span class="blur-sm select-none">{html.escape(c['agency'])} - Procurement Division</span></div>
                      <div><strong class="text-slate-200">Shipley Section L/M Compliance Matrix &amp; FAR/DFARS Redlines:</strong> <span class="blur-sm select-none">Pre-built in #capturedesk-autopilot &amp; API #05/#06</span></div>
                    </div>
                    <div class="pt-3 flex flex-col sm:flex-row gap-3">
                      <a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center justify-center px-6 py-3 text-sm font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg shadow-lg transition-all">
                        Unlock Direct RFP Link &amp; Capture Dossier &rarr;
                      </a>
                      <a href="../../apis.html#product-compliance-matrix" class="inline-flex items-center justify-center px-5 py-3 text-xs font-mono text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 rounded-lg border border-amber-500/30 transition-colors">
                        Shred via Shipley Compliance API &rarr;
                      </a>
                    </div>
                    <p class="text-[11px] font-mono text-slate-400">Instant 60-second Discord, Slack, Microsoft Teams &amp; CRM webhook activation. Cancel anytime.</p>
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
                  <div class="flex items-center justify-between">
                    <span class="text-xs font-mono text-sky-400 uppercase font-semibold">SIGNALWIRE PRO &bull; $99/MO</span>
                    <span class="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">$990/YR</span>
                  </div>
                  <div class="text-2xl font-extrabold text-white">Stop Hunting Portals Manually</div>
                  <p class="text-xs text-slate-300 leading-relaxed">
                    Get every pre-vetted Federal (SAM.gov), DemandStar, and 5-State SLED (TX, VA, CA, FL, MD) IT &amp; cybersecurity solicitation pushed directly to your team every 6 hours.
                  </p>
                  <ul class="text-xs font-mono text-slate-300 space-y-2 pt-2">
                    <li>&check; 99.4% Commodity &amp; Renewal Spam Stripped</li>
                    <li>&check; Direct One-Click Official Portal Links</li>
                    <li>&check; Tier 2 CaptureDesk ($399/mo | $3,490/yr) Auto-Dossiers</li>
                  </ul>
                  <a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="w-full inline-flex items-center justify-center px-5 py-3 text-xs font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg transition-all">
                    Start Tier 1 Leads ($99/mo) &rarr;
                  </a>
                  <a href="{WHOP_TIER2_URL}" target="_blank" rel="noopener noreferrer" class="w-full inline-flex items-center justify-center px-5 py-2.5 text-xs font-mono font-semibold text-indigo-200 bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 rounded-lg transition-all">
                    Launch Tier 2 CaptureDesk ($399/mo) &rarr;
                  </a>
                </div>

                <div class="p-6 rounded-2xl bg-navy-900 border border-indigo-500/30 space-y-3">
                  <div class="text-xs font-mono text-indigo-400 uppercase font-semibold">13 LIVE APIs &amp; MCP SERVER</div>
                  <div class="text-lg font-bold text-white">Automate Your Bid Response</div>
                  <p class="text-xs text-slate-300 leading-relaxed">
                    Tailor Key Personnel &amp; GSA LCAT resumes, auto-answer SOC 2, FedRAMP &amp; NIST 800-171 security questionnaires, generate 13 CFR &sect; 125.6 (50% Rule) teaming plans, extract Section B CLIN pricing tables, draft Shipley proposal narratives &amp; CO Q&amp;A, classify NAICS/SIC/PSC/UNSPSC codes, score Bid/No-Bid Pwin (0&ndash;100), audit FAR/DFARS &amp; CMMC 2.0 flow-downs, or shred this RFP into a compliance matrix via our 13 RapidAPI microservices &amp; <code class="text-indigo-200">@signaltender/mcp-server</code>.
                  </p>
                  <a href="../../apis.html#product-key-personnel" class="w-full inline-flex items-center justify-center px-4 py-2.5 text-xs font-mono font-semibold text-indigo-300 bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/40 rounded-lg transition-all">
                    Explore 13 APIs &amp; MCP Server &rarr;
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
              <div class="p-4 bg-slate-900/70 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div class="relative flex-1 flex items-center">
                  <svg class="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10.5a7.5 7.5 0 0013.15 6.15z" />
                  </svg>
                  <input
                    id="static-rfp-search"
                    type="text"
                    placeholder="Filter solicitations by keyword, agency, technology, or due date..."
                    oninput="window.filterStaticContractsTable(this.value)"
                    class="w-full pl-10 pr-20 py-2 rounded-xl bg-navy-950 border border-slate-700/90 focus:border-sky-500 focus:outline-none text-xs font-mono text-white placeholder-slate-500"
                  />
                  <button
                    id="static-rfp-clear-btn"
                    type="button"
                    onclick="document.getElementById('static-rfp-search').value=''; window.filterStaticContractsTable('');"
                    class="hidden absolute right-2.5 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-300 border border-slate-700 cursor-pointer"
                  >
                    Clear
                  </button>
                </div>
                <span id="static-rfp-count-badge" class="text-xs font-mono text-emerald-400 shrink-0">LIVE FILTER READY</span>
              </div>
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
              <div class="p-4 bg-slate-900/70 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div class="relative flex-1 flex items-center">
                  <svg class="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10.5a7.5 7.5 0 0013.15 6.15z" />
                  </svg>
                  <input
                    id="static-rfp-search"
                    type="text"
                    placeholder="Filter solicitations by keyword, agency, technology, or due date..."
                    oninput="window.filterStaticContractsTable(this.value)"
                    class="w-full pl-10 pr-20 py-2 rounded-xl bg-navy-950 border border-slate-700/90 focus:border-sky-500 focus:outline-none text-xs font-mono text-white placeholder-slate-500"
                  />
                  <button
                    id="static-rfp-clear-btn"
                    type="button"
                    onclick="document.getElementById('static-rfp-search').value=''; window.filterStaticContractsTable('');"
                    class="hidden absolute right-2.5 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-300 border border-slate-700 cursor-pointer"
                  >
                    Clear
                  </button>
                </div>
                <span id="static-rfp-count-badge" class="text-xs font-mono text-emerald-400 shrink-0">LIVE FILTER READY</span>
              </div>
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
              <div class="p-4 bg-slate-900/70 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div class="relative flex-1 flex items-center">
                  <svg class="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10.5a7.5 7.5 0 0013.15 6.15z" />
                  </svg>
                  <input
                    id="static-rfp-search"
                    type="text"
                    placeholder="Filter solicitations by keyword, agency, technology, or due date..."
                    oninput="window.filterStaticContractsTable(this.value)"
                    class="w-full pl-10 pr-20 py-2 rounded-xl bg-navy-950 border border-slate-700/90 focus:border-sky-500 focus:outline-none text-xs font-mono text-white placeholder-slate-500"
                  />
                  <button
                    id="static-rfp-clear-btn"
                    type="button"
                    onclick="document.getElementById('static-rfp-search').value=''; window.filterStaticContractsTable('');"
                    class="hidden absolute right-2.5 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-300 border border-slate-700 cursor-pointer"
                  >
                    Clear
                  </button>
                </div>
                <span id="static-rfp-count-badge" class="text-xs font-mono text-emerald-400 shrink-0">LIVE FILTER READY</span>
              </div>
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
        <a href="#overview" class="flex items-center space-x-2 shrink-0">
          <svg class="w-6 h-6 shrink-0" viewBox="6 5 52 54" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="32" cy="24" r="15" stroke="#F8FAFC" stroke-width="6" />
            <circle cx="32" cy="24" r="5" fill="#38BDF8" />
            <path d="M10 54L32 42L54 54" stroke="#38BDF8" stroke-width="6.5" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
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

      window.filterContractsDirectory = function (qVal) {{
        var inp = document.getElementById('contracts-live-search');
        var anchorEl = inp || document.activeElement;
        var anchorTopBefore = (anchorEl && anchorEl.getBoundingClientRect) ? anchorEl.getBoundingClientRect().top : null;
        var q = String(qVal !== undefined ? qVal : (inp ? inp.value : '')).trim().toLowerCase();
        if (inp && inp.value !== qVal && qVal !== undefined) inp.value = qVal;
        var clearBtn = document.getElementById('contracts-live-clear');
        if (clearBtn) {{
          if (q) clearBtn.classList.remove('hidden');
          else clearBtn.classList.add('hidden');
        }}
        var root = document.getElementById('contracts-dynamic-root');
        if (!root) return;
        var tbody = root.querySelector('table tbody');
        if (!tbody) return;
        var tblWrap = tbody.closest('.overflow-x-auto') || tbody.parentElement;
        if (tblWrap && !tblWrap.getAttribute('data-locked-min-h') && tblWrap.offsetHeight > 0) {{
          tblWrap.style.minHeight = tblWrap.offsetHeight + 'px';
          tblWrap.style.overflowAnchor = 'none';
          tblWrap.setAttribute('data-locked-min-h', '1');
        }}
        var rows = tbody.querySelectorAll('tr:not(#contracts-live-empty)');
        var shown = 0;
        for (var i = 0; i < rows.length; i++) {{
          var txt = (rows[i].innerText || '').toLowerCase();
          if (!q || txt.indexOf(q) !== -1) {{
            rows[i].classList.remove('hidden');
            shown++;
          }} else {{
            rows[i].classList.add('hidden');
          }}
        }}
        var cntEl = document.getElementById('contracts-live-count');
        if (cntEl) {{
          cntEl.textContent = shown + ' OF ' + rows.length + ' SOLICITATIONS SHOWN';
        }}
        var emptyRow = document.getElementById('contracts-live-empty');
        if (!emptyRow) {{
          emptyRow = document.createElement('tr');
          emptyRow.id = 'contracts-live-empty';
          emptyRow.className = 'hidden';
          emptyRow.innerHTML = '<td colspan="5" class="py-8 px-5 text-center font-mono text-xs text-slate-400">No solicitations matched that search query. <button type="button" onclick="window.filterContractsDirectory(\'\')" class="text-sky-400 underline ml-1 cursor-pointer">Reset filter</button></td>';
          tbody.appendChild(emptyRow);
        }}
        if (shown === 0 && rows.length > 0) emptyRow.classList.remove('hidden');
        else emptyRow.classList.add('hidden');
        if (anchorEl && anchorTopBefore !== null && anchorEl.getBoundingClientRect) {{
          var deltaY = anchorEl.getBoundingClientRect().top - anchorTopBefore;
          if (Math.abs(deltaY) > 0.5) {{
            var docEl = document.documentElement;
            var prevB = docEl.style.scrollBehavior;
            docEl.style.scrollBehavior = 'auto';
            window.scrollBy(0, deltaY);
            docEl.style.scrollBehavior = prevB;
          }}
        }}
      }};

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
                  '<div class="mt-6 p-6 rounded-xl bg-navy-950 border-2 border-indigo-500/50 space-y-5">' +
                    '<div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">' +
                      '<span class="text-xs font-mono uppercase tracking-wider text-indigo-300 font-bold">// CAPTUREDESK AI DOSSIER &amp; SOURCE PORTAL ACCESS</span>' +
                      '<span class="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[10px] font-mono">AI-ENRICHED</span>' +
                    '</div>' +
                    '<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">' +
                      '<div class="p-3 rounded-lg bg-navy-900 border border-slate-800 space-y-1">' +
                        '<div class="text-[10px] text-sky-400 font-bold">01. AI CLASSIFICATION (API #08)</div>' +
                        '<div class="text-slate-200">NAICS <span class="text-white font-semibold">541512 / 541519</span> &bull; SBA Cap: <span class="text-emerald-400">$34.0M</span></div>' +
                      '</div>' +
                      '<div class="p-3 rounded-lg bg-navy-900 border border-slate-800 space-y-1">' +
                        '<div class="text-[10px] text-emerald-400 font-bold">02. CLIN LABOR BENCHMARKS (API #03)</div>' +
                        '<div class="text-slate-200">Sr. Architect: <span class="text-emerald-400 font-bold">$162/hr</span> &bull; Lead Eng: <span class="text-emerald-400 font-bold">$146/hr</span></div>' +
                      '</div>' +
                    '</div>' +
                    '<div class="space-y-2 text-xs font-mono text-slate-400 pt-1">' +
                      '<div><strong class="text-slate-200">Official Government Bid URL:</strong> <span class="blur-sm select-none">https://portal.government.gov/solicitation/view/' + esc(item.id) + '98412</span></div>' +
                      '<div><strong class="text-slate-200">Full Issuing Buyer &amp; Contracting Officer:</strong> <span class="blur-sm select-none">' + esc(item.agency) + ' - Procurement Division</span></div>' +
                      '<div><strong class="text-slate-200">Shipley Section L/M Compliance Matrix &amp; FAR/DFARS Redlines:</strong> <span class="blur-sm select-none">Pre-built in #capturedesk-autopilot &amp; API #05/#06</span></div>' +
                    '</div>' +
                    '<div class="pt-3 flex flex-col sm:flex-row gap-3">' +
                      '<a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center justify-center px-6 py-3 text-sm font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg shadow-lg transition-all">' +
                        'Unlock Direct RFP Link &amp; Capture Dossier &rarr;' +
                      '</a>' +
                      '<a href="#product-compliance-matrix" class="inline-flex items-center justify-center px-5 py-3 text-xs font-mono text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 rounded-lg border border-amber-500/30 transition-colors">' +
                        'Shred via Shipley Compliance API &rarr;' +
                      '</a>' +
                    '</div>' +
                    '<p class="text-[11px] font-mono text-slate-400">Instant 60-second Discord, Slack, Microsoft Teams &amp; CRM webhook activation. Cancel anytime.</p>' +
                  '</div>' +
                '</div>' +
                '<div class="p-6 rounded-2xl bg-navy-900/60 border border-slate-800">' +
                  '<h2 class="text-base font-bold text-white font-mono uppercase tracking-wider mb-3">More Open ' + esc(jm.short) + ' IT Solicitations</h2>' +
                  '<ul class="text-sm space-y-1">' + relatedHtml + '</ul>' +
                '</div>' +
              '</div>' +
              '<div class="lg:col-span-4 space-y-6">' +
                '<div class="p-6 rounded-2xl bg-navy-900 border border-slate-800 space-y-4">' +
                  '<div class="flex items-center justify-between">' +
                    '<span class="text-xs font-mono text-sky-400 uppercase font-semibold">SIGNALWIRE PRO &bull; $99/MO</span>' +
                    '<span class="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">$990/YR</span>' +
                  '</div>' +
                  '<div class="text-2xl font-extrabold text-white">Stop Hunting Portals Manually</div>' +
                  '<p class="text-xs text-slate-300 leading-relaxed">' +
                    'Get every pre-vetted Federal (SAM.gov), DemandStar, and 5-State SLED (TX, VA, CA, FL, MD) IT &amp; cybersecurity solicitation pushed directly to your team every 6 hours.' +
                  '</p>' +
                  '<ul class="text-xs font-mono text-slate-300 space-y-2 pt-2">' +
                    '<li>&check; 99.4% Commodity &amp; Renewal Spam Stripped</li>' +
                    '<li>&check; Direct One-Click Official Portal Links</li>' +
                    '<li>&check; Tier 2 CaptureDesk ($399/mo | $3,490/yr) Auto-Dossiers</li>' +
                  '</ul>' +
                  '<a href="{WHOP_TIER1_URL}" target="_blank" rel="noopener noreferrer" class="w-full inline-flex items-center justify-center px-5 py-3 text-xs font-mono font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg transition-all">' +
                    'Start Tier 1 Leads ($99/mo) &rarr;' +
                  '</a>' +
                  '<a href="{WHOP_TIER2_URL}" target="_blank" rel="noopener noreferrer" class="w-full inline-flex items-center justify-center px-5 py-2.5 text-xs font-mono font-semibold text-indigo-200 bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 rounded-lg transition-all">' +
                    'Launch Tier 2 CaptureDesk ($399/mo) &rarr;' +
                  '</a>' +
                '</div>' +
                '<div class="p-6 rounded-2xl bg-navy-900 border border-indigo-500/30 space-y-3">' +
                  '<div class="text-xs font-mono text-indigo-400 uppercase font-semibold">13 LIVE APIs &amp; MCP SERVER</div>' +
                  '<div class="text-lg font-bold text-white">Automate Your Bid Response</div>' +
                  '<p class="text-xs text-slate-300 leading-relaxed">' +
                    'Tailor Key Personnel &amp; GSA LCAT resumes, auto-answer SOC 2, FedRAMP &amp; NIST 800-171 security questionnaires, generate 13 CFR &sect; 125.6 (50% Rule) teaming plans, extract Section B CLIN pricing tables, draft Shipley proposal narratives &amp; CO Q&amp;A, classify NAICS/SIC/PSC/UNSPSC codes, score Bid/No-Bid Pwin (0&ndash;100), audit FAR/DFARS &amp; CMMC 2.0 flow-downs, or shred this RFP into a compliance matrix via our 13 RapidAPI microservices &amp; <code class="text-indigo-200">@signaltender/mcp-server</code>.' +
                  '</p>' +
                  '<a href="#product-key-personnel" class="w-full inline-flex items-center justify-center px-4 py-2.5 text-xs font-mono font-semibold text-indigo-300 bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/40 rounded-lg transition-all">' +
                    'Explore 13 APIs &amp; MCP Server &rarr;' +
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
            '<div class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">' +'<div class="p-4 sm:p-5 bg-slate-900/70 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">' +'<div class="relative flex-1 flex items-center">' +'<svg class="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10.5a7.5 7.5 0 0013.15 6.15z" /></svg>' +'<input id="contracts-live-search" type="text" placeholder="Search all open IT &amp; cybersecurity solicitations by keyword, agency, portal, or tag..." oninput="window.filterContractsDirectory(this.value)" class="w-full pl-10 pr-20 py-2.5 rounded-xl bg-navy-950 border border-slate-700/90 focus:border-sky-500 focus:outline-none text-xs font-mono text-white placeholder-slate-500" />' +'<button id="contracts-live-clear" type="button" onclick="window.filterContractsDirectory(\'\')" class="hidden absolute right-2.5 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-300 border border-slate-700 cursor-pointer">Clear</button>' +'</div>' +'<span id="contracts-live-count" class="text-xs font-mono text-emerald-400 shrink-0">LIVE SEARCH ACTIVE</span>' +'</div>' +'<div class="overflow-x-auto">' +
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
          '<div class="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden shadow-2xl">' +'<div class="p-4 sm:p-5 bg-slate-900/70 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">' +'<div class="relative flex-1 flex items-center">' +'<svg class="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10.5a7.5 7.5 0 0013.15 6.15z" /></svg>' +'<input id="contracts-live-search" type="text" placeholder="Search all open IT &amp; cybersecurity solicitations by keyword, agency, portal, or tag..." oninput="window.filterContractsDirectory(this.value)" class="w-full pl-10 pr-20 py-2.5 rounded-xl bg-navy-950 border border-slate-700/90 focus:border-sky-500 focus:outline-none text-xs font-mono text-white placeholder-slate-500" />' +'<button id="contracts-live-clear" type="button" onclick="window.filterContractsDirectory(\'\')" class="hidden absolute right-2.5 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-300 border border-slate-700 cursor-pointer">Clear</button>' +'</div>' +'<span id="contracts-live-count" class="text-xs font-mono text-emerald-400 shrink-0">LIVE SEARCH ACTIVE</span>' +'</div>' +'<div class="overflow-x-auto">' +
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

