# DoD CDRL (DD Form 1423) & Data Item Description (DID) Schedule Extractor API

Extracts all Contract Data Requirements List (CDRL / DD Form 1423) items from DoD RFPs, maps Data Item Descriptions (DIDs), Block 4 authority, submission frequencies, inspection/acceptance codes, and builds a WBS Data Delivery Calendar.

## Key Capabilities
- **Endpoint**: `POST /v1/generate/cdrls-did-data-deliverables`
- **RapidAPI Host**: `dod-cdrl-dd-form-1423-did-schedule-tracker-api.p.rapidapi.com`
- **Governing Citations**: DFARS Subpart 227.71, DoD 5010.12-M (Procedures for the Acquisition and Management of Technical Data), & ASSIST DID Registry
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`generate_cdrls_did_data_deliverables`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
