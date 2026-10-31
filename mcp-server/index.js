#!/usr/bin/env node
/**
 * SignalTender Official Model Context Protocol (MCP) Server (@signaltender/mcp-server)
 * Zero-dependency JSON-RPC 2.0 stdio server exposing the full SignalTender B2B & GovCon API catalog
 * to Claude Desktop, Cursor, Windsurf, Cline, and OpenAI/Anthropic Agent frameworks.
 *
 * Authentication via environment variables (no hardcoded keys):
 *   - RAPIDAPI_KEY: Subscriber's RapidAPI Key (from https://rapidapi.com/user/aarbchen)
 *   - RAPIDAPI_PROXY_SECRET: Optional direct gateway secret for internal CaptureDesk calls
 *   - SIGNALTENDER_API_BASE_URL: Defaults to https://b2b-contract-parser-api.onrender.com
 */

const readline = require("readline");

const BASE_URL = (
  process.env.SIGNALTENDER_API_BASE_URL ||
  "https://b2b-contract-parser-api.onrender.com"
).replace(/\/+$/, "");

const RAPIDAPI_KEY = process.env.RAPIDAPI_KEY || "";
const SIGNALTENDER_API_KEY = process.env.SIGNALTENDER_API_KEY || "";
const RAPIDAPI_PROXY_SECRET = process.env.RAPIDAPI_PROXY_SECRET || "";

const RAPIDAPI_HOSTS = {
  "parse_b2b_contract": "b2b-contract-parsing-api.p.rapidapi.com",
  "audit_contract_risks": "ai-contract-risk-redline-auditor-api.p.rapidapi.com",
  "search_historical_awards": "historical-procurement-pricing-api.p.rapidapi.com",
  "get_live_solicitations": "live-sled-federal-open-rfp-feed-api.p.rapidapi.com",
  "generate_compliance_matrix": "rfp-compliance-matrix-proposal-outline-api.p.rapidapi.com",
  "scan_far_dfars_clauses": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com",
  "match_capability_statement": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com",
  "classify_naics_psc_nigp": "naics-sic-psc-unspsc-industry-classifier-api.p.rapidapi.com",
  "generate_rfp_response": "ai-rfp-response-clarification-q-a-generator-api.p.rapidapi.com",
  "extract_pricing_schedule": "b2b-quote-invoice-clin-table-extractor-api.p.rapidapi.com",
  "generate_teaming_strategy": "govcon-teaming-partner-subcontracting-plan-api.p.rapidapi.com",
  "answer_security_questionnaire": "soc-2-fedramp-nist-800-171-security-questionnaire-api.p.rapidapi.com",
  "match_key_personnel": "govcon-key-personnel-lcat-resume-tailoring-api.p.rapidapi.com",
  "analyze_rfp_amendment_diff": "rfp-amendment-q-a-change-impact-analyzer-api.p.rapidapi.com",
  "generate_cpars_past_performance": "cpars-past-performance-volume-generator-api.p.rapidapi.com",
  "generate_igce_price_to_win": "govcon-igce-wrap-rate-price-to-win-modeler-api.p.rapidapi.com",
  "generate_oral_presentation_prep": "govcon-oral-presentation-tech-demo-murder-board-prep-api.p.rapidapi.com",
  "generate_ato_rmf_package": "govcon-rmf-continuous-ato-cato-ssp-poa-m-generator-api.p.rapidapi.com",
  "analyze_debriefing_bid_protest": "govcon-debriefing-far-15-506-gao-bid-protest-analyzer-api.p.rapidapi.com",
  "generate_gsa_mas_offer": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com",
  "generate_sources_sought_response": "govcon-sources-sought-rfi-set-aside-shaping-responder-api.p.rapidapi.com",
  "generate_oci_mitigation_plan": "govcon-oci-far-9-5-mitigation-plan-generator-api.p.rapidapi.com",
  "generate_sbir_sttr_commercialization": "sbir-sttr-phase-i-iii-commercialization-plan-api.p.rapidapi.com",
  "audit_section_508_vpat": "govcon-section-508-wcag-2-2-aa-vpat-2-5-auditor-api.p.rapidapi.com",
  "audit_supply_chain_scrm": "govcon-supply-chain-scrm-ndaa-889-taa-sbom-auditor-api.p.rapidapi.com",
  "generate_quality_assurance_qasp": "govcon-qasp-prs-sla-kpi-surveillance-matrix-api.p.rapidapi.com",
  "generate_phase_in_transition_plan": "govcon-30-60-90-day-phase-in-transition-plan-api.p.rapidapi.com",
  "audit_dcaa_accounting_sf1408": "dcaa-pre-award-sf1408-accounting-system-auditor-api.p.rapidapi.com",
  "generate_ota_white_paper": "dod-ota-10-usc-4022-prototype-white-paper-api.p.rapidapi.com",
  "audit_foci_dd254_clearance": "dcsa-fcl-dd254-foci-sf328-clearance-auditor-api.p.rapidapi.com",
  "generate_small_business_participation": "far-52-219-9-subcontracting-plan-esrs-calculator-api.p.rapidapi.com",
  "generate_data_rights_assertion_table": "dfars-252-227-7013-7014-7017-data-rights-assertion-api.p.rapidapi.com",
  "generate_capture_black_hat_review": "govcon-shipley-black-hat-incumbent-ghosting-api.p.rapidapi.com",
  "generate_post_award_cpar_rebuttal": "govcon-cpars-self-assessment-14-day-rebuttal-api.p.rapidapi.com",
  "generate_rea_equitable_adjustment": "govcon-rea-constructive-change-cda-claim-api.p.rapidapi.com",
  "generate_mentor_protege_jv_agreement": "sba-mentor-protege-13-cfr-125-8-joint-venture-api.p.rapidapi.com",
  "audit_service_contract_act_wage": "govcon-sca-far-52-222-41-wage-determination-mapper-api.p.rapidapi.com",
  "generate_evms_ipmdr_variance_analysis": "govcon-evms-ansi-748-ipmdr-variance-narrative-api.p.rapidapi.com",
  "generate_cost_accounting_cas_ds2": "govcon-cas-48-cfr-9904-ds1-ds2-disclosure-auditor-api.p.rapidapi.com",
  "audit_itar_ear_export_control": "govcon-itar-usml-ear-ccl-tcp-export-control-api.p.rapidapi.com",
  "generate_cdrls_did_data_deliverables": "dod-cdrl-dd-form-1423-did-schedule-tracker-api.p.rapidapi.com",
  "generate_justification_ja_sole_source": "far-6-302-13-501-sole-source-ja-lsj-generator-api.p.rapidapi.com",
  "audit_cyber_incident_dfars_7012": "dfars-252-204-7012-dibnet-72hr-incident-report-api.p.rapidapi.com",
  "generate_doe_national_lab_mando_subcontract": "doe-dear-48-cfr-952-970-national-lab-compliance-api.p.rapidapi.com",
  "generate_gwac_task_order_fair_opportunity": "far-16-505-oasis-polaris-sewp-task-order-shaper-api.p.rapidapi.com",
  "audit_govt_furnished_property_gfp": "far-52-245-1-dfars-piee-gfp-property-management-api.p.rapidapi.com",
  "generate_oconus_sofa_defense_logistics": "dod-oconus-sofa-dba-sync-spot-deployment-compliance-api.p.rapidapi.com",
  "generate_cui_marking_distribution_plan": "dod-32-cfr-2002-dodi-5200-48-cui-marking-plan-api.p.rapidapi.com",
  "generate_state_local_cooperative_piggyback": "naspo-sourcewell-omnia-tips-sled-coop-piggyback-api.p.rapidapi.com",
  "generate_value_engineering_vecp": "far-part-48-52-248-1-vecp-shared-savings-proposal-api.p.rapidapi.com",
  "audit_organizational_ethics_far_52_203_13": "far-52-203-13-business-ethics-oig-disclosure-auditor-api.p.rapidapi.com",
  "generate_fedramp_equivalency_body_of_evidence": "dod-fedramp-moderate-equivalency-memorandum-boe-api.p.rapidapi.com",
  "generate_ai_governance_nist_ai_rmf_omb_m24": "federal-ai-governance-omb-m-24-10-nist-ai-rmf-api.p.rapidapi.com",
  "generate_termination_for_convenience_settlement": "far-part-49-sf-1435-1436-t4c-settlement-proposal-api.p.rapidapi.com",
  "generate_novated_merger_change_of_name_far_42": "far-42-1204-govcon-m-a-novation-agreement-package-api.p.rapidapi.com",
  "generate_section_l_m_proposal_red_team_scorer": "sseb-color-team-pink-red-gold-proposal-scorer-api.p.rapidapi.com",
  "generate_gsa_tdr_quarterly_sales_iff_reconciler": "gsa-fas-srp-tdr-iff-cav-ioa-audit-reconciler-api.p.rapidapi.com",
  "generate_award_fee_plan_incentive_maximizer": "far-16-401-cpaf-cpif-award-fee-board-presentation-api.p.rapidapi.com"
};

const TOOLS = [
  {
    "name": "parse_b2b_contract",
    "title": "Parse B2B Contract & RFP Metadata",
    "description": "Extract structured contract metadata (contracting parties, effective and termination dates, total contract value, payment terms, key deliverables, security clearances, and governing law) from unstructured B2B contracts, Statements of Work (SOWs), or RFPs into normalized JSON. This is a read-only, stateless, non-destructive extraction call (requires X-RapidAPI-Key; accepts 50 to 100,000 characters in `raw_text`, and `document_type_hint` optionally biases extraction rules toward federal RFP, MSA, SOW, or NDA conventions). Use this tool when you need general commercial or header metadata from a contract; use `extract_pricing_schedule` instead for line-by-line CLIN/rate-card tables, `audit_contract_risks` for toxic clause redlining, or `generate_compliance_matrix` for Section C/L/M requirement shredding.",
    "annotations": {
      "title": "Parse B2B Contract & RFP Metadata",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "raw_text": {
          "type": "string",
          "minLength": 50,
          "maxLength": 100000,
          "description": "Raw unstructured text from a B2B contract, Master Services Agreement (MSA), Statement of Work (SOW), or Request for Proposal (RFP) between 50 and 100,000 characters."
        },
        "document_type_hint": {
          "type": "string",
          "minLength": 1,
          "maxLength": 100000,
          "description": "Optional document type hint (e.g., 'RFP', 'MSA', 'SOW')."
        }
      },
      "required": [
        "raw_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "buyer_entity": {
          "type": "string",
          "description": "The organization, government authority, or enterprise issuing the RFP, tender, or legal contract."
        },
        "vendor_requirements": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "A list of strict technical, security, licensing, or compliance qualifications required from the vendor."
        },
        "total_budget_usd": {
          "type": [
            "number",
            "null"
          ],
          "description": "The stated budget, maximum contract value, or total fee in USD. Must be None if no explicit financial figure is mentioned."
        },
        "submission_deadline": {
          "type": [
            "string",
            "null"
          ],
          "description": "The exact deadline for submission in ISO 8601 format (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SSZ'). Must be None if missing."
        },
        "is_awarded": {
          "type": "boolean",
          "description": "A boolean indicating if this document is a past award (True) or an active, open bid/solicitation (False)."
        },
        "key_deliverables": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "A list of the main project deliverables, milestones, goods, or work products required."
        }
      }
    }
  },
  {
    "name": "audit_contract_risks",
    "title": "Audit Contract Risks & Generate Legal Redlines",
    "description": "Audit commercial and B2B legal agreements (MSAs, NDAs, SaaS terms, subcontracts) to detect high-risk clauses, compute a 0-100 overall risk score, and generate verbatim clause quotes paired with ready-to-paste fallback redline language. This operation is read-only, stateless, and non-destructive (requires X-RapidAPI-Key; `raw_text` accepts 50 to 100,000 characters, and `party_perspective` shifts redline rewrites to protect the 'vendor', 'buyer', or 'neutral' counsel). Use this tool when reviewing commercial/legal terms (indemnification, liability caps, IP ownership, termination for convenience); use `scan_far_dfars_clauses` instead for federal FAR/DFARS/CMMC regulatory flow-down audits, or `parse_b2b_contract` for basic metadata extraction.",
    "annotations": {
      "title": "Audit Contract Risks & Generate Legal Redlines",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "raw_text": {
          "type": "string",
          "minLength": 50,
          "maxLength": 100000,
          "description": "Full or partial legal contract text (MSA, NDA, subcontract, or SaaS agreement) to audit for commercial, IP, indemnification, and termination risks (50 to 100,000 characters)."
        },
        "party_perspective": {
          "type": "string",
          "enum": [
            "vendor",
            "buyer",
            "neutral"
          ],
          "default": "vendor",
          "description": "Negotiating party perspective ('vendor' protects service provider liability/IP, 'buyer' strengthens customer remedies/SLAs, 'neutral' balances mutual terms)."
        },
        "focus_categories": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "maxItems": 100,
          "description": "Optional list of specific clause risk categories to prioritize during the audit."
        }
      },
      "required": [
        "raw_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "contract_type": {
          "type": "string",
          "description": "Identified legal document type (e.g., 'Master Services Agreement', 'Mutual NDA', 'Statement of Work')."
        },
        "party_perspective": {
          "type": "string",
          "description": "The negotiating perspective used to evaluate risks ('vendor', 'buyer', or 'neutral')."
        },
        "overall_risk_score": {
          "type": "integer",
          "description": "Quantified overall risk score from 0 (minimal risk) to 100 (critical/unacceptable exposure)."
        },
        "overall_risk_level": {
          "type": "string",
          "description": "Aggregate risk severity classification ('LOW', 'MEDIUM', 'HIGH', or 'CRITICAL')."
        },
        "executive_summary": {
          "type": "string",
          "description": "High-level deal-desk summary of the contract's risk posture and primary negotiation blockers."
        },
        "missing_standard_protections": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "List of standard protective clauses missing from the contract (e.g., 'No Limitation of Liability cap')."
        },
        "flagged_clauses": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Detailed list of risky clauses identified in the contract, ordered by severity."
        }
      }
    }
  },
  {
    "name": "search_historical_awards",
    "title": "Search Historical Federal Contract Awards & CLIN Pricing",
    "description": "Query historical federal contract awards, incumbent prime contractors, award ceilings, and labor/CLIN pricing benchmarks filtered by keyword, agency, or 6-digit NAICS code. This is a read-only, stateless, non-destructive database query (requires X-RapidAPI-Key; all filter parameters are optional and combinable, returning up to `limit` [default 20, max 100] matching historical awards per call). Use this tool when researching past award prices, incumbent vendors, or Price-to-Win (PTW) benchmarks; use `get_live_solicitations` instead to find currently open RFPs available for bidding, or `classify_naics_psc_nigp` if you need to discover the right NAICS code first.",
    "annotations": {
      "title": "Search Historical Federal Contract Awards & CLIN Pricing",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": true
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "keywords": {
          "type": "string",
          "minLength": 2,
          "maxLength": 200,
          "description": "Required technical or domain search keywords matched against award descriptions and CLIN titles (e.g., 'zero trust', 'cloud migration', 'SIEM')."
        },
        "agency": {
          "type": "string",
          "minLength": 1,
          "maxLength": 100000,
          "description": "Optional issuing federal or state agency name substring filter (e.g., 'Department of Defense', 'Veterans Affairs')."
        },
        "naics_code": {
          "type": "string",
          "minLength": 1,
          "maxLength": 100000,
          "description": "Optional exact 6-digit North American Industry Classification System (NAICS) code filter (e.g., '541512' for Computer Systems Design).",
          "pattern": "^[0-9]{6}$"
        },
        "min_amount_usd": {
          "type": "number",
          "minimum": 0,
          "maximum": 1000000000,
          "description": "Minimum award amount in USD."
        },
        "max_amount_usd": {
          "type": "number",
          "minimum": 0,
          "maximum": 1000000000,
          "description": "Maximum award amount in USD."
        },
        "limit": {
          "type": "integer",
          "default": 10,
          "minimum": 1.0,
          "maximum": 100.0,
          "description": "Maximum number of award records to return."
        }
      }
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "total_count": {
          "type": "integer",
          "description": "Total number of matching award records found."
        },
        "query": {
          "type": [
            "string",
            "null"
          ],
          "description": "Echoed query parameter or filter criteria."
        },
        "results": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "List of standardized award records with line items."
        }
      }
    }
  },
  {
    "name": "get_live_solicitations",
    "title": "Get Live Open Federal & State SLED RFPs",
    "description": "Retrieve currently open, AI-vetted Federal (SAM.gov) and All-50-State SLED (VA, TX, CA, FL, MD, IL, PA, OH, GA, NC, NY, MA, NJ, WA, MI, CO, AZ, MN, TN, IN, MO, WI, SC, OR, CT, UT, NV, AL, LA, KY, OK, IA, KS, AR, MS, NM, NE, ID, HI, NH, ME, RI, MT, DE, SD, ND, AK, VT, WV, WY, DemandStar) IT, Cloud, and Cybersecurity solicitations from SignalTender's 52-portal procurement database. This is a read-only, stateless, non-destructive live database query (requires X-RapidAPI-Key; all four filter parameters are optional and combinable, returning up to `limit` [default 10, max 50] active solicitations whose closing dates have not passed). Use this tool when discovering active open RFPs to bid on right now; use `search_historical_awards` instead for past awarded contracts and incumbent pricing, or `match_capability_statement` once you have selected an RFP to score Bid/No-Bid Pwin.",
    "annotations": {
      "title": "Get Live Open Federal & State SLED RFPs",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": true
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "state": {
          "type": "string",
          "enum": [
            "federal",
            "texas",
            "virginia",
            "california",
            "florida",
            "maryland",
            "illinois",
            "pennsylvania",
            "ohio",
            "georgia",
            "north_carolina",
            "new_york",
            "massachusetts",
            "new_jersey",
            "washington",
            "michigan",
            "colorado",
            "arizona",
            "minnesota",
            "tennessee",
            "indiana",
            "missouri",
            "wisconsin",
            "south_carolina",
            "oregon",
            "connecticut",
            "utah",
            "nevada",
            "alabama",
            "louisiana",
            "kentucky",
            "oklahoma",
            "iowa",
            "kansas",
            "arkansas",
            "mississippi",
            "new_mexico",
            "nebraska",
            "idaho",
            "hawaii",
            "new_hampshire",
            "maine",
            "rhode_island",
            "montana",
            "delaware",
            "south_dakota",
            "north_dakota",
            "alaska",
            "vermont",
            "west_virginia",
            "wyoming",
            "municipal"
          ],
          "description": "Filter by portal jurisdiction: 'federal', 'texas', 'virginia', 'california', 'florida', 'maryland', 'illinois', 'pennsylvania', 'ohio', 'georgia', 'north_carolina', 'new_york', 'massachusetts', 'new_jersey', 'washington', 'michigan', 'colorado', 'arizona', 'minnesota', 'tennessee', 'indiana', 'missouri', 'wisconsin', 'south_carolina', 'oregon', 'connecticut', 'utah', 'nevada', 'alabama', 'louisiana', 'kentucky', 'oklahoma', 'iowa', 'kansas', 'arkansas', 'mississippi', 'new_mexico', 'nebraska', 'idaho', 'hawaii', 'new_hampshire', 'maine', 'rhode_island', 'montana', 'delaware', 'south_dakota', 'north_dakota', 'alaska', 'vermont', 'west_virginia', 'wyoming', or 'municipal'."
        },
        "category": {
          "type": "string",
          "enum": [
            "cybersecurity",
            "cloud-infrastructure",
            "software-development",
            "network-telecom"
          ],
          "description": "Optional technology vertical filter ('cybersecurity', 'cloud-infrastructure', 'software-development', or 'network-telecom')."
        },
        "keyword": {
          "type": "string",
          "minLength": 1,
          "maxLength": 100000,
          "description": "Optional case-insensitive substring keyword matched against solicitation title and issuing buyer agency."
        },
        "closing_after": {
          "type": "string",
          "minLength": 1,
          "maxLength": 100000,
          "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
          "description": "Return only solicitations closing on or after this ISO 8601 date (YYYY-MM-DD)."
        },
        "limit": {
          "type": "integer",
          "default": 25,
          "minimum": 1,
          "maximum": 100,
          "description": "Maximum number of open solicitations to return per request (integer between 1 and 50; defaults to 10)."
        }
      }
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "total_count": {
          "type": "integer",
          "description": "Total number of matching open solicitations returned."
        },
        "portals_monitored": {
          "type": "integer",
          "description": "Number of Federal, State SLED, and Municipal procurement portals indexed."
        },
        "filters_applied": {
          "type": "object",
          "description": "Echoed query filter parameters."
        },
        "solicitations": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "List of verified open IT, cloud, software, and cybersecurity solicitations."
        }
      }
    }
  },
  {
    "name": "generate_compliance_matrix",
    "title": "Generate Shipley RFP Compliance Matrix & Proposal Outline",
    "description": "Shred unstructured RFP Section C (SOW/PWS), Section L (Instructions), and Section M (Evaluation Criteria) text into a numbered `shall`/`must` Requirements Traceability Matrix, Section L-to-M cross-reference map, and annotated Proposal Outline with page allocations. This is a read-only, stateless analysis operation (requires X-RapidAPI-Key; `raw_text` accepts 50 to 100,000 characters, and `proposal_methodology` selects 'shipley' [default Volume I-IV structure], 'federal_far' [FAR 15.3], or 'standard_b2b' outline conventions). Use this tool when shredding a base RFP into a compliance checklist and proposal outline; use `analyze_rfp_amendment_diff` instead when comparing an SF-30 amendment against a base RFP, or `generate_rfp_response` to draft the actual prose narrative for a specific section.",
    "annotations": {
      "title": "Generate Shipley RFP Compliance Matrix & Proposal Outline",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "raw_text": {
          "type": "string",
          "minLength": 50,
          "maxLength": 100000,
          "description": "Raw RFP Section C (Statement of Work / PWS), Section L (Instructions to Offerors), and/or Section M (Evaluation Factors) text (50 to 100,000 characters)."
        },
        "proposal_methodology": {
          "type": "string",
          "enum": [
            "shipley",
            "standard_b2b",
            "federal_far"
          ],
          "default": "shipley",
          "description": "Proposal structuring methodology: 'shipley' (Shipley Associates capture standard), 'standard_b2b' (commercial enterprise RFP), or 'federal_far' (strict FAR Section L/M mapping)."
        }
      },
      "required": [
        "raw_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "solicitation_title": {
          "type": "string",
          "description": "Inferred or stated title/scope of the RFP or Statement of Work."
        },
        "proposal_methodology": {
          "type": "string",
          "description": "Echoed proposal methodology applied ('shipley', 'standard_b2b', or 'federal_far')."
        },
        "total_mandatory_shall_count": {
          "type": "integer",
          "description": "Total count of mandatory ('MANDATORY_SHALL') requirements identified in the text."
        },
        "submission_format_rules": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Extracted administrative formatting, page limit, font, margin, or submission instructions that could trigger rejection if violated."
        },
        "evaluation_criteria_weights": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Extracted Section M or commercial evaluation scoring factors and relative weights."
        },
        "requirements_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Ordered list of shredded RFP requirements mapped to proposal sections and required verification evidence."
        },
        "proposal_outline": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured section-by-section proposal outline with mapped requirements, win themes, and page budgets."
        }
      }
    }
  },
  {
    "name": "scan_far_dfars_clauses",
    "title": "Scan FAR / DFARS & CMMC Regulatory Flow-Down Clauses",
    "description": "Scan solicitation Section I or subcontract flow-down text to identify every FAR (`52.2xx`) and DFARS (`252.2xx`) clause, flag mandatory subcontractor flow-downs, and score CMMC 2.0, NIST SP 800-171, and FedRAMP compliance burden. This is a read-only, stateless regulatory audit (requires X-RapidAPI-Key; `raw_text` accepts 30 to 100,000 characters, and `contractor_role` adjusts risk severity and flow-down obligations for a 'prime_contractor' [default], 'subcontractor', or 'commercial_item_vendor' under FAR Part 12). Use this tool when performing federal acquisition regulation (FAR/DFARS/CMMC) clause compliance; use `audit_contract_risks` instead for commercial MSA/NDA legal redlining, or `answer_security_questionnaire` to draft control-by-control NIST 800-171 / SOC 2 questionnaire responses.",
    "annotations": {
      "title": "Scan FAR / DFARS & CMMC Regulatory Flow-Down Clauses",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "raw_text": {
          "type": "string",
          "minLength": 30,
          "maxLength": 100000,
          "description": "Solicitation Section I, contract clause list, or subcontract agreement text containing FAR (`52.2xx`) or DFARS (`252.2xx`) citations (30 to 100,000 characters)."
        },
        "contractor_role": {
          "type": "string",
          "enum": [
            "prime_contractor",
            "subcontractor",
            "commercial_item_vendor"
          ],
          "default": "prime_contractor",
          "description": "Bidder's contracting tier: 'prime_contractor' (evaluates full agency compliance and outbound flow-down duties), 'subcontractor' (flags over-broad prime flow-downs), or 'commercial_item_vendor' (filters against FAR 52.212-5 commercial item exemptions)."
        },
        "handles_cui_or_cdi": {
          "type": "boolean",
          "default": true,
          "description": "Whether the contractor will store, process, or transmit Controlled Unclassified Information (CUI) or Covered Defense Information (CDI)."
        }
      },
      "required": [
        "raw_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "solicitation_summary": {
          "type": "string",
          "description": "Concise executive summary of the regulatory posture, agency context, and contract vehicle."
        },
        "contractor_role_evaluated": {
          "type": "string",
          "description": "The contractor role perspective used for the audit."
        },
        "overall_compliance_burden_score": {
          "type": "integer",
          "description": "Overall regulatory and cybersecurity compliance burden score from 0 (minimal commercial burden) to 100 (extreme defense/CMMC/IP burden)."
        },
        "compliance_burden_level": {
          "type": "string",
          "description": "Categorical compliance burden level (LOW, MODERATE, HIGH, EXTREME_DEFENSE_GRADE)."
        },
        "total_clauses_detected": {
          "type": "integer",
          "description": "Total number of FAR, DFARS, and agency supplement clauses identified."
        },
        "mandatory_flowdown_count": {
          "type": "integer",
          "description": "Number of detected clauses that carry mandatory subcontractor flow-down obligations."
        },
        "cyber_compliance_profile": {
          "type": "object",
          "description": "Structured CMMC 2.0, NIST SP 800-171, FedRAMP, and cyber incident reporting requirements."
        },
        "detected_clauses": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Detailed breakdown of every FAR/DFARS/supplement clause found, with severity, flow-down status, and remediation advice."
        },
        "ip_and_data_rights_warnings": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Specific warnings regarding Government Unlimited Rights, GPR, computer software rights (FAR 52.227 / DFARS 252.227), or patent traps."
        },
        "priority_compliance_actions": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Ordered checklist of immediate pre-proposal actions (e.g., SPRS score verification, CMMC assessment, IP assertion table in Section K/L)."
        }
      }
    }
  },
  {
    "name": "match_capability_statement",
    "title": "Score Bid/No-Bid Pwin & Match Capability Statement",
    "description": "Evaluate an RFP scope against a vendor's Capability Statement and past performance to compute a 0-100 Probability of Win (Pwin) score, a Gate-1 Bid/No-Bid recommendation, a technical/socioeconomic gap analysis, and a tailored executive pitch. This is a read-only, stateless capture scoring call (requires X-RapidAPI-Key; both `rfp_text` and `company_capability_statement` are required, while `target_pursuit_role` weights eligibility rules for 'prime_contractor', 'subcontractor_or_jv', or 'either_prime_or_sub' [default]). Use this tool when conducting Gate-1 capture qualification to decide whether to bid an opportunity; use `generate_teaming_strategy` instead if you already decided to bid and need a 13 CFR 125.6 (50% Rule) Prime/Sub workshare plan, or `match_key_personnel` to evaluate individual candidate resumes.",
    "annotations": {
      "title": "Score Bid/No-Bid Pwin & Match Capability Statement",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "rfp_text": {
          "type": "string",
          "minLength": 40,
          "maxLength": 100000,
          "description": "Target solicitation scope, mandatory technical qualifications, NAICS/set-aside designation, clearance requirements, and Section M evaluation criteria."
        },
        "company_capability_statement": {
          "type": "string",
          "minLength": 40,
          "maxLength": 100000,
          "description": "Vendor capability statement including core competencies, socioeconomic certifications (8(a), SDVOSB, WOSB, HUBZone), facility clearances, and past performance summary."
        },
        "target_pursuit_role": {
          "type": "string",
          "enum": [
            "prime_contractor",
            "subcontractor_or_jv",
            "either_prime_or_sub"
          ],
          "default": "either_prime_or_sub",
          "description": "Preferred pursuit posture to evaluate: 'prime_contractor', 'subcontractor_or_jv', or 'either_prime_or_sub'."
        }
      },
      "required": [
        "rfp_text",
        "company_capability_statement"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "solicitation_title": {
          "type": "string",
          "description": "Identified or inferred title and agency of the solicitation."
        },
        "pwin_score": {
          "type": "integer",
          "description": "Estimated Probability of Win (Pwin) score from 0 (disqualified / no fit) to 100 (ideal prime fit)."
        },
        "bid_recommendation": {
          "type": "string",
          "description": "Executive gate decision: STRONG_BID, CONDITIONAL_BID_TEAMING_REQUIRED, HIGH_RISK_STRETCH_BID, or NO_BID."
        },
        "recommended_pursuit_role": {
          "type": "string",
          "description": "Optimal pursuit structure (e.g., 'Prime Contractor', 'Prime with Teaming Subcontractor for Top Secret FCL', 'Subcontractor to Large Prime')."
        },
        "score_breakdown": {
          "type": "object",
          "description": "Granular 0-100 scoring across technical fit, past performance, clearances/certifications, and set-aside/vehicle eligibility."
        },
        "hard_disqualifiers_detected": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Mandatory knockout blockers detected (e.g., missing Top Secret FCL, ineligible socioeconomic status, missing required contract vehicle)."
        },
        "key_discriminators": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "High-impact competitive strengths from the vendor profile to highlight as Shipley win themes."
        },
        "requirement_gap_analysis": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Requirement-by-requirement alignment matrix with matched vendor evidence and gap remediation actions."
        },
        "teaming_and_subcontracting_strategy": {
          "type": "string",
          "description": "Concrete recommendation on how to structure the capture team, JV, or subcontractor roster to maximize Pwin."
        },
        "tailored_executive_summary_pitch": {
          "type": "string",
          "description": "Ready-to-paste, persuasive Shipley Executive Summary / Sources Sought pitch paragraph tailored to the buyer agency using the vendor's exact past performance."
        }
      }
    }
  },
  {
    "name": "classify_naics_psc_nigp",
    "title": "Classify NAICS, SIC, Federal PSC & State NIGP/UNSPSC Codes",
    "description": "Map any company profile, product description, or Statement of Work (SOW) into ranked 6-digit NAICS codes (with official SBA Small Business Size Standards in revenue or headcount), 4-digit SIC codes, 4-character Federal PSC codes, and State NIGP/UNSPSC commodity codes. This is a read-only, stateless taxonomy classification call (requires X-RapidAPI-Key; `description_text` is required, `context_type` tunes code selection for vendor KYB profiles vs. RFP scopes, and `max_secondary_codes` [1-5, default 3] controls how many secondary NAICS/PSC alternatives are returned alongside the primary code). Use this tool whenever you need industry, procurement, or KYB taxonomy codes and SBA small-business size caps; use `search_historical_awards` instead to query past contract awards once you have a NAICS code, or `parse_b2b_contract` to extract contract dates and dollar values.",
    "annotations": {
      "title": "Classify NAICS, SIC, Federal PSC & State NIGP/UNSPSC Codes",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "description_text": {
          "type": "string",
          "minLength": 20,
          "maxLength": 50000,
          "description": "Unstructured text describing a company's offerings, a B2B product catalog, or a government RFP/SOW technical scope (20 to 50,000 characters)."
        },
        "context_type": {
          "type": "string",
          "enum": [
            "company_or_vendor_profile",
            "rfp_or_sow_scope",
            "product_or_line_item"
          ],
          "default": "company_or_vendor_profile",
          "description": "Classification context: 'company_or_vendor_profile', 'rfp_or_sow_scope', or 'product_or_line_item'."
        },
        "max_secondary_codes": {
          "type": "integer",
          "default": 3,
          "minimum": 1.0,
          "maximum": 5.0,
          "description": "Maximum number of secondary/alternative NAICS, PSC, and NIGP codes to return in addition to the top-ranked primary code (integer 1 to 5; defaults to 3)."
        }
      },
      "required": [
        "description_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "entity_or_offering_summary": {
          "type": "string",
          "description": "Concise 1-sentence executive summary of the company, SOW, or product analyzed."
        },
        "primary_industry_sector": {
          "type": "string",
          "description": "2-digit NAICS sector code and name (e.g., '54 - Professional, Scientific, and Technical Services')."
        },
        "primary_naics": {
          "type": "object",
          "description": "Highest-confidence primary 6-digit NAICS code and SBA Small Business Size Standard."
        },
        "secondary_naics_codes": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Additional relevant 6-digit NAICS codes for SAM.gov registration and secondary capabilities."
        },
        "sic_codes": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "4-digit Standard Industrial Classification (SIC) codes for FinTech KYB, banking underwriting, and corporate filings."
        },
        "federal_psc_codes": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "4-character Federal Product Service Codes (PSC) for SAM.gov saved searches and FPDS award tracking."
        },
        "state_unspsc_and_nigp_codes": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "8-digit UNSPSC and 5-digit NIGP Class-Item codes for State/Municipal SLED vendor portals and ERP catalogs."
        },
        "kyb_and_procurement_notes": {
          "type": "string",
          "description": "Actionable guidance covering SAM.gov NAICS/PSC profile setup, SBA small-business size standard nuances (e.g., 150-employee IT Value Added Reseller footnote under 541519), SLED NIGP registration, and KYB risk classification."
        }
      }
    }
  },
  {
    "name": "generate_rfp_response",
    "title": "Draft Shipley Proposal Section & Vendor Clarification Q&A",
    "description": "Draft an evaluator-ready Shipley proposal narrative (complete with Win Themes, Feature-Benefit-Proof blocks, and Risk Mitigations) AND a list of strategic Contracting Officer Clarification Q&A questions from an RFP section and company capabilities. This is a read-only, stateless composite generation call that always returns both the drafted narrative and the clarification questions in a single JSON payload (requires X-RapidAPI-Key; `target_section_type` selects the proposal section format, and `tone_and_methodology` customizes the writing style). Use this tool when writing Technical Approach, Executive Summary, or Management Plan prose; use `generate_compliance_matrix` instead to build a requirement checklist/outline first, or `generate_cpars_past_performance` for structured Volume III CPARS contract citations.",
    "annotations": {
      "title": "Draft Shipley Proposal Section & Vendor Clarification Q&A",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "rfp_section_text": {
          "type": "string",
          "minLength": 30,
          "maxLength": 80000,
          "description": "Verbatim RFP Section C/PWS technical requirements, Section L instructions, or Section M evaluation criteria that the drafted proposal section must satisfy."
        },
        "company_context_and_capabilities": {
          "type": "string",
          "minLength": 30,
          "maxLength": 80000,
          "description": "Bidder's technical architecture, past performance metrics, SLAs, certifications, and competitive discriminators to weave into the narrative."
        },
        "target_section_type": {
          "type": "string",
          "enum": [
            "technical_approach",
            "executive_summary",
            "management_and_staffing_plan",
            "past_performance_narrative",
            "transition_and_quality_control"
          ],
          "default": "technical_approach",
          "description": "Type of proposal section to draft: 'technical_approach', 'executive_summary', 'management_and_staffing_plan', 'past_performance_narrative', or 'transition_and_quality_control'."
        },
        "tone_and_methodology": {
          "type": "string",
          "default": "Shipley Proposal Methodology (Active Voice, Evaluator-First, Feature-Benefit-Proof)",
          "minLength": 1,
          "maxLength": 100000,
          "description": "Editorial voice and methodology instruction applied to the prose draft (defaults to 'Shipley Proposal Methodology (Active Voice, Evaluator-First, Feature-Benefit-Proof)')."
        }
      },
      "required": [
        "rfp_section_text",
        "company_context_and_capabilities"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "section_title": {
          "type": "string",
          "description": "Evaluator-focused title for the drafted proposal section."
        },
        "executive_theme_statement": {
          "type": "string",
          "description": "Overarching Shipley win-theme thesis statement for the entire proposal section."
        },
        "estimated_word_count": {
          "type": "integer",
          "description": "Total word count of the drafted narrative across all subsections."
        },
        "compliance_coverage_score": {
          "type": "integer",
          "description": "Percentage (0-100) of input RFP requirements explicitly addressed in the drafted response."
        },
        "drafted_subsections": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Complete, multi-subsection Shipley proposal draft ready to paste into Word or proposal automation software."
        },
        "feature_benefit_proof_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured Feature-Benefit-Proof & competitive ghosting table for evaluator skimming."
        },
        "strategic_clarification_questions": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Formal Contracting Officer (KO) Q&A questions designed to neutralize competitor-wired specs and clarify scope risks."
        },
        "red_team_evaluator_critique": {
          "type": "string",
          "description": "Internal Red Team review note highlighting strengths of the draft and any remaining proof-point placeholders to verify before final submission."
        }
      }
    }
  },
  {
    "name": "extract_pricing_schedule",
    "title": "Extract Section B CLIN Pricing Tables, Quotes & Labor Rate Cards",
    "description": "Extract multi-tier CLIN/SLIN pricing schedules, GSA/T&M labor rate cards, vendor quotes, and Bill of Materials (BOM) tables from unstructured text into normalized JSON with automated line-item math auditing. This is a read-only, stateless extraction call (requires X-RapidAPI-Key; `document_text` accepts 20 to 100,000 characters, `expected_document_type` optionally hints the table schema, and `audit_math_and_anomalies` [default true] verifies `quantity * unit_price == extended_price` and flags arithmetic discrepancies). Use this tool when parsing pricing tables, CLIN schedules, invoices, or labor rate cards; use `parse_b2b_contract` instead for general contract dates/parties/deliverables, or `search_historical_awards` to look up historical government award prices.",
    "annotations": {
      "title": "Extract Section B CLIN Pricing Tables, Quotes & Labor Rate Cards",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "document_text": {
          "type": "string",
          "minLength": 20,
          "maxLength": 100000,
          "description": "Raw text or copied table content from a Federal Section B CLIN schedule, T&M labor rate card, B2B vendor quote, BOM, or invoice (20 to 100,000 characters)."
        },
        "expected_document_type": {
          "type": "string",
          "enum": [
            "federal_section_b_clin_schedule",
            "vendor_quote",
            "commercial_invoice",
            "labor_rate_card_tm",
            "bill_of_materials_bom",
            "purchase_order"
          ],
          "default": "federal_section_b_clin_schedule",
          "description": "Primary document type hint: 'federal_section_b_clin_schedule', 'vendor_quote', 'commercial_invoice', 'labor_rate_card_tm', 'bill_of_materials_bom', or 'purchase_order'."
        },
        "audit_math_and_anomalies": {
          "type": "boolean",
          "default": true,
          "description": "When true (default), cross-checks each line item (`quantity * unit_price == total_price`) and subtotal summation, returning any arithmetic mismatches in `math_discrepancies`."
        }
      },
      "required": [
        "document_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "document_title_or_reference": {
          "type": "string",
          "description": "Extracted solicitation number, quote ID, invoice number, or contract title."
        },
        "detected_document_type": {
          "type": "string",
          "description": "Classified pricing document type."
        },
        "dominant_pricing_model": {
          "type": "string",
          "description": "Overall contract pricing structure (e.g., 'HYBRID_MIXED', 'FIRM_FIXED_PRICE_FFP', 'TIME_AND_MATERIALS_TM')."
        },
        "vendor_or_issuer_name": {
          "type": [
            "string",
            "null"
          ],
          "description": "Vendor, prime contractor, or quote issuer name if present in the text."
        },
        "customer_or_agency_name": {
          "type": [
            "string",
            "null"
          ],
          "description": "Buyer organization, government agency, or bill-to entity if present in the text."
        },
        "currency_code": {
          "type": "string",
          "description": "ISO 4217 3-letter currency code (defaults to 'USD')."
        },
        "base_period_total_usd": {
          "type": "number",
          "description": "Sum of all Base Period / Year 1 / Initial Term line items in USD."
        },
        "options_total_usd": {
          "type": "number",
          "description": "Sum of all Option Year / Renewal Tier line items in USD (0.0 if no option periods exist)."
        },
        "total_evaluated_contract_value_usd": {
          "type": "number",
          "description": "Grand total contract ceiling or quote value across Base + All Option Periods in USD."
        },
        "payment_terms_and_invoicing_rules": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Extracted payment terms (e.g., 'Net 30', 'WAWF/IPP electronic invoicing', 'Milestone billing schedule', 'Annual upfront')."
        },
        "period_subtotals": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Subtotal breakdown grouped by contract performance period or billing tier."
        },
        "line_items": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Normalized array of all extracted CLINs, SLINs, labor rate rows, and BOM SKUs."
        },
        "math_and_pricing_anomalies": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Arithmetic discrepancies (Quantity * Unit Price != Stated Total), missing NTE ceilings, or escalation anomalies."
        },
        "finops_and_price_to_win_summary": {
          "type": "string",
          "description": "Executive FinOps & Price-to-Win (PTW) analysis summarizing blended labor rates, annual escalation percentages, discount depth, and negotiation leverage."
        }
      }
    }
  },
  {
    "name": "generate_teaming_strategy",
    "title": "Generate 13 CFR 125.6 (50% Rule) Teaming & Subcontracting Plan",
    "description": "Generate a legally compliant GovCon Teaming Strategy, a 13 CFR 125.6 & FAR 52.219-14 (Limitations on Subcontracting / 50% Rule) Prime/Sub workshare split, Ostensible Subcontractor risk audit, partner archetypes, FAR Subpart 9.6 Teaming Agreement clauses, and a BD outreach email. This is a read-only, stateless compliance and strategy generator (requires X-RapidAPI-Key; `set_aside_type` enforces SBA workshare ceilings for 'sdvosb' [default], '8a', 'wosb_edwosb', 'hubzone', 'small_business', or 'full_and_open', while `bidder_role` tailors outputs for 'prime_seeking_subs' [default], 'sub_seeking_prime', or 'joint_venture_mentor_protege'). Use this tool when structuring Prime/Sub workshare splits or recruiting teaming partners to fill capability gaps; use `match_capability_statement` instead for an initial single-vendor Bid/No-Bid Pwin score.",
    "annotations": {
      "title": "Generate 13 CFR 125.6 (50% Rule) Teaming & Subcontracting Plan",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "rfp_text": {
          "type": "string",
          "minLength": 40,
          "maxLength": 100000,
          "description": "Raw RFP scope, PWS task areas, contract ceiling, security clearance requirements, and FAR 52.219-14 / set-aside instructions."
        },
        "bidder_capabilities": {
          "type": "string",
          "minLength": 30,
          "maxLength": 100000,
          "description": "Bidder's socioeconomic status, self-performed technical domains, clearance level, and past performance strengths."
        },
        "set_aside_type": {
          "type": "string",
          "enum": [
            "full_and_open",
            "small_business",
            "sdvosb",
            "8a",
            "wosb_edwosb",
            "hubzone"
          ],
          "default": "sdvosb",
          "description": "Solicitation set-aside designation ('sdvosb' [default], '8a', 'wosb_edwosb', 'hubzone', 'small_business', or 'full_and_open') used to enforce 13 CFR 125.6 similarly situated entity and 50% self-performance rules."
        },
        "bidder_role": {
          "type": "string",
          "enum": [
            "prime_seeking_subs",
            "sub_seeking_prime",
            "joint_venture_mentor_protege"
          ],
          "default": "prime_seeking_subs",
          "description": "Bidder's teaming posture: 'prime_seeking_subs' (default, allocates >=50% to Prime and defines sub gap archetypes), 'sub_seeking_prime' (positions bidder for 20-49% specialty workshare), or 'joint_venture_mentor_protege' (13 CFR 125.8 JV compliance)."
        }
      },
      "required": [
        "rfp_text",
        "bidder_capabilities"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "solicitation_title": {
          "type": "string",
          "description": "Inferred solicitation title, agency, and set-aside designation."
        },
        "recommended_teaming_structure": {
          "type": "string",
          "description": "High-level recommended teaming architecture (e.g., 'SDVOSB Prime (58% Workshare) + 1 Similarly Situated SDVOSB Sub (22%) + 1 Large Business Niche Sub (20%)')."
        },
        "executive_teaming_rationale": {
          "type": "string",
          "description": "Strategic Shipley capture rationale explaining how this teaming structure maximizes Pwin while maintaining strict SBA/FAR compliance."
        },
        "limitations_on_subcontracting_audit": {
          "type": "object",
          "description": "Automated audit of the workshare split under 13 CFR \u00a7 125.6 and FAR 52.219-14 (50% Rule & Ostensible Subcontractor test)."
        },
        "capability_gaps_and_partner_archetypes": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Itemized capability gaps identified in the RFP and the exact partner profiles needed to close them."
        },
        "teaming_agreement_clauses": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Ready-to-paste FAR Subpart 9.6 Teaming Agreement clauses (Exhibit A Workshare, Exclusivity, Pass-Through Subcontract Conversion)."
        },
        "partner_outreach_email_template": {
          "type": "string",
          "description": "Ready-to-send Business Development outreach email to recruit the target Prime or Subcontractor partner."
        }
      }
    }
  },
  {
    "name": "answer_security_questionnaire",
    "title": "Respond to SOC 2, FedRAMP, NIST 800-171 & CMMC Security Questionnaires",
    "description": "Draft audit-ready responses to vendor security questionnaires (SOC 2, ISO 27001, FedRAMP Moderate/High, NIST SP 800-171 Rev 2/3, CMMC 2.0, CAIQ/SIG/HECVAT) with cross-framework control citations, an estimated DoD SPRS score (-203 to 110), required evidence artifacts, and POA&M remediation items for any control gaps. This is a read-only, stateless advisory responder (requires X-RapidAPI-Key; maps each question in `questionnaire_text` against the vendor's `security_posture_summary`, while `target_framework` selects 'auto_detect' [default] or locks control citations to a specific standard and flags any unsupported controls as 'Partially Met' or 'POA&M Required' rather than fabricating compliance). Use this tool when completing customer due-diligence questionnaires, SSP control tables, or DoD SPRS self-assessments; use `scan_far_dfars_clauses` instead to audit FAR/DFARS solicitation clauses, or `generate_compliance_matrix` for general RFP Section C/L/M requirements.",
    "annotations": {
      "title": "Respond to SOC 2, FedRAMP, NIST 800-171 & CMMC Security Questionnaires",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "questionnaire_text": {
          "type": "string",
          "minLength": 20,
          "maxLength": 100000,
          "description": "Numbered or bulleted security questionnaire items from an enterprise SIG/CAIQ/HECVAT sheet, customer infosec assessment, or Federal RFP / NIST 800-171 SSP checklist."
        },
        "security_posture_summary": {
          "type": "string",
          "minLength": 20,
          "maxLength": 100000,
          "description": "Required summary of the vendor's actual security stack, cloud hosting (e.g., AWS GovCloud), active certifications (SOC 2 Type II, ISO 27001, FedRAMP), encryption (FIPS 140-3, AES-256), MFA/IAM, and SIEM logging."
        },
        "target_framework": {
          "type": "string",
          "enum": [
            "auto_detect",
            "soc2_iso27001",
            "nist_800_171_cmmc",
            "fedramp_800_53",
            "caiq_sig_hecvat"
          ],
          "default": "auto_detect",
          "description": "Compliance control mapping mode: 'auto_detect' (default, infers framework from questionnaire text), 'soc2_iso27001' (AICPA TSC & ISO 27001 Annex A), 'nist_800_171_cmmc' (110 CMMC 2.0 Level 2 controls + DoD SPRS score calculation), 'fedramp_800_53' (NIST SP 800-53 Rev 5), or 'caiq_sig_hecvat'."
        }
      },
      "required": [
        "questionnaire_text",
        "security_posture_summary"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "questionnaire_title": {
          "type": "string",
          "description": "Inferred security questionnaire title, buyer domain, and compliance scope."
        },
        "overall_readiness_score": {
          "type": "integer",
          "description": "Overall security questionnaire readiness score (0-100) based on control alignment."
        },
        "executive_compliance_attestation": {
          "type": "string",
          "description": "Executive CISO attestation paragraph summarizing the vendor's security architecture, certifications, and shared-responsibility model."
        },
        "sprs_and_framework_summary": {
          "type": "object",
          "description": "Summary of detected frameworks, estimated DoD SPRS / GRC maturity impact, and control counts."
        },
        "question_responses": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Question-by-question auditor-ready responses with cross-framework control citations and evidence artifacts."
        },
        "poam_and_remediation_items": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Actionable Plan of Action & Milestones (POA&M) items or continuous improvement recommendations for any partial or open controls."
        }
      }
    }
  },
  {
    "name": "match_key_personnel",
    "title": "Audit Key Personnel LCAT Qualifications & Tailor Shipley Resume + LOC",
    "description": "Evaluate a candidate's resume against RFP Section L/M Key Personnel and GSA MAS / OASIS+ / Alliant 3 Labor Category (LCAT) requirements (years of experience, education, security clearance, DoD 8570/8140 certifications), rewrite relevant roles into a Shipley Key Personnel bio, and generate a ready-to-sign Letter of Commitment (LOC). This is a read-only, stateless qualification audit and resume formatter that does not store candidate PII (requires X-RapidAPI-Key; `allow_education_experience_substitution` [default true] applies standard federal GSA/OPM equivalency rules such as Bachelor's + 4 years = Master's when scoring eligibility). Use this tool when qualifying and formatting individual Key Personnel resumes for a proposal; use `match_capability_statement` instead to score overall company-level Bid/No-Bid Pwin, or `generate_cpars_past_performance` for company-level contract citations.",
    "annotations": {
      "title": "Audit Key Personnel LCAT Qualifications & Tailor Shipley Resume + LOC",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "lcat_or_rfp_requirements": {
          "type": "string",
          "minLength": 30,
          "maxLength": 80000,
          "description": "Raw RFP Section L/M Key Personnel instructions, GSA MAS / GWAC Labor Category (LCAT) minimum qualifications, required security clearance, and mandatory DoD 8570/8140 certifications."
        },
        "candidate_resume_text": {
          "type": "string",
          "minLength": 40,
          "maxLength": 100000,
          "description": "Candidate's unstructured resume or CV including education degrees, active security clearances, professional certifications (CISSP, PMP, AWS, etc.), and chronological work history."
        },
        "allow_education_experience_substitution": {
          "type": "boolean",
          "default": true,
          "description": "When true (default), applies standard federal GSA/OPM degree-for-experience substitution rules (e.g., Bachelor's + 4 additional years of specialized experience satisfies a Master's requirement) unless the RFP text explicitly prohibits substitutions."
        }
      },
      "required": [
        "lcat_or_rfp_requirements",
        "candidate_resume_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "target_lcat_title": {
          "type": "string",
          "description": "Normalized Labor Category (LCAT) and Key Personnel role title extracted from the solicitation."
        },
        "overall_qualification_score": {
          "type": "integer",
          "description": "Quantitative Key Personnel & LCAT qualification score (0-100)."
        },
        "qualification_verdict": {
          "type": "string",
          "description": "Audit verdict: 'FULLY_QUALIFIED_COMPLIANT', 'QUALIFIED_VIA_SUBSTITUTION', 'WAIVER_OR_CERT_PENDING', or 'DISQUALIFIED_HARD_KNOCKOUT'."
        },
        "lcat_compliance_audit": {
          "type": "object",
          "description": "Granular verification of years of experience, degree equivalency, security clearance, and DoD 8570/8140 certifications."
        },
        "requirement_by_requirement_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Line-by-line compliance checklist mapping each RFP Key Personnel mandate to candidate resume evidence."
        },
        "tailored_shipley_resume_profile": {
          "type": "object",
          "description": "Proposal-ready Shipley Key Personnel bio, rewritten past-performance bullets, and ready-to-sign Letter of Commitment (LOC)."
        }
      }
    }
  },
  {
    "name": "analyze_rfp_amendment_diff",
    "title": "Diff SF-30 RFP Amendments & Q&A Logs Against Base Solicitation",
    "description": "Diff base RFP/SOW text against subsequent SF-30 Solicitation Amendments, SLED Addenda, and official Government Q&A logs to flag altered `shall`/`must` mandates, deadline extensions, page-limit revisions, CLIN pricing changes, de-facto Q&A requirements, and invalidated proposal sections with Shipley redraft language. This is a read-only, stateless change-impact analysis call (requires X-RapidAPI-Key; `base_solicitation_text` and `amendment_or_qa_text` accept up to 100,000 characters each, and providing optional `current_proposal_outline` enables targeted auditing of which specific drafted proposal volumes/pages are invalidated). Use this tool whenever an agency issues an SF-30 amendment, addendum, or Q&A response matrix after initial RFP release; use `generate_compliance_matrix` instead when shredding an initial base RFP for the first time.",
    "annotations": {
      "title": "Diff SF-30 RFP Amendments & Q&A Logs Against Base Solicitation",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "base_solicitation_text": {
          "type": "string",
          "minLength": 40,
          "maxLength": 100000,
          "description": "Original base RFP text from Section B (CLINs), Section C/PWS (Statement of Work), Section L (Instructions/Deadlines/Page Limits), or Section M (Evaluation Criteria)."
        },
        "amendment_or_qa_text": {
          "type": "string",
          "minLength": 40,
          "maxLength": 100000,
          "description": "Subsequent SF-30 Amendment text, state/local SLED Addendum text, or official Contracting Officer Q&A clarification matrix to diff against the base solicitation."
        },
        "current_proposal_outline": {
          "type": "string",
          "default": "Volume I: Technical Approach & Architecture; Volume II: Management & Key Personnel Staffing; Volume III: Past Performance; Volume IV: CLIN Pricing & Basis of Estimate (BOE)",
          "minLength": 1,
          "maxLength": 50000,
          "description": "Optional summary of the bidder's in-progress proposal outline, volume page allocations, or technical baseline used to pinpoint exact sections that must be rewritten."
        }
      },
      "required": [
        "base_solicitation_text",
        "amendment_or_qa_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "amendment_impact_summary": {
          "type": "object",
          "description": "Executive roll-up of amendment severity, rework risk score, deadline shifts, and mandatory SF-30 acknowledgment rules."
        },
        "requirement_and_clin_deltas": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Ordered list of material requirement, CLIN pricing, page limit, evaluation criteria, and deadline changes."
        },
        "qa_clarification_rulings": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured breakdown of Government Q&A answers, flagging hidden de-facto requirements and competitive impacts."
        },
        "invalidated_proposal_sections": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Bidder proposal sections invalidated by the amendment, paired with ready-to-paste replacement narrative."
        }
      }
    }
  },
  {
    "name": "generate_cpars_past_performance",
    "title": "Generate Shipley Volume III Past Performance & CPARS Citations",
    "description": "Transform unstructured project histories, prior contract summaries, and CPARS excerpts into Shipley Section L/M Past Performance Volume III citations with predicted DoD Source Selection Relevance ('Very Relevant' to 'Not Relevant') and Performance Confidence ratings, Scope/Magnitude/Complexity matrices, FAR 42.1503 5-Factor CPARS narratives, and Context-Challenge-Action-Result (CCAR) blocks. This is a read-only, stateless generative evaluation call where relevance/confidence ratings are model-inferred against Section M criteria (requires X-RapidAPI-Key; `rfp_section_l_m_requirements` and `project_history_text` accept up to 100,000 characters, and optional `bidder_role_and_context` calibrates Prime vs. Subcontractor/JV attribution and page budgets). Use this tool when building Volume III Past Performance contract citations and CPARS questionnaires; use `generate_rfp_response` instead for Volume I Technical Approach prose, or `match_key_personnel` for individual staff resumes.",
    "annotations": {
      "title": "Generate Shipley Volume III Past Performance & CPARS Citations",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "rfp_section_l_m_requirements": {
          "type": "string",
          "minLength": 40,
          "maxLength": 100000,
          "description": "Target RFP Section L (Volume III Past Performance instructions, recency window, minimum annual/total dollar value, max citations), Section M (relevance evaluation criteria), and Section C/PWS core task areas."
        },
        "project_history_text": {
          "type": "string",
          "minLength": 40,
          "maxLength": 100000,
          "description": "Unstructured prior contract summaries, internal project delivery notes, or official CPARS evaluation excerpts (contract numbers, agencies, dollar values, FTEs, KPIs, and technical accomplishments)."
        },
        "bidder_role_and_context": {
          "type": "string",
          "default": "Prime Offeror submitting 3 Past Performance citations (2 Prime contracts + 1 Major Subcontractor contract) for a Federal / DoD best-value trade-off solicitation.",
          "minLength": 1,
          "maxLength": 20000,
          "description": "Optional pursuit context specifying Prime vs. Subcontractor citation mix, Joint Venture / SBA Mentor-Protege structure (13 CFR 125.8), or Volume III page-limit constraints."
        }
      },
      "required": [
        "rfp_section_l_m_requirements",
        "project_history_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "volume_summary": {
          "type": "object",
          "description": "Executive Past Performance Volume III summary, DoD Confidence rating prediction, and ready-to-paste Volume Introduction."
        },
        "past_performance_citations": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "List of Shipley-formatted Past Performance citations with Relevance ratings, Scope/Magnitude/Complexity matrices, and CPARS narratives."
        },
        "relevance_gaps_and_mitigations": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Evaluator risk audit of potential Relevance gaps paired with FAR 15.305(a)(2) mitigation language."
        },
        "ppq_and_cor_interview_prep_checklist": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Actionable checklist for preparing Past Performance Questionnaires (PPQs) and briefing Contracting Officer Representatives (CORs) before government reference checks."
        }
      }
    }
  },
  {
    "name": "generate_igce_price_to_win",
    "title": "Build GovCon IGCE, Indirect Wrap-Rate & Price-to-Win (PTW) Model",
    "description": "Model an Independent Government Cost Estimate (IGCE), compounded Indirect Wrap-Rate breakdown (Fringe, Overhead, G&A, and Fee/Profit), GSA CALC+ aligned LCAT rate card, multi-year Section B CLIN pricing schedule, 4-scenario Price-to-Win (PTW) sensitivity matrix, and Shipley Volume IV Basis of Estimate (BOE) narrative from RFP Section B/SOW text. This is a read-only, stateless financial modeling and estimation call (requires X-RapidAPI-Key; `rfp_section_b_and_sow_text` accepts 30 to 120,000 characters, optional `historical_benchmark_and_incumbent_context` and `bidder_indirect_wrap_assumptions` anchor indirect multipliers and incumbent baselines, and `evaluation_methodology` calibrates FAR 15.101-1 Best-Value Tradeoff vs. LPTA or FAR 15.404-1(d) Cost Realism). Use this tool when building forward-looking Volume IV Price/Cost models, wrap-rate build-ups, and Price-to-Win targets; use `search_historical_awards` instead to query past FPDS/SAM award records, or `extract_pricing_schedule` to parse an existing vendor quote or invoice table.",
    "annotations": {
      "title": "Build GovCon IGCE, Indirect Wrap-Rate & Price-to-Win (PTW) Model",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "rfp_section_b_and_sow_text": {
          "type": "string",
          "minLength": 30,
          "maxLength": 120000,
          "description": "Raw RFP Section B (Supplies or Services and Prices/Costs), PWS/SOW level-of-effort & LCAT staffing requirements, contract type (FFP, T&M, Labor-Hour, CPFF), Period of Performance (Base + Option Years), and Place of Performance (Contractor-site vs. Government-site)."
        },
        "historical_benchmark_and_incumbent_context": {
          "type": "string",
          "minLength": 1,
          "maxLength": 60000,
          "description": "Optional incumbent contract value, FPDS/USAspending historical award benchmarks, GSA MAS SIN 54151S CALC+ ceiling rates, or known agency budget ceilings to anchor the IGCE and Price-to-Win model."
        },
        "bidder_indirect_wrap_assumptions": {
          "type": "string",
          "minLength": 1,
          "maxLength": 25000,
          "description": "Optional bidder indirect rate assumptions (Fringe %, Overhead %, G&A %, Target Fee/Profit %, annual productive hours per FTE such as 1,880 or 1,920, and annual Option Year escalation %)."
        },
        "evaluation_methodology": {
          "type": "string",
          "enum": [
            "BEST_VALUE_TRADEOFF",
            "LPTA_LOWEST_PRICE_TECHNICALLY_ACCEPTABLE",
            "HIGHEST_TECHNICALLY_RATED_FAIR_REASONABLE_PRICE",
            "COST_REALISM_CPFF"
          ],
          "default": "BEST_VALUE_TRADEOFF",
          "description": "Source selection evaluation methodology: 'BEST_VALUE_TRADEOFF' (FAR 15.101-1), 'LPTA_LOWEST_PRICE_TECHNICALLY_ACCEPTABLE' (FAR 15.101-2), 'HIGHEST_TECHNICALLY_RATED_FAIR_REASONABLE_PRICE', or 'COST_REALISM_CPFF' (FAR 15.404-1(d))."
        }
      },
      "required": [
        "rfp_section_b_and_sow_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "solicitation_pricing_overview": {
          "type": "string",
          "description": "Executive summary of contract structure, total FTEs, Period of Performance, and pricing strategy."
        },
        "recommended_price_to_win_usd": {
          "type": "number",
          "description": "Recommended total evaluated Price-to-Win ($ USD) across Base + all Option Years."
        },
        "independent_government_cost_estimate_igce_usd": {
          "type": "number",
          "description": "Estimated Independent Government Cost Estimate (IGCE) baseline ($ USD) across the full PoP."
        },
        "ptw_discount_vs_igce_pct": {
          "type": "number",
          "description": "Percentage difference between recommended Price-to-Win and the estimated IGCE (e.g., -6.4 represents a 6.4% discount below IGCE)."
        },
        "cost_realism_and_price_reasonableness_posture": {
          "type": "string",
          "description": "FAR 15.404-1 Price Reasonableness & Cost Realism risk classification."
        },
        "wrap_rate_calculator_breakdown": {
          "type": "object",
          "description": "Compounded Fringe, Overhead, G&A, and Fee wrap-rate breakdown."
        },
        "lcat_rate_card_and_fte_buildup": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Bottom-up LCAT staffing, unburdened direct wage, burdened bill rate, and GSA CALC+ benchmark table."
        },
        "clin_period_of_performance_schedule": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Section B CLIN pricing schedule across Base Year and Option Years."
        },
        "ptw_sensitivity_scenarios": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Competitive Price-to-Win sensitivity matrix (Aggressive Floor, Recommended Target PTW, Incumbent Benchmark, IGCE Ceiling)."
        },
        "section_b_cost_narrative_and_boe_summary": {
          "type": "string",
          "description": "Ready-to-paste Shipley Volume IV Price/Cost Narrative and Basis of Estimate (BOE) justification."
        }
      }
    }
  },
  {
    "name": "generate_oral_presentation_prep",
    "title": "Build GovCon Oral Presentation Deck, Live Tech-Demo Runbook & Murder-Board Q&A",
    "description": "Generate a FAR 15.102 & Shipley Phase-II Oral Presentation slide-by-slide blueprint, Key Personnel speaker-attributed talking points, a minute-by-minute Live Technical Demonstration / Scenario Challenge runbook with zero-downtime failover contingencies, an adversarial SSEB 'Murder Board' Q&A coaching matrix, and evaluator caucus takeaways from RFP Section L/M oral instructions. This is a read-only, stateless generative preparation call (requires X-RapidAPI-Key; `rfp_oral_instructions_and_sow_text` accepts 30 to 120,000 characters, `proposed_solution_and_key_personnel` maps slides strictly to eligible Key Personnel speakers, optional `known_incumbent_and_risk_areas` sharpens Murder-Board trap questions, and `presentation_format_mode` selects 'COMBINED_ORALS_TECH_DEMO_AND_QA' [default], 'EXECUTIVE_SLIDE_BRIEFING_AND_QA', 'LIVE_TECHNICAL_SCENARIO_CHALLENGE', or 'KEY_PERSONNEL_INTERVIEW_AND_CAUCUS'). Use this tool when preparing for Phase-II advisory down-select oral presentations, live technical demonstrations, or SSEB Q&A caucuses; use `generate_rfp_response` instead for written Volume I Technical Approach prose, or `match_key_personnel` for written Volume II resumes and Letters of Commitment.",
    "annotations": {
      "title": "Build GovCon Oral Presentation Deck, Live Tech-Demo Runbook & Murder-Board Q&A",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "rfp_oral_instructions_and_sow_text": {
          "type": "string",
          "minLength": 30,
          "maxLength": 120000,
          "description": "Raw RFP Section L Oral Presentation / Live Tech-Demo rules (time limits, slide limits, speaker eligibility restrictions under FAR 15.102, live scenario prompts), Section M evaluation criteria, and PWS/SOW technical scope (30 to 120,000 characters)."
        },
        "bidder_solution_and_key_personnel_context": {
          "type": "string",
          "minLength": 20,
          "maxLength": 100000,
          "description": "Proposed Key Personnel names/roles/clearances, technical architecture, past performance metrics, and competitive win themes to weave into the speaker scripts and Murder-Board Q&A answers."
        },
        "presentation_format": {
          "type": "string",
          "enum": [
            "far_15_102_oral_technical_proposal",
            "live_technical_demo_and_coding_challenge",
            "executive_key_personnel_orals_and_qna",
            "sled_finalist_vendor_interview"
          ],
          "default": "far_15_102_oral_technical_proposal",
          "description": "Oral evaluation format: 'far_15_102_oral_technical_proposal' (default Federal FAR 15.102 / GSA FEDSIM Phase II Orals), 'live_technical_demo_and_coding_challenge' (hands-on tech demo & scenario execution), 'executive_key_personnel_orals_and_qna' (Key Personnel oral defense), or 'sled_finalist_vendor_interview' (State/Local BAFO interview)."
        },
        "total_session_minutes": {
          "type": "integer",
          "default": 90,
          "minimum": 15.0,
          "maximum": 240.0,
          "description": "Total scheduled duration of the oral presentation, live demo, and Q&A session in minutes (15 to 240; defaults to 90)."
        }
      },
      "required": [
        "rfp_oral_instructions_and_sow_text",
        "bidder_solution_and_key_personnel_context"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "solicitation_and_format_summary": {
          "type": "string",
          "description": "Identified solicitation title/ID, oral format, speaker restrictions, and Section M evaluation hierarchy."
        },
        "recommended_time_budget_breakdown": {
          "type": "string",
          "description": "Minute-by-minute time allocation across Opening/Intros, Core Technical Slides, Live Demo, Caucus Buffer, and Q&A."
        },
        "key_personnel_speaker_choreography": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Rules of engagement and handoff choreography ensuring every Key Personnel speaker demonstrates deep technical mastery without talking over teammates."
        },
        "slide_deck_blueprint": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Slide-by-slide Shipley oral presentation blueprint with action captions, speaker assignments, visual concepts, and verbatim scripts."
        },
        "live_tech_demo_runbook": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Step-by-step live technical demonstration runbook with operator actions, evaluator strength callouts, and offline failover contingencies."
        },
        "murder_board_qna_bank": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Adversarial SSEB Murder-Board questions with hidden evaluator concerns, responder roles, gold-standard answers, and traps to avoid."
        },
        "closing_evaluator_leave_behind_pitch": {
          "type": "string",
          "description": "Final 60-second executive closing statement designed to anchor 'High Confidence / Multiple Significant Strengths' before the SSEB caucuses."
        }
      }
    }
  },
  {
    "name": "generate_ato_rmf_package",
    "title": "Generate GovCon RMF, Continuous ATO (cATO), SSP & POA&M Package",
    "description": "Transform RFP cybersecurity clauses, system architecture descriptions, and cloud hosting baselines into a NIST SP 800-53 Rev 5 / DoDI 8510.01 RMF / FedRAMP / StateRAMP Authority to Operate (ATO & Continuous ATO) package with FIPS 199 / CNSSI 1253 security categorization, System Security Plan (SSP) control inheritance matrices, eMASS/CSAM-ready Plan of Action & Milestones (POA&M) schedules, Continuous Monitoring (ConMon) DevSecOps blueprints, and Shipley proposal narratives. This is a read-only, stateless generative authorization modeling call (requires X-RapidAPI-Key; `system_architecture_and_rfp_cyber_text` accepts 40 to 100,000 characters, `cloud_hosting_and_inherited_controls_context` accepts 20 to 80,000 characters, and `target_authorization_framework` and `target_impact_level` calibrate control baselines across DoD RMF IL2-IL6, FedRAMP, StateRAMP, and CMMC 2.0). Use this tool when building System Security Plans (SSPs), eMASS POA&M items, FIPS 199 categorizations, or cATO roadmaps for an ATO boundary; use `answer_security_questionnaire` instead to answer vendor security questionnaires and calculate a numeric DoD SPRS score (-203 to 110), or `scan_far_dfars_clauses` to audit FAR/DFARS solicitation clauses.",
    "annotations": {
      "title": "Generate GovCon RMF, Continuous ATO (cATO), SSP & POA&M Package",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "rfp_security_and_ato_requirements": {
          "type": "string",
          "minLength": 20,
          "maxLength": 100000,
          "description": "Raw text from RFP Section C/H/L/M detailing ATO, RMF (eMASS/Xacta), FedRAMP, StateRAMP, DISA Impact Level (IL4/IL5), NIST SP 800-53 Rev 5, or CMMC Level 2 authorization requirements."
        },
        "system_architecture_and_boundary_context": {
          "type": "string",
          "minLength": 20,
          "maxLength": 80000,
          "description": "Description of the bidder's cloud environment, hosting boundary, identity provider, encryption posture, DevSecOps toolchain, and any existing compliance gaps."
        },
        "target_authorization_framework": {
          "type": "string",
          "enum": [
            "dod_rmf_il4_il5_cato",
            "fedramp_high_or_moderate",
            "stateramp_or_state_cloud_sec",
            "cmmc_level_2_nist_800_171"
          ],
          "default": "dod_rmf_il4_il5_cato",
          "description": "Target government cybersecurity authorization framework."
        },
        "target_ato_timeline_days": {
          "type": "integer",
          "default": 90,
          "minimum": 14.0,
          "maximum": 365.0,
          "description": "Target calendar days from contract award to achieve full ATO / cATO authorization."
        }
      },
      "required": [
        "rfp_security_and_ato_requirements",
        "system_architecture_and_boundary_context"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "ato_readiness_score": {
          "type": "integer",
          "description": "Overall ATO / cATO readiness score from 0 to 100 based on boundary maturity, control coverage, and open findings."
        },
        "authorization_boundary_summary": {
          "type": "object",
          "description": "FIPS 199 categorization, Impact Level baseline, GRC system of record, CSP control inheritance percentage, and boundary summary."
        },
        "ssp_control_implementations": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Audit-ready NIST SP 800-53 Rev 5 / NIST 800-171 System Security Plan (SSP) control implementation narratives."
        },
        "cato_devsecops_pipeline_blueprint": {
          "type": "object",
          "description": "Continuous ATO (cATO) DevSecOps CI/CD security gates, ConMon cadence, and OSCAL/SBOM automation blueprint."
        },
        "poam_remediation_schedule": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured Plan of Action & Milestones (POA&M) remediation table for any open findings or architecture gaps."
        },
        "rmf_six_step_milestone_plan": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Day-by-day RMF Step 1 through Step 6 schedule to achieve IATT and full ATO within target_ato_timeline_days."
        },
        "proposal_technical_volume_ato_narrative": {
          "type": "string",
          "description": "Executive-ready Shipley Technical Volume narrative explaining how the Offeror will achieve rapid, low-risk ATO / cATO without delaying mission deployment."
        }
      }
    }
  },
  {
    "name": "analyze_debriefing_bid_protest",
    "title": "Analyze GovCon Post-Award Debriefing, FAR 15.506 Q&A & GAO Bid-Protest Viability",
    "description": "Analyze an Unsuccessful Offeror Notice, SSEB evaluation scorecard, RFP Section M criteria, and submitted proposal excerpts to generate strategic FAR 15.506 / DFARS 252.215-7016 Enhanced Debriefing follow-up questions, a 0-100 GAO Bid-Protest Viability Score, a Go/No-Go protest recommendation, CICA 31 U.S.C. 3553 automatic stay deadline calculations, a 4-C.F.R. Part 21 Protest Grounds Matrix (Unstated Evaluation Criteria, Disparate Treatment, Flawed Best-Value Tradeoff, Misleading Discussions), and an Executive Recompete/Corrective-Action Playbook. This is a read-only, stateless post-award diagnostic and debriefing analysis call that provides structured procurement intelligence rather than formal legal representation (requires X-RapidAPI-Key; `unsuccessful_offeror_notice_and_debrief_text` accepts 30 to 100,000 characters, `rfp_section_m_and_submitted_proposal_excerpts` accepts 30 to 100,000 characters, optional `award_and_debrief_timeline_context` anchors the 10-day GAO filing and 5-day CICA stay clock, and `target_acquisition_regime` calibrates rules across DoD DFARS Enhanced Debriefings, Civilian FAR Part 15, FAR 16.505 Task Orders >$10M/$35M, and FAR 8.405-2 GSA MAS). Use this tool after contract award notification when preparing for a FAR 15.506 post-award debriefing or evaluating GAO/COFC bid-protest grounds; use `match_capability_statement` instead for pre-bid Gate-1 Bid/No-Bid Pwin scoring, or `analyze_rfp_amendment_diff` for pre-award SF-30 solicitation amendments. Use this tool when evaluating an unsuccessful offeror notice or preparing FAR 15.506 enhanced debriefing questions and GAO/COFC bid-protest viability analyses; use `generate_cpars_past_performance` or `generate_post_award_cpar_rebuttal` instead for CPARS performance evaluations.",
    "annotations": {
      "title": "Analyze GovCon Post-Award Debriefing, FAR 15.506 Q&A & GAO Bid-Protest Viability",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "award_notice_or_debrief_text": {
          "type": "string",
          "minLength": 20,
          "maxLength": 100000,
          "description": "Raw text from the Agency Unsuccessful Offeror Notice, Post-Award Debriefing letter/slides, Source Selection Decision Document (SSDD) excerpt, or competitor protest allegations."
        },
        "rfp_section_m_and_bidder_context": {
          "type": "string",
          "minLength": 20,
          "maxLength": 100000,
          "description": "RFP Section L/M evaluation criteria, weighting hierarchy (Best-Value Tradeoff vs. LPTA), and summary of the bidder's submitted ratings, evaluated price, and proposal strengths/weaknesses."
        },
        "analysis_mode": {
          "type": "string",
          "enum": [
            "unsuccessful_offeror_debrief_and_protest",
            "winning_awardee_intervention_defense",
            "pre_award_competitive_range_exclusion"
          ],
          "default": "unsuccessful_offeror_debrief_and_protest",
          "description": "Perspective mode: 'unsuccessful_offeror_debrief_and_protest' (default, FAR 15.506 debrief questions + GAO protest merits audit), 'winning_awardee_intervention_defense' (defend contract award as Intervenor), or 'pre_award_competitive_range_exclusion' (FAR 15.505 exclusion challenge)."
        },
        "procurement_jurisdiction": {
          "type": "string",
          "enum": [
            "federal_far_gao_cofc",
            "dod_dfars_215_506_enhanced",
            "gsa_mas_task_order_far_8_405_5",
            "idid_gwac_task_order_far_16_505",
            "state_sled_procurement_protest"
          ],
          "default": "dod_dfars_215_506_enhanced",
          "description": "Governing procurement protest forum and jurisdiction."
        }
      },
      "required": [
        "award_notice_or_debrief_text",
        "rfp_section_m_and_bidder_context"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "protest_viability_or_defense_score": {
          "type": "integer",
          "description": "Overall 0-100 score measuring GAO/COFC protest sustain probability (or Awardee Defense strength when in winning_awardee_intervention_defense mode)."
        },
        "recommended_executive_decision": {
          "type": "string",
          "description": "Clear executive recommendation (e.g., 'PURSUE_ENHANCED_DEBRIEF_THEN_GAO_PROTEST', 'FILE_AGENCY_LEVEL_CORRECTIVE_ACTION_REQUEST', 'DO_NOT_PROTEST_PRESERVE_CUSTOMER_GOODWILL', or 'INTERVENE_AND_MOVE_TO_DISMISS')."
        },
        "task_order_jurisdictional_bar_check": {
          "type": "string",
          "description": "Audit of FASA task-order protest jurisdiction bars under FAR 16.505(a)(10) ($35M DoD / $10M Civilian threshold) or FAR 8.405-5 GSA Schedule rules."
        },
        "statutory_deadline_calendar": {
          "type": "object",
          "description": "Strict FAR 15.505/15.506, DFARS 215.506-70, and CICA (31 U.S.C. 3553) automatic-stay deadline schedule."
        },
        "far_15_506_debriefing_questions": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Strategic FAR 15.506 / DoD Enhanced Debriefing questions to submit to the Contracting Officer."
        },
        "protest_grounds_or_defense_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Detailed GAO/COFC protest grounds (or Awardee Intervenor defenses) mapped to FAR/GAO precedent."
        },
        "ready_to_send_debrief_request_or_counsel_memo": {
          "type": "string",
          "description": "Ready-to-send FAR 15.506 Enhanced Debriefing Request Letter & Questions (or Executive Bid-Protest / Intervenor Strategy Memo)."
        }
      }
    }
  },
  {
    "name": "generate_gsa_mas_offer",
    "title": "Generate GSA MAS Schedule SIN Mapping, 0.75% IFF Rate Card & PRC Compliance Package",
    "description": "Map commercial labor rate cards, software/cloud SKUs, commercial discounting practices, and past project histories into a GSA Multiple Award Schedule (MAS) Large Category F (IT) eOffer or eMod package containing a Special Item Number (SIN) mapping matrix (`54151S`, `54151HACS`, `518210C`, `511210`, `OLM`), a GSA Price Proposal Template (PPT) ceiling rate card grossed up for the 0.75% Industrial Funding Fee (`Net / 0.9925`) with 5-year GSAR 552.238-118 EPA escalation, GSAR 552.238-81 Price Reductions Clause (PRC) / Most Favored Customer (MFC) guardrails, CSP-1 vs. Transactional Data Reporting (TDR) pathway recommendations, and a ready-to-submit SCP-FSS-001 proposal narrative. This is a read-only, stateless, non-destructive compliance and pricing generator (requires X-RapidAPI-Key; `commercial_catalog_and_lcat_rates` accepts 20 to 45,000 characters and `corporate_experience_and_project_context` accepts 20 to 35,000 characters). Use this tool when preparing a GSA Multiple Award Schedule (MAS) eOffer, SIN addition eMod, or GSAR 552.238-81 Price Reductions Clause (PRC) / MFC audit; use `generate_igce_price_to_win` instead for single-RFP IGCE wrap-rate and Price-to-Win modeling, or `match_key_personnel` to tailor individual candidate resumes to LCAT minimums.",
    "annotations": {
      "title": "Generate GSA MAS Schedule SIN Mapping, 0.75% IFF Rate Card & PRC Compliance Package",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "commercial_catalog_and_lcat_rates": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "Commercial Price List (CPL), LCAT titles, hourly rates, minimum education/years of experience, software/SaaS SKUs, and standard commercial discounting practices (20 to 45,000 characters)."
        },
        "corporate_experience_and_project_context": {
          "type": "string",
          "minLength": 20,
          "maxLength": 35000,
          "description": "Past project experience for SCP-FSS-001 Factor 4 (1-2 completed projects per target SIN), target GSA IT/Cyber SINs (`54151S`, `54151HACS`, `518210C`), and commercial customer classes (20 to 35,000 characters)."
        },
        "pricing_disclosure_pathway": {
          "type": "string",
          "enum": [
            "CSP-1_Traditional_PRC",
            "TDR_Transactional_Data_Reporting",
            "Auto_Recommend"
          ],
          "default": "Auto_Recommend",
          "description": "GSA MAS pricing disclosure pathway: 'CSP-1_Traditional_PRC' (traditional Commercial Sales Practices with Most Favored Customer tracking), 'TDR_Transactional_Data_Reporting' (GSAR 552.238-81 Alt I TDR exemption), or 'Auto_Recommend' (default)."
        },
        "submission_type": {
          "type": "string",
          "enum": [
            "New_GSA_MAS_Offer",
            "Add_SIN_or_EPA_Price_Mod"
          ],
          "default": "New_GSA_MAS_Offer",
          "description": "Submission mode: 'New_GSA_MAS_Offer' (default, full SCP-FSS-001 eOffer package) or 'Add_SIN_or_EPA_Price_Mod' (GSA eMod SIN addition or GSAR 552.238-118 Economic Price Adjustment)."
        }
      },
      "required": [
        "commercial_catalog_and_lcat_rates",
        "corporate_experience_and_project_context"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "gsa_mas_readiness_score": {
          "type": "integer",
          "description": "Overall GSA eOffer / eMod readiness score (0-100) under SCP-FSS-001."
        },
        "recommended_pricing_pathway": {
          "type": "string",
          "description": "Recommended GSA pricing disclosure pathway (TDR Transactional Data Reporting vs. CSP-1 Traditional Most Favored Customer) with rationale."
        },
        "iff_and_epa_pricing_summary": {
          "type": "string",
          "description": "Executive summary of the 0.75% Industrial Funding Fee (IFF) gross-up (`Net / 0.9925`), proposed GSA discount off CPL, and 5-year GSAR 552.238-118 EPA escalation."
        },
        "sin_mapping_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured GSA MAS Special Item Number (SIN) mapping matrix (`54151S`, `54151HACS`, `518210C`, `OLM`, etc.) with Factor 4 relevant project narratives."
        },
        "gsa_lcat_iff_price_list": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "GSA MAS Price Proposal Template (PPT) table with minimum education/experience, CPL rate, Net rate, 0.75% IFF ceiling rate (`Net / 0.9925`), and 5-year EPA progression."
        },
        "prc_and_mfc_compliance_guardrails": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "GSAR 552.238-81 Price Reductions Clause (PRC) and Most Favored Customer (MFC) Basis of Award guardrails and safe-harbor exemptions."
        },
        "ready_to_submit_scp_fss_001_narrative": {
          "type": "string",
          "description": "Authoritative, paste-ready SCP-FSS-001 Administrative, Technical (Factor 1 Corporate Experience, Factor 2 Past Performance, Factor 3 Quality Control, Factor 4 Relevant SIN Experience), and Price Proposal narrative for GSA eOffer / eMod."
        }
      }
    }
  },
  {
    "name": "generate_sources_sought_response",
    "title": "Generate GovCon Sources Sought, RFI & FAR 19.502-2 Set-Aside Shaping Response",
    "description": "Analyze agency Sources Sought notices, Market Research RFIs, and Draft PWS/SOWs against a vendor's socioeconomic status (`8(a)`, `SDVOSB`, `HUBZone`, `WOSB/EDWOSB`, Small Business) and past performance to generate a persuasive FAR 19.502-2 Rule-of-Two set-aside justification, a 13 CFR 121.402 NAICS & SBA size standard shaping analysis, a requirement-by-requirement capability alignment matrix, Contracting Officer / OSDBU acquisition-shaping recommendations, and a ready-to-submit Sources Sought / RFI response narrative. This is a read-only, stateless, non-destructive capture shaping generator (requires X-RapidAPI-Key; `sources_sought_or_rfi_notice_text` accepts 20 to 45,000 characters and `vendor_capability_and_socioeconomic_profile` accepts 20 to 35,000 characters). Use this tool during pre-RFP Market Research / Sources Sought / RFI phases to persuade the Contracting Officer to set aside an upcoming procurement for small business; use `match_capability_statement` instead for Gate-1 Bid/No-Bid Pwin scoring on an already-released RFP, or `generate_rfp_response` to draft final RFP proposal volumes. Use this tool when responding to pre-RFP Sources Sought notices or RFIs to lock in small-business set-asides under the FAR 19.502-2 Rule of Two; use `match_capability_statement` instead for full RFP Bid/No-Bid Pwin scoring, or `generate_rfp_response` for full proposal narrative drafting.",
    "annotations": {
      "title": "Generate GovCon Sources Sought, RFI & FAR 19.502-2 Set-Aside Shaping Response",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "sources_sought_or_rfi_notice_text": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "Full text of the agency Sources Sought notice, Market Research RFI, SSN capability questions, or Draft PWS/SOW (20 to 45,000 characters)."
        },
        "vendor_capability_and_socioeconomic_profile": {
          "type": "string",
          "minLength": 20,
          "maxLength": 35000,
          "description": "Vendor socioeconomic designations (8(a), SDVOSB, HUBZone, WOSB/EDWOSB, Small Business), UEI/CAGE, GSA MAS / GWAC contract vehicles, facility clearances, and past performance (20 to 35,000 characters)."
        },
        "target_set_aside_preference": {
          "type": "string",
          "enum": [
            "8a_Sole_Source_or_Competitive",
            "SDVOSB_Set_Aside",
            "HUBZone_Set_Aside",
            "WOSB_EDWOSB_Set_Aside",
            "Total_Small_Business_Rule_of_Two",
            "Auto_Recommend"
          ],
          "default": "Auto_Recommend",
          "description": "Preferred FAR Part 19 set-aside pathway to justify to the Contracting Officer and OSDBU ('8a_Sole_Source_or_Competitive', 'SDVOSB_Set_Aside', 'HUBZone_Set_Aside', 'WOSB_EDWOSB_Set_Aside', 'Total_Small_Business_Rule_of_Two', or 'Auto_Recommend')."
        }
      },
      "required": [
        "sources_sought_or_rfi_notice_text",
        "vendor_capability_and_socioeconomic_profile"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "set_aside_shaping_confidence_score": {
          "type": "integer",
          "description": "0-100 score indicating the strength of the vendor's case to persuade the Contracting Officer and OSDBU to set aside the procurement."
        },
        "recommended_acquisition_strategy_and_set_aside": {
          "type": "string",
          "description": "Recommended acquisition vehicle (GSA MAS, 8(a) STARS III, VETS 2, Polaris, Open Market) and FAR Part 19 set-aside determination."
        },
        "rule_of_two_and_far_19_502_justification": {
          "type": "string",
          "description": "Formal FAR 19.502-2 Rule-of-Two & FAR Part 10 market research justification proving two or more capable small businesses (or sole-source 8(a)/SDVOSB authority) exist at fair market prices."
        },
        "naics_psc_and_size_standard_shaping_analysis": {
          "type": "string",
          "description": "Analysis of the posted NAICS/PSC code under 13 CFR 121.402, recommending either retention or a higher/more accurate SBA size standard."
        },
        "requirement_capability_alignment_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Requirement-by-requirement alignment table mapping agency RFI tasks to demonstrated prime capability and 13 CFR 125.6 workshare compliance."
        },
        "contracting_officer_shaping_questions_and_recommendations": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Strategic recommendations for the Contracting Officer and Small Business Specialist (OSDBU) to shape the final RFP in the vendor's favor."
        },
        "ready_to_submit_sources_sought_response_narrative": {
          "type": "string",
          "description": "Complete, paste-ready Sources Sought / RFI Response Narrative (Corporate Overview, Socioeconomic & Vehicle Eligibility, Technical Capability, Past Performance, and Acquisition Strategy Recommendation)."
        }
      }
    }
  },
  {
    "name": "generate_oci_mitigation_plan",
    "title": "Audit FAR Subpart 9.5 Organizational Conflicts of Interest (OCI) & Generate Mitigation Plan",
    "description": "Audit existing prime/subcontract awards (SETA, A&AS, IV&V, Systems Engineering, Cloud Architecture) against a target solicitation scope to detect Unequal Access to Information, Biased Ground Rules, and Impaired Objectivity under FAR Subpart 9.5 (FAR 9.505-1 through 9.505-4) and generate an OCI Risk Score (0-100), a 3-Pillar Case-Law Audit Matrix, an Organizational Firewall & NDA Control Matrix, and a ready-to-submit OCI Disclosure & Mitigation Plan volume. This is a read-only, stateless, non-destructive compliance and legal-engineering generator (requires X-RapidAPI-Key; `new_solicitation_scope_and_oci_clauses` accepts 20 to 45,000 characters and `existing_contracts_and_corporate_relationships` accepts 20 to 35,000 characters). Use this tool when auditing FAR 9.5 / DFARS 252.209-7008 / 252.209-7009 Organizational Conflicts of Interest or drafting an OCI Mitigation Plan & Non-Disclosure Firewall; use `scan_far_dfars_clauses` instead for general Section I FAR/DFARS flow-down clause scanning, or `generate_teaming_strategy` to structure 13 CFR 125.6 Prime/Sub workshare splits.",
    "annotations": {
      "title": "Audit FAR Subpart 9.5 Organizational Conflicts of Interest (OCI) & Generate Mitigation Plan",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "target_solicitation_and_sow_text": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "Full or excerpted target RFP scope, PWS/SOW tasks, Section H/I/K/L OCI disclosure instructions, and issuing agency/program office."
        },
        "current_and_prior_contracts_portfolio": {
          "type": "string",
          "minLength": 20,
          "maxLength": 35000,
          "description": "Summary of the bidder's (and any proposed subcontractor's) active or recent prime/sub contracts, SETA/A&AS/IV&V advisory roles, and access to nonpublic source-selection or proprietary third-party data."
        },
        "proposed_bidding_role_and_teaming_structure": {
          "type": "string",
          "enum": [
            "Prime_Offeror",
            "Subcontractor_or_Teaming_Partner",
            "Joint_Venture_or_Mentor_Protege",
            "SETA_or_A_and_AS_Incumbent_Pivoting_to_Development"
          ],
          "default": "Prime_Offeror",
          "description": "Bidder's pursuit structure ('Prime_Offeror', 'Subcontractor_or_Teaming_Partner', 'Joint_Venture_or_Mentor_Protege', or 'SETA_or_A_and_AS_Incumbent_Pivoting_to_Development')."
        }
      },
      "required": [
        "target_solicitation_and_sow_text",
        "current_and_prior_contracts_portfolio"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "oci_clearance_and_defensibility_score": {
          "type": "integer",
          "description": "0-100 score indicating how defensible the bidder's OCI posture and mitigation plan are against Contracting Officer exclusion or GAO bid protest."
        },
        "overall_oci_determination": {
          "type": "string",
          "description": "Formal FAR Subpart 9.5 OCI risk determination and pursuit posture recommendation."
        },
        "executive_oci_risk_summary": {
          "type": "string",
          "description": "Executive legal and capture summary of the OCI audit findings for the Contracting Officer and Capture Director."
        },
        "three_pillar_far_9_5_audit_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Comprehensive audit across all three FAR Subpart 9.5 / GAO OCI pillars: Unequal Access to Information (FAR 9.505-4), Biased Ground Rules (FAR 9.505-1/9.505-2), and Impaired Objectivity (FAR 9.505-3)."
        },
        "organizational_firewall_and_nda_controls": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Concrete organizational, technical (IT/GovCloud enclave), personnel NDA, and workshare carve-out controls."
        },
        "ready_to_submit_oci_mitigation_plan_narrative": {
          "type": "string",
          "description": "Complete, paste-ready Volume I / Section L Organizational Conflict of Interest (OCI) Disclosure & Mitigation Plan narrative including a FAR 9.505-4 Non-Disclosure Agreement (NDA) template and Contracting Officer certification block."
        }
      }
    }
  },
  {
    "name": "generate_sbir_sttr_commercialization",
    "title": "Generate SBIR / STTR Phase I\u2013III Technical Work Plan, TRL Matrix & Commercialization Plan",
    "description": "Convert R&D technical specifications and an SBIR/STTR solicitation topic description into a DoD/AFWERX/SpaceWERX/NSF SBIR/STTR Technical Work Plan, a TRL 1\u20139 progression matrix, a Phase III Dual-Use Commercialization & Transition Plan, and a pre-award DFARS 252.227-7018 / FAR 52.227-20 SBIR Data Rights assertion schedule. This is a read-only, stateless, non-destructive R&D proposal and IP compliance generator (requires X-RapidAPI-Key; `sbir_sttr_topic_and_rd_specs` accepts 20 to 45,000 characters and `company_technology_and_ip_baseline` accepts 20 to 35,000 characters). Use this tool when preparing Phase I, Phase II, Direct-to-Phase II (AFWERX/SpaceWERX), or Phase III SBIR/STTR technical volumes, commercialization plans, and DFARS 252.227-7018 IP data-rights tables; use `generate_rfp_response` instead for standard FAR Part 15 technical approach volumes, or `scan_far_dfars_clauses` for general Section I clause flow-down audits.",
    "annotations": {
      "title": "Generate SBIR / STTR Phase I\u2013III Technical Work Plan, TRL Matrix & Commercialization Plan",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "sbir_sttr_topic_and_rd_specs": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "Full or excerpted DoD, AFWERX, SPACEWERX, Navy, Army, DARPA, NSF, NASA, or DHS SBIR/STTR topic instructions, Phase I/II/III technical objectives, and evaluation criteria (20 to 45,000 characters)."
        },
        "company_technology_and_ip_baseline": {
          "type": "string",
          "minLength": 20,
          "maxLength": 35000,
          "description": "Summary of the small business offeror's R&D technology, current TRL, Principal Investigator (PI) credentials, prior IRAD/patents, STTR university/lab partner (if applicable), and dual-use commercial traction (20 to 35,000 characters)."
        },
        "target_phase_and_program": {
          "type": "string",
          "default": "Direct_to_Phase_II_or_Phase_II_Prototype",
          "minLength": 1,
          "maxLength": 120,
          "description": "Target SBIR/STTR phase ('Phase_I_Feasibility_and_Proof_of_Concept', 'Direct_to_Phase_II_or_Phase_II_Prototype', 'Phase_IIB_or_STRATFI_TACFI_Matching', or 'Phase_III_Sole_Source_Transition_15_USC_638_r_4')."
        },
        "sponsoring_agency_or_program": {
          "type": "string",
          "default": "USAF AFWERX / DoD DSIP",
          "minLength": 1,
          "maxLength": 200,
          "description": "Optional sponsoring agency, PEO, or Phase III transition customer (e.g., USAF AFWERX / SpaceWERX, Office of Naval Research, NSF TIP)."
        }
      },
      "required": [
        "sbir_sttr_topic_and_rd_specs",
        "company_technology_and_ip_baseline"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "sbir_pwin_and_transition_readiness_score": {
          "type": "integer",
          "description": "0-100 score evaluating technical merit, TRL feasibility, dual-use commercialization potential, and Phase III Program-of-Record transition readiness."
        },
        "recommended_phase_and_transition_pathway": {
          "type": "string",
          "description": "Strategic SBIR/STTR pursuit and transition recommendation."
        },
        "executive_technical_and_dual_use_summary": {
          "type": "string",
          "description": "Executive summary of the R&D innovation, warfighter/agency operational impact, and commercial dual-use market thesis."
        },
        "trl_progression_and_technical_work_plan": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured Phase I/II Technical Work Plan and TRL 1-9 progression milestones with quantifiable exit criteria."
        },
        "dfars_252_227_7018_sbir_data_rights_assertions": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Pre-populated DFARS 252.227-7018 / FAR 52.227-20 SBIR/STTR Data Rights Assertion Table protecting core IP for 20 years."
        },
        "phase_iii_dual_use_commercialization_and_work_plan_narrative": {
          "type": "string",
          "description": "Complete, paste-ready SBIR/STTR Volume 2 Technical Work Plan & Commercialization Plan narrative including Customer Memorandum (MOU) justification, TAM/SAM/SOM dual-use revenue forecast, and 15 U.S.C. \u00a7 638(r)(4) Phase III sole-source transition roadmap."
        }
      }
    }
  },
  {
    "name": "audit_section_508_vpat",
    "title": "Audit Revised Section 508, WCAG 2.2 AA & Generate VPAT 2.5 Accessibility Conformance Report (ACR)",
    "description": "Audit software, cloud SaaS portals, and electronic deliverables against Revised Section 508 (36 CFR Part 1194 / FAR Subpart 39.2), W3C WCAG 2.1 / 2.2 Level A & AA Success Criteria, and State SLED digital accessibility laws (such as Colorado HB21-1110) to generate an Accessibility Readiness Score (0-100), a structured ITI VPAT 2.5 Conformance Matrix (WCAG 2.2 Level A/AA + Revised Section 508 Chapters 3, 5, and 6), an Engineering Accessibility Remediation POA&M Roadmap, and a paste-ready VPAT 2.5 ACR & Equally Effective Alternate Access Plan (EEAAP) proposal narrative. This is a read-only, stateless, non-destructive accessibility compliance generator (requires X-RapidAPI-Key; `product_architecture_and_ui_specs` accepts 20 to 45,000 characters and `known_accessibility_test_results_or_gaps` accepts 10 to 35,000 characters). Use this tool when auditing software/SaaS accessibility or generating a Section 508 VPAT 2.5 ACR table for federal/SLED proposals; use `answer_security_questionnaire` instead for cybersecurity/SOC 2/NIST 800-171 questionnaires, or `scan_far_dfars_clauses` for general Section I FAR/DFARS clause flow-down audits.",
    "annotations": {
      "title": "Audit Revised Section 508, WCAG 2.2 AA & Generate VPAT 2.5 Accessibility Conformance Report (ACR)",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "product_architecture_and_ui_specs": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "Description of the software/SaaS application, UI framework (React/Angular/USWDS), electronic documents, user workflows, and target RFP Section 508 / accessibility solicitation clauses (20 to 45,000 characters)."
        },
        "known_accessibility_test_results_or_gaps": {
          "type": "string",
          "default": "Automated axe-core/WAVE CI scan + manual NVDA/JAWS screen-reader and keyboard-only navigation baseline.",
          "minLength": 10,
          "maxLength": 35000,
          "description": "Known accessibility test findings (axe-core, Lighthouse, DHS Trusted Tester v5, JAWS/NVDA/VoiceOver), existing exceptions (e.g., third-party GIS map canvas or legacy PDF exports), and current remediation status (10 to 35,000 characters)."
        },
        "target_compliance_standard": {
          "type": "string",
          "enum": [
            "Revised_Section_508_And_WCAG_2_2_AA",
            "Federal_Section_508_36_CFR_1194_Only",
            "State_SLED_Accessibility_HB21_1110_And_WCAG_2_2_AA",
            "DoD_DISA_Section_508_And_Vpat_2_5_Rev"
          ],
          "default": "Revised_Section_508_And_WCAG_2_2_AA",
          "description": "Target accessibility regulatory regime ('Revised_Section_508_And_WCAG_2_2_AA' [default], 'Federal_Section_508_36_CFR_1194_Only', 'State_SLED_Accessibility_HB21_1110_And_WCAG_2_2_AA', or 'DoD_DISA_Section_508_And_Vpat_2_5_Rev')."
        }
      },
      "required": [
        "product_architecture_and_ui_specs"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "accessibility_readiness_score": {
          "type": "integer",
          "description": "0-100 score quantifying the product's Section 508 / WCAG 2.2 AA compliance readiness and VPAT 2.5 defensibility for federal/state procurement."
        },
        "overall_section_508_determination": {
          "type": "string",
          "description": "Overall Section 508 / WCAG 2.2 AA procurement conformance determination under FAR 39.2 and ITI VPAT 2.5 standards."
        },
        "executive_vpat_summary": {
          "type": "string",
          "description": "Executive accessibility compliance summary for the Agency Section 508 Coordinator and Contracting Officer."
        },
        "vpat_2_5_conformance_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured ITI VPAT 2.5 Accessibility Conformance Report (ACR) audit rows covering WCAG 2.2 Level A/AA and Revised Section 508 Chapters 3, 5, and 6."
        },
        "engineering_remediation_roadmap": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Prioritized Accessibility Plan of Action & Milestones (POA&M) and engineering remediation roadmap for any 'Partially_Supports' or 'Does_Not_Support' items."
        },
        "ready_to_submit_vpat_2_5_acr_narrative": {
          "type": "string",
          "description": "Complete, paste-ready ITI VPAT 2.5 Accessibility Conformance Report (ACR) & FAR 39.2 Proposal Volume narrative including evaluation methodology (DHS Trusted Tester v5, axe-core, NVDA/JAWS) and Equally Effective Alternate Access Plan (EEAAP) language."
        }
      }
    }
  },
  {
    "name": "audit_supply_chain_scrm",
    "title": "Audit Supply Chain Risk (NIST 800-161 C-SCRM, NDAA 889, FASCSA, TAA, BAA) & Generate SBOM Attestation",
    "description": "Audit hardware Bills of Materials (BOMs), sub-tier suppliers, and software components (SBOM) against NIST SP 800-161 Rev. 1 Cybersecurity Supply Chain Risk Management (C-SCRM), FAR 52.204-25 (NDAA Section 889 Part A/B prohibition on Huawei, ZTE, Hytera, Hikvision, Dahua and their affiliates), FAR 52.204-30 (FASCSA exclusion orders), the Buy American Act (FAR Part 25 domestic content), and the Trade Agreements Act (FAR 52.225-5 designated countries), returning JSON with a Supply Chain Risk Score (0-100), an overall SCRM verdict, per-line NDAA 889 and TAA determinations, a BAA domestic-content percentage, NIST 800-161 SR-family control gaps, an NTIA minimum-elements SBOM and CISA Secure Software Self-Attestation readiness review, paste-ready C-SCRM Plan sections, a SCRM POA&M remediation roadmap, and a proposal-ready SCRM narrative. This is a read-only, stateless, non-destructive compliance auditor (requires X-RapidAPI-Key; nothing is stored, filed, or submitted to SAM.gov, and FASCSA results must still be verified in SAM.gov; `solicitation_or_contract_context` accepts 20 to 45,000 characters, `bom_line_items` accepts 1 to 200 lines, and `software_components` accepts up to 500 SBOM components). Use this tool when vetting a BOM, reseller quote, or SBOM for NDAA 889 / FASCSA / TAA / BAA award eligibility or drafting a C-SCRM Plan and SBOM attestation; use `audit_section_508_vpat` instead for Section 508 / WCAG 2.2 accessibility and VPAT conformance, `scan_far_dfars_clauses` for general Section I FAR/DFARS clause flow-down risk scanning, `answer_security_questionnaire` for SOC 2 / FedRAMP / NIST 800-171 questionnaires, or `generate_ato_rmf_package` for NIST 800-53 SSP / RMF / cATO authorization packages.",
    "annotations": {
      "title": "Audit Supply Chain Risk (NIST 800-161 C-SCRM, NDAA 889, FASCSA, TAA, BAA) & Generate SBOM Attestation",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "solicitation_or_contract_context": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "Solicitation / contract scope, Section H/I supply chain clauses, delivery location, end-use, and any agency C-SCRM, NDAA 889, TAA, BAA, or SBOM requirements (20 to 45,000 characters)."
        },
        "offeror_name": {
          "type": "string",
          "default": "Offeror (Prime Contractor)",
          "minLength": 2,
          "maxLength": 300,
          "description": "Legal name of the prime offeror / reseller submitting the BOM and supply chain representations (2 to 300 characters)."
        },
        "contracting_agency": {
          "type": "string",
          "default": "Department of Defense (DoD)",
          "minLength": 2,
          "maxLength": 300,
          "description": "Contracting agency or SLED buyer, e.g. 'U.S. Army PEO C3T', 'GSA FAS', or 'Arizona ADOA-ASET' (2 to 300 characters)."
        },
        "applicable_contract_clauses": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "maxItems": 40,
          "description": "Supply chain clauses and standards in the solicitation, e.g. 'FAR 52.204-25', 'FAR 52.204-30', 'FAR 52.225-5', 'DFARS 252.225-7001', 'DFARS 252.204-7012', 'DFARS 252.246-7008', 'NIST SP 800-161 Rev. 1', 'OMB M-22-18' (0 to 40 entries)."
        },
        "bom_line_items": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "minItems": 1,
          "maxItems": 200,
          "description": "Hardware / COTS Bill of Materials line items to screen (1 to 200 lines)."
        },
        "software_components": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "maxItems": 500,
          "description": "Software Bill of Materials (SBOM) components for NTIA minimum-elements and CISA secure software attestation review (0 to 500 components)."
        },
        "sbom_format": {
          "type": "string",
          "enum": [
            "CycloneDX_1_6",
            "SPDX_2_3",
            "SPDX_3_0",
            "Proprietary_Or_Spreadsheet",
            "None_Available"
          ],
          "default": "CycloneDX_1_6",
          "description": "Format of the offeror's SBOM deliverable: 'CycloneDX_1_6' (default), 'SPDX_2_3', 'SPDX_3_0', 'Proprietary_Or_Spreadsheet', or 'None_Available'."
        },
        "target_compliance_regime": {
          "type": "string",
          "enum": [
            "Auto_Detect_From_Clauses",
            "Federal_DoD_Full_C_SCRM_NDAA_889_TAA_BAA",
            "Federal_Civilian_FASCSA_And_CISA_Secure_Software",
            "State_SLED_Prohibited_Vendor_And_Domestic_Preference"
          ],
          "default": "Auto_Detect_From_Clauses",
          "description": "Target supply chain regulatory regime: 'Auto_Detect_From_Clauses' (default), 'Federal_DoD_Full_C_SCRM_NDAA_889_TAA_BAA', 'Federal_Civilian_FASCSA_And_CISA_Secure_Software', or 'State_SLED_Prohibited_Vendor_And_Domestic_Preference'."
        },
        "additional_supplier_notes": {
          "type": "string",
          "default": "",
          "minLength": 1,
          "maxLength": 20000,
          "description": "Optional sub-tier supplier attestations, SAM.gov FAR 52.204-24/26 representations, ownership/affiliation notes, or existing C-SCRM program documentation (0 to 20,000 characters)."
        }
      },
      "required": [
        "solicitation_or_contract_context",
        "bom_line_items"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "supply_chain_risk_score": {
          "type": "integer",
          "description": "Quantitative supply chain risk score from 0 (no material risk) to 100 (prohibited / award-blocking)."
        },
        "overall_scrm_verdict": {
          "type": "string",
          "description": "Overall C-SCRM / NDAA 889 / FASCSA / TAA / BAA award-eligibility verdict."
        },
        "executive_scrm_summary": {
          "type": "string",
          "description": "Executive supply chain risk summary for the Contracting Officer and offeror leadership."
        },
        "ndaa_889_findings": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Per-line FAR 52.204-25 (NDAA Section 889 Part A/B) prohibited-vendor screening findings."
        },
        "fascsa_exclusion_check": {
          "type": "object",
          "description": "FAR 52.204-30 FASCSA exclusion/removal order screening."
        },
        "taa_compliance_by_line": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Per-line Trade Agreements Act (FAR 52.225-5) designated-country determinations."
        },
        "baa_domestic_content": {
          "type": "object",
          "description": "Buy American Act (FAR Part 25) domestic content analysis."
        },
        "nist_800_161_control_gaps": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "NIST SP 800-161 Rev. 1 C-SCRM control gaps with severity and implementation guidance."
        },
        "sbom_attestation": {
          "type": "object",
          "description": "NTIA SBOM minimum-elements review and CISA Secure Software Self-Attestation readiness."
        },
        "c_scrm_plan_sections": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready Cybersecurity Supply Chain Risk Management (C-SCRM) Plan sections aligned to NIST SP 800-161 Rev. 1."
        },
        "remediation_roadmap": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Prioritized SCRM Plan of Action & Milestones (POA&M) remediation roadmap."
        },
        "ready_to_submit_scrm_narrative": {
          "type": "string",
          "description": "Paste-ready proposal Supply Chain Risk Management volume narrative with NDAA 889 / FASCSA representations, TAA/BAA certification language, and SBOM attestation statement."
        }
      }
    }
  },
  {
    "name": "generate_quality_assurance_qasp",
    "title": "Generate GovCon Quality Assurance Surveillance Plan (QASP), PRS Table & PWS SLA/KPI Matrix",
    "description": "Transform Performance Work Statement (PWS), Statement of Work (SOW), or Statement of Objectives (SOO) deliverables into a FAR Subpart 37.6 Quality Assurance Surveillance Plan (QASP) package containing a 0-100 QASP Readiness Score, an executive surveillance summary, a Performance Requirements Summary (PRS) Table (with PWS section reference, performance objective, measurable KPI standard, Acceptable Quality Level [AQL], FAR 46.4 surveillance method, monitoring frequency, positive/negative incentive or invoice deduction formula, and assigned COR/QA role), automated SLA/KPI telemetry metrics, a closed-loop Non-Conformance & Cure Notice Corrective Action Report (CAR) workflow with FAR 52.246 inspection citations, and a ready-to-submit QASP/QCP proposal narrative. This is a read-only, stateless, non-destructive quality engineering and proposal generator (requires X-RapidAPI-Key; `pws_or_sow_deliverables_text` accepts 30 to 75,000 characters, while `contract_type_and_incentive_structure` and `surveillance_rigor_and_mission_criticality` calibrate AQL thresholds and incentive/deduction mechanics across FFP, T&M, CPAF, CPIF, and Hybrid IDIQ task orders). Use this tool when building a FAR 37.6 Quality Assurance Surveillance Plan (QASP), Performance Requirements Summary (PRS) matrix, or Contractor Quality Control Plan (QCP) with AQLs and SLA deduction formulas; use `generate_compliance_matrix` instead to shred general Section C/L/M `shall`/`must` requirements into a proposal outline, or `generate_rfp_response` to draft general Technical Approach prose.",
    "annotations": {
      "title": "Generate GovCon Quality Assurance Surveillance Plan (QASP), PRS Table & PWS SLA/KPI Matrix",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "pws_or_sow_deliverables_text": {
          "type": "string",
          "minLength": 30,
          "maxLength": 75000,
          "description": "Raw Performance Work Statement (PWS), Statement of Work (SOW), or Statement of Objectives (SOO) tasks, service levels, and deliverable requirements (30 to 75,000 characters)."
        },
        "contract_type_and_incentive_structure": {
          "type": "string",
          "default": "Firm_Fixed_Price_FFP",
          "minLength": 2,
          "maxLength": 120,
          "description": "Contract type and fee structure ('Firm_Fixed_Price_FFP', 'Time_and_Materials_TM', 'Cost_Plus_Award_Fee_CPAF', 'Cost_Plus_Incentive_Fee_CPIF', or 'Hybrid_IDIQ_Task_Order')."
        },
        "surveillance_rigor_and_mission_criticality": {
          "type": "string",
          "default": "Mission_Critical_24x7_Zero_Trust",
          "minLength": 2,
          "maxLength": 120,
          "description": "Mission criticality profile ('Mission_Critical_24x7_Zero_Trust', 'Standard_Enterprise_IT_SLA', or 'R_and_D_Agile_DevSecOps')."
        },
        "solicitation_or_contract_number": {
          "type": "string",
          "default": "SOL-2026-QASP-001",
          "minLength": 1,
          "maxLength": 200,
          "description": "Optional solicitation or contract number for QASP traceability."
        },
        "target_agency": {
          "type": "string",
          "default": "Department of Defense (DoD) / Federal & State Agency",
          "minLength": 1,
          "maxLength": 300,
          "description": "Optional issuing agency or contracting office."
        }
      },
      "required": [
        "pws_or_sow_deliverables_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "qasp_readiness_score": {
          "type": "integer",
          "description": "0-100 score quantifying the measurability, FAR Subpart 37.6 compliance, and audit defensibility of the generated QASP and PRS matrix."
        },
        "executive_surveillance_summary": {
          "type": "string",
          "description": "Executive summary of the Performance-Based Acquisition (FAR 37.6) surveillance strategy, ISO 9001 / CMMI Level 3 quality governance, and COR partnership model."
        },
        "performance_requirements_summary_prs_table": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured FAR Subpart 37.6 Performance Requirements Summary (PRS) matrix mapping PWS sections to objectives, standards, AQLs, surveillance methods, and incentive/deduction formulas."
        },
        "sla_and_kpi_telemetry_metrics": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Automated SLA and KPI telemetry metrics with target thresholds, measurement windows, data sources, and breach escalation triggers."
        },
        "non_conformance_and_cure_notice_workflow": {
          "type": "object",
          "description": "Closed-loop Non-Conformance, Corrective Action Report (CAR), Root Cause Analysis (RCA), Corrective Action Plan (CAP), and FAR 52.246 inspection workflow."
        },
        "ready_to_submit_qasp_narrative": {
          "type": "string",
          "description": "Complete, paste-ready Quality Assurance Surveillance Plan (QASP) & Quality Control Plan (QCP) proposal volume narrative in Markdown."
        }
      }
    }
  },
  {
    "name": "generate_phase_in_transition_plan",
    "title": "Generate GovCon 30/60/90-Day Phase-In / Phase-Out Transition & Incumbent Capture Plan",
    "description": "Generate a risk-mitigated 30/60/90-Day Phase-In and Phase-Out Transition Plan from solicitation Section C/L/M transition instructions and incumbent workforce context, returning a 0-100 Transition Risk Readiness Score, an executive transition summary, chronological Work Breakdown Structure (WBS) milestones across Days 1-30, 31-60, and 61-90 (plus Phase-Out), an Executive Order 14055 / Service Contract Act (SCA) Incumbent Workforce Capture & Right-of-First-Refusal retention plan with DD-254/DISS clearance crossover timelines and outreach scripts, functional Knowledge Transfer & Shadowing tracks with COR Operational Readiness Review (ORR) gates, a FAR 52.237-3 Continuity of Services Phase-Out checklist, and a ready-to-submit Shipley Transition Plan proposal volume. This is a read-only, stateless, non-destructive capture and program-management generator (requires X-RapidAPI-Key; `solicitation_transition_and_sow_text` accepts 30 to 75,000 characters, optional `incumbent_workforce_and_clearance_context` accepts up to 50,000 characters, and `transition_timeline_window` calibrates milestone cadences across 30-day rapid cutovers, standard 30/60/90-day transitions, 120-day enterprise transitions, and FAR 52.237-3 phase-outs). Use this tool when drafting a Phase-In / Phase-Out Transition Plan volume, WBS mobilization schedule, or incumbent staff capture strategy; use `match_key_personnel` instead to audit and format individual Key Personnel resumes and Letters of Commitment, or `generate_teaming_strategy` for 13 CFR 125.6 Prime/Sub workshare splits.",
    "annotations": {
      "title": "Generate GovCon 30/60/90-Day Phase-In / Phase-Out Transition & Incumbent Capture Plan",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "solicitation_transition_and_sow_text": {
          "type": "string",
          "minLength": 30,
          "maxLength": 75000,
          "description": "Solicitation Section C/L/M transition instructions, PWS scope, incumbent staffing size, clearance levels, and continuity-of-operations mandates (30 to 75,000 characters)."
        },
        "incumbent_workforce_and_clearance_context": {
          "type": "string",
          "default": "",
          "minLength": 0,
          "maxLength": 50000,
          "description": "Optional incumbent contractor details, target FTE count, Collective Bargaining Agreement (CBA) / Service Contract Act (SCA) context, and DD-254 facility/personnel security clearance transfer requirements (0 to 50,000 characters)."
        },
        "transition_timeline_window": {
          "type": "string",
          "default": "Standard_30_60_90_Day_Phase_In",
          "minLength": 2,
          "maxLength": 120,
          "description": "Transition schedule profile ('Rapid_30_Day_Cutover', 'Standard_30_60_90_Day_Phase_In', 'Extended_120_Day_Enterprise_Transition', or 'Include_Phase_Out_FAR_52_237_3')."
        },
        "transition_duration_days": {
          "type": "integer",
          "default": 90,
          "minimum": 15.0,
          "maximum": 180.0,
          "description": "Optional total Phase-In transition duration in calendar days (15 to 180; defaults to 90)."
        },
        "target_agency": {
          "type": "string",
          "default": "Department of Defense (DoD) / Federal & State Agency",
          "minLength": 1,
          "maxLength": 300,
          "description": "Optional issuing agency or contracting office."
        },
        "clearance_requirement": {
          "type": "string",
          "default": "Secret / Top Secret SCI & Public Trust",
          "minLength": 1,
          "maxLength": 200,
          "description": "Optional personnel and facility security clearance level required (DD-254 / DISS / Public Trust)."
        }
      },
      "required": [
        "solicitation_transition_and_sow_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "transition_risk_readiness_score": {
          "type": "integer",
          "description": "0-100 score quantifying Day-1 operational continuity, incumbent capture probability, and FAR 52.237-3 compliance readiness."
        },
        "executive_transition_summary": {
          "type": "string",
          "description": "Executive summary of the zero-mission-disruption Phase-In / Phase-Out strategy, governance structure, and Day-1 Full Operational Capability (FOC) roadmap."
        },
        "wbs_30_60_90_day_milestones": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Chronological Work Breakdown Structure (WBS) transition milestones across Days 1-30, Days 31-60, Days 61-90 (and Phase-Out) with activities, deliverables, exit criteria, and risk mitigations."
        },
        "incumbent_capture_and_retention_plan": {
          "type": "object",
          "description": "Comprehensive incumbent workforce capture, EO 14055 / SCA right-of-first-refusal compliance, DD-254/DISS clearance crossover timeline, and outreach script."
        },
        "knowledge_transfer_and_shadowing_schedule": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Functional knowledge transfer tracks with side-by-side shadowing durations, artifact handover checklists, and COR Operational Readiness Review (ORR) gates."
        },
        "far_52_237_3_phase_out_continuity_checklist": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "FAR 52.237-3 Continuity of Services Phase-Out checklist covering GFE/GFP return, CUI sanitization, credential revocation, and successor contractor training."
        },
        "ready_to_submit_transition_volume": {
          "type": "string",
          "description": "Complete, paste-ready Shipley Phase-In / Phase-Out Transition Plan proposal volume narrative in Markdown."
        }
      }
    }
  },
  {
    "name": "audit_dcaa_accounting_sf1408",
    "title": "Audit DCAA Pre-Award Accounting System (SF 1408) & Indirect Rate Pools",
    "description": "Audit a contractor's chart of accounts, indirect cost pool structure (Fringe, Overhead, G&A, B&P/IR&D), timekeeping procedures, labor distribution policy, and general ledger setup against the 18-point DCAA Standard Form 1408 (SF 1408) Pre-Award Accounting System Checklist, FAR 16.301-3, FAR Subpart 31.2, and DFARS 252.242-7006, returning an SF 1408 executive readiness overview, a line-by-line SF 1408 checklist audit, an indirect rate pool and allocation base analysis, a FAR 31.205 unallowable cost segregation assessment (with FAR 52.242-3 penalty risk), labor timekeeping and DCAA floor-check controls, and a pre-award survey remediation roadmap. This is a read-only, stateless, non-destructive GovCon accounting and compliance audit call (requires X-RapidAPI-Key; `chart_of_accounts_and_pools_text` accepts 20 to 45,000 characters, while `target_contract_type_and_solicitation` and `accounting_software_and_erp_stack` calibrate audit criteria across CPFF, CPIF, CPAF, T&M, and FFP contracts on Deltek Costpoint, Unanet, QuickBooks + GovCon timekeeping, or NetSuite). Use this tool when preparing for a DCAA SF 1408 Pre-Award Accounting System Survey, validating Fringe/Overhead/G&A pool-to-base causal/beneficial relationships, or segregating FAR 31.205 unallowable costs; use `generate_igce_price_to_win` instead to model proposal CLIN wrap-rate pricing and Price-to-Win sensitivity, or `extract_pricing_schedule` to parse Section B CLIN tables.",
    "annotations": {
      "title": "Audit DCAA Pre-Award Accounting System (SF 1408) & Indirect Rate Pools",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "chart_of_accounts_and_pools_text": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "Contractor's chart of accounts, indirect cost pool structure (Fringe, Overhead, G&A, B&P/IR&D), timekeeping procedures, labor distribution policy, and general ledger setup (20 to 45,000 characters)."
        },
        "target_contract_type_and_solicitation": {
          "type": "string",
          "default": "Cost_Plus_Fixed_Fee_CPFF_And_T_And_M",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target contract type (CPFF, CPIF, CPAF, T&M, FFP) and solicitation SF 1408 / FAR 16.301-3 adequacy requirements (defaults to 'Cost_Plus_Fixed_Fee_CPFF_And_T_And_M')."
        },
        "accounting_software_and_erp_stack": {
          "type": "string",
          "default": "QuickBooks_Online_With_GovCon_Timekeeping",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Current accounting ERP & timekeeping stack (e.g., Deltek Costpoint, Unanet GovCon, QuickBooks + ICAT/BigTime, NetSuite; defaults to 'QuickBooks_Online_With_GovCon_Timekeeping')."
        }
      },
      "required": [
        "chart_of_accounts_and_pools_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "sf1408_executive_overview": {
          "type": "object",
          "description": "Executive DCAA SF 1408 readiness verdict, compliance score (0-100), cost-reimbursable award eligibility, and summary."
        },
        "sf1408_18_point_checklist": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Line-by-line audit of Standard Form 1408 Section II accounting system adequacy criteria with findings and remediation steps."
        },
        "indirect_rate_pool_and_base_analysis": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Indirect cost pool (Fringe, Overhead, G&A, B&P/IR&D) and allocation base audit under FAR 31.201-4 and CAS 418/410."
        },
        "far_31_205_unallowable_cost_segregation": {
          "type": "object",
          "description": "Audit of FAR 31.205 expressly unallowable cost account segregation and FAR 52.242-3 penalty protection controls."
        },
        "labor_timekeeping_and_floor_check_controls": {
          "type": "object",
          "description": "Evaluation of daily labor timekeeping, supervisor approvals, Total Time Accounting (TTA), and DCAA floor-check readiness."
        },
        "pre_award_survey_remediation_roadmap": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Ordered pre-audit action items and artifact checklist to pass the DCAA SF 1408 Pre-Award Accounting System Survey."
        }
      }
    }
  },
  {
    "name": "generate_ota_white_paper",
    "title": "Generate DoD Other Transaction Authority (OTA / 10 U.S.C. 4022) Prototype White Paper & Milestone Schedule",
    "description": "Convert commercial dual-use technology specifications and DoD Problem Statements / Commercial Solutions Openings (CSOs) / Request for Prototype Proposals (RPPs) across DIU, C5ISR/CECOM, SOSSEC, SpEC, MTEC, NSTXL, and AFWERX into a 10 U.S.C. 4022 statutory eligibility assessment, evaluator-ready OTA Prototype White Paper sections, an outcome-based Fixed-Price Payable Milestone Schedule & Rough Order of Magnitude (ROM), a Phase 3 Sole-Source Follow-On Production Strategy under 10 U.S.C. 4022(f), an OTA Intellectual Property & Data Rights posture (FAR/DFARS/Bayh-Dole exempt), and consortium pitch deck talking points. This is a read-only, stateless, non-destructive capture and prototype proposal generator (requires X-RapidAPI-Key; `commercial_solution_and_problem_topic_text` accepts 20 to 45,000 characters, while `target_ota_consortium_and_pathway` and `nontraditional_contractor_and_cost_share_status` calibrate consortium formatting and 10 U.S.C. 4022(d)(1) Nontraditional Defense Contractor [NDC], Small Business, or 1/3 cost-share rules). Use this tool when drafting a DoD 10 U.S.C. 4022 Other Transaction Authority (OTA) Prototype White Paper, DIU Commercial Solutions Opening (CSO) solution brief, or Fixed-Price Payable Milestone Schedule; use `generate_sbir_sttr_commercialization` instead for 15 U.S.C. 638 SBIR/STTR Phase I-III proposals, or `generate_rfp_response` for traditional FAR Part 15 technical proposal volumes.",
    "annotations": {
      "title": "Generate DoD Other Transaction Authority (OTA / 10 U.S.C. 4022) Prototype White Paper & Milestone Schedule",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "commercial_solution_and_problem_topic_text": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "DoD Problem Statement / CSO / RPP topic description (DIU, C5ISR/CECOM, SOSSEC, SpEC, MTEC, NSTXL) and vendor's dual-use commercial technology, TRL, and architecture (20 to 45,000 characters)."
        },
        "target_ota_consortium_and_pathway": {
          "type": "string",
          "default": "DIU_Commercial_Solutions_Opening_CSO",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target OTA pathway or consortium (e.g., DIU Commercial Solutions Opening [CSO], SOSSEC, SpEC Space Enterprise Consortium, C5ISR, NSTXL, AFWERX; defaults to 'DIU_Commercial_Solutions_Opening_CSO')."
        },
        "nontraditional_contractor_and_cost_share_status": {
          "type": "string",
          "default": "Nontraditional_Defense_Contractor_NDC_Zero_Cost_Share",
          "minLength": 2,
          "maxLength": 2000,
          "description": "10 U.S.C. 4022 statutory eligibility posture: Nontraditional Defense Contractor (NDC), Small Business, or Traditional Defense Contractor with NDC sub / 1/3 cost-share (defaults to 'Nontraditional_Defense_Contractor_NDC_Zero_Cost_Share')."
        }
      },
      "required": [
        "commercial_solution_and_problem_topic_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "ota_statutory_eligibility_assessment": {
          "type": "object",
          "description": "10 U.S.C. 4022 statutory eligibility assessment covering NDC/Small Business status, cost-share exemption, and 10 U.S.C. 4022(f) sole-source production eligibility."
        },
        "executive_white_paper_sections": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Evaluator-ready OTA Prototype White Paper / Solution Brief sections tailored to DIU CSO and DoD Consortium scoring criteria."
        },
        "payable_milestone_schedule_and_rom": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Outcome-based Fixed-Price Payable Milestone Schedule and Rough Order of Magnitude (ROM) pricing table."
        },
        "dual_use_and_follow_on_production_strategy": {
          "type": "object",
          "description": "TRL advancement roadmap, commercial dual-use viability, and 10 U.S.C. 4022(f) non-competitive follow-on production transition strategy."
        },
        "intellectual_property_and_data_rights_posture": {
          "type": "object",
          "description": "OTA Intellectual Property and Data Rights negotiation posture leveraging FAR/DFARS/Bayh-Dole exemptions."
        },
        "consortium_pitch_deck_talking_points": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "High-impact talking points for the Phase 2 DIU / Consortium oral pitch and live technical demonstration."
        }
      }
    }
  },
  {
    "name": "audit_foci_dd254_clearance",
    "title": "Audit DCSA Facility Clearance (FCL), DD Form 254 & FOCI Mitigation",
    "description": "Audit DD Form 254 Contract Security Classification Specifications (Blocks 10, 11, 13), Standard Form 328 (SF 328 \u2014 Certificate Pertaining to Foreign Interests), and corporate cap-table / foreign investor structures against 32 CFR Part 117 (NISPOM) and Defense Counterintelligence and Security Agency (DCSA) Facility Clearance (FCL) and Foreign Ownership, Control, or Influence (FOCI) mitigation standards, returning an FCL & FOCI executive overview, a DD Form 254 Block 10/11 safeguarding matrix (COMSEC, SCI, SIPRNet, CUI), an SF 328 foreign interest factor audit, a DCSA FOCI mitigation agreement blueprint (Board Resolution, SCA, SSA with NID, or Proxy/Voting Trust with ECP and TCP controls), and a Key Management Personnel (KMP) Exclusion Resolution & NISP eMASS checklist. This is a read-only, stateless, non-destructive industrial security audit call (requires X-RapidAPI-Key; `dd254_and_ownership_cap_table_text` accepts 20 to 45,000 characters, while `target_facility_clearance_level` and `foreign_ownership_and_board_context` calibrate DCSA FCL safeguarding and 32 CFR 117.11 FOCI mitigation instruments). Use this tool when auditing DD Form 254 classified safeguarding requirements, SF 328 foreign ownership/LP triggers, or DCSA FCL / FOCI mitigation agreements; use `generate_ato_rmf_package` instead for DoD RMF / Continuous ATO (cATO) NIST 800-53 System Security Plans, or `match_key_personnel` for individual candidate security clearance and LCAT resume verification.",
    "annotations": {
      "title": "Audit DCSA Facility Clearance (FCL), DD Form 254 & FOCI Mitigation",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "dd254_and_ownership_cap_table_text": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "DD Form 254 Contract Security Classification Specification text (Blocks 10, 11, 13), SF 328 Certificate Pertaining to Foreign Interests entries, and corporate cap-table / foreign investor ownership structure (20 to 45,000 characters)."
        },
        "target_facility_clearance_level": {
          "type": "string",
          "default": "Top_Secret_FCL_With_SCI_And_SIPRNet",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Required Facility Clearance (FCL) and safeguarding posture (e.g., Confidential, Secret, Top Secret, TS/SCI, COMSEC, SIPRNet, JWICS; defaults to 'Top_Secret_FCL_With_SCI_And_SIPRNet')."
        },
        "foreign_ownership_and_board_context": {
          "type": "string",
          "default": "Minority_Foreign_LP_Or_Board_Seat_Under_Review",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Summary of foreign equity voting/ownership percentages, foreign board seats, foreign debt, or foreign technology licensing ties under 32 CFR Part 117 (NISPOM; defaults to 'Minority_Foreign_LP_Or_Board_Seat_Under_Review')."
        }
      },
      "required": [
        "dd254_and_ownership_cap_table_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "fcl_and_foci_executive_overview": {
          "type": "object",
          "description": "High-level DCSA Facility Clearance (FCL) eligibility verdict, FOCI severity tier, and recommended mitigation instrument."
        },
        "dd254_block10_and_11_safeguarding_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Block-by-block audit of DD Form 254 Block 10, 11, and 13 classified access, safeguarding, COMSEC, SCI, and SIPRNet mandates under 32 CFR Part 117."
        },
        "sf328_foreign_interest_factor_audit": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Evaluation of Standard Form 328 (Certificate Pertaining to Foreign Interests) triggers across foreign equity, LP feeders, board seats, debt, and revenue."
        },
        "dcsa_foci_mitigation_agreement_blueprint": {
          "type": "object",
          "description": "Structured DCSA FOCI mitigation blueprint (Board Resolution, SCA, SSA, or Proxy/Voting Trust) with Outside Director, ECP, and TCP controls."
        },
        "kmp_exclusion_resolution_and_nisp_emass_checklist": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Step-by-step Key Management Personnel (KMP) List, Board Exclusion Resolution, DISS, and NISP eMASS submission checklist."
        }
      }
    }
  },
  {
    "name": "generate_small_business_participation",
    "title": "Generate FAR 52.219-9 Small Business Subcontracting Plan & eSRS Goals",
    "description": "Calculate Small Business subcontracting dollar and percentage goals across SB, SDB/8(a), WOSB, SDVOSB, and HUBZone categories (under both % of Total Subcontracted Dollars and % of Total Contract Value baselines), draft all 15 mandatory elements of a FAR 52.219-9 Small Business Subcontracting Plan and DFARS 252.219-7003 Small Business Participation Commitment Document (SBPCD), and structure eSRS.gov ISR/SSR reporting and FAR 52.219-16 Liquidated Damages good-faith effort controls. This is a read-only, stateless, non-destructive subcontracting compliance and goal calculator (requires X-RapidAPI-Key; `solicitation_subcontracting_and_clin_text` accepts 20 to 45,000 characters, while `plan_type_and_regulatory_regime` and `agency_socioeconomic_goal_benchmarks` calibrate Individual, Master, or Commercial Subcontracting Plans against DoD or Civilian SBA statutory targets). Use this tool when preparing a Large Business Prime FAR 52.219-9 Small Business Subcontracting Plan, DFARS 252.219-7003 Small Business Participation Volume, or eSRS ISR/SSR goal calculation; use `generate_teaming_strategy` instead when a Small Business Prime needs a 13 CFR 125.6 (50% Rule) Limitations on Subcontracting workshare split, or `generate_sources_sought_response` for pre-RFP Rule-of-Two set-aside shaping.",
    "annotations": {
      "title": "Generate FAR 52.219-9 Small Business Subcontracting Plan & eSRS Goals",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "solicitation_subcontracting_and_clin_text": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "Total contract ceiling, Base + Option period breakdown, total planned subcontracted dollars, RFP Section L/M Small Business Participation factor targets, and named subcontractor commitments (20 to 45,000 characters)."
        },
        "plan_type_and_regulatory_regime": {
          "type": "string",
          "default": "Individual_Subcontracting_Plan_FAR_52_219_9_And_DFARS_252_219_7003",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Subcontracting Plan structure: Individual Plan, Master Plan + Individual Goals, or Commercial Subcontracting Plan under FAR 52.219-9 / DFARS 252.219-7003 (defaults to 'Individual_Subcontracting_Plan_FAR_52_219_9_And_DFARS_252_219_7003')."
        },
        "agency_socioeconomic_goal_benchmarks": {
          "type": "string",
          "default": "DoD_23Pct_SB_5Pct_SDB_5Pct_WOSB_5Pct_SDVOSB_3Pct_HUBZone",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Agency statutory or RFP-mandated small business subcontracting goal percentages across SB, SDB/8(a), WOSB, SDVOSB, and HUBZone (defaults to 'DoD_23Pct_SB_5Pct_SDB_5Pct_WOSB_5Pct_SDVOSB_3Pct_HUBZone')."
        }
      },
      "required": [
        "solicitation_subcontracting_and_clin_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "subcontracting_plan_overview": {
          "type": "object",
          "description": "Executive summary and dual-baseline financial breakdown of total contract value vs. total subcontracted spend."
        },
        "socioeconomic_category_goal_table": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Socioeconomic subcontracting goal breakdown across SB, SDB/8(a), WOSB, SDVOSB, and HUBZone showing both % of subcontracted spend and % of total contract value."
        },
        "far_52_219_9_15_element_compliance_narratives": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Drafted compliance narratives covering the 15 mandatory elements of FAR 52.219-9(d)."
        },
        "esrs_isr_ssr_reporting_and_good_faith_effort_controls": {
          "type": "object",
          "description": "eSRS.gov ISR/SSR reporting calendar, FAR 52.219-16 Liquidated Damages good-faith effort controls, and outreach procedures."
        },
        "dfars_small_business_participation_commitment_summary": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Actionable checklist for DFARS 252.219-7003 Small Business Participation Commitment Document (SBPCD) enforceability and bilateral teaming agreements."
        }
      }
    }
  },
  {
    "name": "generate_data_rights_assertion_table",
    "title": "Generate DFARS 252.227-7017 & FAR 52.227-14 IP & Data Rights Assertion Table",
    "description": "Audit software components, AI/ML models and weights, firmware, technical data packages, and CDRL deliverables by development funding history (100% private expense, SBIR/STTR, mixed funding, or government-funded) to generate a 4-column DFARS 252.227-7017 Data Rights Assertion Table, verbatim DFARS 252.227-7013/7014/7018 and FAR 52.227-14 restrictive marking legends, a 10 U.S.C. 4401 Modular Open Systems Approach (MOSA) boundary and DFARS 252.227-7027 deferred-ordering protection plan, and a pre-award IP negotiation checklist. This is a read-only, stateless, non-destructive Government Contracts IP compliance generator (requires X-RapidAPI-Key; `software_modules_and_cdrl_deliverables_text` accepts 20 to 45,000 characters, while `governing_acquisition_regime` and `modular_open_systems_approach_mosa_context` calibrate DoD DFARS vs. Civilian FAR data rights rules and 10 U.S.C. 4401 open interface boundaries). Use this tool when building a proposal's DFARS 252.227-7017 / FAR 52.227-14 Data Rights Assertion Table, verbatim restrictive legends, or MOSA IP segregation plan; use `generate_sbir_sttr_commercialization` instead for full SBIR/STTR Phase I-III work plans, or `scan_far_dfars_clauses` for general Section I FAR/DFARS clause scanning.",
    "annotations": {
      "title": "Generate DFARS 252.227-7017 & FAR 52.227-14 IP & Data Rights Assertion Table",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "software_modules_and_cdrl_deliverables_text": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "Inventory of software components, AI/ML models, weights, firmware, technical data packages, and CDRL deliverables with their development funding history (100% private expense, mixed funding, SBIR/STTR, or government-funded; 20 to 45,000 characters)."
        },
        "governing_acquisition_regime": {
          "type": "string",
          "default": "DoD_DFARS_252_227_7013_7014_7015_7017_And_7018",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Applicable IP clause framework: DoD DFARS 252.227-7013/7014/7015/7017/7018 (SBIR) or Civilian FAR 52.227-14 / 52.227-19 (defaults to 'DoD_DFARS_252_227_7013_7014_7015_7017_And_7018')."
        },
        "modular_open_systems_approach_mosa_context": {
          "type": "string",
          "default": "MOSA_Open_API_Boundary_Preserving_Proprietary_Core_Algorithms",
          "minLength": 2,
          "maxLength": 2000,
          "description": "10 U.S.C. 4401 Modular Open Systems Approach (MOSA) interface strategy separating open APIs/form-fit-function data from proprietary source code and model weights (defaults to 'MOSA_Open_API_Boundary_Preserving_Proprietary_Core_Algorithms')."
        }
      },
      "required": [
        "software_modules_and_cdrl_deliverables_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "ip_strategy_executive_overview": {
          "type": "object",
          "description": "Executive summary of the data rights assertion posture, background IP protection, and MOSA alignment."
        },
        "dfars_252_227_7017_assertion_table": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Complete 4-column DFARS 252.227-7017 Identification and Assertion of Use, Release, or Disclosure Restrictions table."
        },
        "restrictive_marking_and_legend_templates": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Verbatim DFARS/FAR restrictive legends and placement instructions for source code, binaries, and technical data deliverables."
        },
        "mosa_and_deferred_ordering_protection_plan": {
          "type": "object",
          "description": "10 U.S.C. \u00a7 4401 MOSA interface boundary plan, black-box encapsulation strategy, and DFARS 252.227-7027/7037 audit defense."
        },
        "pre_award_ip_negotiation_checklist": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Pre-award checklist for submitting the signed DFARS 252.227-7017 attachment with the proposal and negotiating Specially Negotiated License Rights."
        }
      }
    }
  },
  {
    "name": "generate_capture_black_hat_review",
    "title": "Generate GovCon Black-Hat Competitive Review & Ethical Ghosting Statements",
    "description": "Conduct a Shipley Black-Hat competitive intelligence simulation on a target solicitation and incumbent contractor, returning a Black-Hat executive assessment with unseating probability (0-100%), simulated competitor Black-Hat profiles (predicted bid strategy, pricing/wrap-rate posture, exploitable vulnerabilities, and counter-strategies), paste-ready Shipley ethical ghosting statements mapped to RFP Section L/M evaluation factors, an incumbent recompete vulnerability matrix (transition risk neutralizer, technical debt exposure, PTW wrap-rate wedge, and Contracting Officer shaping questions), and Red Team evaluator scoring triggers. This is a read-only, stateless, non-destructive capture intelligence generator (requires X-RapidAPI-Key; `solicitation_and_incumbent_context_text` accepts 20 to 45,000 characters, while `bidder_discriminators_and_proof_points` and `evaluation_type_and_posture` tailor ghosting prose across Best-Value Tradeoff and LPTA competitions). Use this tool when running a pre-RFP or pre-proposal Black-Hat competitive review to expose incumbent weaknesses and draft Shipley ethical ghosting language; use `match_capability_statement` instead for an initial Gate-1 Bid/No-Bid Pwin score, or `generate_igce_price_to_win` for quantitative LCAT and wrap-rate sensitivity modeling.",
    "annotations": {
      "title": "Generate GovCon Black-Hat Competitive Review & Ethical Ghosting Statements",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "solicitation_and_incumbent_context_text": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "Target RFP scope, Section M evaluation weights, incumbent contractor name/PIID, historical award ceiling, known incumbent pain points (SLA misses, turnover, legacy tech debt), and likely competitor bidders (20 to 45,000 characters)."
        },
        "bidder_discriminators_and_proof_points": {
          "type": "string",
          "default": "Cleared_Automation_First_Team_With_Zero_Trust_cATO_And_Lower_Wrap_Rate",
          "minLength": 2,
          "maxLength": 4000,
          "description": "Bidder's technical discriminators, proprietary accelerators, past performance metrics, socio-economic status, and wrap-rate / PTW advantages (defaults to 'Cleared_Automation_First_Team_With_Zero_Trust_cATO_And_Lower_Wrap_Rate')."
        },
        "evaluation_type_and_posture": {
          "type": "string",
          "default": "Challenger_Unseating_Incumbent_Best_Value_Tradeoff",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Capture posture and source selection method (e.g., Challenger Unseating Incumbent under Best-Value Tradeoff, Incumbent Defending Recompete, or LPTA; defaults to 'Challenger_Unseating_Incumbent_Best_Value_Tradeoff')."
        }
      },
      "required": [
        "solicitation_and_incumbent_context_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "black_hat_executive_assessment": {
          "type": "object",
          "description": "High-level Black-Hat competitive intelligence summary, unseating probability, and primary win strategy."
        },
        "competitor_black_hat_profiles": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Simulated Black-Hat profiles for the incumbent and top challenger archetypes with exploitable vulnerabilities and counter-strategies."
        },
        "shipley_ethical_ghosting_statements": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready Shipley ethical ghosting statements mapped to RFP Section L/M evaluation factors."
        },
        "incumbent_recompete_vulnerability_matrix": {
          "type": "object",
          "description": "Tactical playbook neutralizing incumbent transition advantages, exposing technical debt, and shaping Q&A amendments."
        },
        "red_team_evaluator_scoring_triggers": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Concrete proof points and callout boxes designed to earn formal SSEB 'Significant Strengths' under FAR 15.305."
        }
      }
    }
  },
  {
    "name": "generate_post_award_cpar_rebuttal",
    "title": "Generate FAR 42.1503 CPARS Self-Assessment & 14-Day Reviewing Official Rebuttal",
    "description": "Transform contract performance metrics (SLA attainment, CDRL on-time delivery, cost variance, key personnel stability, small business utilization) and Assessing Official (AO) draft CPAR narratives into a FAR 42.1503 Table 42-1 justified CPARS Self-Assessment Package, factor-by-factor rating upgrade narratives (Quality, Schedule, Cost Control, Management, Small Business), a formal 14-Calendar-Day Reviewing Official (RO) Rebuttal Brief correcting factual omissions and excusable Government GFE delays, and a COR Evidence Binder checklist. This is a read-only, stateless, non-destructive post-award past-performance generator (requires X-RapidAPI-Key; `contract_metrics_and_assessing_official_text` accepts 20 to 45,000 characters, while `cpar_submission_mode` and `target_far_42_1503_rating_goal` calibrate proactive annual self-assessments vs. 14-day non-concurrence rebuttals under FAR 42.1503(d)). Use this tool when preparing an annual CPARS Self-Assessment for the COR/Assessing Official or rebutting an unfavorable draft CPAR within the statutory 14-calendar-day window; use `generate_cpars_past_performance` instead when formatting already-completed historical contracts into a Proposal Volume III Past Performance submission, or `analyze_debriefing_bid_protest` for FAR 15.506 post-award debriefings and GAO bid protests.",
    "annotations": {
      "title": "Generate FAR 42.1503 CPARS Self-Assessment & 14-Day Reviewing Official Rebuttal",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "contract_metrics_and_assessing_official_text": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "Contract performance metrics (SLA attainment, CDRL on-time delivery, cost variance, key personnel fill rate, small business goals) and, if rebutting a draft CPAR, the Assessing Official's draft ratings and narrative (20 to 45,000 characters)."
        },
        "cpar_submission_mode": {
          "type": "string",
          "default": "Proactive_Annual_CPARS_Self_Assessment_And_14_Day_Rebuttal_Package",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Submission mode under FAR 42.1503: Proactive Annual Self-Assessment Package, 14-Calendar-Day Draft CPAR Rebuttal to Reviewing Official, or Both (defaults to 'Proactive_Annual_CPARS_Self_Assessment_And_14_Day_Rebuttal_Package')."
        },
        "target_far_42_1503_rating_goal": {
          "type": "string",
          "default": "Upgrade_To_Exceptional_And_Very_Good_With_Positive_Rec",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target FAR 42.1503 Table 42-1 rating outcome across Quality, Schedule, Cost Control, Management, Small Business, and Regulatory Compliance (defaults to 'Upgrade_To_Exceptional_And_Very_Good_With_Positive_Rec')."
        }
      },
      "required": [
        "contract_metrics_and_assessing_official_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "cpar_evaluation_overview": {
          "type": "object",
          "description": "High-level FAR 42.1503 CPARS assessment, 14-day deadline rule, and rating upgrade feasibility."
        },
        "far_42_1503_factor_by_factor_narratives": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Factor-by-factor CPARS narratives mapped to FAR 42.1503 Table 42-1 across Quality, Schedule, Cost Control, Management, and Small Business."
        },
        "fourteen_day_reviewing_official_rebuttal_brief": {
          "type": "object",
          "description": "Formal 14-Calendar-Day Reviewing Official rebuttal brief correcting factual errors and excusable Government delays."
        },
        "cor_evidence_binder_checklist": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Checklist of objective artifacts (CDRL acceptance receipts, monthly IPR slides, WAWF vouchers, eSRS confirmations, COR emails) to attach to the CPARS submission."
        }
      }
    }
  },
  {
    "name": "generate_rea_equitable_adjustment",
    "title": "Generate FAR Part 43 REA, Constructive Change & Eichleay CDA Claim Package",
    "description": "Analyze post-award scope creep, out-of-scope COR technical directions, Government-Furnished Equipment/Information (GFE/GFI) or ATO delays, and stop-work orders under FAR 52.243-1/2/3/4, FAR 52.242-14/15/17, and the Contract Disputes Act (41 U.S.C. 7101) to generate a Request for Equitable Adjustment (REA) or Certified CDA Claim package containing a 5-element constructive change proof, a DCAA-auditable Quantum Cost Schedule (direct labor, indirect burden, Eichleay unabsorbed home office overhead, FAR 31.205-33 allowable REA preparation costs, and DFARS 215.404-71 weighted guidelines profit), an Eichleay 3-step standby overhead and CPM schedule extension analysis, and verbatim DFARS 252.243-7002 and CDA 41 U.S.C. 7103 certifications. This is a read-only, stateless, non-destructive post-award contract claims and quantum analysis generator (requires X-RapidAPI-Key; `contract_change_and_delay_facts` accepts 20 to 45,000 characters, while `remedy_clause_and_submission_type` and `quantum_pricing_methodology` calibrate non-adversarial FAR Part 43 REAs vs. interest-bearing CDA claims). Use this tool when quantifying post-award constructive changes, Government delays, or Eichleay standby overhead for a Contracting Officer REA or CDA claim; use `analyze_debriefing_bid_protest` instead for pre-award or post-award GAO/COFC bid protests under FAR 15.506, or `generate_post_award_cpar_rebuttal` for FAR 42.1503 CPARS rating rebuttals.",
    "annotations": {
      "title": "Generate FAR Part 43 REA, Constructive Change & Eichleay CDA Claim Package",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "contract_change_and_delay_facts": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "Chronology of out-of-scope COR/CO technical directions, Government-furnished equipment/information (GFE/GFI) or ATO delays, stop-work orders, standby labor costs, and company overhead figures (20 to 45,000 characters)."
        },
        "remedy_clause_and_submission_type": {
          "type": "string",
          "default": "FAR_52_243_1_Constructive_Change_And_FAR_52_242_17_Delay_Non_Adversarial_REA",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target remedy clause and submission posture (e.g., Non-Adversarial FAR Part 43 REA under FAR 52.243-1/2/3/4 & DFARS 252.243-7002 vs. Certified CDA Claim under 41 U.S.C. 7103; defaults to 'FAR_52_243_1_Constructive_Change_And_FAR_52_242_17_Delay_Non_Adversarial_REA')."
        },
        "quantum_pricing_methodology": {
          "type": "string",
          "default": "Segregated_Actual_Labor_Hours_Plus_Eichleay_Standby_Overhead_And_FAR_31_205_33_Prep_Costs",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Quantum pricing method (Segregated Actual Costs, Modified Total Cost, Jury Verdict Method, Eichleay Unabsorbed Home Office Overhead, and FAR 31.205-33 REA Preparation Cost recovery; defaults to 'Segregated_Actual_Labor_Hours_Plus_Eichleay_Standby_Overhead_And_FAR_31_205_33_Prep_Costs')."
        }
      },
      "required": [
        "contract_change_and_delay_facts"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "rea_entitlement_executive_overview": {
          "type": "object",
          "description": "High-level REA vs. CDA legal posture, 5-element constructive change proof, and total recommended adjustment."
        },
        "rea_quantum_cost_schedule": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "DCAA-auditable Quantum Cost Breakdown across direct labor, indirect pools, Eichleay standby overhead, REA preparation costs (FAR 31.205-33), and weighted guidelines profit."
        },
        "eichleay_and_delay_schedule_analysis": {
          "type": "object",
          "description": "Eichleay 3-step unabsorbed home office overhead calculation and Critical Path Method (CPM) schedule extension justification."
        },
        "statutory_certification_and_notice_block": {
          "type": "object",
          "description": "Verbatim DFARS 252.243-7002 REA and CDA 41 U.S.C. 7103 certifications, timely notice defense, and SF-30 reservation-of-rights language."
        }
      }
    }
  },
  {
    "name": "generate_mentor_protege_jv_agreement",
    "title": "Generate SBA Mentor-Prot\u00e9g\u00e9 (13 CFR 125.9) & Joint Venture Operating Agreement",
    "description": "Audit and generate SBA All-Small Mentor-Prot\u00e9g\u00e9 Program Agreements (13 CFR 125.9) and unpopulated Joint Venture Operating Agreements (13 CFR 125.8, 121.103(h), 124.513 8(a), 126.616 HUBZone, 127.506 WOSB, 128.402 SDVOSB), returning an SBA affiliation safe-harbor overview, all mandatory 13 CFR 125.8(b)(2) Operating Agreement clauses (Prot\u00e9g\u00e9 Managing Venturer & Responsible Manager controls neutralizing OHA negative-control protests, >= 40% substantive Prot\u00e9g\u00e9 workshare, commensurate profit distribution, dual-signature JV bank account, and equipment/labor schedules), a quantitative 40% Prot\u00e9g\u00e9 workshare and FAR 52.219-14 audit, and a 6-year SBA MPP Developmental Plan blueprint. This is a read-only, stateless, non-destructive GovCon corporate structuring and SBA compliance generator (requires X-RapidAPI-Key; `mentor_and_protege_profile_text` accepts 20 to 45,000 characters, while `target_set_aside_and_jv_type` and `agreement_deliverable_scope` calibrate SBA socio-economic JV rules and developmental assistance plans). Use this tool when drafting or auditing an SBA 13 CFR 125.8 Joint Venture Operating Agreement or 13 CFR 125.9 Mentor-Prot\u00e9g\u00e9 Developmental Plan to survive OHA size/status protests; use `generate_teaming_strategy` instead for standard FAR Subpart 9.6 Prime/Subcontractor Teaming Agreements, or `generate_small_business_participation` for Large Business Prime FAR 52.219-9 Subcontracting Plans.",
    "annotations": {
      "title": "Generate SBA Mentor-Prot\u00e9g\u00e9 (13 CFR 125.9) & Joint Venture Operating Agreement",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "mentor_and_protege_profile_text": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "Profiles of the Prot\u00e9g\u00e9 (Managing Venturer) and Mentor (Partner Venturer), socioeconomic certifications (Small, 8(a), SDVOSB, WOSB, HUBZone), target solicitation details, and proposed workshare split (20 to 45,000 characters)."
        },
        "target_set_aside_and_jv_type": {
          "type": "string",
          "default": "Unpopulated_SDVOSB_And_All_Small_MPP_Joint_Venture_13_CFR_125_8_And_128_402",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target socioeconomic set-aside and SBA JV regulation (13 CFR 125.8 Small Business, 128.402 SDVOSB, 124.513 8(a), 127.506 WOSB, or 126.616 HUBZone; defaults to 'Unpopulated_SDVOSB_And_All_Small_MPP_Joint_Venture_13_CFR_125_8_And_128_402')."
        },
        "agreement_deliverable_scope": {
          "type": "string",
          "default": "Full_13_CFR_125_8_JV_Operating_Agreement_Clauses_Plus_13_CFR_125_9_MPP_Developmental_Plan",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Deliverable scope: 13 CFR 125.8(b)(2) Joint Venture Operating Agreement + Solicitation Addendum Clauses, 13 CFR 125.9 SBA Mentor-Prot\u00e9g\u00e9 Developmental Plan, and OHA Size/Status Protest Pre-Audit (defaults to 'Full_13_CFR_125_8_JV_Operating_Agreement_Clauses_Plus_13_CFR_125_9_MPP_Developmental_Plan')."
        }
      },
      "required": [
        "mentor_and_protege_profile_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "mentor_protege_and_jv_overview": {
          "type": "object",
          "description": "Executive overview of SBA regulatory compliance, unpopulated LLC structure, affiliation safe harbor, and 2-year rule."
        },
        "thirteen_cfr_125_8_mandatory_clauses": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Complete set of 13 CFR 125.8(b)(2) mandatory Joint Venture Operating Agreement clauses neutralizing OHA protest traps."
        },
        "forty_percent_workshare_and_limitations_audit": {
          "type": "object",
          "description": "Quantitative audit of FAR 52.219-14 Limitations on Subcontracting and the mandatory >= 40% Prot\u00e9g\u00e9 workshare rule."
        },
        "sba_mpp_developmental_plan_blueprint": {
          "type": "object",
          "description": "SBA All-Small Mentor-Prot\u00e9g\u00e9 Program (13 CFR 125.9) developmental assistance blueprint and term compliance check."
        }
      }
    }
  },
  {
    "name": "audit_service_contract_act_wage",
    "title": "Map RFP LCATs to DOL SCA Wage Determinations & Audit Fringe / FAR 52.222-43 Compliance",
    "description": "Map solicitation labor categories (LCATs) to Department of Labor (DOL) SAM.gov Service Contract Act (SCA / FAR 52.222-41) Directory of Occupations 5-digit codes and Davis-Bacon Act classifications, audit FLSA 29 CFR Part 541 exempt vs. non-exempt status, compute mandatory Health & Welfare (H&W) fringe obligations (Standard vs. EO 13706 Paid Sick Leave), Vacation (including EO 14055 predecessor seniority credit), and 11 Federal Holidays hourly loads, and generate an SF 1444 conformance and FAR 52.222-43 Option Year price adjustment compliance narrative. This is a read-only, stateless, non-destructive labor compliance and pricing audit call (requires X-RapidAPI-Key; `rfp_labor_categories_and_locality_text` accepts 20 to 45,000 characters, while `wage_determination_and_fringe_mode` and `audit_objective` calibrate H&W rates, holiday counts, and FAR 52.222-43 zero-escalation rules). Use this tool when mapping RFP labor categories to DOL SCA Wage Determinations, calculating H&W and vacation fringe floors, or preparing SF 1444 conformance requests; use `generate_igce_price_to_win` instead for full multi-year CLIN wrap-rate and Price-to-Win modeling, or `match_key_personnel` to evaluate candidate resumes against LCAT education/experience requirements.",
    "annotations": {
      "title": "Map RFP LCATs to DOL SCA Wage Determinations & Audit Fringe / FAR 52.222-43 Compliance",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "rfp_labor_categories_and_locality_text": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "Solicitation labor categories (LCATs), job duties, proposed base hourly rates, place of performance county/MSA, and applicable DOL Wage Determination or CBA details (20 to 45,000 characters)."
        },
        "wage_determination_and_fringe_mode": {
          "type": "string",
          "default": "SAM_DOL_SCA_Directory_6th_Ed_With_EO_13706_HW_And_11_Federal_Holidays",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Wage determination and fringe calculation mode (Standard H&W vs. EO 13706 Paid Sick Leave H&W, 11 Federal Holidays including Juneteenth, and predecessor seniority vacation accrual; defaults to 'SAM_DOL_SCA_Directory_6th_Ed_With_EO_13706_HW_And_11_Federal_Holidays')."
        },
        "audit_objective": {
          "type": "string",
          "default": "Map_DOL_Codes_Verify_Wage_Floors_And_Calculate_FAR_52_222_43_Baseline",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Audit objective: DOL 5-digit Occupation Code mapping, FLSA 29 CFR 541 exemption check, H&W/Vacation/Holiday build-up, SF 1444 conformance check, and FAR 52.222-43 price adjustment baseline (defaults to 'Map_DOL_Codes_Verify_Wage_Floors_And_Calculate_FAR_52_222_43_Baseline')."
        }
      },
      "required": [
        "rfp_labor_categories_and_locality_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "sca_wage_compliance_overview": {
          "type": "object",
          "description": "High-level SCA/DBA statutory compliance overview, locality Wage Determination profile, and H&W fringe rate."
        },
        "sca_labor_category_mappings": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "LCAT-by-LCAT mapping to DOL SCA Directory of Occupations codes, FLSA exemption audit, and total minimum hourly cost floor."
        },
        "far_52_222_43_price_adjustment_and_sf1444_plan": {
          "type": "object",
          "description": "FAR 52.222-43 Option Year price adjustment protection rules, SF 1444 conformance playbook, and incumbent seniority vacation audit."
        },
        "cost_volume_boe_sca_narrative_template": {
          "type": "string",
          "description": "Paste-ready Cost Volume Narrative warranting SCA compliance, zero Option Year SCA escalation contingency per FAR 52.222-43, and bona fide fringe benefit plan administration."
        }
      }
    }
  },
  {
    "name": "generate_evms_ipmdr_variance_analysis",
    "title": "Calculate EVMS Metrics (CPI, SPI, TCPI, IEAC) & Generate IPMDR Format 5 Narratives",
    "description": "Calculate Earned Value Management System (EVMS) performance indices (CV, CV%, SV, SV%, CPI, SPI, TCPI_BAC, VAC, and 3-method Independent Estimate at Completion [IEAC]) across Work Breakdown Structure (WBS) Control Accounts under DFARS 252.234-7001/7002, FAR 52.234-4, and NDIA EIA-748-D (32 Guidelines), and generate ready-to-submit DI-MGMT-81861C IPMDR Format 5 Root-Cause Variance Analysis (isolating Rate vs. Usage and Schedule drivers), Critical Path impact assessments, and Control Account Manager (CAM) Corrective Action Plans with Estimated Completion Dates (ECDs). This is a read-only, stateless, non-destructive earned-value calculation and CDRL narrative generator (requires X-RapidAPI-Key; `wbs_control_account_metrics_text` accepts 20 to 45,000 characters, while `variance_reporting_thresholds` and `evms_reporting_standard` calibrate CDRL breach flags and EIA-748 Management Reserve / baseline integrity audits). Use this tool when computing WBS Control Account CPI/SPI/TCPI/IEAC metrics and drafting monthly IPMR/IPMDR Format 5 Variance Analysis CDRL narratives; use `audit_dcaa_accounting_sf1408` instead for pre-award DCAA SF 1408 accounting system adequacy, or `generate_quality_assurance_qasp` for FAR 37.6 QASP and SLA surveillance matrices.",
    "annotations": {
      "title": "Calculate EVMS Metrics (CPI, SPI, TCPI, IEAC) & Generate IPMDR Format 5 Narratives",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "wbs_control_account_metrics_text": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "WBS Control Account metrics (BCWS/PV, BCWP/EV, ACWP/AC, BAC), technical/schedule/rate variance drivers, Management Reserve (MR) balance, and contract reporting thresholds (20 to 45,000 characters)."
        },
        "variance_reporting_thresholds": {
          "type": "string",
          "default": "Plus_Minus_10_Percent_And_50000_USD_Cumulative_Format_5",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Contract CDRL variance reporting thresholds (e.g., +/- 10% and +/- $50,000 current period or cumulative CV/SV; defaults to 'Plus_Minus_10_Percent_And_50000_USD_Cumulative_Format_5')."
        },
        "evms_reporting_standard": {
          "type": "string",
          "default": "DI_MGMT_81861C_IPMDR_Format_5_And_EIA_748_D_32_Guidelines",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target EVMS reporting DID and standard (DI-MGMT-81861C IPMDR Format 5, DFARS 252.234-7002, and EIA-748-D 32 Guidelines; defaults to 'DI_MGMT_81861C_IPMDR_Format_5_And_EIA_748_D_32_Guidelines')."
        }
      },
      "required": [
        "wbs_control_account_metrics_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "evms_executive_program_summary": {
          "type": "object",
          "description": "Program-level EVMS rollup, CPI/SPI/TCPI realism check, and EIA-748 compliance overview."
        },
        "control_account_format_5_narratives": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Ready-to-submit IPMDR Format 5 Variance Analysis narratives with Root Cause, Impact, and CAM Corrective Action Plans for each WBS Control Account."
        },
        "ieac_and_baseline_integrity_audit": {
          "type": "object",
          "description": "3-method Independent Estimate at Completion (IEAC) comparison, Management Reserve audit, and EIA-748 baseline integrity controls."
        }
      }
    }
  },
  {
    "name": "generate_cost_accounting_cas_ds2",
    "title": "Audit CAS Coverage (Modified vs. Full CAS) & Draft CASB Form DS-1 Disclosure Sections",
    "description": "Determine Cost Accounting Standards (CAS / 48 CFR Chapter 99) exemptions vs. Modified CAS ($2M trigger contract / < $50M net CAS-covered awards) vs. Full CAS (>= $50M net CAS-covered awards or single award >= $50M) under FAR 52.230-1 through 52.230-6, audit contractor cost accounting practices against CAS 401, CAS 402, CAS 405, CAS 406, CAS 410 (Total Cost Input vs. Value-Added G&A base), and CAS 418, and generate paste-ready CASB Form DS-1 Disclosure Statement Continuation Sheet narratives across Parts I, II, III, IV, and VII plus FAR 52.230-6 General Dollar Magnitude (GDM) cost-impact governance rules. This is a read-only, stateless, non-destructive GovCon cost accounting compliance and disclosure generator (requires X-RapidAPI-Key; `contractor_accounting_and_awards_profile` accepts 20 to 45,000 characters, while `target_cas_coverage_and_ds_form` and `g_and_a_allocation_base_preference` calibrate Modified vs. Full CAS audits and CAS 410 G&A base distortion checks). Use this tool when determining FAR Part 30 CAS coverage tiers, auditing CAS 401-420 compliance, or drafting a CASB Form DS-1 Disclosure Statement; use `audit_dcaa_accounting_sf1408` instead for pre-award Standard Form 1408 accounting system surveys, or `generate_igce_price_to_win` for proposal LCAT wrap-rate pricing.",
    "annotations": {
      "title": "Audit CAS Coverage (Modified vs. Full CAS) & Draft CASB Form DS-1 Disclosure Sections",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "contractor_accounting_and_awards_profile": {
          "type": "string",
          "minLength": 20,
          "maxLength": 45000,
          "description": "Contractor business size status, prior/current year net CAS-covered awards, contract types, direct vs. indirect charging rules, Fringe/Overhead/G&A pool structures, and pass-through subcontract volume (20 to 45,000 characters)."
        },
        "target_cas_coverage_and_ds_form": {
          "type": "string",
          "default": "Full_CAS_19_Standards_Transition_And_CASB_DS1_Disclosure_Statement",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target CAS coverage evaluation and disclosure form (CAS Exemption Audit, Modified CAS 401/402/405/406, Full CAS 19 Standards, or CASB DS-1 / DS-2 Disclosure Statement preparation; defaults to 'Full_CAS_19_Standards_Transition_And_CASB_DS1_Disclosure_Statement')."
        },
        "g_and_a_allocation_base_preference": {
          "type": "string",
          "default": "Evaluate_Total_Cost_Input_TCI_vs_Value_Added_Base_Under_CAS_410",
          "minLength": 2,
          "maxLength": 2000,
          "description": "CAS 410 G&A allocation base preference (Total Cost Input [TCI], Value-Added Cost Input excluding direct material/subcontracts, or Single Element Cost Input; defaults to 'Evaluate_Total_Cost_Input_TCI_vs_Value_Added_Base_Under_CAS_410')."
        }
      },
      "required": [
        "contractor_accounting_and_awards_profile"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "cas_applicability_and_coverage_determination": {
          "type": "object",
          "description": "48 CFR 9903 CAS exemption vs. Modified CAS vs. Full CAS determination and FAR 52.230 clause mapping."
        },
        "core_cas_standards_compliance_audit": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Audit of CAS 401, CAS 402, CAS 405, CAS 406, CAS 410, and CAS 418 compliance against DCAA CAM Chapter 8."
        },
        "casb_ds1_disclosure_statement_sections": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready CASB Form DS-1 Disclosure Statement Continuation Sheet narratives across Parts I, II, III, IV, and VII."
        },
        "far_52_230_6_cost_impact_and_change_governance": {
          "type": "object",
          "description": "FAR 52.230-6 60-day CFAO advance notice rules and General Dollar Magnitude (GDM) cost-impact governance."
        }
      }
    }
  },
  {
    "name": "audit_itar_ear_export_control",
    "title": "ITAR (22 CFR 120\u2013130), EAR & Technology Control Plan (TCP) Export Compliance",
    "description": "Classify defense/dual-use technical deliverables against USML Categories (ITAR) and CCL ECCNs (EAR), flags DFARS 252.225-7048 export obligations, and generates a facility Technology Control Plan (TCP). Returns a strictly validated `ItarEarExportResponse` JSON object containing `export_jurisdiction_overview`, `usml_and_eccn_classification_matrix`, `technology_control_plan_tcp_controls`, and `deemed_export_and_ddtc_bis_licensing` grounded in 22 CFR Parts 120\u2013130 (ITAR USML Categories IV & XI), 15 CFR Parts 730\u2013774 (EAR CCL), & DFARS 252.225-7048. This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `technical_deliverables_and_rfp_export_text` accepts 15 to 45,000 characters, while `target_export_regime` and `foreign_national_and_oconus_context` calibrate the regulatory regime and threshold assumptions). Use this tool when executing ITAR (22 CFR 120\u2013130), EAR & Technology Control Plan (TCP) Export Compliance workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "ITAR (22 CFR 120\u2013130), EAR & Technology Control Plan (TCP) Export Compliance",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "technical_deliverables_and_rfp_export_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for ITAR (22 CFR 120\u2013130), EAR & Technology Control Plan (TCP) Export Compliance (15 to 45,000 characters)."
        },
        "target_export_regime": {
          "type": "string",
          "default": "ITAR_22_CFR_120_130_And_EAR_15_CFR_730_774_Dual_Audit",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'ITAR_22_CFR_120_130_And_EAR_15_CFR_730_774_Dual_Audit')."
        },
        "foreign_national_and_oconus_context": {
          "type": "string",
          "default": "U.S. Persons Only on ITAR USML Technical Data; Evaluate Deemed Export Rule (22 CFR 120.50 / 15 CFR 734.13)",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'U.S. Persons Only on ITAR USML Technical Data; Evaluate Deemed Export Rule (22 CFR 120.50 / 15 CFR 734.13)')."
        }
      },
      "required": [
        "technical_deliverables_and_rfp_export_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "export_jurisdiction_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "usml_and_eccn_classification_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "technology_control_plan_tcp_controls": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "deemed_export_and_ddtc_bis_licensing": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "generate_cdrls_did_data_deliverables",
    "title": "DoD CDRL (DD Form 1423) & Data Item Description (DID) Schedule Extractor",
    "description": "Extract all Contract Data Requirements List (CDRL / DD Form 1423) items from DoD RFPs, maps Data Item Descriptions (DIDs), Block 4 authority, submission frequencies, inspection/acceptance codes, and builds a WBS Data Delivery Calendar. Returns a strictly validated `CdrlDd1423Response` JSON object containing `cdrl_schedule_overview`, `dd_form_1423_extracted_items`, `did_tailoring_and_delivery_calendar`, and `piee_wawf_and_block18_pricing_governance` grounded in DFARS Subpart 227.71, DoD 5010.12-M (Procedures for the Acquisition and Management of Technical Data), & ASSIST DID Registry. This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `rfp_exhibit_a_cdrl_and_pws_text` accepts 15 to 45,000 characters, while `contract_award_and_pop_start_context` and `dd1423_pricing_group_strategy` calibrate the regulatory regime and threshold assumptions). Use this tool when executing DoD CDRL (DD Form 1423) & Data Item Description (DID) Schedule Extractor workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "DoD CDRL (DD Form 1423) & Data Item Description (DID) Schedule Extractor",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "rfp_exhibit_a_cdrl_and_pws_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for DoD CDRL (DD Form 1423) & Data Item Description (DID) Schedule Extractor (15 to 45,000 characters)."
        },
        "contract_award_and_pop_start_context": {
          "type": "string",
          "default": "Contract Award / Post-Award Conference (PAC) = Day 0; 12-Month Base Period + 4 Option Years",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'Contract Award / Post-Award Conference (PAC) = Day 0; 12-Month Base Period + 4 Option Years')."
        },
        "dd1423_pricing_group_strategy": {
          "type": "string",
          "default": "Map DD Form 1423 Block 18 Price Groups (Group I, II, III, IV \u2014 NSP vs. Separately Priced Data CLIN)",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'Map DD Form 1423 Block 18 Price Groups (Group I, II, III, IV \u2014 NSP vs. Separately Priced Data CLIN)')."
        }
      },
      "required": [
        "rfp_exhibit_a_cdrl_and_pws_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "cdrl_schedule_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "dd_form_1423_extracted_items": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "did_tailoring_and_delivery_calendar": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "piee_wawf_and_block18_pricing_governance": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "generate_justification_ja_sole_source",
    "title": "FAR 6.302 / FAR 8.405-6 Sole-Source Justification & Approval (J&A / LSJ) Drafter",
    "description": "Draft a complete 12-Part FAR 6.303-2 Justification & Approval (J&A), FAR 8.405-6 Limited Sources Justification (LSJ), or FAR 16.505(b)(2) Fair Opportunity Exception package for Contracting Officers. Returns a strictly validated `SoleSourceJaResponse` JSON object containing `statutory_exception_overview`, `far_6_303_2_twelve_part_ja_sections`, `unacceptable_delay_and_duplicative_cost_quantification`, and `sam_gov_posting_and_approval_routing` grounded in FAR 6.302-1 (10 U.S.C. \u00a7 3204(a)(1) / 41 U.S.C. \u00a7 3304(a)(1)), FAR 6.303-2 (12 Mandatory Content Elements), & FAR 8.405-6 / 16.505(b)(2). This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `sole_source_requirement_and_vendor_uniqueness_text` accepts 15 to 45,000 characters, while `statutory_authority_pathway` and `estimated_dollar_value_and_approval_tier` calibrate the regulatory regime and threshold assumptions). Use this tool when executing FAR 6.302 / FAR 8.405-6 Sole-Source Justification & Approval (J&A / LSJ) Drafter workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "FAR 6.302 / FAR 8.405-6 Sole-Source Justification & Approval (J&A / LSJ) Drafter",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "sole_source_requirement_and_vendor_uniqueness_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for FAR 6.302 / FAR 8.405-6 Sole-Source Justification & Approval (J&A / LSJ) Drafter (15 to 45,000 characters)."
        },
        "statutory_authority_pathway": {
          "type": "string",
          "default": "FAR_6_302_1_Only_One_Responsible_Source_10_USC_3204_a_1",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'FAR_6_302_1_Only_One_Responsible_Source_10_USC_3204_a_1')."
        },
        "estimated_dollar_value_and_approval_tier": {
          "type": "string",
          "default": "$18.5M Total Estimated Value \u2014 Competition Advocate Approval Tier ($750K to $15M / $20M DoD PEO/HCA Threshold)",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to '$18.5M Total Estimated Value \u2014 Competition Advocate Approval Tier ($750K to $15M / $20M DoD PEO/HCA Threshold)')."
        }
      },
      "required": [
        "sole_source_requirement_and_vendor_uniqueness_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "statutory_exception_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "far_6_303_2_twelve_part_ja_sections": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "unacceptable_delay_and_duplicative_cost_quantification": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "sam_gov_posting_and_approval_routing": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "audit_cyber_incident_dfars_7012",
    "title": "DFARS 252.204-7012 (72-Hour DIBNet) & CIRCIA Cyber Incident Reporting Package",
    "description": "Evaluate CUI/CDI security incidents against DFARS 252.204-7012, CISA CIRCIA, and FedRAMP incident SLAs, generating a structured 72-hour DoD DIBNet ICF report, 90-day forensic media preservation checklist, and subcontractor flow-down notifications. Returns a strictly validated `Dfars7012IncidentResponse` JSON object containing `incident_reporting_determination`, `dibnet_72_hour_icf_report_fields`, `forensic_90_day_preservation_and_sla_clock`, and `dc3_damage_assessment_and_prime_flowdown_notices` grounded in DFARS 252.204-7012(c)\u2013(m) (72-Hour DoD DIBNet Reporting & 90-Day Image Preservation), CISA CIRCIA (6 U.S.C. \u00a7 681b), & NIST SP 800-61r2. This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `security_incident_telemetry_and_affected_contracts_text` accepts 15 to 45,000 characters, while `regulatory_reporting_regimes` and `assurance_certificate_and_cloud_posture` calibrate the regulatory regime and threshold assumptions). Use this tool when executing DFARS 252.204-7012 (72-Hour DIBNet) & CIRCIA Cyber Incident Reporting Package workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "DFARS 252.204-7012 (72-Hour DIBNet) & CIRCIA Cyber Incident Reporting Package",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "security_incident_telemetry_and_affected_contracts_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for DFARS 252.204-7012 (72-Hour DIBNet) & CIRCIA Cyber Incident Reporting Package (15 to 45,000 characters)."
        },
        "regulatory_reporting_regimes": {
          "type": "string",
          "default": "DFARS_252_204_7012_72Hr_DIBNet_Plus_CISA_CIRCIA_72Hr_And_FedRAMP_US_CERT",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'DFARS_252_204_7012_72Hr_DIBNet_Plus_CISA_CIRCIA_72Hr_And_FedRAMP_US_CERT')."
        },
        "assurance_certificate_and_cloud_posture": {
          "type": "string",
          "default": "DoD ECA Medium Token Assurance Certificate Active; Enclave Hosted on AWS GovCloud (US) FedRAMP High / IL5",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'DoD ECA Medium Token Assurance Certificate Active; Enclave Hosted on AWS GovCloud (US) FedRAMP High / IL5')."
        }
      },
      "required": [
        "security_incident_telemetry_and_affected_contracts_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "incident_reporting_determination": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "dibnet_72_hour_icf_report_fields": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "forensic_90_day_preservation_and_sla_clock": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "dc3_damage_assessment_and_prime_flowdown_notices": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "generate_doe_national_lab_mando_subcontract",
    "title": "DOE / NNSA National Lab M&O Subcontract & DEAR (48 CFR Ch. 9) Compliance Auditor",
    "description": "Audit DOE/NNSA Management & Operating (M&O) National Laboratory solicitations (Sandia, LANL, ORNL, LLNL) for DEAR 48 CFR 952/970 clauses, Q-Clearance / L-Clearance requirements, Foreign National Unclassified Visits (DOE O 142.3B), and patent waivers. Returns a strictly validated `DoeDearSubcontractResponse` JSON object containing `doe_national_lab_subcontract_overview`, `dear_48_cfr_952_970_clause_audit_matrix`, `q_l_clearance_foci_and_doe_o_142_3b_controls`, and `patent_rights_and_crada_tech_transfer_strategy` grounded in 48 CFR Chapter 9 (DEAR Parts 952 & 970), 10 CFR Part 710 (Q/L Access Authorizations), DOE O 142.3B, & DOE O 470.4B. This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `doe_national_lab_rfp_and_dear_clauses_text` accepts 15 to 45,000 characters, while `target_national_lab_and_mando_prime` and `clearance_and_ip_posture` calibrate the regulatory regime and threshold assumptions). Use this tool when executing DOE / NNSA National Lab M&O Subcontract & DEAR (48 CFR Ch. 9) Compliance Auditor workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "DOE / NNSA National Lab M&O Subcontract & DEAR (48 CFR Ch. 9) Compliance Auditor",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "doe_national_lab_rfp_and_dear_clauses_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for DOE / NNSA National Lab M&O Subcontract & DEAR (48 CFR Ch. 9) Compliance Auditor (15 to 45,000 characters)."
        },
        "target_national_lab_and_mando_prime": {
          "type": "string",
          "default": "Sandia_National_Laboratories_NTESS_And_Los_Alamos_National_Lab_Triad_NNSA",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'Sandia_National_Laboratories_NTESS_And_Los_Alamos_National_Lab_Triad_NNSA')."
        },
        "clearance_and_ip_posture": {
          "type": "string",
          "default": "DOE Q-Clearance / L-Clearance Cross-Over from DoD TS/Secret + Domestic Small Business Patent Retention (DEAR 952.227-11)",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'DOE Q-Clearance / L-Clearance Cross-Over from DoD TS/Secret + Domestic Small Business Patent Retention (DEAR 952.227-11)')."
        }
      },
      "required": [
        "doe_national_lab_rfp_and_dear_clauses_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "doe_national_lab_subcontract_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "dear_48_cfr_952_970_clause_audit_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "q_l_clearance_foci_and_doe_o_142_3b_controls": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "patent_rights_and_crada_tech_transfer_strategy": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "generate_gwac_task_order_fair_opportunity",
    "title": "GWAC / IDIQ Task Order Fair Opportunity (FAR 16.505) & Pool Selection Optimizer",
    "description": "Match task order TORFPs across OASIS+, GSA Polaris, 8(a) STARS III, VETS 2, NASA SEWP, and NITAAC CIO-SP3/4 against vendor contract pools, scoring self-scoring scorecard matrices and drafting rapid 5-day TORFP responses. Returns a strictly validated `GwacTaskOrderResponse` JSON object containing `gwac_fair_opportunity_overview`, `vehicle_pool_and_scorecard_alignment_matrix`, `rapid_torfp_technical_and_staffing_sections`, and `far_16_505_protest_thresholds_and_ombudsman_governance` grounded in FAR 16.505(b)(1) (Fair Opportunity), FAR 16.505(a)(10) ($10M Civilian / $25M DoD Task Order Protest Jurisdictional Cap), & GSAR 552.216-74. This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `torfp_scope_and_vehicle_holders_text` accepts 15 to 45,000 characters, while `target_gwac_or_mac_vehicles` and `turnaround_window_and_evaluation_mode` calibrate the regulatory regime and threshold assumptions). Use this tool when executing GWAC / IDIQ Task Order Fair Opportunity (FAR 16.505) & Pool Selection Optimizer workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "GWAC / IDIQ Task Order Fair Opportunity (FAR 16.505) & Pool Selection Optimizer",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "torfp_scope_and_vehicle_holders_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for GWAC / IDIQ Task Order Fair Opportunity (FAR 16.505) & Pool Selection Optimizer (15 to 45,000 characters)."
        },
        "target_gwac_or_mac_vehicles": {
          "type": "string",
          "default": "GSA_OASIS_Plus_Unrestricted_And_SB_GSA_Polaris_8a_STARS_III_VETS_2_CIO_SP3",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'GSA_OASIS_Plus_Unrestricted_And_SB_GSA_Polaris_8a_STARS_III_VETS_2_CIO_SP3')."
        },
        "turnaround_window_and_evaluation_mode": {
          "type": "string",
          "default": "5-Business-Day Rapid TORFP Turnaround | FAR 16.505(b)(1) Highest Technically Rated Offeror (HTRO) / Fair Opportunity",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to '5-Business-Day Rapid TORFP Turnaround | FAR 16.505(b)(1) Highest Technically Rated Offeror (HTRO) / Fair Opportunity')."
        }
      },
      "required": [
        "torfp_scope_and_vehicle_holders_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "gwac_fair_opportunity_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "vehicle_pool_and_scorecard_alignment_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "rapid_torfp_technical_and_staffing_sections": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "far_16_505_protest_thresholds_and_ombudsman_governance": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "audit_govt_furnished_property_gfp",
    "title": "Government-Furnished Property (GFP / FAR 52.245-1) & PIEE Property Management Plan",
    "description": "Audit GFP/GFE/GFI attachments under FAR 52.245-1 and DFARS 252.245-7003/7005, generating a DCMA-ready Property Management System Plan (PMSP), PIEE GFP Module reporting workflow, and IUID marking checklist. Returns a strictly validated `GfpPropertyAuditResponse` JSON object containing `gfp_property_system_overview`, `far_52_245_1_ten_lifecycle_outcomes_audit`, `gfp_cap_line_item_and_iuid_registry_table`, and `piee_gfp_module_and_plant_clearance_workflow` grounded in FAR 52.245-1, DFARS 252.245-7003 (Contractor Property Management System Administration), DFARS 252.245-7005 (PIEE GFP Module), & MIL-STD-130N. This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `gfp_attachment_and_property_clauses_text` accepts 15 to 45,000 characters, while `dcma_property_system_audit_scope` and `liability_and_cap_regime` calibrate the regulatory regime and threshold assumptions). Use this tool when executing Government-Furnished Property (GFP / FAR 52.245-1) & PIEE Property Management Plan workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "Government-Furnished Property (GFP / FAR 52.245-1) & PIEE Property Management Plan",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "gfp_attachment_and_property_clauses_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for Government-Furnished Property (GFP / FAR 52.245-1) & PIEE Property Management Plan (15 to 45,000 characters)."
        },
        "dcma_property_system_audit_scope": {
          "type": "string",
          "default": "FAR_52_245_1_10_Lifecycle_Outcomes_DFARS_252_245_7005_PIEE_GFP_Module_And_MIL_STD_130_IUID",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'FAR_52_245_1_10_Lifecycle_Outcomes_DFARS_252_245_7005_PIEE_GFP_Module_And_MIL_STD_130_IUID')."
        },
        "liability_and_cap_regime": {
          "type": "string",
          "default": "FAR 52.245-1(h) Limited Risk of Loss (Government Self-Insures Except Willful Misconduct / Revoked PMSA)",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'FAR 52.245-1(h) Limited Risk of Loss (Government Self-Insures Except Willful Misconduct / Revoked PMSA)')."
        }
      },
      "required": [
        "gfp_attachment_and_property_clauses_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "gfp_property_system_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "far_52_245_1_ten_lifecycle_outcomes_audit": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "gfp_cap_line_item_and_iuid_registry_table": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "piee_gfp_module_and_plant_clearance_workflow": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "generate_oconus_sofa_defense_logistics",
    "title": "DoD OCONUS / INDOPACOM Deployment, SOFA, Defense Base Act (DBA) & SPOT Compliance",
    "description": "Evaluate Pacific/OCONUS defense IT solicitations for Status of Forces Agreement (SOFA) TESA/TDY accreditation, FAR 52.228-3 Defense Base Act (DBA) insurance wraps, DFARS 252.225-7040 SPOT synchronization, and COLA/Post Allowance rate structures. Returns a strictly validated `OconusSofaDbaResponse` JSON object containing `oconus_theater_deployment_overview`, `sofa_host_nation_accreditation_matrix`, `dba_insurance_and_dssr_allowance_model`, and `spot_loa_and_crc_deployment_checklist` grounded in FAR 52.228-3 (42 U.S.C. \u00a7\u00a7 1651\u20131654 Defense Base Act), DFARS 252.225-7040 / 252.225-7995 (SPOT LOA), & DSSR Chapters 130/220/650. This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `oconus_pws_and_theater_clauses_text` accepts 15 to 45,000 characters, while `target_combatant_command_and_host_nations` and `dba_and_dssr_allowance_assumptions` calibrate the regulatory regime and threshold assumptions). Use this tool when executing DoD OCONUS / INDOPACOM Deployment, SOFA, Defense Base Act (DBA) & SPOT Compliance workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "DoD OCONUS / INDOPACOM Deployment, SOFA, Defense Base Act (DBA) & SPOT Compliance",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "oconus_pws_and_theater_clauses_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for DoD OCONUS / INDOPACOM Deployment, SOFA, Defense Base Act (DBA) & SPOT Compliance (15 to 45,000 characters)."
        },
        "target_combatant_command_and_host_nations": {
          "type": "string",
          "default": "USINDOPACOM_USFJ_Japan_USFK_Korea_Guam_And_USEUCOM_Germany_DOCPER_TESA",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'USINDOPACOM_USFJ_Japan_USFK_Korea_Guam_And_USEUCOM_Germany_DOCPER_TESA')."
        },
        "dba_and_dssr_allowance_assumptions": {
          "type": "string",
          "default": "FAR 52.228-3 Defense Base Act (DBA) Insurance + DSSR Living Quarters Allowance (LQA), Post Allowance (COLA), & Danger Pay",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'FAR 52.228-3 Defense Base Act (DBA) Insurance + DSSR Living Quarters Allowance (LQA), Post Allowance (COLA), & Danger Pay')."
        }
      },
      "required": [
        "oconus_pws_and_theater_clauses_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "oconus_theater_deployment_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "sofa_host_nation_accreditation_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "dba_insurance_and_dssr_allowance_model": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "spot_loa_and_crc_deployment_checklist": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "generate_cui_marking_distribution_plan",
    "title": "Controlled Unclassified Information (CUI / 32 CFR 2002 & DoDI 5200.48) Handling Plan",
    "description": "Analyze deliverables against the NARA CUI Registry, 32 CFR Part 2002, and DoDI 5200.48 to generate exact CUI banner/portion markings, DoD Distribution Statements (A\u2013F), and a CUI Sanitization & Spill Response SOP. Returns a strictly validated `CuiMarkingPlanResponse` JSON object containing `cui_registry_governance_overview`, `deliverable_cui_banner_and_distribution_matrix`, `portion_marking_and_designation_indicator_blocks`, and `nist_800_88_sanitization_and_spill_response_sop` grounded in 32 CFR Part 2002 (NARA CUI Program), DoDI 5200.48 (Controlled Unclassified Information), DoDI 5230.24 (Distribution Statements), & NIST SP 800-88 Rev. 1. This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `deliverables_and_security_classification_guide_text` accepts 15 to 45,000 characters, while `cui_authority_framework` and `controlling_dod_office_and_ldc_context` calibrate the regulatory regime and threshold assumptions). Use this tool when executing Controlled Unclassified Information (CUI / 32 CFR 2002 & DoDI 5200.48) Handling Plan workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "Controlled Unclassified Information (CUI / 32 CFR 2002 & DoDI 5200.48) Handling Plan",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "deliverables_and_security_classification_guide_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for Controlled Unclassified Information (CUI / 32 CFR 2002 & DoDI 5200.48) Handling Plan (15 to 45,000 characters)."
        },
        "cui_authority_framework": {
          "type": "string",
          "default": "32_CFR_Part_2002_NARA_CUI_Registry_DoDI_5200_48_And_DoDI_5230_24_Distribution_Statements",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to '32_CFR_Part_2002_NARA_CUI_Registry_DoDI_5200_48_And_DoDI_5230_24_Distribution_Statements')."
        },
        "controlling_dod_office_and_ldc_context": {
          "type": "string",
          "default": "Controlling DoD Office: AFLCMC/HNC (Hanscom AFB, MA) | Limited Dissemination Controls: NOFORN, FEDCON, DL ONLY",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'Controlling DoD Office: AFLCMC/HNC (Hanscom AFB, MA) | Limited Dissemination Controls: NOFORN, FEDCON, DL ONLY')."
        }
      },
      "required": [
        "deliverables_and_security_classification_guide_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "cui_registry_governance_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "deliverable_cui_banner_and_distribution_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "portion_marking_and_designation_indicator_blocks": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "nist_800_88_sanitization_and_spill_response_sop": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "generate_state_local_cooperative_piggyback",
    "title": "SLED Cooperative Purchasing (NASPO ValuePoint, Sourcewell, OMNIA, TIPS & DIR) Piggyback Mapper",
    "description": "Evaluate state and municipal IT procurements to identify eligible NASPO ValuePoint, Sourcewell, OMNIA Partners, TIPS, TX DIR, and GSA Cooperative Purchasing (SIN 54151S/HACS) piggyback vehicles that bypass a 6-month competitive RFP. Returns a strictly validated `SledCoopPiggybackResponse` JSON object containing `sled_cooperative_piggyback_overview`, `eligible_cooperative_vehicles_matrix`, `participating_addendum_and_distributor_pathways`, and `statutory_interlocal_authority_and_cpo_memo` grounded in 40 U.S.C. \u00a7 502(c) (GSA Cooperative Purchasing for IT/Cyber SINs), ABA Model Procurement Code Article 10 (Intergovernmental Relations), & State Participating Addendum Statutes. This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `sled_buyer_requirement_and_vendor_contracts_text` accepts 15 to 45,000 characters, while `target_cooperative_portfolios` and `vendor_direct_vs_distributor_model` calibrate the regulatory regime and threshold assumptions). Use this tool when executing SLED Cooperative Purchasing (NASPO ValuePoint, Sourcewell, OMNIA, TIPS & DIR) Piggyback Mapper workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "SLED Cooperative Purchasing (NASPO ValuePoint, Sourcewell, OMNIA, TIPS & DIR) Piggyback Mapper",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "sled_buyer_requirement_and_vendor_contracts_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for SLED Cooperative Purchasing (NASPO ValuePoint, Sourcewell, OMNIA, TIPS & DIR) Piggyback Mapper (15 to 45,000 characters)."
        },
        "target_cooperative_portfolios": {
          "type": "string",
          "default": "NASPO_ValuePoint_Cloud_AR2472_Sourcewell_OMNIA_Partners_TIPS_USA_TX_DIR_And_GSA_Coop_Purchasing",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'NASPO_ValuePoint_Cloud_AR2472_Sourcewell_OMNIA_Partners_TIPS_USA_TX_DIR_And_GSA_Coop_Purchasing')."
        },
        "vendor_direct_vs_distributor_model": {
          "type": "string",
          "default": "Evaluate Both Direct Master Agreement Holdership and Carahsoft / TD SYNNEX / Ingram Micro Authorized Reseller Piggyback",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'Evaluate Both Direct Master Agreement Holdership and Carahsoft / TD SYNNEX / Ingram Micro Authorized Reseller Piggyback')."
        }
      },
      "required": [
        "sled_buyer_requirement_and_vendor_contracts_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "sled_cooperative_piggyback_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "eligible_cooperative_vehicles_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "participating_addendum_and_distributor_pathways": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "statutory_interlocal_authority_and_cpo_memo": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "generate_value_engineering_vecp",
    "title": "FAR Part 48 Value Engineering Change Proposal (VECP / FAR 52.248-1) & Shared-Savings Modeler",
    "description": "Transform cloud FinOps, AI automation, or architecture optimizations on an active contract into a formal FAR 52.248-1 Value Engineering Change Proposal (VECP), calculating Instant/Concurrent/Future acquisition savings and the contractor's 50%\u201375% shared-savings royalty. Returns a strictly validated `VecpFar48Response` JSON object containing `vecp_shared_savings_overview`, `instant_concurrent_and_future_savings_table`, `far_52_248_1_c_eight_element_proposal_package`, and `collateral_savings_and_data_rights_protection` grounded in FAR Part 48 (Value Engineering) & FAR 52.248-1(c)\u2013(i) (50%/50% to 75%/25% Voluntary VECP Incentive Sharing & 36\u201360 Month Future Acquisition Royalty). This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `baseline_contract_and_proposed_engineering_change_text` accepts 15 to 45,000 characters, while `far_part_48_sharing_regime` and `development_and_government_implementation_costs` calibrate the regulatory regime and threshold assumptions). Use this tool when executing FAR Part 48 Value Engineering Change Proposal (VECP / FAR 52.248-1) & Shared-Savings Modeler workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "FAR Part 48 Value Engineering Change Proposal (VECP / FAR 52.248-1) & Shared-Savings Modeler",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "baseline_contract_and_proposed_engineering_change_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for FAR Part 48 Value Engineering Change Proposal (VECP / FAR 52.248-1) & Shared-Savings Modeler (15 to 45,000 characters)."
        },
        "far_part_48_sharing_regime": {
          "type": "string",
          "default": "FAR_52_248_1_Voluntary_Incentive_Fixed_Price_50_50_To_75_25_Contractor_Share",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'FAR_52_248_1_Voluntary_Incentive_Fixed_Price_50_50_To_75_25_Contractor_Share')."
        },
        "development_and_government_implementation_costs": {
          "type": "string",
          "default": "Contractor VECP Development Cost: $320,000 | Government Test/ECP Implementation Cost: $180,000 | 36-Month Sharing Period",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'Contractor VECP Development Cost: $320,000 | Government Test/ECP Implementation Cost: $180,000 | 36-Month Sharing Period')."
        }
      },
      "required": [
        "baseline_contract_and_proposed_engineering_change_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "vecp_shared_savings_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "instant_concurrent_and_future_savings_table": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "far_52_248_1_c_eight_element_proposal_package": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "collateral_savings_and_data_rights_protection": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "audit_organizational_ethics_far_52_203_13",
    "title": "FAR 52.203-13 Business Ethics, Procurement Integrity Act & OIG Mandatory Disclosure",
    "description": "Audit compliance incidents, overpayments, and hiring of former government officials against FAR 52.203-13 (Mandatory Disclosure Rule), False Claims Act (31 U.S.C. 3729), and Procurement Integrity Act (FAR 3.104), generating an Internal Control System & Post-Government Employment opinion. Returns a strictly validated `EthicsMandatoryDisclosureResponse` JSON object containing `credible_evidence_and_ethics_overview`, `far_52_203_13_and_pia_trigger_audit_matrix`, `oig_disclosure_submission_and_pge_wall_memos`, and `far_9_4_present_responsibility_and_internal_controls` grounded in FAR 52.203-13 (Contractor Code of Business Ethics and Conduct), 31 U.S.C. \u00a7 3729 (False Claims Act), FAR 3.104 (41 U.S.C. \u00a7 2101\u20132107 PIA), & 18 U.S.C. \u00a7 207. This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `compliance_incident_or_former_official_hiring_text` accepts 15 to 45,000 characters, while `audit_focus_regime` and `contract_value_and_performance_duration` calibrate the regulatory regime and threshold assumptions). Use this tool when executing FAR 52.203-13 Business Ethics, Procurement Integrity Act & OIG Mandatory Disclosure workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "FAR 52.203-13 Business Ethics, Procurement Integrity Act & OIG Mandatory Disclosure",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "compliance_incident_or_former_official_hiring_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for FAR 52.203-13 Business Ethics, Procurement Integrity Act & OIG Mandatory Disclosure (15 to 45,000 characters)."
        },
        "audit_focus_regime": {
          "type": "string",
          "default": "FAR_52_203_13_Credible_Evidence_OIG_Disclosure_FAR_3_104_PIA_And_18_USC_207_Revolving_Door",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'FAR_52_203_13_Credible_Evidence_OIG_Disclosure_FAR_3_104_PIA_And_18_USC_207_Revolving_Door')."
        },
        "contract_value_and_performance_duration": {
          "type": "string",
          "default": "Active Contract > $6.0M Threshold and > 120 Days Performance (Full FAR 52.203-13(c) Internal Control System Required)",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'Active Contract > $6.0M Threshold and > 120 Days Performance (Full FAR 52.203-13(c) Internal Control System Required)')."
        }
      },
      "required": [
        "compliance_incident_or_former_official_hiring_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "credible_evidence_and_ethics_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "far_52_203_13_and_pia_trigger_audit_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "oig_disclosure_submission_and_pge_wall_memos": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "far_9_4_present_responsibility_and_internal_controls": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "generate_fedramp_equivalency_body_of_evidence",
    "title": "DoD FedRAMP Moderate Equivalency (2024 DoD CIO Memo) & 3PAO Body of Evidence Auditor",
    "description": "Audit cloud service offerings against the DoD CIO FedRAMP Moderate Equivalency Memorandum (100% 3PAO assessment, zero unmitigated high/moderate POA&Ms, KSIs) and generates a complete Cloud Equivalency Body of Evidence (BoE) checklist. Returns a strictly validated `FedrampEquivalencyResponse` JSON object containing `dod_cio_equivalency_overview`, `body_of_evidence_boe_8_artifact_checklist`, `three_pao_100_pct_and_zero_poam_remediation_matrix`, and `dibcs_72hr_incident_reporting_and_prime_verification` grounded in DoD CIO Memorandum 'Federal Risk and Authorization Management Program Moderate Equivalency for Cloud Service Provider's Cloud Service Offerings' (Jan 2, 2024) & DFARS 252.204-7012(b)(2)(ii)(D). This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `cloud_service_offering_and_3pao_posture_text` accepts 15 to 45,000 characters, while `target_equivalency_standard` and `underlying_iaas_and_fips_posture` calibrate the regulatory regime and threshold assumptions). Use this tool when executing DoD FedRAMP Moderate Equivalency (2024 DoD CIO Memo) & 3PAO Body of Evidence Auditor workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "DoD FedRAMP Moderate Equivalency (2024 DoD CIO Memo) & 3PAO Body of Evidence Auditor",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "cloud_service_offering_and_3pao_posture_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for DoD FedRAMP Moderate Equivalency (2024 DoD CIO Memo) & 3PAO Body of Evidence Auditor (15 to 45,000 characters)."
        },
        "target_equivalency_standard": {
          "type": "string",
          "default": "DoD_CIO_Jan_2024_FedRAMP_Moderate_Equivalency_Memo_DFARS_252_204_7012_c_d_And_FedRAMP_Rev5",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'DoD_CIO_Jan_2024_FedRAMP_Moderate_Equivalency_Memo_DFARS_252_204_7012_c_d_And_FedRAMP_Rev5')."
        },
        "underlying_iaas_and_fips_posture": {
          "type": "string",
          "default": "Hosted on AWS GovCloud (US) FedRAMP High JAB P-ATO; FIPS 140-3 Validated Cryptographic Modules",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'Hosted on AWS GovCloud (US) FedRAMP High JAB P-ATO; FIPS 140-3 Validated Cryptographic Modules')."
        }
      },
      "required": [
        "cloud_service_offering_and_3pao_posture_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "dod_cio_equivalency_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "body_of_evidence_boe_8_artifact_checklist": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "three_pao_100_pct_and_zero_poam_remediation_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "dibcs_72hr_incident_reporting_and_prime_verification": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "generate_ai_governance_nist_ai_rmf_omb_m24",
    "title": "Federal AI Governance, OMB M-24-10/M-24-18 & NIST AI RMF 1.0 Compliance Package",
    "description": "Evaluate AI/ML/LLM solutions proposed for federal and SLED agencies against OMB Memoranda M-24-10 & M-24-18, NIST AI RMF 1.0 (Govern, Map, Measure, Manage), and DoD Responsible AI (RAI) Toolkit, outputting a Safety-Impact Classification & Model Card. Returns a strictly validated `AiGovernanceOmbResponse` JSON object containing `omb_safety_and_rights_impact_overview`, `nist_ai_rmf_govern_map_measure_manage_matrix`, `omb_m_24_10_and_m_24_18_minimum_practices_audit`, and `federal_ai_system_card_and_hitl_safeguards` grounded in OMB Memorandum M-24-10, OMB Memorandum M-24-18 (Advancing the Responsible Acquisition of AI in Government), NIST AI 100-1 (AI RMF 1.0), NIST AI 600-1, & DoD CDAO RAI Shield. This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `proposed_ai_system_and_agency_use_case_text` accepts 15 to 45,000 characters, while `target_ai_governance_frameworks` and `deployment_enclave_and_training_data_policy` calibrate the regulatory regime and threshold assumptions). Use this tool when executing Federal AI Governance, OMB M-24-10/M-24-18 & NIST AI RMF 1.0 Compliance Package workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "Federal AI Governance, OMB M-24-10/M-24-18 & NIST AI RMF 1.0 Compliance Package",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "proposed_ai_system_and_agency_use_case_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for Federal AI Governance, OMB M-24-10/M-24-18 & NIST AI RMF 1.0 Compliance Package (15 to 45,000 characters)."
        },
        "target_ai_governance_frameworks": {
          "type": "string",
          "default": "OMB_M_24_10_OMB_M_24_18_NIST_AI_RMF_1_0_NIST_AI_600_1_GenAI_And_DoD_CDAO_RAI_Toolkit",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'OMB_M_24_10_OMB_M_24_18_NIST_AI_RMF_1_0_NIST_AI_600_1_GenAI_And_DoD_CDAO_RAI_Toolkit')."
        },
        "deployment_enclave_and_training_data_policy": {
          "type": "string",
          "default": "Stateless RAG on Agency Tenant (Zero Training on Government CUI/PII; Open-Format Export to Prevent Vendor Lock-In)",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'Stateless RAG on Agency Tenant (Zero Training on Government CUI/PII; Open-Format Export to Prevent Vendor Lock-In)')."
        }
      },
      "required": [
        "proposed_ai_system_and_agency_use_case_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "omb_safety_and_rights_impact_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "nist_ai_rmf_govern_map_measure_manage_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "omb_m_24_10_and_m_24_18_minimum_practices_audit": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "federal_ai_system_card_and_hitl_safeguards": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "generate_termination_for_convenience_settlement",
    "title": "FAR Part 49 Termination for Convenience (T4C / SF 1435\u20131438) Settlement Proposal Calculator",
    "description": "Compute recoverable sunk costs, subcontractor termination claims, settlement expenses, and profit on work performed under FAR Part 49 and FAR 52.249-2, generating an Inventory Basis (SF 1435) or Total Cost Basis (SF 1436) T4C Settlement Proposal. Returns a strictly validated `T4cSettlementResponse` JSON object containing `t4c_settlement_executive_overview`, `sf_1435_1436_recoverable_quantum_schedule`, `subcontractor_settlement_and_sf_1428_inventory_schedule`, and `far_31_205_42_allowability_and_one_year_filing_clock` grounded in FAR Part 49, FAR 52.249-2 (Termination for Convenience of the Government), FAR 31.205-42 (Termination Costs), & Standard Forms 1435 / 1436 / 1437 / 1438 / 1428. This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `termination_notice_and_incurred_cost_ledger_text` accepts 15 to 45,000 characters, while `settlement_proposal_basis_and_form` and `contract_type_and_clause_regime` calibrate the regulatory regime and threshold assumptions). Use this tool when executing FAR Part 49 Termination for Convenience (T4C / SF 1435\u20131438) Settlement Proposal Calculator workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "FAR Part 49 Termination for Convenience (T4C / SF 1435\u20131438) Settlement Proposal Calculator",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "termination_notice_and_incurred_cost_ledger_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for FAR Part 49 Termination for Convenience (T4C / SF 1435\u20131438) Settlement Proposal Calculator (15 to 45,000 characters)."
        },
        "settlement_proposal_basis_and_form": {
          "type": "string",
          "default": "SF_1435_Inventory_Basis_Preferred_Under_FAR_49_206_2_vs_SF_1436_Total_Cost_Basis",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'SF_1435_Inventory_Basis_Preferred_Under_FAR_49_206_2_vs_SF_1436_Total_Cost_Basis')."
        },
        "contract_type_and_clause_regime": {
          "type": "string",
          "default": "FAR 52.249-2 Fixed-Price Termination for Convenience (vs. FAR 52.249-6 Cost-Reimbursement / FAR 52.212-4(l) Commercial)",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'FAR 52.249-2 Fixed-Price Termination for Convenience (vs. FAR 52.249-6 Cost-Reimbursement / FAR 52.212-4(l) Commercial)')."
        }
      },
      "required": [
        "termination_notice_and_incurred_cost_ledger_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "t4c_settlement_executive_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "sf_1435_1436_recoverable_quantum_schedule": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "subcontractor_settlement_and_sf_1428_inventory_schedule": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "far_31_205_42_allowability_and_one_year_filing_clock": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "generate_novated_merger_change_of_name_far_42",
    "title": "GovCon M&A Contract Novation (FAR 42.1204) & Change-of-Name Due Diligence Package",
    "description": "Generate a complete FAR 42.1204 Three-Party Novation Agreement package for GovCon asset/stock acquisitions, auditing anti-assignment exceptions (41 U.S.C. 6305), SAM.gov UEI/CAGE transfer checklists, and SBA recertification triggers under 13 CFR 121.404(g). Returns a strictly validated `NovationFar42Response` JSON object containing `transaction_structure_and_novation_overview`, `far_42_1204_document_checklist_and_three_party_agreement`, `sba_13_cfr_121_404_recertification_and_backlog_audit`, and `sam_uei_cage_and_dcsa_fcl_transition_runbook` grounded in 41 U.S.C. \u00a7 6305 (Anti-Assignment Act), FAR Subpart 42.12 (FAR 42.1204 Novation & FAR 42.1205 Change-of-Name), & 13 CFR \u00a7 121.404(g). This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `m_and_a_transaction_and_contract_backlog_text` accepts 15 to 45,000 characters, while `deal_structure_and_pathway` and `small_business_and_clearance_context` calibrate the regulatory regime and threshold assumptions). Use this tool when executing GovCon M&A Contract Novation (FAR 42.1204) & Change-of-Name Due Diligence Package workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "GovCon M&A Contract Novation (FAR 42.1204) & Change-of-Name Due Diligence Package",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "m_and_a_transaction_and_contract_backlog_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for GovCon M&A Contract Novation (FAR 42.1204) & Change-of-Name Due Diligence Package (15 to 45,000 characters)."
        },
        "deal_structure_and_pathway": {
          "type": "string",
          "default": "Asset_Purchase_Requiring_FAR_42_1204_Three_Party_Novation_vs_Stock_Purchase_Or_FAR_42_1205_Change_Of_Name",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'Asset_Purchase_Requiring_FAR_42_1204_Three_Party_Novation_vs_Stock_Purchase_Or_FAR_42_1205_Change_Of_Name')."
        },
        "small_business_and_clearance_context": {
          "type": "string",
          "default": "Audit 13 CFR 121.404(g) 30-Day SBA Size Recertification, GWAC/MAC Eligibility, & DCSA 32 CFR 117 Changed Condition Package",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'Audit 13 CFR 121.404(g) 30-Day SBA Size Recertification, GWAC/MAC Eligibility, & DCSA 32 CFR 117 Changed Condition Package')."
        }
      },
      "required": [
        "m_and_a_transaction_and_contract_backlog_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "transaction_structure_and_novation_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "far_42_1204_document_checklist_and_three_party_agreement": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "sba_13_cfr_121_404_recertification_and_backlog_audit": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "sam_uei_cage_and_dcsa_fcl_transition_runbook": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "generate_section_l_m_proposal_red_team_scorer",
    "title": "SSEB Source Selection Simulator & Shipley Pink/Red/Gold Team Proposal Scorer",
    "description": "Simulate a Government Source Selection Evaluation Board (SSEB) under FAR 15.305, grading a draft proposal volume against RFP Section L/M into DoD Color/Adjectival Ratings (Blue/Outstanding to Red/Unacceptable) with exact Strengths, Weaknesses, Deficiencies, and page-level rewrites. Returns a strictly validated `RedTeamEvaluatorResponse` JSON object containing `sseb_consensus_evaluation_overview`, `factor_by_factor_color_and_risk_scorecard`, `sseb_strengths_weaknesses_deficiencies_and_rewrites`, and `competitive_range_and_gold_team_recovery_plan` grounded in FAR 15.305 (Proposal Evaluation), DoD Source Selection Procedures (DFARS PGI 215.3 \u2014 Blue/Purple/Green/Yellow/Red Consensus Grading), & Shipley Color Team Standards. This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `rfp_section_l_m_and_draft_proposal_text` accepts 15 to 45,000 characters, while `source_selection_grading_methodology` and `color_team_review_stage` calibrate the regulatory regime and threshold assumptions). Use this tool when executing SSEB Source Selection Simulator & Shipley Pink/Red/Gold Team Proposal Scorer workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "SSEB Source Selection Simulator & Shipley Pink/Red/Gold Team Proposal Scorer",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "rfp_section_l_m_and_draft_proposal_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for SSEB Source Selection Simulator & Shipley Pink/Red/Gold Team Proposal Scorer (15 to 45,000 characters)."
        },
        "source_selection_grading_methodology": {
          "type": "string",
          "default": "DoD_Source_Selection_Procedures_2022_Color_Adjectival_Blue_Purple_Green_Yellow_Red_And_FAR_15_305",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'DoD_Source_Selection_Procedures_2022_Color_Adjectival_Blue_Purple_Green_Yellow_Red_And_FAR_15_305')."
        },
        "color_team_review_stage": {
          "type": "string",
          "default": "Red_Team_Full_SSEB_Simulation_With_Paste_Ready_Feature_Benefit_Proof_Upgrades_To_Blue_Outstanding",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'Red_Team_Full_SSEB_Simulation_With_Paste_Ready_Feature_Benefit_Proof_Upgrades_To_Blue_Outstanding')."
        }
      },
      "required": [
        "rfp_section_l_m_and_draft_proposal_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "sseb_consensus_evaluation_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "factor_by_factor_color_and_risk_scorecard": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "sseb_strengths_weaknesses_deficiencies_and_rewrites": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "competitive_range_and_gold_team_recovery_plan": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "generate_gsa_tdr_quarterly_sales_iff_reconciler",
    "title": "GSA FAS Sales Reporting Portal (SRP), TDR Line-Item & IFF CAV/IOA Audit Reconciler",
    "description": "Audit commercial vs. GSA Schedule invoices to separate Open-Market vs. Schedule sales, calculate quarterly 0.75% IFF remittance, validate Transactional Data Reporting (TDR) 16-field data elements, and prepare for a GSA IOA Contractor Assistance Visit (CAV). Returns a strictly validated `GsaTdrIffAuditResponse` JSON object containing `gsa_srp_and_iff_reconciliation_overview`, `invoice_schedule_vs_open_market_classification_table`, `tdr_16_field_validation_and_ioa_cav_checklist`, and `iff_remittance_calendar_and_price_reductions_safe_harbor` grounded in GSAR 552.238-80 (Industrial Funding Fee and Sales Reporting \u2014 0.75% IFF within 30 days of quarter close), GSAR 552.238-81 (TDR), & GSA IOA Contractor Assistance Visit (CAV) Guide. This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `quarterly_invoice_ledger_and_gsa_contract_text` accepts 15 to 45,000 characters, while `gsa_reporting_regime` and `reporting_quarter_and_sins` calibrate the regulatory regime and threshold assumptions). Use this tool when executing GSA FAS Sales Reporting Portal (SRP), TDR Line-Item & IFF CAV/IOA Audit Reconciler workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "GSA FAS Sales Reporting Portal (SRP), TDR Line-Item & IFF CAV/IOA Audit Reconciler",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "quarterly_invoice_ledger_and_gsa_contract_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for GSA FAS Sales Reporting Portal (SRP), TDR Line-Item & IFF CAV/IOA Audit Reconciler (15 to 45,000 characters)."
        },
        "gsa_reporting_regime": {
          "type": "string",
          "default": "GSAR_552_238_80_IFF_0_75_Pct_GSAR_552_238_81_TDR_16_Data_Elements_And_IOA_CAV_Readiness",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'GSAR_552_238_80_IFF_0_75_Pct_GSAR_552_238_81_TDR_16_Data_Elements_And_IOA_CAV_Readiness')."
        },
        "reporting_quarter_and_sins": {
          "type": "string",
          "default": "FY2026 Q4 (July 1 \u2013 Sept 30; SRP Filing Due Oct 30) | SINs: 54151S, 54151HACS, 518210C, OLM",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'FY2026 Q4 (July 1 \u2013 Sept 30; SRP Filing Due Oct 30) | SINs: 54151S, 54151HACS, 518210C, OLM')."
        }
      },
      "required": [
        "quarterly_invoice_ledger_and_gsa_contract_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "gsa_srp_and_iff_reconciliation_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "invoice_schedule_vs_open_market_classification_table": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "tdr_16_field_validation_and_ioa_cav_checklist": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "iff_remittance_calendar_and_price_reductions_safe_harbor": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  },
  {
    "name": "generate_award_fee_plan_incentive_maximizer",
    "title": "FAR Subpart 16.4 Award-Fee (CPAF) & Incentive-Fee (CPIF / FPIF) Evaluation Maximizer",
    "description": "Model CPAF, CPIF, and FPIF share-ratio curves (overrun/underrun ceiling geometry under FAR 16.401) and transforms periodic performance metrics into an Award-Fee Evaluation Board (AFEB) self-assessment presentation to maximize unearned/rollover fee pools. Returns a strictly validated `CpafCpifAwardFeeResponse` JSON object containing `award_and_incentive_fee_geometry_overview`, `cpif_fpif_share_ratio_and_pta_sensitivity_table`, `afeb_table_16_1_self_assessment_briefing_sections`, and `far_16_401_e_4_rollover_rules_and_afdo_strategy` grounded in FAR Subpart 16.4 (Incentive Contracts), FAR 16.401(e)(3) Table 16-1 (Standard Award-Fee Adjectival Ratings), FAR 16.401(e)(4) (Rollover Prohibition), & DFARS 216.405-2. This is a read-only, stateless, non-destructive GovCon compliance and capture analysis call (requires X-RapidAPI-Key or X-SignalTender-Key; `incentive_or_award_fee_plan_and_period_metrics_text` accepts 15 to 45,000 characters, while `contract_fee_structure_type` and `evaluation_period_and_pool_context` calibrate the regulatory regime and threshold assumptions). Use this tool when executing FAR Subpart 16.4 Award-Fee (CPAF) & Incentive-Fee (CPIF / FPIF) Evaluation Maximizer workflows; use `scan_far_dfars_clauses` instead for general FAR/DFARS clause flow-down audits, or `generate_compliance_matrix` for general Section L/M 'shall' requirement extraction.",
    "annotations": {
      "title": "FAR Subpart 16.4 Award-Fee (CPAF) & Incentive-Fee (CPIF / FPIF) Evaluation Maximizer",
      "readOnlyHint": true,
      "destructiveHint": false,
      "idempotentHint": true,
      "openWorldHint": false
    },
    "inputSchema": {
      "type": "object",
      "properties": {
        "incentive_or_award_fee_plan_and_period_metrics_text": {
          "type": "string",
          "minLength": 15,
          "maxLength": 45000,
          "description": "Primary solicitation text, clause excerpts, deliverable schedule, or technical/financial context for FAR Subpart 16.4 Award-Fee (CPAF) & Incentive-Fee (CPIF / FPIF) Evaluation Maximizer (15 to 45,000 characters)."
        },
        "contract_fee_structure_type": {
          "type": "string",
          "default": "Combined_CPAF_Award_Fee_Adjectival_Table_16_1_And_CPIF_FPIF_Share_Ratio_PTA_Geometry",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Target regulatory regime, statutory authority, or evaluation framework (defaults to 'Combined_CPAF_Award_Fee_Adjectival_Table_16_1_And_CPIF_FPIF_Share_Ratio_PTA_Geometry')."
        },
        "evaluation_period_and_pool_context": {
          "type": "string",
          "default": "Award-Fee Period 04 (6-Month Evaluation Pool: $1,250,000 Available Award Fee + Base Fee 2.0%)",
          "minLength": 2,
          "maxLength": 2000,
          "description": "Operational context, threshold parameters, or compliance posture assumptions (defaults to 'Award-Fee Period 04 (6-Month Evaluation Pool: $1,250,000 Available Award Fee + Base Fee 2.0%)')."
        }
      },
      "required": [
        "incentive_or_award_fee_plan_and_period_metrics_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "status": {
          "type": "string",
          "description": "Execution status ('success')."
        },
        "award_and_incentive_fee_geometry_overview": {
          "type": "object",
          "description": "Executive determination overview, regulatory citations, and readiness score."
        },
        "cpif_fpif_share_ratio_and_pta_sensitivity_table": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Structured line-by-line regulatory audit, classification, or quantitative schedule rows."
        },
        "afeb_table_16_1_self_assessment_briefing_sections": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Paste-ready compliance narratives, control specifications, or submission sections."
        },
        "far_16_401_e_4_rollover_rules_and_afdo_strategy": {
          "type": "object",
          "description": "Statutory governance protocol and actionable submission verification checklist."
        }
      }
    }
  }
];

const ENDPOINT_MAP = {
  "parse_b2b_contract": {
    "method": "POST",
    "path": "/v1/parse/contract"
  },
  "audit_contract_risks": {
    "method": "POST",
    "path": "/v1/parse/contract-risks"
  },
  "search_historical_awards": {
    "method": "POST",
    "path": "/v1/awards/search"
  },
  "get_live_solicitations": {
    "method": "GET",
    "path": "/v1/solicitations/live"
  },
  "generate_compliance_matrix": {
    "method": "POST",
    "path": "/v1/generate/compliance-matrix"
  },
  "scan_far_dfars_clauses": {
    "method": "POST",
    "path": "/v1/audit/far-dfars-clauses"
  },
  "match_capability_statement": {
    "method": "POST",
    "path": "/v1/match/capability-statement"
  },
  "classify_naics_psc_nigp": {
    "method": "POST",
    "path": "/v1/classify/naics-psc-nigp"
  },
  "generate_rfp_response": {
    "method": "POST",
    "path": "/v1/generate/rfp-response"
  },
  "extract_pricing_schedule": {
    "method": "POST",
    "path": "/v1/extract/pricing-schedule"
  },
  "generate_teaming_strategy": {
    "method": "POST",
    "path": "/v1/generate/teaming-strategy"
  },
  "answer_security_questionnaire": {
    "method": "POST",
    "path": "/v1/audit/security-questionnaire"
  },
  "match_key_personnel": {
    "method": "POST",
    "path": "/v1/match/key-personnel"
  },
  "analyze_rfp_amendment_diff": {
    "method": "POST",
    "path": "/v1/analyze/amendment-diff"
  },
  "generate_cpars_past_performance": {
    "method": "POST",
    "path": "/v1/generate/past-performance"
  },
  "generate_igce_price_to_win": {
    "method": "POST",
    "path": "/v1/generate/price-to-win"
  },
  "generate_oral_presentation_prep": {
    "method": "POST",
    "path": "/v1/generate/oral-presentation-prep"
  },
  "generate_ato_rmf_package": {
    "method": "POST",
    "path": "/v1/generate/ato-rmf-package"
  },
  "analyze_debriefing_bid_protest": {
    "method": "POST",
    "path": "/v1/generate/debriefing-bid-protest"
  },
  "generate_gsa_mas_offer": {
    "method": "POST",
    "path": "/v1/generate/gsa-mas-offer"
  },
  "generate_sources_sought_response": {
    "method": "POST",
    "path": "/v1/generate/sources-sought-response"
  },
  "generate_oci_mitigation_plan": {
    "method": "POST",
    "path": "/v1/generate/oci-mitigation-plan"
  },
  "generate_sbir_sttr_commercialization": {
    "method": "POST",
    "path": "/v1/generate/sbir-sttr-commercialization"
  },
  "audit_section_508_vpat": {
    "method": "POST",
    "path": "/v1/audit/section-508-vpat"
  },
  "audit_supply_chain_scrm": {
    "method": "POST",
    "path": "/v1/audit/supply-chain-scrm"
  },
  "generate_quality_assurance_qasp": {
    "method": "POST",
    "path": "/v1/generate/quality-assurance-qasp"
  },
  "generate_phase_in_transition_plan": {
    "method": "POST",
    "path": "/v1/generate/phase-in-transition-plan"
  },
  "audit_dcaa_accounting_sf1408": {
    "method": "POST",
    "path": "/v1/audit/dcaa-accounting-sf1408"
  },
  "generate_ota_white_paper": {
    "method": "POST",
    "path": "/v1/generate/ota-white-paper"
  },
  "audit_foci_dd254_clearance": {
    "method": "POST",
    "path": "/v1/audit/foci-dd254-clearance"
  },
  "generate_small_business_participation": {
    "method": "POST",
    "path": "/v1/generate/small-business-participation"
  },
  "generate_data_rights_assertion_table": {
    "method": "POST",
    "path": "/v1/generate/data-rights-assertion-table"
  },
  "generate_capture_black_hat_review": {
    "method": "POST",
    "path": "/v1/generate/capture-black-hat-review"
  },
  "generate_post_award_cpar_rebuttal": {
    "method": "POST",
    "path": "/v1/generate/post-award-cpar-rebuttal"
  },
  "generate_rea_equitable_adjustment": {
    "method": "POST",
    "path": "/v1/generate/rea-equitable-adjustment"
  },
  "generate_mentor_protege_jv_agreement": {
    "method": "POST",
    "path": "/v1/generate/mentor-protege-jv-agreement"
  },
  "audit_service_contract_act_wage": {
    "method": "POST",
    "path": "/v1/audit/service-contract-act-wage"
  },
  "generate_evms_ipmdr_variance_analysis": {
    "method": "POST",
    "path": "/v1/generate/evms-ipmdr-variance-analysis"
  },
  "generate_cost_accounting_cas_ds2": {
    "method": "POST",
    "path": "/v1/generate/cost-accounting-cas-ds2"
  },
  "audit_itar_ear_export_control": {
    "method": "POST",
    "path": "/v1/audit/itar-ear-export-control"
  },
  "generate_cdrls_did_data_deliverables": {
    "method": "POST",
    "path": "/v1/generate/cdrls-did-data-deliverables"
  },
  "generate_justification_ja_sole_source": {
    "method": "POST",
    "path": "/v1/generate/justification-ja-sole-source"
  },
  "audit_cyber_incident_dfars_7012": {
    "method": "POST",
    "path": "/v1/audit/cyber-incident-dfars-7012"
  },
  "generate_doe_national_lab_mando_subcontract": {
    "method": "POST",
    "path": "/v1/generate/doe-national-lab-mando-subcontract"
  },
  "generate_gwac_task_order_fair_opportunity": {
    "method": "POST",
    "path": "/v1/generate/gwac-task-order-fair-opportunity"
  },
  "audit_govt_furnished_property_gfp": {
    "method": "POST",
    "path": "/v1/audit/govt-furnished-property-gfp"
  },
  "generate_oconus_sofa_defense_logistics": {
    "method": "POST",
    "path": "/v1/generate/oconus-sofa-defense-logistics"
  },
  "generate_cui_marking_distribution_plan": {
    "method": "POST",
    "path": "/v1/generate/cui-marking-distribution-plan"
  },
  "generate_state_local_cooperative_piggyback": {
    "method": "POST",
    "path": "/v1/generate/state-local-cooperative-piggyback"
  },
  "generate_value_engineering_vecp": {
    "method": "POST",
    "path": "/v1/generate/value-engineering-vecp"
  },
  "audit_organizational_ethics_far_52_203_13": {
    "method": "POST",
    "path": "/v1/audit/organizational-ethics-far-52-203-13"
  },
  "generate_fedramp_equivalency_body_of_evidence": {
    "method": "POST",
    "path": "/v1/generate/fedramp-equivalency-body-of-evidence"
  },
  "generate_ai_governance_nist_ai_rmf_omb_m24": {
    "method": "POST",
    "path": "/v1/generate/ai-governance-nist-ai-rmf-omb-m24"
  },
  "generate_termination_for_convenience_settlement": {
    "method": "POST",
    "path": "/v1/generate/termination-for-convenience-settlement"
  },
  "generate_novated_merger_change_of_name_far_42": {
    "method": "POST",
    "path": "/v1/generate/novated-merger-change-of-name-far-42"
  },
  "generate_section_l_m_proposal_red_team_scorer": {
    "method": "POST",
    "path": "/v1/generate/section-l-m-proposal-red-team-scorer"
  },
  "generate_gsa_tdr_quarterly_sales_iff_reconciler": {
    "method": "POST",
    "path": "/v1/generate/gsa-tdr-quarterly-sales-iff-reconciler"
  },
  "generate_award_fee_plan_incentive_maximizer": {
    "method": "POST",
    "path": "/v1/generate/award-fee-plan-incentive-maximizer"
  }
};

const PUBLIC_MIRROR_HOSTS = {
  "generate_sources_sought_response": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com",
  "generate_oci_mitigation_plan": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com",
  "generate_sbir_sttr_commercialization": "rfp-compliance-matrix-proposal-outline-api.p.rapidapi.com",
  "audit_section_508_vpat": "soc-2-fedramp-nist-800-171-security-questionnaire-api.p.rapidapi.com",
  "audit_supply_chain_scrm": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com",
  "generate_quality_assurance_qasp": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com",
  "generate_phase_in_transition_plan": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com",
  "audit_dcaa_accounting_sf1408": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com",
  "generate_ota_white_paper": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com",
  "audit_foci_dd254_clearance": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com",
  "generate_small_business_participation": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com",
  "generate_data_rights_assertion_table": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com",
  "generate_capture_black_hat_review": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com",
  "generate_post_award_cpar_rebuttal": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com",
  "generate_rea_equitable_adjustment": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com",
  "generate_mentor_protege_jv_agreement": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com",
  "audit_service_contract_act_wage": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com",
  "generate_evms_ipmdr_variance_analysis": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com",
  "generate_cost_accounting_cas_ds2": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com",
  "audit_itar_ear_export_control": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com",
  "generate_cdrls_did_data_deliverables": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com",
  "generate_justification_ja_sole_source": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com",
  "audit_cyber_incident_dfars_7012": "soc-2-fedramp-nist-800-171-security-questionnaire-api.p.rapidapi.com",
  "generate_doe_national_lab_mando_subcontract": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com",
  "generate_gwac_task_order_fair_opportunity": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com",
  "audit_govt_furnished_property_gfp": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com",
  "generate_oconus_sofa_defense_logistics": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com",
  "generate_cui_marking_distribution_plan": "soc-2-fedramp-nist-800-171-security-questionnaire-api.p.rapidapi.com",
  "generate_state_local_cooperative_piggyback": "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com",
  "generate_value_engineering_vecp": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com",
  "audit_organizational_ethics_far_52_203_13": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com",
  "generate_fedramp_equivalency_body_of_evidence": "soc-2-fedramp-nist-800-171-security-questionnaire-api.p.rapidapi.com",
  "generate_ai_governance_nist_ai_rmf_omb_m24": "soc-2-fedramp-nist-800-171-security-questionnaire-api.p.rapidapi.com",
  "generate_termination_for_convenience_settlement": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com",
  "generate_novated_merger_change_of_name_far_42": "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com",
  "generate_section_l_m_proposal_red_team_scorer": "rfp-compliance-matrix-proposal-outline-api.p.rapidapi.com",
  "generate_gsa_tdr_quarterly_sales_iff_reconciler": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com",
  "generate_award_fee_plan_incentive_maximizer": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com"
};

async function callSignalTenderEndpoint(toolName, args) {
  const route = ENDPOINT_MAP[toolName];
  if (!route) {
    throw new Error(`Unknown tool: ${toolName}`);
  }

  let url;
  const headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
  };

  if (RAPIDAPI_PROXY_SECRET) {
    url = new URL(`${BASE_URL}${route.path}`);
    headers["X-RapidAPI-Proxy-Secret"] = RAPIDAPI_PROXY_SECRET;
  } else if (SIGNALTENDER_API_KEY || RAPIDAPI_KEY.startsWith("st_live_")) {
    url = new URL(`${BASE_URL}${route.path}`);
    headers["X-SignalTender-Key"] = SIGNALTENDER_API_KEY || RAPIDAPI_KEY;
  } else if (RAPIDAPI_KEY) {
    const rapidHost = RAPIDAPI_HOSTS[toolName];
    url = new URL(`https://${rapidHost}${route.path}`);
    headers["X-RapidAPI-Key"] = RAPIDAPI_KEY;
    headers["X-RapidAPI-Host"] = rapidHost;
  } else {
    return {
      isError: true,
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              error: "Missing API credentials",
              message:
                "Please set RAPIDAPI_KEY in your MCP server environment config. Get a free Basic key across all SignalTender APIs at https://signaltender.net/apis.html or https://rapidapi.com/user/aarbchen"
            },
            null,
            2
          )
        }
      ]
    };
  }

  const buildUrlWithParams = (baseUrlStr) => {
    const u = new URL(baseUrlStr);
    if (route.method === "GET" && args && typeof args === "object") {
      Object.entries(args).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") {
          u.searchParams.set(k, String(v));
        }
      });
    }
    return u;
  };

  url = buildUrlWithParams(url.toString());
  const fetchOptions = {
    method: route.method,
    headers
  };

  if (route.method === "POST") {
    fetchOptions.body = JSON.stringify(args || {});
  }

  let response = await fetch(url.toString(), fetchOptions);

  if ((response.status === 403 || response.status === 404) && RAPIDAPI_KEY && !RAPIDAPI_PROXY_SECRET) {
    const mirrorHost = PUBLIC_MIRROR_HOSTS[toolName];
    if (mirrorHost && mirrorHost !== headers["X-RapidAPI-Host"]) {
      const mirrorUrl = buildUrlWithParams(`https://${mirrorHost}${route.path}`);
      const mirrorHeaders = { ...headers, "X-RapidAPI-Host": mirrorHost };
      response = await fetch(mirrorUrl.toString(), { ...fetchOptions, headers: mirrorHeaders });
    }
    if (response.status === 403 || response.status === 404) {
      const directUrl = buildUrlWithParams(`${BASE_URL}${route.path}`);
      const directHeaders = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-SignalTender-Sandbox": "interactive-studio"
      };
      response = await fetch(directUrl.toString(), { ...fetchOptions, headers: directHeaders });
    }
  }

  const text = await response.text();
  const result = {
    isError: !response.ok,
    content: [
      {
        type: "text",
        text
      }
    ]
  };
  if (response.ok) {
    try {
      const parsed = JSON.parse(text);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        result.structuredContent = parsed;
      }
    } catch (_) {}
  }
  return result;
}

function sendJsonRpc(message) {
  process.stdout.write(JSON.stringify(message) + "\n");
}

const rl = readline.createInterface({
  input: process.stdin,
  terminal: false
});

rl.on("line", async (line) => {
  if (!line.trim()) return;
  let req;
  try {
    req = JSON.parse(line);
  } catch (err) {
    return;
  }

  const { id, method, params } = req;

  try {
    if (method === "initialize") {
      sendJsonRpc({
        jsonrpc: "2.0",
        id,
        result: {
          protocolVersion: "2024-11-05",
          capabilities: {
            tools: {}
          },
          serverInfo: {
            name: "@signaltender/mcp-server",
            version: "1.41.0"
          }
        }
      });
    } else if (method === "notifications/initialized") {
      // No response needed for notification
    } else if (method === "tools/list") {
      sendJsonRpc({
        jsonrpc: "2.0",
        id,
        result: {
          tools: TOOLS
        }
      });
    } else if (method === "tools/call") {
      const toolName = params && params.name;
      const toolArgs = (params && params.arguments) || {};
      const result = await callSignalTenderEndpoint(toolName, toolArgs);
      sendJsonRpc({
        jsonrpc: "2.0",
        id,
        result
      });
    } else if (method === "ping") {
      sendJsonRpc({
        jsonrpc: "2.0",
        id,
        result: {}
      });
    } else if (id !== undefined) {
      sendJsonRpc({
        jsonrpc: "2.0",
        id,
        error: {
          code: -32601,
          message: `Method not found: ${method}`
        }
      });
    }
  } catch (err) {
    if (id !== undefined) {
      sendJsonRpc({
        jsonrpc: "2.0",
        id,
        error: {
          code: -32603,
          message: err.message || "Internal MCP server error"
        }
      });
    }
  }
});

