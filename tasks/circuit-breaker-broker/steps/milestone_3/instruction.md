Finish the broker with durable state, integrity checks, and denial alerting.

Persist the full in-memory snapshot to `/app/state/state.json` on every mutation using a temp file in `/app/state/` followed by rename; the shape must match `/app/spec/state_snapshot.schema.json`. Add `GET /api/state/integrity` (SHA-256 of canonical JSON plus counts) and `POST /api/admin/reload-state` (empty in-memory state when the file is missing or malformed).

Threshold registration via `POST /api/alerts/thresholds` takes `breaker_id`, `max_denial_count`, and `window_us`; HTTP 200 must echo those fields back (use JSON `null` for `max_denial_count` when clearing). After each check, count denials for that breaker in `[now_us - window_us, now_us]`; fire an alert when denials strictly exceed the threshold and at least 30 audit rows fall in the window, respecting a 60_000_000 µs cooldown. Expose `GET /api/alerts` and `POST /api/alerts/clear`. Details are in `/app/spec/SPEC.md`.
