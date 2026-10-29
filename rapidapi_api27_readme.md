# GovCon 30/60/90-Day Phase-In / Phase-Out Transition & Incumbent Capture API

Generates a risk-mitigated **30/60/90-Day Phase-In and Phase-Out Transition Plan** from solicitation Section C/L/M transition instructions and incumbent workforce context. It returns a **0–100 Transition Risk Readiness Score**, chronological **Work Breakdown Structure (WBS) milestones**, an **Executive Order 14055 / Service Contract Act (SCA) Incumbent Workforce Capture & Right-of-First-Refusal retention plan**, **DD-254 / DISS security clearance crossover timelines**, **Knowledge Transfer & Shadowing schedules with COR Operational Readiness Review (ORR) gates**, a **FAR 52.237-3 Continuity of Services Phase-Out checklist**, and a **ready-to-submit Shipley Transition Plan proposal volume**.

## Key Capabilities
- **Chronological 30/60/90-Day WBS Transition Milestones:** Structures `WBS 1.1` (Days 1–30 Mobilization, Kickoff & Incumbent Capture), `WBS 1.2` (Days 31–60 Parallel Shadowing, Knowledge Transfer & Enclave Cutover), `WBS 1.3` (Days 61–90 ORR & Full Operational Capability), and `WBS 1.4` (FAR 52.237-3 Phase-Out) with deliverables, Go/No-Go exit criteria, responsible leads, and operational risk mitigations.
- **EO 14055, SCA & CBA Incumbent Workforce Capture Plan:** Details target incumbent retention percentages (85%–95%+), Executive Order 14055 / FAR 52.222-17 qualified worker right-of-first-refusal compliance, Service Contract Act (SCA) Wage Determination & Collective Bargaining Agreement (CBA) seniority/fringe bridges, and a ready-to-use Town Hall / 1-on-1 Incumbent Capture Outreach Script.
- **DD-254 & DISS Security Clearance Crossover Timeline:** Maps 24-to-72-hour Defense Information System for Security (DISS) / NBIS Cage-to-Cage sponsorship transfers, DD Form 254 subcontractor flow-downs, CAC/PIV badging, and Privileged Access Agreements (PAAs).
- **Knowledge Transfer & COR Operational Readiness Review (ORR) Gates:** Defines functional shadowing tracks, SOP/runbook/GFE handover items, and measurable COR sign-off gates before assuming autonomous operations.
- **FAR 52.237-3 Continuity of Services Checklist & Shipley Narrative:** Produces a complete Phase-Out continuity checklist and paste-ready Shipley Transition Plan volume narrative.

## Endpoint
`POST /v1/generate/phase-in-transition-plan`

### Example Request
```json
{
  "solicitation_transition_and_sow_text": "Section L.4.3 & PWS C.2 Phase-In / Phase-Out Transition (60-Day Phase-In / 90-Day FOC): Execute a zero-mission-disruption transition for a 38-FTE Enterprise Cloud, Zero-Trust ICAM, and 24x7 Tier-2/3 Service Desk operation supporting Tennessee STS and DoD mission partners.",
  "incumbent_workforce_and_clearance_context": "Incumbent prime currently staffs 38 FTEs (28 Secret cleared, 10 Top Secret/SCI cleared under DD Form 254; 14 SCA technicians subject to EO 14055 right-of-first-refusal). Target incumbent capture rate is >= 90%.",
  "transition_timeline_window": "Standard_30_60_90_Day_Phase_In"
}
```

### Response Highlights
`status`, `transition_risk_readiness_score`, `executive_transition_summary`, `wbs_30_60_90_day_milestones[]`, `incumbent_capture_and_retention_plan`, `knowledge_transfer_and_shadowing_schedule[]`, `far_52_237_3_phase_out_continuity_checklist[]`, `ready_to_submit_transition_volume`.
