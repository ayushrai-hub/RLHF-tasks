from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ENV_DIR = Path("/app/environment")
DATA_PATH = ENV_DIR / "data" / "Remifentanil.csv"
OUTPUT_DIR = ENV_DIR / "outputs"
TEST_DIR = Path(__file__).resolve().parent

CSV_COLUMNS = {
    "subject_pk_summary.csv": [
        "subject",
        "id",
        "sex",
        "age",
        "weight",
        "bsa",
        "lbm",
        "n_observed",
        "time_min",
        "time_max",
        "cmax",
        "tmax",
        "auc_linear",
        "total_amt",
        "max_rate",
    ],
    "model_comparison.csv": [
        "model",
        "n",
        "n_subjects",
        "log_likelihood",
        "aic",
        "bic",
        "rmse",
        "mae",
        "residual_error_model",
        "convergence",
        "selected",
    ],
    "fixed_effects.csv": [
        "model",
        "term",
        "estimate",
        "standard_error",
        "statistic",
        "p_value",
    ],
    "random_effects_summary.csv": [
        "model",
        "effect",
        "variance",
        "std_dev",
        "correlation_with_intercept",
    ],
    "covariate_effects.csv": [
        "outcome",
        "term",
        "estimate",
        "standard_error",
        "statistic",
        "p_value",
        "direction_agrees_with_published",
    ],
    "residual_error_models.csv": [
        "residual_error_model",
        "rmse",
        "mae",
        "residual_sd",
        "abs_resid_fitted_correlation",
        "selected",
    ],
    "prediction_diagnostics.csv": [
        "subject",
        "n_observed",
        "heldout",
        "observed_mean",
        "predicted_mean",
        "rmse",
        "mae",
        "bias",
    ],
}

PNG_FILES = [
    "concentration_time_profiles.png",
    "observed_vs_predicted.png",
    "residual_diagnostics.png",
    "covariate_effects_plot.png",
    "visual_predictive_check.png",
]

REFERENCE_R = r"""
suppressPackageStartupMessages(library(jsonlite))
suppressPackageStartupMessages(library(nlme))

args <- commandArgs(trailingOnly = TRUE)
data_path <- args[[1]]
output_dir <- args[[2]]

r6 <- function(x) round(as.numeric(x), 6)
subjects <- function(x) sort(unique(as.integer(x)))

pk_formula <- log_conc ~ early_decay + mid_decay + late_decay +
  log_rate + log_amt + age10 + bsa_c + lbm10 + wt10 + sex_male

prepare_data <- function(dat) {
  names(dat) <- trimws(names(dat))
  for (col in c("ID", "Subject", "Time", "conc", "Rate", "Amt",
                "Age", "Ht", "Wt", "BSA", "LBM")) {
    dat[[col]] <- as.numeric(dat[[col]])
  }
  dat$Subject <- as.integer(dat$Subject)
  dat$ID <- as.integer(dat$ID)
  dat$Sex <- factor(dat$Sex, levels = sort(unique(dat$Sex)))
  dat$subject_factor <- factor(dat$Subject, levels = subjects(dat$Subject))
  dat$observed_conc <- !is.na(dat$conc) & dat$conc > 0
  obs <- dat[dat$observed_conc, ]
  dat$early_decay <- exp(-dat$Time / 3)
  dat$mid_decay <- exp(-dat$Time / 30)
  dat$late_decay <- exp(-dat$Time / 120)
  dat$log_rate <- log1p(pmax(dat$Rate, 0))
  dat$log_amt <- log1p(pmax(dat$Amt, 0))
  dat$age10 <- (dat$Age - mean(obs$Age)) / 10
  dat$bsa_c <- dat$BSA - mean(obs$BSA)
  dat$lbm10 <- (dat$LBM - mean(obs$LBM)) / 10
  dat$wt10 <- (dat$Wt - mean(obs$Wt)) / 10
  dat$sex_male <- as.numeric(as.character(dat$Sex) == "Male")
  dat$log_conc <- ifelse(dat$observed_conc, log(dat$conc), NA_real_)
  dat
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
    population_fixed = lm(pk_formula, data = obs),
    subject_random_intercept = nlme::lme(
      fixed = pk_formula,
      random = ~ 1 | subject_factor,
      data = obs,
      method = "ML",
      control = control,
      na.action = na.omit
    ),
    subject_random_slope = nlme::lme(
      fixed = pk_formula,
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

metric_row <- function(name, model, dat, selected = FALSE) {
  obs <- dat[dat$observed_conc, ]
  pred <- predict_original(model, obs, level = 1)
  resid <- obs$conc - pred
  data.frame(
    model = name,
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
    metric_row(
      "subject_random_intercept",
      models$subject_random_intercept,
      dat,
      FALSE
    ),
    metric_row("subject_random_slope", models$subject_random_slope, dat, TRUE)
  )
  out[order(out$model), ]
}

coefficient_table <- function(model_name, model) {
  if (inherits(model, "lme")) {
    tab <- as.data.frame(summary(model)$tTable)
    data.frame(
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
    data.frame(
      model = model_name,
      term = rownames(tab),
      estimate = r6(tab$Estimate),
      standard_error = r6(tab$`Std. Error`),
      statistic = r6(tab$`t value`),
      p_value = r6(tab$`Pr(>|t|)`),
      stringsAsFactors = FALSE
    )
  }
}

fixed_effects <- function(models) {
  out <- rbind(
    coefficient_table("population_fixed", models$population_fixed),
    coefficient_table(
      "subject_random_intercept",
      models$subject_random_intercept
    ),
    coefficient_table("subject_random_slope", models$subject_random_slope)
  )
  rownames(out) <- NULL
  out[order(out$model, out$term), ]
}

trapezoid_auc <- function(times, concs) {
  ok <- !is.na(times) & !is.na(concs)
  times <- times[ok]
  concs <- concs[ok]
  if (length(times) < 2) return(0)
  ord <- order(times)
  times <- times[ord]
  concs <- concs[ord]
  sum(diff(times) * (head(concs, -1) + tail(concs, -1)) / 2)
}

subject_pk_summary <- function(dat) {
  rows <- lapply(subjects(dat$Subject), function(one_subject) {
    one <- dat[dat$Subject == one_subject, ]
    obs <- one[one$observed_conc, ]
    cmax <- if (nrow(obs) == 0) NA_real_ else max(obs$conc)
    tmax <- if (nrow(obs) == 0) NA_real_ else obs$Time[which.max(obs$conc)]
    data.frame(
      subject = one_subject,
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

parse_varcorr <- function(model_name, model) {
  vc <- nlme::VarCorr(model)
  rows <- rownames(vc)
  out <- data.frame()
  for (i in seq_along(rows)) {
    effect <- rows[i]
    if (grepl("=", effect, fixed = TRUE)) next
    effect <- gsub("\\(Intercept\\)", "intercept", effect)
    effect <- gsub("Residual", "residual", effect)
    variance <- suppressWarnings(as.numeric(vc[i, "Variance"]))
    std_dev <- suppressWarnings(as.numeric(vc[i, "StdDev"]))
    corr <- NA_real_
    if ("Corr" %in% colnames(vc)) {
      corr <- suppressWarnings(as.numeric(gsub("[() ]", "", vc[i, "Corr"])))
    }
    out <- rbind(
      out,
      data.frame(
        model = model_name,
        effect = effect,
        variance = r6(variance),
        std_dev = r6(std_dev),
        correlation_with_intercept = ifelse(is.na(corr), NA_real_, r6(corr)),
        stringsAsFactors = FALSE
      )
    )
  }
  out
}

random_effects_summary <- function(models) {
  out <- rbind(
    parse_varcorr(
      "subject_random_intercept",
      models$subject_random_intercept
    ),
    parse_varcorr("subject_random_slope", models$subject_random_slope)
  )
  rownames(out) <- NULL
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
    fit <- lm(
      as.formula(paste(outcome, "~", paste(terms, collapse = " + "))),
      data = df
    )
    tab <- as.data.frame(summary(fit)$coefficients)
    for (term in terms) {
      estimate <- tab[term, "Estimate"]
      expected <- NA
      if (term == "age10") {
        expected <- estimate < 0
      } else if (term == "bsa_c") {
        expected <- estimate > 0
      } else if (term == "sex_male") {
        expected <- estimate < 0
      }
      rows[[length(rows) + 1]] <- data.frame(
        outcome = outcome,
        term = term,
        estimate = r6(estimate),
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
  out <- data.frame(
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
  out[order(out$residual_error_model), ]
}

prediction_diagnostics <- function(dat) {
  subj <- subjects(dat$Subject)
  heldout_subjects <- subj[seq(5, length(subj), by = 5)]
  train <- dat[dat$observed_conc & !(dat$Subject %in% heldout_subjects), ]
  control <- nlme::lmeControl(
    opt = "optim",
    msMaxIter = 200,
    maxIter = 100,
    niterEM = 50,
    returnObject = TRUE
  )
  fit <- nlme::lme(
    fixed = pk_formula,
    random = ~ 1 + mid_decay | subject_factor,
    data = train,
    method = "ML",
    control = control,
    na.action = na.omit
  )
  rows <- lapply(subj, function(one_subject) {
    one <- dat[dat$observed_conc & dat$Subject == one_subject, ]
    heldout <- one_subject %in% heldout_subjects
    pred <- predict_original(fit, one, level = ifelse(heldout, 0, 1))
    resid <- one$conc - pred
    data.frame(
      subject = one_subject,
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
  subj <- subjects(dat$Subject)
  list(
    total_n = as.integer(nrow(dat)),
    subjects_n = as.integer(length(subj)),
    nonmissing_conc_n = as.integer(sum(dat$observed_conc)),
    missing_conc_n = as.integer(sum(is.na(dat$conc) | dat$conc <= 0)),
    selected_model = "subject_random_slope",
    selected_residual_error = "proportional",
    heldout_subjects = as.integer(subj[seq(5, length(subj), by = 5)]),
    hidden_data_ready = TRUE
  )
}

read_actual <- function(filename) {
  read.csv(
    file.path(output_dir, filename),
    stringsAsFactors = FALSE,
    na.strings = c("", "NA"),
    check.names = FALSE
  )
}

compare_vector <- function(expected, actual, label) {
  if (is.numeric(expected) || is.integer(expected)) {
    actual <- as.numeric(actual)
    ok <- (is.na(expected) & is.na(actual)) |
      (!is.na(expected) & !is.na(actual) & abs(expected - actual) <= 1e-6)
    if (!all(ok)) stop(label, " numeric mismatch")
  } else if (is.logical(expected)) {
    actual <- as.logical(actual)
    ok <- (is.na(expected) & is.na(actual)) |
      (!is.na(expected) & !is.na(actual) & expected == actual)
    if (!all(ok)) stop(label, " logical mismatch")
  } else {
    expected_chr <- as.character(expected)
    actual_chr <- as.character(actual)
    ok <- (is.na(expected_chr) & is.na(actual_chr)) |
      (!is.na(expected_chr) & !is.na(actual_chr) & expected_chr == actual_chr)
    if (!all(ok)) stop(label, " character mismatch")
  }
}

compare_frame <- function(expected, filename) {
  actual <- read_actual(filename)
  if (!identical(names(expected), names(actual))) stop(filename, " columns")
  if (nrow(expected) != nrow(actual)) stop(filename, " rows")
  for (col in names(expected)) {
    compare_vector(expected[[col]], actual[[col]], paste(filename, col))
  }
}

compare_json <- function(expected, filename) {
  actual <- jsonlite::fromJSON(file.path(output_dir, filename))
  for (key in names(expected)) {
    compare_vector(expected[[key]], actual[[key]], paste(filename, key))
  }
}

dat <- read.csv(data_path, stringsAsFactors = FALSE)
prepared <- prepare_data(dat)
models <- fit_models(prepared)
subject_summary <- subject_pk_summary(prepared)

compare_frame(model_comparison(models, prepared), "model_comparison.csv")
compare_frame(fixed_effects(models), "fixed_effects.csv")
compare_frame(random_effects_summary(models), "random_effects_summary.csv")
compare_frame(covariate_effects(subject_summary), "covariate_effects.csv")
compare_frame(residual_error_models(models, prepared), "residual_error_models.csv")
compare_frame(prediction_diagnostics(prepared), "prediction_diagnostics.csv")
compare_json(analysis_summary(prepared), "analysis_summary.json")
"""


def run_analysis(data_path: Path | None = None) -> Path:
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if data_path is None:
        env.pop("REMIFENTANIL_DATA_PATH", None)
    else:
        env["REMIFENTANIL_DATA_PATH"] = str(data_path)
    result = subprocess.run(
        ["/usr/bin/Rscript", str(ENV_DIR / "analysis.R")],
        cwd=str(ENV_DIR),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=900,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return OUTPUT_DIR


def copy_outputs(dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(OUTPUT_DIR, dest)
    return dest


@pytest.fixture(scope="session")
def public_case(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    run_analysis()
    out = copy_outputs(tmp_path_factory.mktemp("public") / "outputs")
    return {"data": DATA_PATH, "out": out}


@pytest.fixture(scope="session")
def hidden_case(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    hidden_dir = tmp_path_factory.mktemp("hidden")
    hidden_csv = hidden_dir / "Remifentanil_hidden.csv"
    result = subprocess.run(
        [
            sys.executable,
            str(TEST_DIR / "generate_hidden_data.py"),
            str(DATA_PATH),
            str(hidden_csv),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    run_analysis(hidden_csv)
    out = copy_outputs(hidden_dir / "outputs")
    return {"data": hidden_csv, "out": out}


def read_summary(out_dir: Path) -> dict:
    """Read the JSON analysis summary for an output directory."""
    return json.loads((out_dir / "analysis_summary.json").read_text())


def assert_artifacts(case: dict[str, Path]) -> None:
    """Verify that all required CSV, JSON, and PNG artifacts exist."""
    out_dir = case["out"]
    expected = set(CSV_COLUMNS) | {"analysis_summary.json"} | set(PNG_FILES)
    present = {path.name for path in out_dir.iterdir() if path.is_file()}
    assert expected <= present


def assert_schema_and_counts(case: dict[str, Path]) -> None:
    """Verify output schemas, row counts, selected labels, and holdout counts."""
    out_dir = case["out"]
    summary = read_summary(out_dir)
    expected_rows = {
        "subject_pk_summary.csv": summary["subjects_n"],
        "model_comparison.csv": 3,
        "fixed_effects.csv": 33,
        "random_effects_summary.csv": 5,
        "covariate_effects.csv": 10,
        "residual_error_models.csv": 3,
        "prediction_diagnostics.csv": summary["subjects_n"],
    }
    for filename, columns in CSV_COLUMNS.items():
        df = pd.read_csv(out_dir / filename)
        assert list(df.columns) == columns
        assert len(df) == expected_rows[filename]
    assert summary["selected_model"] == "subject_random_slope"
    assert summary["selected_residual_error"] == "proportional"
    assert summary["hidden_data_ready"] is True
    assert len(summary["heldout_subjects"]) == summary["subjects_n"] // 5


def assert_numeric_rounding(case: dict[str, Path]) -> None:
    """Verify that numeric CSV columns are written to six decimal places."""
    out_dir = case["out"]
    for filename in CSV_COLUMNS:
        df = pd.read_csv(out_dir / filename)
        for col in df.select_dtypes(include=["number"]).columns:
            values = df[col].dropna()
            scaled = (values * 1_000_000).round()
            assert ((values * 1_000_000 - scaled).abs() < 1e-6).all()


def assert_json_types(case: dict[str, Path]) -> None:
    """Verify that analysis summary count fields remain JSON integers."""
    summary = read_summary(case["out"])
    assert isinstance(summary["total_n"], int)
    assert isinstance(summary["subjects_n"], int)
    assert isinstance(summary["nonmissing_conc_n"], int)
    assert isinstance(summary["missing_conc_n"], int)
    assert all(isinstance(x, int) for x in summary["heldout_subjects"])


def subject_summary_reference(data_path: Path) -> pd.DataFrame:
    """Recompute subject-level noncompartmental summaries in Python."""
    data = pd.read_csv(data_path)
    rows = []
    for subject in sorted(data["Subject"].unique()):
        one = data[data["Subject"] == subject].copy()
        obs = one[one["conc"].notna() & (one["conc"] > 0)].sort_values("Time")
        time = obs["Time"].to_numpy(dtype=float)
        conc = obs["conc"].to_numpy(dtype=float)
        auc = 0.0
        if len(time) > 1:
            auc = float(np.sum(np.diff(time) * (conc[:-1] + conc[1:]) / 2))
        cmax_index = int(np.argmax(conc))
        rows.append(
            {
                "subject": int(subject),
                "id": int(one["ID"].dropna().iloc[0]),
                "sex": str(one["Sex"].iloc[0]),
                "age": round(float(one["Age"].iloc[0]), 6),
                "weight": round(float(one["Wt"].iloc[0]), 6),
                "bsa": round(float(one["BSA"].iloc[0]), 6),
                "lbm": round(float(one["LBM"].iloc[0]), 6),
                "n_observed": int(len(obs)),
                "time_min": round(float(time.min()), 6),
                "time_max": round(float(time.max()), 6),
                "cmax": round(float(conc[cmax_index]), 6),
                "tmax": round(float(time[cmax_index]), 6),
                "auc_linear": round(auc, 6),
                "total_amt": round(float(one["Amt"].sum()), 6),
                "max_rate": round(float(one["Rate"].max()), 6),
            }
        )
    return pd.DataFrame(rows, columns=CSV_COLUMNS["subject_pk_summary.csv"])


def assert_subject_summary(case: dict[str, Path]) -> None:
    """Compare subject_pk_summary.csv against the Python recomputation."""
    expected = subject_summary_reference(case["data"])
    actual = pd.read_csv(case["out"] / "subject_pk_summary.csv")
    assert list(actual.columns) == list(expected.columns)
    for col in expected.columns:
        if pd.api.types.is_numeric_dtype(expected[col]):
            assert np.allclose(actual[col], expected[col], atol=1e-6, rtol=0)
        else:
            actual_values = actual[col].astype(str).tolist()
            expected_values = expected[col].astype(str).tolist()
            assert actual_values == expected_values


def png_info(path: Path) -> tuple[int, int, int]:
    """Return PNG dimensions and byte diversity after validating the signature."""
    raw = path.read_bytes()
    assert raw.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", raw[16:24])
    offset = 8
    idat = bytearray()
    while offset < len(raw):
        size = struct.unpack(">I", raw[offset : offset + 4])[0]
        chunk = raw[offset + 4 : offset + 8]
        payload = raw[offset + 8 : offset + 8 + size]
        if chunk == b"IDAT":
            idat.extend(payload)
        offset += 12 + size
    inflated = zlib.decompress(bytes(idat))
    return width, height, len(set(inflated))


def assert_pngs(case: dict[str, Path]) -> None:
    """Verify that rendered PNG artifacts are large enough and nonblank."""
    for name in PNG_FILES:
        path = case["out"] / name
        width, height, unique_bytes = png_info(path)
        assert width >= 1000
        assert height >= 600
        assert path.stat().st_size > 20_000
        assert unique_bytes > 24


def assert_reference_match(case: dict[str, Path]) -> None:
    """Compare model outputs against the independent R reference implementation."""
    handle = tempfile.NamedTemporaryFile("w", suffix=".R", delete=False)
    try:
        with handle:
            handle.write(REFERENCE_R)
        result = subprocess.run(
            [
                "/usr/bin/Rscript",
                handle.name,
                str(case["data"]),
                str(case["out"]),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=900,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    finally:
        Path(handle.name).unlink(missing_ok=True)


def test_public_outputs_exist(public_case: dict[str, Path]) -> None:
    """The public run produces every required artifact."""
    assert_artifacts(public_case)


def test_public_schema_counts_and_types(public_case: dict[str, Path]) -> None:
    """The public run follows the published output contract."""
    assert_schema_and_counts(public_case)
    assert_json_types(public_case)


def test_public_values_match_reference(public_case: dict[str, Path]) -> None:
    """The public run matches an independent R reference recomputation."""
    assert_reference_match(public_case)
    assert_subject_summary(public_case)


def test_public_rounding_and_plots(public_case: dict[str, Path]) -> None:
    """The public run rounds numeric outputs and renders nonblank PNGs."""
    assert_numeric_rounding(public_case)
    assert_pngs(public_case)


def test_hidden_schema_counts_and_types(hidden_case: dict[str, Path]) -> None:
    """The hidden-data pass preserves schemas and dynamic row counts."""
    assert_artifacts(hidden_case)
    assert_schema_and_counts(hidden_case)
    assert_json_types(hidden_case)


def test_hidden_values_match_reference(hidden_case: dict[str, Path]) -> None:
    """The hidden-data pass matches the independent R reference."""
    assert_reference_match(hidden_case)
    assert_subject_summary(hidden_case)


def test_hidden_rounding_and_plots(hidden_case: dict[str, Path]) -> None:
    """The hidden-data pass has rounded numerics and rendered PNGs."""
    assert_numeric_rounding(hidden_case)
    assert_pngs(hidden_case)
