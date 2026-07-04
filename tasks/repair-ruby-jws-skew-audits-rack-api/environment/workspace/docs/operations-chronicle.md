# Operations chronicle

Supplemental classroom notes for StampGate audits. Read alongside `/workspace/docs/policy-handbook.md`.

## Per-issuer audit flags

Some issuers publish extra validation rules through `GET /api/issuers/{issuer_id}/audit-flags`. When the route returns HTTP 200, honor every boolean flag in the JSON body during skew validation and replay reporting.

| Issuer | Flag | Effect |
|--------|------|--------|
| echo | `require_exact_iat` true | `iat` must equal `observed_at_utc`. Ignore `skew_override` and `default_max_clock_skew_sec` for that issuer. |
| juliet | `require_exact_iat` true | Same rule as echo. |

Issuers without a row in the audit-flags table return HTTP 404. Treat a 404 as no extra flags.

## Detached JWS signing input

Detached assertions omit the payload segment from the compact serialization. Reconstruct signing input as `header_b64 + "." + detached_payload_b64` before RSA, ECDSA, or Ed25519 verification.

## Deprecated configuration sources

The Rack service still exposes `/api/v2/jwks` and the static file `/workspace/config/jwks.defaults.json` from an older lab image. Neither source matches the live SQLite policy database. Policy cache generation must use `/api/policy` and `/api/issuers` only and record them under `policy_sources`.

## Matched iat echo

Successful JWS rows in window check and audit report JSON must include `matched_iat` as an integer. Replay rows still include `matched_iat` even though the nonce tuple was already stored.

## Kid case sensitivity

JWKS lookup compares `kid` strings with case-sensitive equality.

## JTI length and `nbf` ordering

Reject ledger rows when `jti` length is below `require_jti_min_length` from the policy cache before detached JWS parsing or signature verification.

Reject when payload `nbf` (or `iat` when `nbf` is absent) is greater than `observed_at_utc`, even if `iat` alone would fall inside the skew window.

## Skew boundary inclusivity

Reject when `abs(observed_at_utc - iat)` is greater than the effective skew seconds. Exactly equal to the limit is valid. This applies to default skew, per-issuer overrides, and forward or backward clock drift.

## Payload `iss` claim

Payload `iss` must equal `{issuer_prefix}{issuer_id}` using the ledger `issuer` column and policy cache `issuer_prefix`. Wrong issuer claims are `invalid_signature`.

## Pending issuers and policy cache lists

`/api/issuers` returns every issuer row including `pending` accounts. Policy cache JSON must list only `active` issuers under `active_issuers` and only `revoked` issuers under `revoked_issuers`. Pending issuer `hotel` must be omitted from both arrays. `issuer_count` counts active issuers only.

## Nonce table preservation

The report path must use the existing `nonce_seen` table from `/workspace/sql/nonce-schema.sql`. Do not drop or recreate the table with fewer columns. Each first acceptance inserts `issuer`, `jti`, `alg`, `assertion_id`, and `recorded_at`.
