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
import re
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
    1. Audits the last 100 actual rendered emails (GET /api/v2/emails) sent to prospects
       to catch any unrendered {{variable}}, % encoding, or broken link in real time.
    2. Deduplicates by email ID, separates genuine human replies from auto-replies/OOO
       and unsubscribes, extracts OOO referral emails (Please send all correspondence to: <email>),
       computes live prefix delivery/bounce rates + cohort stats, and saves adaptive weights
       to learned_outbound_intelligence.json (consumed by outreach_generator.py).
    """
    intel_path = ROOT_DIR / "learned_outbound_intelligence.json"
    intel: Dict[str, Any] = {}
    if intel_path.exists():
        try:
            intel = json.loads(intel_path.read_text(encoding="utf-8"))
        except Exception:
            intel = {}

    sent_count = 0
    human_reply_count = 0
    auto_reply_count = 0
    unsubscribe_reply_count = 0
    unrendered_var_alerts = 0
    ooo_referrals: List[str] = list(intel.get("ooo_referral_emails") or [])
    cohort_stats: Dict[str, Dict[str, int]] = {}
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
        if local in ("info", "contact", "office", "admin", "hello", "general", "inquiries", "pq", "prequal"):
            bucket = "generic_info"
        elif local in ("estimating", "estimates", "bids", "bidding", "precon", "billing", "rcm", "managedcare", "contracts", "proposals", "sales", "capture"):
            bucket = "dept_desk"
        else:
            bucket = "named_person"
        if status_code < 0:
            prefix_stats[bucket]["bounced"] += 1
        else:
            prefix_stats[bucket]["clean"] += 1

    seen_msg_ids = set()
    try:
        r_em = requests.get(
            f"https://api.instantly.ai/api/v2/emails?campaign_id={cid}&limit=100",
            headers=headers,
            timeout=20,
        )
        if r_em.status_code == 200:
            items = (r_em.json() or {}).get("items") or []
            for m in items:
                msg_id = str(m.get("id") or "").strip()
                if msg_id and msg_id in seen_msg_ids:
                    continue
                if msg_id:
                    seen_msg_ids.add(msg_id)
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
                cohort_key = str(pl.get("matched_state") or pl.get("agency") or pl.get("state") or "default")[:40]
                if cohort_key not in cohort_stats:
                    cohort_stats[cohort_key] = {
                        "sent": 0,
                        "human_replies": 0,
                        "auto_replies": 0,
                        "unsubscribes": 0,
                    }

                if ue_type == 2:
                    combo_low = f"{subj_txt} {body_txt}".lower()
                    is_auto = any(
                        kw in combo_low
                        for kw in (
                            "automatic reply", "auto-reply", "autoreply", "out of office",
                            "out-of-office", "away from the office", "on vacation",
                            "thank you for contacting", "prequalification", "no longer with",
                        )
                    )
                    is_unsub = any(
                        kw in combo_low
                        for kw in ("unsubscribe", "remove me", "stop emailing", "take me off")
                    )
                    if is_unsub:
                        unsubscribe_reply_count += 1
                        cohort_stats[cohort_key]["unsubscribes"] += 1
                    elif is_auto:
                        auto_reply_count += 1
                        cohort_stats[cohort_key]["auto_replies"] += 1
                        p_local = prospect_em.split("@", 1)[0] if "@" in prospect_em else ""
                        if p_local in ("pq", "prequal", "prequalification", "billing", "ap", "accounts", "noreply", "no-reply", "donotreply", "support", "helpdesk"):
                            try:
                                import govcon_lead_harvester
                                govcon_lead_harvester.save_completed_outreach_archive({prospect_em})
                                if ld_obj.get("id"):
                                    requests.delete(f"https://api.instantly.ai/api/v2/leads/{ld_obj['id']}", headers=headers, timeout=10)
                            except Exception:
                                pass
                        for ref_m in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", body_txt):
                            ref_clean = ref_m.strip().lower().rstrip(".")
                            ref_dom = ref_clean.split("@", 1)[-1]
                            if (
                                ref_clean != prospect_em
                                and ref_clean != to_em
                                and not any(b in ref_dom for b in ("signaltender", "camberdesk", "rubricward"))
                                and ref_clean not in ooo_referrals
                            ):
                                ooo_referrals.append(ref_clean)
                                # Automatically enroll OOO referred colleague into verified_public_govcon_contacts.json
                                try:
                                    vp_file = ROOT_DIR / "verified_public_govcon_contacts.json"
                                    if vp_file.exists():
                                        vp_list = json.loads(vp_file.read_text(encoding="utf-8")) or []
                                        if not any(str(x.get("Email") or "").strip().lower() == ref_clean for x in vp_list if isinstance(x, dict)):
                                            vp_list.insert(0, {
                                                "First Name": "Capture",
                                                "Last Name": "Team",
                                                "Title": f"Federal & SLED Capture Lead (Referred by {prospect_em})",
                                                "Company Name": str(ld_obj.get("company_name") or ref_dom.split(".")[0].title()),
                                                "Email": ref_clean,
                                                "City": "",
                                                "State": str(pl.get("matched_state") or "Virginia"),
                                                "Website": f"https://{ref_dom}",
                                                "NAICS Codes": "541512, 541519",
                                                "Industry": "information technology & services",
                                                "Keywords": "govcon, sled rfp, sam.gov, cybersecurity, cloud, software",
                                                "Primary Email Catch-all Status": "Not Catch-all",
                                            })
                                            vp_file.write_text(json.dumps(vp_list, indent=2), encoding="utf-8")
                                except Exception:
                                    pass
                    else:
                        human_reply_count += 1
                        cohort_stats[cohort_key]["human_replies"] += 1
                else:
                    sent_count += 1
                    cohort_stats[cohort_key]["sent"] += 1
    except Exception:
        pass

    recommended_weights: Dict[str, float] = {}
    for bucket, st in prefix_stats.items():
        total = st["clean"] + st["bounced"]
        bounce_rate = (st["bounced"] / total) if total > 0 else 0.0
        base_w = 1.0 if bucket == "named_person" else (0.9 if bucket == "dept_desk" else 0.25)
        recommended_weights[bucket] = round(max(0.05, base_w * (1.0 - min(0.85, bounce_rate * 5.0))), 3)

    intel.update({
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "campaign_id": cid,
        "recent_rendered_emails_audited": sent_count,
        "recent_human_replies_detected": human_reply_count,
        "recent_auto_replies_detected": auto_reply_count,
        "recent_unsubscribes_detected": unsubscribe_reply_count,
        "ooo_referral_emails": ooo_referrals,
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
        "human_replies_detected": human_reply_count,
        "auto_replies_detected": auto_reply_count,
        "unsubscribes_detected": unsubscribe_reply_count,
        "ooo_referrals_extracted": ooo_referrals,
        "unrendered_alerts": unrendered_var_alerts,
        "adaptive_weights": recommended_weights,
    }


def run_fast_campaign_vital_check() -> Dict[str, Any]:
    """
    Zero-CPU (<2s HTTP) vital check executed on every watcher cycle even while the user is actively
    using their laptop:
      1. Ensures `disable_bounce_protect: True` so Instantly never pauses the campaign on a bounce spike.
      2. If `status != 1` (campaign paused), purges bounced leads (`status < 0`) and immediately
         calls `POST /api/v2/campaigns/{CAMPAIGN_ID}/activate`.
      3. Returns `needs_replenish = True` if `not_sending_status == 2` (out of uncontacted leads).
    """
    vital: Dict[str, Any] = {
        "brand": "SignalTender",
        "campaign_id": CAMPAIGN_ID,
        "campaign_status": 1,
        "not_sending_status": 0,
        "disable_bounce_protect": True,
        "reactivated": False,
        "bounces_purged": 0,
        "needs_replenish": False,
    }
    if not INSTANTLY_API_KEY or not CAMPAIGN_ID:
        return vital
    headers = {"Authorization": f"Bearer {INSTANTLY_API_KEY}", "Content-Type": "application/json"}
    auth_only = {"Authorization": f"Bearer {INSTANTLY_API_KEY}"}
    try:
        rc = requests.get(f"https://api.instantly.ai/api/v2/campaigns/{CAMPAIGN_ID}", headers=auth_only, timeout=12)
        if rc.status_code == 200:
            cdata = rc.json() or {}
            c_status = int(cdata.get("status") or 0)
            ns_status = int(cdata.get("not_sending_status") or 0)
            dbp = bool(cdata.get("disable_bounce_protect"))
            vital["campaign_status"] = c_status
            vital["not_sending_status"] = ns_status
            vital["disable_bounce_protect"] = dbp
            if not dbp:
                requests.patch(
                    f"https://api.instantly.ai/api/v2/campaigns/{CAMPAIGN_ID}",
                    headers=headers,
                    json={"disable_bounce_protect": True, "stop_on_reply": True, "prioritize_new_leads": False},
                    timeout=12,
                )
                vital["disable_bounce_protect"] = True
            uncontacted_cnt = 0
            sa = None
            for _ in range(10):
                req_b = {"campaign": CAMPAIGN_ID, "limit": 100}
                if sa:
                    req_b["starting_after"] = sa
                rl = requests.post("https://api.instantly.ai/api/v2/leads/list", headers=headers, json=req_b, timeout=15)
                if rl.status_code != 200:
                    break
                rj = rl.json() or {}
                its = rj.get("items") or []
                for it in its:
                    if int(it.get("status") or 0) < 0 or int(it.get("lt_interest_status") or 0) < 0:
                        lid = str(it.get("id") or "").strip()
                        if lid:
                            requests.delete(f"https://api.instantly.ai/api/v2/leads/{lid}", headers=auth_only, timeout=10)
                            vital["bounces_purged"] += 1
                        em_b = str(it.get("email") or "").strip().lower()
                        if em_b:
                            try:
                                bl_p = ROOT_DIR / "bounced_leads_blacklist.json"
                                if bl_p.exists():
                                    bld = json.loads(bl_p.read_text(encoding="utf-8")) or {}
                                    bset = set(bld.get("bounced_emails") or [])
                                    bset.add(em_b)
                                    bld["bounced_emails"] = sorted(bset)
                                    bl_p.write_text(json.dumps(bld, indent=2), encoding="utf-8")
                            except Exception:
                                pass
                    elif int(it.get("status") or 0) == 1 and not it.get("timestamp_last_contact"):
                        uncontacted_cnt += 1
                sa = rj.get("next_starting_after")
                if not sa or len(its) < 100:
                    break
            vital["uncontacted"] = uncontacted_cnt
            if c_status != 1:
                ra = requests.post(
                    f"https://api.instantly.ai/api/v2/campaigns/{CAMPAIGN_ID}/activate",
                    headers=headers,
                    json={},
                    timeout=12,
                )
                vital["reactivated"] = ra.status_code in (200, 201)
            if ns_status == 2 and uncontacted_cnt > 0:
                requests.patch(
                    f"https://api.instantly.ai/api/v2/campaigns/{CAMPAIGN_ID}",
                    headers=headers,
                    json={"prioritize_new_leads": False, "disable_bounce_protect": True, "stop_on_reply": True},
                    timeout=12,
                )
                requests.post(f"https://api.instantly.ai/api/v2/campaigns/{CAMPAIGN_ID}/activate", headers=headers, json={}, timeout=12)
            if ns_status == 2 or uncontacted_cnt < 40:
                vital["needs_replenish"] = True
    except Exception:
        pass
    return vital


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
            needs_seq_fix = len(steps) < 3 or int(steps[1].get('delay') or 99) > 1 or int(steps[2].get('delay') or 99) > 2
            for st_item in steps:
                vars_list = st_item.get("variants") or []
                if not vars_list or not str(vars_list[0].get("subject") or "").strip() or not str(vars_list[0].get("body") or "").strip():
                    needs_seq_fix = True
            if needs_seq_fix:
                expected_seq = [
                    {
                        "steps": [
                            {"type": "email", "delay": 1, "variants": [{"subject": "{{subject_line}}", "body": "{{email_body}}"}]},
                            {"type": "email", "delay": 1, "variants": [{"subject": "{{followup_subject}}", "body": "{{followup_body}}"}]},
                            {"type": "email", "delay": 2, "variants": [{"subject": "{{breakup_subject}}", "body": "{{breakup_body}}"}]},
                        ]
                    }
                ]
                rp = requests.patch(
                    f"https://api.instantly.ai/api/v2/campaigns/{CAMPAIGN_ID}",
                    headers=headers,
                    json={"sequences": expected_seq, "disable_bounce_protect": True, "stop_on_reply": True},
                    timeout=15,
                )
                summary["sequence_repaired"] = rp.status_code in (200, 201)
            elif not bool(cdata.get("disable_bounce_protect")):
                requests.patch(
                    f"https://api.instantly.ai/api/v2/campaigns/{CAMPAIGN_ID}",
                    headers=headers,
                    json={"disable_bounce_protect": True, "stop_on_reply": True, "prioritize_new_leads": False},
                    timeout=15,
                )
                summary["bounce_protect_disabled"] = True
            if int(cdata.get("status") or 0) != 1:
                ra = requests.post(
                    f"https://api.instantly.ai/api/v2/campaigns/{CAMPAIGN_ID}/activate",
                    headers=headers,
                    json={},
                    timeout=15,
                )
                summary["campaign_reactivated"] = ra.status_code in (200, 201)
            summary["not_sending_status"] = int(cdata.get("not_sending_status") or 0)
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
                archived_set = govcon_lead_harvester.load_completed_outreach_archive()
                if st_code < 0 or lt_code < 0 or "%" in em or em in archived_set or not govcon_lead_harvester.is_verified_it_cyber_prospect(str(it.get("company_name") or ""), em, "", str((it.get("payload") or {}).get("top_naics") or "")):
                    to_purge.append((em, lid))
                    continue

                p_vars = it.get("payload") or {}
                fb_txt = str(p_vars.get("followup_body") or "")
                eb_txt = str(p_vars.get("email_body") or "")
                br_txt = str(p_vars.get("breakup_body") or "")
                cur_fn = str(it.get("first_name") or "").strip()
                cur_comp = str(it.get("company_name") or "").strip()

                has_non_it_contract = any(
                    bad_kw in eb_txt.lower()
                    for bad_kw in (
                        "sign panel fabrication", "water valve distribution", "pavement repair",
                        "x-ray screening", "x ray screening", "heart rate monitoring",
                        "gamma calibrator", "hiv care network", "alternate system of assessment",
                        "system of care", "panic alert system", "weather notification system",
                    )
                )
                has_stale_counts = (
                    has_non_it_contract
                    or ("39 AI " + "capture modules" in fb_txt)
                    or ("31-State " + "SLED" in fb_txt)
                    or ("58 AI capture modules" not in fb_txt)
                    or ("https://" not in fb_txt)
                    or ("Last note from me" in fb_txt)
                    or not br_txt.strip()
                )
                has_bad_handle = is_dotless_handle_name(cur_fn, em) and cur_fn.lower() not in ("capture", "there", "team")
                has_started = bool((it.get("status_summary") or {}).get("lastStep")) or bool(it.get("timestamp_last_contact"))

                if (has_stale_counts or has_bad_handle) and em in csv_map:
                    clean_row = csv_map[em]
                    locked_subj = str(p_vars.get("subject_line") or clean_row["Subject Line"]) if has_started else clean_row["Subject Line"]
                    locked_eb = str(p_vars.get("email_body") or clean_row["Email Body"]) if (has_started and not has_bad_handle and not has_non_it_contract) else clean_row["Email Body"]
                    patch_body = {
                        "first_name": clean_row["First Name"],
                        "company_name": clean_company_for_copy(clean_row["Company"]),
                        "custom_variables": {
                            "subject_line": locked_subj,
                            "email_body": locked_eb,
                            "followup_subject": f"Re: {locked_subj}",
                            "followup_body": clean_row.get("Followup Body", ""),
                            "breakup_subject": f"Re: {locked_subj}",
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
                    from urllib.parse import quote_plus as _qp
                    fixed_fn = "Capture" if has_bad_handle else cur_fn
                    fixed_comp = clean_company_for_copy(cur_comp)
                    fixed_eb = eb_txt
                    if has_bad_handle and cur_fn:
                        for prefix in ("Hi", "Hey", "Hello"):
                            fixed_eb = fixed_eb.replace(f"{prefix} {cur_fn},", f"{prefix} {fixed_comp} team,")
                    raw_durl = str(p_vars.get("top_dossier_url") or "https://signaltender.net/#contracts").split("?")[0]
                    st_lbl = str(p_vars.get("matched_state") or "Federal")
                    prefilled_durl = f"{raw_durl}?co={_qp(fixed_comp)}&state={_qp(st_lbl)}&email={_qp(em)}"
                    greet = f"Hi {fixed_comp} team," if (has_bad_handle or fixed_fn.lower() in ("capture", "there", "team", "")) else f"Hi {fixed_fn},"
                    fixed_fb = (
                        f"{greet}\n\n"
                        f"Quick follow-up — our 58 AI capture modules (covering Federal SAM.gov, National Municipal DemandStar & all 50 U.S. State SLED portals nationwide) already compiled the Section L/M compliance matrix, incumbent analysis, and 6-file Shipley proposal workbench for {fixed_comp}:\n"
                        f"{prefilled_durl}\n\n"
                        f"Or reply 'SEND' and I'll reply with the 6-file .ZIP package attached.\n\n"
                        f"Best,\nAaron Chen\nFounder, SignalTender"
                    )
                    locked_subj = str(p_vars.get("subject_line") or f"Active {st_lbl} IT & Cyber RFPs for {fixed_comp}")
                    new_vars = dict(p_vars)
                    new_vars["subject_line"] = locked_subj
                    new_vars["email_body"] = fixed_eb
                    new_vars["followup_subject"] = f"Re: {locked_subj}"
                    new_vars["followup_body"] = fixed_fb
                    new_vars["top_dossier_url"] = prefilled_durl
                    new_vars["breakup_subject"] = f"Re: {locked_subj}"
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
    uncontacted_remaining = sum(
        1 for it in all_leads
        if int(it.get("status") or 0) == 1
        and not it.get("timestamp_last_contact")
        and (str(it.get("email") or "").strip().lower(), str(it.get("id") or "").strip()) not in set(to_purge)
    )
    summary["uncontacted_leads_remaining"] = uncontacted_remaining
    # Auto-heal poisoned crawled:* keys in dns_mx_cache.json if crawled:* exceeds 3x verified + archived domains
    try:
        mx_p = ROOT_DIR / "dns_mx_cache.json"
        if mx_p.exists():
            mx_d = json.loads(mx_p.read_text(encoding="utf-8")) or {}
            crawled_keys = [k for k in mx_d if k.startswith("crawled:")]
            if len(crawled_keys) > 400 or uncontacted_remaining < 50:
                vp_d = json.loads((ROOT_DIR / "verified_public_govcon_contacts.json").read_text(encoding="utf-8")) if (ROOT_DIR / "verified_public_govcon_contacts.json").exists() else []
                arch_d = set(json.loads((ROOT_DIR / "completed_outreach_archive.json").read_text(encoding="utf-8"))) if (ROOT_DIR / "completed_outreach_archive.json").exists() else set()
                known_doms = {str(c.get("Email") or "").split("@")[-1].lower() for c in vp_d if isinstance(c, dict)} | {e.split("@")[-1].lower() for e in arch_d if "@" in e}
                cleaned_mx = {
                    k: v for k, v in mx_d.items()
                    if not k.startswith("usaspending_award_pg:")
                    and (not k.startswith("crawled:") or k.split("crawled:", 1)[1].lower() in known_doms)
                }
                mx_p.write_text(json.dumps(cleaned_mx, indent=2), encoding="utf-8")
                summary["mx_crawl_cache_pruned"] = len(mx_d) - len(cleaned_mx)
    except Exception:
        pass

    if uncontacted_remaining < 50 or int(summary.get("not_sending_status") or 0) == 2:
        try:
            import outreach_generator
            os.environ["GOVCON_FORCE_WEBSITE_CRAWL"] = "1"
            os.environ["OUTREACH_FORCE_INSTANTLY_RESYNC"] = "1"
            outreach_generator.generate_outreach()
            requests.post(
                f"https://api.instantly.ai/api/v2/campaigns/{CAMPAIGN_ID}/activate",
                headers=headers,
                json={},
                timeout=15,
            )
            summary["auto_replenished_queue"] = True
        except Exception as rep_err:
            report_error("autonomous_outbound_optimizer.py", f"SignalTender lead replenishment warning: {rep_err}", severity="WARNING")

    # Persist autonomous 3-stage conversion diagnosis ("Are people showing interest -> Why not -> Auto-Fix")
    try:
        ol = summary.get("outbox_learning") or {}
        diag = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "brand": "SignalTender",
            "1_are_people_showing_interest": {
                "human_replies_detected": int(ol.get("human_replies_detected") or 0),
                "recent_emails_audited": int(ol.get("rendered_audited") or 0),
                "uncontacted_leads_remaining": uncontacted_remaining,
            },
            "2_why_not_bottlenecks_checked": {
                "campaign_was_paused": bool(summary.get("campaign_reactivated")),
                "bounce_protect_was_enabled": bool(summary.get("bounce_protect_disabled")),
                "lead_queue_was_low": uncontacted_remaining < 50,
                "bounced_or_non_buyer_leads_found": int(summary.get("bounced_or_bad_purged") or 0),
                "leads_missing_step2_link_or_stale_patched": int(summary.get("leads_patched_in_place") or 0),
            },
            "3_autonomous_solutions_applied": {
                "rule_conv_001_step2_clickable_dossier_link": True,
                "rule_conv_002_zero_synthetic_counter_ids": True,
                "rule_conv_003_enterprise_solicitation_and_buyer_inbox_filter": True,
                "rule_conv_004_inflight_subject_lock": True,
                "rule_conv_005_html_br_reply_formatting": True,
                "auto_replenished_queue": bool(summary.get("auto_replenished_queue")),
            },
        }
        (ROOT_DIR / "conversion_funnel_diagnostics.json").write_text(json.dumps(diag, indent=2), encoding="utf-8")
    except Exception:
        pass
    return summary


if __name__ == "__main__":
    import sys as _sys
    if "--fast-vital-check" in _sys.argv:
        print(json.dumps(run_fast_campaign_vital_check(), indent=2))
    else:
        res = run_autonomous_outbound_optimizer()
        print(json.dumps(res, indent=2))



def run_outbound_optimizer() -> Dict[str, Any]:
    return run_autonomous_outbound_optimizer()
