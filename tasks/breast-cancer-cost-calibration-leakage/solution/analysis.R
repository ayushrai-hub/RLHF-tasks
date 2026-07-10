app_dir <- Sys.getenv("APP_DIR", "/app")
data_path <- file.path(app_dir, "data", "risk_queue.csv")
out_dir <- file.path(app_dir, "outputs")

id_col <- "record_id"
target_col <- "target"
period_col <- "event_month"
audit_col <- "audit_group"
blocked_cols <- c(
  "record_id", "target", "event_month", "audit_group",
  "ops_score_a", "ops_code_b", "ops_bucket_c"
)
fn_cost <- 12
fp_cost <- 1
thresholds <- round(seq(0.05, 0.95, by = 0.01), 2)
ridge_lambda <- 5

round6 <- function(x) {
  ifelse(is.na(x) | !is.finite(x), NA_real_, round(as.numeric(x), 6))
}

safe_div <- function(a, b) {
  if (b == 0) 0 else a / b
}

clip <- function(x, lo = 1e-7, hi = 1 - 1e-7) {
  pmin(pmax(x, lo), hi)
}

sigmoid <- function(eta) {
  eta <- pmin(pmax(eta, -35), 35)
  1 / (1 + exp(-eta))
}

read_frame <- function() {
  df <- read.csv(data_path, stringsAsFactors = FALSE, na.strings = c("", "NA"))
  df[[period_col]] <- as.integer(df[[period_col]])
  df[[target_col]] <- suppressWarnings(as.numeric(df[[target_col]]))
  df
}

split_frame <- function(df) {
  labeled <- df[!is.na(df[[target_col]]), , drop = FALSE]
  labeled[[target_col]] <- as.integer(labeled[[target_col]])
  evaluation <- df[is.na(df[[target_col]]), , drop = FALSE]
  train_all <- labeled[labeled[[period_col]] < 10, , drop = FALSE]
  valid <- train_all[train_all[[period_col]] >= 8, , drop = FALSE]
  fit <- train_all[train_all[[period_col]] < 8, , drop = FALSE]
  if (length(unique(valid[[target_col]])) < 2 || length(unique(fit[[target_col]])) < 2) {
    set.seed(20260657)
    fit_idx <- logical(nrow(train_all))
    for (cls in sort(unique(train_all[[target_col]]))) {
      where <- which(train_all[[target_col]] == cls)
      valid_n <- max(1, ceiling(length(where) * 0.25))
      valid_idx <- sample(where, valid_n)
      fit_idx[valid_idx] <- TRUE
    }
    valid <- train_all[fit_idx, , drop = FALSE]
    fit <- train_all[!fit_idx, , drop = FALSE]
  }
  list(fit = fit, valid = valid, evaluation = evaluation, train_all = train_all)
}

model_columns <- function(df) {
  setdiff(names(df), blocked_cols)
}

make_preprocessor <- function(fit, cols) {
  numeric_cols <- cols[vapply(fit[cols], is.numeric, logical(1))]
  med <- vapply(numeric_cols, function(col) {
    x <- fit[[col]]
    x[x %in% c(-999, -777)] <- NA
    median(x, na.rm = TRUE)
  }, numeric(1))
  med[!is.finite(med)] <- 0
  center <- vapply(numeric_cols, function(col) {
    x <- fit[[col]]
    x[x %in% c(-999, -777)] <- NA
    x[is.na(x)] <- med[[col]]
    mean(x)
  }, numeric(1))
  scale <- vapply(numeric_cols, function(col) {
    x <- fit[[col]]
    x[x %in% c(-999, -777)] <- NA
    x[is.na(x)] <- med[[col]]
    s <- sqrt(mean((x - mean(x))^2))
    if (!is.finite(s) || s == 0) 1 else s
  }, numeric(1))
  list(cols = numeric_cols, med = med, center = center, scale = scale)
}

transform_frame <- function(frame, prep) {
  mat <- sapply(prep$cols, function(col) {
    x <- frame[[col]]
    x[x %in% c(-999, -777)] <- NA
    x[is.na(x)] <- prep$med[[col]]
    (x - prep$center[[col]]) / prep$scale[[col]]
  })
  mat <- as.matrix(mat)
  if (is.null(dim(mat))) {
    mat <- matrix(mat, ncol = 1)
    colnames(mat) <- prep$cols
  }
  storage.mode(mat) <- "double"
  mat
}

fit_ridge_logistic <- function(x, y, lambda) {
  xb <- cbind("(Intercept)" = 1, x)
  beta <- rep(0, ncol(xb))
  penalty <- diag(lambda, ncol(xb))
  penalty[1, 1] <- 0
  for (iter in seq_len(100)) {
    eta <- as.vector(xb %*% beta)
    p <- sigmoid(eta)
    variance <- pmax(p * (1 - p), 1e-8)
    z <- eta + (y - p) / variance
    wx <- xb * variance
    lhs <- crossprod(xb, wx) + penalty
    rhs <- crossprod(xb, variance * z)
    next_beta <- as.vector(qr.solve(lhs, rhs))
    if (max(abs(next_beta - beta)) < 1e-9) {
      beta <- next_beta
      break
    }
    beta <- next_beta
  }
  names(beta) <- colnames(xb)
  beta
}

predict_ridge <- function(beta, x) {
  xb <- cbind("(Intercept)" = 1, x)
  sigmoid(as.vector(xb %*% beta))
}

stabilize_probs <- function(p, ids) {
  offsets <- ((rank(as.character(ids), ties.method = "first") %% 997) - 498) * 1e-8
  clip(p + offsets)
}

roc_auc <- function(y, p) {
  y <- as.integer(y)
  n_pos <- sum(y == 1)
  n_neg <- sum(y == 0)
  if (n_pos == 0 || n_neg == 0) return(NA_real_)
  r <- rank(p, ties.method = "average")
  (sum(r[y == 1]) - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
}

average_precision <- function(y, p) {
  y <- as.integer(y)
  total_pos <- sum(y == 1)
  if (total_pos == 0) return(NA_real_)
  ord <- order(-p, seq_along(p))
  ys <- y[ord]
  ps <- p[ord]
  ends <- c(which(diff(ps) != 0), length(ps))
  tp <- cumsum(ys)[ends]
  fp <- ends - tp
  precision <- tp / (tp + fp)
  recall <- tp / total_pos
  sum((recall - c(0, head(recall, -1))) * precision)
}

confusion_parts <- function(y, pred) {
  list(
    tn = sum(y == 0 & pred == 0),
    fp = sum(y == 0 & pred == 1),
    fn = sum(y == 1 & pred == 0),
    tp = sum(y == 1 & pred == 1)
  )
}

score_at_threshold <- function(y, p, threshold) {
  pred <- as.integer(p >= threshold)
  c <- confusion_parts(y, pred)
  data.frame(
    threshold = round6(threshold),
    tp = c$tp,
    fp = c$fp,
    tn = c$tn,
    fn = c$fn,
    expected_cost = round6((fn_cost * c$fn + fp_cost * c$fp) / max(1, length(y))),
    recall = round6(safe_div(c$tp, c$tp + c$fn)),
    specificity = round6(safe_div(c$tn, c$tn + c$fp)),
    precision = round6(safe_div(c$tp, c$tp + c$fp))
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
      mean_probability <- mean(p[mask])
      observed_rate <- mean(y[mask])
      absolute_error <- abs(mean_probability - observed_rate)
    } else {
      mean_probability <- NA_real_
      observed_rate <- NA_real_
      absolute_error <- NA_real_
    }
    data.frame(
      bin_id = i,
      bin_left = round6(left),
      bin_right = round6(right),
      count = count,
      mean_probability = round6(mean_probability),
      observed_rate = round6(observed_rate),
      absolute_error = round6(absolute_error)
    )
  })
  do.call(rbind, rows)
}

ece_score <- function(y, p) {
  bins <- calibration_rows(y, p)
  sum(bins$count * ifelse(is.na(bins$absolute_error), 0, bins$absolute_error)) /
    max(1, sum(bins$count))
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

feature_rows <- function(beta) {
  b <- beta[names(beta) != "(Intercept)"]
  imp <- abs(b)
  total <- sum(imp)
  if (!is.finite(total) || total == 0) total <- 1
  out <- data.frame(feature = names(imp), importance = round6(imp / total))
  out <- out[order(-out$importance, out$feature), ]
  head(out, 30)
}

metric_dict <- function(train_all, valid, evaluation, y, p, pred, threshold, fair) {
  c <- confusion_parts(y, pred)
  expected_cost <- (fn_cost * c$fn + fp_cost * c$fp) / max(1, length(y))
  list(
    n_train = nrow(train_all),
    n_validation = nrow(valid),
    n_test = nrow(evaluation),
    positive_rate_train = round6(mean(train_all[[target_col]])),
    positive_rate_test = round6(mean(y)),
    roc_auc = round6(roc_auc(y, p)),
    pr_auc = round6(average_precision(y, p)),
    brier = round6(mean((y - p)^2)),
    ece = round6(ece_score(y, p)),
    balanced_accuracy = round6((safe_div(c$tp, c$tp + c$fn) + safe_div(c$tn, c$tn + c$fp)) / 2),
    f1 = round6(safe_div(2 * c$tp, 2 * c$tp + c$fp + c$fn)),
    precision = round6(safe_div(c$tp, c$tp + c$fp)),
    recall = round6(safe_div(c$tp, c$tp + c$fn)),
    specificity = round6(safe_div(c$tn, c$tn + c$fp)),
    threshold = round6(threshold),
    expected_cost = round6(expected_cost),
    false_negative_cost = round6(fn_cost),
    false_positive_cost = round6(fp_cost),
    primary_metric_value = round6(-expected_cost),
    fairness_demographic_parity_gap = round6(max(fair$demographic_parity_gap, na.rm = TRUE)),
    fairness_equal_opportunity_gap = round6(max(fair$equal_opportunity_gap, na.rm = TRUE))
  )
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

write_outputs <- function(metrics, predictions, validation_scores, bins, costs, boot, fair, features) {
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
  write_metrics(metrics)
  write.csv(predictions, file.path(out_dir, "predictions.csv"), row.names = FALSE, na = "")
  write.csv(validation_scores, file.path(out_dir, "validation_scores.csv"), row.names = FALSE, na = "")
  write.csv(bins, file.path(out_dir, "calibration_bins.csv"), row.names = FALSE, na = "")
  write.csv(costs, file.path(out_dir, "cost_curve.csv"), row.names = FALSE, na = "")
  write.csv(boot, file.path(out_dir, "threshold_bootstrap.csv"), row.names = FALSE, na = "")
  write.csv(fair, file.path(out_dir, "fairness_report.csv"), row.names = FALSE, na = "")
  write.csv(features, file.path(out_dir, "feature_importance.csv"), row.names = FALSE, na = "")
}

df <- read_frame()
splits <- split_frame(df)
cols <- model_columns(df)
prep <- make_preprocessor(splits$fit, cols)

x_fit <- transform_frame(splits$fit, prep)
y_fit <- as.integer(splits$fit[[target_col]])
beta <- fit_ridge_logistic(x_fit, y_fit, ridge_lambda)

x_valid <- transform_frame(splits$valid, prep)
valid_y <- as.integer(splits$valid[[target_col]])
valid_p <- stabilize_probs(predict_ridge(beta, x_valid), splits$valid[[id_col]])
valid_p_out <- round6(valid_p)
threshold <- choose_threshold(valid_y, valid_p_out)
valid_pred <- as.integer(valid_p_out >= threshold)

x_eval <- transform_frame(splits$evaluation, prep)
eval_p <- stabilize_probs(predict_ridge(beta, x_eval), splits$evaluation[[id_col]])
eval_p_out <- round6(eval_p)
eval_pred <- as.integer(eval_p_out >= threshold)

predictions <- data.frame(
  record_id = as.character(splits$evaluation[[id_col]]),
  probability = eval_p_out,
  prediction = as.integer(eval_pred)
)
predictions <- predictions[order(predictions$record_id), ]

validation_scores <- data.frame(
  record_id = as.character(splits$valid[[id_col]]),
  target = as.integer(valid_y),
  audit_group = as.character(splits$valid[[audit_col]]),
  probability = valid_p_out,
  prediction = as.integer(valid_pred)
)
validation_scores <- validation_scores[order(validation_scores$record_id), ]

fair <- fairness_rows(splits$valid, valid_y, valid_p_out, valid_pred)
metrics <- metric_dict(
  splits$train_all,
  splits$valid,
  splits$evaluation,
  valid_y,
  valid_p_out,
  valid_pred,
  threshold,
  fair
)

write_outputs(
  metrics,
  predictions,
  validation_scores,
  calibration_rows(valid_y, valid_p_out),
  cost_rows(valid_y, valid_p_out),
  bootstrap_rows(validation_scores$target, validation_scores$probability),
  fair,
  feature_rows(beta)
)
