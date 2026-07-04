# Consensus Recovery Contract

## Required tokens (read first)

CLI: `node /app/consensus_lab/cli.js --bundle <bundle-dir> --output <output-dir>`. Repairs belong in `/app/raft_mesh/`.

| Field | Exact values for the default partition bundle |
|-------|---------------------------------------------|
| `classification` | `raft_split_brain` |
| `root_cause` | `raft_split_brain` (must equal `classification`, not a sentence) |
| `primary_node` | `n1` |
| `rejected_causes` | include misleading `election_timeout_spike` and `snapshot_lag_display_bug` when applicable |
| `command_trace.json` top-level shape | `{"schema_version": 4, "commands": [...]}` — never a bare JSON array |
| `term_timeline.csv` header | `phase,node_id,term,start_tick,end_tick,role,votes_received` |

**Duplicate WAL lines:** conflicting `(index, term)` pairs with different canonical payloads reject as `duplicate_entry`. Identical duplicates (same index, term, and canonical payload) are silently dropped; `parse_summary.accepted_commands` counts unique accepted entries and `parse_summary.duplicate_commands` counts skipped identical duplicates.

**Invalid command keys:** empty, missing, or regex-failing `command.key` values reject as `node_id_invalid` (not `bad_encoding`), including when the key field is empty while a conflicting duplicate is also present.

Rejected bundles exit non-zero, write only `consensus_report.json`, and must not create `term_timeline.csv`, `command_trace.json`, `safety_certificate.json`, or `wal_digest.txt`.

## Bundle layout

The replay bundle is rooted at `/app/scenarios/partition` and includes `cluster.json`, `wal_entries.jsonl`, `wal_frames.bin`, `rpc_trace.jsonl`, `partition_events.jsonl`, `election_timeouts.json`, `snapshots.csv`, `forensics_notes.txt`, and `env.d/*.env`.

## WAL command encoding

WAL lines are JSON objects. Some lines may be wrapped as `base64+json`, `base64+gzip+json`, or `base64+brotli+json`; the decoded payload is the same command object. UTF-8 BOM on the first line is stripped.

Each accepted command has fields `index` (positive integer), `term` (positive integer), `tick` (non-negative integer), `node_id`, and `command` with `op` (`set` or `del`), `key`, and optional `value`. Keys normalize with NFKC, invisible characters removed, trimmed, and must match `^[a-zA-Z0-9_.-]{1,64}$`; empty or invalid keys reject as `node_id_invalid`. Node IDs use the same normalization and must match `^[a-z0-9-]{1,32}$` after lowercasing. Duplicate `(index, term)` pairs with conflicting canonical payloads reject as `duplicate_entry`; identical duplicates are skipped and counted in `parse_summary.duplicate_commands`. Gaps in index sequence within the same term reject as `log_index_gap`. Terms above `2147483647` reject as `term_overflow`.

## Binary WAL frames

`wal_frames.bin` uses big-endian 32-bit length prefixes followed by UTF-8 JSON payloads mirroring accepted WAL command objects. Frame `tick` values stay in file order; out-of-order ticks reject as `wal_order_violation`. Oversized frames reject as `wal_frame_oversize`.

## RPC trace

Each RPC line is JSON with `tick`, `type` (`RequestVote` or `AppendEntries`), `from`, `to`, `term`, `last_log_index`, `last_log_term`, and optional `granted` or `success`. RPC terms must be non-decreasing in file order for the same `(from, to)` pair; violations reject as `rpc_order_violation`. RPC terms below the correlated WAL term at the same tick reject as `rpc_term_stale`.

## Cluster and snapshots

`cluster.json` declares `nodes` (array), `quorum_size`, and `election_timeout_ms`. Node IDs canonicalize like WAL entries. Homoglyph collisions across declared nodes reject as `cluster_homoglyph`. `quorum_size` must be at least `(floor(n/2)+1)` and at most `n`; otherwise `config_quorum_invalid`.

`snapshots.csv` columns: `node_id,last_included_index,last_included_term,checksum`. Colliding `(node_id, last_included_index)` with different terms reject as `snapshot_conflict`.

## Partition timeline

Partition events have `tick`, `kind` (`partition` or `heal`), and for `partition` also `isolated` (array of node ids) and `majority` (array). Overlapping partition windows that isolate the same node twice without an intervening heal reject as `partition_overlap`. Canonical node lists sort lexicographically after normalization.

## Env merge

Env fragments under `env.d/` merge in lexical filename order. Homoglyph key conflicts reject as `env_conflict`. Production bundles require `RAFT_ENV=production`.

## Rejection priority (lowest number wins)

`node_id_invalid`, `term_overflow`, `log_index_gap`, `duplicate_entry`, `rpc_term_stale`, `rpc_order_violation`, `wal_frame_oversize`, `wal_order_violation`, `snapshot_conflict`, `cluster_homoglyph`, `partition_overlap`, `config_quorum_invalid`, `commit_regression`, `env_conflict`, `bad_binary_frame`, `bundle_incomplete`, `env_not_production`, `bad_encoding`, `clock_regression`, `no_valid_commands`.

Rejected runs write only `consensus_report.json` with `status=rejected` and `error.code` set to the winning code. Exit code is non-zero.

## Virtual remediation simulation

The engine replays each accepted bundle twice: `before` (broken mesh) and `after` (repaired mesh). Commands traverse leader election → log append → quorum commit → client apply stages.

Broken mesh defects (all must be remediated in `after`):

1. RequestVote grants votes without comparing candidate `last_log_index` / `last_log_term` to the voter log tail.
2. Leaders advance `commit_index` on entries from prior terms without the current-term safety check.
3. Quorum vote counting includes grants recorded under stale terms during partition heal.
4. Partition overlap detection ignores duplicate isolation of the same node across windows.
5. WAL binary frames are parsed with the wrong byte order, silently dropping trailing entries.

## Accepted outputs (schema version 4)

`consensus_report.json` contains `status`, `incident_id`, `linearizability_digest`, `classification`, `root_cause`, `primary_node`, `secondary_symptoms`, `rejected_causes`, `repair_plan`, `before`, `after`, and `parse_summary`. Use the exact keys `before` and `after`. `root_cause` must equal the classification token (`raft_split_brain` for the default bundle). Before/after metric objects include `leaders_observed`, `split_brain_detected`, `commands_committed`, `commands_lost`, `election_rounds`, `commit_index_max`, and `linearizable_keys`.

For accepted command streams, `after.commands_committed` must come from replayed unique commands, not from a constant. The default partition bundle commits at least 4 commands after remediation; valid 256-command pressure streams commit more than 200; valid 4000-command stress streams commit more than 3000.

`command_trace.json` is a schema version 4 object with a `commands` array (not a bare list). Entries are sorted by `key` and contain `key`, `index`, `term`, `value`, and `stages` (sorted stage names that succeeded in `after` replay, for example `append`, `apply`, `election`, `quorum`).

`term_timeline.csv` columns: `phase,node_id,term,start_tick,end_tick,role,votes_received`.

`safety_certificate.json` includes `schema_version`, `split_brain_detected`, `commit_index_aligned`, `linearizability_digest`, `simulation_seed`, and `invariants` (array of `{name, passed}`).

`wal_digest.txt` is sorted `key=value` lines including `cluster_policy_changed=false`.

Classification for the default partition bundle must be `raft_split_brain` with `primary_node=n1`. Misleading election-timeout spikes and snapshot lag notes belong in `rejected_causes`, not `root_cause`.
