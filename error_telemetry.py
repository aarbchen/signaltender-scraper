"""
Closed-Loop Error Telemetry & Discord Resolution Helper (`error_telemetry.py`).
Automatically routes any local or Render Cron runtime exception / alert into:
  1. Local `error_log.txt` (structured human-readable lines)
  2. Remote `POST https://b2b-contract-parser-api.onrender.com/v1/telemetry/report-error`
And when an error is fixed and verified, `send_discord_resolution()` dispatches a
`[RESOLVED]` confirmation message directly to Discord `#alerts` so the operator always
knows in real time what was fixed and that 0 issues remain open.
"""

import os
import sys
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))
load_dotenv()

ERROR_LOG_PATH = os.path.join(BASE_DIR, "error_log.txt")
TELEMETRY_API_BASE = os.getenv(
    "SIGNALTENDER_API_BASE_URL",
    "https://b2b-contract-parser-api.onrender.com",
).rstrip("/")


def configure_utf8_stdio() -> None:
    """Ensure stdout and stderr never fail with Windows cp1252 charmap UnicodeEncodeError."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def report_error(
    source: str,
    message: str,
    severity: str = "ERROR",
    traceback_str: str | None = None,
) -> None:
    """Log an error locally and report it to the central Render telemetry store."""
    configure_utf8_stdio()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    env_label = "render_cron" if os.getenv("RENDER") else "local"
    clean_msg = str(message).strip().replace("\r", " ")
    line = f"[{now_str}] [{env_label.upper()}] [{source}] {clean_msg}\n"
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8", errors="replace") as f:
            f.write(line)
    except Exception:
        pass

    try:
        requests.post(
            f"{TELEMETRY_API_BASE}/v1/telemetry/report-error",
            json={
                "source": source,
                "message": clean_msg[:3800],
                "environment": env_label,
                "severity": severity,
                "traceback": str(traceback_str)[:7500] if traceback_str else None,
            },
            timeout=5,
        )
    except Exception:
        pass


def send_discord_resolution(
    components: str,
    resolved_issues: str,
    fix_verification: str,
    open_error_count: int = 0,
) -> bool:
    """
    Post a `[RESOLVED]` confirmation alert to Discord `#alerts` (`DISCORD_WEBHOOK_URL`)
    so any previous `[ALERT]` in `#alerts` is explicitly followed by a green resolution notice.
    """
    configure_utf8_stdio()
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[!] DISCORD_WEBHOOK_URL not configured; skipping Discord [RESOLVED] post.", flush=True)
        return False

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    status_line = (
        "All Government Portals, Scrapers & APIs Operational (`0 Open Alerts`)"
        if open_error_count == 0
        else f"`{open_error_count}` Remaining Alert(s) Under Investigation"
    )
    content = (
        f"**[RESOLVED] SignalTender Autonomous Self-Healer ({now_str}):**\n"
        f"• **Component(s):** {components}\n"
        f"• **Alert(s) Resolved:** {resolved_issues}\n"
        f"• **Fix & Live Verification:** {fix_verification}\n"
        f"• **Current System Status:** {status_line}"
    )
    try:
        resp = requests.post(
            webhook_url,
            json={"content": content[:1990], "flags": 4},
            timeout=10,
        )
        resp.raise_for_status()
        print("[+] Dispatched [RESOLVED] confirmation to Discord #alerts.", flush=True)
        return True
    except Exception as exc:
        print(f"[!] Failed to dispatch Discord [RESOLVED] alert: {exc}", flush=True)
        return False
