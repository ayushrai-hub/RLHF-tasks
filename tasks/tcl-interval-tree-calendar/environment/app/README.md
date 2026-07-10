# Interval Tree Calendar Service

A Tcl 8.6 HTTP service that indexes time-bounded calendar events in an augmented interval tree (BST keyed by `start_ms`, with `max_end_ms` augmentation) persisted to SQLite. Served via busybox httpd CGI.

## Quick Start

```bash
bash /app/scripts/start_service.sh
curl http://127.0.0.1:8080/healthz
```

## Usage

```bash
# Add an event
curl -X POST http://127.0.0.1:8080/events \
  -H 'Content-Type: application/json' \
  -d '{"name":"standup","start_ms":1000,"end_ms":2000,"metadata":{}}'

# Stab query
curl http://127.0.0.1:8080/stab?at=1500

# Overlap query
curl 'http://127.0.0.1:8080/overlap?start=1000&end=2000'

# Stats
curl http://127.0.0.1:8080/stats

# Delete
curl -X DELETE http://127.0.0.1:8080/events/1
```

See `/app/SPEC.md` for full contract details and `/app/docs/` for architecture notes.
