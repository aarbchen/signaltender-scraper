import os
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

# Discord Webhooks
CLIENT_DISCORD_WEBHOOK_URL = (
    os.getenv("DISCORD_CONTENT_WEBHOOK_URL")
    or os.getenv("CLIENT_DISCORD_WEBHOOK_URL")
    or os.getenv("DISCORD_WEBHOOK_URL")
)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

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


def format_lead_block(record: dict) -> str:
    """Format an individual Supabase contract record into a clean Discord message block."""
    title = record.get("title") or "N/A"
    agency = record.get("agency") or "N/A"
    closing_date = record.get("closing_date")
    link = record.get("url") or "N/A"

    lines = [
        f"**Title:** {title}",
        f"**Agency:** {agency}",
    ]
    if closing_date:
        lines.append(f"**Closing Date:** {closing_date}")
    lines.append(f"**Link:** {link}")
    return "\n".join(lines)


def deliver_leads(client_webhook_url: str = None) -> int:
    """
    Query Supabase for 'New Lead' contracts, format them into professional
    Discord message blocks, POST to the client webhook, and update the status
    in Supabase to 'Delivered'.
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
        records = resp.data if resp and getattr(resp, "data", None) else []

        if not records:
            print("[+] No 'New Lead' records found to deliver.", flush=True)
            return 0

        print(f"[*] Found {len(records)} 'New Lead' record(s) ready for delivery.", flush=True)

        # Group records into batches to ensure Discord's 2000 character limit is never exceeded
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

        delivered_count = 0

        for batch_index, batch in enumerate(batches, start=1):
            blocks = [format_lead_block(rec) for rec in batch]
            message_content = "\n\n---\n\n".join(blocks)

            print(f"[*] Posting batch {batch_index}/{len(batches)} ({len(batch)} lead(s)) to Client Discord webhook...", flush=True)
            response = requests.post(
                target_webhook,
                json={"content": message_content},
                timeout=10,
            )
            if response.status_code == 429:
                retry_after = response.json().get("retry_after", 1.0)
                time.sleep(float(retry_after))
                response = requests.post(
                    target_webhook,
                    json={"content": message_content},
                    timeout=10,
                )
            response.raise_for_status()
            print(f"[+] Successfully posted batch {batch_index} to Discord.", flush=True)

            # Update Supabase status from 'New Lead' to 'Delivered'
            urls_in_batch = [rec["url"] for rec in batch if rec.get("url")]
            if urls_in_batch:
                supabase.table(TABLE_NAME).update({"status": "Delivered"}).in_("url", urls_in_batch).execute()
            delivered_count += len(batch)
            print(f"[+] Updated {len(batch)} record(s) in Supabase to 'Delivered'.", flush=True)

        print(f"[+] Client delivery complete! Successfully delivered {delivered_count} lead(s).", flush=True)
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
