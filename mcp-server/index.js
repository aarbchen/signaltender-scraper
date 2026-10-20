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
  analyze_rfp_amendment_diff: "rfp-amendment-q-a-change-impact-analyzer-api.p.rapidapi.com"
};

const TOOLS = [
  {
    name: "parse_b2b_contract",
    description:
      "API #01: Extract structured JSON (party names, effective/termination dates, total contract value, payment terms, deliverables, and governing law) from unstructured B2B contracts, SOWs, or RFPs.",
    inputSchema: {
      type: "object",
      properties: {
        raw_text: {
          type: "string",
          description: "Raw unstructured text from a contract, Statement of Work (SOW), or RFP (min 50 chars)."
        },
        document_type_hint: {
          type: "string",
          description: "Optional document type hint (e.g., 'RFP', 'MSA', 'SOW')."
        }
      },
      required: ["raw_text"]
    }
  },
  {
    name: "audit_contract_risks",
    description:
      "API #02: Audit legal contracts (MSAs, NDAs, Subcontracts, SaaS agreements) for toxic clauses, score overall risk (0-100), and generate verbatim clause quotes with ready-to-paste fallback redline language.",
    inputSchema: {
      type: "object",
      properties: {
        raw_text: {
          type: "string",
          description: "Full or partial contract text to audit for legal and commercial risks."
        },
        party_perspective: {
          type: "string",
          enum: ["vendor", "buyer", "neutral"],
          default: "vendor",
          description: "Negotiating perspective for redline generation ('vendor', 'buyer', or 'neutral')."
        }
      },
      required: ["raw_text"]
    }
  },
  {
    name: "search_historical_awards",
    description:
      "API #03: Query historical federal contract awards, incumbent prime contractors, award ceilings, and CLIN pricing benchmarks by keyword, NAICS code, or agency.",
    inputSchema: {
      type: "object",
      properties: {
        keywords: {
          type: "string",
          description: "Search keywords (e.g., 'zero trust', 'cloud migration', 'SIEM')."
        },
        agency: {
          type: "string",
          description: "Optional agency name filter."
        },
        naics_code: {
          type: "string",
          description: "Optional 6-digit NAICS code filter (e.g., '541512')."
        }
      },
      required: ["keywords"]
    }
  },
  {
    name: "get_live_solicitations",
    description:
      "API #04: Stream live, AI-vetted open Federal (SAM.gov) and State/Local SLED (VA, TX, CA, FL, MD, DemandStar) IT, Cloud, and Cybersecurity RFPs from SignalTender's 7-portal procurement database.",
    inputSchema: {
      type: "object",
      properties: {
        state: {
          type: "string",
          description: "Optional jurisdiction filter ('federal', 'virginia', 'texas', 'california', 'florida', 'maryland', 'municipal')."
        },
        category: {
          type: "string",
          description: "Optional IT vertical filter ('cybersecurity', 'cloud-infrastructure', 'software-development', 'network-telecom')."
        },
        keyword: {
          type: "string",
          description: "Optional search keyword in solicitation title or agency."
        },
        limit: {
          type: "integer",
          default: 10,
          description: "Max number of open solicitations to return (1-50)."
        }
      }
    }
  },
  {
    name: "generate_compliance_matrix",
    description:
      "API #05: Parse raw RFP Section C/L/M or SOW text into a Shipley-aligned shall/must Compliance Matrix, Section L-to-M cross-reference map, and hierarchical Proposal Outline with page allocations.",
    inputSchema: {
      type: "object",
      properties: {
        raw_text: {
          type: "string",
          description: "Raw RFP Section C (SOW), Section L (Instructions), and/or Section M (Evaluation Criteria) text."
        },
        proposal_methodology: {
          type: "string",
          enum: ["shipley", "standard_b2b", "federal_far"],
          default: "shipley",
          description: "Proposal structuring methodology."
        }
      },
      required: ["raw_text"]
    }
  },
  {
    name: "scan_far_dfars_clauses",
    description:
      "API #06: Detect FAR (52.2xx) and DFARS (252.2xx) regulatory clauses in a solicitation, flag mandatory subcontractor flow-downs, and score CMMC 2.0 / NIST 800-171 / FedRAMP compliance burden.",
    inputSchema: {
      type: "object",
      properties: {
        raw_text: {
          type: "string",
          description: "Solicitation Section I or subcontract flow-down text containing FAR/DFARS citations."
        },
        contractor_role: {
          type: "string",
          enum: ["prime_contractor", "subcontractor", "commercial_item_vendor"],
          default: "prime_contractor",
          description: "Role of the contractor evaluating the clauses."
        }
      },
      required: ["raw_text"]
    }
  },
  {
    name: "match_capability_statement",
    description:
      "API #07: Compare an RFP against a company's Capability Statement & Past Performance to calculate a 0-100 Pwin (Probability of Win) Score, Bid/No-Bid decision, gap analysis, and tailored executive pitch.",
    inputSchema: {
      type: "object",
      properties: {
        rfp_text: {
          type: "string",
          description: "Solicitation scope, mandatory qualifications, set-aside, and evaluation criteria."
        },
        company_capability_statement: {
          type: "string",
          description: "Vendor capability statement, socioeconomic certs, clearances, and past performance."
        },
        target_pursuit_role: {
          type: "string",
          enum: ["prime_contractor", "subcontractor_or_jv", "either_prime_or_sub"],
          default: "either_prime_or_sub"
        }
      },
      required: ["rfp_text", "company_capability_statement"]
    }
  },
  {
    name: "classify_naics_psc_nigp",
    description:
      "API #08: Map any product description, SOW, or company profile to exact 6-digit NAICS, 4-digit SIC (for KYB/FinTech), Federal PSC, and State NIGP/UNSPSC commodity codes with SBA size standards.",
    inputSchema: {
      type: "object",
      properties: {
        description_text: {
          type: "string",
          description: "Company profile, product description, or Statement of Work text."
        },
        context_type: {
          type: "string",
          enum: ["company_or_vendor_profile", "rfp_or_sow_scope", "product_or_service_catalog"],
          default: "company_or_vendor_profile"
        },
        max_secondary_codes: {
          type: "integer",
          default: 3
        }
      },
      required: ["description_text"]
    }
  },
  {
    name: "generate_rfp_response",
    description:
      "API #09: Draft an evaluator-ready Shipley Technical Proposal Section (with Win Themes, Proof Points, and Risk Mitigations) AND generate strategic Vendor Clarification Q&A questions.",
    inputSchema: {
      type: "object",
      properties: {
        rfp_section_text: {
          type: "string",
          description: "RFP Section C/L/M requirements to respond to."
        },
        company_context_and_capabilities: {
          type: "string",
          description: "Bidder's technical capabilities, past performance metrics, and differentiators."
        },
        target_section_type: {
          type: "string",
          enum: ["technical_approach", "executive_summary", "management_and_staffing_plan", "past_performance_narrative"],
          default: "technical_approach"
        },
        tone_and_methodology: {
          type: "string",
          enum: ["shipley_federal", "sled_state_municipal", "enterprise_commercial"],
          default: "shipley_federal"
        }
      },
      required: ["rfp_section_text", "company_context_and_capabilities"]
    }
  },
  {
    name: "extract_pricing_schedule",
    description:
      "API #10: Extract multi-tier CLIN/SLIN pricing tables, GSA/T&M labor rate cards, and BOM spreadsheets from unstructured vendor quotes or Section B schedules into normalized JSON with line-by-line math verification.",
    inputSchema: {
      type: "object",
      properties: {
        document_text: {
          type: "string",
          description: "Raw text or table content from a vendor quote, invoice, or Federal Section B CLIN schedule."
        },
        expected_document_type: {
          type: "string",
          enum: ["auto_detect", "federal_section_b_clin_schedule", "gsa_or_tm_labor_rate_card", "b2b_vendor_quote_or_bom", "commercial_invoice"],
          default: "auto_detect"
        },
        audit_math_and_anomalies: {
          type: "boolean",
          default: true
        }
      },
      required: ["document_text"]
    }
  },
  {
    name: "generate_teaming_strategy",
    description:
      "API #11: Analyze an RFP and bidder capabilities to generate a 13 CFR 125.6 / FAR 52.219-14 Limitations on Subcontracting (50% Rule) workshare plan, capability gap & partner archetypes, FAR 9.6 Teaming Agreement clauses, and partner outreach emails.",
    inputSchema: {
      type: "object",
      properties: {
        rfp_text: {
          type: "string",
          description: "Raw text from the RFP, Statement of Work (SOW), or Section L/M evaluation criteria."
        },
        bidder_capabilities: {
          type: "string",
          description: "Summary of the bidder's socioeconomic status, facility clearances, past performance, and technical capabilities."
        },
        set_aside_type: {
          type: "string",
          enum: ["full_and_open", "small_business", "sdvosb", "8a", "wosb_edwosb", "hubzone"],
          default: "sdvosb"
        },
        bidder_role: {
          type: "string",
          enum: ["prime_seeking_subs", "sub_seeking_prime", "joint_venture_mentor_protege"],
          default: "prime_seeking_subs"
        }
      },
      required: ["rfp_text", "bidder_capabilities"]
    }
  },
  {
    name: "answer_security_questionnaire",
    description:
      "API #12: Auto-answer SOC 2, FedRAMP, NIST SP 800-171, CMMC 2.0, and CAIQ/SIG/HECVAT vendor security questionnaires with cross-framework control citations, DoD SPRS readiness metrics, evidence artifact recommendations, and Plan of Action & Milestones (POA&M) remediation items.",
    inputSchema: {
      type: "object",
      properties: {
        questionnaire_text: {
          type: "string",
          description: "Raw security questionnaire items from an enterprise SIG/CAIQ/HECVAT spreadsheet or Federal RFP / SSP checklist."
        },
        security_posture_summary: {
          type: "string",
          description: "Summary of the vendor's cloud stack, certifications (SOC 2, ISO 27001, FedRAMP, CMMC), encryption, IAM/MFA, and logging controls."
        },
        target_framework: {
          type: "string",
          enum: ["auto_detect", "soc2_iso27001", "nist_800_171_cmmc", "fedramp_800_53", "caiq_sig_hecvat"],
          default: "auto_detect"
        }
      },
      required: ["questionnaire_text", "security_posture_summary"]
    }
  },
  {
    name: "match_key_personnel",
    description:
      "API #13: Audit candidate resumes against RFP Section L/M Key Personnel and GSA MAS / OASIS+ / Alliant 3 Labor Category (LCAT) qualification requirements, rewrite experience into Shipley Key Personnel bio & bullet citations, and generate a ready-to-sign Letter of Commitment (LOC).",
    inputSchema: {
      type: "object",
      properties: {
        lcat_or_rfp_requirements: {
          type: "string",
          description: "Raw RFP Section L/M Key Personnel requirements, GSA LCAT minimums, clearance mandates, and DoD 8570/8140 certification criteria."
        },
        candidate_resume_text: {
          type: "string",
          description: "Candidate's raw resume, CV, security clearance level, certifications, education, and work history."
        },
        allow_education_experience_substitution: {
          type: "boolean",
          default: true
        }
      },
      required: ["lcat_or_rfp_requirements", "candidate_resume_text"]
    }
  },
  {
    name: "analyze_rfp_amendment_diff",
    description:
      "API #14: Diff base RFP/SOW text against SF-30 Solicitation Amendments, SLED Addenda, and official Government Q&A clarification matrices to flag altered mandates, deadline extensions, CLIN pricing changes, and invalidated proposal sections.",
    inputSchema: {
      type: "object",
      properties: {
        base_solicitation_text: {
          type: "string",
          description: "Raw text from the base RFP, Statement of Work (Section C), Instructions (Section L), Pricing Schedule (Section B), or Evaluation Criteria (Section M)."
        },
        amendment_or_qa_text: {
          type: "string",
          description: "Raw text from one or more SF-30 Solicitation Amendments, SLED Addenda, or official Government Q&A clarification matrices."
        },
        current_proposal_outline: {
          type: "string",
          description: "Optional summary of the bidder's existing proposal outline, page budget, or technical baseline to audit for invalidated sections."
        }
      },
      required: ["base_solicitation_text", "amendment_or_qa_text"]
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
  analyze_rfp_amendment_diff: { method: "POST", path: "/v1/analyze/amendment-diff" }
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
            version: "1.0.0"
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

