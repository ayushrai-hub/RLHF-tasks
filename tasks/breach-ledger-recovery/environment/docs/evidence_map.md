# Evidence Map

The omega bundle contains inventory JSON, SSH auth logs, web access JSONL at `web/access.jsonl`, user shell histories, persistence snapshots, process records in `proc/snapshots.jsonl`, DNS and egress logs, binary audit frames, deleted-file metadata in SQLite at `deleted.sqlite`, Git event JSONL in `git/events.jsonl`, encoded secret fragments, a staged zip archive, container records in `containers/list.jsonl`, and live configuration files.

Binary audit frames are length-prefixed JSON objects. The four-byte prefix is unsigned big-endian, equivalent to a Python `struct` big-endian unsigned integer. Frame timestamps are trusted over claimed log timestamps when a frame includes `claimed_ts`.

Secret fragments are listed in `secrets/manifest.json`. Each fragment file is base64 text containing gzip-compressed bytes XORed with the single-byte key from the manifest. Decoded fragment payloads concatenate in manifest order, and the SHA-256 digest must match the manifest.

The staged zip archive is compatible with ordinary zipfile readers and includes an exfiltration manifest and a gzip command log. Archive entries are evidence only when their names are clean relative paths. When an archive exfiltration manifest and egress log describe the same correlated transfer, the manifest timestamp takes precedence over the egress log timestamp; byte counts still use the largest value across sources.

Deleted-file metadata and archive manifests both contribute stolen-file candidates. Network evidence contributes indicators only when it correlates with accepted intrusion activity; background service traffic remains a false lead. Web vulnerability indicators come from successful access-log records, not from scans or failed requests.

Validation checks are intentionally layered. Unsafe path names are rejected before lower-priority content conflicts, trusted binary audit timestamps override claimed timestamps for tamper reporting, and process records must remain consistent with persistence and history evidence.
