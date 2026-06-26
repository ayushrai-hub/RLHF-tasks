# Artifact shapes

Run pipeline via terraform apply under `/app/environment/infra` (or verifier harness).

Outputs under `/app/output/`:
- `lock_snapshot.json`: `{ "entry_id": str, "rows": [{"module_id", "repo_key", "version"}] }` — rows sorted by `(module_id, repo_key)`; `repo_key` is `<module_id>/<version>`
- `repo_table.bzl`: JSON `{ "rows": [{"module_id", "repo_key", "url"}] }` — rows sorted by `(module_id, repo_key)`
- `checksum_rows.json`: `{ "rows": [{"repo_key", "digest"}] }` — rows sorted by `repo_key`
- `module_lock.bzl`: `{ "entry_id", "lines": [str], "stub_rollup": str }` — one `lock(<repo_key>,<digest>)` line per resolved module sorted by `repo_key`; `stub_rollup` is lowercase hex SHA-256 over lines joined by `\n`

Sidecar URL: `http://127.0.0.1:8787/catalog`

Every apply must read the current root index, active root fixture, policy text, and sidecar catalog at runtime. A reused closure slot may preserve resolved module versions, but checksum rows, module-lock lines, link digests, and slot seals must still reflect the live catalog payload for the active apply.

Each `checksum_rows.json` digest must match `packages[<module_id>].checksum` from the sidecar for every resolved module.

Cross-artifact link digest: SHA-256 hex over UTF-8 JSON with `sort_keys=true` and compact separators `(',', ':')` for `{"lock": <lock rows>, "checksum": <checksum rows>}`.

Lock, repo, checksum, and module-lock lines for a run must expose the same `repo_key` set.

Runtime journal directory: `/app/environment/.runtime/journal/`

| File | Role |
|------|------|
| `closure.json` | Slot ledger: `{ "slots": { "<entry_id>": { "seed_digest", "nodes", "pins", "link_digest", "sealed_at_gen" } } }` |
| `epoch.json` | Per-entry apply counters incremented each successful run |
| `replay_gen.json` | Monotonic `{ "gen": int }` incremented on every successful apply regardless of entry |
| `replay_tail.json` | Last sealed apply snapshot: `{ "entry_id", "seed_digest", "link_digest", "gen" }` |
| `replay_chain.jsonl` | One JSON object per line `{ "entry_id", "gen", "link_digest", "chain_prefix" }` forming a prefix-linked apply witness |

Each slot's `seed_digest` must match the active root fixture fingerprint for that entry. The fingerprint is the comma-separated sorted seed module ids from the active root fixture, a pipe character, then the fixture `storage_class` (for example a dual-seed standard entry uses `mod_core,mod_graph|standard`).

Hydration must treat a foreign tail, stale seed digest, tail/slot link digest mismatch, tail `gen` disagreeing with `replay_gen.json`, a replay-chain head disagreeing with the active entry and generation, or broken prefix linkage as a cache miss. During normal rotation the replay-chain witness grows by prefix-linked appends. When prefix linkage fails validation, discard the broken witness entirely and emit a fresh single-line witness whose sole record carries prefix `genesis` before recording the new apply; do not retain prior lines or append onto a broken chain.

Version pins and host-alias rules come from `/app/environment/docs/vol_h/` amendments.

Tampered files under `/app/output/` are replaced on the next apply for the same entry.
