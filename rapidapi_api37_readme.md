# Service Contract Act (SCA / FAR 52.222-41) & Davis-Bacon Wage Determination Mapper API

Maps RFP Labor Categories (LCATs) and places of performance to U.S. Department of Labor (DOL) McNamara-O'Hara Service Contract Act (SCA / FAR 52.222-41) Directory of Occupations codes and Davis-Bacon Act (DBA) wage determinations, auditing base hourly wage floors, Health & Welfare (H&W) fringe rates (Standard vs. EO 13706 Paid Sick Leave), FLSA exempt vs. non-exempt classifications, SF-1444 conformance requests, and FAR 52.222-43 Option-Year Price Adjustment tables.

## Key Capabilities
- **Endpoint**: `POST /v1/audit/service-contract-act-wage`
- **RapidAPI Host**: `govcon-sca-far-52-222-41-wage-determination-mapper-api.p.rapidapi.com`
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`audit_service_contract_act_wage`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
