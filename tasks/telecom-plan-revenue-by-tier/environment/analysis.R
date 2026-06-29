#!/usr/bin/env Rscript

# Starter template. Implement the billing pipeline described in
# /app/docs/question.md and /app/docs/codebook.md here.
#
# Read the lake from the directory named by DATALAKE_DIR (falling back to
# /app/data), decide which exports are authoritative, compute the billed plan
# revenue for the cycle, and write the result object to /app/answer.json with the
# fields the question requires.

suppressPackageStartupMessages({
  library(jsonlite)
})

lake <- Sys.getenv("DATALAKE_DIR", "/app/data")

# TODO: replace this stub with your pipeline.
result <- list(
  answer = 0,
  by_tier = list(),
  recurring_total_usd = 0,
  data_overage_total_usd = 0,
  n_active_subscriptions = 0
)

write_json(result, "/app/answer.json", auto_unbox = TRUE, digits = 10)
