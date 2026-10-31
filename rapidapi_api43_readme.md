# DFARS 252.204-7012 (72-Hour DIBNet) & CIRCIA Cyber Incident Reporting Package API

Evaluates CUI/CDI security incidents against DFARS 252.204-7012, CISA CIRCIA, and FedRAMP incident SLAs, generating a structured 72-hour DoD DIBNet ICF report, 90-day forensic media preservation checklist, and subcontractor flow-down notifications.

## Key Capabilities
- **Endpoint**: `POST /v1/audit/cyber-incident-dfars-7012`
- **RapidAPI Host**: `dfars-252-204-7012-72-hour-dibnet-circia-incident-api.p.rapidapi.com`
- **Governing Citations**: DFARS 252.204-7012(c)–(m) (72-Hour DoD DIBNet Reporting & 90-Day Image Preservation), CISA CIRCIA (6 U.S.C. § 681b), & NIST SP 800-61r2
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`audit_cyber_incident_dfars_7012`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
