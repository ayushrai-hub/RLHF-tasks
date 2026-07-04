# Assertion ledger format

Path `/workspace/data/assertion-ledger.csv`

Comma separated with header row. Columns:

| Column | Type | Notes |
|--------|------|-------|
| assertion_id | string | Stable identifier like `asrt-001` |
| issuer | string | StampGate issuer id |
| jti | string | JWT ID claim |
| alg | string | Expected JWS algorithm |
| iat | integer | Payload issued-at hint (audit uses detached payload) |
| nbf | integer | Payload not-before hint |
| observed_at_utc | integer | Unix seconds UTC when the assertion was observed |
| detached_jws | string | Detached JWS `header_b64..sig_b64` |
| detached_payload_b64 | string | Base64url JSON payload segment |

Rows are processed in file order for replay tracking.

The shipped ledger contains thirty assertions covering active issuers, revoked access, replay pairs, zero skew overrides, extended skew, EdDSA lowercase kid, ES256 raw signatures, algorithm mismatch traps, short JTI rejection, future `nbf` rejection, and per-issuer audit flags documented in `/workspace/docs/policy-handbook.md` and `/workspace/docs/operations-chronicle.md`.
