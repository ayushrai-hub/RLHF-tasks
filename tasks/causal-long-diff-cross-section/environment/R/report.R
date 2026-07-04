write_estimate <- function(value, path = "/app/estimate.json") {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  jsonlite::write_json(list(estimate = as.numeric(value)), path, auto_unbox = TRUE)
}
