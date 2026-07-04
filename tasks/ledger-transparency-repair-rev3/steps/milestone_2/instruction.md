# Repair OpenSSL Verifier

The native verifier at `/app/native/ledger_verify.c` is linked through Ruby Fiddle in `/app/service/transparency_cli.rb`. It still canonicalizes CSV rows with obsolete comma rules, skips real Ed25519 and HMAC checks, and computes the wrong hash-chain root. Use the ceremony contract you captured in `/app/output/ceremony_rules.json` plus the ratified sources under `/app/docs` and `/app/data`.

Repair `/app/native/ledger_verify.c`, rebuild `/app/native/libledger_verify.so` with `make -C /app/native`, and keep the exported symbols declared in `/app/native/ledger_verify.h` unchanged:

- `int ledger_canonicalize_row(const char *csv_row, char *out, size_t out_len);`
- `int ledger_verify_signature(const char *canonical, const char *sig_hex, const char *signer, const char *posted_at);`
- `int ledger_row_digest(const char *canonical, const char *sig_hex, char *out, size_t out_len);`
- `int ledger_compute_chain_root(const char **row_digests, size_t count, char *root_hex, size_t root_len);`

Canonicalization must rebuild the pipe-delimited signing payload, normalize memos and timestamps, strip leading zeros from amounts, verify Ed25519 signatures with the correct public key for each row's posted time, reject rows signed with the wrong key for their normalized posted_at, verify legacy-bootstrap rows with HMAC-SHA256 keyed by `/app/data/ceremony_seed.bin` only through the documented cutoff, and compute row digests and the chain root with the v3 genesis string. Initialize the chain state with the lowercase hex SHA256 digest of the UTF-8 bytes of `ledger-genesis-v3` — not the raw genesis string — then link each row with `sha256(prev_digest + "|" + row_digest)`.

Run `bash /tests/test.sh` when this part is done.
