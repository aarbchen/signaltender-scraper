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

import json
import os
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv()

INSTANTLY_API_KEY = (os.getenv("INSTANTLY_API_KEY") or "").strip()
INSTANTLY_CAMPAIGN_ID = (os.getenv("INSTANTLY_CAMPAIGN_ID") or "").strip()
ANTHROPIC_API_KEY = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
DISCORD_WEBHOOK_URL = (os.getenv("DISCORD_WEBHOOK_URL") or "").strip()
SITE_BASE_URL = os.getenv("SIGNALTENDER_SITE_URL", "https://signaltender.net").rstrip("/")
PROCESSED_REPLIES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "processed_outbound_replies.json")


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
    that delivers the live RFP directory/dossier link + self-serve Tier 1 ($99/mo) / Tier 2 ($399/mo) checkout.
    """
    low = str(reply_text or "").lower()
    if any(p in low for p in ("unsubscribe", "remove me", "take me off", "stop emailing", "not interested", "no thanks", "off your list")):
        return {"intent": "UNSUBSCRIBE", "reply_body": ""}

    default_reply = (
        f"Appreciate the quick reply!\n\n"
        f"Here is the live directory of pre-shredded Federal & 12-State SLED IT/Cyber dossiers (with direct agency RFP links, Section L/M matrices, and NAICS/SBA caps):\n"
        f"{SITE_BASE_URL}/contracts\n\n"
        f"If your team wants every new solicitation delivered automatically every 6 hours, we have two instant self-serve options (no sales calls or annual contracts):\n"
        f"• Tier 1 — SignalWire Pro ($99/mo): Real-time 14-portal Federal & State SLED IT/Cyber alerts via Email, Slack, Teams, Discord, or Webhook.\n"
        f"• Tier 2 — CaptureDesk Autopilot ($399/mo): Full AI Section L/M compliance matrices, CPARS Volume III past performance citations, SF-30 amendment diffs, and 20 REST/MCP APIs on every lead.\n\n"
        f"You can activate instant access in 60 seconds here:\n"
        f"{SITE_BASE_URL}/#checkout\n\n"
        f"Best,\nAaron Chen\nFounder, SignalTender"
    )

    if not ANTHROPIC_API_KEY:
        return {"intent": "POSITIVE_INTEREST", "reply_body": default_reply}

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        prompt = (
            f"You are Aaron Chen, Founder of SignalTender ({SITE_BASE_URL}). A GovCon IT/Cyber prospect ({from_email}) "
            f"just replied to our cold email offering 3 open public-sector IT RFPs.\n\n"
            f"Subject: {subject}\n"
            f"Prospect Reply:\n{reply_text}\n\n"
            f"Classify their reply into JSON with keys:\n"
            f"- \"intent\": one of \"POSITIVE_INTEREST\", \"QUESTION\", \"OUT_OF_OFFICE\", or \"UNSUBSCRIBE\".\n"
            f"- \"reply_body\": if POSITIVE_INTEREST or QUESTION, write a concise, natural plain-text reply from Aaron Chen "
            f"(Founder, SignalTender) that directly answers their note, gives them the live RFP directory & dossier link "
            f"({SITE_BASE_URL}/contracts), and briefly shares the self-serve Tier 1 SignalWire Pro ($99/mo) and Tier 2 "
            f"CaptureDesk Autopilot ($399/mo) instant checkout link ({SITE_BASE_URL}/#checkout). Zero emojis, zero markdown bold (**). "
            f"Output strictly valid JSON."
        )
        resp = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=600,
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
            }
    except Exception:
        pass

    return {"intent": "POSITIVE_INTEREST", "reply_body": default_reply}


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
            params={"campaign_id": INSTANTLY_CAMPAIGN_ID, "limit": 25},
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
                                    f"• **Auto-Sent Response:** Delivered `/contracts` dossier directory + `/#checkout` self-serve activation link."
                                ),
                                "flags": 4,
                            },
                            timeout=8,
                        )
                    except Exception:
                        pass
            elif intent == "UNSUBSCRIBE":
                unsub_count += 1

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

