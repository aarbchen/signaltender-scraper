from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()
import os
import re
import time
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = os.getenv("SUPABASE_TABLE_NAME", "contracts")
SITE_BASE_URL = os.getenv("SIGNALTENDER_SITE_URL", "https://signaltender.net").rstrip("/")

# Master Client Discord Webhook + Optional State/Portal-Specific Webhooks
CLIENT_DISCORD_WEBHOOK_URL = (
    os.getenv("DISCORD_CONTENT_WEBHOOK_URL")
    or os.getenv("CLIENT_DISCORD_WEBHOOK_URL")
    or os.getenv("DISCORD_WEBHOOK_URL")
)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

JURISDICTION_WEBHOOKS = {
    "federal": os.getenv("DISCORD_FEDERAL_WEBHOOK_URL"),
    "texas": os.getenv("DISCORD_TEXAS_WEBHOOK_URL"),
    "virginia": os.getenv("DISCORD_VIRGINIA_WEBHOOK_URL"),
    "california": os.getenv("DISCORD_CALIFORNIA_WEBHOOK_URL"),
    "florida": os.getenv("DISCORD_FLORIDA_WEBHOOK_URL"),
    "maryland": os.getenv("DISCORD_MARYLAND_WEBHOOK_URL"),
    "new_york": os.getenv("DISCORD_NEW_YORK_WEBHOOK_URL"),
    "illinois": os.getenv("DISCORD_ILLINOIS_WEBHOOK_URL"),
    "pennsylvania": os.getenv("DISCORD_PENNSYLVANIA_WEBHOOK_URL"),
    "ohio": os.getenv("DISCORD_OHIO_WEBHOOK_URL"),
    "georgia": os.getenv("DISCORD_GEORGIA_WEBHOOK_URL"),
    "north_carolina": os.getenv("DISCORD_NORTH_CAROLINA_WEBHOOK_URL"),
    "massachusetts": os.getenv("DISCORD_MASSACHUSETTS_WEBHOOK_URL"),
    "municipal": os.getenv("DISCORD_MUNICIPAL_WEBHOOK_URL"),
}

JURISDICTION_LABELS = {
    "federal": "FEDERAL // SAM.GOV",
    "texas": "TEXAS // ESBD",
    "virginia": "VIRGINIA // eVA",
    "california": "CALIFORNIA // CAL EPROCURE",
    "florida": "FLORIDA // MFMP VIP",
    "maryland": "MARYLAND // EMMA & BONFIRE",
    "new_york": "NEW YORK // NYSCR",
    "illinois": "ILLINOIS // BIDBUY",
    "pennsylvania": "PENNSYLVANIA // eMARKETPLACE",
    "ohio": "OHIO // OHIOBUYS",
    "georgia": "GEORGIA // GPR & TEAM GA",
    "north_carolina": "NORTH CAROLINA // NC eVP & METRO",
    "massachusetts": "MASSACHUSETTS // COMMBUYS & BOSTON",
    "municipal": "MUNICIPAL // DEMANDSTAR",
}

ERROR_LOG_PATH = r"D:\Daas\error_log.txt"


def send_discord_alert(message: str) -> None:
    report_error("client_delivery.py", str(message))
    """Send system alert to Discord webhook and log errors as per project rules."""
    if not DISCORD_WEBHOOK_URL:
        print(" -> ERROR: Alert webhook URL not found in environment.", flush=True)
        return
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": f"**[ALERT] Delivery Pipeline:**\n{message}"},
            timeout=10,
        )
        response.raise_for_status()
        print(" -> Discord alert sent successfully.", flush=True)
    except Exception as e:
        print(f" -> Failed to send Discord alert: {e}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"Failed to send Discord alert: {e}\n")
        except Exception:
            pass


def clean_title_text(raw_title: str) -> str:
    s = str(raw_title or "").replace("\ufffd", "–")
    s = re.sub(r"\bWeb-\s+Based\b", "Web-Based", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*-\s*Due:\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def slugify_contract(title: str, fallback_id: str = "") -> str:
    clean = clean_title_text(title).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", clean).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if len(slug) > 75:
        slug = slug[:75].rsplit("-", 1)[0].strip("-")
    if not slug:
        slug = "government-it-contract"
    if fallback_id:
        return f"{slug}-{fallback_id}"
    return slug


def classify_jurisdiction(record: dict) -> str:
    title = str(record.get("title") or "").strip()
    agency = str(record.get("agency") or "").strip().lower()
    url = str(record.get("url") or record.get("source_url") or "").strip().lower()

    if "demandstar.com" in url:
        return "municipal"
    if "sam.gov" in url or "sbir.gov" in url:
        return "federal"
    if "txsmartbuy.com" in url:
        return "texas"
    if "eva.virginia.gov" in url or "cgieva.com" in url:
        return "virginia"
    if "caleprocure.ca.gov" in url:
        return "california"
    if "myfloridamarketplace.com" in url:
        return "florida"
    if "bidbuy.illinois.gov" in url or "transitchicago.bonfirehub.com" in url or "cookcountyil.bonfirehub.com" in url:
        return "illinois"
    if "emarketplace.state.pa.us" in url or "dgs.pa.gov" in url or "philaport.bonfirehub.com" in url:
        return "pennsylvania"
    if (
        "ohiobuys.ohio.gov" in url
        or "ohioauditor.gov" in url
        or "morpc.org" in url
        or "franklincountyohio.gov" in url
        or "columbus.bonfirehub.com" in url
        or "cincinnati-oh.bonfirehub.com" in url
        or "westerville.bonfirehub.com" in url
        or "dps.bonfirehub.com" in url
        or "akronohio.bonfirehub.com" in url
    ):
        return "ohio"
    if (
        "doas.state.ga.us" in url
        or "georgia.gov" in url
        or "ga.gov" in url
        or "forsythco.bonfirehub.com" in url
        or "fultonschools.bonfirehub.com" in url
        or "cobbk12.bonfirehub.com" in url
        or "itsmarta.com" in url
    ):
        return "georgia"
    if (
        "evp.nc.gov" in url
        or "nc.gov" in url
        or "unc.edu" in url
        or "ncsu.edu" in url
        or "wake.gov" in url
        or "mecknc.gov" in url
        or "charlottenc.gov" in url
        or "durhamnc.gov" in url
        or "guilfordcountync.gov" in url
    ):
        return "north_carolina"
    if (
        "a856-cityrecord.nyc.gov" in url
        or "passport.cityofnewyork.us" in url
        or "cityofnewyork.us" in url
        or "panynj.bonfirehub.com" in url
        or "suffolkcountyny.bonfirehub.com" in url
        or "rocklandgov.bonfirehub.com" in url
        or "nyscr.ny.gov" in url
        or "ogs.ny.gov" in url
    ):
        return "new_york"
    if (
        "commbuys.com" in url
        or "mass.gov" in url
        or "boston.gov" in url
        or "mbta.com" in url
        or "massport.com" in url
        or "masstech.org" in url
    ):
        return "massachusetts"
    if "emma.maryland.gov" in url or "bonfirehub.com" in url:
        return "maryland"

    if title.startswith("[TX]") or "texas" in agency or ", tx" in agency or "ut md anderson" in agency:
        return "texas"
    if title.startswith("[VA]") or "virginia" in agency or "arlington county" in agency:
        return "virginia"
    if title.startswith("[CA]") or "california" in agency:
        return "california"
    if title.startswith("[FL]") or "florida" in agency:
        return "florida"
    if title.startswith("[IL]") or "state of illinois" in agency or "chicago transit authority" in agency or "cook county" in agency:
        return "illinois"
    if title.startswith("[PA]") or "pennsylvania" in agency or "philadelphia" in agency or agency.startswith("pa "):
        return "pennsylvania"
    if title.startswith("[GA]") or "georgia" in agency or "(ga)" in agency or "fulton county" in agency or "atlanta" in agency or "cobb county" in agency or "gwinnett" in agency or "dekalb" in agency:
        return "georgia"
    if title.startswith("[NC]") or "north carolina" in agency or "(nc)" in agency or "nc " in agency or "wake county" in agency or "mecklenburg" in agency or "charlotte" in agency or "raleigh" in agency or "durham" in agency or "guilford" in agency:
        return "north_carolina"
    if (
        title.startswith("[NY]")
        or "new york" in agency
        or "nyc " in agency
        or "(ny)" in agency
        or "panynj" in agency
        or "port authority of new york" in agency
        or "suffolk county" in agency
        or "rockland county" in agency
    ):
        return "new_york"
    if (
        title.startswith("[MA]")
        or "massachusetts" in agency
        or "(ma)" in agency
        or "commbuys" in agency
        or "city of boston" in agency
        or "boston public" in agency
        or "mbta" in agency
        or "massport" in agency
        or "eotss" in agency
    ):
        return "massachusetts"
    if title.startswith("[OH]") or "ohio" in agency or "columbus" in agency or "morpc" in agency or "franklin county" in agency:
        return "ohio"
    if title.startswith("[MD]") or "maryland" in agency or "prince george" in agency or "howard county" in agency:
        return "maryland"
    if "federal government" in agency:
        return "federal"
    return "municipal"

def classify_vertical_tag(record: dict) -> str:
    blob = f"{record.get('title', '')} {record.get('agency', '')}".lower()
    if any(k in blob for k in ("cyber", "infosec", "security", "siem", "soc", "zero trust", "firewall", "audit", "rmf")):
        return "Cybersecurity & Zero-Trust"
    if any(k in blob for k in ("cloud", "aws", "azure", "saas", "data center", "server", "storage", "hosting")):
        return "Cloud & Infrastructure"
    if any(k in blob for k in ("network", "fiber", "broadband", "telecom", "wireless", "hardware", "audio/visual")):
        return "Network, Telecom & Hardware"
    return "Enterprise Software, Data & AI"


def format_lead_block(record: dict) -> str:
    """Format an individual Supabase contract record into an enriched Discord intelligence block."""
    raw_title = str(record.get("title") or "N/A").strip()
    clean_title = clean_title_text(raw_title)
    agency = str(record.get("agency") or "N/A").strip()
    closing_date = str(record.get("closing_date") or "").strip()
    if not closing_date:
        m_due = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", raw_title, flags=re.IGNORECASE)
        closing_date = m_due.group(1) if m_due else "Open / See Official Portal"
    link = str(record.get("url") or "N/A").strip()
    rec_id = str(record.get("id") or "")

    j_key = classify_jurisdiction(record)
    j_badge = JURISDICTION_LABELS.get(j_key, "FEDERAL // SAM.GOV")
    vertical = classify_vertical_tag(record)
    slug = slugify_contract(raw_title, fallback_id=rec_id)
    dossier_url = f"{SITE_BASE_URL}/contracts/rfp/{slug}.html"

    lines = [
        f"**[{j_badge}]** • `{vertical}`",
        f"**Solicitation:** {clean_title}",
        f"**Buyer Agency:** {agency} | **Closing Date:** `{closing_date}`",
        f"**Official Portal:** <{link}>",
        f"**SignalTender Dossier:** <{dossier_url}>",
        f"{'─' * 44}",
    ]
    return "\n".join(lines)


def _post_batches_to_webhook(records: list[dict], webhook_url: str, label: str = "Master Wire") -> bool:
    """Group records into <1900-char batches and POST to a Discord webhook with rate-limit retry."""
    if not records or not webhook_url:
        return False

    batches = []
    current_batch = []
    current_char_count = 0

    for rec in records:
        block = format_lead_block(rec)
        block_len = len(block) + 4
        if current_char_count + block_len > 1900 and current_batch:
            batches.append(current_batch)
            current_batch = [rec]
            current_char_count = len(block)
        else:
            current_batch.append(rec)
            current_char_count += block_len

    if current_batch:
        batches.append(current_batch)

    for batch_index, batch in enumerate(batches, start=1):
        blocks = [format_lead_block(rec) for rec in batch]
        message_content = "\n\n".join(blocks)

        print(f"[*] Posting {label} batch {batch_index}/{len(batches)} ({len(batch)} lead(s)) to Discord...", flush=True)
        payload = {
            "username": "SignalWire Pro",
            "content": message_content,
            "flags": 4,
        }
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
        )
        if response.status_code == 429:
            retry_after = response.json().get("retry_after", 1.5)
            time.sleep(float(retry_after))
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
            )
        response.raise_for_status()
        time.sleep(0.4)

    return True


def _send_subscriber_email_briefing(to_email: str, body_text: str, count: int) -> bool:
    """Send 6-hour SignalWire RFP briefing email ONLY to active subscribers who opted in (`email_briefings_enabled: True`)."""
    from urllib.parse import quote_plus
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASSWORD", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user or "aaron@getsignaltender.com").strip()
    subject = f"SignalTender 6-Hour GovCon RFP Wire ({count} New IT/Cyber Solicitations)"
    disable_url = f"https://b2b-contract-parser-api.onrender.com/v1/webhooks/email-briefings?email={quote_plus(to_email)}&enabled=false"
    clean_body = (
        body_text.replace("**", "").replace("`", "")
        + f"\n\nFull Live Directory & Unlocked Dossiers: {SITE_BASE_URL}/contracts\n"
        + f"Manage or Turn Off 6-Hour Email Briefings Anytime: {SITE_BASE_URL}/#checkout (1-Click Off: {disable_url})\n"
    )
    try:
        if resend_key:
            r = requests.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                json={"from": f"SignalTender Capture Wire <{from_email}>", "to": [to_email], "subject": subject, "text": clean_body},
                timeout=10,
            )
            return r.status_code in (200, 201)
        elif smtp_user and smtp_pass:
            import smtplib, ssl
            from email.message import EmailMessage
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = f"SignalTender Capture Wire <{from_email}>"
            msg["To"] = to_email
            msg.set_content(clean_body)
            with smtplib.SMTP(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT") or "587"), timeout=10) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(smtp_user, smtp_pass)
                s.send_message(msg)
            return True
        inst_key = os.getenv("INSTANTLY_API_KEY", "").strip()
        inst_sub_cid = os.getenv("INSTANTLY_SUBSCRIBER_CAMPAIGN_ID", "748eecf5-6b63-4dff-b9f2-1d2ff1a4a96f").strip()
        if inst_key and inst_sub_cid:
            r = requests.post(
                "https://api.instantly.ai/api/v2/leads",
                headers={"Authorization": f"Bearer {inst_key}", "Content-Type": "application/json"},
                json={
                    "campaign": inst_sub_cid,
                    "email": to_email,
                    "skip_if_in_campaign": False,
                    "custom_variables": {"subject_line": subject, "email_body": clean_body},
                },
                timeout=10,
            )
            return r.status_code in (200, 201)
    except Exception:
        pass
    return False


def _dispatch_to_external_customer_webhooks(supabase: Client, records: list[dict]) -> int:
    """
    Dispatch newly discovered RFPs to any active subscriber external webhooks
    (Slack, Microsoft Teams, Zapier, Make.com, n8n, HubSpot, Salesforce) stored
    in Supabase with status='SUBSCRIBER_ACTIVE'.
    """
    import json
    dispatched = 0
    try:
        sub_resp = supabase.table(TABLE_NAME).select("title,status").eq("status", "SUBSCRIBER_ACTIVE").execute()
        sub_rows = sub_resp.data if sub_resp and getattr(sub_resp, "data", None) else []
    except Exception:
        sub_rows = []

    if not sub_rows or not records:
        return 0

    blocks = []
    char_total = 0
    for rec in records[:10]:
        b = format_lead_block(rec)
        if char_total + len(b) + 4 > 1900 and blocks:
            break
        blocks.append(b)
        char_total += len(b) + 4
    combined_text = "\n\n".join(blocks)

    for srow in sub_rows:
        try:
            meta = json.loads(str(srow.get("title") or "{}"))
            sub_email = str(meta.get("email") or "").strip().lower()
            if sub_email and "@" in sub_email and bool(meta.get("email_briefings_enabled", False)):
                _send_subscriber_email_briefing(sub_email, combined_text, len(records))
            w_url = str(meta.get("webhook_url") or "").strip()
            if not w_url.startswith("https://"):
                continue
            u_low = w_url.lower()
            if "hooks.slack.com" in u_low or "webhook.office.com" in u_low or "logic.azure.com" in u_low:
                payload = {"text": combined_text}
            elif "discord.com/api/webhooks" in u_low or "discordapp.com/api/webhooks" in u_low:
                payload = {"username": "SignalWire Pro", "content": combined_text, "flags": 4}
            else:
                payload = {
                    "event": "signaltender.signalwire.batch",
                    "text": combined_text,
                    "content": combined_text,
                    "contracts": [
                        {
                            "id": str(r.get("id") or ""),
                            "title": r.get("title"),
                            "agency": r.get("agency"),
                            "closing_date": r.get("closing_date"),
                            "official_bid_url": r.get("url"),
                            "jurisdiction": classify_jurisdiction(r),
                            "vertical": classify_vertical_tag(r),
                        }
                        for r in records[:25]
                    ],
                }
            requests.post(w_url, json=payload, timeout=10)
            dispatched += 1
        except Exception as ext_err:
            print(f"[!] External customer webhook warning: {ext_err}", flush=True)
    return dispatched


def deliver_leads(client_webhook_url: str = None) -> int:
    """
    Query Supabase for 'New Lead' contracts, format them into enriched Discord
    intelligence blocks (with pSEO Dossier + FastAPI links), route them to the
    Master Client Discord Wire, any configured state-specific Discord channels,
    AND any active subscriber Slack/Teams/CRM webhooks, then update status to 'Delivered'.
    """
    target_webhook = client_webhook_url or CLIENT_DISCORD_WEBHOOK_URL

    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL or SUPABASE_KEY is missing in environment variables.")
        if not target_webhook:
            raise ValueError("Client Discord Webhook URL is missing in environment variables.")

        print("[*] Connecting to Supabase...", flush=True)
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        print(f"[*] Querying '{TABLE_NAME}' table for records with status='New Lead'...", flush=True)
        resp = supabase.table(TABLE_NAME).select("*").eq("status", "New Lead").execute()
        records = [
            r for r in (resp.data if resp and getattr(resp, "data", None) else [])
            if not str(r.get("url") or "").startswith("subscriber://")
        ]

        if not records:
            print("[+] No 'New Lead' records found to deliver.", flush=True)
            return 0

        print(f"[*] Found {len(records)} 'New Lead' record(s) ready for delivery.", flush=True)

        # 1. Post all leads to the Master Client Discord Webhook (#all-active-rfps)
        _post_batches_to_webhook(records, target_webhook, label="Master All-Access Wire")

        # 2. Route leads to any state/portal-specific Discord channel webhooks configured in .env
        for j_key, j_webhook in JURISDICTION_WEBHOOKS.items():
            if not j_webhook or j_webhook == target_webhook:
                continue
            j_records = [r for r in records if classify_jurisdiction(r) == j_key]
            if j_records:
                try:
                    _post_batches_to_webhook(j_records, j_webhook, label=f"State Channel ({j_key.upper()})")
                except Exception as ch_err:
                    print(f"[!] State channel webhook ({j_key}) warning: {ch_err}", flush=True)

        # 3. Route leads to any active subscriber external webhooks (Slack, MS Teams, Zapier, Make, n8n, CRM)
        ext_count = _dispatch_to_external_customer_webhooks(supabase, records)
        if ext_count:
            print(f"[+] Dispatched RFP batch to {ext_count} external customer Slack/Teams/CRM webhook(s).", flush=True)

        # 4. Update Supabase status from 'New Lead' to 'Delivered'
        urls_delivered = [rec["url"] for rec in records if rec.get("url")]
        for i in range(0, len(urls_delivered), 50):
            chunk = urls_delivered[i : i + 50]
            supabase.table(TABLE_NAME).update({"status": "Delivered"}).in_("url", chunk).execute()

        delivered_count = len(records)
        print(f"[+] Client delivery complete! Successfully delivered {delivered_count} enriched lead(s).", flush=True)
        return delivered_count

    except Exception as e:
        error_msg = f"client_delivery.py failed: {e}"
        print(f"\n[!] Error during client delivery: {e}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n[!] Error during client delivery: {e}\n")
        except Exception:
            pass
        send_discord_alert(error_msg)
        return 0


if __name__ == "__main__":
    deliver_leads()
