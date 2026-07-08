The analysis reads /app/data/breast-cancer-cost-calibration-leakage.csv and writes eight deliverables under /app/outputs. Floating-point output is rounded to six decimals unless a field is blank for an empty summary cell.

Rows with target populated are historical rows. Rows with blank target values are the evaluation period. Historical rows with event_month < 10 form the training and validation population. The default fitting window is event_month < 8 and the default validation window is 8 <= event_month < 10. If either window has fewer than two target classes after hidden mutation, use a stratified 25% validation split of all historical rows with event_month < 10 and random_state 20260657. n_train is the number of historical rows with event_month < 10.

Model inputs exclude record_id, target, event_month, audit_group, ops_score_a, ops_code_b, and ops_bucket_c. Values -999 and -777 are missing sentinels. Use a calibrated tabular classifier with appropriate preprocessing for mixed numeric and categorical columns. Predictions and validation summaries should come from the same fitted model and selected threshold.

predictions.csv has record_id, probability, prediction for every blank-target evaluation row, sorted by record_id ascending. probability is in [0, 1], and prediction is binary using the selected threshold.

validation_scores.csv has record_id, target, audit_group, probability, prediction for every validation row, sorted by record_id ascending. These probabilities and predictions define the validation metrics, bins, cost curve, bootstrap, and fairness summaries.

metrics.json keys appear in this order: n_train, n_validation, n_test, positive_rate_train, positive_rate_test, roc_auc, pr_auc, brier, ece, balanced_accuracy, f1, precision, recall, specificity, threshold, expected_cost, false_negative_cost, false_positive_cost, primary_metric_value, fairness_demographic_parity_gap, fairness_equal_opportunity_gap. positive_rate_test is the validation target mean. false_negative_cost is 12, false_positive_cost is 1, and primary_metric_value is exactly -expected_cost.

Choose threshold from 0.05, 0.06, ..., 0.95 by minimum validation expected cost. Break ties by higher recall and then lower threshold. cost_curve.csv has threshold, tp, fp, tn, fn, expected_cost, recall, specificity, precision for all ninety one thresholds in ascending order.

calibration_bins.csv has ten rows with bin_id, bin_left, bin_right, count, mean_probability, observed_rate, absolute_error. bin_id is 0 through 9. Bins are [0.0,0.1), ..., [0.8,0.9), [0.9,1.0]. Empty bins keep count 0 and blank mean_probability, observed_rate, and absolute_error.

threshold_bootstrap.csv has replicate, selected_threshold, expected_cost, recall, specificity, precision, n_resampled. Use 200 one-based replicates and numpy default_rng(20260657). Each replicate samples positions from validation_scores.csv after its record_id sort, searches the same threshold grid with the same tie-breaking rule, and sets n_resampled to the validation sample size.

fairness_report.csv has one row per audit_group present in validation, sorted by audit_group, with audit_group, n, observed_positive_rate, predicted_positive_rate, recall, false_positive_rate, mean_probability, demographic_parity_gap, equal_opportunity_gap. demographic_parity_gap is abs(group predicted_positive_rate minus the overall validation predicted positive rate). equal_opportunity_gap is abs(group recall minus the overall validation recall). The metrics.json fairness fields are the maximum per-group gaps.

feature_importance.csv has feature, importance for up to the top 30 model inputs or transformed inputs, sorted by importance descending then feature ascending. Importance values are nonnegative and exclude leakage or post-review fields.

The analysis derives outputs from /app/data and does not read verifier labels, tests, solution files, or reward artifacts. Hidden evaluation labels recompute quality gates from predictions.csv: AUROC at least 0.988, average precision at least 0.998, Brier at most 0.028, expected cost no more than 0.025 above the benchmark, and balanced accuracy at least 0.80.
