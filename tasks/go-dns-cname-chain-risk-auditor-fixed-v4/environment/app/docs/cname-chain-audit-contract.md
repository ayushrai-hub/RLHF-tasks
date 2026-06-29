# DNS CNAME Chain Audit Contract

## Command

Run the auditor as:

```bash
/app/bin/audit-cname-chains --config /app/config/audit-policy.json --zones /app/fixtures/zones --services /app/fixtures/service-catalog.json --out /app/out
```

The CLI must create the output directory when missing. On every run it must remove stale files already under the output directory before writing the two documented output files.

## Inputs

### Audit policy JSON

`--config` points to a UTF-8 JSON object with these fields:

- `as_of`: required RFC3339 timestamp. This timestamp is copied to `generated_at` in the report and is the only time reference for retirement checks.
- `max_hops`: required positive integer. Chain expansion stops once this many CNAME edges have been followed if no terminal or loop has been found.
- `service_aliases`: optional object mapping normalized terminal DNS names to service IDs from the service catalog. Missing aliases behave as an empty object.

### Service catalog JSON

`--services` points to a UTF-8 JSON object with a `services` array. Each service row has:

- `service_id`: required non-empty string.
- `domains`: array of DNS names owned by the service. Names are normalized before matching.
- `owner`: optional string. Missing or blank owner is an ownership gap.
- `status`: required string. `active` means active; `retired` means stale. Other status values are treated as active for stale-service checks.
- `retired_at`: optional date string in `YYYY-MM-DD` or RFC3339 format. A non-empty value on or before `as_of` also makes the service stale.

If a normalized terminal name appears in `service_aliases`, use that service ID even if the name also appears in `domains`. Otherwise match the terminal name against normalized `domains`.

### Zone JSONL files

`--zones` points to a directory. Recursively read files ending in `.jsonl`, skipping hidden path segments whose basename starts with `.`. Process files in lexicographic path order. Each physical line is one JSON object.

A parsed CNAME row has:

- `zone`: required string.
- `name`: required string, the CNAME owner name.
- `type`: required string, case-insensitive. Only `CNAME` records participate in chain analysis. Other record types are ignored without warning.
- `target`: required string for CNAME rows.
- `priority`: optional integer. Missing priority defaults to `0`.

DNS names are normalized by trimming whitespace, lowercasing, and removing one or more trailing dots. Source paths in outputs are relative to the `--zones` directory and use `/` separators. Source lines are 1-based physical line numbers.

## Duplicate CNAME records

Duplicate identity is `(normalized zone, normalized name)` for parsed CNAME rows. Keep exactly one winner by applying this ranked order:

1. Higher `priority` wins.
2. If still tied, the lexicographically smallest `source_path` wins.
3. If still tied, the smallest `source_line` wins.

Only the winner participates in chain expansion, findings, and summary counts. Every discarded parsed duplicate emits one `duplicate_cname` warning using the discarded record's `source_path` and `source_line`. The warning detail must be exactly `duplicate CNAME <name>; kept <kept_source_path>:<kept_source_line>`.

## Chain expansion

Create one chain row for every kept CNAME record. Start with that record's normalized `name`, follow its `target`, and continue while the normalized target is itself the `name` of another kept CNAME record. Each followed CNAME edge becomes one hop with `name` and `target` fields.

If the next target repeats a name already seen in the current chain, mark `loop` as `true`, set `terminal` to the repeated normalized name, append the closing hop, and stop expansion. If the chain reaches a target that is not a kept CNAME owner, mark `loop` as `false`, set `terminal` to that normalized target, and stop expansion. If `max_hops` is reached before either condition, stop expansion with the last target as `terminal` and `loop` as `false`.

`chain_id` is the starting normalized CNAME owner name. `hops` must preserve expansion order.

## Evaluation order and suppression rules

Evaluate each kept chain in this order:

1. Expand the CNAME graph and detect loops.
2. Resolve the terminal to a service by `service_aliases` or service domains.
3. Evaluate stale-service status.
4. Evaluate ownership gaps.
5. Add summary counters.

Invalid JSON rows stop at parsing and emit only `invalid_json`. Invalid parsed CNAME rows with missing required fields emit only `invalid_cname` and do not participate in duplicates, chain rows, findings, or summary counters. Non-CNAME records are ignored completely.

Discarded duplicate CNAME rows emit `duplicate_cname` but do not participate in chain rows, findings, or summary counters. Loop chains stop after `loop_detected`; do not resolve services, stale status, or ownership for loop chains. Unknown-service chains emit `ownership_gap` and do not emit `stale_service`. Known services with blank owners still evaluate stale status, so a chain can emit both `stale_service` and `ownership_gap` when both conditions are true.

Example: if `a.example` points to `b.example`, `b.example` points to `a.example`, and `a.example` also matches a service alias, the chain still emits only `loop_detected`; service lookup is suppressed because loop detection happens first.

## Output files

The CLI writes exactly these files under `--out`:

- `cname_chain_report.json`
- `warnings.json`

No stale files from a previous run may remain under `--out`.

## Report schema

`cname_chain_report.json` is a JSON object with exactly these top-level fields:

- `generated_at`: string copied from `config.as_of`.
- `summary`: object.
- `chains`: array of chain objects.
- `findings`: array of finding objects.

`summary` has exactly:

- `chains_total`: integer count of emitted chain rows.
- `findings_total`: integer count of emitted findings.
- `warnings_total`: integer count of warning rows written to `warnings.json`.
- `loops`: integer count of `loop_detected` findings.
- `stale_services`: integer count of `stale_service` findings.
- `ownership_gaps`: integer count of `ownership_gap` findings.
- `max_chain_length`: integer maximum number of hops across emitted chains, or `0` when no chains exist.

Each chain object has exactly:

- `chain_id`: starting normalized CNAME owner name.
- `zone`: normalized zone from the winning record.
- `name`: starting normalized CNAME owner name.
- `target`: normalized target from the winning record.
- `terminal`: normalized terminal target or repeated loop name.
- `service_id`: matched service ID, or `""` when unknown, looped, or not resolved.
- `owner`: matched owner string, or `""` when unknown, blank, looped, or not resolved.
- `status`: matched service status, `unknown` for unknown services, or `loop` for loop chains.
- `loop`: boolean.
- `hops`: array of objects with `name` and `target` strings.
- `source_path`: relative source path of the winning starting record.
- `source_line`: source line of the winning starting record.

Each finding object has exactly:

- `code`: one of `loop_detected`, `ownership_gap`, or `stale_service`.
- `severity`: `critical` for `loop_detected`, `medium` for `ownership_gap`, and `high` for `stale_service`.
- `chain_id`: chain ID.
- `name`: starting normalized CNAME owner name.
- `service_id`: matched service ID, or `""` for loop and unknown-service findings.
- `owner`: matched owner, or `""` when unknown or blank.
- `source_path`: source path of the winning starting record.
- `source_line`: source line of the winning starting record.
- `detail`: exact detail string described in the finding table.

## Warning schema

`warnings.json` is a JSON array. Each warning object has exactly:

- `code`: one of `duplicate_cname`, `invalid_cname`, or `invalid_json`.
- `severity`: `warning` for `duplicate_cname`; `error` for `invalid_cname` and `invalid_json`.
- `subject_id`: normalized CNAME name when known, otherwise `""`.
- `source_path`: relative source path.
- `source_line`: 1-based source line.
- `detail`: exact detail string described in the warning table.

## Finding and warning details

| code | detail format |
|---|---|
| `loop_detected` | `CNAME loop detected: <name1> -> <name2> -> ... -> <repeated_name>` |
| `stale_service` | `terminal <terminal> resolves to stale service <service_id>` |
| `ownership_gap` unknown service | `terminal <terminal> has no catalog owner` |
| `ownership_gap` blank owner | `service <service_id> has no owner` |
| `invalid_json` | `invalid JSON at <source_path>:<source_line>` |
| `invalid_cname` | `invalid CNAME record missing <field>` where `<field>` is the first missing field in this order: `zone`, `name`, `target` |
| `duplicate_cname` | `duplicate CNAME <name>; kept <kept_source_path>:<kept_source_line>` |

## Sorting

Sort `chains` by `chain_id`, then `zone`, then `source_path`, then `source_line`, all ascending.

Sort `findings` by `code`, then `chain_id`, then `source_path`, then `source_line`, then `detail`, all ascending.

Sort warnings in `warnings.json` by `code`, then `subject_id`, then `source_path`, then `source_line`, then `detail`, all ascending.

JSON output must be deterministic and pretty-printed with two-space indentation.

## Null, blank, missing, and zero values

The outputs do not use JSON `null`. Unknown, missing, blank, loop-suppressed, or not-resolved strings serialize as `""` except chain `status`, which is `unknown` for unknown services and `loop` for loop chains. Missing arrays serialize as `[]`. Counts serialize as `0`.
