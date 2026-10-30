# GovCon Request for Equitable Adjustment (REA), Constructive Change & CDA Claim API

Analyzes post-award scope creep, government Furnished Equipment (GFE) delays, defective specifications, or stop-work orders under FAR 52.243-1/2/3/4, FAR 52.242-14/15/17, and the Contract Disputes Act (41 U.S.C. 7101-7109) to generate a legally structured Request for Equitable Adjustment (REA) with DCAA-auditable quantum cost tables, Eichleay unabsorbed home-office overhead analysis,FAR 31.205-33 billable preparation cost segregation, and SF-30 bilateral modification text.

## Key Capabilities
- **Endpoint**: `POST /v1/generate/rea-equitable-adjustment`
- **RapidAPI Host**: `govcon-rea-constructive-change-cda-claim-api.p.rapidapi.com`
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`generate_rea_equitable_adjustment`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
