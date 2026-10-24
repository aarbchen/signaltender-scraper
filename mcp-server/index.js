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
  parse_b2b_contract: "b2b-contract-parsing-api.p.rapidapi.com",
  audit_contract_risks: "ai-contract-risk-redline-auditor-api.p.rapidapi.com",
  search_historical_awards: "historical-procurement-pricing-api.p.rapidapi.com",
  get_live_solicitations: "live-sled-federal-open-rfp-feed-api.p.rapidapi.com",
  generate_compliance_matrix: "rfp-compliance-matrix-proposal-outline-api.p.rapidapi.com",
  scan_far_dfars_clauses: "far-dfars-cmmc-clause-risk-scanner-api.p.rapidapi.com",
  match_capability_statement: "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com",
  classify_naics_psc_nigp: "naics-sic-psc-unspsc-industry-classifier-api.p.rapidapi.com",
  generate_rfp_response: "ai-rfp-response-clarification-q-a-generator-api.p.rapidapi.com",
  extract_pricing_schedule: "b2b-quote-invoice-clin-table-extractor-api.p.rapidapi.com",
  generate_teaming_strategy: "govcon-teaming-partner-subcontracting-plan-api.p.rapidapi.com",
  answer_security_questionnaire: "soc-2-fedramp-nist-800-171-security-questionnaire-api.p.rapidapi.com",
  match_key_personnel: "govcon-key-personnel-lcat-resume-tailoring-api.p.rapidapi.com",
  analyze_rfp_amendment_diff: "rfp-amendment-q-a-change-impact-analyzer-api.p.rapidapi.com",
  generate_cpars_past_performance: "cpars-past-performance-volume-generator-api.p.rapidapi.com",
  generate_igce_price_to_win: "govcon-igce-wrap-rate-price-to-win-modeler-api.p.rapidapi.com",
  generate_oral_presentation_prep: "govcon-oral-presentation-tech-demo-murder-board-prep-api.p.rapidapi.com",
  generate_ato_rmf_package: "govcon-rmf-continuous-ato-cato-ssp-poa-m-generator-api.p.rapidapi.com",
  analyze_debriefing_bid_protest: "govcon-debriefing-far-15-506-gao-bid-protest-analyzer-api.p.rapidapi.com",
  generate_gsa_mas_offer: "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com",
  generate_sources_sought_response: "ai-bid-no-bid-capability-matcher-api.p.rapidapi.com"
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
          "enum": [
            "RFP",
            "MSA",
            "SOW",
            "NDA",
            "SUBCONTRACT",
            "AUTO"
          ],
          "default": "AUTO",
          "description": "Optional document classification hint ('RFP', 'MSA', 'SOW', 'NDA', 'SUBCONTRACT', or 'AUTO') used to prioritize federal solicitation fields vs. commercial agreement terms."
        }
      },
      "required": [
        "raw_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "document_type": {
          "type": "string",
          "description": "Detected contract or solicitation type."
        },
        "parties": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Identified contracting parties or issuing agency."
        },
        "effective_date": {
          "type": [
            "string",
            "null"
          ],
          "description": "ISO-8601 effective or posting date if present."
        },
        "termination_or_due_date": {
          "type": [
            "string",
            "null"
          ],
          "description": "Contract expiration or proposal submission deadline."
        },
        "total_contract_value": {
          "type": [
            "number",
            "string",
            "null"
          ],
          "description": "Extracted total contract ceiling or value."
        },
        "payment_terms": {
          "type": [
            "string",
            "null"
          ],
          "description": "Payment schedule, Net terms, or contract pricing type (FFP, T&M, CPFF)."
        },
        "deliverables": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Core technical and operational deliverables."
        },
        "governing_law": {
          "type": [
            "string",
            "null"
          ],
          "description": "Governing jurisdiction or acquisition regulation (e.g., FAR/DFARS, Delaware)."
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
        }
      },
      "required": [
        "raw_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "overall_risk_score": {
          "type": "integer",
          "description": "Composite contract risk score from 0 (low risk) to 100 (critical risk)."
        },
        "risk_level": {
          "type": "string",
          "description": "Qualitative risk tier (LOW, MODERATE, HIGH, CRITICAL)."
        },
        "flagged_clauses": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Detected risky clauses with verbatim quote, risk rationale, and recommended redline replacement."
        }
      }
    }
  },
  {
    "name": "search_historical_awards",
    "title": "Search Historical Federal Contract Awards & CLIN Pricing",
    "description": "Query historical federal contract awards, incumbent prime contractors, award ceilings, and labor/CLIN pricing benchmarks filtered by keyword, agency, or 6-digit NAICS code. This is a read-only, deterministic database query (requires X-RapidAPI-Key; `keywords` is required and narrows scope descriptions, while optional `agency` and 6-digit `naics_code` filters intersect results and return up to 25 matching awards per call). Use this tool when researching past award prices, incumbent vendors, or Price-to-Win (PTW) benchmarks; use `get_live_solicitations` instead to find currently open RFPs available for bidding, or `classify_naics_psc_nigp` if you need to discover the right NAICS code first.",
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
          "description": "Optional issuing federal or state agency name substring filter (e.g., 'Department of Defense', 'Veterans Affairs')."
        },
        "naics_code": {
          "type": "string",
          "pattern": "^[0-9]{6}$",
          "description": "Optional exact 6-digit North American Industry Classification System (NAICS) code filter (e.g., '541512' for Computer Systems Design)."
        }
      },
      "required": [
        "keywords"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "total_matches": {
          "type": "integer",
          "description": "Number of historical award records matching the query."
        },
        "awards": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "List of historical contract awards with recipient, agency, ceiling amount, NAICS, and labor/CLIN benchmarks."
        }
      }
    }
  },
  {
    "name": "get_live_solicitations",
    "title": "Get Live Open Federal & State SLED RFPs",
    "description": "Retrieve currently open, AI-vetted Federal (SAM.gov) and State/Local SLED (VA, TX, CA, FL, MD, IL, PA, OH, GA, NC, NY, MA, NJ, DemandStar) IT, Cloud, and Cybersecurity solicitations from SignalTender's 15-portal procurement database. This is a read-only, non-destructive live database query (requires X-RapidAPI-Key; all four filter parameters are optional and combinable, returning up to `limit` [default 10, max 50] active solicitations whose closing dates have not passed). Use this tool when discovering active open RFPs to bid on right now; use `search_historical_awards` instead for past awarded contracts and incumbent pricing, or `match_capability_statement` once you have selected an RFP to score Bid/No-Bid Pwin.",
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
            "virginia",
            "texas",
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
            "municipal"
          ],
          "description": "Optional jurisdiction portal filter ('federal' for SAM.gov, 'virginia', 'texas', 'california', 'florida', 'maryland', 'illinois', 'pennsylvania', 'ohio', 'georgia', 'north_carolina', 'new_york', 'massachusetts', 'new_jersey', or 'municipal' for DemandStar)."
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
          "description": "Optional case-insensitive substring keyword matched against solicitation title and issuing buyer agency."
        },
        "limit": {
          "type": "integer",
          "minimum": 1,
          "maximum": 50,
          "default": 10,
          "description": "Maximum number of open solicitations to return per request (integer between 1 and 50; defaults to 10)."
        }
      }
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "count": {
          "type": "integer",
          "description": "Number of open solicitations returned."
        },
        "solicitations": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Active RFP records including id, title, agency, closing_date, jurisdiction, and official portal URL."
        }
      }
    }
  },
  {
    "name": "generate_compliance_matrix",
    "title": "Generate Shipley RFP Compliance Matrix & Proposal Outline",
    "description": "Shred unstructured RFP Section C (SOW/PWS), Section L (Instructions), and Section M (Evaluation Criteria) text into a numbered `shall`/`must` Requirements Traceability Matrix, Section L-to-M cross-reference map, and annotated Proposal Outline with page allocations. This is a read-only, stateless analysis operation (requires X-RapidAPI-Key; `raw_text` accepts 50 to 100,000 characters, and `proposal_methodology` selects 'shipley' [default Volume I-IV structure], 'federal_standard' [FAR 15.3], or 'commercial_agile' outline conventions). Use this tool first when shredding a base RFP into a compliance checklist and proposal outline; use `analyze_rfp_amendment_diff` instead when comparing an SF-30 amendment against a base RFP, or `generate_rfp_response` to draft the actual prose narrative for a specific section.",
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
            "federal_standard",
            "commercial_agile"
          ],
          "default": "shipley",
          "description": "Proposal structuring methodology: 'shipley' (default evaluator-first Volume I-IV outline with win themes), 'federal_standard' (strict FAR Part 15 Section L/M mapping), or 'commercial_agile' (B2B solution deliverable sprints)."
        }
      },
      "required": [
        "raw_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "requirements_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Extracted mandatory shall/must requirements with priority, volume assignment, and verification evidence needed."
        },
        "proposal_outline": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Hierarchical proposal sections with mapped requirement IDs, win theme strategy, and page allocation."
        }
      }
    }
  },
  {
    "name": "scan_far_dfars_clauses",
    "title": "Scan FAR / DFARS & CMMC Regulatory Flow-Down Clauses",
    "description": "Scan solicitation Section I or subcontract flow-down text to identify every FAR (`52.2xx`) and DFARS (`252.2xx`) clause, flag mandatory subcontractor flow-downs, and score CMMC 2.0, NIST SP 800-171, and FedRAMP compliance burden. This is a read-only, stateless regulatory audit (requires X-RapidAPI-Key; `raw_text` accepts 30 to 100,000 characters, and `contractor_role` adjusts risk severity and flow-down obligations for a 'prime_contractor' [default], 'subcontractor', or 'commercial_item_vendor' under FAR Part 12). Use this tool specifically for federal acquisition regulation (FAR/DFARS/CMMC) clause compliance; use `audit_contract_risks` instead for commercial MSA/NDA legal redlining, or `answer_security_questionnaire` to draft control-by-control NIST 800-171 / SOC 2 questionnaire responses.",
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
        }
      },
      "required": [
        "raw_text"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "compliance_burden_score": {
          "type": "integer",
          "description": "Regulatory compliance complexity score from 0 to 100."
        },
        "detected_clauses": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Parsed FAR/DFARS clauses with mandatory flow-down status, risk level, and remediation guidance."
        },
        "cybersecurity_posture_summary": {
          "type": "string",
          "description": "Required CMMC 2.0, NIST SP 800-171, or FedRAMP authorization posture."
        }
      }
    }
  },
  {
    "name": "match_capability_statement",
    "title": "Score Bid/No-Bid Pwin & Match Capability Statement",
    "description": "Evaluate an RFP scope against a vendor's Capability Statement and past performance to compute a 0-100 Probability of Win (Pwin) score, a Gate-1 Bid/No-Bid recommendation, a technical/socioeconomic gap analysis, and a tailored executive pitch. This is a read-only, stateless capture scoring call (requires X-RapidAPI-Key; both `rfp_text` and `company_capability_statement` are required, while `target_pursuit_role` weights eligibility rules for 'prime_contractor', 'subcontractor', or 'either_prime_or_sub' [default]). Use this tool at Gate-1 capture qualification to decide whether to bid an opportunity; use `generate_teaming_strategy` instead if you already decided to bid and need a 13 CFR 125.6 (50% Rule) Prime/Sub workshare plan, or `match_key_personnel` to evaluate individual candidate resumes.",
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
            "subcontractor",
            "either_prime_or_sub"
          ],
          "default": "either_prime_or_sub",
          "description": "Intended pursuit role: 'prime_contractor' enforces strict set-aside and past-performance minimums, 'subcontractor' scores niche workshare fit, and 'either_prime_or_sub' (default) recommends the highest-Pwin path."
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
        "pwin_score": {
          "type": "integer",
          "description": "Calculated Probability of Win (Pwin) score from 0 to 100."
        },
        "bid_recommendation": {
          "type": "string",
          "description": "Gate-1 recommendation (BID_AS_PRIME, BID_AS_SUB, TEAMING_REQUIRED, NO_BID)."
        },
        "strengths_and_discriminators": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Matched vendor capabilities and competitive discriminators."
        },
        "capability_gaps": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Unmet RFP requirements or compliance blockers."
        },
        "tailored_executive_pitch": {
          "type": "string",
          "description": "Ready-to-use executive summary pitch aligned to the buyer agency."
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
            "product_or_service_catalog"
          ],
          "default": "company_or_vendor_profile",
          "description": "Input context mode: 'company_or_vendor_profile' (default, optimizes for SAM.gov vendor registration & FinTech KYB SIC/NAICS), 'rfp_or_sow_scope' (optimizes for solicitation set-aside NAICS & Federal PSC), or 'product_or_service_catalog' (emphasizes NIGP/UNSPSC commodity codes)."
        },
        "max_secondary_codes": {
          "type": "integer",
          "minimum": 1,
          "maximum": 5,
          "default": 3,
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
        "primary_naics": {
          "type": "object",
          "description": "Top-ranked 6-digit NAICS code, title, confidence score, and official SBA Small Business Size Standard."
        },
        "secondary_naics_codes": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Up to max_secondary_codes alternative 6-digit NAICS classifications."
        },
        "sic_codes": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Matched 4-digit Standard Industrial Classification (SIC) codes."
        },
        "federal_psc_codes": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Matched 4-character Federal Product Service Codes (PSC)."
        },
        "state_unspsc_and_nigp_codes": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Matched State SLED NIGP and 8-digit UNSPSC commodity codes."
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
            "past_performance_narrative"
          ],
          "default": "technical_approach",
          "description": "Target proposal section structure: 'technical_approach' (default, solution architecture & requirement execution), 'executive_summary' (vision & discriminators), 'management_and_staffing_plan' (governance, transition & QA), or 'past_performance_narrative' (prose summary)."
        },
        "tone_and_methodology": {
          "type": "string",
          "default": "Shipley Proposal Methodology (Active Voice, Evaluator-First, Feature-Benefit-Proof)",
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
          "description": "Compliance-mapped heading for the drafted proposal section."
        },
        "drafted_narrative_markdown": {
          "type": "string",
          "description": "Full Shipley-formatted proposal section prose in Markdown."
        },
        "win_themes_and_discriminators": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Key win themes and ghosting points embedded in the draft."
        },
        "strategic_clarification_questions": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Strategic vendor Q&A questions to submit to the Contracting Officer to expose ambiguous or competitor-wired specs."
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
            "auto_detect",
            "federal_section_b_clin_schedule",
            "gsa_or_tm_labor_rate_card",
            "b2b_vendor_quote_or_bom",
            "commercial_invoice"
          ],
          "default": "auto_detect",
          "description": "Document schema hint: 'auto_detect' (default), 'federal_section_b_clin_schedule' (parses Base/Option Year CLINs & contract types like FFP/T&M), 'gsa_or_tm_labor_rate_card' (LCAT hourly rates), 'b2b_vendor_quote_or_bom', or 'commercial_invoice'."
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
        "detected_document_type": {
          "type": "string",
          "description": "Classified pricing document type."
        },
        "dominant_pricing_model": {
          "type": "string",
          "description": "Primary contract pricing structure (e.g., FIRM_FIXED_PRICE_FFP, TIME_AND_MATERIALS_TM)."
        },
        "line_items": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Normalized CLIN/line items with quantity, unit, unit_price, extended_price, and period."
        },
        "calculated_grand_total": {
          "type": "number",
          "description": "Verified sum of all extracted line items."
        },
        "math_discrepancies": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Flagged arithmetic errors or rate anomalies when audit_math_and_anomalies is enabled."
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
        "workshare_allocation": {
          "type": "object",
          "description": "Compliant Prime vs. Subcontractor percentage split under 13 CFR 125.6."
        },
        "ostensible_subcontractor_risk": {
          "type": "string",
          "description": "SBA 13 CFR 121.103(h)(3) affiliation risk assessment and mitigation steps."
        },
        "recommended_partner_archetypes": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Ideal subcontractor or prime partner profiles to close capability gaps."
        },
        "teaming_agreement_clauses": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Ready-to-paste FAR Subpart 9.6 Teaming Agreement exclusivity and workshare clauses."
        },
        "partner_outreach_email": {
          "type": "string",
          "description": "Tailored business development outreach email to recruit teaming partners."
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
        "detected_framework": {
          "type": "string",
          "description": "Primary compliance standard applied to the responses."
        },
        "estimated_dod_sprs_score": {
          "type": [
            "integer",
            "null"
          ],
          "description": "Calculated DoD SPRS score (-203 to 110) when NIST 800-171 / CMMC applies."
        },
        "question_responses": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Audit-ready answers with compliance status, control citations, and verification evidence."
        },
        "poam_remediation_items": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Plan of Action and Milestones (POA&M) entries for partially met or unmet controls."
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
        "qualification_score": {
          "type": "integer",
          "description": "Candidate LCAT/Key Personnel compliance score from 0 to 100."
        },
        "compliance_verdict": {
          "type": "string",
          "description": "Eligibility status (FULLY_QUALIFIED, QUALIFIED_VIA_SUBSTITUTION, NON_COMPLIANT_GAP)."
        },
        "requirement_audit_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Line-by-line audit of education, years of experience, clearance, and certification mandates."
        },
        "tailored_shipley_resume_markdown": {
          "type": "string",
          "description": "Rewritten Shipley Key Personnel biographical sketch and compliance-mapped experience bullets."
        },
        "letter_of_commitment_loc": {
          "type": "string",
          "description": "Ready-to-sign Key Personnel Letter of Commitment (LOC) template."
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
        "schedule_and_page_limit_changes": {
          "type": "object",
          "description": "Detected due-date extensions, page-limit updates, and administrative modifications."
        },
        "material_requirement_changes": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Added, modified, or deleted shall/must requirements and de-facto Q&A mandates."
        },
        "invalidated_proposal_sections": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Affected proposal sections with severity and ready-to-paste Shipley redraft language."
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
        "overall_confidence_assessment": {
          "type": "string",
          "description": "Predicted DoD Source Selection Performance Confidence rating (e.g., Substantial Confidence)."
        },
        "tailored_citations": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Shipley Volume III citations with Relevance rating, Scope/Magnitude/Complexity mapping, FAR 42.1503 5-factor CPARS narrative, and CCAR blocks."
        },
        "gap_mitigation_strategies": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Shipley narrative mitigations for any recency, dollar-magnitude, or prime-role gaps."
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
          "maxLength": 60000,
          "description": "Optional incumbent contract value, FPDS/USAspending historical award benchmarks, GSA MAS SIN 54151S CALC+ ceiling rates, or known agency budget ceilings to anchor the IGCE and Price-to-Win model."
        },
        "bidder_indirect_wrap_assumptions": {
          "type": "string",
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
        "recommended_price_to_win_usd": {
          "type": "number",
          "description": "Recommended total evaluated Price-to-Win ($ USD) across Base and all Option Years."
        },
        "independent_government_cost_estimate_igce_usd": {
          "type": "number",
          "description": "Estimated Independent Government Cost Estimate (IGCE) baseline ($ USD) across the full PoP."
        },
        "cost_realism_and_price_reasonableness_posture": {
          "type": "string",
          "description": "FAR 15.404-1 Price Reasonableness and Cost Realism risk posture."
        },
        "wrap_rate_calculator_breakdown": {
          "type": "object",
          "description": "Compounded Fringe, Overhead, G&A, and Fee/Profit wrap-rate breakdown."
        },
        "lcat_rate_card_and_fte_buildup": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Bottom-up LCAT staffing, unburdened direct wage, burdened bill rate, and GSA CALC+ benchmark table."
        },
        "ptw_sensitivity_scenarios": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "4-scenario Price-to-Win sensitivity matrix with Pwin impact and SSEB tradeoff analysis."
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
        "proposed_solution_and_key_personnel": {
          "type": "string",
          "minLength": 20,
          "maxLength": 80000,
          "description": "Proposed technical/management solution architecture, key discriminators, and named Key Personnel speakers (roles, clearances, domain expertise, and past performance proof points) who will present."
        },
        "known_incumbent_and_risk_areas": {
          "type": "string",
          "maxLength": 30000,
          "description": "Optional competitive context, incumbent vulnerabilities, transition risks, or technical gaps where the Source Selection Evaluation Board (SSEB) is likely to probe during Murder-Board Q&A."
        },
        "presentation_format_mode": {
          "type": "string",
          "enum": [
            "COMBINED_ORALS_TECH_DEMO_AND_QA",
            "EXECUTIVE_SLIDE_BRIEFING_AND_QA",
            "LIVE_TECHNICAL_SCENARIO_CHALLENGE",
            "KEY_PERSONNEL_INTERVIEW_AND_CAUCUS"
          ],
          "default": "COMBINED_ORALS_TECH_DEMO_AND_QA",
          "description": "Oral presentation format mode: 'COMBINED_ORALS_TECH_DEMO_AND_QA' (default, slide deck + live technical demo + Q&A), 'EXECUTIVE_SLIDE_BRIEFING_AND_QA' (Shipley slide deck + Q&A), 'LIVE_TECHNICAL_SCENARIO_CHALLENGE' (on-the-spot engineering problem/coding challenge), or 'KEY_PERSONNEL_INTERVIEW_AND_CAUCUS' (structured SSEB oral interview)."
        }
      },
      "required": [
        "rfp_oral_instructions_and_sow_text",
        "proposed_solution_and_key_personnel"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "predicted_oral_confidence_rating": {
          "type": "string",
          "description": "Predicted DoD/Federal Source Selection Oral Confidence rating (e.g., High Confidence / Outstanding)."
        },
        "slide_deck_blueprint": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Slide-by-slide Shipley oral presentation deck with assigned Key Personnel speaker, time budget, visual layout, and talking points."
        },
        "live_tech_demo_runbook": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Minute-by-minute live technical demonstration runbook with operator actions, telemetry proof, and backup failover plans."
        },
        "murder_board_qa_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Adversarial SSEB Murder-Board questions paired with Answer-First-Elaborate-Anchor responses and trap-avoidance rules."
        },
        "evaluator_caucus_takeaways": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Verbatim strengths designed for SSEB evaluators to record on consensus scoring sheets."
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
        "system_architecture_and_rfp_cyber_text": {
          "type": "string",
          "minLength": 40,
          "maxLength": 100000,
          "description": "Raw RFP Section C/L/M cybersecurity & ATO requirements, target system architecture, data types processed (CUI, CDI, ITAR, PHI, PII, CJIS), user communities, and interconnection boundaries (40 to 100,000 characters)."
        },
        "cloud_hosting_and_inherited_controls_context": {
          "type": "string",
          "minLength": 20,
          "maxLength": 80000,
          "description": "Cloud Service Provider (CSP) enclave (AWS GovCloud, Azure Government, GCP Assured Workloads, on-prem), platform layer (Kubernetes, Platform One BigBang, Serverless), and existing security tooling (SIEM, SOAR, ICAM, SAST/DAST)."
        },
        "target_authorization_framework": {
          "type": "string",
          "enum": [
            "dod_rmf_dodi_8510_01_cato",
            "fedramp_rev5_agency_ato",
            "stateramp_txramp_govramp",
            "nist_800_171_cmmc_level_2"
          ],
          "default": "dod_rmf_dodi_8510_01_cato",
          "description": "Target authorization framework: 'dod_rmf_dodi_8510_01_cato' (default DoD RMF & Continuous ATO), 'fedramp_rev5_agency_ato' (Civilian Federal Agency ATO / FedRAMP Rev 5), 'stateramp_txramp_govramp' (State SLED StateRAMP / TX-RAMP / GovRAMP), or 'nist_800_171_cmmc_level_2' (CMMC 2.0 Level 2)."
        },
        "target_impact_level": {
          "type": "string",
          "enum": [
            "IL2_LOW",
            "IL4_MODERATE_CUI",
            "IL5_CUI_NSS",
            "IL6_CLASSIFIED_HIGH",
            "FEDRAMP_MODERATE",
            "FEDRAMP_HIGH"
          ],
          "default": "IL5_CUI_NSS",
          "description": "Target DoD Cloud Computing SRG Impact Level or FIPS 199 baseline: 'IL2_LOW', 'IL4_MODERATE_CUI', 'IL5_CUI_NSS' (default), 'IL6_CLASSIFIED_HIGH', 'FEDRAMP_MODERATE', or 'FEDRAMP_HIGH'."
        }
      },
      "required": [
        "system_architecture_and_rfp_cyber_text",
        "cloud_hosting_and_inherited_controls_context"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "authorization_boundary_summary": {
          "type": "string",
          "description": "Executive summary of the system authorization boundary, hosting enclave, and target ATO pathway."
        },
        "fips_199_security_categorization": {
          "type": "object",
          "description": "FIPS 199 & CNSSI 1253 Confidentiality/Integrity/Availability categorization and overall high-water mark."
        },
        "control_inheritance_summary": {
          "type": "string",
          "description": "Estimated breakdown of Inherited CSP Controls vs. Hybrid Shared Controls vs. Customer-Implemented Controls."
        },
        "ssp_control_implementation_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "NIST SP 800-53 Rev 5 SSP control family implementation narratives, STIG mappings, and audit artifacts."
        },
        "emass_poam_remediation_schedule": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "eMASS / CSAM-ready POA&M entries with CAT I/II/III severity, compensating controls, and milestones."
        },
        "continuous_ato_conmon_blueprint": {
          "type": "object",
          "description": "Continuous ATO (cATO) DevSecOps pipeline gates, OSCAL automation, and ConMon cadence."
        }
      }
    }
  },
  {
    "name": "analyze_debriefing_bid_protest",
    "title": "Analyze GovCon Post-Award Debriefing, FAR 15.506 Q&A & GAO Bid-Protest Viability",
    "description": "Analyze an Unsuccessful Offeror Notice, SSEB evaluation scorecard, RFP Section M criteria, and submitted proposal excerpts to generate strategic FAR 15.506 / DFARS 252.215-7016 Enhanced Debriefing follow-up questions, a 0-100 GAO Bid-Protest Viability Score, a Go/No-Go protest recommendation, CICA 31 U.S.C. 3553 automatic stay deadline calculations, a 4-C.F.R. Part 21 Protest Grounds Matrix (Unstated Evaluation Criteria, Disparate Treatment, Flawed Best-Value Tradeoff, Misleading Discussions), and an Executive Recompete/Corrective-Action Playbook. This is a read-only, stateless post-award diagnostic and debriefing analysis call that provides structured procurement intelligence rather than formal legal representation (requires X-RapidAPI-Key; `unsuccessful_offeror_notice_and_debrief_text` accepts 30 to 100,000 characters, `rfp_section_m_and_submitted_proposal_excerpts` accepts 30 to 100,000 characters, optional `award_and_debrief_timeline_context` anchors the 10-day GAO filing and 5-day CICA stay clock, and `target_acquisition_regime` calibrates rules across DoD DFARS Enhanced Debriefings, Civilian FAR Part 15, FAR 16.505 Task Orders >$10M/$35M, and FAR 8.405-2 GSA MAS). Use this tool after contract award notification when preparing for a FAR 15.506 post-award debriefing or evaluating GAO/COFC bid-protest grounds; use `match_capability_statement` instead for pre-bid Gate-1 Bid/No-Bid Pwin scoring, or `analyze_rfp_amendment_diff` for pre-award SF-30 solicitation amendments.",
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
        "unsuccessful_offeror_notice_and_debrief_text": {
          "type": "string",
          "minLength": 30,
          "maxLength": 100000,
          "description": "Raw text from the Agency Notice of Unsuccessful Offeror, Pre-Award/Post-Award Debriefing slides or letter, Source Selection Decision Document (SSDD) redacted summary, and adjectival/price scores for the Awardee vs. your offer (30 to 100,000 characters)."
        },
        "rfp_section_m_and_submitted_proposal_excerpts": {
          "type": "string",
          "minLength": 30,
          "maxLength": 100000,
          "description": "Relevant RFP Section L/M evaluation criteria, relative factor weights, and excerpts from your submitted proposal that directly address or refute the weaknesses or deficiencies cited by the Source Selection Evaluation Board (SSEB) (30 to 100,000 characters)."
        },
        "award_and_debrief_timeline_context": {
          "type": "string",
          "maxLength": 20000,
          "description": "Optional timeline context including contract award notification date, date debriefing was requested, date written/oral debriefing was received, and whether DoD DFARS 252.215-7016 2-business-day Enhanced Debriefing Q&A remains open."
        },
        "target_acquisition_regime": {
          "type": "string",
          "enum": [
            "dod_dfars_enhanced_debrief_far_15_506",
            "civilian_far_15_506_negotiated",
            "far_16_505_idid_task_order",
            "far_8_405_gsa_fss_brief_explanation"
          ],
          "default": "dod_dfars_enhanced_debrief_far_15_506",
          "description": "Governing acquisition regime: 'dod_dfars_enhanced_debrief_far_15_506' (default DoD Enhanced Post-Award Debriefing under DFARS 252.215-7016 & FAR 15.506), 'civilian_far_15_506_negotiated' (Civilian Agency FAR Part 15), 'far_16_505_idid_task_order' (IDIQ/GWAC Task Order under FAR 16.505(b)(6) with >$10M Civilian / >$35M DoD GAO protest threshold), or 'far_8_405_gsa_fss_brief_explanation' (GSA MAS Schedule order under FAR 8.405-2(d))."
        }
      },
      "required": [
        "unsuccessful_offeror_notice_and_debrief_text",
        "rfp_section_m_and_submitted_proposal_excerpts"
      ]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "protest_viability_score": {
          "type": "integer",
          "description": "Quantitative GAO / Agency-Level Bid-Protest viability score from 0 to 100."
        },
        "protest_go_no_go_recommendation": {
          "type": "string",
          "description": "Strategic post-award recommendation (e.g., FILE_GAO_PROTEST_WITH_CICA_STAY, SUBMIT_ENHANCED_DEBRIEF_QUESTIONS_FIRST, DO_NOT_PROTEST_PIVOT_TO_RECOMPETE)."
        },
        "cica_automatic_stay_and_filing_deadlines": {
          "type": "object",
          "description": "Calculated CICA 31 U.S.C. 3553 automatic stay deadline (5 calendar days post-debrief close) and GAO 10-day timeliness deadline."
        },
        "sseb_scorecard_and_tradeoff_audit": {
          "type": "object",
          "description": "Comparative audit of Awardee vs. Bidder adjectival ratings, price premium, and FAR 15.308 Best-Value Tradeoff flaws."
        },
        "far_15_506_enhanced_debriefing_questions": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Precision written questions for the Contracting Officer under FAR 15.506 / DFARS 252.215-7016."
        },
        "gao_protest_grounds_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Evaluated bid-protest grounds with GAO case-law precedents, RFP/proposal evidence, and competitive prejudice analysis."
        },
        "corrective_action_and_recompete_playbook": {
          "type": "string",
          "description": "Executive action plan for agency corrective action or positioning for task-order on-ramps and recompetes."
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
          "description": "Overall GSA eOffer / eMod readiness score from 0 to 100."
        },
        "recommended_pricing_pathway": {
          "type": "string",
          "description": "Recommended GSA pricing disclosure regime (TDR vs. CSP-1 MFC) and rationale."
        },
        "iff_and_epa_pricing_summary": {
          "type": "string",
          "description": "Summary of 0.75% Industrial Funding Fee (`Net / 0.9925`) calculation and 5-year EPA escalation."
        },
        "sin_mapping_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Mapped GSA MAS SINs (`54151S`, `54151HACS`, `518210C`, `OLM`) with Factor 4 project narratives."
        },
        "gsa_lcat_iff_price_list": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "GSA Price Proposal Template (PPT) rate card with CPL, Net, 0.75% IFF ceiling rate, and 5-year EPA progression."
        },
        "prc_and_mfc_compliance_guardrails": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "GSAR 552.238-81 Price Reductions Clause (PRC) and Most Favored Customer (MFC) safe-harbor guardrails."
        },
        "ready_to_submit_scp_fss_001_narrative": {
          "type": "string",
          "description": "Paste-ready SCP-FSS-001 Administrative, Technical, and Price Proposal narrative for GSA eOffer / eMod."
        }
      }
    }
  },
  {
    "name": "generate_sources_sought_response",
    "title": "Generate Sources Sought, RFI Capability Matrix & Rule-of-Two Set-Aside Shaping Package",
    "description": "Transform a government Sources Sought Notice, Request for Information (RFI), or draft PWS/SOW and a contractor's capability profile into a FAR Part 10 market-research response package containing a requirement-by-requirement capability matrix, a FAR 19.502-2 Rule-of-Two small business set-aside justification (8(a), SDVOSB, WOSB/EDWOSB, HUBZone, or Total Small Business), NAICS/PSC size-standard recommendations, incumbent/competitor lock-in neutralization questions, and a paste-ready Sources Sought cover letter and technical response narrative. This is a read-only, stateless, non-destructive capture-shaping generator (requires X-RapidAPI-Key; `sources_sought_or_rfi_notice_text` accepts 20 to 45,000 characters and `vendor_capability_and_socioeconomic_profile` accepts 20 to 35,000 characters). Use this tool when responding to pre-RFP Sources Sought notices or RFIs to influence set-aside determination, NAICS code selection, and contract vehicle choice; use `generate_rfp_response` instead when drafting final proposal volumes for a formal solicitation, or `match_capability_statement` for a fast Bid/No-Bid Pwin score.",
    "annotations": {
      "title": "Generate Sources Sought, RFI Capability Matrix & Rule-of-Two Set-Aside Shaping Package",
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
          "description": "Full text of the government Sources Sought Notice, Request for Information (RFI), Market Research Questionnaire, or draft PWS/SOW (20 to 45,000 characters)."
        },
        "vendor_capability_and_socioeconomic_profile": {
          "type": "string",
          "minLength": 20,
          "maxLength": 35000,
          "description": "Contractor's core technical capabilities, past performance citations, socio-economic certifications (8(a), SDVOSB, WOSB, HUBZone, Small Business), active contract vehicles (GSA MAS, OASIS+, SEWP, CIO-SP3), UEI/CAGE, and clearance posture (20 to 35,000 characters)."
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
          "description": "Preferred FAR Part 19 set-aside pathway to justify to the Contracting Officer and OSDBU, or 'Auto_Recommend'."
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
        "shaping_confidence_score": {
          "type": "integer",
          "description": "Confidence score (0-100) that the contractor's response demonstrates full technical capability and supports the target acquisition strategy."
        },
        "recommended_set_aside_determination": {
          "type": "string",
          "description": "Recommended FAR Part 19 set-aside classification supported by Rule-of-Two evidence."
        },
        "recommended_naics_and_psc": {
          "type": "object",
          "description": "Recommended NAICS code, SBA size standard, PSC code, and strategic sizing justification."
        },
        "rule_of_two_set_aside_justification": {
          "type": "object",
          "description": "FAR 19.502-2 Rule-of-Two market research argument and suggested GWAC/Schedule vehicle."
        },
        "rfi_requirement_alignment_matrix": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Requirement-by-requirement alignment mapping each RFI/PWS area to contractor capabilities and past performance."
        },
        "strategic_shaping_questions_for_co": {
          "type": "array",
          "items": {
            "type": "object"
          },
          "description": "Strategic questions for the Contracting Officer to neutralize incumbent lock-in and shape Section L/M."
        },
        "ready_to_submit_sources_sought_narrative": {
          "type": "string",
          "description": "Complete, paste-ready Sources Sought / RFI cover letter, administrative data table, capability narrative, and set-aside recommendation."
        }
      }
    }
  }
];

const ENDPOINT_MAP = {
  parse_b2b_contract: { method: "POST", path: "/v1/parse/contract" },
  audit_contract_risks: { method: "POST", path: "/v1/parse/contract-risks" },
  search_historical_awards: { method: "POST", path: "/v1/awards/search" },
  get_live_solicitations: { method: "GET", path: "/v1/solicitations/live" },
  generate_compliance_matrix: { method: "POST", path: "/v1/generate/compliance-matrix" },
  scan_far_dfars_clauses: { method: "POST", path: "/v1/audit/far-dfars-clauses" },
  match_capability_statement: { method: "POST", path: "/v1/match/capability-statement" },
  classify_naics_psc_nigp: { method: "POST", path: "/v1/classify/naics-psc-nigp" },
  generate_rfp_response: { method: "POST", path: "/v1/generate/rfp-response" },
  extract_pricing_schedule: { method: "POST", path: "/v1/extract/pricing-schedule" },
  generate_teaming_strategy: { method: "POST", path: "/v1/generate/teaming-strategy" },
  answer_security_questionnaire: { method: "POST", path: "/v1/audit/security-questionnaire" },
  match_key_personnel: { method: "POST", path: "/v1/match/key-personnel" },
  analyze_rfp_amendment_diff: { method: "POST", path: "/v1/analyze/amendment-diff" },
  generate_cpars_past_performance: { method: "POST", path: "/v1/generate/past-performance" },
  generate_igce_price_to_win: { method: "POST", path: "/v1/generate/price-to-win" },
  generate_oral_presentation_prep: { method: "POST", path: "/v1/generate/oral-presentation-prep" },
  generate_ato_rmf_package: { method: "POST", path: "/v1/generate/ato-rmf-package" },
  analyze_debriefing_bid_protest: { method: "POST", path: "/v1/generate/debriefing-bid-protest" },
  generate_gsa_mas_offer: { method: "POST", path: "/v1/generate/gsa-mas-offer" },
  generate_sources_sought_response: { method: "POST", path: "/v1/generate/sources-sought-response" }
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

  const fetchOptions = {
    method: route.method,
    headers
  };

  if (route.method === "GET" && args && typeof args === "object") {
    Object.entries(args).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        url.searchParams.set(k, String(v));
      }
    });
  } else if (route.method === "POST") {
    fetchOptions.body = JSON.stringify(args || {});
  }

  const response = await fetch(url.toString(), fetchOptions);
  const text = await response.text();
  return {
    isError: !response.ok,
    content: [
      {
        type: "text",
        text
      }
    ]
  };
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
            version: "1.7.0"
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

