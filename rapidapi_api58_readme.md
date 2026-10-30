# FAR Subpart 16.4 Award-Fee (CPAF) & Incentive-Fee (CPIF / FPIF) Evaluation Maximizer API

Models CPAF, CPIF, and FPIF share-ratio curves (overrun/underrun ceiling geometry under FAR 16.401) and transforms periodic performance metrics into an Award-Fee Evaluation Board (AFEB) self-assessment presentation to maximize unearned/rollover fee pools.

## Key Capabilities
- **Endpoint**: `POST /v1/generate/award-fee-plan-incentive-maximizer`
- **RapidAPI Host**: `far-16-401-cpaf-cpif-award-fee-board-presentation-api.p.rapidapi.com`
- **Governing Citations**: FAR Subpart 16.4 (Incentive Contracts), FAR 16.401(e)(3) Table 16-1 (Standard Award-Fee Adjectival Ratings), FAR 16.401(e)(4) (Rollover Prohibition), & DFARS 216.405-2
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`generate_award_fee_plan_incentive_maximizer`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
