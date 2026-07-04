# znctl toolchain

Build:

`CARGO_TARGET_DIR=/tmp/znctl-build cargo build --manifest-path /app/environment/Cargo.toml`

Verifier binary: `/tmp/znctl-build/debug/znctl`

## Master syntax

Master files use a DNS-like line format:

- `$ORIGIN <name>.` sets the active anchor for following relative names.
- `$INCLUDE <path> [<anchor>]` pulls another file from the same directory. An optional second token sets the anchor for the included file only; the prior anchor resumes after the include returns.
- Data lines: `<name> [<ttl>] <class> <type> <rdata...> @key=<id> [@mark=<label>]`
- `@` names the apex of the current anchor.

Fixture cases live under `/app/environment/fixtures/masters/` as `m1`, `m2`, and `m3`. Scope seeds are `s1`, `s2`, and `s3` under `/app/environment/fixtures/scopes/`. Case `m1` uses rule keys `k1` and `k2`; case `m2` uses `top`, `nest`, and `deep`; case `m3` uses `x1`, `x2`, and `x3`. Case `m2` includes `inner.inc` under an explicit include anchor declared in the master text. The `nest` row in `inner.inc` carries an A rdata address the verifier may replace with `192.0.2.99`. Verifier workflows may change the fragment `$ORIGIN` to `inner.example.com.`. Case `m1` includes an MX row whose rdata target ends in `mail.example.com.`; the verifier may swap that target to `mail2.example.com.` or append `extra 300 IN TXT "note" @key=k4` before reload.

## Commands

`znctl init <workroot> <case>` copies a fixture case into `<workroot>/masters/`.

`znctl apply-scope <workroot> <scope>` loads scope `s1`, `s2`, or `s3` into `<workroot>/.state/scope-snap.bin`. The snap records a floor equal to one-fifth of the smallest seeded packet total (rounded down). Re-running apply-scope replaces the snap before the next normalize or reload.

`normalize` ingests masters, merges the scope snap table, assigns lanes from include visit order, and emits products. A normalize pass alone does not write `scope-journal.bin`; reload reconciliation creates that journal as described in `reload-path.md`.

`reload` repeats ingestion and scope merge, then follows `reload-path.md`.

## Binary encodings

Scope seed magic `ZNLD`, version `1`, little-endian row count, per row: key length, key bytes, pkt u64 LE, byte u64 LE.

Snap binary magic `ZNSN`, version `1`, little-endian row count, per-row scope payload (key, pkt, byte, lane byte), then floor u64 LE. Lane bytes in the snap are bookkeeping only; scope merge must not overwrite fragment-assigned lanes.

Material magic `ZNMT`, version `1`, row count, per row in lane order: key length, key, pkt u64, byte u64, body length, body bytes. The pkt field carries ttl totals; byte carries auxiliary scope totals.

Scope journal magic `ZNWJ`, version `1`, row count, per row in lane order: key length, key bytes, carried u8 (`1` when that key received a phase `1` event in the first reload pass).

## Lane binding (cold)

The working edge list contains only edges whose `from` field equals the active root master path (`root.master`), sorted by ascending include ordinal. Ordinal zero is a valid include position and must remain in the working list. Lane assignment uses include visit rank from that list combined with within-file visit order. Rows are finally ordered by ascending lane before emission; ties on lane sort by ascending within-file visit order.

Cold preprocessing canonicalizes relative holder names against the per-row parse anchor. Rows parsed inside an included fragment must not inherit the anchor of an unrelated fragment.

## Canonical body and digests

Canonical body string is holder, rtype, class, ttl, and rdata joined with single spaces (ttl rendered as decimal). `body_digest` is the first sixteen lowercase hex digits of FNV-1a over the canonical body string after collapsing internal whitespace to single spaces.

Zone line text is `holder ttl class rtype rdata` with the same fields. `zone_digest` is FNV-1a over that line using the same digest rule.

FNV-1a: offset basis `0xCBF29CE484222325`, prime `0x100000001B3`, xor-then-multiply per byte, mask to 64 bits, format as sixteen lowercase hex digits.

## Generated JSONL and zone text

`<workroot>/.state/record-catalog.jsonl` — fields: `owner`, `rtype`, `class`, `ttl`, `rdata`, `key`. Lines sorted by ascending lane (lane implicit in line order).

`<workroot>/.state/equiv-report.jsonl` — fields: `owner`, `body_digest`, `zone_digest`. Lines sorted by ascending lane.

`<workroot>/.state/emitted.zone` — one zone line per catalog row in lane order.

Catalog ttl and equiv digests must agree with material rows when both are emitted in the same pass. Equivalence report lines follow catalog lane order. Emitted zone lines follow catalog lane order, not lexical sort.

Material rows are written in lane order with packet totals before auxiliary byte totals. Catalog ttl values reflect row ttl fields, not auxiliary byte totals. Zone digest inputs use catalog ttl values.
