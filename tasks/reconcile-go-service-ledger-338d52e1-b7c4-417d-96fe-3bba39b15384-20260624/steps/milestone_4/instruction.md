Finish the report comparison feature in the `/app` HTTP API.

Keep all milestone 3 behavior working, then add `POST /v1/reports/compare`. The request body must be JSON with `baseline_report_id`, `candidate_report_id`, and optional `min_abs_delta`, which defaults to 0 when omitted. Look up both report ids from the current server's in-memory report store. Return 400 for malformed JSON, missing report ids, or a negative `min_abs_delta`; return 404 when either report id is not in memory.

The successful response must be JSON with `baseline_report_id`, `candidate_report_id`, `min_abs_delta`, sorted `changes`, and `totals`. Compare the union of `(service, metric)` pairs from both reports. For each pair, use the metric `sum` values and include a change when the metric exists in only one report or when `abs(candidate_sum - baseline_sum) > min_abs_delta`. Omit metrics whose absolute delta is less than or equal to the threshold.

Each change entry must contain `service`, `metric`, `status`, `baseline_count`, `candidate_count`, `baseline_sum`, `candidate_sum`, `delta_sum`, and `percent_change`. When a metric exists on only one side, use `0` for the missing side's count and sum. Sort entries by service name, then metric name. Use these statuses:

- `new_metric` when the pair exists only in the candidate report.
- `removed_metric` when the pair exists only in the baseline report.
- `regressed` when both exist and `candidate_sum - baseline_sum` is greater than `min_abs_delta`.
- `improved` when both exist and `baseline_sum - candidate_sum` is greater than `min_abs_delta`.

Set `percent_change` to `null` when `baseline_sum` is zero; otherwise use `(candidate_sum - baseline_sum) / baseline_sum * 100`. The `totals` object must include `changed_metrics`, `new_metrics`, `removed_metrics`, `regressed_metrics`, and `improved_metrics`.
