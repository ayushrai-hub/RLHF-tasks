# MFA host HTTP contract

Base URL: `http://127.0.0.1:9477`

## Enroll account

`POST /v1/accounts/enroll`

Body JSON:

```json
{ "handle": "<unique handle>" }
```

Response JSON:

```json
{
  "account_id": "<32 hex chars>",
  "wrapped_secret": "<base32 secret with trailing = fill to a multiple of eight characters>",
  "signing_material": "<64 hex chars>"
}
```

Conflict response:

```json
{ "error": { "code": "enroll_conflict", "detail": "handle already enrolled" } }
```

## Rotate signing material

`POST /v1/accounts/rotate`

Body JSON:

```json
{ "account_id": "<32 hex chars>" }
```

Response JSON:

```json
{
  "account_id": "<32 hex chars>",
  "signing_material": "<64 hex chars>"
}
```

## MFA login

`POST /v1/sessions/mfa`

Optional header: `X-Clock-Epoch: <unix seconds>` for deterministic grading.

Body JSON:

```json
{ "account_id": "<32 hex chars>", "passcode": "<six digits>" }
```

Response JSON:

```json
{ "session_token": "<token>", "expires_at": 1710000000 }
```

Reject response:

```json
{ "error": { "code": "totp_reject", "detail": "passcode rejected" } }
```

## Verify session seal (server)

`POST /v1/sessions/verify`

Body JSON:

```json
{ "account_id": "<32 hex chars>", "session_token": "<token>" }
```

## Client passcode derivation

The C driver derives six-digit passcodes from the enrolled secret and a Unix epoch. Materialization must stay compatible with the host step policy in `/app/environment/m3_host/config/host.toml` (`step_seconds`, `step_window`). When the graded driver supplies distinct host and passcode epochs via `K9_CLOCK_EPOCH` and `K9_PASSCODE_EPOCH`, passcode materialization must follow the passcode epoch while host HTTP calls use the host epoch. Dual-epoch window policy must read host step width from `/app/environment/c9_drv/config/driver.toml` (`step_seconds`, not `step_window`). When a passcode epoch binding is active, stride selection must not shrink the configured step width.

Passcodes must match what the host accepts for the material epoch within the configured window. Cross-check implementations may use Python `hmac` and `struct` for the same counter packing contract.

## Local CLI probe subcommand

`m3_cli probe --account-id A --store-dir D [--clock-epoch E]` prints the six-digit passcode the MFA path would submit for the persisted account. When `--clock-epoch` is omitted, the probe uses `K9_CLOCK_EPOCH` if set. The probe follows the same passcode materialization path as MFA.

## Local CLI verify subcommand

`m3_cli verify --account-id A --token T --store-dir D [--clock-epoch E]` performs session token verification using persisted signing key bytes. Exit code `12` indicates token rejection (MAC mismatch or expired payload). Exit code `0` prints `verified` on success.

## Session seal format

Session tokens are three-part base64url seals returned by MFA. Local verification must reject MAC mismatches and expired payloads (`exp <= now_epoch`) using the signing material persisted at enrollment. MAC input is the ASCII concatenation of the first two seal segments separated by a dot; verification receives the full three-part token unchanged. Payload expiry is read from decoded JSON after the MAC check succeeds.

## Local store file

Path: `<store_dir>/<account_id>.store`

JSON body:

```json
{
  "account_id": "<32 hex chars>",
  "secret_raw": "<hex of decoded wrapped secret>",
  "signing_material": "<64 hex chars>"
}
```

Store files must grant read and write permission to the owner only; group and other permission bits must be clear after enrollment writes complete.
