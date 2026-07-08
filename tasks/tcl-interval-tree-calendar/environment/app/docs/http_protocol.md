# HTTP Protocol

All endpoints listen on port 8080 (configurable via `BIND_PORT`). Request and response bodies are JSON. The CGI script sets appropriate `Content-Type: application/json` headers.

## POST /events

Insert a new event into the interval tree.

**Request body:**
```json
{"name": "meeting", "start_ms": 1000, "end_ms": 2000, "metadata": {"room": "A"}}
```

**Response 201:**
```json
{"id": 1, "name": "meeting", "start_ms": 1000, "end_ms": 2000, "max_end_ms": 2000}
```

**Response 400:** missing or invalid fields.

## GET /stab?at=<ms>

Return all events where `start_ms <= at <= end_ms`.

**Response 200:**
```json
{"at": 1500, "events": [{"id": 1, "name": "meeting", "start_ms": 1000, "end_ms": 2000}]}
```

## GET /overlap?start=<ms>&end=<ms>

Return all events that overlap the interval `[start, end]` (inclusive). An event overlaps if `event.start_ms <= end AND event.end_ms >= start`.

**Response 200:**
```json
{"start": 1000, "end": 2000, "events": [{"id": 1, "name": "meeting", "start_ms": 1000, "end_ms": 2000}]}
```

## DELETE /events/:id

Remove an event from the tree and propagate `max_end_ms` up the ancestor path.

**Response 200:**
```json
{"id": 1, "deleted": true}
```

**Response 404:** event not found.

## GET /stats

Return aggregate statistics about the current tree state.

**Response 200:**
```json
{"total_events": 3, "tree_depth": 2, "overlapping_pairs": 1}
```

`overlapping_pairs` counts each pair (i, j) with i.id < j.id exactly once.

## GET /healthz

Health check endpoint. Always returns 200.

**Response 200:**
```json
{"status": "ok"}
```
