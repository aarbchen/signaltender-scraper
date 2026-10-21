# GovCon GSA MAS Schedule, SIN Mapper & PRC Compliance API

Automate **GSA Multiple Award Schedule (MAS) Large Category F (Information Technology)** eOffer and eMod preparation. Transform raw Commercial Price Lists (CPL), Labor Category (LCAT) descriptions, SaaS/Cloud SKUs, commercial discounting rules, and project histories into a structured JSON package containing:

1. **Special Item Number (SIN) Mapping Matrix (`54151S`, `54151HACS`, `518210C`, `511210`, `54151ECOM`, `OLM`):**
   - Maps your commercial LCATs and products to the exact GSA MAS IT & Cybersecurity SINs, flags Cooperative Purchasing (`COOP`) and Disaster Recovery eligibility, and drafts **SCP-FSS-001 Factor 4 Relevant Project Experience** narratives.
2. **GSA Price Proposal Template (PPT) Ceiling Rate Card with `0.75%` Industrial Funding Fee (`IFF`):**
   - Computes exact **GSA Net Rates** and **GSA Ceiling Rates inclusive of the 0.75% IFF (`Net_Rate / 0.9925`)**, paired with a 5-year **GSAR 552.238-118 Economic Price Adjustment (EPA)** escalation schedule (Year 1 through Year 5).
3. **Most Favored Customer (`MFC`) & Price Reductions Clause (`GSAR 552.238-81`) Safe-Harbor Guardrails:**
   - Compares **Transactional Data Reporting (`TDR` — GSAR 552.238-81 Alt I)** vs. **Commercial Sales Practices (`CSP-1`)**, defines your Basis of Award (`BOA`) customer class, and flags commercial discounting triggers that would cause a retroactive GSA price reduction.
4. **Paste-Ready `SCP-FSS-001` Proposal Narrative:**
   - Generates Administrative, Technical (`Factor 1 Corporate Experience`, `Factor 2 Past Performance`, `Factor 3 Quality Control`, `Factor 4 Relevant SIN Experience`), and Price Proposal narratives ready for GSA **eOffer / eMod**.

---

## Endpoint
`POST /v1/generate/gsa-mas-offer`

### Request Body (`application/json`)
| Field | Type | Required | Description |
|---|---|---|---|
| `commercial_catalog_and_lcat_rates` | `string` | Yes | Commercial Price List (CPL), LCAT titles/rates, minimum education/years of experience, software/SaaS SKUs, and standard commercial discounting practices (`20`–`45,000` chars). |
| `corporate_experience_and_project_context` | `string` | Yes | Past project experience (`1–2` completed projects per target SIN), target GSA IT/Cyber SINs (`54151S`, `54151HACS`, `518210C`), and commercial customer classes (`20`–`35,000` chars). |
| `pricing_disclosure_pathway` | `string` | No | `"Auto_Recommend"` (default), `"TDR_Transactional_Data_Reporting"`, or `"CSP-1_Traditional_PRC"`. |
| `submission_type` | `string` | No | `"New_GSA_MAS_Offer"` (default) or `"Add_SIN_or_EPA_Price_Mod"`. |
