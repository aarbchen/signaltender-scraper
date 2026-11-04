import py_compile
from pathlib import Path

# 1. Patch D:\CamberDesk\outbound_reply_responder.py
cd_path = Path(r"D:\CamberDesk\outbound_reply_responder.py")
cd_src = cd_path.read_text(encoding="utf-8")

old_cd_block = '''def lookup_prospect_context(from_email: str) -> Dict[str, str]:
    clean_em = str(from_email or "").strip().lower()
    dom = clean_em.split("@", 1)[1] if "@" in clean_em else ""
    matched: Dict[str, str] = {}
    for csv_candidate in (CSV_PATH, MLOT_CSV_PATH):
        if csv_candidate.exists() and not matched:
            try:
                with open(csv_candidate, mode="r", encoding="utf-8", newline="") as f:
                    for row in csv.DictReader(f):
                        row_em = str(row.get("email") or "").strip().lower()
                        if row_em == clean_em or (dom and row_em.endswith("@" + dom)):
                            matched = dict(row)
                            break
            except Exception:
                pass
    verified_json = ROOT_DIR / "verified_public_dot_contacts.json"
    if not matched and verified_json.exists():
        try:
            for item in json.loads(verified_json.read_text(encoding="utf-8")) or []:
                row_em = str(item.get("email") or "").strip().lower()
                if row_em == clean_em or (dom and row_em.endswith("@" + dom)):
                    matched = dict(item)
                    break
        except Exception:
            pass
    fallback_co = dom.split(".")[0].replace("-", " ").title() if dom else "your estimating team"
    res_state = matched.get("state") or "TX"
    res_pid = matched.get("project_id") or "TXDOT-CSJ-0015-13-412"
    comp_name = matched.get("company_name") or fallback_co
    raw_compiler = matched.get("compiler_url") or ""
    if not raw_compiler or "project_id=" not in raw_compiler or "api.camberdesk.com" in raw_compiler:
        raw_compiler = f"https://camberdesk.com/v1/camber-autopilot/compile-bid-package?project_id={res_pid}&state_code={res_state}&format=binary"
    raw_dossier = matched.get("dossier_url") or _build_prefilled_site_url("/", comp_name, res_state, clean_em, "lettings")
    if "?" not in raw_dossier and (comp_name or clean_em):
        q_params = urllib.parse.urlencode({"co": comp_name, "state": res_state, "email": clean_em})
        if "#" in raw_dossier:
            base_part, hash_part = raw_dossier.split("#", 1)
            raw_dossier = f"{base_part}?{q_params}#{hash_part}"
        else:
            raw_dossier = f"{raw_dossier}?{q_params}"
    return {
        "first_name": matched.get("first_name") or "Chief Estimator",
        "company_name": comp_name,
        "state": res_state,
        "project_id": res_pid,
        "project_title": matched.get("project_title") or "IH-35 Bridge Deck Replacement & Superpave Overlay",
        "dossier_url": raw_dossier,
        "compiler_url": raw_compiler,
        "tier1_stripe_url": _build_prefilled_site_url("/", comp_name, res_state, clean_em, "checkout-tier1"),
        "tier2_stripe_url": _build_prefilled_site_url("/", comp_name, res_state, clean_em, "checkout-tier2"),
        "tier3_stripe_url": _build_prefilled_site_url("/", comp_name, res_state, clean_em, "checkout-tier3"),
        "workspace_checkout_url": _build_prefilled_site_url("/", comp_name, res_state, clean_em, "checkout"),
    }


def _strip_quoted_thread(raw_text: str) -> str:
    """Strip quoted email history ('On ... wrote:', '> ...', '-----Original Message-----') before classifying."""
    lines: List[str] = []
    for ln in str(raw_text or "").splitlines():
        s = ln.strip()
        if s.startswith(">"):
            continue
        if s.lower().startswith("on ") and s.lower().endswith("wrote:"):
            break
        if s.startswith("-----Original Message-----") or s.startswith("From: "):
            break
        lines.append(ln)
    cleaned = "\\n".join(lines).strip()
    return cleaned if cleaned else str(raw_text or "").strip()


def classify_estimator_reply(reply_text: str, subject: str = "", from_email: str = "") -> str:
    stripped = _strip_quoted_thread(reply_text)
    txt = stripped.lower()
    subj_low = str(subject or "").lower()
    em_low = str(from_email or "").lower()
    if (
        em_low.startswith(("mailer-daemon@", "postmaster@", "noreply-dmarc@", "bounces@"))
        or subj_low.startswith(("undeliverable:", "delivery status notification", "returned mail:", "mail delivery failed", "failure notice"))
        or any(
            b_p in txt
            for b_p in (
                "delivery to the following recipient failed",
                "550 5.1.1",
                "address not found",
                "user unknown",
                "mailbox unavailable",
            )
        )
    ):
        return "BOUNCE"
    if (
        subj_low.startswith(("automatic reply:", "auto-reply:", "out of office:", "out of the office:"))
        or any(
            ooo_p in txt
            for ooo_p in (
                "out of the office",
                "out of office",
                "currently away from",
                "limited access to email",
                "on vacation until",
                "on parental leave",
                "on medical leave",
                "away from my desk",
                "auto-reply",
                "automatic reply",
                "automated response",
                "this is an automated",
                "do not reply to this",
                "we have received your e-mail",
                "we have received your email",
                "our typical response time",
            )
        )
    ):
        return "OUT_OF_OFFICE"
    negated_unsub = any(
        neg in txt
        for neg in (
            "don't unsubscribe", "do not unsubscribe", "dont unsubscribe",
            "don't remove me", "do not remove me", "dont remove me",
            "don't take me off", "do not take me off", "dont take me off",
            "don't stop emailing", "do not stop emailing",
        )
    )
    if not negated_unsub and any(u in txt for u in ("unsubscribe", "remove me", "stop emailing", "not interested", "take me off", "no thanks", "off your list")):
        return "UNSUBSCRIBE"
    if "?" in stripped and not any(p in txt for p in ("send zip", "send it", "send over")):
        return "QUESTION"
    if any(p in txt for p in ("send zip", "send it", "yes", "sure", "send over", "interested", "bid tab", "spreadsheet")):
        return "POSITIVE_INTEREST"

    if ANTHROPIC_API_KEY and txt:
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 30,
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Classify this construction estimator email reply into exactly one label: "
                                "POSITIVE_INTEREST, QUESTION, or UNSUBSCRIBE.\\n\\n"
                                f"Reply: {stripped[:500]}"
                            ),
                        }
                    ],
                },
                timeout=15,
            )
            if resp.status_code == 200:
                out = ((resp.json().get("content") or [{}])[0].get("text") or "").upper()
                if "UNSUBSCRIBE" in out:
                    return "UNSUBSCRIBE"
                if "QUESTION" in out:
                    return "QUESTION"
        except Exception:
            pass
    return "POSITIVE_INTEREST"


def build_zip_fulfillment_reply(from_email: str, reply_text: str = "", label: str = "POSITIVE_INTEREST") -> Dict[str, str]:
    ctx = lookup_prospect_context(from_email)'''

new_cd_block = '''def _format_estimator_greeting(first_name: str, company_name: str) -> str:
    fn = str(first_name or "").strip()
    co = str(company_name or "").strip()
    role_tokens = {
        "estimating", "chief estimator", "estimator", "capture", "info", "sales",
        "team", "there", "contracts", "office", "admin", "bids", "bidding", "project",
        "estimating team", "preconstruction",
    }
    co_first = co.lower().split()[0] if co else ""
    if not fn or fn.lower() in role_tokens or (co and fn.lower() in (co.lower(), co_first)):
        if co and co.lower() not in ("your estimating team", "estimating team"):
            return f"Hi {co} Estimating team,"
        return "Hi there,"
    return f"Hi {fn},"


def lookup_prospect_context(from_email: str, reply_text: str = "", subject: str = "") -> Dict[str, str]:
    clean_em = str(from_email or "").strip().lower()
    dom = clean_em.split("@", 1)[1] if "@" in clean_em else ""
    combined_thread = f"{subject or ''}\\n{reply_text or ''}"
    thread_emails = {
        e.strip().lower()
        for e in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", combined_thread)
        if "camberdesk" not in e.lower()
    }
    matched: Dict[str, str] = {}
    for csv_candidate in (CSV_PATH, MLOT_CSV_PATH):
        if csv_candidate.exists() and not matched:
            try:
                with open(csv_candidate, mode="r", encoding="utf-8", newline="") as f:
                    rows = list(csv.DictReader(f))
                for row in rows:
                    row_em = str(row.get("email") or "").strip().lower()
                    if row_em == clean_em or (dom and row_em.endswith("@" + dom)) or (row_em and row_em in thread_emails):
                        matched = dict(row)
                        break
                if not matched and combined_thread.strip():
                    for row in rows:
                        pid_cand = str(row.get("project_id") or "").strip()
                        if pid_cand and len(pid_cand) >= 6 and pid_cand.lower() in combined_thread.lower():
                            matched = dict(row)
                            break
            except Exception:
                pass
    verified_json = ROOT_DIR / "verified_public_dot_contacts.json"
    if not matched and verified_json.exists():
        try:
            for item in json.loads(verified_json.read_text(encoding="utf-8")) or []:
                row_em = str(item.get("email") or "").strip().lower()
                if row_em == clean_em or (dom and row_em.endswith("@" + dom)) or (row_em and row_em in thread_emails):
                    matched = dict(item)
                    break
        except Exception:
            pass
    fallback_co = dom.split(".")[0].replace("-", " ").title() if dom else "your estimating team"
    res_state = matched.get("state") or "TX"
    res_pid = matched.get("project_id") or "TXDOT-CSJ-0015-13-412"
    comp_name = matched.get("company_name") or fallback_co
    raw_compiler = matched.get("compiler_url") or ""
    if not raw_compiler or "project_id=" not in raw_compiler or "api.camberdesk.com" in raw_compiler:
        raw_compiler = f"https://camberdesk.com/v1/camber-autopilot/compile-bid-package?project_id={res_pid}&state_code={res_state}&format=binary"
    if comp_name and comp_name.lower() not in ("your estimating team", "estimating team") and "co=" not in raw_compiler:
        sep = "&" if "?" in raw_compiler else "?"
        raw_compiler = f"{raw_compiler}{sep}{urllib.parse.urlencode({'co': comp_name})}"
    raw_dossier = matched.get("dossier_url") or _build_prefilled_site_url("/", comp_name, res_state, clean_em, "lettings")
    if "?" not in raw_dossier and (comp_name or clean_em):
        q_params = urllib.parse.urlencode({"co": comp_name, "state": res_state, "email": clean_em})
        if "#" in raw_dossier:
            base_part, hash_part = raw_dossier.split("#", 1)
            raw_dossier = f"{base_part}?{q_params}#{hash_part}"
        else:
            raw_dossier = f"{raw_dossier}?{q_params}"
    return {
        "first_name": matched.get("first_name") or "Chief Estimator",
        "company_name": comp_name,
        "state": res_state,
        "project_id": res_pid,
        "project_title": matched.get("project_title") or "IH-35 Bridge Deck Replacement & Superpave Overlay",
        "dossier_url": raw_dossier,
        "compiler_url": raw_compiler,
        "tier1_stripe_url": _build_prefilled_site_url("/", comp_name, res_state, clean_em, "checkout-tier1"),
        "tier2_stripe_url": _build_prefilled_site_url("/", comp_name, res_state, clean_em, "checkout-tier2"),
        "tier3_stripe_url": _build_prefilled_site_url("/", comp_name, res_state, clean_em, "checkout-tier3"),
        "workspace_checkout_url": _build_prefilled_site_url("/", comp_name, res_state, clean_em, "checkout"),
    }


def _strip_quoted_thread(raw_text: str) -> str:
    """Strip quoted email history ('On ... wrote:', '> ...', '-----Original Message-----') before classifying."""
    lines: List[str] = []
    for ln in str(raw_text or "").splitlines():
        s = ln.strip()
        if s.startswith(">"):
            continue
        if s.lower().startswith("on ") and s.lower().endswith("wrote:"):
            break
        if s.startswith("-----Original Message-----") or s.startswith("From: "):
            break
        lines.append(ln)
    cleaned = "\\n".join(lines).strip()
    return cleaned if cleaned else str(raw_text or "").strip()


def classify_estimator_reply(reply_text: str, subject: str = "", from_email: str = "") -> str:
    stripped = _strip_quoted_thread(reply_text)
    txt = stripped.lower()
    subj_low = str(subject or "").lower()
    em_low = str(from_email or "").lower()
    if (
        em_low.startswith(("mailer-daemon@", "postmaster@", "noreply-dmarc@", "bounces@"))
        or subj_low.startswith(("undeliverable:", "delivery status notification", "returned mail:", "mail delivery failed", "failure notice"))
        or any(
            b_p in txt
            for b_p in (
                "delivery to the following recipient failed",
                "550 5.1.1",
                "address not found",
                "user unknown",
                "mailbox unavailable",
                "does not exist",
            )
        )
    ):
        return "BOUNCE"
    if (
        subj_low.startswith(("automatic reply:", "auto-reply:", "out of office:", "out of the office:", "anti-spam", "email verification"))
        or any(
            ooo_p in txt
            for ooo_p in (
                "out of the office",
                "out of office",
                "currently away from",
                "limited access to email",
                "on vacation until",
                "on parental leave",
                "on medical leave",
                "away from my desk",
                "auto-reply",
                "automatic reply",
                "automated response",
                "this is an automated",
                "do not reply to this",
                "we have received your e-mail",
                "we have received your email",
                "our typical response time",
                "barracuda",
                "mimecast",
                "proofpoint",
                "boxbe",
                "verify your email",
                "challenge-response",
                "unattended mailbox",
                "no longer monitored",
            )
        )
    ):
        return "OUT_OF_OFFICE"
    negated_unsub = any(
        neg in txt
        for neg in (
            "don't unsubscribe", "do not unsubscribe", "dont unsubscribe",
            "don't remove me", "do not remove me", "dont remove me",
            "don't take me off", "do not take me off", "dont take me off",
            "don't stop emailing", "do not stop emailing",
        )
    )
    unsub_phrases = (
        "unsubscribe", "remove me", "remove us", "remove this", "take me off", "take us off",
        "stop emailing", "stop sending", "stop contacting", "do not contact", "don't contact",
        "dont contact", "never email", "not interested", "no thanks", "off your list",
        "wrong person", "wrong email", "retired", "no longer with", "left the company",
        "doesn't work here", "does not work here", "not bidding", "don't bid", "do not bid",
        "opt out", "opt-out", "who gave you", "why are you emailing",
    )
    if not negated_unsub and any(u in txt for u in unsub_phrases):
        return "UNSUBSCRIBE"
    if "?" in stripped and not any(p in txt for p in ("send zip", "send it", "send over")):
        return "QUESTION"
    if (
        any(p in txt for p in ("send zip", "send it", "send over", "bid tab", "spreadsheet"))
        or re.search(r"\\b(yes|yeah|yep|please|interested)\\b|(?<!not\\s)(?<!un)\\bsure\\b", txt)
    ):
        return "POSITIVE_INTEREST"

    if ANTHROPIC_API_KEY and txt:
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 30,
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Classify this construction estimator email reply into exactly one label: "
                                "POSITIVE_INTEREST, QUESTION, or UNSUBSCRIBE.\\n\\n"
                                f"Reply: {stripped[:500]}"
                            ),
                        }
                    ],
                },
                timeout=15,
            )
            if resp.status_code == 200:
                out = ((resp.json().get("content") or [{}])[0].get("text") or "").upper()
                if "UNSUBSCRIBE" in out:
                    return "UNSUBSCRIBE"
                if "QUESTION" in out:
                    return "QUESTION"
        except Exception:
            pass
    return "POSITIVE_INTEREST"


def build_zip_fulfillment_reply(from_email: str, reply_text: str = "", label: str = "POSITIVE_INTEREST", subject: str = "") -> Dict[str, str]:
    ctx = lookup_prospect_context(from_email, reply_text=reply_text, subject=subject)'''

assert old_cd_block in cd_src, "old_cd_block not found"
cd_src = cd_src.replace(old_cd_block, new_cd_block, 1)

cd_src = cd_src.replace(
    '    body = (\n        f"Hi {ctx[\'first_name\']},\\n\\n"',
    '    greeting_line = _format_estimator_greeting(ctx["first_name"], ctx["company_name"])\n    body = (\n        f"{greeting_line}\\n\\n"',
    1
)
cd_src = cd_src.replace(
    '        fname = info.get("first_name") or "Chief Estimator"\n        pid = info.get("project_id") or "TXDOT-CSJ-0015-13-412"\n        comp = info.get("company_name") or "your estimating team"',
    '        fname = info.get("first_name") or "Chief Estimator"\n        pid = info.get("project_id") or "TXDOT-CSJ-0015-13-412"\n        comp = info.get("company_name") or "your estimating team"\n        greeting_line = _format_estimator_greeting(fname, comp)',
    1
)
cd_src = cd_src.replace('body_48 = (\n                f"Hi {fname},\\n\\n"', 'body_48 = (\n                f"{greeting_line}\\n\\n"', 1)
cd_src = cd_src.replace('body_96 = (\n                f"Hi {fname},\\n\\n"', 'body_96 = (\n                f"{greeting_line}\\n\\n"', 1)
cd_src = cd_src.replace(
    'pkg = build_zip_fulfillment_reply(from_em, reply_text=body_txt, label=label)',
    'pkg = build_zip_fulfillment_reply(from_em, reply_text=body_txt, label=label, subject=subj_in)',
    1
)
cd_path.write_text(cd_src, encoding="utf-8")
py_compile.compile(str(cd_path), doraise=True)
print("[OK] Patched D:\\CamberDesk\\outbound_reply_responder.py")


# 2. Patch D:\RubricWard\outbound_reply_responder.py
rw_path = Path(r"D:\RubricWard\outbound_reply_responder.py")
rw_src = rw_path.read_text(encoding="utf-8")

old_rw_block = '''def lookup_prospect_context(from_email: str) -> Dict[str, str]:
    clean_em = str(from_email or "").strip().lower()
    dom = clean_em.split("@", 1)[1] if "@" in clean_em else ""
    matched: Dict[str, str] = {}
    if CSV_PATH.exists():
        try:
            with open(CSV_PATH, mode="r", encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    row_em = str(row.get("email") or "").strip().lower()
                    if row_em == clean_em or (dom and row_em.endswith("@" + dom)):
                        matched = dict(row)
                        break
        except Exception:
            pass
    verified_json = ROOT_DIR / "verified_public_dot_contacts.json"
    if not matched and verified_json.exists():
        try:
            for item in json.loads(verified_json.read_text(encoding="utf-8")) or []:
                row_em = str(item.get("email") or "").strip().lower()
                if row_em == clean_em or (dom and row_em.endswith("@" + dom)):
                    matched = dict(item)
                    break
        except Exception:
            pass
    fallback_co = dom.split(".")[0].replace("-", " ").title() if dom else "your revenue cycle team"
    res_state = matched.get("state") or matched.get("state_code") or "TX"
    res_pid = matched.get("project_id") or matched.get("letting_id") or "TXDOI-MRF-CPT-29881-DFW"
    comp_name = matched.get("company_name") or fallback_co
    raw_compiler = matched.get("compiler_url") or ""
    if not raw_compiler or "project_id=" not in raw_compiler or "api.rubricward.com" in raw_compiler:
        raw_compiler = f"{SITE_BASE_URL}/v1/camber-autopilot/compile-bid-package?project_id={res_pid}&state_code={res_state}&format=binary"
    raw_dossier = matched.get("dossier_url") or _build_prefilled_site_url("/", comp_name, res_state, clean_em, "lettings")
    if "?" not in raw_dossier and (comp_name or clean_em):
        q_params = urllib.parse.urlencode({"co": comp_name, "state": res_state, "email": clean_em})
        if "#" in raw_dossier:
            base_part, hash_part = raw_dossier.split("#", 1)
            raw_dossier = f"{base_part}?{q_params}#{hash_part}"
        else:
            raw_dossier = f"{raw_dossier}?{q_params}"
    return {
        "first_name": matched.get("first_name") or "Revenue Cycle Director",
        "company_name": comp_name,
        "state": res_state,
        "project_id": res_pid,
        "project_title": matched.get("project_title") or "Commercial Payer TiC MRF Underpayment & NSA IDR Cohort",
        "dossier_url": raw_dossier,
        "compiler_url": raw_compiler,
        "tier2_checkout_url": _build_prefilled_site_url("/", comp_name, res_state, clean_em, "checkout-tier2"),
        "tier3_checkout_url": _build_prefilled_site_url("/", comp_name, res_state, clean_em, "checkout-tier3"),
    }


def classify_rcm_reply(reply_text: str, subject: str = "", from_email: str = "") -> str:
    stripped = _strip_quoted_thread(reply_text)
    txt = stripped.lower()
    subj_low = str(subject or "").lower()
    em_low = str(from_email or "").lower()
    if (
        em_low.startswith(("mailer-daemon@", "postmaster@", "noreply-dmarc@", "bounces@"))
        or subj_low.startswith(("undeliverable:", "delivery status notification", "returned mail:", "mail delivery failed", "failure notice"))
        or any(
            b_p in txt
            for b_p in (
                "delivery to the following recipient failed",
                "550 5.1.1",
                "address not found",
                "user unknown",
                "mailbox unavailable",
            )
        )
    ):
        return "BOUNCE"
    if (
        subj_low.startswith(("automatic reply:", "auto-reply:", "out of office:", "out of the office:"))
        or any(
            ooo_p in txt
            for ooo_p in (
                "out of the office",
                "out of office",
                "currently away from",
                "limited access to email",
                "on vacation until",
                "on parental leave",
                "on medical leave",
                "away from my desk",
                "auto-reply",
                "automatic reply",
                "automated response",
                "this is an automated",
                "do not reply to this",
                "we have received your e-mail",
                "we have received your email",
                "our typical response time",
            )
        )
    ):
        return "OUT_OF_OFFICE"
    negated_unsub = any(
        neg in txt
        for neg in (
            "don't unsubscribe", "do not unsubscribe", "dont unsubscribe",
            "don't remove me", "do not remove me", "dont remove me",
            "don't take me off", "do not take me off", "dont take me off",
            "don't stop emailing", "do not stop emailing",
        )
    )
    if not negated_unsub and any(u in txt for u in ("unsubscribe", "remove me", "stop emailing", "not interested", "take me off", "no thanks", "off your list")):
        return "UNSUBSCRIBE"
    if "?" in stripped and not any(p in txt for p in ("send zip", "send mrf", "mrf", "send it", "send over")):
        return "QUESTION"
    if any(p in txt for p in ("send zip", "send mrf", "mrf", "send it", "yes", "sure", "send over", "interested", "mrf", "appeal", "spreadsheet")):
        return "POSITIVE_INTEREST"'''

new_rw_block = '''def _format_rcm_greeting(first_name: str, company_name: str) -> str:
    fn = str(first_name or "").strip()
    co = str(company_name or "").strip()
    role_tokens = {
        "revenue cycle", "revenue cycle director", "revenue cycle team",
        "specialty group revenue cycle team", "billing", "managed care",
        "director", "capture", "info", "sales", "team", "there", "contracts",
        "office", "admin", "patient financial services",
    }
    co_first = co.lower().split()[0] if co else ""
    if not fn or fn.lower() in role_tokens or "revenue cycle" in fn.lower() or (co and fn.lower() in (co.lower(), co_first)):
        if co and co.lower() not in ("your revenue cycle team", "revenue cycle team", "specialty group revenue cycle team"):
            return f"Hi {co} Revenue Cycle team,"
        return "Hi there,"
    return f"Hi {fn},"


def lookup_prospect_context(from_email: str, reply_text: str = "", subject: str = "") -> Dict[str, str]:
    clean_em = str(from_email or "").strip().lower()
    dom = clean_em.split("@", 1)[1] if "@" in clean_em else ""
    combined_thread = f"{subject or ''}\\n{reply_text or ''}"
    thread_emails = {
        e.strip().lower()
        for e in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", combined_thread)
        if "rubricward" not in e.lower()
    }
    matched: Dict[str, str] = {}
    if CSV_PATH.exists():
        try:
            with open(CSV_PATH, mode="r", encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            for row in rows:
                row_em = str(row.get("email") or "").strip().lower()
                if row_em == clean_em or (dom and row_em.endswith("@" + dom)) or (row_em and row_em in thread_emails):
                    matched = dict(row)
                    break
            if not matched and combined_thread.strip():
                for row in rows:
                    pid_cand = str(row.get("project_id") or "").strip()
                    if pid_cand and len(pid_cand) >= 6 and pid_cand.lower() in combined_thread.lower():
                        matched = dict(row)
                        break
        except Exception:
            pass
    verified_json = ROOT_DIR / "verified_public_dot_contacts.json"
    if not matched and verified_json.exists():
        try:
            for item in json.loads(verified_json.read_text(encoding="utf-8")) or []:
                row_em = str(item.get("email") or "").strip().lower()
                if row_em == clean_em or (dom and row_em.endswith("@" + dom)) or (row_em and row_em in thread_emails):
                    matched = dict(item)
                    break
        except Exception:
            pass
    fallback_co = dom.split(".")[0].replace("-", " ").title() if dom else "your revenue cycle team"
    res_state = matched.get("state") or matched.get("state_code") or "TX"
    res_pid = matched.get("project_id") or matched.get("letting_id") or "TXDOI-MRF-CPT-29881-DFW"
    comp_name = matched.get("company_name") or fallback_co
    raw_compiler = matched.get("compiler_url") or ""
    if not raw_compiler or "project_id=" not in raw_compiler or "api.rubricward.com" in raw_compiler:
        raw_compiler = f"{SITE_BASE_URL}/v1/camber-autopilot/compile-bid-package?project_id={res_pid}&state_code={res_state}&format=binary"
    if comp_name and comp_name.lower() not in ("your revenue cycle team", "revenue cycle team") and "co=" not in raw_compiler:
        sep = "&" if "?" in raw_compiler else "?"
        raw_compiler = f"{raw_compiler}{sep}{urllib.parse.urlencode({'co': comp_name})}"
    raw_dossier = matched.get("dossier_url") or _build_prefilled_site_url("/", comp_name, res_state, clean_em, "lettings")
    if "?" not in raw_dossier and (comp_name or clean_em):
        q_params = urllib.parse.urlencode({"co": comp_name, "state": res_state, "email": clean_em})
        if "#" in raw_dossier:
            base_part, hash_part = raw_dossier.split("#", 1)
            raw_dossier = f"{base_part}?{q_params}#{hash_part}"
        else:
            raw_dossier = f"{raw_dossier}?{q_params}"
    return {
        "first_name": matched.get("first_name") or "Revenue Cycle Director",
        "company_name": comp_name,
        "state": res_state,
        "project_id": res_pid,
        "project_title": matched.get("project_title") or "Commercial Payer TiC MRF Underpayment & NSA IDR Cohort",
        "dossier_url": raw_dossier,
        "compiler_url": raw_compiler,
        "tier2_checkout_url": _build_prefilled_site_url("/", comp_name, res_state, clean_em, "checkout-tier2"),
        "tier3_checkout_url": _build_prefilled_site_url("/", comp_name, res_state, clean_em, "checkout-tier3"),
    }


def classify_rcm_reply(reply_text: str, subject: str = "", from_email: str = "") -> str:
    stripped = _strip_quoted_thread(reply_text)
    txt = stripped.lower()
    subj_low = str(subject or "").lower()
    em_low = str(from_email or "").lower()
    if (
        em_low.startswith(("mailer-daemon@", "postmaster@", "noreply-dmarc@", "bounces@"))
        or subj_low.startswith(("undeliverable:", "delivery status notification", "returned mail:", "mail delivery failed", "failure notice"))
        or any(
            b_p in txt
            for b_p in (
                "delivery to the following recipient failed",
                "550 5.1.1",
                "address not found",
                "user unknown",
                "mailbox unavailable",
                "does not exist",
            )
        )
    ):
        return "BOUNCE"
    if (
        subj_low.startswith(("automatic reply:", "auto-reply:", "out of office:", "out of the office:", "anti-spam", "email verification"))
        or any(
            ooo_p in txt
            for ooo_p in (
                "out of the office",
                "out of office",
                "currently away from",
                "limited access to email",
                "on vacation until",
                "on parental leave",
                "on medical leave",
                "away from my desk",
                "auto-reply",
                "automatic reply",
                "automated response",
                "this is an automated",
                "do not reply to this",
                "we have received your e-mail",
                "we have received your email",
                "our typical response time",
                "barracuda",
                "mimecast",
                "proofpoint",
                "boxbe",
                "verify your email",
                "challenge-response",
                "unattended mailbox",
                "no longer monitored",
            )
        )
    ):
        return "OUT_OF_OFFICE"
    negated_unsub = any(
        neg in txt
        for neg in (
            "don't unsubscribe", "do not unsubscribe", "dont unsubscribe",
            "don't remove me", "do not remove me", "dont remove me",
            "don't take me off", "do not take me off", "dont take me off",
            "don't stop emailing", "do not stop emailing",
        )
    )
    unsub_phrases = (
        "unsubscribe", "remove me", "remove us", "remove this", "take me off", "take us off",
        "stop emailing", "stop sending", "stop contacting", "do not contact", "don't contact",
        "dont contact", "never email", "not interested", "no thanks", "off your list",
        "wrong person", "wrong email", "retired", "no longer with", "left the company",
        "doesn't work here", "does not work here", "opt out", "opt-out",
        "who gave you", "why are you emailing",
    )
    if not negated_unsub and any(u in txt for u in unsub_phrases):
        return "UNSUBSCRIBE"
    if "?" in stripped and not any(p in txt for p in ("send zip", "send mrf", "mrf", "send it", "send over")):
        return "QUESTION"
    if (
        any(p in txt for p in ("send zip", "send mrf", "mrf", "send it", "send over", "appeal", "spreadsheet"))
        or re.search(r"\\b(yes|yeah|yep|please|interested)\\b|(?<!not\\s)(?<!un)\\bsure\\b", txt)
    ):
        return "POSITIVE_INTEREST"'''

assert old_rw_block in rw_src, "old_rw_block not found"
rw_src = rw_src.replace(old_rw_block, new_rw_block, 1)

rw_src = rw_src.replace(
    'def build_reply_response(prospect_name: str, letting_id: str, inbound_body: str = "", from_email: str = "", label: str = "POSITIVE_INTEREST") -> Dict[str, str]:\n    cleaned_inbound = _strip_quoted_thread(inbound_body)\n    ctx = lookup_prospect_context(from_email) if from_email else {',
    'def build_reply_response(prospect_name: str, letting_id: str, inbound_body: str = "", from_email: str = "", label: str = "POSITIVE_INTEREST", subject: str = "") -> Dict[str, str]:\n    cleaned_inbound = _strip_quoted_thread(inbound_body)\n    ctx = lookup_prospect_context(from_email, reply_text=inbound_body, subject=subject) if from_email else {',
    1
)
rw_src = rw_src.replace(
    '    t2_url = ctx.get("tier2_checkout_url") or TIER2_STRIPE_URL\n    t3_url = ctx.get("tier3_checkout_url") or TIER3_STRIPE_URL\n    return {\n        "model": ANTHROPIC_MODEL,\n        "letting_id": ctx["project_id"],\n        "cleaned_inbound": cleaned_inbound,\n        "subject": f"Re: Commercial Payer TiC MRF, ERISA Appeal & NSA IDR 6-File .ZIP Package for {ctx[\'project_id\']}",\n        "body": (\n            f"Hi {prospect_name or ctx[\'first_name\']},\\n\\n"',
    '    t2_url = ctx.get("tier2_checkout_url") or TIER2_STRIPE_URL\n    t3_url = ctx.get("tier3_checkout_url") or TIER3_STRIPE_URL\n    greeting_line = _format_rcm_greeting(prospect_name or ctx.get("first_name", ""), ctx.get("company_name", ""))\n    return {\n        "model": ANTHROPIC_MODEL,\n        "letting_id": ctx["project_id"],\n        "cleaned_inbound": cleaned_inbound,\n        "subject": f"Re: Commercial Payer TiC MRF, ERISA Appeal & NSA IDR 6-File .ZIP Package for {ctx[\'project_id\']}",\n        "body": (\n            f"{greeting_line}\\n\\n"',
    1
)
rw_src = rw_src.replace(
    '        fname = info.get("first_name") or "there"\n        pid = info.get("project_id") or "TXDOI-MRF-CPT-29881-DFW"\n        comp = info.get("company_name") or "your revenue cycle team"',
    '        fname = info.get("first_name") or "there"\n        pid = info.get("project_id") or "TXDOI-MRF-CPT-29881-DFW"\n        comp = info.get("company_name") or "your revenue cycle team"\n        greeting_line = _format_rcm_greeting(fname, comp)',
    1
)
rw_src = rw_src.replace('body_48 = (\n                f"Hi {fname},\\n\\n"', 'body_48 = (\n                f"{greeting_line}\\n\\n"', 1)
rw_src = rw_src.replace('body_96 = (\n                f"Hi {fname},\\n\\n"', 'body_96 = (\n                f"{greeting_line}\\n\\n"', 1)
rw_src = rw_src.replace(
    'ctx = lookup_prospect_context(from_em)\n                    pkg = build_reply_response(\n                        prospect_name=ctx["first_name"],\n                        letting_id=ctx["project_id"],\n                        inbound_body=body_txt,\n                        from_email=from_em,\n                        label=label,\n                    )',
    'ctx = lookup_prospect_context(from_em, reply_text=body_txt, subject=subj_in)\n                    pkg = build_reply_response(\n                        prospect_name=ctx["first_name"],\n                        letting_id=ctx["project_id"],\n                        inbound_body=body_txt,\n                        from_email=from_em,\n                        label=label,\n                        subject=subj_in,\n                    )',
    1
)
rw_path.write_text(rw_src, encoding="utf-8")
py_compile.compile(str(rw_path), doraise=True)
print("[OK] Patched D:\\RubricWard\\outbound_reply_responder.py")


# 3. Patch d:\Daas\outbound_reply_responder.py
st_path = Path(r"d:\Daas\outbound_reply_responder.py")
st_src = st_path.read_text(encoding="utf-8")

old_st_unsub = '''    if not negated_unsub and any(
        p in low
        for p in ("unsubscribe", "remove me", "take me off", "stop emailing", "not interested", "no thanks", "off your list")
    ):
        return {"intent": "UNSUBSCRIBE", "reply_body": ""}

    subj_low = str(subject or "").lower()
    if (
        subj_low.startswith(("automatic reply:", "auto-reply:", "out of office:", "out of the office:"))
        or any(
            ooo_p in low
            for ooo_p in (
                "out of the office",
                "out of office",
                "currently away from",
                "limited access to email",
                "on vacation until",
                "on parental leave",
                "on medical leave",
                "away from my desk",
                "auto-reply",
                "automatic reply",
                "automated response",
                "this is an automated",
                "do not reply to this",
                "we have received your e-mail",
                "we have received your email",
                "our typical response time",
            )
        )
    ):
        return {"intent": "OUT_OF_OFFICE", "reply_body": ""}'''

new_st_unsub = '''    if not negated_unsub and any(
        p in low
        for p in (
            "unsubscribe", "remove me", "remove us", "remove this", "take me off", "take us off",
            "stop emailing", "stop sending", "stop contacting", "do not contact", "don't contact",
            "dont contact", "never email", "not interested", "no thanks", "off your list",
            "wrong person", "wrong email", "retired", "no longer with", "left the company",
            "doesn't work here", "does not work here", "opt out", "opt-out",
            "who gave you", "why are you emailing",
        )
    ):
        return {"intent": "UNSUBSCRIBE", "reply_body": ""}

    subj_low = str(subject or "").lower()
    if (
        subj_low.startswith(("automatic reply:", "auto-reply:", "out of office:", "out of the office:", "anti-spam", "email verification"))
        or any(
            ooo_p in low
            for ooo_p in (
                "out of the office",
                "out of office",
                "currently away from",
                "limited access to email",
                "on vacation until",
                "on parental leave",
                "on medical leave",
                "away from my desk",
                "auto-reply",
                "automatic reply",
                "automated response",
                "this is an automated",
                "do not reply to this",
                "we have received your e-mail",
                "we have received your email",
                "our typical response time",
                "barracuda",
                "mimecast",
                "proofpoint",
                "boxbe",
                "verify your email",
                "challenge-response",
                "unattended mailbox",
                "no longer monitored",
            )
        )
    ):
        return {"intent": "OUT_OF_OFFICE", "reply_body": ""}'''

assert old_st_unsub in st_src, "old_st_unsub not found"
st_src = st_src.replace(old_st_unsub, new_st_unsub, 1)
st_path.write_text(st_src, encoding="utf-8")
py_compile.compile(str(st_path), doraise=True)
print("[OK] Patched d:\\Daas\\outbound_reply_responder.py")

