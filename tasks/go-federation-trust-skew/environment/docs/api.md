# Ward API

## Claim shape

| Field | Type | Notes |
|-------|------|-------|
| `Kid` | string | Issuer key id |
| `Gen` | uint64 | Bundle generation |
| `Realm` | string | Presented realm |
| `ExtID` | string | External subject id |
| `AnchorMs` | int64 | Monotonic anchor (ms) |
| `NotBefore` | int64 | Window start (ms) |
| `NotAfter` | int64 | Window end (ms) |
| `Sig` | []byte | HMAC-SHA256 over payload |

Payload format:

```
kid|gen|realm|ext|anchorMs|notBefore|notAfter
```

## Outcome shape

| Field | Type | Notes |
|-------|------|-------|
| `Code` | string | Deny code or `ADMIT` |
| `Principal` | string | Resolved local principal when admitted |
| `UsedGen` | uint64 | Generation evaluated |
| `UsedMapGen` | uint64 | Map generation consulted |

## Probe JSON (`/app/output/stage/probe.json`)

| Field | Type | Notes |
|-------|------|-------|
| `ready` | bool | True when serial fresh assertion admits |
| `code` | string | Outcome code |
| `principal` | string | Resolved principal when admitted |

## Harness outputs

`/app/output/harness/status.txt` contains `harness_ok` when the harness sample subset completes successfully.
