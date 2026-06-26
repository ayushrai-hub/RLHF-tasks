suppressPackageStartupMessages({
  library(dplyr)
})

group_state_folds <- function(df, n_folds = 5L, seed = 23L) {
  states <- sort(unique(df[["_STATE"]]))
  set.seed(seed)
  shuffled <- sample(states)
  fold_id <- (seq_along(shuffled) - 1L) %% n_folds + 1L
  state_to_fold <- setNames(fold_id, as.character(shuffled))
  row_fold <- state_to_fold[as.character(df[["_STATE"]])]
  lapply(seq_len(n_folds), function(k) {
    list(train_idx = which(row_fold != k),
         val_idx   = which(row_fold == k),
         val_states = shuffled[fold_id == k])
  })
}

count_overlap_states <- function(train_states, test_states) {
  length(intersect(unique(train_states), unique(test_states)))
}
