# CPARS & Past Performance Volume Generator API (`POST /v1/generate/past-performance`)

Transform unstructured project histories, prior contract summaries, and CPARS evaluation excerpts into evaluator-ready **Shipley Section L/M Past Performance Volume III citations** with **DoD Source Selection Relevance ratings (`VERY_RELEVANT` / `RELEVANT`)**, **Scope / Magnitude / Complexity cross-walk matrices**, **FAR 42.1503 5-Factor CPARS justifications**, and **Context-Challenge-Action-Result narratives** in a single stateless REST call.

---

## Why Proposal Teams, Capture Managers & GovCon SaaS Platforms Use This API

In Federal (FAR 15.305) and DoD Source Selection trade-off procurements, **Volume III: Past Performance** is frequently weighted equal to—or higher than—Technical Approach. Yet proposal teams waste 25–40 hours per pursuit manually rewriting messy project notes, CPARS PDFs, and subcontractor write-ups to fit strict Section L page limits and Section M evaluation matrices.

The **CPARS & Past Performance Volume Generator API** automates Volume III authoring and SSEB (Source Selection Evaluation Board) risk auditing:

1. **DoD Source Selection Table 4 & Table 5 Scoring:** Predicts both the overall portfolio **Performance Confidence Assessment** (`SUBSTANTIAL_CONFIDENCE`, `SATISFACTORY_CONFIDENCE`, `NEUTRAL_CONFIDENCE`, `LIMITED_CONFIDENCE`) and each individual contract's **Relevance Rating** (`VERY_RELEVANT`, `RELEVANT`, `SOMEWHAT_RELEVANT`, `NOT_RELEVANT`).
2. **Recency, Dollar Magnitude & Prime/Sub Gate Audit:** Verifies whether your submitted citations meet Section L recency windows (e.g., within 3–5 years), annual/total contract value floors, and Prime vs. Major Subcontractor citation ratios.
3. **Three-Pillar Scope, Magnitude & Complexity Cross-Walk:** Maps every prior contract directly to the target RFP's PWS/SOW sections across **Scope** (technical tasks), **Magnitude** (dollar ceiling, burn rate, FTEs, user scale), and **Complexity** (DoD IL4/IL5/IL6, FedRAMP High, CMMC 2.0, Top Secret clearances).
4. **FAR 42.1503 5-Factor CPARS Alignment:** Structures ratings and quantified proof points across all five statutory CPARS evaluation areas: *Quality of Product/Service*, *Schedule/Timeliness*, *Cost Control*, *Business Relations & Management*, and *Small Business Subcontracting*.
5. **Shipley Context -> Challenge -> Action -> Result Narratives:** Generates ready-to-paste, multi-paragraph Shipley Past Performance citations plus FAR 15.305(a)(2) relevance gap mitigations and a PPQ / COR reference interview prep checklist.

---

## Endpoint Reference

### `POST /v1/generate/past-performance`
* **Operation ID:** `Generate CPARS & Past Performance Volume Citations`
* **RapidAPI Host:** `cpars-past-performance-volume-generator-api.p.rapidapi.com`
* **Content-Type:** `application/json`

### Request Body (`PastPerformanceGeneratorRequest`)

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `rfp_section_l_m_requirements` | `string` | **Yes** | Raw text from target RFP Section L (Volume III instructions, recency/dollar/scope thresholds, Prime/Sub rules, page limits), Section M (evaluation criteria), and Section C/PWS technical scope. *(Aliases supported: `rfp_text`, `solicitation_requirements`, `raw_text`)* |
| `project_history_text` | `string` | **Yes** | Unstructured project descriptions, prior contract summaries, CPARS evaluation excerpts, Subcontractor experience, or internal delivery notes. *(Aliases supported: `past_performance_text`, `contract_history_text`, `cpars_text`)* |
| `bidder_role_and_context` | `string` | No | Optional context such as Prime vs. Subcontractor citation mix, Joint Venture / Mentor-Protege structure, or Volume III page-limit constraints. |

---

## Code Examples

### cURL
```bash
curl -X POST "https://cpars-past-performance-volume-generator-api.p.rapidapi.com/v1/generate/past-performance" \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: YOUR_RAPIDAPI_KEY" \
  -H "X-RapidAPI-Host: cpars-past-performance-volume-generator-api.p.rapidapi.com" \
  -d '{
    "rfp_section_l_m_requirements": "SOLICITATION FA8726-26-R-0054: Section L.5 Volume III Past Performance requires up to 3 recent (within 5 years) citations >= $4M/yr ($12M Total Value), with at least 2 as Prime Contractor. Section M.3 evaluates Scope, Magnitude, and Complexity across PWS 3.1 AWS GovCloud IL5 Migration, PWS 3.2 Zero-Trust ICAM, and PWS 3.3 24x7x365 Cleared SOC & Splunk SIEM.",
    "project_history_text": "Contract 1 (Prime): U.S. Space Force SSC Enterprise Cloud Enclave (FA8802-22-C-0019, FFP/T&M, $18.4M Total, $6.1M/yr, 2022-2025, 34 FTEs, NAICS 541512). Migrated 42 mission apps to AWS GovCloud IL5, deployed Zero-Trust ICAM for 14,500 users, and ran 24x7 TS/SCI Splunk SOC. CPARS: Exceptional across all 5 factors (99.98% SLA, $420K FinOps savings). Contract 2 (Prime): DISA Defense Enclave Cyber Modernization (HC1028-23-F-0112, T&M, $13.2M Total, $4.4M/yr, 2023-Present, 26 FTEs). Automated STIG hardening, Zero-Trust microsegmentation, and cATO pipelines across 8,000 endpoints.",
    "bidder_role_and_context": "Prime Offeror submitting 2 DoD Prime contracts + 1 Major Subcontractor contract; Volume III page limit is 15 pages."
  }'
```

### Python (`requests`)
```python
import requests

url = "https://cpars-past-performance-volume-generator-api.p.rapidapi.com/v1/generate/past-performance"
headers = {
    "Content-Type": "application/json",
    "X-RapidAPI-Key": "YOUR_RAPIDAPI_KEY",
    "X-RapidAPI-Host": "cpars-past-performance-volume-generator-api.p.rapidapi.com",
}
payload = {
    "rfp_section_l_m_requirements": (
        "SOLICITATION FA8726-26-R-0054 (USAF Enterprise Cloud & Zero-Trust SOC Modernization): "
        "Section L.5 requires up to 3 citations within 5 years >= $12M TCV (at least 2 as Prime). "
        "Section M.3 evaluates Scope, Magnitude, and Complexity across PWS 3.1 AWS GovCloud IL5 Migration, "
        "PWS 3.2 Zero-Trust ICAM, and PWS 3.3 24x7 Cleared Splunk SOC."
    ),
    "project_history_text": (
        "Contract 1 (Prime): U.S. Space Force SSC Cloud Enclave (FA8802-22-C-0019, $18.4M TCV, 2022-2025, 34 FTEs). "
        "Migrated 42 apps to AWS GovCloud IL5, Zero-Trust ICAM for 14,500 users, 24x7 Splunk SOC. CPARS: Exceptional."
    ),
    "bidder_role_and_context": "Prime Offeror (SDVOSB) with 15-page Volume III limit",
}

response = requests.post(url, json=payload, headers=headers, timeout=90)
print(response.json())
```

---

## Sample JSON Response (`PastPerformanceGeneratorResponse`)

```json
{
  "volume_summary": {
    "target_solicitation_id": "FA8726-26-R-0054 (USAF Enterprise Cloud & Zero-Trust SOC Modernization)",
    "overall_confidence_prediction": "SUBSTANTIAL_CONFIDENCE",
    "portfolio_relevance_score": 95,
    "recency_and_magnitude_compliance_summary": "COMPLIANT: Both Prime citations (FA8802-22-C-0019 at $18.4M TCV / $6.1M/yr and HC1028-23-F-0112 at $13.2M TCV / $4.4M/yr) are active/completed within the 5-year recency window, exceed the $12M TCV / $4M annual floor, and satisfy the 2-Prime minimum rule.",
    "volume_executive_introduction": "Team Sentinel presents a low-risk, mission-proven Past Performance portfolio demonstrating Substantial Confidence across all PWS 3.1–3.3 task areas..."
  },
  "past_performance_citations": [
    {
      "citation_id": "PP-CITATION-01",
      "contract_title_and_number": "FA8802-22-C-0019 — U.S. Space Force SSC Enterprise Cloud Enclave",
      "customer_agency_and_role": "U.S. Space Force Space Systems Command (SSC) — Prime Contractor (100% Responsibility)",
      "contract_metadata_block": "Contract Type: FFP/T&M Hybrid | Total Value: $18,400,000 ($6.1M/yr) | PoP: 04/2022 – 03/2025 | Staffing: 34 Cleared FTEs | NAICS: 541512",
      "predicted_relevance_rating": "VERY_RELEVANT",
      "relevance_score": 97,
      "mapped_rfp_pws_sections": [
        "PWS 3.1 AWS GovCloud IL5 Migration",
        "PWS 3.2 Zero-Trust ICAM & Microsegmentation",
        "PWS 3.3 24x7x365 Cleared SOC & Splunk SIEM Operations"
      ],
      "scope_magnitude_complexity": {
        "scope_alignment_analysis": "100% alignment with PWS 3.1–3.3: migrated 42 mission applications to AWS GovCloud IL5, implemented enterprise Okta/ICAM, and operated a 24x7 Splunk ES SOC.",
        "magnitude_and_fte_comparison": "Exceeds Section L thresholds by 53% ($18.4M TCV vs. $12.0M minimum; $6.1M/yr vs. $4.0M/yr floor; 34 FTEs supporting 14,500 users).",
        "complexity_and_environment_match": "Identical DoD IL5 / Top Secret operational environment with strict RMF Continuous ATO and STIG compliance mandates."
      },
      "cpars_factor_alignment": {
        "quality_of_product_or_service": "EXCEPTIONAL",
        "schedule_timeliness": "EXCEPTIONAL",
        "cost_control": "EXCEPTIONAL",
        "business_relations_and_management": "EXCEPTIONAL",
        "small_business_subcontracting": "EXCEPTIONAL",
        "cpars_justification_narrative": "Earned 'Exceptional' across all 5 FAR 42.1503 CPARS factors for 3 consecutive assessment periods, achieving 99.98% enclave availability and $420,000 in verified cloud FinOps savings."
      },
      "shipley_context_challenge_action_result_narrative": "CONTEXT: Under Contract FA8802-22-C-0019, our team served as Prime Contractor for U.S. Space Force SSC..."
    }
  ],
  "relevance_gaps_and_mitigations": [
    {
      "gap_id": "PP-GAP-01",
      "rfp_requirement_or_pws_area": "Subcontractor High-Volume SOAR Telemetry Scaling",
      "identified_gap_description": "Citation 3 was performed as a Major Subcontractor (40% workshare) rather than Prime.",
      "mitigation_and_teaming_strategy": "Under FAR 15.305(a)(2)(iii), explicitly bind the Major Subcontractor via a bilateral Teaming Agreement assigning 100% of PWS 3.3 SOAR playbook engineering to the same personnel."
    }
  ],
  "ppq_and_cor_interview_prep_checklist": [
    "Verify COR contact email and phone numbers on file in CPARS/SAM prior to Section L submission.",
    "Send pre-filled Past Performance Questionnaire (PPQ) Attachment L-3 header blocks to all 3 CORs 10 business days before proposal due date."
  ]
}
```

---

## Model Context Protocol (MCP) Integration

This endpoint is natively registered in the SignalTender MCP Server (`@signaltender/mcp-server` on NPM and `https://b2b-contract-parser-api.onrender.com/mcp`) as the **`generate_cpars_past_performance`** tool for Claude Desktop, Cursor, Windsurf, and autonomous GovCon capture agents.
