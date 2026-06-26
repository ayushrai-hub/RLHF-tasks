suppressPackageStartupMessages({
  library(dplyr)
})

balanced_accuracy <- function(y_true, y_pred) {
  y_true <- as.integer(y_true); y_pred <- as.integer(y_pred)
  tp <- sum(y_true == 1L & y_pred == 1L)
  fn <- sum(y_true == 1L & y_pred == 0L)
  tn <- sum(y_true == 0L & y_pred == 0L)
  fp <- sum(y_true == 0L & y_pred == 1L)
  sens <- if (tp + fn == 0L) 0 else tp / (tp + fn)
  spec <- if (tn + fp == 0L) 0 else tn / (tn + fp)
  (sens + spec) / 2
}

per_class_recall <- function(y_true, y_pred) {
  y_true <- as.integer(y_true); y_pred <- as.integer(y_pred)
  pos <- if (sum(y_true == 1L) == 0L) 0 else sum(y_true == 1L & y_pred == 1L) / sum(y_true == 1L)
  neg <- if (sum(y_true == 0L) == 0L) 0 else sum(y_true == 0L & y_pred == 0L) / sum(y_true == 0L)
  list(`0` = neg, `1` = pos)
}

per_class_precision <- function(y_true, y_pred) {
  y_true <- as.integer(y_true); y_pred <- as.integer(y_pred)
  pos <- if (sum(y_pred == 1L) == 0L) 0 else sum(y_true == 1L & y_pred == 1L) / sum(y_pred == 1L)
  neg <- if (sum(y_pred == 0L) == 0L) 0 else sum(y_true == 0L & y_pred == 0L) / sum(y_pred == 0L)
  list(`0` = neg, `1` = pos)
}

auroc <- function(y_true, y_score) {
  y_true <- as.integer(y_true)
  ord <- order(y_score, decreasing = TRUE)
  yt <- y_true[ord]
  pos <- sum(yt == 1L); neg <- sum(yt == 0L)
  if (pos == 0L || neg == 0L) return(NA_real_)
  rank_pos <- which(yt == 1L)
  (sum(length(yt) - rank_pos + 1L) - pos * (pos + 1L) / 2) / (pos * neg)
}

cost_weighted_loss <- function(y_true, y_pred, cost_fn = 5.0, cost_fp = 1.0) {
  y_true <- as.integer(y_true); y_pred <- as.integer(y_pred)
  fn_count <- sum(y_true == 1L & y_pred == 0L)
  fp_count <- sum(y_true == 0L & y_pred == 1L)
  (cost_fn * fn_count + cost_fp * fp_count) / length(y_true)
}

brier_score <- function(y_true, y_proba) {
  y_true <- as.numeric(y_true); y_proba <- as.numeric(y_proba)
  mean((y_true - y_proba) ^ 2, na.rm = TRUE)
}

subgroup_balanced_accuracy <- function(y_true, y_pred, group, min_rows = 30L) {
  y_true <- as.integer(y_true); y_pred <- as.integer(y_pred)
  groups <- unique(group)
  out <- list()
  for (g in groups) {
    idx <- which(group == g)
    if (length(idx) < min_rows) next
    out[[as.character(g)]] <- balanced_accuracy(y_true[idx], y_pred[idx])
  }
  out
}
