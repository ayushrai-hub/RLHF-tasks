# Circuit Breaker Broker — API schemas

Deterministic microsecond clock (`now_us`); never use wall-clock time for resilience math. All numeric JSON fields are JSON numbers. Every HTTP 4xx under `/api` returns a non-empty JSON object.

---

## Milestone 1

### `GET /api/health`
`{"status": "ok"}`

### `GET /api/now`
`{"now_us": <int>}` — starts at 0.

### `POST /api/admin/advance`
Body: `{"micros": <non-negative integer>}`. Adds `micros` to `now_us`, returns new `now_us`. After advancing, apply the OPEN→HALF-OPEN auto-recovery rule from `POST /api/check` to every simple breaker. HTTP 400 on invalid body.

### `POST /api/breakers` (breaker registration)
Body: `id`, `policy: "simple"`, `failure_threshold` (positive integer), `recovery_timeout_us` (positive integer).

- `id`: 1–64 chars `[A-Za-z0-9_-]`
- `failure_threshold`, `recovery_timeout_us`: positive integers

HTTP 201 echoes `id`, `policy`, `failure_threshold`, `recovery_timeout_us`, `state` (= "CLOSED"), `failure_count` (= 0), `last_state_change_us` (= current `now_us`). Duplicate id → 409. Malformed → 400.

### `GET /api/breakers/{id}`
Returns breaker state. HTTP 404 if missing.

### `POST /api/breakers/report` (report result)
Body: `{"id": "...", "success": <boolean>}`.

- CLOSED state:
  - If `success` is false: increment `failure_count`. If `failure_count >= failure_threshold`, transition to "OPEN", update `last_state_change_us` = `now_us`.
  - If `success` is true: reset `failure_count` to 0.
- OPEN state:
  - Rejects reporting / checkups with HTTP 503 Service Unavailable: `{"error": "circuit open", "state": "OPEN", "retry_after_us": <int>}` where `retry_after_us` is `(last_state_change_us + recovery_timeout_us) - now_us`.
- HALF-OPEN state:
  - If `success` is true: transition to "CLOSED", reset `failure_count` to 0, update `last_state_change_us` = `now_us`.
  - If `success` is false: transition to "OPEN", update `last_state_change_us` = `now_us`.

### `POST /api/check` (query route check)
Body: `{"breaker_id": "..."}`.

Before evaluating allowance, if the breaker is OPEN and `now_us - last_state_change_us >= recovery_timeout_us`, transition it to HALF-OPEN and set `last_state_change_us = now_us`. The same auto-recovery rule runs in `POST /api/admin/advance` after advancing the clock.

- Returns HTTP 200:
  - CLOSED or HALF-OPEN: `{"allowed": true, "state": "..."}`.
  - OPEN: `{"allowed": false, "state": "OPEN", "retry_after_us": <int>}` where `retry_after_us` is `(last_state_change_us + recovery_timeout_us) - now_us`.

### `GET /`
HTML5 dashboard: title mentions circuit breaker broker; canvas ids `closedChart`, `openChart`, `breakersChart`.

---

## Milestone 2

### `POST /api/breakers` (sliding window)
Body: `id`, `policy: "sliding"`, `failure_threshold`, `window_us`. Reject requests that include `recovery_timeout_us`.
- Transitions to OPEN if there are >= `failure_threshold` failures recorded in the sliding window `[now_us - window_us, now_us]`.
- HTTP 201 echoes `id`, `policy`, `failure_threshold`, `window_us`, `recovery_timeout_us` (JSON `null` — present but not applicable to sliding breakers), `state` (= `"CLOSED"`), `failure_count` (= 0), `last_state_change_us` (= current `now_us`). `GET /api/breakers/{id}` uses the same shape.
- Auto-recovery: for sliding breakers, treat `window_us` as the recovery interval. In `/api/check` and `/api/admin/advance`, if OPEN and `now_us - last_state_change_us >= window_us`, transition to HALF-OPEN and set `last_state_change_us = now_us`.

### Composite Breaker Fallback
- `POST /api/check` accepts `breaker_ids` (1–8 list of distinct IDs). All-or-nothing check.
- Returns HTTP 200:
  - If all allowed: `{"allowed": true, "state_map": {id: state}}`.
  - If any OPEN: `{"allowed": false, "denied_by": <first open breaker id>, "retry_after_us": <max retry_after_us or null>}`.

### Audit row (appended on every check attempt)
Fields: `id` (integer starting at 1), `now_us`, `breaker_ids` (array), `allowed` (boolean), `denied_by` (string or null).

### `GET /api/audit`
`{"audit": [...], "count": <len>}` where `count == len(audit)`.
Query params: `limit` (default 100, max 1000), `breaker_id` (matches if present in `breaker_ids`), `since_id`.
FIFO storage cap: 1000 rows; evict oldest on overflow.

### `GET /`
Includes `<script src="...">` whose URL contains `chart.js`.

---

## Milestone 3

### Persistence
Atomic write to `/app/state/state.json` via temp file in `/app/state/` then rename. Top-level keys per `/app/spec/state_snapshot.schema.json` only. Rewrite on every mutation.

### `GET /api/state/integrity`
`state_file_exists`, `sha256` (64 lowercase hex of canonical JSON), `snapshot` with counts `breakers`, `audit`, `alerts`, `audit_id_counter`, `alert_id_counter`, `now_us`.

### `POST /api/admin/reload-state`
HTTP 200: `reloaded: true`, `integrity` object. Missing/malformed file → empty in-memory state.

### Auto-recovery transitions
Documented above for Milestone 1 (`recovery_timeout_us`) and Milestone 2 sliding breakers (`window_us`). Apply in both `/api/admin/advance` and `/api/check` handlers.

### `GET /api/alerts/thresholds`
JSON map keyed by `breaker_id`. Each value: `max_denial_count` (positive integer), `window_us` (positive integer).

### `POST /api/alerts/thresholds`
Body: `breaker_id`, `max_denial_count` (positive integer or `null` to clear), `window_us` (positive int). HTTP 404 unknown breaker. HTTP 400 on invalid body. HTTP 200 echoes the stored threshold: `breaker_id`, `max_denial_count` (number or JSON `null` when cleared), `window_us`.

### Alert record

| Field | Type |
|-------|------|
| `id` | positive integer |
| `now_us` | non-negative integer |
| `breaker_id` | string |
| `denial_count` | positive integer |
| `threshold` | positive integer |
| `severity` | `"low"`, `"medium"`, `"high"`, or `"critical"` |

### Alert firing
After each check attempt: if the breaker has a threshold and >=30 audit rows with `now_us` in `[broker_now - window_us, broker_now]`, count `allowed: false` events (denials) in the window. Fire if count is strictly greater than `max_denial_count`. Cooldown: 60_000_000 µs.
Severity from margin `(denial_count - threshold) / max(threshold, 1e-9)`: low if margin `< 0.25`, medium if `< 0.50`, high if `< 1.0`, else critical.

### `GET /api/alerts`
`{"alerts": [...], "count": N}` where `count == len(alerts)`. Filter, sort ascending, return last `limit` rows.

### `POST /api/alerts/clear`
HTTP 200: `{"cleared": true}`. Resets alerts and cooldown maps.
