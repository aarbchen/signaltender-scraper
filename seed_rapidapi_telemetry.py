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
    {
        "id": "API 21",
        "name": "GovCon Sources Sought, RFI & Set-Aside Shaping Responder API",
        "method": "POST",
        "path": "/v1/generate/sources-sought-response",
        "rapid_host": "govcon-sources-sought-rfi-set-aside-shaping-responder-api.p.rapidapi.com",
        "payload": {
            "sources_sought_or_rfi_notice_text": (
                "SOURCES SOUGHT / RFI NOTICE ID: FA8726-27-RFI-0019 (USAF AFLCMC / Hanscom AFB). "
                "The Government is conducting FAR Part 10 market research to determine small business capability "
                "and set-aside viability for Enterprise Zero-Trust Identity, Credential, and Access Management (ICAM), "
                "24x7 Managed Detection and Response (MDR) SOC telemetry, and DoD IL5 Cloud DevSecOps migration. "
                "Anticipated NAICS: 541512 ($34.0M)."
            ),
            "vendor_capability_and_socioeconomic_profile": (
                "Aegis Federal Cyber & Cloud LLC (UEI: K9M4N8P2Q1R5 | CAGE: 8X9A2) is an SBA-certified SDVOSB and 8(a) "
                "Program participant under NAICS 541512, 541519, and 518210. Contract Vehicles: GSA MAS SIN 54151HACS & 54151S. "
                "Past Performance: USAF Air Mobility Command IL5 Zero-Trust ICAM ($4.8M, Prime, Exceptional CPARS); "
                "DISA 24x7 Splunk SOAR & Endpoint MDR Telemetry ($3.6M, Prime). Top Secret FCL."
            ),
            "target_set_aside_preference": "SDVOSB_Set_Aside",
        },
    },
    {
        "id": "API 22",
        "name": "GovCon Organizational Conflict of Interest (OCI) & FAR 9.5 Mitigation Plan API",
        "method": "POST",
        "path": "/v1/generate/oci-mitigation-plan",
        "rapid_host": "govcon-oci-far-9-5-mitigation-plan-generator-api.p.rapidapi.com",
        "payload": {
            "target_solicitation_and_sow_text": (
                "SOLICITATION FA8802-27-R-0014 (USSF Space Systems Command DevSecOps & Ground C2 Integration). "
                "Section H.8 OCI Notice (FAR Subpart 9.5 / DFARS 252.209-7008 & 252.209-7009): Offerors performing "
                "Systems Engineering and Technical Assistance (SETA) or Advisory & Assistance Services (A&AS) across USSF SSC "
                "shall disclose all active contracts and submit a comprehensive Organizational Conflict of Interest (OCI) "
                "Mitigation Plan addressing Unequal Access to Information, Biased Ground Rules, and Impaired Objectivity."
            ),
            "current_and_prior_contracts_portfolio": (
                "Prime Offeror (Aegis Federal Cyber LLC) holds USSF SSC SETA Task Order FA8802-24-F-0091 in Division B "
                "(El Segundo, CA) providing enterprise architecture studies. Division A (Colorado Springs, CO) is bidding on "
                "FA8802-27-R-0014 with zero personnel overlap, separate Microsoft 365 GCC High / AWS GovCloud IL5 enclaves, "
                "and conflict-free subcontractor Vanguard Orbital Testing LLC assigned 100% of IV&V tasks."
            ),
            "proposed_bidding_role_and_teaming_structure": "Prime_Offeror",
        },
    },
    {
        "id": "API 23",
        "name": "SBIR / STTR Phase I-III Technical Volume & Commercialization Plan API",
        "method": "POST",
        "path": "/v1/generate/sbir-sttr-commercialization",
        "rapid_host": "sbir-sttr-phase-i-iii-commercialization-plan-api.p.rapidapi.com",
        "payload": {
            "sbir_sttr_topic_and_rd_specs": (
                "AFWERX / DoD SBIR 26.3 Topic AF263-D014 (Autonomous Zero-Trust Tactical Edge Mesh & Post-Quantum "
                "Telemetry Encryption for Contested C2 Networks). Objective: Develop and demonstrate a low-SWaP, "
                "CNSA 2.0 / FIPS 203 ML-KEM compliant zero-trust tactical datalink gateway capable of autonomous "
                "key rotation and anti-jamming mesh routing across Denied, Degraded, Intermittent, and Limited (DDIL) "
                "airborne and ground nodes."
            ),
            "company_technology_and_ip_baseline": (
                "Aegis Quantum Defense LLC (SBA Small Business, 18 employees, CAGE 9Q4L1) has developed 'Q-MeshCore v2.1' "
                "at TRL 4 using internal IR&D funding ($620K). Prior IP includes patented hardware-accelerated lattice "
                "KEM key-exchange firmware and an embedded Rust eBPF packet filter benchmarked at 10 Gbps with <180us latency."
            ),
            "target_phase_and_program": "Direct_to_Phase_II",
        },
    },
    {
        "id": "API 24",
        "name": "GovCon Section 508, WCAG 2.2 AA & VPAT 2.5 Accessibility Conformance API",
        "method": "POST",
        "path": "/v1/audit/section-508-vpat",
        "rapid_host": "govcon-section-508-wcag-2-2-aa-vpat-2-5-auditor-api.p.rapidapi.com",
        "payload": {
            "product_architecture_and_ui_specs": (
                "Aegis CloudOps Portal v4.2 is a multi-tenant React 18 / TypeScript web application and REST API "
                "dashboard deployed on AWS GovCloud (US-East) for federal SOC analysts. Features include interactive "
                "D3/Canvas network topology graphs, keyboard-navigable ARIA data tables, SSO/PIV authentication flows, "
                "automated PDF/CSV compliance report exports, and embedded video training modules with WebVTT closed captions. "
                "Target Solicitation Clauses: 36 CFR Part 1194 (Revised Section 508), WCAG 2.2 Level AA, Colorado HB 21-1110 (OIT 8 CCR 1501-11)."
            ),
            "known_accessibility_test_results_or_gaps": (
                "Automated Axe-core 4.9 and Lighthouse audits pass 94% of WCAG 2.1/2.2 Level A/AA rules. Known gaps: "
                "(1) Network topology force-directed canvas graph lacks full screen-reader node traversal and 24x24px "
                "target size spacing; (2) Legacy PDF export engine omits tagged document structure (PDF/UA) on multi-page "
                "charts; (3) Session timeout modal requires keyboard focus trap refinement."
            ),
            "target_compliance_standard": "Revised_Section_508_And_WCAG_2_2_AA",
        },
    },
    {
        "id": "API 25",
        "name": "GovCon Supply Chain Risk Management (SCRM), NDAA 889, TAA & SBOM Auditor API",
        "method": "POST",
        "path": "/v1/audit/supply-chain-scrm",
        "rapid_host": "govcon-supply-chain-scrm-ndaa-889-taa-sbom-auditor-api.p.rapidapi.com",
        "payload": {
            "solicitation_or_contract_context": (
                "Arizona ADOA-ASET Statewide Network Refresh & Public Safety Video Surveillance RFP (Arizona APP / Procure.AZ.gov). "
                "Scope: furnish and install 48-port PoE+ access switches, 4MP IP dome cameras, and a cloud video management "
                "platform for 12 ADOT and DPS facilities. Section H requires offerors to certify FAR 52.204-25 (NDAA Section 889) "
                "compliance for federally funded (DHS/FEMA grant) line items, Trade Agreements Act designated-country end products, "
                "NIST SP 800-161 Rev. 1 C-SCRM practices, and delivery of a CycloneDX SBOM for all software/firmware."
            ),
            "offeror_name": "Sonoran Secure Networks LLC",
            "contracting_agency": "Arizona ADOA-ASET",
            "applicable_contract_clauses": [
                "FAR 52.204-25 (NDAA Section 889 Covered Telecommunications Prohibition)",
                "FAR 52.204-30 (FASCSA Orders Prohibition)",
                "FAR 52.225-5 (Trade Agreements Act)",
                "NIST SP 800-161 Rev. 1 (C-SCRM)",
            ],
            "bom_line_items": [
                {
                    "line_item_id": "BOM-001",
                    "part_number": "C9300-48P-E",
                    "description": "48-Port PoE+ Access Switch",
                    "manufacturer": "Cisco Systems",
                    "country_of_origin": "Mexico",
                    "supplier_name": "CDW Government",
                    "supplier_tier": "Tier_4_Distributor_Or_Raw_Material",
                    "item_category": "IT_Hardware_Or_Network_Equipment",
                    "quantity": 24,
                    "unit_cost_usd": 6850.0,
                },
                {
                    "line_item_id": "BOM-002",
                    "part_number": "DS-2CD2143G2-I",
                    "description": "4MP IP Dome Camera",
                    "manufacturer": "Hikvision",
                    "country_of_origin": "China",
                    "supplier_name": "Desert Security Wholesale",
                    "supplier_tier": "Tier_4_Distributor_Or_Raw_Material",
                    "item_category": "Telecommunications_Or_Video_Surveillance",
                    "quantity": 180,
                    "unit_cost_usd": 189.0,
                },
                {
                    "line_item_id": "BOM-003",
                    "part_number": "P3265-LVE",
                    "description": "Outdoor 2MP Dome Camera (Replacement Candidate)",
                    "manufacturer": "Axis Communications",
                    "country_of_origin": "Sweden",
                    "supplier_tier": "Tier_1_Direct_OEM",
                    "item_category": "Telecommunications_Or_Video_Surveillance",
                    "quantity": 180,
                    "unit_cost_usd": 742.0,
                },
            ],
            "software_components": [
                {
                    "name": "log4j-core",
                    "version": "2.14.1",
                    "purl": "pkg:maven/org.apache.logging.log4j/log4j-core@2.14.1",
                    "license": "Apache-2.0",
                    "supplier": "Apache Software Foundation",
                    "known_vulnerabilities": ["CVE-2021-44228"],
                },
                {
                    "name": "openssl",
                    "version": "3.0.13",
                    "purl": "pkg:generic/openssl@3.0.13",
                    "license": "Apache-2.0",
                    "supplier": "OpenSSL Software Foundation",
                    "known_vulnerabilities": [],
                },
            ],
            "sbom_format": "CycloneDX_1_6",
            "target_compliance_regime": "Auto_Detect_From_Clauses",
        },
    },
    {
        "id": "API 26",
        "name": "GovCon Quality Assurance Surveillance Plan (QASP), PWS SLA & KPI Matrix API",
        "method": "POST",
        "path": "/v1/generate/quality-assurance-qasp",
        "rapid_host": "govcon-qasp-prs-sla-kpi-surveillance-matrix-api.p.rapidapi.com",
        "payload": {
            "pws_or_sow_deliverables_text": (
                "PWS Section C.3 (24x7 Zero-Trust SOC, Cloud Enclave Sustainment & Incident Response — DISA / MNIT Enterprise): "
                "(1) C.3.1 24x7 Security Operations Center (SOC) Triage: Contractor shall detect, triage, and contain Severity-1 cyber "
                "incidents within 30 minutes of SIEM alert generation with 99.95% monthly Splunk/SOAR platform availability. "
                "(2) C.3.2 Continuous ATO (cATO) & Vulnerability Management: Contractor shall remediate 100% of Critical/CAT-I CISA KEV "
                "findings within 48 hours and High/CAT-II findings within 14 calendar days. "
                "(3) C.3.3 Key Personnel & Cleared Staffing Continuity: Maintain >= 95% fill rate across all 24 FTE positions with <= 10 "
                "business days backfill for any vacancy."
            ),
            "contract_type_and_incentive_structure": "Firm_Fixed_Price_FFP",
            "surveillance_rigor_and_mission_criticality": "Mission_Critical_24x7_Zero_Trust",
        },
    },
    {
        "id": "API 27",
        "name": "GovCon 30/60/90-Day Phase-In / Phase-Out Transition & Incumbent Capture API",
        "method": "POST",
        "path": "/v1/generate/phase-in-transition-plan",
        "rapid_host": "govcon-30-60-90-day-phase-in-transition-plan-api.p.rapidapi.com",
        "payload": {
            "solicitation_transition_and_sow_text": (
                "Section L.4.3 & PWS C.2 Phase-In / Phase-Out Transition (60-Day Phase-In / 90-Day FOC): "
                "The incoming Prime Contractor shall execute a zero-mission-disruption transition for a 38-FTE Enterprise Cloud, "
                "Zero-Trust ICAM, and 24x7 Tier-2/3 Service Desk operation supporting Tennessee STS and DoD mission partners. "
                "Full Operational Capability (FOC) is required at Day 60, with Days 61-90 dedicated to steady-state SLA optimization."
            ),
            "incumbent_workforce_and_clearance_context": (
                "Incumbent prime currently staffs 38 FTEs (28 Secret cleared, 10 Top Secret/SCI cleared under DD Form 254; "
                "14 Service Contract Act [SCA] helpdesk/network technicians subject to EO 14055 right-of-first-refusal). "
                "Target incumbent capture rate is >= 90% with 6 pre-cleared bench engineers ready on Day 1."
            ),
            "transition_timeline_window": "Standard_30_60_90_Day_Phase_In",
        },
    },
    {
        "id": "API 28",
        "name": "DCAA Pre-Award Accounting System (SF 1408) & Indirect Rate Auditor API",
        "method": "POST",
        "path": "/v1/audit/dcaa-accounting-sf1408",
        "rapid_host": "dcaa-pre-award-sf1408-accounting-system-auditor-api.p.rapidapi.com",
        "payload": {
            "chart_of_accounts_and_pools_text": (
                "General Ledger & Chart of Accounts: 5000-series Direct Costs (5100 Direct Labor, 5200 Subcontractors, 5300 ODCs/Travel); "
                "6000-series Fringe Pool (Payroll Taxes, 401k Match, Health Insurance, PTO — allocated on Total Labor Dollars at 29.5%); "
                "7000-series Engineering Overhead Pool (Indirect Technical Labor, Engineering Facilities, Cloud Dev Tools — allocated on Direct Labor + Direct Fringe at 24.0%); "
                "8000-series G&A Pool (Executive, Accounting, Legal, BD, B&P — allocated on Total Cost Input [TCI] at 11.8%); "
                "9000-series Unallowable Costs (9100 Interest, 9200 Entertainment, 9300 Non-Compliant Advertising). "
                "Timekeeping: Daily web timesheets with charge-code authorization, employee + supervisor electronic signoff, and audit trail."
            ),
            "target_contract_type_and_solicitation": "Cost_Plus_Fixed_Fee_CPFF_And_T_And_M",
            "accounting_software_and_erp_stack": "QuickBooks_Online_With_GovCon_Timekeeping",
        },
    },
    {
        "id": "API 29",
        "name": "DoD Other Transaction Authority (OTA / 10 U.S.C. 4022) Prototype White Paper API",
        "method": "POST",
        "path": "/v1/generate/ota-white-paper",
        "rapid_host": "dod-ota-10-usc-4022-prototype-white-paper-api.p.rapidapi.com",
        "payload": {
            "commercial_solution_and_problem_topic_text": (
                "DIU Commercial Solutions Opening (CSO) Topic: Autonomous Counter-UAS & Contested Logistics RF Situational Awareness. "
                "DoD Problem: Forward operating bases require a low-SWaP, passive RF and electro-optical sensor fusion node capable of "
                "detecting Group 1-3 autonomous drones in GPS-denied environments without emitting targetable radar signatures. "
                "Vendor Commercial Solution: AegisRF Commercial Edge v3.4 (currently TRL 6, deployed across 14 commercial airports and critical "
                "energy substations, $18M Series A funded). Uses passive time-difference-of-arrival (TDOA) SDR arrays and quantized neural edge "
                "inference on NVIDIA Jetson Orin Industrial to classify 400+ RF protocols in < 120ms."
            ),
            "target_ota_consortium_and_pathway": "DIU_Commercial_Solutions_Opening_CSO",
            "nontraditional_contractor_and_cost_share_status": "Nontraditional_Defense_Contractor_NDC_Zero_Cost_Share",
        },
    },
    {
        "id": "API 30",
        "name": "DCSA Facility Clearance (FCL), DD Form 254 & FOCI Mitigation Analyzer API",
        "method": "POST",
        "path": "/v1/audit/foci-dd254-clearance",
        "rapid_host": "dcsa-fcl-dd254-foci-sf328-clearance-auditor-api.p.rapidapi.com",
        "payload": {
            "dd254_and_ownership_cap_table_text": (
                "DD Form 254 Block 6/7: Top Secret Facility Clearance Required; Safeguarding Level: Secret. "
                "Block 10 Checked: (a) COMSEC, (e)(1) SCI, (j) CUI, (k) SIPRNet. Block 11 Checked: (a) Access only at Government/Other Cleared Facility, "
                "(c) Receive/Generate Classified Technical Data, (j) Operations Security (OPSEC) & NIST SP 800-171 SPRS >= 110. "
                "Corporate Cap Table & SF 328 Context: Delaware C-Corp (82% U.S. citizen founders; 14% held via Cayman Islands LP feeder in Series B VC fund; "
                "4% held by UK/NATO strategic minority investor with 1 non-voting board observer seat; zero foreign debt)."
            ),
            "target_facility_clearance_level": "Top_Secret_FCL_With_SCI_And_SIPRNet",
            "foreign_ownership_and_board_context": "Minority_Foreign_LP_Or_Board_Seat_Under_Review",
        },
    },
    {
        "id": "API 31",
        "name": "FAR 52.219-9 Subcontracting Plan & eSRS Goal Calculator API",
        "method": "POST",
        "path": "/v1/generate/small-business-participation",
        "rapid_host": "far-52-219-9-subcontracting-plan-esrs-calculator-api.p.rapidapi.com",
        "payload": {
            "solicitation_subcontracting_and_clin_text": (
                "Total 5-Year IDIQ Task Order Ceiling: $50,000,000 (Base Year $10M + Four 1-Year Options at $10M/yr). "
                "Total Planned Subcontracted Spend: $20,000,000 (40.0% of Total Contract Value). "
                "Section M Small Business Participation Factor requires >= 25% of Total Contract Value ($12.5M) or >= 62.5% of Total Subcontracted Spend "
                "awarded to Small Businesses, including SDB/8(a) Cyber Sentinel LLC (NAICS 541512, $3.5M), SDVOSB Valor Cloud Solutions (NAICS 541519, $3.0M), "
                "WOSB Athena Analytics Inc. (NAICS 541511, $2.5M), and HUBZone Appalachian DevSecOps Corp (NAICS 541512, $1.5M)."
            ),
            "plan_type_and_regulatory_regime": "Individual_Subcontracting_Plan_FAR_52_219_9_And_DFARS_252_219_7003",
            "agency_socioeconomic_goal_benchmarks": "DoD_23Pct_SB_5Pct_SDB_5Pct_WOSB_5Pct_SDVOSB_3Pct_HUBZone",
        },
    },
    {
        "id": "API 32",
        "name": "FAR 52.227-14 & DFARS 252.227-7013/7014 IP & Technical Data Rights API",
        "method": "POST",
        "path": "/v1/generate/data-rights-assertion-table",
        "rapid_host": "dfars-252-227-7013-7014-7017-data-rights-assertion-api.p.rapidapi.com",
        "payload": {
            "software_modules_and_cdrl_deliverables_text": (
                "1. SentinelCore Zero-Trust Inference Engine & Pre-Trained Weights v4.2: Developed 100% at private expense (2022-2025 IR&D GL Account #8410) prior to solicitation; delivered as compiled container image under CDRL A004. "
                "2. Tactical RF Sensor Ingestion Firmware: Developed under DoD SBIR Phase II Contract FA8650-24-C-1102; delivered under CDRL A005. "
                "3. Mission Adapter Microservice & REST/gRPC Interface Control Document (ICD): Developed with mixed/contract funding under CLIN 0002; delivered under CDRL A002 (ICD) and CDRL A006 (Adapter Source)."
            ),
            "governing_acquisition_regime": "DoD_DFARS_252_227_7013_7014_7015_7017_And_7018",
            "modular_open_systems_approach_mosa_context": "MOSA_Open_API_Boundary_Preserving_Proprietary_Core_Algorithms",
        },
    },
    {
        "id": "API 33",
        "name": "GovCon Black-Hat Competitive Intelligence, Incumbent Vulnerability & Ghosting API",
        "method": "POST",
        "path": "/v1/generate/capture-black-hat-review",
        "rapid_host": "govcon-shipley-black-hat-incumbent-ghosting-api.p.rapidapi.com",
        "payload": {
            "solicitation_and_incumbent_context_text": (
                "Target Recompete: DoD C5ISR Enterprise Cloud & 24x7 Cyber SOC Operations ($85M 5-Year Single-Award Task Order). "
                "Section M Evaluation: Best-Value Tradeoff (Factor 1 Technical Approach [Most Important] > Factor 2 Management & Transition > Factor 3 Past Performance > Price). "
                "Incumbent: LegacyDefense Corp (held contract for 5 years; known pain points include 18% annual SOC analyst turnover, delayed RMF cATO pipeline, and high 2.15x Tier-1 wrap rate). "
                "Other Likely Bidders: BeltwayScale SI (aggressive price cutter using junior LCATs)."
            ),
            "bidder_discriminators_and_proof_points": "Cleared_Automation_First_Team_With_Zero_Trust_cATO_And_Lower_Wrap_Rate",
            "evaluation_type_and_posture": "Challenger_Unseating_Incumbent_Best_Value_Tradeoff",
        },
    },
    {
        "id": "API 34",
        "name": "GovCon CPARS Self-Assessment, Interim Evaluation & 14-Day Rebuttal API",
        "method": "POST",
        "path": "/v1/generate/post-award-cpar-rebuttal",
        "rapid_host": "govcon-cpars-self-assessment-14-day-rebuttal-api.p.rapidapi.com",
        "payload": {
            "contract_metrics_and_assessing_official_text": (
                "Contract W52P1J-24-F-0188 (Period of Performance: Oct 1, 2025 – Sep 30, 2026). "
                "Contractor Metrics: 99.97% Cloud Enclave Uptime (PWS SLA >= 99.5%); 48 of 48 CDRLs delivered on or ahead of schedule (100% first-time COR acceptance); "
                "automated DevSecOps pipeline cut vulnerability remediation time by 64% saving 3,200 Government labor hours; Cost Variance: 2.8% under CPFF ceiling ($410K underrun returned); "
                "Small Business Subcontracting: achieved 28.4% SB vs. 23.0% goal. "
                "Draft AO Narrative Issue: AO assigned 'Satisfactory' across Quality and Schedule, citing a 3-week Milestone 2 delay that was caused by Government GFE SIPRNet circuit provisioning delay documented in COR Email 2026-03-14."
            ),
            "cpar_submission_mode": "Proactive_Annual_CPARS_Self_Assessment_And_14_Day_Rebuttal_Package",
            "target_far_42_1503_rating_goal": "Upgrade_To_Exceptional_And_Very_Good_With_Positive_Rec",
        },
    },
    {
        "id": "API 35",
        "name": "GovCon Request for Equitable Adjustment (REA), Constructive Change & CDA Claim API",
        "method": "POST",
        "path": "/v1/generate/rea-equitable-adjustment",
        "rapid_host": "govcon-rea-constructive-change-cda-claim-api.p.rapidapi.com",
        "payload": {
            "contract_change_and_delay_facts": (
                "CONTRACT: FA8726-25-C-0089 (USAF Tactical Zero-Trust Cloud Migration, FFP + T&M CLINs, $14.2M Ceiling). "
                "EVENT 1 (GFE DELAY): Government failed to deliver 12 Accredited Cross-Domain Guard appliances by Nov 1, 2025 "
                "per Section H.8; actual delivery occurred Jan 14, 2026 (74-day Government-caused delay), forcing 6 cleared "
                "engineers into standby/workaround re-sequencing (1,480 direct labor hours, $142,080 unabsorbed direct labor). "
                "EVENT 2 (CONSTRUCTIVE CHANGE): On Dec 3, 2025, COR directed via Technical Direction Email #19 that contractor "
                "integrate an out-of-scope legacy mainframe COBOL feed not listed in PWS Section 3.2 (2,120 additional engineering hours)."
            ),
            "remedy_clause_and_submission_type": "FAR_52_243_Changes_Clause_REA_Pre_Claim_Negotiation",
            "quantum_pricing_methodology": "Standard_DCAA_Fringe_Overhead_GA_Plus_Weighted_Guidelines_Profit",
        },
    },
    {
        "id": "API 36",
        "name": "SBA Mentor-Protégé (13 CFR 125.9) & Joint Venture Operating Agreement Compliance API",
        "method": "POST",
        "path": "/v1/generate/mentor-protege-jv-agreement",
        "rapid_host": "sba-mentor-protege-13-cfr-125-8-joint-venture-api.p.rapidapi.com",
        "payload": {
            "mentor_and_protege_profile_text": (
                "TARGET SOLICITATION: W52P1J-26-R-0074 (U.S. Army ACC-Rock Island Enterprise Cyber SOC & Zero-Trust Engineering, "
                "$45M Total Small Business / SDVOSB Set-Aside, NAICS 541512, $34M Size Standard). "
                "UNPOPULATED JV NAME: Aegis-Vanguard Cyber JV LLC. "
                "MANAGING VENTURER (PROTEGE): Vanguard Defense Cyber LLC (Verified SDVOSB & SBA Small Business, UEI: VGD991827361, "
                "51% Ownership, provides full-time Employed Responsible Manager Marcus Vance, PMP/CISSP, performs 44% of total JV labor hours). "
                "PARTNER VENTURER (MENTOR): Aegis Global Federal Corp (Large Business, SBA Approved Mentor-Protege Agreement #MPA-2025-8841, "
                "49% Ownership, performs 56% of total JV labor hours)."
            ),
            "target_set_aside_and_jv_type": "SBA_All_Small_Mentor_Protege_JV_13_CFR_125_8_And_125_9",
            "agreement_deliverable_scope": "Unpopulated_LLC_40Pct_Protege_Workshare_Floor",
        },
    },
    {
        "id": "API 37",
        "name": "Service Contract Act (SCA / FAR 52.222-41) & Davis-Bacon Wage Determination Mapper API",
        "method": "POST",
        "path": "/v1/audit/service-contract-act-wage",
        "rapid_host": "govcon-sca-far-52-222-41-wage-determination-mapper-api.p.rapidapi.com",
        "payload": {
            "rfp_labor_categories_and_locality_text": (
                "SOLICITATION: 47QTCK-26-R-0055 (Federal Enterprise Service Desk, Network Operations & Records Administration, "
                "Place of Performance: Arlington, VA / Washington-Arlington-Alexandria DC-VA-MD-WV Locality, WD 2015-4281 Rev 28). "
                "PROPOSED LCATS & BASE RATES: (1) Tier 1 IT Service Desk Specialist (12 FTEs, Proposed Base Wage: $24.10/hr, "
                "Proposed Health & Welfare: $4.98/hr); (2) Tier 2 Systems & Network Support Technician (8 FTEs, Proposed Base Wage: $31.50/hr); "
                "(3) Technical Documentation & CDRL Specialist (3 FTEs, Proposed Base Wage: $33.25/hr); "
                "(4) Senior Zero-Trust Cloud Architect (4 FTEs, Salaried FLSA Exempt $168,000/yr)."
            ),
            "wage_determination_and_fringe_mode": "McNamara_OHara_Service_Contract_Act_SCA_FAR_52_222_41",
            "audit_objective": "EO_13706_Paid_Sick_Leave_H_And_W_ Plus_FAR_52_222_43_Price_Adjustment",
        },
    },
    {
        "id": "API 38",
        "name": "GovCon Earned Value Management System (EVMS / EIA-748) & IPMDR Variance Narrative API",
        "method": "POST",
        "path": "/v1/generate/evms-ipmdr-variance-analysis",
        "rapid_host": "govcon-evms-ansi-748-ipmdr-variance-narrative-api.p.rapidapi.com",
        "payload": {
            "wbs_control_account_metrics_text": (
                "CONTRACT: N00024-25-C-5410 (U.S. Navy Combat System Cloud & Sensor Fusion Modernization, CPFF, DFARS 252.234-7002 EVMS Required). "
                "PROGRAM BUDGET AT COMPLETION (BAC): $24,500,000. REPORTING PERIOD: October 2026. "
                "WBS 1.2 (Zero-Trust Tactical Edge K8s Platform): BCWS = $4,200,000; BCWP = $3,780,000; ACWP = $4,150,000; WBS BAC = $8,500,000 "
                "(Root Cause: 4-week shortage of FPGA/GPU crypto acceleration cards required temporary senior firmware re-engineering). "
                "WBS 1.3 (DevSecOps Automated RMF Pipeline): BCWS = $2,800,000; BCWP = $2,940,000; ACWP = $2,710,000; WBS BAC = $5,500,000. "
                "WBS 1.4 (System Integration & Test Lab): BCWS = $1,900,000; BCWP = $1,710,000; ACWP = $1,995,000; WBS BAC = $4,800,000."
            ),
            "variance_reporting_thresholds": "DFARS_252_234_7002_EIA_748_32_Guidelines_And_DID_DI_MGMT_81861C_IPMDR",
            "evms_reporting_standard": "Composite_CPI_Times_SPI_Weighted_And_Bottom_Up_ETC",
        },
    },
    {
        "id": "API 39",
        "name": "Cost Accounting Standards (CAS / 48 CFR 9904) Coverage & DS-1 Disclosure Auditor API",
        "method": "POST",
        "path": "/v1/generate/cost-accounting-cas-ds2",
        "rapid_host": "govcon-cas-48-cfr-9904-ds1-ds2-disclosure-auditor-api.p.rapidapi.com",
        "payload": {
            "contractor_accounting_and_awards_profile": (
                "TARGET AWARD: $38.5M Negotiated DoD CPFF Engineering Contract (Non-Commercial, Certified Cost or Pricing Data required under FAR 15.403-4). "
                "BUSINESS UNIT PRIOR YEAR CAS-COVERED AWARDS: $56.2M in net CAS-covered awards during prior cost accounting period (including one $12M CAS-covered task order). "
                "BUSINESS UNIT STATUS: Commercial & Defense Systems Segment (currently transitioning from Modified CAS to Full CAS >= $50M threshold). "
                "ACCOUNTING PRACTICES: Direct Labor charged via daily project timecards; Fringe Benefits (30.8%) pooled and allocated on Total Labor Dollars; "
                "Engineering Overhead (24.5%) allocated on Direct Labor + Direct Fringe; G&A (11.2%) allocated on Total Cost Input (TCI). "
                "PLANNED ACCOUNTING CHANGE: Effective Jan 1, 2027, contractor proposes to move Cloud SecOps DevSecOps Tooling ($620K/yr) from G&A Pool to Engineering Overhead Pool."
            ),
            "target_cas_coverage_and_ds_form": "CAS_Coverage_Determination_And_DS1_Eight_Part_Audit",
            "g_and_a_allocation_base_preference": "FAR_52_230_6_Cost_Impact_And_Desirable_Change_Analysis",
        },
    },
    {
        "id": "API 40",
        "name": 'ITAR (22 CFR 120–130), EAR & Technology Control Plan (TCP) Export Compliance API',
        "method": "POST",
        "path": '/v1/audit/itar-ear-export-control',
        "rapid_host": "itar-22-cfr-120-130-ear-tcp-export-compliance-api.p.rapidapi.com",
        "payload": {
            'technical_deliverables_and_rfp_export_text': 'SOLICITATION W31P4Q-26-R-0118 (U.S. Army Aviation & Missile Command — Multi-Spectral EO/IR Counter-UAS Seeker & Fire-Control Firmware): Section C.3 Deliverables: (1) Real-time FPGA infrared target-tracking and seeker guidance firmware source code; (2) Ruggedized commercial-off-the-shelf (COTS) Linux mission processor board with AES-256 cryptographic bus; (3) Field Maintenance Technical Manuals (TM) and ICDs delivered to NATO coalition partners under Foreign Military Sales (FMS). Includes DFARS 252.225-7048 (Export-Controlled Items) and DoDI 5230.24 Distribution Statement D.',
            'target_export_regime': 'ITAR_22_CFR_120_130_And_EAR_15_CFR_730_774_Dual_Audit',
            'foreign_national_and_oconus_context': 'U.S. Persons Only on ITAR USML Technical Data; Evaluate Deemed Export Rule (22 CFR 120.50 / 15 CFR 734.13)',
        },
    },
    {
        "id": "API 41",
        "name": 'DoD CDRL (DD Form 1423) & Data Item Description (DID) Schedule Extractor API',
        "method": "POST",
        "path": '/v1/generate/cdrls-did-data-deliverables',
        "rapid_host": "dod-cdrl-dd-form-1423-did-schedule-extractor-api.p.rapidapi.com",
        "payload": {
            'rfp_exhibit_a_cdrl_and_pws_text': 'EXHIBIT A — CONTRACT DATA REQUIREMENTS LIST (DD FORM 1423-1): CDRL A001: Program Management Plan (PMP), Authority: DI-MGMT-80004A, PWS Para 3.1, Freq: ONE/R, First Sub: 30 DAC, Dist: Statement D, Block 18: NSP. CDRL A002: Monthly Contract Status Report (MSR), Authority: DI-MGMT-80368A, PWS Para 3.2, Freq: MTHLY, Sub: 10th business day, Inspection/Acceptance: DD (Destination/Destination). CDRL A003: Software Product Specification (SPS) & Source Code Baseline, Authority: DI-IPSC-81441A, PWS Para 4.4, Freq: ASREQ/R, Sub: 15 days prior to FCA/PCA. CDRL A004: System Security Plan (SSP) & RMF Continuous Monitoring Package, Authority: DI-MGMT-82001, PWS Para 5.1, Freq: QTRLY, Sub: 45 DAC.',
            'contract_award_and_pop_start_context': 'Contract Award / Post-Award Conference (PAC) = Day 0; 12-Month Base Period + 4 Option Years',
            'dd1423_pricing_group_strategy': 'Map DD Form 1423 Block 18 Price Groups (Group I, II, III, IV — NSP vs. Separately Priced Data CLIN)',
        },
    },
    {
        "id": "API 42",
        "name": 'FAR 6.302 / FAR 8.405-6 Sole-Source Justification & Approval (J&A / LSJ) Drafter API',
        "method": "POST",
        "path": '/v1/generate/justification-ja-sole-source',
        "rapid_host": "far-6-302-8-405-6-sole-source-j-and-a-lsj-drafter-api.p.rapidapi.com",
        "payload": {
            'sole_source_requirement_and_vendor_uniqueness_text': 'REQUIREMENT: Bridge & Follow-On Sole-Source Modification for USAF Tactical C2 Cloud Mesh & Proprietary Cross-Domain Guard (36 Months, $18.5M). Proposed Contractor: Aegis Tactical Cyber LLC (SBA Certified 8(a) / SDVOSB, CAGE 9K4L2). Uniqueness Rationale: Aegis developed the NSA NCDSMO-accredited Cross-Domain Solution (CDS) FPGA filter and Zero-Trust tactical mesh under SBIR Phase II FA8750-24-C-0091. Transitioning to another vendor would require an 18-to-24 month NSA recertification delay and $11.4M in duplicative non-recurring engineering (NRE) that cannot be recovered through competition.',
            'statutory_authority_pathway': 'FAR_6_302_1_Only_One_Responsible_Source_10_USC_3204_a_1',
            'estimated_dollar_value_and_approval_tier': '$18.5M Total Estimated Value — Competition Advocate Approval Tier ($750K to $15M / $20M DoD PEO/HCA Threshold)',
        },
    },
    {
        "id": "API 43",
        "name": 'DFARS 252.204-7012 (72-Hour DIBNet) & CIRCIA Cyber Incident Reporting Package API',
        "method": "POST",
        "path": '/v1/audit/cyber-incident-dfars-7012',
        "rapid_host": "dfars-252-204-7012-72-hour-dibnet-circia-incident-api.p.rapidapi.com",
        "payload": {
            'security_incident_telemetry_and_affected_contracts_text': "INCIDENT SUMMARY (Discovered 2026-10-30 08:15 UTC): SOC EDR (CrowdStrike Falcon GovCloud) detected unauthorized credential-stuffing and anomalous SMB lateral movement on Engineering File Server 'ENG-CUI-SRV04' hosting Controlled Technical Information (CTI / CUI) for US Navy Contract N00024-25-C-5411 (CAGE 7V8N1, Top Secret FCL). Host isolated within 14 minutes; 380 MB encrypted archivestaged in temp directory prior to containment. Subcontractor 'Precision Aero Engineering LLC' also accessed the shared CUI folder.",
            'regulatory_reporting_regimes': 'DFARS_252_204_7012_72Hr_DIBNet_Plus_CISA_CIRCIA_72Hr_And_FedRAMP_US_CERT',
            'assurance_certificate_and_cloud_posture': 'DoD ECA Medium Token Assurance Certificate Active; Enclave Hosted on AWS GovCloud (US) FedRAMP High / IL5',
        },
    },
    {
        "id": "API 44",
        "name": 'DOE / NNSA National Lab M&O Subcontract & DEAR (48 CFR Ch. 9) Compliance Auditor API',
        "method": "POST",
        "path": '/v1/generate/doe-national-lab-mando-subcontract',
        "rapid_host": "doe-nnsa-national-lab-mo-dear-48-cfr-ch-9-auditor-api.p.rapidapi.com",
        "payload": {
            'doe_national_lab_rfp_and_dear_clauses_text': 'SOLICITATION SNL-RFP-2026-88412 (Sandia National Laboratories / NTESS M&O Prime Contract DE-NA0003525 — High-Performance Computing AI/ML Simulation & Zero-Trust Enclave Engineering): General Terms & Conditions: Incorporates DEAR 48 CFR 952.204-2 (Security Requirements — DOE Q & L Clearances), DEAR 952.204-70 (Classification/Declassification), DEAR 970.5227-1 / 952.227-11 (Patent Rights — Retention by the Contractor), DOE Order 142.3B (Unclassified Foreign National Visits and Assignments Program), and DOE Order 205.1C (Department of Energy Cyber Security Program).',
            'target_national_lab_and_mando_prime': 'Sandia_National_Laboratories_NTESS_And_Los_Alamos_National_Lab_Triad_NNSA',
            'clearance_and_ip_posture': 'DOE Q-Clearance / L-Clearance Cross-Over from DoD TS/Secret + Domestic Small Business Patent Retention (DEAR 952.227-11)',
        },
    },
    {
        "id": "API 45",
        "name": 'GWAC / IDIQ Task Order Fair Opportunity (FAR 16.505) & Pool Selection Optimizer API',
        "method": "POST",
        "path": '/v1/generate/gwac-task-order-fair-opportunity',
        "rapid_host": "gwac-idiq-task-order-fair-opportunity-far-16-505-api.p.rapidapi.com",
        "payload": {
            'torfp_scope_and_vehicle_holders_text': 'TASK ORDER REQUEST FOR PROPOSAL (TORFP) 47QFCA-26-R-0092 (DHS CISA Continuous Threat Hunting & Cloud DevSecOps Engineering): Ceiling: $32.0M over 5 years. NAICS: 541512 ($34.0M Size Standard) / PSC D310. Bidder Vehicle Portfolio: Prime holder on GSA OASIS+ Small Business (Technical & Engineering Domain), 8(a) STARS III, GSA MAS (SIN 54151HACS / 54151S), and Army ITES-3S. Response Deadline: 7 calendar days; maximum 12-page Technical Volume + 2-page Staffing Plan.',
            'target_gwac_or_mac_vehicles': 'GSA_OASIS_Plus_Unrestricted_And_SB_GSA_Polaris_8a_STARS_III_VETS_2_CIO_SP3',
            'turnaround_window_and_evaluation_mode': '5-Business-Day Rapid TORFP Turnaround | FAR 16.505(b)(1) Highest Technically Rated Offeror (HTRO) / Fair Opportunity',
        },
    },
    {
        "id": "API 46",
        "name": 'Government-Furnished Property (GFP / FAR 52.245-1) & PIEE Property Management Plan API',
        "method": "POST",
        "path": '/v1/audit/govt-furnished-property-gfp',
        "rapid_host": "govcon-gfp-far-52-245-1-piee-property-management-api.p.rapidapi.com",
        "payload": {
            'gfp_attachment_and_property_clauses_text': 'RFP ATTACHMENT J-4 CONSOLIDATED GOVERNMENT-FURNISHED PROPERTY (GFP) SCHEDULE (Contract W56HZV-26-C-0084): (1) 18x KG-175D TACLANE Type-1HAIPE Encryptors (Serially Managed, Unit Acq Cost: $24,500 ea, COMSEC/CCI); (2) 45x Dell Latitude Rugged GFE Engineer Laptops (Unit Acq Cost: $3,800 ea, Non-Serially Managed); (3) 2x Environmental Thermal Shock Chambers (Special Test Equipment [STE], Unit Acq Cost: $142,000 ea); (4) 400x Titanium Sensor Housings (Contractor-Acquired Property [CAP] under Cost-Reimbursable CLIN 0004). Includes FAR 52.245-1, FAR 52.245-9, DFARS 252.211-7003 (IUID), and DFARS 252.245-7005.',
            'dcma_property_system_audit_scope': 'FAR_52_245_1_10_Lifecycle_Outcomes_DFARS_252_245_7005_PIEE_GFP_Module_And_MIL_STD_130_IUID',
            'liability_and_cap_regime': 'FAR 52.245-1(h) Limited Risk of Loss (Government Self-Insures Except Willful Misconduct / Revoked PMSA)',
        },
    },
    {
        "id": "API 47",
        "name": 'DoD OCONUS / INDOPACOM Deployment, SOFA, Defense Base Act (DBA) & SPOT Compliance API',
        "method": "POST",
        "path": '/v1/generate/oconus-sofa-defense-logistics',
        "rapid_host": "dod-oconus-indopacom-sofa-defense-base-act-spot-api.p.rapidapi.com",
        "payload": {
            'oconus_pws_and_theater_clauses_text': "SOLICITATION FA5209-26-R-0038 (374th Contracting Squadron / USINDOPACOM C5ISR Network & Zero-Trust Operations): Places of Performance: Yokota AB & Kadena AB, Japan (12 FTEs); Camp Humphreys, Republic of Korea (8 FTEs); and Ramstein AB, Germany (6 FTEs). Clauses: FAR 52.228-3 (Workers' Compensation Insurance [Defense Base Act]), DFARS 252.225-7040 (Contractor Personnel Supporting U.S. Armed Forces Deployed Outside the United States), USFJ Instruction 64-100 (SOFA Article XIV Contractor Status), USFK Reg 700-19 (Invited Contractor / Technical Representative), and USEUCOM DOCPER TESA under NATO SOFA Article 72/73.",
            'target_combatant_command_and_host_nations': 'USINDOPACOM_USFJ_Japan_USFK_Korea_Guam_And_USEUCOM_Germany_DOCPER_TESA',
            'dba_and_dssr_allowance_assumptions': 'FAR 52.228-3 Defense Base Act (DBA) Insurance + DSSR Living Quarters Allowance (LQA), Post Allowance (COLA), & Danger Pay',
        },
    },
    {
        "id": "API 48",
        "name": 'Controlled Unclassified Information (CUI / 32 CFR 2002 & DoDI 5200.48) Handling Plan API',
        "method": "POST",
        "path": '/v1/generate/cui-marking-distribution-plan',
        "rapid_host": "cui-32-cfr-2002-dodi-5200-48-handling-plan-api.p.rapidapi.com",
        "payload": {
            'deliverables_and_security_classification_guide_text': 'CONTRACT DELIVERABLES REQUIRING CUI MARKING & DISTRIBUTION CONTROLS: (1) CDRL A001 Zero-Trust Cloud Network Architecture & Vulnerability Scan Report (Information Systems Vulnerability Information + Controlled Technical Information); (2) CDRL A002 ITAR/USML Seeker Firmware Interface Control Document (Export Controlled Technical Data + CTI); (3) CDRL A003 Proprietary CLIN Cost & Pricing BOE Spreadsheets (General Procurement and Acquisition + Source Selection); (4) CDRL A004 Public Release Executive Program Fact Sheet (Cleared via DoD OPSEC / Public Affairs review).',
            'cui_authority_framework': '32_CFR_Part_2002_NARA_CUI_Registry_DoDI_5200_48_And_DoDI_5230_24_Distribution_Statements',
            'controlling_dod_office_and_ldc_context': 'Controlling DoD Office: AFLCMC/HNC (Hanscom AFB, MA) | Limited Dissemination Controls: NOFORN, FEDCON, DL ONLY',
        },
    },
    {
        "id": "API 49",
        "name": 'SLED Cooperative Purchasing (NASPO ValuePoint, Sourcewell, OMNIA, TIPS & DIR) Piggyback Mapper API',
        "method": "POST",
        "path": '/v1/generate/state-local-cooperative-piggyback',
        "rapid_host": "sled-cooperative-purchasing-naspo-sourcewell-piggyback-api.p.rapidapi.com",
        "payload": {
            'sled_buyer_requirement_and_vendor_contracts_text': 'BUYER OPPORTUNITY: City of Charlotte, NC & Wake County Public School System seeking $1.85M Zero-Trust Cloud Security, SIEM Telemetry, and Managed SOC Onboarding before June 30 fiscal year-end. Vendor Contract Vehicles: Hold GSA MAS SIN 54151S & SIN 54151HACS (Cooperative Purchasing Authorized), listed on Carahsoft NASPO ValuePoint Cloud Solutions Master Agreement (AR2472 / Utah Lead State with active NC Participating Addendum), and TIPS Technology Solutions Contract #230105.',
            'target_cooperative_portfolios': 'NASPO_ValuePoint_Cloud_AR2472_Sourcewell_OMNIA_Partners_TIPS_USA_TX_DIR_And_GSA_Coop_Purchasing',
            'vendor_direct_vs_distributor_model': 'Evaluate Both Direct Master Agreement Holdership and Carahsoft / TD SYNNEX / Ingram Micro Authorized Reseller Piggyback',
        },
    },
    {
        "id": "API 50",
        "name": 'FAR Part 48 Value Engineering Change Proposal (VECP / FAR 52.248-1) & Shared-Savings Modeler API',
        "method": "POST",
        "path": '/v1/generate/value-engineering-vecp',
        "rapid_host": "far-part-48-vecp-far-52-248-1-shared-savings-modeler-api.p.rapidapi.com",
        "payload": {
            'baseline_contract_and_proposed_engineering_change_text': 'ACTIVE CONTRACT: FA8732-25-C-0044 (USAF Enterprise Cloud & Telemetry Platform, $48.0M Firm-Fixed-Price, includes FAR 52.248-1 Value Engineering). Proposed VECP-2026-01: Replace legacy x86 persistent EC2/RDS analytics clusters and manual Tier-1 log triage with Graviton4 serverless Iceberg lakehouse + automated AI SOAR playbooks. Reduces annual AWS GovCloud infrastructure and sustainment labor cost by $3,400,000/year across the remaining 2 Instant Contract Option Years ($6.8M gross instant savings) plus $4.2M across 2 Future follow-on task orders.',
            'far_part_48_sharing_regime': 'FAR_52_248_1_Voluntary_Incentive_Fixed_Price_50_50_To_75_25_Contractor_Share',
            'development_and_government_implementation_costs': 'Contractor VECP Development Cost: $320,000 | Government Test/ECP Implementation Cost: $180,000 | 36-Month Sharing Period',
        },
    },
    {
        "id": "API 51",
        "name": 'FAR 52.203-13 Business Ethics, Procurement Integrity Act & OIG Mandatory Disclosure API',
        "method": "POST",
        "path": '/v1/audit/organizational-ethics-far-52-203-13',
        "rapid_host": "far-52-203-13-business-ethics-pia-oig-disclosure-api.p.rapidapi.com",
        "payload": {
            'compliance_incident_or_former_official_hiring_text': "MATTER 1 (Labor Category Billing Audit): Internal QA review on DHS T&M Task Order 70RTAC-25-F-0041 ($14.2M) discovered that 2 Mid-Level DevSecOps Engineers lacked the BS degree required by the Senior LCAT for 6 billing periods (resulting in a $68,400 inadvertent overbilling). MATTER 2 (Post-Government Employment Hiring): Capture team wishes to hire a retiring GS-15 DoD Program Manager who served as COR on an adjacent division's contract (with a written DoD Ethics Counselor PGEL opinion).",
            'audit_focus_regime': 'FAR_52_203_13_Credible_Evidence_OIG_Disclosure_FAR_3_104_PIA_And_18_USC_207_Revolving_Door',
            'contract_value_and_performance_duration': 'Active Contract > $6.0M Threshold and > 120 Days Performance (Full FAR 52.203-13(c) Internal Control System Required)',
        },
    },
    {
        "id": "API 52",
        "name": 'DoD FedRAMP Moderate Equivalency (2024 DoD CIO Memo) & 3PAO Body of Evidence Auditor API',
        "method": "POST",
        "path": '/v1/generate/fedramp-equivalency-body-of-evidence',
        "rapid_host": "dod-fedramp-moderate-equivalency-3pao-boe-auditor-api.p.rapidapi.com",
        "payload": {
            'cloud_service_offering_and_3pao_posture_text': 'CLOUD SERVICE OFFERING (CSO): SentinelMesh SaaS Engineering Collaboration & CUI Document Vault used by a Defense Prime to store Controlled Technical Information (CTI / CUI). Current Posture: Hosted on AWS GovCloud (US-West); holds SOC 2 Type II and ISO 27001, plus an A2LA-accredited 3PAO FedRAMP Moderate Rev 5 Security Assessment Report (SAR) covering 295 of 323 controls, with 2 open Moderate POA&Ms (FIPS 140-2/3 TLS proxy validation in staging and automated 30-day vulnerability scan feed).',
            'target_equivalency_standard': 'DoD_CIO_Jan_2024_FedRAMP_Moderate_Equivalency_Memo_DFARS_252_204_7012_c_d_And_FedRAMP_Rev5',
            'underlying_iaas_and_fips_posture': 'Hosted on AWS GovCloud (US) FedRAMP High JAB P-ATO; FIPS 140-3 Validated Cryptographic Modules',
        },
    },
    {
        "id": "API 53",
        "name": 'Federal AI Governance, OMB M-24-10/M-24-18 & NIST AI RMF 1.0 Compliance Package API',
        "method": "POST",
        "path": '/v1/generate/ai-governance-nist-ai-rmf-omb-m24',
        "rapid_host": "federal-ai-governance-omb-m-24-10-nist-ai-rmf-1-0-api.p.rapidapi.com",
        "payload": {
            'proposed_ai_system_and_agency_use_case_text': "PROPOSED AI SOLUTION: 'TriageCopilot Gov' — Retrieval-Augmented Generation (RAG) LLM and multi-modal document classification engine for Veterans Benefits / DHS Case Adjudication & Cyber Threat Triage. Architecture: Hosted in isolated AWS GovCloud IL4/IL5 enclave; retrieves citations from authoritative agency manuals with mandatory Human-in-the-Loop (HITL) adjudicator sign-off before any benefit determination or network block.",
            'target_ai_governance_frameworks': 'OMB_M_24_10_OMB_M_24_18_NIST_AI_RMF_1_0_NIST_AI_600_1_GenAI_And_DoD_CDAO_RAI_Toolkit',
            'deployment_enclave_and_training_data_policy': 'Stateless RAG on Agency Tenant (Zero Training on Government CUI/PII; Open-Format Export to Prevent Vendor Lock-In)',
        },
    },
    {
        "id": "API 54",
        "name": 'FAR Part 49 Termination for Convenience (T4C / SF 1435–1438) Settlement Proposal Calculator API',
        "method": "POST",
        "path": '/v1/generate/termination-for-convenience-settlement',
        "rapid_host": "far-part-49-t4c-sf-1435-1438-settlement-calculator-api.p.rapidapi.com",
        "payload": {
            'termination_notice_and_incurred_cost_ledger_text': 'TERMINATION NOTICE: Contracting Officer issued Complete Notice of Termination for Convenience under FAR 52.249-2 on Contract W15P7T-25-C-0082 ($12.0M Ceiling, $4.1M Progress/Milestone Payments received to date). Incurred Costs to Date of Termination: Direct Labor $2,450,000; Fringe/OH/G&A Indirects $1,980,000; Raw Materials & Unfinished Work-in-Process (WIP) $620,000; Subcontractor Termination Claims (2 Subcontractors < $100K TCO delegation threshold): $385,000; Post-Termination Accounting, Legal & Plant Clearance Settlement Expenses (FAR 31.205-42(g)): $145,000. Target Profit on Work Performed: 10.0%.',
            'settlement_proposal_basis_and_form': 'SF_1435_Inventory_Basis_Preferred_Under_FAR_49_206_2_vs_SF_1436_Total_Cost_Basis',
            'contract_type_and_clause_regime': 'FAR 52.249-2 Fixed-Price Termination for Convenience (vs. FAR 52.249-6 Cost-Reimbursement / FAR 52.212-4(l) Commercial)',
        },
    },
    {
        "id": "API 55",
        "name": 'GovCon M&A Contract Novation (FAR 42.1204) & Change-of-Name Due Diligence Package API',
        "method": "POST",
        "path": '/v1/generate/novated-merger-change-of-name-far-42',
        "rapid_host": "govcon-ma-contract-novation-far-42-1204-package-api.p.rapidapi.com",
        "payload": {
            'm_and_a_transaction_and_contract_backlog_text': "TRANSACTION SUMMARY: Transferor 'CyberVanguard Federal LLC' (SDVOSB, CAGE 6M2P9, UEI M8N2K4P9Q1R7, Top Secret FCL) is selling substantially all of its Defense Cyber Division assets to Transferee 'Aegis Defense Holdings Inc.' (Mid-Tier Other-Than-Small Business, CAGE 4T9W1, UEI T4W9X1Y2Z8A3, Top Secret FCL) for $45M. Affected Backlog: (1) USAF Prime Contract FA8726-24-C-0019 ($22M Small Business Set-Aside, Cognizant ACO: DCMA Boston); (2) DISA Task Order HC1028-25-F-0112 under GSA 8(a) STARS III; (3) NAVWAR Full & Open IDIQ N00039-25-D-0041.",
            'deal_structure_and_pathway': 'Asset_Purchase_Requiring_FAR_42_1204_Three_Party_Novation_vs_Stock_Purchase_Or_FAR_42_1205_Change_Of_Name',
            'small_business_and_clearance_context': 'Audit 13 CFR 121.404(g) 30-Day SBA Size Recertification, GWAC/MAC Eligibility, & DCSA 32 CFR 117 Changed Condition Package',
        },
    },
    {
        "id": "API 56",
        "name": 'SSEB Source Selection Simulator & Shipley Pink/Red/Gold Team Proposal Scorer API',
        "method": "POST",
        "path": '/v1/generate/section-l-m-proposal-red-team-scorer',
        "rapid_host": "sseb-source-selection-simulator-shipley-proposal-scorer-api.p.rapidapi.com",
        "payload": {
            'rfp_section_l_m_and_draft_proposal_text': "RFP SECTION M EVALUATION CRITERIA (Solicitation FA8732-26-R-0077 — Best-Value Tradeoff): Factor 1: Technical & Zero-Trust Cloud Architecture (Most Important) — Subfactor 1.1 Automated IL5 DevSecOps & cATO Pipeline; Subfactor 1.2 14-Day Zero-Downtime SOC Cutover. Factor 2: Management & Key Personnel. DRAFT PROPOSAL EXCERPT (Section 2.1): 'Our team has extensive experience with AWS GovCloud and Kubernetes. We will work closely with the Government ISSM after award to develop a System Security Plan and transition the SOC within 30 to 45 days using industry best practices.'",
            'source_selection_grading_methodology': 'DoD_Source_Selection_Procedures_2022_Color_Adjectival_Blue_Purple_Green_Yellow_Red_And_FAR_15_305',
            'color_team_review_stage': 'Red_Team_Full_SSEB_Simulation_With_Paste_Ready_Feature_Benefit_Proof_Upgrades_To_Blue_Outstanding',
        },
    },
    {
        "id": "API 57",
        "name": 'GSA FAS Sales Reporting Portal (SRP), TDR Line-Item & IFF CAV/IOA Audit Reconciler API',
        "method": "POST",
        "path": '/v1/generate/gsa-tdr-quarterly-sales-iff-reconciler',
        "rapid_host": "gsa-fas-sales-reporting-portal-tdr-iff-audit-reconciler-api.p.rapidapi.com",
        "payload": {
            'quarterly_invoice_ledger_and_gsa_contract_text': "GSA MAS CONTRACT 47QTCA24D0088 (TDR Participating SINs: 54151S, 54151HACS, OLM). Quarterly Invoice Ledger: (1) INV-9001: $420,000 billed to DHS CISA under Task Order 70RTAC26F0012 (cites 47QTCA24D0088, SIN 54151HACS; includes $20,000 Open-Market Hardware marked 'Open Market FAR 8.402(f)'); (2) INV-9002: $185,000 billed to VA TAC (cites 47QTCA24D0088, SIN 54151S, Principal Cloud Architect @ $182.50/hr vs. GSA Ceiling $185.00/hr); (3) INV-9003: $95,000 Commercial Enterprise SaaS invoice to Acme Corp (Non-Government Commercial Sale).",
            'gsa_reporting_regime': 'GSAR_552_238_80_IFF_0_75_Pct_GSAR_552_238_81_TDR_16_Data_Elements_And_IOA_CAV_Readiness',
            'reporting_quarter_and_sins': 'FY2026 Q4 (July 1 – Sept 30; SRP Filing Due Oct 30) | SINs: 54151S, 54151HACS, 518210C, OLM',
        },
    },
    {
        "id": "API 58",
        "name": 'FAR Subpart 16.4 Award-Fee (CPAF) & Incentive-Fee (CPIF / FPIF) Evaluation Maximizer API',
        "method": "POST",
        "path": '/v1/generate/award-fee-plan-incentive-maximizer',
        "rapid_host": "far-subpart-16-4-award-fee-cpaf-cpif-fpif-maximizer-api.p.rapidapi.com",
        "payload": {
            'incentive_or_award_fee_plan_and_period_metrics_text': 'CONTRACT N00024-25-C-6201 (NAVSEA Combat System Software Sustainment — CPAF / CPIF Hybrid): Target Cost: $25,000,000 | Target Fee: $2,000,000 (8.0%) | Minimum Fee: $500,000 (2.0%) | Maximum Fee: $3,500,000 (14.0%) | Underrun Share Ratio: 70/30 (Govt/Contractor) | Overrun Share Ratio: 60/40 (Govt/Contractor). Award-Fee Pool ($1,250,000 Period 04): Contractor achieved 99.98% operational availability, delivered 14/14 software builds 9 days ahead of schedule, automated STIG hardening saving 4,200 engineering hours, and closed zero P1 cyber defects.',
            'contract_fee_structure_type': 'Combined_CPAF_Award_Fee_Adjectival_Table_16_1_And_CPIF_FPIF_Share_Ratio_PTA_Geometry',
            'evaluation_period_and_pool_context': 'Award-Fee Period 04 (6-Month Evaluation Pool: $1,250,000 Available Award Fee + Base Fee 2.0%)',
        },
    },
]


def run_telemetry_seeder(rotating: bool = False, slice_size: int = 4) -> None:
    print(f"=== SignalTender Multi-API Telemetry Seeder (rotating={rotating}) ===", flush=True)
    print(f"Gateway: {BASE_URL}", flush=True)

    if not PROXY_SECRET and not RAPIDAPI_KEY:
        print("[!] Neither RAPIDAPI_PROXY_SECRET nor RAPIDAPI_KEY set in environment.", flush=True)
        return

    try:
        requests.get(f"{BASE_URL}/v1/health", timeout=60)
    except Exception:
        pass

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
                resp = requests.get(url, params=ep.get("params", {}), headers=headers, timeout=90)
            else:
                resp = requests.post(url, json=ep.get("payload", {}), headers=headers, timeout=90)
            PUBLIC_MIRROR_BY_ID = {"API 21": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com", "API 22": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com", "API 23": "rfp-compliance-matrix-proposal-outline-api.p.rapidapi.com", "API 24": "soc-2-fedramp-nist-800-171-security-questionnaire-api.p.rapidapi.com", "API 25": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com", "API 26": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com", "API 27": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com", "API 28": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com", "API 29": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com", "API 30": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com", "API 31": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com", "API 32": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com", "API 33": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com", "API 34": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com", "API 35": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com", "API 36": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com", "API 37": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com", "API 38": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com", "API 39": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com", "API 40": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com", "API 41": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com", "API 42": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com", "API 43": "soc-2-fedramp-nist-800-171-security-questionnaire-api.p.rapidapi.com", "API 44": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com", "API 45": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com", "API 46": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com", "API 47": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com", "API 48": "soc-2-fedramp-nist-800-171-security-questionnaire-api.p.rapidapi.com", "API 49": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com", "API 50": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com", "API 51": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com", "API 52": "soc-2-fedramp-nist-800-171-security-questionnaire-api.p.rapidapi.com", "API 53": "soc-2-fedramp-nist-800-171-security-questionnaire-api.p.rapidapi.com", "API 54": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com", "API 55": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com", "API 56": "rfp-compliance-matrix-proposal-outline-api.p.rapidapi.com", "API 57": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com", "API 58": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com"}
            if resp.status_code in (403, 404) and RAPIDAPI_KEY:
                mhost = PUBLIC_MIRROR_BY_ID.get(ep['id'])
                if mhost and mhost != ep['rapid_host']:
                    murl = f"https://{mhost}{ep['path']}"
                    mheaders = {**headers, 'X-RapidAPI-Host': mhost}
                    if ep['method'] == 'GET':
                        resp = requests.get(murl, params=ep.get('params', {}), headers=mheaders, timeout=90)
                    else:
                        resp = requests.post(murl, json=ep.get('payload', {}), headers=mheaders, timeout=90)
            if resp.status_code in (403, 404) and RAPIDAPI_KEY and PROXY_SECRET:
                # Fallback to direct Render gateway if RapidAPI Studio route is not yet mapped
                direct_url = f"{BASE_URL}{ep['path']}"
                parts = [s.strip() for s in (PROXY_SECRET or "").split(",") if s.strip()]
                prod_parts = [s for s in parts if not s.startswith("local_")]
                chosen = prod_parts[0] if prod_parts else (parts[0] if parts else "")
                direct_headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-RapidAPI-Proxy-Secret": chosen,
                }
                if ep["method"] == "GET":
                    resp = requests.get(direct_url, params=ep.get("params", {}), headers=direct_headers, timeout=90)
                else:
                    resp = requests.post(direct_url, json=ep.get("payload", {}), headers=direct_headers, timeout=90)
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

