# ruff: noqa: E501
import subprocess
import tempfile
from pathlib import Path

import pytest

REF_LIB = r"""
suppressPackageStartupMessages(library(nnet))

approx_ok <- function(a, b, tol) length(a) == 1 && is.finite(a) && is.finite(b) && abs(a - b) <= tol
fail <- function(msg) { message(paste0("FAIL: ", msg)); quit(status = 1) }

PARTIES <- c("Conservative", "Labour", "Liberal Democrat")
NONREF  <- c("Labour", "Liberal Democrat")
EQ_LAB  <- c("labour", "libdem")
TERMS <- c("intercept", "age", "gender_male", "econ_national", "econ_household",
           "blair", "hague", "kennedy", "europe", "political_knowledge",
           "europe_x_political_knowledge")
canon_map <- c("(Intercept)" = "intercept", "age" = "age", "gender_male" = "gender_male",
               "econ_national" = "econ_national", "econ_household" = "econ_household",
               "blair" = "blair", "hague" = "hague", "kennedy" = "kennedy",
               "europe" = "europe", "political_knowledge" = "political_knowledge",
               "europe:political_knowledge" = "europe_x_political_knowledge")

build_mm <- function(df) {
  cbind(intercept = 1, age = df$age, gender_male = df$gender_male,
        econ_national = df$econ_national, econ_household = df$econ_household,
        blair = df$blair, hague = df$hague, kennedy = df$kennedy,
        europe = df$europe, political_knowledge = df$political_knowledge,
        europe_x_political_knowledge = df$europe * df$political_knowledge)
}
mnl_probs <- function(Bm, mm) {
  eta <- mm %*% t(Bm); ex <- exp(eta); denom <- 1 + rowSums(ex)
  cbind(Conservative = 1 / denom, Labour = ex[, 1] / denom, `Liberal Democrat` = ex[, 2] / denom)
}

compute_ref <- function(path = Sys.getenv("REF_DATA_PATH", "/app/environment/data/BEPS.csv")) {
  raw <- read.csv(path, stringsAsFactors = FALSE)
  md <- data.frame(
    vote = factor(raw$vote, levels = PARTIES),
    age = as.numeric(raw$age),
    gender_male = as.integer(raw$gender == "male"),
    econ_national = as.numeric(raw$economic.cond.national),
    econ_household = as.numeric(raw$economic.cond.household),
    blair = as.numeric(raw$Blair), hague = as.numeric(raw$Hague),
    kennedy = as.numeric(raw$Kennedy), europe = as.numeric(raw$Europe),
    political_knowledge = as.numeric(raw$political.knowledge),
    stringsAsFactors = FALSE)

  fml <- vote ~ age + gender_male + econ_national + econ_household +
    blair + hague + kennedy + europe * political_knowledge
  fit <- multinom(fml, data = md, trace = FALSE, maxit = 500)
  cf <- coef(fit)
  B <- matrix(0, nrow = 2, ncol = length(TERMS), dimnames = list(NONREF, TERMS))
  for (lv in NONREF) for (mn in colnames(cf)) B[lv, canon_map[[mn]]] <- cf[lv, mn]

  V <- vcov(fit); vn <- rownames(V)
  parse_one <- function(nm) {
    for (lv in NONREF) { pre <- paste0(lv, ":")
      if (startsWith(nm, pre)) return(list(level = lv, term = canon_map[[substring(nm, nchar(pre) + 1)]])) }
    stop(paste("unparsed", nm)) }
  theta0 <- numeric(length(vn)); meta <- vector("list", length(vn))
  for (i in seq_along(vn)) { pr <- parse_one(vn[i]); meta[[i]] <- pr; theta0[i] <- B[pr$level, pr$term] }

  ame_cont <- function(Bm, df, pred, h = 1e-4) {
    dfp <- df; dfp[[pred]] <- df[[pred]] + h; dfm <- df; dfm[[pred]] <- df[[pred]] - h
    (colMeans(mnl_probs(Bm, build_mm(dfp))) - colMeans(mnl_probs(Bm, build_mm(dfm)))) / (2 * h) }
  ame_disc <- function(Bm, df, pred) {
    df1 <- df; df1[[pred]] <- 1; df0 <- df; df0[[pred]] <- 0
    colMeans(mnl_probs(Bm, build_mm(df1))) - colMeans(mnl_probs(Bm, build_mm(df0))) }
  ame_of_theta <- function(theta, df, pred, kind) {
    Bm <- B; for (i in seq_along(theta)) Bm[meta[[i]]$level, meta[[i]]$term] <- theta[i]
    if (kind == "disc") ame_disc(Bm, df, pred) else ame_cont(Bm, df, pred) }
  ame_se <- function(df, pred, kind, hstep = 1e-4) {
    base <- ame_of_theta(theta0, df, pred, kind); J <- matrix(0, 3, length(theta0))
    for (i in seq_along(theta0)) { tp <- theta0; tp[i] <- tp[i] + hstep; tm <- theta0; tm[i] <- tm[i] - hstep
      J[, i] <- (ame_of_theta(tp, df, pred, kind) - ame_of_theta(tm, df, pred, kind)) / (2 * hstep) }
    list(ame = base, se = sqrt(pmax(diag(J %*% V %*% t(J)), 0))) }

  se_lookup <- setNames(sqrt(diag(V)), vn)
  coef_df <- do.call(rbind, lapply(seq_along(NONREF), function(e) {
    lv <- NONREF[e]
    do.call(rbind, lapply(TERMS, function(tm) {
      mn <- names(canon_map)[match(tm, canon_map)]
      data.frame(equation = EQ_LAB[e], term = tm, estimate = B[lv, tm],
                 std_error = se_lookup[[paste0(lv, ":", mn)]], stringsAsFactors = FALSE) })) }))

  PREDS <- c("age", "gender_male", "econ_national", "econ_household",
             "blair", "hague", "kennedy", "europe", "political_knowledge")
  KIND <- ifelse(PREDS == "gender_male", "disc", "cont")
  me_df <- do.call(rbind, lapply(seq_along(PREDS), function(j) {
    r <- ame_se(md, PREDS[j], KIND[j])
    do.call(rbind, lapply(seq_along(PARTIES), function(k)
      data.frame(outcome = PARTIES[k], predictor = PREDS[j],
                 ame = r$ame[k], ame_se = r$se[k], stringsAsFactors = FALSE))) }))

  full_dev <- deviance(fit); Xfull <- build_mm(md)
  LR_TERMS <- c("age", "gender_male", "econ_national", "econ_household",
                "blair", "hague", "kennedy", "europe_x_political_knowledge")
  lr_df <- do.call(rbind, lapply(LR_TERMS, function(tm) {
    Xr <- Xfull[, setdiff(colnames(Xfull), c("intercept", tm)), drop = FALSE]
    rfit <- multinom(md$vote ~ Xr, trace = FALSE, maxit = 500)
    data.frame(term = tm, lr_chisq = deviance(rfit) - full_dev, stringsAsFactors = FALSE) }))

  P0 <- mnl_probs(B, Xfull); ll <- -full_dev / 2
  ll_null <- -deviance(multinom(md$vote ~ 1, trace = FALSE, maxit = 500)) / 2
  pred_class <- PARTIES[max.col(P0, ties.method = "first")]
  Y <- model.matrix(~ md$vote - 1)
  int_stat <- lr_df$lr_chisq[lr_df$term == "europe_x_political_knowledge"]

  me_europe_at_k <- function(k, h = 1e-4) {
    dfk <- md; dfk$political_knowledge <- k
    dfp <- dfk; dfp$europe <- dfk$europe + h
    dfm <- dfk; dfm$europe <- dfk$europe - h
    (colMeans(mnl_probs(B, build_mm(dfp))) - colMeans(mnl_probs(B, build_mm(dfm)))) / (2 * h) }
  me_k0 <- me_europe_at_k(0); me_k3 <- me_europe_at_k(3); int_eff <- me_k3 - me_k0
  eki <- list(
    ame_europe_k0_conservative = me_k0[["Conservative"]],
    ame_europe_k0_labour = me_k0[["Labour"]],
    ame_europe_k0_libdem = me_k0[["Liberal Democrat"]],
    ame_europe_k3_conservative = me_k3[["Conservative"]],
    ame_europe_k3_labour = me_k3[["Labour"]],
    ame_europe_k3_libdem = me_k3[["Liberal Democrat"]],
    interaction_effect_conservative = int_eff[["Conservative"]],
    interaction_effect_labour = int_eff[["Labour"]],
    interaction_effect_libdem = int_eff[["Liberal Democrat"]])

  shares_at_europe <- function(eu) { dfe <- md; dfe$europe <- eu; colMeans(mnl_probs(B, build_mm(dfe))) }
  sh_phile <- shares_at_europe(1); sh_septic <- shares_at_europe(11); fd <- sh_septic - sh_phile
  efd <- list(
    share_europhile_conservative = sh_phile[["Conservative"]],
    share_europhile_labour = sh_phile[["Labour"]],
    share_europhile_libdem = sh_phile[["Liberal Democrat"]],
    share_eurosceptic_conservative = sh_septic[["Conservative"]],
    share_eurosceptic_labour = sh_septic[["Labour"]],
    share_eurosceptic_libdem = sh_septic[["Liberal Democrat"]],
    first_diff_conservative = fd[["Conservative"]],
    first_diff_labour = fd[["Labour"]],
    first_diff_libdem = fd[["Liberal Democrat"]])

  list(n = nrow(md), n_parameters = length(theta0), coef = coef_df, me = me_df, lr = lr_df, eki = eki, efd = efd,
       fit = list(log_likelihood = ll, deviance = full_dev, aic = 2 * length(theta0) - 2 * ll,
                  mcfadden_r2 = 1 - ll / ll_null, accuracy = mean(pred_class == as.character(md$vote)),
                  multiclass_brier = mean(rowSums((P0 - Y)^2)),
                  interaction_lr_chisq = int_stat,
                  interaction_p = pchisq(int_stat, df = 2, lower.tail = FALSE)))
}
"""

_REF_PATH = "/tmp/beps_ref.R"


@pytest.fixture(scope="session", autouse=True)
def provision_ref_lib():
    """Write the shared R reference library to a fixed temp path for the session."""
    Path(_REF_PATH).write_text(REF_LIB)
    yield
    Path(_REF_PATH).unlink(missing_ok=True)


def run_r(r_code, *, timeout=600):
    """Run an R snippet through Rscript and return the completed process."""
    fd, path = tempfile.mkstemp(suffix=".R", text=True)
    try:
        with open(fd, "w") as f:
            f.write(r_code)
        return subprocess.run(["Rscript", path], capture_output=True, text=True, timeout=timeout)
    finally:
        Path(path).unlink(missing_ok=True)
