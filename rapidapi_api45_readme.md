# GWAC / IDIQ Task Order Fair Opportunity (FAR 16.505) & Pool Selection Optimizer API

Matches task order TORFPs across OASIS+, GSA Polaris, 8(a) STARS III, VETS 2, NASA SEWP, and NITAAC CIO-SP3/4 against vendor contract pools, scoring self-scoring scorecard matrices and drafting rapid 5-day TORFP responses.

## Key Capabilities
- **Endpoint**: `POST /v1/generate/gwac-task-order-fair-opportunity`
- **RapidAPI Host**: `far-16-505-oasis-polaris-sewp-task-order-shaper-api.p.rapidapi.com`
- **Governing Citations**: FAR 16.505(b)(1) (Fair Opportunity), FAR 16.505(a)(10) ($10M Civilian / $25M DoD Task Order Protest Jurisdictional Cap), & GSAR 552.216-74
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`generate_gwac_task_order_fair_opportunity`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
