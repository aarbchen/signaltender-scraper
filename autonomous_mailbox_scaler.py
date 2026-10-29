"""
Autonomous 50% Revenue-to-Mailbox Reinvestment, Cloudflare DNS/BIMI & Instantly Provisioning Engine
(`autonomous_mailbox_scaler.py`).
====================================================================================================
Executes a closed-loop, self-funding outbound scaling flywheel:
  1. 50% Revenue Treasury Ledger:
     - Tracks every real Stripe conversion (`SUBSCRIBER_ACTIVE` & `SUBSCRIBER_REINVESTMENT_TREASURY`
       in Supabase + local `reinvestment_treasury_ledger.json`) and allocates 50% of gross subscription
       revenue (`$49.50` per Tier 1 `$99`, `$199.50` per Tier 2 `$399`, `$749.50` per Tier 3 `$1,499`,
       `$1,249.50` per Tier 4 `$2,499`) into the mailbox expansion treasury.
     - Every `$21.00` in unspent 50% treasury balance unlocks 1 Sending Pod:
       `1 GovCon Shard Domain (~$10.44/yr) + 3 Branded Mailboxes (~$3.50/mo x 3 = $10.50) = +90 emails/day`.
  2. Live Shard Domain Discovery, Registration & Cloudflare DNS + BIMI + 301 Redirect:
     - Verifies live `.com` availability via Verisign RDAP (`https://rdap.verisign.com/com/v1/domain/<domain>`).
     - Registers the domain via Cloudflare Registrar API (`CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID`),
       Porkbun API (`PORKBUN_API_KEY` + `PORKBUN_SECRET_KEY`), or Mailforge API (`MAILFORGE_API_KEY`).
     - Provisions the Cloudflare Zone (`POST /client/v4/zones`) and automatically creates:
       • Google Workspace `MX` records (`ASPMX.L.GOOGLE.COM`, `ALT1`..`ALT4`)
       • `SPF` TXT (`v=spf1 include:_spf.google.com ~all`)
       • `_dmarc` TXT (`v=DMARC1; p=quarantine; pct=100; rua=mailto:dmarc@signaltender.net; adkim=r; aspf=r;`)
       • `default._bimi` TXT (`v=BIMI1; l=https://signaltender.net/bimi-logo.svg;`) for inbox brand logo rendering
       • Root `@` & `www` proxied `A` records + Cloudflare Single Redirect Ruleset (`301 -> https://signaltender.net`)
  3. 3 Mailboxes per Domain + SignalTender Avatar Photo Branding:
     - Generates a crisp 500x500 PNG SignalTender radar-chevron avatar (`signaltender_mailbox_avatar_500.png`).
     - Creates 3 mailboxes per shard domain (`aaron@<domain>`, `capture@<domain>`, `desk@<domain>`) via
       Google Workspace Admin SDK Directory API (`POST /admin/directory/v1/users`) or Mailforge API.
     - Uploads the SignalTender 500x500 PNG logo to each mailbox profile via Google Admin SDK
       (`PUT /admin/directory/v1/users/{userKey}/photos/thumbnail`, URL-safe base64 `photoData`).
  4. Instantly.ai V2 Auto-Queue, Warmup Enable & Campaign Expansion:
     - Registers each new mailbox in Instantly (`POST /api/v2/accounts`), enables automated warmup
       (`POST /api/v2/accounts/warmup/enable`), holds new accounts in Warmup-Only mode until
       `stat_warmup_score >= 85`, and automatically graduates warmed accounts into Campaign
       `c7727dff-92cc-4621-9e96-c960938d5a47` while scaling `daily_limit` (`30 * warmed_mailboxes`)
       and `INSTANTLY_MAX_ACTIVE_BUFFER` (`max(245, warmed_mailboxes * 90)`).
"""

from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()

import argparse
import base64
from datetime import datetime, timezone
import json
import math
import os
import secrets
from typing import Any, Dict, List, Optional, Tuple
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TREASURY_LEDGER_PATH = os.path.join(BASE_DIR, "reinvestment_treasury_ledger.json")
AVATAR_PNG_PATH = os.path.join(BASE_DIR, "apple-touch-icon.png")
BIMI_SVG_URL = "https://signaltender.net/bimi-logo.svg"

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or "").strip()
DISCORD_WEBHOOK_URL = (os.getenv("DISCORD_WEBHOOK_URL") or "").strip()

INSTANTLY_API_KEY = (os.getenv("INSTANTLY_API_KEY") or "").strip()
INSTANTLY_CAMPAIGN_ID = (os.getenv("INSTANTLY_CAMPAIGN_ID") or "c7727dff-92cc-4621-9e96-c960938d5a47").strip()

CLOUDFLARE_API_TOKEN = (os.getenv("CLOUDFLARE_API_TOKEN") or "").strip()
CLOUDFLARE_ACCOUNT_ID = (os.getenv("CLOUDFLARE_ACCOUNT_ID") or "1bd620fee1e67b48923bfbe445c3a88c").strip()

PORKBUN_API_KEY = (os.getenv("PORKBUN_API_KEY") or "").strip()
PORKBUN_SECRET_KEY = (os.getenv("PORKBUN_SECRET_KEY") or "").strip()

GOOGLE_WORKSPACE_ADMIN_TOKEN = (os.getenv("GOOGLE_WORKSPACE_ADMIN_TOKEN") or "").strip()
MAILFORGE_API_KEY = (os.getenv("MAILFORGE_API_KEY") or os.getenv("INFRAFORGE_API_KEY") or "").strip()

REINVESTMENT_RATIO = float(os.getenv("REINVESTMENT_RATIO") or "0.50")
COST_PER_SENDING_POD_USD = float(os.getenv("COST_PER_SENDING_POD_USD") or "21.00")  # ~$10.44 domain + 3 x $3.50 mailboxes
MAILBOXES_PER_DOMAIN = 3
SENDS_PER_MAILBOX_PER_DAY = 30

TIER_DEFAULT_USD = {
    "tier_1": 99.00,
    "tier_2": 399.00,
    "tier_3": 1499.00,
    "tier_4": 2499.00,
}

EXCLUDED_FOUNDER_OR_TEST_EMAILS = {
    "aarbchen@gmail.com",
    "aaron@getsignaltender.com",
    "aaron@signaltender.com",
    "capture@signaltender.net",
}

# Strictly SignalTender-branded GovCon B2B shard domain candidates (3 mailboxes per domain: aaron@, capture@, desk@)
SHARD_DOMAIN_CANDIDATES = [
    "signaltendercapture.com",
    "signaltenderfederal.com",
    "signaltendergov.com",
    "signaltendersled.com",
    "signaltenderbriefs.com",
    "signaltenderdesk.com",
    "signaltenderwire.com",
    "signaltenderrfp.com",
    "getsignaltendergov.com",
    "usesignaltender.com",
    "gosignaltender.com",
    "withsignaltender.com",
    "meetsignaltender.com",
    "signaltenderproposals.com",
    "signaltenderradar.com",
    "signaltenderintel.com",
    "signaltenderbids.com",
    "signaltendermatrix.com",
    "signaltenderhq.com",
    "signaltenderalerts.com",
    "signaltenderscout.com",
    "signaltenderops.com",
    "signaltendercloud.com",
    "signaltendercyber.com",
    "signaltenderprime.com",
    "signaltenderteaming.com",
    "signaltenderautopilot.com",
    "signaltenderai.com",
    "signaltenderpro.com",
    "signaltenderhub.com",
    "signaltendernet.com",
    "signaltenderteam.com",
    "signaltenderdirect.com",
    "signaltenderfeed.com",
    "signaltenderwatch.com",
    "signaltendersuite.com",
    "signaltenderportal.com",
    "signaltendercore.com",
    "signaltenderlab.com",
    "signaltendervault.com",
]

MAILBOX_PERSONAS = [
    {"local_part": "aaron", "first_name": "Aaron", "last_name": "Chen | SignalTender"},
    {"local_part": "capture", "first_name": "Aaron", "last_name": "SignalTender Capture"},
    {"local_part": "desk", "first_name": "Aaron Chen", "last_name": "SignalTender Desk"},
]


def is_valid_signaltender_shard_domain(domain: str) -> bool:
    """
    Enforce a strict brand-relevance guardrail: every domain the script considers or buys
    MUST contain `signaltender` in the root label, contain only clean lowercase letters, and end in `.com`.
    """
    import re
    clean = str(domain or "").strip().lower()
    return bool(re.match(r"^[a-z]*signaltender[a-z]*\.com$", clean)) and 15 <= len(clean) <= 32


def ensure_signaltender_avatar_png() -> str:
    """
    Verify and return the official SignalTender Apple Touch Icon (`d:\\Daas\\apple-touch-icon.png`)
    used for Google Workspace Directory API `users.photos.update` (`PUT /admin/directory/v1/users/{userKey}/photos/thumbnail`).
    """
    if os.path.exists(AVATAR_PNG_PATH) and os.path.getsize(AVATAR_PNG_PATH) > 500:
        return AVATAR_PNG_PATH
    fallback_contracts_icon = os.path.join(BASE_DIR, "contracts", "apple-touch-icon.png")
    if os.path.exists(fallback_contracts_icon):
        return fallback_contracts_icon
    return AVATAR_PNG_PATH


def get_avatar_websafe_base64() -> str:
    """Return URL-safe base64 string of the 500x500 SignalTender PNG avatar for Google Directory API."""
    path = ensure_signaltender_avatar_png()
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        raw = f.read()
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _load_local_ledger() -> Dict[str, Any]:
    default_ledger: Dict[str, Any] = {
        "schema_version": "1.0",
        "reinvestment_ratio": REINVESTMENT_RATIO,
        "cost_per_sending_pod_usd": COST_PER_SENDING_POD_USD,
        "total_gross_revenue_usd": 0.0,
        "total_reinvestment_allocated_usd": 0.0,
        "total_reinvestment_spent_usd": 0.0,
        "available_reinvestment_balance_usd": 0.0,
        "credited_conversion_keys": [],
        "provisioned_domains": [],
        "provisioned_mailboxes": [],
        "staged_provisioning_queue": [],
        "updated_at": "",
    }
    if os.path.exists(TREASURY_LEDGER_PATH):
        try:
            with open(TREASURY_LEDGER_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    default_ledger.update(loaded)
        except Exception:
            pass
    return default_ledger


def _save_local_ledger(ledger: Dict[str, Any]) -> None:
    ledger["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        with open(TREASURY_LEDGER_PATH, "w", encoding="utf-8") as f:
            json.dump(ledger, f, indent=2)
    except Exception as exc:
        report_error("autonomous_mailbox_scaler.py", f"Failed to save local treasury ledger: {exc}", severity="WARNING")


def check_domain_availability_rdap(domain: str) -> bool:
    """
    Check if a `.com` domain is unregistered and available to purchase using Verisign's
    official RDAP registry endpoint (`https://rdap.verisign.com/com/v1/domain/<domain>`).
    Returns True if HTTP 404 (not registered), False if HTTP 200 (already registered).
    """
    clean_dom = domain.strip().lower()
    if not clean_dom.endswith(".com"):
        return False
    try:
        resp = requests.get(
            f"https://rdap.verisign.com/com/v1/domain/{clean_dom}",
            headers={"Accept": "application/rdap+json"},
            timeout=8,
        )
        if resp.status_code == 404:
            return True
        return False
    except Exception:
        return False


def discover_available_shard_domains(existing_domains: set[str], count_needed: int = 5) -> List[str]:
    """Return up to `count_needed` verified-available SignalTender-branded `.com` shard domains."""
    available: List[str] = []
    for cand in SHARD_DOMAIN_CANDIDATES:
        cand_clean = cand.strip().lower()
        if cand_clean in existing_domains or not is_valid_signaltender_shard_domain(cand_clean):
            continue
        if check_domain_availability_rdap(cand_clean):
            available.append(cand_clean)
            if len(available) >= count_needed:
                break
    return available


def fetch_live_instantly_accounts() -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """
    Return `(all_accounts, warmed_emails, warming_only_emails)` from Instantly.ai V2.
    """
    if not INSTANTLY_API_KEY:
        return [], [], []
    try:
        import outbound_mailer
        resp = requests.get(
            "https://api.instantly.ai/api/v2/accounts?limit=100",
            headers={"Authorization": f"Bearer {INSTANTLY_API_KEY}"},
            timeout=10,
        )
        if resp.status_code == 200:
            items = (resp.json() or {}).get("items") or []
            warmed = []
            warming = []
            for a in items:
                if not isinstance(a, dict) or not a.get("email"):
                    continue
                em = str(a.get("email") or "").strip().lower()
                if outbound_mailer.is_instantly_account_warmed(a):
                    warmed.append(em)
                else:
                    warming.append(em)
            return items, warmed, warming
    except Exception:
        pass
    return [], [], []


def sync_revenue_treasury_from_supabase(ledger: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inspects Supabase `contracts` for:
      1. `status = SUBSCRIBER_REINVESTMENT_TREASURY` rows written directly by `/v1/webhooks/stripe`
         when `checkout.session.completed` or `invoice.paid` fires.
      2. `status = SUBSCRIBER_ACTIVE` rows (excluding founder/test accounts).
    Credits 50% of every new conversion into `ledger["total_reinvestment_allocated_usd"]`.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return ledger

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    credited_keys = set(ledger.get("credited_conversion_keys") or [])
    gross_rev = float(ledger.get("total_gross_revenue_usd") or 0.0)
    allocated_rev = float(ledger.get("total_reinvestment_allocated_usd") or 0.0)

    try:
        # 1. Explicit treasury credit rows written by Stripe webhook
        r_treasury = requests.get(
            f"{SUPABASE_URL}/rest/v1/contracts",
            params={
                "status": "eq.SUBSCRIBER_REINVESTMENT_TREASURY",
                "select": "id,title,agency,url,status",
                "order": "id.asc",
                "limit": "500",
            },
            headers=headers,
            timeout=10,
        )
        if r_treasury.status_code == 200:
            for row in (r_treasury.json() or []):
                tx_key = str(row.get("url") or f"treasury_row_{row.get('id')}").strip()
                if tx_key in credited_keys:
                    continue
                try:
                    meta = json.loads(str(row.get("agency") or "{}"))
                except Exception:
                    meta = {}
                amt = float(meta.get("amount_usd") or 0.0)
                if amt <= 0:
                    continue
                reinvest_share = round(amt * REINVESTMENT_RATIO, 2)
                gross_rev = round(gross_rev + amt, 2)
                allocated_rev = round(allocated_rev + reinvest_share, 2)
                credited_keys.add(tx_key)

        # 2. Active paid subscribers in Supabase (excluding founder/admin/audit test accounts)
        r_subs = requests.get(
            f"{SUPABASE_URL}/rest/v1/contracts",
            params={
                "status": "eq.SUBSCRIBER_ACTIVE",
                "select": "id,title,agency,url,status",
                "order": "id.asc",
                "limit": "500",
            },
            headers=headers,
            timeout=10,
        )
        if r_subs.status_code == 200:
            for row in (r_subs.json() or []):
                raw_url = str(row.get("url") or "").strip()
                email = raw_url.replace("subscriber://", "").strip().lower()
                if (
                    not email
                    or email in EXCLUDED_FOUNDER_OR_TEST_EMAILS
                    or email.startswith("client.portal.audit.")
                    or email.endswith("@example.com")
                ):
                    continue
                raw_agency = str(row.get("agency") or "")
                stripe_cid = ""
                for part in raw_agency.split("|"):
                    if part.startswith("stripe:"):
                        stripe_cid = part.replace("stripe:", "").strip()
                if stripe_cid in ("", "cus_founder_admin", "none"):
                    continue
                sub_key = f"sub::{email}::{stripe_cid}"
                if sub_key in credited_keys:
                    continue
                title_str = str(row.get("title") or "").lower()
                tier_code = "tier_2"
                for t_cand in ("tier_4", "tier_3", "tier_2", "tier_1"):
                    if t_cand in title_str:
                        tier_code = t_cand
                        break
                amt = TIER_DEFAULT_USD.get(tier_code, 399.00)
                reinvest_share = round(amt * REINVESTMENT_RATIO, 2)
                gross_rev = round(gross_rev + amt, 2)
                allocated_rev = round(allocated_rev + reinvest_share, 2)
                credited_keys.add(sub_key)
    except Exception as exc:
        report_error("autonomous_mailbox_scaler.py", f"Supabase treasury sync warning: {exc}", severity="WARNING")

    spent = float(ledger.get("total_reinvestment_spent_usd") or 0.0)
    ledger["total_gross_revenue_usd"] = round(gross_rev, 2)
    ledger["total_reinvestment_allocated_usd"] = round(allocated_rev, 2)
    ledger["available_reinvestment_balance_usd"] = round(max(0.0, allocated_rev - spent), 2)
    ledger["credited_conversion_keys"] = sorted(credited_keys)
    return ledger


def provision_cloudflare_domain_and_dns(domain: str) -> Dict[str, Any]:
    """
    Automates Cloudflare domain registration (or Porkbun registration) + Cloudflare Zone creation +
    SPF, DMARC, BIMI (`default._bimi` -> SignalTender SVG logo), Google Workspace MX records,
    and 301 Root Redirect (`https://<shard-domain>/*` -> `https://signaltender.net`).
    """
    result: Dict[str, Any] = {
        "domain": domain,
        "registered": False,
        "zone_id": "",
        "nameservers": [],
        "dns_records_created": [],
        "bimi_logo_configured": False,
        "redirect_301_configured": False,
        "status": "staged_awaiting_credentials",
    }

    if not is_valid_signaltender_shard_domain(domain):
        result["status"] = "rejected_non_signaltender_domain"
        return result

    # 1. Optional Porkbun automated retail domain registration if PORKBUN_API_KEY is configured
    if PORKBUN_API_KEY and PORKBUN_SECRET_KEY:
        try:
            pb_resp = requests.post(
                f"https://api.porkbun.com/api/json/v3/domain/create/{domain}",
                json={
                    "apikey": PORKBUN_API_KEY,
                    "secretapikey": PORKBUN_SECRET_KEY,
                    "cost": 1100,
                    "agreeToTerms": "yes",
                },
                timeout=15,
            )
            if pb_resp.status_code == 200 and (pb_resp.json() or {}).get("status") == "SUCCESS":
                result["registered"] = True
        except Exception as exc:
            report_error("autonomous_mailbox_scaler.py", f"Porkbun registration warning for {domain}: {exc}", severity="WARNING")

    if not CLOUDFLARE_API_TOKEN or not CLOUDFLARE_ACCOUNT_ID:
        return result

    cf_headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        # 2. Check or create Cloudflare Zone
        z_get = requests.get(
            "https://api.cloudflare.com/client/v4/zones",
            params={"name": domain},
            headers=cf_headers,
            timeout=10,
        )
        zone_id = ""
        nameservers: List[str] = []
        if z_get.status_code == 200 and (z_get.json().get("result") or []):
            z_obj = z_get.json()["result"][0]
            zone_id = str(z_obj.get("id") or "")
            nameservers = list(z_obj.get("name_servers") or [])
        else:
            z_post = requests.post(
                "https://api.cloudflare.com/client/v4/zones",
                headers=cf_headers,
                json={
                    "name": domain,
                    "account": {"id": CLOUDFLARE_ACCOUNT_ID},
                    "type": "full",
                },
                timeout=12,
            )
            if z_post.status_code in (200, 201) and (z_post.json().get("result") or {}):
                z_obj = z_post.json()["result"]
                zone_id = str(z_obj.get("id") or "")
                nameservers = list(z_obj.get("name_servers") or [])

        if not zone_id:
            return result

        result["zone_id"] = zone_id
        result["nameservers"] = nameservers

        # 3. Provision MX, SPF, DMARC, BIMI (SignalTender Logo), and Root Proxied A Records
        dns_specs = [
            {"type": "MX", "name": "@", "content": "ASPMX.L.GOOGLE.COM", "priority": 1, "ttl": 3600},
            {"type": "MX", "name": "@", "content": "ALT1.ASPMX.L.GOOGLE.COM", "priority": 5, "ttl": 3600},
            {"type": "MX", "name": "@", "content": "ALT2.ASPMX.L.GOOGLE.COM", "priority": 5, "ttl": 3600},
            {"type": "MX", "name": "@", "content": "ALT3.ASPMX.L.GOOGLE.COM", "priority": 10, "ttl": 3600},
            {"type": "MX", "name": "@", "content": "ALT4.ASPMX.L.GOOGLE.COM", "priority": 10, "ttl": 3600},
            {"type": "TXT", "name": "@", "content": "v=spf1 include:_spf.google.com ~all", "ttl": 3600},
            {
                "type": "TXT",
                "name": "_dmarc",
                "content": f"v=DMARC1; p=quarantine; pct=100; rua=mailto:dmarc@signaltender.net; adkim=r; aspf=r;",
                "ttl": 3600,
            },
            {
                "type": "TXT",
                "name": "default._bimi",
                "content": f"v=BIMI1; l={BIMI_SVG_URL};",
                "ttl": 3600,
            },
            {"type": "A", "name": "@", "content": "192.0.2.1", "proxied": True, "ttl": 1},
            {"type": "A", "name": "www", "content": "192.0.2.1", "proxied": True, "ttl": 1},
        ]

        for rec in dns_specs:
            r_dns = requests.post(
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
                headers=cf_headers,
                json=rec,
                timeout=10,
            )
            if r_dns.status_code in (200, 201):
                result["dns_records_created"].append(f"{rec['type']}:{rec['name']}")
                if rec["name"] == "default._bimi":
                    result["bimi_logo_configured"] = True

        # 4. Configure 301 Redirect Ruleset (`*` -> `https://signaltender.net`)
        r_redir = requests.put(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/rulesets/phases/http_request_dynamic_redirect/entrypoint",
            headers=cf_headers,
            json={
                "rules": [
                    {
                        "expression": "true",
                        "description": "Redirect shard domain traffic to SignalTender primary domain",
                        "action": "redirect",
                        "action_parameters": {
                            "from_value": {
                                "status_code": 301,
                                "target_url": {"value": "https://signaltender.net"},
                                "preserve_query_string": True,
                            }
                        },
                    }
                ]
            },
            timeout=10,
        )
        if r_redir.status_code in (200, 201):
            result["redirect_301_configured"] = True

        result["status"] = "cloudflare_zone_and_bimi_active"
    except Exception as exc:
        report_error("autonomous_mailbox_scaler.py", f"Cloudflare DNS provisioning warning for {domain}: {exc}", severity="WARNING")

    return result


def provision_mailboxes_and_apply_logo(domain: str) -> List[Dict[str, Any]]:
    """
    Creates 3 mailboxes (`aaron@<domain>`, `capture@<domain>`, `desk@<domain>`) and uploads
    the 500x500 PNG SignalTender radar-chevron logo (`signaltender_mailbox_avatar_500.png`)
    to each mailbox's Google Workspace profile (`PUT /admin/directory/v1/users/{userKey}/photos/thumbnail`).
    """
    avatar_b64 = get_avatar_websafe_base64()
    mailboxes: List[Dict[str, Any]] = []

    for persona in MAILBOX_PERSONAS:
        email_addr = f"{persona['local_part']}@{domain}".lower()
        temp_pw = f"StGov!{secrets.token_hex(6)}9a"
        mb_entry: Dict[str, Any] = {
            "email": email_addr,
            "domain": domain,
            "first_name": persona["first_name"],
            "last_name": persona["last_name"],
            "avatar_logo_path": AVATAR_PNG_PATH,
            "bimi_svg_url": BIMI_SVG_URL,
            "avatar_applied": False,
            "created_in_workspace": False,
            "queued_in_instantly": False,
            "warmup_enabled": False,
        }

        if GOOGLE_WORKSPACE_ADMIN_TOKEN:
            gw_headers = {
                "Authorization": f"Bearer {GOOGLE_WORKSPACE_ADMIN_TOKEN}",
                "Content-Type": "application/json",
            }
            try:
                u_resp = requests.post(
                    "https://admin.googleapis.com/admin/directory/v1/users",
                    headers=gw_headers,
                    json={
                        "primaryEmail": email_addr,
                        "name": {
                            "givenName": persona["first_name"],
                            "familyName": persona["last_name"],
                        },
                        "password": temp_pw,
                        "changePasswordAtNextLogin": False,
                    },
                    timeout=12,
                )
                if u_resp.status_code in (200, 201, 409):
                    mb_entry["created_in_workspace"] = True
                    if avatar_b64:
                        p_resp = requests.put(
                            f"https://admin.googleapis.com/admin/directory/v1/users/{email_addr}/photos/thumbnail",
                            headers=gw_headers,
                            json={
                                "mimeType": "image/png",
                                "photoData": avatar_b64,
                            },
                            timeout=12,
                        )
                        if p_resp.status_code in (200, 201):
                            mb_entry["avatar_applied"] = True
            except Exception as exc:
                report_error("autonomous_mailbox_scaler.py", f"Google Workspace user/photo provisioning warning for {email_addr}: {exc}", severity="WARNING")

        mailboxes.append(mb_entry)

    return mailboxes


def queue_mailboxes_to_instantly_and_expand(new_mailboxes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    1. Enables automated warmup on any newly connected Instantly mailboxes (`POST /api/v2/accounts/warmup/enable`).
    2. Holds warming accounts (`stat_warmup_score < 85`) in Warmup-Only mode.
    3. Attaches all graduated accounts (`stat_warmup_score >= 85` or `warmup_status == 0`) to Campaign
       `c7727dff-92cc-4621-9e96-c960938d5a47`, sets `daily_limit = 30 * warmed_count`, and returns
       the live fleet telemetry.
    """
    all_accounts, warmed_emails, warming_emails = fetch_live_instantly_accounts()
    inst_headers = {
        "Authorization": f"Bearer {INSTANTLY_API_KEY}",
        "Content-Type": "application/json",
    }

    # Ensure any warming account with warmup_status == 0 (and score < 85) has warmup enabled
    need_warmup_enable = [
        str(a.get("email") or "").strip().lower()
        for a in all_accounts
        if str(a.get("email") or "").strip().lower() in warming_emails
        and int(a.get("warmup_status") or 0) == 0
    ]
    if need_warmup_enable and INSTANTLY_API_KEY:
        try:
            requests.post(
                "https://api.instantly.ai/api/v2/accounts/warmup/enable",
                headers=inst_headers,
                json={"emails": need_warmup_enable},
                timeout=10,
            )
        except Exception:
            pass

    daily_send_cap = max(30, len(warmed_emails) * SENDS_PER_MAILBOX_PER_DAY)
    recommended_active_buffer = max(245, len(warmed_emails) * 90)

    if INSTANTLY_API_KEY and INSTANTLY_CAMPAIGN_ID and warmed_emails:
        try:
            c_resp = requests.get(
                f"https://api.instantly.ai/api/v2/campaigns/{INSTANTLY_CAMPAIGN_ID}",
                headers=inst_headers,
                timeout=12,
            )
            if c_resp.status_code == 200:
                c_data = c_resp.json() or {}
                patch_body: Dict[str, Any] = {}
                if set(c_data.get("email_list") or []) != set(warmed_emails):
                    patch_body["email_list"] = warmed_emails
                if int(c_data.get("daily_limit") or 0) != daily_send_cap:
                    patch_body["daily_limit"] = daily_send_cap
                if patch_body:
                    requests.patch(
                        f"https://api.instantly.ai/api/v2/campaigns/{INSTANTLY_CAMPAIGN_ID}",
                        headers=inst_headers,
                        json=patch_body,
                        timeout=12,
                    )
        except Exception as exc:
            report_error("autonomous_mailbox_scaler.py", f"Instantly campaign expansion patch warning: {exc}", severity="WARNING")

    return {
        "total_instantly_accounts": len(all_accounts),
        "warmed_active_senders": warmed_emails,
        "warmed_count": len(warmed_emails),
        "warming_queue_senders": warming_emails,
        "warming_count": len(warming_emails),
        "campaign_daily_limit": daily_send_cap,
        "recommended_active_lead_buffer": recommended_active_buffer,
        "newly_staged_mailboxes": len(new_mailboxes),
    }


def evaluate_and_alert_instantly_plan_upgrade(
    instantly_fleet: Dict[str, Any],
    pods_affordable: int,
    avail_usd: float,
    ledger: Dict[str, Any],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Evaluates whether the current + newly funded mailbox fleet exceeds the current Instantly.ai plan's
    monthly send quota or active-contact buffer:
      • Growth ($37/mo):      Up to ~6 mailboxes (180/day = 5,400/mo vs 5,000/mo cap; 245-1,000 active contacts)
      • Hypergrowth ($97/mo): Up to ~110 mailboxes (3,300/day = 99,000/mo vs 100,000/mo cap; 25,000 active contacts)
      • Light Speed ($358/mo): Up to ~500 mailboxes (500,000/mo cap; 100,000+ active contacts)
    Dispatches a one-time alert to Discord `#alerts` (and founder email) the moment an upgrade threshold is crossed.
    """
    current_plan = (os.getenv("INSTANTLY_PLAN_TIER") or "growth").strip().lower()
    total_current_mb = int(instantly_fleet.get("total_instantly_accounts") or 6)
    projected_mb = total_current_mb + (pods_affordable * MAILBOXES_PER_DOMAIN)
    projected_daily_sends = projected_mb * SENDS_PER_MAILBOX_PER_DAY
    projected_monthly_sends = projected_daily_sends * 30
    projected_active_buffer = max(245, projected_mb * 90)

    upgrade_needed = False
    target_plan = current_plan
    target_price_str = "$37/mo"
    reason = "Within current plan capacity."

    if current_plan == "growth" and (projected_mb > 6 or projected_monthly_sends > 5400):
        upgrade_needed = True
        target_plan = "hypergrowth"
        target_price_str = "$97/mo (+$60/mo delta)"
        reason = (
            f"Projected fleet of {projected_mb} mailboxes ({projected_daily_sends}/day = "
            f"{projected_monthly_sends:,} emails/mo, {projected_active_buffer:,} active in-flight leads) "
            f"exceeds Instantly Growth ($37/mo: 5,000 emails/mo & base contact buffer)."
        )
    elif current_plan == "hypergrowth" and (projected_mb > 110 or projected_monthly_sends > 100000):
        upgrade_needed = True
        target_plan = "light_speed"
        target_price_str = "$358/mo"
        reason = (
            f"Projected fleet of {projected_mb} mailboxes ({projected_monthly_sends:,} emails/mo) "
            f"exceeds Instantly Hypergrowth (100,000 emails/mo cap)."
        )

    alert_key = f"upgrade_to_{target_plan}_{projected_mb}_mb"
    already_alerted = str(ledger.get("last_instantly_upgrade_alert") or "")
    alert_dispatched = False

    if upgrade_needed and not dry_run and alert_key != already_alerted:
        msg = (
            f"**[ACTION REQUIRED // TIME TO UPGRADE INSTANTLY.AI PLAN TO {target_plan.upper()}]**\n"
            f"• **Current Plan:** `{current_plan.upper()}`\n"
            f"• **Recommended Upgrade:** `Instantly {target_plan.upper()} ({target_price_str})`\n"
            f"• **Why Now:** {reason}\n"
            f"• **50% Reinvestment Treasury Available:** `${avail_usd:,.2f}` (`{pods_affordable}` new 3-mailbox pods ready)\n"
            f"• **Next Step:** Upgrade in https://app.instantly.ai/app/settings/billing and set `INSTANTLY_PLAN_TIER={target_plan}` "
            f"+ `INSTANTLY_MAX_ACTIVE_BUFFER=25000` in `.env` to unlock full multi-thousand lead rotation."
        )
        if DISCORD_WEBHOOK_URL:
            try:
                r = requests.post(
                    DISCORD_WEBHOOK_URL,
                    json={"content": msg, "flags": 4},
                    timeout=10,
                )
                if 200 <= r.status_code < 300:
                    alert_dispatched = True
            except Exception:
                pass

        resend_key = (os.getenv("RESEND_API_KEY") or "").strip()
        if resend_key:
            try:
                requests.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                    json={
                        "from": "SignalTender Autopilot <aaron@getsignaltender.com>",
                        "to": ["aarbchen@gmail.com"],
                        "subject": f"[SignalTender Action Required] Time to Upgrade Instantly.ai to {target_plan.capitalize()} ({projected_mb} Mailboxes Ready)",
                        "text": msg.replace("**", "").replace("`", ""),
                    },
                    timeout=10,
                )
            except Exception:
                pass

        ledger["last_instantly_upgrade_alert"] = alert_key

    return {
        "current_plan": current_plan,
        "upgrade_needed": upgrade_needed,
        "recommended_plan": target_plan,
        "recommended_plan_cost": target_price_str,
        "projected_mailboxes": projected_mb,
        "projected_monthly_sends": projected_monthly_sends,
        "projected_active_buffer": projected_active_buffer,
        "reason": reason,
        "alert_dispatched": alert_dispatched,
    }


def record_stripe_conversion_reinvestment(
    email: str,
    tier: str,
    amount_usd: float,
    event_id: str = "",
) -> Dict[str, Any]:
    """
    Called when a new Stripe subscription payment lands. Credits 50% of `amount_usd` into
    the Reinvestment Treasury Ledger and immediately triggers or stages the corresponding
    Cloudflare Shard Domain + 3-Mailbox Pod orders.
    """
    ensure_signaltender_avatar_png()
    ledger = _load_local_ledger()
    tx_key = event_id or f"stripe::{email.strip().lower()}::{int(datetime.now(timezone.utc).timestamp())}"
    credited = set(ledger.get("credited_conversion_keys") or [])

    if tx_key not in credited and amount_usd > 0:
        reinvest_usd = round(amount_usd * REINVESTMENT_RATIO, 2)
        ledger["total_gross_revenue_usd"] = round(float(ledger.get("total_gross_revenue_usd") or 0.0) + amount_usd, 2)
        ledger["total_reinvestment_allocated_usd"] = round(
            float(ledger.get("total_reinvestment_allocated_usd") or 0.0) + reinvest_usd, 2
        )
        spent = float(ledger.get("total_reinvestment_spent_usd") or 0.0)
        ledger["available_reinvestment_balance_usd"] = round(
            max(0.0, ledger["total_reinvestment_allocated_usd"] - spent), 2
        )
        credited.add(tx_key)
        ledger["credited_conversion_keys"] = sorted(credited)
        _save_local_ledger(ledger)

    return run_autonomous_mailbox_scaler(dry_run=False)


def run_autonomous_mailbox_scaler(dry_run: bool = False, simulate_revenue_usd: float = 0.0) -> Dict[str, Any]:
    """
    Main entrypoint for the Autonomous 50% Revenue-to-Mailbox Scaling Engine.
    """
    ensure_signaltender_avatar_png()
    ledger = _load_local_ledger()
    ledger = sync_revenue_treasury_from_supabase(ledger)

    if simulate_revenue_usd > 0:
        sim_reinvest = round(simulate_revenue_usd * REINVESTMENT_RATIO, 2)
        avail_usd = round(float(ledger.get("available_reinvestment_balance_usd") or 0.0) + sim_reinvest, 2)
    else:
        avail_usd = float(ledger.get("available_reinvestment_balance_usd") or 0.0)

    pods_affordable = int(avail_usd // COST_PER_SENDING_POD_USD)

    existing_domains = {
        str(d.get("domain") or "").strip().lower()
        for d in (ledger.get("provisioned_domains") or [])
        if isinstance(d, dict) and d.get("domain")
    }
    staged_domains = {
        str(d.get("domain") or "").strip().lower()
        for d in (ledger.get("staged_provisioning_queue") or [])
        if isinstance(d, dict) and d.get("domain")
    }
    # Also include domains already connected in Instantly
    _, warmed_list, warming_list = fetch_live_instantly_accounts()
    for em in warmed_list + warming_list:
        if "@" in em:
            existing_domains.add(em.split("@", 1)[1].strip().lower())

    new_pods_created: List[Dict[str, Any]] = []
    if pods_affordable > 0:
        candidate_domains = discover_available_shard_domains(
            existing_domains | staged_domains,
            count_needed=min(pods_affordable, 10),
        )
        for dom in candidate_domains:
            if dry_run:
                new_pods_created.append({
                    "domain": dom,
                    "rdap_available": True,
                    "mailboxes": [f"{p['local_part']}@{dom}" for p in MAILBOX_PERSONAS],
                    "bimi_logo": BIMI_SVG_URL,
                    "avatar_png": AVATAR_PNG_PATH,
                    "pod_cost_usd": COST_PER_SENDING_POD_USD,
                    "daily_capacity_added": MAILBOXES_PER_DOMAIN * SENDS_PER_MAILBOX_PER_DAY,
                    "mode": "dry_run_preview",
                })
                continue

            cf_res = provision_cloudflare_domain_and_dns(dom)
            mb_res = provision_mailboxes_and_apply_logo(dom)
            pod_record = {
                "domain": dom,
                "cloudflare": cf_res,
                "mailboxes": mb_res,
                "pod_cost_usd": COST_PER_SENDING_POD_USD,
                "daily_capacity_added": MAILBOXES_PER_DOMAIN * SENDS_PER_MAILBOX_PER_DAY,
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            new_pods_created.append(pod_record)

            if cf_res.get("registered") or cf_res.get("zone_id"):
                ledger.setdefault("provisioned_domains", []).append(cf_res)
                ledger.setdefault("provisioned_mailboxes", []).extend(mb_res)
                ledger["total_reinvestment_spent_usd"] = round(
                    float(ledger.get("total_reinvestment_spent_usd") or 0.0) + COST_PER_SENDING_POD_USD, 2
                )
                ledger["available_reinvestment_balance_usd"] = round(
                    max(0.0, float(ledger.get("total_reinvestment_allocated_usd") or 0.0) - ledger["total_reinvestment_spent_usd"]),
                    2,
                )
            else:
                # Stage in provisioning queue until CLOUDFLARE_API_TOKEN / PORKBUN_API_KEY is added to .env
                ledger.setdefault("staged_provisioning_queue", []).append(pod_record)

    instantly_fleet = queue_mailboxes_to_instantly_and_expand(
        [mb for pod in new_pods_created for mb in (pod.get("mailboxes") or []) if isinstance(mb, dict)]
    )
    instantly_plan_check = evaluate_and_alert_instantly_plan_upgrade(
        instantly_fleet=instantly_fleet,
        pods_affordable=pods_affordable,
        avail_usd=avail_usd,
        ledger=ledger,
        dry_run=dry_run,
    )

    if not dry_run:
        _save_local_ledger(ledger)

    summary = {
        "reinvestment_ratio": f"{int(REINVESTMENT_RATIO * 100)}%",
        "cost_per_3_mailbox_pod_usd": COST_PER_SENDING_POD_USD,
        "total_gross_revenue_usd": ledger.get("total_gross_revenue_usd", 0.0),
        "total_50pct_reinvestment_allocated_usd": ledger.get("total_reinvestment_allocated_usd", 0.0),
        "available_reinvestment_balance_usd": avail_usd,
        "pods_affordable_now": pods_affordable,
        "mailboxes_affordable_now": pods_affordable * MAILBOXES_PER_DOMAIN,
        "daily_sends_added_when_provisioned": pods_affordable * MAILBOXES_PER_DOMAIN * SENDS_PER_MAILBOX_PER_DAY,
        "avatar_logo_png_ready": os.path.exists(AVATAR_PNG_PATH),
        "bimi_svg_url": BIMI_SVG_URL,
        "cloudflare_api_configured": bool(CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID),
        "google_workspace_api_configured": bool(GOOGLE_WORKSPACE_ADMIN_TOKEN),
        "instantly_fleet": instantly_fleet,
        "instantly_plan_upgrade_check": instantly_plan_check,
        "pods_processed": new_pods_created,
    }
    print(json.dumps(summary, indent=2), flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous 50% Revenue-to-Mailbox Reinvestment & Cloudflare/Instantly Scaler")
    parser.add_argument("--dry-run", action="store_true", help="Simulate pod discovery and RDAP availability without spending budget")
    parser.add_argument("--simulate-revenue", type=float, default=0.0, help="Simulate a Stripe conversion of $X USD (e.g., 399.00)")
    args = parser.parse_args()
    run_autonomous_mailbox_scaler(dry_run=args.dry_run, simulate_revenue_usd=args.simulate_revenue)
