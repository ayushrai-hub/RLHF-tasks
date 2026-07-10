# Validation Matrix

The analyzer is order-insensitive for equivalent evidence, but the artifacts are byte-stable. Duplicate records with identical payloads are preserved in output counts and timelines where the source format naturally repeats (identical copies are not deduplicated).

`identity_conflict` applies only to `inventory/users.json`: the same normalized username (including values listed under `aliases`) must always map to the same `uid`. A second record that reuses a username with a different `uid` rejects with `identity_conflict`.

`host_conflict` applies only to `inventory/hosts.json`: the same normalized host alias (including the canonical `host` value and every normalized `aliases` entry) must always map to the same canonical host name. A second record that reuses an alias with a different canonical host rejects with `host_conflict`.

`archive_escape` applies to staged zip member names: absolute paths, backslash separators, and traversal sequences reject with `archive_escape`.

Other duplicate keys (commits, deleted-file paths, process keys) use their own contract codes when payloads disagree.

Auth log sequence numbers are unique across plain and gzip auth logs. Binary audit frame sequence numbers participate in timeline ordering but do not repair duplicate auth sequence numbers.

SQLite evidence is queried from `deleted_files(path, sha256, deleted_at, size, recovered_from)`. Archive command logs extend the command timeline and exfiltration evidence; they do not override higher-priority validation failures elsewhere.
