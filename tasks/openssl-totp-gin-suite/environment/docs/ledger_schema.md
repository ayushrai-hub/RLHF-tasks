# Run ledger schema

Path: `/app/output/run_ledger.json`

```json
{
  "runs": [
    {
      "scenario": "<seed name>",
      "status": "<token>",
      "artifact_digest": "<lowercase hex sha256 or empty string>",
      "kid": "<16 hex chars from account_id prefix or empty string>"
    }
  ]
}
```

Status tokens:

| status | meaning |
|--------|---------|
| `ok` | enroll, MFA, and local seal verification succeeded |
| `enroll_reject` | duplicate enrollment rejected with `enroll_conflict` |
| `totp_reject` | MFA rejected for out-of-window passcode |
| `seal_reject` | local seal verification failed |
| `store_reject` | local store file permissions or persistence incorrect |

Non-`ok` rows must set `artifact_digest` to `""` and `kid` to `""`.

`ok` rows set `artifact_digest` to lowercase hex SHA-256 of the session token and `kid` to the first 16 characters of `account_id`.
