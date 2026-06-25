Extend the broker with sliding-window failure tracking, composite route checks, and audit logging.

Sliding breakers use `policy: "sliding"` with `failure_threshold` and `window_us`; reject registration bodies that include `recovery_timeout_us`. Created and retrieved sliding breakers still expose `recovery_timeout_us` in JSON as explicit `null`. They reopen to HALF-OPEN after `window_us` elapses in OPEN state, using the same auto-recovery hooks as simple breakers use for `recovery_timeout_us`.

`POST /api/check` also accepts `breaker_ids` (1–8 distinct IDs) for all-or-nothing evaluation. Append an audit row on every check with autoincrement `id`, `now_us`, `breaker_ids`, `allowed`, and `denied_by`. Expose `GET /api/audit` with `limit`, `breaker_id`, and `since_id` filters over a FIFO cap of 1000 rows. The root dashboard must load Chart.js via a script tag whose URL contains `chart.js`. See `/app/spec/SPEC.md` for response schemas.
