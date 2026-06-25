# Audit chain + validator chain

## `audit_log` entry hash

Every insert into `audit_log` computes a chained hash to make the log
tamper-evident.

* `prev_hash` for `seq=1` (genesis) is 64 zeros (`"0" * 64`).
* `prev_hash` for `seq=N>1` is the `entry_hash` of `seq=N-1`.
* `entry_hash` is the lowercase-hex HMAC-SHA256 of the canonical
  message

      seq || '|' || ts_epoch_ms || '|' || actor || '|' || action
        || '|' || target || '|' || decision || '|' || prev_hash

  keyed by the 32-byte master key. All separators are literal `|`,
  no whitespace, integers rendered in base-10 ASCII.

The verifier walks the table in `seq` order and re-derives every
`entry_hash`; mismatches are oracle-fatal.

## `playlists.audit_validator_sha256`

Each call to `validate <rule>` updates a single
`audit_validator_sha256` column on the playlist row. The new value is
the lowercase-hex SHA-256 of the canonical concatenation

    prev_validator_sha256 || '|' || rule_name || '|' || (valid ? '1' : '0')

where `prev_validator_sha256` is the current column value (empty string
on the very first update). All six rules MUST be appended in the order
they were called; the column therefore deterministically encodes both
the order and the outcome of every validator call. The verifier
compares this column against the expected vector in
`/app/fixtures/expected_validators.json`.

### Scratch (non-canonical) invocations do NOT update the column

When the validator is invoked with `HLS_MANIFESTS_DIR` pointing at a
non-canonical directory (any path whose absolute, normalised form is
not equal to the canonical default `/app/data/hls_export/manifests/`),
the implementation MUST compute the new `validator_sha256` value for
the JSON response but MUST NOT persist it to
`playlists.audit_validator_sha256`. The 24-case fixture sweep relies
on this guard: it points the validator at per-case scratch trees
under `/tmp` to assert the boolean outcome of every rule, and the
canonical chain on `cam001` must remain byte-for-byte equal to the
value produced by the in-order sweep against the canonical manifests
directory. Implementations that fold every call into the column will
fail both the chain-pinning test and the explicit immutability tests
on `cam001`.
