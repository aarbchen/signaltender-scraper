# GovCon Sources Sought, RFI & Set-Aside Shaping Responder API

Automate **pre-RFP Federal & SLED market research shaping (`FAR Part 10`, `FAR 19.502-2 Rule of Two`, `13 CFR 125.6`)**. Transform raw `SAM.gov` or State SLED **Sources Sought Notices**, **Requests for Information (RFIs)**, draft PWS/SOW excerpts, and your company's capability profile into a structured JSON package containing:

1. **`FAR 19.502-2` Rule-of-Two Set-Aside Viability & `13 CFR 125.6` Subcontracting Compliance:**
   - Evaluates the probability of locking the upcoming solicitation into your target socio-economic set-aside (`SDVOSB`, `8(a) Competitive / Sole-Source`, `HUBZone`, `WOSB/EDWOSB`, or `Total Small Business`) and provides an explicit prime-vs.-similarly-situated workshare model under **`13 CFR 125.6` / `FAR 52.219-14` Limitations on Subcontracting (50%+ Rule)**.
2. **Requirement-by-Requirement Capability & Past Performance Alignment Matrix:**
   - Maps every technical task area and Contracting Officer market research question in the Sources Sought / RFI notice to your exact company capabilities, past performance citations (`Agency`, `Contract #`, `Value`, `Relevance`), and differentiators.
3. **Strategic Acquisition Shaping Recommendations (NAICS, Vehicles, Evaluation Factors & Anti-Incumbent Edits):**
   - Formulates diplomatic, FAR-backed recommendations for the Contracting Officer (`CO`) and Small Business Specialist (`OSDBU / SBS`) to steer the acquisition toward your preferred NAICS size standard (`541512`, `541519`, `541511`), contract vehicle (`GSA MAS 54151HACS`, `8(a) STARS III`, `OASIS+`, `CIO-SP3`), and evaluation criteria while removing restrictive incumbent-tailored requirements.
4. **Paste-Ready Sources Sought / RFI Capability Statement & OSDBU Briefing Deck:**
   - Generates a complete, submission-ready **Corporate Overview Block (`UEI`, `CAGE`, `NAICS`, `PSC`, `Socio-Economic Status`, `Clearance`, `Vehicles`)**, **Market Research Question Responses**, **Full Capability Statement Narrative**, and **Contracting Officer / OSDBU Discovery Call Talking Points**.

---

## Endpoint
`POST /v1/generate/sources-sought-response`

### Request Body (`application/json`)
| Field | Type | Required | Description |
|---|---|---|---|
| `sources_sought_notice_text` | `string` | Yes | Raw SAM.gov or SLED Sources Sought notice, Request for Information (RFI), draft SOW/PWS scope, and market research questions (`20`–`45,000` chars). |
| `company_capabilities_and_vehicles` | `string` | Yes | Vendor core competencies, socio-economic certifications (`8(a)`, `SDVOSB`, `HUBZone`, `WOSB`, `Small Business`), NAICS codes, contract vehicles (`GSA MAS`, `OASIS+`, `8(a) STARS III`, `CIO-SP3`, `SEWP`), clearances, and past performance (`20`–`35,000` chars). |
| `target_set_aside_goal` | `string` | No | `"Auto_Recommend"` (default), `"Total_Small_Business"`, `"8a_Set_Aside_or_Sole_Source"`, `"SDVOSB_Set_Aside"`, `"WOSB_EDWOSB_Set_Aside"`, `"HUBZone_Set_Aside"`, or `"Full_and_Open_Unrestricted"`. |
| `desired_contract_vehicle_and_naics` | `string` | No | Preferred GWAC/IDIQ vehicle and NAICS code to shape the acquisition toward (`1`–`500` chars). |
