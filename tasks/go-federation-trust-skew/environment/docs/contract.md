# Ward contract

## Validation commands

```bash
go build /app/environment/...
go run /app/environment/cmd/probe/main.go
bash /app/environment/scripts/verify_output.sh
```

## Test sources

Do not modify the hidden graded suite at `/app/environment/internal/ward/m4_grade_test.go`. Its integrity is checked at verify time:

```bash
sha256sum /app/environment/internal/ward/m4_grade_test.go
```

## Observable symptoms

Under simulated clock skew, bundle rotation, realm formatting drift, and concurrent map reload, operators report:

- Assertions outside the nominal window are admitted at tolerance edges.
- Assertions signed with retired bundle generations still admit.
- Equivalent realm strings mismatch while exact string matches pass.
- External id resolution returns principals from before the latest map reload.

Serial probe (`cmd/probe`) may report `"ready": true` on a single fresh assertion while graded cases still fail.

## Time window

All times are **milliseconds** on a monotonic anchor axis.

Configured slack defaults to **5000 ms** (`DefaultSlack`).

## Bundle generation

Each issuer key id (`kid`) carries a monotonically increasing generation counter in the spool ledger.

## Realm binding

Local service realm is configured as `svc://payments.local`.

Presented realm strings may not match the configured local realm literally.

## External id map

The map store exposes a monotonic generation counter incremented on every reload.

Missing external ids yield `DENY_ALIAS`.

## Deny codes

| Code | Meaning |
|------|---------|
| `ADMIT` | Assertion accepted |
| `DENY_TIME_WINDOW` | Anchor outside slack-expanded window |
| `DENY_STALE_KEY` | Bundle generation not live |
| `DENY_MAC` | Signature mismatch |
| `DENY_REALM` | Realm binding failed |
| `DENY_ALIAS` | External id not mapped |

## Output regeneration

Static JSON under `/app/output/` is rewritten by tests and harness scripts. Hand-written output is insufficient.
