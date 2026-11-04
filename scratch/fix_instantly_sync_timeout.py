from pathlib import Path
import py_compile

for repo_dir in [Path(r"D:\CamberDesk"), Path(r"D:\RubricWard")]:
    p = repo_dir / "sync_instantly_campaign.py"
    src = p.read_text(encoding="utf-8")
    src = src.replace(
        '            r_existing = requests.post(\n                "https://api.instantly.ai/api/v2/leads/list",\n                headers=headers,\n                json=list_req,\n                timeout=15,\n            )',
        '            r_existing = None\n            for _att in range(3):\n                try:\n                    r_existing = requests.post(\n                        "https://api.instantly.ai/api/v2/leads/list",\n                        headers=headers,\n                        json=list_req,\n                        timeout=35,\n                    )\n                    if r_existing.status_code == 200:\n                        break\n                except Exception:\n                    pass\n            if r_existing is None:\n                break'
    )
    src = src.replace(
        'if lid and (is_bounced_or_bad or is_st_overlap or has_dollar_or_link or (em_existing not in valid_email_map)):',
        'if lid and (is_bounced_or_bad or is_st_overlap or has_dollar_or_link or is_receptionist_or_generic_inbox(em_existing) or (em_existing not in valid_email_map)):'
    )
    src = src.replace('timeout=12,', 'timeout=25,')
    p.write_text(src, encoding="utf-8")
    py_compile.compile(str(p), doraise=True)
    print(f"[OK] Hardened {p}")

