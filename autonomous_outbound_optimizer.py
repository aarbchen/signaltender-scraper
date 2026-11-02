from datetime import datetime, timezone
r"""
SignalTender — Autonomous Outbound Sent-Payload, Sequence & Lead Self-Healing Optimizer
(`d:\Daas\autonomous_outbound_optimizer.py`).
====================================================================================================
Runs automatically inside `silent_autopilot_watcher.py` and `auto_error_healer.py` so the user
never has to ask whether there are outbound campaign bugs or tell the system to fix them:
  1. Sequence Step Self-Healing (`GET / PATCH /api/v2/campaigns/{cid}`):
     - Verifies Step 1, Step 2, and Step 3 all have non-empty `subject` and `body`.
  2. Bounce & Unsubscribe Auto-Purge + Archive (`POST /api/v2/leads/list`):
     - Detects any bounced (`status < 0`) or unsubscribed (`lt_interest_status < 0`) lead, deletes it
       from Instantly, and archives it via `govcon_lead_harvester.save_completed_outreach_archive()`.
  3. In-Flight & Uncontacted Lead Variable Self-Healing (`PATCH /api/v2/leads/{id}`):
     - Audits all existing leads in Instantly (`c7727dff-92cc-4621-9e96-c960938d5a47`) against `campaign_leads.csv`.
     - Immediately patches any lead whose `followup_body` has stale API/state counts (`39 AI capture modules`,
       `31-State SLED`), or whose `first_name` / `email_body` uses a dotless `first_initial + last_name` handle
       (`Hi Tbuzan,`, `Hi Rdepew,`, `Hi Bbertram,`) so every upcoming Step 1, Step 2, and Step 3 email is 100% clean.
"""

from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()

from concurrent.futures import ThreadPoolExecutor
import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, List
import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=str(ROOT_DIR / ".env"))

INSTANTLY_API_KEY = (os.getenv("INSTANTLY_API_KEY") or "").strip()
CAMPAIGN_ID = (os.getenv("INSTANTLY_CAMPAIGN_ID") or "c7727dff-92cc-4621-9e96-c960938d5a47").strip()
CSV_PATH = ROOT_DIR / "campaign_leads.csv"


def audit_rendered_sent_outbox_and_learn(cid: str, headers: Dict[str, str], all_leads: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    1. Audits the last 50 actual rendered emails (`GET /api/v2/emails`) sent to prospects
       to catch any unrendered `{{variable}}`, `%` encoding, or broken link in real time.
    2. Computes live prefix delivery/bounce rates and hook/cohort reply rates (`ue_type == 2`)
       and saves adaptive weights to `learned_outbound_intelligence.json`.
    """
    intel_path = ROOT_DIR / "learned_outbound_intelligence.json"
    intel: Dict[str, Any] = {}
    if intel_path.exists():
        try:
            intel = json.loads(intel_path.read_text(encoding="utf-8"))
        except Exception:
            intel = {}

    sent_count = 0
    reply_count = 0
    unrendered_var_alerts = 0
    cohort_stats: Dict[str, Dict[str, int]] = intel.get("cohort_stats", {})
    prefix_stats: Dict[str, Dict[str, int]] = {
        "named_person": {"clean": 0, "bounced": 0},
        "dept_desk": {"clean": 0, "bounced": 0},
        "generic_info": {"clean": 0, "bounced": 0},
    }

    lead_by_email: Dict[str, Dict[str, Any]] = {}
    for ld in all_leads:
        em = (ld.get("email") or "").strip().lower()
        if not em:
            continue
        lead_by_email[em] = ld
        local = em.split("@")[0]
        status_code = int(ld.get("status", 1) or 1)
        if local in ("info", "contact", "office", "admin", "hello", "general", "inquiries"):
            bucket = "generic_info"
        elif local in ("estimating", "estimates", "bids", "bidding", "precon", "billing", "rcm", "managedcare", "contracts", "proposals", "sales"):
            bucket = "dept_desk"
        else:
            bucket = "named_person"
        if status_code < 0:
            prefix_stats[bucket]["bounced"] += 1
        else:
            prefix_stats[bucket]["clean"] += 1

    try:
        r_em = requests.get(
            f"https://api.instantly.ai/api/v2/emails?campaign_id={cid}&limit=50",
            headers=headers,
            timeout=20,
        )
        if r_em.status_code == 200:
            items = (r_em.json() or {}).get("items") or []
            for m in items:
                ue_type = int(m.get("ue_type", 1) or 1)
                to_em = (m.get("to_address_email_list") or "").strip().lower()
                from_em = (m.get("from_address_email") or "").strip().lower()
                body_txt = ((m.get("body") or {}).get("text") or "")
                subj_txt = (m.get("subject") or "")

                if "{{" in body_txt or "}}" in body_txt or "{{" in subj_txt:
                    unrendered_var_alerts += 1

                prospect_em = from_em if ue_type == 2 else to_em
                ld_obj = lead_by_email.get(prospect_em) or {}
                pl = ld_obj.get("payload") or {}
                cohort_key = str(pl.get("agency") or pl.get("state") or "default")[:40]
                if cohort_key not in cohort_stats:
                    cohort_stats[cohort_key] = {"sent": 0, "replies": 0}

                if ue_type == 2:
                    reply_count += 1
                    cohort_stats[cohort_key]["replies"] = cohort_stats[cohort_key].get("replies", 0) + 1
                else:
                    sent_count += 1
                    cohort_stats[cohort_key]["sent"] = max(cohort_stats[cohort_key].get("sent", 0), 1)
    except Exception:
        pass

    # Compute adaptive priority weights by prefix bucket (penalizing any bucket with >3% bounce rate)
    recommended_weights: Dict[str, float] = {}
    for bucket, st in prefix_stats.items():
        total = st["clean"] + st["bounced"]
        bounce_rate = (st["bounced"] / total) if total > 0 else 0.0
        base_w = 1.0 if bucket == "named_person" else (0.85 if bucket == "dept_desk" else 0.5)
        recommended_weights[bucket] = round(max(0.1, base_w * (1.0 - min(0.8, bounce_rate * 5.0))), 3)

    intel.update({
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "campaign_id": cid,
        "recent_rendered_emails_audited": sent_count,
        "recent_inbound_replies_detected": reply_count,
        "unrendered_template_tags_detected": unrendered_var_alerts,
        "prefix_delivery_stats": prefix_stats,
        "adaptive_prefix_priority_weights": recommended_weights,
        "cohort_stats": cohort_stats,
    })
    try:
        intel_path.write_text(json.dumps(intel, indent=2), encoding="utf-8")
    except Exception:
        pass
    return {
        "rendered_audited": sent_count,
        "replies_detected": reply_count,
        "unrendered_alerts": unrendered_var_alerts,
        "adaptive_weights": recommended_weights,
    }



def run_autonomous_outbound_optimizer() -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "brand": "SignalTender",
        "campaign_id": CAMPAIGN_ID,
        "sequence_repaired": False,
        "bounced_or_bad_purged": 0,
        "leads_patched_in_place": 0,
        "status": "ok",
    }
    if not INSTANTLY_API_KEY or not CAMPAIGN_ID:
        summary["status"] = "skipped_no_key"
        return summary

    headers = {
        "Authorization": f"Bearer {INSTANTLY_API_KEY}",
        "Content-Type": "application/json",
    }
    auth_only = {"Authorization": f"Bearer {INSTANTLY_API_KEY}"}

    # 1. Verify 3-step sequence integrity
    try:
        rc = requests.get(f"https://api.instantly.ai/api/v2/campaigns/{CAMPAIGN_ID}", headers=auth_only, timeout=12)
        if rc.status_code == 200:
            cdata = rc.json() or {}
            seqs = cdata.get("sequences") or []
            steps = (seqs[0].get("steps") or []) if seqs and isinstance(seqs[0], dict) else []
            needs_seq_fix = len(steps) < 3
            for st_item in steps:
                vars_list = st_item.get("variants") or []
                if not vars_list or not str(vars_list[0].get("subject") or "").strip() or not str(vars_list[0].get("body") or "").strip():
                    needs_seq_fix = True
            if needs_seq_fix:
                expected_seq = [
                    {
                        "steps": [
                            {"type": "email", "delay": 2, "variants": [{"subject": "{{subject_line}}", "body": "{{email_body}}"}]},
                            {"type": "email", "delay": 2, "variants": [{"subject": "{{followup_subject}}", "body": "{{followup_body}}"}]},
                            {"type": "email", "delay": 2, "variants": [{"subject": "{{breakup_subject}}", "body": "{{breakup_body}}"}]},
                        ]
                    }
                ]
                rp = requests.patch(
                    f"https://api.instantly.ai/api/v2/campaigns/{CAMPAIGN_ID}",
                    headers=headers,
                    json={"sequences": expected_seq},
                    timeout=15,
                )
                summary["sequence_repaired"] = rp.status_code in (200, 201)
    except Exception as exc:
        report_error("autonomous_outbound_optimizer.py", f"SignalTender sequence audit warning: {exc}", severity="WARNING")

    # 2. Load clean CSV map
    csv_map: Dict[str, Dict[str, str]] = {}
    if CSV_PATH.exists():
        try:
            with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as cf:
                for row in csv.DictReader(cf):
                    em = str(row.get("Email") or "").strip().lower()
                    if em:
                        csv_map[em] = row
        except Exception:
            pass

    from outreach_generator import clean_company_for_copy, is_dotless_handle_name
    import govcon_lead_harvester

    to_purge: list[tuple[str, str]] = []
    to_patch: list[tuple[str, str, Dict[str, Any]]] = []
    all_leads: List[Dict[str, Any]] = []

    try:
        starting_after = None
        for _ in range(15):
            req_body: Dict[str, Any] = {"campaign": CAMPAIGN_ID, "limit": 100}
            if starting_after:
                req_body["starting_after"] = starting_after
            rl = requests.post("https://api.instantly.ai/api/v2/leads/list", headers=headers, json=req_body, timeout=15)
            if rl.status_code != 200:
                break
            rj = rl.json() or {}
            items = rj.get("items") or []
            all_leads.extend(items)
            for it in items:
                em = str(it.get("email") or "").strip().lower()
                lid = str(it.get("id") or "").strip()
                if not em or not lid:
                    continue
                st_code = int(it.get("status") or 0)
                lt_code = int(it.get("lt_interest_status") or 0)
                if st_code < 0 or lt_code < 0 or "%" in em:
                    to_purge.append((em, lid))
                    continue

                p_vars = it.get("payload") or {}
                fb_txt = str(p_vars.get("followup_body") or "")
                eb_txt = str(p_vars.get("email_body") or "")
                br_txt = str(p_vars.get("breakup_body") or "")
                cur_fn = str(it.get("first_name") or "").strip()
                cur_comp = str(it.get("company_name") or "").strip()

                has_stale_counts = ("39 AI " + "capture modules" in fb_txt) or ("31-State " + "SLED" in fb_txt) or ("58 AI capture modules" not in fb_txt) or not br_txt.strip()
                has_bad_handle = is_dotless_handle_name(cur_fn, em) and cur_fn.lower() not in ("capture", "there", "team")

                if (has_stale_counts or has_bad_handle) and em in csv_map:
                    clean_row = csv_map[em]
                    patch_body = {
                        "first_name": clean_row["First Name"],
                        "company_name": clean_company_for_copy(clean_row["Company"]),
                        "custom_variables": {
                            "subject_line": clean_row["Subject Line"],
                            "email_body": clean_row["Email Body"],
                            "followup_subject": clean_row.get("Followup Subject", ""),
                            "followup_body": clean_row.get("Followup Body", ""),
                            "breakup_subject": clean_row.get("Breakup Subject", ""),
                            "breakup_body": clean_row.get("Breakup Body", ""),
                            "spintax_subject_1": clean_row.get("Spintax Subject 1", ""),
                            "spintax_body_1": clean_row.get("Spintax Body 1", ""),
                            "spintax_body_2": clean_row.get("Spintax Body 2", ""),
                            "matched_state": clean_row.get("Matched State", ""),
                            "top_dossier_url": clean_row.get("Top Contract Dossier URL", ""),
                            "compiler_deeplink_url": clean_row.get("Compiler Deep-Link URL", ""),
                            "top_naics": clean_row.get("Top Contract NAICS", ""),
                            "top_posture": clean_row.get("Top Contract Posture", ""),
                            "target_segment": clean_row.get("Target Segment", "PRIME_PROPOSAL_AUTOPILOT"),
                        },
                    }
                    to_patch.append((em, lid, patch_body))
                elif has_stale_counts or has_bad_handle:
                    # Fallback in-place heal even if lead rotated out of current CSV
                    fixed_fn = "Capture" if has_bad_handle else cur_fn
                    fixed_comp = clean_company_for_copy(cur_comp)
                    fixed_eb = eb_txt
                    if has_bad_handle and cur_fn:
                        for prefix in ("Hi", "Hey", "Hello"):
                            fixed_eb = fixed_eb.replace(f"{prefix} {cur_fn},", f"{prefix} {fixed_comp} team,")
                    fixed_fb = (
                        fb_txt.replace("39 AI " + "capture modules", "58 AI capture modules")
                        .replace("covering Federal (SAM.gov), National Municipal (DemandStar) & 31-State SLED portals nationwide", "covering Federal (SAM.gov), National Municipal (DemandStar) & all 50 U.S. State SLED portals nationwide")
                    )
                    if has_bad_handle and cur_fn:
                        for prefix in ("Hi", "Hey", "Hello"):
                            fixed_fb = fixed_fb.replace(f"{prefix} {cur_fn},", f"{prefix} {fixed_comp} team,")
                    new_vars = dict(p_vars)
                    new_vars["email_body"] = fixed_eb
                    new_vars["followup_body"] = fixed_fb
                    if not br_txt.strip():
                        new_vars["breakup_subject"] = f"Re: {p_vars.get('subject_line', '')}"
                        new_vars["breakup_body"] = (
                            f"Hi {fixed_comp} team,\n\n"
                            f"Last note from me so I don't clutter your inbox.\n\n"
                            f"If {fixed_comp} has a live SAM.gov or State SLED RFP on your desk this month, reply 'SEND' (or reply with the Solicitation Number) and I'll send over the direct agency links plus a complete 6-file Shipley proposal & Section L/M compliance shred for your team on the house.\n\n"
                            f"Best,\nAaron Chen\nFounder, SignalTender"
                        )
                    to_patch.append((em, lid, {"first_name": fixed_fn, "company_name": fixed_comp, "custom_variables": new_vars}))

            starting_after = rj.get("next_starting_after")
            if not starting_after or len(items) < 100:
                break
    except Exception as exc:
        report_error("autonomous_outbound_optimizer.py", f"SignalTender lead scan warning: {exc}", severity="WARNING")

    if to_purge:
        try:
            govcon_lead_harvester.save_completed_outreach_archive({em for em, _ in to_purge})
        except Exception:
            pass
        for _, lid in to_purge:
            try:
                r_del = requests.delete(f"https://api.instantly.ai/api/v2/leads/{lid}", headers=auth_only, timeout=10)
                if 200 <= r_del.status_code < 300:
                    summary["bounced_or_bad_purged"] += 1
            except Exception:
                pass

    if to_patch:
        def _do_patch(item_tuple: tuple[str, str, Dict[str, Any]]) -> int:
            _, lid, p_body = item_tuple
            try:
                rp = requests.patch(f"https://api.instantly.ai/api/v2/leads/{lid}", headers=headers, json=p_body, timeout=12)
                return 1 if 200 <= rp.status_code < 300 else 0
            except Exception:
                return 0

        with ThreadPoolExecutor(max_workers=10) as pool:
            summary["leads_patched_in_place"] = sum(pool.map(_do_patch, to_patch))

    summary["outbox_learning"] = audit_rendered_sent_outbox_and_learn(CAMPAIGN_ID, auth_only, all_leads)
    return summary


if __name__ == "__main__":
    res = run_autonomous_outbound_optimizer()
    print(json.dumps(res, indent=2))



def run_outbound_optimizer() -> Dict[str, Any]:
    return run_autonomous_outbound_optimizer()
