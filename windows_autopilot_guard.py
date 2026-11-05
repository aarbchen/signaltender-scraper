"""
OS-Level Windows Task Scheduler Watchdog (`windows_autopilot_guard.py`).
Runs every 30 minutes via Windows Task Scheduler using `pythonw.exe` with ZERO console windows
and ZERO child subprocesses unless `silent_autopilot_watcher.py` needs to be respawned.
"""

import ctypes
import json
import os
import subprocess
import sys
import time
from dotenv import load_dotenv

from error_telemetry import configure_utf8_stdio, report_error

configure_utf8_stdio()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))
load_dotenv()

HEARTBEAT_PATH = os.path.join(BASE_DIR, ".autopilot_watcher_heartbeat.json")
MAX_HEARTBEAT_AGE_SECONDS = 2700  # 45 minutes


def is_pid_running_windows(pid: int) -> bool:
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
    if not os.path.exists(HEARTBEAT_PATH):
        return False, "No heartbeat file"
    try:
        with open(HEARTBEAT_PATH, "r", encoding="utf-8") as f:
            hb = json.load(f)
        pid = int(hb.get("pid") or hb.get("primary_pid") or 0)
        ts = float(hb.get("timestamp") or 0)
        if not is_pid_running_windows(pid):
            return False, f"Watcher PID {pid} not running"
        if ts > 0 and (time.time() - ts) > MAX_HEARTBEAT_AGE_SECONDS:
            return False, f"Watcher heartbeat stale ({int(time.time() - ts)}s)"
        return True, f"PID {pid} active"
    except Exception as exc:
        return False, f"Heartbeat error: {exc}"


def main() -> int:
    try:
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)
    except Exception:
        pass

    alive, _ = is_watcher_alive()
    if alive:
        return 0

    pythonw_exe = os.path.join(BASE_DIR, "daas_env", "Scripts", "pythonw.exe")
    if not os.path.exists(pythonw_exe):
        pythonw_exe = sys.executable
    try:
        watcher_script = os.path.join(BASE_DIR, "silent_autopilot_watcher.py")
        subprocess.Popen([pythonw_exe, watcher_script], cwd=BASE_DIR, creationflags=0x08000000 | 0x00004000)
    except Exception as exc:
        report_error("windows_autopilot_guard.py", f"Failed to respawn silent_autopilot_watcher.py: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
