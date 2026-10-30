# GSA FAS Sales Reporting Portal (SRP), TDR Line-Item & IFF CAV/IOA Audit Reconciler API

Audits commercial vs. GSA Schedule invoices to separate Open-Market vs. Schedule sales, calculate quarterly 0.75% IFF remittance, validate Transactional Data Reporting (TDR) 16-field data elements, and prepare for a GSA IOA Contractor Assistance Visit (CAV).

## Key Capabilities
- **Endpoint**: `POST /v1/generate/gsa-tdr-quarterly-sales-iff-reconciler`
- **RapidAPI Host**: `gsa-fas-srp-tdr-iff-cav-ioa-audit-reconciler-api.p.rapidapi.com`
- **Governing Citations**: GSAR 552.238-80 (Industrial Funding Fee and Sales Reporting — 0.75% IFF within 30 days of quarter close), GSAR 552.238-81 (TDR), & GSA IOA Contractor Assistance Visit (CAV) Guide
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`generate_gsa_tdr_quarterly_sales_iff_reconciler`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
