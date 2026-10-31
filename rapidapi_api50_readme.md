# FAR Part 48 Value Engineering Change Proposal (VECP / FAR 52.248-1) & Shared-Savings Modeler API

Transforms cloud FinOps, AI automation, or architecture optimizations on an active contract into a formal FAR 52.248-1 Value Engineering Change Proposal (VECP), calculating Instant/Concurrent/Future acquisition savings and the contractor's 50%–75% shared-savings royalty.

## Key Capabilities
- **Endpoint**: `POST /v1/generate/value-engineering-vecp`
- **RapidAPI Host**: `far-part-48-vecp-far-52-248-1-shared-savings-modeler-api.p.rapidapi.com`
- **Governing Citations**: FAR Part 48 (Value Engineering) & FAR 52.248-1(c)–(i) (50%/50% to 75%/25% Voluntary VECP Incentive Sharing & 36–60 Month Future Acquisition Royalty)
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`generate_value_engineering_vecp`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
