# H2 evidence database schema

The H2 database lives at `jdbc:h2:file:/app/data/evidence` (file mode,
single writer). `init` MUST create the following four tables exactly,
in this order, using uppercase identifiers. H2 is the canonical
reference; no other DBMS is supported.

## Connection credentials

All JDBC connections (including every connection the recovery
implementation opens internally) MUST authenticate with the H2
default user `sa` and an empty password `""`. The verifier connects
with the same `("sa", "")` pair via JayDeBeApi to run SQL assertions;
if the database is created without these credentials (for example by
calling `DriverManager.getConnection(url)` with no user/password,
which H2 binds to the current OS user), the verifier connection
fails with `JdbcSQLInvalidAuthorizationSpecException` and every
DB-backed test cascades. Always pass `"sa"` and `""` explicitly:

    DriverManager.getConnection("jdbc:h2:file:/app/data/evidence", "sa", "")

## `playlists`

| Column                  | Type           | Constraint            |
|-------------------------|----------------|-----------------------|
| playlist_id             | VARCHAR(64)    | PRIMARY KEY           |
| manifest_path           | VARCHAR(255)   | NOT NULL              |
| segment_count           | INT            | NOT NULL              |
| codec_private_sha256    | VARCHAR(64)    | NOT NULL              |
| audit_validator_sha256  | VARCHAR(64)    | NOT NULL DEFAULT ''   |

`audit_validator_sha256` starts as the empty string and is updated by
each `validate <rule>` call (see `audit-chain.md`).

## `wrapped_keys`

| Column          | Type           | Constraint                              |
|-----------------|----------------|-----------------------------------------|
| playlist_id     | VARCHAR(64)    | NOT NULL                                |
| key_version     | INT            | NOT NULL                                |
| wrapped_key_hex | VARCHAR(192)   | NOT NULL                                |
| iv_hex          | VARCHAR(32)    | NOT NULL                                |
| sig_hex         | VARCHAR(64)    | NOT NULL                                |
| PRIMARY KEY (playlist_id, key_version)                                    |

`wrapped_key_hex` is the AES-KW (RFC 3394) wrapping of the 16-byte raw
content key using the 32-byte master key. `iv_hex` is the 16-byte
AES-CBC IV used by the segments of that playlist. `sig_hex` is the
lowercase-hex HMAC-SHA256 of the canonical message

    playlist_id || '|' || key_version || '|' || wrapped_key_hex || '|' || iv_hex

keyed by the 32-byte master key. Verifying `sig_hex` is mandatory
before unwrapping.

## `audit_log`

| Column      | Type        | Constraint            |
|-------------|-------------|-----------------------|
| seq         | INT         | PRIMARY KEY AUTO_INCREMENT |
| ts_epoch_ms | BIGINT      | NOT NULL              |
| actor       | VARCHAR(64) | NOT NULL              |
| action      | VARCHAR(32) | NOT NULL              |
| target      | VARCHAR(64) | NOT NULL              |
| decision    | VARCHAR(16) | NOT NULL              |
| prev_hash   | VARCHAR(64) | NOT NULL              |
| entry_hash  | VARCHAR(64) | NOT NULL              |

`actor` is the process tag (`recovery-cli`). `action` is one of
`unwrap`, `decrypt`, `remux`, `validate`. `decision` is `allow` or
`deny`. The hash chain follows `audit-chain.md`.

## `artifacts`

| Column        | Type        | Constraint                  |
|---------------|-------------|-----------------------------|
| artifact_id   | INT         | PRIMARY KEY AUTO_INCREMENT |
| playlist_id   | VARCHAR(64) | NOT NULL                    |
| mp4_path      | VARCHAR(255)| NOT NULL                    |
| sha256        | VARCHAR(64) | NOT NULL                    |
| created_ms    | BIGINT      | NOT NULL                    |

`sha256` is the lowercase-hex digest of the MP4 file bytes.

## Seed data

`init` loads `/app/data/wrapped_keys.json`. The file is a JSON array
of objects with keys `playlist_id`, `manifest_path`, `segment_count`,
`codec_private_sha256`, `key_version`, `wrapped_key_hex`, `iv_hex`,
`sig_hex`. A single playlist row plus one wrapped-key row are inserted
per object; duplicates are silently skipped on re-run.

The clock for `ts_epoch_ms` is `System.currentTimeMillis()` unless
`RECOVERY_NOW_OVERRIDE` is set in the environment, in which case the
override (unix ms) is used. The test fixtures rely on the override so
audit timestamps are deterministic.
