import py_compile
from pathlib import Path

st_healer = Path(r"d:\Daas\auto_error_healer.py")
src = st_healer.read_text(encoding="utf-8")

ST_SEMANTIC_FUNC = '''

def check_and_heal_client_semantic_quality() -> list[str]:
    """
    RULE-021: Autonomous Client-Facing Semantic Quality & End-to-End Fulfillment Self-Healer for SignalTender.
    Verifies:
    1. Zero robotic role greetings ('Hi Capture,', 'Hi Team,') or unreplaced '{{' braces in campaign_leads.csv.
    2. Every Top Contract Dossier URL in campaign_leads.csv resolves to an existing static HTML file in d:\\Daas\\contracts\\rfp\\*.html.
    3. Reply classifier in outbound_reply_responder.py handles hostile '?' unsubscribes and spam-filter challenge auto-replies without spending AI tokens.
    """
    import csv
    issues: list[str] = []
    try:
        import outbound_reply_responder as orr
        res_unsub = orr.classify_and_draft_reply("test@example.com", "Re: Open RFPs", "Why are you emailing me? Remove us from your list.")
        if res_unsub.get("intent") != "UNSUBSCRIBE":
            issues.append("outbound_reply_responder.py failed hostile '?' UNSUBSCRIBE classification test (RULE-021)")
        res_ooo = orr.classify_and_draft_reply("test@example.com", "Email Verification", "Barracuda Spam Firewall: please verify your email")
        if res_ooo.get("intent") != "OUT_OF_OFFICE":
            issues.append("outbound_reply_responder.py failed spam-challenge OUT_OF_OFFICE classification test (RULE-021)")
    except Exception as exc:
        issues.append(f"outbound_reply_responder.py semantic check error: {exc}")

    csv_path = os.path.join(WORKSPACE_DIR, "campaign_leads.csv")
    need_regen = False
    if os.path.exists(csv_path):
        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as cf:
                rows = list(csv.DictReader(cf))
            for r in rows:
                eb = str(r.get("Email Body") or "")
                fb = str(r.get("Followup Body") or "")
                d_url = str(r.get("Top Contract Dossier URL") or "").strip()
                if "{{" in eb or "}}" in eb or "{{" in fb or "}}" in fb:
                    need_regen = True
                if any(bg in eb for bg in ("Hi Capture,", "Hi Team,", "Hi Contracts,")):
                    need_regen = True
                if "/contracts/rfp/" in d_url:
                    rel_p = d_url.split("signaltender.net/", 1)[-1].split("?", 1)[0].split("#", 1)[0]
                    if not os.path.exists(os.path.join(WORKSPACE_DIR, rel_p)):
                        need_regen = True
        except Exception as exc:
            issues.append(f"campaign_leads.csv semantic audit error: {exc}")

    if need_regen:
        try:
            import pseo_generator
            import outreach_generator
            pseo_generator.generate_pseo_site()
            outreach_generator.generate_outreach_campaigns()
            print("  [AUTO-HEALED] Regenerated SignalTender pSEO dossiers & outreach campaigns (RULE-021)", flush=True)
        except Exception as exc:
            issues.append(f"SignalTender semantic auto-heal failed: {exc}")

    return issues
'''

if "def check_and_heal_client_semantic_quality(" not in src:
    target = "def run_healer("
    assert target in src
    src = src.replace(target, ST_SEMANTIC_FUNC + "\n\n" + target, 1)
    src = src.replace(
        "    contract_issues = verify_scraper_contracts_and_rls_safety()",
        "    contract_issues = verify_scraper_contracts_and_rls_safety()\n    contract_issues.extend(check_and_heal_client_semantic_quality())",
        1
    )
    st_healer.write_text(src, encoding="utf-8")
    py_compile.compile(str(st_healer), doraise=True)
    print("[OK] Wired check_and_heal_client_semantic_quality into d:\\Daas\\auto_error_healer.py")

