# StampGate policy API

Base URL `http://127.0.0.1:8966`

## GET /health

Returns HTTP 200 with JSON body:

```json
{"status": "ok", "service": "stampgate"}
```

## GET /api/policy

Returns the global JWS validation parameters.

| Field | Type | Meaning |
|-------|------|---------|
| allowed_algorithms | array of strings | Permitted JWS `alg` values |
| default_max_clock_skew_sec | integer | Default `iat` tolerance in seconds |
| require_jti_min_length | integer | Minimum `jti` string length |
| issuer_prefix | string | Prefix for payload `iss` claims |

## GET /api/issuers

Returns a JSON array sorted by `issuer_id` ascending. Each element contains:

| Field | Type | Required |
|-------|------|----------|
| issuer_id | string | yes |
| status | string | yes, `active`, `revoked`, or `pending` |
| skew_override | integer | no, only when the issuer has a custom skew |

## GET /api/issuers/{issuer_id}/jwks

Active issuers return HTTP 200 with a `keys` array of JWK objects. Each key includes `kid`, `alg`, and algorithm-specific material. `kid` matching is case-sensitive.

Revoked or unknown issuers return HTTP 404.

## GET /api/issuers/{issuer_id}/audit-flags

Returns supplemental validation flags when configured.

```json
{"issuer_id": "echo", "require_exact_iat": true}
```

Unknown or unconfigured issuers return HTTP 404 with `{"error": "no_audit_flags"}`.

## Deprecated routes

`GET /api/v2/jwks` still exists for regression drills. It returns an empty key set and must not be used for policy cache generation.

## Policy cache command

`stampgate-audit policy` must read `/api/policy` and `/api/issuers`. Do not call the deprecated `/api/v2/jwks` route. `policy_client.rb` must not contain that deprecated path string even inside comments.

Per-issuer audit flags are documented in `/workspace/docs/operations-chronicle.md` and are consulted during `verify` and `report`, not during `policy`.
