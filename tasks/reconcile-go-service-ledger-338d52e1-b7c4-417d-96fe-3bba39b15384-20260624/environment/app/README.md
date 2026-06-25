# Service Ledger

Service Ledger is a small Go command line tool and HTTP API for reconciling operational events into service-level metric reports. Configuration files define canonical service names, aliases, tiers, weights, and retention windows. Event streams are newline-delimited JSON records from several telemetry sources.

The application code is under `/app`. The main entry point is `/app/cmd/ledger`.
