suppressPackageStartupMessages({
  library(data.table)
  library(ranger)
  library(jsonlite)
})

SEED <- 42L
DATA <- Sys.getenv("DATA_PATH", "/app/data/tvs_loan.csv")
SPLIT <- Sys.getenv("SPLIT_PATH", "/app/data/split.csv")
OUT <- Sys.getenv("OUTPUT_PATH", "/app/outputs")
TARGET <- "V32"
C_FN <- 20L
C_FP <- 1L
CAT_COLS <- c("V10", "V13", "V14", "V15", "V31")
MNAR_COLS <- c("V21", "V23", "V24", "V26", "V27")

set.seed(SEED)
dir.create(OUT, recursive = TRUE, showWarnings = FALSE)

df <- fread(DATA, data.table = FALSE, showProgress = FALSE)
df$row_id <- seq_len(nrow(df)) - 1L
y <- as.integer(df[[TARGET]])

assign_split <- fread(SPLIT, data.table = FALSE, showProgress = FALSE)
test_id <- assign_split$row_id[assign_split$split == "test"]
train_mask <- !(df$row_id %in% test_id)
test_mask <- df$row_id %in% test_id

feat_cols <- setdiff(names(df), c(TARGET, "row_id", "V1", "V16"))
num_cols <- setdiff(feat_cols, CAT_COLS)

design <- data.frame(row.names = seq_len(nrow(df)))
for (c in num_cols) {
  v <- as.numeric(df[[c]])
  m <- suppressWarnings(median(v[train_mask], na.rm = TRUE))
  if (is.na(m)) m <- 0
  v[is.na(v)] <- m
  design[[c]] <- v
}
for (c in MNAR_COLS) {
  design[[paste0(c, "_missing")]] <- as.integer(is.na(df[[c]]))
}
encode_ordinal <- function(values, levels_map) {
  codes <- match(as.character(values), levels_map)
  codes[is.na(codes)] <- 0L
  as.integer(codes)
}
for (c in CAT_COLS) {
  raw_vals <- as.character(df[[c]])
  if (c == "V15") raw_vals[raw_vals == "OWENED BY OFFICE"] <- "OWNED BY OFFICE"
  raw_vals[is.na(raw_vals)] <- "MISSING"
  lv <- sort(unique(raw_vals[train_mask]))
  design[[c]] <- encode_ordinal(raw_vals, lv)
}

x_train <- design[train_mask, , drop = FALSE]
x_test <- design[test_mask, , drop = FALSE]
y_train <- y[train_mask]
y_test <- y[test_mask]

pos_rate <- mean(y_train)
case_weights <- ifelse(y_train == 1, 1 / pos_rate, 1 / (1 - pos_rate))

train_frame <- x_train
train_frame$.target <- factor(y_train, levels = c(0, 1))
model <- ranger(
  dependent.variable.name = ".target",
  data = train_frame,
  num.trees = 400,
  probability = TRUE,
  importance = "impurity",
  case.weights = case_weights,
  seed = SEED,
  num.threads = 2
)

test_raw <- predict(model, x_test)$predictions[, "1"]
raw_mean <- mean(model$predictions[, "1"], na.rm = TRUE)
test_raw[is.na(test_raw)] <- raw_mean
proba_r <- round(test_raw, 6)

binary_auc <- function(labels, scores) {
  r <- rank(scores, ties.method = "average")
  n1 <- sum(labels == 1)
  n0 <- sum(labels == 0)
  if (n1 == 0 || n0 == 0) return(0.5)
  (sum(r[labels == 1]) - n1 * (n1 + 1) / 2) / (n1 * n0)
}
pr_auc <- function(labels, scores) {
  o <- order(scores, decreasing = TRUE)
  yt <- labels[o]
  tp <- cumsum(yt)
  fp <- cumsum(1 - yt)
  recall <- tp / sum(yt)
  precision <- tp / (tp + fp)
  sum(diff(c(0, recall)) * precision)
}

n_pos <- sum(y_test == 1)
baseline_cost <- C_FN * n_pos

grid <- round(seq(0.01, 0.99, by = 0.01), 6)
sweep <- data.frame(threshold = grid)
fn_v <- fp_v <- tp_v <- tn_v <- cost_v <- integer(length(grid))
for (i in seq_along(grid)) {
  pred <- as.integer(proba_r >= grid[i])
  fn_v[i] <- sum(pred == 0 & y_test == 1)
  fp_v[i] <- sum(pred == 1 & y_test == 0)
  tp_v[i] <- sum(pred == 1 & y_test == 1)
  tn_v[i] <- sum(pred == 0 & y_test == 0)
  cost_v[i] <- C_FN * fn_v[i] + C_FP * fp_v[i]
}
sweep$total_cost <- cost_v
sweep$FN <- fn_v
sweep$FP <- fp_v
sweep$TP <- tp_v
sweep$TN <- tn_v
best_i <- which.min(cost_v)
chosen <- grid[best_i]

pred_label <- as.integer(proba_r >= chosen)
half_label <- as.integer(proba_r >= 0.5)
cost_at_chosen <- C_FN * sum(pred_label == 0 & y_test == 1) + C_FP * sum(pred_label == 1 & y_test == 0)
cost_at_half <- C_FN * sum(half_label == 0 & y_test == 1) + C_FP * sum(half_label == 1 & y_test == 0)

tp_c <- sum(pred_label == 1 & y_test == 1)
recall_default <- if (n_pos > 0) tp_c / n_pos else 0
pred_pos <- sum(pred_label == 1)
precision_default <- if (pred_pos > 0) tp_c / pred_pos else 0

imp <- model$variable.importance
top_design <- names(imp)[which.max(imp)]
top_feature <- sub("_missing$", "", top_design)

preds <- data.frame(
  row_id = as.integer(df$row_id[test_mask]),
  pred_proba = proba_r,
  pred_label = pred_label
)
preds <- preds[order(preds$row_id), ]
fwrite(preds, file.path(OUT, "predictions.csv"))

metrics <- list(
  roc_auc = round(binary_auc(y_test, proba_r), 6),
  pr_auc = round(pr_auc(y_test, proba_r), 6),
  recall_default = round(recall_default, 6),
  precision_default = round(precision_default, 6),
  brier = round(mean((proba_r - y_test)^2), 6),
  accuracy = round(mean(pred_label == y_test), 6),
  n_test = as.integer(sum(test_mask)),
  default_rate_test = round(mean(y_test), 6),
  chosen_threshold = round(chosen, 6),
  top_feature = top_feature
)
write_json(metrics, file.path(OUT, "metrics.json"), auto_unbox = TRUE, pretty = TRUE, digits = 10)

cost_report <- list(
  cost_matrix = list(C_FN = C_FN, C_FP = C_FP),
  threshold_sweep = sweep,
  chosen_threshold = round(chosen, 6),
  total_cost_at_chosen = as.integer(cost_at_chosen),
  total_cost_at_0p5 = as.integer(cost_at_half),
  baseline_cost_predict_all_negative = as.integer(baseline_cost),
  cost_saving_vs_half = as.integer(cost_at_half - cost_at_chosen)
)
write_json(cost_report, file.path(OUT, "cost_report.json"), auto_unbox = TRUE, pretty = TRUE, digits = 10)

cat(sprintf(
  "oracle complete: roc=%.4f pr=%.4f thr=%.2f cost_chosen=%d cost_half=%d baseline=%d\n",
  metrics$roc_auc, metrics$pr_auc, chosen, cost_at_chosen, cost_at_half, baseline_cost
))
