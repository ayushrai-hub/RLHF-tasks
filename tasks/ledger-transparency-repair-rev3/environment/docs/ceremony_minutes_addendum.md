# Ceremony Minutes Addendum — 2026-03-12

The council ratified pipe-delimited signing payloads for verification. CSV commas are storage separators only, not signing separators.

Memo cells trim whitespace, collapse internal spaces, NFC-normalize Unicode,
and replace empty memos with the literal `(empty)`.

posted_at values normalize to UTC ISO8601 with a `Z` suffix. amount_cents
is a decimal integer without leading zeros.

Ed25519 signatures are lowercase hex. ledger-key-v2 is primary for
posted_at on or after 2026-03-01T00:00:00Z; ledger-key-v1 covers earlier rows.

legacy-bootstrap rows verify with HMAC-SHA256 keyed by `/app/data/ceremony_seed.bin`
through 2026-03-15T00:00:00Z. In `/app/output/ceremony_rules.json`, record the bootstrap
algorithm export token as `"hmac-sha256"` (lowercase), not `"HMAC-SHA256"`.

## Machine-readable vocabulary

The captured rules file at `/app/output/ceremony_rules.json` must use these exact
token strings (not prose paraphrases):

- `signing.memo_normalization`: `["trim", "collapse_whitespace", "nfc"]`
- `signing.amount_format`: `"decimal_integer_no_leading_zeros"`
- `signing.posted_at_format`: `"utc_iso8601_z"`
- `bootstrap.algorithm`: `"hmac-sha256"`
- `chain.genesis`: `"ledger-genesis-v3"`
- `chain.row_digest`: `"sha256(canonical|signature_hex)"`
- `chain.link`: `"sha256(prev_digest|row_digest)"`
- `receipts.prefix`: `"rcpt-HBR-"`
- `receipts.seq_width`: `4`
