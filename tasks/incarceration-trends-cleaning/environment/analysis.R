#!/usr/bin/env Rscript

# Starting point for the incarceration-trends cleaning task.
# Replace the body below with your own implementation.
#
# Read the per-state CSVs under DATA_DIR, build the two output tables described
# in /app/environment/OUTPUT_CONTRACT.md, and write them into OUTPUT_DIR. The
# outputs directory is wiped and rebuilt on every run, so every result must be
# produced here.

DATA_DIR <- "/app/environment/data/states"
OUTPUT_DIR <- "/app/environment/outputs"
dir.create(OUTPUT_DIR, showWarnings = FALSE, recursive = TRUE)

# TODO: read the state files, clean and combine the records, derive the rates,
# and write county_year_clean.csv and urbanicity_summary.csv into OUTPUT_DIR.
