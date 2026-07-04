brier <- function(y, p) mean((as.numeric(y) - as.numeric(p)) ^ 2)
ba <- function(y, p) {
  lab <- as.integer(p >= 0.5)
  (mean(lab[y == 1] == 1) + mean(lab[y == 0] == 0)) / 2
}
auc_rank <- function(y, p) {
  y <- as.integer(y)
  r <- rank(as.numeric(p), ties.method = 'average')
  n1 <- sum(y == 1)
  n0 <- sum(y == 0)
  (sum(r[y == 1]) - n1 * (n1 + 1) / 2) / (n1 * n0)
}
