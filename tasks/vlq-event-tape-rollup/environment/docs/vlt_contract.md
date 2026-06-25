# VLT rollup contract

## VLT1 bundle layout

Magic `VLT1`, little-endian `tape_id` (uint16), little-endian `event_count` (uint32).
Each event: unsigned VLQ `tag`, signed VLQ `delta` (zigzag), little-endian `payload_len` (uint16), then payload bytes.

## Signed VLQ

Decode unsigned zigzag word `u` as `(u >> 1) ^ -(u & 1)` using 64-bit arithmetic. Deltas stored in memory after load are already decoded.

## Tape lane and journal

The driver accepts optional `--reset` or `--warm` flags after the output path.

Cold runs (default or `--reset`) wipe `/app/var/vlt_journal` and the in-process tape lane cache before processing panels.

Warm runs (`--warm`) reuse lane entries only when the on-disk bundle fingerprint still matches the cached fingerprint. Fingerprints are FNV-1a digests of raw bundle bytes using the same seed and multiplier as row digests.

After each panel completes, the driver writes `/app/var/vlt_journal/<panel>.chk` containing `name|tape_fingerprint|row_digest`.

## Queries

Evaluated against lane-resolved tape documents:

- `fold`: sum decoded deltas over half-open index range `[from, to)`.
- `peek`: decoded delta at index `at`.
- `tally`: count events where `(tag & mask) != 0`.

## Report JSON

Top-level `schema_version`, `campaign_id`, `panels`, `digest`.
Bundled campaign `vlt_roll_demo` lists panels `t2`, `t5`, and `t8` in manifest order via `/app/environment/fixtures/z7bind.json`.
Each panel: `name`, `event_count`, `tag_span` (max tag value), `answers`, `row_digest`.
Each answer includes `op`, range/index fields, and `value`.

## Row serialization

`name|event_count|tag_span` then per answer:
`|fold|from|to|value`, `|peek|at|value`, or `|tally|mask|value`.

## Digests

Both `row_digest` and top-level `digest` use the same FNV-1a helper on their UTF-8 serialization strings.

FNV-1a: start with seed `1469598103934665603`. For each byte in order, XOR the byte into the hash, then multiply the hash by `1099511628211` and keep only the low 64 bits (mask `2^64-1`). Emit the final value as 16 lowercase hex digits.

`common/digest.cpp` already implements this per-byte order; leave it unchanged.

## Campaign digest

Build the preimage in two parts:

1. First line `schema_version|campaign_id`, then one row serialization per panel in manifest order, each on its own line.
2. Append one final line containing the journal tail binding: digest a newline-joined list of `panel.chk=<digest-of-checkpoint-file-bytes>` entries in manifest panel order (each inner digest uses the same FNV-1a rules over the raw checkpoint file bytes).

Digest the combined string (parts joined by newline) with FNV-1a for the top-level `digest` field.
