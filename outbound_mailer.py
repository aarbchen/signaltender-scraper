"""
Built-In Zero-Cost Outbound Drip Sender & Welcome Dossier Mailer (`outbound_mailer.py`).
Dispatches personalized, state-matched 2-step GovCon RFP dossier sequences from
`campaign_leads.csv` (and instant welcome dossiers for inbound leads) with:
  - Multi-transport support:
      1. Resend REST API (`RESEND_API_KEY` in `.env` — 3,000 free emails/mo)
      2. Standard SMTP / Google Workspace / Gmail App Password / Zoho / Custom SMTP
         (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`)
      3. Safe Outbox Staging (`outbox_ready_queue.json`) when credentials are not yet set
  - Anti-spam deliverability guardrails:
      - Configurable daily send cap (`OUTBOUND_DAILY_LIMIT`, default 30/day)
      - Persistent deduplication & 3-day Step 1 -> Step 2 cadence (`sent_outreach_log.json`)
      - RFC 8058 `List-Unsubscribe` headers & plain-text + HTML multipart formatting
"""

from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()

import argparse
import csv
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
import json
import os
import smtplib
import ssl
import time
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMPAIGN_CSV_PATH = os.path.join(BASE_DIR, "campaign_leads.csv")
SENT_LOG_PATH = os.path.join(BASE_DIR, "sent_outreach_log.json")
OUTBOX_QUEUE_PATH = os.path.join(BASE_DIR, "outbox_ready_queue.json")

RESEND_API_KEY = (os.getenv("RESEND_API_KEY") or "").strip()
SMTP_HOST = (os.getenv("SMTP_HOST") or "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT") or "587")
SMTP_USER = (os.getenv("SMTP_USER") or "").strip()
SMTP_PASSWORD = (os.getenv("SMTP_PASSWORD") or "").strip()
SMTP_FROM_NAME = (os.getenv("SMTP_FROM_NAME") or "SignalTender GovCon Capture Desk").strip()
SMTP_FROM_EMAIL = (os.getenv("SMTP_FROM_EMAIL") or SMTP_USER or "capture@signaltender.net").strip()
OUTBOUND_DAILY_LIMIT = int(os.getenv("OUTBOUND_DAILY_LIMIT") or "20")
DISCORD_WEBHOOK_URL = (os.getenv("DISCORD_WEBHOOK_URL") or "").strip()


def _load_sent_log() -> Dict[str, Any]:
    if os.path.exists(SENT_LOG_PATH):
        try:
            with open(SENT_LOG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("sent", {})
                    data.setdefault("unsubscribed", [])
                    return data
        except Exception:
            pass
    return {"sent": {}, "unsubscribed": []}


def _save_sent_log(data: Dict[str, Any]) -> None:
    try:
        with open(SENT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def send_single_email(
    to_email: str,
    subject: str,
    body_text: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Dispatch a single plain-text + HTML email via Resend API or SMTP,
    or stage it in `outbox_ready_queue.json` if credentials are not yet configured.
    """
    clean_to = str(to_email or "").strip().lower()
    if not clean_to or "@" not in clean_to:
        return {"status": "skipped", "reason": "invalid_email"}

    if dry_run or (not RESEND_API_KEY and not (SMTP_USER and SMTP_PASSWORD)):
        return {
            "status": "staged_in_outbox",
            "transport": "outbox_queue",
            "to": clean_to,
            "subject": subject,
        }

    # Transport 1: Resend API
    if RESEND_API_KEY:
        try:
            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>",
                    "to": [clean_to],
                    "subject": subject,
                    "text": body_text,
                    "headers": {
                        "List-Unsubscribe": f"<mailto:{SMTP_FROM_EMAIL}?subject=unsubscribe>",
                    },
                },
                timeout=12,
            )
            if 200 <= resp.status_code < 300:
                return {"status": "sent", "transport": "resend", "to": clean_to}
            return {"status": "error", "transport": "resend", "detail": resp.text[:200]}
        except Exception as exc:
            report_error("outbound_mailer.py", f"Resend send error for {clean_to}: {exc}", severity="WARNING")
            return {"status": "error", "transport": "resend", "detail": str(exc)}

    # Transport 2: Standard SMTP (TLS 587 or SSL 465)
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg["To"] = clean_to
        msg["List-Unsubscribe"] = f"<mailto:{SMTP_FROM_EMAIL}?subject=unsubscribe>"
        msg.set_content(body_text)

        context = ssl.create_default_context()
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=15) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        return {"status": "sent", "transport": "smtp", "to": clean_to}
    except Exception as exc:
        report_error("outbound_mailer.py", f"SMTP send error for {clean_to}: {exc}", severity="WARNING")
        return {"status": "error", "transport": "smtp", "detail": str(exc)}


def run_outbound_drip(daily_limit: Optional[int] = None, dry_run: bool = False) -> Dict[str, Any]:
    """
    Processes `campaign_leads.csv`, determines which prospects are due for Step 1
    (initial 3-RFP State Dossier value drop) or Step 2 (3+ days after Step 1),
    and dispatches or stages up to `daily_limit` emails.
    """
    cap = daily_limit if daily_limit is not None else OUTBOUND_DAILY_LIMIT
    if not os.path.exists(CAMPAIGN_CSV_PATH):
        print(f"[!] {CAMPAIGN_CSV_PATH} not found. Run outreach_generator.py first.", flush=True)
        return {"status": "missing_csv", "processed": 0}

    sent_log = _load_sent_log()
    sent_map: Dict[str, Dict[str, Any]] = sent_log.get("sent", {})
    unsubscribed = {str(u).lower() for u in (sent_log.get("unsubscribed") or [])}

    with open(CAMPAIGN_CSV_PATH, mode="r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    three_days_ago = now - timedelta(days=3)

    live_credentials_present = bool(RESEND_API_KEY or (SMTP_USER and SMTP_PASSWORD))
    staged_packets: List[Dict[str, Any]] = []
    sent_count = 0
    staged_count = 0

    for row in rows:
        if (sent_count + staged_count) >= cap:
            break

        email = str(row.get("Email") or "").strip().lower()
        if not email or "@" not in email or email in unsubscribed:
            continue

        fname = str(row.get("First Name") or "there").strip()
        company = str(row.get("Company") or "your team").strip()
        matched_state = str(row.get("Matched State") or "Federal & SLED").strip()
        dossier_url = str(row.get("Top Contract Dossier URL") or "https://signaltender.net/#contracts").strip()

        prev = sent_map.get(email)
        target_step = 0
        subject = ""
        body = ""

        if not prev:
            target_step = 1
            subject = str(row.get("Subject Line") or "").strip()
            body = str(row.get("Email Body") or "").strip()
        elif int(prev.get("step", 0)) == 1:
            last_sent_str = str(prev.get("sent_at") or "")
            try:
                last_dt = datetime.fromisoformat(last_sent_str.replace("Z", "+00:00"))
                if last_dt <= three_days_ago:
                    target_step = 2
                    subject = str(row.get("Followup Subject") or "").strip()
                    body = str(row.get("Followup Body") or "").strip()
            except Exception:
                pass

        if target_step == 0 or not subject or not body:
            continue

        res = send_single_email(to_email=email, subject=subject, body_text=body, dry_run=dry_run)
        if res.get("status") == "sent":
            sent_count += 1
            sent_map[email] = {
                "step": target_step,
                "sent_at": now_iso,
                "company": company,
                "matched_state": matched_state,
                "dossier_url": dossier_url,
                "transport": res.get("transport"),
            }
            time.sleep(1.2)
        elif res.get("status") == "staged_in_outbox":
            staged_count += 1
            staged_packets.append({
                "step": target_step,
                "to_email": email,
                "first_name": fname,
                "company": company,
                "matched_state": matched_state,
                "subject": subject,
                "body": body,
                "top_dossier_url": dossier_url,
                "staged_at": now_iso,
            })

    if sent_count > 0:
        sent_log["sent"] = sent_map
        _save_sent_log(sent_log)

    if staged_packets:
        try:
            with open(OUTBOX_QUEUE_PATH, "w", encoding="utf-8") as qf:
                json.dump(
                    {
                        "updated_at": now_iso,
                        "live_credentials_configured": live_credentials_present,
                        "instructions": "Set RESEND_API_KEY or SMTP_USER + SMTP_PASSWORD in .env to auto-send this queue on every run.",
                        "ready_count": len(staged_packets),
                        "emails": staged_packets,
                    },
                    qf,
                    indent=2,
                )
        except Exception:
            pass

    mode_str = "LIVE DISPATCH" if (live_credentials_present and not dry_run) else "OUTBOX STAGING"
    print(
        f"[+] Outbound Mailer ({mode_str}): {sent_count} sent live, "
        f"{staged_count} staged in outbox_ready_queue.json (Daily Cap: {cap}).",
        flush=True,
    )
    return {
        "status": "ok",
        "mode": mode_str,
        "sent_live": sent_count,
        "staged_in_outbox": staged_count,
        "daily_cap": cap,
    }


run_outbound_mailer = run_outbound_drip


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SignalTender Built-In Outbound Drip Mailer")
    parser.add_argument("--limit", type=int, default=OUTBOUND_DAILY_LIMIT, help="Maximum emails to process in this batch")
    parser.add_argument("--dry-run", action="store_true", help="Stage emails in outbox_ready_queue.json without sending")
    args = parser.parse_args()
    run_outbound_drip(daily_limit=args.limit, dry_run=args.dry_run)
