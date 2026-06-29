# Local file retention reconciliation contract

## Command

Run the reconciler from /app with:

```bash
go run /app/bin/local-retention-reconciler.go --config /app/config/retention-policy.json --manifests /app/manifests --out /app/out
```

The CLI must accept the same `--config`, `--manifests`, and `--out` flags for other absolute paths. It writes exactly these JSON files under the output directory:

- `retention_report.json`
- `cleanup_plan.json`
- `warnings.json`

On every successful run, remove stale `.json` files directly inside the output directory before writing the three required files. Do not remove non-JSON files or recurse into output subdirectories.

## Policy config

The config file is a UTF-8 JSON object with these fields:

- `evaluation_time`: required RFC3339 timestamp. All retention, exception, and age calculations use this instant in UTC.
- `defaults`: optional object with `retention_days`, `max_mode`, and `delete_action` used only when a class policy omits that field.
- `classes`: object keyed by class name. Each value defines a retention policy.
- `class_aliases`: optional object mapping alternate manifest class names to canonical class names. Resolve aliases before class policy lookup, exception matching, cleanup-block matching, report output, and unknown-class checks. Alias chains may be followed until no further alias exists; if a cycle is encountered, stop at the repeated class name.
- `exceptions`: optional array of exception-window objects.
- `cleanup_blocks`: optional array of cleanup-block objects used to suppress selected cleanup actions without removing the record from the report.
- `cleanup_capacity`: optional object mapping cleanup action names (`delete`, `archive`, `quarantine`, or `chmod`) to the maximum number of that action that may be scheduled in a single wave. Missing, zero, or negative capacities mean unlimited for that action.
- `cleanup_byte_capacity`: optional object mapping cleanup action names to the maximum total `size_bytes` for that action that may be scheduled in a single wave. Missing, zero, or negative byte capacities mean unlimited. Count capacity and byte capacity are applied together after cleanup dependency cycles are removed. If every currently ready action would exceed a positive byte capacity by itself, schedule the lexicographically first ready action anyway so the plan always makes progress.

Retention groups are declared on manifest records, not in config. They are evaluated after per-record retention, permission, exception, and cleanup-block checks. Cleanup dependencies and wave budgets are evaluated after retention-group holds.

Each class policy has:

- `policy_id`: string. If blank or missing, use the class key.
- `retention_days`: positive integer days. If missing or zero, use `defaults.retention_days`.
- `max_mode`: four octal digits such as `0640`. If blank, use `defaults.max_mode`.
- `delete_action`: one of `delete`, `archive`, or `quarantine`. If blank, use `defaults.delete_action`; if that is blank, use `delete`.

Each exception object has:

- `exception_id`: required string.
- `path_prefix`: required absolute POSIX path prefix. Prefix matching is literal after path cleanup; `/a/b/` matches `/a/b/c.txt` but not `/a/bad/c.txt`.
- `class`: optional class filter. A blank or missing class matches every class. Class filters compare to the resolved canonical class after `class_aliases` are applied.
- `starts_at`: required RFC3339 timestamp. The start is inclusive.
- `ends_at`: required RFC3339 timestamp. The end is exclusive.
- `retention_days`: optional positive integer override. A value of zero means the exception does not change retention days.
- `allow_mode`: optional boolean. When true on the chosen active exception, permission warnings and permission-only cleanup actions are suppressed for that record.

Each cleanup-block object has:

- `blocker_id`: required string.
- `path_prefix`: required absolute POSIX path prefix using the same normalized prefix matching as exceptions.
- `class`: optional class filter compared to the resolved canonical class. A blank or missing class matches every class.
- `starts_at`: required RFC3339 timestamp. The start is inclusive.
- `ends_at`: required RFC3339 timestamp. The end is exclusive.
- `applies_to`: optional array of cleanup action names. When blank or missing, the block applies to every cleanup action. Otherwise it applies only to listed actions such as `delete`, `archive`, `quarantine`, or `chmod`.

## Manifest discovery and schema

The manifest root is walked recursively. Read files whose names end with `.jsonl`; ignore all other files. Input files are processed by lexicographic POSIX path, and lines are one-based.

Each non-empty JSONL line should be an object with:

- `path`: required absolute POSIX file path. Normalize with POSIX `clean` rules. A path that does not start with `/` is invalid.
- `record_type`: required string. Only `file` records are reconciled; any other value is invalid.
- `class`: required class name string.
- `modified_at`: required RFC3339 timestamp.
- `mode`: required four octal digits such as `0644`.
- `owner`: optional string; missing serializes as `""`.
- `group`: optional string; missing serializes as `""`.
- `retention_group`: optional string. Missing or blank serializes as `""`. Non-blank values link selected kept records for the group-hold behavior described below; the value is trimmed before output and matching.
- `cleanup_after`: optional array of absolute POSIX paths. Each absolute entry is normalized and deduplicated. Relative, blank, or duplicate entries are ignored. Dependencies only affect records that still have a cleanup action after cleanup blocks and retention-group holds.
- `size_bytes`: optional non-negative integer; missing serializes as `0`.
- `source_rank`: optional integer used for duplicate resolution; missing is `0`.
- `scanned_at`: optional RFC3339 timestamp used for duplicate resolution; missing is the zero timestamp and serializes nowhere in outputs.

Malformed JSONL lines emit warnings and do not stop processing later lines in the same file. Invalid parsed records emit warnings and are excluded from duplicate resolution, reports, and cleanup actions. Valid peer records in the same file must still be preserved.

## Duplicate resolution

Duplicate identity is the normalized `path`. Resolve duplicates after syntactic validation and before policy evaluation. Keep exactly one candidate per path using this ranked order:

1. higher `source_rank` wins;
2. if tied, later `scanned_at` wins;
3. if tied, lexicographically smallest `source_path` wins;
4. if tied, smaller `source_line` wins.

Every discarded valid duplicate emits one `duplicate_manifest` warning using the discarded record's path, source file, and source line. The warning detail is exactly `duplicate path <path>; kept <kept_source_path>:<kept_source_line>`.

## Retention, exceptions, permissions, cleanup blocks, and retention groups

For each kept record, first resolve the record class through `class_aliases`, then resolve its class policy. The `class` field emitted in reports is the resolved canonical class, not the raw alias. If the resolved class is unknown, include the record in `retention_report.json` with `policy_id: ""`, `effective_deadline: null`, `exception_id: ""`, `blocked_by: ""`, `mode_compliant: false`, and `status: "needs_review"`; emit `unknown_class`; do not create a cleanup action for that record.

For known classes, compute `base_deadline = modified_at + retention_days` from the class policy. The deadline instant is due when `evaluation_time >= effective_deadline`.

Matching active exceptions are those whose `path_prefix` matches the normalized path, whose class is blank or equals the resolved record class, and whose window satisfies `starts_at <= evaluation_time < ends_at`. If more than one active exception matches, choose one by:

1. longest normalized `path_prefix`;
2. latest `starts_at`;
3. lexicographically smallest `exception_id`.

If the chosen active exception has positive `retention_days`, use that value to compute `effective_deadline`; otherwise use the class retention days. `exception_id` is the chosen active exception id, or `""` when none applies. Matching expired exceptions where `evaluation_time >= ends_at` never affect retention or permissions and emit `expired_exception` for each selected record they match. Future exceptions do not emit warnings.

Cleanup blocks are active when their normalized `path_prefix` matches the record path, their class is blank or equals the resolved record class, their window satisfies `starts_at <= evaluation_time < ends_at`, and their `applies_to` is blank or contains the cleanup action that would otherwise be emitted. If more than one active cleanup block applies to the same pending action, choose one by:

1. longest normalized `path_prefix`;
2. latest `starts_at`;
3. lexicographically smallest `blocker_id`.

Retention-group holds run after cleanup-block selection. A non-blank `retention_group` protects other records in the same group when at least one selected group member has final status `exception_retained` or `cleanup_blocked`. The chosen group protector is the lexicographically smallest protected record path in that group. If another group member would otherwise emit a cleanup action (`delete`, `archive`, `quarantine`, or `chmod`), suppress that action, set its status to `group_blocked`, and set `blocked_by` to `group:<retention_group>:<protector_path>`. The protector record keeps its own status; `group_blocked` records do not protect additional peers.

Permission compliance compares the record's octal mode to the effective maximum mode. A mode is too permissive when it contains any permission bit not present in `max_mode`. For example, `0644` exceeds `0640` because world-read is not allowed. If the chosen active exception has `allow_mode: true`, treat the record as mode-compliant and do not emit `mode_too_permissive`.

Cleanup dependencies and capacity are evaluated after cleanup blocks and retention-group holds. Only records that still have cleanup actions participate. For a remaining action, each `cleanup_after` path that also has a remaining action must be scheduled in an earlier wave. Dependencies pointing to missing records, unknown-class records, retained records, cleanup-blocked records, group-blocked records, dependency-blocked records, or otherwise actionless records are ignored. Cycles among remaining cleanup actions are not scheduled: every action in the strongly connected cycle is suppressed, its report status becomes `dependency_blocked`, `blocked_by` becomes `cycle:<anchor_path>`, and a `dependency_cycle` warning is emitted for each suppressed action. The cycle anchor is the lexicographically smallest path in that cycle.

After cycle suppression, schedule remaining actions into one-based waves. A record can be scheduled in a wave only when all remaining dependency actions have already been scheduled in earlier waves. Within each wave, available records are considered by action, then path, then source path, then source line. The `cleanup_capacity` limit is applied per action per wave; entries that exceed the wave capacity spill to later waves while preserving the same ordering and dependency constraints.

## Evaluation order and suppression rules

Evaluate each kept record in this order:

1. Resolve `class_aliases`. All downstream policy, exception, cleanup-block, output, and warning behavior uses the resolved class.
2. Unknown class check. Unknown classes short-circuit retention, exception, permission, and cleanup-block checks. The record remains in the report as `needs_review`, with `effective_deadline: null`, `exception_id: ""`, `blocked_by: ""`, and no cleanup action.
3. Expired matching exception warnings. These warnings are emitted before choosing an active exception and do not suppress retention or permission checks.
4. Active exception selection and effective deadline computation.
5. Permission comparison unless the chosen active exception has `allow_mode: true`.
6. Status and pending cleanup action selection.
7. Cleanup-block selection for the pending action, if any. Cleanup blocks run after the pending action is known. They suppress the action, set status to `cleanup_blocked`, set `blocked_by` to the chosen `blocker_id`, and emit `cleanup_blocked`. They do not remove earlier warnings such as `mode_too_permissive`.
8. Retention-group hold selection. After every record has a first-pass status and after cleanup blocks have suppressed their own actions, identify protected records with status `exception_retained` or `cleanup_blocked`. Pending cleanup actions for other records in the same non-blank `retention_group` become `group_blocked` and emit `group_blocked`; earlier warnings remain.
9. Cleanup dependency and capacity scheduling. Remaining cleanup actions are first checked for cycles, then assigned one-based `wave` values using dependencies and `cleanup_capacity`. Dependency-cycle suppression happens after group holds and does not remove earlier warnings.

Status selection is deterministic:

- `needs_review`: class is unknown.
- `<delete_action>_due`: `evaluation_time >= effective_deadline`; for example `delete_due`, `archive_due`, or `quarantine_due`.
- `cleanup_blocked`: a due, quarantine, or permission-review action would have been emitted, but the chosen active cleanup block suppresses it.
- `group_blocked`: a due, quarantine, or permission-review action would have been emitted, but another protected record in the same retention group suppresses it.
- `dependency_blocked`: a remaining cleanup action is part of a cleanup dependency cycle and is suppressed before wave scheduling.
- `quarantine_due`: the class delete action is `quarantine` and the record is mode-too-permissive, even if the retention deadline has not passed.
- `permission_review`: the record is mode-too-permissive, not already due, and not suppressed by an exception.
- `exception_retained`: an active exception is chosen, the effective deadline is later than the base deadline, and no higher-priority status applied.
- `retained`: no higher-priority status applied.

Cleanup action selection follows the chosen status. Due statuses create `delete`, `archive`, or `quarantine` actions. `permission_review` creates a `chmod` action. `exception_retained`, `retained`, and `needs_review` create no action. If a record is both expired and mode-too-permissive, create the retention action only and include both reason codes in the documented order. If a cleanup block, retention-group hold, or dependency cycle applies to that pending action, emit no cleanup action at all and keep the original reason codes only implicit in the warnings and report status. Remaining actions are assigned cleanup waves after dependency cycles are removed; an action is ready for a wave only after every retained dependency action in `cleanup_after` has an earlier wave. For each wave, ready actions are considered by the cleanup-plan sort order. An action may be placed in the wave only if both its `cleanup_capacity` count limit and `cleanup_byte_capacity` sum limit for that action would still be satisfied.

Example: a cache file under an expired exception prefix still emits `expired_exception`, uses the normal cache deadline, and may create `delete` with `reason_codes: ["retention_expired", "mode_too_permissive"]`. A file under an active `allow_mode: true` exception can be `exception_retained` without a mode warning even if its raw mode exceeds the policy maximum. A file whose raw class is `customer_export_legacy` resolves through `class_aliases` to `customer_export`; if it is due for `delete` under an active cleanup block that applies to `delete`, it remains in `retention_report.json` as `cleanup_blocked`, has `blocked_by` set to the chosen block id, emits `cleanup_blocked`, and has no row in `cleanup_plan.json`. If `/case/hold.txt` is `exception_retained` in retention group `case-7`, and `/case/stale.txt` in the same group would otherwise emit `archive`, `/case/stale.txt` becomes `group_blocked`, has `blocked_by: "group:case-7:/case/hold.txt"`, emits `group_blocked`, and has no cleanup action. If `/case/a.log` has `cleanup_after: ["/case/b.log"]` and `/case/b.log` has `cleanup_after: ["/case/a.log"]`, both actions become `dependency_blocked`, both use `blocked_by: "cycle:/case/a.log"`, and no cleanup action is emitted for either file. If `cleanup_capacity.archive` is `1`, two ready archive actions are split across two waves by the cleanup action sort order. If `cleanup_byte_capacity.archive` is `100`, ready archive actions with sizes `70`, `50`, and `20` schedule as `70 + 20` in wave 1 and `50` in wave 2, because `70 + 50` would exceed the byte budget even though the count budget might allow two actions.

## Output schemas

All output JSON must be pretty printed with two-space indentation and a trailing newline. Extra top-level files ending in `.json` must be removed on rerun.

### retention_report.json

Top-level fields:

- `generated_at`: config `evaluation_time` normalized to RFC3339 UTC.
- `summary`: object with fields below.
- `records`: array of record objects sorted by `path` lexicographically.

`summary` fields:

- `records_total`: number of kept records in `records`.
- `actions_total`: number of cleanup actions.
- `warnings_total`: number of emitted warnings.
- `records_by_status`: object mapping every status that appears to its count.
- `bytes_by_status`: object mapping every status that appears to the sum of `size_bytes` for records with that status.

Each record object has exactly:

- `path`: normalized path string.
- `class`: resolved canonical class string after `class_aliases`.
- `policy_id`: resolved policy id, or `""` for unknown classes.
- `owner`: selected record owner, or `""`.
- `group`: selected record group, or `""`.
- `mode`: selected record mode string.
- `retention_group`: trimmed selected retention group string, or `""`.
- `size_bytes`: selected non-negative integer size.
- `source_path`: POSIX source manifest path.
- `source_line`: one-based source line.
- `modified_at`: selected timestamp normalized to RFC3339 UTC.
- `age_days`: whole elapsed days from `modified_at` to `evaluation_time`, floored at zero.
- `base_deadline`: RFC3339 UTC deadline for known classes, otherwise `null`.
- `effective_deadline`: RFC3339 UTC effective deadline for known classes, otherwise `null`.
- `exception_id`: chosen active exception id, or `""`.
- `blocked_by`: chosen cleanup block id, or `group:<retention_group>:<protector_path>` when a retention-group hold suppresses a pending cleanup action, otherwise `""`.
- `mode_compliant`: boolean after exception suppression.
- `status`: status string.

### cleanup_plan.json

Top-level fields:

- `generated_at`: config `evaluation_time` normalized to RFC3339 UTC.
- `actions`: array sorted by `wave`, then `action`, then `path`, then `source_path`, then `source_line`.

Each action object has exactly:

- `wave`: one-based cleanup wave assigned after dependency and capacity scheduling.
- `action`: `delete`, `archive`, `quarantine`, or `chmod`.
- `path`: normalized path.
- `policy_id`: resolved policy id.
- `exception_id`: chosen active exception id, or `""`.
- `reason_codes`: array in this order when present: `retention_expired`, then `mode_too_permissive`.
- `due_at`: effective deadline for retention actions; `generated_at` for `chmod` or permission-only `quarantine` actions.
- `source_path`: selected record source path.
- `source_line`: selected record source line.

### warnings.json

Top-level fields:

- `generated_at`: config `evaluation_time` normalized to RFC3339 UTC.
- `warnings`: array sorted by `code`, then `subject_path`, then `source_path`, then `source_line`, then `detail`.

Each warning object has exactly:

- `code`: warning code.
- `severity`: `warning` or `error`.
- `subject_path`: normalized record path when available, otherwise `""`. For `invalid_manifest`, use the normalized `path` value if the `path` field was present and absolute, even when another field failed validation. Use `""` only when the path is missing, blank, non-string, or not absolute.
- `source_path`: POSIX source path.
- `source_line`: one-based line number.
- `detail`: exact detail string.

Warning codes:

| code | severity | when emitted | detail format |
|---|---|---|---|
| `cleanup_blocked` | `warning` | an active cleanup block suppresses a pending cleanup action | `cleanup blocked by <blocker_id> for <path>; action <action>` |
| `dependency_cycle` | `error` | a remaining cleanup action is part of a cleanup dependency cycle | `cleanup dependency cycle <anchor_path> includes <path>` |
| `duplicate_manifest` | `warning` | a valid duplicate record is discarded | `duplicate path <path>; kept <kept_source_path>:<kept_source_line>` |
| `expired_exception` | `warning` | a selected record matches an exception whose end is not after `evaluation_time` | `expired exception <exception_id> ignored for <path>` |
| `group_blocked` | `warning` | a retention-group hold suppresses a pending cleanup action | `group <retention_group> blocked <action> for <path> due to <protector_path>` |
| `invalid_manifest` | `error` | a parsed record fails schema validation | `invalid manifest record: <reason>` |
| `malformed_manifest` | `error` | a non-empty JSONL line is not valid JSON | `malformed JSON at <source_path>:<source_line>` |
| `mode_too_permissive` | `warning` | a known-class record exceeds its effective max mode without `allow_mode` suppression | `mode <mode> exceeds max <max_mode>` |
| `unknown_class` | `error` | a kept record names no known class | `unknown class <class>` |

Validation reasons for `invalid_manifest` are exactly one of: `path must be absolute`, `record_type must be file`, `class is required`, `modified_at is required`, `modified_at must be RFC3339`, `mode must be four octal digits`, or `size_bytes must be non-negative`. Use the first applicable reason in that order.
