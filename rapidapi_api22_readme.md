# GovCon Organizational Conflict of Interest (OCI) & FAR 9.5 Mitigation Plan API

Automate **Federal & Defense Organizational Conflict of Interest (`FAR Subpart 9.5`, `DFARS 252.209-7008 / 252.209-7009`) compliance and mitigation planning**. Transform target solicitation PWS/SOW scope, Section H/L OCI instructions, and your existing Prime/Sub SETA, A&AS, IV&V, or Systems Engineering contract portfolio into a structured JSON package containing:

1. **3-Pillar `FAR Subpart 9.5` Statutory OCI Audit Matrix:**
   - Evaluates your existing awards and corporate/affiliate relationships against all three statutory OCI categories recognized by the Government Accountability Office (GAO) and Court of Federal Claims (COFC):
     - **`Unequal_Access_To_Information` (`FAR 9.505-4`):** Access to non-public source-selection information, proprietary third-party technical data, or independent government cost estimates (`IGCEs`).
     - **`Biased_Ground_Rules` (`FAR 9.505-1` / `9.505-2`):** Prior involvement in drafting specifications, PWS/SOW task areas, or evaluation criteria (`SETA / A&AS` exposure).
     - **`Impaired_Objectivity` (`FAR 9.505-3`):** Situations where a contractor's judgment could be compromised by evaluating its own products, software, or affiliate deliverables (`IV&V` / test & evaluation conflicts).
2. **Enforceable Technical, Physical & Organizational Firewall Controls:**
   - Generates concrete, auditable mitigation controls across `Information_And_IT_Enclave_Firewall` (separate `M365 GCC High` / `AWS GovCloud IL5` RBAC tenants and DLP logging), `Physical_And_Personnel_Separation`, `Non_Disclosure_And_Employee_Screening` (`FAR 9.505-4` bilateral NDAs), `Subcontractor_Firewalled_Workshare_Recusal` (carving out conflicted IV&V tasks to a 100% independent subcontractor without Prime review), and `Independent_Compliance_Audit_And_CO_Reporting`.
3. **Contracting Officer (`CO`) Determination & GAO Protest Defense Posture:**
   - Formulates the exact `FAR 9.504` legal rationale and GAO case-law defense demonstrating why the proposed firewall and recusal architecture neutralizes any potential conflict without requiring exclusion.
4. **Paste-Ready OCI Disclosure & Mitigation Plan Volume:**
   - Produces a complete, Section H/K/L submission-ready **OCI Disclosure Statement**, **Mitigation Plan Narrative**, and **Executive Attestation Block**.

---

## Endpoint
`POST /v1/generate/oci-mitigation-plan`

### Request Body (`application/json`)
| Field | Type | Required | Description |
|---|---|---|---|
| `new_solicitation_scope_and_oci_clauses` | `string` | Yes | Target solicitation PWS/SOW scope, Section H/I/K/L OCI disclosure instructions, and applicable `FAR Subpart 9.5` / `DFARS 252.209-7008` / agency OCI clauses (`20`–`45,000` chars). |
| `existing_contracts_and_corporate_relationships` | `string` | Yes | Active or recent Prime/Sub awards, SETA/A&AS/IV&V support contracts, parent/affiliate relationships, and proposed teaming partners (`20`–`35,000` chars). |
| `proposed_mitigation_posture` | `string` | No | `"Auto_Recommend_Mitigation"` (default), `"Information_Firewall_Only"`, `"Subcontractor_Firewalled_Recusal"`, `"Dual_Firewall_And_Subcontract_Recusal"`, or `"Pre_Bid_No_OCI_Certification"`. |

