"""
SignalTender Multi-API Telemetry & Green-Badge Seeder (seed_rapidapi_telemetry.py)
Warms and verifies all production microservices across both:
  1. The unified Render FastAPI gateway (using RAPIDAPI_PROXY_SECRET from .env)
  2. All RapidAPI Marketplace Proxy Hosts (if RAPIDAPI_KEY is set in .env),
     recording 200 OK responses and low-latency telemetry to maintain RapidAPI's
     green 100% Service Level badges across all storefronts.
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv(dotenv_path=r"D:\Data API Ecosystem\.env")
load_dotenv()

BASE_URL = os.getenv(
    "SIGNALTENDER_API_BASE_URL",
    "https://b2b-contract-parser-api.onrender.com",
).rstrip("/")
PROXY_SECRET = os.getenv("RAPIDAPI_PROXY_SECRET")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

ENDPOINTS = [
    {
        "id": "API 01",
        "name": "B2B Contract Parsing API",
        "method": "POST",
        "path": "/v1/parse/contract",
        "rapid_host": "b2b-contract-parsing-api.p.rapidapi.com",
        "payload": {
            "raw_text": (
                "MASTER SERVICES AGREEMENT. Effective Date: November 1, 2026 between "
                "Aegis Cyber LLC ('Vendor') and Department of Veterans Affairs ('Client'). "
                "Total Contract Value: $890,000.00 over 12 months. Payment Terms: Net 30. "
                "Governing Law: Federal Acquisition Regulation (FAR). Deliverables: 24x7 SOC monitoring."
            )
        },
    },
    {
        "id": "API 02",
        "name": "AI Contract Risk & Redline Auditor API",
        "method": "POST",
        "path": "/v1/parse/contract-risks",
        "rapid_host": "ai-contract-risk-redline-auditor-api.p.rapidapi.com",
        "payload": {
            "raw_text": (
                "Section 8.1 Indemnification: Vendor shall indemnify and hold harmless Client "
                "from any and all claims or consequential damages without cap or limitation. "
                "Section 9.2 Termination: Client may terminate upon 24 hours notice without cause."
            ),
            "party_perspective": "vendor",
        },
    },
    {
        "id": "API 03",
        "name": "Historical Procurement Pricing API",
        "method": "POST",
        "path": "/v1/awards/search",
        "rapid_host": "historical-procurement-pricing-api.p.rapidapi.com",
        "payload": {"keywords": "cyber"},
    },
    {
        "id": "API 04",
        "name": "Live SLED & Federal Open RFP Feed API",
        "method": "GET",
        "path": "/v1/solicitations/live",
        "rapid_host": "live-sled-federal-open-rfp-feed-api.p.rapidapi.com",
        "params": {"state": "virginia", "limit": 5},
    },
    {
        "id": "API 05",
        "name": "RFP Compliance Matrix & Proposal Outline API",
        "method": "POST",
        "path": "/v1/generate/compliance-matrix",
        "rapid_host": "rfp-compliance-matrix-proposal-outline-api.p.rapidapi.com",
        "payload": {
            "raw_text": (
                "SECTION C: C.3.1 The Contractor shall provide 24x7x365 Managed Detection and Response "
                "across 10,000 endpoints with FedRAMP High authorization. SECTION L: Offerors must submit "
                "Volume I (Technical Approach, max 20 pages). SECTION M: Technical Approach is most important."
            ),
            "proposal_methodology": "shipley",
        },
    },
    {
        "id": "API 06",
        "name": "FAR / DFARS & CMMC Clause Risk Scanner API",
        "method": "POST",
        "path": "/v1/audit/far-dfars-clauses",
        "rapid_host": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com",
        "payload": {
            "raw_text": (
                "This solicitation incorporates FAR 52.215-2, DFARS 252.204-7012 (Safeguarding Covered "
                "Defense Information), DFARS 252.204-7020, and DFARS 252.204-7021 (CMMC Level 2 Required)."
            ),
            "contractor_role": "prime_contractor",
        },
    },
    {
        "id": "API 07",
        "name": "AI Bid/No-Bid & Capability Matcher API",
        "method": "POST",
        "path": "/v1/match/capability-statement",
        "rapid_host": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com",
        "payload": {
            "rfp_text": (
                "SOLICITATION: DHS-SOC-2026. NAICS: 541512. Set-Aside: SDVOSB. Scope: 24x7 Zero-Trust SOC "
                "and Splunk SOAR engineering. Requires Secret FCL, ISO 27001, and CMMC Level 2."
            ),
            "company_capability_statement": (
                "Apex Cyber LLC — Certified SDVOSB. Secret FCL, ISO 27001, CMMC Level 2 Ready. "
                "Past Performance: USCG 24x7 SOC ($6.8M) and VA SIEM Modernization ($5.4M)."
            ),
            "target_pursuit_role": "either_prime_or_sub",
        },
    },
    {
        "id": "API 08",
        "name": "NAICS, SIC, PSC & UNSPSC Industry Classifier API",
        "method": "POST",
        "path": "/v1/classify/naics-psc-nigp",
        "rapid_host": "naics-sic-psc-unspsc-industry-classifier-api.p.rapidapi.com",
        "payload": {
            "description_text": (
                "Managed 24x7x365 Zero-Trust cybersecurity operations, AWS GovCloud migration engineering, "
                "and custom DevSecOps software development for federal and state agencies."
            ),
            "context_type": "company_or_vendor_profile",
            "max_secondary_codes": 2,
        },
    },
    {
        "id": "API 09",
        "name": "AI RFP Response & Clarification Q&A Generator API",
        "method": "POST",
        "path": "/v1/generate/rfp-response",
        "rapid_host": "ai-rfp-response-clarification-q-a-generator-api.p.rapidapi.com",
        "payload": {
            "rfp_section_text": (
                "C.4.1 The Contractor shall migrate 30 legacy applications to a FedRAMP High cloud "
                "within 90 days with zero unplanned downtime and <= 10 minute Severity-1 MTTR."
            ),
            "company_context_and_capabilities": (
                "Aegis Cloud LLC — Certified 8(a) & SDVOSB (CMMC Level 2, ISO 27001). Migrated 62 apps "
                "for DoE to AWS GovCloud with 99.998% uptime and 4.2-minute SOC MTTR."
            ),
            "target_section_type": "technical_approach",
            "tone_and_methodology": "shipley_federal",
        },
    },
    {
        "id": "API 10",
        "name": "B2B Quote, Invoice & CLIN Table Extractor API",
        "method": "POST",
        "path": "/v1/extract/pricing-schedule",
        "rapid_host": "b2b-quote-invoice-clin-table-extractor-api.p.rapidapi.com",
        "payload": {
            "document_text": (
                "SECTION B - CLIN SCHEDULE\n"
                "CLIN 0001 (FFP): FedRAMP High Cloud Platform | Qty: 12 Months | Unit: $25,000.00 | Total: $300,000.00\n"
                "CLIN 0002 (T&M): Senior Cloud Architect | Qty: 1,920 Hrs | Rate: $180.00/hr | Total: $345,600.00"
            ),
            "expected_document_type": "federal_section_b_clin_schedule",
            "audit_math_and_anomalies": True,
        },
    },
    {
        "id": "API 11",
        "name": "GovCon Teaming Partner & Subcontracting Plan API",
        "method": "POST",
        "path": "/v1/generate/teaming-strategy",
        "rapid_host": "govcon-teaming-partner-subcontracting-plan-api.p.rapidapi.com",
        "payload": {
            "rfp_text": (
                "SDVOSB Set-Aside (NAICS 541512, $18M ceiling). Requires AWS GovCloud DevSecOps (60%), "
                "24x7 Tier-3 SOC with Top Secret FCL (25%), and ServiceNow ITSM (15%). Incorporates FAR 52.219-14."
            ),
            "bidder_capabilities": (
                "Verified SDVOSB, Secret FCL, AWS GovCloud DevSecOps Prime past performance ($12M USAF). "
                "Seeking TS-cleared SOC & ServiceNow sub."
            ),
            "set_aside_type": "sdvosb",
            "bidder_role": "prime_seeking_subs",
        },
    },
    {
        "id": "API 12",
        "name": "SOC 2, FedRAMP & NIST 800-171 Security Questionnaire Responder API",
        "method": "POST",
        "path": "/v1/audit/security-questionnaire",
        "rapid_host": "soc-2-fedramp-nist-800-171-security-questionnaire-api.p.rapidapi.com",
        "payload": {
            "questionnaire_text": (
                "1. Does your platform enforce phishing-resistant Multi-Factor Authentication (MFA) for all users accessing CUI? "
                "2. How is customer data encrypted at rest and in transit (FIPS 140-2/140-3)? "
                "3. Describe your SIEM audit log retention and DFARS 252.204-7012 incident reporting SLA."
            ),
            "security_posture_summary": (
                "AWS GovCloud & Commercial US-East, SOC 2 Type II certified, Okta FIDO2/WebAuthn MFA enforced, "
                "AES-256 KMS at rest, TLS 1.3 in transit, FIPS endpoints enabled on GovCloud ALB, Datadog SIEM 365-day retention."
            ),
            "target_framework": "auto_detect",
        },
    },
    {
        "id": "API 13",
        "name": "GovCon Key Personnel & LCAT Resume Tailoring API",
        "method": "POST",
        "path": "/v1/match/key-personnel",
        "rapid_host": "govcon-key-personnel-lcat-resume-tailoring-api.p.rapidapi.com",
        "payload": {
            "lcat_or_rfp_requirements": (
                "Section L.4.2 Key Personnel - Lead Zero-Trust Cloud Architect (GSA MAS SIN 54151S SME III): "
                "Must possess an active DoD Top Secret clearance, Master's degree in Computer Science or Information Assurance "
                "(or Bachelor's + 4 additional years of specialized experience), minimum 10 years of federal cloud architecture experience "
                "including 5 years leading AWS GovCloud / FedRAMP High migrations, and active DoD 8570 IAM Level III (CISSP or CISM) certification."
            ),
            "candidate_resume_text": (
                "Jane Doe | Active Top Secret / SCI Clearance | Certifications: ISC2 CISSP, AWS Certified Solutions Architect - Professional, PMP. "
                "Education: B.S. in Computer Engineering, Virginia Tech (2011). "
                "Experience (14 yrs total): Principal Cloud Architect at Apex Defense Systems (2018-Present, 8 yrs) — Led 6 DoD and DISA IL5/FedRAMP High "
                "cloud migrations on AWS GovCloud and Kubernetes; Senior Systems Engineer at CyberCore Federal (2012-2018, 6 yrs) — Designed RMF / NIST 800-53 "
                "zero-trust enclaves for U.S. Navy SPAWAR."
            ),
            "allow_education_experience_substitution": True,
        },
    },
    {
        "id": "API 14",
        "name": "RFP Amendment & Q&A Change-Impact Analyzer API",
        "method": "POST",
        "path": "/v1/analyze/amendment-diff",
        "rapid_host": "rfp-amendment-q-a-change-impact-analyzer-api.p.rapidapi.com",
        "payload": {
            "base_solicitation_text": (
                "RFP FA8732-26-R-0018 (Base Solicitation): Section L.4: Proposals are due November 10, 2026 at 14:00 EST. "
                "Volume I Technical Approach shall not exceed 25 pages. Section C.3.1: The Contractor shall deploy a FedRAMP Moderate "
                "cloud data platform supporting 5,000 concurrent users. Section C.4.2: Key Personnel Lead Cloud Architect must hold an "
                "active Top Secret clearance. Section B CLIN 0001: Base Year Cloud Migration Engineering (Firm-Fixed-Price)."
            ),
            "amendment_or_qa_text": (
                "SF-30 AMENDMENT 0002 (Issued Oct 20, 2026): 1. Block 11: The proposal due date is extended from November 10, 2026 to "
                "November 24, 2026 at 17:00 EST. 2. Section L.4 is revised to increase Volume I page limit from 25 pages to 35 pages. "
                "3. Section C.3.1 is replaced: The Contractor shall deploy a FedRAMP High and DoD IL5 authorized cloud data platform "
                "supporting 15,000 concurrent users. 4. Section B CLIN 0001 is converted from FFP to T&M ($4,200,000 NTE). "
                "Q&A #12: Active Secret clearance with Top Secret adjudication in progress is acceptable at submission. "
                "Q&A #19: Real-time STIG-compliant log forwarding to the agency Splunk Cloud environment is mandatory."
            ),
            "current_proposal_outline": (
                "Volume I Technical (25 pages max): Sec 1.0 Executive Summary; Sec 2.0 FedRAMP Moderate Architecture (5,000 users); "
                "Sec 3.0 Key Personnel (Top Secret required at submission); Volume III Pricing: CLIN 0001 FFP Schedule."
            ),
        },
    },
    {
        "id": "API 15",
        "name": "CPARS & Past Performance Volume Generator API",
        "method": "POST",
        "path": "/v1/generate/past-performance",
        "rapid_host": "cpars-past-performance-volume-generator-api.p.rapidapi.com",
        "payload": {
            "rfp_section_l_m_requirements": (
                "SOLICITATION FA8726-26-R-0054 (USAF Enterprise Cloud & Zero-Trust SOC Modernization): "
                "Section L.5 Volume III Past Performance requires up to 3 recent (within 5 years) citations >= $4M/yr ($12M Total Value), "
                "with at least 2 performed as Prime Contractor. Section M.3 evaluates Scope, Magnitude, and Complexity across PWS 3.1 AWS GovCloud IL5 Migration, "
                "PWS 3.2 Zero-Trust ICAM, and PWS 3.3 24x7x365 Cleared SOC & Splunk SIEM."
            ),
            "project_history_text": (
                "Contract 1 (Prime): U.S. Space Force SSC Enterprise Cloud Enclave (FA8802-22-C-0019, FFP/T&M, $18.4M Total, $6.1M/yr, 2022-2025, 34 FTEs, NAICS 541512). "
                "Migrated 42 mission apps to AWS GovCloud IL5, deployed Zero-Trust ICAM for 14,500 users, and ran 24x7 TS/SCI Splunk SOC. "
                "CPARS: Exceptional across Quality, Schedule, Cost Control, Management, and Small Business (99.98% SLA, $420K FinOps savings). "
                "Contract 2 (Prime): DISA Defense Enclave Cyber Modernization (HC1028-23-F-0112, T&M, $13.2M Total, $4.4M/yr, 2023-Present, 26 FTEs). "
                "Automated STIG hardening, Zero-Trust microsegmentation, and cATO pipelines across 8,000 endpoints."
            ),
            "bidder_role_and_context": (
                "Prime Offeror submitting 2 DoD Prime contracts + 1 Major Subcontractor contract; Volume III page limit is 15 pages."
            ),
        },
    },
    {
        "id": "API 16",
        "name": "GovCon IGCE, Wrap-Rate & Price-to-Win Modeler API",
        "method": "POST",
        "path": "/v1/generate/price-to-win",
        "rapid_host": "govcon-igce-wrap-rate-price-to-win-modeler-api.p.rapidapi.com",
        "payload": {
            "rfp_section_b_and_sow_text": (
                "SOLICITATION FA8732-26-R-0041 (USAF Cloud & Zero-Trust DevSecOps Engineering): "
                "Section B Schedule of Supplies/Services: 1-Year Base Period + Two (2) 1-Year Option Periods (36 Months Total PoP). "
                "CLIN 0001: Enterprise Cloud Migration & Zero-Trust Engineering (Time-and-Materials / Labor Hour, 7 FTEs, 1,920 hrs/FTE/yr): "
                "1x Program Manager (TS/SCI, 12+ yrs), 2x Principal Cloud/Zero-Trust Architects (TS/SCI, 10+ yrs, CISSP), "
                "3x Senior DevSecOps Kubernetes Engineers (Secret, 7+ yrs), 1x Cyber RMF / Continuous ATO Lead (Secret, 8+ yrs, CAP/CISSP). "
                "CLIN 0002: 24x7 Managed Security Operations Center (SOC) Tier-2/3 Monitoring (Firm-Fixed-Price, 3 FTEs, Secret). "
                "CLIN 0003: Cloud FinOps Tooling & Travel ODCs (Cost Reimbursable, No Fee, Government Plug = $125,000/year). "
                "Section M.4 Evaluation Criteria: Best-Value Tradeoff (Technical + Past Performance significantly more important than Cost/Price) "
                "with FAR 52.222-46 Evaluation of Compensation for Professional Employees realism screening."
            ),
            "bidder_indirect_wrap_assumptions": (
                "GSA MAS SIN 54151S & SIN 54151HACS Prime Contractor. Place of Performance: Contractor Site (Northern Virginia / NCR). "
                "Indirect Rate Assumptions: Fringe 31.5%, Contractor-Site Overhead 24.0%, G&A 11.5% (Total Indirect Wrap ~ 1.818x before fee), "
                "Target Profit/Fee: 8.5% on T&M, 10.5% on FFP. Subcontractor Material Handling / G&A on Subk: 4.0%. Annual Escalation: 3.25%/yr."
            ),
            "historical_benchmark_and_incumbent_context": (
                "Incumbent is a Large Business defense integrator awarded $6.85M over 3 years ($2.28M/yr) under a legacy OASIS task order; "
                "recompete is now a Small Business Set-Aside on GSA MAS."
            ),
        },
    },
    {
        "id": "API 17",
        "name": "GovCon Oral Presentation, Tech-Demo & Murder-Board Prep API",
        "method": "POST",
        "path": "/v1/generate/oral-presentation-prep",
        "rapid_host": "govcon-oral-presentation-tech-demo-murder-board-prep-api.p.rapidapi.com",
        "payload": {
            "rfp_oral_instructions_and_sow_text": (
                "SOLICITATION FA8732-26-R-0088 (USAF Zero-Trust Cloud & DevSecOps Modernization — Phase II Advisory Down-Select): "
                "Section L.8 Phase II Oral Presentation & Live Technical Demonstration Instructions: "
                "90-Minute Total Session (60-minute structured Oral Presentation + 15-minute Live Technical Demonstration "
                "+ 15-minute interactive Government Q&A / Caucus). Maximum 18 slides. Only proposed Key Personnel may present."
            ),
            "bidder_solution_and_key_personnel_context": (
                "Key Personnel Speakers: (1) Marcus Vance, PMP — Program Manager (TS/SCI); "
                "(2) Elena Rostova, CISSP — Lead Zero-Trust Cloud Architect; "
                "(3) Devon Brooks, CKA — DevSecOps & cATO Lead. "
                "Technical Solution: Pre-hardened BigBang IL5 Kubernetes landing zone with automated STIG enforcement and 14-day Day-1 transition Playbook."
            ),
            "known_incumbent_and_risk_areas": (
                "Challenger Small Business unseating a 5-year Large Business incumbent."
            ),
            "presentation_format_mode": "COMBINED_ORALS_TECH_DEMO_AND_QA",
        },
    },
    {
        "id": "API 18",
        "name": "GovCon RMF, Continuous ATO (cATO), SSP & POA&M Generator API",
        "method": "POST",
        "path": "/v1/generate/ato-rmf-package",
        "rapid_host": "govcon-rmf-continuous-ato-cato-ssp-poa-m-generator-api.p.rapidapi.com",
                "payload": {
            "system_architecture_and_rfp_cyber_text": (
                "SOLICITATION FA8726-26-R-0092 (USAF Mission Command Cloud & DevSecOps Modernization): "
                "Section C.4 Cybersecurity & RMF Requirements: Contractor shall design, deploy, and maintain "
                "a Cloud-Native Mission Application hosted on AWS GovCloud (US-East/West) at DoD Impact Level 5 (IL5). "
                "System processes Controlled Unclassified Information (CUI) and Mission-Critical Operational Telemetry. "
                "Must achieve Interim Authority to Test (IATT) within 60 days and Full Continuous Authority to Operate (cATO) "
                "under DoDI 8510.01 (RMF) and NIST SP 800-53 Rev 5 Moderate/High Overlay."
            ),
            "cloud_hosting_and_inherited_controls_context": (
                "Hosted on AWS GovCloud (US) with FedRAMP High & DoD SRG IL5 Provisional Authorization (PA). "
                "Platform layer uses Platform One BigBang Kubernetes (EKS) with Istio mTLS service mesh, "
                "Keycloak CAC/PKI ICAM, GitLab CI/CD runners, Anchore/Trivy container scanning, and Splunk Cloud SIEM."
            ),
            "target_authorization_framework": "dod_rmf_dodi_8510_01_cato",
            "target_impact_level": "IL5_CUI_NSS",
        },
    },
    {
        "id": "API 19",
        "name": "GovCon Debriefing, FAR 15.506 & GAO Bid-Protest Analyzer API",
        "method": "POST",
        "path": "/v1/generate/debriefing-bid-protest",
        "rapid_host": "govcon-debriefing-far-15-506-gao-bid-protest-analyzer-api.p.rapidapi.com",
        "payload": {
            "award_notice_or_debrief_text": (
                "SOLICITATION FA8732-26-R-0094 (USAF Enterprise Zero-Trust & Cloud SIEM Modernization): "
                "Notice of Unsuccessful Offeror & Post-Award Debriefing Slide Summary (Issued Oct 20, 2026): "
                "Awardee: Apex Federal Solutions ($48.4M Total Evaluated Price; Technical/Management: Outstanding; Past Performance: Substantial Confidence). "
                "Your Offer (Vanguard Cyber Defense): $42.1M Total Evaluated Price; Technical/Management: Acceptable (1 Significant Weakness assigned under "
                "Subfactor 1.2 for 'lack of automated multi-region IL5 failover telemetry in Section 3.4'); Past Performance: Satisfactory Confidence."
            ),
            "rfp_section_m_and_bidder_context": (
                "RFP Section M.2 Evaluation Criteria: Best-Value Tradeoff (FAR 15.101-1). Subfactor 1.2 requires 'automated regional failover orchestration within 15 minutes RTO' "
                "and does NOT mandate active-active multi-region telemetry streaming. Our Technical Volume Section 3.4 (pp. 22-24, Figure 3-2) explicitly documented "
                "automated Terraform + Route53 health-check failover across AWS GovCloud US-East and US-West achieving an 8-minute RTO."
            ),
            "procurement_jurisdiction": "dod_dfars_215_506_enhanced",

            "analysis_mode": "unsuccessful_offeror_debrief_and_protest",
        },
    },
    {
        "id": "API 20",
        "name": "GovCon GSA MAS Schedule, SIN Mapper & PRC Compliance API",
        "method": "POST",
        "path": "/v1/generate/gsa-mas-offer",
        "rapid_host": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com",
        "payload": {
            "commercial_catalog_and_lcat_rates": (
                "Commercial Price List (CPL) 2026: "
                "1) Principal Zero-Trust & Cloud Security Architect ($195/hr CPL, BS CS + CISSP/AWS Pro, 10 yrs exp); "
                "2) Lead DevSecOps & Platform Engineer ($175/hr CPL, BS + CKA, 7 yrs exp); "
                "3) Senior Cyber RMF / ISSO Analyst ($158/hr CPL, BS + CAP/CISM, 6 yrs exp). "
                "Commercial clients receive 4-6% volume discounts on orders >$250K; proposed GSA Net Discount is 8.0% off CPL before the 0.75% IFF."
            ),
            "corporate_experience_and_project_context": (
                "Target GSA MAS Large Category F SINs: 54151S (IT Professional Services), 54151HACS (Highly Adaptive Cybersecurity Services), "
                "518210C (Cloud & Cloud-Related IT Professional Services), and OLM. "
                "Completed Projects: (A) DISA Zero-Trust ICAM & Kubernetes Cloud Migration ($2.4M, 2024-2026); "
                "(B) Virginia VITA Statewide Identity Governance, PAM & 24x7 MDR SOC ($2.1M, 2023-2026)."
            ),
            "pricing_disclosure_pathway": "Auto_Recommend",
            "submission_type": "New_GSA_MAS_Offer",
        },
    },
]


def run_telemetry_seeder(rotating: bool = False, slice_size: int = 4) -> None:
    print(f"=== SignalTender Multi-API Telemetry Seeder (rotating={rotating}) ===", flush=True)
    print(f"Gateway: {BASE_URL}", flush=True)

    if not PROXY_SECRET and not RAPIDAPI_KEY:
        print("[!] Neither RAPIDAPI_PROXY_SECRET nor RAPIDAPI_KEY set in environment.", flush=True)
        return

    if rotating and len(ENDPOINTS) > slice_size:
        slot = (int(time.time()) // 21600) % 4
        start_idx = (slot * slice_size) % len(ENDPOINTS)
        target_endpoints = [ENDPOINTS[(start_idx + i) % len(ENDPOINTS)] for i in range(slice_size)]
        # Always include zero-LLM database endpoints (API 03 & API 04) for fast latency telemetry
        existing_ids = {e["id"] for e in target_endpoints}
        for fast_ep in ENDPOINTS:
            if fast_ep["id"] in ("API 03", "API 04") and fast_ep["id"] not in existing_ids:
                target_endpoints.append(fast_ep)
    else:
        target_endpoints = ENDPOINTS

    passed = 0
    for ep in target_endpoints:
        t0 = time.time()
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if RAPIDAPI_KEY:
            url = f"https://{ep['rapid_host']}{ep['path']}"
            headers["X-RapidAPI-Key"] = RAPIDAPI_KEY
            headers["X-RapidAPI-Host"] = ep["rapid_host"]
        else:
            url = f"{BASE_URL}{ep['path']}"
            parts = [s.strip() for s in (PROXY_SECRET or "").split(",") if s.strip()]
            prod_parts = [s for s in parts if not s.startswith("local_")]
            chosen = prod_parts[0] if prod_parts else (parts[0] if parts else "")
            headers["X-RapidAPI-Proxy-Secret"] = chosen

        try:
            if ep["method"] == "GET":
                resp = requests.get(url, params=ep.get("params", {}), headers=headers, timeout=60)
            else:
                resp = requests.post(url, json=ep.get("payload", {}), headers=headers, timeout=60)
            elapsed_ms = int((time.time() - t0) * 1000)
            status_tag = "OK" if resp.status_code == 200 else f"HTTP {resp.status_code}"
            print(f"[{ep['id']}] {ep['name']} -> {status_tag} ({elapsed_ms} ms)", flush=True)
            if resp.status_code == 200:
                passed += 1
        except Exception as exc:
            print(f"[{ep['id']}] {ep['name']} -> ERROR: {exc}", flush=True)

    print(f"\nCompleted: {passed}/{len(target_endpoints)} endpoints returned 200 OK.", flush=True)


if __name__ == "__main__":
    run_telemetry_seeder()

