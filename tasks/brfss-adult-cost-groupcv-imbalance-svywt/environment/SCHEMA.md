# BRFSS task output schema

Full per-key semantics for the two output files. The high level summary lives in the task instruction; this file is the reference for exact contracts, tolerances, and the grading procedure.

## /home/output/predictions.csv

One CSV with three columns. Rows sorted by `row_id` ascending. Every held out `row_id` must appear exactly once.

| column | type | constraint |
|---|---|---|
| `row_id` | string | every held out row_id present exactly once |
| `pred_label` | integer | 0 or 1 |
| `pred_proba_positive` | float | in `[0, 1]` |

`pred_label` values must agree with applying the reported `decision_threshold` to `pred_proba_positive` on the same rows (at least 95 percent agreement is required to clear the consistency check).

## /home/output/metrics.json

Top level JSON object. Required keys:

### Counts

- `n_train` — integer row count of the training file.
- `n_test` — integer row count of the held out file.

### Headline metrics on the held out cohort

You cannot read the held out `HAVEDIAB` column. Report your training side cross validation estimates for the four numeric metrics below; the grading code independently recomputes the true held out values from your `predictions.csv` and compares the two within tolerance.

- `primary_metric_value` — equals `balanced_accuracy`.
- `balanced_accuracy` — float. CV estimate of held out balanced accuracy.
- `auroc` — float. CV estimate of the held out AUROC of `pred_proba_positive` against `HAVEDIAB`.
- `brier_score` — float. CV estimate of the held out mean squared error of `pred_proba_positive` against `HAVEDIAB`.
- `cost_weighted_loss` — float. CV estimate of the per row average loss your model incurred against your `cost_matrix`.

### Per class breakdowns

- `per_class_recall` — nested object with string keys `"0"` and `"1"`, giving recall for the negative and positive class respectively (CV estimates).
- `per_class_precision` — same shape, precision for each class (CV estimates).

### Cost contract

- `cost_matrix` — nested object with exactly two keys `cost_false_negative` and `cost_false_positive`, both floats. The false negative cost must be the larger of the two (screening context).
- `decision_threshold` — float, strictly between 0 and 1. The classifier threshold you applied to `pred_proba_positive` to produce `pred_label`.

### Group + survey design

- `group_field` — literal string `"_STATE"`. Names the column the geographic split groups on.
- `n_states_train` — integer count of distinct `_STATE` values in the training file.
- `n_overlap_states` — integer count of states that appear in both training and held out. Equals zero for this split.
- `weighted_prevalence_train` — float. Survey weighted prevalence of `HAVEDIAB` equal to one in the training file using `_LLCPWT` as the weight.
- `weight_field` — literal string `"_LLCPWT"`.
- `strata_field` — literal string `"_STSTR"`.
- `psu_field` — literal string `"_PSU"`.

## Estimation guidance

Because held out `HAVEDIAB` is not accessible from the agent container, every numeric metric above is reported as a training side cross validation estimate. A typical approach is group K fold by `_STATE` so the validation folds approximate the cross state shift of the actual held out cohort; pure stratified K fold without grouping understates the geographic generalization gap. The grading code does not require an exact match between your CV estimate and the held out truth, it just requires the two to land within a tolerance that comfortably covers honest CV vs held out drift.

## Subgroup expectation

The grading code recomputes balanced accuracy per held out `_STATE` for every state with a non trivial row count. A model that does well on average but collapses on a few states will fail the subgroup check. Survey weighted training and state level features both help close the gap.

## Extra keys

Any additional keys you add to `metrics.json` are fine and will not be inspected. The list above is the minimum required set.
