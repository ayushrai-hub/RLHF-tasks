require_columns <- function(data, columns) {
  missing <- setdiff(columns, names(data))
  if (length(missing) > 0) {
    stop(paste("missing columns:", paste(missing, collapse = ", ")))
  }
  invisible(TRUE)
}

require_finite_column <- function(data, column) {
  values <- data[[column]]
  if (any(!is.finite(values))) {
    stop(paste("non-finite values in", column))
  }
  invisible(TRUE)
}
