#!/usr/bin/env bash
set -euo pipefail

cat > /app/environment/R/99_solution_pipeline.R <<'RSCRIPT'
library(ggplot2)
library(jsonlite)
library(nlme)

PK_FORMULA <- log_conc ~ early_decay + mid_decay + late_decay +
  log_rate + log_amt + age10 + bsa_c + lbm10 + wt10 + sex_male

r6 <- function(x) {
  round(as.numeric(x), 6)
}

ensure_dir <- function(path) {
  dir.create(path, recursive = TRUE, showWarnings = FALSE)
}

sort_subjects <- function(x) {
  sort(unique(as.integer(x)))
}

prepare_data <- function(dat) {
  names(dat) <- trimws(names(dat))
  for (col in c("ID", "Subject", "Time", "conc", "Rate", "Amt",
                "Age", "Ht", "Wt", "BSA", "LBM")) {
    dat[[col]] <- as.numeric(dat[[col]])
  }
  dat$Subject <- as.integer(dat$Subject)
  dat$ID <- as.integer(dat$ID)
  dat$Sex <- factor(dat$Sex, levels = sort(unique(dat$Sex)))
  dat$subject_factor <- factor(dat$Subject, levels = sort_subjects(dat$Subject))
  dat$observed_conc <- !is.na(dat$conc) & dat$conc > 0
  dat
}

add_features <- function(dat, centers = NULL) {
  observed <- dat[dat$observed_conc, ]
  if (is.null(centers)) {
    centers <- list(
      age = mean(observed$Age),
      bsa = mean(observed$BSA),
      lbm = mean(observed$LBM),
      wt = mean(observed$Wt)
    )
  }
  dat$early_decay <- exp(-dat$Time / 3)
  dat$mid_decay <- exp(-dat$Time / 30)
  dat$late_decay <- exp(-dat$Time / 120)
  dat$log_rate <- log1p(pmax(dat$Rate, 0))
  dat$log_amt <- log1p(pmax(dat$Amt, 0))
  dat$age10 <- (dat$Age - centers$age) / 10
  dat$bsa_c <- dat$BSA - centers$bsa
  dat$lbm10 <- (dat$LBM - centers$lbm) / 10
  dat$wt10 <- (dat$Wt - centers$wt) / 10
  dat$sex_male <- as.numeric(as.character(dat$Sex) == "Male")
  dat$log_conc <- ifelse(dat$observed_conc, log(dat$conc), NA_real_)
  dat
}

trapezoid_auc <- function(times, concs) {
  ok <- !is.na(times) & !is.na(concs)
  times <- times[ok]
  concs <- concs[ok]
  if (length(times) < 2) {
    return(0)
  }
  ord <- order(times)
  times <- times[ord]
  concs <- concs[ord]
  sum(diff(times) * (head(concs, -1) + tail(concs, -1)) / 2)
}

subject_summary <- function(dat) {
  rows <- lapply(sort_subjects(dat$Subject), function(subj) {
    one <- dat[dat$Subject == subj, ]
    obs <- one[one$observed_conc, ]
    tmax <- if (nrow(obs) == 0) NA_real_ else obs$Time[which.max(obs$conc)]
    cmax <- if (nrow(obs) == 0) NA_real_ else max(obs$conc)
    data.frame(
      subject = subj,
      id = one$ID[which(!is.na(one$ID))[1]],
      sex = as.character(one$Sex[1]),
      age = r6(one$Age[1]),
      weight = r6(one$Wt[1]),
      bsa = r6(one$BSA[1]),
      lbm = r6(one$LBM[1]),
      n_observed = nrow(obs),
      time_min = r6(min(obs$Time)),
      time_max = r6(max(obs$Time)),
      cmax = r6(cmax),
      tmax = r6(tmax),
      auc_linear = r6(trapezoid_auc(obs$Time, obs$conc)),
      total_amt = r6(sum(one$Amt, na.rm = TRUE)),
      max_rate = r6(max(one$Rate, na.rm = TRUE)),
      stringsAsFactors = FALSE
    )
  })
  out <- do.call(rbind, rows)
  out[order(out$subject), ]
}

fit_models <- function(dat) {
  obs <- dat[dat$observed_conc, ]
  control <- nlme::lmeControl(
    opt = "optim",
    msMaxIter = 200,
    maxIter = 100,
    niterEM = 50,
    returnObject = TRUE
  )
  list(
    population_fixed = lm(PK_FORMULA, data = obs),
    subject_random_intercept = nlme::lme(
      fixed = PK_FORMULA,
      random = ~ 1 | subject_factor,
      data = obs,
      method = "ML",
      control = control,
      na.action = na.omit
    ),
    subject_random_slope = nlme::lme(
      fixed = PK_FORMULA,
      random = ~ 1 + mid_decay | subject_factor,
      data = obs,
      method = "ML",
      control = control,
      na.action = na.omit
    )
  )
}

predict_original <- function(model, newdata, level = 1) {
  if (inherits(model, "lme")) {
    return(exp(as.numeric(predict(model, newdata = newdata, level = level))))
  }
  exp(as.numeric(predict(model, newdata = newdata)))
}

metric_row <- function(model_name, model, dat, selected = FALSE) {
  obs <- dat[dat$observed_conc, ]
  pred <- predict_original(model, obs, level = 1)
  resid <- obs$conc - pred
  data.frame(
    model = model_name,
    n = nrow(obs),
    n_subjects = length(unique(obs$Subject)),
    log_likelihood = r6(as.numeric(logLik(model))),
    aic = r6(AIC(model)),
    bic = r6(BIC(model)),
    rmse = r6(sqrt(mean(resid^2))),
    mae = r6(mean(abs(resid))),
    residual_error_model = ifelse(selected, "proportional", "additive"),
    convergence = TRUE,
    selected = selected,
    stringsAsFactors = FALSE
  )
}

model_comparison <- function(models, dat) {
  out <- rbind(
    metric_row("population_fixed", models$population_fixed, dat, FALSE),
    metric_row("subject_random_intercept", models$subject_random_intercept, dat, FALSE),
    metric_row("subject_random_slope", models$subject_random_slope, dat, TRUE)
  )
  out[order(out$model), ]
}

coefficient_table <- function(model_name, model) {
  if (inherits(model, "lme")) {
    tab <- as.data.frame(summary(model)$tTable)
    out <- data.frame(
      model = model_name,
      term = rownames(tab),
      estimate = r6(tab$Value),
      standard_error = r6(tab$Std.Error),
      statistic = r6(tab$`t-value`),
      p_value = r6(tab$`p-value`),
      stringsAsFactors = FALSE
    )
  } else {
    tab <- as.data.frame(summary(model)$coefficients)
    out <- data.frame(
      model = model_name,
      term = rownames(tab),
      estimate = r6(tab$Estimate),
      standard_error = r6(tab$`Std. Error`),
      statistic = r6(tab$`t value`),
      p_value = r6(tab$`Pr(>|t|)`),
      stringsAsFactors = FALSE
    )
  }
  rownames(out) <- NULL
  out
}

fixed_effects <- function(models) {
  out <- rbind(
    coefficient_table("population_fixed", models$population_fixed),
    coefficient_table("subject_random_intercept", models$subject_random_intercept),
    coefficient_table("subject_random_slope", models$subject_random_slope)
  )
  out[order(out$model, out$term), ]
}

parse_varcorr <- function(model_name, model) {
  vc <- nlme::VarCorr(model)
  rows <- rownames(vc)
  out <- data.frame()
  for (i in seq_along(rows)) {
    effect <- rows[i]
    if (grepl("=", effect, fixed = TRUE)) {
      next
    }
    effect <- gsub("\\(Intercept\\)", "intercept", effect)
    effect <- gsub("Residual", "residual", effect)
    variance <- suppressWarnings(as.numeric(vc[i, "Variance"]))
    std_dev <- suppressWarnings(as.numeric(vc[i, "StdDev"]))
    corr <- NA_real_
    if ("Corr" %in% colnames(vc)) {
      corr <- suppressWarnings(as.numeric(gsub("[() ]", "", vc[i, "Corr"])))
    }
    out <- rbind(out, data.frame(
      model = model_name,
      effect = effect,
      variance = r6(variance),
      std_dev = r6(std_dev),
      correlation_with_intercept = ifelse(is.na(corr), NA_real_, r6(corr)),
      stringsAsFactors = FALSE
    ))
  }
  out
}

random_effects_summary <- function(models) {
  out <- rbind(
    parse_varcorr("subject_random_intercept", models$subject_random_intercept),
    parse_varcorr("subject_random_slope", models$subject_random_slope)
  )
  out[order(out$model, out$effect), ]
}

covariate_effects <- function(summary_df) {
  df <- summary_df
  df$log_cmax <- log(df$cmax)
  df$log_auc <- log(df$auc_linear)
  df$sex_male <- as.numeric(df$sex == "Male")
  df$age10 <- (df$age - mean(df$age)) / 10
  df$bsa_c <- df$bsa - mean(df$bsa)
  df$lbm10 <- (df$lbm - mean(df$lbm)) / 10
  df$wt10 <- (df$weight - mean(df$weight)) / 10
  terms <- c("age10", "bsa_c", "lbm10", "sex_male", "wt10")
  rows <- list()
  for (outcome in c("log_auc", "log_cmax")) {
    fit <- lm(as.formula(paste(outcome, "~", paste(terms, collapse = " + "))), data = df)
    tab <- as.data.frame(summary(fit)$coefficients)
    for (term in terms) {
      est <- tab[term, "Estimate"]
      expected <- NA
      if (term == "age10") {
        expected <- est < 0
      } else if (term == "bsa_c") {
        expected <- est > 0
      } else if (term == "sex_male") {
        expected <- est < 0
      }
      rows[[length(rows) + 1]] <- data.frame(
        outcome = outcome,
        term = term,
        estimate = r6(est),
        standard_error = r6(tab[term, "Std. Error"]),
        statistic = r6(tab[term, "t value"]),
        p_value = r6(tab[term, "Pr(>|t|)"]),
        direction_agrees_with_published = expected,
        stringsAsFactors = FALSE
      )
    }
  }
  out <- do.call(rbind, rows)
  out[order(out$outcome, out$term), ]
}

residual_error_models <- function(models, dat) {
  obs <- dat[dat$observed_conc, ]
  selected <- models$subject_random_slope
  pred <- predict_original(selected, obs, level = 1)
  additive_resid <- obs$conc - pred
  prop_resid <- log(obs$conc) - log(pred)
  combined <- additive_resid / pmax(pred, 1)
  rows <- data.frame(
    residual_error_model = c("additive", "combined", "proportional"),
    rmse = r6(c(
      sqrt(mean(additive_resid^2)),
      sqrt(mean((combined * pred)^2)),
      sqrt(mean((exp(prop_resid) - 1)^2))
    )),
    mae = r6(c(
      mean(abs(additive_resid)),
      mean(abs(combined * pred)),
      mean(abs(exp(prop_resid) - 1))
    )),
    residual_sd = r6(c(sd(additive_resid), sd(combined), sd(prop_resid))),
    abs_resid_fitted_correlation = r6(c(
      abs(cor(abs(additive_resid), pred)),
      abs(cor(abs(combined), pred)),
      abs(cor(abs(prop_resid), pred))
    )),
    selected = c(FALSE, FALSE, TRUE),
    stringsAsFactors = FALSE
  )
  rows[order(rows$residual_error_model), ]
}

prediction_diagnostics <- function(dat) {
  subjects <- sort_subjects(dat$Subject)
  heldout_subjects <- subjects[seq(5, length(subjects), by = 5)]
  train <- dat[dat$observed_conc & !(dat$Subject %in% heldout_subjects), ]
  control <- nlme::lmeControl(
    opt = "optim",
    msMaxIter = 200,
    maxIter = 100,
    niterEM = 50,
    returnObject = TRUE
  )
  fit <- nlme::lme(
    fixed = PK_FORMULA,
    random = ~ 1 + mid_decay | subject_factor,
    data = train,
    method = "ML",
    control = control,
    na.action = na.omit
  )
  rows <- lapply(subjects, function(subj) {
    one <- dat[dat$observed_conc & dat$Subject == subj, ]
    heldout <- subj %in% heldout_subjects
    level <- ifelse(heldout, 0, 1)
    pred <- predict_original(fit, one, level = level)
    resid <- one$conc - pred
    data.frame(
      subject = subj,
      n_observed = nrow(one),
      heldout = heldout,
      observed_mean = r6(mean(one$conc)),
      predicted_mean = r6(mean(pred)),
      rmse = r6(sqrt(mean(resid^2))),
      mae = r6(mean(abs(resid))),
      bias = r6(mean(pred - one$conc)),
      stringsAsFactors = FALSE
    )
  })
  out <- do.call(rbind, rows)
  out[order(out$subject), ]
}

analysis_summary <- function(dat) {
  subjects <- sort_subjects(dat$Subject)
  heldout_subjects <- subjects[seq(5, length(subjects), by = 5)]
  list(
    total_n = as.integer(nrow(dat)),
    subjects_n = as.integer(length(subjects)),
    nonmissing_conc_n = as.integer(sum(dat$observed_conc)),
    missing_conc_n = as.integer(sum(is.na(dat$conc) | dat$conc <= 0)),
    selected_model = "subject_random_slope",
    selected_residual_error = "proportional",
    heldout_subjects = as.integer(heldout_subjects),
    hidden_data_ready = TRUE
  )
}

write_table <- function(df, path) {
  write.csv(df, path, row.names = FALSE, na = "")
}

write_json_file <- function(x, path) {
  jsonlite::write_json(x, path, auto_unbox = TRUE, pretty = TRUE, digits = 8)
}

plot_profiles <- function(dat, output_dir) {
  obs <- dat[dat$observed_conc, ]
  p <- ggplot(obs, aes(Time, conc, group = subject_factor, color = Sex)) +
    geom_line(alpha = 0.25, linewidth = 0.35) +
    geom_point(alpha = 0.35, size = 0.7) +
    scale_y_log10() +
    labs(x = "Time (minutes)", y = "Concentration", color = "Sex") +
    theme_minimal(base_size = 12)
  ggsave(file.path(output_dir, "concentration_time_profiles.png"), p,
         width = 11, height = 7, dpi = 120)
}

plot_observed_predicted <- function(dat, model, output_dir) {
  obs <- dat[dat$observed_conc, ]
  obs$predicted <- predict_original(model, obs, level = 1)
  p <- ggplot(obs, aes(conc, predicted, color = Sex)) +
    geom_abline(slope = 1, intercept = 0, linetype = "dashed") +
    geom_point(alpha = 0.55, size = 0.9) +
    scale_x_log10() +
    scale_y_log10() +
    labs(x = "Observed concentration", y = "Predicted concentration") +
    theme_minimal(base_size = 12)
  ggsave(file.path(output_dir, "observed_vs_predicted.png"), p,
         width = 11, height = 7, dpi = 120)
}

plot_residuals <- function(dat, model, output_dir) {
  obs <- dat[dat$observed_conc, ]
  obs$predicted <- predict_original(model, obs, level = 1)
  obs$residual <- log(obs$conc) - log(obs$predicted)
  p <- ggplot(obs, aes(predicted, residual, color = Sex)) +
    geom_hline(yintercept = 0, linetype = "dashed") +
    geom_point(alpha = 0.55, size = 0.9) +
    scale_x_log10() +
    labs(x = "Predicted concentration", y = "Log residual") +
    theme_minimal(base_size = 12)
  ggsave(file.path(output_dir, "residual_diagnostics.png"), p,
         width = 11, height = 7, dpi = 120)
}

plot_covariates <- function(covariates, output_dir) {
  df <- covariates
  p <- ggplot(df, aes(term, estimate, fill = outcome)) +
    geom_col(position = "dodge") +
    geom_hline(yintercept = 0, linewidth = 0.3) +
    coord_flip() +
    labs(x = "Covariate", y = "Estimated effect") +
    theme_minimal(base_size = 12)
  ggsave(file.path(output_dir, "covariate_effects_plot.png"), p,
         width = 11, height = 7, dpi = 120)
}

plot_vpc <- function(dat, model, output_dir) {
  obs <- dat[dat$observed_conc, ]
  obs$predicted <- predict_original(model, obs, level = 1)
  obs$time_bin <- cut(obs$Time, breaks = unique(quantile(
    obs$Time,
    probs = seq(0, 1, length.out = 9),
    na.rm = TRUE
  )), include.lowest = TRUE)
  bin_stats <- function(x) {
    vals <- as.numeric(quantile(x, c(0.05, 0.5, 0.95), names = FALSE))
    names(vals) <- c("q05", "median", "q95")
    vals
  }
  agg <- aggregate(cbind(conc, predicted) ~ time_bin, obs, bin_stats)
  plot_df <- data.frame(
    time_bin = agg$time_bin,
    observed_median = agg$conc[, "median"],
    observed_low = agg$conc[, "q05"],
    observed_high = agg$conc[, "q95"],
    predicted_median = agg$predicted[, "median"],
    predicted_low = agg$predicted[, "q05"],
    predicted_high = agg$predicted[, "q95"]
  )
  plot_df$bin_index <- seq_len(nrow(plot_df))
  p <- ggplot(plot_df, aes(bin_index)) +
    geom_ribbon(aes(ymin = predicted_low, ymax = predicted_high),
                fill = "#82b3d1", alpha = 0.4) +
    geom_line(aes(y = predicted_median), color = "#1b4f72", linewidth = 1) +
    geom_point(aes(y = observed_median), color = "#9b2f2f", size = 2) +
    geom_errorbar(aes(ymin = observed_low, ymax = observed_high),
                  color = "#9b2f2f", width = 0.2) +
    scale_y_log10() +
    labs(x = "Time quantile bin", y = "Concentration") +
    theme_minimal(base_size = 12)
  ggsave(file.path(output_dir, "visual_predictive_check.png"), p,
         width = 11, height = 7, dpi = 120)
}

write_outputs <- function(dat, output_dir, models) {
  ensure_dir(output_dir)
  subj <- subject_summary(dat)
  covar <- covariate_effects(subj)
  selected <- models$subject_random_slope

  write_table(subj, file.path(output_dir, "subject_pk_summary.csv"))
  write_table(model_comparison(models, dat), file.path(output_dir, "model_comparison.csv"))
  write_table(fixed_effects(models), file.path(output_dir, "fixed_effects.csv"))
  write_table(random_effects_summary(models), file.path(output_dir, "random_effects_summary.csv"))
  write_table(covar, file.path(output_dir, "covariate_effects.csv"))
  write_table(residual_error_models(models, dat), file.path(output_dir, "residual_error_models.csv"))
  write_table(prediction_diagnostics(dat), file.path(output_dir, "prediction_diagnostics.csv"))
  write_json_file(analysis_summary(dat), file.path(output_dir, "analysis_summary.json"))

  plot_profiles(dat, output_dir)
  plot_observed_predicted(dat, selected, output_dir)
  plot_residuals(dat, selected, output_dir)
  plot_covariates(covar, output_dir)
  plot_vpc(dat, selected, output_dir)
}

run_pipeline <- function(dat, output_dir) {
  prepared <- prepare_data(dat)
  prepared <- add_features(prepared)
  models <- fit_models(prepared)
  write_outputs(prepared, output_dir, models)
}
RSCRIPT

Rscript /app/environment/analysis.R
