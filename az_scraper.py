"""
Arizona State SLED Procurement Scraper (`az_scraper.py` — Portal #19).
Harvests open IT, Software, Cloud, Data, Identity, Network, and Cybersecurity RFPs/RFQs/RFIs across Arizona:
  1. Official Arizona Procurement Portal (APP / Procure.AZ.gov) public RFx browse grid
     (`https://app.az.gov/page.aspx/en/rfp/request_browse_public`) — the same Ivalua/Periscope
     `page.aspx ... request_browse_public` platform used by Maryland eMMA and OhioBuys. Covers ADOA State
     Procurement Office (SPO), ADOA-ASET (Arizona Strategic Enterprise Technology), ADOT, ADOR, DES, AHCCCS,
     ADHS, DPS, and cooperative APP members (City of Chandler, Salt River Pima-Maricopa Indian Community, etc.).
  2. Robust fallback: when APP is unreachable (Cloudflare / reCAPTCHA browser_check / timeout), the scraper
     replays the last successful live harvest from `az_leads_cache.json` (still-open solicitations only).
     It never fabricates solicitations; if both the live grid and the cache are empty it returns [] so that
     `mainscraper.py` can run its 3-Tier Selector-Free Open-Data / LLM fallback.
Enforces RLS-safe `SELECT` + `.insert()` on Supabase `contracts` (never an upsert) and closed-loop error telemetry.
"""

from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()

import asyncio
import html
import json
import os
import re
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
TABLE_NAME = "contracts"
ERROR_LOG_PATH = "error_log.txt"

APP_BASE_URL = "https://app.az.gov"
APP_BROWSE_URL = f"{APP_BASE_URL}/page.aspx/en/rfp/request_browse_public"
APP_DETAIL_URL_TMPL = APP_BASE_URL + "/page.aspx/en/bpm/process_manage_extranet/{rfx_id}"
GRID_ID = "body_x_grid_grd"
MAX_PAGES = 15  # APP lists ~150 public RFx (15 per page); hard cap protects Render cron runtime
AZ_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "az_leads_cache.json")

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TECH_PATTERNS = [
    r"\bit\b", r"cyber", r"software", r"cloud", r"zero\s*trust",
    r"siem", r"\bsoc\b", r"application", r"modernization", r"\berp\b",
    r"data\s*warehouse", r"fhir", r"interoperability", r"telemetry",
    r"sd[\-\s]?wan", r"identity", r"\bicam\b", r"fraud\s*detection",
    r"\bai\b", r"artificial\s*intelligence", r"cmmc", r"\bnist\b",
    r"case\s*management", r"saas", r"contact\s*center", r"network",
    r"cybersecurity", r"database", r"platform", r"information\s*technology",
    r"biometric", r"itsm", r"esinet", r"\bngcs\b", r"next\s*gen(eration)?\s*911",
    r"telecommunication", r"document\s*management", r"\bedms\b", r"digital",
    r"\bgis\b", r"\bweb\b", r"portal", r"automation", r"\bapi\b", r"analytics",
    r"verification\s*and\s*validation", r"\biv&v\b", r"\bcrm\b", r"data\s*center",
    r"migration", r"authentication", r"cognito", r"\baws\b", r"azure", r"broadband",
]

# APP "Commodity" (NIGP/UNSPSC) column — narrower, high-precision IT signals
TECH_COMMODITY_PATTERNS = [
    r"software", r"computer", r"information\s*technology", r"data\s*processing",
    r"telecommunication", r"network", r"internet", r"cyber", r"cloud",
    r"biometric", r"systems?\s*integration", r"it\s*consult", r"database",
]

EXCLUSION_PATTERNS = [
    r"hvac", r"roofing", r"plumbing", r"paving", r"janitorial",
    r"snow\s*plow", r"towing\s*services", r"landscap", r"trash",
    r"uniforms", r"food\s*storage", r"auctioneer", r"fish\s*food", r"trout",
    r"\bink\b", r"\btoner\b", r"sole\s*source", r"notice\s*of\s*intent",
    r"cancel+ed", r"demolition", r"tires?\b", r"pest\s*control", r"veterinary",
    r"satellite\s*television", r"street\s*sweeping", r"septic", r"fertilizer",
    r"pool\s*chemicals", r"wastewater", r"kitchen", r"columbarium",
    r"job\s*order\s*contracting",
]


def send_discord_alert(message: str) -> None:
    report_error("az_scraper.py", str(message))
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n[!] az_scraper.py: {message}\n")
    except Exception:
        pass
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": f"**[ALERT] Arizona Scraper (`az_scraper.py`):**\n{message}", "flags": 4},
            timeout=10,
        )
    except Exception:
        pass


def _clean_text(raw: str) -> str:
    """Strip tags, unescape entities, repair APP mojibake (smart quotes / dashes), collapse whitespace."""
    s = re.sub(r"<[^>]+>", " ", str(raw or ""))
    s = html.unescape(s)
    # APP occasionally double-encodes Windows-1252 smart punctuation (U+FFFD + C1 control bytes)
    s = re.sub(r"(?<=\w)[\ufffd\u0080-\u009f]+(?=[st]\b)", "'", s)
    s = re.sub(r"[\ufffd\u0080-\u009f]+", " - ", s)
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("\xa0", " ")
    s = re.sub(r"\s+-\s+-\s+", " - ", s)
    return re.sub(r"\s+", " ", s).strip()


def _dedupe_repeated_phrase(text: str) -> str:
    """APP renders hierarchical org cells like 'City of Chandler City of Chandler' — keep one copy."""
    t = _clean_text(text)
    m = re.match(r"^(.+?)(?:\s+\1)+$", t)
    if m:
        return m.group(1).strip()
    words = t.split()
    for size in range(len(words) // 2, 1, -1):
        head = " ".join(words[:size])
        if t.startswith(head + " " + head):
            return head
    return t


def _parse_app_date(raw: str) -> str:
    """Normalize APP 'M/D/YYYY h:mm:ss AM' (UTC-7) to MM/DD/YYYY."""
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(raw or ""))
    if not m:
        return ""
    month, day, year = m.groups()
    return f"{int(month):02d}/{int(day):02d}/{year}"


def _is_future_or_today(mmddyyyy: str) -> bool:
    if not mmddyyyy:
        return True
    try:
        return datetime.strptime(mmddyyyy, "%m/%d/%Y").date() >= date.today()
    except Exception:
        return True


def _is_tech_relevant(title: str, commodity: str = "") -> bool:
    t = str(title or "").lower()
    c = str(commodity or "").lower()
    if any(re.search(ex, t) for ex in EXCLUSION_PATTERNS):
        return False
    if any(re.search(pat, t) for pat in TECH_PATTERNS):
        return True
    return bool(c) and any(re.search(pat, c) for pat in TECH_COMMODITY_PATTERNS)


def _extract_form_fields(page_html: str) -> Dict[str, str]:
    """Collect all postable ASP.NET/Ivalua form fields (hidden state + grid inputs) from the APP browse page."""
    fields: Dict[str, str] = {}
    start = page_html.find('<form method="post"')
    if start < 0:
        start = page_html.find("<form")
    form_html = page_html[start: page_html.find("</form>", start)] if start >= 0 else page_html
    for m in re.finditer(r"<input\b([^>]*)>", form_html, re.S | re.I):
        attrs = m.group(1)
        name_m = re.search(r"\bname=['\"]([^'\"]+)['\"]", attrs)
        if not name_m:
            continue
        type_m = re.search(r"\btype=['\"]([^'\"]+)['\"]", attrs)
        input_type = type_m.group(1).lower() if type_m else "text"
        if input_type in ("submit", "button", "image", "file"):
            continue
        if input_type in ("checkbox", "radio") and "checked" not in attrs.lower():
            continue
        value_m = re.search(r"\bvalue=['\"]([^'\"]*)['\"]", attrs)
        fields[html.unescape(name_m.group(1))] = html.unescape(value_m.group(1)) if value_m else ""
    return fields


def _grid_header_keys(page_html: str) -> List[str]:
    return re.findall(rf'<th id="{GRID_ID}__ctl0_([^"]+)"', page_html)


def _parse_grid_rows(page_html: str) -> List[Dict[str, str]]:
    """Parse the Ivalua `body_x_grid_grd` table: Code | Label | Commodity | Agency | Status | Begin | End."""
    grid_start = page_html.find(f'id="{GRID_ID}"')
    if grid_start < 0:
        return []
    grid_html = page_html[grid_start:]
    headers = _grid_header_keys(grid_html)
    tb_start = grid_html.find("<tbody")
    if tb_start < 0:
        return []
    body = grid_html[tb_start: grid_html.find("</tbody>", tb_start)]

    def _col(name_fragment: str, fallback_idx: int) -> int:
        for i, h in enumerate(headers):
            if name_fragment.lower() in h.lower():
                return i
        return fallback_idx

    idx_code = _col("BpmCode", 1)
    idx_label = _col("colLabel", 2)
    idx_commodity = _col("colFamily", 4)
    idx_agency = _col("selActCode", 5)
    idx_status = _col("selStatusCode", 7)
    idx_end = _col("colEndDate", 11)

    rows: List[Dict[str, str]] = []
    for tr_m in re.finditer(r"<tr\b[^>]*>(.*?)</tr>", body, re.S):
        tr_html = tr_m.group(1)
        cells = [_clean_text(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", tr_html, re.S)]
        if len(cells) < 6:
            continue
        id_m = re.search(r"/bpm/process_manage_extranet/(\d+)", tr_html) or re.search(rf"{GRID_ID}_tr_(\d+)_", tr_html)
        if not id_m:
            continue

        def _cell(i: int) -> str:
            return cells[i] if 0 <= i < len(cells) else ""

        rows.append(
            {
                "rfx_id": id_m.group(1),
                "code": _cell(idx_code),
                "label": _cell(idx_label),
                "commodity": _cell(idx_commodity),
                "agency": _dedupe_repeated_phrase(_cell(idx_agency)),
                "status": _cell(idx_status),
                "end_date": _parse_app_date(_cell(idx_end)),
            }
        )
    return rows


def _max_page_index(page_html: str) -> int:
    m = re.search(rf"maxpageindex{GRID_ID}'[^>]*value='(\d+)'", page_html)
    if not m:
        m = re.search(rf'maxpageindex{GRID_ID}"[^>]*value="(\d+)"', page_html)
    try:
        return int(m.group(1)) if m else 0
    except Exception:
        return 0


def _is_blocked(resp: requests.Response) -> bool:
    return (
        resp.status_code in (403, 429, 503)
        or "browser_check" in str(resp.url)
        or "Just a moment..." in resp.text[:3000]
    )


def _fetch_app_grid_live() -> Tuple[List[Dict[str, str]], Optional[str]]:
    """
    Page through the public APP RFx grid via plain HTTP form postbacks (no Chromium -> zero OOM risk on Render).
    Returns (rows, error_message_or_None).
    """
    session = requests.Session()
    try:
        first = session.get(APP_BROWSE_URL, headers=HTTP_HEADERS, timeout=30)
        first.encoding = "utf-8"
    except Exception as e:
        return [], f"APP browse request failed: {e}"
    if _is_blocked(first):
        return [], f"APP browse blocked (HTTP {first.status_code}, url={first.url})"
    if first.status_code != 200 or f'id="{GRID_ID}"' not in first.text:
        return [], f"APP browse returned HTTP {first.status_code} without RFx grid"

    all_rows = _parse_grid_rows(first.text)
    max_idx = min(_max_page_index(first.text), MAX_PAGES - 1)
    current_html = first.text
    post_headers = {**HTTP_HEADERS, "Referer": APP_BROWSE_URL, "Origin": APP_BASE_URL}

    for page_idx in range(1, max_idx + 1):
        fields = _extract_form_fields(current_html)
        fields[f"hdnCurrentPageIndex{GRID_ID}"] = str(page_idx)
        fields["__EVENTTARGET"] = f"body:x:grid:gridPagerBtn{page_idx}Page"
        fields["__EVENTARGUMENT"] = ""
        try:
            resp = session.post(APP_BROWSE_URL, data=fields, headers=post_headers, timeout=30)
            resp.encoding = "utf-8"
        except Exception as e:
            print(f"[!] Arizona APP page {page_idx + 1} request failed: {e}", flush=True)
            break
        if _is_blocked(resp) or resp.status_code != 200:
            print(f"[!] Arizona APP page {page_idx + 1} blocked/failed (HTTP {resp.status_code}); keeping {len(all_rows)} rows.", flush=True)
            break
        page_rows = _parse_grid_rows(resp.text)
        if not page_rows:
            break
        all_rows.extend(page_rows)
        current_html = resp.text

    unique = list({r["rfx_id"]: r for r in all_rows}.values())
    print(f"[*] Arizona APP grid: parsed {len(unique)} public RFx rows across {max_idx + 1} page(s).", flush=True)
    return unique, None


def _row_to_lead(row: Dict[str, str]) -> Optional[Dict[str, str]]:
    label = row.get("label") or ""
    if not label:
        return None
    status = (row.get("status") or "").lower()
    if status and not any(k in status for k in ("open", "bidding", "published", "active")):
        return None
    closing = row.get("end_date") or ""
    if not _is_future_or_today(closing):
        return None
    if not _is_tech_relevant(label, row.get("commodity") or ""):
        return None
    code = (row.get("code") or row.get("rfx_id") or "").strip()
    agency_raw = row.get("agency") or "State of Arizona"
    agency = f"{agency_raw} (Arizona APP / Procure.AZ.gov)"
    title = f"[AZ-{code}] {label}" if code else f"[AZ] {label}"
    if closing:
        title = f"{title} - Due: {closing}"
    return {
        "title": title,
        "agency": agency,
        "closing_date": closing or None,
        "url": APP_DETAIL_URL_TMPL.format(rfx_id=row["rfx_id"]),
        "status": "NEW",
    }


def _load_cached_leads() -> List[Dict[str, str]]:
    try:
        with open(AZ_CACHE_PATH, "r", encoding="utf-8") as f:
            cached = json.load(f)
        leads = cached.get("leads", []) if isinstance(cached, dict) else cached
        return [
            lead for lead in (leads or [])
            if isinstance(lead, dict) and lead.get("url") and _is_future_or_today(str(lead.get("closing_date") or ""))
        ]
    except Exception:
        return []


def _save_cached_leads(leads: List[Dict[str, str]]) -> None:
    try:
        with open(AZ_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {"harvested_at": datetime.now().isoformat(timespec="seconds"), "source": APP_BROWSE_URL, "leads": leads},
                f,
                indent=2,
                ensure_ascii=False,
            )
    except Exception:
        pass


async def run_scraper(push_to_db: bool = True) -> List[Dict[str, str]]:
    print("[*] Starting Arizona SLED Scraper (Arizona APP Procure.AZ.gov & ADOA-ASET)...", flush=True)
    try:
        grid_rows, live_err = await asyncio.to_thread(_fetch_app_grid_live)
        by_url: Dict[str, Dict[str, str]] = {}

        for row in grid_rows:
            lead = _row_to_lead(row)
            if lead:
                by_url[lead["url"]] = lead

        if grid_rows:
            # Live grid reachable: refresh the cache (even with 0 tech matches) so fallback never replays stale data
            _save_cached_leads(list(by_url.values()))
        else:
            cached = _load_cached_leads()
            msg = f"Arizona APP live harvest unavailable ({live_err or 'empty grid'}); replaying {len(cached)} cached open lead(s)."
            print(f"[!] {msg}", flush=True)
            if not cached:
                send_discord_alert(msg)
            for lead in cached:
                by_url.setdefault(lead["url"], lead)

        final_leads = list(by_url.values())
        print(f"[+] Arizona Scraper extracted {len(final_leads)} active IT/Cyber solicitations.", flush=True)

        if push_to_db and final_leads and SUPABASE_URL and SUPABASE_KEY:
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            existing_resp = supabase.table(TABLE_NAME).select("url,title").execute()
            existing_urls = {r.get("url") for r in (existing_resp.data or []) if r.get("url")}
            existing_titles = {r.get("title") for r in (existing_resp.data or []) if r.get("title")}

            to_insert = [
                item for item in final_leads
                if item["url"] not in existing_urls and item["title"] not in existing_titles
            ]
            if to_insert:
                supabase.table(TABLE_NAME).insert(to_insert).execute()
                print(f"[+] Inserted {len(to_insert)} net-new Arizona leads into Supabase.", flush=True)
            else:
                print("[*] All Arizona leads already present in Supabase.", flush=True)

        return final_leads
    except Exception as e:
        err_msg = f"Arizona scraper error: {e}"
        print(f"[!] {err_msg}", flush=True)
        send_discord_alert(err_msg)
        return []


if __name__ == "__main__":
    asyncio.run(run_scraper(push_to_db=True))
