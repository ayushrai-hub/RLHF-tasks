#!/usr/bin/env Rscript

DATA_PATH <- Sys.getenv("REMIFENTANIL_DATA_PATH", unset = "/app/environment/data/Remifentanil.csv")
OUTPUT_DIR <- "/app/environment/outputs"
dir.create(OUTPUT_DIR, showWarnings = FALSE, recursive = TRUE)

dat <- read.csv(DATA_PATH, stringsAsFactors = FALSE)

for (path in sort(list.files("/app/environment/R", pattern = "[.]R$", full.names = TRUE))) {
  source(path)
}

run_pipeline(dat, OUTPUT_DIR)
