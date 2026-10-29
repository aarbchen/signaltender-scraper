from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()
"""
SignalTender — Automated X (Twitter) API v2 RFP Broadcaster (`x_autoposter.py`)
Publishes high-signal open Federal (SAM.gov), Municipal (DemandStar), and 26-State SLED
IT, Cybersecurity, Cloud, and AI solicitations directly to the official SignalTender X account
via `POST https://api.x.com/2/tweets` using zero-dependency RFC 5849 OAuth 1.0a HMAC-SHA1 signing.
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import urllib.parse
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv(dotenv_path=r"D:\Data API Ecosystem\.env")
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ERROR_LOG_PATH = os.path.join(BASE_DIR, "error_log.txt")
POSTED_CACHE_PATH = os.path.join(BASE_DIR, "posted_x_rfps.json")
READY_QUEUE_PATH = os.path.join(BASE_DIR, "x_ready_posts.json")
INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")

SITE_BASE_URL = os.getenv("SIGNALTENDER_SITE_URL", "https://signaltender.net").rstrip("/")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

X_TWEETS_ENDPOINT = "https://api.x.com/2/tweets"

JURISDICTION_SHORT_TAGS = {
    "federal": "FEDERAL // SAM.GOV",
    "texas": "TEXAS // ESBD",
    "virginia": "VIRGINIA // eVA",
    "california": "CALIFORNIA // CAL ePROCURE",
    "florida": "FLORIDA // MFMP VIP",
    "maryland": "MARYLAND // eMMA",
    "illinois": "ILLINOIS // BIDBUY",
    "pennsylvania": "PENNSYLVANIA // eMARKETPLACE",
    "ohio": "OHIO // OHIOBUYS",
    "georgia": "GEORGIA // GPR",
    "north_carolina": "NORTH CAROLINA // NC eVP",
    "new_york": "NEW YORK // NYSCR & NYC",
    "massachusetts": "MASSACHUSETTS // COMMBUYS",
    "new_jersey": "NEW JERSEY // NJSTART",
    "washington": "WASHINGTON // WEBS & WATECH",
    "michigan": "MICHIGAN // SIGMA VSS & DTMB",
    "colorado": "COLORADO // VSS & OIT",
    "arizona": "ARIZONA // APP & ADOA-ASET",
    "minnesota": "MINNESOTA // SWIFT & MNIT",
    "tennessee": "TENNESSEE // EDISON CPO & STS",
    "indiana": "INDIANA // IDOA & IOT",
    "missouri": "MISSOURI // MISSOURIBUYS & OA-ITSD",
    "wisconsin": "WISCONSIN // eSUPPLIER & DOA DET",
    "south_carolina": "SOUTH CAROLINA // SCBO & SFAA",
    "oregon": "OREGON // OREGONBUYS & DAS EIS",
    "connecticut": "CONNECTICUT // CTSOURCE & DAS BITS",
    "utah": "UTAH // U3P SCIQUEST & DTS",
    "municipal": "MUNICIPAL // DEMANDSTAR",
}


def log_error(msg: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{timestamp}] [X Autoposter] {msg}\n"
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def send_discord_alert(message: str) -> None:
    report_error("x_autoposter.py", str(message))
    log_error(message)
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": f"**[ALERT] X Autoposter:**\n{message}", "flags": 4},
            timeout=10,
        )
    except Exception as exc:
        log_error(f"Failed to send Discord alert: {exc}")


def _pct_encode(val: str) -> str:
    return urllib.parse.quote(str(val), safe="-._~")


def build_oauth1_header(
    method: str,
    url: str,
    api_key: str,
    api_secret: str,
    access_token: str,
    access_token_secret: str,
) -> str:
    """
    Constructs an RFC 5849 OAuth 1.0a HMAC-SHA1 Authorization header for X API v2 JSON POST requests.
    """
    oauth_params = {
        "oauth_consumer_key": api_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }

    sorted_params = sorted(oauth_params.items(), key=lambda kv: (_pct_encode(kv[0]), _pct_encode(kv[1])))
    param_str = "&".join(f"{_pct_encode(k)}={_pct_encode(v)}" for k, v in sorted_params)

    base_elems = [
        method.upper(),
        _pct_encode(url),
        _pct_encode(param_str),
    ]
    signature_base_string = "&".join(base_elems)

    signing_key = f"{_pct_encode(api_secret)}&{_pct_encode(access_token_secret)}"
    hashed = hmac.new(
        signing_key.encode("utf-8"),
        signature_base_string.encode("utf-8"),
        hashlib.sha1,
    )
    oauth_signature = base64.b64encode(hashed.digest()).decode("utf-8")
    oauth_params["oauth_signature"] = oauth_signature

    header_parts = [f'{_pct_encode(k)}="{_pct_encode(v)}"' for k, v in sorted(oauth_params.items())]
    return "OAuth " + ", ".join(header_parts)


def get_x_credentials() -> dict[str, str]:
    return {
        "api_key": (os.getenv("X_API_KEY") or os.getenv("TWITTER_API_KEY") or "").strip(),
        "api_secret": (os.getenv("X_API_SECRET") or os.getenv("TWITTER_API_SECRET") or "").strip(),
        "access_token": (os.getenv("X_ACCESS_TOKEN") or os.getenv("TWITTER_ACCESS_TOKEN") or "").strip(),
        "access_token_secret": (
            os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv("TWITTER_ACCESS_TOKEN_SECRET") or ""
        ).strip(),
    }


def load_posted_cache() -> dict:
    if not os.path.exists(POSTED_CACHE_PATH):
        return {"posted_slugs": [], "history": []}
    try:
        with open(POSTED_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("posted_slugs", [])
                data.setdefault("history", [])
                return data
    except Exception:
        pass
    return {"posted_slugs": [], "history": []}


def save_posted_cache(cache: dict) -> None:
    try:
        with open(POSTED_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        log_error(f"Failed to save posted_x_rfps.json: {exc}")


def load_verified_contracts() -> list[dict]:
    """
    Loads the pre-vetted, deduplicated open IT/Cyber solicitations embedded in `index.html`
    by `pseo_generator.py` so every candidate is guaranteed to have a live static
    `/contracts/rfp/<slug>.html` dossier page and zero sole-source / NSN hardware noise.
    """
    if not os.path.exists(INDEX_HTML_PATH):
        return []
    try:
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            html_txt = f.read()
        m = re.search(
            r"window\.SIGNALTENDER_CONTRACTS\s*=\s*(\[.*?\]);\s*window\.SIGNALTENDER_JURISDICTIONS",
            html_txt,
            flags=re.S,
        )
        if not m:
            return []
        contracts = json.loads(m.group(1))
        if not isinstance(contracts, list):
            return []
        valid = []
        for c in contracts:
            slug = str(c.get("slug") or "").strip()
            title = str(c.get("clean_title") or "").strip()
            if not slug or not title:
                continue
            low = title.lower()
            if "sole source" in low or "intent to sole source" in low or re.match(r"^\d{2}--", low):
                continue
            valid.append(c)
        return valid
    except Exception as exc:
        log_error(f"Error loading verified contracts from index.html: {exc}")
        return []


def format_rfp_x_post(contract: dict) -> str:
    """
    Formats a high-signal X post for an open IT/Cyber solicitation.
    X wraps all HTTP/HTTPS URLs via t.co to 23 characters, so weighted tweet length
    is `len(text_without_url) + 23 <= 275`.
    """
    j_key = str(contract.get("jurisdiction") or "federal").lower()
    j_label = JURISDICTION_SHORT_TAGS.get(j_key, "GOVCON // LIVE WIRE")
    clean_title = re.sub(r"^\[[A-Z]{2,4}\]\s*", "", str(contract.get("clean_title") or "").strip())
    due_str = str(contract.get("due_str") or "Open").strip()
    naics_str = str(contract.get("naics_display") or "541512").split("/")[0].strip()
    slug = str(contract.get("slug") or "").strip()
    dossier_url = f"{SITE_BASE_URL}/contracts/rfp/{slug}.html"

    header = f"[LIVE RFP // {j_label}]\n"
    meta_prefix = f"\nNAICS {naics_str} | Due: {due_str}\nDossier: "
    meta_suffix = "\n#GovCon #RFP #Cybersecurity"

    # X counts `dossier_url` as 23 chars via t.co
    fixed_weighted_len = len(header) + len(meta_prefix) + 23 + len(meta_suffix)
    max_title_len = 272 - fixed_weighted_len
    if len(clean_title) > max_title_len:
        cut = clean_title[: max(30, max_title_len - 3)]
        if " " in cut:
            cut = cut.rsplit(" ", 1)[0]
        clean_title = cut.rstrip(" ,;:-") + "..."

    return f"{header}{clean_title}{meta_prefix}{dossier_url}{meta_suffix}"


def post_tweet_v2(text: str) -> tuple[bool, dict]:
    creds = get_x_credentials()
    if not all(creds.values()):
        return False, {"error": "Missing X API OAuth 1.0a credentials in .env"}

    auth_header = build_oauth1_header(
        method="POST",
        url=X_TWEETS_ENDPOINT,
        api_key=creds["api_key"],
        api_secret=creds["api_secret"],
        access_token=creds["access_token"],
        access_token_secret=creds["access_token_secret"],
    )
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "SignalTender-Autoposter/1.0",
    }
    try:
        resp = requests.post(X_TWEETS_ENDPOINT, json={"text": text}, headers=headers, timeout=20)
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text[:400]}
        if resp.status_code in (200, 201):
            return True, body
        return False, {"status_code": resp.status_code, "body": body}
    except Exception as exc:
        return False, {"error": str(exc)}


def run_x_autoposter(max_posts: int = 1, dry_run: bool = False) -> dict:
    """
    Selects up to `max_posts` unposted high-signal RFPs across diverse jurisdictions
    and publishes them to X via `POST /2/tweets`.
    """
    contracts = load_verified_contracts()
    if not contracts:
        print("[X Autoposter] No verified contracts found in index.html.", flush=True)
        return {"status": "no_contracts", "posted": 0}

    cache = load_posted_cache()
    posted_set = set(cache.get("posted_slugs", []))

    unposted = [c for c in contracts if c.get("slug") not in posted_set]
    if not unposted:
        # Reset rotation once all active contracts have been cycled
        posted_set.clear()
        cache["posted_slugs"] = []
        unposted = contracts[:]

    # Prioritize rotating jurisdiction diversity relative to the last posted jurisdiction
    last_j = cache["history"][-1].get("jurisdiction") if cache.get("history") else None
    preferred = [c for c in unposted if c.get("jurisdiction") != last_j] or unposted
    selected = preferred[: max(1, max_posts)]

    # Always write a fresh 10-post rotating queue to x_ready_posts.json
    ready_queue = []
    seen_j = set()
    for c in unposted:
        jk = c.get("jurisdiction", "federal")
        if jk not in seen_j or len(ready_queue) >= 8:
            seen_j.add(jk)
            ready_queue.append(
                {
                    "slug": c.get("slug"),
                    "jurisdiction": jk,
                    "title": c.get("clean_title"),
                    "due_date": c.get("due_str"),
                    "dossier_url": f"{SITE_BASE_URL}/contracts/rfp/{c.get('slug')}.html",
                    "tweet_text": format_rfp_x_post(c),
                }
            )
        if len(ready_queue) >= 10:
            break
    try:
        with open(READY_QUEUE_PATH, "w", encoding="utf-8") as qf:
            json.dump(
                {
                    "account": "@SignalTenderX",
                    "profile_url": "https://x.com/SignalTenderX",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "posts": ready_queue,
                },
                qf,
                indent=2,
                ensure_ascii=False,
            )
    except Exception:
        pass

    creds = get_x_credentials()
    has_creds = all(creds.values())

    if not has_creds and not dry_run:
        print(
            "[X Autoposter] X API credentials (X_API_KEY / X_ACCESS_TOKEN) not yet set in .env; saved ready queue to x_ready_posts.json.",
            flush=True,
        )
        return {"status": "queued_no_credentials", "posted": 0, "queued": len(ready_queue)}

    posted_count = 0
    results = []
    for item in selected:
        tweet_text = format_rfp_x_post(item)
        if dry_run:
            print(f"[X Autoposter DRY-RUN] ({len(tweet_text)} chars):\n{tweet_text}\n", flush=True)
            results.append({"slug": item["slug"], "text": tweet_text, "dry_run": True})
            continue

        ok, resp_data = post_tweet_v2(tweet_text)
        if ok:
            tweet_id = (resp_data.get("data") or {}).get("id", "")
            posted_count += 1
            cache["posted_slugs"].append(item["slug"])
            cache["history"].append(
                {
                    "slug": item["slug"],
                    "jurisdiction": item.get("jurisdiction"),
                    "tweet_id": tweet_id,
                    "posted_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            save_posted_cache(cache)
            print(f"[X Autoposter] Published RFP to X (tweet_id={tweet_id}): {item['slug']}", flush=True)
            results.append({"slug": item["slug"], "tweet_id": tweet_id})
        else:
            status_code = resp_data.get("status_code") if isinstance(resp_data, dict) else None
            if status_code in (402, 403, 429):
                print(
                    f"[X Autoposter] X API returned HTTP {status_code} (quota/credits gate); saved {len(ready_queue)} ready posts to x_ready_posts.json.",
                    flush=True,
                )
                return {"status": f"queued_http_{status_code}", "posted": 0, "queued": len(ready_queue)}
            err_msg = f"X API post failed for {item['slug']}: {resp_data}"
            log_error(err_msg)
            print(f"[X Autoposter] {err_msg}", flush=True)
            results.append({"slug": item["slug"], "error": resp_data})
            break

    return {"status": "ok" if posted_count > 0 or dry_run else "error", "posted": posted_count, "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SignalTender Automated X (Twitter) RFP Broadcaster")
    parser.add_argument("--max-posts", type=int, default=1, help="Maximum RFPs to post per run (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Format and preview X post without calling API")
    args = parser.parse_args()
    run_x_autoposter(max_posts=args.max_posts, dry_run=args.dry_run)
