# metrics.json

Written to /app/outputs/metrics.json as a single JSON object with exactly these keys:

- roc_auc: float, ROC-AUC on the held-out test set, rounded to 6 decimals
- pr_auc: float, average precision on the held-out test set, rounded to 6 decimals; the value is recomputed from the submitted probabilities, so a trapezoidal precision-recall area is also within tolerance
- recall_default: float, recall for the default class at your chosen threshold, rounded to 6 decimals
- precision_default: float, precision for the default class at your chosen threshold, rounded to 6 decimals
- brier: float, Brier score of the predicted probabilities on the test set, rounded to 6 decimals
- accuracy: float, accuracy at your chosen threshold, rounded to 6 decimals
- n_test: int, number of held-out test rows
- default_rate_test: float, fraction of test rows with V32 == 1, rounded to 6 decimals
- chosen_threshold: float, the single probability threshold that minimizes total cost, rounded to 6 decimals
- top_feature: string, name of the highest-importance input column, must be a column of tvs_loan.csv other than V32
