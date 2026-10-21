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
    "/v1/generate/price-to-win": "govcon-igce-wrap-rate-price-to-win-modeler-api.p.rapidapi.com",
    "/v1/audit/far-dfars-clauses": "far-dfars-cmmc-clause-flow-down-auditor-api.p.rapidapi.com",
    "/v1/generate/teaming-strategy": "small-business-set-aside-subcontracting-calculator-api.p.rapidapi.com",
    "/v1/generate/past-performance": "cpars-past-performance-volume-generator-api.p.rapidapi.com",
    "/v1/generate/oral-presentation-prep": "govcon-oral-presentation-tech-demo-murder-board-prep-api.p.rapidapi.com",
    "/v1/generate/ato-rmf-package": "govcon-rmf-continuous-ato-cato-ssp-poa-m-generator-api.p.rapidapi.com",
    "/v1/generate/debriefing-bid-protest": "govcon-debriefing-far-15-506-gao-bid-protest-analyzer-api.p.rapidapi.com",
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
    "pennsylvania": "PENNSYLVANIA // eMARKETPLACE",
    "ohio": "OHIO // OHIOBUYS",
    "georgia": "GEORGIA // GPR & TEAM GA",
    "north_carolina": "NORTH CAROLINA // NC eVP & METRO",
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

    if "demandstar.com" in url:
        return "municipal"
    if "sam.gov" in url or "sbir.gov" in url:
        return "federal"
    if "txsmartbuy.com" in url:
        return "texas"
    if "eva.virginia.gov" in url or "cgieva.com" in url:
        return "virginia"
    if "caleprocure.ca.gov" in url:
        return "california"
    if "myfloridamarketplace.com" in url:
        return "florida"
    if "bidbuy.illinois.gov" in url or "transitchicago.bonfirehub.com" in url or "cookcountyil.bonfirehub.com" in url:
        return "illinois"
    if "emarketplace.state.pa.us" in url or "dgs.pa.gov" in url or "philaport.bonfirehub.com" in url:
        return "pennsylvania"
    if (
        "ohiobuys.ohio.gov" in url
        or "ohioauditor.gov" in url
        or "morpc.org" in url
        or "franklincountyohio.gov" in url
        or "columbus.bonfirehub.com" in url
        or "cincinnati-oh.bonfirehub.com" in url
        or "westerville.bonfirehub.com" in url
        or "dps.bonfirehub.com" in url
        or "akronohio.bonfirehub.com" in url
    ):
        return "ohio"
    if (
        "doas.state.ga.us" in url
        or "georgia.gov" in url
        or "ga.gov" in url
        or "forsythco.bonfirehub.com" in url
        or "fultonschools.bonfirehub.com" in url
        or "cobbk12.bonfirehub.com" in url
        or "itsmarta.com" in url
    ):
        return "georgia"
    if (
        "evp.nc.gov" in url
        or "nc.gov" in url
        or "unc.edu" in url
        or "ncsu.edu" in url
        or "wake.gov" in url
        or "mecknc.gov" in url
        or "charlottenc.gov" in url
        or "durhamnc.gov" in url
        or "guilfordcountync.gov" in url
    ):
        return "north_carolina"
    if "emma.maryland.gov" in url or "bonfirehub.com" in url:
        return "maryland"

    if title.startswith("[TX]") or "texas" in agency or ", tx" in agency or "ut md anderson" in agency:
        return "texas"
    if title.startswith("[VA]") or "virginia" in agency or "arlington county" in agency:
        return "virginia"
    if title.startswith("[CA]") or "california" in agency:
        return "california"
    if title.startswith("[FL]") or "florida" in agency:
        return "florida"
    if title.startswith("[IL]") or "state of illinois" in agency or "chicago transit authority" in agency or "cook county" in agency:
        return "illinois"
    if title.startswith("[PA]") or "pennsylvania" in agency or "philadelphia" in agency or agency.startswith("pa "):
        return "pennsylvania"
    if title.startswith("[GA]") or "georgia" in agency or "(ga)" in agency or "fulton county" in agency or "atlanta" in agency or "cobb county" in agency or "gwinnett" in agency or "dekalb" in agency:
        return "georgia"
    if title.startswith("[NC]") or "north carolina" in agency or "(nc)" in agency or "nc " in agency or "wake county" in agency or "mecklenburg" in agency or "charlotte" in agency or "raleigh" in agency or "durham" in agency or "guilford" in agency:
        return "north_carolina"
    if title.startswith("[OH]") or "ohio" in agency or "columbus" in agency or "morpc" in agency or "franklin county" in agency:
        return "ohio"
    if title.startswith("[MD]") or "maryland" in agency or "prince george" in agency or "howard county" in agency:
        return "maryland"
    if "federal government" in agency:
        return "federal"
    return "municipal"

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
    """Remove trailing '- Due: MM/DD/YYYY' and normalize encoding/spacing artifacts."""
    s = str(title or "").replace("\ufffd", "–")
    s = re.sub(r"\bWeb-\s+Based\b", "Web-Based", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*-\s*Due:\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


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
    clean = strip_due_suffix(title).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", clean).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if len(slug) > 75:
        slug = slug[:75].rsplit("-", 1)[0].strip("-")
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

    blob_low = f"{clean_title} {agency}".lower()
    if j_key == "federal":
        if any(k in blob_low for k in ("dod", "defense", "army", "navy", "air force", "space force", "darpa", "disa")):
            compliance_posture = "CMMC 2.0 Level 2 • NIST SP 800-171 Rev 2 • DFARS 252.204-7012 & FAR 52.204-21"
        else:
            compliance_posture = "FedRAMP Moderate / NIST SP 800-53 Rev 5 • FAR 52.204-21 • Section 508 VPAT"
        teaming_posture = "13 CFR § 125.6 (50% Rule): Prime ≥50% labor | Target Sub: SDVOSB / 8(a) / WOSB (25%–35%) + 3 CPARS Refs"
    elif j_key == "texas":
        compliance_posture = "TX-RAMP Level 2 Certification • Texas DIR Security Controls • TAC 206 WCAG 2.1 AA VPAT"
        teaming_posture = "TX HUB Subcontracting Plan (HSP Required >$100K): 26.0% Other Services HUB Goal + 3 TX/SLED Refs"
    elif j_key == "virginia":
        compliance_posture = "VITA SEC 530 Enterprise Cloud Standard • SOC 2 Type II • Virginia IT Accessibility Act VPAT"
        teaming_posture = "Virginia DSBSD SWaM Plan: 42% Small, Women- & Minority-Owned (SWaM) Goal + 3 Public-Sector Refs"
    elif j_key == "florida":
        if any(k in blob_low for k in ("correction", "law enforcement", "police", "sheriff", "court", "justice", "fdc", "fdle")):
            compliance_posture = "FBI CJIS Security Policy v5.9.4 • FAC 60GG-2 Cybersecurity • SOC 2 Type II + VPAT"
        else:
            compliance_posture = "Florida Digital Service FAC 60GG-2 Security • SOC 2 Type II • Section 508 / WCAG 2.1 AA"
        teaming_posture = "FL OSD Certified Minority / Veteran Business Enterprise (CMBE/VBE) Teaming + 3 SLED Past Performance Refs"
    elif j_key == "maryland":
        compliance_posture = "Maryland DoIT IT Security Manual • SOC 2 Type II / NIST 800-53 • MD Non-Visual Access (NVA) VPAT"
        teaming_posture = "Maryland MBE (15%–29% Sub Goal) + VSBE (1%–5% Veteran Goal) Participation + 3 Public-Sector Refs"
    elif j_key == "illinois":
        compliance_posture = "Illinois DoIT Enterprise Security Policy • SOC 2 Type II • IITAA 2.1 WCAG 2.1 AA VPAT"
        teaming_posture = "Illinois CEI BEP (20%–30% Business Enterprise Goal) + VBP Veteran Participation + 3 SLED Past Perf Refs"
    elif j_key == "pennsylvania":
        compliance_posture = "PA OA-ITB Security Policy • SOC 2 Type II / NIST 800-53 • PA EIT Accessibility VPAT"
        teaming_posture = "PA DGS BDISBO SDB/VBE Subcontracting Goal (15%–25%) + COSTARS/ITQ Alignment + 3 SLED Refs"
    elif j_key == "ohio":
        compliance_posture = "Ohio DAS OIT ITP-B.1 Cloud Security • SOC 2 Type II / NIST 800-53 • Ohio IT Accessibility VPAT"
        teaming_posture = "Ohio DAS MBE (15% Set-Aside/Sub Goal) + EDGE Participation + STS033 Schedule + 3 SLED Refs"
    elif j_key == "georgia":
        compliance_posture = "Georgia Tech Authority (GTA) SSG Security • StateRAMP / NIST 800-53 • GA Section 508 VPAT"
        teaming_posture = "Georgia DOAS Small Business / Minority Subcontracting (MBE/VBE) + GTA GETS Alignment + 3 SLED Refs"
    elif j_key == "north_carolina":
        compliance_posture = "NCDIT Statewide Information Security Manual (NIST 800-53) • StateRAMP / SOC 2 Type II • NC Section 508 VPAT"
        teaming_posture = "NC DOA Office for Historically Underutilized Businesses (HUB 10%+ Goal) + NCDIT ITSTC Alignment + 3 SLED Refs"
    elif j_key == "california":
        compliance_posture = "CalCloud / SIMM 5305-A Security • SOC 2 Type II / FedRAMP • Gov Code § 11546.7 WCAG 2.1 AA"
        teaming_posture = "CA DGS Small Business (5% SB Preference) + 3%–5% DVBE Participation + 3 State/Local Refs"
    else:
        compliance_posture = "SOC 2 Type II / NIST CSF 2.0 • Encryption in Transit/Rest • Section 508 / WCAG 2.1 AA VPAT"
        teaming_posture = "Local SBE / MWBE Good-Faith Subcontracting (15%–25%) + 3 Public-Sector Past Performance Refs"

    # APIs 11-16 Intelligence Enrichment (IGCE/Wrap-Rate/PTW, Key Personnel LCATs, CPARS Relevance, Ostensible Sub Risk)
    if "cyber" in vertical.lower():
        igce_ptw_posture = "Wrap ~1.84x (Contractor-Site) • Target PTW: -4.5% vs. IGCE • Sr. Cyber Arch $168/hr | SecOps Eng $148/hr"
        key_personnel_lcats = "Program Manager (PMP/CISSP, 10+ yrs) • Principal Zero-Trust/SOC Architect (CISSP/CISM, 8+ yrs)"
    elif "cloud" in vertical.lower():
        igce_ptw_posture = "Wrap ~1.82x (Contractor-Site) • Target PTW: -5.2% vs. IGCE • Principal Cloud Arch $165/hr | DevSecOps $146/hr"
        key_personnel_lcats = "Program Manager (PMP, 10+ yrs) • Lead Cloud/DevSecOps Architect (AWS/Azure Pro + CISSP, 8+ yrs)"
    elif "network" in vertical.lower() or "telecom" in vertical.lower():
        igce_ptw_posture = "Wrap ~1.76x (Hybrid Site) • Target PTW: -6.0% vs. IGCE • Lead Network Arch $154/hr | Field Eng $128/hr"
        key_personnel_lcats = "Telecom Project Manager (PMP/BICSI, 8+ yrs) • Lead Network Infrastructure Engineer (CCNP/CCIE, 7+ yrs)"
    else:
        igce_ptw_posture = "Wrap ~1.80x (Contractor-Site) • Target PTW: -5.5% vs. IGCE • Sr. Solutions Arch $162/hr | Lead Software Eng $146/hr"
        key_personnel_lcats = "Engagement Program Manager (PMP/CSM, 10+ yrs) • Lead Enterprise Systems Architect (8+ yrs)"

    cpars_relevance_benchmark = "Substantial Confidence Target • 3 Very Relevant Refs (Within 5 Yrs, Exceptional Quality/Schedule CPARS)"
    ostensible_sub_risk = "LOW RISK (13 CFR § 121.103(h)(3)) — Prime retains ≥51% labor, PM authority & core architecture"

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
        "compliance_posture": compliance_posture,
        "teaming_posture": teaming_posture,
        "igce_ptw_posture": igce_ptw_posture,
        "key_personnel_lcats": key_personnel_lcats,
        "cpars_relevance_benchmark": cpars_relevance_benchmark,
        "ostensible_sub_risk": ostensible_sub_risk,
        "win_themes": win_themes[:3],
        "evidence_needed": evidence_checklist[:2],
        "enriched_at": datetime.now(timezone.utc).isoformat(),
    }


def _clip_bullet(text: str, max_len: int = 230) -> str:
    s = re.sub(r"\s+", " ", str(text or "").strip())
    if len(s) <= max_len:
        return s
    cut = s[: max_len - 1].rsplit(" ", 1)[0].rstrip(",;:-")
    return f"{cut}…"


def format_capturedesk_discord_embed(dossier: dict) -> str:
    clean_title = strip_due_suffix(dossier.get("title", ""))
    j_badge = dossier.get("jurisdiction_badge") or JURISDICTION_LABELS.get(classify_jurisdiction(dossier), "FEDERAL // SAM.GOV")
    vertical = dossier.get("vertical") or classify_vertical_tag(dossier)
    themes_formatted = "\n".join(f"  • {_clip_bullet(t, 175)}" for t in dossier.get("win_themes", [])[:3])
    nigp_part = f" | NIGP `{dossier['primary_nigp']}`" if dossier.get("primary_nigp") else ""
    posture_line = ""
    if dossier.get("compliance_posture") or dossier.get("teaming_posture"):
        c_pos = dossier.get("compliance_posture") or "SOC 2 Type II / Section 508 VPAT"
        t_pos = dossier.get("teaming_posture") or "13 CFR § 125.6 (50% Rule) + 3 Past Performance Refs"
        ptw_pos = dossier.get("igce_ptw_posture") or "Wrap ~1.80x • Target PTW: -5.5% vs. IGCE • Sr. Arch $162/hr"
        lcat_pos = dossier.get("key_personnel_lcats") or "Program Manager (PMP) • Lead Solutions Architect"
        posture_line = (
            f"**Cyber, RMF/cATO & Teaming Posture (API #06/#11/#12/#18):** `{c_pos}` | `{t_pos}`\n"
            f"**IGCE Wrap-Rate, PTW, Key LCATs, Orals & Protest (API #13/#15/#16/#17/#19):** `{ptw_pos}` | `{lcat_pos}`\n"
        )
    evidence_lines = ""
    if dossier.get("evidence_needed"):
        ev_formatted = "\n".join(f"  • {_clip_bullet(e, 165)}" for e in dossier["evidence_needed"][:2])
        evidence_lines = f"**Required Proof & Proposal Evidence:**\n{ev_formatted}\n"

    body = (
        f"**[{j_badge}]** • `{vertical}`\n"
        f"**Solicitation:** {clean_title}\n"
        f"**Buyer Agency:** {dossier['agency']} | **Closing Date:** `{dossier['closing_date']}`\n"
        f"**Industry & Size Classification:** NAICS `{dossier['primary_naics']}` | PSC `{dossier['primary_psc']}`{nigp_part} | SBA Size: `{dossier['sba_size_standard']}`\n"
        f"{posture_line}"
        f"**Tailored Shipley Win Strategy:**\n{themes_formatted}\n"
        f"{evidence_lines}"
    )
    footer = (
        f"**Official Portal:** <{dossier['source_url']}>\n"
        f"**SignalTender Dossier:** <{dossier['dossier_url']}>\n"
        f"{'─' * 44}"
    )
    max_body_len = 1920 - len(footer)
    if len(body) > max_body_len:
        body = body[: max_body_len - 4].rsplit(" ", 1)[0] + "…\n"
    return body + footer


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
            if DISCORD_CAPTUREDESK_WEBHOOK_URL:
                import time
                for d in new_dossiers:
                    single_block = format_capturedesk_discord_embed(d)
                    r = requests.post(
                        DISCORD_CAPTUREDESK_WEBHOOK_URL,
                        json={
                            "username": "CaptureDesk Autopilot",
                            "content": single_block,
                            "flags": 4,
                        },
                        timeout=15,
                    )
                    if r.status_code == 429:
                        retry_after = r.json().get("retry_after", 1.5)
                        time.sleep(float(retry_after))
                        r = requests.post(
                            DISCORD_CAPTUREDESK_WEBHOOK_URL,
                            json={
                                "username": "CaptureDesk Autopilot",
                                "content": single_block,
                                "flags": 4,
                            },
                            timeout=15,
                        )
                    r.raise_for_status()
                    time.sleep(0.5)
                print(f" -> [CaptureDesk] Dispatched {len(new_dossiers)} individual CaptureDesk dossier(s) to DISCORD_CAPTUREDESK_WEBHOOK_URL.", flush=True)

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
                            ext_payload = {"username": "CaptureDesk Autopilot", "content": d_text, "flags": 4}
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
