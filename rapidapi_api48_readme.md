# Controlled Unclassified Information (CUI / 32 CFR 2002 & DoDI 5200.48) Handling Plan API

Analyzes deliverables against the NARA CUI Registry, 32 CFR Part 2002, and DoDI 5200.48 to generate exact CUI banner/portion markings, DoD Distribution Statements (A–F), and a CUI Sanitization & Spill Response SOP.

## Key Capabilities
- **Endpoint**: `POST /v1/generate/cui-marking-distribution-plan`
- **RapidAPI Host**: `dod-32-cfr-2002-dodi-5200-48-cui-marking-plan-api.p.rapidapi.com`
- **Governing Citations**: 32 CFR Part 2002 (NARA CUI Program), DoDI 5200.48 (Controlled Unclassified Information), DoDI 5230.24 (Distribution Statements), & NIST SP 800-88 Rev. 1
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`generate_cui_marking_distribution_plan`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
