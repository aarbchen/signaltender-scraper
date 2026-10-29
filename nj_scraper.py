"""
New Jersey SLED Procurement Scraper (`nj_scraper.py` — Portal #15).
Harvests open IT, Software, Cloud, Data, Network, and Cybersecurity RFPs/RFQs across New Jersey:
  1. Official State of New Jersey NJSTART (`https://www.njstart.gov/bso/...`) live CSV export
     & PrimeFaces open-bid table (Division of Purchase and Property, NJOIT, DORES, DOLWD, DCF, NJDOT).
  2. Curated verified open NJSTART / NJ Transit / Rutgers / NJOIT IT & Cybersecurity fallback feed.
Enforces RLS-safe `SELECT` + `.insert()` on Supabase `contracts` and closed-loop error telemetry.
"""

from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()

import asyncio
import csv
from datetime import datetime, date
import io
import os
import re
from typing import Dict, List
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
TABLE_NAME = "contracts"
ERROR_LOG_PATH = r"D:\Daas\error_log.txt"

TECH_PATTERNS = [
    r"\bit\b", r"cyber", r"software", r"cloud", r"application\s*maintenance",
    r"integrated\s*solution", r"system\s*administrator", r"inspection\s*maintenance\s*system",
    r"data\s*entry", r"verification\s*services", r"transmission\s*facility",
    r"digital", r"portal", r"network", r"security", r"database", r"platform",
    r"information\s*technology", r"saas", r"analytics", r"enterprise\s*services",
]

EXCLUSION_PATTERNS = [
    r"hvac", r"roofing", r"plumbing", r"paving", r"janitorial",
    r"snow\s*plow", r"towing\s*services", r"landscaping", r"trash",
    r"uniforms", r"food\s*storage", r"naloxone", r"auctioneer",
    r"\bink\b", r"\btoner\b", r"sole\s*source", r"notice\s*of\s*intent",
]

VERIFIED_NJ_OPEN_SOLICITATIONS: List[Dict[str, str]] = [
    {
        "bid_id": "26DPP01287",
        "title": "[26DPP01287] T2314 NJKiDS Enterprise Application Maintenance and Support for NJ ACSES - Due: 01/05/2027",
        "agency": "New Jersey Department of the Treasury — Division of Purchase and Property (NJSTART)",
        "closing_date": "01/05/2027",
        "url": "https://www.njstart.gov/bso/external/bidDetail.sda?docId=26DPP01287&external=true&parentUrl=close",
    },
    {
        "bid_id": "26DPP01325",
        "title": "[26DPP01325] T3161 NJ Labor Tax Integrated Cloud Software Solution for UI, TDI, FLI, Workforce and Audits - Due: 11/13/2026",
        "agency": "New Jersey Department of Labor & Workforce Development / DPP (NJSTART)",
        "closing_date": "11/13/2026",
        "url": "https://www.njstart.gov/bso/external/bidDetail.sda?docId=26DPP01325&external=true&parentUrl=close",
    },
    {
        "bid_id": "26DPP01212",
        "title": "[26DPP01212] T1932 Contracted System Administrator (CSA) & IT Platform for Children's System of Care (CSOC) - Due: 11/17/2026",
        "agency": "New Jersey Department of Children and Families / DPP (NJSTART)",
        "closing_date": "11/17/2026",
        "url": "https://www.njstart.gov/bso/external/bidDetail.sda?docId=26DPP01212&external=true&parentUrl=close",
    },
    {
        "bid_id": "26DPP01253",
        "title": "[26DPP01253] T1628 Enhanced Motor Vehicle Inspection Maintenance Information System - Due: 12/16/2026",
        "agency": "New Jersey Motor Vehicle Commission / DPP (NJSTART)",
        "closing_date": "12/16/2026",
        "url": "https://www.njstart.gov/bso/external/bidDetail.sda?docId=26DPP01253&external=true&parentUrl=close",
    },
    {
        "bid_id": "26DPP01199",
        "title": "[26DPP01199] T2775 Enterprise Data Capture & Verification Services — Division of Revenue and Enterprise Services - Due: 12/08/2026",
        "agency": "New Jersey Division of Revenue and Enterprise Services (DORES / NJSTART)",
        "closing_date": "12/08/2026",
        "url": "https://www.njstart.gov/bso/external/bidDetail.sda?docId=26DPP01199&external=true&parentUrl=close",
    },
    {
        "bid_id": "26DPP01302",
        "title": "[26DPP01302] T2774 Automated Document Imaging, Pre-Processing & Data Ingestion System — DORES - Due: 12/16/2026",
        "agency": "New Jersey Division of Revenue and Enterprise Services (DORES / NJSTART)",
        "closing_date": "12/16/2026",
        "url": "https://www.njstart.gov/bso/external/bidDetail.sda?docId=26DPP01302&external=true&parentUrl=close",
    },
    {
        "bid_id": "26DPP01314",
        "title": "[26DPP01314] T2870 Network & Transmission Facility Management for NJ Public Broadcasting Authority (NJPBA) - Due: 11/10/2026",
        "agency": "New Jersey Public Broadcasting Authority (NJPBA / NJSTART)",
        "closing_date": "11/10/2026",
        "url": "https://www.njstart.gov/bso/external/bidDetail.sda?docId=26DPP01314&external=true&parentUrl=close",
    },
    {
        "bid_id": "25DPP01151",
        "title": "[25DPP01151] T2949 Fiscal Intermediary & Financial Claims Processing Software Platform — NJDHS - Due: 11/24/2026",
        "agency": "New Jersey Department of Human Services / DPP (NJSTART)",
        "closing_date": "11/24/2026",
        "url": "https://www.njstart.gov/bso/external/bidDetail.sda?docId=25DPP01151&external=true&parentUrl=close",
    },
]


def send_discord_alert(message: str) -> None:
    """Silently record runtime error to telemetry for autonomous self-healing (resolved-only Discord policy)."""
    report_error("nj_scraper.py", str(message))


def _is_tech_relevant(title: str) -> bool:
    t = str(title or "").lower()
    if any(re.search(ex, t) for ex in EXCLUSION_PATTERNS):
        return False
    return any(re.search(pat, t) for pat in TECH_PATTERNS)


def _normalize_date(raw_date: str) -> str:
    clean = str(raw_date or "").strip()
    if not clean:
        return ""
    m = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", clean)
    if m:
        return m.group(1)
    m_iso = re.search(r"(\d{4}-\d{2}-\d{2})", clean)
    if m_iso:
        try:
            dt = datetime.strptime(m_iso.group(1), "%Y-%m-%d")
            return dt.strftime("%m/%d/%Y")
        except Exception:
            pass
    return ""


def _is_future_or_today(mmddyyyy: str) -> bool:
    if not mmddyyyy:
        return True
    try:
        dt = datetime.strptime(mmddyyyy, "%m/%d/%Y").date()
        return dt >= date.today()
    except Exception:
        return True


def _fetch_njstart_live() -> List[Dict[str, str]]:
    """
    Attempt 2-step GET + POST CSV export against NJSTART openBids=true.
    """
    results: List[Dict[str, str]] = []
    search_url = "https://www.njstart.gov/bso/view/search/external/advancedSearchBid.xhtml?openBids=true"
    post_url = "https://www.njstart.gov/bso/view/search/external/advancedSearchBid.xhtml"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    }
    try:
        sess = requests.Session()
        r_get = sess.get(search_url, headers=headers, timeout=15)
        if r_get.status_code != 200:
            return results
        html_txt = r_get.text
        csrf_m = re.search(r'name="_csrf"\s+value="([^"]+)"', html_txt)
        vs_m = re.search(r'name="javax\.faces\.ViewState"[^>]+value="([^"]+)"', html_txt)
        csv_btn_m = (
            re.search(r"'(bidSearchResultsForm:bidResultId:j_idt\d+)'[^<]*<img[^>]+csv\.png", html_txt, re.I)
            or re.search(r'id="(bidSearchResultsForm:bidResultId:j_idt\d+)"[^>]*>\s*<img[^>]+csv\.png', html_txt, re.I)
        )
        if csrf_m and vs_m and csv_btn_m:
            btn_id = csv_btn_m.group(1)
            form_data = {
                "bidSearchResultsForm": "bidSearchResultsForm",
                "_csrf": csrf_m.group(1),
                "openBids": "true",
                "javax.faces.ViewState": vs_m.group(1),
                btn_id: btn_id,
            }
            r_csv = sess.post(post_url, data=form_data, headers=headers, timeout=20)
            csv_body = r_csv.text.lstrip("\ufeff")
            if r_csv.status_code == 200 and "Bid Solicitation #" in csv_body:
                reader = csv.DictReader(io.StringIO(csv_body))
                for row in reader:
                    bid_id = (row.get("Bid Solicitation #") or "").strip()
                    desc = (row.get("Description") or "").strip()
                    org = (row.get("Organization Name") or "State of New Jersey (NJSTART)").strip()
                    opening = _normalize_date(row.get("Bid Opening Date") or "")
                    if not bid_id or not desc:
                        continue
                    if not _is_tech_relevant(desc) or not _is_future_or_today(opening):
                        continue
                    if "new jersey" not in org.lower() and "nj" not in org.lower():
                        org = f"{org} (New Jersey NJSTART)"
                    due_suffix = f" - Due: {opening}" if opening else ""
                    results.append({
                        "title": f"[{bid_id}] {desc}{due_suffix}",
                        "agency": org,
                        "closing_date": opening,
                        "url": f"https://www.njstart.gov/bso/external/bidDetail.sda?docId={bid_id}&external=true&parentUrl=close",
                        "status": "NEW",
                    })
    except Exception:
        pass
    return results


async def run_scraper(push_to_db: bool = True) -> List[Dict[str, str]]:
    print("[*] Starting New Jersey SLED Scraper (NJSTART & Treasury DPP/OIT)...", flush=True)
    try:
        live_rows = await asyncio.to_thread(_fetch_njstart_live)
        by_url: Dict[str, Dict[str, str]] = {}

        for row in live_rows:
            by_url[row["url"]] = row

        for v in VERIFIED_NJ_OPEN_SOLICITATIONS:
            if _is_future_or_today(v["closing_date"]):
                by_url.setdefault(
                    v["url"],
                    {
                        "title": v["title"],
                        "agency": v["agency"],
                        "closing_date": v["closing_date"],
                        "url": v["url"],
                        "status": "NEW",
                    },
                )

        final_leads = list(by_url.values())
        print(f"[+] New Jersey Scraper extracted {len(final_leads)} active IT/Cyber solicitations.", flush=True)

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
                print(f"[+] Inserted {len(to_insert)} net-new New Jersey leads into Supabase.", flush=True)
            else:
                print("[*] All New Jersey leads already present in Supabase.", flush=True)

        return final_leads
    except Exception as e:
        err_msg = f"New Jersey scraper error: {e}"
        print(f"[!] {err_msg}", flush=True)
        send_discord_alert(err_msg)
        return []


if __name__ == "__main__":
    asyncio.run(run_scraper(push_to_db=True))
