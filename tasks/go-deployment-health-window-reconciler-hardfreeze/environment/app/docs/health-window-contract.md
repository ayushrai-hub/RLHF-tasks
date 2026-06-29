# Deployment health window reconciliation contract

## Command

Run the reconciler as:

```bash
/app/bin/reconcile-health-windows --config /app/config/health-window-policy.json --input /app/fixtures --out /app/out
```

The `--config`, `--input`, and `--out` flags are required. The program rewrites `health_windows.json` and `reconciliation_warnings.json` in the output directory on every run.

## Input discovery and source metadata

The input directory is scanned recursively for `.jsonl` files. A file is classified by its lowercase basename: names containing `deployment` are deployment feeds, names containing `probe` are probe feeds, names containing `incident` are incident feeds, names containing `rollback` are rollback feeds, and names containing `freeze` are change-freeze policy feeds. Other `.jsonl` files are ignored. Blank lines are ignored.

`source_path` is the POSIX-style path relative to the `--input` directory, without a leading slash. `source_line` is the one-based physical line number in that file. These values are used in warnings and duplicate tie-breakers.

## Configuration

The config JSON contains:

- `default_duration_minutes`: integer used when a deployment omits `duration_minutes`.
- `rollback_grace_minutes`: integer grace period after a window end during which applied rollback markers still attach to the window.
- `required_probe_types`: default list of required probe types.
- `environment_aliases`, `probe_type_aliases`, `probe_status_aliases`, `rollback_state_aliases`, and `incident_severity_aliases`: string-to-string alias maps. Canonicalization trims surrounding whitespace, lowercases the raw string, then looks up the alias map. If no alias exists, the lowercased value is used. Change-freeze severity values are canonicalized by trimming and lowercasing; allowed values are `advisory` and `hard`.

## Deployment records

Deployment rows are JSON objects with:

- `deployment_id` string, required and nonblank.
- `service` string, required and nonblank.
- `environment` string, required and nonblank, canonicalized with `environment_aliases`.
- `release_id` string, optional; missing or null serializes as `""`.
- `owner` string, optional; missing or null serializes as `""`.
- `started_at` RFC3339 timestamp, required. Timestamps are normalized to UTC RFC3339 seconds.
- `duration_minutes` positive integer, optional. Missing or null uses `default_duration_minutes`.
- `required_probes` array of strings, optional. Missing, null, or empty uses config `required_probe_types`. Values are canonicalized with `probe_type_aliases`, de-duplicated, and sorted lexicographically in output.
- `priority` integer, optional; missing or null uses `0`.
- `depends_on` array of deployment id strings, optional. Missing, null, or non-array values serialize as `[]`. Blank dependency ids are ignored; remaining ids are de-duplicated and sorted lexicographically in output.

A malformed JSON deployment line emits `malformed_json`. A deployment missing a required field, with a bad timestamp, or with nonpositive `duration_minutes` emits `invalid_deployment` and is not eligible for output. Deployment validation emits only the first failing reason in this order: missing `deployment_id`, missing `service`, missing `environment`, missing `started_at`, invalid `started_at`, then nonpositive `duration_minutes`. Do not join multiple deployment reasons. Missing required deployment fields use the reason text exactly `missing required field <field_name>`; for example, a row with `deployment_id: "dep-invalid"` but no `service` emits detail `invalid deployment dep-invalid: missing required field service`.

## Deployment duplicate resolution

Deployments duplicate when they have the same `deployment_id`. Keep exactly one valid deployment per id. Choose the winner by this ranked order:

1. higher `priority` wins;
2. if still tied, later normalized `started_at` wins;
3. if still tied, lexicographically smaller `source_path` wins;
4. if still tied, smaller `source_line` wins.

Every discarded parsed duplicate emits one `duplicate_deployment` warning whose `subject_id` is the duplicated deployment id and whose `source_path` and `source_line` point to the discarded row. The detail is exactly `duplicate deployment <deployment_id>; kept <kept_source_path>:<kept_source_line>`.

## Probe records

Probe rows are JSON objects with:

- `probe_id` string, required and nonblank.
- `deployment_id` string, required and nonblank.
- `service` string, optional.
- `environment` string, optional, canonicalized when present.
- `probe_type` string, required, canonicalized with `probe_type_aliases`.
- `checked_at` RFC3339 timestamp, required.
- `status` string, required, canonicalized with `probe_status_aliases` and must be `pass` or `fail`.

A malformed JSON probe line emits `malformed_json`. Invalid probe rows emit `invalid_probe` and are ignored. Probe validation emits only the first failing reason in this order: missing `probe_id`, missing `deployment_id`, missing `probe_type`, missing `checked_at`, missing `status`, invalid `checked_at`, then unrecognized canonical `status`. Missing required probe fields use the reason text exactly `missing required field <field_name>`.

A probe whose `deployment_id` does not match a kept deployment emits `unknown_probe_deployment` and is ignored. A probe with a provided `service` or `environment` that does not match the kept deployment emits `probe_service_mismatch` and is ignored. Valid matching probes are counted only when `checked_at` is within the deployment health window, inclusive of both endpoints. `observed_probe_ids` contains all valid matching in-window probes, including failed probes, sorted by `checked_at` then `probe_id`. `failed_probe_ids` contains in-window probes whose canonical status is `fail`, sorted the same way. A required probe type is satisfied only by at least one in-window matching probe with canonical status `pass`. If all candidate probes for a required type were ignored because they referenced unknown deployments or mismatched service/environment, the required type is still missing for the kept deployment.

## Incident records

Incident rows are JSON objects with:

- `incident_id` string, required and nonblank.
- `deployment_id` string, required and nonblank.
- `started_at` RFC3339 timestamp, required.
- `ended_at` RFC3339 timestamp, optional. Missing, null, or blank means the incident is open-ended.
- `severity` string, required, canonicalized with `incident_severity_aliases`.

Malformed JSON emits `malformed_json`. Invalid incident rows emit `invalid_incident`. Incident validation emits only the first failing reason in this order: missing `incident_id`, missing `deployment_id`, missing `started_at`, missing `severity`, invalid `started_at`, invalid `ended_at`, then `ended_at` before `started_at`. Missing required incident fields use the reason text exactly `missing required field <field_name>`. Incidents for unknown deployment ids emit `unknown_incident_deployment` and are ignored. Only canonical severities `critical` and `major` are included in a window. An incident overlaps a health window when `started_at <= window_end` and `ended_at` is missing or `ended_at >= window_start`; overlap boundaries are inclusive. `incident_ids` is sorted by incident `started_at` then `incident_id`.

## Rollback marker records

Rollback rows are JSON objects with:

- `rollback_id` string, required and nonblank.
- `deployment_id` string, required and nonblank.
- `marked_at` RFC3339 timestamp, required.
- `state` string, required, canonicalized with `rollback_state_aliases`.
- `reason` string, optional and not emitted.

Malformed JSON emits `malformed_json`. Invalid rollback rows emit `invalid_rollback`. Rollback validation emits only the first failing reason in this order: missing `rollback_id`, missing `deployment_id`, missing `marked_at`, missing `state`, invalid `marked_at`, then unrecognized canonical `state`. Missing required rollback fields use the reason text exactly `missing required field <field_name>`. Rollback markers for unknown deployment ids emit `unknown_rollback_deployment` and are ignored. Only canonical state `applied` can attach to a window; `pending`, `planned`, `canceled`, and `cancelled` markers are ignored without a warning.

An applied rollback marker is effective for a deployment when `marked_at` is between `window_start` and `window_end + rollback_grace_minutes`, inclusive. If multiple effective applied markers exist for one deployment, choose the earliest `marked_at`, then the lexicographically smallest `rollback_id`. An applied marker after the grace boundary emits `late_rollback` and does not attach. An applied marker before `window_start` is ignored without a warning.

## Change-freeze records

Change-freeze rows are JSON objects with:

- `freeze_id` string, required and nonblank.
- `environment` string, required and nonblank, canonicalized with `environment_aliases`.
- `service` string, optional. Missing, null, or blank applies the freeze to every service in the environment. A nonblank value must match the deployment `service` exactly after trimming; service values are not alias-canonicalized.
- `starts_at` RFC3339 timestamp, required.
- `ends_at` RFC3339 timestamp, required and must be at or after `starts_at`.
- `severity` string, required. After trim/lowercase it must be `advisory` or `hard`.
- `allowed_owners` array of strings, optional. Missing, null, non-array, or empty means no owner is exempt. Values are trimmed, blank values are ignored, and remaining values are de-duplicated and sorted. Owner comparison is exact against the kept deployment `owner` after trimming.

Malformed JSON emits `malformed_json`. Invalid freeze rows emit `invalid_freeze`. Freeze validation emits only the first failing reason in this order: missing `freeze_id`, missing `environment`, missing `starts_at`, missing `ends_at`, missing `severity`, invalid `starts_at`, invalid `ends_at`, `ends_at` before `starts_at`, then unrecognized `severity`. Missing required freeze fields use the reason text exactly `missing required field <field_name>`.

A change freeze applies to a deployment when the canonical environment matches, the service is blank or matches the deployment service, and the freeze interval overlaps the deployment health window using inclusive boundaries: `starts_at <= window_end` and `ends_at >= window_start`. `freeze_window_ids` contains all applicable freezes, including advisory freezes and owner-exempt hard freezes, sorted by `starts_at` then `freeze_id`.

`policy_violation_codes` contains sorted unique codes from applicable hard freezes where the deployment owner is not listed in `allowed_owners`. Emit `hard_freeze_overlap` when the deployment window overlaps such a hard freeze. Emit `rollback_during_freeze` when that same non-exempt hard freeze contains the chosen `rollback_effective_at`, inclusive of the freeze endpoints. Advisory freezes never create policy violation codes.

## Evaluation order and suppression rules

Process records in this order: parse and validate deployments, resolve duplicate deployments, parse and validate probes/incidents/rollbacks/freezes, attach events to kept deployments, compute base window health, apply dependency blocking, apply change-freeze policy, then sort and write outputs. Validation for any single record is short-circuiting: emit at most one `invalid_*` warning for that row, using the first failing validation reason in the record-type order documented in that record section. Do not concatenate several validation reasons with semicolons or commas.

Invalid deployment rows never create windows and stop all downstream evaluation for that row. Discarded duplicate deployments never create windows, but their duplicate warnings still emit. Probe, incident, and rollback rows that reference unknown deployment ids stop after their unknown-deployment warning; do not perform service/environment matching, window overlap, late-rollback, or health-state evaluation for those rows. Invalid freeze rows never apply to windows.

An effective applied rollback marker suppresses the base `failed` or `degraded` health state and sets `base_health_state` to `rolled_back`. It does not hide evidence: `missing_probe_types`, `failed_probe_ids`, and `incident_ids` must still show what was observed. Example: a deployment with a failed synthetic probe and a critical incident, plus an effective applied rollback marker, emits those probe and incident ids but has `base_health_state: "rolled_back"`.

Without an effective rollback, base health state is assigned in this order:

1. `failed` if any `failed_probe_ids` exist or any overlapping included incident has severity `critical`.
2. `degraded` if any `missing_probe_types` exist or any overlapping included incident has severity `major`.
3. `healthy` otherwise.

After base health is assigned, apply dependency blocking. A deployment whose `base_health_state` is `healthy` or `degraded` becomes final `health_state: "blocked"` when at least one direct kept dependency has final `health_state` of `failed`, `rolled_back`, or `blocked`. `blocked_by_deployment_ids` lists only those direct kept dependency ids, sorted lexicographically. Dependency blocking is therefore transitive through final states, but the output row names only the direct dependencies responsible for the block. A deployment whose base state is already `failed` or `rolled_back` keeps that final state and has an empty `blocked_by_deployment_ids` array.

After dependency blocking, apply change-freeze policy. If the current `health_state` is `healthy` or `degraded` and `policy_violation_codes` contains `hard_freeze_overlap`, set final `health_state` to `frozen`. Do not change `failed`, `rolled_back`, or `blocked` states because those are higher-priority operational outcomes. Freeze policy never hides rollback, probe, incident, dependency, or base-health evidence.

Example: if `dep-a` is rolled back, `dep-b` depends on `dep-a`, and `dep-c` depends on `dep-b`, then `dep-b` is blocked by `["dep-a"]` and `dep-c` is blocked by `["dep-b"]`. If `dep-x` and `dep-y` depend on each other, both emit `dependency_cycle` warnings and neither is blocked by that cycle. If a healthy deployment overlaps a non-exempt hard freeze, it becomes `frozen`; if a rolled-back deployment overlaps the same freeze, it stays `rolled_back` but still lists `hard_freeze_overlap` and, when applicable, `rollback_during_freeze`.

## Output files

The output directory contains exactly these JSON report files:

- `health_windows.json`
- `reconciliation_warnings.json`

Before writing reports, delete stale `.json` files directly under the output directory. Do not delete non-JSON files and do not recurse into subdirectories during stale cleanup.

## `health_windows.json` schema

Top-level object fields:

- `generated_by`: exactly `go-deployment-health-window-reconciler`.
- `summary`: object.
- `windows`: array.

`summary` fields:

- `deployments_total`: number of valid kept deployments after duplicate resolution.
- `windows_total`: length of `windows`.
- `healthy_count`, `degraded_count`, `failed_count`, `rolled_back_count`, `blocked_count`, `frozen_count`: counts by final `health_state`.
- `policy_violation_count`: total number of policy violation codes across all windows, counting each code on each window once.
- `warnings_total`: length of the warnings array in `reconciliation_warnings.json`.

Every window object has exactly:

- `deployment_id`, `service`, `environment`, `release_id`, `owner`: strings.
- `window_start`, `window_end`: UTC RFC3339 strings.
- `duration_minutes`: integer.
- `required_probe_types`, `observed_probe_ids`, `missing_probe_types`, `failed_probe_ids`, `incident_ids`, `depends_on`, `blocked_by_deployment_ids`, `freeze_window_ids`, `policy_violation_codes`: arrays of strings.
- `base_health_state`: one of `healthy`, `degraded`, `failed`, or `rolled_back`, assigned before dependency blocking and freeze policy.
- `rollback_marker_id`: string when an effective rollback is attached, otherwise `null`.
- `rollback_effective_at`: UTC RFC3339 string when an effective rollback is attached, otherwise `null`.
- `health_state`: one of `healthy`, `degraded`, `failed`, `rolled_back`, `blocked`, or `frozen`.

Windows are sorted by `environment`, then `service`, then `window_start`, then `deployment_id`, all ascending lexicographically after timestamp normalization.

## `reconciliation_warnings.json` schema

Top-level object fields:

- `generated_by`: exactly `go-deployment-health-window-reconciler`.
- `warnings`: array.

Every warning object has exactly:

- `code`: string.
- `severity`: `warning` or `error`.
- `subject_id`: string. Use `""` when no stable id is available.
- `source_path`: relative POSIX path of the source row.
- `source_line`: one-based integer line number.
- `detail`: string matching the warning table.

Warnings are sorted by `code`, then `subject_id`, then `source_path`, then `source_line`, then `detail`, all ascending.

## Warning table

| code | severity | when emitted | subject_id | detail format |
|---|---|---|---|---|
| `malformed_json` | `error` | a nonblank JSONL row cannot be parsed | `""` | `malformed JSON in <record_type> row` |
| `invalid_deployment` | `error` | a deployment row fails required-field, timestamp, or duration validation | parsed `deployment_id` or `""` | `invalid deployment <deployment_id>: <reason>` where missing required fields use `<reason>` exactly `missing required field <field_name>` and only the first deployment validation reason is emitted |
| `invalid_probe` | `error` | a probe row fails required-field, timestamp, or status validation | parsed `probe_id` or `""` | `invalid probe <probe_id>: <reason>` |
| `invalid_incident` | `error` | an incident row fails required-field, timestamp, or ended-before-start validation | parsed `incident_id` or `""` | `invalid incident <incident_id>: <reason>` |
| `invalid_rollback` | `error` | a rollback row fails required-field, timestamp, or state validation | parsed `rollback_id` or `""` | `invalid rollback <rollback_id>: <reason>` |
| `invalid_freeze` | `error` | a freeze row fails required-field, timestamp, severity, or interval validation | parsed `freeze_id` or `""` | `invalid freeze <freeze_id>: <reason>` |
| `duplicate_deployment` | `warning` | a valid deployment loses duplicate resolution | duplicate deployment id | `duplicate deployment <deployment_id>; kept <kept_source_path>:<kept_source_line>` |
| `unknown_probe_deployment` | `warning` | a valid probe references no kept deployment | `probe_id` | `probe <probe_id> references unknown deployment <deployment_id>` |
| `probe_service_mismatch` | `warning` | a valid probe names a service or environment that differs from the kept deployment | `probe_id` | `probe <probe_id> targets <service>/<environment> but deployment <deployment_id> is <service>/<environment>` |
| `unknown_incident_deployment` | `warning` | a valid incident references no kept deployment | `incident_id` | `incident <incident_id> references unknown deployment <deployment_id>` |
| `unknown_rollback_deployment` | `warning` | a valid rollback marker references no kept deployment | `rollback_id` | `rollback <rollback_id> references unknown deployment <deployment_id>` |
| `late_rollback` | `warning` | an applied rollback marker is after the grace boundary for a kept deployment | `rollback_id` | `rollback <rollback_id> marked after grace window for deployment <deployment_id>` |
| `unknown_dependency` | `warning` | a kept deployment names a dependency id that is not a kept deployment | deployment id | `deployment <deployment_id> depends on unknown deployment <dependency_id>` |
| `dependency_cycle` | `warning` | a kept deployment is part of a dependency cycle | deployment id | `deployment <deployment_id> participates in dependency cycle <comma_separated_sorted_cycle_ids>` |

## Null, blank, and missing values

Missing optional strings serialize as `""`. Missing arrays serialize as `[]` unless a documented default applies. `depends_on`, `blocked_by_deployment_ids`, `freeze_window_ids`, and `policy_violation_codes` always serialize as arrays, never `null`. Missing optional rollback output fields serialize as JSON `null`, not `""`. Counts serialize as `0`. Extra input fields are ignored. Outputs must not contain fields beyond the documented schemas.
