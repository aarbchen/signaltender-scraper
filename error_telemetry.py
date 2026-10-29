"""
Closed-Loop Error Telemetry, Self-Improving Rule Ledger & Resolved-Only Discord Helper (`error_telemetry.py`).
==============================================================================================================
1. Silently routes any local or Render Cron runtime exception / bug detection into:
   - Local `error_log.txt`
   - Remote `POST https://b2b-contract-parser-api.onrender.com/v1/telemetry/report-error`
   WITHOUT spamming Discord `#alerts` with raw `[ALERT]` detection notifications.
2. When an issue is fixed and verified by `omniscient_auditor.py` or `auto_error_healer.py`:
   - `codify_learned_rule()` / `derive_and_codify_rule_from_fix()` permanently records an
     anti-regression rule in `d:\\Daas\\learned_anti_regression_rules.json` AND syncs it into
     `d:\\Daas\\AGENTS.md` so the system improves itself with every fix and never repeats mistakes.
   - `send_discord_resolution()` dispatches a single `[RESOLVED]` confirmation message to
     Discord `#alerts` containing the fix details AND the newly codified prevention rule.
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))
load_dotenv()

ERROR_LOG_PATH = os.path.join(BASE_DIR, "error_log.txt")
LEARNED_RULES_PATH = os.path.join(BASE_DIR, "learned_anti_regression_rules.json")
AGENTS_MD_PATH = os.path.join(BASE_DIR, "AGENTS.md")
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


def load_learned_rules() -> list[dict]:
    """Load all persisted self-improvement anti-regression rules from `learned_anti_regression_rules.json`."""
    if not os.path.exists(LEARNED_RULES_PATH):
        return []
    try:
        with open(LEARNED_RULES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("rules"), list):
            return data["rules"]
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _sync_rule_to_agents_md(rule_entry: dict) -> None:
    """Append newly learned anti-regression rules to Section 9 of `d:\\Daas\\AGENTS.md` (deduplicated by rule_id)."""
    if not os.path.exists(AGENTS_MD_PATH):
        return
    try:
        rule_id = str(rule_entry.get("rule_id") or "").strip()
        if not rule_id:
            return
        with open(AGENTS_MD_PATH, "r", encoding="utf-8") as f:
            agents_txt = f.read()
        if f"[{rule_id}]" in agents_txt:
            return

        section_header = "9. **Autonomous Self-Improving Anti-Regression Rule Ledger (`learned_anti_regression_rules.json` & `omniscient_auditor.py`):**"
        bullet = (
            f"   - **`[{rule_id}]` ({rule_entry.get('category', 'System')} — `{rule_entry.get('source', 'omniscient_auditor.py')}`):** "
            f"{rule_entry.get('prevention_rule', '').strip()}"
        )
        if section_header not in agents_txt:
            addition = (
                f"\n\n{section_header}\n"
                "   - **Resolved-Only Alerting & Mandatory Rule Codification:** Never emit raw `[ALERT]` notifications to Discord when a bug is detected; fix the bug automatically, codify a permanent prevention rule into `learned_anti_regression_rules.json` and `AGENTS.md`, and emit only a `[RESOLVED]` notification.\n"
                f"{bullet}\n"
            )
            updated_txt = agents_txt.rstrip() + addition
        else:
            updated_txt = agents_txt.rstrip() + "\n" + bullet + "\n"

        with open(AGENTS_MD_PATH, "w", encoding="utf-8") as wf:
            wf.write(updated_txt)
    except Exception:
        pass


def codify_learned_rule(
    rule_id: str,
    category: str,
    source: str,
    bug_signature: str,
    root_cause: str,
    fix_applied: str,
    prevention_rule: str,
    auto_Sync_agents_md: bool = True,
) -> dict:
    """
    Persist or update a permanent anti-regression rule in `learned_anti_regression_rules.json`
    and sync it into `AGENTS.md` so the system never repeats the same mistake.
    """
    configure_utf8_stdio()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rules = load_learned_rules()
    clean_id = str(rule_id).strip().upper()

    existing_entry = None
    for item in rules:
        if str(item.get("rule_id") or "").upper() == clean_id:
            existing_entry = item
            break

    if existing_entry is not None:
        existing_entry["last_healed_at"] = now_iso
        existing_entry["times_triggered_and_healed"] = int(existing_entry.get("times_triggered_and_healed") or 1) + 1
        existing_entry["fix_applied"] = fix_applied
        existing_entry["prevention_rule"] = prevention_rule
        target_entry = existing_entry
    else:
        target_entry = {
            "rule_id": clean_id,
            "category": category,
            "source": source,
            "bug_signature": bug_signature[:300],
            "root_cause": root_cause[:500],
            "fix_applied": fix_applied[:500],
            "prevention_rule": prevention_rule[:600],
            "created_at": now_iso,
            "last_healed_at": now_iso,
            "times_triggered_and_healed": 1,
        }
        rules.append(target_entry)

    payload = {
        "schema_version": "1.0",
        "description": (
            "SignalTender Self-Improving Anti-Regression Rule Ledger. "
            "Automatically populated by omniscient_auditor.py and auto_error_healer.py "
            "on every bug fix and enforced on every subsequent run."
        ),
        "updated_at": now_iso,
        "total_rules": len(rules),
        "rules": rules,
    }
    try:
        with open(LEARNED_RULES_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    if auto_Sync_agents_md:
        _sync_rule_to_agents_md(target_entry)
    return target_entry


def derive_and_codify_rule_from_fix(
    components: str,
    resolved_issues: str,
    fix_verification: str,
) -> dict:
    """
    Automatically synthesize and persist a permanent prevention rule from any resolved bug
    so every single fix across Products, Acquisition Channels, and Website adds a rule.
    """
    comp_clean = str(components or "system").strip()
    issue_clean = str(resolved_issues or "").strip()
    fix_clean = str(fix_verification or "").strip()
    lower_blob = f"{comp_clean} {issue_clean} {fix_clean}".lower()

    if "portal" in lower_blob or "state" in lower_blob or "jurisdiction" in lower_blob:
        rule_id = "RULE-PORTAL-PARITY-SYNC"
        category = "Website & Portal Parity"
        prevention = (
            "Enforce 100% portal/state count and abbreviation roll-call parity across index.html, "
            "apis.html, pseo_generator.py, and all outbound/conversion surfaces before any commit."
        )
    elif "api" in lower_blob and ("count" in lower_blob or "catalog" in lower_blob or "matrix" in lower_blob or "mcp" in lower_blob):
        rule_id = "RULE-API-CATALOG-MCP-PARITY"
        category = "Products & API Catalog"
        prevention = (
            "Enforce 1:1 parity across index.html, apis.html, CATALOG, API_META, mcp.py, "
            "mcp-server/index.js, and seed_rapidapi_telemetry.py on every API update."
        )
    elif "campaign_leads" in lower_blob or "outbox" in lower_blob or "outreach" in lower_blob or "reply" in lower_blob:
        rule_id = "RULE-ACQUISITION-OUTBOUND-SYNC"
        category = "Acquisition Channels"
        prevention = (
            "Verify every outbound lead row in campaign_leads.csv and outbox_ready_queue.json has "
            "live /contracts/rfp/<slug>.html URLs, current portal/API counts, and zero DNC addresses."
        )
    elif "sitemap" in lower_blob or "pseo" in lower_blob or "contracts/rfp" in lower_blob or "json-ld" in lower_blob:
        rule_id = "RULE-PSEO-SITEMAP-PARITY"
        category = "Acquisition & Programmatic SEO"
        prevention = (
            "Enforce 1:1 parity between window.SIGNALTENDER_CONTRACTS, /contracts/rfp/*.html static files, "
            "and sitemap.xml with valid JSON-LD and cache-busted OpenGraph tags."
        )
    elif "overflow" in lower_blob or "375" in lower_blob or "viewport" in lower_blob or "clipped" in lower_blob:
        rule_id = "RULE-VIEWPORT-NO-OVERFLOW"
        category = "Website Mobile & Desktop UX"
        prevention = (
            "Enforce zero horizontal overflow or text clipping at 375px mobile and 1024px/1280px desktop "
            "viewports using min-w-0, flex-wrap, and bounded badge containers."
        )
    elif "scraper" in lower_blob or "timedelta" in lower_blob or "upsert" in lower_blob or "hash(" in lower_blob:
        rule_id = "RULE-SCRAPER-DETERMINISM-RLS"
        category = "Products & Scrapers"
        prevention = (
            "Enforce async def run_scraper(push_to_db=True), deterministic SHA-256 IDs, anchored dates, "
            "RLS-safe SELECT + .insert(), and silent telemetry across all scraper modules."
        )
    else:
        normalized_sig = re.sub(r"\d+", "N", issue_clean[:120].lower())
        digest = hashlib.sha256(f"{comp_clean}::{normalized_sig}".encode("utf-8")).hexdigest()[:6].upper()
        rule_id = f"RULE-AUTO-{digest}"
        category = "Autonomous Self-Healing"
        prevention = (
            f"Continuously audit `{comp_clean}` for `{issue_clean[:140]}` in omniscient_auditor.py "
            f"and automatically apply `{fix_clean[:140]}` prior to deployment."
        )

    return codify_learned_rule(
        rule_id=rule_id,
        category=category,
        source=comp_clean,
        bug_signature=issue_clean[:300],
        root_cause=issue_clean[:400],
        fix_applied=fix_clean[:400],
        prevention_rule=prevention,
        auto_Sync_agents_md=True,
    )


def report_error(
    source: str,
    message: str,
    severity: str = "ERROR",
    traceback_str: str | None = None,
) -> None:
    """
    Silently log an error locally and report it to the central Render telemetry store
    for autonomous self-healing (NEVER spams raw [ALERT] detection messages to Discord).
    """
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
    learned_rule: str | None = None,
) -> bool:
    """
    Codify a permanent anti-regression rule for the fix and post a single `[RESOLVED]`
    confirmation alert to Discord `#alerts` (`DISCORD_WEBHOOK_URL`).
    """
    configure_utf8_stdio()
    rule_entry = derive_and_codify_rule_from_fix(components, resolved_issues, fix_verification)
    rule_line = learned_rule or f"`[{rule_entry['rule_id']}]` {rule_entry['prevention_rule']}"

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[!] DISCORD_WEBHOOK_URL not configured; skipping Discord [RESOLVED] post.", flush=True)
        return False

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    status_line = (
        "All Products, Acquisition Channels & Website Operational (`0 Open Alerts`)"
        if open_error_count == 0
        else f"`{open_error_count}` Remaining Item(s) Queued for Auto-Healing"
    )
    content = (
        f"**[RESOLVED] SignalTender Autonomous Self-Healer ({now_str}):**\n"
        f"• **Component(s):** {components}\n"
        f"• **Bug(s) Fixed:** {resolved_issues}\n"
        f"• **Fix & Live Verification:** {fix_verification}\n"
        f"• **Self-Improvement Rule Added:** {rule_line}\n"
        f"• **Current System Status:** {status_line}"
    )
    try:
        resp = requests.post(
            webhook_url,
            json={"content": content[:1990], "flags": 4},
            timeout=10,
        )
        resp.raise_for_status()
        print("[+] Dispatched [RESOLVED] confirmation (with new anti-regression rule) to Discord #alerts.", flush=True)
        return True
    except Exception as exc:
        print(f"[!] Failed to dispatch Discord [RESOLVED] alert: {exc}", flush=True)
        return False
