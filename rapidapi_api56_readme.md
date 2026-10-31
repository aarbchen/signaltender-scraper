# SSEB Source Selection Simulator & Shipley Pink/Red/Gold Team Proposal Scorer API

Simulates a Government Source Selection Evaluation Board (SSEB) under FAR 15.305, grading a draft proposal volume against RFP Section L/M into DoD Color/Adjectival Ratings (Blue/Outstanding to Red/Unacceptable) with exact Strengths, Weaknesses, Deficiencies, and page-level rewrites.

## Key Capabilities
- **Endpoint**: `POST /v1/generate/section-l-m-proposal-red-team-scorer`
- **RapidAPI Host**: `sseb-source-selection-simulator-shipley-proposal-scorer-api.p.rapidapi.com`
- **Governing Citations**: FAR 15.305 (Proposal Evaluation), DoD Source Selection Procedures (DFARS PGI 215.3 — Blue/Purple/Green/Yellow/Red Consensus Grading), & Shipley Color Team Standards
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`generate_section_l_m_proposal_red_team_scorer`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
