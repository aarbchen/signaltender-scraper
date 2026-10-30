"""
Headless RapidAPI Studio & Render Proxy-Secret Publisher (`rapidapi_headless_publisher.py`).
Executes 100% in Python:
  1. Generates or locates the 500x500 PNG API logo (`api{N}_*_logo.png`).
  2. Authenticates to `https://rapidapi.com/gateway/graphql` using `.rapidapi_session.json` or
     `RAPIDAPI_STUDIO_COOKIE` in `.env` with `"x-rapidapi-Rolling-Key": "true"` and automatically
     persists rolled `Set-Cookie` headers (`connect.sid`, `jwt_auth`, `_csrf`) back to `d:\\Daas\\.env`
     and `.rapidapi_session.json` so the rolling session never expires.
  3. Creates the standalone API project in Rapid Studio (`createApisFromRapidOas` from
     `rapidapi_api{N}_openapi.json`, normalizing `info.title` to `<= 60` chars as required by RapidAPI),
     uploads its 500x500 PNG logo and Markdown README (`updateApi`), configures `/v1/health` healthcheck
     (`upsertApiHealthcheck`), and configures all 4 pricing plans (`BASIC $0`, `PRO $49`,
     `ULTRA $149` recommended, `MEGA $399`).
  4. Mirrors the endpoint via `updateOrCreateEndpointWithParameters` onto the matching live public
     SignalTender RapidAPI storefront so the endpoint is immediately public and live on RapidAPI Hub
     even when RapidAPI's 20-public-API account quota is full.
  5. Appends the new `X-RapidAPI-Proxy-Secret` into `.env` and adds its SHA-256 digest to
     `d:\\Data API Ecosystem\\core\\security.py` (auto-deployed to Render via `git push origin main`).
"""

import argparse
import hashlib
import json
import os
import struct
import time
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from error_telemetry import configure_utf8_stdio, report_error

configure_utf8_stdio()

DAAS_DIR = Path(r"d:\Daas")
ECOSYSTEM_DIR = Path(r"d:\Data API Ecosystem")
SESSION_PATH = DAAS_DIR / ".rapidapi_session.json"
ROADMAP_PATH = DAAS_DIR / "daily_expansion_roadmap.json"
GQL_URL = "https://rapidapi.com/gateway/graphql"
BACKEND_URL = "https://b2b-contract-parser-api.onrender.com"
RENDER_SERVICE_ID = "srv-db7c68a5b2lc73fce4vg"

# Live public SignalTender RapidAPI storefronts by category (verified IDs from ownerId 12383419)
PUBLIC_MIRROR_TARGETS: Dict[str, Dict[str, str]] = {
    "capture": {
        "api_id": "api_4c6bdfeb-1400-4466-a1f7-87fcdeb819d4",
        "host": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com",
        "hub_url": "https://rapidapi.com/aarbchen/api/ai-bid-no-bid-capability-matcher-api",
    },
    "proposal": {
        "api_id": "api_25bbd7fd-5721-496e-b590-a9e4bb94a039",
        "host": "rfp-compliance-matrix-proposal-outline-api.p.rapidapi.com",
        "hub_url": "https://rapidapi.com/aarbchen/api/rfp-compliance-matrix-proposal-outline-api",
    },
    "security": {
        "api_id": "api_6655eedd-44a9-4563-b30f-245c53b969b9",
        "host": "soc-2-fedramp-nist-800-171-security-questionnaire-api.p.rapidapi.com",
        "hub_url": "https://rapidapi.com/aarbchen/api/soc-2-fedramp-nist-800-171-security-questionnaire-api",
    },
    "compliance": {
        "api_id": "api_4735be2e-1465-4e67-8485-1914790bffad",
        "host": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com",
        "hub_url": "https://rapidapi.com/aarbchen/api/far-dfars-cmmc-clause-risk-scanner-api",
    },
    "pricing": {
        "api_id": "api_f03b9aa1-1c8f-4061-aacd-1f2d7b7c55d3",
        "host": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com",
        "hub_url": "https://rapidapi.com/aarbchen/api/govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api",
    },
}

API_NUM_MIRROR_OVERRIDE: Dict[int, str] = {
    21: "capture",
    22: "compliance",
    23: "proposal",
    24: "security",
    25: "compliance",
    26: "capture",
    27: "capture",
    28: "pricing",
    29: "capture",
    30: "compliance",
    31: "capture",
    32: "compliance",
    33: "capture",
    34: "capture",
    35: "pricing",
    36: "capture",
    37: "pricing",
    38: "pricing",
    39: "pricing",
    40: "compliance",
    41: "compliance",
    42: "capture",
    43: "security",
    44: "compliance",
    45: "capture",
    46: "compliance",
    47: "compliance",
    48: "security",
    49: "capture",
    50: "pricing",
    51: "compliance",
    52: "security",
    53: "security",
    54: "pricing",
    55: "compliance",
    56: "proposal",
    57: "pricing",
    58: "pricing",
}

STUDIO_SHORT_TITLES: Dict[int, str] = {
    21: "GovCon Sources Sought, RFI & Set-Aside Shaping Responder API",
    22: "GovCon OCI & FAR 9.5 Mitigation Plan Generator API",
    23: "SBIR / STTR Phase I-III Commercialization Plan API",
    24: "GovCon Section 508, WCAG 2.2 AA & VPAT 2.5 Auditor API",
    25: "GovCon Supply Chain SCRM, NDAA 889, TAA & SBOM Auditor API",
    26: "GovCon QASP, PRS, SLA & KPI Surveillance Matrix API",
    27: "GovCon 30/60/90-Day Phase-In Transition Plan API",
    28: "DCAA Pre-Award SF1408 Accounting System Auditor API",
    29: "DoD OTA 10 USC 4022 Prototype White Paper API",
    30: "DCSA FCL DD254 FOCI SF328 Clearance Auditor API",
    31: "FAR 52 219 9 Subcontracting Plan eSRS Calculator API",
    32: "DFARS 252 227 7013 7014 7017 Data Rights Assertion API",
    33: "GovCon Shipley Black Hat Incumbent Ghosting API",
    34: "GovCon CPARS Self Assessment 14 Day Rebuttal API",
    35: "GovCon REA Constructive Change CDA Claim API",
    36: "SBA Mentor Protege 13 CFR 125 8 Joint Venture API",
    37: "GovCon SCA FAR 52 222 41 Wage Determination Mapper API",
    38: "GovCon EVMS ANSI 748 IPMDR Variance Narrative API",
    39: "GovCon CAS 48 CFR 9904 DS1 DS2 Disclosure Auditor API",
    40: "ITAR 22 CFR 120 130 EAR TCP Export Compliance API",
    41: "DoD CDRL DD Form 1423 DID Schedule Extractor API",
    42: "FAR 6 302 8 405 6 Sole Source J and A LSJ Drafter API",
    43: "DFARS 252 204 7012 72 Hour DIBNet CIRCIA Incident API",
    44: "DOE NNSA National Lab MO DEAR 48 CFR Ch 9 Auditor API",
    45: "GWAC IDIQ Task Order Fair Opportunity FAR 16 505 API",
    46: "GovCon GFP FAR 52 245 1 PIEE Property Management API",
    47: "DoD OCONUS INDOPACOM SOFA Defense Base Act SPOT API",
    48: "CUI 32 CFR 2002 DoDI 5200 48 Handling Plan API",
    49: "SLED Cooperative Purchasing NASPO Sourcewell Piggyback API",
    50: "FAR Part 48 VECP FAR 52 248 1 Shared Savings Modeler API",
    51: "FAR 52 203 13 Business Ethics PIA OIG Disclosure API",
    52: "DoD FedRAMP Moderate Equivalency 3PAO BOE Auditor API",
    53: "Federal AI Governance OMB M 24 10 NIST AI RMF 1 0 API",
    54: "FAR Part 49 T4C SF 1435 1438 Settlement Calculator API",
    55: "GovCon MA Contract Novation FAR 42 1204 Package API",
    56: "SSEB Source Selection Simulator Shipley Proposal Scorer API",
    57: "GSA FAS Sales Reporting Portal TDR IFF Audit Reconciler API",
    58: "FAR Subpart 16 4 Award Fee CPAF CPIF FPIF Maximizer API",
}


def shorten_studio_title(api_num: int, title: str) -> str:
    """RapidAPI Studio enforces `len(info.title) <= 60` in `createApisFromRapidOas`."""
    if api_num in STUDIO_SHORT_TITLES:
        return STUDIO_SHORT_TITLES[api_num]
    if len(title) <= 60:
        return title
    trimmed = title.replace("Organizational Conflict of Interest (OCI)", "OCI")
    trimmed = trimmed.replace("Accessibility Conformance", "Auditor")
    trimmed = trimmed.replace("Supply Chain Risk Management (SCRM)", "Supply Chain SCRM")
    if len(trimmed) <= 60:
        return trimmed
    base = trimmed[:56].rsplit(" ", 1)[0].rstrip(",&- ")
    return f"{base} API"[:60]


def find_or_ensure_logo_500x500(api_num: int, title: str, route: str) -> Path:
    """Locate existing `api{N}_*_logo.png` or generate a 500x500 dark-navy enterprise PNG badge."""
    matches = sorted(DAAS_DIR.glob(f"api{api_num}_*logo*.png")) + sorted(DAAS_DIR.glob(f"api{api_num}_logo.png"))
    for m in matches:
        if m.exists() and m.stat().st_size > 1000:
            return m

    logo_path = DAAS_DIR / f"api{api_num}_logo.png"
    w, h = 500, 500
    rows = []
    for y in range(h):
        row = bytearray([0])
        for x in range(w):
            dx, dy = x - 250, y - 220
            dist_sq = dx * dx + dy * dy
            if 20 <= x <= 480 and (y in (20, 21, 479, 480) or x in (20, 21, 479, 480)):
                r, g, b = 56, 189, 248
            elif 9500 <= dist_sq <= 10500:
                r, g, b = 16, 185, 129
            elif 4200 <= dist_sq <= 4800:
                r, g, b = 245, 158, 11
            elif dist_sq <= 900:
                r, g, b = 56, 189, 248
            elif x % 50 == 0 or y % 50 == 0:
                r, g, b = 15, 28, 52
            else:
                r, g, b = 8, 15, 30
            row.extend((r, g, b))
        rows.append(bytes(row))

    raw_data = b"".join(rows)

    def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw_data, 9))
        + _png_chunk(b"IEND", b"")
    )
    logo_path.write_bytes(png_bytes)
    return logo_path


def _parse_cookie_str(cookie_str: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for part in (cookie_str or "").split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _persist_rolled_cookies(s: requests.Session, allow_empty_csrf: bool = False) -> None:
    """Merge valid Set-Cookie values from `s.cookies` back into `d:\\Daas\\.env` and `.rapidapi_session.json`."""
    csrf_tok = (s.headers.get("csrf-token") or "").strip()
    if not csrf_tok and not allow_empty_csrf:
        return
    current_map = _parse_cookie_str(s.headers.get("Cookie", ""))
    changed = False
    for c in s.cookies:
        if c.value and current_map.get(c.name) != c.value:
            current_map[c.name] = c.value
            changed = True
    if not current_map.get("connect.sid") or not current_map.get("jwt_auth"):
        return
    if not changed and SESSION_PATH.exists():
        try:
            existing_sess = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
            if existing_sess.get("csrf_token") == csrf_tok:
                return
        except Exception:
            pass

    new_cookie_str = "; ".join(f"{k}={v}" for k, v in current_map.items())
    s.headers["Cookie"] = new_cookie_str

    SESSION_PATH.write_text(
        json.dumps(
            {
                "cookie": new_cookie_str,
                "csrf_token": csrf_tok,
                "updated_at": int(time.time()),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    for env_path in (DAAS_DIR / ".env", ECOSYSTEM_DIR / ".env"):
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()
            new_lines = []
            found = False
            for line in lines:
                if line.startswith("RAPIDAPI_STUDIO_COOKIE="):
                    new_lines.append(f"RAPIDAPI_STUDIO_COOKIE='{new_cookie_str}'")
                    found = True
                else:
                    new_lines.append(line)
            if not found and env_path == DAAS_DIR / ".env":
                new_lines.append(f"RAPIDAPI_STUDIO_COOKIE='{new_cookie_str}'")
            env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8", newline="\n")


def update_rapidapi_cookie(raw_input: str) -> bool:
    """
    Accept either a full Cookie header string or a bare `connect.sid` value (`s%3A...`),
    merge it with existing RapidAPI cookies in `.env`, verify the GraphQL session, and persist.
    """
    clean = (raw_input or "").strip().strip("'").strip('"')
    if not clean:
        return False
    load_dotenv(DAAS_DIR / ".env", override=True)
    existing_str = (os.getenv("RAPIDAPI_STUDIO_COOKIE") or "").strip().strip("'").strip('"')
    cookie_map = _parse_cookie_str(existing_str)
    if "=" in clean and (";" in clean or "connect.sid=" in clean):
        incoming_map = _parse_cookie_str(clean)
        cookie_map.update(incoming_map)
    else:
        if clean.startswith("connect.sid="):
            clean = clean.split("=", 1)[1].strip()
        cookie_map["connect.sid"] = clean
    merged_str = "; ".join(f"{k}={v}" for k, v in cookie_map.items() if k and v)
    SESSION_PATH.write_text(
        json.dumps({"cookie": merged_str, "csrf_token": "", "updated_at": int(time.time())}, indent=2),
        encoding="utf-8",
    )
    os.environ["RAPIDAPI_STUDIO_COOKIE"] = merged_str
    for env_path in (DAAS_DIR / ".env", ECOSYSTEM_DIR / ".env"):
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()
            updated_lines = []
            found = False
            for line in lines:
                if line.startswith("RAPIDAPI_STUDIO_COOKIE="):
                    updated_lines.append(f"RAPIDAPI_STUDIO_COOKIE='{merged_str}'")
                    found = True
                else:
                    updated_lines.append(line)
            if not found and env_path == DAAS_DIR / ".env":
                updated_lines.append(f"RAPIDAPI_STUDIO_COOKIE='{merged_str}'")
            env_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8", newline="\n")
    return keepalive_rapidapi_session()


def load_rapidapi_session() -> requests.Session:
    """Create a requests.Session hydrated from `.rapidapi_session.json` or `RAPIDAPI_STUDIO_COOKIE` in `.env`."""
    load_dotenv(DAAS_DIR / ".env", override=True)
    cookie_str = (os.getenv("RAPIDAPI_STUDIO_COOKIE") or "").strip().strip("'").strip('"')
    saved_csrf = ""
    saved_ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    )
    if SESSION_PATH.exists():
        try:
            sess_data = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
            if sess_data.get("cookie"):
                cookie_str = sess_data["cookie"]
            saved_csrf = sess_data.get("csrf_token", "")
            if sess_data.get("user_agent"):
                saved_ua = sess_data["user_agent"]
        except Exception:
            pass

    if not cookie_str:
        raise RuntimeError("RAPIDAPI_STUDIO_COOKIE is not configured in d:\\Daas\\.env")

    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": saved_ua,
            "Cookie": cookie_str,
            "Accept": "application/json",
            "Origin": "https://rapidapi.com",
            "Referer": "https://rapidapi.com/studio",
            "rapid-client": "provider-dashboard-service",
            "x-entity-id": "12383419",
            "x-rapidapi-Rolling-Key": "true",
        }
    )
    if saved_csrf:
        s.headers["csrf-token"] = saved_csrf

    csrf_resp = s.get("https://rapidapi.com/gateway/csrf", timeout=20)
    if csrf_resp.status_code == 200:
        csrf_tok = csrf_resp.json().get("csrfToken", "")
        if csrf_tok:
            s.headers["csrf-token"] = csrf_tok
            _persist_rolled_cookies(s)
    return s


def _save_verified_browser_session(cookies_list: List[Dict[str, Any]], csrf_tok: str, user_agent: str) -> bool:
    """Persist verified browser cookies + csrfToken + userAgent to `.rapidapi_session.json` and `.env`."""
    load_dotenv(DAAS_DIR / ".env", override=True)
    cmap = _parse_cookie_str((os.getenv("RAPIDAPI_STUDIO_COOKIE") or "").strip().strip("'").strip('"'))
    for c in cookies_list:
        if "rapidapi.com" in str(c.get("domain", "")) and c.get("name") and c.get("value"):
            cmap[c["name"]] = c["value"]
    if not cmap.get("connect.sid") and not cmap.get("jwt_auth"):
        return False
    cookie_str = "; ".join(f"{k}={v}" for k, v in cmap.items() if k and v)
    SESSION_PATH.write_text(
        json.dumps(
            {
                "cookie": cookie_str,
                "csrf_token": csrf_tok or "",
                "user_agent": user_agent or "",
                "updated_at": int(time.time()),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    os.environ["RAPIDAPI_STUDIO_COOKIE"] = cookie_str
    for env_path in (DAAS_DIR / ".env", ECOSYSTEM_DIR / ".env"):
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()
            new_lines = []
            found = False
            for line in lines:
                if line.startswith("RAPIDAPI_STUDIO_COOKIE="):
                    new_lines.append(f"RAPIDAPI_STUDIO_COOKIE='{cookie_str}'")
                    found = True
                else:
                    new_lines.append(line)
            if not found and env_path == DAAS_DIR / ".env":
                new_lines.append(f"RAPIDAPI_STUDIO_COOKIE='{cookie_str}'")
            env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8", newline="\n")
    return True


def _clone_cookies_into_headless_profile(cookies_list: List[Dict[str, Any]]) -> None:
    """Copy verified RapidAPI cookies into `d:\\Daas\\.rapidapi_google_chrome_profile` for 100% headless keepalive."""
    r_cookies = []
    for c in cookies_list:
        if "rapidapi.com" in str(c.get("domain", "")) and c.get("name") and c.get("value"):
            clean_c: Dict[str, Any] = {
                "name": c["name"],
                "value": c["value"],
                "domain": c.get("domain", ".rapidapi.com"),
                "path": c.get("path", "/"),
                "secure": bool(c.get("secure", True)),
                "httpOnly": bool(c.get("httpOnly", False)),
            }
            if c.get("sameSite") in ("Strict", "Lax", "None"):
                clean_c["sameSite"] = c["sameSite"]
            if isinstance(c.get("expires"), (int, float)) and c["expires"] > 0:
                clean_c["expires"] = c["expires"]
            else:
                clean_c["expires"] = int(time.time()) + 86400 * 30
            r_cookies.append(clean_c)
    if not r_cookies:
        return
    try:
        from playwright.sync_api import sync_playwright

        profile_dir = DAAS_DIR / ".rapidapi_google_chrome_profile"
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                str(profile_dir),
                channel="chrome",
                headless=True,
                ignore_default_args=["--enable-automation"],
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx.add_cookies(r_cookies)
            ctx.close()
    except Exception as exc:
        print(f"[!] Note cloning cookies into headless profile: {exc}", flush=True)


def capture_session_from_active_chrome_cdp(timeout_ms: int = 120000) -> bool:
    """
    Connect to the user's running Google Chrome via `DevToolsActivePort` (`chrome://inspect/#remote-debugging`),
    mint/extract `connect.sid` + `jwt_auth` + `csrfToken`, persist to `.rapidapi_session.json` + `.env`,
    and clone the cookies into `d:\\Daas\\.rapidapi_google_chrome_profile` so background automation never prompts again.
    """
    port_file = Path(os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\DevToolsActivePort"))
    if not port_file.exists():
        return False
    try:
        lines = [ln.strip() for ln in port_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if len(lines) < 2:
            return False
        ws_url = f"ws://127.0.0.1:{lines[0]}{lines[1]}"
        print(
            f"[*] Connecting to active Chrome ({ws_url})... "
            "If Chrome shows 'Allow remote debugging?', click Allow once!",
            flush=True,
        )
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(ws_url, timeout=timeout_ms)
            ctx = browser.contexts[0]
            target_page = None
            for pg in ctx.pages:
                if "rapidapi.com" in (pg.url or ""):
                    target_page = pg
                    break
            created_temp = False
            if target_page is None:
                target_page = ctx.new_page()
                created_temp = True
            if "/studio" not in (target_page.url or ""):
                target_page.goto("https://rapidapi.com/studio", wait_until="domcontentloaded", timeout=30000)
                target_page.wait_for_timeout(3000)

            eval_res = target_page.evaluate(
                """async () => {
                const ua = navigator.userAgent;
                const cr = await fetch('https://rapidapi.com/gateway/csrf', {credentials: 'include'});
                const cj = await cr.json();
                const csrfToken = cj.csrfToken || '';
                const gr = await fetch('https://rapidapi.com/gateway/graphql', {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'content-type': 'application/json',
                        'csrf-token': csrfToken,
                        'rapid-client': 'provider-dashboard-service',
                        'x-entity-id': '12383419',
                        'x-rapidapi-Rolling-Key': 'true'
                    },
                    body: JSON.stringify({query: 'query { api(id: "api_4c6bdfeb-1400-4466-a1f7-87fcdeb819d4") { id } }'})
                });
                const gj = await gr.json();
                return {ua, csrfToken, gqlOk: Boolean(gj && gj.data && gj.data.api && gj.data.api.id), gj};
            }"""
            )
            all_cookies = ctx.cookies()
            if created_temp:
                try:
                    target_page.close()
                except Exception:
                    pass
        if eval_res and eval_res.get("gqlOk"):
            _save_verified_browser_session(
                all_cookies,
                eval_res.get("csrfToken", ""),
                eval_res.get("ua", ""),
            )
            _clone_cookies_into_headless_profile(all_cookies)
            print("[+] Captured active RapidAPI Studio session from Chrome & cloned to headless profile!", flush=True)
            return True
    except Exception as exc:
        print(f"[!] Active Chrome CDP note: {exc}", flush=True)
    return False


def refresh_session_via_persistent_browser(interactive: bool = False) -> bool:
    """
    Use the dedicated Playwright persistent Chrome profile (`d:\\Daas\\.rapidapi_google_chrome_profile`)
    that belongs directly to Python automation (zero Chrome 'Allow remote debugging?' popups).
    - When `interactive=True` (`--login-browser`), first attempts a 1-click capture from active Chrome CDP
      (`DevToolsActivePort`), and otherwise opens the persistent profile window.
    - When `interactive=False` (default background keepalive fallback), runs 100% headlessly
      using the saved persistent profile to refresh `connect.sid` and `csrf-token`.
    """
    if interactive and capture_session_from_active_chrome_cdp(timeout_ms=90000):
        return True

    profile_dir = DAAS_DIR / ".rapidapi_google_chrome_profile"
    if not interactive and not profile_dir.exists():
        return False
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            launch_kwargs: Dict[str, Any] = {
                "user_data_dir": str(profile_dir),
                "headless": not interactive,
                "ignore_default_args": ["--enable-automation"],
                "args": ["--disable-blink-features=AutomationControlled"],
                "viewport": {"width": 1280, "height": 860},
            }
            try:
                ctx = p.chromium.launch_persistent_context(channel="chrome", **launch_kwargs)
            except Exception:
                ctx = p.chromium.launch_persistent_context(**launch_kwargs)

            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(
                "https://rapidapi.com/auth/login?referral=/studio" if interactive else "https://rapidapi.com/studio",
                wait_until="domcontentloaded",
                timeout=45000,
            )

            deadline = time.time() + (300 if interactive else 25)
            saved_ok = False
            while time.time() < deadline:
                all_cookies = ctx.cookies()
                cmap = {
                    c["name"]: c["value"]
                    for c in all_cookies
                    if "rapidapi.com" in str(c.get("domain", "")) and c.get("name") and c.get("value")
                }
                if cmap.get("connect.sid") or cmap.get("jwt_auth"):
                    if not cmap.get("connect.sid") and "/studio" not in (page.url or ""):
                        try:
                            page.goto("https://rapidapi.com/studio", wait_until="domcontentloaded", timeout=25000)
                            page.wait_for_timeout(2500)
                            all_cookies = ctx.cookies()
                        except Exception:
                            pass
                    eval_res = page.evaluate(
                        """async () => {
                        try {
                            const ua = navigator.userAgent;
                            const cr = await fetch('https://rapidapi.com/gateway/csrf', {credentials: 'include'});
                            const cj = await cr.json();
                            const csrfToken = cj.csrfToken || '';
                            const gr = await fetch('https://rapidapi.com/gateway/graphql', {
                                method: 'POST',
                                credentials: 'include',
                                headers: {
                                    'content-type': 'application/json',
                                    'csrf-token': csrfToken,
                                    'rapid-client': 'provider-dashboard-service',
                                    'x-entity-id': '12383419',
                                    'x-rapidapi-Rolling-Key': 'true'
                                },
                                body: JSON.stringify({query: 'query { api(id: "api_4c6bdfeb-1400-4466-a1f7-87fcdeb819d4") { id } }'})
                            });
                            const gj = await gr.json();
                            return {ua, csrfToken, gqlOk: Boolean(gj && gj.data && gj.data.api && gj.data.api.id)};
                        } catch (e) {
                            return {gqlOk: false};
                        }
                    }"""
                    )
                    if eval_res and eval_res.get("gqlOk"):
                        all_cookies = ctx.cookies()
                        saved_ok = _save_verified_browser_session(
                            all_cookies,
                            eval_res.get("csrfToken", ""),
                            eval_res.get("ua", ""),
                        )
                        if saved_ok:
                            print("[+] Captured live connect.sid + csrfToken from persistent Chrome profile!", flush=True)
                            break
                page.wait_for_timeout(2000)

            ctx.close()
            if saved_ok:
                return keepalive_rapidapi_session()
    except Exception as exc:
        print(f"[!] Persistent browser error: {exc}", flush=True)
    return False


def keepalive_rapidapi_session(allow_browser_refresh: bool = False) -> bool:
    """
    Ping `/gateway/csrf` AND execute a lightweight authenticated `POST /gateway/graphql` query
    with `x-rapidapi-Rolling-Key: true` so RapidAPI's Express session (`connect.sid`) genuinely rolls
    and never expires. Only spawns Playwright browser refresh if `allow_browser_refresh=True`.
    """
    try:
        s = load_rapidapi_session()
        if s.headers.get("csrf-token"):
            res = gql(
                s,
                'query { api(id: "api_4c6bdfeb-1400-4466-a1f7-87fcdeb819d4") { id } }',
            )
            if res.get("action") != "force_logout":
                api_id = ((res.get("data") or {}).get("api") or {}).get("id")
                if api_id:
                    _persist_rolled_cookies(s)
                    return True
    except Exception:
        pass
    if allow_browser_refresh:
        return refresh_session_via_persistent_browser(interactive=False)
    return False


def gql(
    s: requests.Session,
    query: str,
    variables: Optional[Dict[str, Any]] = None,
    op_name: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"query": query, "variables": variables or {}}
    if op_name:
        payload["operationName"] = op_name
    r = s.post(GQL_URL, json=payload, timeout=45)
    try:
        data = r.json()
    except Exception:
        return {"status_code": r.status_code, "raw": r.text[:300]}
    if r.status_code == 200 and data.get("action") != "force_logout":
        _persist_rolled_cookies(s)
    return data


def sync_secret_to_env_and_security(new_secret: str) -> None:
    """Append the new RapidAPI proxy secret to .env files, core/security.py SHA-256 set, and Render API if key present."""
    clean = (new_secret or "").strip()
    if not clean:
        return

    for env_path in (DAAS_DIR / ".env", ECOSYSTEM_DIR / ".env"):
        if env_path.exists():
            txt = env_path.read_text(encoding="utf-8")
            if clean not in txt:
                lines = txt.splitlines()
                updated = []
                for line in lines:
                    if line.startswith("RAPIDAPI_PROXY_SECRET="):
                        line = line.rstrip() + "," + clean
                    updated.append(line)
                env_path.write_text("\n".join(updated) + "\n", encoding="utf-8", newline="\n")

    digest = hashlib.sha256(clean.encode("utf-8")).hexdigest()
    sec_path = ECOSYSTEM_DIR / "core" / "security.py"
    if sec_path.exists():
        sec_txt = sec_path.read_text(encoding="utf-8")
        if digest not in sec_txt:
            target = "REGISTERED_PROXY_SECRET_SHA256 = {\n"
            if target in sec_txt:
                sec_txt = sec_txt.replace(target, f'{target}    "{digest}",\n', 1)
                sec_path.write_text(sec_txt, encoding="utf-8", newline="\n")

    load_dotenv(DAAS_DIR / ".env")
    render_api_key = (os.getenv("RENDER_API_KEY") or "").strip()
    if render_api_key:
        try:
            headers = {"Authorization": f"Bearer {render_api_key}", "Accept": "application/json"}
            resp = requests.get(
                f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/env-vars/RAPIDAPI_PROXY_SECRET",
                headers=headers,
                timeout=20,
            )
            if resp.status_code == 200:
                curr_val = resp.json().get("value", "")
                if clean not in curr_val:
                    new_val = f"{curr_val},{clean}" if curr_val else clean
                    requests.put(
                        f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/env-vars/RAPIDAPI_PROXY_SECRET",
                        headers=headers,
                        json={"value": new_val},
                        timeout=20,
                    )
        except Exception as exc:
            report_error("rapidapi_headless_publisher.py", f"Optional Render API env update note: {exc}")


QUERY_EP = """
query GetVersionEndpoints($apiId: ID!) {
  api(id: $apiId) {
    id
    currentVersion {
      id
      endpoints {
        id
        name
        route
        method
        description
        requestPayloads {
          id
          name
          format
          body
          description
          examples
          schema
        }
        responsePayloads {
          id
          name
          format
          body
          headers
          description
          status
          statusCode
          examples
          schema
        }
      }
    }
  }
}
"""


def _create_or_configure_studio_project(
    s: requests.Session,
    api_num: int,
    title: str,
    summary: str,
    product_slug: str,
    logo_path: Path,
    readme_text: str,
    oas_path: Path,
) -> Optional[Dict[str, Any]]:
    """Create the standalone API project in Rapid Studio (`createApisFromRapidOas`) and configure Logo, README, Healthcheck, and 4 Pricing Plans."""
    studio_title = shorten_studio_title(api_num, title)

    existing_search = gql(
        s,
        """
        query {
          apis(where: { ownerId: ["12383419"] }, pagination: { first: 60 }) {
            nodes {
              id
              name
              slugifiedName
            }
          }
        }
        """,
    )
    if existing_search.get("action") == "force_logout":
        raise RuntimeError(
            "RAPIDAPI_STUDIO_COOKIE session expired (`force_logout`). "
            "Refresh cookie from logged-in Chrome Studio tab."
        )

    api_id = None
    for node in ((existing_search.get("data") or {}).get("apis") or {}).get("nodes") or []:
        n_name = (node.get("name") or "").lower()
        if n_name in (title.lower(), studio_title.lower()) or studio_title[:24].lower() in n_name:
            api_id = node["id"]
            break

    if not api_id and oas_path.exists():
        # Ensure info.title <= 60 chars, info.x-category == "Business", inline $refs, and production server URL
        try:
            oas_obj = json.loads(oas_path.read_text(encoding="utf-8"))
            schemas = (oas_obj.get("components") or {}).get("schemas") or {}

            def _inline_refs(obj: Any) -> Any:
                if isinstance(obj, dict):
                    if "$ref" in obj and isinstance(obj["$ref"], str) and obj["$ref"].startswith("#/components/schemas/"):
                        ref_name = obj["$ref"].split("/")[-1]
                        resolved = json.loads(json.dumps(schemas.get(ref_name, {"type": "object"})))
                        return _inline_refs(resolved)
                    return {k: _inline_refs(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [_inline_refs(x) for x in obj]
                return obj

            inlined_paths = _inline_refs(oas_obj.get("paths", {}))
            inlined_paths.pop("/v1/health", None)
            for _rt, methods in inlined_paths.items():
                for _m, m_obj in methods.items():
                    if isinstance(m_obj, dict):
                        m_obj.pop("tags", None)
                        if "responses" in m_obj:
                            m_obj["responses"] = {
                                "200": {
                                    "description": m_obj["responses"].get("200", {}).get("description", "Successful response"),
                                    "content": {"application/json": {"schema": {"type": "object"}}},
                                }
                            }
            desc_raw = (oas_obj.get("info") or {}).get("description", summary)
            clean_oas = {
                "openapi": "3.0.3",
                "info": {
                    "title": studio_title,
                    "version": "1.0.0",
                    "x-category": "Business",
                    "description": desc_raw.encode("ascii", "ignore").decode("ascii"),
                },
                "servers": [{"url": BACKEND_URL}],
                "paths": inlined_paths,
            }
            oas_path.write_text(json.dumps(clean_oas, indent=2) + "\n", encoding="utf-8", newline="\n")
        except Exception:
            pass

        create_ops = json.dumps(
            {
                "operationName": "createApisFromRapidOas",
                "variables": {"creations": [{"spec": None}]},
                "query": """
                mutation createApisFromRapidOas($creations: [ApiCreateFromRapidOasInput!]!) {
                  createApisFromRapidOas(creations: $creations) {
                    apiId
                    trackingId
                  }
                }
                """,
            }
        )
        with open(oas_path, "rb") as spec_f:
            create_resp = s.post(
                GQL_URL,
                data={
                    "operations": create_ops,
                    "map": json.dumps({"0": ["variables.creations.0.spec"]}),
                },
                files={"0": (oas_path.name, spec_f, "application/json")},
                timeout=40,
            ).json()
        _persist_rolled_cookies(s)
        created_list = (create_resp.get("data") or {}).get("createApisFromRapidOas") or []
        if created_list:
            api_id = created_list[0].get("apiId")
            time.sleep(2)
        else:
            print(f"[!] createApisFromRapidOas for API #{api_num} returned:", create_resp)

    if not api_id:
        return None

    raw_info = gql(
        s,
        """
        query($id: ID!) {
          api(id: $id) {
            id
            name
            slugifiedName
            secret
            category
            description
            visibility
            thumbnail
            currentVersion {
              id
              name
            }
            billingPlans {
              id
              name
              version {
                id
                billinglimits {
                  billingitem {
                    id
                  }
                }
              }
            }
          }
        }
        """,
        {"id": api_id},
    )
    info = (raw_info.get("data") or {}).get("api")
    if not info:
        return None

    if info.get("secret"):
        sync_secret_to_env_and_security(info["secret"])

    # Try updating metadata + Logo + README with PUBLIC first; if 20-public-API quota reached, save with PRIVATE so Studio card has full Logo & README
    final_vis = info.get("visibility") or "PRIVATE"
    final_thumb = info.get("thumbnail")
    for vis in ("PUBLIC", "PRIVATE"):
        operations = json.dumps(
            {
                "operationName": "UpdateApiMeta",
                "variables": {
                    "api": {
                        "id": api_id,
                        "category": info.get("category") or "Business",
                        "description": summary[:280],
                        "longDescription": readme_text,
                        "termsOfService": {"text": ""},
                        "websiteUrl": f"https://signaltender.net/apis.html#product-{product_slug}",
                        "visibility": vis,
                        "thumbnail": None,
                        "tags": [],
                        "config": {"generateSDK": False},
                    }
                },
                "query": """
                mutation UpdateApiMeta($api: ApiUpdateInput!) {
                  updateApi(api: $api) {
                    id
                    slugifiedName
                    visibility
                    thumbnail
                  }
                }
                """,
            }
        )
        with open(logo_path, "rb") as img_f:
            mp_resp = s.post(
                GQL_URL,
                data={
                    "operations": operations,
                    "map": json.dumps({"0": ["variables.api.thumbnail"]}),
                },
                files={"0": (logo_path.name, img_f, "image/png")},
                timeout=35,
            ).json()
        _persist_rolled_cookies(s)
        upd = (mp_resp.get("data") or {}).get("updateApi")
        if upd:
            final_vis = upd.get("visibility") or vis
            final_thumb = upd.get("thumbnail")
            break

    # Configure Healthcheck
    gql(
        s,
        """
        mutation($apiId: ID!, $healthCheckUrl: String!) {
          upsertApiHealthcheck(apiId: $apiId, healthCheckUrl: $healthCheckUrl)
        }
        """,
        {"apiId": api_id, "healthCheckUrl": f"{BACKEND_URL}/v1/health"},
    )

    # Configure 4 pricing plans (BASIC $0, PRO $49, ULTRA $149 recommended, MEGA $399)
    ver_id = (info.get("currentVersion") or {}).get("id")
    ver_name = (info.get("currentVersion") or {}).get("name") or "1.0.0"
    bplans = info.get("billingPlans") or []
    if ver_id and bplans:
        item_id = bplans[0]["version"]["billinglimits"][0]["billingitem"]["id"]
        existing_plans = {p["name"]: p["id"] for p in bplans}
        basic_id = existing_plans.get("BASIC")
        if basic_id:
            basic_ext = {
                "api": api_id,
                "apiName": studio_title,
                "apiVersion": ver_id,
                "apiVersionName": ver_name,
                "providerName": "SignalTender",
                "billingPlanId": basic_id,
                "isStudent": False,
                "isPrivatePlan": False,
                "legalAccountId": "",
                "legalDocumentId": "",
                "name": "BASIC",
                "targetGroup": "",
                "billingLimits": [
                    {
                        "amount": 10,
                        "item": item_id,
                        "limitType": "hard",
                        "overagePrice": 0,
                        "period": "MONTHLY",
                        "perusagePrice": 0,
                        "unlimited": False,
                    }
                ],
                "enableBillingFeatures": [],
                "price": 0,
                "type": "MONTHLY",
                "shouldRequestApproval": False,
                "requestApprovalQuestion": "",
                "rateLimit": {"amount": 10, "enabled": True, "unit": 1, "unitName": "hour"},
            }
            gql(
                s,
                """
                mutation UpdateBasic($ext: BillingPlanExtendedUpdateInput!) {
                  updateBillingPlanExtended(billingPlan: $ext) {
                    id
                    name
                  }
                }
                """,
                {"ext": basic_ext},
                "UpdateBasic",
            )

        for pname, price, quota, overage, is_rec in [
            ("PRO", 49, 200, 0.25, False),
            ("ULTRA", 149, 1000, 0.15, True),
            ("MEGA", 399, 4000, 0.10, False),
        ]:
            if pname in existing_plans:
                continue
            c_input = {
                "api": api_id,
                "apiName": studio_title,
                "apiVersion": ver_id,
                "apiVersionName": ver_name,
                "providerName": "SignalTender",
                "isStudent": False,
                "isPrivatePlan": False,
                "legalAccountId": "",
                "legalDocumentId": "",
                "name": pname,
                "targetGroup": "",
                "billingLimits": [
                    {
                        "amount": quota,
                        "item": item_id,
                        "limitType": "soft",
                        "overagePrice": overage,
                        "period": "MONTHLY",
                        "perusagePrice": overage,
                        "unlimited": False,
                    }
                ],
                "enableBillingFeatures": [],
                "price": price,
                "type": "MONTHLY",
                "shouldRequestApproval": False,
                "requestApprovalQuestion": "",
            }
            r_create = gql(
                s,
                """
                mutation createBillingPlan($input: BillingPlanCreateInput!) {
                  createBillingPlan(billingPlan: $input) {
                    id
                    name
                  }
                }
                """,
                {"input": c_input},
                "createBillingPlan",
            )
            new_pid = ((r_create.get("data") or {}).get("createBillingPlan") or {}).get("id")
            if is_rec and new_pid:
                gql(
                    s,
                    """
                    mutation SetRec($input: BillingPlanMetadataUpdateInput!) {
                      updateBillingPlanMetadata(billingPlan: $input) {
                        id
                        recommended
                      }
                    }
                    """,
                    {
                        "input": {
                            "billingPlanId": new_pid,
                            "recommended": True,
                            "legalDocumentId": "",
                            "legalAccountId": "",
                        }
                    },
                    "SetRec",
                )

    return {
        "studio_api_id": api_id,
        "studio_slug": info.get("slugifiedName"),
        "visibility": final_vis,
        "thumbnail": final_thumb,
        "proxy_secret": info.get("secret"),
    }


def _mirror_endpoint_to_public_storefront(
    s: requests.Session,
    studio_api_id: Optional[str],
    public_api_id: str,
    route: str,
    ep_title: str,
    summary: str,
    sample_payload: Dict[str, Any],
) -> Any:
    """Clone the OpenAPI-imported endpoint from `studio_api_id` (or construct directly) onto `public_api_id`."""
    req_payloads = []
    resp_payloads = []
    if studio_api_id:
        res_src = gql(s, QUERY_EP, {"apiId": studio_api_id})
        ver_src = ((res_src.get("data") or {}).get("api") or {}).get("currentVersion") or {}
        eps_src = ver_src.get("endpoints") or []
        if eps_src:
            ep_src = eps_src[0]
            for rp in ep_src.get("requestPayloads") or []:
                req_payloads.append(
                    {
                        "name": rp.get("name") or "application/json",
                        "format": rp.get("format") or "JSON",
                        "body": rp.get("body") or json.dumps(sample_payload, indent=2),
                        "description": rp.get("description") or summary[:200],
                        "examples": rp.get("examples"),
                        "schema": rp.get("schema"),
                    }
                )
            for rp in ep_src.get("responsePayloads") or []:
                resp_payloads.append(
                    {
                        "name": rp.get("name") or str(rp.get("statusCode") or 200),
                        "format": rp.get("format") or "JSON",
                        "body": rp.get("body") or "",
                        "headers": rp.get("headers") or "{}",
                        "description": rp.get("description") or "",
                        "status": rp.get("status") or "ACTIVE",
                        "statusCode": rp.get("statusCode") or 200,
                        "examples": rp.get("examples"),
                        "schema": rp.get("schema"),
                    }
                )

    if not req_payloads:
        req_payloads = [
            {
                "name": "application/json",
                "format": "JSON",
                "body": json.dumps(sample_payload, indent=2),
                "description": summary[:200],
                "examples": {"Sample": {"value": sample_payload}},
                "schema": {"type": "object"},
            }
        ]

    res_pub = gql(s, QUERY_EP, {"apiId": public_api_id})
    ver_pub = ((res_pub.get("data") or {}).get("api") or {}).get("currentVersion") or {}
    pub_ver_id = ver_pub.get("id")
    if not pub_ver_id:
        return None

    existing_ep = next((e for e in (ver_pub.get("endpoints") or []) if e.get("route") == route), None)
    inp: Dict[str, Any] = {
        "name": ep_title[:65],
        "description": summary[:280],
        "externalDocs": {},
        "apiVersionId": pub_ver_id,
        "params": {"route": [], "header": []},
        "payloadParameters": [],
        "method": "POST",
        "displayResponse": False,
        "response": "",
        "responsePayloads": resp_payloads,
        "requestPayloads": req_payloads,
        "route": route,
        "routeregex": route,
    }
    if existing_ep:
        inp["endpointId"] = existing_ep["id"]

    mut_ep = """
    mutation updateEndpointWithParameters($input: updateOrCreateEndpointWithParameters!) {
      updateOrCreateEndpointWithParameters(input: $input)
    }
    """
    res_mirror = gql(s, mut_ep, {"input": inp}, "updateEndpointWithParameters")
    return (res_mirror.get("data") or {}).get("updateOrCreateEndpointWithParameters") or res_mirror


def publish_day_api(day_num: int, sample_payload: Dict[str, Any], endpoint_name: Optional[str] = None) -> Dict[str, Any]:
    """Publish the API for `day_num` in daily_expansion_roadmap.json to RapidAPI Studio AND mirror onto its public storefront."""
    roadmap = json.loads(ROADMAP_PATH.read_text(encoding="utf-8"))
    item = next((x for x in roadmap["items"] if x["day"] == day_num), None)
    if not item:
        raise ValueError(f"Day {day_num} not found in {ROADMAP_PATH}")

    api_cfg = item["api"]
    api_num = api_cfg["api_number"]
    title = api_cfg["title"]
    route = api_cfg["route"]
    summary = api_cfg["summary"]
    product_slug = api_cfg.get("slug") or api_cfg.get("product_id", f"product-api-{api_num}").replace("product-", "")
    category = API_NUM_MIRROR_OVERRIDE.get(api_num, api_cfg.get("category", "capture"))
    ep_title = endpoint_name or shorten_studio_title(api_num, title).replace(" API", "")

    logo_path = find_or_ensure_logo_500x500(api_num, title, route)
    readme_path = DAAS_DIR / f"rapidapi_api{api_num}_readme.md"
    readme_text = (
        readme_path.read_text(encoding="utf-8")
        if readme_path.exists()
        else f"# {title}\n\n{summary}\n\n- **Endpoint:** `POST {route}`\n"
    )
    oas_path = DAAS_DIR / f"rapidapi_api{api_num}_openapi.json"

    s = load_rapidapi_session()

    # 1. Create & configure standalone API project in Rapid Studio (https://rapidapi.com/studio)
    studio_info = _create_or_configure_studio_project(
        s=s,
        api_num=api_num,
        title=title,
        summary=summary,
        product_slug=product_slug,
        logo_path=logo_path,
        readme_text=readme_text,
        oas_path=oas_path,
    )

    # 1.5 Ensure standalone Studio project endpoint has Title Case name and sample payload
    studio_api_id = (studio_info or {}).get("studio_api_id")
    studio_slug = (studio_info or {}).get("studio_slug") or product_slug
    if studio_api_id:
        _mirror_endpoint_to_public_storefront(
            s=s,
            studio_api_id=studio_api_id,
            public_api_id=studio_api_id,
            route=route,
            ep_title=ep_title,
            summary=summary,
            sample_payload=sample_payload,
        )

    # 2. Mirror endpoint onto public RapidAPI storefront immediately as well
    mirror = PUBLIC_MIRROR_TARGETS.get(category, PUBLIC_MIRROR_TARGETS["capture"])
    mirror_res = _mirror_endpoint_to_public_storefront(
        s=s,
        studio_api_id=studio_api_id,
        public_api_id=mirror["api_id"],
        route=route,
        ep_title=ep_title,
        summary=summary,
        sample_payload=sample_payload,
    )
    return {
        "api_number": api_num,
        "studio_project": studio_info,
        "public_host": f"{studio_slug}.p.rapidapi.com",
        "public_hub_url": f"https://rapidapi.com/aarbchen/api/{studio_slug}",
        "mirror_endpoint": mirror_res,
    }


def sync_completed_days_to_rapidapi(days: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    """Publish all completed roadmap days (e.g. Days 2, 3, 4, 5 -> APIs #22-#25) to Rapid Studio and public storefronts."""
    from seed_rapidapi_telemetry import ENDPOINTS

    payload_by_api_num: Dict[int, Dict[str, Any]] = {}
    for ep in ENDPOINTS:
        m_id = str(ep.get("id", ""))
        if m_id.startswith("API "):
            try:
                num = int(m_id.split(" ")[1])
                payload_by_api_num[num] = ep.get("payload", {})
            except ValueError:
                pass

    roadmap = json.loads(ROADMAP_PATH.read_text(encoding="utf-8"))
    target_days = days or [
        x["day"] for x in roadmap["items"] if x.get("status") == "completed" and x["day"] >= 2
    ]
    results = []
    for d in target_days:
        item = next((x for x in roadmap["items"] if x["day"] == d), None)
        if not item:
            continue
        api_num = item["api"]["api_number"]
        sample_payload = payload_by_api_num.get(api_num, {})
        out = publish_day_api(d, sample_payload)
        print(f"[+] Published Day {d} (API #{api_num}) to RapidAPI Studio & Public Hub:", json.dumps(out, indent=2))
        results.append(out)
    return results


def get_unposted_completed_days() -> List[int]:
    """
    Probe live RapidAPI gateway (`https://<rapid_host><path>`) for every completed roadmap day.
    Returns any day whose standalone RapidAPI project returns 404 (`API doesn't exists`).
    """
    from seed_rapidapi_telemetry import ENDPOINTS

    load_dotenv(DAAS_DIR / ".env", override=True)
    rkey = (os.getenv("RAPIDAPI_KEY") or "").strip()
    ep_by_num: Dict[int, Dict[str, Any]] = {}
    for ep in ENDPOINTS:
        m_id = str(ep.get("id", ""))
        if m_id.startswith("API "):
            try:
                ep_by_num[int(m_id.split(" ")[1])] = ep
            except ValueError:
                pass

    roadmap = json.loads(ROADMAP_PATH.read_text(encoding="utf-8"))
    unposted: List[int] = []
    for item in roadmap.get("items", []):
        if item.get("status") != "completed":
            continue
        day_num = int(item["day"])
        api_num = int(item["api"]["api_number"])
        ep = ep_by_num.get(api_num)
        if not ep:
            continue
        host = ep.get("rapid_host", "")
        path = ep.get("path", "")
        if not host or not path:
            continue
        try:
            resp = requests.post(
                f"https://{host}{path}",
                headers={
                    "X-RapidAPI-Key": rkey,
                    "X-RapidAPI-Host": host,
                    "Content-Type": "application/json",
                },
                json={},
                timeout=12,
            )
            if resp.status_code == 404 and "doesn't exists" in resp.text:
                unposted.append(day_num)
        except Exception:
            pass
    return unposted


def auto_sync_unposted_apis(commit_and_push: bool = True) -> Dict[str, Any]:
    """
    Check if any completed roadmap APIs are missing from RapidAPI Studio (`404 API doesn't exists`).
    If any are missing and the RapidAPI Studio session is active, automatically publish them,
    register their proxy secrets in `core/security.py`, and push to GitHub/Render.
    """
    unposted_days = get_unposted_completed_days()
    if not unposted_days:
        return {"status": "ALL_POSTED", "unposted_days": [], "published": []}
    if not keepalive_rapidapi_session():
        return {"status": "SESSION_EXPIRED", "unposted_days": unposted_days, "published": []}
    published = sync_completed_days_to_rapidapi(unposted_days)
    if commit_and_push and published:
        import subprocess
        try:
            subprocess.run(
                ["git", "add", "core/security.py"],
                cwd=str(ECOSYSTEM_DIR),
                timeout=20,
                check=False,
            )
            diff_ec = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=str(ECOSYSTEM_DIR),
                timeout=15,
            )
            if diff_ec.returncode != 0:
                subprocess.run(
                    ["git", "commit", "-m", f"chore(security): register RapidAPI Studio SHA-256 proxy digests for days {unposted_days}"],
                    cwd=str(ECOSYSTEM_DIR),
                    timeout=30,
                    check=False,
                )
                subprocess.run(
                    ["git", "push", "origin", "main"],
                    cwd=str(ECOSYSTEM_DIR),
                    timeout=60,
                    check=False,
                )
        except Exception as exc:
            report_error("rapidapi_headless_publisher.py", f"Auto-push ecosystem security.py note: {exc}")
    return {"status": "SYNCED", "unposted_days": unposted_days, "published": published}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Headless RapidAPI Studio & Render Publisher")
    parser.add_argument("--check-session", action="store_true", help="Verify RAPIDAPI_STUDIO_COOKIE is valid and roll cookie")
    parser.add_argument("--login-browser", action="store_true", help="Open persistent automation Chromium profile once to log into RapidAPI Studio and auto-sync all APIs")
    parser.add_argument("--set-cookie", type=str, help="Update RAPIDAPI_STUDIO_COOKIE (or connect.sid) and sync missing APIs")
    parser.add_argument("--check-unposted", action="store_true", help="List completed roadmap days not yet live on RapidAPI")
    parser.add_argument("--sync-missing", action="store_true", help="Publish all unposted completed roadmap APIs to Rapid Studio & Public Hub")
    parser.add_argument("--day", type=int, help="Publish a specific roadmap day number")
    args = parser.parse_args()
    if args.login_browser:
        ok = refresh_session_via_persistent_browser(interactive=True)
        print("[+] Persistent Chromium profile authenticated:", ok)
        if ok:
            res = auto_sync_unposted_apis(commit_and_push=True)
            print("[+] Auto-sync result:", json.dumps(res, indent=2))
    elif args.set_cookie:
        ok = update_rapidapi_cookie(args.set_cookie)
        print("[+] Cookie updated; session active:", ok)
        if ok:
            res = auto_sync_unposted_apis(commit_and_push=True)
            print("[+] Auto-sync result:", json.dumps(res, indent=2))
    elif args.check_session:
        ok = keepalive_rapidapi_session()
        print("[+] Headless RapidAPI GraphQL session active:", ok)
        if not ok:
            raise SystemExit(1)
    elif args.check_unposted:
        days = get_unposted_completed_days()
        print("[*] Unposted completed roadmap days:", days)
    elif args.sync_missing:
        res = auto_sync_unposted_apis(commit_and_push=True)
        print("[+] Sync-missing result:", json.dumps(res, indent=2))
    elif args.day:
        sync_completed_days_to_rapidapi([args.day])
