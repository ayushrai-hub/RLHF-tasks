Output contract

The solution writes three files into /app/output.

The first, predictions.csv, holds the scored 2025 test set. It has exactly three
columns in this order: row_id, pred_label, pred_proba_positive. Every one of the
410 rows in /app/data/test.csv appears exactly once, and the file is sorted by
row_id. pred_label is the integer 0 or 1. pred_proba_positive is the predicted
probability of the positive class; it must be finite and lie between 0 and 1
inclusive.

The second, validation_predictions.csv, holds predictions for the validation set
using the same three columns in the same order. It covers all 260 rows of
/app/data/validation.csv, once each, sorted by row_id.

To rule out degenerate or copied output, the test-set probabilities must show
genuine spread: after rounding to four decimals there must be at least 40
distinct values, and their standard deviation must be at least 0.07. Predictions
that reproduce the held-out labels too exactly are rejected.

The third, metrics.json, reports exactly the following keys and no others:

  n_train - number of labeled rows used for the final fit
  n_test - number of test rows scored
  primary_metric_value - validation AUROC computed from validation_predictions.csv
  validation_balanced_accuracy - balanced accuracy on validation from the submitted labels
  validation_rare_disease_balanced_accuracy - balanced accuracy on validation rows where rare_disease is 1
  validation_brier - Brier score on the validation set
  predicted_positive_rate - fraction of final test predictions with pred_label of 1
  model_family - short, non-empty description of the model
  missing_value_strategy - short, non-empty description of how missing values were handled
  text_feature_strategy - short, non-empty description of how the trial title text was used
  final_fit_rows - number of labeled rows used for the final fit
  temporal_split_year - the test year, which is 2025

n_train and final_fit_rows both equal the combined row count of the train and
validation files, because the final model is refit on all labeled data before
the test set is scored. n_test is 410 and temporal_split_year is 2025. The
reported validation metrics and predicted_positive_rate are recomputed from the
submitted predictions during grading and must agree within 0.01.

Acceptance targets

The submission is graded on two evaluations.

On the visible validation set the model must reach an AUROC of at least 0.80, a
balanced accuracy of at least 0.69, and a Brier score no higher than 0.14.
Balanced accuracy among the rare-disease validation rows must be at least 0.60.

On the held-out 2025 test set the model must reach an AUROC of at least 0.7700,
a balanced accuracy of at least 0.69, and a Brier score no higher than 0.16.
Positive recall for the small-biotech sponsor subgroup must be at least 0.60,
rare-disease balanced accuracy must be at least 0.61, and the final predicted
positive rate must fall between 0.24 and 0.36. The held-out Brier score must also
beat a baseline that predicts the training prevalence for every row, by a margin
of at least 0.01.
