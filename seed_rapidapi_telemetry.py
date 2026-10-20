"""
SignalTender 10-API Telemetry & Green-Badge Seeder (seed_rapidapi_telemetry.py)
Warms and verifies all 10 production microservices across both:
  1. The unified Render FastAPI gateway (using RAPIDAPI_PROXY_SECRET from .env)
  2. All 10 RapidAPI Marketplace Proxy Hosts (if RAPIDAPI_KEY is set in .env),
     recording 200 OK responses and low-latency telemetry to unlock RapidAPI's
     9.8-10.0 Service Level badges across all 10 storefronts.
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
]


def run_telemetry_seeder() -> None:
    print(f"=== SignalTender Multi-API Telemetry Seeder ===")
    print(f"Gateway: {BASE_URL}")

    if not PROXY_SECRET and not RAPIDAPI_KEY:
        print("[!] Neither RAPIDAPI_PROXY_SECRET nor RAPIDAPI_KEY set in environment.")
        return

    passed = 0
    for ep in ENDPOINTS:
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
            print(f"[{ep['id']}] {ep['name']} -> {status_tag} ({elapsed_ms} ms)")
            if resp.status_code == 200:
                passed += 1
        except Exception as exc:
            print(f"[{ep['id']}] {ep['name']} -> ERROR: {exc}")

    print(f"\nCompleted: {passed}/{len(ENDPOINTS)} endpoints returned 200 OK.")


if __name__ == "__main__":
    run_telemetry_seeder()

