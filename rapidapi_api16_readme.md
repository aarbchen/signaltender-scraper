# GovCon IGCE, Wrap-Rate & Price-to-Win Modeler API (`POST /v1/generate/price-to-win`)

Transform raw **RFP Section B CLIN structures**, **PWS/SOW level-of-effort & LCAT staffing requirements**, and optional **incumbent / GSA CALC+ historical benchmarks** into a complete, audit-ready **Independent Government Cost Estimate (IGCE)**, **Compounded Indirect Wrap-Rate Breakdown (Fringe / Overhead / G&A / Fee)**, **Bottom-Up GSA CALC+ LCAT Rate Card**, **Multi-Year Section B CLIN Schedule**, **4-Scenario Price-to-Win (PTW) Sensitivity Matrix**, and **Shipley Volume IV Basis of Estimate (BOE) Narrative**.

---

## Key Capabilities & Returned JSON Structure

1. **Independent Government Cost Estimate (IGCE) & Recommended Price-to-Win (`recommended_price_to_win_usd`, `independent_government_cost_estimate_igce_usd`, `ptw_discount_vs_igce_pct`):**
   - Calculates total evaluated price across Base + Option Years and quantifies the target discount vs. the Government IGCE baseline.
2. **FAR 15.404-1 Price Reasonableness & Cost Realism Audit (`cost_realism_and_price_reasonableness_posture`):**
   - Flags whether proposed rates sit in the `OPTIMAL_COMPETITIVE_BAND` or risk an upward Most Probable Cost (MPC) adjustment / technical unacceptability under `FAR 15.404-1(d)`.
3. **Compounded Indirect Wrap-Rate Calculator (`wrap_rate_calculator_breakdown`):**
   - Computes `fringe_rate_pct`, `overhead_rate_pct`, `general_and_administrative_ga_pct`, `target_fee_or_profit_pct`, `compounded_wrap_multiplier_without_fee`, `fully_burdened_wrap_multiplier_with_fee`, productive annual hours (`1,880` / `1,920` hrs/FTE), and Option Year escalation.
4. **Bottom-Up LCAT Rate Card & GSA CALC+ Crosswalk (`lcat_rate_card_and_fte_buildup`):**
   - Maps every solicitation labor category to a comparable **GSA MAS SIN 54151S / CALC+** category, unburdened direct wage, fully burdened bill rate, GSA CALC+ market median rate, and extended Base Year cost.
5. **Multi-Year Section B CLIN Schedule & 4-Scenario PTW Matrix (`clin_period_of_performance_schedule`, `ptw_sensitivity_scenarios`):**
   - Models `AGGRESSIVE_LPTA_FLOOR`, `RECOMMENDED_TARGET_PTW`, `INCUMBENT_DEFENSIVE_BENCHMARK`, and `IGCE_CEILING_ESTIMATE` with Pwin % impact and SSEB tradeoff assessments.
6. **Ready-to-Paste Shipley Volume IV BOE Narrative (`section_b_cost_narrative_and_boe_summary`):**
   - Generates an evaluator-ready Volume IV Price/Cost Narrative and Basis of Estimate (BOE).
