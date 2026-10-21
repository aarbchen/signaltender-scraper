# GovCon Post-Award Debriefing, FAR 15.506 Q&A & GAO Bid-Protest Analyzer API

Transform **Agency Unsuccessful Offeror Notices**, **FAR 15.506 / DFARS 215.506-70 Enhanced Post-Award Debriefing Letters & Slides**, **Source Selection Decision Documents (SSDDs)**, and **RFP Section M Evaluation Criteria** into strategic Contracting Officer debriefing questions, a **GAO / Court of Federal Claims (COFC) Bid-Protest Viability Scorecard (`0–100`)**, **Winning Awardee Intervenor Defense Briefs**, **FASA Task-Order Jurisdictional Checks (`FAR 16.505(a)(10)`)**, and a strict **CICA (`31 U.S.C. § 3553`) Automatic-Stay Deadline Calendar**.

---

## Why Capture Directors, Proposal Teams & GovCon Legal Counsel Use This API

When an agency issues an award notification or competitive-range exclusion, the statutory clock starts ticking immediately:
- **3 Calendar Days (`FAR 15.506(a)(1)`):** Deadline to submit a written request for a required Post-Award Debriefing.
- **2 Business Days (`DFARS 215.506-70`):** Window under DoD Enhanced Post-Award Debriefing procedures to submit written follow-up questions—keeping the debriefing legally open until the agency delivers written answers.
- **5 Calendar Days Post-Debrief (`31 U.S.C. § 3553 / CICA`):** Strict window to file a GAO Bid Protest and trigger the **automatic stay of contract performance**.

Outside GovCon bid-protest counsel typically charges **`$600–$1,100/hour`** (`$15,000+` just for an initial debriefing & protest merits review). This stateless REST API performs an instant, structured FAR Part 15 & GAO case-law audit in seconds.

---

## Key Capabilities & Structured Outputs

1. **`protest_viability_or_defense_score` (`0–100`) & `recommended_executive_decision`:**
   - Quantifies whether the record shows reversible prejudicial error (`HIGH_SUSTAIN_PROBABILITY`) vs. normal agency technical discretion (`DO_NOT_PROTEST_PRESERVE_CUSTOMER_GOODWILL`).
2. **`task_order_jurisdictional_bar_check` (`FAR 16.505(a)(10)` & `FAR 8.405-5`):**
   - Automatically checks Federal Acquisition Streamlining Act (FASA) task-order protest jurisdictional bars (`$35M` DoD IDIQ threshold / `$10M` Civilian IDIQ threshold vs. GSA MAS Schedule `FAR 8.4` orders which remain protestable at GAO regardless of dollar value).
3. **`statutory_deadline_calendar`:**
   - Computes exact FAR 15.505/15.506 debriefing request windows, DoD Enhanced Debriefing 2-business-day question extensions, CICA automatic-stay deadlines, and GAO 10-day outer timeliness rules (`4 CFR § 21.2`).
4. **`far_15_506_debriefing_questions[]`:**
   - Non-adversarial, precision-crafted questions to submit to the Contracting Officer that force the agency to disclose whether it applied unstated evaluation criteria, conducted unequal discussions, or made an undocumented price/technical tradeoff.
5. **`protest_grounds_or_defense_matrix[]`:**
   - Audits the record across core GAO sustain categories:
     - `UNSTATED_EVALUATION_CRITERIA` (`FAR 15.305(a)`)
     - `DISPARATE_UNEQUAL_TREATMENT` (`FAR 15.306(e)`)
     - `FLAWED_BEST_VALUE_TRADEOFF_SSDD` (`FAR 15.308`)
     - `UNREASONABLE_COST_OR_PRICE_REALISM` (`FAR 15.404-1`)
     - `MEANINGFUL_DISCUSSIONS_FAILURE` (`FAR 15.306(d)`)
     - `OCI_CONFLICT_OF_INTEREST` (`FAR Subpart 9.5`)
   - Also supports **`winning_awardee_intervention_defense`** mode for winning primes preparing an Intervenor dismissal/defense brief when a losing competitor files a protest.
6. **`ready_to_send_debrief_request_or_counsel_memo`:**
   - Full, copy-pasteable FAR 15.506 / DFARS 215.506-70 Enhanced Debriefing Request & Written Question submission (or Executive Bid-Protest / Intervenor Strategy Memo).

---

## Endpoint Specification

- **Method:** `POST`
- **Path:** `/v1/generate/debriefing-bid-protest`
- **Content-Type:** `application/json`

### Example Request (`cURL`)

```bash
curl -X POST "https://govcon-post-award-debriefing-far-15-506-q-a-gao-bid-protest-api.p.rapidapi.com/v1/generate/debriefing-bid-protest" \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: YOUR_RAPIDAPI_KEY" \
  -H "X-RapidAPI-Host: govcon-post-award-debriefing-far-15-506-q-a-gao-bid-protest-api.p.rapidapi.com" \
  -d '{
    "award_notice_or_debrief_text": "UNSUCCESSFUL OFFEROR NOTICE & POST-AWARD DEBRIEFING SUMMARY — Solicitation FA8732-26-R-0041 (USAF Cloud & Zero-Trust DevSecOps Modernization): Award made to Incumbent Defense Corp at $28.4M (Technical: Outstanding, Past Performance: Substantial Confidence). Your Proposal (Apex Cyber Federal, $22.9M — $5.5M lower price) received Technical: Acceptable (1 Weakness assigned under Subfactor 1B for not proposing a dedicated brick-and-mortar SCIF lab in Dayton, OH) and Past Performance: Satisfactory Confidence.",
    "rfp_section_m_and_bidder_context": "Section M.2 Evaluation Criteria: Best-Value Tradeoff (Technical Approach > Past Performance > Cost/Price). Section C/L/M never required an on-prem Dayton SCIF lab (PWS 3.1 explicitly stated 100% remote AWS GovCloud IL5 delivery with quarterly TDY travel). Offeror submitted 3 USAF Prime IL5 Cloud DevSecOps contracts rated Exceptional in CPARS.",
    "analysis_mode": "unsuccessful_offeror_debrief_and_protest",
    "procurement_jurisdiction": "dod_dfars_215_506_enhanced"
  }'
```

---

## Model Context Protocol (MCP) & Ecosystem Integration

This API is included in the official **SignalTender MCP Server** (`@signaltender/mcp-server` / `io.github.aarbchen/signaltender-mcp`) as tool `analyze_debriefing_bid_protest` for seamless integration with Claude Desktop, Cursor, Windsurf, and autonomous GovCon capture pipelines.
- **Full Suite & Live Sandbox:** [https://signaltender.net/apis.html](https://signaltender.net/apis.html)

