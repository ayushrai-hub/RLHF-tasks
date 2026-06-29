# cost_report.json

Written to /app/outputs/cost_report.json as a single JSON object with exactly these keys:

- cost_matrix: object with keys C_FN and C_FP giving the cost of each error type; C_FN is the integer 20 and C_FP is the integer 1
- threshold_sweep: array with one object per evaluated candidate threshold, each carrying threshold (float), total_cost (number), FN, FP, TP and TN (ints) computed on the test set
- chosen_threshold: float, same value as in metrics.json, equal to the threshold with the lowest total_cost in the sweep
- total_cost_at_chosen: number, total test cost at the chosen threshold, where total cost is 20 times the false negatives plus 1 times the false positives
- total_cost_at_0p5: number, total test cost when the threshold is fixed at 0.5
- baseline_cost_predict_all_negative: number, total test cost when every customer is predicted a non-defaulter
- cost_saving_vs_half: number, total_cost_at_0p5 minus total_cost_at_chosen, greater than or equal to 0
