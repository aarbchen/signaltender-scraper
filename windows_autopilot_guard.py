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
    # 1. Always keep RapidAPI Studio rolling session (`connect.sid`) alive 24/7 via GraphQL POST
    #    and automatically publish any unposted completed roadmap APIs if session is active.
    try:
        import rapidapi_headless_publisher
        rapidapi_headless_publisher.keepalive_rapidapi_session()
        rapidapi_headless_publisher.auto_sync_unposted_apis(commit_and_push=True)
    except Exception:
        pass

    # 2. Check outbound replies 24/7 even when VS Code is reset or closed
    try:
        import outbound_reply_responder
        outbound_reply_responder.run_reply_responder()
    except Exception:
        pass

    import subprocess
    python_exe = os.path.join(BASE_DIR, "daas_env", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable
    no_win_flag = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

    alive, detail = is_watcher_alive()
    if not alive:
        # Watcher is NOT alive (VS Code was reset or closed).
        # Respawn `silent_autopilot_watcher.py` using python.exe + CREATE_NO_WINDOW so stdout/stderr are never None.
        try:
            watcher_script = os.path.join(BASE_DIR, "silent_autopilot_watcher.py")
            proc = subprocess.Popen([python_exe, watcher_script], cwd=BASE_DIR, creationflags=no_win_flag)
            print(f"[*] Respawned silent_autopilot_watcher.py (PID {proc.pid})", flush=True)
        except Exception:
            pass

    # Enforce RULE-006 & Resolved-only policy: at night (11:00 PM – 6:00 AM) when user is away (>= 15m idle),
    # ensure omniscient_auditor.py runs if watcher was dead OR if omniscient_audit_report.json is > 45m old.
    try:
        import omniscient_auditor
        allowed, _ = omniscient_auditor.is_nighttime_and_user_away(min_idle_seconds=900)
        report_path = os.path.join(BASE_DIR, "omniscient_audit_report.json")
        report_age = (time.time() - os.path.getmtime(report_path)) if os.path.exists(report_path) else 999999.0
        if allowed and (not alive or report_age > 2700):
            subprocess.run(
                [
                    python_exe,
                    os.path.join(BASE_DIR, "omniscient_auditor.py"),
                    "--mode",
                    "fast",
                    "--auto-deploy",
                    "--force-now",
                ],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                timeout=900,
                creationflags=no_win_flag,
            )
    except Exception:
        pass
    if alive:
        print(f"[+] Watcher alive: {detail}", flush=True)
        return 0
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
