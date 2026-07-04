task_data_dir <- function(default = "/app/data") {
  Sys.getenv("CAUSAL_DATA_DIR", default)
}

read_main_data <- function(data_dir = task_data_dir()) {
  read.csv(file.path(data_dir, "main.csv"))
}

read_task_params <- function(data_dir = task_data_dir()) {
  path <- file.path(data_dir, "params.json")
  if (file.exists(path)) {
    jsonlite::fromJSON(path)
  } else {
    list()
  }
}
