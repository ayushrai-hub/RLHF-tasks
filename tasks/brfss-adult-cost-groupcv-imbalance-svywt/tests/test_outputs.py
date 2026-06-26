import json
import subprocess
from pathlib import Path

import pytest

OUTPUT_PATH = Path("/home/output")
DATA_PATH = Path("/home/data")
EVAL_PATH = Path("/tests/eval/labels.csv")
RESULTS_PATH = Path("/tmp/brfss_check_results.json")

R_TEST_CODE = r"""
suppressPackageStartupMessages({
  library(jsonlite); library(readr); library(dplyr); library(tidyr); library(stringr)
})

DATA_PATH    <- Sys.getenv("DATA_PATH",        "/home/data")
OUTPUT_PATH  <- Sys.getenv("OUTPUT_PATH",      "/home/output")
EVAL_PATH    <- Sys.getenv("EVAL_LABELS_PATH", "/tests/eval/labels.csv")
HELPERS_PATH <- Sys.getenv("HELPERS_PATH",     "/home/helpers")
RESULTS_OUT  <- Sys.getenv("BRFSS_RESULTS_OUT","/tmp/brfss_check_results.json")

source(file.path(HELPERS_PATH, "load_data.R"))
source(file.path(HELPERS_PATH, "metrics.R"))
source(file.path(HELPERS_PATH, "splitters.R"))

agent_metrics     <- fromJSON(file.path(OUTPUT_PATH, "metrics.json"),
                              simplifyVector = TRUE, simplifyDataFrame = FALSE)
agent_predictions <- read_csv(file.path(OUTPUT_PATH, "predictions.csv"),
                              show_col_types = FALSE)
raw_train         <- load_train(DATA_PATH)
raw_test          <- load_test(DATA_PATH)
eval_labels       <- read_csv(EVAL_PATH, show_col_types = FALSE)
codebook          <- load_codebook(DATA_PATH)
state_fips        <- load_state_fips(DATA_PATH)
by_state          <- load_by_state(DATA_PATH)
by_year           <- load_by_year(DATA_PATH)
weights_ref       <- load_weights_table(DATA_PATH)
ageg5yr_codes     <- load_ageg5yr_codes(DATA_PATH)
bmi5cat_codes     <- load_bmi5cat_codes(DATA_PATH)
diabete_codes     <- load_diabete_codes(DATA_PATH)
response_codes    <- load_response_codes(DATA_PATH)
cost_matrix_ref   <- read_csv(file.path(DATA_PATH, "brfss_cost_matrix.csv"), show_col_types = FALSE)
module_rotation   <- read_csv(file.path(DATA_PATH, "brfss_module_rotation.csv"), show_col_types = FALSE)

pass <- function() list(passed = TRUE, message = "")
fail <- function(msg) list(passed = FALSE, message = msg)
`%||%` <- function(a, b) if (is.null(a)) b else a

TOL_PRIMARY      <- 0.04
TOL_PRECISION    <- 0.04
TOL_WEIGHTED     <- 0.005
TOL_AUROC        <- 0.04
TOL_BRIER        <- 0.04
TOL_COST         <- 0.10
COUNT_TOL_REL    <- 0.02

QUALITY_FLOOR              <- 0.66
BASELINE_BEAT_MARGIN_FLOOR <- 0.66
AUROC_FLOOR                <- 0.74
SUBGROUP_MIN_ROWS          <- 50L
SUBGROUP_BA_FLOOR          <- 0.60
SUBGROUP_BA_MEDIAN_FLOOR   <- 0.65
MINORITY_RECALL_FLOOR      <- 0.62
MINORITY_PRECISION_FLOOR   <- 0.18
BRIER_CEIL                 <- 0.225
COST_CEIL                  <- 0.55
SUSPICIOUS_CEIL            <- 0.80

COST_FN_REF      <- 5.0
COST_FP_REF      <- 1.0

REQUIRED_METRIC_KEYS <- c("n_train", "n_test", "primary_metric_value", "balanced_accuracy",
                          "auroc", "brier_score")
REQUIRED_PRED_COLS   <- c("row_id", "pred_label", "pred_proba_positive")

merged <- inner_join(eval_labels, agent_predictions, by = "row_id")
recomputed_primary <- balanced_accuracy(merged$HAVEDIAB, merged$pred_label)
recomputed_recall  <- per_class_recall(merged$HAVEDIAB, merged$pred_label)
recomputed_precision <- per_class_precision(merged$HAVEDIAB, merged$pred_label)
recomputed_cost    <- cost_weighted_loss(merged$HAVEDIAB, merged$pred_label,
                                         cost_fn = COST_FN_REF, cost_fp = COST_FP_REF)
recomputed_auroc   <- auroc(merged$HAVEDIAB, merged$pred_proba_positive)
recomputed_brier   <- brier_score(merged$HAVEDIAB, merged$pred_proba_positive)
merged_with_state  <- merged %>%
  inner_join(raw_test %>% select(row_id, `_STATE`), by = "row_id")
subgroup_ba_holdout <- subgroup_balanced_accuracy(
  merged_with_state$HAVEDIAB,
  merged_with_state$pred_label,
  merged_with_state[["_STATE"]],
  min_rows = SUBGROUP_MIN_ROWS
)

CHECKS <- list(
  schema_predictions_columns_present = function() {
    missing <- setdiff(REQUIRED_PRED_COLS, names(agent_predictions))
    if (length(missing) == 0L) pass()
    else fail(paste("missing cols:", paste(missing, collapse = ",")))
  },
  schema_metrics_keys_present = function() {
    missing <- setdiff(REQUIRED_METRIC_KEYS, names(agent_metrics))
    if (length(missing) == 0L) pass()
    else fail(paste("missing keys:", paste(missing, collapse = ",")))
  },
  schema_metrics_counts_match_data = function() {
    nt <- suppressWarnings(as.integer(agent_metrics[["n_train"]]))
    ns <- suppressWarnings(as.integer(agent_metrics[["n_test"]]))
    if (!is.na(nt) && nt == nrow(raw_train) && !is.na(ns) && ns == nrow(raw_test)) pass()
    else fail(sprintf("reported n_train=%s (training file has %d) n_test=%s (held-out file has %d)",
                      as.character(agent_metrics[["n_train"]]), nrow(raw_train),
                      as.character(agent_metrics[["n_test"]]), nrow(raw_test)))
  },
  schema_pred_label_is_binary = function() {
    bad <- setdiff(unique(agent_predictions$pred_label), c(0L, 1L, 0, 1))
    if (length(bad) == 0L) pass()
    else fail(paste("non-binary pred_label values:", paste(head(bad, 5), collapse = ",")))
  },
  schema_pred_proba_in_unit_interval = function() {
    p <- agent_predictions$pred_proba_positive
    if (all(p >= 0 - 1e-9 & p <= 1 + 1e-9, na.rm = TRUE)) pass()
    else fail(sprintf("pred_proba_positive out of [0,1]: min=%.4f max=%.4f",
                      min(p, na.rm = TRUE), max(p, na.rm = TRUE)))
  },
  schema_predictions_sorted_by_row_id = function() {
    rid <- agent_predictions$row_id
    if (identical(rid, sort(rid))) pass()
    else fail("predictions.csv not sorted by row_id ascending")
  },
  schema_predictions_row_count_matches_n_test = function() {
    if (nrow(agent_predictions) == nrow(raw_test)) pass()
    else fail(sprintf("predictions rows=%d test rows=%d", nrow(agent_predictions), nrow(raw_test)))
  },
  anticheat_predictions_have_variance = function() {
    if (length(unique(agent_predictions$pred_label)) >= 2L &&
        length(unique(round(agent_predictions$pred_proba_positive, 3))) >= 10L) pass()
    else fail("constant-or-near-constant predictions")
  },
  anticheat_no_nan_no_inf = function() {
    bad <- !is.finite(agent_predictions$pred_proba_positive) |
           is.na(agent_predictions$pred_label)
    if (sum(bad) == 0L) pass() else fail(sprintf("%d NaN/inf rows in predictions", sum(bad)))
  },
  anticheat_coverage_matches_eval = function() {
    miss <- setdiff(eval_labels$row_id, agent_predictions$row_id)
    if (length(miss) == 0L) pass()
    else fail(sprintf("missing %d/%d eval row_ids from predictions",
                      length(miss), nrow(eval_labels)))
  },
  anticheat_no_train_rows_in_predictions = function() {
    overlap <- intersect(raw_train$row_id, agent_predictions$row_id)
    if (length(overlap) == 0L) pass()
    else fail(sprintf("%d train row_ids appeared in predictions.csv", length(overlap)))
  },
  anticheat_balanced_accuracy_matches_recomputed = function() {
    delta <- abs(agent_metrics$balanced_accuracy - recomputed_primary)
    if (delta <= TOL_PRIMARY) pass()
    else fail(sprintf("reported BA=%.3f vs recomputed=%.3f delta=%.3f > %.3f",
                      agent_metrics$balanced_accuracy, recomputed_primary, delta, TOL_PRIMARY))
  },
  anticheat_primary_metric_value_equals_balanced_accuracy = function() {
    if (abs(agent_metrics$primary_metric_value - agent_metrics$balanced_accuracy) <= 1e-6) pass()
    else fail("primary_metric_value does not equal balanced_accuracy")
  },
  quality_balanced_accuracy_above_floor = function() {
    if (recomputed_primary >= QUALITY_FLOOR) pass()
    else fail(sprintf("recomputed BA=%.3f below floor %.3f; trivial classifier",
                      recomputed_primary, QUALITY_FLOOR))
  },
  anticheat_balanced_accuracy_not_suspiciously_perfect = function() {
    if (recomputed_primary < SUSPICIOUS_CEIL) pass()
    else fail(sprintf("recomputed BA=%.3f >= ceiling %.3f; likely label leakage",
                      recomputed_primary, SUSPICIOUS_CEIL))
  },
  anticheat_minority_class_recall_floor = function() {
    pos_recall <- recomputed_recall[["1"]]
    if (pos_recall >= MINORITY_RECALL_FLOOR) pass()
    else fail(sprintf("minority-class recall=%.3f below %.2f floor; agent collapsed to majority",
                      pos_recall, MINORITY_RECALL_FLOOR))
  },
  anticheat_per_class_recall_matches_recomputed = function() {
    a_pos <- agent_metrics$per_class_recall[["1"]]
    a_neg <- agent_metrics$per_class_recall[["0"]]
    delta_pos <- abs(a_pos - recomputed_recall[["1"]])
    delta_neg <- abs(a_neg - recomputed_recall[["0"]])
    if (delta_pos <= TOL_PRECISION && delta_neg <= TOL_PRECISION) pass()
    else fail(sprintf("per_class_recall mismatch: pos delta=%.3f neg delta=%.3f tol=%.2f",
                      delta_pos, delta_neg, TOL_PRECISION))
  },
  anticheat_per_class_precision_keys_present = function() {
    pp <- agent_metrics$per_class_precision
    if (!is.null(pp[["0"]]) && !is.null(pp[["1"]])) pass()
    else fail("per_class_precision must report both class 0 and class 1")
  },
  anticheat_per_class_precision_matches_recomputed = function() {
    a_pos <- agent_metrics$per_class_precision[["1"]]
    a_neg <- agent_metrics$per_class_precision[["0"]]
    delta_pos <- abs(as.numeric(a_pos) - recomputed_precision[["1"]])
    delta_neg <- abs(as.numeric(a_neg) - recomputed_precision[["0"]])
    if (!is.finite(delta_pos) || !is.finite(delta_neg)) {
      return(fail("per_class_precision values not finite-numeric"))
    }
    if (delta_pos <= TOL_PRECISION && delta_neg <= TOL_PRECISION) pass()
    else fail(sprintf("per_class_precision mismatch: pos delta=%.3f neg delta=%.3f tol=%.2f",
                      delta_pos, delta_neg, TOL_PRECISION))
  },
  anticheat_cost_weighted_loss_matches_recomputed = function() {
    delta <- abs(agent_metrics$cost_weighted_loss - recomputed_cost)
    if (delta <= TOL_COST) pass()
    else fail(sprintf("cost_weighted_loss reported=%.3f recomputed=%.3f delta=%.3f tol=%.2f",
                      agent_metrics$cost_weighted_loss, recomputed_cost, delta, TOL_COST))
  },
  anticheat_cost_matrix_documented = function() {
    cm <- agent_metrics$cost_matrix
    if (!is.null(cm$cost_false_negative) && !is.null(cm$cost_false_positive) &&
        cm$cost_false_negative > cm$cost_false_positive) pass()
    else fail("cost_matrix must document cost_false_negative > cost_false_positive")
  },
  anticheat_decision_threshold_in_unit_interval = function() {
    t <- agent_metrics$decision_threshold
    if (!is.null(t) && t > 0 && t < 1) pass()
    else fail(sprintf("decision_threshold=%s out of (0,1) range", as.character(t)))
  },
  anticheat_decision_threshold_reflected_in_predictions = function() {
    t <- agent_metrics$decision_threshold
    inferred <- agent_predictions$pred_label == as.integer(agent_predictions$pred_proba_positive >= t)
    if (mean(inferred, na.rm = TRUE) >= 0.95) pass()
    else fail(sprintf("only %.1f%% of predictions consistent with reported threshold %.3f",
                      100 * mean(inferred, na.rm = TRUE), t))
  },
  anticheat_group_field_is_state = function() {
    if (!is.null(agent_metrics$group_field) && agent_metrics$group_field == "_STATE") pass()
    else fail("group_field must equal '_STATE'")
  },
  anticheat_n_overlap_states_is_zero = function() {
    train_states <- sort(unique(raw_train[["_STATE"]]))
    test_states  <- sort(unique(raw_test[["_STATE"]]))
    overlap_true <- length(intersect(train_states, test_states))
    rep <- agent_metrics$n_overlap_states
    if (overlap_true == 0L && (is.null(rep) || rep == 0L)) pass()
    else fail(sprintf("overlap states actual=%d reported=%s", overlap_true,
                      as.character(rep)))
  },
  anticheat_n_states_train_matches_raw = function() {
    expected <- length(unique(raw_train[["_STATE"]]))
    rep <- agent_metrics$n_states_train
    if (!is.null(rep) && rep == expected) pass()
    else fail(sprintf("n_states_train reported=%s expected=%d", as.character(rep), expected))
  },
  anticheat_weighted_prevalence_train_matches_recomputed = function() {
    num <- sum(raw_train$HAVEDIAB * raw_train[["_LLCPWT"]], na.rm = TRUE)
    den <- sum(raw_train[["_LLCPWT"]], na.rm = TRUE)
    expected <- num / den
    rep <- agent_metrics$weighted_prevalence_train
    if (!is.null(rep) && abs(rep - expected) <= TOL_WEIGHTED) pass()
    else fail(sprintf("weighted_prevalence_train reported=%s expected=%.4f",
                      as.character(rep), expected))
  },
  anticheat_weight_psu_strata_fields_named = function() {
    if (identical(agent_metrics$weight_field, "_LLCPWT") &&
        identical(agent_metrics$strata_field, "_STSTR") &&
        identical(agent_metrics$psu_field,    "_PSU")) pass()
    else fail("weight_field / strata_field / psu_field must name BRFSS design columns")
  },
  data_codebook_covers_train_columns = function() {
    expected <- setdiff(names(raw_train), "row_id")
    documented <- codebook$variable
    missing <- setdiff(expected, documented)
    if (length(missing) == 0L) pass()
    else fail(paste("codebook missing variables:", paste(missing, collapse = ",")))
  },
  data_state_fips_covers_observed_states = function() {
    obs <- sort(unique(c(raw_train[["_STATE"]], raw_test[["_STATE"]])))
    listed <- state_fips$state_fips
    missing <- setdiff(obs, listed)
    if (length(missing) == 0L) pass()
    else fail(paste("state_fips ref missing codes:", paste(missing, collapse = ",")))
  },
  data_by_state_train_counts_match_recomputed = function() {
    recomputed <- raw_train %>%
      group_by(`_STATE`) %>%
      summarise(n_rows = n(), .groups = "drop")
    ref <- by_state %>% filter(split == "train") %>% select(`_STATE`, n_rows)
    joined <- inner_join(recomputed, ref, by = "_STATE", suffix = c("_re", "_ref"))
    if (nrow(joined) == nrow(recomputed) &&
        all(joined$n_rows_re == joined$n_rows_ref)) pass()
    else fail("per-state train counts disagree with reference table")
  },
  data_by_year_counts_consistent = function() {
    recomputed <- raw_train %>%
      group_by(year) %>%
      summarise(n_rows = n(), .groups = "drop")
    ref <- by_year %>% filter(split == "train") %>% select(year, n_rows)
    joined <- inner_join(recomputed, ref, by = "year", suffix = c("_re", "_ref"))
    if (nrow(joined) == nrow(recomputed) &&
        all(joined$n_rows_re == joined$n_rows_ref)) pass()
    else fail("per-year train counts disagree with reference table")
  },
  data_weights_table_sums_within_tolerance = function() {
    grouped <- raw_train %>%
      group_by(`_STATE`, year) %>%
      summarise(weight_sum_re = sum(`_LLCPWT`, na.rm = TRUE), .groups = "drop")
    ref <- weights_ref %>% filter(split == "train") %>%
      select(`_STATE`, year, weight_sum)
    joined <- inner_join(grouped, ref, by = c("_STATE", "year"))
    if (nrow(joined) == 0L) return(fail("weights_ref join empty"))
    rel <- abs(joined$weight_sum_re - joined$weight_sum) /
           pmax(joined$weight_sum, 1e-9)
    if (max(rel) <= COUNT_TOL_REL) pass()
    else fail(sprintf("weights table max relative error %.3f > %.3f",
                      max(rel), COUNT_TOL_REL))
  },
  data_ageg5yr_codes_cover_train_values = function() {
    obs <- sort(unique(raw_train[["_AGEG5YR"]]))
    listed <- ageg5yr_codes$code
    missing <- setdiff(obs, listed)
    if (length(missing) == 0L) pass()
    else fail(paste("ageg5yr_codes missing:", paste(missing, collapse = ",")))
  },
  data_bmi5cat_codes_cover_train_values = function() {
    obs <- sort(unique(raw_train[["_BMI5CAT"]][!is.na(raw_train[["_BMI5CAT"]])]))
    listed <- bmi5cat_codes$code
    missing <- setdiff(obs, listed)
    if (length(missing) == 0L) pass()
    else fail(paste("bmi5cat_codes missing:", paste(missing, collapse = ",")))
  },
  data_diabete_codes_present = function() {
    if (all(c(1L, 3L, 4L) %in% diabete_codes$raw_code)) pass()
    else fail("diabete_codes reference missing core 1/3/4 codes")
  },
  data_response_codes_match_codebook = function() {
    fields <- unique(response_codes$field)
    if (length(setdiff(fields, codebook$variable)) == 0L) pass()
    else fail("response_codes references variables not in codebook")
  },
  data_cost_matrix_ref_consistent_with_oracle = function() {
    fn_row <- cost_matrix_ref %>% filter(grepl("False negative", rationale, fixed = TRUE))
    fp_row <- cost_matrix_ref %>% filter(grepl("False positive", rationale, fixed = TRUE))
    if (nrow(fn_row) == 1L && nrow(fp_row) == 1L &&
        fn_row$cost_units > fp_row$cost_units) pass()
    else fail("cost_matrix_ref must encode FN cost > FP cost")
  },
  data_dictionary_json_covers_codebook_variables = function() {
    dict <- fromJSON(file.path(DATA_PATH, "brfss_dictionary.json"),
                     simplifyVector = FALSE, simplifyDataFrame = FALSE)
    missing <- setdiff(codebook$variable, names(dict))
    if (length(missing) == 0L) pass()
    else fail(paste("brfss_dictionary.json missing entries for:",
                    paste(missing, collapse = ",")))
  },
  data_label_dictionary_declares_havediab_target = function() {
    ld <- fromJSON(file.path(DATA_PATH, "brfss_label_dictionary.json"),
                   simplifyVector = TRUE, simplifyDataFrame = FALSE)
    if (identical(ld$target_variable, "HAVEDIAB") &&
        !is.null(ld$label_map) &&
        identical(sort(names(ld$label_map)), c("0", "1"))) pass()
    else fail("brfss_label_dictionary.json must declare target_variable='HAVEDIAB' and a label_map with keys '0','1'")
  },
  data_module_rotation_documents_missing_2022_columns = function() {
    rot22_off <- module_rotation %>%
      filter(asked_2022 == "N") %>% pull(question_variable)
    obs_missing_2022 <- raw_train %>%
      filter(year == 2022) %>%
      summarise(across(everything(), ~ mean(is.na(.)))) %>%
      tidyr::pivot_longer(everything(), names_to = "variable", values_to = "frac_na") %>%
      filter(frac_na > 0.95) %>% pull(variable)
    missing <- setdiff(obs_missing_2022, rot22_off)
    if (length(missing) == 0L) pass()
    else fail(paste("module_rotation does not document all-NA-in-2022 variables:",
                    paste(missing, collapse = ",")))
  },
  quality_balanced_accuracy_beats_majority_baseline = function() {
    if (recomputed_primary >= BASELINE_BEAT_MARGIN_FLOOR) pass()
    else fail(sprintf("BA=%.3f does not beat the majority-class baseline by margin (need >= %.2f)",
                      recomputed_primary, BASELINE_BEAT_MARGIN_FLOOR))
  },
  quality_auroc_above_floor = function() {
    if (!is.na(recomputed_auroc) && recomputed_auroc >= AUROC_FLOOR) pass()
    else fail(sprintf("held-out AUROC=%s below floor %.2f; discrimination too weak",
                      as.character(round(recomputed_auroc, 3L)), AUROC_FLOOR))
  },
  anticheat_auroc_matches_recomputed = function() {
    rep <- agent_metrics$auroc
    if (is.null(rep) || !is.finite(as.numeric(rep))) return(fail("auroc missing or non-numeric"))
    delta <- abs(as.numeric(rep) - recomputed_auroc)
    if (!is.na(delta) && delta <= TOL_AUROC) pass()
    else fail(sprintf("auroc reported=%.3f recomputed=%.3f delta=%.3f tol=%.2f",
                      as.numeric(rep), recomputed_auroc, delta, TOL_AUROC))
  },
  anticheat_brier_score_matches_recomputed = function() {
    rep <- agent_metrics$brier_score
    if (is.null(rep) || !is.finite(as.numeric(rep))) return(fail("brier_score missing or non-numeric"))
    delta <- abs(as.numeric(rep) - recomputed_brier)
    if (!is.na(delta) && delta <= TOL_BRIER) pass()
    else fail(sprintf("brier_score reported=%.3f recomputed=%.3f delta=%.3f tol=%.2f",
                      as.numeric(rep), recomputed_brier, delta, TOL_BRIER))
  },
  quality_subgroup_ba_min_floor = function() {
    if (length(subgroup_ba_holdout) == 0L) {
      return(fail(sprintf("no held-out state has >= %d rows; cannot compute subgroup BA floor",
                          SUBGROUP_MIN_ROWS)))
    }
    vals <- unlist(subgroup_ba_holdout)
    worst <- min(vals)
    worst_state <- names(subgroup_ba_holdout)[which.min(vals)]
    if (worst >= SUBGROUP_BA_FLOOR) pass()
    else fail(sprintf("worst held-out state BA=%.3f (state=%s) below %.2f floor; poor cross-state generalization",
                      worst, worst_state, SUBGROUP_BA_FLOOR))
  },
  quality_subgroup_ba_median_floor = function() {
    if (length(subgroup_ba_holdout) == 0L) {
      return(fail(sprintf("no held-out state has >= %d rows; cannot compute subgroup BA median floor",
                          SUBGROUP_MIN_ROWS)))
    }
    vals <- unlist(subgroup_ba_holdout)
    med <- median(vals)
    if (med >= SUBGROUP_BA_MEDIAN_FLOOR) pass()
    else fail(sprintf("median held-out state BA=%.3f below %.2f floor; consistently weak across states",
                      med, SUBGROUP_BA_MEDIAN_FLOOR))
  },
  quality_brier_below_ceiling = function() {
    if (!is.na(recomputed_brier) && recomputed_brier <= BRIER_CEIL) pass()
    else fail(sprintf("held-out brier=%.3f exceeds %.3f ceiling; probabilities are poorly calibrated",
                      recomputed_brier, BRIER_CEIL))
  },
  quality_cost_weighted_loss_below_ceiling = function() {
    if (!is.na(recomputed_cost) && recomputed_cost <= COST_CEIL) pass()
    else fail(sprintf("held-out cost_weighted_loss=%.3f exceeds %.3f ceiling; threshold not cost-tuned",
                      recomputed_cost, COST_CEIL))
  },
  quality_minority_class_precision_floor = function() {
    p1 <- recomputed_precision[["1"]]
    if (!is.na(p1) && p1 >= MINORITY_PRECISION_FLOOR) pass()
    else fail(sprintf("minority-class precision=%.3f below %.2f floor; predicting positive indiscriminately",
                      p1, MINORITY_PRECISION_FLOOR))
  }
)

results <- list()
n_pass <- 0L; n_fail <- 0L
for (nm in names(CHECKS)) {
  r <- tryCatch(CHECKS[[nm]](),
                error = function(e) list(passed = FALSE, message = conditionMessage(e)))
  passed <- isTRUE(r$passed)
  msg <- if (passed) "" else (r$message %||% "no message")
  results[[nm]] <- list(passed = passed, message = msg)
  status <- if (passed) "PASS" else "FAIL"
  log_msg <- if (passed) "" else paste0(" -- ", msg)
  cat(sprintf("%-60s %s%s\n", nm, status, log_msg))
  if (passed) n_pass <- n_pass + 1L else n_fail <- n_fail + 1L
}
cat(sprintf("\n%d / %d checks passed\n", n_pass, n_pass + n_fail))

writeLines(toJSON(results, auto_unbox = TRUE, pretty = FALSE), RESULTS_OUT)
quit(status = 0L)
"""


def test_environment_train_data_loadable():
    """Verifier sanity: BRFSS adult training file is mounted at /home/data and is non-empty."""
    p = DATA_PATH / "brfss_adult_train.csv"
    assert p.exists(), f"training data missing at {p}"
    assert p.stat().st_size > 0, f"training data empty at {p}"


def test_environment_eval_labels_loadable():
    """Verifier sanity: held out labels file is mounted at /tests/eval and includes the HAVEDIAB column."""
    assert EVAL_PATH.exists(), f"eval labels missing at {EVAL_PATH}"
    assert EVAL_PATH.stat().st_size > 0, f"eval labels empty at {EVAL_PATH}"
    header = EVAL_PATH.open().readline().strip()
    assert "HAVEDIAB" in header, f"eval labels file missing HAVEDIAB column: {header!r}"


def test_predictions_file_has_rows():
    """Layer 0 freebie: the agent produced a predictions.csv with at least one data row."""
    p = OUTPUT_PATH / "predictions.csv"
    assert p.exists(), (
        "predictions.csv was not produced at /home/output/predictions.csv"
    )
    lines = [line for line in p.read_text().splitlines() if line.strip()]
    assert len(lines) >= 2, f"predictions.csv has only {len(lines)} non-blank line(s)"


def test_metrics_has_numeric_primary_metric_value():
    """Layer 0 freebie: metrics.json exists and primary_metric_value parses as a number."""
    p = OUTPUT_PATH / "metrics.json"
    assert p.exists(), "metrics.json was not produced at /home/output/metrics.json"
    m = json.loads(p.read_text())
    v = m.get("primary_metric_value")
    assert isinstance(v, (int, float)) and not isinstance(v, bool), (
        f"primary_metric_value missing or non-numeric: {v!r}"
    )


@pytest.fixture(scope="session")
def r_results():
    """Run the embedded R verifier ONCE per session and parse its JSON results map."""
    script = Path("/tmp/run_r_tests.R")
    script.write_text(R_TEST_CODE)
    if RESULTS_PATH.exists():
        RESULTS_PATH.unlink()
    proc = subprocess.run(
        ["Rscript", "--no-init-file", str(script)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, end="")
    if not RESULTS_PATH.exists():
        pytest.fail(
            f"R verifier did not produce {RESULTS_PATH} (exit={proc.returncode}); "
            "see captured stdout/stderr above for the upstream R error."
        )
    return json.loads(RESULTS_PATH.read_text())


def _assert_r_check(name, r_results):
    result = r_results.get(name)
    assert result is not None, f"R verifier did not report on {name}"
    assert result.get("passed"), f"{name}: {result.get('message', 'no message')}"


def test_r_schema_predictions_columns_present(r_results):
    """Predictions CSV exposes the required row_id, pred_label, and pred_proba_positive columns."""
    _assert_r_check("schema_predictions_columns_present", r_results)


def test_r_schema_metrics_keys_present(r_results):
    """Metrics JSON exposes the universally required top-level keys."""
    _assert_r_check("schema_metrics_keys_present", r_results)


def test_r_schema_metrics_counts_match_data(r_results):
    """Reported n_train and n_test equal the actual training and held-out row counts."""
    _assert_r_check("schema_metrics_counts_match_data", r_results)


def test_r_schema_pred_label_is_binary(r_results):
    """Every pred_label value is exactly 0 or 1."""
    _assert_r_check("schema_pred_label_is_binary", r_results)


def test_r_schema_pred_proba_in_unit_interval(r_results):
    """Every pred_proba_positive value lies in the [0,1] unit interval."""
    _assert_r_check("schema_pred_proba_in_unit_interval", r_results)


def test_r_schema_predictions_sorted_by_row_id(r_results):
    """Predictions CSV is sorted by row_id ascending."""
    _assert_r_check("schema_predictions_sorted_by_row_id", r_results)


def test_r_schema_predictions_row_count_matches_n_test(r_results):
    """Prediction row count equals the held-out test row count."""
    _assert_r_check("schema_predictions_row_count_matches_n_test", r_results)


def test_r_anticheat_predictions_have_variance(r_results):
    """Predictions are not collapsed to a single label or near-constant probability."""
    _assert_r_check("anticheat_predictions_have_variance", r_results)


def test_r_anticheat_no_nan_no_inf(r_results):
    """No NaN, infinity, or NA values appear in the prediction outputs."""
    _assert_r_check("anticheat_no_nan_no_inf", r_results)


def test_r_anticheat_coverage_matches_eval(r_results):
    """Every eval row_id has a prediction; nothing is silently skipped."""
    _assert_r_check("anticheat_coverage_matches_eval", r_results)


def test_r_anticheat_no_train_rows_in_predictions(r_results):
    """No training row_ids leak into the predictions file."""
    _assert_r_check("anticheat_no_train_rows_in_predictions", r_results)


def test_r_anticheat_balanced_accuracy_matches_recomputed(r_results):
    """Reported balanced_accuracy matches what the verifier recomputes."""
    _assert_r_check("anticheat_balanced_accuracy_matches_recomputed", r_results)


def test_r_anticheat_primary_metric_value_equals_balanced_accuracy(r_results):
    """primary_metric_value is set equal to balanced_accuracy as specified."""
    _assert_r_check(
        "anticheat_primary_metric_value_equals_balanced_accuracy", r_results
    )


def test_r_quality_balanced_accuracy_above_floor(r_results):
    """Held-out balanced_accuracy clears the minimum quality floor expected of a real model."""
    _assert_r_check("quality_balanced_accuracy_above_floor", r_results)


def test_r_anticheat_balanced_accuracy_not_suspiciously_perfect(r_results):
    """Held-out balanced_accuracy does not look like label leakage."""
    _assert_r_check("anticheat_balanced_accuracy_not_suspiciously_perfect", r_results)


def test_r_anticheat_minority_class_recall_floor(r_results):
    """Positive-class recall clears the floor; the agent did not collapse to the majority class."""
    _assert_r_check("anticheat_minority_class_recall_floor", r_results)


def test_r_anticheat_per_class_recall_matches_recomputed(r_results):
    """Reported per_class_recall for classes 0 and 1 matches recomputed values."""
    _assert_r_check("anticheat_per_class_recall_matches_recomputed", r_results)


def test_r_anticheat_per_class_precision_keys_present(r_results):
    """Reported per_class_precision contains both class 0 and class 1 entries."""
    _assert_r_check("anticheat_per_class_precision_keys_present", r_results)


def test_r_anticheat_per_class_precision_matches_recomputed(r_results):
    """Reported per_class_precision values match what the verifier recomputes from the held-out predictions."""
    _assert_r_check("anticheat_per_class_precision_matches_recomputed", r_results)


def test_r_anticheat_cost_weighted_loss_matches_recomputed(r_results):
    """Reported cost_weighted_loss matches what the verifier recomputes from the documented cost_matrix."""
    _assert_r_check("anticheat_cost_weighted_loss_matches_recomputed", r_results)


def test_r_anticheat_cost_matrix_documented(r_results):
    """cost_matrix names cost_false_negative and cost_false_positive with FN strictly greater than FP."""
    _assert_r_check("anticheat_cost_matrix_documented", r_results)


def test_r_anticheat_decision_threshold_in_unit_interval(r_results):
    """decision_threshold lies strictly between 0 and 1."""
    _assert_r_check("anticheat_decision_threshold_in_unit_interval", r_results)


def test_r_anticheat_decision_threshold_reflected_in_predictions(r_results):
    """Most pred_label values agree with applying the reported threshold to pred_proba_positive."""
    _assert_r_check("anticheat_decision_threshold_reflected_in_predictions", r_results)


def test_r_anticheat_group_field_is_state(r_results):
    """group_field names the _STATE column used to define the geographic split."""
    _assert_r_check("anticheat_group_field_is_state", r_results)


def test_r_anticheat_n_overlap_states_is_zero(r_results):
    """Train and held-out cohorts share zero overlapping _STATE values, as reported."""
    _assert_r_check("anticheat_n_overlap_states_is_zero", r_results)


def test_r_anticheat_n_states_train_matches_raw(r_results):
    """Reported n_states_train equals the count of distinct _STATE values in the training file."""
    _assert_r_check("anticheat_n_states_train_matches_raw", r_results)


def test_r_anticheat_weighted_prevalence_train_matches_recomputed(r_results):
    """Reported weighted_prevalence_train matches the survey-weighted training prevalence of HAVEDIAB."""
    _assert_r_check("anticheat_weighted_prevalence_train_matches_recomputed", r_results)


def test_r_anticheat_weight_psu_strata_fields_named(r_results):
    """weight_field, strata_field, and psu_field name the canonical BRFSS design columns."""
    _assert_r_check("anticheat_weight_psu_strata_fields_named", r_results)


def test_r_data_codebook_covers_train_columns(r_results):
    """Codebook documents every column present in the training file."""
    _assert_r_check("data_codebook_covers_train_columns", r_results)


def test_r_data_state_fips_covers_observed_states(r_results):
    """state_fips reference covers every state code observed in train and test."""
    _assert_r_check("data_state_fips_covers_observed_states", r_results)


def test_r_data_by_state_train_counts_match_recomputed(r_results):
    """Per-state training row counts in the reference table match the actual training data."""
    _assert_r_check("data_by_state_train_counts_match_recomputed", r_results)


def test_r_data_by_year_counts_consistent(r_results):
    """Per-year training row counts in the reference table match the actual training data."""
    _assert_r_check("data_by_year_counts_consistent", r_results)


def test_r_data_weights_table_sums_within_tolerance(r_results):
    """Survey weight sums per (state, year) match the reference table within tolerance."""
    _assert_r_check("data_weights_table_sums_within_tolerance", r_results)


def test_r_data_ageg5yr_codes_cover_train_values(r_results):
    """_AGEG5YR code reference covers every value observed in the training file."""
    _assert_r_check("data_ageg5yr_codes_cover_train_values", r_results)


def test_r_data_bmi5cat_codes_cover_train_values(r_results):
    """_BMI5CAT code reference covers every non-NA value observed in the training file."""
    _assert_r_check("data_bmi5cat_codes_cover_train_values", r_results)


def test_r_data_diabete_codes_present(r_results):
    """Diabetes raw-code reference includes the core 1, 3, and 4 codes."""
    _assert_r_check("data_diabete_codes_present", r_results)


def test_r_data_response_codes_match_codebook(r_results):
    """Every variable in response_codes appears in the codebook."""
    _assert_r_check("data_response_codes_match_codebook", r_results)


def test_r_data_cost_matrix_ref_consistent_with_oracle(r_results):
    """Reference cost matrix encodes FN cost greater than FP cost."""
    _assert_r_check("data_cost_matrix_ref_consistent_with_oracle", r_results)


def test_r_data_dictionary_json_covers_codebook_variables(r_results):
    """JSON dictionary file documents every variable named in the codebook."""
    _assert_r_check("data_dictionary_json_covers_codebook_variables", r_results)


def test_r_data_label_dictionary_declares_havediab_target(r_results):
    """Label dictionary file declares HAVEDIAB as the target and exposes a 0/1 label map."""
    _assert_r_check("data_label_dictionary_declares_havediab_target", r_results)


def test_r_data_module_rotation_documents_missing_2022_columns(r_results):
    """module_rotation table documents every column that is almost entirely NA in the 2022 training rows."""
    _assert_r_check("data_module_rotation_documents_missing_2022_columns", r_results)


def test_r_quality_balanced_accuracy_beats_majority_baseline(r_results):
    """Held-out balanced_accuracy clears a non-trivial margin over the majority-class baseline."""
    _assert_r_check("quality_balanced_accuracy_beats_majority_baseline", r_results)


def test_r_quality_auroc_above_floor(r_results):
    """Recomputed held-out AUROC clears the discrimination floor."""
    _assert_r_check("quality_auroc_above_floor", r_results)


def test_r_anticheat_auroc_matches_recomputed(r_results):
    """Reported auroc matches what the verifier recomputes from pred_proba_positive."""
    _assert_r_check("anticheat_auroc_matches_recomputed", r_results)


def test_r_anticheat_brier_score_matches_recomputed(r_results):
    """Reported brier_score matches what the verifier recomputes from pred_proba_positive."""
    _assert_r_check("anticheat_brier_score_matches_recomputed", r_results)


def test_r_quality_subgroup_ba_min_floor(r_results):
    """The worst-performing held-out state (with enough rows) still clears the per-state BA floor."""
    _assert_r_check("quality_subgroup_ba_min_floor", r_results)


def test_r_quality_subgroup_ba_median_floor(r_results):
    """The median per-state BA across eligible held-out states clears a stricter floor than the worst one."""
    _assert_r_check("quality_subgroup_ba_median_floor", r_results)


def test_r_quality_brier_below_ceiling(r_results):
    """Held-out Brier score sits below a ceiling, ruling out poorly calibrated probability outputs."""
    _assert_r_check("quality_brier_below_ceiling", r_results)


def test_r_quality_cost_weighted_loss_below_ceiling(r_results):
    """Held-out cost-weighted loss sits below a ceiling, ruling out un-tuned decision thresholds."""
    _assert_r_check("quality_cost_weighted_loss_below_ceiling", r_results)


def test_r_quality_minority_class_precision_floor(r_results):
    """Minority-class precision clears a small floor, ruling out predict-positive-always degenerate models."""
    _assert_r_check("quality_minority_class_precision_floor", r_results)
