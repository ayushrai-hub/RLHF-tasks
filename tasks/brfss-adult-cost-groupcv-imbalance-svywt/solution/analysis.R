suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
  library(Matrix)
  library(glmnet)
  library(jsonlite)
})

DATA_PATH    <- Sys.getenv("DATA_PATH",    "/home/data")
OUTPUT_PATH  <- Sys.getenv("OUTPUT_PATH",  "/home/output")
HELPERS_PATH <- Sys.getenv("HELPERS_PATH", "/home/helpers")
SEED <- 23L
set.seed(SEED)
dir.create(OUTPUT_PATH, showWarnings = FALSE, recursive = TRUE)

source(file.path(HELPERS_PATH, "load_data.R"))
source(file.path(HELPERS_PATH, "survey_design.R"))
source(file.path(HELPERS_PATH, "splitters.R"))
source(file.path(HELPERS_PATH, "metrics.R"))

COST_FN <- 5.0
COST_FP <- 1.0
DEFAULT_THRESHOLD <- 0.5

cost_matrix_ref <- read_csv(file.path(DATA_PATH, "brfss_cost_matrix.csv"), show_col_types = FALSE)
module_rotation  <- read_csv(file.path(DATA_PATH, "brfss_module_rotation.csv"), show_col_types = FALSE)
state_fips_ref   <- load_state_fips(DATA_PATH)
ageg5yr_ref      <- load_ageg5yr_codes(DATA_PATH)
bmi5cat_ref      <- load_bmi5cat_codes(DATA_PATH)
diabete_ref      <- load_diabete_codes(DATA_PATH)
response_codes   <- load_response_codes(DATA_PATH)
codebook         <- load_codebook(DATA_PATH)
by_state_ref     <- load_by_state(DATA_PATH)
by_year_ref      <- load_by_year(DATA_PATH)
weights_ref      <- load_weights_table(DATA_PATH)

train_raw <- load_train(DATA_PATH)
test_raw  <- load_test(DATA_PATH)

drop_invalid_responses <- function(df) {
  if ("EDUCA" %in% names(df))    df$EDUCA[df$EDUCA == 9]               <- NA_real_
  if ("INCOME3" %in% names(df))  df$INCOME3[df$INCOME3 %in% c(77, 99)] <- NA_real_
  if ("EMPLOY1" %in% names(df))  df$EMPLOY1[df$EMPLOY1 == 9]           <- NA_real_
  if ("BPHIGH6" %in% names(df))  df$BPHIGH6[df$BPHIGH6 %in% c(7, 9)]   <- NA_real_
  if ("TOLDHI3" %in% names(df))  df$TOLDHI3[df$TOLDHI3 %in% c(7, 9)]   <- NA_real_
  if ("SMOKE100" %in% names(df)) df$SMOKE100[df$SMOKE100 %in% c(7, 9)] <- NA_real_
  if ("_TOTINDA" %in% names(df)) df[["_TOTINDA"]][df[["_TOTINDA"]] == 9] <- NA_real_
  df
}

train_raw <- drop_invalid_responses(train_raw)
test_raw  <- drop_invalid_responses(test_raw)

feature_cols <- c("_AGEG5YR", "SEXVAR", "_RACEPRV", "EDUCA", "INCOME3", "EMPLOY1",
                  "_BMI5CAT", "BPHIGH6", "TOLDHI3", "SMOKE100", "_TOTINDA", "year")

build_design_matrix <- function(df, feature_cols, ref_train = NULL) {
  X <- df[, feature_cols, drop = FALSE]
  for (col in feature_cols) {
    src <- if (is.null(ref_train)) X[[col]] else ref_train[[col]]
    med <- median(src, na.rm = TRUE)
    if (is.na(med)) med <- 0
    X[[col]][is.na(X[[col]])] <- med
  }
  state_dummies <- model.matrix(~ factor(`_STATE`) - 1, data = df)
  cbind(as.matrix(X), state_dummies)
}

X_train <- build_design_matrix(train_raw, feature_cols)
y_train <- as.integer(train_raw$HAVEDIAB)
w_train <- as.numeric(train_raw[["_LLCPWT"]])
w_train <- pmax(w_train, 1e-6)

X_test <- build_design_matrix(test_raw, feature_cols, ref_train = train_raw)
common_cols <- intersect(colnames(X_train), colnames(X_test))
X_train <- X_train[, common_cols, drop = FALSE]
X_test  <- X_test[,  common_cols, drop = FALSE]

prevalence <- mean(y_train)
class_weight_pos <- 1 / max(prevalence, 1e-6)
class_weight_neg <- 1 / max(1 - prevalence, 1e-6)
sample_weight <- ifelse(y_train == 1L, class_weight_pos, class_weight_neg) * w_train
sample_weight <- sample_weight / mean(sample_weight)

folds <- group_state_folds(train_raw, n_folds = 5L, seed = SEED)

val_proba <- rep(NA_real_, nrow(train_raw))
val_truth <- y_train

for (k in seq_along(folds)) {
  fold <- folds[[k]]
  fit_k <- glmnet(X_train[fold$train_idx, , drop = FALSE], y_train[fold$train_idx],
                  family = "binomial", alpha = 0.0, standardize = FALSE,
                  weights = sample_weight[fold$train_idx],
                  lambda = 0.01)
  p_val <- as.numeric(predict(fit_k, newx = X_train[fold$val_idx, , drop = FALSE],
                              s = 0.01, type = "response"))
  val_proba[fold$val_idx] <- p_val
}

threshold_grid <- seq(0.05, 0.55, by = 0.025)
best_threshold <- DEFAULT_THRESHOLD
best_cost <- Inf
for (t in threshold_grid) {
  yhat <- as.integer(val_proba >= t)
  c <- cost_weighted_loss(val_truth, yhat, cost_fn = COST_FN, cost_fp = COST_FP)
  if (!is.na(c) && c < best_cost) { best_cost <- c; best_threshold <- t }
}

fit_full <- glmnet(X_train, y_train, family = "binomial", alpha = 0.0,
                   standardize = FALSE, weights = sample_weight, lambda = 0.01)
test_proba <- as.numeric(predict(fit_full, newx = X_test, s = 0.01, type = "response"))
test_label <- as.integer(test_proba >= best_threshold)

predictions <- data.frame(
  row_id = test_raw$row_id,
  pred_label = test_label,
  pred_proba_positive = round(test_proba, 6L)
)
predictions <- predictions[order(predictions$row_id), ]
write_csv(predictions, file.path(OUTPUT_PATH, "predictions.csv"))

ba_cv  <- balanced_accuracy(val_truth, as.integer(val_proba >= best_threshold))
auc_cv <- auroc(val_truth, val_proba)
brier_cv <- brier_score(val_truth, val_proba)
per_recall_cv    <- per_class_recall(val_truth, as.integer(val_proba >= best_threshold))
per_precision_cv <- per_class_precision(val_truth, as.integer(val_proba >= best_threshold))


train_states <- sort(unique(train_raw[["_STATE"]]))
test_states  <- sort(unique(test_raw[["_STATE"]]))
n_overlap    <- length(intersect(train_states, test_states))

wprev_train <- weighted_prevalence(train_raw, "HAVEDIAB", "_LLCPWT")
wprev_test  <- NA_real_

cost_cv <- cost_weighted_loss(val_truth, as.integer(val_proba >= best_threshold),
                              cost_fn = COST_FN, cost_fp = COST_FP)

metrics <- list(
  n_train = nrow(train_raw),
  n_test  = nrow(test_raw),
  primary_metric_value = round(as.numeric(ba_cv), 6L),
  balanced_accuracy    = round(as.numeric(ba_cv), 6L),
  auroc                = round(as.numeric(auc_cv), 6L),
  brier_score          = round(as.numeric(brier_cv), 6L),
  per_class_recall     = list(`0` = round(per_recall_cv[["0"]], 6L),
                              `1` = round(per_recall_cv[["1"]], 6L)),
  per_class_precision  = list(`0` = round(per_precision_cv[["0"]], 6L),
                              `1` = round(per_precision_cv[["1"]], 6L)),
  cost_weighted_loss   = round(as.numeric(cost_cv), 6L),
  cost_matrix          = list(cost_false_negative = COST_FN,
                              cost_false_positive = COST_FP,
                              cost_true_positive  = 0,
                              cost_true_negative  = 0),
  decision_threshold   = round(best_threshold, 4L),
  group_field          = "_STATE",
  n_states_train       = length(train_states),
  n_states_test        = length(test_states),
  n_overlap_states     = n_overlap,
  weight_field         = "_LLCPWT",
  strata_field         = "_STSTR",
  psu_field            = "_PSU",
  weighted_prevalence_train = round(wprev_train, 6L)
)
write_json(metrics, file.path(OUTPUT_PATH, "metrics.json"), auto_unbox = TRUE, pretty = TRUE)

cat(sprintf("oracle complete: n_test=%d cv_balanced_accuracy=%.4f auroc=%.4f brier=%.4f threshold=%.3f cost=%.4f\n",
            nrow(predictions), ba_cv, auc_cv, brier_cv, best_threshold, cost_cv))
