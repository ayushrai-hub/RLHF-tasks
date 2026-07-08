The calendar HTTP service is pre-built and running at http://127.0.0.1:8080. It stores time-bounded events in an augmented-interval binary search tree backed by SQLite.

Implement the twenty-two analytics procedures in /app/src/analytics.tcl. Twenty-one of those procedures back HTTP analytics endpoints. The remaining one, read_events_se, is an internal helper only and has no endpoint; it returns all stored events as id start_ms end_ms triples used by the other procedures.

All algorithm definitions, formula specifications, endpoint schemas, error conditions, sort orders, tie-breaking rules, and procedure signatures are in /app/SPEC.md sections 8 through 29. Read every section carefully before implementing.

After modifying source files, run /app/scripts/start_service.sh to restart the service.
