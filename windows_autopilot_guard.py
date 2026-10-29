"""
OS-Level Windows Task Scheduler Watchdog (`windows_autopilot_guard.py`).
=========================================================================
Runs independently of VS Code via Windows Task Scheduler (`\\SignalTender_Autopilot_Guard`)
every 30 minutes and at Windows logon.

Responsibilities:
  1. Verifies whether `silent_autopilot_watcher.py` is actively running inside VS Code
     by checking `.autopilot_watcher_heartbeat.json` and verifying the Windows PID.
  2. Even if VS Code is closed/reset, runs `omniscient_auditor.py` and `auto_error_healer.py`
     in the OS background to audit Products, Acquisition Channels, and Website, auto-fix any
     detected bugs, codify permanent anti-regression rules (`learned_anti_regression_rules.json`
     + `AGENTS.md`), and dispatch ONLY `[RESOLVED]` notifications to Discord `#alerts`
     (never spamming raw `[ALERT]` notifications on bug detection).
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
    """Silently record runtime error to telemetry for autonomous self-healing (resolved-only Discord policy)."""
    report_error("windows_autopilot_guard.py", str(content))
    return True


def main() -> int:
    alive, detail = is_watcher_alive()
    if alive:
        print(f"[+] Watcher alive: {detail}", flush=True)
        return 0

    # Watcher is NOT alive (VS Code was reset or closed).
    # Enforce RULE-006 & Resolved-only policy: only run omniscient_auditor.py at night (11:00 PM – 6:00 AM)
    # when the user is away (>= 30m idle), auto-fix any deterministic issues, and dispatch [RESOLVED] only when healed.
    try:
        import omniscient_auditor
        allowed, _ = omniscient_auditor.is_nighttime_and_user_away(min_idle_seconds=1800)
        if not allowed:
            return 0
        omniscient_auditor.run_omniscient_audit(mode="fast", auto_fix=True, auto_deploy=True, force_now=True)
    except Exception:
        pass
    try:
        auto_error_healer.run_healer(clear_resolved=True, run_smoke=False)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        report_error("windows_autopilot_guard.py", f"Watchdog exception: {exc}")
        sys.exit(1)
