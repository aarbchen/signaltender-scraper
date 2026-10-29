# FAR 52.227-14 & DFARS 252.227-7013/7014 IP & Technical Data Rights API

Audits software components, AI/ML models and weights, firmware, technical data packages, and CDRL deliverables by development funding history (**100% private expense, SBIR/STTR, mixed funding, or government-funded**) to generate a compliant **4-column DFARS 252.227-7017 Data Rights Assertion Table**, verbatim **DFARS 252.227-7013/7014/7018 & FAR 52.227-14 restrictive marking legends**, and a **10 U.S.C. 4401 Modular Open Systems Approach (MOSA)** boundary protection plan.

## Key Capabilities
- **Doctrine of Segregability & DFARS 252.227-7017 Assertion Table:** Segregates software modules, neural weights, firmware, and technical data at the lowest practicable component level across `Restricted Rights`, `Limited Rights`, `Government Purpose Rights (GPR)`, `SBIR/STTR Data Rights (20-Year Protection)`, and `Commercial Computer Software License Rights`.
- **Verbatim Restrictive Marking Legends:** Generates word-for-word DFARS 252.227-7013(f), 252.227-7014(f), 252.227-7018(f), and FAR 52.227-14 Alt II/III restrictive legends with source-code header, container metadata, and CDRL cover-page placement rules.
- **10 U.S.C. 4401 MOSA Boundary & Black-Box Encapsulation Plan:** Separates open API / Form-Fit-Function (FFF) / OMIT deliverables (furnished with Unlimited/GPR rights) from compiled proprietary core algorithms so background source code is never surrendered.
- **DFARS 252.227-7027 Deferred Ordering & 7037 Audit Defense:** Establishes IR&D General Ledger charge-code segregation and pre-award Git commit timestamp trails to survive post-award Contracting Officer validation challenges.

## Endpoint
`POST /v1/generate/data-rights-assertion-table`

### Example Request
```json
{
  "software_modules_and_cdrl_deliverables_text": "1. SentinelCore Zero-Trust Inference Engine & Pre-Trained Weights v4.2: Developed 100% at private expense (2022-2025 IR&D GL Account #8410) prior to solicitation; delivered as compiled container image under CDRL A004. 2. Tactical RF Sensor Ingestion Firmware: Developed under DoD SBIR Phase II Contract FA8650-24-C-1102; delivered under CDRL A005. 3. Mission Adapter Microservice & REST/gRPC Interface Control Document (ICD): Developed with mixed/contract funding under CLIN 0002; delivered under CDRL A002 (ICD) and CDRL A006 (Adapter Source).",
  "governing_acquisition_regime": "DoD_DFARS_252_227_7013_7014_7015_7017_And_7018",
  "modular_open_systems_approach_mosa_context": "MOSA_Open_API_Boundary_Preserving_Proprietary_Core_Algorithms"
}
```

### Response Highlights
`status`, `ip_strategy_executive_overview`, `dfars_252_227_7017_assertion_table[]`, `restrictive_marking_and_legend_templates[]`, `mosa_and_deferred_ordering_protection_plan`, `pre_award_ip_negotiation_checklist[]`.
