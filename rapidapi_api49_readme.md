# SLED Cooperative Purchasing (NASPO ValuePoint, Sourcewell, OMNIA, TIPS & DIR) Piggyback Mapper API

Evaluates state and municipal IT procurements to identify eligible NASPO ValuePoint, Sourcewell, OMNIA Partners, TIPS, TX DIR, and GSA Cooperative Purchasing (SIN 54151S/HACS) piggyback vehicles that bypass a 6-month competitive RFP.

## Key Capabilities
- **Endpoint**: `POST /v1/generate/state-local-cooperative-piggyback`
- **RapidAPI Host**: `sled-cooperative-purchasing-naspo-sourcewell-piggyback-api.p.rapidapi.com`
- **Governing Citations**: 40 U.S.C. § 502(c) (GSA Cooperative Purchasing for IT/Cyber SINs), ABA Model Procurement Code Article 10 (Intergovernmental Relations), & State Participating Addendum Statutes
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`generate_state_local_cooperative_piggyback`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
