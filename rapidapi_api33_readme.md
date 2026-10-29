# GovCon Black-Hat Competitive Intelligence, Incumbent Vulnerability & Ghosting API

Conducts a **Shipley Black-Hat Competitive Intelligence Simulation** on a target government solicitation and incumbent contractor—profiling likely competitor bidding strategies and wrap-rate postures, generating **verbatim ethical ghosting statements** mapped to **RFP Section L/M evaluation factors**, neutralizing incumbent transition advantages, and drafting **Contracting Officer Q&A shaping questions**.

## Key Capabilities
- **Black-Hat Executive Assessment:** Estimates incumbent-unseating probability (`0–100%`), identifies the primary win-strategy archetype, and pinpoints the most dangerous competitor threat under Best-Value Tradeoff or LPTA evaluation rules.
- **Simulated Competitor Black-Hat Profiles:** Models the Incumbent Prime Contractor, Large Tier-1 Systems Integrator Challengers, and Low-Price/LPTA Bidders across likely technical solution, wrap-rate/pricing posture, exploitable vulnerabilities, and counter-strategies.
- **Shipley Ethical Ghosting Statements:** Generates paste-ready, non-disparaging proposal prose that frames competitor weaknesses (manual RMF processes, turnover, contingent key personnel, bloated wrap rates, or unrealistic salary slashing) as unacceptable mission risks to the SSEB.
- **Incumbent Recompete Vulnerability Matrix & Red Team Triggers:** Provides a Day-1 transition risk neutralizer (EO 14055 / DISS crossover), technical debt exposure angles, PTW wrap-rate wedges, Contracting Officer Q&A shaping questions, and FAR 15.305 Significant Strength triggers.

## Endpoint
`POST /v1/generate/capture-black-hat-review`

### Example Request
```json
{
  "solicitation_and_incumbent_context_text": "Target Recompete: DoD C5ISR Enterprise Cloud & 24x7 Cyber SOC Operations ($85M 5-Year Single-Award Task Order). Section M Evaluation: Best-Value Tradeoff (Factor 1 Technical Approach [Most Important] > Factor 2 Management & Transition > Factor 3 Past Performance > Price). Incumbent: LegacyDefense Corp (held contract for 5 years; known pain points include 18% annual SOC analyst turnover, delayed RMF cATO pipeline, and high 2.15x Tier-1 wrap rate).",
  "bidder_discriminators_and_proof_points": "Cleared_Automation_First_Team_With_Zero_Trust_cATO_And_Lower_Wrap_Rate",
  "evaluation_type_and_posture": "Challenger_Unseating_Incumbent_Best_Value_Tradeoff"
}
```

### Response Highlights
`status`, `black_hat_executive_assessment`, `competitor_black_hat_profiles[]`, `shipley_ethical_ghosting_statements[]`, `incumbent_recompete_vulnerability_matrix`, `red_team_evaluator_scoring_triggers[]`.
