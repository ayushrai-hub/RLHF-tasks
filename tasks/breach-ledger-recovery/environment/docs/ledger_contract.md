# Breach Ledger Contract

The `breach-ledger` command reads one incident bundle and emits four artifacts. The bundle is accepted only when all evidence can be parsed and all cross-file consistency checks pass. When several problems are present, the reported error is the first matching code in this priority list:

1. `path_traversal`
2. `archive_escape`
3. `malformed_binary_frame`
4. `identity_conflict`
5. `host_conflict`
6. `ssh_sequence_violation`
7. `secret_fragment_conflict`
8. `deleted_meta_conflict`
9. `git_history_conflict`
10. `process_conflict`
11. `timeline_conflict`
12. `missing_required_evidence`

Rejected bundles exit non-zero and write only `incident_report.json`. That JSON has `schema_version: 2`, `status: "rejected"`, and `error.code` set to the priority winner.

## Identity conflict (`identity_conflict`)

Raise `identity_conflict` when `inventory/users.json` binds the same normalized username to more than one `uid`. Scan records in file order: for each entry, compare the normalized `username` and every normalized `aliases` value against prior bindings. If a name was already assigned a different `uid`, reject with `identity_conflict`. Duplicate rows that repeat the same username with the same `uid` do not trigger this code.

## Deleted metadata conflict (`deleted_meta_conflict`)

Raise `deleted_meta_conflict` when two rows from SQLite table `deleted_files(path, sha256, deleted_at, size, recovered_from)` describe the same exact `path` but disagree on the recovered file payload metadata. A duplicate path with a different `sha256` or `size` is conflicting deleted metadata. Unsafe deleted-file paths still use the higher-priority `path_traversal` code.

## Process snapshot conflict (`process_conflict`)

Raise `process_conflict` when two JSONL rows in `proc/snapshots.jsonl` have the same process key but different payloads. The process key is the normalized `host` joined with the numeric `pid`; the compared payload is the canonical JSON row after parsing. Identical duplicate process rows do not trigger this code.

## Required evidence (`missing_required_evidence`)

The analyzer requires evidence for both intrusion paths. Attacker `A` must be established by an accepted password SSH auth record, and attacker `B` must be established by a successful vulnerable web access record. If either initial-access path is absent after parsing, reject with `missing_required_evidence`. This code also applies when required supporting stores cannot be read, including the deleted-file SQLite database and the secret fragment manifest.

Accepted report schema:

- `schema_version`: integer `2`
- `status`: `"accepted"`
- `classification`: `"multi_hop_intrusion"`
- `initial_access`: array sorted by `attacker_id`; each item records `attacker_id`, `host`, `vector`, `vulnerability`, `account`, `source_ip`, and `timestamp`. The two intrusion paths use attacker identifiers `A` (remote shell access) and `B` (web-tier exploitation).
- `compromised_hosts`: sorted unique host names
- `compromised_accounts`: sorted unique user names
- `commands`: chronological command strings from hostile shell history, binary audit frames, and staged archive command logs; null bytes are removed
- `persistence`: sorted flat strings using `cron:<host>:/etc/cron.d/<name>`, `systemd:<host>:<unit>`, or `shell:<user>:<path>`. For shell entries, `<path>` is the raw `path=` metadata value from the persistence file (do not normalize to an absolute path).
- `stolen_files`: sorted unique absolute paths from deleted metadata and staged archive manifests
- `stolen_secrets`: decoded secret lines sorted by byte value
- `exfiltration`: destination summary with `destination_ip`, `protocol`, `bytes`, and `timestamp`. When multiple egress records correlate to intrusion activity, `bytes` is the largest value (use 64-bit integers). When an archive exfiltration manifest and egress log both describe the same correlated transfer (matching destination and byte count), the archive manifest's `timestamp` is authoritative.
- `modified_configs`: sorted unique basenames of live configuration files whose SHA-256 digest differs from `configs/manifest.json`
- `iocs`: sorted unique typed indicator strings:
  - `ip:<address>` for intrusion-related source or destination addresses
  - `cve:<id>` for the exploited web vulnerability
  - `url:<path>` for the exploited web request path
  - `domain:<hostname>` for correlated DNS queries (exclude service-account noise)
  - `secret-sha256:<hex>` for the decoded secret payload digest
- `false_leads`: sorted bare account or address labels (no type prefix) that appear in DNS, egress, web, or process evidence but do not correlate to hostile commands, persistence, or exfiltration. Background metrics traffic from the `svc-metrics` account and internal address `172.16.10.55` are false leads in the omega bundle.
- `tampered_events`: sorted records from trusted audit frames where `claimed_ts` differs from `ts`; each record has `seq`, `host`, `user`, `claimed_ts`, `true_ts`, and `detail`
- `parse_summary`: object with exactly these evidence-family counters:
  - `auth_entries`: parsed SSH auth records from `logs/auth.log*`
  - `web_entries`: parsed web access records from `web/access.jsonl`
  - `history_entries`: parsed command lines from `histories/*.bash_history`
  - `persistence_entries`: parsed cron, systemd, and shell persistence records
  - `dns_entries`: parsed DNS records from `network/dns.log`
  - `egress_entries`: parsed egress records from `network/egress.log`
  - `audit_frames`: parsed trusted binary audit frames
  - `deleted_files`: parsed rows from SQLite table `deleted_files`
  - `git_events`: parsed records from `git/events.jsonl`
  - `secret_fragments`: decoded secret fragment payloads listed by the secret manifest
  - `archive_entries`: inspected zip members from staged archives
  - `config_files`: live config files compared against `configs/manifest.json`
  - `process_snapshots`: parsed records from `proc/snapshots.jsonl`
  - `container_entries`: parsed records from `containers/list.jsonl`

`attack_timeline.csv` uses the header `seq,ts,host,user,source,action,detail,attacker_id`. Rows sort by timestamp, then sequence number, then host, then action, then detail. The `seq` column is a decimal integer; events without a source sequence number use `0`. Details must not contain null bytes. The `source` column names the evidence family (`auth`, `web`, `history`, `audit`, `archive`, `process`, `container`, `dns`, `egress`, `persistence`, and similar).

`iocs.txt` is a newline-terminated, sorted, unique list matching the report's `iocs` array.

`remediation_plan.json` contains `schema_version`, `golden_config_changed`, `modified_config_count`, `persistence_item_count`, and a sorted `actions` array. The analyzer compares files under `configs/live` to `configs/manifest.json`; config drift is reported, but manifest files are not changed. `golden_config_changed` is `true` only when the manifest file itself was altered. Remediation actions use these prefixes:

- `remove:<persistence item>` for each persistence entry
- `restore_config:<basename>` for each modified configuration basename
- `block_ip:<address>` for each `ip:` IOC (written as `block_` prefixed to the full IOC string)
- `review_file:<absolute path>` for each stolen file
- plus fixed actions `disable_account:backup`, `patch:CVE-2025-4178`, and `rotate_secret:token` when the accepted bundle includes the corresponding evidence

Path rules apply to SQLite rows and zip entries. Deleted-file paths must be absolute and cannot traverse after cleaning. Zip member names must be relative, clean, and stay inside the archive namespace.

Timeline validation rejects bundles where an attributed attacker event timestamp is strictly earlier than that attacker's initial-access timestamp.
