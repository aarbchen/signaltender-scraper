"""
Closed-Loop Error Telemetry Helper (`error_telemetry.py`).
Automatically routes any local or Render Cron runtime exception / alert into:
  1. Local `error_log.txt` (structured JSONL + human-readable lines)
  2. Remote `POST https://b2b-contract-parser-api.onrender.com/v1/telemetry/report-error`
so `auto_error_healer.py` and `verify_site_integrity.py` automatically receive and surface
all errors from both local runs and remote Render 6-hour cron jobs without requiring
manual screenshots of Discord `#alerts`.
"""

import os
import sys
from datetime import datetime, timezone
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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
    line = f"[{now_str}] [{env_label.upper()}] [{source}] {message}\n"
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
                "message": str(message)[:3800],
                "environment": env_label,
                "severity": severity,
                "traceback": str(traceback_str)[:7500] if traceback_str else None,
            },
            timeout=5,
        )
    except Exception:
        pass

