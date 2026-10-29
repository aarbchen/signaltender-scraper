"""
Silent Event-Driven Autopilot & Self-Healing Watcher (`silent_autopilot_watcher.py`).
=====================================================================================
Runs silently in the background (`IsDaemon=True`) without cluttering the user's chat window.
Every 15 minutes, it quietly checks:
  1. Remote Render Cron telemetry (`GET /v1/telemetry/errors?status=open`) and local `error_log.txt`.
  2. Daily 50-State & 58-API expansion status (`last_completed_date` in `daily_expansion_roadmap.json`).

If everything is healthy (`0` open errors) and today's expansion is already completed,
it stays 100% silent in the background (producing ZERO chat messages).
ONLY when real agent action is needed (either a new day's expansion is due, or an open
code error is detected in telemetry), it prints a `[WAKEUP_AGENT]` payload and exits (`0`),
which automatically wakes Argon in the conversation to execute the fix or daily build.
"""

import json
import os
import sys
import time
from datetime import datetime

from error_telemetry import configure_utf8_stdio
import auto_error_healer

configure_utf8_stdio()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROADMAP_PATH = os.path.join(BASE_DIR, "daily_expansion_roadmap.json")
HEARTBEAT_PATH = os.path.join(BASE_DIR, ".autopilot_watcher_heartbeat.json")
GUARD_STATE_PATH = os.path.join(BASE_DIR, ".autopilot_guard_state.json")
CHECK_INTERVAL_SECONDS = 900  # 15 minutes


def claim_primary_watcher() -> None:
    """Elect the most recently launched watcher PID as the primary wakeup owner across tabs."""
    now_ts = time.time()
    now_iso = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    try:
        with open(HEARTBEAT_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {"pid": os.getpid(), "primary_pid": os.getpid(), "timestamp": now_ts, "updated_at": now_iso},
                f,
            )
    except Exception:
        pass


def is_primary_watcher() -> bool:
    """Return True if this process is the elected primary watcher (or if the primary PID is no longer alive)."""
    if not os.path.exists(HEARTBEAT_PATH):
        return True
    try:
        with open(HEARTBEAT_PATH, "r", encoding="utf-8") as f:
            hb = json.load(f)
        prim = int(hb.get("primary_pid") or hb.get("pid") or 0)
        if prim <= 0 or prim == os.getpid():
            return True
        # Check if primary_pid is still alive on Windows/POSIX
        try:
            os.kill(prim, 0)
            return False
        except OSError:
            return True
    except Exception:
        return True


def write_watcher_heartbeat() -> None:
    """Record live PID and timestamp so the OS-level Windows Task Scheduler guard knows the watcher is alive."""
    now_ts = time.time()
    now_iso = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    try:
        prim = os.getpid()
        if os.path.exists(HEARTBEAT_PATH):
            try:
                with open(HEARTBEAT_PATH, "r", encoding="utf-8") as rf:
                    old_hb = json.load(rf)
                old_prim = int(old_hb.get("primary_pid") or 0)
                if old_prim > 0 and old_prim != os.getpid():
                    try:
                        os.kill(old_prim, 0)
                        prim = old_prim
                    except OSError:
                        prim = os.getpid()
            except Exception:
                pass
        with open(HEARTBEAT_PATH, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "primary_pid": prim, "timestamp": now_ts, "updated_at": now_iso}, f)
    except Exception:
        pass

    # If the OS guard previously alerted #alerts that VS Code was offline, post a green recovery notice
    if os.path.exists(GUARD_STATE_PATH):
        try:
            with open(GUARD_STATE_PATH, "r", encoding="utf-8") as f:
                st = json.load(f)
            if st.get("alerted_offline"):
                import requests
                webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
                if webhook_url:
                    requests.post(
                        webhook_url,
                        json={
                            "content": (
                                f"**[RESOLVED] SignalTender Autopilot Watcher Resumed ({now_iso}):**\n"
                                f"• **Status:** `silent_autopilot_watcher.py` (`PID {os.getpid()}`) is back online inside VS Code.\n"
                                "• **Coverage:** Autonomous self-healing & daily 50-state / 58-API expansion active."
                            ),
                            "flags": 4,
                        },
                        timeout=10,
                    )
                with open(GUARD_STATE_PATH, "w", encoding="utf-8") as wf:
                    json.dump({"alerted_offline": False, "recovered_at": now_iso}, wf)
        except Exception:
            pass


def is_daily_expansion_due() -> tuple[bool, str]:
    """Return (True, reason) if today's 5-scraper + 5-API daily expansion quota has not been completed yet."""
    if not os.path.exists(ROADMAP_PATH):
        return False, ""
    try:
        with open(ROADMAP_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        daily_quota = int(data.get("daily_quota") or 5)
        last_date = str(data.get("last_completed_date") or "").strip()
        completed_today_date = str(data.get("completed_today_date") or "").strip()
        completed_today_count = int(data.get("completed_today_count") or 0)

        now_local = datetime.now().astimezone()
        today_str = now_local.strftime("%Y-%m-%d")
        if completed_today_date != today_str:
            # Count any items explicitly stamped with today_str in completed_at
            completed_today_count = sum(
                1
                for item in data.get("items", [])
                if item.get("status") == "completed" and str(item.get("completed_at") or "").startswith(today_str)
            )

        pending = [item for item in data.get("items", []) if item.get("status") == "pending"]
        if not pending:
            return False, ""

        # Trigger whenever (< daily_quota completed today AND >= 2:00 AM Central) OR last_completed_date < today_str
        if (completed_today_count < daily_quota or last_date < today_str) and now_local.hour >= 2:
            remaining = max(1, daily_quota - completed_today_count)
            due_slice = pending[:remaining]
            summary_parts = []
            for it in due_slice:
                d_num = it.get("day")
                s_name = (it.get("portal") or it.get("scraper") or {}).get("state_name")
                a_num = it.get("api", {}).get("api_number")
                summary_parts.append(f"Item {d_num} ({s_name} Scraper + API #{a_num})")
            return (
                True,
                f"5x Daily Expansion Quota ({completed_today_count}/{daily_quota} completed for {today_str}; "
                f"{len(due_slice)} remaining today): " + ", ".join(summary_parts),
            )
    except Exception:
        pass
    return False, ""


def main() -> int:
    claim_primary_watcher()
    print(
        "[*] Silent Autopilot & Self-Healing Watcher active in background "
        "(zero chat interruptions unless an error or new daily build requires action).",
        flush=True,
    )
    while True:
        write_watcher_heartbeat()
        if not is_primary_watcher():
            time.sleep(CHECK_INTERVAL_SECONDS)
            continue
        try:
            import rapidapi_headless_publisher
            rapidapi_headless_publisher.keepalive_rapidapi_session()
        except Exception:
            pass
        try:
            import outbound_reply_responder
            outbound_reply_responder.run_reply_responder()
        except Exception:
            pass
        # 1. Check for any open runtime alerts in Render telemetry or local error_log.txt
        remote_errors = auto_error_healer.fetch_remote_open_errors()
        local_errors = auto_error_healer.read_local_unacknowledged_errors()
        contract_issues = auto_error_healer.verify_scraper_contracts_and_rls_safety()

        if remote_errors or local_errors or contract_issues:
            print(
                "\n[WAKEUP_AGENT: SELF_HEALING_REQUIRED]\n"
                f"Open remote errors: {len(remote_errors)} | "
                f"Local errors: {len(local_errors)} | "
                f"Contract issues: {len(contract_issues)}\n"
                "Please diagnose and fix the reported issue, run auto_error_healer.py --clear-resolved, "
                "and restart silent_autopilot_watcher.py.",
                flush=True,
            )
            return 0

        # 2. Check if today's 2:00 AM Central daily expansion is due
        due, reason = is_daily_expansion_due()
        if due:
            print(
                f"\n[WAKEUP_AGENT: DAILY_EXPANSION_DUE]\n{reason}\n"
                "Please execute the next pending item in daily_expansion_roadmap.json end-to-end "
                "and restart silent_autopilot_watcher.py.",
                flush=True,
            )
            return 0

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    sys.exit(main())

