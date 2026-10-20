# GovCon Key Personnel & LCAT Resume Tailoring API

**GovCon Key Personnel & LCAT Resume Tailoring API** (`POST /v1/match/key-personnel`) is a stateless, enterprise-grade GovCon HRTech and proposal compliance microservice that audits candidate resumes against **RFP Section L/M Key Personnel** and **GSA MAS / OASIS+ / Alliant 3 Labor Category (LCAT)** qualification matrices, rewrites experience into **Shipley-compliant Key Personnel biographical sketches**, and drafts ready-to-sign **Letters of Commitment (LOC)**.

---

## Key Capabilities

1. **GSA & GWAC LCAT Qualification Auditing (`0–100` Score):**
   - Verifies candidate years of general and specialized experience (`required_years_experience` vs. `verified_candidate_years_experience`) to prevent bid protests and GSA Office of Inspector General (OIG) defective-pricing findings for unqualified labor billing.
   - Outputs an explicit `qualification_verdict`: `FULLY_QUALIFIED_COMPLIANT`, `QUALIFIED_VIA_SUBSTITUTION`, `WAIVER_OR_CERT_PENDING`, or `DISQUALIFIED_HARD_KNOCKOUT`.
2. **Degree vs. Experience Equivalency Substitution Engine:**
   - Evaluates standard GSA/FAR degree-to-experience equivalency formulas (e.g., Bachelor's + 4 years of specialized experience substituting for a Master's degree, or 4 years of extra experience substituting for a Bachelor's degree) when `allow_education_experience_substitution: true`.
3. **Security Clearance & DoD 8570 / 8140 Certification Verification:**
   - Audits candidate security clearances (`Public Trust`, `Secret`, `Top Secret / SCI`, `CI/Full-Scope Polygraph`) and DoD 8570.01-M / DoD 8140 IAT/IAM/CSSP baseline certifications (`CISSP`, `CISM`, `Security+`, `CEH`, `CASP+`, `PMP`, `AWS Pro`).
4. **Shipley Key Personnel Bio Rewrite & Letter of Commitment (LOC):**
   - Generates a third-person, evaluator-first **Shipley Key Personnel Biographical Sketch** (`executive_key_personnel_bio`), rewritten action-result experience bullets (`tailored_experience_citations`), and a ready-to-sign **Key Personnel Letter of Commitment (`draft_letter_of_commitment`)**.

---

## Example Request (`POST /v1/match/key-personnel`)

```json
{
  "lcat_or_rfp_requirements": "Section L.4.2 Key Personnel - Lead Zero-Trust Cloud Architect (GSA MAS SIN 54151S SME III): Must possess an active DoD Top Secret clearance, Master's degree in Computer Science or Information Assurance (or Bachelor's + 4 additional years of specialized experience), minimum 10 years of federal cloud architecture experience including 5 years leading AWS GovCloud / FedRAMP High migrations, and active DoD 8570 IAM Level III (CISSP or CISM) certification.",
  "candidate_resume_text": "Jane Doe | Active Top Secret / SCI Clearance | Certifications: ISC2 CISSP, AWS Certified Solutions Architect - Professional, PMP. Education: B.S. in Computer Engineering, Virginia Tech (2011). Experience (14 yrs total): Principal Cloud Architect at Apex Defense Systems (2018-Present, 8 yrs) — Led 6 DoD and DISA IL5/FedRAMP High cloud migrations on AWS GovCloud and Kubernetes; Senior Systems Engineer at CyberCore Federal (2012-2018, 6 yrs) — Designed RMF / NIST 800-53 zero-trust enclaves for U.S. Navy SPAWAR.",
  "allow_education_experience_substitution": true
}
```

---

## Ideal Use Cases
- **GovCon Proposal & Capture Teams:** Instantly verify Key Personnel resumes against Section L/M and generate Shipley Volume I / Management Volume bios + Letters of Commitment in seconds.
- **Cleared Staffing & Recruiting Agencies (ATS / HRTech):** Automate candidate-to-LCAT compliance screening across GSA MAS, OASIS+, Polaris, Alliant 3, and CIO-SP4 task orders.
- **Prime Contractor Program Managers:** Audit subcontractor resumes prior to task order onboarding to ensure strict LCAT billing compliance.
