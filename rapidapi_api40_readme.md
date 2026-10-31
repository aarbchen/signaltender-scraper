# ITAR (22 CFR 120–130), EAR & Technology Control Plan (TCP) Export Compliance API

Classifies defense/dual-use technical deliverables against USML Categories (ITAR) and CCL ECCNs (EAR), flags DFARS 252.225-7048 export obligations, and generates a facility Technology Control Plan (TCP).

## Key Capabilities
- **Endpoint**: `POST /v1/audit/itar-ear-export-control`
- **RapidAPI Host**: `itar-22-cfr-120-130-ear-tcp-export-compliance-api.p.rapidapi.com`
- **Governing Citations**: 22 CFR Parts 120–130 (ITAR USML Categories IV & XI), 15 CFR Parts 730–774 (EAR CCL), & DFARS 252.225-7048
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`audit_itar_ear_export_control`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
