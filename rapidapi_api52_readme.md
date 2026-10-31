# DoD FedRAMP Moderate Equivalency (2024 DoD CIO Memo) & 3PAO Body of Evidence Auditor API

Audits cloud service offerings against the DoD CIO FedRAMP Moderate Equivalency Memorandum (100% 3PAO assessment, zero unmitigated high/moderate POA&Ms, KSIs) and generates a complete Cloud Equivalency Body of Evidence (BoE) checklist.

## Key Capabilities
- **Endpoint**: `POST /v1/generate/fedramp-equivalency-body-of-evidence`
- **RapidAPI Host**: `dod-fedramp-moderate-equivalency-3pao-boe-auditor-api.p.rapidapi.com`
- **Governing Citations**: DoD CIO Memorandum 'Federal Risk and Authorization Management Program Moderate Equivalency for Cloud Service Provider's Cloud Service Offerings' (Jan 2, 2024) & DFARS 252.204-7012(b)(2)(ii)(D)
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`generate_fedramp_equivalency_body_of_evidence`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
