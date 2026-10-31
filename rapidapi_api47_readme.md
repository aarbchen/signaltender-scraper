# DoD OCONUS / INDOPACOM Deployment, SOFA, Defense Base Act (DBA) & SPOT Compliance API

Evaluates Pacific/OCONUS defense IT solicitations for Status of Forces Agreement (SOFA) TESA/TDY accreditation, FAR 52.228-3 Defense Base Act (DBA) insurance wraps, DFARS 252.225-7040 SPOT synchronization, and COLA/Post Allowance rate structures.

## Key Capabilities
- **Endpoint**: `POST /v1/generate/oconus-sofa-defense-logistics`
- **RapidAPI Host**: `dod-oconus-indopacom-sofa-defense-base-act-spot-api.p.rapidapi.com`
- **Governing Citations**: FAR 52.228-3 (42 U.S.C. §§ 1651–1654 Defense Base Act), DFARS 252.225-7040 / 252.225-7995 (SPOT LOA), & DSSR Chapters 130/220/650
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`generate_oconus_sofa_defense_logistics`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
