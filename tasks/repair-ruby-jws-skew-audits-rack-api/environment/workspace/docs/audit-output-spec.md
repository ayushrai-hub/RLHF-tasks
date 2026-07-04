# Audit output specification

All JSON artifacts use two space indentation and a trailing newline.

## policy-cache.json

Path `/workspace/output/policy-cache.json`. Validate against `/workspace/schemas/policy-cache.schema.json`.

| Field | Type | Notes |
|-------|------|-------|
| schema_version | string | Always `1.0` |
| api_base | string | Echo `--api` argument |
| global_policy | object | Copy of `/api/policy` fields |
| active_issuers | array of strings | Sorted ascending, active only |
| revoked_issuers | array of strings | Sorted ascending |
| issuer_overrides | object | Keys are issuer ids with skew overrides |
| issuer_count | integer | Length of `active_issuers` |
| revoked_count | integer | Length of `revoked_issuers` |
| policy_sources | array of strings | Always `["/api/policy", "/api/issuers"]` |

`issuer_overrides` entries contain `max_clock_skew_sec` copied from `skew_override`. Only include issuers that have an override in the API response.

Only issuers with `status` `active` belong in `active_issuers`. Only issuers with `status` `revoked` belong in `revoked_issuers`. Omit `pending` issuers from both lists.

Example override entries:

```json
"acme-lab": {"max_clock_skew_sec": 0},
"ops": {"max_clock_skew_sec": 120}
```

## jws-window-check.json

Path `/workspace/output/jws-window-check.json`. Validate against `/workspace/schemas/jws-window-check.schema.json`.

| Field | Type |
|-------|------|
| schema_version | string |
| ledger_path | string |
| policy_path | string |
| events | array |

Each event object:

| Field | Type |
|-------|------|
| assertion_id | string |
| issuer | string |
| observed_at_utc | integer |
| decision | string |

When `decision` is `valid_window`, include `matched_iat` with the payload `iat` that matched. Omit `matched_iat` for rejected decisions.

Allowed `decision` values for window check: `valid_window`, `invalid_signature`, `outside_skew`, `revoked`, `alg_mismatch`, `invalid_jti`.

Sort `events` by `assertion_id` ascending.

## jws-audit-report.json

Path `/workspace/output/jws-audit-report.json`. Validate against `/workspace/schemas/jws-audit-report.schema.json`.

Same envelope as window check plus `cache_path` and summary integers.

| Field | Type | Meaning |
|-------|------|---------|
| valid_count | integer | Rows with decision `valid` |
| replay_count | integer | Rows with decision `replay` |
| rejected_count | integer | Rows with `invalid_signature`, `outside_skew`, `revoked`, `alg_mismatch`, or `invalid_jti` |

Allowed `decision` values: `valid`, `invalid_signature`, `outside_skew`, `revoked`, `alg_mismatch`, `invalid_jti`, `replay`.

Include `matched_iat` on `valid` and `replay` rows. Omit it on rejected rows.

Sort `events` by `assertion_id` ascending.

Validation rules for ledger rows are in `/workspace/docs/policy-handbook.md` and `/workspace/docs/operations-chronicle.md`.
