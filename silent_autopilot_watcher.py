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
from zoneinfo import ZoneInfo

from error_telemetry import configure_utf8_stdio
import auto_error_healer

configure_utf8_stdio()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROADMAP_PATH = os.path.join(BASE_DIR, "daily_expansion_roadmap.json")
CHECK_INTERVAL_SECONDS = 900  # 15 minutes


def is_daily_expansion_due() -> tuple[bool, str]:
    """Return (True, reason) if today's daily expansion has not been completed yet."""
    if not os.path.exists(ROADMAP_PATH):
        return False, ""
    try:
        with open(ROADMAP_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        last_date = str(data.get("last_completed_date") or "").strip()
        now_central = datetime.now(ZoneInfo("America/Chicago"))
        today_str = now_central.strftime("%Y-%m-%d")

        pending = [item for item in data.get("items", []) if item.get("status") == "pending"]
        if not pending:
            return False, ""

        # If last_completed_date is strictly before today AND it's >= 2:00 AM Central
        # (or if last_completed_date is more than 1 day behind), trigger catch-up immediately.
        if last_date < today_str and now_central.hour >= 2:
            next_item = pending[0]
            day_num = next_item.get("day")
            st_name = next_item.get("scraper", {}).get("state_name")
            api_num = next_item.get("api", {}).get("api_number")
            return (
                True,
                f"Daily expansion due for {today_str} (last_completed_date={last_date}): "
                f"Day {day_num} — {st_name} Scraper + API #{api_num}",
            )
    except Exception:
        pass
    return False, ""


def main() -> int:
    print(
        "[*] Silent Autopilot & Self-Healing Watcher active in background "
        "(zero chat interruptions unless an error or new daily build requires action).",
        flush=True,
    )
    while True:
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
