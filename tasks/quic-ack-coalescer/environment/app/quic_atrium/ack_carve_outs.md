# Migrations

## v2026.05.18 → v2026.06.07

The policy schema gains nothing in this round, but two behaviors change in
ways that require call-site review.

### Hamilton direction default

Pre-2026.06.07: `FORWARD` always.

Post-2026.06.07: `REVERSE` by default, flips to `FORWARD` only on
`urgent=true` for any registered connection.

Migration notes — any downstream that pinned an expected basis-points layout
on `REVERSE` direction will keep working; any downstream that pinned on the
forward default needs to flip a connection's `urgent` flag to keep parity.

### Closed verdict enum

The verdict set expanded from five entries to seven. The new entries are
`BAD_SPACE` and `RESET_VOID`. Every map carrying verdict counts MUST now
include all seven keys even at zero counts. A consumer that iterates
`by_verdict.keys()` will pick up the new entries automatically; a consumer
that hard-codes the five-entry list needs a refresh.

### Window inclusivity

Pre-2026.06.07: the docs were ambiguous about the right edge of the coalesce
window. Code in practice treated the boundary as REORDERED.

Post-2026.06.07: the boundary at `delta == coalesce_ms` is COALESCED. The
prior reading is wrong and reproduces by accident on fixtures whose deltas
never land on the boundary.

### Numeric-suffix sort

`by_conn`, `hamilton`, and `events` sort by numeric-suffix on `conn_id`.
Plain lexicographic order on conn ids like `C2, C10, C11` is wrong.

## v2026.02.10 → v2026.05.18

`hmac8` width grew from 4 to 8 hex characters. Any pre-baked test fixture
with a four-character seal must regenerate the seal.

Tier synonym lookup now lower-cases and trims the raw label before lookup.
Adding a label that is upper-case in `tier_synonyms` will never match.

## v2025.11.30 → v2026.02.10

`budget_threshold` semantics flipped from strict-greater-than to
greater-than-or-equal. A fixture that had been calibrated to "right at the
threshold, no cascade" now does cascade. The threshold should be raised by
one if the prior pre-cascade behavior is required.

The cascade rewrite no longer requires same pn_space. The earliest
still-accepted event on the next day, in any pn_space, is the rewrite
target.

## v2025.08.04 → v2025.11.30

`report_digest` added. Pre-existing reports lacked the field; consumers that
schema-validate against the old shape must add it as a required field.

The canonical bytes that feed the digest use two-space indent and no
trailing newline. The on-disk file appends exactly one trailing newline.
The digest is over the indented bytes, NOT the bytes after the trailing
newline.
