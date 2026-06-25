#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(nnet)
  library(jsonlite)
  library(ggplot2)
})

DATA_PATH  <- "/app/environment/data/BEPS.csv"
OUTPUT_DIR <- "/app/environment/outputs"
dir.create(OUTPUT_DIR, showWarnings = FALSE, recursive = TRUE)

dat <- read.csv(DATA_PATH, stringsAsFactors = FALSE)
