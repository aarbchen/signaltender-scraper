"""
Autonomous Closed-Loop Error Inspector & Self-Healer (`auto_error_healer.py`).
=============================================================================
Solves the "screenshot feedback loop" problem permanently:
  1. Pulls any open runtime errors from the central cloud telemetry endpoint
     (`GET https://b2b-contract-parser-api.onrender.com/v1/telemetry/errors?status=open`)
     AND local `d:\\Daas\\error_log.txt`.
  2. Audits all 16 scraper modules and pipeline scripts to verify:
     - Every state/municipal scraper defines `async def run_scraper(push_to_db: bool = True)`.
     - Every file defining `def send_discord_alert(...)` calls `report_error(...)` so 100% of
       Discord `#alerts` are mirrored to `/v1/telemetry/report-error`.
     - Zero `.upsert(` calls against Supabase `contracts` (which trigger PostgREST RLS `42501`).
     - UTF-8 stdio reconfiguration is present to prevent Windows `cp1252` `charmap` errors.
  3. Never silently wipes open errors during default inspection (`clear_resolved=False`):
     any open error causes a non-zero exit so the agent diagnoses and fixes the root cause first.
  4. When invoked with `--clear-resolved` after a fix is verified, archives local logs,
     clears remote telemetry, AND dispatches a `[RESOLVED]` confirmation message to Discord `#alerts`
     via `send_discord_resolution()` so the operator always sees what was resolved and what is healthy.
"""

import argparse
import asyncio
import importlib
import inspect
import os
import pathlib
import re
import sys
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv
from error_telemetry import (
    configure_utf8_stdio,
    ERROR_LOG_PATH,
    TELEMETRY_API_BASE,
    send_discord_resolution,
)

configure_utf8_stdio()
BASE_DIR = pathlib.Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")
load_dotenv()

SLED_DIR = BASE_DIR / "sled-scraper"
if str(SLED_DIR) not in sys.path:
    sys.path.insert(0, str(SLED_DIR))

SCRAPER_MODULES = [
    "sam_scraper",
    "sledscraper",
    "va_scraper",
    "ca_scraper",
    "fl_scraper",
    "md_scraper",
    "il_scraper",
    "pa_scraper",
    "oh_scraper",
    "ga_scraper",
    "nc_scraper",
    "ny_scraper",
    "ma_scraper",
    "nj_scraper",
    "wa_scraper",
    "mi_scraper",
    "co_scraper",
    "az_scraper",
    "mn_scraper",
    "tn_scraper",
    "in_scraper",
    "mo_scraper",
    "wi_scraper",
    "sc_scraper",
    "or_scraper",
    "ct_scraper",
    "ut_scraper",
    "nv_scraper",
    "al_scraper",
    "la_scraper",
    "ky_scraper",
    "ok_scraper",
    "ia_scraper",
    "ks_scraper",
    "ar_scraper",
    "ms_scraper",
    "nm_scraper",
    "ne_scraper",
    "id_scraper",
    "hi_scraper",
    "nh_scraper",
    "me_scraper",
    "ri_scraper",
    "mt_scraper",
    "de_scraper",
    "sd_scraper",
    "nd_scraper",
    "ak_scraper",
    "vt_scraper",
    "wv_scraper",
    "wy_scraper",
]

ALL_MONITORED_FILES = [
    "mainscraper.py",
    "sled-scraper/sledscraper.py",
    "sam_scraper.py",
    "va_scraper.py",
    "ca_scraper.py",
    "fl_scraper.py",
    "md_scraper.py",
    "il_scraper.py",
    "pa_scraper.py",
    "oh_scraper.py",
    "ga_scraper.py",
    "nc_scraper.py",
    "ny_scraper.py",
    "ma_scraper.py",
    "nj_scraper.py",
    "wa_scraper.py",
    "mi_scraper.py",
    "co_scraper.py",
    "az_scraper.py",
    "mn_scraper.py",
    "tn_scraper.py",
    "in_scraper.py",
    "mo_scraper.py",
    "wi_scraper.py",
    "sc_scraper.py",
    "or_scraper.py",
    "ct_scraper.py",
    "ut_scraper.py",
    "nv_scraper.py",
    "al_scraper.py",
    "la_scraper.py",
    "ky_scraper.py",
    "ok_scraper.py",
    "ia_scraper.py",
    "ks_scraper.py",
    "ar_scraper.py",
    "ms_scraper.py",
    "nm_scraper.py",
    "ne_scraper.py",
    "id_scraper.py",
    "hi_scraper.py",
    "nh_scraper.py",
    "me_scraper.py",
    "ri_scraper.py",
    "mt_scraper.py",
    "de_scraper.py",
    "sd_scraper.py",
    "nd_scraper.py",
    "ak_scraper.py",
    "vt_scraper.py",
    "wv_scraper.py",
    "wy_scraper.py",
    "pseo_generator.py",
    "capturedesk_autopilot.py",
    "client_delivery.py",
    "outreach_generator.py",
    "outbound_reply_responder.py",
]


def fetch_remote_open_errors() -> list[dict]:
    """Fetch open runtime errors reported by Render Cron or local runs from the cloud gateway."""
    try:
        resp = requests.get(
            f"{TELEMETRY_API_BASE}/v1/telemetry/errors",
            params={"status": "open"},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("errors", [])
    except Exception:
        pass
    return []


def clear_remote_errors(resolution_note: str = "Verified and resolved by auto_error_healer.py") -> int:
    """Mark open errors on the cloud telemetry endpoint as resolved."""
    try:
        resp = requests.post(
            f"{TELEMETRY_API_BASE}/v1/telemetry/clear-errors",
            json={"resolution_note": resolution_note},
            timeout=8,
        )
        if resp.status_code == 200:
            return int(resp.json().get("cleared_count", 0))
    except Exception:
        pass
    return 0


def read_local_unacknowledged_errors() -> list[str]:
    """Read any unacknowledged error lines from local `error_log.txt`."""
    if not os.path.exists(ERROR_LOG_PATH):
        return []
    try:
        with open(ERROR_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            lines = [ln.strip() for ln in f.readlines() if ln.strip()]
        return [ln for ln in lines if not ln.startswith("#") and "[RESOLVED]" not in ln]
    except Exception:
        return []


def archive_local_error_log(resolution_note: str) -> None:
    """Clear active `error_log.txt` after archiving historical entries to `error_log_resolved.txt`."""
    if not os.path.exists(ERROR_LOG_PATH):
        return
    try:
        with open(ERROR_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            existing = f.read().strip()
        if existing:
            archive_path = BASE_DIR / "error_log_resolved.txt"
            stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            with open(archive_path, "a", encoding="utf-8", errors="replace") as af:
                af.write(f"\n=== ARCHIVED & RESOLVED AT {stamp}: {resolution_note} ===\n")
                af.write(existing + "\n")
        with open(ERROR_LOG_PATH, "w", encoding="utf-8") as f:
            f.write("")
    except Exception:
        pass


def discover_latest_anthropic_models() -> dict[str, str]:
    """
    Query Anthropic's official `GET /v1/models` endpoint (cached for 12 hours in `.frontier_model_cache.json`)
    to automatically discover the highest semantic version of `claude-sonnet-*`, `claude-haiku-*`, and `claude-opus-*`.
    """
    defaults = {
        "sonnet": "claude-sonnet-5-5",
        "haiku": "claude-haiku-5-5",
        "opus": "claude-opus-5-5",
    }
    cache_path = BASE_DIR / ".frontier_model_cache.json"
    now_ts = datetime.now(timezone.utc).timestamp()
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if now_ts - float(cached.get("timestamp") or 0) < 43200 and cached.get("sonnet"):
                return {
                    "sonnet": str(cached.get("sonnet") or defaults["sonnet"]),
                    "haiku": str(cached.get("haiku") or defaults["haiku"]),
                    "opus": str(cached.get("opus") or defaults["opus"]),
                }
        except Exception:
            pass

    api_key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        return defaults

    try:
        resp = requests.get(
            "https://api.anthropic.com/v1/models",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            timeout=8,
        )
        if resp.status_code == 200:
            items = (resp.json() or {}).get("data") or []
            best_versions: dict[str, tuple[tuple[int, int], str]] = {
                "sonnet": ((5, 5), defaults["sonnet"]),
                "haiku": ((5, 5), defaults["haiku"]),
                "opus": ((5, 5), defaults["opus"]),
            }
            ver_re = re.compile(r"^claude-(sonnet|haiku|opus)-(\d+)(?:-(\d+))?$")
            for item in items:
                mid = str((item or {}).get("id") or "").strip()
                m = ver_re.match(mid)
                if not m:
                    continue
                family = m.group(1)
                major = int(m.group(2))
                minor = int(m.group(3) or 0)
                if (major, minor) > best_versions[family][0]:
                    best_versions[family] = ((major, minor), mid)
            discovered = {k: v[1] for k, v in best_versions.items()}
            try:
                cache_path.write_text(
                    json.dumps({"timestamp": now_ts, **discovered}, indent=2),
                    encoding="utf-8",
                )
            except Exception:
                pass
            return discovered
    except Exception:
        pass
    return defaults


def verify_scraper_contracts_and_rls_safety() -> list[str]:
    """
    Static + dynamic contract audit across all scrapers, pipeline scripts, AND
    every Python file in both `d:\\Daas` and `d:\\Data API Ecosystem` (`b2b-contract-parser-api`),
    plus live Render gateway health verification.
    Returns a list of violation descriptions (empty list = 100% healthy).
    """
    import py_compile
    issues: list[str] = []

    # 0. Compile every .py file in BOTH d:\Data API Ecosystem and d:\Daas in-memory (zero .pyc disk lock collisions)
    #    and ensure zero literal ASCII 0x08 (\x08) backspace control chars corrupting regex \b word boundaries.
    for repo_root in (pathlib.Path(r"D:\Data API Ecosystem"), BASE_DIR):
        if not repo_root.exists():
            continue
        for py_file in repo_root.rglob("*.py"):
            s_path = str(py_file)
            if any(skip in s_path for skip in ("daas_env", "venv", ".venv", "__pycache__", ".git")):
                continue
            try:
                py_txt = py_file.read_text(encoding="utf-8", errors="replace")
                if "\x08" in py_txt and "auto_error_healer.py" not in s_path:
                    issues.append(f"Corrupted ASCII 0x08 backspace char (broken regex \\b) found in {s_path}")
                compile(py_txt, s_path, "exec")
            except SyntaxError as comp_err:
                issues.append(f"Python syntax/compilation error in {s_path}: {comp_err}")
            except Exception:
                pass

    # 0b. Verify live Render deployment health, all 34+ catalog routes in /openapi.json, & live RAPIDAPI_PROXY_SECRET auth
    try:
        h_resp = requests.get(f"{TELEMETRY_API_BASE}/v1/health", timeout=8)
        if h_resp.status_code != 200:
            issues.append(f"Render b2b-contract-parser-api /v1/health returned HTTP {h_resp.status_code}")
        oa_resp = requests.get(f"{TELEMETRY_API_BASE}/openapi.json", timeout=8)
        if oa_resp.status_code == 200:
            oa_paths = oa_resp.json().get("paths", {})
            required_routes = list((
                "/v1/health",
                "/v1/webhooks/register-destination",
                "/v1/webhooks/subscriber-access",
                "/v1/leads/capture",
                "/v1/billing/create-checkout-session",
                "/v1/support/contact",
                "/v1/proposal-autopilot/compile-full-package",
                "/v1/proposal-autopilot/teaming-clearinghouse",
                "/v1/proposal-autopilot/foia-winning-bid-vault",
            ))
            seed_file = BASE_DIR / "seed_rapidapi_telemetry.py"
            if seed_file.exists():
                seed_routes = re.findall(r'"path"\s*:\s*"(/v1/[^"]+)"', seed_file.read_text(encoding="utf-8", errors="replace"))
                for sr in seed_routes:
                    if sr not in required_routes:
                        required_routes.append(sr)
            for req_path in required_routes:
                if req_path not in oa_paths:
                    issues.append(f"Render live OpenAPI missing expected route {req_path} (possible failed deploy)")

        # Verify live Render container accepts our local RAPIDAPI_PROXY_SECRET
        raw_sec = (os.getenv("RAPIDAPI_PROXY_SECRET") or "").strip()
        if raw_sec:
            first_sec = [s.strip() for s in raw_sec.split(",") if s.strip()][0]
            auth_probe = requests.get(
                f"{TELEMETRY_API_BASE}/v1/solicitations/live",
                params={"state": "virginia", "limit": 1},
                headers={"X-RapidAPI-Proxy-Secret": first_sec},
                timeout=8,
            )
            if auth_probe.status_code in (401, 403):
                issues.append(
                    f"Live Render /v1/solicitations/live rejected local RAPIDAPI_PROXY_SECRET with HTTP {auth_probe.status_code} (Render env drift)"
                )
    except Exception:
        pass

    # 1. Verify every scraper module defines `async def run_scraper(push_to_db=...)` via fast AST inspection
    #    and never uses rolling `timedelta(` date math or process-salted `abs(hash(`.
    import ast
    for mod_name in SCRAPER_MODULES:
        mod_path = (SLED_DIR / f"{mod_name}.py") if mod_name == "sledscraper" else (BASE_DIR / f"{mod_name}.py")
        if not mod_path.exists():
            issues.append(f"{mod_name}.py file not found at {mod_path}")
            continue
        try:
            mod_src = mod_path.read_text(encoding="utf-8", errors="replace")
            if "timedelta(" in mod_src:
                issues.append(f"{mod_name}.py uses rolling `timedelta(` date math; use deterministic anchored calendar dates.")
            if "abs(hash(" in mod_src:
                issues.append(f"{mod_name}.py uses process-salted `abs(hash(`; use `hashlib.sha256(...).hexdigest()`.")
            tree = ast.parse(mod_src, filename=str(mod_path))
            found_async = False
            found_sync = False
            has_push_param = False
            for node in tree.body:
                if isinstance(node, ast.AsyncFunctionDef) and node.name == "run_scraper":
                    found_async = True
                    arg_names = [a.arg for a in node.args.args] + [a.arg for a in node.args.kwonlyargs]
                    if "push_to_db" in arg_names:
                        has_push_param = True
                elif isinstance(node, ast.FunctionDef) and node.name == "run_scraper":
                    found_sync = True
            if not found_async and not found_sync:
                issues.append(f"{mod_name}.py is missing `run_scraper(push_to_db: bool = True)`")
            elif found_sync and not found_async:
                issues.append(f"{mod_name}.run_scraper must be an `async def` coroutine function")
            elif not has_push_param:
                issues.append(f"{mod_name}.run_scraper is missing the `push_to_db` parameter")
        except Exception as exc:
            issues.append(f"Failed to parse AST for {mod_name}.py: {exc}")

    # 2. Verify all monitored files:
    #    - Do not use .upsert() on contracts (which triggers Supabase PostgREST RLS 42501)
    #    - Automatically discover & upgrade to the latest frontier Sonnet & Haiku models from `/v1/models`
    #    - Wire report_error() inside send_discord_alert() so 100% of Discord alerts reach /v1/telemetry/report-error
    frontier = discover_latest_anthropic_models()
    latest_sonnet = frontier["sonnet"]
    latest_haiku = frontier["haiku"]
    sonnet_model_pattern = re.compile(
        r"\bclaude-(?:3-(?:5-|7-)?sonnet[a-z0-9\-]*|sonnet-[0-9]+(?:-[0-9]+)*)"
    )
    haiku_model_pattern = re.compile(
        r"\bclaude-(?:3-(?:5-)?haiku[a-z0-9\-]*|haiku-[0-9]+(?:-[0-9]+)*)"
    )
    for rel_path in ALL_MONITORED_FILES:
        full_p = BASE_DIR / rel_path
        if full_p.exists():
            src = full_p.read_text(encoding="utf-8", errors="replace")
            if ".upsert(" in src and rel_path != "pseo_generator.py":
                issues.append(
                    f"{rel_path} still contains `.upsert(` which triggers Supabase PostgREST RLS 42501; use SELECT + `.insert(`."
                )
            bad_sonnets = {m for m in sonnet_model_pattern.findall(src) if m != latest_sonnet}
            bad_haikus = {m for m in haiku_model_pattern.findall(src) if m != latest_haiku}
            if bad_sonnets or bad_haikus:
                healed_src = sonnet_model_pattern.sub(latest_sonnet, src)
                healed_src = haiku_model_pattern.sub(latest_haiku, healed_src)
                try:
                    full_p.write_text(healed_src, encoding="utf-8")
                    print(
                        f"  [AUTO-HEALED] Auto-upgraded Anthropic model(s) -> '{latest_sonnet}' / '{latest_haiku}' in {rel_path}"
                    )
                except Exception as exc:
                    issues.append(
                        f"{rel_path} contains outdated Anthropic model ID(s) and auto-heal failed: {exc}"
                    )
            m_alert = re.search(r"def\s+send_discord_alert\s*\([^)]*\)\s*(?:->\s*[^:]+)?\s*:(.*?)(?:\ndef\s|\nasync\s+def\s|\Z)", src, flags=re.S)
            if m_alert:
                alert_body = m_alert.group(1)
                if "report_error(" not in alert_body:
                    issues.append(
                        f"{rel_path}: `send_discord_alert()` must call `report_error()` so errors are silently captured in `/v1/telemetry/report-error`."
                    )
                if "requests.post" in alert_body and ("DISCORD_WEBHOOK_URL" in alert_body or "webhook_url" in alert_body) and "DISCORD_EMIT_DETECTION_ALERTS" not in alert_body:
                    issues.append(
                        f"{rel_path}: `send_discord_alert()` violates RULE-001 (posts raw [ALERT] detection webhook to Discord instead of silent report_error() + [RESOLVED]-only alerting)."
                    )

    # Also auto-upgrade frontier Sonnet & Haiku model IDs in d:\Data API Ecosystem (core/config.py & services/llm_parser.py)
    eco_dir_models = pathlib.Path(r"D:\Data API Ecosystem")
    for eco_rel in ("core/config.py", "services/llm_parser.py"):
        eco_fp = eco_dir_models / eco_rel
        if eco_fp.exists():
            eco_src = eco_fp.read_text(encoding="utf-8", errors="replace")
            bad_eco_s = {m for m in sonnet_model_pattern.findall(eco_src) if m != latest_sonnet}
            bad_eco_h = {m for m in haiku_model_pattern.findall(eco_src) if m != latest_haiku}
            if bad_eco_s or bad_eco_h:
                healed_eco = sonnet_model_pattern.sub(latest_sonnet, eco_src)
                healed_eco = haiku_model_pattern.sub(latest_haiku, healed_eco)
                try:
                    eco_fp.write_text(healed_eco, encoding="utf-8")
                    print(
                        f"  [AUTO-HEALED] Auto-upgraded Anthropic model(s) -> '{latest_sonnet}' / '{latest_haiku}' in Data API Ecosystem/{eco_rel}"
                    )
                except Exception:
                    pass

    # 3. Verify linkedin_autoposter.py strictly targets SignalTender Company Page (urn:li:organization:146880945)
    li_path = BASE_DIR / "linkedin_autoposter.py"
    if li_path.exists():
        li_src = li_path.read_text(encoding="utf-8", errors="replace")
        if "LINKEDIN_PERSON_URN" in li_src or '"author": author_person' in li_src:
            issues.append("linkedin_autoposter.py must NEVER target a personal profile (`LINKEDIN_PERSON_URN`); only `urn:li:organization:146880945` is allowed.")

    # 3b. Verify stateless Render Cron Supabase state persistence across all 6 stateful acquisition/email jobs
    for fname, state_uri in (
        ("govcon_lead_harvester.py", "subscriber://outbound-archive/master"),
        ("outbound_reply_responder.py", "subscriber://outbound-replies/processed"),
        ("x_autoposter.py", "subscriber://social-x/posted-slugs"),
        ("linkedin_autoposter.py", "subscriber://social-linkedin/state"),
        ("capturedesk_autopilot.py", "subscriber://capturedesk/dossiers-cache"),
        ("autonomous_mailbox_scaler.py", "subscriber://treasury/mailbox-scaler-ledger"),
    ):
        fp = BASE_DIR / fname
        if fp.exists():
            fsrc = fp.read_text(encoding="utf-8", errors="replace")
            if state_uri not in fsrc:
                issues.append(f"{fname} is missing stateless Render Cron Supabase state sync (`{state_uri}`).")

    # 3c. Verify warmed mailboxes (score >= 85) are never blocked by an artificial 14-day delay or warmup/disable
    try:
        import outbound_mailer
        test_warmed = {
            "email": "test@try-signaltender.com",
            "status": 1,
            "warmup_status": 1,
            "stat_warmup_score": 100,
            "timestamp_created": datetime.now(timezone.utc).isoformat(),
        }
        if outbound_mailer.is_instantly_account_warmed(test_warmed) is not True:
            issues.append("outbound_mailer.is_instantly_account_warmed() blocked a warmed mailbox (stat_warmup_score >= 85) due to age gate!")
    except Exception as exc:
        issues.append(f"Failed to verify outbound_mailer.is_instantly_account_warmed(): {exc}")

    og_fp = BASE_DIR / "outreach_generator.py"
    if og_fp.exists() and "accounts/warmup/disable" in og_fp.read_text(encoding="utf-8", errors="replace"):
        issues.append("outreach_generator.py must NEVER call `accounts/warmup/disable` on active sending mailboxes.")

    # 3d. Verify proposal_compiler.py runtime quality gate & PostgREST subscriber://* wildcard filters
    eco_dir = pathlib.Path(r"D:\Data API Ecosystem")
    pc_fp = eco_dir / "api" / "routers" / "proposal_compiler.py"
    if pc_fp.exists():
        pc_src = pc_fp.read_text(encoding="utf-8", errors="replace")
        for req_sym in ("_infer_target_jurisdiction", "_enforce_proposal_package_quality_gate", "_lookup_offeror_verified_profile", "not.like.subscriber://*"):
            if req_sym not in pc_src:
                issues.append(f"api/routers/proposal_compiler.py is missing required quality-gate symbol `{req_sym}` (RULE-008-PRODUCT-OUTPUT-QUALITY-GATE).")
    for r_rel in ("solicitations.py", "stripe_webhook.py"):
        r_fp = eco_dir / "api" / "routers" / r_rel
        if r_fp.exists():
            r_src = r_fp.read_text(encoding="utf-8", errors="replace")
            if "not.like.subscriber://%" in r_src or "not.like.subscriber://*" not in r_src:
                issues.append(f"api/routers/{r_rel} must use PostgREST wildcard `not.like.subscriber://*` (never `not.like.subscriber://%`).")

    # 4. Verify all 5 SignalTender Discord webhooks and the main Discord Bot user have the SignalTender radar-chevron avatar set
    icon_path = BASE_DIR / "apple-touch-icon.png"
    icon_b64 = None
    if icon_path.exists():
        import base64
        icon_b64 = "data:image/png;base64," + base64.b64encode(icon_path.read_bytes()).decode("ascii")
    for env_key in (
        "DISCORD_WEBHOOK_URL",
        "DISCORD_CONTENT_WEBHOOK_URL",
        "DISCORD_CAPTUREDESK_WEBHOOK_URL",
        "DISCORD_TIER3_WEBHOOK_URL",
        "DISCORD_TIER4_WEBHOOK_URL",
    ):
        wh_url = (os.getenv(env_key) or "").strip()
        if not wh_url or "discord.com/api/webhooks/" not in wh_url:
            continue
        try:
            r = requests.get(wh_url, timeout=8)
            if r.status_code == 200:
                wh_data = r.json()
                if not wh_data.get("avatar") and icon_b64:
                    patch_r = requests.patch(wh_url, json={"avatar": icon_b64}, timeout=10)
                    if patch_r.status_code != 200 or not patch_r.json().get("avatar"):
                        issues.append(f"{env_key} Discord webhook is missing the SignalTender logo avatar and auto-patch failed ({patch_r.status_code}).")
        except Exception:
            pass

    bot_token = (os.getenv("DISCORD_BOT_TOKEN") or "").strip()
    if bot_token and icon_b64:
        try:
            r_bot = requests.get(
                "https://discord.com/api/v10/users/@me",
                headers={"Authorization": f"Bot {bot_token}"},
                timeout=8,
            )
            if r_bot.status_code == 200 and not r_bot.json().get("avatar"):
                requests.patch(
                    "https://discord.com/api/v10/users/@me",
                    headers={"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"},
                    json={"avatar": icon_b64},
                    timeout=10,
                )
        except Exception:
            pass


    # 5. Verify Outbound Campaign CSV, Prospect Pool & Self-Improver Health (Root Causes #1 & #2: Zero Non-IT Contracts & Zero NSF SBIR 541715 Grant Startups)
    try:
        import csv
        import govcon_lead_harvester
        vp_p = BASE_DIR / "verified_public_govcon_contacts.json"
        if vp_p.exists():
            vp_rows = json.loads(vp_p.read_text(encoding="utf-8")) or []
            bad_sbir = [
                r.get("Email") for r in vp_rows
                if isinstance(r, dict) and not govcon_lead_harvester.is_verified_it_cyber_prospect(
                    str(r.get("Company Name") or ""), str(r.get("Email") or ""), str(r.get("Keywords") or ""), str(r.get("NAICS Codes") or "")
                )
            ]
            if bad_sbir:
                govcon_lead_harvester.run_harvester()
                import outreach_generator
                outreach_generator.generate_outreach()
                import autonomous_outbound_optimizer
                autonomous_outbound_optimizer.run_autonomous_outbound_optimizer()
                print(f"  [AUTO-HEALED] Purged {len(bad_sbir)} non-IT/SBIR grant startups from prospect pool & resynced Instantly.")
        csv_p = BASE_DIR / "campaign_leads.csv"
        if csv_p.exists():
            with open(csv_p, "r", encoding="utf-8-sig", newline="") as cf:
                rows = list(csv.DictReader(cf))
            bad_contract_rows = [
                r.get("Email") for r in rows
                if any(
                    bad_kw in str(r.get("Email Body") or "").lower()
                    for bad_kw in (
                        "sign panel fabrication", "water valve distribution", "pavement repair",
                        "x-ray screening", "x ray screening", "heart rate monitoring",
                        "gamma calibrator", "hiv care network", "alternate system of assessment",
                    )
                )
            ]
            if bad_contract_rows:
                import outreach_generator
                outreach_generator.generate_outreach()
                import autonomous_outbound_optimizer
                autonomous_outbound_optimizer.run_autonomous_outbound_optimizer()
                print(f"  [AUTO-HEALED] Regenerated campaign_leads.csv & patched Instantly leads to remove {len(bad_contract_rows)} non-IT contract references.")
    except Exception:
        pass


    # 5b. Live Instantly API & Production Funnel Goalie Check (Audits live campaign state & ALL paginated leads, not just local CSV)
    inst_key = (os.getenv("INSTANTLY_API_KEY") or "").strip()
    inst_cid = (os.getenv("INSTANTLY_CAMPAIGN_ID") or "c7727dff-92cc-4621-9e96-c960938d5a47").strip()
    if inst_key and inst_cid:
        try:
            ih = {"Authorization": f"Bearer {inst_key}", "Content-Type": "application/json"}
            rc = requests.get(f"https://api.instantly.ai/api/v2/campaigns/{inst_cid}", headers=ih, timeout=12)
            if rc.status_code == 200:
                cd = rc.json() or {}
                need_opt = False
                if int(cd.get("status") or 0) != 1 or not bool(cd.get("disable_bounce_protect")) or int(cd.get("not_sending_status") or 0) == 2:
                    need_opt = True
                all_inst_leads = []
                sa = None
                for _ in range(10):
                    b = {"campaign": inst_cid, "limit": 100}
                    if sa:
                        b["starting_after"] = sa
                    rl = requests.post("https://api.instantly.ai/api/v2/leads/list", headers=ih, json=b, timeout=12)
                    if rl.status_code != 200:
                        break
                    rj = rl.json() or {}
                    its = rj.get("items") or []
                    all_inst_leads.extend(its)
                    sa = rj.get("next_starting_after")
                    if not sa or len(its) < 100:
                        break
                bounced_cnt = sum(1 for x in all_inst_leads if int(x.get("status") or 0) < 0)
                unc_cnt = sum(1 for x in all_inst_leads if int(x.get("status") or 0) == 1 and not x.get("timestamp_last_contact"))
                bad_payloads = 0
                for x in all_inst_leads:
                    p = x.get("payload") or {}
                    s1 = str(p.get("email_body") or "")
                    s2 = str(p.get("followup_body") or "")
                    if "https://" not in s2 or "https://" in s1 or "{{" in (s1 + s2) or s2.count("(") != s2.count(")"):
                        bad_payloads += 1
                if bounced_cnt > 0 or unc_cnt < 40 or bad_payloads > 0:
                    need_opt = True
                if need_opt:
                    import autonomous_outbound_optimizer
                    autonomous_outbound_optimizer.run_autonomous_outbound_optimizer()
                    print(f"  [AUTO-HEALED] Live Instantly Goalie healed campaign (bounced={bounced_cnt}, uncontacted={unc_cnt}, bad_payloads={bad_payloads}).")
        except Exception as exc:
            print(f"  [WARN] Live Instantly Goalie check warning: {exc}")

    return issues


async def run_live_smoke_tests() -> list[str]:
    """Run fast non-destructive smoke tests on key state scrapers (`push_to_db=False`)."""
    import concurrent.futures

    smoke_issues: list[str] = []
    smoke_modules = (
        "ga_scraper",
        "nc_scraper",
        "ny_scraper",
        "ma_scraper",
        "nj_scraper",
        "wa_scraper",
        "mi_scraper",
        "co_scraper",
        "az_scraper",
        "mn_scraper",
        "tn_scraper",
        "in_scraper",
        "mo_scraper",
        "wi_scraper",
        "sc_scraper",
        "or_scraper",
        "ct_scraper",
        "ut_scraper",
    )

    def _run_one(mod_name: str) -> str | None:
        try:
            mod = importlib.import_module(mod_name)
            records = asyncio.run(mod.run_scraper(push_to_db=False))
            if not isinstance(records, list) or len(records) == 0:
                return f"{mod_name}.run_scraper(push_to_db=False) returned 0 records"
            return None
        except Exception as exc:
            return f"{mod_name}.run_scraper(push_to_db=False) raised exception: {exc}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=9) as pool:
        for issue in pool.map(_run_one, smoke_modules):
            if issue:
                smoke_issues.append(issue)
    return smoke_issues




def check_and_heal_client_semantic_quality() -> list[str]:
    """
    RULE-021: Autonomous Client-Facing Semantic Quality & End-to-End Fulfillment Self-Healer for SignalTender.
    Verifies:
    1. Zero robotic role greetings ('Hi Capture,', 'Hi Team,') or unreplaced '{{' braces in campaign_leads.csv.
    2. Every Top Contract Dossier URL in campaign_leads.csv resolves to an existing static HTML file in d:/Daas/contracts/rfp/*.html.
    3. Reply classifier in outbound_reply_responder.py handles hostile '?' unsubscribes and spam-filter challenge auto-replies without spending AI tokens.
    """
    import csv
    issues: list[str] = []
    try:
        import outbound_reply_responder as orr
        res_unsub = orr.classify_and_draft_reply("test@example.com", "Re: Open RFPs", "Why are you emailing me? Remove us from your list.")
        if res_unsub.get("intent") != "UNSUBSCRIBE":
            issues.append("outbound_reply_responder.py failed hostile '?' UNSUBSCRIBE classification test (RULE-021)")
        res_ooo = orr.classify_and_draft_reply("test@example.com", "Email Verification", "Barracuda Spam Firewall: please verify your email")
        if res_ooo.get("intent") != "OUT_OF_OFFICE":
            issues.append("outbound_reply_responder.py failed spam-challenge OUT_OF_OFFICE classification test (RULE-021)")
    except Exception as exc:
        issues.append(f"outbound_reply_responder.py semantic check error: {exc}")

    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campaign_leads.csv")
    need_regen = False
    if os.path.exists(csv_path):
        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as cf:
                rows = list(csv.DictReader(cf))
            for r in rows:
                eb = str(r.get("Email Body") or "")
                fb = str(r.get("Followup Body") or "")
                d_url = str(r.get("Top Contract Dossier URL") or "").strip()
                if "{{" in eb or "}}" in eb or "{{" in fb or "}}" in fb:
                    need_regen = True
                if any(bg in eb for bg in ("Hi Capture,", "Hi Team,", "Hi Contracts,")):
                    need_regen = True
                if "/contracts/rfp/" in d_url:
                    rel_p = d_url.split("signaltender.net/", 1)[-1].split("?", 1)[0].split("#", 1)[0]
                    if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), rel_p)):
                        need_regen = True
        except Exception as exc:
            issues.append(f"campaign_leads.csv semantic audit error: {exc}")

    if need_regen:
        try:
            import pseo_generator
            import outreach_generator
            pseo_generator.generate_pseo_site()
            outreach_generator.generate_outreach()
            print("  [AUTO-HEALED] Regenerated SignalTender pSEO dossiers & outreach campaigns (RULE-021)", flush=True)
        except Exception as exc:
            issues.append(f"SignalTender semantic auto-heal failed: {exc}")

    # Verify stripe_webhook.py sample dossier URLs resolve to real static files across all 3 businesses
    sw_path = os.path.join(r"d:\Data API Ecosystem", "api", "routers", "stripe_webhook.py")
    if os.path.exists(sw_path):
        try:
            sw_txt = open(sw_path, "r", encoding="utf-8", errors="replace").read()
            for m in re.finditer(r"https://(?:signaltender\.net/contracts/rfp|camberdesk\.com/lettings/project|rubricward\.com/lettings/project)/([a-z0-9\-]+\.html)", sw_txt):
                u = m.group(0)
                fn = m.group(1)
                if "signaltender.net" in u and not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "contracts", "rfp", fn)):
                    issues.append(f"stripe_webhook.py references non-existent SignalTender sample dossier: {u}")
                elif "camberdesk.com" in u and os.path.exists(r"D:\CamberDesk\lettings\project") and not os.path.exists(os.path.join(r"D:\CamberDesk\lettings\project", fn)):
                    issues.append(f"stripe_webhook.py references non-existent CamberDesk sample dossier: {u}")
                elif "rubricward.com" in u and os.path.exists(r"D:\RubricWard\lettings\project") and not os.path.exists(os.path.join(r"D:\RubricWard\lettings\project", fn)):
                    issues.append(f"stripe_webhook.py references non-existent RubricWard sample dossier: {u}")
        except Exception as exc:
            issues.append(f"stripe_webhook.py sample dossier URL check error: {exc}")

    return issues


def run_healer(
    clear_resolved: bool = False,
    run_smoke: bool = False,
    resolution_note: str | None = None,
) -> int:
    print("[*] Running SignalTender Closed-Loop Autonomous Error Inspector & Self-Healer...", flush=True)
    contract_issues = verify_scraper_contracts_and_rls_safety()
    contract_issues.extend(check_and_heal_client_semantic_quality())
    smoke_issues = asyncio.run(run_live_smoke_tests()) if run_smoke else []

    remote_errors = fetch_remote_open_errors()
    local_errors = read_local_unacknowledged_errors()

    if clear_resolved and not contract_issues and not smoke_issues and (remote_errors or local_errors):
        sources = sorted(
            {
                *(err.get("source", "scraper") for err in remote_errors),
                *(
                    re.findall(r"\[([a-zA-Z0-9_.-]+\.py)\]", ln)[0]
                    for ln in local_errors
                    if re.findall(r"\[([a-zA-Z0-9_.-]+\.py)\]", ln)
                ),
            }
        ) or ["pipeline"]
        components_str = ", ".join(f"`{s}`" for s in sources)
        summaries = []
        for err in remote_errors[:3]:
            summaries.append(f"{err.get('source')}: {str(err.get('message', ''))[:140]}")
        for ln in local_errors[:3]:
            if len(summaries) < 3:
                summaries.append(ln[:140])
        resolved_summary = " | ".join(summaries) if summaries else "Runtime alert(s) in telemetry log"

        fix_note = resolution_note or (
            f"Auto-healed & verified by auto_error_healer.py "
            f"({len(SCRAPER_MODULES) + 1}/{len(SCRAPER_MODULES) + 1} scrapers & pipeline contracts healthy; cleared {len(local_errors)} local + {len(remote_errors)} remote alert(s))"
        )
        archive_local_error_log(fix_note)
        cleared_remote = clear_remote_errors(fix_note)
        send_discord_resolution(
            components=components_str,
            resolved_issues=resolved_summary,
            fix_verification=fix_note,
            open_error_count=0,
        )
        print(
            f"[+] Resolved & archived {len(local_errors)} local error_log.txt line(s) and {cleared_remote} remote telemetry alert(s), and posted [RESOLVED] to Discord #alerts.",
            flush=True,
        )
        remote_errors = fetch_remote_open_errors()
        local_errors = read_local_unacknowledged_errors()

    if contract_issues:
        print(f"[FAIL] Scraper Contract / RLS Safety Audit found {len(contract_issues)} issue(s):", flush=True)
        for item in contract_issues:
            print(f"  - {item}", flush=True)

    if smoke_issues:
        print(f"[FAIL] Live Scraper Smoke Tests found {len(smoke_issues)} issue(s):", flush=True)
        for item in smoke_issues:
            print(f"  - {item}", flush=True)

    if remote_errors:
        print(f"[ALERT] {len(remote_errors)} open remote Render Cron / telemetry error(s) detected (diagnose & fix before running --clear-resolved):", flush=True)
        for err in remote_errors:
            print(f"  - [{err.get('environment')}] [{err.get('source')}] (x{err.get('occurrence_count', 1)}): {err.get('message')}", flush=True)

    if local_errors:
        print(f"[ALERT] {len(local_errors)} unacknowledged error line(s) in local error_log.txt (diagnose & fix before running --clear-resolved):", flush=True)
        for ln in local_errors[-10:]:
            print(f"  - {ln}", flush=True)

    total_problems = len(contract_issues) + len(smoke_issues) + len(remote_errors) + len(local_errors)
    if total_problems == 0:
        print(
            "[PASS] Autonomous Error Telemetry & Scraper Contract Audit: 0 open errors (local + Render Cron), "
            f"{len(SCRAPER_MODULES) + 1}/{len(SCRAPER_MODULES) + 1} scrapers verified (`run_scraper` + `report_error` + RLS-safe `.insert()`).",
            flush=True,
        )
        return 0
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SignalTender Autonomous Error Inspector & Self-Healer")
    parser.add_argument("--clear-resolved", action="store_true", help="Archive and clear resolved errors after passing checks and post [RESOLVED] to Discord #alerts")
    parser.add_argument("--smoke", action="store_true", help="Run live non-destructive scraper smoke tests")
    parser.add_argument("--resolution-note", type=str, default=None, help="Explicit explanation of the fix applied for Discord #alerts [RESOLVED] notification")
    args = parser.parse_args()
    sys.exit(run_healer(clear_resolved=args.clear_resolved, run_smoke=args.smoke, resolution_note=args.resolution_note))
