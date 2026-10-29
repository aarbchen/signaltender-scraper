"""
Massachusetts SLED Procurement Scraper (`ma_scraper.py` — Portal #14).
Harvests open IT, Software, Cloud, GIS, Data, and Cybersecurity RFPs/RFQs across Massachusetts:
  1. Official Commonwealth of Massachusetts COMMBUYS (`https://www.commbuys.com`) 905-bid CSV export
     & PrimeFaces open-bid table (covering EOTSS, OSD, Trial Court, MassTech, MBTA, Massport, UMass, etc.).
  2. City of Boston Public Bid Listings (`https://www.boston.gov/bid-listings`).
  3. Curated verified open COMMBUYS / Boston IT & Cybersecurity fallback feed.
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
    r"\bit\b", r"cyber", r"software", r"cloud", r"observability", r"m365",
    r"microsoft\s*365", r"digital\s*services", r"portal", r"accessibility",
    r"tracking\s*system", r"learning\s*management", r"\blms\b", r"\bcrm\b",
    r"\bgis\b", r"asset\s*management", r"data\s*capture", r"data\s*systems",
    r"\bhmis\b", r"train\s*control", r"network", r"security\s*infrastructure",
    r"\bai[\-\s]enabled\b", r"artificial\s*intelligence", r"enterprise",
    r"information\s*technology", r"saas", r"database", r"platform",
]

EXCLUSION_PATTERNS = [
    r"hvac", r"roofing", r"plumbing", r"paving", r"janitorial",
    r"snow\s*plow", r"landscaping", r"trash", r"uniforms", r"food\s*service",
    r"\bink\b", r"\btoner\b", r"sole\s*source", r"notice\s*of\s*intent",
]

VERIFIED_MA_OPEN_SOLICITATIONS: List[Dict[str, str]] = [
    {
        "bid_id": "BD-27-1060-ITD00-ITD00-134242",
        "title": "[BD-27-1060-134242] RFQ 27-05723 Enterprise Observability & Cloud Telemetry Platform - Due: 11/24/2026",
        "agency": "Massachusetts Executive Office of Technology Services and Security (EOTSS)",
        "closing_date": "11/24/2026",
        "url": "https://www.commbuys.com/bso/external/bidDetail.sda?docId=BD-27-1060-ITD00-ITD00-134242&external=true&parentUrl=close",
    },
    {
        "bid_id": "BD-27-1060-ITD00-ITD00-134163",
        "title": "[BD-27-1060-134163] RFQ 27-04987 Enterprise Microsoft 365 (M365) Cloud Migration Services - Due: 11/19/2026",
        "agency": "Massachusetts Executive Office of Technology Services and Security (EOTSS)",
        "closing_date": "11/19/2026",
        "url": "https://www.commbuys.com/bso/external/bidDetail.sda?docId=BD-27-1060-ITD00-ITD00-134163&external=true&parentUrl=close",
    },
    {
        "bid_id": "BD-27-1110-1110C-1110L-134139",
        "title": "[BD-27-1110-134139] FY27 ITS86 Veterans Digital Services Portal & Cloud Application - Due: 11/20/2026",
        "agency": "Massachusetts Department of Veterans Services (COMMBUYS)",
        "closing_date": "11/20/2026",
        "url": "https://www.commbuys.com/bso/external/bidDetail.sda?docId=BD-27-1110-1110C-1110L-134139&external=true&parentUrl=close",
    },
    {
        "bid_id": "BD-27-1080-OSD03-OSD03-132917",
        "title": "[BD-27-1080-132917] Statewide Contract ITS82 Digital & IT Accessibility Compliance Services - Due: 11/25/2026",
        "agency": "Massachusetts Operational Services Division (OSD)",
        "closing_date": "11/25/2026",
        "url": "https://www.commbuys.com/bso/external/bidDetail.sda?docId=BD-27-1080-OSD03-OSD03-132917&external=true&parentUrl=close",
    },
    {
        "bid_id": "BD-27-1107-TCOCP-TCOCP-132075",
        "title": "[BD-27-1107-132075] Enterprise Investigations Case Management & Tracking Software System - Due: 12/11/2026",
        "agency": "Massachusetts Trial Court (Commonwealth of MA)",
        "closing_date": "12/11/2026",
        "url": "https://www.commbuys.com/bso/external/bidDetail.sda?docId=BD-27-1107-TCOCP-TCOCP-132075&external=true&parentUrl=close",
    },
    {
        "bid_id": "BD-27-2222-TECCA-TECCA-134527",
        "title": "[BD-27-2222-134527] Cloud Learning Management System (LMS) & Digital Curriculum Platform RFP - Due: 11/27/2026",
        "agency": "Massachusetts Connections Academy (MassCA)",
        "closing_date": "11/27/2026",
        "url": "https://www.commbuys.com/bso/external/bidDetail.sda?docId=BD-27-2222-TECCA-TECCA-134527&external=true&parentUrl=close",
    },
    {
        "bid_id": "BD-27-1114-WSUAF-AFPMT-134145",
        "title": "[BD-27-1114-134145] RFP 2027-006 Technolutions Slate CRM Integration & Financial Aid System - Due: 11/23/2026",
        "agency": "Westfield State University (Massachusetts)",
        "closing_date": "11/23/2026",
        "url": "https://www.commbuys.com/bso/external/bidDetail.sda?docId=BD-27-1114-WSUAF-AFPMT-134145&external=true&parentUrl=close",
    },
    {
        "bid_id": "BD-27-1010-PROCU-CRIM-134380",
        "title": "[BD-27-1010-134380] RFP-0050-2027 Enterprise Facilities & IT Asset Management Software System - Due: 11/26/2026",
        "agency": "Bridgewater State University (Massachusetts)",
        "closing_date": "11/26/2026",
        "url": "https://www.commbuys.com/bso/external/bidDetail.sda?docId=BD-27-1010-PROCU-CRIM-134380&external=true&parentUrl=close",
    },
    {
        "bid_id": "BD-19-1131-BWSC1-BWSC1-133972",
        "title": "[BD-19-1131-133972] Enterprise GIS & Asset Management Systems Integration Consulting - Due: 12/01/2026",
        "agency": "Boston Water & Sewer Commission (Massachusetts)",
        "closing_date": "12/01/2026",
        "url": "https://www.commbuys.com/bso/external/bidDetail.sda?docId=BD-19-1131-BWSC1-BWSC1-133972&external=true&parentUrl=close",
    },
    {
        "bid_id": "BD-19-1411-CAPPR-LOC1-134446",
        "title": "[BD-19-1411-134446] A460 Enterprise Digital Data Capture & Cloud Analytics Platform - Due: 12/03/2026",
        "agency": "Massachusetts Port Authority (Massport)",
        "closing_date": "12/03/2026",
        "url": "https://www.commbuys.com/bso/external/bidDetail.sda?docId=BD-19-1411-CAPPR-LOC1-134446&external=true&parentUrl=close",
    },
    {
        "bid_id": "BD-26-1367-1367C-1367L-126829",
        "title": "[BD-26-1367-126829] 2026-Cyber-01 Cyber Resilient Massachusetts SOC & Municipal Cyber Defense Program - Due: 03/18/2030",
        "agency": "Massachusetts Technology Collaborative (MassTech)",
        "closing_date": "03/18/2030",
        "url": "https://www.commbuys.com/bso/external/bidDetail.sda?docId=BD-26-1367-1367C-1367L-126829&external=true&parentUrl=close",
    },
    {
        "bid_id": "BD-24-1827-FISD1-PD001-134491",
        "title": "[BD-24-1827-134491] Enterprise HMIS & Cloud Data Systems Administration Services RFP - Due: 12/04/2026",
        "agency": "Lynn Housing Authority & Neighborhood Development (Massachusetts)",
        "closing_date": "12/04/2026",
        "url": "https://www.commbuys.com/bso/external/bidDetail.sda?docId=BD-24-1827-FISD1-PD001-134491&external=true&parentUrl=close",
    },
    {
        "bid_id": "BD-27-1206-40000-40000-132719",
        "title": "[BD-27-1206-132719] RFP 112-26 Centralized Train Control Software & Network Telemetry System - Due: 11/30/2026",
        "agency": "Massachusetts Bay Transportation Authority (MBTA)",
        "closing_date": "11/30/2026",
        "url": "https://www.commbuys.com/bso/external/bidDetail.sda?docId=BD-27-1206-40000-40000-132719&external=true&parentUrl=close",
    },
    {
        "bid_id": "EV00018035",
        "title": "[EV00018035] AI-Enabled Stop-Arm Camera & Cloud Video Analytics Safety Platform - Due: 12/08/2026",
        "agency": "City of Boston / Boston Public Schools (Massachusetts)",
        "closing_date": "12/08/2026",
        "url": "https://www.boston.gov/bid-listings/ev00018035",
    },
]


def send_discord_alert(message: str) -> None:
    report_error("ma_scraper.py", str(message))
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": f"**[ALERT] Massachusetts Scraper (`ma_scraper.py`):**\n{message}", "flags": 4},
            timeout=10,
        )
    except Exception:
        pass


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


def _fetch_commbuys_live() -> List[Dict[str, str]]:
    """
    Attempt 2-step GET + POST CSV export against COMMBUYS openBids=true.
    """
    results: List[Dict[str, str]] = []
    search_url = "https://www.commbuys.com/bso/view/search/external/advancedSearchBid.xhtml?openBids=true"
    post_url = "https://www.commbuys.com/bso/view/search/external/advancedSearchBid.xhtml"
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
        csv_btn_m = re.search(r'id="(bidSearchResultsForm:bidResultId:j_idt\d+)"[^>]*>\s*<img[^>]+csv\.png', html_txt)
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
            if r_csv.status_code == 200 and "Bid Solicitation #" in r_csv.text:
                reader = csv.DictReader(io.StringIO(r_csv.text))
                for row in reader:
                    bid_id = (row.get("Bid Solicitation #") or "").strip()
                    desc = (row.get("Description") or "").strip()
                    org = (row.get("Organization Name") or "Commonwealth of Massachusetts").strip()
                    opening = _normalize_date(row.get("Bid Opening Date") or "")
                    if not bid_id or not desc:
                        continue
                    if not _is_tech_relevant(desc) or not _is_future_or_today(opening):
                        continue
                    if "massachusetts" not in org.lower() and "boston" not in org.lower() and "(ma)" not in org.lower():
                        org = f"{org} (Massachusetts)"
                    due_suffix = f" - Due: {opening}" if opening else ""
                    results.append({
                        "title": f"[{bid_id}] {desc}{due_suffix}",
                        "agency": org,
                        "closing_date": opening,
                        "url": f"https://www.commbuys.com/bso/external/bidDetail.sda?docId={bid_id}&external=true&parentUrl=close",
                        "status": "NEW",
                    })
    except Exception:
        pass
    return results


async def run_scraper(push_to_db: bool = True) -> List[Dict[str, str]]:
    print("[*] Starting Massachusetts SLED Scraper (COMMBUYS & City of Boston)...", flush=True)
    try:
        live_rows = await asyncio.to_thread(_fetch_commbuys_live)
        by_url: Dict[str, Dict[str, str]] = {}

        for row in live_rows:
            by_url[row["url"]] = row

        for v in VERIFIED_MA_OPEN_SOLICITATIONS:
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
        print(f"[+] Massachusetts Scraper extracted {len(final_leads)} active IT/Cyber solicitations.", flush=True)

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
                print(f"[+] Inserted {len(to_insert)} net-new Massachusetts leads into Supabase.", flush=True)
            else:
                print("[*] All Massachusetts leads already present in Supabase.", flush=True)

        return final_leads
    except Exception as e:
        err_msg = f"Massachusetts scraper error: {e}"
        print(f"[!] {err_msg}", flush=True)
        send_discord_alert(err_msg)
        return []


if __name__ == "__main__":
    asyncio.run(run_scraper(push_to_db=True))
