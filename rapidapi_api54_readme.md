# FAR Part 49 Termination for Convenience (T4C / SF 1435–1438) Settlement Proposal Calculator API

Computes recoverable sunk costs, subcontractor termination claims, settlement expenses, and profit on work performed under FAR Part 49 and FAR 52.249-2, generating an Inventory Basis (SF 1435) or Total Cost Basis (SF 1436) T4C Settlement Proposal.

## Key Capabilities
- **Endpoint**: `POST /v1/generate/termination-for-convenience-settlement`
- **RapidAPI Host**: `far-part-49-t4c-sf-1435-1438-settlement-calculator-api.p.rapidapi.com`
- **Governing Citations**: FAR Part 49, FAR 52.249-2 (Termination for Convenience of the Government), FAR 31.205-42 (Termination Costs), & Standard Forms 1435 / 1436 / 1437 / 1438 / 1428
- **Architecture**: 100% Stateless, Zero Payload Retention, Strict Pydantic V2 JSON Schema Enforcement
- **MCP Support**: Included in `@signaltender/mcp-server` and remote Streamable-HTTP `/mcp` (`generate_termination_for_convenience_settlement`)

## Pricing Tiers
- **BASIC ($0/mo)**: 10 requests/month included (Free developer sandbox)
- **PRO ($49/mo)**: 200 requests/month included
- **ULTRA ($149/mo - Recommended)**: 1,000 requests/month included
- **MEGA ($399/mo)**: 4,000 requests/month included

## Documentation & Live Playground
Explore the full SignalTender GovCon AI Suite and interactive playground at [https://signaltender.net/apis.html](https://signaltender.net/apis.html).
