from pathlib import Path
import py_compile

for repo_dir in [Path(r"D:\CamberDesk"), Path(r"D:\RubricWard")]:
    for fname in ["sync_instantly_campaign.py", "autonomous_outbound_optimizer.py"]:
        p = repo_dir / fname
        if not p.exists():
            continue
        src = p.read_text(encoding="utf-8")
        src = src.replace('"limit": 100', '"limit": 50')
        src = src.replace('len(items) < 100', 'len(items) < 50')
        src = src.replace('for _ in range(15):', 'for _ in range(25):')
        src = src.replace('    except Exception as e:\n        import traceback; traceback.print_exc()', '    except Exception:\n        pass')
        p.write_text(src, encoding="utf-8")
        py_compile.compile(str(p), doraise=True)
        print(f"[OK] Updated pagination limit=50 in {p}")

