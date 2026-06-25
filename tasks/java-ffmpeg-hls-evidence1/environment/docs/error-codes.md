# Error codes (closed set)

All error responses follow `{"error":"<code>","message":"<short>"}`
written to stderr with exit 1. Keys in ASCII-ascending order, compact
JSON, no trailing newline.

| Code               | When                                                |
|--------------------|-----------------------------------------------------|
| `usage`            | Missing or unknown subcommand, missing required arg |
| `db_not_init`      | Subcommand requires a seeded DB and it is missing   |
| `playlist_unknown` | `playlist_id` not present in `playlists`            |
| `segment_unknown`  | `segment_index` not in `segment_index.json`         |
| `sig_mismatch`     | `wrapped_keys.sig_hex` did not verify               |
| `unwrap_failed`    | AES-KW unwrap of `wrapped_key_hex` failed           |
| `decrypt_failed`   | AES-128 CBC decrypt or PKCS#7 strip failed          |
| `missing_segments` | `remux` ran before all segments were decrypted      |
| `ffmpeg_failed`    | ffmpeg exited non-zero or wrote no output           |
| `validator_unknown`| `validate <rule>` received an unrecognised rule     |
| `config_corrupt`   | `recovery_config.json` is malformed JSON            |
