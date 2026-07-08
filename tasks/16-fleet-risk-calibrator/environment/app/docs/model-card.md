# Fleet Model Card

The scorer builds one feature vector for each service call.
Feature and weight names are matched by exact string.
If a model head's weight map does not contain a feature, that feature contributes 0 for that head.
Sparse head weight maps are valid and must not be rejected only because a feature weight is absent.

Sensor matching:

- Use the most recent sensor window for the same asset_id with window_end <= opened_at.
- If no such window exists, stop with a non-zero exit and an error that names the missing window problem.
- For previous-window features, use the immediately previous window for that asset before the matched window.
- If temp_c is blank on the matched or previous window, replace it with an exponentially weighted mean of prior nonblank temperatures for that asset.
- The temperature EWMA uses prior windows only, the configured trend_lookback_hours, and weight 0.5 ** (age_hours / temp_ewma_half_life_hours).
- If the EWMA has no usable prior temperature, use the asset type's impute_temp_c value.

Feature rules:

- temp_over_limit = max(0, effective_temp_c - temp_limit_c) / 10
- vibration_ratio = min(vibration_mm_s / max_vibration_mm_s, 3.0)
- pressure_delta = abs(pressure_kpa - nominal_pressure_kpa) / nominal_pressure_kpa
- current_z = (current_a - current_mean_a) / current_std_a
- runtime_log = ln(1 + runtime_hours) / 10
- urgent_flag = 1 when priority is urgent, otherwise 0
- rework_flag = 1 when notes_code is REWORK, otherwise 0
- tech_hours_scaled = technician_hours / 4
- temp_rise = max(0, matched_effective_temp_c - previous_effective_temp_c) / 10, or 0 when no previous window exists
- repeat_repair_rate = min(corrective events for the same asset in the prior 45 days, 3) / 3
- severity_memory = max severity for corrective or failure events for the same asset in the prior 90 days / 5
- vibration_slope is the positive least-squares slope per day of vibration_mm_s over same-asset windows in trend_lookback_hours, divided by max_vibration_mm_s and capped to 1.5
- history_decay sums severity / 5 * 0.5 ** (age_days / history_half_life_days) for prior corrective or failure events inside history_lookback_days, capped at 2.5 and divided by 2.5
- leak_flag = 1 when notes_code is LEAK, otherwise 0
- heat_flag = 1 when notes_code is HEAT, otherwise 0
- pressure_drift = abs(matched_pressure_kpa - previous_pressure_kpa) / nominal_pressure_kpa, or 0 when no previous window exists

Scoring:

- /app/config/model.json contains multiple heads.
- For each head, logit = intercept + sum(feature_value * weight).
- Missing weights are zero contributions in that head.
- The head raw probability is 1 / (1 + exp(-logit)).
- The head calibrated value is found by linear interpolation between that head's calibration knots.
- Values below the first knot clamp to the first calibrated value.
- Values above the last knot clamp to the last calibrated value.
- raw_score is the asset type blend of head raw probabilities.
- base_calibrated_risk is the asset type blend of head calibrated values.
- downtime_risk is the calibrated value from the downtime head.
- If /app/config/model.json contains post_calibration for the asset type, fit its weighted isotonic calibrator with PAVA.
- For PAVA, sort observations by raw ascending, keeping input order for equal raw values.
- Start one block per observation with mean = label and weight = weight.
- While a previous block mean is greater than the next block mean, merge the two blocks with a weighted-average mean.
- The panel risk for raw_score is the first final block whose rightmost raw is >= raw_score, or the last block mean when raw_score is above every block.
- Clamp panel risk to [0, 1].
- calibrated_risk = (1 - post_calibration.blend_weight) * base_calibrated_risk + post_calibration.blend_weight * panel_risk.
- If there is no post_calibration group for the asset type, calibrated_risk is base_calibrated_risk.
- raw_score and downtime_risk are not changed by post_calibration.

The top_factor field uses calibrated integrated-gradient attribution from an all-zero feature baseline.
This attribution explains the head-calibrated ensemble before the PAVA post_calibration blend.
Use 32 midpoint steps with alpha = (step_index + 0.5) / 32 for step_index 0 through 31.
At each step, scale every feature value by alpha and recompute each head logit.
For one head and feature, the local derivative is calibration_slope(raw) * raw * (1 - raw) * feature_weight.
calibration_slope(raw) is the slope of the interpolation segment that contains raw, and is 0 outside the calibration knot range.
Multiply each head derivative by the asset type blend weight for that head.
The attribution for a feature is feature_value times the average blended derivative across the 32 steps.
Missing feature weights contribute 0 to that feature's attribution in that head.
top_factor is the feature with the largest positive attribution after sorting feature names ascending for ties.
If every attribution is zero or negative, top_factor is none.
