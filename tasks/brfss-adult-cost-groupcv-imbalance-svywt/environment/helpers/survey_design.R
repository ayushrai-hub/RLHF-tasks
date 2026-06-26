suppressPackageStartupMessages({
  library(survey)
})

build_design <- function(df) {
  options(survey.lonely.psu = "adjust")
  d <- svydesign(ids = ~`_PSU`, strata = ~`_STSTR`, weights = ~`_LLCPWT`,
                 data = df, nest = TRUE)
  attr(d, "weight_col") <- "_LLCPWT"
  attr(d, "strata_col") <- "_STSTR"
  attr(d, "psu_col")    <- "_PSU"
  d
}

weighted_prevalence <- function(df, target_col = "HAVEDIAB", weight_col = "_LLCPWT") {
  if (!target_col %in% names(df)) return(NA_real_)
  num <- sum(df[[target_col]] * df[[weight_col]], na.rm = TRUE)
  den <- sum(df[[weight_col]], na.rm = TRUE)
  if (den == 0) NA_real_ else num / den
}
