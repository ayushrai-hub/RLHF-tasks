Bundle contract
===============

Driver workflow
---------------
See `/app/environment/docs/build_hints.txt` for service start, bundle install, and driver invocation. Verifier tests read the SQLite bundle store via Python's stdlib `sqlite3` module.

API root
--------
The JSON service listens at `http://127.0.0.1:9292`.

Scenario table
--------------
`/app/environment/corpus/m9_table.toml` uses `[[profiles]]` blocks. Each block sets profile `id`, window instants `since` and `until`, optional `prio` band filter, and `retry` flag. Profile ids are listed in `/app/environment/docs/m9_ids.txt`. The coherent profile window (`s01`) spans the full seeded day and includes 20 distinct entries; paginated harvests must retrieve every batch until that full set is materialized.

Pagination channels
-------------------
The JSON index action returns a response header carrying the next batch token when more rows remain. Client code must advance using that header value on subsequent requests. The response body also carries a token field; those two channels are not always identical after a retry sequence. A body-token walk can return strictly fewer rows than a header-driven walk for the same window; the harvester must follow the header channel.

Window instants
---------------
The `since` field reports the inclusive start instant passed to the JSON index action. The `until` field reports the exclusive end instant: rows whose `recorded_at` equals `until` are excluded from the half-open window. Every row in a profile CSV must fall inside that profile's half-open window.

JSON index action
-----------------
Index route: /v1/k6/entries

Accepts `since`, `until`, optional `prio` band token, and `cursor` batch token. Each entry carries `rec_key`, `route_path`, `priority`, `recorded_at`, `lat_ms`, and `status_code` per `/app/environment/api/q9_host/db/schema.rb`. Priority band tokens map from numeric priority through `/app/environment/docs/k6_levels.txt`.

Bundle layout
-------------
For each profile id listed in `/app/environment/docs/m9_ids.txt`, the driver writes a per-profile `.csv` row file with no duplicate `rec_key` values within that file. The shared SQLite store lives at `/app/output/p7_bundle/bundle.db` with table `k6_facts`. Rollup output lives at `/app/output/p7_bundle/rollup.toml` with per-`route_tmpl` groups plus `bundle_digest`. Rows from a narrow-window profile must be a subset of the wider coherent-window population for the same keys. The union of `rec_key` values across all profile CSV files must equal the `k6_facts` key set.

Sink columns
------------
CSV and SQL rows expose `rec_key`, `route_tmpl`, `prio_band`, `rec_at`, `lat_ms`, and `stat_cd`. The `route_tmpl` field reports the collapsed route path derived from each entry's `route_path`. The `prio_band` field reports the band token mapped from entry priority. The `rec_at` field reports the entry instant in UTC for both sinks. The `lat_ms` field reports the same integer latency in both sinks for a given `rec_key`. Verifier SQL reads `SELECT rec_key, route_tmpl, prio_band, rec_at, lat_ms, stat_cd FROM k6_facts`.

Rollup
------
Route grouping and rollup reduction rules (`req_total`, `err_share`, `tail_p95_ms`, and `bundle_digest`) are defined in the module comment above `/app/environment/rb/p7_pull/lib/b3_stat.rb`. Rollup groups are reduced from the full shared store population after all profiles finish. The sum of every group's `req_total` must equal the row count in `k6_facts`. Within each `route_tmpl` group, `req_total` counts rows in that group, `err_share` is the fraction of rows where `stat_cd` is not 200 (including 404, 500, and 503), and `tail_p95_ms` is the 95th percentile of `lat_ms` in that group only. Cross-sink `rec_at` values must agree between CSV and SQL for the same `rec_key` and use UTC ISO8601 with a `Z` suffix. Floating-point comparisons on rollup `err_share` use a tolerance of `1e-6`.
