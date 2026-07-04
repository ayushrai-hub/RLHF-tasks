read_task_csv <- function(name) {
  read.csv(file.path('/app/data', name), stringsAsFactors = FALSE, na.strings = c('', 'NA'))
}
write_json_file <- function(x, path) {
  jsonlite::write_json(x, path, auto_unbox = TRUE, digits = 15)
}
