# GovCon M&A Contract Novation (FAR 42.1204) & Change-of-Name Due Diligence Package API

Generates a complete FAR 42.1204 Three-Party Novation Agreement package for GovCon asset/stock acquisitions, auditing anti-assignment exceptions (41 U.S.C. 6305), SAM.gov UEI/CAGE transfer checklists, and SBA recertification triggers under 13 CFR 121.404(g).

## Key Capabilities
- **Endpoint**: `POST /v1/generate/novated-merger-change-of-name-far-42`
- **RapidAPI Host**: `far-42-1204-govcon-m-a-novation-agreement-package-api.p.rapidapi.com`
- **Governing Citations**: 41 U.S.C. § 6305 (Anti-Assignment Act), FAR Subpart 42.12 (FAR 42.1204 Novation & FAR 42.1205 Change-of-Name), & 13 CFR § 121.404(g)
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`generate_novated_merger_change_of_name_far_42`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
