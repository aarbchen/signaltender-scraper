import os
import csv
import re
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
SITE_BASE_URL = os.getenv("SIGNALTENDER_SITE_URL", "https://signaltender.net").rstrip("/")

# Optional Zero-Touch Cold Email API Credentials (Option C)
INSTANTLY_API_KEY = os.getenv("INSTANTLY_API_KEY")
INSTANTLY_CAMPAIGN_ID = os.getenv("INSTANTLY_CAMPAIGN_ID")
SMARTLEAD_API_KEY = os.getenv("SMARTLEAD_API_KEY")
SMARTLEAD_CAMPAIGN_ID = os.getenv("SMARTLEAD_CAMPAIGN_ID")

TABLE_NAME = "contracts"
ERROR_LOG_PATH = r"D:\Daas\error_log.txt"

# Tech filter regex array as per project_rules.md data integrity protocol
tech_keywords = [
    r"\bit\b", r"cyber(security)?", r"software", r"network", r"computer",
    r"server", r"infosec", r"audio/visual", r"hardware",
    r"technology", r"cloud", r"broadband", r"telecom", r"fiber",
    r"saas", r"data", r"system", r"digital", r"platform", r"web", r"infrastructure"
]

# Commodity IT & low-value renewal exclusions
commodity_it_exclusions = [
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

STATE_ALIASES = {
    "tx": "tx", "texas": "tx",
    "va": "va", "virginia": "va",
    "ca": "ca", "california": "ca",
    "fl": "fl", "florida": "fl",
    "md": "md", "maryland": "md",
}


def send_discord_alert(message: str):
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": f"🚨 **Outreach Generator Alert:**\n{message}"},
            timeout=10,
        )
        response.raise_for_status()
    except Exception as e:
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"Failed to send Discord alert in outreach_generator.py: {e}\n")
        except Exception:
            pass


def parse_contract_date(date_str: str, title: str = "") -> date | None:
    """Parse MM/DD/YYYY or YYYY-MM-DD from closing_date or '- Due: MM/DD/YYYY' in title."""
    candidates = [str(date_str or "").strip()]
    m_title = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", str(title or ""), flags=re.IGNORECASE)
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


def is_contract_open(rec: dict, today: date | None = None) -> bool:
    """Return True if the contract has no closing date or its closing date is >= today."""
    ref_date = today or datetime.now().date()
    dt = parse_contract_date(rec.get("closing_date") or "", rec.get("title") or "")
    if dt is None:
        return True
    return dt >= ref_date


def detect_contract_region(rec: dict) -> str:
    """Classify a Supabase contract record into 'tx', 'va', 'ca', 'fl', 'md', 'fed', or 'other'."""
    url = str(rec.get("url") or "").lower()
    agency = str(rec.get("agency") or "").lower()
    title = str(rec.get("title") or "")
    if title.startswith("[TX]") or "txsmartbuy" in url or "texas" in agency:
        return "tx"
    if title.startswith("[VA]") or "cgieva.com" in url or "eva.virginia.gov" in url or "virginia" in agency:
        return "va"
    if title.startswith("[CA]") or "caleprocure.ca.gov" in url or "california" in agency:
        return "ca"
    if title.startswith("[FL]") or "myfloridamarketplace.com" in url or "florida" in agency:
        return "fl"
    if title.startswith("[MD]") or "maryland" in url or "bonfirehub.com" in url or "maryland" in agency or "prince george" in agency or "howard county" in agency:
        return "md"
    if "sam.gov" in url:
        return "fed"
    return "other"


def format_contract_line(index: int, rec: dict) -> str:
    """Format a single contract row without duplicating '- Due: MM/DD/YYYY'."""
    title = str(rec.get("title") or "Unspecified Contract").strip()
    agency = str(rec.get("agency") or "Public Agency").strip()
    closing_date = str(rec.get("closing_date") or "").strip()

    if "due:" in title.lower():
        return f"{index}. {title} - {agency}\n"
    elif closing_date and closing_date.lower() not in ["n/a", "none", "null", "tbd"]:
        return f"{index}. {title} - {agency} (Due: {closing_date})\n"
    else:
        return f"{index}. {title} - {agency}\n"


def select_contracts_for_prospect(all_contracts: list[dict], prospect_state: str, max_count: int = 3) -> list[dict]:
    """
    Prioritize contracts matching the prospect's state + Federal (SAM.gov) contracts,
    then backfill with the freshest remaining B2B IT contracts up to max_count.
    """
    norm_state = STATE_ALIASES.get(str(prospect_state or "").strip().lower(), "")
    if not norm_state:
        return all_contracts[:max_count]

    state_matches = [c for c in all_contracts if detect_contract_region(c) == norm_state]
    fed_matches = [c for c in all_contracts if detect_contract_region(c) == "fed"]
    other_matches = [c for c in all_contracts if detect_contract_region(c) not in (norm_state, "fed")]

    combined = state_matches + fed_matches + other_matches
    return combined[:max_count]


def sync_leads_to_cold_email_api(leads_payload: list[dict]) -> None:
    """
    Option C: Zero-Touch Cold Email API Sync.
    Automatically pushes generated leads directly to Instantly.ai or Smartlead.ai
    when INSTANTLY_API_KEY/INSTANTLY_CAMPAIGN_ID or SMARTLEAD_API_KEY/SMARTLEAD_CAMPAIGN_ID
    are configured in .env.
    """
    if not leads_payload:
        return

    # 1. Instantly.ai REST API Integration
    if INSTANTLY_API_KEY and INSTANTLY_CAMPAIGN_ID:
        try:
            print(f"[*] Pushing {len(leads_payload)} leads directly to Instantly.ai campaign {INSTANTLY_CAMPAIGN_ID}...", flush=True)
            instantly_leads = [
                {
                    "email": item["Email"],
                    "first_name": item["First Name"],
                    "company_name": item["Company"],
                    "custom_variables": {
                        "subject_line": item["Subject Line"],
                        "email_body": item["Email Body"],
                    },
                }
                for item in leads_payload
            ]
            resp = requests.post(
                "https://api.instantly.ai/api/v1/lead/add",
                json={
                    "api_key": INSTANTLY_API_KEY,
                    "campaign_id": INSTANTLY_CAMPAIGN_ID,
                    "skip_if_in_workspace": True,
                    "leads": instantly_leads,
                },
                timeout=30,
            )
            resp.raise_for_status()
            print(f"[+] Successfully synced {len(instantly_leads)} leads to Instantly.ai!", flush=True)
        except Exception as inst_err:
            err_msg = f"Instantly.ai API sync warning: {inst_err}"
            print(f"[!] {err_msg}", flush=True)
            send_discord_alert(err_msg)

    # 2. Smartlead.ai REST API Integration
    if SMARTLEAD_API_KEY and SMARTLEAD_CAMPAIGN_ID:
        try:
            print(f"[*] Pushing {len(leads_payload)} leads directly to Smartlead.ai campaign {SMARTLEAD_CAMPAIGN_ID}...", flush=True)
            smartlead_leads = [
                {
                    "email": item["Email"],
                    "first_name": item["First Name"],
                    "company_name": item["Company"],
                    "custom_fields": {
                        "subject_line": item["Subject Line"],
                        "email_body": item["Email Body"],
                    },
                }
                for item in leads_payload
            ]
            resp = requests.post(
                f"https://server.smartlead.ai/api/v1/campaigns/{SMARTLEAD_CAMPAIGN_ID}/leads?api_key={SMARTLEAD_API_KEY}",
                json={
                    "lead_list": smartlead_leads,
                    "settings": {
                        "ignore_global_block_list": False,
                        "ignore_unsubscribe_list": False,
                        "ignore_duplicate_leads_in_other_campaign": True,
                    },
                },
                timeout=30,
            )
            resp.raise_for_status()
            print(f"[+] Successfully synced {len(smartlead_leads)} leads to Smartlead.ai!", flush=True)
        except Exception as sl_err:
            err_msg = f"Smartlead.ai API sync warning: {sl_err}"
            print(f"[!] {err_msg}", flush=True)
            send_discord_alert(err_msg)


def generate_outreach():
    if not SUPABASE_URL or not SUPABASE_KEY:
        err = "SUPABASE_URL or SUPABASE_KEY not found in .env"
        print(f"[!] ERROR: {err}", flush=True)
        send_discord_alert(err)
        return

    try:
        print("[*] Connecting to Supabase to fetch active B2B IT contracts...", flush=True)
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        response = (
            supabase.table(TABLE_NAME)
            .select("*")
            .order("id", desc=True)
            .limit(200)
            .execute()
        )
        records = response.data if response and getattr(response, "data", None) else []

        if not records:
            print("[!] No contracts found in Supabase.", flush=True)
            return

        today = datetime.now().date()
        tech_contracts = []
        expired_skipped = 0

        for rec in records:
            if str(rec.get("url") or "").startswith("subscriber://") or str(rec.get("status") or "").startswith("SUBSCRIBER_"):
                continue
            title = str(rec.get("title") or "").strip()
            title_lower = title.lower()
            if not title:
                continue
            if any(re.search(pattern, title_lower) for pattern in commodity_it_exclusions):
                continue
            if not is_contract_open(rec, today=today):
                expired_skipped += 1
                continue
            if any(re.search(pattern, title_lower) for pattern in tech_keywords):
                tech_contracts.append(rec)

        if expired_skipped > 0:
            print(f"[*] Filtered out {expired_skipped} expired contract(s) with closing_date < {today}.", flush=True)

        if not tech_contracts:
            print("[!] FATAL: Zero open IT/Cyber contracts found in Supabase. Run mainscraper.py first.", flush=True)
            return

        default_top = tech_contracts[:3]
        default_payload_text = "".join(format_contract_line(i, r) for i, r in enumerate(default_top, 1))
        print(
            f"[+] Loaded {len(tech_contracts)} open, verified B2B IT contracts from Supabase.\n"
            f"Default Top {len(default_top)} Payload Preview:\n{default_payload_text}",
            flush=True,
        )

        apollo_file = "apollo-contacts.csv"
        output_file = "campaign_leads.csv"
        whop_checkout_url = os.getenv(
            "STRIPE_CHECKOUT_URL",
            f"{SITE_BASE_URL}/index.html#checkout",
        )

        if not os.path.exists(apollo_file):
            print(f"[!] Please ensure your exported Apollo file is named '{apollo_file}' and is in D:\\Daas", flush=True)
            return

        print("[*] Reading Apollo contacts and generating personalized zero-touch email payloads...", flush=True)

        leads_for_api = []

        with open(apollo_file, mode="r", encoding="utf-8-sig") as infile, \
             open(output_file, mode="w", newline="", encoding="utf-8") as outfile:

            reader = csv.DictReader(infile)
            headers = reader.fieldnames or []

            first_name_key = "First Name"
            company_key = "Company" if "Company" in headers else ("Company Name" if "Company Name" in headers else "Company")
            email_key = "Email" if "Email" in headers else "Person Primary Email"
            state_key = next((h for h in ("State", "Company State", "Person State") if h in headers), None)

            out_fieldnames = ["First Name", "Email", "Company", "Subject Line", "Email Body"]
            writer = csv.DictWriter(outfile, fieldnames=out_fieldnames)
            writer.writeheader()

            count = 0
            for row in reader:
                fname = (row.get(first_name_key) or "").strip() or "There"
                company = (row.get(company_key) or "").strip() or "your team"
                email = (row.get(email_key) or "").strip()
                prospect_state = (row.get(state_key) or "").strip() if state_key else ""

                if not email:
                    continue

                matched_contracts = select_contracts_for_prospect(tech_contracts, prospect_state, max_count=3)
                bid_count = len(matched_contracts)
                payload_text = "".join(format_contract_line(i, r) for i, r in enumerate(matched_contracts, 1))

                subject = f"Live IT/Cyber Contracts for {company}"

                body = (
                    f"Hi {fname},\n\n"
                    f"I built a private intelligence feed that scrapes Federal (SAM.gov), DemandStar, and 5 State SLED portals (TX, VA, CA, FL, MD) in real-time. "
                    f"I noticed {company} works in the tech space and wanted to send you {bid_count} live, active bids that just hit the wire:\n\n"
                    f"{payload_text}\n"
                    f"My automated system pulls high-value IT & cybersecurity RFPs every 6 hours and strips out 99% of commodity and renewal noise. "
                    f"You can browse our public directory ({SITE_BASE_URL}/contracts/index.html) or get instant access to the live private Discord wire right here:\n\n"
                    f"{whop_checkout_url}\n\n"
                    f"No sales calls, no demos. $99/mo. Cancel anytime."
                )

                lead_item = {
                    "First Name": fname,
                    "Email": email,
                    "Company": company,
                    "Subject Line": subject,
                    "Email Body": body,
                }
                writer.writerow(lead_item)
                leads_for_api.append(lead_item)
                count += 1

        print(f"[+] Success! Generated {count} personalized outreach emails in {output_file}.", flush=True)

        # Trigger Option C Zero-Touch Cold Email API Sync if credentials are set in .env
        sync_leads_to_cold_email_api(leads_for_api)

    except Exception as e:
        err_msg = f"outreach_generator.py error: {e}"
        print(f"[!] {err_msg}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n[!] {err_msg}\n")
        except Exception:
            pass
        send_discord_alert(err_msg)


if __name__ == "__main__":
    generate_outreach()