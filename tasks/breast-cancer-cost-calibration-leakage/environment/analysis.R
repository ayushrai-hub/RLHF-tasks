app_dir <- Sys.getenv("APP_DIR", "/app")
data_path <- file.path(app_dir, "data", "risk_queue.csv")
out_dir <- file.path(app_dir, "outputs")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

id_col <- "record_id"
target_col <- "target"
period_col <- "event_month"
audit_col <- "audit_group"
fn_cost <- 12
fp_cost <- 1
thresholds <- round(seq(0.05, 0.95, by = 0.01), 2)

round6 <- function(x) {
  ifelse(is.na(x) | !is.finite(x), NA_real_, round(as.numeric(x), 6))
}

safe_div <- function(a, b) {
  if (b == 0) 0 else a / b
}

score_at_threshold <- function(y, p, threshold) {
  pred <- as.integer(p >= threshold)
  tp <- sum(y == 1 & pred == 1)
  fp <- sum(y == 0 & pred == 1)
  tn <- sum(y == 0 & pred == 0)
  fn <- sum(y == 1 & pred == 0)
  data.frame(
    threshold = round6(threshold),
    tp = tp,
    fp = fp,
    tn = tn,
    fn = fn,
    expected_cost = round6((fn_cost * fn + fp_cost * fp) / max(1, length(y))),
    recall = round6(safe_div(tp, tp + fn)),
    specificity = round6(safe_div(tn, tn + fp)),
    precision = round6(safe_div(tp, tp + fp))
  )
}

cost_rows <- function(y, p) {
  do.call(rbind, lapply(thresholds, function(t) score_at_threshold(y, p, t)))
}

choose_threshold <- function(y, p) {
  rows <- cost_rows(y, p)
  rows <- rows[order(rows$expected_cost, -rows$recall, rows$threshold), ]
  rows$threshold[1]
}

calibration_rows <- function(y, p) {
  rows <- lapply(0:9, function(i) {
    left <- i / 10
    right <- (i + 1) / 10
    mask <- if (i == 9) p >= left & p <= right else p >= left & p < right
    count <- sum(mask)
    if (count > 0) {
      mp <- mean(p[mask])
      observed <- mean(y[mask])
      err <- abs(mp - observed)
    } else {
      mp <- NA_real_
      observed <- NA_real_
      err <- NA_real_
    }
    data.frame(
      bin_id = i,
      bin_left = round6(left),
      bin_right = round6(right),
      count = count,
      mean_probability = round6(mp),
      observed_rate = round6(observed),
      absolute_error = round6(err)
    )
  })
  do.call(rbind, rows)
}

bootstrap_rows <- function(y, p) {
  n <- length(y)
  rows <- lapply(1:200, function(b) {
    idx <- ((seq_len(n) * (37 * b + 11) + 101 * b) %% n) + 1
    sy <- y[idx]
    sp <- p[idx]
    threshold <- choose_threshold(sy, sp)
    scored <- score_at_threshold(sy, sp, threshold)
    data.frame(
      replicate = b,
      selected_threshold = scored$threshold,
      expected_cost = scored$expected_cost,
      recall = scored$recall,
      specificity = scored$specificity,
      precision = scored$precision,
      n_resampled = n
    )
  })
  do.call(rbind, rows)
}

fairness_rows <- function(frame, y, p, pred) {
  groups <- as.character(frame[[audit_col]])
  groups[is.na(groups)] <- "missing"
  overall_pred <- if (length(pred)) mean(pred) else 0
  overall_recall <- if (sum(y == 1)) mean(pred[y == 1]) else 0
  rows <- lapply(sort(unique(groups)), function(group) {
    mask <- groups == group
    gy <- y[mask]
    gp <- p[mask]
    gpred <- pred[mask]
    predicted_positive_rate <- if (length(gpred)) mean(gpred) else 0
    recall <- if (sum(gy == 1)) mean(gpred[gy == 1]) else 0
    fpr <- if (sum(gy == 0)) mean(gpred[gy == 0]) else 0
    data.frame(
      audit_group = group,
      n = sum(mask),
      observed_positive_rate = round6(if (length(gy)) mean(gy) else 0),
      predicted_positive_rate = round6(predicted_positive_rate),
      recall = round6(recall),
      false_positive_rate = round6(fpr),
      mean_probability = round6(if (length(gp)) mean(gp) else 0),
      demographic_parity_gap = round6(abs(predicted_positive_rate - overall_pred)),
      equal_opportunity_gap = round6(abs(recall - overall_recall))
    )
  })
  do.call(rbind, rows)
}

write_metrics <- function(metrics) {
  keys <- names(metrics)
  values <- vapply(keys, function(k) {
    x <- metrics[[k]]
    if (grepl("^n_", k)) as.character(as.integer(x)) else sprintf("%.6f", as.numeric(x))
  }, character(1))
  body <- paste(sprintf('  "%s": %s', keys, values), collapse = ",\n")
  writeLines(c("{", body, "}"), file.path(out_dir, "metrics.json"))
}

df <- read.csv(data_path, stringsAsFactors = FALSE, na.strings = c("", "NA"))
df[[target_col]] <- suppressWarnings(as.numeric(df[[target_col]]))
labeled <- df[!is.na(df[[target_col]]), ]
labeled[[target_col]] <- as.integer(labeled[[target_col]])
evaluation <- df[is.na(df[[target_col]]), ]
train_all <- labeled[labeled[[period_col]] < 10, ]
valid <- train_all[train_all[[period_col]] >= 8, ]

rate <- mean(train_all[[target_col]])
valid_p <- rep(rate, nrow(valid))
eval_p <- rep(rate, nrow(evaluation))
eval_p <- pmin(pmax(eval_p + seq_len(length(eval_p)) * 1e-5, 0), 1)
threshold <- 0.5
valid_pred <- as.integer(valid_p >= threshold)
eval_pred <- as.integer(eval_p >= threshold)

validation_scores <- data.frame(
  record_id = as.character(valid[[id_col]]),
  target = as.integer(valid[[target_col]]),
  audit_group = as.character(valid[[audit_col]]),
  probability = round6(valid_p),
  prediction = valid_pred
)
validation_scores <- validation_scores[order(validation_scores$record_id), ]

predictions <- data.frame(
  record_id = as.character(evaluation[[id_col]]),
  probability = round6(eval_p),
  prediction = eval_pred
)
predictions <- predictions[order(predictions$record_id), ]

fair <- fairness_rows(valid, valid[[target_col]], valid_p, valid_pred)
costs <- cost_rows(valid[[target_col]], valid_p)
bins <- calibration_rows(valid[[target_col]], valid_p)
boot <- bootstrap_rows(validation_scores$target, validation_scores$probability)
features <- data.frame(feature = "baseline_rate", importance = 1)

metrics <- list(
  n_train = nrow(train_all),
  n_validation = nrow(valid),
  n_test = nrow(evaluation),
  positive_rate_train = round6(mean(train_all[[target_col]])),
  positive_rate_test = round6(mean(valid[[target_col]])),
  roc_auc = 0,
  pr_auc = 0,
  brier = round6(mean((valid[[target_col]] - valid_p)^2)),
  ece = round6(sum(bins$count * ifelse(is.na(bins$absolute_error), 0, bins$absolute_error)) / max(1, sum(bins$count))),
  balanced_accuracy = 0,
  f1 = 0,
  precision = 0,
  recall = 0,
  specificity = 0,
  threshold = threshold,
  expected_cost = costs$expected_cost[which(costs$threshold == threshold)[1]],
  false_negative_cost = fn_cost,
  false_positive_cost = fp_cost,
  primary_metric_value = -costs$expected_cost[which(costs$threshold == threshold)[1]],
  fairness_demographic_parity_gap = max(fair$demographic_parity_gap, na.rm = TRUE),
  fairness_equal_opportunity_gap = max(fair$equal_opportunity_gap, na.rm = TRUE)
)

write_metrics(metrics)
write.csv(predictions, file.path(out_dir, "predictions.csv"), row.names = FALSE, na = "")
write.csv(validation_scores, file.path(out_dir, "validation_scores.csv"), row.names = FALSE, na = "")
write.csv(bins, file.path(out_dir, "calibration_bins.csv"), row.names = FALSE, na = "")
write.csv(costs, file.path(out_dir, "cost_curve.csv"), row.names = FALSE, na = "")
write.csv(boot, file.path(out_dir, "threshold_bootstrap.csv"), row.names = FALSE, na = "")
write.csv(fair, file.path(out_dir, "fairness_report.csv"), row.names = FALSE, na = "")
write.csv(features, file.path(out_dir, "feature_importance.csv"), row.names = FALSE, na = "")
