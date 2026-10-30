# GovCon Earned Value Management System (EVMS / EIA-748) & IPMDR Variance Narrative API

Ingests Work Breakdown Structure (WBS) Control Account cost and schedule metrics (BCWS, BCWP, ACWP, BAC) to compute Earned Value Management (EVMS) indices (CV, SV, CPI, SPI, TCPI, IEAC, VAC) and draft audit-ready Format 5 Integrated Program Management Data and Analysis Report (IPMDR / CDRL DID DI-MGMT-81861C) Variance Analysis Narratives with Root Cause, Program Impact, Corrective Action Plans (CAP), and EIA-748 32-Guideline DCMA surveillance checks under FAR 52.234-4 and DFARS 252.234-7002.

## Key Capabilities
- **Endpoint**: `POST /v1/generate/evms-ipmdr-variance-analysis`
- **RapidAPI Host**: `govcon-evms-ansi-748-ipmdr-variance-narrative-api.p.rapidapi.com`
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`generate_evms_ipmdr_variance_analysis`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
