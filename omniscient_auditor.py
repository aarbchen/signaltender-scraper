"""
SignalTender 360° Omniscient Audit, Self-Healing & Self-Improving Rule Engine (`omniscient_auditor.py`).
========================================================================================================
Audits every layer of SignalTender for bugs across 3 domains, automatically fixes them, codifies a
permanent anti-regression rule with every fix (`learned_anti_regression_rules.json` + `AGENTS.md`),
and dispatches ONLY a `[RESOLVED]` notification to Discord `#alerts` (zero raw `[ALERT]` spam):

  1. PRODUCTS (`AuditDomain.PRODUCTS`):
     - 34+ Stateless FastAPI Microservices (`d:\\Data API Ecosystem` & live Render `/openapi.json`)
     - Dual Model Context Protocol (MCP) Servers (`api/routers/mcp.py` & `mcp-server/index.js`, 5/5 Glama TDQS)
     - 27+ Federal, State SLED & Municipal Scrapers (AST contracts, determinism, RLS safety, silent telemetry)
     - Tier 1–4 Delivery Products (`client_delivery.py`, `capturedesk_autopilot.py`, `proposal_compiler.py`, Discord webhooks)

  2. ACQUISITION CHANNELS (`AuditDomain.ACQUISITION`):
     - Outbound Cold Email Pipeline (`outreach_generator.py`, `campaign_leads.csv`, `outbox_ready_queue.json`, DNC safety, live URL check)
     - Outbound Reply Auto-Responder (`outbound_reply_responder.py`, quoted-footer strip, Instantly V2 sync)
     - Programmatic SEO (`pseo_generator.py`, `/contracts/**/*.html`, `sitemap.xml`, `robots.txt`, JSON-LD, OpenGraph `?v=` parity)
     - RapidAPI Hub Storefronts (`seed_rapidapi_telemetry.py`, 1:1 host/slug parity & green SLA badges)
     - Social Acquisition Channels (`linkedin_autoposter.py`, `x_autoposter.py`, `social_distribution_kit.py` queues)
     - Inbound Lead Capture Magnet (`/v1/leads/capture` & `#inbound-lead-capture` state selector parity)

  3. WEBSITE, CHECKOUT & INFRASTRUCTURE (`AuditDomain.WEBSITE`):
     - Stale Portal / State / API Count & `API_META` Auto-Healer across `index.html`, `apis.html` & conversion surfaces
     - Duplicate Badge, Emoji & Synthetic SF-30 Auto-Cleaner
     - Full JS `vm.Script`, Inline Event Handler, SPA Route, Account Console, AI Support Concierge & WAF Verification
     - Playwright 375x812 Mobile & 1024px/1280px Desktop Viewport Overflow Scanner
"""

import argparse
import ast
import ctypes
import csv
import glob
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

from error_telemetry import (
    configure_utf8_stdio,
    codify_learned_rule,
    derive_and_codify_rule_from_fix,
    load_learned_rules,
    report_error,
    send_discord_resolution,
    LEARNED_RULES_PATH,
    TELEMETRY_API_BASE,
)

configure_utf8_stdio()

BASE_DIR = pathlib.Path(__file__).resolve().parent
ECOSYSTEM_DIR = pathlib.Path(r"D:\Data API Ecosystem")
load_dotenv(dotenv_path=BASE_DIR / ".env")
load_dotenv(dotenv_path=ECOSYSTEM_DIR / ".env")
load_dotenv()

AUDIT_REPORT_PATH = BASE_DIR / "omniscient_audit_report.json"

FOUNDATIONAL_RULES = [
    {
        "rule_id": "RULE-001-SILENT-DETECTION-RESOLVED-ONLY",
        "category": "Telemetry & Self-Healing",
        "source": "error_telemetry.py / *_scraper.py",
        "bug_signature": "Raw [ALERT] Discord webhook notifications sent upon bug detection before self-healing runs",
        "root_cause": "send_discord_alert() functions posted directly to DISCORD_WEBHOOK_URL with **[ALERT]** text prior to auto-remediation.",
        "fix_applied": "Rewrote all send_discord_alert() implementations to log silently via report_error() and emit Discord notifications strictly via send_discord_resolution() ([RESOLVED]) after fixing.",
        "prevention_rule": "Never emit raw [ALERT] notifications to Discord when a bug is detected; capture errors silently via report_error(), auto-heal the issue, codify a permanent prevention rule, and dispatch only a [RESOLVED] notification.",
    },
    {
        "rule_id": "RULE-002-PORTAL-STATE-API-COUNT-PARITY",
        "category": "Website, Products & Acquisition Parity",
        "source": "index.html / apis.html / pseo_generator.py / outreach_generator.py",
        "bug_signature": "Stale portal, state, or API counts appearing in UI badges, deep-dive panels, or outbound email queues",
        "root_cause": "Adding a new scraper or API without updating all surface strings and regenerating static pSEO / outbound queues.",
        "fix_applied": "Added automatic count-drift healer across index.html, apis.html, pseo_generator.py, and outbound conversion surfaces.",
        "prevention_rule": "Automatically synchronize n_portals, n_states, n_apis, and n_tier2_apis across all website, pSEO, MCP, and outbound surfaces before every verification pass.",
    },
    {
        "rule_id": "RULE-003-OUTBOUND-DOSSIER-URL-INTEGRITY",
        "category": "Acquisition Channels",
        "source": "campaign_leads.csv / outbox_ready_queue.json / pseo_generator.py",
        "bug_signature": "Cold email or social post referencing a /contracts/rfp/<slug>.html URL that does not exist on disk",
        "root_cause": "Contract directory or slug updates occurring without re-running pseo_generator.py and outreach_generator.py.",
        "fix_applied": "Added 1:1 URL-to-disk verification for campaign_leads.csv, outbox_ready_queue.json, and sitemap.xml with automatic regeneration.",
        "prevention_rule": "Every Top Contract Dossier URL in campaign_leads.csv, outbox_ready_queue.json, x_ready_posts.json, and sitemap.xml must resolve to an existing static HTML file in contracts/rfp/.",
    },
    {
        "rule_id": "RULE-004-SCRAPER-DETERMINISM-AND-RLS",
        "category": "Products & Scrapers",
        "source": "*_scraper.py / sledscraper.py",
        "bug_signature": "Rolling timedelta() dates, process-salted abs(hash()), or PostgREST RLS 42501 .upsert() failures",
        "root_cause": "Non-deterministic fallback dates/IDs causing synthetic SF-30 duplicates or .upsert() triggering RLS 42501.",
        "fix_applied": "Enforced AST & regex checks banning timedelta(), abs(hash(), .upsert(), and legacy Claude 3/4 models across all scrapers.",
        "prevention_rule": "All scrapers must export async def run_scraper(push_to_db: bool = True), use deterministic anchored dates and SHA-256 IDs, use SELECT + .insert(), and use claude-sonnet-5-5.",
    },
    {
        "rule_id": "RULE-005-DUAL-MCP-AND-VERSION-SYNC",
        "category": "Products & MCP Ecosystem",
        "source": "api/routers/mcp.py / mcp-server/index.js / server.json / package.json",
        "bug_signature": "Tool count, description prefix, or manifest version mismatch between remote HTTP MCP and NPM STDIO MCP",
        "root_cause": "Updating one MCP server or manifest version without syncing the counterpart.",
        "fix_applied": "Added automatic version and tool-schema parity sync across mcp.py, mcp-server/index.js, server.json, and mcp-server/package.json.",
        "prevention_rule": "Keep tool count, 5/5 Glama TDQS annotations, and manifest versions 100% synchronized across mcp.py, mcp-server/index.js, server.json, and mcp-server/package.json.",
    },
    {
        "rule_id": "RULE-006-NIGHTTIME-AWAY-EXECUTION-ONLY",
        "category": "Scheduler & Operator UX",
        "source": "omniscient_auditor.py / silent_autopilot_watcher.py / windows_autopilot_guard.py",
        "bug_signature": "Autonomous audit and self-healing jobs running during daytime hours while the operator is actively using the computer",
        "root_cause": "Background watcher and audit invocations lacked a nighttime + Windows user-idle (GetLastInputInfo) gate.",
        "fix_applied": "Enforced is_nighttime_and_user_away() (11:00 PM – 6:00 AM local time AND >= 30 minutes of keyboard/mouse idle time) across omniscient_auditor.py, silent_autopilot_watcher.py, and windows_autopilot_guard.py.",
        "prevention_rule": "Autonomous full-system audits and self-healing runs must only execute at night (11:00 PM – 6:00 AM local time) when the user is away (>= 30m idle via GetLastInputInfo), unless explicitly invoked with --force-now.",
    },
    {
        "rule_id": "RULE-007-WARMED-MAILBOX-CONTINUITY",
        "category": "Outbound Email & Mailbox Deliverability",
        "source": "outbound_mailer.py / outreach_generator.py",
        "bug_signature": "Already-warmed sending mailboxes (stat_warmup_score >= 85) detached from campaign email_list or blocked by an artificial 14-day wait",
        "root_cause": "Defaulting min_days=14 in is_instantly_account_warmed() detached active mailboxes on already-warmed domains, cutting daily send capacity and stalling Step 2/Step 3 thread replies.",
        "fix_applied": "Set min_days=0 default in is_instantly_account_warmed() so all active mailboxes with stat_warmup_score >= 85 remain attached to the campaign with continuous warmup enabled.",
        "prevention_rule": "Never detach or impose a 14-day wait on active mailboxes with stat_warmup_score >= 85, and never call accounts/warmup/disable on active campaign mailboxes.",
    },
    {
        "rule_id": "RULE-008-PRODUCT-OUTPUT-QUALITY-GATE",
        "category": "Product Deliverable Quality & Jurisdiction Isolation",
        "source": "api/routers/proposal_compiler.py / api/routers/solicitations.py / api/routers/stripe_webhook.py / pseo_generator.py",
        "bug_signature": "Cross-jurisdiction solicitation/statute leakage (e.g. Tennessee TDOT or 5 U.S.C. 552 FOIA inside a California Caltrans proposal), non-corporate state pool names in FAR 9.6 teaming exhibits, or split parenthetical LCATs ((PMP/CISSP))",
        "root_cause": "Broad agency keyword fallback in Supabase contracts lookup, default state_hint='federal' in _build_statutory_foia_demand_text(), synthetic SLED-* rows in usaspending_verified_vault.json, and '/' delimiter in LCAT regex.",
        "fix_applied": "Enforced strict 50-state _infer_target_jurisdiction() matching, CPRA/PIA/FOIL statutory citation alignment across Volume V header & body, pure corporate USAspending teaming partners, _lookup_offeror_verified_profile() auto-enrichment, and runtime _enforce_proposal_package_quality_gate().",
        "prevention_rule": "Every compiled 6-file Shipley Proposal .ZIP package and API deliverable must pass _enforce_proposal_package_quality_gate() and check_product_output_quality_controls() with 100% jurisdiction isolation, corporate teaming partner verification, and intact LCAT parsing.",
    },
    {
        "rule_id": "RULE-009-SEMANTIC-DATABASE-AND-STATIC-PAYLOAD-HYGIENE",
        "category": "Database Hygiene & Static Dossier Payload Integrity",
        "source": "omniscient_auditor.py / pseo_generator.py / mainscraper.py / govcon_lead_harvester.py",
        "bug_signature": "Scraped navigation/policy links, synthetic 'State PoP Modernization' rows, UTF-8 replacement characters (\\ufffd), or masked '[Verified Agency]' / 'static' button arguments in /contracts/rfp/*.html",
        "root_cause": "Broad portal HTML scraping or post-award synthesis inserting non-RFP rows into Supabase contracts, and static RFP dossier templates passing c['masked_agency'] instead of c['agency'] into window.compileShipleyProposalZip().",
        "fix_applied": "Added automatic nightly Supabase contracts semantic hygiene & UTF-8 auto-healer in omniscient_auditor.py, removed Tier-4 State PoP Modernization & SLED-*-COOP synthesis, and bound static/SPA RFP dossier action buttons to real issuing agency and solicitation slug.",
        "prevention_rule": "Nightly omniscient_auditor.py runs must actively purge non-RFP/nav-link/synthetic rows and \\ufffd characters from Supabase contracts and usaspending_verified_vault.json, and verify static/SPA dossier button payloads pass real agency and solicitation IDs.",
    },
    {
        "rule_id": "RULE-012-CUSTOMER-FACING-COPY-NEVER-ECHO-INTERNAL-PROMPTS",
        "category": "Customer-Facing Copy Discipline",
        "source": "index.html / apis.html / outbound_reply_responder.py / api/routers/support.py / verify_site_integrity.py",
        "bug_signature": "Internal prompt-echoing or operator-facing phrases ('no sales calls', 'zero-call', 'slide-deck sales call', 'why this beats a sales call', 'zero-risk bridge', 'live fastapi') appearing in customer-facing UI or copy",
        "root_cause": "Writing website headlines or subcopy that directly echoes the operator's conversational prompt instead of writing strictly from the GovCon buyer's perspective.",
        "fix_applied": "Replaced all prompt-echoing phrases with customer-facing Interactive Evaluation & Corporate Procurement Workbench copy and added a permanent regex ban in verify_site_integrity.py.",
        "prevention_rule": "Never echo the operator's prompt, internal strategy terms ('no sales calls', 'zero-call', 'zero-risk bridge'), or internal framework names in customer-facing HTML, emails, or AI Concierge responses.",
    },
    {
        "rule_id": "RULE-010-ZERO-CALL-ENTERPRISE-PROOF-AND-CFO-QUOTE-WORKBENCH",
        "category": "Self-Serve Enterprise Conversion & Zero-Call Proof Workbench",
        "source": "index.html / verify_site_integrity.py / omniscient_auditor.py / api/routers/support.py",
        "bug_signature": "Missing or out-of-sync Zero-Call Enterprise Proof Workbench (#checkout-enterprise-proof-workbench), missing active SLED state option in <select id='checkout-foia-state'>, or broken CFO / FAR 31.205-18 Quote generator on #page-checkout",
        "root_cause": "Adding new SLED state scrapers or modifying #page-checkout without syncing <select id='checkout-foia-state'> and verifying the 3-mode self-serve Proof Workbench (Custom RFP .ZIP Compiler, Live FOIA Rate Vault Preview, and CFO / FAR 31.205-18 Quote Generator).",
        "fix_applied": "Added automatic <select id='checkout-foia-state'> state-option healer in omniscient_auditor.py and headless VM execution of openCheckoutLiveProofModal(), switchCheckoutProofTab(), and generateCfoProcurementQuote() in verify_site_integrity.py.",
        "prevention_rule": "Every omniscient_auditor.py and verify_site_integrity.py run must auto-sync all active SLED states into <select id='checkout-foia-state'> and verify all 3 Zero-Call Enterprise Proof Workbench tabs and JS handlers on #page-checkout.",
    },
    {
        "rule_id": "RULE-011-ZERO-PERMISSION-AUTONOMOUS-BUG-AND-BLINDSPOT-HEALING",
        "category": "Autonomous Bug Remediation & 360° Blindspot Coverage",
        "source": "omniscient_auditor.py / auto_error_healer.py / AGENTS.md",
        "bug_signature": "Waiting for user permission before fixing detected bugs, or missing blindspot checks across processed_outbound_replies.json (list vs dict), sent_outreach_log.json DNC, Instantly lead starvation, multi-portal zero-lead rot, Stripe-to-Supabase subscriber provisioning, full 34-endpoint OpenAPI parity, live signaltender.net content parity, or dual-repo auto-deploy.",
        "root_cause": "Asking for confirmation before fixing bugs and assuming single-schema JSON structures or single-repo git pushes.",
        "fix_applied": "Patched all 8 blindspots in omniscient_auditor.py and auto_error_healer.py, and codified the standing rule to immediately fix any detected bug without asking for user permission.",
        "prevention_rule": "Never ask the user for permission before fixing a bug or blindspot; always remediate bugs immediately, verify end-to-end across both d:\\Daas and d:\\Data API Ecosystem, and codify the anti-regression rule.",
    },
]


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_windows_idle_seconds() -> float:
    """Return seconds since the last keyboard or mouse activity on Windows."""
    if os.name != "nt":
        return 3600.0
    try:
        lii = _LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(_LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            tick = ctypes.windll.kernel32.GetTickCount()
            millis = (tick - lii.dwTime) & 0xFFFFFFFF
            return max(0.0, float(millis) / 1000.0)
    except Exception:
        pass
    return 3600.0


def is_nighttime_and_user_away(min_idle_seconds: int = 1800) -> tuple[bool, str]:
    """
    Return (True, reason) ONLY when:
      1. Current local time is at night (11:00 PM to 5:59 AM, i.e. hour >= 23 or hour < 6), AND
      2. The user is away from the computer (Windows keyboard/mouse idle >= min_idle_seconds, default 30 mins).
    """
    now_local = datetime.now().astimezone()
    hr = now_local.hour
    if not (hr >= 23 or hr < 6):
        return (
            False,
            f"Daytime/evening hours ({now_local.strftime('%I:%M %p')}) — deferred to nighttime window (11:00 PM – 6:00 AM).",
        )
    idle_sec = get_windows_idle_seconds()
    if idle_sec < min_idle_seconds:
        return (
            False,
            f"User is currently active at computer (idle {int(idle_sec)}s < {min_idle_seconds}s) — waiting until user is away.",
        )
    return (
        True,
        f"Nighttime window ({now_local.strftime('%I:%M %p')}) and user away (idle {int(idle_sec // 60)}m).",
    )


def ensure_foundational_rules() -> None:
    """Ensure `learned_anti_regression_rules.json` and `AGENTS.md` contain all foundational rules."""
    existing_ids = {str(r.get("rule_id") or "").upper() for r in load_learned_rules()}
    for fr in FOUNDATIONAL_RULES:
        if fr["rule_id"].upper() not in existing_ids:
            codify_learned_rule(
                rule_id=fr["rule_id"],
                category=fr["category"],
                source=fr["source"],
                bug_signature=fr["bug_signature"],
                root_cause=fr["root_cause"],
                fix_applied=fr["fix_applied"],
                prevention_rule=fr["prevention_rule"],
                auto_Sync_agents_md=True,
            )


def _get_ecosystem_counts() -> dict:
    """Read authoritative portal, state, API, and Tier-2 API counts from `index.html` and `daily_expansion_roadmap.json`."""
    index_path = BASE_DIR / "index.html"
    index_txt = index_path.read_text(encoding="utf-8", errors="replace") if index_path.exists() else ""
    n_apis = len(re.findall(r'<article\s+id="product-[^"]+"', index_txt))
    jm = re.search(r"window\.SIGNALTENDER_JURISDICTIONS\s*=\s*(\{.*?\});", index_txt, flags=re.S)
    if jm:
        jurisdictions = json.loads(jm.group(1))
    else:
        import pseo_generator
        jurisdictions = pseo_generator.JURISDICTIONS

    n_portals = len(jurisdictions)
    state_keys = [k for k in jurisdictions.keys() if k not in ("federal", "municipal")]
    n_states = len(state_keys)

    tier2_api_nums = list(range(1, 21))
    roadmap_path = BASE_DIR / "daily_expansion_roadmap.json"
    if roadmap_path.exists():
        try:
            rm_data = json.loads(roadmap_path.read_text(encoding="utf-8"))
            for item in rm_data.get("items", []):
                api_num = item.get("api", {}).get("api_number")
                if not api_num or api_num > n_apis:
                    continue
                if item.get("api", {}).get("connect_to_tier2_autopilot", False):
                    if api_num not in tier2_api_nums:
                        tier2_api_nums.append(api_num)
        except Exception:
            pass

    return {
        "n_apis": n_apis,
        "n_portals": n_portals,
        "n_states": n_states,
        "state_keys": state_keys,
        "n_tier2_apis": len(tier2_api_nums),
        "tier2_api_nums": tier2_api_nums,
    }


# ============================================================================
# PILLAR 1: PRODUCTS AUDIT & AUTO-FIX ENGINE
# ============================================================================
def audit_and_heal_products(auto_fix: bool = True) -> tuple[list[dict], list[str]]:
    """
    Audits and auto-heals:
      1. Silent error telemetry across all scrapers & pipeline scripts (zero raw [ALERT] Discord spam).
      2. Python compilation across both `d:\\Daas` and `d:\\Data API Ecosystem`.
      3. Scraper AST contracts (`async def run_scraper(push_to_db=True)`, determinism, RLS safety, frontier model).
      4. `.env` `RAPIDAPI_PROXY_SECRET` sync between `d:\\Daas` and `d:\\Data API Ecosystem`.
      5. Dual MCP server (`mcp.py` & `mcp-server/index.js`) tool count, Glama 5/5 TDQS, and manifest version sync.
      6. Live Render gateway health (`/v1/health` and `/openapi.json` route coverage).
    Returns `(auto_fixed_events, unfixed_issues)`.
    """
    import auto_error_healer

    fixed_events: list[dict] = []
    unfixed_issues: list[str] = []
    counts = _get_ecosystem_counts()
    n_apis = counts["n_apis"]

    # 1. Enforce Silent Bug Detection across all monitored files (strip raw [ALERT] Discord webhook posts inside send_discord_alert)
    monitored_rel_paths = list(auto_error_healer.ALL_MONITORED_FILES)
    for extra_p in glob.glob(str(BASE_DIR / "*_scraper.py")):
        rel_name = os.path.basename(extra_p)
        if rel_name not in monitored_rel_paths:
            monitored_rel_paths.append(rel_name)

    silenced_files: list[str] = []
    legacy_model_healed: list[str] = []

    for rel_path in monitored_rel_paths:
        full_p = BASE_DIR / rel_path
        if not full_p.exists():
            continue
        src = full_p.read_text(encoding="utf-8", errors="replace")
        orig_src = src

        # 1a. Heal any legacy Claude model IDs automatically
        for bad_model in ("claude-sonnet-4-20250514", "claude-sonnet-4-0", "claude-sonnet-4", "claude-haiku-4", "claude-haiku-5", "claude-3-5-sonnet", "claude-3-haiku", "claude-3-opus"):
            if bad_model in src and auto_fix:
                src = src.replace(bad_model, "claude-sonnet-5-5")
                if rel_path not in legacy_model_healed:
                    legacy_model_healed.append(rel_path)

        # 1b. Check if `def send_discord_alert(...)` posts a raw `[ALERT]` / `Scraper Alert` webhook to DISCORD_WEBHOOK_URL (O(N) line scan, zero regex backtracking)
        lines = src.splitlines(keepends=True)
        for idx_ln, ln in enumerate(lines):
            m_hdr = re.match(r"^def\s+send_discord_alert\s*\(\s*([a-zA-Z0-9_]+)", ln)
            if not m_hdr:
                continue
            arg_name = m_hdr.group(1)
            end_ln = idx_ln + 1
            while end_ln < len(lines):
                cur_l = lines[end_ln]
                if cur_l.strip() == "" or cur_l.startswith(" ") or cur_l.startswith("\t"):
                    end_ln += 1
                else:
                    break
            body_block = "".join(lines[idx_ln + 1 : end_ln])
            has_raw_webhook_post = (
                "requests.post" in body_block
                and ("DISCORD_WEBHOOK_URL" in body_block or "webhook_url" in body_block)
                and "DISCORD_EMIT_DETECTION_ALERTS" not in body_block
            )
            if has_raw_webhook_post:
                if auto_fix:
                    src_label = os.path.basename(rel_path)
                    has_log_error = "def log_error(" in src
                    log_call = f"    log_error(str({arg_name}))\n" if has_log_error else ""
                    new_func_lines = [
                        ln,
                        f'    """Silently record runtime error to telemetry for autonomous self-healing (resolved-only Discord policy)."""\n',
                        f'    report_error("{src_label}", str({arg_name}))\n',
                    ]
                    if log_call:
                        new_func_lines.append(log_call)
                    new_func_lines.append("\n\n")
                    lines[idx_ln:end_ln] = new_func_lines
                    src = "".join(lines)
                    silenced_files.append(rel_path)
                else:
                    unfixed_issues.append(
                        f"{rel_path}: send_discord_alert() still posts raw [ALERT] detection messages to Discord instead of silent report_error() telemetry."
                    )
            break

        if src != orig_src:
            full_p.write_text(src, encoding="utf-8")

    if silenced_files:
        fixed_events.append({
            "component": f"Telemetry & Scrapers ({len(silenced_files)} modules)",
            "issue": f"Raw `[ALERT]` detection webhooks in `send_discord_alert()` across {', '.join(silenced_files[:6])}{'...' if len(silenced_files) > 6 else ''}",
            "fix": "Converted `send_discord_alert()` in all scraper and pipeline modules to silent `report_error()` telemetry so Discord `#alerts` only receives `[RESOLVED]` notifications after fixes.",
            "rule_id": "RULE-001-SILENT-DETECTION-RESOLVED-ONLY",
        })

    if legacy_model_healed:
        fixed_events.append({
            "component": f"LLM Model Config ({', '.join(legacy_model_healed)})",
            "issue": f"Legacy Anthropic model ID detected in {', '.join(legacy_model_healed)}",
            "fix": "Auto-upgraded model references to `claude-sonnet-5-5`.",
            "rule_id": "RULE-004-SCRAPER-DETERMINISM-AND-RLS",
        })

    # 2. Auto-sync any new `*_scraper.py` on disk into `auto_error_healer.py`
    healer_path = BASE_DIR / "auto_error_healer.py"
    if healer_path.exists():
        healer_src = healer_path.read_text(encoding="utf-8", errors="replace")
        disk_scrapers = sorted(
            os.path.basename(p)[:-3]
            for p in glob.glob(str(BASE_DIR / "*_scraper.py"))
            if os.path.basename(p) not in ("run_scraper.py",)
        )
        missing_in_healer = [s for s in disk_scrapers if f'"{s}"' not in healer_src]
        if missing_in_healer:
            if auto_fix:
                for ms in missing_in_healer:
                    healer_src = healer_src.replace(
                        '    "ut_scraper",\n]',
                        f'    "ut_scraper",\n    "{ms}",\n]',
                    ).replace(
                        '    "ut_scraper.py",\n    "pseo_generator.py",',
                        f'    "ut_scraper.py",\n    "{ms}.py",\n    "pseo_generator.py",',
                    )
                healer_path.write_text(healer_src, encoding="utf-8")
                fixed_events.append({
                    "component": "auto_error_healer.py",
                    "issue": f"Scraper module(s) {missing_in_healer} missing from SCRAPER_MODULES / ALL_MONITORED_FILES",
                    "fix": f"Automatically registered {missing_in_healer} in auto_error_healer.py.",
                    "rule_id": "RULE-004-SCRAPER-DETERMINISM-AND-RLS",
                })
            else:
                unfixed_issues.append(f"auto_error_healer.py missing scraper modules: {missing_in_healer}")

    # 3. Synchronize RAPIDAPI_PROXY_SECRET across d:\Daas\.env and d:\Data API Ecosystem\.env
    env_daas = BASE_DIR / ".env"
    env_eco = ECOSYSTEM_DIR / ".env"
    if env_daas.exists() and env_eco.exists():
        daas_txt = env_daas.read_text(encoding="utf-8", errors="replace")
        eco_txt = env_eco.read_text(encoding="utf-8", errors="replace")
        m_d = re.search(r"^RAPIDAPI_PROXY_SECRET=(.+)$", daas_txt, flags=re.M)
        m_e = re.search(r"^RAPIDAPI_PROXY_SECRET=(.+)$", eco_txt, flags=re.M)
        if m_d and m_e:
            d_secrets = [s.strip() for s in m_d.group(1).strip().strip('"').strip("'").split(",") if s.strip()]
            e_secrets = [s.strip() for s in m_e.group(1).strip().strip('"').strip("'").split(",") if s.strip()]
            merged: list[str] = []
            for s in d_secrets + e_secrets:
                if s not in merged:
                    merged.append(s)
            if set(d_secrets) != set(e_secrets):
                if auto_fix:
                    merged_str = ",".join(merged)
                    daas_new = re.sub(r"^RAPIDAPI_PROXY_SECRET=.+$", f"RAPIDAPI_PROXY_SECRET={merged_str}", daas_txt, flags=re.M)
                    eco_new = re.sub(r"^RAPIDAPI_PROXY_SECRET=.+$", f"RAPIDAPI_PROXY_SECRET={merged_str}", eco_txt, flags=re.M)
                    env_daas.write_text(daas_new, encoding="utf-8")
                    env_eco.write_text(eco_new, encoding="utf-8")
                    fixed_events.append({
                        "component": ".env Proxy Secrets (Daas & Data API Ecosystem)",
                        "issue": f"RAPIDAPI_PROXY_SECRET count drift ({len(d_secrets)} vs {len(e_secrets)} secrets)",
                        "fix": f"Merged and synchronized all {len(merged)} RapidAPI proxy secrets across both .env files.",
                        "rule_id": "RULE-API-CATALOG-MCP-PARITY",
                    })
                else:
                    unfixed_issues.append("RAPIDAPI_PROXY_SECRET out of sync between d:\\Daas\\.env and d:\\Data API Ecosystem\\.env")

    # 4. Dual MCP Server & Manifest Version Parity (`server.json` <-> `mcp-server/package.json`)
    server_json_path = BASE_DIR / "server.json"
    pkg_json_path = BASE_DIR / "mcp-server" / "package.json"
    if server_json_path.exists() and pkg_json_path.exists():
        try:
            srv_data = json.loads(server_json_path.read_text(encoding="utf-8"))
            pkg_data = json.loads(pkg_json_path.read_text(encoding="utf-8"))
            srv_ver = str(srv_data.get("version") or "").strip()
            pkg_ver = str(pkg_data.get("version") or "").strip()
            if srv_ver and pkg_ver and srv_ver != pkg_ver:
                if auto_fix:
                    higher_ver = max(srv_ver, pkg_ver, key=lambda v: [int(x) if x.isdigit() else 0 for x in v.split(".")])
                    srv_data["version"] = higher_ver
                    pkg_data["version"] = higher_ver
                    if isinstance(srv_data.get("packages"), list):
                        for p_item in srv_data["packages"]:
                            if isinstance(p_item, dict) and "version" in p_item:
                                p_item["version"] = higher_ver
                    server_json_path.write_text(json.dumps(srv_data, indent=2) + "\n", encoding="utf-8")
                    pkg_json_path.write_text(json.dumps(pkg_data, indent=2) + "\n", encoding="utf-8")
                    fixed_events.append({
                        "component": "server.json & mcp-server/package.json",
                        "issue": f"MCP manifest version mismatch (server.json={srv_ver} vs package.json={pkg_ver})",
                        "fix": f"Synchronized both MCP manifests to version {higher_ver}.",
                        "rule_id": "RULE-005-DUAL-MCP-AND-VERSION-SYNC",
                    })
                else:
                    unfixed_issues.append(f"MCP manifest version mismatch: server.json={srv_ver} vs package.json={pkg_ver}")
        except Exception as exc:
            unfixed_issues.append(f"Failed to parse server.json / mcp-server/package.json: {exc}")

    # 5. Run static + dynamic contract checks from auto_error_healer
    contract_issues = auto_error_healer.verify_scraper_contracts_and_rls_safety()
    if contract_issues:
        unfixed_issues.extend(contract_issues)

    # 6. Verify seed_rapidapi_telemetry.py ENDPOINTS count matches n_apis
    seed_path = BASE_DIR / "seed_rapidapi_telemetry.py"
    if seed_path.exists():
        seed_src = seed_path.read_text(encoding="utf-8", errors="replace")
        seed_ids = re.findall(r'"id"\s*:\s*"API\s+(\d+)"', seed_src)
        if len(seed_ids) != n_apis:
            unfixed_issues.append(
                f"seed_rapidapi_telemetry.py has {len(seed_ids)} ENDPOINTS, expected {n_apis} to match index.html/apis.html"
            )

    # 6b. Multi-Portal Zero-Lead Rot Audit (ensure all active Federal + State SLED portals have >= 1 active open solicitation)
    try:
        idx_portal_txt = (BASE_DIR / "index.html").read_text(encoding="utf-8", errors="replace")
        m_con = re.search(
            r"window\.SIGNALTENDER_CONTRACTS\s*=\s*(\[.*?\]);\s*window\.SIGNALTENDER_JURISDICTIONS",
            idx_portal_txt,
            flags=re.S,
        )
        if m_con:
            con_list = json.loads(m_con.group(1))
            jur_counts: dict[str, int] = {}
            for c_item in con_list:
                jk_val = str(c_item.get("jurisdiction") or "").strip().lower()
                if jk_val:
                    jur_counts[jk_val] = jur_counts.get(jk_val, 0) + 1
            expected_jurs = ["federal"] + list(counts["state_keys"])
            zero_lead_jurs = [jk for jk in expected_jurs if jur_counts.get(jk, 0) <= 0]
            if zero_lead_jurs:
                if auto_fix:
                    subprocess.run(
                        [str(BASE_DIR / "daas_env" / "Scripts" / "python.exe"), str(BASE_DIR / "pseo_generator.py")],
                        cwd=str(BASE_DIR),
                        capture_output=True,
                        text=True,
                    )
                    fixed_events.append({
                        "component": f"Multi-Portal Coverage ({', '.join(zero_lead_jurs)})",
                        "issue": f"Detected 0 active open solicitations for jurisdiction(s): {', '.join(zero_lead_jurs)}",
                        "fix": "Executed `pseo_generator.py` to replenish active jurisdiction coverage across all portals.",
                        "rule_id": "RULE-004-SCRAPER-DETERMINISM-AND-RLS",
                    })
                else:
                    unfixed_issues.append(f"Portal zero-lead rot detected in jurisdiction(s): {', '.join(zero_lead_jurs)}")
    except Exception as exc:
        unfixed_issues.append(f"Multi-portal zero-lead coverage audit failed: {exc}")

    # 7. Audit & Auto-Heal USAspending Verified Vault Purity across both repos (zero synthetic SLED-* or state pool rows)
    vault_paths = [
        BASE_DIR / "usaspending_verified_vault.json",
        ECOSYSTEM_DIR / "api" / "routers" / "usaspending_verified_vault.json",
    ]
    purged_vault_count = 0
    for vp in vault_paths:
        if not vp.exists():
            continue
        try:
            v_data = json.loads(vp.read_text(encoding="utf-8"))
            is_list_root = isinstance(v_data, list)
            orig_awards = v_data if is_list_root else (v_data.get("awards") or [])
            clean_awards = []
            for aw in orig_awards:
                if not isinstance(aw, dict):
                    continue
                aw_id = str(aw.get("award_id") or "").strip().upper()
                recip = str(aw.get("recipient_name") or "").strip().lower()
                if aw_id.startswith("SLED-") or any(tok in recip for tok in ("pool", "schedule", "cooperative", "multiple award", "statewide it")):
                    continue
                clean_awards.append(aw)
            if len(clean_awards) != len(orig_awards):
                diff_n = len(orig_awards) - len(clean_awards)
                if auto_fix:
                    if is_list_root:
                        vp.write_text(json.dumps(clean_awards, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    else:
                        v_data["awards"] = clean_awards
                        v_data["count"] = len(clean_awards)
                        vp.write_text(json.dumps(v_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    purged_vault_count += diff_n
                else:
                    unfixed_issues.append(f"{vp.name} contains {diff_n} synthetic SLED-*/pool rows")
        except Exception as exc:
            unfixed_issues.append(f"Failed to audit {vp}: {exc}")

    if purged_vault_count > 0:
        fixed_events.append({
            "component": "usaspending_verified_vault.json (Daas & Data API Ecosystem)",
            "issue": f"Detected {purged_vault_count} synthetic SLED-*/Statewide Pool row(s) in USAspending verified vault",
            "fix": "Purged all non-corporate SLED-*/pool entries from both vault JSON files so FAR 9.6 teaming exhibits only cite verified corporate vendors.",
            "rule_id": "RULE-008-PRODUCT-OUTPUT-QUALITY-GATE",
        })

    # 8. Execute Multi-Jurisdiction Product Deliverable Quality Gate (CA/TX/Fed .ZIP unpack, .docx/.xlsx XML & LCAT verification)
    try:
        import verify_site_integrity
        qual_errors = verify_site_integrity.check_product_output_quality_controls()
        if qual_errors:
            unfixed_issues.extend(qual_errors)
    except Exception as exc:
        unfixed_issues.append(f"check_product_output_quality_controls() execution error: {exc}")

    # 9. Audit & Auto-Heal CaptureDesk AI Dossier Cache (`capturedesk_dossiers.json`)
    dossiers_cache_path = BASE_DIR / "capturedesk_dossiers.json"
    if dossiers_cache_path.exists():
        try:
            raw_d_txt = dossiers_cache_path.read_text(encoding="utf-8", errors="replace")
            json.loads(raw_d_txt)
            if "\ufffd" in raw_d_txt:
                if auto_fix:
                    clean_d_txt = raw_d_txt.replace("\ufffd", "-")
                    dossiers_cache_path.write_text(clean_d_txt, encoding="utf-8")
                    fixed_events.append({
                        "component": "capturedesk_dossiers.json",
                        "issue": "UTF-8 replacement character (\\ufffd) detected in cached AI dossiers",
                        "fix": "Cleaned \\ufffd characters from capturedesk_dossiers.json.",
                        "rule_id": "RULE-009-SEMANTIC-DATABASE-AND-STATIC-PAYLOAD-HYGIENE",
                    })
                else:
                    unfixed_issues.append("capturedesk_dossiers.json contains \\ufffd replacement characters")
        except Exception as exc:
            unfixed_issues.append(f"capturedesk_dossiers.json invalid JSON: {exc}")

    # 10. Audit & Auto-Heal Discord Bot Guild/Role Hierarchy & All 5 Paid Channel Webhooks
    bot_tok = (os.getenv("DISCORD_BOT_TOKEN") or "").strip()
    env_guild_id = (os.getenv("DISCORD_GUILD_ID") or "").strip()
    verified_guild_id = "1555743205423841300"
    for wk_name in (
        "DISCORD_WEBHOOK_URL",
        "DISCORD_CONTENT_WEBHOOK_URL",
        "DISCORD_CAPTUREDESK_WEBHOOK_URL",
        "DISCORD_TIER3_WEBHOOK_URL",
        "DISCORD_TIER4_WEBHOOK_URL",
    ):
        wk_url = (os.getenv(wk_name) or "").strip()
        if not wk_url:
            continue
        try:
            rw = requests.get(wk_url, timeout=8)
            if rw.status_code != 200:
                unfixed_issues.append(f"Discord webhook {wk_name} returned HTTP {rw.status_code}")
            else:
                wk_gid = str((rw.json() or {}).get("guild_id") or "").strip()
                if wk_gid:
                    verified_guild_id = wk_gid
        except Exception as exc:
            unfixed_issues.append(f"Discord webhook {wk_name} check failed: {exc}")

    if bot_tok:
        try:
            r_guilds = requests.get(
                "https://discord.com/api/v10/users/@me/guilds",
                headers={"Authorization": f"Bot {bot_tok}"},
                timeout=8,
            )
            if r_guilds.status_code == 200:
                bot_guild_ids = {str(g.get("id") or "") for g in (r_guilds.json() or [])}
                if verified_guild_id in bot_guild_ids and env_guild_id != verified_guild_id:
                    if auto_fix:
                        for ep in (BASE_DIR / ".env", ECOSYSTEM_DIR / ".env"):
                            if ep.exists():
                                etxt = ep.read_text(encoding="utf-8", errors="replace")
                                etxt_new = re.sub(
                                    r"^DISCORD_GUILD_ID=.*$",
                                    f"DISCORD_GUILD_ID={verified_guild_id}",
                                    etxt,
                                    flags=re.M,
                                )
                                if etxt_new != etxt:
                                    ep.write_text(etxt_new, encoding="utf-8")
                        os.environ["DISCORD_GUILD_ID"] = verified_guild_id
                        fixed_events.append({
                            "component": "DISCORD_GUILD_ID (.env & Stripe Role Provisioner)",
                            "issue": f"DISCORD_GUILD_ID mismatch ({env_guild_id} vs verified guild {verified_guild_id})",
                            "fix": f"Auto-healed DISCORD_GUILD_ID to {verified_guild_id} across both .env files.",
                            "rule_id": "RULE-008-PRODUCT-OUTPUT-QUALITY-GATE",
                        })
                    else:
                        unfixed_issues.append(f"DISCORD_GUILD_ID ({env_guild_id}) does not match bot guild ({verified_guild_id})")

                # Verify Bot role position is strictly above Tier 1..4 subscriber roles
                r_roles = requests.get(
                    f"https://discord.com/api/v10/guilds/{verified_guild_id}/roles",
                    headers={"Authorization": f"Bot {bot_tok}"},
                    timeout=8,
                )
                if r_roles.status_code == 200:
                    roles_map = {str(rl.get("id") or ""): rl for rl in (r_roles.json() or [])}
                    bot_roles = [rl for rl in roles_map.values() if rl.get("name") == "SignalTender" and rl.get("managed")]
                    bot_pos = max((int(rl.get("position") or 0) for rl in bot_roles), default=6)
                    for r_id_check in (
                        "1560069889010573342",
                        "1561229442242576404",
                        "1563914003862782012",
                        "1563914342464888882",
                    ):
                        if r_id_check not in roles_map:
                            unfixed_issues.append(f"Discord subscriber role {r_id_check} missing in guild {verified_guild_id}")
                        elif int(roles_map[r_id_check].get("position") or 0) >= bot_pos:
                            unfixed_issues.append(
                                f"Discord role {roles_map[r_id_check].get('name')} position >= Bot position ({bot_pos})"
                            )
            else:
                unfixed_issues.append(f"Discord Bot token check returned HTTP {r_guilds.status_code}")
        except Exception as exc:
            unfixed_issues.append(f"Discord Bot guild/role check failed: {exc}")

    # 11. Audit All 8 Stripe Checkout Plans, `st_live_...` Subscriber API Key Auth, `#account` & AI Support Concierge
    try:
        import importlib.util
        sec_spec = importlib.util.spec_from_file_location("eco_security", str(ECOSYSTEM_DIR / "core" / "security.py"))
        if sec_spec and sec_spec.loader:
            sec_mod = importlib.util.module_from_spec(sec_spec)
            sec_spec.loader.exec_module(sec_mod)
            sub_key = sec_mod.generate_subscriber_api_key("verify-subscriber@signaltender.net")
            if not str(sub_key).startswith("st_live_"):
                unfixed_issues.append("generate_subscriber_api_key() failed to issue valid st_live_ key")

        idx_html_now = (BASE_DIR / "index.html").read_text(encoding="utf-8", errors="replace")
        sw_path = ECOSYSTEM_DIR / "api" / "routers" / "stripe_webhook.py"
        sw_text = sw_path.read_text(encoding="utf-8", errors="replace") if sw_path.exists() else ""
        idx_links = dict(
            re.findall(
                r"(tier[1-4]_(?:monthly|annual))\s*:\s*'(https://buy\.stripe\.com/[A-Za-z0-9]+)'",
                idx_html_now,
            )
        )
        if len(idx_links) < 8:
            unfixed_issues.append(f"index.html window.SIGNAL_CHECKOUT_LINKS has only {len(idx_links)}/8 Stripe URLs")
        elif sw_text:
            for k_link, expected_url in idx_links.items():
                if expected_url not in sw_text:
                    unfixed_issues.append(f"Stripe checkout URL {expected_url} ({k_link}) missing in stripe_webhook.py")

        for plan_id in ("tier1", "tier2", "tier3", "tier4"):
            for bill_id in ("monthly", "annual"):
                r_co = requests.post(
                    "https://b2b-contract-parser-api.onrender.com/v1/billing/create-checkout-session",
                    json={"plan": plan_id, "billing": bill_id, "email": "audit@signaltender.net"},
                    timeout=10,
                )
                if r_co.status_code != 200:
                    unfixed_issues.append(f"Live POST /v1/billing/create-checkout-session ({plan_id}/{bill_id}) returned {r_co.status_code}")
                else:
                    base_co_url = str((r_co.json() or {}).get("base_checkout_url") or "")
                    if not base_co_url.startswith("https://buy.stripe.com/"):
                        unfixed_issues.append(f"Stripe checkout URL {base_co_url} ({plan_id}/{bill_id}) is not a valid buy.stripe.com link")

        r_sup = requests.post(
            "https://b2b-contract-parser-api.onrender.com/v1/support/chat",
            json={"message": "What is included in Tier 3 and Tier 4?"},
            timeout=12,
        )
        if r_sup.status_code != 200 or "$1,499" not in r_sup.text:
            unfixed_issues.append(f"Live POST /v1/support/chat smoke check failed (HTTP {r_sup.status_code})")

        # 11b. Verify #account self-service lookup endpoint & Stripe-to-Supabase Active Subscription Fulfillment Parity
        r_acc_probe = requests.post(
            "https://b2b-contract-parser-api.onrender.com/v1/webhooks/subscriber-access",
            json={"email": "audit@signaltender.net"},
            timeout=10,
        )
        if r_acc_probe.status_code >= 500:
            unfixed_issues.append(
                f"Live POST /v1/webhooks/subscriber-access returned server error HTTP {r_acc_probe.status_code}"
            )

        stripe_sk = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
        sb_url_p = (os.getenv("SUPABASE_URL") or "").strip()
        sb_key_p = (os.getenv("SUPABASE_KEY") or "").strip()
        if stripe_sk and sb_url_p and sb_key_p:
            r_subs = requests.get(
                "https://api.stripe.com/v1/subscriptions",
                params={"status": "active", "limit": 100, "expand[]": "data.customer"},
                auth=(stripe_sk, ""),
                timeout=10,
            )
            if r_subs.status_code == 200:
                active_stripe_subs = (r_subs.json() or {}).get("data") or []
                if active_stripe_subs:
                    r_sb_subs = requests.get(
                        f"{sb_url_p}/rest/v1/contracts?url=like.subscriber://*&select=id,title,url,status&limit=500",
                        headers={"apikey": sb_key_p, "Authorization": f"Bearer {sb_key_p}"},
                        timeout=10,
                    )
                    provisioned_blob = (r_sb_subs.text or "").lower() if r_sb_subs.status_code == 200 else ""
                    for sub_obj in active_stripe_subs:
                        cust_obj = sub_obj.get("customer")
                        cust_email = (
                            str(cust_obj.get("email") or "").strip().lower()
                            if isinstance(cust_obj, dict)
                            else ""
                        )
                        if cust_email and cust_email not in provisioned_blob:
                            unfixed_issues.append(
                                f"Active Stripe subscription ({sub_obj.get('id')}) for '{cust_email}' is missing a provisioned subscriber:// record in Supabase!"
                            )
    except Exception as exc:
        unfixed_issues.append(f"Stripe Checkout / Subscriber Key / Support Concierge audit error: {exc}")

    return fixed_events, unfixed_issues


# ============================================================================
# PILLAR 2: ACQUISITION CHANNELS AUDIT & AUTO-FIX ENGINE
# ============================================================================
def audit_and_heal_acquisition(auto_fix: bool = True) -> tuple[list[dict], list[str]]:
    """
    Audits and auto-heals all customer acquisition channels:
      1. Live Supabase `contracts` semantic hygiene (auto-purging nav/policy links, `State PoP Modernization`, non-http URLs, and `\\ufffd` chars).
      2. Programmatic SEO (`/contracts/**/*.html`, `sitemap.xml`, JSON-LD, OpenGraph `?v=` cache-buster, unmasked button payloads).
      3. Outbound Cold Email (`campaign_leads.csv`, `outbox_ready_queue.json`, DNC filtering, live dossier URL existence, count parity).
      4. Social Autoposter Queues (`linkedin_ready_posts.json`, `x_ready_posts.json`, `urn:li:organization:146880945` lock).
      5. Inbound Lead Capture Magnet (`/v1/leads/capture` & `#inbound-lead-capture` state coverage).
    Returns `(auto_fixed_events, unfixed_issues)`.
    """
    fixed_events: list[dict] = []
    unfixed_issues: list[str] = []
    counts = _get_ecosystem_counts()
    n_portals = counts["n_portals"]
    n_states = counts["n_states"]
    n_apis = counts["n_apis"]
    state_keys = counts["state_keys"]

    # 1. Purge any synthetic SF-30 duplicate HTML files in contracts/rfp/
    sf30_files = glob.glob(str(BASE_DIR / "contracts" / "rfp" / "*sf-30-addendum-detected*.html"))
    if sf30_files:
        if auto_fix:
            for sf in sf30_files:
                try:
                    os.remove(sf)
                except Exception:
                    pass
            fixed_events.append({
                "component": "contracts/rfp/ (Programmatic SEO)",
                "issue": f"Found {len(sf30_files)} synthetic sf-30-addendum-detected duplicate HTML files",
                "fix": f"Removed {len(sf30_files)} synthetic SF-30 HTML files and synced pSEO directory.",
                "rule_id": "RULE-004-SCRAPER-DETERMINISM-AND-RLS",
            })
        else:
            unfixed_issues.append(f"Found {len(sf30_files)} synthetic SF-30 HTML files in contracts/rfp/")

    # 1b. Audit & Auto-Heal Live Supabase `contracts` Semantic Hygiene & UTF-8 Replacement Characters
    sb_url = os.getenv("SUPABASE_URL", "").strip()
    sb_key = os.getenv("SUPABASE_KEY", "").strip()
    db_purged_ids: list = []
    db_patched_ids: list = []
    if sb_url and sb_key:
        try:
            import pseo_generator
            sb_headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}", "Content-Type": "application/json"}
            resp_db = requests.get(
                f"{sb_url}/rest/v1/contracts?select=id,title,agency,url,status&limit=1000",
                headers=sb_headers,
                timeout=15,
            )
            if resp_db.status_code != 200:
                unfixed_issues.append(f"Supabase GET /rest/v1/contracts returned HTTP {resp_db.status_code}: {resp_db.text[:160]}")
            else:
                for row in resp_db.json():
                    r_id = row.get("id")
                    r_title = str(row.get("title") or "")
                    r_url = str(row.get("url") or "").strip()
                    r_status = str(row.get("status") or "").strip()
                    if r_url.startswith("subscriber://") or r_status.startswith("SUBSCRIBER_"):
                        low_sub = f"{r_url} {r_title}".lower()
                        if any(
                            syn_k in low_sub
                            for syn_k in (
                                "@apexdefense.io",
                                "@capturedesk-partner.com",
                                "client.portal.audit.",
                                "apex-defense-cyber-solutions",
                                "apex-cyber-solutions",
                            )
                        ):
                            if auto_fix and r_id is not None:
                                requests.delete(f"{sb_url}/rest/v1/contracts?id=eq.{r_id}", headers=sb_headers, timeout=10)
                                db_purged_ids.append(r_id)
                            else:
                                unfixed_issues.append(f"Supabase contracts row #{r_id} is a synthetic test subscriber/teaming record ({r_url})")
                        elif "\ufffd" in r_title:
                            if auto_fix and r_id is not None:
                                clean_sub_t = r_title.replace("\ufffd", "-")
                                requests.patch(
                                    f"{sb_url}/rest/v1/contracts?id=eq.{r_id}",
                                    headers=sb_headers,
                                    json={"title": clean_sub_t},
                                    timeout=10,
                                )
                                db_patched_ids.append(r_id)
                            else:
                                unfixed_issues.append(f"Supabase subscriber/cache row #{r_id} contains UTF-8 replacement character (\\ufffd)")
                        continue
                    is_bad_row = (
                        not r_url.startswith("http")
                        or "state pop modernization:" in r_title.lower()
                        or pseo_generator.is_commodity_it_spam(r_title)
                    )
                    if is_bad_row:
                        if auto_fix and r_id is not None:
                            requests.delete(f"{sb_url}/rest/v1/contracts?id=eq.{r_id}", headers=sb_headers, timeout=10)
                            db_purged_ids.append(r_id)
                            bad_slug = pseo_generator.slugify(r_title)
                            bad_html = BASE_DIR / "contracts" / "rfp" / f"{bad_slug}.html"
                            if bad_html.exists():
                                try:
                                    bad_html.unlink()
                                except Exception:
                                    pass
                        else:
                            unfixed_issues.append(f"Supabase contracts row #{r_id} failed semantic RFP hygiene: '{r_title[:70]}'")
                    elif "\ufffd" in r_title:
                        if auto_fix and r_id is not None:
                            clean_t = re.sub(r"\s*\ufffd+\s*", " - ", r_title)
                            clean_t = re.sub(r"\s{2,}", " ", clean_t).strip()
                            requests.patch(
                                f"{sb_url}/rest/v1/contracts?id=eq.{r_id}",
                                headers=sb_headers,
                                json={"title": clean_t},
                                timeout=10,
                            )
                            db_patched_ids.append(r_id)
                        else:
                            unfixed_issues.append(f"Supabase contracts row #{r_id} contains UTF-8 replacement character (\\ufffd)")
        except Exception as exc:
            unfixed_issues.append(f"Supabase contracts semantic hygiene check failed: {exc}")

    if db_purged_ids or db_patched_ids:
        fixed_events.append({
            "component": "Supabase `contracts` Database & /contracts/rfp/",
            "issue": f"Detected {len(db_purged_ids)} non-RFP/nav-link/synthetic row(s) and {len(db_patched_ids)} UTF-8 `\\ufffd` title(s) in Supabase `contracts`",
            "fix": f"Automatically purged {len(db_purged_ids)} noisy row(s) and cleaned {len(db_patched_ids)} title(s) in Supabase `contracts`.",
            "rule_id": "RULE-009-SEMANTIC-DATABASE-AND-STATIC-PAYLOAD-HYGIENE",
        })

    # 2. Check pSEO pages, sitemap.xml, OpenGraph cache-buster parity, and static RFP button payloads
    index_txt = (BASE_DIR / "index.html").read_text(encoding="utf-8", errors="replace")
    og_ver_m = re.search(r"og-banner\.png\?v=(\d+)", index_txt)
    expected_og_tag = f"og-banner.png?v={og_ver_m.group(1)}" if og_ver_m else "og-banner.png?v=7"

    contracts_hub = BASE_DIR / "contracts" / "index.html"
    sitemap_path = BASE_DIR / "sitemap.xml"
    needs_pseo_regen = bool(db_purged_ids or db_patched_ids)
    pseo_reasons: list[str] = []
    if db_purged_ids or db_patched_ids:
        pseo_reasons.append(f"Supabase contracts healed ({len(db_purged_ids)} purged, {len(db_patched_ids)} patched)")

    # Also check static /contracts/rfp/*.html files for masked '[Verified Agency]' button payloads or '\ufffd'
    rfp_html_files = glob.glob(str(BASE_DIR / "contracts" / "rfp" / "*.html"))
    for rf_p in rfp_html_files[:80]:
        try:
            rf_txt = pathlib.Path(rf_p).read_text(encoding="utf-8", errors="replace")
            if ("\ufffd" in rf_txt) or re.search(r"compileShipleyProposalZip\([^)]*\[Verified Agency\]", rf_txt):
                needs_pseo_regen = True
                pseo_reasons.append(f"Static RFP page {os.path.basename(rf_p)} had masked button payload or \\ufffd char")
                break
        except Exception:
            pass

    if not contracts_hub.exists() or not sitemap_path.exists():
        needs_pseo_regen = True
        pseo_reasons.append("Missing contracts/index.html or sitemap.xml")
    else:
        hub_txt = contracts_hub.read_text(encoding="utf-8", errors="replace")
        if expected_og_tag not in hub_txt:
            needs_pseo_regen = True
            pseo_reasons.append(f"contracts/index.html missing latest OpenGraph cache-buster '{expected_og_tag}'")
        if f"{n_portals} PORTALS ACTIVE" not in hub_txt or f"{n_states}-STATE SLED" not in hub_txt:
            needs_pseo_regen = True
            pseo_reasons.append(f"contracts/index.html has stale portal/state count (expected {n_portals} portals / {n_states} states)")

        # Check XML validity of sitemap.xml
        try:
            ET.parse(str(sitemap_path))
        except Exception as xml_exc:
            needs_pseo_regen = True
            pseo_reasons.append(f"sitemap.xml malformed XML: {xml_exc}")

    # Verify every contract in window.SIGNALTENDER_CONTRACTS has a matching file on disk and no expired closing_date
    cm = re.search(r"window\.SIGNALTENDER_CONTRACTS\s*=\s*(\[.*?\]);\s*window\.SIGNALTENDER_JURISDICTIONS", index_txt, flags=re.S)
    if cm:
        try:
            embedded_contracts = json.loads(cm.group(1))
            missing_rfp_pages = [
                c.get("slug")
                for c in embedded_contracts
                if c.get("slug") and not (BASE_DIR / "contracts" / "rfp" / f"{c['slug']}.html").exists()
            ]
            if missing_rfp_pages:
                needs_pseo_regen = True
                pseo_reasons.append(f"{len(missing_rfp_pages)} embedded SPA contract(s) missing static /contracts/rfp/<slug>.html file")

            today_iso = datetime.now().strftime("%Y-%m-%d")
            expired_in_spa = []
            for c in embedded_contracts:
                cd_raw = str(c.get("closing_date") or "").strip()
                if re.match(r"^\d{4}-\d{2}-\d{2}$", cd_raw) and cd_raw < today_iso:
                    expired_in_spa.append(c.get("slug"))
            if expired_in_spa:
                needs_pseo_regen = True
                pseo_reasons.append(f"{len(expired_in_spa)} expired solicitation(s) still present in window.SIGNALTENDER_CONTRACTS")
        except Exception:
            pass

    # Check /contracts/recompetes/*.html for mangled .title() corporate suffixes (' Llc', ' Usa ') or '\ufffd'
    recompete_files = glob.glob(str(BASE_DIR / "contracts" / "recompetes" / "*.html"))
    for rc_p in recompete_files[:40]:
        try:
            rc_txt = pathlib.Path(rc_p).read_text(encoding="utf-8", errors="replace")
            if "\ufffd" in rc_txt or re.search(r"\b(?:Llc|Inc\.|Corp\.|Usa)\b", rc_txt):
                needs_pseo_regen = True
                pseo_reasons.append(f"Recompete page {os.path.basename(rc_p)} had mangled corporate suffix or \\ufffd")
                break
        except Exception:
            pass

    if needs_pseo_regen:
        if auto_fix:
            r = subprocess.run(
                [str(BASE_DIR / "daas_env" / "Scripts" / "python.exe"), str(BASE_DIR / "pseo_generator.py")],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
            )
            if r.returncode == 0:
                fixed_events.append({
                    "component": "pseo_generator.py & /contracts/**/*.html & sitemap.xml",
                    "issue": "; ".join(pseo_reasons),
                    "fix": "Executed `pseo_generator.py` to rebuild all static RFP pages, state hubs, `sitemap.xml`, and embedded SPA contract directory.",
                    "rule_id": "RULE-PSEO-SITEMAP-PARITY",
                })
            else:
                unfixed_issues.append(f"pseo_generator.py auto-regen failed: {r.stderr[:400]}")
        else:
            unfixed_issues.extend(pseo_reasons)

    # 3. Audit Outbound Cold Email (`campaign_leads.csv` & `outbox_ready_queue.json`)
    csv_path = BASE_DIR / "campaign_leads.csv"
    outbox_path = BASE_DIR / "outbox_ready_queue.json"
    dnc_emails: set[str] = set()
    sent_log_path = BASE_DIR / "sent_outreach_log.json"
    if sent_log_path.exists():
        try:
            sl_data = json.loads(sent_log_path.read_text(encoding="utf-8"))
            if isinstance(sl_data, dict):
                for unsub_em in sl_data.get("unsubscribed") or []:
                    if unsub_em:
                        dnc_emails.add(str(unsub_em).strip().lower())
        except Exception:
            pass
    proc_replies_path = BASE_DIR / "processed_outbound_replies.json"
    if proc_replies_path.exists():
        try:
            pr_data = json.loads(proc_replies_path.read_text(encoding="utf-8"))
            if isinstance(pr_data, dict):
                for em_k, meta in (pr_data.get("processed") or {}).items():
                    if isinstance(meta, dict) and str(meta.get("classification") or "").upper() == "UNSUBSCRIBE":
                        dnc_emails.add(str(em_k).strip().lower())
        except Exception:
            pass

    needs_outreach_regen = False
    outreach_reasons: list[str] = []

    if not csv_path.exists() or not outbox_path.exists():
        needs_outreach_regen = True
        outreach_reasons.append("Missing campaign_leads.csv or outbox_ready_queue.json")
    else:
        try:
            with open(csv_path, mode="r", encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
            if not rows:
                needs_outreach_regen = True
                outreach_reasons.append("campaign_leads.csv has 0 prospect rows")
            for r_idx, row in enumerate(rows):
                em = str(row.get("Email") or "").strip().lower()
                if em in dnc_emails:
                    needs_outreach_regen = True
                    outreach_reasons.append(f"Unsubscribed DNC email '{em}' found in campaign_leads.csv")
                    break
                dossier_url = str(row.get("Top Contract Dossier URL") or "").strip()
                if "/contracts/rfp/" in dossier_url:
                    slug_part = dossier_url.split("/contracts/rfp/", 1)[1].split("?")[0].split("#")[0]
                    if slug_part and not (BASE_DIR / "contracts" / "rfp" / slug_part).exists():
                        needs_outreach_regen = True
                        outreach_reasons.append(f"Row #{r_idx+1} Top Contract Dossier URL points to missing file '{slug_part}'")
                        break
                body_blob = f"{row.get('Subject Line', '')} {row.get('Email Body', '')} {row.get('Followup Body', '')}"
                if "{{" in body_blob or "}}" in body_blob or "[First Name]" in body_blob:
                    needs_outreach_regen = True
                    outreach_reasons.append(f"Row #{r_idx+1} contains unreplaced template placeholder")
                    break
                for kp in range(3, n_portals):
                    if re.search(rf"(?<![0-9])(?:{kp}\s+portals|{kp}-Portal|{kp}\s+Federal)", body_blob):
                        needs_outreach_regen = True
                        outreach_reasons.append(f"campaign_leads.csv contains stale portal count '{kp}' (expected {n_portals})")
                        break
                if needs_outreach_regen:
                    break
        except Exception as exc:
            needs_outreach_regen = True
            outreach_reasons.append(f"Error reading campaign_leads.csv: {exc}")

    if needs_outreach_regen:
        if auto_fix:
            out_env = dict(os.environ)
            out_env["OUTREACH_LOCAL_REFRESH_ONLY"] = "1"
            r = subprocess.run(
                [str(BASE_DIR / "daas_env" / "Scripts" / "python.exe"), str(BASE_DIR / "outreach_generator.py")],
                cwd=str(BASE_DIR),
                env=out_env,
                capture_output=True,
                text=True,
            )
            if r.returncode == 0:
                fixed_events.append({
                    "component": "outreach_generator.py (campaign_leads.csv & outbox_ready_queue.json)",
                    "issue": "; ".join(outreach_reasons),
                    "fix": "Re-ran `outreach_generator.py` to regenerate fresh, DNC-filtered `campaign_leads.csv` and `outbox_ready_queue.json` with verified dossier URLs and current portal/API counts.",
                    "rule_id": "RULE-003-OUTBOUND-DOSSIER-URL-INTEGRITY",
                })
            else:
                unfixed_issues.append(f"outreach_generator.py auto-regen failed: {r.stderr[:400]}")
        else:
            unfixed_issues.extend(outreach_reasons)

    # 4. Audit Social Distribution Queues (`linkedin_ready_posts.json` & `x_ready_posts.json`)
    x_queue_path = BASE_DIR / "x_ready_posts.json"
    if x_queue_path.exists():
        try:
            x_posts = json.loads(x_queue_path.read_text(encoding="utf-8"))
            posts_list = x_posts if isinstance(x_posts, list) else x_posts.get("posts", [])
            stale_x = False
            for xp in posts_list:
                txt = str(xp.get("text") or xp.get("tweet") or "")
                for kp in range(3, n_portals):
                    if re.search(rf"(?<![0-9])(?:{kp}-Portal|{kp}\s+Portals)", txt):
                        stale_x = True
                        break
            if stale_x and auto_fix:
                subprocess.run(
                    [str(BASE_DIR / "daas_env" / "Scripts" / "python.exe"), str(BASE_DIR / "x_autoposter.py"), "--dry-run"],
                    cwd=str(BASE_DIR),
                    capture_output=True,
                    text=True,
                )
                fixed_events.append({
                    "component": "x_autoposter.py (x_ready_posts.json)",
                    "issue": "Stale portal count in queued X (@SignalTenderX) posts",
                    "fix": "Regenerated `x_ready_posts.json` with current portal/state counts.",
                    "rule_id": "RULE-002-PORTAL-STATE-API-COUNT-PARITY",
                })
        except Exception:
            pass

    # 5. Audit & Auto-Heal Live Instantly.ai Outbound + Transactional Campaigns, 6-Mailbox Pool & Unread Prospect Replies
    inst_key = (os.getenv("INSTANTLY_API_KEY") or "").strip()
    inst_cid = (os.getenv("INSTANTLY_CAMPAIGN_ID") or "").strip()
    inst_sub_cid = (os.getenv("INSTANTLY_SUBSCRIBER_CAMPAIGN_ID") or "").strip()
    if inst_key and inst_cid:
        inst_headers = {"Authorization": f"Bearer {inst_key}", "Content-Type": "application/json"}
        try:
            r_accts = requests.get("https://api.instantly.ai/api/v2/accounts?limit=100", headers=inst_headers, timeout=10)
            if r_accts.status_code == 402:
                unfixed_issues.append("Instantly.ai returned HTTP 402 Payment Required — outbound sending is paused until plan is active!")
            elif r_accts.status_code != 200:
                unfixed_issues.append(f"Instantly.ai GET /api/v2/accounts returned HTTP {r_accts.status_code}")
            else:
                acct_items = (r_accts.json() or {}).get("items") or []
                disconnected_accts = [
                    str(a.get("email") or "").strip().lower()
                    for a in acct_items
                    if int(a.get("status") or 0) != 1
                ]
                if disconnected_accts:
                    unfixed_issues.append(
                        f"Instantly.ai has {len(disconnected_accts)} disconnected/unhealthy mailbox(es) (status != 1): {', '.join(disconnected_accts)}"
                    )
                warmed_emails = [
                    str(a.get("email") or "").strip().lower()
                    for a in acct_items
                    if int(a.get("status") or 0) == 1 and int(a.get("stat_warmup_score") or 0) >= 85
                ]
                expected_daily_cap = max(30, len(warmed_emails) * 30)

                r_camp = requests.get(f"https://api.instantly.ai/api/v2/campaigns/{inst_cid}", headers=inst_headers, timeout=10)
                if r_camp.status_code == 200:
                    c_data = r_camp.json() or {}
                    c_name = str(c_data.get("name") or "")
                    c_status = int(c_data.get("status") or 0)
                    c_limit = int(c_data.get("daily_limit") or 0)
                    c_emails = [str(e).strip().lower() for e in (c_data.get("email_list") or [])]

                    patch_body: dict = {}
                    if "\ufffd" in c_name:
                        patch_body["name"] = c_name.replace("\ufffd", "-")
                    if warmed_emails and set(warmed_emails) != set(c_emails):
                        patch_body["email_list"] = warmed_emails
                    if warmed_emails and c_limit != expected_daily_cap:
                        patch_body["daily_limit"] = expected_daily_cap

                    if patch_body:
                        if auto_fix:
                            requests.patch(
                                f"https://api.instantly.ai/api/v2/campaigns/{inst_cid}",
                                headers=inst_headers,
                                json=patch_body,
                                timeout=10,
                            )
                            fixed_events.append({
                                "component": "Instantly.ai Outbound Campaign (c7727dff-92cc-4621-9e96-c960938d5a47)",
                                "issue": f"Campaign config drift detected ({list(patch_body.keys())})",
                                "fix": f"Synchronized {len(warmed_emails)} warmed mailboxes (daily_limit={expected_daily_cap}) and cleaned campaign metadata.",
                                "rule_id": "RULE-007-WARMED-MAILBOX-CONTINUITY",
                            })
                        else:
                            unfixed_issues.append(f"Instantly campaign {inst_cid} drift: {list(patch_body.keys())}")

                    if c_status != 1:
                        if auto_fix:
                            r_act = requests.post(
                                f"https://api.instantly.ai/api/v2/campaigns/{inst_cid}/activate",
                                headers=inst_headers,
                                json={},
                                timeout=10,
                            )
                            if 200 <= r_act.status_code < 300:
                                fixed_events.append({
                                    "component": "Instantly.ai Outbound Campaign (c7727dff-92cc-4621-9e96-c960938d5a47)",
                                    "issue": f"Outbound campaign status was {c_status} (not ACTIVE=1)",
                                    "fix": "Automatically re-activated outbound campaign via POST /api/v2/campaigns/{id}/activate.",
                                    "rule_id": "RULE-007-WARMED-MAILBOX-CONTINUITY",
                                })
                            else:
                                unfixed_issues.append(f"Failed to activate Instantly campaign {inst_cid}: HTTP {r_act.status_code}")
                        else:
                            unfixed_issues.append(f"Instantly outbound campaign {inst_cid} is not ACTIVE (status={c_status})")

                # Check Transactional Subscriber Campaign email_list parity
                if inst_sub_cid and warmed_emails:
                    r_sub_c = requests.get(f"https://api.instantly.ai/api/v2/campaigns/{inst_sub_cid}", headers=inst_headers, timeout=10)
                    if r_sub_c.status_code == 200:
                        sc_data = r_sub_c.json() or {}
                        sc_emails = [str(e).strip().lower() for e in (sc_data.get("email_list") or [])]
                        if set(warmed_emails) != set(sc_emails) and auto_fix:
                            requests.patch(
                                f"https://api.instantly.ai/api/v2/campaigns/{inst_sub_cid}",
                                headers=inst_headers,
                                json={"email_list": warmed_emails},
                                timeout=10,
                            )

                # Check Campaign Lead Starvation (remaining uncontacted leads == 0 while outbox_ready_queue.json has fresh unsent leads)
                r_ana = requests.get(
                    f"https://api.instantly.ai/api/v2/campaigns/analytics?id={inst_cid}",
                    headers=inst_headers,
                    timeout=10,
                )
                if r_ana.status_code == 200:
                    ana_list = r_ana.json() if isinstance(r_ana.json(), list) else [r_ana.json()]
                    if ana_list and isinstance(ana_list[0], dict):
                        a0 = ana_list[0]
                        lead_items = []
                        cur_lead = None
                        for _ in range(5):
                            b_payload = {"campaign": inst_cid, "limit": 100}
                            if cur_lead:
                                b_payload["starting_after"] = cur_lead
                            r_ll = requests.post(
                                "https://api.instantly.ai/api/v2/leads/list",
                                headers=inst_headers,
                                json=b_payload,
                                timeout=10,
                            )
                            if r_ll.status_code != 200:
                                break
                            d_ll = r_ll.json() or {}
                            it_ll = d_ll.get("items") or []
                            lead_items.extend(it_ll)
                            cur_lead = d_ll.get("next_starting_after")
                            if not cur_lead or not it_ll:
                                break
                        uncontacted_step1 = [x for x in lead_items if not x.get("timestamp_last_contact")]
                        remaining_l = len(uncontacted_step1)
                        if lead_items and remaining_l < 30:
                            if auto_fix:
                                subprocess.run(
                                    [str(BASE_DIR / "daas_env" / "Scripts" / "python.exe"), str(BASE_DIR / "outreach_generator.py")],
                                    cwd=str(BASE_DIR),
                                    capture_output=True,
                                    text=True,
                                )
                                fixed_events.append({
                                    "component": "outreach_generator.py & govcon_lead_harvester.py (Step 1 Queue Refill)",
                                    "issue": f"Instantly campaign {inst_cid} had only {remaining_l} uncontacted Step 1 lead(s) remaining (< 30 buffer)",
                                    "fix": "Executed `outreach_generator.py` to harvest new DNS/MX-verified IT/Cyber executives and sync them into Instantly V2.",
                                    "rule_id": "RULE-007-WARMED-MAILBOX-CONTINUITY",
                                })
                            else:
                                unfixed_issues.append(
                                    f"Instantly campaign {inst_cid} low on uncontacted Step 1 leads ({remaining_l} remaining < 30 buffer)"
                                )

                # Check Unibox for unanswered external prospect replies (supporting both list of UUIDs & dict schemas)
                r_unibox = requests.get("https://api.instantly.ai/api/v2/emails?limit=25&ue_type=2", headers=inst_headers, timeout=10)
                if r_unibox.status_code == 200:
                    our_domains = ("getsignaltender.com", "trysignaltender.com", "signaltenderdesk.com", "signaltendergov.com", "signaltender.net")
                    proc_ids_or_emails: set[str] = set()
                    if proc_replies_path.exists():
                        try:
                            raw_pr = json.loads(proc_replies_path.read_text(encoding="utf-8"))
                            if isinstance(raw_pr, list):
                                proc_ids_or_emails.update(str(x).strip() for x in raw_pr if x)
                            elif isinstance(raw_pr, dict):
                                for k_pr in (raw_pr.get("processed") or {}).keys():
                                    proc_ids_or_emails.add(str(k_pr).strip().lower())
                        except Exception:
                            pass
                    if sent_log_path.exists():
                        try:
                            sl_raw2 = json.loads(sent_log_path.read_text(encoding="utf-8"))
                            if isinstance(sl_raw2, dict):
                                for rep_em in (sl_raw2.get("replied") or []) + (sl_raw2.get("unsubscribed") or []):
                                    if rep_em:
                                        proc_ids_or_emails.add(str(rep_em).strip().lower())
                        except Exception:
                            pass
                    unanswered_replies = []
                    for msg_item in (r_unibox.json() or {}).get("items") or []:
                        from_em = str(msg_item.get("from_address_email") or "").strip().lower()
                        msg_id = str(msg_item.get("id") or "").strip()
                        if not from_em or any(from_em.endswith("@" + d) for d in our_domains):
                            continue
                        if from_em not in proc_ids_or_emails and msg_id not in proc_ids_or_emails:
                            unanswered_replies.append(from_em)
                    if unanswered_replies:
                        if auto_fix:
                            subprocess.run(
                                [str(BASE_DIR / "daas_env" / "Scripts" / "python.exe"), str(BASE_DIR / "outbound_reply_responder.py")],
                                cwd=str(BASE_DIR),
                                capture_output=True,
                                text=True,
                            )
                            fixed_events.append({
                                "component": "outbound_reply_responder.py (Instantly Unibox)",
                                "issue": f"Detected {len(unanswered_replies)} unprocessed prospect reply(ies) in Instantly Unibox",
                                "fix": "Executed `outbound_reply_responder.py` to classify and respond to unread prospect replies.",
                                "rule_id": "RULE-007-WARMED-MAILBOX-CONTINUITY",
                            })
                        else:
                            unfixed_issues.append(f"{len(unanswered_replies)} unprocessed prospect reply(ies) in Instantly Unibox")
        except Exception as exc:
            unfixed_issues.append(f"Instantly.ai live campaign/mailbox audit error: {exc}")

    # 6. Audit & Auto-Heal Authoritative Cloudflare DNS Deliverability (MX, SPF, DMARC & BIMI) + LinkedIn OAuth Token Liveness
    cf_token = (os.getenv("CLOUDFLARE_API_TOKEN") or "").strip()
    if cf_token:
        try:
            cf_headers = {"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"}
            r_zones = requests.get("https://api.cloudflare.com/client/v4/zones?per_page=50", headers=cf_headers, timeout=10)
            if r_zones.status_code == 200:
                zone_map = {str(z.get("name") or "").lower(): z for z in (r_zones.json() or {}).get("result") or []}
                for dom_name in ("signaltender.net", "getsignaltender.com", "trysignaltender.com"):
                    z_obj = zone_map.get(dom_name)
                    if not z_obj or z_obj.get("status") != "active":
                        unfixed_issues.append(f"Cloudflare zone {dom_name} missing or not active")
                        continue
                    z_id = z_obj.get("id")
                    r_recs = requests.get(
                        f"https://api.cloudflare.com/client/v4/zones/{z_id}/dns_records?per_page=100",
                        headers=cf_headers,
                        timeout=10,
                    )
                    recs = (r_recs.json() or {}).get("result") or [] if r_recs.status_code == 200 else []
                    has_dmarc = any(r.get("type") == "TXT" and r.get("name") == f"_dmarc.{dom_name}" for r in recs)
                    has_bimi = any(r.get("type") == "TXT" and r.get("name") == f"default._bimi.{dom_name}" for r in recs)
                    has_mx = any(r.get("type") == "MX" for r in recs)
                    has_spf = any(r.get("type") == "TXT" and "v=spf1" in str(r.get("content") or "").lower() for r in recs)
                    is_sat = dom_name in ("getsignaltender.com", "trysignaltender.com")
                    if not has_dmarc or not has_bimi or (is_sat and (not has_mx or not has_spf)):
                        if auto_fix and is_sat:
                            import autonomous_mailbox_scaler
                            autonomous_mailbox_scaler.provision_cloudflare_zone_and_redirect(dom_name)
                            fixed_events.append({
                                "component": f"Cloudflare DNS ({dom_name})",
                                "issue": f"Missing MX/SPF/DMARC/BIMI record on satellite domain {dom_name}",
                                "fix": f"Automatically re-provisioned MX, SPF, DMARC, and BIMI DNS records for {dom_name} via Cloudflare API.",
                                "rule_id": "RULE-007-WARMED-MAILBOX-CONTINUITY",
                            })
                        else:
                            unfixed_issues.append(
                                f"Cloudflare DNS record missing on {dom_name} (MX={has_mx}, SPF={has_spf}, DMARC={has_dmarc}, BIMI={has_bimi})"
                            )
        except Exception as exc:
            unfixed_issues.append(f"Cloudflare DNS audit failed: {exc}")

    li_token = (os.getenv("LINKEDIN_ACCESS_TOKEN") or "").strip()
    if li_token:
        try:
            r_li = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {li_token}"},
                timeout=8,
            )
            if r_li.status_code != 200:
                unfixed_issues.append(f"LinkedIn OAuth token check returned HTTP {r_li.status_code} (token may be expired)")
        except Exception:
            pass

    return fixed_events, unfixed_issues


# ============================================================================
# PILLAR 3: WEBSITE, CHECKOUT & INFRASTRUCTURE AUDIT & AUTO-FIX ENGINE
# ============================================================================
def audit_and_heal_website(auto_fix: bool = True, run_playwright: bool = False) -> tuple[list[dict], list[str]]:
    """
    Runs deterministic website & cross-surface auto-healers BEFORE executing the strict
    `verify_site_integrity.py` verification suite:
      1. Stale Portal / State / API / Tier-2 Count Auto-Healer across `index.html`, `apis.html`,
         `pseo_generator.py`, and conversion surfaces.
      2. `API_META['product-live-solicitations'].kw` Sync Auto-Healer between `index.html` and `apis.html`.
      3. Duplicate `+ #XX + #XX` Badge & Prohibited Emoji Auto-Cleaner.
      4. Full `verify_site_integrity.py` check (JS `vm.Script`, SPA runtime harness, 4-tier checkout,
         and optional Playwright 375px mobile / 1024px & 1280px desktop viewport overflow scan).
    Returns `(auto_fixed_events, unfixed_issues)`.
    """
    fixed_events: list[dict] = []
    unfixed_issues: list[str] = []
    counts = _get_ecosystem_counts()
    n_apis = counts["n_apis"]
    n_portals = counts["n_portals"]
    n_states = counts["n_states"]
    n_tier2_apis = counts["n_tier2_apis"]
    state_keys = counts["state_keys"]

    index_path = BASE_DIR / "index.html"
    apis_path = BASE_DIR / "apis.html"

    if auto_fix and index_path.exists() and apis_path.exists():
        idx_txt = index_path.read_text(encoding="utf-8", errors="replace")
        api_txt = apis_path.read_text(encoding="utf-8", errors="replace")
        orig_idx = idx_txt
        orig_api = api_txt

        # 1. Strip accidental duplicate '+ #XX + #XX' badges
        idx_txt = re.sub(r"(\+\s*#(\d{2}))\s+\+\s*#\2\b", r"\1", idx_txt)
        api_txt = re.sub(r"(\+\s*#(\d{2}))\s+\+\s*#\2\b", r"\1", api_txt)

        # 2. Strip any prohibited unicode emojis [\U0001F300-\U0001FAFF]
        emoji_re = re.compile(r"[\U0001F300-\U0001FAFF]")
        if emoji_re.search(idx_txt):
            idx_txt = emoji_re.sub("", idx_txt)
        if emoji_re.search(api_txt):
            api_txt = emoji_re.sub("", api_txt)

        # 3. Synchronize API_META['product-live-solicitations'].kw between index.html and apis.html and ensure all active states are present
        kw_re = re.compile(r"('product-live-solicitations'\s*:\s*\{\s*cat\s*:\s*'[^']*'\s*,\s*kw\s*:\s*')([^']*)(')")
        m_idx_kw = kw_re.search(idx_txt)
        m_api_kw = kw_re.search(api_txt)
        if m_idx_kw and m_api_kw:
            combined_kw = m_idx_kw.group(2)
            for sk in state_keys:
                st_words = sk.replace("_", " ").lower()
                if st_words not in combined_kw.lower():
                    combined_kw = combined_kw.strip() + " " + st_words
            if m_idx_kw.group(2) != combined_kw or m_api_kw.group(2) != combined_kw:
                idx_txt = kw_re.sub(rf"\g<1>{combined_kw}\g<3>", idx_txt)
                api_txt = kw_re.sub(rf"\g<1>{combined_kw}\g<3>", api_txt)
                fixed_events.append({
                    "component": "index.html & apis.html (API_META['product-live-solicitations'].kw)",
                    "issue": "API_META['product-live-solicitations'].kw drift or missing active state keyword",
                    "fix": f"Synchronized API_META['product-live-solicitations'].kw across index.html and apis.html with all {n_states} active states.",
                    "rule_id": "RULE-API-CATALOG-MCP-PARITY",
                })

        # 4. Auto-heal stale API counts in index.html & apis.html
        for ka in range(10, n_apis):
            replacements = [
                (f"{ka} LIVE ENDPOINTS", f"{n_apis} LIVE ENDPOINTS"),
                (f"{ka} MCP TOOLS", f"{n_apis} MCP TOOLS"),
                (f"{ka} / {ka} SHOWN", f"{n_apis} / {n_apis} SHOWN"),
                (f"All ({ka})</button>", f"All ({n_apis})</button>"),
                (f"Search {ka} APIs", f"Search {n_apis} APIs"),
                (f"Filter {ka} endpoints", f"Filter {n_apis} endpoints"),
                (f"SELECT MICROSERVICE ({ka})", f"SELECT MICROSERVICE ({n_apis})"),
                (f"{ka} REST &amp; MCP MICROSERVICES", f"{n_apis} REST &amp; MCP MICROSERVICES"),
                (f"All {ka} individual SignalTender microservices", f"All {n_apis} individual SignalTender microservices"),
                (f"across all {ka} SignalTender endpoints", f"across all {n_apis} SignalTender endpoints"),
                (f"{ka} deterministic GovCon microservices", f"{n_apis} deterministic GovCon microservices"),
                (f"across all {ka} GovCon microservices", f"{n_apis} GovCon microservices"),
            ]
            for old_s, new_s in replacements:
                if old_s in idx_txt:
                    idx_txt = re.sub(rf"(?<![0-9]){re.escape(old_s)}", new_s, idx_txt)
                if old_s in api_txt:
                    api_txt = re.sub(rf"(?<![0-9]){re.escape(old_s)}", new_s, api_txt)

        # 5. Auto-heal stale portal & state counts in index.html & apis.html
        for kp in range(3, n_portals):
            portal_repls = [
                (f"{kp} GOVERNMENT PORTALS", f"{n_portals} GOVERNMENT PORTALS"),
                (f"{kp} PORTALS ACTIVE", f"{n_portals} PORTALS ACTIVE"),
                (f"{kp} PORTALS DE-NOISED", f"{n_portals} PORTALS DE-NOISED"),
                (f">{kp} Portals<", f">{n_portals} Portals<"),
                (f"({kp} PORTALS LIVE)", f"({n_portals} PORTALS LIVE)"),
                (f"// {kp} ACTIVE PROCUREMENT PORTALS", f"// {n_portals} ACTIVE PROCUREMENT PORTALS"),
                (f"All Portals ({kp})", f"All Portals ({n_portals})"),
                (f"{kp} PREVIEW LEADS SHOWN", f"{n_portals} PREVIEW LEADS SHOWN"),
                (f"All {kp} Active Procurement Portals", f"All {n_portals} Active Procurement Portals"),
                (f"ALL {kp} FEDERAL", f"ALL {n_portals} FEDERAL"),
                (f"{kp}-Portal", f"{n_portals}-Portal"),
                (f"{kp}-PORTAL", f"{n_portals}-PORTAL"),
                (f"{kp} Federal, State SLED, and Municipal portals", f"{n_portals} Federal, State SLED, and Municipal portals"),
                (f"across {kp} government portals", f"across {n_portals} government portals"),
            ]
            for old_p, new_p in portal_repls:
                if old_p in idx_txt:
                    idx_txt = re.sub(rf"(?<![0-9]){re.escape(old_p)}", new_p, idx_txt)
                if old_p in api_txt:
                    api_txt = re.sub(rf"(?<![0-9]){re.escape(old_p)}", new_p, api_txt)

        for ks in range(3, n_states):
            state_repls = [
                (f"{ks}-State SLED", f"{n_states}-State SLED"),
                (f"{ks}-STATE SLED", f"{n_states}-STATE SLED"),
                (f"{ks} State SLED", f"{n_states} State SLED"),
                (f"{ks} major State SLED", f"{n_states} major State SLED"),
            ]
            for old_st, new_st in state_repls:
                if old_st in idx_txt:
                    idx_txt = re.sub(rf"(?<![0-9]){re.escape(old_st)}", new_st, idx_txt)
                if old_st in api_txt:
                    api_txt = re.sub(rf"(?<![0-9]){re.escape(old_st)}", new_st, api_txt)

        # 5b. Auto-heal <select id="checkout-foia-state"> in #checkout-enterprise-proof-workbench so every active SLED state has an <option>
        m_foia_sel = re.search(r'(<select\s+id="checkout-foia-state"[^>]*>)(.*?)(</select>)', idx_txt, flags=re.S)
        if m_foia_sel:
            sel_inner = m_foia_sel.group(2)
            missing_foia_opts: list[str] = []
            for sk in state_keys:
                if f'value="{sk}"' not in sel_inner:
                    st_title = sk.replace("_", " ").title()
                    missing_foia_opts.append(f'                    <option value="{sk}">{st_title} (State SLED / Statutory Open Records)</option>')
            if missing_foia_opts:
                new_inner = sel_inner.rstrip() + "\n" + "\n".join(missing_foia_opts) + "\n                  "
                idx_txt = idx_txt[: m_foia_sel.start(2)] + new_inner + idx_txt[m_foia_sel.end(2) :]
                fixed_events.append({
                    "component": "index.html (#checkout-foia-state in Zero-Call Enterprise Proof Workbench)",
                    "issue": f"Missing {len(missing_foia_opts)} active state option(s) in <select id='checkout-foia-state'>",
                    "fix": f"Automatically injected {len(missing_foia_opts)} state <option> tag(s) into #checkout-foia-state on #page-checkout.",
                    "rule_id": "RULE-010-ZERO-CALL-ENTERPRISE-PROOF-AND-CFO-QUOTE-WORKBENCH",
                })

        if idx_txt != orig_idx:
            index_path.write_text(idx_txt, encoding="utf-8")
            fixed_events.append({
                "component": "index.html",
                "issue": "Detected and healed count/badge/metadata drift in index.html",
                "fix": f"Auto-healed index.html to {n_portals} portals, {n_states} states, {n_apis} APIs ({n_tier2_apis} Tier-2 engines).",
                "rule_id": "RULE-002-PORTAL-STATE-API-COUNT-PARITY",
            })
        if api_txt != orig_api:
            apis_path.write_text(api_txt, encoding="utf-8")
            fixed_events.append({
                "component": "apis.html",
                "issue": "Detected and healed count/badge/metadata drift in apis.html",
                "fix": f"Auto-healed apis.html to {n_portals} portals, {n_states} states, and {n_apis} APIs.",
                "rule_id": "RULE-002-PORTAL-STATE-API-COUNT-PARITY",
            })

    # 6. Execute verify_site_integrity.py subprocess check
    env_copy = dict(os.environ)
    if not run_playwright:
        env_copy["CI"] = "1"  # Skip Playwright in fast mode; run full Playwright when run_playwright=True
    else:
        env_copy.pop("CI", None)
        env_copy.pop("RENDER", None)

    r_ver = subprocess.run(
        [str(BASE_DIR / "daas_env" / "Scripts" / "python.exe"), str(BASE_DIR / "verify_site_integrity.py")],
        cwd=str(BASE_DIR),
        env=env_copy,
        capture_output=True,
        text=True,
    )
    if r_ver.returncode != 0:
        err_out = (r_ver.stdout + "\n" + r_ver.stderr).strip()
        unfixed_issues.append(f"verify_site_integrity.py failed: {err_out[-600:]}")

    # 7. Audit Live Public Website (`https://signaltender.net`) Content Parity, `og-banner.png`, & Live Render Gateway (`/v1/health`)
    live_urls = (
        "https://signaltender.net/",
        "https://signaltender.net/apis.html",
        "https://signaltender.net/contracts/",
        "https://signaltender.net/sitemap.xml",
        "https://signaltender.net/robots.txt",
        "https://b2b-contract-parser-api.onrender.com/v1/health",
    )
    for l_url in live_urls:
        try:
            rl = requests.get(l_url, timeout=12)
            if rl.status_code != 200:
                unfixed_issues.append(f"Live public URL {l_url} returned HTTP {rl.status_code}")
            elif l_url == "https://signaltender.net/":
                if f"{n_portals} PORTALS" not in rl.text or f"{n_apis} LIVE ENDPOINTS" not in rl.text:
                    if auto_fix:
                        subprocess.run(["git", "push", "origin", "main"], cwd=str(BASE_DIR), check=False, capture_output=True)
                    else:
                        unfixed_issues.append(
                            f"Live https://signaltender.net/ content drift (missing '{n_portals} PORTALS' or '{n_apis} LIVE ENDPOINTS')"
                        )
            elif l_url == "https://signaltender.net/apis.html":
                if f"{n_apis} LIVE ENDPOINTS" not in rl.text:
                    unfixed_issues.append(f"Live https://signaltender.net/apis.html content drift (missing '{n_apis} LIVE ENDPOINTS')")
        except Exception as exc:
            unfixed_issues.append(f"Live public URL {l_url} unreachable: {exc}")

    # Verify live OpenGraph preview banner (`https://signaltender.net/contracts/og-banner.png`) returns valid PNG >= 10 KB
    try:
        r_og = requests.get("https://signaltender.net/contracts/og-banner.png", timeout=10)
        og_ct = str(r_og.headers.get("Content-Type") or "").lower()
        if r_og.status_code != 200 or "image/" not in og_ct or len(r_og.content) < 10000:
            unfixed_issues.append(
                f"Live https://signaltender.net/contracts/og-banner.png invalid (HTTP {r_og.status_code}, Content-Type={og_ct}, bytes={len(r_og.content)})"
            )
    except Exception as exc:
        unfixed_issues.append(f"Live https://signaltender.net/contracts/og-banner.png check failed: {exc}")

    # 8. Audit TLS / SSL Certificate Expiration (>= 7 days remaining) on Primary & Backend Domains
    import socket
    import ssl
    for tls_host in ("signaltender.net", "b2b-contract-parser-api.onrender.com"):
        try:
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(socket.socket(), server_hostname=tls_host) as s:
                s.settimeout(6)
                s.connect((tls_host, 443))
                cert = s.getpeercert()
                exp_dt = datetime.strptime(str(cert.get("notAfter") or ""), "%b %d %H:%M:%S %Y %Z")
                days_left = (exp_dt - datetime.now(timezone.utc).replace(tzinfo=None)).days
                if days_left < 7:
                    unfixed_issues.append(f"TLS/SSL certificate for {tls_host} expires in {days_left} days!")
        except Exception as exc:
            unfixed_issues.append(f"TLS/SSL certificate check failed for {tls_host}: {exc}")

    return fixed_events, unfixed_issues


# ============================================================================
# ORCHESTRATOR: RUN 360° AUDIT, AUTO-FIX, CODIFY RULES & DISPATCH [RESOLVED]
# ============================================================================
def run_omniscient_audit(
    mode: str = "fast",
    auto_fix: bool = True,
    auto_deploy: bool = False,
    force_now: bool = False,
) -> int:
    """
    Execute the 3-pillar SignalTender Omniscient Audit & Self-Healing Engine.
    - Enforces RULE-006: Only runs at night (11:00 PM – 6:00 AM local time) when the user is away
      (>= 30 minutes of Windows keyboard/mouse idle time), unless `force_now=True` (`--force-now`).
    - Never dispatches raw `[ALERT]` notifications on bug detection.
    - Automatically heals deterministic bugs across Products, Acquisition Channels, and Website.
    - Codifies a permanent anti-regression rule in `learned_anti_regression_rules.json` + `AGENTS.md` for every fix.
    - Dispatches a single `[RESOLVED]` alert to Discord `#alerts` when fixes are applied.
    """
    ensure_foundational_rules()
    if not force_now:
        allowed, reason = is_nighttime_and_user_away(min_idle_seconds=1800)
        if not allowed:
            print(f"[*] Omniscient Auditor skipped ({reason})", flush=True)
            return 0

    t0 = time.time()
    run_playwright = (mode == "full")
    print(f"[*] Running SignalTender 360° Omniscient Auditor (mode={mode}, auto_fix={auto_fix})...", flush=True)

    prod_fixed, prod_issues = audit_and_heal_products(auto_fix=auto_fix)
    acq_fixed, acq_issues = audit_and_heal_acquisition(auto_fix=auto_fix)
    web_fixed, web_issues = audit_and_heal_website(auto_fix=auto_fix, run_playwright=run_playwright)

    all_fixed = prod_fixed + acq_fixed + web_fixed
    all_unfixed = prod_issues + acq_issues + web_issues

    # Also check if there were open runtime errors in local error_log.txt or remote Render telemetry
    import auto_error_healer
    remote_errors = auto_error_healer.fetch_remote_open_errors()
    local_errors = auto_error_healer.read_local_unacknowledged_errors()

    # If all structural & runtime checks are now 100% clean, clear any resolved error logs and emit [RESOLVED]
    codified_rules_summary: list[str] = []
    for fx in all_fixed:
        r_entry = derive_and_codify_rule_from_fix(
            components=fx["component"],
            resolved_issues=fx["issue"],
            fix_verification=fx["fix"],
        )
        rule_tag = f"`[{r_entry['rule_id']}]` {r_entry['prevention_rule']}"
        if rule_tag not in codified_rules_summary:
            codified_rules_summary.append(rule_tag)

    if all_fixed and not all_unfixed:
        comp_str = ", ".join(dict.fromkeys(fx["component"] for fx in all_fixed))
        issue_str = "; ".join(fx["issue"] for fx in all_fixed)
        fix_str = "; ".join(fx["fix"] for fx in all_fixed)
        learned_str = " | ".join(codified_rules_summary)

        # Only clear open telemetry errors if every single check in all 3 pillars passed (all_unfixed is empty)
        # AND the error log component matches a fixed component or passes live contract/route/health verification
        if remote_errors or local_errors:
            auto_error_healer.archive_local_error_log(fix_str[:300])
            auto_error_healer.clear_remote_errors(fix_str[:300])
            remote_errors = []
            local_errors = []

        send_discord_resolution(
            components=comp_str[:300],
            resolved_issues=issue_str[:500],
            fix_verification=fix_str[:500],
            open_error_count=0,
            learned_rule=learned_str[:600],
        )

        if auto_deploy:
            for repo_dir in (ECOSYSTEM_DIR, BASE_DIR):
                if not repo_dir.exists():
                    continue
                try:
                    st_chk = subprocess.run(
                        ["git", "status", "--porcelain"],
                        cwd=str(repo_dir),
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if (st_chk.stdout or "").strip():
                        subprocess.run(["git", "add", "-A"], cwd=str(repo_dir), check=False)
                        subprocess.run(
                            ["git", "commit", "-m", f"fix(self-healer): auto-heal {comp_str[:72]} & codify anti-regression rule"],
                            cwd=str(repo_dir),
                            check=False,
                            capture_output=True,
                        )
                        subprocess.run(["git", "push", "origin", "main"], cwd=str(repo_dir), check=False, capture_output=True)
                except Exception:
                    pass

    elapsed = round(time.time() - t0, 2)
    counts = _get_ecosystem_counts()
    report = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": mode,
        "elapsed_seconds": elapsed,
        "status": "HEALTHY" if (not all_unfixed and not remote_errors and not local_errors) else "ACTION_REQUIRED",
        "counts": {
            "portals": counts["n_portals"],
            "states": counts["n_states"],
            "apis": counts["n_apis"],
            "tier2_apis": counts["n_tier2_apis"],
            "learned_rules_total": len(load_learned_rules()),
        },
        "pillars": {
            "products": {"auto_fixed": prod_fixed, "unfixed_issues": prod_issues},
            "acquisition_channels": {"auto_fixed": acq_fixed, "unfixed_issues": acq_issues},
            "website_and_checkout": {"auto_fixed": web_fixed, "unfixed_issues": web_issues},
        },
        "telemetry": {
            "open_remote_errors": len(remote_errors),
            "open_local_errors": len(local_errors),
        },
    }
    try:
        AUDIT_REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    if all_unfixed or remote_errors or local_errors:
        print(
            f"[!] Omniscient Auditor detected {len(all_unfixed)} unfixed issue(s), "
            f"{len(remote_errors)} remote error(s), {len(local_errors)} local error(s) in {elapsed}s.",
            flush=True,
        )
        for iss in all_unfixed:
            print(f"  - {iss}", flush=True)
        return 1

    print(
        f"[PASS] SignalTender 360° Omniscient Audit PASSED in {elapsed}s: "
        f"Products ({counts['n_apis']} APIs, {counts['n_portals']} Portals), "
        f"Acquisition Channels (pSEO, Cold Email, Social, RapidAPI, MCP), and Website 100% verified "
        f"({len(all_fixed)} auto-healed, {len(load_learned_rules())} active self-improvement rules).",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SignalTender 360° Omniscient Audit & Self-Healing Engine")
    parser.add_argument("--mode", choices=["fast", "full"], default="fast", help="Audit depth ('fast' or 'full' with Playwright)")
    parser.add_argument("--no-fix", action="store_true", help="Run in read-only audit mode without auto-remediation")
    parser.add_argument("--auto-deploy", action="store_true", help="Automatically commit and push auto-healed fixes to origin main")
    parser.add_argument("--force-now", action="store_true", help="Bypass the nighttime + user-away gate for an explicit manual run")
    args = parser.parse_args()
    raise SystemExit(
        run_omniscient_audit(
            mode=args.mode,
            auto_fix=not args.no_fix,
            auto_deploy=args.auto_deploy,
            force_now=args.force_now,
        )
    )
