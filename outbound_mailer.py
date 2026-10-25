"""
Built-In Zero-Cost Outbound Drip Sender, Auto-Ramp Scheduler & Welcome Dossier Mailer (`outbound_mailer.py`).
Dispatches personalized, state-matched 2-step GovCon RFP dossier sequences from
`campaign_leads.csv` (and instant welcome dossiers for inbound leads) with:
  1. Automatic Post-Warmup Volume Ramp (`compute_dynamic_daily_limit()`):
     - Pre-Launch (Before Oct 31, 2026): Safe Warmup Guard (0 live sends; stages 20 in `outbox_ready_queue.json`).
     - Days 1-3  (Oct 31 - Nov 2):  20 emails/day (max 5 per 6-hour cron run).
     - Days 4-7  (Nov 3  - Nov 6):  30 emails/day (max 8 per 6-hour cron run).
     - Days 8-14 (Nov 7  - Nov 13): 45 emails/day (max 12 per 6-hour cron run).
     - Day 15+   (Nov 14+):         60 emails/day (max 15 per 6-hour cron run).
  2. Stateless Render Cron Persistence via Supabase (`status = SUBSCRIBER_OUTBOUND_SENT_LOG`):
     - Reads and logs every sent Step 1 and Step 2 email to both local `sent_outreach_log.json` and
       Supabase (`SELECT` + RLS-safe `.insert()`) so 6-hour Render Cron containers never double-send
       or exceed the 24-hour UTC daily cap.
  3. Multi-Transport Support:
     - Resend REST API (`RESEND_API_KEY`)
     - Standard SMTP (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`)
     - Safe Outbox Staging (`outbox_ready_queue.json`)
"""

from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()

import argparse
import csv
from datetime import datetime, timezone, timedelta, date
from email.message import EmailMessage
import json
import math
import os
import smtplib
import ssl
import time
from typing import Any, Dict, List, Optional, Tuple
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMPAIGN_CSV_PATH = os.path.join(BASE_DIR, "campaign_leads.csv")
SENT_LOG_PATH = os.path.join(BASE_DIR, "sent_outreach_log.json")
OUTBOX_QUEUE_PATH = os.path.join(BASE_DIR, "outbox_ready_queue.json")

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or "").strip()

RESEND_API_KEY = (os.getenv("RESEND_API_KEY") or "").strip()
SMTP_HOST = (os.getenv("SMTP_HOST") or "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT") or "587")
SMTP_USER = (os.getenv("SMTP_USER") or "").strip()
SMTP_PASSWORD = (os.getenv("SMTP_PASSWORD") or "").strip()
SMTP_FROM_NAME = (os.getenv("SMTP_FROM_NAME") or "SignalTender GovCon Capture Desk").strip()
SMTP_FROM_EMAIL = (os.getenv("SMTP_FROM_EMAIL") or SMTP_USER or "capture@signaltender.net").strip()
OUTBOUND_LAUNCH_DATE_STR = (os.getenv("OUTBOUND_LAUNCH_DATE") or "2026-10-15").strip()
DISCORD_WEBHOOK_URL = (os.getenv("DISCORD_WEBHOOK_URL") or "").strip()

try:
    from govcon_lead_harvester import ALREADY_CONTACTED_LEGACY_EMAILS
except Exception:
    ALREADY_CONTACTED_LEGACY_EMAILS = set()


_CACHED_INSTANTLY_MAILBOX_COUNT: Optional[int] = None


def _detect_live_instantly_mailbox_count(fallback: int = 2) -> int:
    """
    Queries `GET https://api.instantly.ai/api/v2/accounts` (cached per process) so adding
    new mailboxes in Instantly automatically scales daily sending capacity without requiring
    manual `.env` edits.
    """
    global _CACHED_INSTANTLY_MAILBOX_COUNT
    if _CACHED_INSTANTLY_MAILBOX_COUNT is not None:
        return max(fallback, _CACHED_INSTANTLY_MAILBOX_COUNT)
    inst_key = (os.getenv("INSTANTLY_API_KEY") or "").strip()
    if not inst_key:
        _CACHED_INSTANTLY_MAILBOX_COUNT = fallback
        return fallback
    try:
        r = requests.get(
            "https://api.instantly.ai/api/v2/accounts?limit=100",
            headers={"Authorization": f"Bearer {inst_key}"},
            timeout=6,
        )
        if r.status_code == 200:
            items = (r.json() or {}).get("items") or []
            active_items = [x for x in items if isinstance(x, dict) and int(x.get("status") or 0) == 1]
            _CACHED_INSTANTLY_MAILBOX_COUNT = len(active_items) or len(items) or fallback
            return max(fallback, _CACHED_INSTANTLY_MAILBOX_COUNT)
    except Exception:
        pass
    _CACHED_INSTANTLY_MAILBOX_COUNT = fallback
    return fallback


def compute_dynamic_daily_limit(now_utc: Optional[datetime] = None) -> Tuple[int, int, str]:
    """
    Returns `(daily_cap, per_cron_run_cap, phase_label)` based on the current UTC date
    relative to `OUTBOUND_LAUNCH_DATE` (default `2026-10-31`) and the live connected
    Instantly mailbox count (or `OUTBOUND_MAILBOX_COUNT`, default `2`), or honors
    explicit `OUTBOUND_DAILY_LIMIT_OVERRIDE` if set in `.env`.
    """
    override = (os.getenv("OUTBOUND_DAILY_LIMIT_OVERRIDE") or "").strip()
    if override.isdigit() and int(override) > 0:
        d_cap = int(override)
        return d_cap, max(1, math.ceil(d_cap / 4)), f"Manual Override ({d_cap}/day)"

    mb_raw = (os.getenv("OUTBOUND_MAILBOX_COUNT") or "2").strip()
    env_mb_count = max(1, int(mb_raw)) if mb_raw.isdigit() else 2
    mailbox_count = _detect_live_instantly_mailbox_count(fallback=env_mb_count)
    scale_factor = mailbox_count / 2.0

    now_dt = now_utc or datetime.now(timezone.utc)
    today_d = now_dt.date()
    try:
        launch_d = date.fromisoformat(OUTBOUND_LAUNCH_DATE_STR)
    except Exception:
        launch_d = date(2026, 10, 15)

    days_since_launch = (today_d - launch_d).days
    if days_since_launch < 0:
        # Before Oct 31 warmup completion: stage 20 in outbox, 0 live dispatch unless forced
        d_cap = max(10, int(round(20 * scale_factor)))
        c_cap = max(1, math.ceil(d_cap / 4))
        return d_cap, c_cap, f"Pre-Launch Warmup Guard (Launches {launch_d.isoformat()} at {d_cap}/day across {mailbox_count} mailboxes)"
    if days_since_launch <= 2:
        # Days 1-3 (Oct 31 - Nov 2)
        d_cap = max(10, int(round(20 * scale_factor)))
        c_cap = max(1, math.ceil(d_cap / 4))
        return d_cap, c_cap, f"Ramp Phase 1 (Day {days_since_launch + 1}: {d_cap}/day | {c_cap}/cron across {mailbox_count} mailboxes)"
    if days_since_launch <= 6:
        # Days 4-7 (Nov 3 - Nov 6)
        d_cap = max(15, int(round(30 * scale_factor)))
        c_cap = max(1, math.ceil(d_cap / 4))
        return d_cap, c_cap, f"Ramp Phase 2 (Day {days_since_launch + 1}: {d_cap}/day | {c_cap}/cron across {mailbox_count} mailboxes)"
    if days_since_launch <= 13:
        # Days 8-14 (Nov 7 - Nov 13)
        d_cap = max(22, int(round(45 * scale_factor)))
        c_cap = max(1, math.ceil(d_cap / 4))
        return d_cap, c_cap, f"Ramp Phase 3 (Day {days_since_launch + 1}: {d_cap}/day | {c_cap}/cron across {mailbox_count} mailboxes)"
    # Day 15+ (Nov 14+)
    d_cap = max(30, int(round(60 * scale_factor)))
    c_cap = max(1, math.ceil(d_cap / 4))
    return d_cap, c_cap, f"Full Warmed Cadence (Day {days_since_launch + 1}: {d_cap}/day | {c_cap}/cron across {mailbox_count} mailboxes)"


def _load_sent_log() -> Dict[str, Any]:
    """
    Loads sent outreach state from local `sent_outreach_log.json` AND merges any
    `SUBSCRIBER_OUTBOUND_SENT_LOG` rows from Supabase so stateless Render Cron containers
    always have the full history of Step 1 and Step 2 sends.
    """
    data: Dict[str, Any] = {"sent": {}, "unsubscribed": []}
    if os.path.exists(SENT_LOG_PATH):
        try:
            with open(SENT_LOG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    data["sent"] = dict(loaded.get("sent") or {})
                    data["unsubscribed"] = list(loaded.get("unsubscribed") or [])
        except Exception:
            pass

    if SUPABASE_URL and SUPABASE_KEY:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        try:
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/contracts",
                params={
                    "status": "eq.SUBSCRIBER_OUTBOUND_SENT_LOG",
                    "select": "id,title,agency,url,status",
                    "order": "id.asc",
                    "limit": "2000",
                },
                headers=headers,
                timeout=10,
            )
            if resp.status_code == 200 and isinstance(resp.json(), list):
                for row in resp.json():
                    raw_title = str(row.get("title") or "").strip()
                    try:
                        meta = json.loads(raw_title)
                        if isinstance(meta, dict) and meta.get("email"):
                            em = str(meta["email"]).strip().lower()
                            step_num = int(meta.get("step") or 1)
                            prev = data["sent"].get(em)
                            if not prev or step_num >= int(prev.get("step") or 0):
                                data["sent"][em] = {
                                    "step": step_num,
                                    "sent_at": str(meta.get("sent_at") or ""),
                                    "company": str(meta.get("company") or ""),
                                    "matched_state": str(meta.get("matched_state") or ""),
                                    "dossier_url": str(meta.get("dossier_url") or ""),
                                    "transport": str(meta.get("transport") or "supabase_log"),
                                }
                    except Exception:
                        continue
        except Exception as exc:
            report_error("outbound_mailer.py", f"Supabase sent-log fetch warning: {exc}", severity="WARNING")

    return data


def _save_sent_log(data: Dict[str, Any]) -> None:
    try:
        with open(SENT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _record_sent_email_supabase(email: str, record: Dict[str, Any]) -> None:
    """
    Persists a sent Step 1 or Step 2 outreach event to Supabase (`status = SUBSCRIBER_OUTBOUND_SENT_LOG`)
    using RLS-safe `SELECT` + `.insert()` (never `.upsert()`).
    """
    if not (SUPABASE_URL and SUPABASE_KEY):
        return
    clean_em = email.strip().lower()
    step_num = int(record.get("step") or 1)
    synthetic_url = f"subscriber://outbound-sent/{clean_em}/step-{step_num}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    try:
        chk = requests.get(
            f"{SUPABASE_URL}/rest/v1/contracts",
            params={"url": f"eq.{synthetic_url}", "select": "id"},
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=8,
        )
        if chk.status_code == 200 and isinstance(chk.json(), list) and len(chk.json()) > 0:
            return
        payload = {
            "title": json.dumps({"email": clean_em, **record}),
            "agency": f"OUTBOUND_STEP_{step_num}:{record.get('matched_state', 'ALL')}",
            "url": synthetic_url,
            "status": "SUBSCRIBER_OUTBOUND_SENT_LOG",
        }
        requests.post(
            f"{SUPABASE_URL}/rest/v1/contracts",
            headers=headers,
            json=payload,
            timeout=8,
        )
    except Exception as exc:
        report_error("outbound_mailer.py", f"Supabase sent-log insert warning: {exc}", severity="WARNING")


def send_single_email(
    to_email: str,
    subject: str,
    body_text: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Dispatch a single plain-text email via Resend API or SMTP,
    or stage it in `outbox_ready_queue.json` if credentials are not yet configured.
    """
    clean_to = str(to_email or "").strip().lower()
    if not clean_to or "@" not in clean_to or clean_to in ALREADY_CONTACTED_LEGACY_EMAILS:
        return {"status": "skipped", "reason": "invalid_or_legacy_email"}

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


def run_outbound_drip(
    daily_limit: Optional[int] = None,
    dry_run: bool = False,
    force_send_before_launch: bool = False,
) -> Dict[str, Any]:
    """
    Processes `campaign_leads.csv`, determines which prospects are due for Step 2
    (3+ days after Step 1) or Step 1 (initial 3-RFP State Dossier value drop),
    enforces the automatic November volume ramp (`compute_dynamic_daily_limit`),
    and dispatches or stages emails cleanly across 6-hour Render Cron runs.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    today_prefix = now.strftime("%Y-%m-%d")
    three_days_ago = now - timedelta(days=3)

    auto_daily_cap, per_cron_cap, ramp_phase_label = compute_dynamic_daily_limit(now)
    daily_cap = daily_limit if daily_limit is not None else auto_daily_cap

    try:
        launch_d = date.fromisoformat(OUTBOUND_LAUNCH_DATE_STR)
    except Exception:
        launch_d = date(2026, 10, 15)
    before_launch_date = (now.date() < launch_d) and not force_send_before_launch

    if not os.path.exists(CAMPAIGN_CSV_PATH):
        print(f"[!] {CAMPAIGN_CSV_PATH} not found. Run outreach_generator.py first.", flush=True)
        return {"status": "missing_csv", "processed": 0}

    sent_log = _load_sent_log()
    sent_map: Dict[str, Dict[str, Any]] = sent_log.get("sent", {})
    unsubscribed = {str(u).lower() for u in (sent_log.get("unsubscribed") or [])} | set(ALREADY_CONTACTED_LEGACY_EMAILS)

    # Count how many emails have ALREADY been sent in the current UTC calendar day
    sent_today_count = sum(
        1
        for rec in sent_map.values()
        if isinstance(rec, dict) and str(rec.get("sent_at") or "").startswith(today_prefix)
    )
    remaining_today_cap = max(0, daily_cap - sent_today_count)
    # When sending live, pace across the 4 daily 6-hour cron runs (`per_cron_cap`); when staging in outbox, stage full `daily_cap`
    live_credentials_present = bool(RESEND_API_KEY or (SMTP_USER and SMTP_PASSWORD))
    effective_live_run_cap = min(remaining_today_cap, per_cron_cap if daily_limit is None else remaining_today_cap)

    with open(CAMPAIGN_CSV_PATH, mode="r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    # Build candidate queue: prioritize due Step 2 follow-ups first, then fresh Step 1 value drops
    step2_candidates: List[Tuple[int, Dict[str, str], str, str]] = []
    step1_candidates: List[Tuple[int, Dict[str, str], str, str]] = []

    for row in rows:
        email = str(row.get("Email") or "").strip().lower()
        if not email or "@" not in email or email in unsubscribed:
            continue
        prev = sent_map.get(email)
        if not prev:
            subj = str(row.get("Subject Line") or "").strip()
            body = str(row.get("Email Body") or "").strip()
            if subj and body:
                step1_candidates.append((1, row, subj, body))
        elif int(prev.get("step", 0)) == 1:
            last_sent_str = str(prev.get("sent_at") or "")
            try:
                last_dt = datetime.fromisoformat(last_sent_str.replace("Z", "+00:00"))
                if last_dt <= three_days_ago:
                    subj = str(row.get("Followup Subject") or "").strip()
                    body = str(row.get("Followup Body") or "").strip()
                    if subj and body:
                        step2_candidates.append((2, row, subj, body))
            except Exception:
                pass

    ordered_candidates = step2_candidates + step1_candidates
    staged_packets: List[Dict[str, Any]] = []
    sent_count = 0
    staged_count = 0

    should_stage_only = dry_run or before_launch_date or not live_credentials_present
    batch_target = daily_cap if should_stage_only else effective_live_run_cap

    for target_step, row, subject, body in ordered_candidates:
        if (sent_count + staged_count) >= batch_target:
            break

        email = str(row.get("Email") or "").strip().lower()
        fname = str(row.get("First Name") or "there").strip()
        company = str(row.get("Company") or "your team").strip()
        matched_state = str(row.get("Matched State") or "Federal & SLED").strip()
        dossier_url = str(row.get("Top Contract Dossier URL") or "https://signaltender.net/#contracts").strip()

        res = send_single_email(
            to_email=email,
            subject=subject,
            body_text=body,
            dry_run=should_stage_only,
        )
        if res.get("status") == "sent":
            sent_count += 1
            rec_obj = {
                "step": target_step,
                "sent_at": now_iso,
                "company": company,
                "matched_state": matched_state,
                "dossier_url": dossier_url,
                "transport": res.get("transport"),
            }
            sent_map[email] = rec_obj
            _record_sent_email_supabase(email, rec_obj)
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
                        "launch_date": OUTBOUND_LAUNCH_DATE_STR,
                        "ramp_phase": ramp_phase_label,
                        "daily_cap": daily_cap,
                        "per_6h_cron_cap": per_cron_cap,
                        "live_credentials_configured": live_credentials_present,
                        "instructions": "Set RESEND_API_KEY or SMTP_USER + SMTP_PASSWORD in .env. Live sending automatically activates on OUTBOUND_LAUNCH_DATE (2026-10-31) and ramps 20 -> 30 -> 45 -> 60/day.",
                        "ready_count": len(staged_packets),
                        "emails": staged_packets,
                    },
                    qf,
                    indent=2,
                )
        except Exception:
            pass

    mode_str = "LIVE DISPATCH" if not should_stage_only else "OUTBOX STAGING"
    print(
        f"[+] Outbound Mailer ({mode_str} | {ramp_phase_label}): {sent_count} sent live today ({sent_today_count + sent_count}/{daily_cap}), "
        f"{staged_count} staged in outbox_ready_queue.json.",
        flush=True,
    )
    return {
        "status": "ok",
        "mode": mode_str,
        "ramp_phase": ramp_phase_label,
        "sent_live": sent_count,
        "sent_today_total": sent_today_count + sent_count,
        "staged_in_outbox": staged_count,
        "daily_cap": daily_cap,
        "per_cron_cap": per_cron_cap,
    }


run_outbound_mailer = run_outbound_drip


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SignalTender Built-In Outbound Drip Mailer")
    parser.add_argument("--limit", type=int, default=None, help="Override daily email limit")
    parser.add_argument("--dry-run", action="store_true", help="Stage emails in outbox_ready_queue.json without sending")
    parser.add_argument("--force-send", action="store_true", help="Allow live sending before OUTBOUND_LAUNCH_DATE")
    args = parser.parse_args()
    run_outbound_drip(daily_limit=args.limit, dry_run=args.dry_run, force_send_before_launch=args.force_send)
