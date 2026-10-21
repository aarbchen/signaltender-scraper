# GovCon Teaming Partner & Subcontracting Plan API (`POST /v1/generate/teaming-strategy`)

Automate **Federal & SLED Teaming Strategy, Capability Gap Analysis, 13 CFR § 125.6 / FAR 52.219-14 Limitations on Subcontracting (50% Rule) Compliance Auditing, Ostensible Subcontractor Risk Scoring, and FAR Subpart 9.6 Teaming Agreement Drafting** via a single stateless REST endpoint.

Built for **GovCon Capture Managers, Proposal Directors, Small Business Primes (8(a), SDVOSB, WOSB, HUBZone), Large Business Integrators, and GovTech SaaS Platforms**.

---

## Key Capabilities

1. **13 CFR § 125.6 & FAR 52.219-14 (Limitations on Subcontracting) Workshare Audit**
   - Automatically calculates whether your proposed Prime vs. Subcontractor labor split complies with the **50% Services / Supplies limitation** (or 85%/75% construction thresholds).
   - Flags **Similarly Situated Entity (SSE)** workshare exceptions under 13 CFR § 125.6(c) so small business socio-economic Primes can legally credit qualified small business subcontractor percentages toward self-performance minimums.

2. **SBA Ostensible Subcontractor Affiliation Risk Radar (13 CFR § 121.103(h)(3))**
   - Evaluates SBA's "unusual reliance" factors (incumbent subcontractor dependency, key personnel control, management structure, and primary/vital requirement performance) and provides concrete size-protest mitigation actions.

3. **Requirement-to-Capability Gap Matrix & Ideal Partner Archetypes**
   - Shreds RFP technical, past performance, Facility Clearance (Secret / Top Secret / SCI), and certification (CMMC Level 2, FedRAMP, ISO) requirements against your company capabilities to define exact subcontractor or prime partner profiles, target NAICS codes, and recommended workshare splits.

4. **Ready-to-Use FAR Subpart 9.6 Teaming Agreement Clauses & BD Outreach Email**
   - Generates tailored **FAR Subpart 9.6 Contractor Team Arrangement (CTA)** legal clauses (exclusivity, post-award subcontract conversion targets, CUI/OCI flow-downs, and IP protection) plus a high-conversion **BD / Capture Partner Outreach Email** ready to send to target Primes or Subcontractors.

---

## Endpoint

### `POST /v1/generate/teaming-strategy`

#### Request Body (`application/json`)

```json
{
  "rfp_text": "SDVOSB Set-Aside (NAICS 541512, $18M ceiling). Requires AWS GovCloud DevSecOps (60%), 24x7 Tier-3 SOC with Top Secret FCL (25%), and ServiceNow ITSM (15%). Incorporates FAR 52.219-14.",
  "bidder_capabilities": "Verified SDVOSB, Secret FCL, AWS GovCloud DevSecOps Prime past performance ($12M USAF). Seeking TS-cleared SOC & ServiceNow sub.",
  "set_aside_type": "sdvosb",
  "bidder_role": "prime_seeking_subs"
}
```

---

## Stateless Zero-Retention Architecture & MCP Support
- **Stateless Processing:** No solicitation text or proprietary capability statements are stored after response delivery.
- **Model Context Protocol (MCP) Ready:** Available natively in `@signaltender/mcp-server` (`generate_govcon_teaming_strategy`) and `https://b2b-contract-parser-api.onrender.com/mcp`.
