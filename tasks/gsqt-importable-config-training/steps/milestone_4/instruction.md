Add a scheduler recovery module that can migrate old in-memory query databases and explain why each query is or is not claimable.

Create `src.query_scheduling.recovery` with `ensure_recovery_schema(query_engine)` and `build_recovery_report(query_engine, now=None)`. Both functions must use only the provided SQLite connection. `now` defaults to `datetime(2026, 1, 1, 12, 0, 0)` when omitted.

`ensure_recovery_schema(...)` should be idempotent. It must preserve existing rows and add the modern recovery fields to `query_schedule` when they are missing: `payload_json TEXT DEFAULT '{}'`, `completed_at TEXT`, and `lease_version INTEGER DEFAULT 0`. It must also create `query_dependencies(query_id INTEGER NOT NULL, depends_on_id INTEGER NOT NULL, PRIMARY KEY(query_id, depends_on_id))` and keep the existing optional `query_lock_events` table usable. Do not assume a pristine schema; milestone 3's fake DBs and older DBs may already have some but not all fields.

`build_recovery_report(...)` should call `ensure_recovery_schema(...)` and return a JSON-serializable dictionary with `schema`, `ready_by_country`, `blocked_by_dependency`, `cycle_ids`, `paused_ids`, and `stale_lock_ids`.

Readiness rules are explicit:
- A row is in the scheduling window when `scheduled_execution_date` is between `now` and `now + 10 minutes`, after normalizing space-separated datetimes to `T`-separated ISO text.
- A row is unavailable when it has `deletion_date`, `completed_at`, a fresh lock, a paused payload, an unresolved dependency, or participates in a dependency cycle.
- A lock is stale when `locked_at` is older than 15 minutes after the same datetime normalization.
- A payload is paused only when valid JSON has `{"scheduler": {"paused": true}}` at that path; missing or invalid JSON should not crash the report and should not be treated as paused.
- A dependency is resolved only when the dependency row exists, is not deleted, and has `completed_at` set.

`ready_by_country` groups claimable query ids by country, sorted within each country by `priority DESC`, normalized `scheduled_execution_date ASC`, then `id ASC`. `blocked_by_dependency` maps query ids as strings to sorted unresolved dependency ids. `cycle_ids`, `paused_ids`, and `stale_lock_ids` are sorted integer lists. `schema` should report booleans for `payload_supported`, `completed_supported`, `lease_supported`, and `dependencies_supported`.
