# State digest (tamper evidence)

state_digest is a lowercase hex SHA-256 fingerprint of compact JSON (no spaces) built from ledger-sealed fields after export validates cross-artifact alignment. The digest builder lives in balance/digest.go; export invokes it using enforcement-ledger.json per enforcement-ledger.md.

## Payload fields

| Field | Source |
|-------|--------|
| buckets | ledger.bucket_tokens |
| config_gen | ledger.config_gen |
| route_counter | ledger.route_counter |
| scope_gen | ledger.scope_gen |
| seq | ledger.seq |
| pending_reload_count | ledger.digest_pending_count |

## pending_reload_count in digest

When meta.reload_scope equals state.scope_gen, pending_reload_count is the live length of meta.pending_reloads.

When meta.reload_scope is less than state.scope_gen, pending_reload_count in the digest payload is 0 even if meta.pending_reloads is non-empty.

This digest field is independent of output pending_count, which always reports the live queue length.
