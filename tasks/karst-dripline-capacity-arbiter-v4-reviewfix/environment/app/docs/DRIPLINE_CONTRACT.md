# Karst Dripline System Behavior Notes

## Fast reading map

The auditor is a deterministic offline Go CLI. It loads six files from the input directory, validates observation rows with first-failure short-circuiting, builds valid allocation candidates, sorts candidates by runtime chamber rank and risk, and then runs one stateful allocation pass. Arrays are always `[]`, never `null`. Quarantine rows never consume capacity. Threshold reasons do not reject a row. Source batches can close and materialize transfer-capacity ledgers before later target observations are allocated. Target allocation consumes base capacity first, then materialized transfer ledgers, then capacity-bonus waivers. The digest covers accepted, deferred, quarantine, batch-summary, transfer-summary, and chamber-summary canonical lines.

## Command interface

The dripline command is located at `/app/cmd/dripline` and is run from `/app` as:

```text
go run ./cmd/dripline --input /app/input --output /app/output/dripline_report.json
```

Required flags are `--input <dir>` and `--output <path>`. The default paths are `/app/input` and `/app/output/dripline_report.json`. If the input directory does not exist, exit nonzero, write a stderr message containing exactly the substring `missing input directory`, and do not create the output file. On success, create missing output parent directories, overwrite an existing output file, write the report only to the output file, and do not write normal status text to stdout.

## Input files

All files are read from the input directory.

### `policy.json`

Required object keys:

1. `schema_version`: must be `karst.dripline.policy.v1`.
2. `output_schema_version`: exact string copied to the output `schema_version`; bundled data uses `karst.dripline.audit.v1`.
3. `chamber_rank`: object mapping chamber names to integer ranks. Lower rank sorts earlier. Ranks may be sparse and non-sequential. Missing chambers sort as rank `999999` and then by chamber name.
4. `thresholds`: object with string numeric fields `ec_min`, `ec_max`, `turbidity_max`, `delta_o18_min`, and `delta_o18_max`.

Threshold numeric strings use the signed grammar below. Policy threshold tokens are trusted after parsing; malformed policy files may fail the command with a useful nonzero error.

### `sensors.csv`

Header order is exactly:

```text
sensor_id,chamber,station_id,status,installed_at
```

`status` can be `active`, `maintenance`, or `retired`. Observation validation uses the final row loaded for a sensor if duplicate sensor rows exist; the supplied baseline data avoids duplicate sensor rows.

### `batches.csv`

Header order is exactly:

```text
batch_id,chamber,window_start,window_end,capacity_ml
```

`window_start` and `window_end` are RFC3339 timestamps. The window is half-open: `window_start <= captured_at < window_end`. `capacity_ml` uses the unsigned numeric grammar and is stored in millilitres. Each batch starts with an independent base-capacity ledger.

### `waivers.csv`

Header order is exactly:

```text
waiver_id,batch_id,sensor_id,kind,expires_at,capacity_bonus_ml
```

`kind` is either `maintenance_override` or `capacity_bonus`. `sensor_id` may be a real sensor id or `*`. `expires_at` is RFC3339. A maintenance override is active for an observation when the waiver has the same batch id, the waiver sensor id is either the observation sensor id or `*`, and `expires_at >= captured_at`. A capacity bonus waiver is active under the same matching rule. Capacity bonus ledgers are consumed in waiver id order and only after base plus transfer ledgers are insufficient. Expired or unmatched waivers do not appear in the output.

`capacity_bonus_ml` uses the unsigned numeric grammar. For `maintenance_override`, its value is normally `0` and is ignored.

### `transfers.csv`

Header order is exactly:

```text
transfer_id,source_batch_id,target_batch_id,opens_at,expires_at,max_transfer_ml,efficiency_ppm
```

Transfers are stateful carryover directives. They reserve unused source base capacity when the source batch closes, convert the reserved amount by `efficiency_ppm`, and create a transfer ledger on the target batch. `opens_at` and `expires_at` are RFC3339 timestamps. `max_transfer_ml` uses the unsigned numeric grammar. `efficiency_ppm` is an unsigned integer token with no decimal part, in the inclusive range `0` to `1000000`.

A transfer is active only when `opens_at <= source_batch.window_end <= expires_at`. The source batch closes after its last valid candidate has been processed. If a batch has no valid candidates, it closes before the first later candidate whose `captured_at` is on or after that batch's `window_end`; any still-open batches close at end of report generation in `window_end`, then `batch_id`, order.

For each active transfer in `transfer_id` order, reserve `min(source_remaining_base_ml, max_transfer_ml)` from the source batch's base ledger. The source base ledger is reduced by the reserved amount. The target transfer amount is `floor(reserved_thousandths * efficiency_ppm / 1000000)` in thousandths. If the transferred amount is positive, create a target transfer ledger, set transfer status `materialized`, and add the transferred amount to the source batch `transfer_out_ml` and target batch `transfer_in_ml`. If no positive amount can be transferred, status is `no_source_capacity`. If the source close time is outside the transfer active window, status is `inactive_window`. If the target batch id is unknown, status is `unknown_target_batch`.

### `observations.ndjson`

Each physical line is one JSON object. Physical NDJSON line numbers start at 1, including malformed or rejected lines. The required keys are:

```text
obs_id, sensor_id, batch_id, captured_at, volume_ml, ec_uS_cm, delta_o18, turbidity_ntu, operator
```

Numeric fields are JSON strings, not JSON numbers.

## Numeric lexical grammar

Unsigned numeric fields are `volume_ml`, `ec_uS_cm`, `turbidity_ntu`, `capacity_ml`, `capacity_bonus_ml`, and `max_transfer_ml`. They must match:

```text
^(0|[1-9][0-9]*)(\.[0-9]{1,3})?$
```

Signed numeric fields are `delta_o18` and all policy thresholds. They must match:

```text
^-?(0|[1-9][0-9]*)(\.[0-9]{1,3})?$
```

`efficiency_ppm` must match an unsigned integer token, must not contain a decimal point, and must be between `0` and `1000000` inclusive. Leading `+`, whitespace padding, exponent notation, thousands separators, unit suffixes, empty strings, `.5`, `5.`, and leading zero forms such as `007` are invalid. Unsigned fields also reject any leading `-`. Arithmetic is done in integer thousandths of a millilitre or unit. JSON numeric outputs are normal JSON numbers after rounding; exact lexical spellings such as `55` versus `55.0` are not part of the report format.

## Observation validation and quarantine

Validation stops at the first failing check in this exact order. Each observation line emits at most one quarantine row.

1. Malformed JSON object: code `bad_json`, detail `line:<n>|json`.
2. Missing or blank `obs_id`: code `missing_obs_id`, detail `obs_id missing`.
3. Duplicate `obs_id`, considering earlier non-malformed observation objects even if they were later quarantined: code `duplicate_obs_id`, detail `obs_id:<obs_id>`.
4. Unknown `sensor_id`: code `unknown_sensor`, detail `sensor:<sensor_id>`.
5. Unknown `batch_id`: code `unknown_batch`, detail `batch:<batch_id>`.
6. Sensor chamber differs from batch chamber: code `chamber_mismatch`, detail `sensor:<sensor_chamber>|batch:<batch_chamber>`.
7. `captured_at` missing or not RFC3339: code `bad_timestamp`, detail `captured_at:<raw>`.
8. `captured_at` outside the half-open batch window: code `outside_batch_window`, detail `batch:<batch_id>`.
9. Sensor status is not `active` and no active maintenance override exists: code `sensor_not_active`, detail `sensor:<sensor_id>|status:<status>`.
10. Numeric lexical checks in field order `volume_ml`, `ec_uS_cm`, `delta_o18`, `turbidity_ntu`: code `bad_numeric`, detail `<field>:<raw>`.
11. Parsed `volume_ml` is zero: code `nonpositive_volume`, detail `volume_ml:0`.

Quarantine row object key order is exactly:

```text
record_id, obs_id, code, detail
```

`record_id` is `line:<physical_line_number>`. If an `obs_id` cannot be read from the object, output `obs_id` as an empty string.

## Candidate reason codes and risk

Valid observations become allocation candidates. Begin each candidate with an empty reason-code list.

If a maintenance override was used to allow a non-active sensor, append `maintenance_waived` first.

Then append threshold reason codes in this exact order when they apply:

1. `ec_out_of_range` when `ec_uS_cm < ec_min` or `ec_uS_cm > ec_max`.
2. `turbidity_high` when `turbidity_ntu > turbidity_max`.
3. `isotope_shift` when `delta_o18 < delta_o18_min` or `delta_o18 > delta_o18_max`.

The risk band is based only on the three threshold reasons, not on waiver, transfer, or capacity reasons: `normal` for zero threshold reasons, `watch` for one, and `critical` for two or three.

## Allocation sort order

Sort all valid candidates before capacity allocation by:

1. batch `window_start` ascending;
2. chamber rank from `policy.chamber_rank`, lower first, missing rank as `999999`;
3. chamber name ascending;
4. risk priority `critical`, then `watch`, then `normal`;
5. `captured_at` ascending;
6. `obs_id` ascending.

The top-level `allocation_order` array contains the `obs_id` values in this exact sorted order, including later deferred observations.

## Stateful capacity allocation

Before each candidate is allocated, any no-candidate source batches whose `window_end <= candidate.captured_at` must close and materialize their transfers. A source batch with valid candidates closes immediately after its last sorted candidate has been allocated. Remaining open batches close after all candidates have been processed.

Each batch has independent base capacity from `batches.csv`. Base capacity is consumed first. If the observation fits in remaining base capacity, accept it and set `capacity_source` to `base`.

If the observation does not fit in remaining base capacity, use materialized transfer ledgers for the target batch in `transfer_id` order. Transfer capacity is consumed after base and before bonus waivers. If any transfer capacity is consumed for an accepted observation, append `transfer_capacity` to that observation's reason codes.

If base plus transfer capacity is still insufficient, compute the remaining excess and use applicable active capacity-bonus waivers in waiver id order. If bonus is consumed for an accepted observation, append `capacity_waived` after any `transfer_capacity` reason. The final `capacity_source` is the `+`-joined list of resource types actually consumed in order: `base`, `transfer`, `bonus`.

If base plus transfer plus bonus is still not enough, put the observation in `deferred_observations`, append `capacity_exhausted` to its reason codes, consume nothing for that observation, and leave all remaining base, transfer, and bonus ledgers unchanged.

Accepted row object key order is exactly:

```text
obs_id, sensor_id, batch_id, chamber, captured_at, volume_ml, risk_band, reason_codes, capacity_source, sequence_index
```

Deferred row object key order is exactly:

```text
obs_id, batch_id, chamber, requested_ml, remaining_base_ml, available_transfer_ml, available_bonus_ml, reason_codes, sequence_index
```

`sequence_index` is 1-based allocation-order position after sorting candidates.

## Summary objects

`batch_summary` is sorted by `batch_id`. Each object key order is exactly:

```text
batch_id, chamber, capacity_ml, transfer_in_ml, transfer_out_ml, bonus_granted_ml, base_used_ml, transfer_used_ml, bonus_used_ml, accepted_count, deferred_count, risk_counts
```

`transfer_in_ml` is the transferred amount materialized into the batch. `transfer_out_ml` is the transferred amount emitted from the batch after efficiency, not the reserved source amount. `bonus_granted_ml` is the sum of all capacity-bonus waiver amounts for that batch, even if they expire before any observation uses them. `risk_counts` has key order `normal`, `watch`, `critical` and counts accepted observations only.

`transfer_summary` is sorted by `transfer_id`. Each object key order is exactly:

```text
transfer_id, source_batch_id, target_batch_id, requested_ml, transferred_ml, consumed_ml, status
```

`requested_ml` is `max_transfer_ml`. `transferred_ml` is the post-efficiency transfer amount created on the target batch. `consumed_ml` is how much of that target transfer ledger was used by accepted observations. Status is one of `materialized`, `inactive_window`, `no_source_capacity`, or `unknown_target_batch`.

`chamber_summary` is sorted by chamber rank using the same chamber-rank rule, then chamber name. Include every chamber that appears in `batches.csv`, plus `unknown` if any quarantine row cannot be attributed to a known sensor or batch chamber. Each object key order is exactly:

```text
chamber, accepted_volume_ml, accepted_count, deferred_count, quarantine_count
```

A quarantine row is attributed to the sensor's chamber when its sensor is known, otherwise to the batch chamber when the batch is known, otherwise to `unknown`.

All millilitre and threshold-derived numeric report values are JSON numbers rounded to two decimal places for display. Exact JSON numeric token spelling is not part of this system format.

## Top-level report schema

Top-level object key order is exactly:

```text
schema_version, allocation_order, accepted_observations, deferred_observations, quarantine, batch_summary, transfer_summary, chamber_summary, digest
```

The output `schema_version` field must be exactly the policy `output_schema_version` value. It is independent of the input policy `schema_version`; do not copy `karst.dripline.policy.v1` into the output report.

## Digest canonicalization

Compute SHA-256 over UTF-8 bytes of canonical lines joined by `\n`, with no trailing newline. Use the order in the output arrays. Empty reason-code lists use the literal `-`. Numbers in digest lines use exactly two decimal places.

Accepted line:

```text
A|<obs_id>|<batch_id>|<sensor_id>|<volume_ml_2dp>|<risk_band>|<reason_codes_or_->|<capacity_source>|<sequence_index>
```

Deferred line:

```text
D|<obs_id>|<batch_id>|<requested_ml_2dp>|<remaining_base_ml_2dp>|<available_transfer_ml_2dp>|<available_bonus_ml_2dp>|<reason_codes_or_->|<sequence_index>
```

Quarantine line:

```text
Q|<record_id>|<obs_id>|<code>|<detail>
```

Batch-summary line:

```text
B|<batch_id>|<capacity_ml_2dp>|<transfer_in_ml_2dp>|<transfer_out_ml_2dp>|<bonus_granted_ml_2dp>|<base_used_ml_2dp>|<transfer_used_ml_2dp>|<bonus_used_ml_2dp>|<accepted_count>|<deferred_count>|<normal>/<watch>/<critical>
```

Transfer-summary line:

```text
T|<transfer_id>|<source_batch_id>|<target_batch_id>|<requested_ml_2dp>|<transferred_ml_2dp>|<consumed_ml_2dp>|<status>
```

Chamber-summary line:

```text
C|<chamber>|<accepted_volume_ml_2dp>|<accepted_count>|<deferred_count>|<quarantine_count>
```
