The maintenance team has a half-finished offline risk scorer in /app, and the nightly dispatch report is wrong
Finish the Go CLI so it scores the provided service calls with the shipped model and leaves the final report files in /app/out

Use /app/config/model.json, /app/config/policy.json, /app/data/service_calls.csv, /app/data/sensor_windows.csv, /app/data/asset_history.csv, /app/data/site_capacity.csv, and /app/data/maintenance_labels.csv as the input set
The executable should be run from /app/cmd/fleetrisk or through go run ./cmd/fleetrisk with explicit flags for those paths and --out-dir /app/out

The finished tool must:
- pick the latest sensor window at or before each call's opened_at timestamp, and fail with a non-zero exit containing no sensor window if a call has no usable window
- write fatal input errors to stderr with an ERROR: prefix
- build the feature vector described in /app/docs/model-card.md, including the documented imputation, clipping, trend, and asset-history rules
- apply both model heads, their piecewise-linear calibration knots, and the asset-type blend from /app/config/model.json
- apply the weighted PAVA post_calibration step from /app/docs/model-card.md before using calibrated_risk
- treat any missing feature weight in a model head as zero contribution, not as an input error
- fill top_factor with the calibrated integrated-gradient attribution described in /app/docs/model-card.md
- choose dispatch, inspect, or monitor with the exact global site-and-region capacity optimizer and crew scheduler, including roster, travel, due-time, break, part inventory, and part-transfer rules described in /app/docs/output-contract.md
- write /app/out/scored_calls.csv, /app/out/maintenance_decisions.csv, /app/out/crew_schedule.csv, /app/out/parts_allocation.csv, /app/out/risk_manifest.json, and /app/out/evaluation.json using the schemas in /app/docs/output-contract.md
- sort the decision CSV by highest calibrated_risk first, breaking ties by request_id
- compute precision, recall, f1, brier_score, roc_auc, and average_precision from /app/data/maintenance_labels.csv, with inspect and dispatch both treated as positive maintenance actions
- use the exact evaluation.json field names from /app/docs/output-contract.md, and do not apply CSV rounding to JSON metric values
- calculate roc_auc with the Mann-Whitney rank formula over calibrated_risk, using average ranks for tied scores
- calculate average_precision after sorting by calibrated_risk descending and request_id ascending, averaging precision at each positive label

Keep the task fully offline, and do not change the input CSV or JSON config files
