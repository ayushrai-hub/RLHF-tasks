# Module scope

Behavior packages under `/app/src/main/scala/abac/`:

- **Wire parsing and CRC** — ABWF magic, frame decode, footer CRC scope
- **Ingest and replay** — transactional ingest, eval_seq ordering, policy state updates
- **Persistence** — SQLite batch and eval storage, tenant-scoped counters
- **Export** — audit JSON and audit_hash per schema
- **HTTP serve** — health and tenant probe endpoints

Internal coordination helpers live under the `abac.internal` package (attribute binding, policy combination, obligation tracking). Agents should treat that package as non-public API surface documented only through policy rules and HTTP contracts.
