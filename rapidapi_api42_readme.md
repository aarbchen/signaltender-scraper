# FAR 6.302 / FAR 8.405-6 Sole-Source Justification & Approval (J&A / LSJ) Drafter API

Drafts a complete 12-Part FAR 6.303-2 Justification & Approval (J&A), FAR 8.405-6 Limited Sources Justification (LSJ), or FAR 16.505(b)(2) Fair Opportunity Exception package for Contracting Officers.

## Key Capabilities
- **Endpoint**: `POST /v1/generate/justification-ja-sole-source`
- **RapidAPI Host**: `far-6-302-8-405-6-sole-source-j-and-a-lsj-drafter-api.p.rapidapi.com`
- **Governing Citations**: FAR 6.302-1 (10 U.S.C. § 3204(a)(1) / 41 U.S.C. § 3304(a)(1)), FAR 6.303-2 (12 Mandatory Content Elements), & FAR 8.405-6 / 16.505(b)(2)
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`generate_justification_ja_sole_source`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
