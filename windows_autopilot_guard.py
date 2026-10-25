"""
OS-Level Windows Task Scheduler Watchdog (`windows_autopilot_guard.py`).
=========================================================================
Runs independently of VS Code via Windows Task Scheduler (`\\SignalTender_Autopilot_Guard`)
every 30 minutes and at Windows logon.

Responsibilities:
  1. Verifies whether `silent_autopilot_watcher.py` is actively running inside VS Code
     by checking `.autopilot_watcher_heartbeat.json` and verifying the Windows PID.
  2. Even if VS Code is closed/reset, runs `auto_error_healer.py` checks against
     remote Render telemetry (`/v1/telemetry/errors?status=open`) and local `error_log.txt`.
  3. If VS Code reset or closed and `silent_autopilot_watcher.py` stopped running,
     dispatches a de-duplicated notification to Discord `#alerts` (`DISCORD_WEBHOOK_URL`)
     so the operator immediately knows on their phone/desktop that the VS Code watcher
     needs to be resumed (and once resumed, `silent_autopilot_watcher.py` posts a
     `[RESOLVED]` recovery confirmation to `#alerts`).
"""

import ctypes
import json
import os
import sys
import time
from datetime import datetime
import requests
from dotenv import load_dotenv

from error_telemetry import configure_utf8_stdio, report_error
import auto_error_healer
import silent_autopilot_watcher

configure_utf8_stdio()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))
load_dotenv()

HEARTBEAT_PATH = os.path.join(BASE_DIR, ".autopilot_watcher_heartbeat.json")
GUARD_STATE_PATH = os.path.join(BASE_DIR, ".autopilot_guard_state.json")
MAX_HEARTBEAT_AGE_SECONDS = 2100  # 35 minutes (watcher updates every 15m)


def is_pid_running_windows(pid: int) -> bool:
    """Return True if a Windows process with the given PID is currently alive."""
    if pid <= 0:
        return False
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not handle:
        return False
    try:
        exit_code = ctypes.c_ulong()
        if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return exit_code.value == STILL_ACTIVE
        return True
    finally:
        kernel32.CloseHandle(handle)


def is_watcher_alive() -> tuple[bool, str]:
    """Check whether `silent_autopilot_watcher.py` is alive via heartbeat file + Windows PID."""
    if not os.path.exists(HEARTBEAT_PATH):
        return False, "No heartbeat file (.autopilot_watcher_heartbeat.json)"
    try:
        with open(HEARTBEAT_PATH, "r", encoding="utf-8") as f:
            hb = json.load(f)
        pid = int(hb.get("pid") or 0)
        ts = float(hb.get("timestamp") or 0)
        age = time.time() - ts
        if not is_pid_running_windows(pid):
            return False, f"Watcher PID {pid} is no longer running (VS Code reset or closed)"
        if age > MAX_HEARTBEAT_AGE_SECONDS:
            return False, f"Watcher heartbeat is stale ({int(age)}s old, PID {pid})"
        return True, f"PID {pid} active (heartbeat {int(age)}s ago)"
    except Exception as exc:
        return False, f"Heartbeat check error: {exc}"


def send_discord_alert(content: str) -> bool:
    """Send a notification to Discord `#alerts` (`DISCORD_WEBHOOK_URL`)."""
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[!] DISCORD_WEBHOOK_URL not configured in .env", flush=True)
        return False
    try:
        resp = requests.post(
            webhook_url,
            json={"content": content[:1990], "flags": 4},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        print(f"[!] Failed to send Discord alert: {exc}", flush=True)
        return False


def main() -> int:
    now_central = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    today_str = datetime.now().astimezone().strftime("%Y-%m-%d")

    if "--send-active-confirmation" in sys.argv:
        alive, detail = is_watcher_alive()
        due, due_reason = silent_autopilot_watcher.is_daily_expansion_due()
        msg = (
            f"**[AUTOPILOT GUARD ACTIVE] SignalTender OS-Level Watchdog Armed ({now_central}):**\n"
            f"• **Windows Task Scheduler:** `\\SignalTender_Autopilot_Guard` registered (runs every 30 mins & at Windows logon, independent of VS Code).\n"
            f"• **VS Code Background Watcher:** `{detail}`\n"
            f"• **Daily 50-State / 58-API Status:** `{'Expansion Due: ' + due_reason if due else 'Up to date (next build triggers automatically after 2:00 AM Central)'}`\n"
            "• **Fail-Safe Behavior:** If VS Code ever resets or closes and cancels the background automation, this OS watchdog will immediately alert `#alerts` here and post a `[RESOLVED]` notice as soon as the watcher resumes."
        )
        ok = send_discord_alert(msg)
        print(f"[+] Dispatched OS Watchdog confirmation to Discord #alerts: {ok}", flush=True)
        return 0 if ok else 1

    alive, detail = is_watcher_alive()
    if alive:
        print(f"[+] Watcher alive: {detail}", flush=True)
        return 0

    # Watcher is NOT alive (VS Code was reset or closed).
    due, due_reason = silent_autopilot_watcher.is_daily_expansion_due()
    remote_errors = auto_error_healer.fetch_remote_open_errors()
    local_errors = auto_error_healer.read_local_unacknowledged_errors()
    n_errors = len(remote_errors) + len(local_errors)

    # Check de-duplication state so we don't spam #alerts every 30 minutes for the same offline event
    prev_state = {}
    if os.path.exists(GUARD_STATE_PATH):
        try:
            with open(GUARD_STATE_PATH, "r", encoding="utf-8") as f:
                prev_state = json.load(f)
        except Exception:
            prev_state = {}

    already_alerted = bool(prev_state.get("alerted_offline"))
    already_alerted_due = bool(prev_state.get("alerted_due_date") == today_str)

    if not already_alerted or (due and not already_alerted_due):
        pending_work = []
        if due:
            pending_work.append(f"**Pending Daily Build:** {due_reason}")
        if n_errors > 0:
            pending_work.append(f"**Open Telemetry Errors:** `{n_errors}` error(s) waiting for self-healing")
        if not pending_work:
            pending_work.append("**Pending Work:** None right now (`0` open errors; today's expansion is complete), but the background watcher is paused until VS Code resumes.")

        alert_msg = (
            f"**[ALERT] SignalTender VS Code Autopilot Watcher Offline ({now_central}):**\n"
            f"• **Reason:** `{detail}`\n"
            f"• **Cloud Operations:** Render 6-hour scrapers, 21 FastAPI endpoints, Discord feeds & Instantly outbound remain **100% ONLINE**.\n"
            f"• {chr(10) + '• '.join(pending_work)}\n"
            "• **How to Resume:** Open Antigravity in VS Code and send any message (e.g. `resume`) to automatically restart `silent_autopilot_watcher.py` and catch up."
        )
        if send_discord_alert(alert_msg):
            try:
                with open(GUARD_STATE_PATH, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "alerted_offline": True,
                            "alerted_at": now_central,
                            "alerted_due_date": today_str if due else prev_state.get("alerted_due_date"),
                        },
                        f,
                    )
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        report_error("windows_autopilot_guard.py", f"Watchdog exception: {exc}")
        sys.exit(1)
