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

# Master Client Discord Webhook + Optional State/Portal-Specific Webhooks (Option B)
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
    "municipal": os.getenv("DISCORD_MUNICIPAL_WEBHOOK_URL"),
}

JURISDICTION_LABELS = {
    "federal": "🇺🇸 FEDERAL // SAM.GOV",
    "texas": "🤠 TEXAS // ESBD",
    "virginia": "🏛️ VIRGINIA // eVA",
    "california": "🐻 CALIFORNIA // CAL EPROCURE",
    "florida": "🌴 FLORIDA // MFMP VIP",
    "maryland": "🦀 MARYLAND // EMMA & BONFIRE",
    "municipal": "🏙️ MUNICIPAL // DEMANDSTAR",
}

ERROR_LOG_PATH = r"D:\Daas\error_log.txt"


def send_discord_alert(message: str) -> None:
    """Send system alert to Discord webhook and log errors as per project rules."""
    if not DISCORD_WEBHOOK_URL:
        print(" -> ERROR: Alert webhook URL not found in environment.", flush=True)
        return
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": f"🚨 **Delivery Pipeline Alert:**\n{message}"},
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


def slugify_contract(title: str, fallback_id: str = "") -> str:
    clean = re.sub(r"^\s*\[[A-Z]{2,4}\]\s*", "", str(title or "")).strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", clean).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)[:65].strip("-")
    if not slug:
        slug = "government-it-contract"
    if fallback_id:
        return f"{slug}-{fallback_id}"
    return slug


def classify_jurisdiction(record: dict) -> str:
    title = str(record.get("title") or "").strip()
    agency = str(record.get("agency") or "").strip().lower()
    url = str(record.get("url") or "").strip().lower()

    if title.startswith("[TX]") or "txsmartbuy" in url or "texas" in agency:
        return "texas"
    if title.startswith("[VA]") or "eva.virginia.gov" in url or "virginia" in agency:
        return "virginia"
    if title.startswith("[CA]") or "caleprocure" in url or "california" in agency:
        return "california"
    if title.startswith("[FL]") or "myfloridamarketplace" in url or "florida" in agency:
        return "florida"
    if title.startswith("[MD]") or "emma.maryland.gov" in url or "bonfirehub.com" in url or "maryland" in agency:
        return "maryland"
    if "demandstar.com" in url:
        return "municipal"
    return "federal"


def classify_vertical_tag(record: dict) -> str:
    blob = f"{record.get('title', '')} {record.get('agency', '')}".lower()
    if any(k in blob for k in ("cyber", "infosec", "security", "siem", "soc", "zero trust", "firewall", "audit")):
        return "🔒 Cybersecurity & Zero-Trust"
    if any(k in blob for k in ("cloud", "aws", "azure", "saas", "data center", "server", "storage", "hosting")):
        return "☁️ Cloud & Infrastructure"
    if any(k in blob for k in ("network", "fiber", "broadband", "telecom", "wireless", "hardware", "audio/visual")):
        return "🌐 Network, Telecom & Hardware"
    return "💻 Enterprise Software, Data & AI"


def format_lead_block(record: dict) -> str:
    """Format an individual Supabase contract record into an enriched Discord intelligence block."""
    title = record.get("title") or "N/A"
    agency = record.get("agency") or "N/A"
    closing_date = record.get("closing_date")
    link = record.get("url") or "N/A"
    rec_id = str(record.get("id") or "")

    j_key = classify_jurisdiction(record)
    j_badge = JURISDICTION_LABELS.get(j_key, "🇺🇸 FEDERAL // SAM.GOV")
    vertical = classify_vertical_tag(record)
    slug = slugify_contract(title, fallback_id=rec_id)
    dossier_url = f"{SITE_BASE_URL}/contracts/rfp/{slug}.html"

    lines = [
        f"**[{j_badge}]** • `{vertical}`",
        f"**Title:** {title}",
        f"**Agency:** {agency}",
    ]
    if closing_date:
        lines.append(f"**Closing Date:** `{closing_date}`")
    lines.append(f"**Official Bid Link:** <{link}>")
    lines.append(f"**SignalTender Dossier & AI Parser:** <{dossier_url}> | <{SITE_BASE_URL}/apis.html>")
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
        block_len = len(block) + 8
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
        message_content = "\n\n---\n\n".join(blocks)

        print(f"[*] Posting {label} batch {batch_index}/{len(batches)} ({len(batch)} lead(s)) to Discord...", flush=True)
        payload = {
            "username": "SignalWire Pro // Tier 1",
            "content": message_content,
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

    blocks = [format_lead_block(rec) for rec in records[:10]]
    combined_text = "\n\n---\n\n".join(blocks)[:1900]

    for srow in sub_rows:
        try:
            meta = json.loads(str(srow.get("title") or "{}"))
            w_url = str(meta.get("webhook_url") or "").strip()
            if not w_url.startswith("https://"):
                continue
            u_low = w_url.lower()
            if "hooks.slack.com" in u_low or "webhook.office.com" in u_low or "logic.azure.com" in u_low:
                payload = {"text": combined_text}
            elif "discord.com/api/webhooks" in u_low or "discordapp.com/api/webhooks" in u_low:
                payload = {"username": "SignalWire Pro // Tier 1", "content": combined_text}
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
