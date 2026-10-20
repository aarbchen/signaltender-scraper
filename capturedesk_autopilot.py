"""
SignalTender — CaptureDesk Autopilot Dossier Engine
Automatically chains SignalTender's live FastAPI microservices (NAICS/PSC/SIC/NIGP Classifier
and Shipley Compliance Matrix & Outline) against newly scraped Federal & State SLED RFPs in Supabase,
persists enriched JSON dossiers, and dispatches executive CaptureDesk briefs to Discord.
"""

import json
import os
import re
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables without hardcoding secrets
load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv(dotenv_path=r"D:\Data API Ecosystem\.env")
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = os.getenv("SUPABASE_TABLE_NAME", "contracts")

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DISCORD_CAPTUREDESK_WEBHOOK_URL = os.getenv("DISCORD_CAPTUREDESK_WEBHOOK_URL")

API_BASE_URL = os.getenv(
    "SIGNALTENDER_API_BASE_URL",
    "https://b2b-contract-parser-api.onrender.com",
).rstrip("/")
RAPIDAPI_PROXY_SECRET = os.getenv("RAPIDAPI_PROXY_SECRET")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

SITE_BASE_URL = os.getenv("SIGNALTENDER_SITE_URL", "https://signaltender.net").rstrip("/")
STRIPE_TIER2_URL = os.getenv(
    "STRIPE_TIER2_CHECKOUT_URL",
    f"{SITE_BASE_URL}/index.html#checkout-tier2",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ERROR_LOG_PATH = os.path.join(BASE_DIR, "error_log.txt")
DOSSIER_CACHE_PATH = os.path.join(BASE_DIR, "capturedesk_dossiers.json")
BATCH_LIMIT = int(os.getenv("CAPTUREDESK_BATCH_LIMIT", "2"))

RAPIDAPI_ENDPOINT_HOSTS = {
    "/v1/classify/naics-psc-nigp": "naics-sic-psc-unspsc-industry-classifier-api.p.rapidapi.com",
    "/v1/generate/compliance-matrix": "rfp-compliance-matrix-proposal-outline-api.p.rapidapi.com",
}

JURISDICTION_LABELS = {
    "federal": "FEDERAL // SAM.GOV",
    "texas": "TEXAS // ESBD",
    "virginia": "VIRGINIA // eVA",
    "california": "CALIFORNIA // CAL EPROCURE",
    "florida": "FLORIDA // MFMP VIP",
    "maryland": "MARYLAND // EMMA & BONFIRE",
    "new_york": "NEW YORK // NYSCR",
    "illinois": "ILLINOIS // BIDBUY",
    "municipal": "MUNICIPAL // DEMANDSTAR",
}


def log_error(msg: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{timestamp}] [CaptureDesk Autopilot] {msg}\n"
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def send_discord_alert(message: str) -> None:
    """Send operational error alert to Discord webhook and log to error_log.txt."""
    log_error(message)
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": f"**[ALERT] CaptureDesk Autopilot:**\n{message}"},
            timeout=10,
        )
    except Exception as exc:
        log_error(f"Failed to send Discord alert: {exc}")


def classify_jurisdiction(record: dict) -> str:
    title = str(record.get("title") or "").strip()
    agency = str(record.get("agency") or "").strip().lower()
    url = str(record.get("url") or record.get("source_url") or "").strip().lower()

    if title.startswith("[TX]") or "txsmartbuy" in url or "texas" in agency or ", tx" in agency:
        return "texas"
    if title.startswith("[VA]") or "eva.virginia.gov" in url or "cgieva.com" in url or "virginia" in agency or "arlington county" in agency:
        return "virginia"
    if title.startswith("[CA]") or "caleprocure" in url or "california" in agency:
        return "california"
    if title.startswith("[FL]") or "myfloridamarketplace" in url or "florida" in agency:
        return "florida"
    if title.startswith("[MD]") or "emma.maryland.gov" in url or "mdcourts.bonfirehub.com" in url or "maryland" in agency:
        return "maryland"
    if title.startswith("[NY]") or "nyscr.ny.gov" in url or "new york" in agency:
        return "new_york"
    if title.startswith("[IL]") or "bidbuy.illinois.gov" in url or "illinois" in agency or "chicago" in agency:
        return "illinois"
    if "demandstar.com" in url:
        return "municipal"
    return "federal"


def classify_vertical_tag(record: dict) -> str:
    blob = f"{record.get('title', '')} {record.get('agency', '')}".lower()
    if any(k in blob for k in ("cyber", "infosec", "security", "siem", "soc", "zero trust", "firewall", "audit", "rmf")):
        return "Cybersecurity & Zero-Trust"
    if any(k in blob for k in ("cloud", "aws", "azure", "saas", "data center", "server", "storage", "hosting")):
        return "Cloud & Infrastructure"
    if any(k in blob for k in ("network", "fiber", "broadband", "telecom", "wireless", "hardware", "audio/visual", "aiphone")):
        return "Network, Telecom & Hardware"
    return "Enterprise Software, Data & AI"


def strip_due_suffix(title: str) -> str:
    """Remove trailing '- Due: MM/DD/YYYY' from display title so it is not duplicated next to Closing Date."""
    return re.sub(r"\s*-\s*Due:\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$", "", str(title or "").strip(), flags=re.IGNORECASE).strip()


def _call_gateway(endpoint: str, payload: dict) -> dict | None:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if RAPIDAPI_PROXY_SECRET:
        parts = [s.strip() for s in RAPIDAPI_PROXY_SECRET.split(",") if s.strip()]
        prod_parts = [s for s in parts if not s.startswith("local_")]
        chosen = prod_parts[0] if prod_parts else (parts[0] if parts else "")
        if chosen:
            headers["X-RapidAPI-Proxy-Secret"] = chosen
            url = f"{API_BASE_URL}{endpoint}"
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=60)
                if resp.status_code == 200:
                    return resp.json()
                log_error(f"Gateway non-200 ({resp.status_code}) on {endpoint}: {resp.text[:250]}")
            except Exception as exc:
                log_error(f"Gateway call error on {endpoint}: {exc}")

    if RAPIDAPI_KEY and endpoint in RAPIDAPI_ENDPOINT_HOSTS:
        rapid_host = RAPIDAPI_ENDPOINT_HOSTS[endpoint]
        rapid_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": rapid_host,
        }
        try:
            resp = requests.post(f"https://{rapid_host}{endpoint}", json=payload, headers=rapid_headers, timeout=60)
            if resp.status_code == 200:
                return resp.json()
            log_error(f"RapidAPI proxy non-200 ({resp.status_code}) on {endpoint}: {resp.text[:250]}")
        except Exception as exc:
            log_error(f"RapidAPI proxy call error on {endpoint}: {exc}")

    return None


def slugify_contract(title: str, fallback_id: str = "") -> str:
    clean = re.sub(r"^\s*\[[A-Z]{2,4}\]\s*", "", str(title or "")).strip().lower()
    clean = re.sub(r"\s*-\s*due:\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$", "", clean, flags=re.IGNORECASE)
    slug = re.sub(r"[^a-z0-9]+", "-", clean).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)[:75].strip("-")
    if not slug:
        slug = "government-it-contract"
    return f"{slug}-{fallback_id}" if fallback_id else slug


def enrich_contract_dossier(record: dict) -> dict:
    """
    Enriches a single Supabase contract record using the live NAICS/PSC/SIC/NIGP Classifier
    and Shipley Compliance Matrix & Proposal Outline microservices, mapping exact Pydantic V2
    response fields so each dossier has solicitation-specific taxonomy codes, win themes,
    and required verification evidence.
    """
    rec_id = str(record.get("id") or "")
    raw_title = str(record.get("title") or "Enterprise Government IT Solicitation").strip()
    clean_title = strip_due_suffix(raw_title)
    agency = str(record.get("agency") or "Government Agency").strip()
    closing_date = str(record.get("closing_date") or "").strip()
    if not closing_date:
        m_due = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", raw_title, flags=re.IGNORECASE)
        closing_date = m_due.group(1) if m_due else "Open / See Official Portal"
    source_url = str(record.get("url") or SITE_BASE_URL).strip()
    slug = slugify_contract(raw_title, rec_id)
    dossier_url = f"{SITE_BASE_URL}/contracts/rfp/{slug}.html"

    j_key = classify_jurisdiction(record)
    j_badge = JURISDICTION_LABELS.get(j_key, "FEDERAL // SAM.GOV")
    vertical = classify_vertical_tag(record)
    methodology = "federal_far" if j_key == "federal" else "shipley"

    synthetic_scope = (
        f"Government Solicitation Title: {clean_title}\n"
        f"Issuing Buyer Agency: {agency} ({j_badge})\n"
        f"Technology Vertical: {vertical}\n"
        f"Submission Deadline: {closing_date}\n"
        f"Official Portal URL: {source_url}\n"
        f"Task Instruction: Analyze the specific solution requested in '{clean_title}' for '{agency}'. "
        "Identify the exact 6-digit NAICS, 4-character Federal PSC, and 5-digit State NIGP commodity codes, "
        "and formulate 3 concrete, solicitation-specific Shipley proposal win themes and proof artifacts "
        "tailored directly to this agency and technology scope."
    )

    # 1. Call NAICS, SIC, PSC & UNSPSC/NIGP Classifier
    classification = _call_gateway(
        "/v1/classify/naics-psc-nigp",
        {
            "description_text": synthetic_scope,
            "context_type": "rfp_or_sow_scope",
            "max_secondary_codes": 2,
        },
    )

    primary_naics = "541512 — Computer Systems Design Services"
    primary_psc = "DA01 — IT & Telecom: Application Development"
    primary_nigp = "920-45 — Software Consulting & Systems Integration"
    sba_threshold = "$34.0M annual receipts"

    if isinstance(classification, dict) and isinstance(classification.get("primary_naics"), dict):
        pn = classification["primary_naics"]
        n_code = pn.get("naics_code") or pn.get("code") or "541512"
        n_title = pn.get("naics_title") or pn.get("title") or "Computer Systems Design Services"
        primary_naics = f"{n_code} — {n_title}"
        sba_threshold = pn.get("sba_size_standard_value") or pn.get("sba_size_standard") or sba_threshold

        psc_list = classification.get("federal_psc_codes") or []
        if psc_list and isinstance(psc_list[0], dict):
            psc0 = psc_list[0]
            p_code = psc0.get("psc_code") or psc0.get("code") or "DA01"
            p_title = psc0.get("psc_title") or psc0.get("title") or "IT & Telecom Services"
            primary_psc = f"{p_code} — {p_title}"

        nigp_list = classification.get("state_unspsc_and_nigp_codes") or []
        if nigp_list and isinstance(nigp_list[0], dict):
            nigp0 = nigp_list[0]
            g_code = nigp0.get("nigp_class_item_code") or "920-45"
            g_title = nigp0.get("nigp_title") or "Software & IT Services"
            primary_nigp = f"{g_code} — {g_title}"

    # 2. Call Shipley Compliance Matrix & Proposal Outline
    compliance_scope = (
        f"SOLICITATION TITLE: {clean_title} — Issuing Agency: {agency} ({j_badge})\n"
        f"SECTION L - INSTRUCTIONS TO OFFERORS: Proposals shall be submitted via {source_url} prior to {closing_date}.\n"
        f"SECTION C - STATEMENT OF WORK: 3.1 The Contractor shall design, deploy, and support '{clean_title}' "
        f"for {agency} in the {vertical} domain. 3.2 The Contractor shall meet all security, accessibility "
        f"(Section 508 / WCAG 2.1 AA), integration, and SLA uptime standards required by {agency}. "
        f"3.3 The Contractor shall provide a phased implementation schedule, training, and transition plan.\n"
        f"SECTION M - EVALUATION FACTORS: Technical Approach & Architecture (45%), Past Performance on Similar "
        f"Public-Sector Engagements (30%), Management & Implementation Plan (25%)."
    )
    compliance = _call_gateway(
        "/v1/generate/compliance-matrix",
        {
            "raw_text": compliance_scope,
            "proposal_methodology": methodology,
        },
    )

    win_themes = []
    admin_themes = []
    evidence_checklist = []
    if isinstance(compliance, dict):
        for sec in compliance.get("proposal_outline") or []:
            if isinstance(sec, dict) and sec.get("win_theme_strategy"):
                sec_title = sec.get("section_title", "").strip()
                strategy = sec.get("win_theme_strategy", "").strip()
                item_str = f"**{sec_title}:** {strategy}" if sec_title else strategy
                if sec.get("assigned_volume") == "ADMINISTRATIVE_CERTIFICATIONS":
                    admin_themes.append(item_str)
                else:
                    win_themes.append(item_str)
        win_themes.extend(admin_themes)
        for req in compliance.get("requirements_matrix") or []:
            if isinstance(req, dict) and req.get("verification_evidence_needed"):
                if str(req.get("assigned_proposal_volume") or "") != "ADMINISTRATIVE_CERTIFICATIONS":
                    evidence_checklist.append(str(req["verification_evidence_needed"]).strip())

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if (not win_themes or not evidence_checklist) and anthropic_key:
        try:
            anth_resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
                    "max_tokens": 700,
                    "system": (
                        "Return ONLY valid JSON with two keys: "
                        "\"win_themes\" (array of 3 concise Shipley capture win strategy strings starting with **Section Heading:**) "
                        "and \"evidence_needed\" (array of 2 concrete technical/compliance proof items required for the proposal)."
                    ),
                    "messages": [
                        {
                            "role": "user",
                            "content": compliance_scope,
                        }
                    ],
                },
                timeout=30,
            )
            if anth_resp.status_code == 200:
                txt = anth_resp.json().get("content", [{}])[0].get("text", "")
                m_json = re.search(r"\{.*\}", txt, flags=re.DOTALL)
                if m_json:
                    parsed = json.loads(m_json.group(0))
                    if not win_themes and isinstance(parsed.get("win_themes"), list):
                        win_themes = [str(x).strip() for x in parsed["win_themes"] if str(x).strip()]
                    if not evidence_checklist and isinstance(parsed.get("evidence_needed"), list):
                        evidence_checklist = [str(x).strip() for x in parsed["evidence_needed"] if str(x).strip()]
        except Exception as anth_exc:
            log_error(f"Direct Anthropic fallback error: {anth_exc}")

    if not win_themes:
        win_themes = [
            f"**Executive Summary & Mission Alignment:** Align implementation schedule and SLA milestones directly with {agency} operational requirements for {clean_title}.",
            f"**Technical Architecture & Security:** Highlight turnkey {vertical} deployment, WCAG 2.1 AA / security compliance, and low-risk migration.",
            f"**Relevant Public-Sector Past Performance:** Provide verifiable {j_badge.split('//')[0].strip()} reference deployments of comparable scope and user scale.",
        ]

    return {
        "id": rec_id,
        "title": clean_title,
        "agency": agency,
        "jurisdiction_badge": j_badge,
        "vertical": vertical,
        "closing_date": closing_date,
        "source_url": source_url,
        "dossier_url": dossier_url,
        "primary_naics": primary_naics,
        "primary_psc": primary_psc,
        "primary_nigp": primary_nigp,
        "sba_size_standard": sba_threshold,
        "win_themes": win_themes[:3],
        "evidence_needed": evidence_checklist[:2],
        "enriched_at": datetime.now(timezone.utc).isoformat(),
    }


def format_capturedesk_discord_embed(dossier: dict) -> str:
    clean_title = strip_due_suffix(dossier.get("title", ""))
    j_badge = dossier.get("jurisdiction_badge") or JURISDICTION_LABELS.get(classify_jurisdiction(dossier), "FEDERAL // SAM.GOV")
    vertical = dossier.get("vertical") or classify_vertical_tag(dossier)
    themes_formatted = "\n".join(f"  • {t}" for t in dossier.get("win_themes", [])[:3])
    nigp_part = f" | NIGP `{dossier['primary_nigp']}`" if dossier.get("primary_nigp") else ""
    evidence_lines = ""
    if dossier.get("evidence_needed"):
        ev_formatted = "\n".join(f"  • {e}" for e in dossier["evidence_needed"][:2])
        evidence_lines = f"**Required Proof & Proposal Evidence:**\n{ev_formatted}\n"

    return (
        f"**[{j_badge}]** • `{vertical}`\n"
        f"**Solicitation:** {clean_title}\n"
        f"**Buyer Agency:** {dossier['agency']} | **Closing Date:** `{dossier['closing_date']}`\n"
        f"**Industry & Size Classification:** NAICS `{dossier['primary_naics']}` | PSC `{dossier['primary_psc']}`{nigp_part} | SBA Size: `{dossier['sba_size_standard']}`\n"
        f"**Tailored Shipley Win Strategy:**\n{themes_formatted}\n"
        f"{evidence_lines}"
        f"**Official Portal:** <{dossier['source_url']}>\n"
        f"**SignalTender Dossier:** <{dossier['dossier_url']}>\n"
        f"{'─' * 44}"
    )


def run_capturedesk_autopilot(force_refresh_ids: list[str] | None = None) -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        print(" -> [CaptureDesk] SUPABASE_URL or SUPABASE_KEY not set; skipping.", flush=True)
        return

    try:
        existing_dossiers: dict = {}
        if os.path.exists(DOSSIER_CACHE_PATH):
            try:
                with open(DOSSIER_CACHE_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        existing_dossiers = loaded
            except Exception:
                existing_dossiers = {}

        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        resp = (
            supabase.table(TABLE_NAME)
            .select("id, title, agency, closing_date, url, status")
            .order("id", desc=True)
            .limit(40)
            .execute()
        )
        rows = [
            r for r in (resp.data or [])
            if not str(r.get("url") or "").startswith("subscriber://")
            and not str(r.get("status") or "").startswith("SUBSCRIBER_")
        ]
        if not rows:
            print(" -> [CaptureDesk] No contracts found in Supabase.", flush=True)
            return

        new_dossiers = []
        for row in rows:
            rec_id = str(row.get("id") or "")
            if not rec_id:
                continue
            if force_refresh_ids is not None:
                if rec_id not in force_refresh_ids:
                    continue
            elif rec_id in existing_dossiers:
                continue
            dossier = enrich_contract_dossier(row)
            existing_dossiers[rec_id] = dossier
            new_dossiers.append(dossier)
            if force_refresh_ids is None and len(new_dossiers) >= BATCH_LIMIT:
                break

        with open(DOSSIER_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(existing_dossiers, f, indent=2)

        print(
            f" -> [CaptureDesk] Enriched {len(new_dossiers)} new dossiers (Total cached: {len(existing_dossiers)}).",
            flush=True,
        )

        if new_dossiers:
            blocks = [format_capturedesk_discord_embed(d) for d in new_dossiers]
            payload_text = "\n\n".join(blocks)[:1950]

            if DISCORD_CAPTUREDESK_WEBHOOK_URL:
                r = requests.post(
                    DISCORD_CAPTUREDESK_WEBHOOK_URL,
                    json={
                        "username": "CaptureDesk Autopilot",
                        "content": payload_text,
                    },
                    timeout=15,
                )
                r.raise_for_status()
                print(" -> [CaptureDesk] Dispatched CaptureDesk dossiers to DISCORD_CAPTUREDESK_WEBHOOK_URL.", flush=True)

            # Also dispatch to active Tier 2 subscriber external webhooks (Slack, MS Teams, Zapier, Make, n8n, CRM)
            try:
                sub_resp = supabase.table(TABLE_NAME).select("title,status").eq("status", "SUBSCRIBER_ACTIVE").execute()
                for srow in (sub_resp.data or []):
                    meta = json.loads(str(srow.get("title") or "{}"))
                    if str(meta.get("tier") or "") != "tier_2":
                        continue
                    w_url = str(meta.get("webhook_url") or "").strip()
                    if not w_url.startswith("https://"):
                        continue
                    u_low = w_url.lower()
                    for d in new_dossiers:
                        d_text = format_capturedesk_discord_embed(d)
                        if "hooks.slack.com" in u_low or "webhook.office.com" in u_low or "logic.azure.com" in u_low:
                            ext_payload = {"text": d_text}
                        elif "discord.com/api/webhooks" in u_low:
                            ext_payload = {"username": "CaptureDesk Autopilot", "content": d_text}
                        else:
                            ext_payload = {
                                "event": "signaltender.rfp_dossier.dispatched",
                                "tier": "tier_2",
                                "text": d_text,
                                "content": d_text,
                                "contract": d,
                            }
                        requests.post(w_url, json=ext_payload, timeout=10)
            except Exception as sub_err:
                log_error(f"External Tier 2 webhook dispatch warning: {sub_err}")

    except Exception as exc:
        send_discord_alert(f"CaptureDesk Autopilot failed: {exc}")


if __name__ == "__main__":
    run_capturedesk_autopilot()
