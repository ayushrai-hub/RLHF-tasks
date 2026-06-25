# Canonical bytes for the report digest

The `report_digest` is the lowercase hex SHA-256 of the canonical
byte sequence below. The sequence is built from the FINAL output —
not from an intermediate stage — so the digest is computed AFTER the
cascade, marker mute, jitter upgrade, and sort are all settled.

## Byte recipe

The preimage is exactly:

    <probe-ledger>\n##\n<reflector-ledger>\n##\nsummary:total=<N>;good=<G>;cycles=<C>\n

where:

* `<probe-ledger>` is the probe array in final output order, one line
  per row, each line `<probe_id>|<reflector_id>|<verdict>|<owd_us>`.
  Rows are joined with `\n` and there is NO trailing `\n` before the
  separator (the separator itself supplies the leading `\n`).
* `<reflector-ledger>` is `<reflector_id>=<jitter_share_permille>`
  for each reflector in the output order (numeric-suffix sort),
  joined with `|`.
* The closing line has the literal prefix `summary:` and ends with a
  single trailing `\n`.

The separator between the three sections is the LITERAL three-byte
sequence `\n##\n`. Not `\n--\n`, not `\n==\n`, not `\n\n`, not
`\n|\n`. Three bytes only: newline, hash, hash, newline.

## Twin emission

The digest is emitted twice in the report:

* `summary.report_digest` (inside the summary block)
* top-level `report_digest`

Both must contain the SAME 64-hex string. A run where the two disagree
is non-conforming; either the canonical bytes were computed differently
for each emission or the report body was reordered between them.

## Common misimplementations

* `\n--\n` as the separator — every digest differs from the spec.
* Blank line (`\n\n`) as the separator — every digest differs.
* Adding a trailing `\n` after the last probe-ledger row before the
  first separator — the leading newline is doubled.
* CRLF line endings (`\r\n`) — every digest differs.
* Sorting the reflector-ledger lexically (`R1, R10, R11, R2, R3`)
  instead of by numeric suffix (`R1, R2, R3, R10, R11`).
* Filtering OWD_ANOMALY / QUIET_SUPPRESSED / synthetic
  REFLECTOR_OFFLINE rows OUT of the probe ledger — every probe-ledger
  row in the final output participates.
* Recomputing the digest from a stale post-cascade snapshot — must
  use the FINAL ledger after marker mute and jitter upgrade.
