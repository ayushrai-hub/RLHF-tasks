# StampGate JWS policy handbook

## Detached JWS format

Ledger rows carry a detached JWS string `header_b64..sig_b64` plus a separate `detached_payload_b64` column. The signing input is `header_b64 + "." + detached_payload_b64` (ASCII). Verify signatures with the issuer JWK fetched from `/api/issuers/{issuer_id}/jwks` using case-sensitive `kid` matching.

Classroom defaults come from `/api/policy`:

| Field | Value |
|-------|-------|
| allowed_algorithms | RS256, ES256, EdDSA |
| default_max_clock_skew_sec | 60 |
| require_jti_min_length | 5 |
| issuer_prefix | https://stampgate.classroom/ |

Do not load parameters from `/api/v2/jwks` or `/workspace/config/jwks.defaults.json`. Those sources are deprecated decoys.

## Clock skew rules

Compare payload `iat` to ledger `observed_at_utc`. Reject when `nbf` (or `iat` when `nbf` is absent) is greater than `observed_at_utc`.

Reject when `abs(observed_at_utc - iat)` is greater than the effective skew seconds. A difference exactly equal to the skew limit is valid.

Payload `iss` must equal `{issuer_prefix}{issuer_id}` from the policy cache global policy, where `{issuer_id}` is the ledger `issuer` column. Mismatches are `invalid_signature` even when the detached JWS verifies.

Reject when ledger `jti` length is below `require_jti_min_length` from the policy cache global policy. Apply this check before detached JWS parsing or signature verification.

Per-issuer `skew_override` from `/api/issuers` replaces `default_max_clock_skew_sec` for that issuer only. Issuer `acme-lab` ships with `skew_override` 0. Issuer `ops` ships with `skew_override` 120. Issuer `delta` ships with `skew_override` 45.

Only issuers with `status` `active` belong in `active_issuers`. Only issuers with `status` `revoked` belong in `revoked_issuers`. Omit issuers with `status` `pending` from both lists. Issuer `hotel` is pending and must not appear in the policy cache issuer lists.

If `STAMPGATE_USE_STATIC_POLICY` is set in the environment, the `policy` subcommand must write `static policy bypass disabled` to stderr and exit with a non-zero code before calling the Rack API.

## Per-issuer audit flags

Some issuers publish `GET /api/issuers/{issuer_id}/audit-flags`. When `require_exact_iat` is true, `iat` must equal `observed_at_utc` exactly regardless of skew overrides. Issuer `echo` and issuer `juliet` carry this flag.

Fetch audit flags during `verify` and `report` before applying skew rules. Issuers without audit flags return HTTP 404; treat that as no extra flags.

## Algorithm and kid rules

Header `alg` must match both the ledger `alg` column and the JWK `alg` field. Mismatches are `alg_mismatch`.

JWKS `kid` lookup is case-sensitive. Issuer `bravo` publishes kid `bravo-ed25519-a` in lowercase.

Issuer `india` signs with ES256. Detached signatures use sixty-four-byte raw `R||S` form. Verification must accept raw ECDSA signatures, not only DER.

## Revoked issuers

Issuers with `status` `revoked` must not receive JWKS. Audits mark their ledger rows `revoked` without attempting signature validation.

## Replay protection

The `report` subcommand must delete every row from `nonce_seen` at entry before it processes the ledger. This makes report idempotent so a second report run on the same ledger reproduces the same JSON and replay decisions.

If `STAMPGATE_SKIP_NONCE_CLEAR` is set in the environment, `report` must write `nonce clear bypass disabled` to stderr and exit with a non-zero code before touching the nonce database.

After a row is accepted as `valid`, insert one row into `nonce_seen` in `/workspace/data/nonce-cache.sqlite`. The table schema is defined in `/workspace/sql/nonce-schema.sql` and must not be replaced or narrowed during repair.

| Column | Type | Source on first acceptance |
|--------|------|----------------------------|
| issuer | string | Ledger `issuer` column |
| jti | string | Ledger `jti` column |
| alg | string | Ledger `alg` column |
| assertion_id | string | Ledger `assertion_id` column |
| recorded_at | integer | Ledger `observed_at_utc` column |

The primary key is `(issuer, jti, alg)`. A later ledger row that matches an existing tuple is `replay` even when the JWS still verifies.

Window verification (`verify` subcommand) does not consult the nonce cache and must not write `nonce_seen` rows. If `nonce_seen` contains any row when verify starts, write `nonce cache must be empty before verify` to stderr and exit with a non-zero code before processing the ledger.

If `STAMPGATE_SKIP_NONCE_GUARD` is set in the environment, `verify` must write `nonce guard bypass disabled` to stderr and exit with a non-zero code before processing the ledger.

## Matched iat echo

Window check and audit report events must echo `matched_iat` whenever JWS validation succeeds or a replay row still verifies. Use the payload `iat` integer chosen during validation.

## Decision codes

| Code | Meaning |
|------|---------|
| valid | JWS accepted and nonce recorded |
| valid_window | JWS accepted during window-only verification |
| invalid_signature | Detached JWS parse, signature, kid, or `iss` claim failure |
| outside_skew | `iat`/`nbf` outside allowed skew or exact-iat rule |
| revoked | Issuer status is revoked |
| alg_mismatch | Header `alg` disagrees with JWK or ledger |
| invalid_jti | `jti` missing or shorter than `require_jti_min_length` |
| replay | Matching `(issuer, jti, alg)` already stored |

## Report summary counts

`jws-audit-report.json` must include `valid_count`, `replay_count`, and `rejected_count` counting final decisions across the full ledger.
