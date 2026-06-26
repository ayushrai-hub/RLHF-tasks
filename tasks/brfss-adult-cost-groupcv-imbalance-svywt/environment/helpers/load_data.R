suppressPackageStartupMessages({
  library(readr)
})

load_train <- function(dir) {
  read_csv(file.path(dir, "brfss_adult_train.csv"), show_col_types = FALSE,
           col_types = cols(.default = col_double(), row_id = col_character()))
}

load_test <- function(dir) {
  read_csv(file.path(dir, "brfss_adult_test.csv"), show_col_types = FALSE,
           col_types = cols(.default = col_double(), row_id = col_character()))
}

load_codebook <- function(dir) {
  read_csv(file.path(dir, "brfss_codebook.csv"), show_col_types = FALSE,
           col_types = cols(.default = col_character()))
}

load_state_fips <- function(dir) {
  read_csv(file.path(dir, "brfss_state_fips.csv"), show_col_types = FALSE,
           col_types = cols(state_fips = col_integer(),
                            state_abbrev = col_character(),
                            state_name = col_character()))
}

load_by_state <- function(dir) {
  read_csv(file.path(dir, "brfss_by_state.csv"), show_col_types = FALSE)
}

load_by_year <- function(dir) {
  read_csv(file.path(dir, "brfss_by_year.csv"), show_col_types = FALSE)
}

load_weights_table <- function(dir) {
  read_csv(file.path(dir, "brfss_weights.csv"), show_col_types = FALSE)
}

load_ageg5yr_codes <- function(dir) {
  read_csv(file.path(dir, "brfss_ageg5yr_codes.csv"), show_col_types = FALSE,
           col_types = cols(code = col_integer(), age_range_years = col_character()))
}

load_bmi5cat_codes <- function(dir) {
  read_csv(file.path(dir, "brfss_bmi5cat_codes.csv"), show_col_types = FALSE,
           col_types = cols(code = col_integer(), bmi_category = col_character()))
}

load_diabete_codes <- function(dir) {
  read_csv(file.path(dir, "brfss_diabete_codes.csv"), show_col_types = FALSE,
           col_types = cols(raw_code = col_integer(), label = col_character()))
}

load_response_codes <- function(dir) {
  read_csv(file.path(dir, "brfss_response_codes.csv"), show_col_types = FALSE)
}
