"""
Autonomous Outbound Reply Classifier & Zero-Touch Responder (`outbound_reply_responder.py`).
===========================================================================================
Solves the "Stop-on-Reply Conversion Gap" in zero-touch B2B cold outreach:
  - Because `stop_on_reply: true` is enabled in Instantly.ai campaign `c7727dff-92cc-4621-9e96-c960938d5a47`,
    any prospect who replies "Yes, send it over" to Step 1 (which has no pricing/checkout link)
    automatically pauses Step 2—meaning our hottest prospects would never receive the raw RFP links
    or the self-serve Tier 1 ($99/mo) / Tier 2 ($399/mo) checkout link unless answered!
  - Runs automatically every 6 hours inside `mainscraper.py`:
    1. Polls Instantly.ai V2 `/api/v2/emails` for unread inbound prospect replies (`ue_type == 2`).
    2. Classifies each reply using `claude-sonnet-5-5` into `POSITIVE_INTEREST`, `QUESTION`, or `UNSUBSCRIBE`.
    3. For `POSITIVE_INTEREST` / `QUESTION`: automatically sends a warm, human-sounding reply via
       Instantly.ai `/api/v2/emails/reply` containing their state's live RFP dossier link + the self-serve
       SignalWire Pro ($99/mo) / CaptureDesk Autopilot ($399/mo) checkout link, and alerts Discord.
    4. For `UNSUBSCRIBE`: marks the lead as Do-Not-Contact so they are never emailed again.
"""

from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()

import csv
import json
import os
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANTLY_API_KEY = (os.getenv("INSTANTLY_API_KEY") or "").strip()
INSTANTLY_CAMPAIGN_ID = (os.getenv("INSTANTLY_CAMPAIGN_ID") or "").strip()
ANTHROPIC_API_KEY = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
DISCORD_WEBHOOK_URL = (os.getenv("DISCORD_WEBHOOK_URL") or "").strip()
SITE_BASE_URL = os.getenv("SIGNALTENDER_SITE_URL", "https://signaltender.net").rstrip("/")
PROCESSED_REPLIES_PATH = os.path.join(BASE_DIR, "processed_outbound_replies.json")
CAMPAIGN_CSV_PATH = os.path.join(BASE_DIR, "campaign_leads.csv")
INTEL_JSON_PATH = os.path.join(BASE_DIR, "govcon_prospect_intelligence.json")


def _lookup_prospect_context(from_email: str) -> dict:
    """
    Look up `from_email` (with corporate-domain fallback if a teammate replies from another
    inbox at the same company) in `campaign_leads.csv` and `govcon_prospect_intelligence.json`
    so `classify_and_draft_reply()` knows the exact 3 RFPs, Top Contract Dossier URL,
    USAspending Award ID, and Recompete/Subcontracting matches that were sent to this prospect.
    """
    clean_em = str(from_email or "").strip().lower()
    dom = clean_em.split("@", 1)[1] if "@" in clean_em else ""
    matched_row: dict | None = None
    domain_row: dict | None = None

    if os.path.exists(CAMPAIGN_CSV_PATH):
        try:
            with open(CAMPAIGN_CSV_PATH, mode="r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    row_em = str(row.get("Email") or "").strip().lower()
                    if row_em == clean_em:
                        matched_row = row
                        break
                    if dom and row_em.endswith("@" + dom) and domain_row is None:
                        domain_row = row
        except Exception:
            pass

    target = matched_row or domain_row or {}
    company = str(target.get("Company") or "").strip()
    award_profile = None
    if company and os.path.exists(INTEL_JSON_PATH):
        try:
            with open(INTEL_JSON_PATH, "r", encoding="utf-8") as jf:
                intel_data = json.load(jf) or {}
            profiles = intel_data.get("company_award_profiles") or {}
            from govcon_lead_harvester import _normalize_company_tokens
            _, _, c_key = _normalize_company_tokens(company)
            award_profile = profiles.get(c_key)
        except Exception:
            award_profile = None

    return {
        "first_name": str(target.get("First Name") or "").strip(),
        "company": company,
        "matched_state": str(target.get("Matched State") or "Federal & State SLED").strip(),
        "top_dossier_url": str(target.get("Top Contract Dossier URL") or f"{SITE_BASE_URL}/contracts").strip(),
        "compiler_deeplink_url": str(target.get("Compiler Deep-Link URL") or f"{SITE_BASE_URL}/#proposal-autopilot").strip(),
        "top_naics": str(target.get("Top Contract NAICS") or "541512 — Computer Systems Design Services").strip(),
        "top_posture": str(target.get("Top Contract Posture") or "").strip(),
        "original_subject": str(target.get("Subject Line") or "").strip(),
        "original_email_body": str(target.get("Email Body") or "").strip(),
        "original_followup_body": str(target.get("Followup Body") or "").strip(),
        "award_profile": award_profile,
    }


def _load_processed_ids() -> set[str]:
    if os.path.exists(PROCESSED_REPLIES_PATH):
        try:
            with open(PROCESSED_REPLIES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {str(x) for x in data}
        except Exception:
            pass
    return set()


def _save_processed_ids(ids: set[str]) -> None:
    try:
        with open(PROCESSED_REPLIES_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted(ids), f, indent=2)
    except Exception:
        pass


def classify_and_draft_reply(from_email: str, subject: str, reply_text: str) -> dict:
    """
    Use claude-sonnet-5-5 to classify an inbound cold-email reply and draft a tailored response
    that references the exact 3 RFPs, Top Contract Dossier URL, and USAspending Recompete/Subcontracting
    context sent to `from_email`, plus self-serve Tier 1 ($99/mo) / Tier 2 ($399/mo) checkout.
    """
    low = str(reply_text or "").lower()
    if any(p in low for p in ("unsubscribe", "remove me", "take me off", "stop emailing", "not interested", "no thanks", "off your list")):
        return {"intent": "UNSUBSCRIBE", "reply_body": ""}

    ctx = _lookup_prospect_context(from_email)
    comp_label = ctx["company"] or "your team"
    state_label = ctx["matched_state"] or "Federal & State SLED"
    top_dossier_url = ctx["top_dossier_url"] or f"{SITE_BASE_URL}/contracts"
    compiler_deeplink_url = ctx.get("compiler_deeplink_url") or f"{SITE_BASE_URL}/#proposal-autopilot"
    fname_greeting = f"Hi {ctx['first_name']},\n\n" if ctx["first_name"] and ctx["first_name"].lower() not in ("capture", "team", "there", "contracts", "partnerships") else ""

    default_reply = (
        f"{fname_greeting}Appreciate the quick reply!\n\n"
        f"Here is the direct CaptureDesk dossier for #1 from the {state_label} IT/Cyber list I sent over to {comp_label} (including the Section L/M compliance matrix, NAICS {ctx['top_naics']}, and official agency portal link):\n"
        f"{top_dossier_url}\n\n"
        f"And here is your pre-loaded 1-Click 6-File Shipley Proposal .ZIP Compiler deep-link (Vol I Technical .docx + Vol II Live-Formula Section B Cost .xlsx + Vol III CPARS/OCI .docx + Vol IV FAR 9.6 Teaming .docx + Vol V FOIA Demand .docx):\n"
        f"{compiler_deeplink_url}\n\n"
        f"And here is the full live directory of pre-shredded Federal & 19-State SLED IT/Cyber dossiers:\n"
        f"{SITE_BASE_URL}/contracts\n\n"
        f"You can also create a Free Explorer Account ($0/mo — no credit card required) in our Client Portal to save {comp_label}'s state & NAICS alert filters, pre-load your Company Capture Vault, track bids on your Saved RFP Bid Board, and test all 27 AI Capture APIs:\n"
        f"{SITE_BASE_URL}/#signup\n\n"
        f"When your team is ready for automated 6-hour dispatches, un-blurred portal links, or 1-click 3-volume Shipley proposal compilation, we have four instant self-serve plans (FAR 31.205-18 allowable B&P expense with instant corporate P-Card PDF receipt & 1-click auto-renew pause):\n"
        f"• Tier 1 — SignalWire Pro ($99/mo): Real-time 21-portal Federal & State SLED IT/Cyber alerts + 90-180d Recompete & Subcontracting Wire via Slack, Microsoft Teams, Discord, CRM Webhook, or Email + 5 Team CC seats.\n"
        f"• Tier 2 — CaptureDesk Autopilot ($399/mo): Full 23-Engine AI Section L/M compliance matrices, Price-to-Win Recompete Models (API #16), Sources Sought Set-Aside Briefs (API #21), Prime-to-Sub Teaming Plans (API #11), CPARS Volume III citations, SF-30 amendment diffs, and your own st_live_... Enterprise API & MCP key.\n"
        f"• Tier 3 — Proposal Autopilot Enterprise ($1,499/mo): 1-Click Complete 3-Volume Shipley Proposal Compiler (.ZIP containing Word .docx Volume I/III + live-formula Excel .xlsx Volume II Cost Model in 90s) + 13 CFR § 125.6 Teaming Clearinghouse.\n"
        f"• Tier 4 — Enterprise OEM & FOIA Winning-Bid Vault ($2,499/mo): Automated Post-Award FOIA/PIA Incumbent LCAT Rate Vault + 50,000 REST/MCP API calls/mo OEM license.\n\n"
        f"Activate instant access anytime here:\n"
        f"{SITE_BASE_URL}/#checkout\n\n"
        f"Best,\nAaron Chen\nFounder, SignalTender"
    )

    if not ANTHROPIC_API_KEY:
        return {"intent": "POSITIVE_INTEREST", "reply_body": default_reply, "context": ctx}

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        awd_prof = ctx.get("award_profile") or {}
        awd_context_str = (
            f"Prospect's Verified USAspending Contract: {awd_prof.get('award_id')} "
            f"({awd_prof.get('award_amount_fmt')} with {awd_prof.get('awarding_sub_agency')}, PoP ending {awd_prof.get('end_date')})\n"
            if awd_prof.get("award_id")
            else ""
        )
        original_sent_block = (
            f"Original Email Sent to {comp_label} ({from_email}):\n"
            f"---\n{ctx['original_email_body']}\n---\n"
            f"Follow-Up Dossier Metadata:\n"
            f"- Top Solicitation #1 Dossier URL: {top_dossier_url}\n"
            f"- Top Solicitation #1 NAICS: {ctx['top_naics']}\n"
            f"- Top Solicitation #1 Compliance & Teaming Posture: {ctx['top_posture']}\n"
            f"{awd_context_str}"
            if ctx.get("original_email_body")
            else f"- Top Solicitation Dossier URL: {top_dossier_url}\n"
        )
        prompt = (
            f"You are Aaron Chen, Founder of SignalTender ({SITE_BASE_URL}). A GovCon IT/Cyber prospect "
            f"({from_email}, Company: {comp_label}, Territory: {state_label}) just replied to our cold email.\n\n"
            f"{original_sent_block}\n"
            f"Subject: {subject}\n"
            f"Prospect Reply:\n{reply_text}\n\n"
            f"Classify their reply into JSON with keys:\n"
            f"- \"intent\": one of \"POSITIVE_INTEREST\", \"QUESTION\", \"OUT_OF_OFFICE\", or \"UNSUBSCRIBE\".\n"
            f"- \"reply_body\": if POSITIVE_INTEREST or QUESTION, write a concise, executive plain-text reply from Aaron Chen "
            f"(Founder, SignalTender) that directly answers their specific question (referencing the exact solicitation #1/#2/#3, "
            f"agency, due date, Recompete Radar, or Prime-to-Sub Teaming item from the Original Email Sent above) and gives them:\n"
            f"  1) Their exact Solicitation #1 Capture Dossier link ({top_dossier_url}), their 1-Click 6-File Shipley .ZIP Compiler deep-link ({compiler_deeplink_url}), + the full directory ({SITE_BASE_URL}/contracts)\n"
            f"  2) The Free Explorer Account sign-up link ({SITE_BASE_URL}/#signup — $0/mo, no credit card required to save state/NAICS alert filters, Company Capture Vault, and Bid Board)\n"
            f"  3) The self-serve Tier 1 SignalWire Pro ($99/mo), Tier 2 CaptureDesk Autopilot ($399/mo), Tier 3 Proposal Autopilot .ZIP Compiler ($1,499/mo), and Tier 4 Enterprise OEM & FOIA Rate Vault ($2,499/mo) instant activation link ({SITE_BASE_URL}/#checkout).\n"
            f"Zero emojis, zero markdown bold (**). Output strictly valid JSON."
        )
        resp = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = ""
        for blk in resp.content:
            if blk.type == "text":
                raw = blk.text.strip()
                break
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and parsed.get("intent"):
            return {
                "intent": str(parsed.get("intent")),
                "reply_body": str(parsed.get("reply_body") or default_reply),
                "context": ctx,
            }
    except Exception:
        pass

    return {"intent": "POSITIVE_INTEREST", "reply_body": default_reply, "context": ctx}


def run_reply_responder() -> dict:
    """Poll Instantly.ai V2 Unibox for unread prospect replies and auto-respond to positive interest."""
    if not INSTANTLY_API_KEY or not INSTANTLY_CAMPAIGN_ID:
        return {"status": "skipped", "reason": "No INSTANTLY_API_KEY configured"}

    headers = {
        "Authorization": f"Bearer {INSTANTLY_API_KEY}",
        "Content-Type": "application/json",
    }
    processed_ids = _load_processed_ids()
    answered_count = 0
    unsub_count = 0

    try:
        resp = requests.get(
            "https://api.instantly.ai/api/v2/emails",
            params={"campaign_id": INSTANTLY_CAMPAIGN_ID, "email_type": "received", "limit": 50},
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200:
            return {"status": "ok", "checked": 0}

        items = resp.json().get("items") or []
        for msg in items:
            msg_id = str(msg.get("id") or "").strip()
            # ue_type == 2 indicates an inbound reply from a lead in Instantly V2
            ue_type = msg.get("ue_type")
            if not msg_id or msg_id in processed_ids or ue_type != 2:
                continue

            from_email = str(msg.get("from_address_email") or msg.get("lead") or "").strip()
            eaccount = str(msg.get("eaccount") or "").strip()
            subject = str(msg.get("subject") or "Re: Open IT RFPs").strip()
            body_obj = msg.get("body") or {}
            reply_text = str(body_obj.get("text") or body_obj.get("html") or "").strip()
            if not reply_text:
                processed_ids.add(msg_id)
                continue

            result = classify_and_draft_reply(from_email, subject, reply_text)
            intent = result["intent"]
            reply_body = result["reply_body"]

            if intent in ("POSITIVE_INTEREST", "QUESTION") and reply_body and eaccount:
                r_send = requests.post(
                    "https://api.instantly.ai/api/v2/emails/reply",
                    headers=headers,
                    json={
                        "reply_to_uuid": msg_id,
                        "eaccount": eaccount,
                        "subject": subject if subject.lower().startswith("re:") else f"Re: {subject}",
                        "body": {"text": reply_body},
                    },
                    timeout=15,
                )
                if 200 <= r_send.status_code < 300:
                    answered_count += 1
                if DISCORD_WEBHOOK_URL:
                    try:
                        requests.post(
                            DISCORD_WEBHOOK_URL,
                            json={
                                "content": (
                                    f"**[HOT OUTBOUND REPLY — AUTO-ANSWERED BY CLAUDE SONNET 5.5]**\n"
                                    f"• **Prospect:** `{from_email}` (`{intent}`)\n"
                                    f"• **Their Reply:** {reply_text[:300]}\n"
                                    f"• **Auto-Sent Response:** Delivered `/contracts` dossier directory + `/#signup` Free Explorer Portal + `/#checkout` activation link."
                                ),
                                "flags": 4,
                            },
                            timeout=8,
                        )
                    except Exception:
                        pass
            elif intent == "UNSUBSCRIBE":
                unsub_count += 1
                if from_email and "@" in from_email:
                    try:
                        import govcon_lead_harvester
                        govcon_lead_harvester.save_completed_outreach_archive({from_email.strip().lower()})
                    except Exception:
                        pass

            processed_ids.add(msg_id)

        _save_processed_ids(processed_ids)
        print(
            f"[+] Outbound Reply Auto-Responder: Checked {len(items)} Unibox item(s) "
            f"({answered_count} positive replies auto-answered, {unsub_count} unsubscribes).",
            flush=True,
        )
    except Exception as exc:
        report_error("outbound_reply_responder.py", f"Outbound reply responder warning: {exc}", severity="WARNING")

    return {"status": "ok", "answered": answered_count, "unsubscribed": unsub_count}


if __name__ == "__main__":
    run_reply_responder()

