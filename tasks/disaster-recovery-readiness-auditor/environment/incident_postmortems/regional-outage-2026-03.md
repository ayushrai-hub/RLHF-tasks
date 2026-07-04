# Regional outage postmortem — March 2026

Draft narrative: eu-west-1 promotion lagged because ledger consistency gate blocked identity promotion. Search rebuild never completed because order-api snapshot gate remained red.

- `FAILOVER_STEP 2026-03-18T09:00:00Z payments-ledger promote_secondary us-east-1 eu-west-1 12 incident_postmortems/regional-outage-2026-03.md`
- `FAILOVER_STEP 2026-03-18T09:15:00Z identity-core wait_for_dependency us-east-1 eu-west-1 15 incident_postmortems/regional-outage-2026-03.md`
- `FAILOVER_STEP 2026-03-18T09:45:00Z identity-core promote_secondary us-east-1 eu-west-1 18 incident_postmortems/regional-outage-2026-03.md`
- `FAILOVER_STEP 2026-03-18T10:00:00Z order-api promote_secondary us-east-1 eu-west-1 35 incident_postmortems/regional-outage-2026-03.md`
- `FAILOVER_STEP 2026-03-18T10:30:00Z search-index blocked order-api catalog_snapshot_gate incident_postmortems/regional-outage-2026-03.md`
- `FAILOVER_STEP 2026-03-18T11:00:00Z cache-cluster flush_and_rebuild us-east-1 eu-west-1 9 incident_postmortems/regional-outage-2026-03.md`
