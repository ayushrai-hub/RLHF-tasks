fill_missing_values <- function(df) {
  for (nm in names(df)) {
    if (is.numeric(df[[nm]])) {
      med <- median(df[[nm]], na.rm = TRUE)
      if (!is.finite(med)) med <- 0
      df[[paste0(nm, '_missing')]] <- as.integer(is.na(df[[nm]]))
      df[[nm]][is.na(df[[nm]])] <- med
    } else {
      df[[nm]][is.na(df[[nm]]) | df[[nm]] == ''] <- 'missing'
      df[[nm]] <- factor(df[[nm]])
    }
  }
  df
}
