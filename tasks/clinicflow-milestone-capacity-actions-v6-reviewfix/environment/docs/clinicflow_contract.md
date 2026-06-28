# Clinicflow milestone contract

This file is the task-facing contract for the Clinicflow CLI. The milestone prompts summarize the requested work; this contract defines the exact observable behavior used by the verifier. Requirements here are normative for `/app/clinicflow`.

The package exposes four commands over time: `python -m clinicflow normalize`, `python -m clinicflow plan`, `python -m clinicflow actions`, and `python -m clinicflow audit`. All commands write UTF-8 JSON, create a missing output parent directory, replace an existing output file, return exit code 0 after writing valid JSON, and must not edit `/app/data/appointments.csv` or `/app/data/service_rules.json` during normal execution.

Do not use network access, current time, random values, pandas, or a database. Output behavior, not a particular implementation technique, is required.


## Milestone 1: normalize

## Task
Extend the existing Python package under `/app/clinicflow` so the command `python -m clinicflow normalize` converts raw clinic appointment requests into a clean JSON file. Work inside the existing modules instead of replacing `/app/data/appointments.csv` or `/app/data/service_rules.json`. The default input is `/app/data/appointments.csv`, the default rules file is `/app/data/service_rules.json`, and the default output is `/app/output/m1_clean.json`. The command also accepts `--input`, `--rules`, and `--output`; the output parent directory is created when it is absent.

## Files to modify
Edit `/app/clinicflow/cli.py` and add helper modules under `/app/clinicflow` if helpful. Keep the CLI command names and default paths exactly as listed. Do not edit files under `/app/data` during normal command execution.

## Inputs
`/app/data/appointments.csv` has the header fields `request_id`, `patient_id`, `service`, `priority`, `age`, `arrival_min`, `needs_transport`, and `site`. `/app/data/service_rules.json` provides `service_weights`, `priority_bonus`, optional `disabled_services`, optional `service_aliases`, optional `site_aliases`, optional `priority_aliases`, optional `site_score_bonus`, optional `patient_flags`, optional `flag_score_bonus`, optional `hold_flags`, and optional `risk_tier_thresholds`. Aliases are applied before validation and output stores canonical service, site, and priority values. A service is known only when the canonical service appears in `service_weights`. Priority values are exactly `P1`, `P2`, and `P3`. `needs_transport` accepts `true` or `false` after trimming and lowercasing. `arrival_min` and `age` are base-10 integers. `patient_flags` maps patient ids to a list of flag strings; non-list flag entries behave as an empty list. `flag_score_bonus` maps flag strings to integer triage additions; invalid bonus values count as `0`. `hold_flags` is the list of flag strings that become appointment hold codes. `risk_tier_thresholds` may override integer thresholds for `urgent` and `watch`; defaults are `urgent >= 45`, `watch >= 30`, otherwise `routine`. The public fixture contains `R-100`, `R-101`, `R-102`, `R-103`, `R-104`, `R-105`, `R-106`, `R-107`, and `R-108`.

## CLI command
Run `python -m clinicflow normalize --input /app/data/appointments.csv --rules /app/data/service_rules.json --output /app/output/m1_clean.json`. Custom paths have the same semantics. The command returns exit code `0` after writing valid JSON.

## Output path
Write UTF-8 JSON to the chosen output path. Generated output paths under `/app/output` are created by the command. The output file is replaced on repeated runs.

## Exact output schema
The top-level JSON object has exactly keys `accepted`, `rejects`, and `meta`. Extra keys are forbidden. `accepted` is a list. Each accepted object has exactly keys `request_id`, `patient_id`, `service`, `priority`, `site`, `arrival_min`, `needs_transport`, `triage_score`, `risk_tier`, and `hold_codes`; extra keys are forbidden. `hold_codes` is always a list of strings. `rejects` is a list. Each reject object has exactly keys `request_id`, `line`, and `issues`; extra keys are forbidden. `meta` is an object with exactly keys `source_count`, `accepted_count`, `rejected_count`, `priority_counts`, `service_counts`, `risk_tier_counts`, and `hold_count`; extra keys are forbidden. `priority_counts` is exactly an object with keys `P1`, `P2`, and `P3`, each an integer count of accepted rows only, including zero values. `risk_tier_counts` is exactly an object with keys `urgent`, `watch`, and `routine`, each an integer count of accepted rows only, including zero values. `hold_count` is the number of accepted rows whose `hold_codes` list is non-empty. `service_counts` contains one key for each canonical service appearing in accepted rows and each value is the accepted-row count for that service.

## Validation and rejection rules
`source_count` equals the number of data rows read from the CSV, excluding the header and including invalid rows. A valid row has nonblank `request_id`, nonblank `patient_id`, a known canonical `service`, priority `P1`, `P2`, or `P3`, parseable non-negative `arrival_min`, parseable `age`, and parseable `needs_transport`. Reject issue labels are exactly `blank`, `negative`, `unknown_service`, `disabled_service`, `duplicate_request`, `invalid_priority`, `non_numeric`, and `malformed`. `line` is the one-based file line number including the header line. A malformed row short-circuits all other validation labels for that row. After alias resolution and normal validation, an otherwise valid row whose `request_id` duplicates an earlier accepted row is rejected with issue `duplicate_request`; only the first valid accepted row for a request id is kept. A rejected row does not reserve its request id. `triage_score` equals canonical service weight plus priority bonus plus `5` when age is at least `65` plus `3` when `needs_transport` is true plus `site_score_bonus[canonical_site]` when present plus the sum of `flag_score_bonus` for each flag listed in `patient_flags[patient_id]`. `hold_codes` is the de-duplicated list of patient flags, in patient flag list order, whose value appears in `hold_flags`. `risk_tier` is derived from final `triage_score` after all bonuses: `urgent` when score is at least the urgent threshold, `watch` when score is at least the watch threshold, otherwise `routine`.

## Defaults and fallbacks
Blank required fields produce `blank`. Negative `arrival_min` produces `negative`. Non-numeric `age`, `arrival_min`, or `needs_transport` produces `non_numeric`. Unknown canonical service produces `unknown_service`. A disabled known canonical service produces `disabled_service`. A repeated request id that already has an accepted row produces `duplicate_request`. Invalid priority produces `invalid_priority`. Missing or malformed optional flag/risk configuration never rejects a row; it falls back to empty flags, zero flag bonuses, no hold codes, and default risk thresholds. When a row has multiple issues, keep issues in this order: `malformed`, `blank`, `non_numeric`, `negative`, `unknown_service`, `disabled_service`, `duplicate_request`, `invalid_priority`.

## Ordering and tie-breakers
Accepted rows are sorted by priority order `P1`, then `P2`, then `P3`; higher `triage_score`; lower `arrival_min`; then lexicographic `request_id`. Reject rows are sorted by ascending `line`, then lexicographic `request_id`. These ordering rules are part of the output contract.

## Cross-milestone dependency
This first checkpoint has no previous output dependency. It only writes `/app/output/m1_clean.json` and leaves later files untouched.

## Non-requirements
Do not use network access, current time, random values, pandas, or a database. No atomic-write implementation technique is required; only the observable JSON behavior above is required.


## Milestone 2: plan

## Task
Extend the same package so `python -m clinicflow plan` reads the clean output from the previous checkpoint and creates a deterministic site-capacity plan. The default clean input is `/app/output/m1_clean.json`, the default rules file is `/app/data/service_rules.json`, and the default output is `/app/output/m2_plan.json`. Preserve the earlier `normalize` command and CLI arguments. The plan command also accepts `--clean`, `--rules`, and `--output`; create the output parent directory when it is absent.

## Files to modify
Edit `/app/clinicflow/cli.py` and helper modules under `/app/clinicflow`. Keep `/app/data/appointments.csv` and `/app/data/service_rules.json` as public input fixtures. Do not replace the clean input file while planning.

## Inputs
`/app/output/m1_clean.json` is the JSON object produced by `normalize`. Use its `accepted` list as the source population. `/app/data/service_rules.json` provides `durations`, `site_capacity`, `site_owner`, optional `site_start_min`, optional `service_buffer_min`, optional `risk_tier_buffer_min`, optional `site_service_duration_overrides`, optional `site_service_blocks`, optional `priority_capacity_reserve`, and optional `owner_capacity_cap`. Duration values are integer visit minutes by service. `service_buffer_min` adds cleanup minutes by service. `risk_tier_buffer_min` adds extra charged minutes by clean-row `risk_tier`; missing or invalid clean `risk_tier` values are treated as `routine`. Optional `site_service_duration_overrides` maps a known site id to service-specific base duration overrides before service/risk buffers are added. `site_capacity` gives maximum scheduled minutes for a site. `owner_capacity_cap` gives a cross-site scheduled-minute ceiling for an owner after site-capacity checks have passed. `site_owner` maps a known site to an owner label. `site_start_min` maps a site to the first visible slot minute. `priority_capacity_reserve` reduces effective capacity only for non-`P1` rows at that site. `site_service_blocks` maps a known site id to services that cannot be scheduled at that site. A site not present in both `site_capacity` and `site_owner` is unknown, even if it appears in the clean file.

## CLI command
Run `python -m clinicflow plan --clean /app/output/m1_clean.json --rules /app/data/service_rules.json --output /app/output/m2_plan.json`. Custom paths have the same semantics. The command returns exit code `0` after writing valid JSON.

## Output path
Write UTF-8 JSON to the chosen output path. Generated output paths under `/app/output` are created by the command. The output file is replaced on repeated runs.

## Exact output schema
The top-level JSON object has exactly keys `scheduled`, `overflow`, and `meta`. Extra keys are forbidden. `scheduled` is a list. Each scheduled object has exactly keys `request_id`, `site_id`, `owner`, `service`, `priority`, `slot_start`, `slot_end`, `overflow`, `risk_tier`, and `hold_codes`; extra keys are forbidden. `overflow` is a list. Each overflow object has exactly keys `request_id`, `site_id`, `owner`, `reason`, `priority`, `duration`, `risk_tier`, and `hold_codes`; extra keys are forbidden. `hold_codes` is always a list. `meta` is an object with exactly keys `source_count`, `scheduled_count`, `overflow_count`, `owner_counts`, `capacity_used`, and `owner_capacity_used`; extra keys are forbidden. `owner_counts` counts every considered accepted row by derived owner, including rows that overflow. `capacity_used` contains integer scheduled charged minutes per configured site, includes `unknown: 0` when any non-empty plan is produced, and excludes overflow rows. `owner_capacity_used` contains scheduled charged minutes by owner for owners that either consumed scheduled minutes or appear in `owner_capacity_cap`; it excludes overflow duration.

## Validation and rejection rules
If the clean input file is absent, malformed JSON, lacks an `accepted` list, or has a non-list `accepted` value, write the empty schema: `scheduled` empty, `overflow` empty, `source_count`, `scheduled_count`, and `overflow_count` all `0`, and `owner_counts`, `capacity_used`, and `owner_capacity_used` as empty objects `{}`. Each accepted item with a known service uses charged minutes equal to service duration or the applicable `site_service_duration_overrides` value plus optional `service_buffer_min` plus optional `risk_tier_buffer_min[risk_tier]`; an item with an unknown service uses duration `0` and reason `unknown_service`. Missing `hold_codes`, non-list `hold_codes`, or invalid `risk_tier` in a synthetic clean artifact fall back to `[]` and `routine`. The boolean field `overflow` in scheduled items is always false. For scheduled rows, `slot_start` equals `site_start_min[site_id]` plus the current scheduled charged minutes used at that site before the item, and `slot_end` equals `slot_start` plus charged minutes. `source_count` equals the number of accepted clean items considered before scheduling, including items that become overflow. `scheduled_count` and `overflow_count` count output list lengths.

## Defaults and fallbacks
Unknown or absent site values use `site_id` equal to `unknown`, `owner` equal to `unassigned`, `capacity_used.unknown` equal to `0` in non-empty plans, and overflow reason `unknown_site`. Unknown-site rows still use charged minutes when the service is known, including service and risk buffers. Unknown service rows use duration `0` and reason `unknown_service`. Plan gating order after duration calculation is: unknown site, unknown service, non-empty `hold_codes` as `manual_hold`, site-service block as `site_service_blocked`, site-capacity overflow as `capacity_exceeded`, owner-cap overflow as `owner_capacity_exceeded`, otherwise scheduled. A `P1` row uses full site capacity; non-`P1` rows use `site_capacity[site] - priority_capacity_reserve[site]`, floored at `0`. Owner-capacity is checked only after the row fits the site-capacity limit. `capacity_used` and `owner_capacity_used` track scheduled charged minutes only and never include `site_start_min` offsets or overflow duration.

## Ordering and tie-breakers
Process clean accepted items in their existing accepted order when consuming site and owner capacity and assigning slot starts; the later output sort must not change which rows consumed capacity first. Scheduled rows are sorted by `site_id` ascending, then `slot_start` ascending, then `request_id` ascending. Overflow rows are sorted by severity order `manual_hold`, `owner_capacity_exceeded`, `capacity_exceeded`, `site_service_blocked`, `unknown_site`, `unknown_service`, then priority order `P1`, `P2`, `P3`, then lexicographic `request_id`. These tie-breakers are public and deterministic.

## Cross-milestone dependency
This checkpoint depends on the previous output `/app/output/m1_clean.json`. Later verification may rerun `normalize` before `plan` to confirm the two commands remain cumulative. Do not remove or rename the earlier command.

## Non-requirements
Do not use network access, current time, random values, pandas, or a database. No atomic-write implementation technique is required; only the observable JSON behavior above is required.


## Milestone 3: actions

## Task
Extend the package so `python -m clinicflow actions` reads the capacity plan and creates a deterministic follow-up action packet for clinic staff. The default plan input is `/app/output/m2_plan.json`, the default rules file is `/app/data/service_rules.json`, and the default output is `/app/output/m3_actions.json`. Preserve the `normalize` and `plan` commands with their earlier CLI argument names and defaults. The actions command accepts `--plan`, `--rules`, and `--output`; create the output parent directory when it is absent.

## Files to modify
Edit `/app/clinicflow/cli.py` and helper modules under `/app/clinicflow`. The public data files remain `/app/data/appointments.csv` and `/app/data/service_rules.json`. Do not edit the plan input during action generation.

## Inputs
`/app/output/m2_plan.json` is the JSON object produced by `plan`. Use both `scheduled` and `overflow` lists. `/app/data/service_rules.json` provides `action_channels`, optional `owner_channel_overrides`, optional `alert_reasons`, and optional `reason_action_overrides`. `action_channels` maps action labels to channel labels. Public action labels are `call_now`, `send_sms`, and `standard_return`. Public channel labels are `phone`, `sms`, `pager`, and `portal`, but channel values coming from `action_channels` or `owner_channel_overrides` are used as-is even when they are a different string. If an action label is absent from `action_channels`, use channel fallback `portal`. `owner_channel_overrides` maps an owner label to action-channel overrides; an owner-specific channel wins over `action_channels` for that owner and action. `alert_reasons` is the list of first reason codes that create alerts; when absent or not a list, use exactly `capacity_exceeded` and `unknown_site`. Optional `reason_action_overrides` maps an overflow reason code to an object with optional `action` and `severity` fields; valid action overrides are `call_now`, `send_sms`, and `standard_return`, and valid severity overrides are `critical`, `warning`, and `info`. Invalid override values are ignored per field, so a valid action override can still apply when the severity override is invalid and vice versa. Plan rows may contain `risk_tier` and `hold_codes` from earlier milestones; missing values fall back to `routine` and `[]`.

## CLI command
Run `python -m clinicflow actions --plan /app/output/m2_plan.json --rules /app/data/service_rules.json --output /app/output/m3_actions.json`. Custom paths have the same semantics. The command returns exit code `0` after writing valid JSON.

## Output path
Write UTF-8 JSON to the chosen output path. Generated output paths under `/app/output` are created by the command. The output file is replaced on repeated runs.

## Exact output schema
The top-level JSON object has exactly keys `actions`, `alerts`, and `meta`. Extra keys are forbidden. `actions` is a list. Each action object has exactly keys `request_id`, `channel`, `action`, `severity`, `owner`, and `reason_codes`; extra keys are forbidden. `alerts` is a list. Each alert object has exactly keys `alert_id`, `severity`, `owner`, `reason`, and `request_ids`; extra keys are forbidden. `meta` is an object with exactly keys `source_count`, `action_counts`, `severity_counts`, and `owner_counts`; extra keys are forbidden. `action_counts` is exactly an object with keys `call_now`, `send_sms`, and `standard_return`, each an integer count including zero values. `severity_counts` is exactly an object with keys `critical`, `warning`, and `info`, each an integer count including zero values. `owner_counts` counts all action rows by owner and includes only owner labels that appear at least once in the action rows. Include `unassigned` only when one or more action rows actually use owner `unassigned`; omit zero-count owners, including `unassigned: 0`.

## Validation and rejection rules
If the plan input file is absent, malformed JSON, has non-list `scheduled`, or has non-list `overflow`, write the empty schema with empty lists and zero counts. `source_count` equals the number of scheduled plus overflow plan records used for actions. A scheduled record with `risk_tier` equal to `urgent` receives action `call_now`, severity `critical`, and reason code `risk_urgent`; this rule runs before the scheduled `P1` rule. A scheduled non-urgent record with priority `P1` receives action `call_now`, severity `warning`, and reason code `priority_P1`. Other scheduled records receive action `standard_return`, severity `info`, and reason code `standard_return`. Overflow records with reason `manual_hold`, `owner_capacity_exceeded`, or `capacity_exceeded` receive action `call_now`, severity `critical`, and their reason as the first reason code. A `manual_hold` action appends each hold code from `hold_codes` after the leading `manual_hold` reason, preserving the list order. Overflow records with reason `unknown_site` or `site_service_blocked` receive action `send_sms`, severity `warning`, and that reason code. Other overflow reasons receive action `standard_return`, severity `info`, and the original reason as the only reason code.

## Defaults and fallbacks
The channel for an action label first checks `owner_channel_overrides[owner][action]` when present, then `action_channels[action]`, then fallback `portal`. Missing owner uses owner fallback `unassigned`. Missing request id uses request id fallback `unknown_request`. Missing overflow reason uses reason code `standard_return`. Missing scheduled `risk_tier` behaves as `routine`; missing or non-list `hold_codes` behaves as an empty list.

## Alert generation rules
Create alerts only from action rows whose first reason code is listed in `alert_reasons`; if `alert_reasons` is absent or not a list, use exactly `capacity_exceeded` and `unknown_site`. The `alert_reasons` list is the sole source of truth: scheduled `risk_urgent`, `priority_P1`, `standard_return`, `manual_hold`, `owner_capacity_exceeded`, `unknown_service`, `site_service_blocked`, or any other reason creates an alert only when that exact reason appears in `alert_reasons`; under the default fallback, only `capacity_exceeded` and `unknown_site` create alerts. Group alert-triggering action rows by exact tuple `(severity, owner, reason)`, where `reason` is the first reason code. Each alert group's `request_ids` list is sorted lexicographically before writing the alert; multiple rows in the same `(severity, owner, reason)` tuple must be collapsed into one alert. Extra hold codes after `manual_hold` do not change the alert grouping key.

## Ordering and tie-breakers
Actions are sorted by severity order `critical`, `warning`, `info`; then owner ascending; then request id ascending. Alerts are sorted by severity order `critical`, `warning`, `info`; then owner ascending; then reason ascending. Alert ids are `A-001`, `A-002`, and so on after sorting. These ordering rules are public and deterministic.

## Cross-milestone dependency
This checkpoint depends on previous outputs `/app/output/m1_clean.json` and `/app/output/m2_plan.json`. Later verification may rerun `normalize`, then `plan`, then `actions` in one cumulative workspace. Keep all earlier commands working, especially `normalize --rules` and `plan --clean`.

## Non-requirements
Do not use network access, current time, random values, pandas, or a database. No atomic-write implementation technique is required; only the observable JSON behavior above is required.


## Milestone 4: audit

## Task
Finish the workflow with `python -m clinicflow audit`. The command reconciles the clean report, capacity plan, and action packet, applies the staff review policy, and writes a deterministic audit file. The default inputs are `/app/output/m1_clean.json`, `/app/output/m2_plan.json`, `/app/output/m3_actions.json`, `/app/data/service_rules.json`, and `/app/data/review_policy.json`; the default output is `/app/output/m4_audit.json`. The command also accepts `--clean`, `--plan`, `--actions`, `--rules`, `--policy`, and `--output`. Preserve all previous commands and their earlier flags.

## Inputs
`audit` consumes the `accepted` rows from the clean report, the `scheduled` and `overflow` rows from the plan, and the `actions` rows from the action packet. Missing or malformed JSON, non-list `accepted`, non-list `scheduled`, non-list `overflow`, or non-list `actions` makes the command write the empty audit schema. `/app/data/review_policy.json` provides `review_minutes_by_action`, `severity_multiplier`, `reason_minutes`, `hold_code_minutes`, `owner_review_cap`, optional `owner_blocked_reasons`, and optional `batch_prefix`. If `batch_prefix` is missing, use the default string `CF`. Invalid numeric policy values behave as `0`, except missing severity multipliers default to `1`; missing owner caps mean no limit for that owner. `owner_blocked_reasons` maps an owner to first reason codes that must be deferred even if capacity exists.

## CLI command
Run `python -m clinicflow audit --clean /app/output/m1_clean.json --plan /app/output/m2_plan.json --actions /app/output/m3_actions.json --rules /app/data/service_rules.json --policy /app/data/review_policy.json --output /app/output/m4_audit.json`. Custom paths have the same semantics. The command writes UTF-8 JSON, creates a missing output parent, replaces an existing output file, and returns exit code `0` after writing valid JSON.

## Exact output schema
The top-level JSON object has exactly keys `review_items`, `owner_summary`, and `meta`. `review_items` is a list. Each review item has exactly keys `request_id`, `owner`, `source`, `action`, `severity`, `first_reason`, `review_minutes`, `review_status`, `review_codes`, and `batch_key`. `source` is exactly `scheduled`, `overflow`, or `missing_plan`. `review_status` is exactly `assigned`, `deferred`, or `invalid`. `review_codes` is always a list of strings. `batch_key` is `-` unless the row is assigned, in which case it is `<batch_prefix>-<owner_token>-<severity>-<first_reason>`, where `owner_token` replaces spaces in the owner with underscores and a missing policy `batch_prefix` uses `CF`. `owner_summary` is an object keyed by owner labels from action rows and by every owner in `owner_review_cap`, including zero-used owners. Each owner summary object has exactly keys `cap`, `minutes_used`, `assigned_count`, `deferred_count`, and `invalid_count`. `cap` is the configured integer cap or `null` when no cap exists. `meta` has exactly keys `source_count`, `assigned_count`, `deferred_count`, `invalid_count`, `severity_counts`, and `digest`. `severity_counts` is exactly an object with keys `critical`, `warning`, and `info`, each counting review items by action severity including zero values.

## Reconciliation rules
For each action row, find the matching plan row by `request_id`, first in `scheduled`, then in `overflow`. If no plan row exists, `source` is `missing_plan`, expected values cannot be derived, and `review_codes` includes `request_not_in_plan`. If a matching plan row exists but the request id is absent from clean `accepted`, include `request_not_in_clean`. Recompute the expected action, severity, reason codes, and channel from the matching plan row using the Milestone 3 rules and the current service rules. Compare the action row against those expected values. Add `owner_mismatch`, `action_mismatch`, `severity_mismatch`, `channel_mismatch`, and `reason_code_mismatch` for each mismatch in exactly that order after any request lookup codes. Invalid rows do not consume review capacity and use `review_minutes` equal to `0`, `review_status` equal to `invalid`, and `batch_key` equal to `-`.

## Stateful review allocation rules
Only rows with no reconciliation codes enter allocation. Compute `review_minutes` as `review_minutes_by_action[action] * severity_multiplier[severity] + reason_minutes[first_reason] + hold_code_minutes * number_of_extra_reason_codes_after_the_first`. Process valid action rows in the final audit order: severity order `critical`, `warning`, `info`; then owner ascending; then request id ascending. For each owner, earlier assigned rows consume review capacity before later rows. If `first_reason` appears in `owner_blocked_reasons[owner]`, the row is `deferred` with `review_codes` exactly `owner_reason_blocked` and consumes no capacity. Otherwise, if assigning the row would exceed `owner_review_cap[owner]`, the row is `deferred` with `review_codes` exactly `review_cap_exceeded` and consumes no capacity. If no cap exists for the owner, the row can be assigned without limit. Assigned rows have empty `review_codes`, consume their review minutes, and receive a batch key.

## Ordering, summaries, and digest
`review_items` are sorted by severity order `critical`, `warning`, `info`; then owner ascending; then request id ascending. `owner_summary` keys are sorted lexicographically. Summary counts are derived from final `review_items`; zero-cap owners from `owner_review_cap` must appear even when they have no action rows. The digest is the first 16 lowercase hex characters of SHA-256 over one canonical line per review item in output order, joined with newlines. Each line is `request_id|owner|source|action|severity|first_reason|review_minutes|review_status|review_codes_csv|batch_key`; `review_codes_csv` is the comma-joined review_codes list, or an empty string when the list is empty. For an empty audit, the digest is the first 16 hex characters of SHA-256 over the empty string.

## Cross-milestone dependency
This checkpoint depends on `/app/output/m1_clean.json`, `/app/output/m2_plan.json`, and `/app/output/m3_actions.json`. Later verification may rerun `normalize`, `plan`, `actions`, then `audit` in one cumulative workspace. Keep all earlier commands working.

## Non-requirements
Do not use network access, current time, random values, pandas, or a database. No atomic-write implementation technique is required; only the observable JSON behavior above is required.
