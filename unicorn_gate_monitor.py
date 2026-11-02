r"""
SignalTender — Autonomous $1M -> $1B+ Unicorn Stage-Gate Transition Monitor (`unicorn_gate_monitor.py`).
Evaluates live recurring revenue & treasury ledger milestones every watcher cycle and automatically
shifts SignalTender from Gate 0 ($1M ARR Master Plan) -> Gate 1 ($10M ARR) -> Gate 2 ($35M ARR) -> Gate 3 ($1B+ Unicorn).
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parent
LEDGER_PATH = ROOT_DIR / "reinvestment_treasury_ledger.json"
STATE_PATH = ROOT_DIR / "unicorn_stage_gate_state.json"


def evaluate_and_advance_unicorn_gate() -> Dict[str, Any]:
    gross_rev = 0.0
    tx_count = 0
    if LEDGER_PATH.exists():
        try:
            ldata = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
            gross_rev = float(ldata.get("cumulative_gross_revenue_usd") or ldata.get("total_gross_revenue_usd") or 0.0)
            tx_count = len(ldata.get("transactions") or ldata.get("events") or [])
        except Exception:
            pass

    if gross_rev >= 2916666.0:
        active_gate = "GATE_3_UNICORN_1B_FINTECH_ESCROW"
        unlocked_pillar = "13 CFR 125.6 Subcontract Split-Escrow & GovCon Receivable Factoring Rail (1.75% Take-Rate)"
    elif gross_rev >= 833333.0:
        active_gate = "GATE_2_SOVEREIGN_ENCLAVE_AND_POST_AWARD_CLM"
        unlocked_pillar = "AWS GovCloud / DoD IL5 Sovereign Enclave OEM + PIEE/WAWF Post-Award CLM"
    elif gross_rev >= 85000.0:
        active_gate = "GATE_1_MULTI_VERTICAL_10M_ARR_EXPANSION"
        unlocked_pillar = "5-Vertical NAICS Router (IT, Defense/SBIR, AEC, GovHealth, Logistics) + 6 Municipal/Grant Aggregators (Bonfire, OpenGov, PlanetBids, IonWave, BidNet, Grants.gov)"
    else:
        active_gate = "GATE_0_1M_ARR_52_PORTAL_AUTOPILOT_SCALE"
        unlocked_pillar = "52-Portal Core Engine + 50% Revenue-to-Mailbox Autonomous Scaling"

    state = {
        "brand": "SignalTender",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "active_gate": active_gate,
        "unlocked_pillar": unlocked_pillar,
        "cumulative_gross_revenue_usd": round(gross_rev, 2),
        "recorded_conversions": tx_count,
        "gate_thresholds_mrr_usd": {
            "gate_1_10m_arr_trigger": 85000.0,
            "gate_2_35m_arr_trigger": 833333.0,
            "gate_3_1b_unicorn_trigger": 2916666.0,
        },
        "blueprint_doc": "UNICORN_1B_EXPANSION_BLUEPRINT.md",
    }
    try:
        STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass
    return state


if __name__ == "__main__":
    print(json.dumps(evaluate_and_advance_unicorn_gate(), indent=2))
