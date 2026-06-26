input_paths <- function() {
  list(
    data = Sys.getenv("REMIFENTANIL_DATA_PATH", unset = "/app/environment/data/Remifentanil.csv"),
    outputs = "/app/environment/outputs"
  )
}
