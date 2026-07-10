# Validation Matrix

The analyzer is order-insensitive for equivalent evidence, but the artifacts are byte-stable. Duplicate records with identical payloads are preserved in output counts and timelines where the source format naturally repeats (identical copies are not deduplicated).

`identity_conflict` applies only to `inventory/users.json`: the same normalized username (including values listed under `aliases`) must always map to the same `uid`. A second record that reuses a username with a different `uid` rejects with `identity_conflict`. Other duplicate keys (hosts, commits, deleted-file paths, process keys) use their own contract codes when payloads disagree.

Auth log sequence numbers are unique across plain and gzip auth logs. Binary audit frame sequence numbers participate in timeline ordering but do not repair duplicate auth sequence numbers.

SQLite evidence is queried from `deleted_files(path, sha256, deleted_at, size, recovered_from)`. Archive command logs extend the command timeline and exfiltration evidence; they do not override higher-priority validation failures elsewhere.
