# /app/recover CLI specification

The recovery service ships as a single Java entry point built into
`/app/build/com/evidence/recovery/RecoveryMain.class`. A thin wrapper
script `/app/recover` invokes it as

    java -cp "/opt/jars/*:/app/build" com.evidence.recovery.RecoveryMain <subcommand> [args...]

All commands print exactly one compact JSON object to stdout on success,
keys in ASCII-ascending order, and exit 0. On failure they print exactly
one compact JSON object to stderr, keys in ASCII-ascending order, and
exit 1. No banners, no log noise to stdout.

Connection details come from the environment:

| Variable     | Default                            | Notes                       |
|--------------|-------------------------------------|-----------------------------|
| EVIDENCE_DB  | jdbc:h2:file:/app/data/evidence    | H2 file URL                 |
| HLS_INPUT    | /app/data/hls_export               | Corrupted HLS export folder |
| ARTIFACTS    | /app/data/artifacts                | MP4 output folder           |
| MASTER_KEY   | /opt/evidence_keys/master.key.hex  | 64-hex-char master key      |

All H2 JDBC connections MUST authenticate with the default H2
credentials `("sa", "")` (user `sa`, empty password); the verifier
opens its connection with the same pair, and omitting them at
database-creation time binds the DB to the OS user and makes the
verifier's connection fail (see `h2-schema.md`).

## Subcommands

### `init`

Bootstrap the H2 evidence database with the documented schema
(`h2-schema.md`) and seed the wrapped-key rows from
`/app/data/wrapped_keys.json`. Idempotent: re-runs over an existing
database succeed without changing already-seeded rows.

Success: `{"db":"<path>","seeded_keys":N,"status":"ok"}`

### `recover-config`

Read `/app/data/recovery_config.json` (broken values), validate every
field against `hls-recovery.md`, and write the repaired config back to
the same path. The repair is deterministic: each broken field has a
single correct replacement derived from the manifest and the wrapped
keys table. Returns the list of repaired field names.

Success: `{"repaired":[<field>,...],"status":"ok"}`

### `decrypt <segment_index>`

Decrypt segment `<segment_index>` from `HLS_INPUT/segments/<index>.ts.enc`
using the unwrapped content key for the segment's playlist. Verifies the
post-decryption signature from the wrapped-key row, writes the plaintext
.ts to `HLS_INPUT/segments/<index>.ts`, and appends an audit row.

Success: `{"audit_id":N,"bytes":B,"segment":I,"status":"ok"}`

### `decrypt-all`

Iterate every segment listed in the playlist manifest and run the same
flow as `decrypt`, with one audit row per access decision (allow or
deny). Returns counts.

Success: `{"allowed":A,"denied":D,"status":"ok"}`

### `remux <playlist_id>`

Run ffmpeg against the now-plaintext segments for `<playlist_id>`,
concat-mux into `ARTIFACTS/<playlist_id>.mp4`, fingerprint the output
with SHA-256, and insert a row into the `artifacts` table.

Success: `{"artifact_id":N,"playlist_id":"<id>","sha256":"<hex>","status":"ok"}`

### `validate <rule> [<playlist_id>]`

See `validator-rules.md` for the six rule names. The optional
`<playlist_id>` argument selects the target playlist row whose
`audit_validator_sha256` chain receives the fold; when omitted it
defaults to `cam001`. Returns whether the manifest, segments, and
wrapped-key rows satisfy the rule. The manifests root is read from the
`HLS_MANIFESTS_DIR` environment variable (default
`/app/data/hls_export/manifests/`) and the segments root from
`HLS_SEGMENTS_DIR` (default `/app/data/hls_export/segments/`); both
must be honoured so the verifier can inject per-case scratch trees from
`/tmp`. The side-effect is to update the `audit_validator_sha256`
field of the named playlist row with the running validator chain ONLY
when the resolved manifests directory equals the canonical default
`/app/data/hls_export/manifests/` (absolute, normalised). When the
manifests directory is a scratch override, the call still returns the
computed `validator_sha256` in its response but MUST NOT mutate the
persisted column (see `audit-chain.md`).

Success: `{"rule":"<name>","valid":<bool>,"validator_sha256":"<hex>"}`

### `audit list`

List every audit row in `seq` order with documented chain-hash fields
(see `audit-chain.md`).

Success: `{"count":N,"entries":[{...},...]}`

## Errors

All error responses are `{"error":"<code>","message":"<short>"}`
written to stderr with exit 1. See `error-codes.md` for the closed
set of codes.
