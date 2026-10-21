# GovCon Oral Presentation, Tech-Demo & Murder-Board Prep API (`POST /v1/generate/oral-presentation-prep`)

Transform raw **RFP Section L/M oral presentation instructions**, **PWS/SOW technical scope**, and **Key Personnel profiles** into a complete, evaluator-ready **Shipley Phase II Oral Presentation Deck Blueprint**, **Live Technical Demonstration Runbook (with Offline Failover Contingencies)**, and **Adversarial SSEB "Murder-Board" Q&A Prep Bank**.

---

## Key Capabilities & Returned JSON Structure

1. **Minute-by-Minute Session Budget & Speaker Choreography (`recommended_time_budget_breakdown`, `key_personnel_speaker_choreography`):**
   - Enforces **FAR 15.102** and **GSA FEDSIM** oral presentation rules where only proposed Key Personnel speak (zero BD/sales fluff), with explicit handoff choreography across the Program Manager, Principal Architect, and Lead Engineers.
2. **Slide-by-Slide Shipley Oral Presentation Deck Blueprint (`slide_deck_blueprint`):**
   - Outputs `slide_number`, `slide_title_and_action_caption`, `assigned_key_personnel_speaker`, `time_allocation_minutes`, `mapped_section_m_factor`, `visual_graphic_concept`, and `verbatim_speaker_script_and_proof_points`.
3. **Live Technical Demonstration & Coding Challenge Runbook (`live_tech_demo_runbook`):**
   - Details chronological operator actions, SSEB Strength callouts, and an `offline_failover_contingency` if conference-room Wi-Fi or VPN drops during the live demo.
4. **Adversarial SSEB "Murder-Board" Q&A Bank (`murder_board_qna_bank`):**
   - Generates high-pressure evaluator questions across `TECHNICAL_ARCHITECTURE_RISK`, `TRANSITION_IN_AND_DAY_1_READINESS`, `KEY_PERSONNEL_RETENTION_AND_STAFFING`, `CYBERSECURITY_CMMC_ATO_COMPLIANCE`, and `COST_REALISM_AND_SCOPE_CREEP`, complete with `hidden_evaluator_concern`, `recommended_responder_role`, `gold_standard_answer_script`, and `trap_to_avoid`.
5. **60-Second Evaluator Leave-Behind Pitch (`closing_evaluator_leave_behind_pitch`):**
   - Anchors **High Confidence / Multiple Significant Strengths** immediately before the SSEB caucuses.
