data_dir <- Sys.getenv("CAUSAL_DATA_DIR", "/app/data")
df <- read.csv(file.path(data_dir, "main.csv"))
df$y_gain <- df$y_followup - df$y_baseline
fit <- lm(y_gain ~ d_treatment, data = df)
ate <- coef(fit)[["d_treatment"]]
jsonlite::write_json(list(estimate = ate), "/app/estimate.json", auto_unbox = TRUE)
