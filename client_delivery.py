from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()
import os
import re
import time
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = os.getenv("SUPABASE_TABLE_NAME", "contracts")
SITE_BASE_URL = os.getenv("SIGNALTENDER_SITE_URL", "https://signaltender.net").rstrip("/")

# Master Client Discord Webhook + Optional State/Portal-Specific Webhooks
CLIENT_DISCORD_WEBHOOK_URL = (
    os.getenv("DISCORD_CONTENT_WEBHOOK_URL")
    or os.getenv("CLIENT_DISCORD_WEBHOOK_URL")
    or os.getenv("DISCORD_WEBHOOK_URL")
)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

JURISDICTION_WEBHOOKS = {
    "federal": os.getenv("DISCORD_FEDERAL_WEBHOOK_URL"),
    "texas": os.getenv("DISCORD_TEXAS_WEBHOOK_URL"),
    "virginia": os.getenv("DISCORD_VIRGINIA_WEBHOOK_URL"),
    "california": os.getenv("DISCORD_CALIFORNIA_WEBHOOK_URL"),
    "florida": os.getenv("DISCORD_FLORIDA_WEBHOOK_URL"),
    "maryland": os.getenv("DISCORD_MARYLAND_WEBHOOK_URL"),
    "new_york": os.getenv("DISCORD_NEW_YORK_WEBHOOK_URL"),
    "illinois": os.getenv("DISCORD_ILLINOIS_WEBHOOK_URL"),
    "pennsylvania": os.getenv("DISCORD_PENNSYLVANIA_WEBHOOK_URL"),
    "ohio": os.getenv("DISCORD_OHIO_WEBHOOK_URL"),
    "georgia": os.getenv("DISCORD_GEORGIA_WEBHOOK_URL"),
    "north_carolina": os.getenv("DISCORD_NORTH_CAROLINA_WEBHOOK_URL"),
    "massachusetts": os.getenv("DISCORD_MASSACHUSETTS_WEBHOOK_URL"),
    "new_jersey": os.getenv("DISCORD_NEW_JERSEY_WEBHOOK_URL"),
    "municipal": os.getenv("DISCORD_MUNICIPAL_WEBHOOK_URL"),
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
    "massachusetts": "MASSACHUSETTS // COMMBUYS & BOSTON",
    "new_jersey": "NEW JERSEY // NJSTART & TREASURY DPP",
    "municipal": "MUNICIPAL // DEMANDSTAR",
}

ERROR_LOG_PATH = r"D:\Daas\error_log.txt"


def send_discord_alert(message: str) -> None:
    report_error("client_delivery.py", str(message))
    """Send system alert to Discord webhook and log errors as per project rules."""
    if not DISCORD_WEBHOOK_URL:
        print(" -> ERROR: Alert webhook URL not found in environment.", flush=True)
        return
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": f"**[ALERT] Delivery Pipeline:**\n{message}"},
            timeout=10,
        )
        response.raise_for_status()
        print(" -> Discord alert sent successfully.", flush=True)
    except Exception as e:
        print(f" -> Failed to send Discord alert: {e}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"Failed to send Discord alert: {e}\n")
        except Exception:
            pass


def clean_title_text(raw_title: str) -> str:
    s = str(raw_title or "").replace("\ufffd", "–")
    s = re.sub(r"\bWeb-\s+Based\b", "Web-Based", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*-\s*Due:\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def slugify_contract(title: str, fallback_id: str = "") -> str:
    clean = clean_title_text(title).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", clean).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if len(slug) > 75:
        slug = slug[:75].rsplit("-", 1)[0].strip("-")
    if not slug:
        slug = "government-it-contract"
    if fallback_id:
        return f"{slug}-{fallback_id}"
    return slug


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
    if (
        "a856-cityrecord.nyc.gov" in url
        or "passport.cityofnewyork.us" in url
        or "cityofnewyork.us" in url
        or "panynj.bonfirehub.com" in url
        or "suffolkcountyny.bonfirehub.com" in url
        or "rocklandgov.bonfirehub.com" in url
        or "nyscr.ny.gov" in url
        or "ogs.ny.gov" in url
    ):
        return "new_york"
    if (
        "commbuys.com" in url
        or "mass.gov" in url
        or "boston.gov" in url
        or "mbta.com" in url
        or "massport.com" in url
        or "masstech.org" in url
    ):
        return "massachusetts"
    if (
        "njstart.gov" in url
        or "nj.gov" in url
        or "njtransit.com" in url
        or "rutgers.edu" in url
    ):
        return "new_jersey"
    if "emma.maryland.gov" in url or "maryland.gov" in url or "countymd.bonfirehub.com" in url:
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
    if (
        title.startswith("[NY]")
        or "new york" in agency
        or "nyc " in agency
        or "(ny)" in agency
        or "panynj" in agency
        or "port authority of new york" in agency
        or "suffolk county" in agency
        or "rockland county" in agency
    ):
        return "new_york"
    if (
        title.startswith("[MA]")
        or "massachusetts" in agency
        or "(ma)" in agency
        or "commbuys" in agency
        or "city of boston" in agency
        or "boston public" in agency
        or "mbta" in agency
        or "massport" in agency
        or "eotss" in agency
    ):
        return "massachusetts"
    if (
        title.startswith("[NJ]")
        or "new jersey" in agency
        or "(nj)" in agency
        or "njstart" in agency
        or "nj transit" in agency
        or "rutgers" in agency
    ):
        return "new_jersey"
    if title.startswith("[OH]") or "ohio" in agency or "columbus" in agency or "morpc" in agency or "franklin county" in agency:
        return "ohio"
    if title.startswith("[MD]") or "maryland" in agency or "prince george" in agency or "howard county" in agency or "bonfirehub.com" in url:
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
    if any(k in blob for k in ("network", "fiber", "broadband", "telecom", "wireless", "hardware", "audio/visual")):
        return "Network, Telecom & Hardware"
    return "Enterprise Software, Data & AI"


def format_lead_block(record: dict) -> str:
    """Format an individual Supabase contract record into an enriched Discord intelligence block."""
    raw_title = str(record.get("title") or "N/A").strip()
    clean_title = clean_title_text(raw_title)
    agency = str(record.get("agency") or "N/A").strip()
    closing_date = str(record.get("closing_date") or "").strip()
    if not closing_date:
        m_due = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", raw_title, flags=re.IGNORECASE)
        closing_date = m_due.group(1) if m_due else "Open / See Official Portal"
    link = str(record.get("url") or "N/A").strip()
    rec_id = str(record.get("id") or "")

    j_key = classify_jurisdiction(record)
    j_badge = JURISDICTION_LABELS.get(j_key, "FEDERAL // SAM.GOV")
    vertical = classify_vertical_tag(record)
    slug = slugify_contract(raw_title, fallback_id=rec_id)
    dossier_url = f"{SITE_BASE_URL}/contracts/rfp/{slug}.html"

    lines = [
        f"**[{j_badge}]** • `{vertical}`",
        f"**Solicitation:** {clean_title}",
        f"**Buyer Agency:** {agency} | **Closing Date:** `{closing_date}`",
        f"**Official Portal:** <{link}>",
        f"**SignalTender Dossier:** <{dossier_url}>",
        f"{'─' * 44}",
    ]
    return "\n".join(lines)


def _post_batches_to_webhook(records: list[dict], webhook_url: str, label: str = "Master Wire") -> bool:
    """Group records into <1900-char batches and POST to a Discord webhook with rate-limit retry."""
    if not records or not webhook_url:
        return False

    batches = []
    current_batch = []
    current_char_count = 0

    for rec in records:
        block = format_lead_block(rec)
        block_len = len(block) + 4
        if current_char_count + block_len > 1900 and current_batch:
            batches.append(current_batch)
            current_batch = [rec]
            current_char_count = len(block)
        else:
            current_batch.append(rec)
            current_char_count += block_len

    if current_batch:
        batches.append(current_batch)

    for batch_index, batch in enumerate(batches, start=1):
        blocks = [format_lead_block(rec) for rec in batch]
        message_content = "\n\n".join(blocks)

        print(f"[*] Posting {label} batch {batch_index}/{len(batches)} ({len(batch)} lead(s)) to Discord...", flush=True)
        payload = {
            "username": "SignalWire Pro",
            "content": message_content,
            "flags": 4,
        }
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
        )
        if response.status_code == 429:
            retry_after = response.json().get("retry_after", 1.5)
            time.sleep(float(retry_after))
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
            )
        response.raise_for_status()
        time.sleep(0.4)

    return True


def _resolve_dossiers_for_cycle(records: list[dict], passed_dossiers: list[dict] | None = None) -> list[dict]:
    """Load or resolve the CaptureDesk Autopilot 21-API dossiers corresponding to the current 6-hour cycle."""
    if passed_dossiers:
        return list(passed_dossiers)
    import json
    dossier_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturedesk_dossiers.json")
    cached: dict = {}
    if os.path.exists(dossier_path):
        try:
            with open(dossier_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    cached = loaded
        except Exception:
            cached = {}

    matched: list[dict] = []
    seen_urls: set[str] = set()
    rec_urls = {str(r.get("url") or "").strip() for r in (records or []) if r.get("url")}
    rec_ids = {str(r.get("id") or "").strip() for r in (records or []) if r.get("id")}

    for rid in rec_ids:
        if rid in cached and isinstance(cached[rid], dict):
            d = cached[rid]
            u = str(d.get("source_url") or "")
            if u not in seen_urls:
                matched.append(d)
                seen_urls.add(u)

    if len(matched) < 2 and cached:
        all_dossiers = [v for v in cached.values() if isinstance(v, dict)]
        all_dossiers.sort(key=lambda x: str(x.get("enriched_at") or ""), reverse=True)
        for d in all_dossiers:
            u = str(d.get("source_url") or "")
            if u in rec_urls and u not in seen_urls:
                matched.append(d)
                seen_urls.add(u)
        for d in all_dossiers:
            if len(matched) >= 3:
                break
            u = str(d.get("source_url") or "")
            if u not in seen_urls:
                matched.append(d)
                seen_urls.add(u)

    return matched[:3]


def format_subscriber_email_briefing(
    tier: str,
    records: list[dict],
    dossiers: list[dict] | None = None,
    to_email: str = "",
) -> tuple[str, str, str]:
    """
    Build an organized, executive-formatted 6-hour email briefing tailored by subscription tier:
      - Tier 1 (`tier_1` / SignalWire Pro):
          Section I: 15-Portal Live RFP Alert Wire (all newly discovered IT/Cyber solicitations with direct official portal links).
      - Tier 2 (`tier_2` / CaptureDesk Autopilot):
          Single Unified 6-Hour Email combining BOTH:
            Section I: CaptureDesk Autopilot 21-API Executive Dossiers (8-part pre-shredded capture memos)
            Section II: Complete 15-Portal Live RFP Alert Wire (all newly discovered IT/Cyber solicitations)
    Returns `(subject, plain_text_body, html_body)`.
    """
    from datetime import datetime, timezone
    from html import escape
    from urllib.parse import quote_plus

    norm_tier = "tier_1" if str(tier or "").strip().lower() in ("tier_1", "tier1", "pro", "signalwire") else "tier_2"
    cycle_ts = datetime.now(timezone.utc).strftime("%b %d, %Y • %H:%M UTC")
    disable_url = (
        f"https://b2b-contract-parser-api.onrender.com/v1/webhooks/email-briefings"
        f"?email={quote_plus(to_email)}&enabled=false"
    )
    resolved_dossiers = _resolve_dossiers_for_cycle(records, dossiers) if norm_tier == "tier_2" else []
    wire_items = (records or [])[:15]
    total_wire = len(records or [])

    fed_count = sum(1 for r in (records or []) if classify_jurisdiction(r) == "federal")
    muni_count = sum(1 for r in (records or []) if classify_jurisdiction(r) == "municipal")
    sled_count = max(0, total_wire - fed_count - muni_count)

    if norm_tier == "tier_1":
        subject = (
            f"[SignalTender // Tier 1 Wire] 6-Hour GovCon RFP Briefing — "
            f"{total_wire} Vetted IT & Cyber Solicitations ({cycle_ts})"
        )
    else:
        subject = (
            f"[SignalTender // Tier 2 Autopilot] 6-Hour Executive Capture Briefing — "
            f"{len(resolved_dossiers)} CaptureDesk 21-API Dossiers + {total_wire} Live Wire RFPs ({cycle_ts})"
        )

    # -------------------------------------------------------------------------
    # 1. Structured Executive Plain-Text Briefing
    # -------------------------------------------------------------------------
    lines: list[str] = []
    rule_heavy = "=" * 78
    rule_light = "-" * 78

    lines.append(rule_heavy)
    if norm_tier == "tier_1":
        lines.append("SIGNALTENDER // TIER 1 — 6-HOUR LIVE RFP ALERT WIRE BRIEFING")
        lines.append(f"Cycle Timestamp : {cycle_ts}")
        lines.append("Plan Tier       : Tier 1 // SignalWire Pro (15 Federal, State SLED & Municipal Portals)")
        lines.append(
            f"Cycle Summary   : {total_wire} Newly Vetted High-Signal IT/Cyber RFPs "
            f"(Federal: {fed_count} | 13-State SLED: {sled_count} | Municipal: {muni_count})"
        )
    else:
        lines.append("SIGNALTENDER // TIER 2 — UNIFIED CAPTUREDESK AUTOPILOT & LIVE RFP WIRE BRIEFING")
        lines.append(f"Cycle Timestamp : {cycle_ts}")
        lines.append("Plan Tier       : Tier 2 // CaptureDesk Autopilot (15 Portals + 21-API Capture Suite)")
        lines.append(
            f"Cycle Summary   : {len(resolved_dossiers)} Pre-Shredded 21-API CaptureDesk Dossiers + "
            f"{total_wire} Newly Vetted Live Wire RFPs (Federal: {fed_count} | SLED: {sled_count} | Municipal: {muni_count})"
        )
        lines.append(rule_light)
        lines.append("TABLE OF CONTENTS (UNIFIED SINGLE-EMAIL BRIEFING)")
        lines.append(
            f"  • SECTION I   : CAPTUREDESK AUTOPILOT 21-API EXECUTIVE DOSSIERS ({len(resolved_dossiers)} Deep-Dive Packages)"
        )
        lines.append(
            f"  • SECTION II  : COMPLETE 15-PORTAL LIVE RFP ALERT WIRE ({len(wire_items)} of {total_wire} Vetted Solicitations)"
        )
        lines.append("  • SECTION III : TIER 2 ENTERPRISE API, MCP & SELF-SERVICE DELIVERY CONTROLS")
    lines.append(rule_heavy)
    lines.append("")

    if norm_tier == "tier_2" and resolved_dossiers:
        lines.append("SECTION I // CAPTUREDESK AUTOPILOT 21-API EXECUTIVE DOSSIERS")
        lines.append("Pre-shredded Bid/No-Go memos, IGCE/Wrap/PTW models, CMMC/NIST/RMF gates, and Shipley win themes.")
        lines.append(rule_light)
        for idx, d in enumerate(resolved_dossiers, start=1):
            d_title = clean_title_text(str(d.get("title") or "Government IT Solicitation"))
            d_agency = str(d.get("agency") or "Government Agency").strip()
            d_due = str(d.get("closing_date") or "Open / See Official Portal").strip()
            d_badge = str(d.get("jurisdiction_badge") or "FEDERAL // SAM.GOV").strip()
            d_vert = str(d.get("vertical") or "Enterprise Software, Data & AI").strip()
            d_naics = str(d.get("primary_naics") or "541512")
            d_psc = str(d.get("primary_psc") or "D399")
            d_nigp = str(d.get("primary_nigp") or "")
            d_sba = str(d.get("sba_size_standard") or "$34.0M")
            d_comp = str(d.get("compliance_posture") or "SOC 2 Type II / NIST 800-53 / Section 508 VPAT")
            d_team = str(d.get("teaming_posture") or "13 CFR § 125.6 (50% Rule) + 3 Past Performance Refs")
            d_ptw = str(d.get("igce_ptw_posture") or "Wrap ~1.80x • Target PTW: -5.5% vs. IGCE")
            d_lcat = str(d.get("key_personnel_lcats") or "Program Manager (PMP) • Lead Solutions Architect")
            d_cpars = str(d.get("cpars_relevance_benchmark") or "Substantial Confidence Target • 3 Very Relevant Refs")
            d_ost = str(d.get("ostensible_sub_risk") or "LOW RISK (13 CFR § 121.103(h)(3))")
            d_src = str(d.get("source_url") or "")
            d_url = str(d.get("dossier_url") or f"{SITE_BASE_URL}/contracts")
            if "?unlocked=1" not in d_url:
                d_url = f"{d_url}?unlocked=1"

            nigp_str = f" | NIGP: {d_nigp}" if d_nigp else ""
            lines.append(f"[DOSSIER #{idx:02d}] [{d_badge}] • {d_vert}")
            lines.append(f"  1. Solicitation Title   : {d_title}")
            lines.append(f"     Issuing Buyer Agency : {d_agency}  |  Closing Date: {d_due}")
            lines.append(
                f"  2. Classification (#02) : NAICS {d_naics} | PSC {d_psc}{nigp_str} | SBA Size: {d_sba}"
            )
            lines.append(f"     Ostensible Sub (#11) : {d_ost}")
            lines.append(f"  3. Cyber & RMF (#06/#18): {d_comp}")
            lines.append(f"  4. IGCE, PTW & MAS (#16): {d_ptw}")
            lines.append(f"  5. Key LCATs & CPARS    : {d_lcat} | {d_cpars}")
            lines.append(f"  6. Teaming Mandate (#11): {d_team}")
            themes = [str(t).replace("**", "").strip() for t in (d.get("win_themes") or [])[:3] if t]
            if themes:
                lines.append("  7. Tailored Shipley Section L/M Win Strategy (#05/#17/#19):")
                for t_item in themes:
                    lines.append(f"       - {t_item}")
            ev_list = [str(e).replace("**", "").strip() for e in (d.get("evidence_needed") or [])[:2] if e]
            if ev_list:
                lines.append("     Required Proposal Evidence:")
                for e_item in ev_list:
                    lines.append(f"       - {e_item}")
            lines.append(f"  8. Official Portal URL  : {d_src}")
            lines.append(f"     21-API Web Dossier   : {d_url}")
            lines.append(rule_light)
        lines.append("")

    wire_section_title = (
        "SECTION II // COMPLETE 15-PORTAL LIVE RFP ALERT WIRE"
        if norm_tier == "tier_2"
        else "SECTION I // 15-PORTAL LIVE RFP ALERT WIRE"
    )
    lines.append(wire_section_title)
    lines.append(
        "All newly discovered, AI-vetted IT, Cloud, Cybersecurity & Software RFPs across 15 government portals."
    )
    lines.append(rule_light)

    for idx, rec in enumerate(wire_items, start=1):
        raw_title = str(rec.get("title") or "N/A").strip()
        clean_title = clean_title_text(raw_title)
        agency = str(rec.get("agency") or "Government Agency").strip()
        closing_date = str(rec.get("closing_date") or "").strip()
        if not closing_date:
            m_due = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", raw_title, flags=re.IGNORECASE)
            closing_date = m_due.group(1) if m_due else "Open / See Official Portal"
        link = str(rec.get("url") or "N/A").strip()
        rec_id = str(rec.get("id") or "")
        j_key = classify_jurisdiction(rec)
        j_badge = JURISDICTION_LABELS.get(j_key, "FEDERAL // SAM.GOV")
        vertical = classify_vertical_tag(rec)
        slug = slugify_contract(raw_title, fallback_id=rec_id)
        dossier_url = f"{SITE_BASE_URL}/contracts/rfp/{slug}.html?unlocked=1"

        lines.append(f"[{idx:02d}] [{j_badge}] • {vertical}")
        lines.append(f"     Solicitation    : {clean_title}")
        lines.append(f"     Buyer Agency    : {agency}  |  Closing Date: {closing_date}")
        lines.append(f"     Official Portal : {link}")
        lines.append(f"     Unlocked Brief  : {dossier_url}")
        lines.append(rule_light)

    lines.append("")
    ctrl_section_title = (
        "SECTION III // TIER 2 ENTERPRISE API, MCP & DELIVERY CONTROLS"
        if norm_tier == "tier_2"
        else "SECTION II // SUBSCRIBER DIRECTORY & DELIVERY CONTROLS"
    )
    lines.append(ctrl_section_title)
    lines.append(f"  • Full 15-Portal Live Directory (Un-Blurred) : {SITE_BASE_URL}/contracts")
    if norm_tier == "tier_2":
        lines.append(f"  • 21-API GovCon Capture Studio               : {SITE_BASE_URL}/apis.html")
        lines.append("  • Remote Streamable-HTTP MCP Server          : https://b2b-contract-parser-api.onrender.com/mcp")
    lines.append(f"  • Manage Discord / Webhook / Email Settings  : {SITE_BASE_URL}/#checkout")
    lines.append(f"  • 1-Click Turn OFF 6-Hour Email Briefings    : {disable_url}")
    lines.append(rule_heavy)

    plain_body = "\n".join(lines)

    # -------------------------------------------------------------------------
    # 2. Executive HTML Briefing (for Resend & SMTP clients)
    # -------------------------------------------------------------------------
    tier_pill = (
        "TIER 2 // CAPTUREDESK AUTOPILOT (UNIFIED DOSSIERS + LIVE WIRE)"
        if norm_tier == "tier_2"
        else "TIER 1 // SIGNALWIRE PRO (15-PORTAL LIVE RFP WIRE)"
    )
    tier_accent = "#6366f1" if norm_tier == "tier_2" else "#0ea5e9"

    dossier_html_cards = []
    if norm_tier == "tier_2" and resolved_dossiers:
        for idx, d in enumerate(resolved_dossiers, start=1):
            d_title = escape(clean_title_text(str(d.get("title") or "Government IT Solicitation")))
            d_agency = escape(str(d.get("agency") or "Government Agency").strip())
            d_due = escape(str(d.get("closing_date") or "Open / See Official Portal").strip())
            d_badge = escape(str(d.get("jurisdiction_badge") or "FEDERAL // SAM.GOV").strip())
            d_vert = escape(str(d.get("vertical") or "Enterprise Software, Data & AI").strip())
            d_naics = escape(str(d.get("primary_naics") or "541512"))
            d_psc = escape(str(d.get("primary_psc") or "D399"))
            d_sba = escape(str(d.get("sba_size_standard") or "$34.0M"))
            d_comp = escape(str(d.get("compliance_posture") or "SOC 2 Type II / NIST 800-53"))
            d_team = escape(str(d.get("teaming_posture") or "13 CFR § 125.6 (50% Rule)"))
            d_ptw = escape(str(d.get("igce_ptw_posture") or "Wrap ~1.80x • Target PTW: -5.5% vs. IGCE"))
            d_lcat = escape(str(d.get("key_personnel_lcats") or "Program Manager (PMP) • Lead Architect"))
            d_src = escape(str(d.get("source_url") or "#"))
            raw_durl = str(d.get("dossier_url") or f"{SITE_BASE_URL}/contracts")
            if "?unlocked=1" not in raw_durl:
                raw_durl = f"{raw_durl}?unlocked=1"
            d_url = escape(raw_durl)
            themes_li = "".join(
                f"<li style='margin-bottom:4px;'>{escape(str(t).replace('**', '').strip())}</li>"
                for t in (d.get("win_themes") or [])[:3]
                if t
            )
            dossier_html_cards.append(
                f"""
                <div style="border:1px solid #312e81;background:#0f172a;border-radius:10px;padding:16px;margin-bottom:14px;">
                  <div style="font-family:monospace;font-size:11px;color:#a5b4fc;margin-bottom:6px;">
                    <strong>[DOSSIER #{idx:02d}] {d_badge}</strong> &bull; {d_vert}
                  </div>
                  <div style="font-size:15px;font-weight:700;color:#ffffff;margin-bottom:6px;">{d_title}</div>
                  <div style="font-size:12px;color:#cbd5e1;margin-bottom:10px;">
                    <strong>Buyer Agency:</strong> {d_agency} &nbsp;|&nbsp; <strong>Closing Date:</strong> <span style="color:#34d399;font-family:monospace;">{d_due}</span>
                  </div>
                  <table style="width:100%;border-collapse:collapse;font-size:12px;color:#e2e8f0;margin-bottom:10px;">
                    <tr><td style="padding:4px 0;color:#94a3b8;width:190px;">Taxonomic &amp; SBA Size (#02):</td><td style="padding:4px 0;font-family:monospace;">NAICS {d_naics} | PSC {d_psc} | SBA Size {d_sba}</td></tr>
                    <tr><td style="padding:4px 0;color:#94a3b8;">Cyber &amp; RMF Gates (#06/#18):</td><td style="padding:4px 0;">{d_comp}</td></tr>
                    <tr><td style="padding:4px 0;color:#94a3b8;">IGCE, Wrap &amp; PTW (#16/#20):</td><td style="padding:4px 0;color:#6ee7b7;">{d_ptw}</td></tr>
                    <tr><td style="padding:4px 0;color:#94a3b8;">Key Personnel LCATs (#13):</td><td style="padding:4px 0;">{d_lcat}</td></tr>
                    <tr><td style="padding:4px 0;color:#94a3b8;">Teaming &amp; Sub Goal (#11):</td><td style="padding:4px 0;">{d_team}</td></tr>
                  </table>
                  <div style="font-size:12px;color:#cbd5e1;margin-bottom:10px;">
                    <strong style="color:#a5b4fc;">Tailored Shipley Section L/M Win Strategy (#05/#17/#19):</strong>
                    <ul style="margin:6px 0 0 18px;padding:0;">{themes_li}</ul>
                  </div>
                  <div style="margin-top:10px;">
                    <a href="{d_src}" style="display:inline-block;padding:7px 12px;background:#1e293b;color:#38bdf8;text-decoration:none;border-radius:6px;font-size:12px;font-family:monospace;border:1px solid #334155;margin-right:8px;">Official Portal Bid &nearr;</a>
                    <a href="{d_url}" style="display:inline-block;padding:7px 12px;background:#4f46e5;color:#ffffff;text-decoration:none;border-radius:6px;font-size:12px;font-family:monospace;font-weight:700;">Open Full 21-API Dossier &rarr;</a>
                  </div>
                </div>
                """
            )

    wire_html_rows = []
    for idx, rec in enumerate(wire_items, start=1):
        raw_title = str(rec.get("title") or "N/A").strip()
        clean_title = escape(clean_title_text(raw_title))
        agency = escape(str(rec.get("agency") or "Government Agency").strip())
        closing_date = str(rec.get("closing_date") or "").strip()
        if not closing_date:
            m_due = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", raw_title, flags=re.IGNORECASE)
            closing_date = m_due.group(1) if m_due else "Open / See Official Portal"
        closing_date = escape(closing_date)
        link = escape(str(rec.get("url") or "#").strip())
        rec_id = str(rec.get("id") or "")
        j_key = classify_jurisdiction(rec)
        j_badge = escape(JURISDICTION_LABELS.get(j_key, "FEDERAL // SAM.GOV"))
        vertical = escape(classify_vertical_tag(rec))
        slug = slugify_contract(raw_title, fallback_id=rec_id)
        dossier_url = escape(f"{SITE_BASE_URL}/contracts/rfp/{slug}.html?unlocked=1")

        wire_html_rows.append(
            f"""
            <div style="border:1px solid #1e293b;background:#0f172a;border-radius:8px;padding:12px 14px;margin-bottom:10px;">
              <div style="font-family:monospace;font-size:11px;color:#38bdf8;margin-bottom:4px;">
                <strong>[{idx:02d}] {j_badge}</strong> &bull; <span style="color:#94a3b8;">{vertical}</span>
              </div>
              <div style="font-size:14px;font-weight:600;color:#f8fafc;margin-bottom:4px;">{clean_title}</div>
              <div style="font-size:12px;color:#cbd5e1;margin-bottom:8px;">
                <strong>Buyer:</strong> {agency} &nbsp;|&nbsp; <strong>Due:</strong> <span style="color:#34d399;font-family:monospace;">{closing_date}</span>
              </div>
              <div>
                <a href="{link}" style="color:#38bdf8;font-size:12px;font-family:monospace;text-decoration:none;margin-right:14px;">Official Government Portal &nearr;</a>
                <a href="{dossier_url}" style="color:#a5b4fc;font-size:12px;font-family:monospace;text-decoration:none;">Unlocked SignalTender Brief &rarr;</a>
              </div>
            </div>
            """
        )

    section_i_html = ""
    if norm_tier == "tier_2" and dossier_html_cards:
        section_i_html = f"""
        <div style="margin-top:18px;margin-bottom:22px;">
          <div style="font-family:monospace;font-size:12px;font-weight:700;color:#a5b4fc;letter-spacing:0.05em;text-transform:uppercase;border-bottom:1px solid #312e81;padding-bottom:6px;margin-bottom:12px;">
            SECTION I // CAPTUREDESK AUTOPILOT 21-API EXECUTIVE DOSSIERS ({len(resolved_dossiers)} PACKAGES)
          </div>
          {''.join(dossier_html_cards)}
        </div>
        """

    wire_header_label = (
        f"SECTION II // COMPLETE 15-PORTAL LIVE RFP ALERT WIRE ({len(wire_items)} OF {total_wire} SOLICITATIONS)"
        if norm_tier == "tier_2"
        else f"SECTION I // 15-PORTAL LIVE RFP ALERT WIRE ({len(wire_items)} OF {total_wire} SOLICITATIONS)"
    )

    html_body = f"""
    <div style="background:#020617;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:24px;max-width:760px;margin:0 auto;border-radius:12px;border:1px solid #1e293b;">
      <div style="border-bottom:2px solid {tier_accent};padding-bottom:14px;margin-bottom:16px;">
        <div style="font-family:monospace;font-size:11px;color:{tier_accent};font-weight:700;letter-spacing:0.06em;">{escape(tier_pill)}</div>
        <h2 style="margin:6px 0 4px 0;font-size:20px;color:#ffffff;">SignalTender 6-Hour GovCon Capture Briefing</h2>
        <div style="font-size:12px;color:#94a3b8;font-family:monospace;">
          Cycle: {escape(cycle_ts)} &bull; Federal: {fed_count} | 13-State SLED: {sled_count} | Municipal: {muni_count}
        </div>
      </div>
      {section_i_html}
      <div style="margin-top:14px;margin-bottom:20px;">
        <div style="font-family:monospace;font-size:12px;font-weight:700;color:#38bdf8;letter-spacing:0.05em;text-transform:uppercase;border-bottom:1px solid #1e293b;padding-bottom:6px;margin-bottom:12px;">
          {escape(wire_header_label)}
        </div>
        {''.join(wire_html_rows)}
      </div>
      <div style="border-top:1px solid #1e293b;padding-top:14px;font-size:12px;color:#94a3b8;line-height:1.6;">
        <div><strong>Subscriber Quick Links:</strong> <a href="{SITE_BASE_URL}/contracts" style="color:#38bdf8;">Live 15-Portal Directory</a> &bull; <a href="{SITE_BASE_URL}/#checkout" style="color:#38bdf8;">Delivery Settings</a> &bull; <a href="{escape(disable_url)}" style="color:#f87171;">Pause Email Briefings</a></div>
      </div>
    </div>
    """.strip()

    return subject, plain_body, html_body


def _send_subscriber_email_briefing(
    to_email: str,
    records: list[dict],
    tier: str = "tier_2",
    dossiers: list[dict] | None = None,
) -> bool:
    """
    Send an organized, tier-specific 6-hour briefing email ONLY to active subscribers
    who opted in (`email_briefings_enabled: True`).
    Tier 2 subscribers receive BOTH CaptureDesk Autopilot 21-API Dossiers (Section I)
    and the Complete 15-Portal Live RFP Alert Wire (Section II) in the same single email.
    """
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASSWORD", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user or "aaron@getsignaltender.com").strip()

    subject, plain_body, html_body = format_subscriber_email_briefing(
        tier=tier,
        records=records,
        dossiers=dossiers,
        to_email=to_email,
    )
    sender_label = (
        "SignalTender CaptureDesk Autopilot"
        if str(tier or "").strip().lower() not in ("tier_1", "tier1", "pro", "signalwire")
        else "SignalTender Live RFP Wire"
    )
    try:
        if resend_key:
            r = requests.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                json={
                    "from": f"{sender_label} <{from_email}>",
                    "to": [to_email],
                    "subject": subject,
                    "text": plain_body,
                    "html": html_body,
                },
                timeout=10,
            )
            return r.status_code in (200, 201)
        elif smtp_user and smtp_pass:
            import smtplib, ssl
            from email.message import EmailMessage
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = f"{sender_label} <{from_email}>"
            msg["To"] = to_email
            msg.set_content(plain_body)
            msg.add_alternative(html_body, subtype="html")
            with smtplib.SMTP(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT") or "587"), timeout=10) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(smtp_user, smtp_pass)
                s.send_message(msg)
            return True
        inst_key = os.getenv("INSTANTLY_API_KEY", "").strip()
        inst_sub_cid = os.getenv("INSTANTLY_SUBSCRIBER_CAMPAIGN_ID", "748eecf5-6b63-4dff-b9f2-1d2ff1a4a96f").strip()
        if inst_key and inst_sub_cid:
            r = requests.post(
                "https://api.instantly.ai/api/v2/leads",
                headers={"Authorization": f"Bearer {inst_key}", "Content-Type": "application/json"},
                json={
                    "campaign": inst_sub_cid,
                    "email": to_email,
                    "skip_if_in_campaign": False,
                    "custom_variables": {"subject_line": subject, "email_body": plain_body},
                },
                timeout=10,
            )
            if r.status_code in (200, 201):
                requests.post(
                    f"https://api.instantly.ai/api/v2/campaigns/{inst_sub_cid}/activate",
                    headers={"Authorization": f"Bearer {inst_key}", "Content-Type": "application/json"},
                    json={},
                    timeout=10,
                )
                return True
    except Exception:
        pass
    return False


def format_external_webhook_payload(
    tier: str,
    webhook_url: str,
    records: list[dict],
    dossiers: list[dict] | None = None,
    destination_type: str = "auto",
) -> dict:
    """
    Build an organized, platform-native 6-hour external webhook payload tailored by
    both Subscription Tier (`tier_1` vs `tier_2`) and Destination Platform (`Slack`,
    `Microsoft Teams`, `Discord`, or `CRM / Zapier / Make.com / n8n / HubSpot / Salesforce`):
      - Tier 1 (`tier_1` / SignalWire Pro):
          Section I: 15-Portal Live RFP Alert Wire (all newly discovered IT/Cyber solicitations).
      - Tier 2 (`tier_2` / CaptureDesk Autopilot):
          Single Unified 6-Hour Dispatch combining BOTH:
            Section I: CaptureDesk Autopilot 21-API Executive Dossiers (8-part pre-shredded memos)
            Section II: Complete 15-Portal Live RFP Alert Wire (all newly discovered IT/Cyber solicitations)
    """
    from datetime import datetime, timezone

    norm_tier = "tier_1" if str(tier or "").strip().lower() in ("tier_1", "tier1", "pro", "signalwire") else "tier_2"
    u_low = str(webhook_url or "").strip().lower()
    d_hint = str(destination_type or "auto").strip().lower()

    if "hooks.slack.com" in u_low or d_hint == "slack":
        platform = "slack"
    elif "webhook.office.com" in u_low or "logic.azure.com" in u_low or d_hint == "teams":
        platform = "teams"
    elif "discord.com/api/webhooks" in u_low or "discordapp.com/api/webhooks" in u_low or d_hint == "discord":
        platform = "discord"
    else:
        platform = d_hint if d_hint not in ("", "auto") else "crm_webhook"

    cycle_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cycle_label = datetime.now(timezone.utc).strftime("%b %d, %Y • %H:%M UTC")
    resolved_dossiers = _resolve_dossiers_for_cycle(records, dossiers) if norm_tier == "tier_2" else []
    wire_items = (records or [])[:12]
    total_wire = len(records or [])

    fed_count = sum(1 for r in (records or []) if classify_jurisdiction(r) == "federal")
    muni_count = sum(1 for r in (records or []) if classify_jurisdiction(r) == "municipal")
    sled_count = max(0, total_wire - fed_count - muni_count)

    # 1. Native Slack `mrkdwn` Formatting (`*bold*`, `<url|Label>`)
    if platform == "slack":
        s_lines: list[str] = []
        if norm_tier == "tier_1":
            s_lines.append("*SIGNALTENDER // TIER 1 — 6-HOUR LIVE RFP ALERT WIRE*")
            s_lines.append(
                f"`Cycle: {cycle_label}` • *{total_wire} Vetted IT/Cyber RFPs* "
                f"(Federal: `{fed_count}` | 13-State SLED: `{sled_count}` | Municipal: `{muni_count}`)"
            )
            s_lines.append("─" * 46)
            s_lines.append("*SECTION I // 15-PORTAL LIVE RFP ALERT WIRE*")
        else:
            s_lines.append("*SIGNALTENDER // TIER 2 — UNIFIED 6-HOUR CAPTUREDESK AUTOPILOT & LIVE WIRE BRIEFING*")
            s_lines.append(
                f"`Cycle: {cycle_label}` • *{len(resolved_dossiers)} CaptureDesk 21-API Dossiers* + "
                f"*{total_wire} Live Wire RFPs* (Federal: `{fed_count}` | SLED: `{sled_count}` | Municipal: `{muni_count}`)"
            )
            s_lines.append(
                "• *Section I:* CaptureDesk Autopilot 21-API Executive Dossiers\n"
                "• *Section II:* Complete 15-Portal Live RFP Alert Wire"
            )
            s_lines.append("─" * 46)
            if resolved_dossiers:
                s_lines.append("*SECTION I // CAPTUREDESK AUTOPILOT 21-API EXECUTIVE DOSSIERS*")
                for idx, d in enumerate(resolved_dossiers, start=1):
                    d_title = clean_title_text(str(d.get("title") or "Government IT Solicitation"))
                    d_agency = str(d.get("agency") or "Government Agency").strip()
                    d_due = str(d.get("closing_date") or "Open / See Official Portal").strip()
                    d_badge = str(d.get("jurisdiction_badge") or "FEDERAL // SAM.GOV").strip()
                    d_vert = str(d.get("vertical") or "Enterprise Software, Data & AI").strip()
                    d_naics = str(d.get("primary_naics") or "541512")
                    d_psc = str(d.get("primary_psc") or "D399")
                    d_sba = str(d.get("sba_size_standard") or "$34.0M")
                    d_comp = str(d.get("compliance_posture") or "SOC 2 Type II / NIST 800-53")
                    d_ptw = str(d.get("igce_ptw_posture") or "Wrap ~1.80x • Target PTW: -5.5% vs. IGCE")
                    d_lcat = str(d.get("key_personnel_lcats") or "Program Manager (PMP) • Lead Solutions Architect")
                    d_team = str(d.get("teaming_posture") or "13 CFR § 125.6 (50% Rule)")
                    d_src = str(d.get("source_url") or f"{SITE_BASE_URL}/contracts")
                    d_url = str(d.get("dossier_url") or f"{SITE_BASE_URL}/contracts")
                    if "?unlocked=1" not in d_url:
                        d_url = f"{d_url}?unlocked=1"
                    themes = [str(t).replace("**", "").strip() for t in (d.get("win_themes") or [])[:2] if t]
                    theme_str = "\n".join(f"    ◦ {t}" for t in themes)

                    s_lines.append(f"*[DOSSIER #{idx:02d}] [{d_badge}]* • `{d_vert}`")
                    s_lines.append(f"  *1. Solicitation:* {d_title}")
                    s_lines.append(f"  *2. Buyer & Deadline:* {d_agency} | Due: `{d_due}`")
                    s_lines.append(f"  *3. Classification (#02/#11):* NAICS `{d_naics}` | PSC `{d_psc}` | SBA Size `{d_sba}`")
                    s_lines.append(f"  *4. Cyber & RMF Gates (#06/#18):* `{d_comp}`")
                    s_lines.append(f"  *5. IGCE, Wrap & PTW (#16/#20):* `{d_ptw}`")
                    s_lines.append(f"  *6. Key LCATs & Teaming (#11/#13):* `{d_lcat}` | `{d_team}`")
                    if theme_str:
                        s_lines.append(f"  *7. Shipley Section L/M Win Strategy (#05/#17/#19):*\n{theme_str}")
                    s_lines.append(f"  *8. Action Links:* <{d_src}|Official Portal Bid ↗>  |  <{d_url}|Open Full 21-API Dossier →>")
                    s_lines.append("─" * 46)
            s_lines.append("*SECTION II // COMPLETE 15-PORTAL LIVE RFP ALERT WIRE*")

        for idx, rec in enumerate(wire_items[:10], start=1):
            raw_title = str(rec.get("title") or "N/A").strip()
            clean_title = clean_title_text(raw_title)
            agency = str(rec.get("agency") or "Government Agency").strip()
            closing_date = str(rec.get("closing_date") or "").strip() or "Open / See Official Portal"
            link = str(rec.get("url") or f"{SITE_BASE_URL}/contracts").strip()
            rec_id = str(rec.get("id") or "")
            j_badge = JURISDICTION_LABELS.get(classify_jurisdiction(rec), "FEDERAL // SAM.GOV")
            vertical = classify_vertical_tag(rec)
            slug = slugify_contract(raw_title, fallback_id=rec_id)
            dossier_url = f"{SITE_BASE_URL}/contracts/rfp/{slug}.html?unlocked=1"
            s_lines.append(
                f"*[{idx:02d}] [{j_badge}]* • `{vertical}`\n"
                f"  • *Solicitation:* {clean_title}\n"
                f"  • *Buyer:* {agency} | *Due:* `{closing_date}`\n"
                f"  • <{link}|Official Government Portal ↗>  |  <{dossier_url}|Unlocked SignalTender Brief →>"
            )
        s_lines.append(f"<{SITE_BASE_URL}/contracts|View Full 15-Portal Directory> • <{SITE_BASE_URL}/#checkout|Delivery Settings>")
        return {"text": "\n".join(s_lines)}

    # 2. Native Microsoft Teams Markdown Card (`**bold**`, `[Label](url)`)
    if platform == "teams":
        t_lines: list[str] = []
        if norm_tier == "tier_1":
            t_lines.append("### SIGNALTENDER // TIER 1 — 6-HOUR LIVE RFP ALERT WIRE")
            t_lines.append(
                f"**Cycle:** `{cycle_label}` | **Total Vetted RFPs:** `{total_wire}` "
                f"(Federal: `{fed_count}` • 13-State SLED: `{sled_count}` • Municipal: `{muni_count}`)"
            )
            t_lines.append("---")
            t_lines.append("#### SECTION I // 15-PORTAL LIVE RFP ALERT WIRE")
        else:
            t_lines.append("### SIGNALTENDER // TIER 2 — UNIFIED 6-HOUR CAPTUREDESK AUTOPILOT & LIVE WIRE BRIEFING")
            t_lines.append(
                f"**Cycle:** `{cycle_label}` | **{len(resolved_dossiers)} CaptureDesk 21-API Dossiers** + "
                f"**{total_wire} Live Wire RFPs** (Federal: `{fed_count}` • SLED: `{sled_count}` • Municipal: `{muni_count}`)"
            )
            t_lines.append(
                "- **Section I:** CaptureDesk Autopilot 21-API Executive Dossiers\n"
                "- **Section II:** Complete 15-Portal Live RFP Alert Wire"
            )
            t_lines.append("---")
            if resolved_dossiers:
                t_lines.append("#### SECTION I // CAPTUREDESK AUTOPILOT 21-API EXECUTIVE DOSSIERS")
                for idx, d in enumerate(resolved_dossiers, start=1):
                    d_title = clean_title_text(str(d.get("title") or "Government IT Solicitation"))
                    d_agency = str(d.get("agency") or "Government Agency").strip()
                    d_due = str(d.get("closing_date") or "Open / See Official Portal").strip()
                    d_badge = str(d.get("jurisdiction_badge") or "FEDERAL // SAM.GOV").strip()
                    d_vert = str(d.get("vertical") or "Enterprise Software, Data & AI").strip()
                    d_naics = str(d.get("primary_naics") or "541512")
                    d_psc = str(d.get("primary_psc") or "D399")
                    d_sba = str(d.get("sba_size_standard") or "$34.0M")
                    d_comp = str(d.get("compliance_posture") or "SOC 2 Type II / NIST 800-53")
                    d_ptw = str(d.get("igce_ptw_posture") or "Wrap ~1.80x • Target PTW: -5.5% vs. IGCE")
                    d_lcat = str(d.get("key_personnel_lcats") or "Program Manager (PMP) • Lead Solutions Architect")
                    d_team = str(d.get("teaming_posture") or "13 CFR § 125.6 (50% Rule)")
                    d_src = str(d.get("source_url") or f"{SITE_BASE_URL}/contracts")
                    d_url = str(d.get("dossier_url") or f"{SITE_BASE_URL}/contracts")
                    if "?unlocked=1" not in d_url:
                        d_url = f"{d_url}?unlocked=1"
                    t_lines.append(
                        f"**[DOSSIER #{idx:02d}] [{d_badge}]** • `{d_vert}`\n"
                        f"- **1. Solicitation:** {d_title}\n"
                        f"- **2. Buyer & Deadline:** {d_agency} | Due: `{d_due}`\n"
                        f"- **3. Classification (#02/#11):** NAICS `{d_naics}` | PSC `{d_psc}` | SBA Size `{d_sba}`\n"
                        f"- **4. Cyber & RMF Gates (#06/#18):** `{d_comp}`\n"
                        f"- **5. IGCE, Wrap & PTW (#16/#20):** `{d_ptw}`\n"
                        f"- **6. Key LCATs & Teaming (#11/#13):** `{d_lcat}` | `{d_team}`\n"
                        f"- **7. Action Links:** [Official Portal Bid ↗]({d_src}) | [Open Full 21-API Dossier →]({d_url})"
                    )
                t_lines.append("---")
            t_lines.append("#### SECTION II // COMPLETE 15-PORTAL LIVE RFP ALERT WIRE")

        for idx, rec in enumerate(wire_items[:10], start=1):
            raw_title = str(rec.get("title") or "N/A").strip()
            clean_title = clean_title_text(raw_title)
            agency = str(rec.get("agency") or "Government Agency").strip()
            closing_date = str(rec.get("closing_date") or "").strip() or "Open / See Official Portal"
            link = str(rec.get("url") or f"{SITE_BASE_URL}/contracts").strip()
            rec_id = str(rec.get("id") or "")
            j_badge = JURISDICTION_LABELS.get(classify_jurisdiction(rec), "FEDERAL // SAM.GOV")
            vertical = classify_vertical_tag(rec)
            slug = slugify_contract(raw_title, fallback_id=rec_id)
            dossier_url = f"{SITE_BASE_URL}/contracts/rfp/{slug}.html?unlocked=1"
            t_lines.append(
                f"**[{idx:02d}] [{j_badge}]** • `{vertical}` — **{clean_title}**\n"
                f"Buyer: {agency} | Due: `{closing_date}` | [Official Government Portal ↗]({link}) | [Unlocked Brief →]({dossier_url})"
            )
        return {"text": "\n\n".join(t_lines)}

    # 3. Customer-Owned Discord Webhook (`flags: 4` suppress embeds, <= 1950 chars)
    if platform == "discord":
        blocks = []
        char_total = 0
        if norm_tier == "tier_2" and resolved_dossiers:
            header = "**[TIER 2 // UNIFIED 6-HR BRIEFING: CAPTUREDESK DOSSIERS + LIVE WIRE]**\n"
            blocks.append(header)
            char_total += len(header)
            d0 = resolved_dossiers[0]
            d_url = str(d0.get("dossier_url") or f"{SITE_BASE_URL}/contracts")
            if "?unlocked=1" not in d_url:
                d_url = f"{d_url}?unlocked=1"
            d_block = (
                f"**[SECTION I // CAPTUREDESK 21-API DOSSIER]** `{d0.get('jurisdiction_badge', 'FEDERAL')}`\n"
                f"**Solicitation:** {clean_title_text(str(d0.get('title') or ''))}\n"
                f"**NAICS/PSC:** `{d0.get('primary_naics', '541512')}` | `{d0.get('primary_psc', 'D399')}` | **IGCE/PTW:** `{d0.get('igce_ptw_posture', '')}`\n"
                f"**Cyber/RMF:** `{d0.get('compliance_posture', '')}`\n"
                f"**Official Portal:** <{d0.get('source_url', '')}> | **21-API Dossier:** <{d_url}>\n"
                f"{'─' * 44}"
            )
            blocks.append(d_block)
            char_total += len(d_block) + 2
        for rec in wire_items[:8]:
            b = format_lead_block(rec)
            if char_total + len(b) + 4 > 1900 and blocks:
                break
            blocks.append(b)
            char_total += len(b) + 4
        return {
            "username": "SignalTender CaptureDesk Autopilot" if norm_tier == "tier_2" else "SignalWire Pro",
            "content": "\n\n".join(blocks),
            "flags": 4,
        }

    # 4. Structured CRM & Automation Webhook JSON (HubSpot, Salesforce, Zapier, Make.com, n8n, Custom HTTPS)
    _, plain_summary, _ = format_subscriber_email_briefing(
        tier=norm_tier,
        records=records,
        dossiers=resolved_dossiers,
        to_email="",
    )
    live_wire_structured = []
    for idx, r in enumerate((records or [])[:25], start=1):
        raw_title = str(r.get("title") or "").strip()
        rec_id = str(r.get("id") or "")
        j_key = classify_jurisdiction(r)
        slug = slugify_contract(raw_title, fallback_id=rec_id)
        live_wire_structured.append(
            {
                "index": idx,
                "id": rec_id,
                "title": clean_title_text(raw_title),
                "agency": r.get("agency"),
                "closing_date": r.get("closing_date"),
                "jurisdiction": j_key,
                "jurisdiction_label": JURISDICTION_LABELS.get(j_key, "FEDERAL // SAM.GOV"),
                "vertical": classify_vertical_tag(r),
                "official_bid_url": r.get("url"),
                "unlocked_dossier_url": f"{SITE_BASE_URL}/contracts/rfp/{slug}.html?unlocked=1",
            }
        )

    if norm_tier == "tier_1":
        return {
            "event": "signaltender.cycle_briefing.dispatched",
            "tier": "tier_1",
            "tier_name": "Tier 1 // SignalWire Pro (15-Portal Live RFP Alert Wire)",
            "platform": platform,
            "cycle_timestamp_utc": cycle_iso,
            "summary": {
                "total_live_wire_contracts": total_wire,
                "capturedesk_dossiers_included": 0,
                "federal_count": fed_count,
                "state_sled_count": sled_count,
                "municipal_count": muni_count,
            },
            "section_1_live_wire_contracts": live_wire_structured,
            "contracts": live_wire_structured,
            "text": plain_summary,
            "content": plain_summary,
        }

    dossiers_structured = []
    for idx, d in enumerate(resolved_dossiers, start=1):
        d_url = str(d.get("dossier_url") or f"{SITE_BASE_URL}/contracts")
        if "?unlocked=1" not in d_url:
            d_url = f"{d_url}?unlocked=1"
        dossiers_structured.append(
            {
                "dossier_index": idx,
                "id": str(d.get("id") or ""),
                "title": clean_title_text(str(d.get("title") or "")),
                "agency": d.get("agency"),
                "closing_date": d.get("closing_date"),
                "jurisdiction_badge": d.get("jurisdiction_badge"),
                "vertical": d.get("vertical"),
                "primary_naics": d.get("primary_naics"),
                "primary_psc": d.get("primary_psc"),
                "primary_nigp": d.get("primary_nigp"),
                "sba_size_standard": d.get("sba_size_standard"),
                "ostensible_sub_risk": d.get("ostensible_sub_risk"),
                "compliance_posture": d.get("compliance_posture"),
                "igce_ptw_posture": d.get("igce_ptw_posture"),
                "key_personnel_lcats": d.get("key_personnel_lcats"),
                "cpars_relevance_benchmark": d.get("cpars_relevance_benchmark"),
                "teaming_posture": d.get("teaming_posture"),
                "win_themes": d.get("win_themes", []),
                "evidence_needed": d.get("evidence_needed", []),
                "official_bid_url": d.get("source_url"),
                "unlocked_dossier_url": d_url,
            }
        )

    return {
        "event": "signaltender.cycle_briefing.dispatched",
        "tier": "tier_2",
        "tier_name": "Tier 2 // CaptureDesk Autopilot (Unified 21-API Dossiers + 15-Portal Live Wire)",
        "platform": platform,
        "cycle_timestamp_utc": cycle_iso,
        "summary": {
            "capturedesk_dossiers_included": len(dossiers_structured),
            "total_live_wire_contracts": total_wire,
            "federal_count": fed_count,
            "state_sled_count": sled_count,
            "municipal_count": muni_count,
        },
        "section_1_capturedesk_dossiers": dossiers_structured,
        "section_2_live_wire_contracts": live_wire_structured,
        "contracts": live_wire_structured,
        "text": plain_summary,
        "content": plain_summary,
    }


def _dispatch_to_external_customer_webhooks(
    supabase: Client,
    records: list[dict],
    dossiers: list[dict] | None = None,
) -> int:
    """
    Dispatch newly discovered RFPs to any active subscriber external webhooks
    (Slack, Microsoft Teams, Zapier, Make.com, n8n, HubSpot, Salesforce) AND
    dispatch tier-specific 6-Hour Email Briefings (with Tier 2 combining both
    CaptureDesk Autopilot 21-API Dossiers and the Live RFP Alert Wire in one unified package)
    stored in Supabase with status='SUBSCRIBER_ACTIVE'.
    """
    import json
    dispatched = 0
    try:
        sub_resp = supabase.table(TABLE_NAME).select("title,status").eq("status", "SUBSCRIBER_ACTIVE").execute()
        sub_rows = sub_resp.data if sub_resp and getattr(sub_resp, "data", None) else []
    except Exception:
        sub_rows = []

    if not sub_rows or not records:
        return 0

    for srow in sub_rows:
        try:
            if str(srow.get("status") or "") != "SUBSCRIBER_ACTIVE":
                continue
            meta = json.loads(str(srow.get("title") or "{}"))
            sub_tier = str(meta.get("tier") or "tier_2").strip().lower()
            if str(meta.get("status") or "") == "canceled" or sub_tier == "canceled":
                continue
            sub_email = str(meta.get("email") or "").strip().lower()
            if sub_email and "@" in sub_email and bool(meta.get("email_briefings_enabled", False)):
                team_cc = meta.get("team_cc_emails") if isinstance(meta.get("team_cc_emails"), list) else []
                email_recipients = [sub_email] + [str(cc).strip().lower() for cc in team_cc if "@" in str(cc) and str(cc).strip().lower() != sub_email][:5]
                for recip_email in email_recipients:
                    _send_subscriber_email_briefing(
                        to_email=recip_email,
                        records=records,
                        tier=sub_tier,
                        dossiers=dossiers,
                    )
            w_url = str(meta.get("webhook_url") or "").strip()
            if not w_url.startswith("https://"):
                continue
            dest_type = str(meta.get("destination_type") or "auto").strip()
            payload = format_external_webhook_payload(
                tier=sub_tier,
                webhook_url=w_url,
                records=records,
                dossiers=dossiers,
                destination_type=dest_type,
            )
            requests.post(w_url, json=payload, timeout=10)
            dispatched += 1
        except Exception as ext_err:
            print(f"[!] External customer webhook warning: {ext_err}", flush=True)
    return dispatched


def _parse_closing_date_obj(date_str: str, title: str = ""):
    from datetime import datetime
    candidates = [str(date_str or "").strip()]
    m_due = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", str(title or ""), flags=re.IGNORECASE)
    if m_due:
        candidates.append(m_due.group(1))
    for cand in candidates:
        if not cand or cand.lower() in ("n/a", "tbd", "none", "null", "open", ""):
            continue
        if "T" in cand:
            cand = cand.split("T")[0].strip()
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
            try:
                return datetime.strptime(cand, fmt).date()
            except ValueError:
                pass
    return None


def _dispatch_closing_soon_nudges_for_inbound_leads(supabase: Client) -> int:
    """
    Upgrade #4 (72-Hour / 5-Day Deadline Urgency Nudge):
    Checks verified Free Explorer / Inbound Dossier leads (`SUBSCRIBER_INBOUND_LEAD`) who have not
    yet converted to `SUBSCRIBER_ACTIVE`. When an open IT/Cyber solicitation in their selected state
    reaches 1 to 5 days before `closing_date`, dispatches a single de-duplicated urgency notification
    (logged in Supabase as `SUBSCRIBER_DEADLINE_NUDGE_LOG` via RLS-safe SELECT + insert).
    """
    import json
    from datetime import datetime, timezone

    today_d = datetime.now(timezone.utc).date()
    nudged_count = 0

    try:
        inb_resp = supabase.table(TABLE_NAME).select("id,title,status").eq("status", "SUBSCRIBER_INBOUND_LEAD").limit(200).execute()
        inb_rows = inb_resp.data if inb_resp and getattr(inb_resp, "data", None) else []
        if not inb_rows:
            return 0

        act_resp = supabase.table(TABLE_NAME).select("title").eq("status", "SUBSCRIBER_ACTIVE").limit(500).execute()
        active_emails = set()
        for r in (act_resp.data if act_resp and getattr(act_resp, "data", None) else []):
            try:
                m = json.loads(str(r.get("title") or "{}"))
                em = str(m.get("email") or "").strip().lower()
                if em:
                    active_emails.add(em)
            except Exception:
                pass

        nudge_resp = supabase.table(TABLE_NAME).select("url").eq("status", "SUBSCRIBER_DEADLINE_NUDGE_LOG").limit(1000).execute()
        already_nudged_urls = {
            str(r.get("url") or "").strip()
            for r in (nudge_resp.data if nudge_resp and getattr(nudge_resp, "data", None) else [])
        }

        open_resp = supabase.table(TABLE_NAME).select("*").order("id", desc=True).limit(200).execute()
        all_contracts = [
            r for r in (open_resp.data if open_resp and getattr(open_resp, "data", None) else [])
            if not str(r.get("url") or "").startswith("subscriber://")
            and not str(r.get("status") or "").startswith("SUBSCRIBER_")
        ]

        closing_soon_by_jurisdiction: dict[str, list[ tuple[int, dict] ]] = {}
        for rec in all_contracts:
            dt = _parse_closing_date_obj(str(rec.get("closing_date") or ""), str(rec.get("title") or ""))
            if not dt:
                continue
            days_left = (dt - today_d).days
            if 1 <= days_left <= 5:
                j_key = classify_jurisdiction(rec)
                closing_soon_by_jurisdiction.setdefault(j_key, []).append((days_left, rec))

        if not closing_soon_by_jurisdiction:
            return 0

        for irow in inb_rows:
            try:
                meta = json.loads(str(irow.get("title") or "{}"))
            except Exception:
                continue
            if not isinstance(meta, dict) or meta.get("suppress_alert"):
                continue
            email = str(meta.get("email") or "").strip().lower()
            if not email or "@" not in email or email in active_emails:
                continue
            dom = email.split("@", 1)[1]
            if dom in ("example.com", "test.com", "localhost"):
                continue
            log_url = f"subscriber://deadline-nudge/{email}"
            if log_url in already_nudged_urls:
                continue

            target_state = str(meta.get("target_state") or "virginia").strip().lower()
            candidates = closing_soon_by_jurisdiction.get(target_state) or closing_soon_by_jurisdiction.get("federal") or []
            if not candidates:
                for fallback_list in closing_soon_by_jurisdiction.values():
                    if fallback_list:
                        candidates = fallback_list
                        break
            if not candidates:
                continue

            candidates.sort(key=lambda x: x[0])
            days_left, top_rec = candidates[0]
            clean_t = clean_title_text(str(top_rec.get("title") or "Government IT Solicitation"))
            agency = str(top_rec.get("agency") or "Government Agency").strip()
            closing_str = str(top_rec.get("closing_date") or "Soon").strip()
            slug = slugify_contract(str(top_rec.get("title") or ""), fallback_id=str(top_rec.get("id") or ""))
            dossier_url = f"{SITE_BASE_URL}/contracts/rfp/{slug}.html"
            fname = str(meta.get("first_name") or "Capture Team").strip()
            comp = str(meta.get("company") or "your team").strip()
            state_disp = target_state.replace("_", " ").title()

            subj = f"{days_left}-Day Deadline Notice: {clean_t[:68]} ({agency}) closes {closing_str}"
            body = (
                f"Hi {fname},\n\n"
                f"Quick deadline heads-up based on {comp}'s {state_disp} territory filter on SignalTender:\n\n"
                f"• Solicitation: {clean_t}\n"
                f"• Issuing Agency: {agency}\n"
                f"• Submission Deadline: {closing_str} ({days_left} day{'s' if days_left != 1 else ''} remaining)\n"
                f"• Pre-Shredded Capture Dossier: {dossier_url}\n\n"
                f"Our CaptureDesk engine has already generated the Shipley Section L/M Compliance Matrix, "
                f"CPARS Volume III Past Performance citations, 13 CFR § 125.6 Teaming Plan, and IGCE Price-to-Win "
                f"model for this solicitation.\n\n"
                f"You can unlock the full un-blurred official portal link and 21-API CaptureDesk suite in 60 seconds "
                f"(Tier 1 SignalWire Pro $99/mo or Tier 2 CaptureDesk Autopilot $399/mo) here:\n"
                f"{SITE_BASE_URL}/#checkout\n\n"
                f"Or manage your saved bids and alert filters in your Client Portal:\n"
                f"{SITE_BASE_URL}/#account\n\n"
                f"Best,\nAaron Chen\nFounder, SignalTender"
            )

            inst_key = os.getenv("INSTANTLY_API_KEY", "").strip()
            inst_sub_cid = os.getenv("INSTANTLY_SUBSCRIBER_CAMPAIGN_ID", "748eecf5-6b63-4dff-b9f2-1d2ff1a4a96f").strip()
            sent_ok = False
            if inst_key and inst_sub_cid:
                r = requests.post(
                    "https://api.instantly.ai/api/v2/leads",
                    headers={"Authorization": f"Bearer {inst_key}", "Content-Type": "application/json"},
                    json={
                        "campaign": inst_sub_cid,
                        "email": email,
                        "first_name": fname,
                        "company_name": comp,
                        "skip_if_in_campaign": False,
                        "custom_variables": {"subject_line": subj, "email_body": body},
                    },
                    timeout=10,
                )
                sent_ok = r.status_code in (200, 201)

            already_nudged_urls.add(log_url)
            chk = supabase.table(TABLE_NAME).select("id").eq("url", log_url).execute()
            if not (chk and getattr(chk, "data", None)):
                supabase.table(TABLE_NAME).insert({
                    "title": json.dumps({
                        "email": email,
                        "company": comp,
                        "contract_id": top_rec.get("id"),
                        "days_left": days_left,
                        "sent_ok": sent_ok,
                        "nudged_at": datetime.now(timezone.utc).isoformat(),
                    }),
                    "agency": f"DEADLINE_NUDGE:{target_state.upper()}",
                    "url": log_url,
                    "status": "SUBSCRIBER_DEADLINE_NUDGE_LOG",
                }).execute()
            nudged_count += 1
    except Exception as nudge_err:
        print(f"[!] Deadline nudge check warning: {nudge_err}", flush=True)

    return nudged_count


def deliver_leads(client_webhook_url: str = None) -> int:
    """
    Query Supabase for 'New Lead' contracts, format them into enriched Discord
    intelligence blocks (with pSEO Dossier + FastAPI links), route them to the
    Master Client Discord Wire, any configured state-specific Discord channels,
    AND any active subscriber Slack/Teams/CRM webhooks, then update status to 'Delivered'.
    """
    target_webhook = client_webhook_url or CLIENT_DISCORD_WEBHOOK_URL

    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL or SUPABASE_KEY is missing in environment variables.")
        if not target_webhook:
            raise ValueError("Client Discord Webhook URL is missing in environment variables.")

        print("[*] Connecting to Supabase...", flush=True)
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        print(f"[*] Querying '{TABLE_NAME}' table for records with status='New Lead'...", flush=True)
        resp = supabase.table(TABLE_NAME).select("*").eq("status", "New Lead").execute()
        records = [
            r for r in (resp.data if resp and getattr(resp, "data", None) else [])
            if not str(r.get("url") or "").startswith("subscriber://")
        ]

        if not records:
            print("[+] No 'New Lead' records found to deliver.", flush=True)
            _dispatch_closing_soon_nudges_for_inbound_leads(supabase)
            return 0

        print(f"[*] Found {len(records)} 'New Lead' record(s) ready for delivery.", flush=True)

        # 1. Post all leads to the Master Client Discord Webhook (#all-active-rfps)
        _post_batches_to_webhook(records, target_webhook, label="Master All-Access Wire")

        # 2. Route leads to any state/portal-specific Discord channel webhooks configured in .env
        for j_key, j_webhook in JURISDICTION_WEBHOOKS.items():
            if not j_webhook or j_webhook == target_webhook:
                continue
            j_records = [r for r in records if classify_jurisdiction(r) == j_key]
            if j_records:
                try:
                    _post_batches_to_webhook(j_records, j_webhook, label=f"State Channel ({j_key.upper()})")
                except Exception as ch_err:
                    print(f"[!] State channel webhook ({j_key}) warning: {ch_err}", flush=True)

        # 3. Route leads to any active subscriber external webhooks (Slack, MS Teams, Zapier, Make, n8n, CRM)
        ext_count = _dispatch_to_external_customer_webhooks(supabase, records)
        if ext_count:
            print(f"[+] Dispatched RFP batch to {ext_count} external customer Slack/Teams/CRM webhook(s).", flush=True)

        # 3b. Check Free Explorer / Inbound leads for 1-to-5-day closing-soon deadline urgency nudges
        nudge_count = _dispatch_closing_soon_nudges_for_inbound_leads(supabase)
        if nudge_count:
            print(f"[+] Dispatched {nudge_count} closing-soon deadline urgency nudge(s) to Free Explorer leads.", flush=True)

        # 4. Update Supabase status from 'New Lead' to 'Delivered'
        urls_delivered = [rec["url"] for rec in records if rec.get("url")]
        for i in range(0, len(urls_delivered), 50):
            chunk = urls_delivered[i : i + 50]
            supabase.table(TABLE_NAME).update({"status": "Delivered"}).in_("url", chunk).execute()

        delivered_count = len(records)
        print(f"[+] Client delivery complete! Successfully delivered {delivered_count} enriched lead(s).", flush=True)
        return delivered_count

    except Exception as e:
        error_msg = f"client_delivery.py failed: {e}"
        print(f"\n[!] Error during client delivery: {e}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n[!] Error during client delivery: {e}\n")
        except Exception:
            pass
        send_discord_alert(error_msg)
        return 0


if __name__ == "__main__":
    deliver_leads()
