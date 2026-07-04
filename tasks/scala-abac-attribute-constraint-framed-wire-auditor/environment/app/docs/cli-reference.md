# CLI reference

## abac-ingest

```
/app/bin/abac-ingest --db /app/data/abac.db --batch /path/to/file.abwf
```

Parses ABWF, verifies CRC, stores events, replays policy state.

## abac-export

```
/app/bin/abac-export --db /app/data/abac.db --tenant TEN --out /app/output/abac-constraint-audit.json
```

Writes audit JSON per `audit-report-schema.md`.

## abac-serve

```
/app/bin/abac-serve --db /app/data/abac.db --listen 127.0.0.1:8091
```

Optional environment fallbacks when flags are omitted: `ABAC_DB` (default `/app/data/abac.db`), `ABAC_LISTEN` (default `127.0.0.1:8091`).

Serves `GET /health` and `POST /v1/tenants/{tenantId}/probe` per `http-api.md`.
