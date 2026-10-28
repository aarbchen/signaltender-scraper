"""
Headless RapidAPI Studio & Render Proxy-Secret Publisher (`rapidapi_headless_publisher.py`).
Executes 100% in Python:
  1. Generates or locates the 500x500 PNG API logo (`api{N}_*_logo.png`).
  2. Authenticates to `https://rapidapi.com/gateway/graphql` using `RAPIDAPI_STUDIO_COOKIE` in `.env`
     with `"x-rapidapi-Rolling-Key": "true"` and automatically persists rolled `Set-Cookie` headers
     (`connect.sid`, `jwt_auth`, `_csrf`) back to `d:\\Daas\\.env` and `.rapidapi_session.json`
     so the rolling session never expires.
  3. Creates the standalone API project in Rapid Studio (`createApisFromRapidOas` from
     `rapidapi_api{N}_openapi.json`), uploads its 500x500 PNG logo and Markdown README (`updateApi`),
     configures `/v1/health` healthcheck (`upsertApiHealthcheck`), and configures all 4 pricing plans
     (`BASIC $0`, `PRO $49`, `ULTRA $149` recommended, `MEGA $399`).
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

# Live public SignalTender RapidAPI storefronts by category (already authorized on Render)
PUBLIC_MIRROR_TARGETS: Dict[str, Dict[str, str]] = {
    "capture": {
        "api_id": "api_4c6bdfeb-1400-4466-a1f7-87fcdeb819d4",
        "host": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com",
        "hub_url": "https://rapidapi.com/aarbchen/api/ai-bid-no-bid-capability-matcher-api",
    },
    "proposal": {
        "api_id": "api_71e5078f-2916-4f86-9f67-861681c2b2f5",
        "host": "rfp-compliance-matrix-proposal-outline-api.p.rapidapi.com",
        "hub_url": "https://rapidapi.com/aarbchen/api/rfp-compliance-matrix-proposal-outline-api",
    },
    "security": {
        "api_id": "api_049302a8-19c6-4550-a7d0-94646552f59f",
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

# Explicit mirror routing for specific API numbers when a dedicated public suite fits best
API_NUM_MIRROR_OVERRIDE: Dict[int, str] = {
    21: "capture",
    22: "compliance",
    23: "proposal",
    24: "security",
    25: "compliance",
}


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


def _persist_rolled_cookies(s: requests.Session) -> None:
    """Merge any Set-Cookie values from `s.cookies` back into `d:\\Daas\\.env` and `.rapidapi_session.json`."""
    if not s.cookies:
        return
    current_map = _parse_cookie_str(s.headers.get("Cookie", ""))
    changed = False
    for c in s.cookies:
        if c.value and current_map.get(c.name) != c.value:
            current_map[c.name] = c.value
            changed = True
    if not changed:
        return

    new_cookie_str = "; ".join(f"{k}={v}" for k, v in current_map.items())
    s.headers["Cookie"] = new_cookie_str

    SESSION_PATH.write_text(
        json.dumps(
            {
                "cookie": new_cookie_str,
                "csrf_token": s.headers.get("csrf-token", ""),
                "updated_at": int(time.time()),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    env_path = DAAS_DIR / ".env"
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
        if not found:
            new_lines.append(f"RAPIDAPI_STUDIO_COOKIE='{new_cookie_str}'")
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8", newline="\n")


def load_rapidapi_session() -> requests.Session:
    """Create a requests.Session hydrated from `.rapidapi_session.json` or `RAPIDAPI_STUDIO_COOKIE` in `.env`."""
    load_dotenv(DAAS_DIR / ".env", override=True)
    cookie_str = (os.getenv("RAPIDAPI_STUDIO_COOKIE") or "").strip().strip("'").strip('"')
    saved_csrf = ""
    if SESSION_PATH.exists():
        try:
            sess_data = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
            if sess_data.get("cookie"):
                cookie_str = sess_data["cookie"]
            saved_csrf = sess_data.get("csrf_token", "")
        except Exception:
            pass

    if not cookie_str:
        raise RuntimeError("RAPIDAPI_STUDIO_COOKIE is not configured in d:\\Daas\\.env")

    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
            ),
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
    _persist_rolled_cookies(s)
    if csrf_resp.status_code == 200:
        csrf_tok = csrf_resp.json().get("csrfToken", "")
        if csrf_tok:
            s.headers["csrf-token"] = csrf_tok
            _persist_rolled_cookies(s)
    return s


def keepalive_rapidapi_session() -> bool:
    """Ping `/gateway/csrf` with `x-rapidapi-Rolling-Key: true` and persist rolled cookies to prevent expiry."""
    try:
        s = load_rapidapi_session()
        return bool(s.headers.get("csrf-token"))
    except Exception:
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
    _persist_rolled_cookies(s)
    return r.json()


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
    existing_search = gql(
        s,
        """
        query {
          apis(where: { ownerId: { is: "12383419" } }, pagination: { first: 60 }) {
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
    title_prefix = title[:28].lower()
    for node in (existing_search.get("data", {}).get("apis", {}) or {}).get("nodes", []):
        n_name = (node.get("name") or "").lower()
        if n_name == title.lower() or title_prefix in n_name:
            api_id = node["id"]
            break

    if not api_id and oas_path.exists():
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
        if (mp_resp.get("data") or {}).get("updateApi"):
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
                "apiName": title,
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
                "apiName": title,
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
        "proxy_secret": info.get("secret"),
    }


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
    product_slug = api_cfg.get("slug", f"api-{api_num}")
    category = API_NUM_MIRROR_OVERRIDE.get(api_num, api_cfg.get("category", "capture"))
    ep_title = endpoint_name or title.replace(" API", "")

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

    # 2. Mirror endpoint onto public RapidAPI storefront immediately so it is 100% live and public
    mirror = PUBLIC_MIRROR_TARGETS.get(category, PUBLIC_MIRROR_TARGETS["capture"])
    ver_res = gql(s, "query($id: ID!) { api(id: $id) { id currentVersion { id } } }", {"id": mirror["api_id"]})
    version_id = ((ver_res.get("data") or {}).get("api") or {}).get("currentVersion", {}).get("id")

    q_ep = """
    mutation updateOrCreateEndpointWithParameters($input: EndpointWithParametersCreateInput!) {
      updateOrCreateEndpointWithParameters(input: $input) {
        id
        name
        route
        method
      }
    }
    """
    ep_input = {
        "apiVersion": version_id,
        "name": ep_title[:65],
        "route": route,
        "method": api_cfg.get("method", "POST"),
        "description": summary[:280],
        "externalDocs": {"url": f"https://signaltender.net/apis.html#product-{product_slug}"},
        "requestPayloads": [
            {
                "format": "application/json",
                "name": f"Api{api_num}Request",
                "description": summary[:200],
                "body": json.dumps(sample_payload),
                "examples": [{"name": "Sample Request", "value": json.dumps(sample_payload, indent=2)}],
            }
        ],
    }
    res_mirror = gql(s, q_ep, {"input": ep_input}, "updateOrCreateEndpointWithParameters")
    return {
        "api_number": api_num,
        "studio_project": studio_info,
        "public_host": mirror["host"],
        "public_hub_url": mirror["hub_url"],
        "mirror_endpoint": (res_mirror.get("data") or {}).get("updateOrCreateEndpointWithParameters"),
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Headless RapidAPI Studio & Render Publisher")
    parser.add_argument("--check-session", action="store_true", help="Verify RAPIDAPI_STUDIO_COOKIE is valid and roll cookie")
    parser.add_argument("--sync-missing", action="store_true", help="Publish all completed roadmap APIs (#22-#25+) to Rapid Studio & Public Hub")
    parser.add_argument("--day", type=int, help="Publish a specific roadmap day number")
    args = parser.parse_args()
    if args.check_session:
        sess = load_rapidapi_session()
        out = gql(
            sess,
            'query { api(id: "api_4c6bdfeb-1400-4466-a1f7-87fcdeb819d4") { id slugifiedName visibility currentVersion { id } } }',
        )
        print("[+] Headless RapidAPI GraphQL session verified:", out)
    elif args.sync_missing:
        sync_completed_days_to_rapidapi()
    elif args.day:
        sync_completed_days_to_rapidapi([args.day])
