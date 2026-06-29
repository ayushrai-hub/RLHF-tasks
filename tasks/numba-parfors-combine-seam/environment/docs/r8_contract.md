# m6 trace contract

## Output path

`/app/output/r8_trace.json`

## Row shape

Each record in `epochs` carries `scenario` (int), `view` (`shard`, `catalog`, or `live`), `principal` (string), `label` (string), `generation` (int), `action_code` (int), and `block_rms` (number). A scenario may emit multiple rows per view when reload outcomes, catalog skew, or readopt rows are recorded alongside the primary active slot.

Root field `body_digest` is a lowercase hexadecimal SHA-256 digest of the canonical JSON encoding of the `epochs` array.

## Snapshot trees

Case trees under `/app/cases/seq` use active-slot lines with principal, label, gen, and optional action fields. Shipped profile labels include ROOT, HAT_A, and REVOKED. Each replay write phase bumps every active-slot gen before verify. Emitted shard-view active-slot generation matches the shipped shard snapshot active-slot gen plus that write bump.

Scenarios s0 through s4 ship under `/app/cases/seq/s0` through `/app/cases/seq/s4`.

## body_digest

Sort `epochs` lexicographically by scenario, view, principal, label, and generation. Serialize the sorted array as compact JSON with sorted object keys and no whitespace. The fingerprint is SHA-256 hex of the UTF-8 encoding of that payload.

## R8 tolerance class

Integral block comparisons use class R8. Fresh reduction paths (shard view and converged catalog compares) use the narrow band: `block_rms = generation * 1e-4 + action_code * 1e-5`. Cached-serve compares after convergence may use a wide band only when the runtime explicitly selects cached tolerance routing; otherwise catalog-view `block_rms` must stay in the narrow band.

## WAL CRC32 line format

Each append-log line is a JSON record, a tab character, then a decimal CRC32. CRC payload uses colon-separated scenario, phase, feed_gen, live_gen, and seq fields. At sync time, feed_gen means the shard generation counter and live_gen means the runtime generation counter. CRC uses the same polynomial as Python zlib.crc32 on UTF-8 payload.

## Phase order

Scenario zero accepts any phase order. Scenario one and later must record bust before success in the append log.

## Checkpoint tail

After a full replay through scenario four, checkpoint wal_seq must match the seq field of the final append-log record. Checkpoint order_seal and lineage_seal must agree with harness recomputation from the intact append log.

## Sync-phase WAL capture

For scenario s1, the final append-log record for that scenario uses phase sync and records aligned feed_gen and live_gen after runtime alignment.

For every scenario replay, the last append-log record for that scenario uses phase sync.

## Epoch cache persistence

epoch_N.json row caches retain every emitted row for the scenario, including live-view rows with non-zero action_code.

## Runtime sync

During sync for scenarios s1 through s4, runtime active-slot generation aligns to shard active-slot generation when they differ after the write phase.

## WAL sequence discipline

Each append assigns a strictly increasing seq across the full chain with no duplicates or regressions. A full replay of scenarios s0 through s4 appends at least twenty-five CRC-valid records.

## Checkpoint seal

checkpoint.json stores last_scenario, wal_seq, order_seal, lineage_seal, and valid. Stored order_seal and lineage_seal must agree with recomputation from the intact append log using the same rules implemented by the replay tools. Emit and recovery reject drift on either seal.

## Order seal bust mixing

When a scenario records phase `bust` immediately followed by phase `success`, order_seal recomputation uses a distinct bust-completion mix term rather than the standard success-path mix. Other success and bust phases use their own mix paths implemented in replay tooling. Emit and recovery reject checkpoint order_seal drift from append-log recomputation.

## Lineage seal

Recompute lineage_seal from sync-phase append-log records per scenario, sorted by scenario id, using the mixing rules implemented in the replay tools and documented in driver notes.

## Cross-view policy

For scenario one and later, shard-view and live-view active-slot generations for the same principal must match in emitted rows unless deny scenario explicitly marks action_code 9. Runtime binding during sync copies shard active-slot generation into the runtime active slot when epoch binding is live.

When live label generation exceeds catalog-view generation for scenario one and later, catalog view must include at least one row with non-zero action_code documenting the mismatch.

Scenario zero rows must preserve baseline generations from shipped case trees for all three views across later scenarios in the same chain.

## Scenario s1 skew

Mid-run shard/live generation skew reconciles during replay. Scenario s1 emits at least two live-view rows when worker-tranche skew is recorded; the secondary row uses action_code 5. On a corrected chain, action_code 7 on s1 live rows is false.

## Reload outcome rows

Scenario s2 emits at least two live-view rows when reload attempts run; one primary active-slot row plus at least one row documenting reload outcomes with non-zero action_code.

Scenario s3 emits at least two live-view rows on the deny path; one primary active-slot row plus at least one row documenting runtime deny outcomes with action_code 9. On a reconciled deny replay through scenario three, the final sync-phase append record for that scenario records live_gen two steps above feed_gen after write-phase live generation bumps on the deny tranche.

Scenario s4 emits at least two live-view rows documenting readopt after deny when the include digest matches an earlier scenario but the include epoch advances; readopt success uses action_code 6.

## Encode-store lineage

When an include digest reappears after a deny scenario with a higher epoch, encode-store fragment lineage reflects the new epoch rather than resurrecting stale fragment counters from the prior digest match.

## Idempotency

Repeated r8_run for the same scenario on unchanged replay roots produces identical sorted row content in epoch_N.json and valid WAL CRC lines for every appended record.

Consecutive r8_recover invocations on unchanged WAL state produce identical checkpoint.json and do not change the emitted body_digest when followed by r8_emit without further replay.

Two consecutive r8_emit runs on unchanged replay state produce identical body_digest.

## Metrics

last_metrics.json reports store_hits, cap_attempts, and crl_epoch. After a full s0 through s4 chain, crl_epoch reflects the include epoch from scenario s4 fixtures.

## Emit gate

r8_emit refuses when checkpoint order_seal or lineage_seal disagrees with append-log recomputation, when phase order is invalid for scenario at least one, when any physical append-log line CRC is invalid (including lines skipped by chain readers), or when checkpoint seal disagreement is detected even if valid was forced true out of band. The emit gate consults raw append-log integrity, not only the filtered chain returned by readers.
