# p7 trace contract

Supplementary protocol notes for the replay lab. The authoritative behavioral contract
is in `/app/instruction.md`. This file names surfaces and vocabulary only.

## Row shape

Each `epochs` record carries scenario index, view (`screen`, `swap`, or `live`),
principal id, label, generation era tag, action_code, and block_rms.

## Body digest

The root `body_digest` field fingerprints the canonical serialized `epochs` array.
Repeat `p7_emit` after an unchanged replay must yield the same digest.

## Tolerance class T7

Narrow relative band applies on fresh reduction paths. Wide relative band applies on
cached-serve compares only after convergence policy marks the path converged.

## WAL append log

Runtime append log lives under `/app/runtime/wal.log`. Lines record sequence id,
opcode, scenario id, and a per-line checksum. Post-baseline scenarios must record
`bust_w3` immediately before each `screen_ok`. Sequence ids increase monotonically and
never reset at scenario boundaries.

## Checkpoint seal

Runtime seal file lives under `/app/runtime/checkpoint.seal`. Emit refuses seal drift,
invalid line checksums, or wrong append order. Recovery rebuilds the seal from the log.

## Cross-authority inspect

`p7_inspect` prints screen-side and swap-side generation counters for sampling.

## Recovery

`p7_recover` rebuilds the seal from the WAL and is idempotent on repeat.
