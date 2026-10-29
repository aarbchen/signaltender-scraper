# SBIR / STTR Phase I–III Technical Volume & Commercialization Plan API

**Transform raw R&D specifications, Principal Investigator (PI) innovation notes, and DoD / AFWERX / SpaceWERX / DARPA / NSF / NASA SBIR & STTR topic descriptions into a complete Phase I–III Technical Work Plan, TRL 1–9 Progression Matrix, Dual-Use Commercialization Plan (`15 U.S.C. § 638(r)(4)`), and pre-award `DFARS 252.227-7018` / `FAR 52.227-20` SBIR Data Rights Assertion Schedule in a single stateless REST call.**

Built for **Defense Tech Startups, Deep-Tech Small Businesses, STTR University Spinouts, AFWERX / SpaceWERX Direct-to-Phase II (D2P2) Applicants, and GovCon Capture Teams**.

---

## Why Defense Tech & SBIR/STTR Teams Use This API

1. **Automated TRL 1–9 Progression & WBS Technical Work Plan:** Maps your current laboratory or prototype baseline (`TRL 2–4`) to target operational demonstrations (`TRL 6–8`) with numbered Work Breakdown Structure tasks (`TASK-1.0`, `TASK-2.0`, `TASK-3.0`), scientific methodology, and quantifiable exit criteria.
2. **Pre-Award `DFARS 252.227-7018` & `FAR 52.227-20` SBIR Data Rights Protection:** Automatically separates privately funded background IP (`Developed_Exclusively_at_Private_Expense` -> `Limited_Rights_Technical_Data` / `Restricted_Rights_Computer_Software`) from foreground SBIR-funded deliverables (`Generated_Under_SBIR_STTR_Funding_DFARS_252_227_7018` -> `SBIR_Data_Rights_20_Year_Protection_Period`) so you never accidentally surrender core IP to the government.
3. **Phase III Sole-Source Transition Roadmap (`15 U.S.C. § 638(r)(4)`):** Generates a complete Volume 2 Technical & Dual-Use Commercialization narrative covering Customer Memorandum (MOU) justification, AFWERX TACFI/STRATFI matching strategy, TAM/SAM/SOM commercial revenue projections, and non-competitive Phase III sole-source transition into a Program of Record.
4. **100% Stateless & Zero Data Retention:** Proprietary R&D architectures, patent-pending algorithms, and SBIR drafts are processed in-memory and never stored or used for model training.

---

## Key Endpoint

### `POST /v1/generate/sbir-sttr-commercialization`
* **Operation Name:** `Generate SBIR STTR Commercialization Plan`
* **Input Payload (`application/json`):**
  * `sbir_sttr_topic_and_rd_specs` *(string, required)*: Full or excerpted DoD, AFWERX, SPACEWERX, Navy, Army, DARPA, NSF, NASA, or DHS SBIR/STTR topic instructions, Phase I/II/III technical objectives, and evaluation criteria.
  * `company_technology_and_ip_baseline` *(string, required)*: Summary of the small business offeror's R&D technology, current TRL, Principal Investigator (PI) credentials, prior IRAD/patents, STTR university/lab partner (if applicable), and dual-use commercial traction.
  * `target_phase_and_program` *(string, optional)*: `'Phase_I_Feasibility_and_Proof_of_Concept'`, `'Direct_to_Phase_II_or_Phase_II_Prototype'` (default), `'Phase_IIB_or_STRATFI_TACFI_Matching'`, or `'Phase_III_Sole_Source_Transition_15_USC_638_r_4'`.
  * `sponsoring_agency` *(string, optional)*: Sponsoring agency or directorate (e.g., `'Department of Defense (AFWERX / DoD SBIR)'`, `'National Science Foundation (NSF)'`, `'NASA'`).

---

## Example Request (`cURL`)

```bash
curl --request POST \
  --url https://sbir-sttr-phase-i-iii-commercialization-plan-api.p.rapidapi.com/v1/generate/sbir-sttr-commercialization \
  --header 'Content-Type: application/json' \
  --header 'x-rapidapi-host: sbir-sttr-phase-i-iii-commercialization-plan-api.p.rapidapi.com' \
  --header 'x-rapidapi-key: YOUR_RAPIDAPI_KEY' \
  --data '{
    "sbir_sttr_topic_and_rd_specs": "Solicitation: AF262-D014 (Direct-to-Phase II AFWERX / SpaceWERX Open Topic). Objective: Develop and demonstrate an autonomous edge-AI tactical spectrum sensing and anti-jamming cognitive radio waveform for contested C5ISR environments. Must demonstrate TRL 6 prototype in relevant tactical environment within 15 months, include a signed Phase III Customer Memorandum of Understanding (MOU) pathway with PEO C3BM, and provide a dual-use commercialization strategy alongside a DFARS 252.227-7018 SBIR Data Rights schedule.",
    "company_technology_and_ip_baseline": "AegisWave Photonics & AI Lab (Small Business, 42 employees) has developed a proprietary sub-millisecond neural blind-signal classifier and FPGA cognitive frequency-hopping core tested at TRL 4 in laboratory anechoic trials using $1.8M in private seed venture capital. Commercial dual-use market includes 5G/6G private industrial wireless interference mitigation and low-Earth-orbit (LEO) commercial satcom ground terminals.",
    "target_phase_and_program": "Direct_to_Phase_II_or_Phase_II_Prototype"
  }'
```

---

## Model Context Protocol (MCP) & Agent Integration

This endpoint is also exposed as the `generate_sbir_sttr_commercialization` tool in the official **SignalTender MCP Server** (`npx -y @signaltender/mcp-server` or `https://b2b-contract-parser-api.onrender.com/mcp`) for Claude Desktop, Cursor, Windsurf, and autonomous GovCon R&D agents.
