# HTTP API (`abac-serve`)

## GET /health

Returns `{"status":"ok"}` with HTTP 200.

## POST /v1/tenants/{tenantId}/probe

JSON body may include `policy_id` and attribute key/value pairs.

Effective probe decision uses **persisted attribute snapshots** from SQLite for the tenant and policy merged with request attributes (request overrides snapshot keys). Required attributes from profile must be satisfied (fail-closed) before returning permit.
