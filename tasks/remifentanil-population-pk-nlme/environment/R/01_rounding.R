r6 <- function(x) {
  ifelse(is.na(x), NA_real_, round(as.numeric(x), 6))
}
