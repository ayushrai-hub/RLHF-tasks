#!/usr/bin/env bash
set -uo pipefail

cd /app/environment

cat > /app/environment/analysis.R <<'EOF_R'
#!/usr/bin/env Rscript
suppressPackageStartupMessages({
  library(nnet)
  library(jsonlite)
  library(ggplot2)
})

DATA_PATH  <- "/app/environment/data/BEPS.csv"
OUTPUT_DIR <- "/app/environment/outputs"
dir.create(OUTPUT_DIR, showWarnings = FALSE, recursive = TRUE)

raw <- read.csv(DATA_PATH, stringsAsFactors = FALSE)
rnd <- function(x) round(as.numeric(x), 6)

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

md <- data.frame(
  vote = factor(raw$vote, levels = PARTIES),
  age = as.numeric(raw$age),
  gender_male = as.integer(raw$gender == "male"),
  econ_national = as.numeric(raw$economic.cond.national),
  econ_household = as.numeric(raw$economic.cond.household),
  blair = as.numeric(raw$Blair),
  hague = as.numeric(raw$Hague),
  kennedy = as.numeric(raw$Kennedy),
  europe = as.numeric(raw$Europe),
  political_knowledge = as.numeric(raw$political.knowledge),
  stringsAsFactors = FALSE
)

build_mm <- function(df) {
  cbind(intercept = 1, age = df$age, gender_male = df$gender_male,
        econ_national = df$econ_national, econ_household = df$econ_household,
        blair = df$blair, hague = df$hague, kennedy = df$kennedy,
        europe = df$europe, political_knowledge = df$political_knowledge,
        europe_x_political_knowledge = df$europe * df$political_knowledge)
}

fml <- vote ~ age + gender_male + econ_national + econ_household +
  blair + hague + kennedy + europe * political_knowledge
fit <- multinom(fml, data = md, trace = FALSE, maxit = 500)

cf <- coef(fit)
B <- matrix(0, nrow = 2, ncol = length(TERMS), dimnames = list(NONREF, TERMS))
for (lv in NONREF) for (mn in colnames(cf)) B[lv, canon_map[[mn]]] <- cf[lv, mn]

mnl_probs <- function(Bm, mm) {
  eta <- mm %*% t(Bm)
  ex <- exp(eta)
  denom <- 1 + rowSums(ex)
  cbind(Conservative = 1 / denom, Labour = ex[, 1] / denom, `Liberal Democrat` = ex[, 2] / denom)
}

V <- vcov(fit)
vn <- rownames(V)
parse_one <- function(nm) {
  for (lv in NONREF) {
    pre <- paste0(lv, ":")
    if (startsWith(nm, pre)) return(list(level = lv, term = canon_map[[substring(nm, nchar(pre) + 1)]]))
  }
  stop(paste("unparsed", nm))
}
theta0 <- numeric(length(vn)); meta <- vector("list", length(vn))
for (i in seq_along(vn)) { pr <- parse_one(vn[i]); meta[[i]] <- pr; theta0[i] <- B[pr$level, pr$term] }

ame_cont <- function(Bm, df, pred, h = 1e-4) {
  dfp <- df; dfp[[pred]] <- df[[pred]] + h
  dfm <- df; dfm[[pred]] <- df[[pred]] - h
  (colMeans(mnl_probs(Bm, build_mm(dfp))) - colMeans(mnl_probs(Bm, build_mm(dfm)))) / (2 * h)
}
ame_disc <- function(Bm, df, pred) {
  df1 <- df; df1[[pred]] <- 1; df0 <- df; df0[[pred]] <- 0
  colMeans(mnl_probs(Bm, build_mm(df1))) - colMeans(mnl_probs(Bm, build_mm(df0)))
}
ame_of_theta <- function(theta, df, pred, kind) {
  Bm <- B
  for (i in seq_along(theta)) Bm[meta[[i]]$level, meta[[i]]$term] <- theta[i]
  if (kind == "disc") ame_disc(Bm, df, pred) else ame_cont(Bm, df, pred)
}
ame_se <- function(df, pred, kind, hstep = 1e-4) {
  base <- ame_of_theta(theta0, df, pred, kind)
  J <- matrix(0, nrow = 3, ncol = length(theta0))
  for (i in seq_along(theta0)) {
    tp <- theta0; tp[i] <- tp[i] + hstep
    tm <- theta0; tm[i] <- tm[i] - hstep
    J[, i] <- (ame_of_theta(tp, df, pred, kind) - ame_of_theta(tm, df, pred, kind)) / (2 * hstep)
  }
  list(ame = base, se = sqrt(pmax(diag(J %*% V %*% t(J)), 0)))
}

se_lookup <- setNames(sqrt(diag(V)), vn)
coef_rows <- list()
for (e in seq_along(NONREF)) {
  lv <- NONREF[e]
  for (tm in TERMS) {
    mn <- names(canon_map)[match(tm, canon_map)]
    est <- B[lv, tm]; se <- se_lookup[[paste0(lv, ":", mn)]]; z <- est / se
    coef_rows[[length(coef_rows) + 1]] <- data.frame(
      equation = EQ_LAB[e], term = tm, estimate = rnd(est), std_error = rnd(se),
      z = rnd(z), p_value = rnd(2 * pnorm(-abs(z))), stringsAsFactors = FALSE)
  }
}
co <- do.call(rbind, coef_rows)
co <- co[order(co$equation, co$term), ]
write.csv(co, file.path(OUTPUT_DIR, "coefficients.csv"), row.names = FALSE)

PREDS <- c("age", "gender_male", "econ_national", "econ_household",
           "blair", "hague", "kennedy", "europe", "political_knowledge")
KIND  <- ifelse(PREDS == "gender_male", "disc", "cont")
me_rows <- list()
for (j in seq_along(PREDS)) {
  r <- ame_se(md, PREDS[j], KIND[j])
  for (k in seq_along(PARTIES)) {
    z <- r$ame[k] / r$se[k]
    me_rows[[length(me_rows) + 1]] <- data.frame(
      outcome = PARTIES[k], predictor = PREDS[j], ame = rnd(r$ame[k]), ame_se = rnd(r$se[k]),
      ame_z = rnd(z), ame_p = rnd(2 * pnorm(-abs(z))), stringsAsFactors = FALSE)
  }
}
me <- do.call(rbind, me_rows)
me <- me[order(me$outcome, me$predictor), ]
write.csv(me, file.path(OUTPUT_DIR, "marginal_effects.csv"), row.names = FALSE)

full_dev <- deviance(fit)
Xfull <- build_mm(md)
LR_TERMS <- c("age", "gender_male", "econ_national", "econ_household",
              "blair", "hague", "kennedy", "europe_x_political_knowledge")
lr_rows <- list()
for (tm in LR_TERMS) {
  Xr <- Xfull[, setdiff(colnames(Xfull), c("intercept", tm)), drop = FALSE]
  rfit <- multinom(md$vote ~ Xr, trace = FALSE, maxit = 500)
  stat <- deviance(rfit) - full_dev
  lr_rows[[length(lr_rows) + 1]] <- data.frame(
    term = tm, df = 2L, lr_chisq = rnd(stat),
    p_value = rnd(pchisq(stat, df = 2, lower.tail = FALSE)), stringsAsFactors = FALSE)
}
lr <- do.call(rbind, lr_rows)
lr <- lr[order(lr$term), ]
write.csv(lr, file.path(OUTPUT_DIR, "lr_tests.csv"), row.names = FALSE)

P0 <- mnl_probs(B, Xfull)
ll <- -full_dev / 2
ll_null <- -deviance(multinom(md$vote ~ 1, trace = FALSE, maxit = 500)) / 2
pred_class <- PARTIES[max.col(P0, ties.method = "first")]
acc <- mean(pred_class == as.character(md$vote))
Y <- model.matrix(~ md$vote - 1)
brier <- mean(rowSums((P0 - Y)^2))
npar <- length(theta0)
int_stat <- lr$lr_chisq[lr$term == "europe_x_political_knowledge"]
int_p <- lr$p_value[lr$term == "europe_x_political_knowledge"]
fit_list <- list(
  n = nrow(md), n_parameters = npar, log_likelihood = rnd(ll), deviance = rnd(full_dev),
  aic = rnd(2 * npar - 2 * ll), mcfadden_r2 = rnd(1 - ll / ll_null),
  accuracy = rnd(acc), multiclass_brier = rnd(brier),
  interaction_lr_chisq = rnd(int_stat), interaction_df = 2L, interaction_p = rnd(int_p))
write_json(fit_list, file.path(OUTPUT_DIR, "model_fit.json"), auto_unbox = TRUE, pretty = TRUE)

me_europe_at_k <- function(k, h = 1e-4) {
  dfk <- md; dfk$political_knowledge <- k
  dfp <- dfk; dfp$europe <- dfk$europe + h
  dfm <- dfk; dfm$europe <- dfk$europe - h
  (colMeans(mnl_probs(B, build_mm(dfp))) - colMeans(mnl_probs(B, build_mm(dfm)))) / (2 * h)
}
me_k0 <- me_europe_at_k(0); me_k3 <- me_europe_at_k(3); int_eff <- me_k3 - me_k0
eki <- list(
  ame_europe_k0_conservative = rnd(me_k0[["Conservative"]]),
  ame_europe_k0_labour = rnd(me_k0[["Labour"]]),
  ame_europe_k0_libdem = rnd(me_k0[["Liberal Democrat"]]),
  ame_europe_k3_conservative = rnd(me_k3[["Conservative"]]),
  ame_europe_k3_labour = rnd(me_k3[["Labour"]]),
  ame_europe_k3_libdem = rnd(me_k3[["Liberal Democrat"]]),
  interaction_effect_conservative = rnd(int_eff[["Conservative"]]),
  interaction_effect_labour = rnd(int_eff[["Labour"]]),
  interaction_effect_libdem = rnd(int_eff[["Liberal Democrat"]]))
write_json(eki, file.path(OUTPUT_DIR, "europe_knowledge_interaction.json"),
           auto_unbox = TRUE, pretty = TRUE, digits = 6)

shares_at_europe <- function(eu) {
  dfe <- md; dfe$europe <- eu
  colMeans(mnl_probs(B, build_mm(dfe)))
}
sh_phile <- shares_at_europe(1)
sh_septic <- shares_at_europe(11)
fd <- sh_septic - sh_phile
efd <- list(
  share_europhile_conservative = rnd(sh_phile[["Conservative"]]),
  share_europhile_labour = rnd(sh_phile[["Labour"]]),
  share_europhile_libdem = rnd(sh_phile[["Liberal Democrat"]]),
  share_eurosceptic_conservative = rnd(sh_septic[["Conservative"]]),
  share_eurosceptic_labour = rnd(sh_septic[["Labour"]]),
  share_eurosceptic_libdem = rnd(sh_septic[["Liberal Democrat"]]),
  first_diff_conservative = rnd(fd[["Conservative"]]),
  first_diff_labour = rnd(fd[["Labour"]]),
  first_diff_libdem = rnd(fd[["Liberal Democrat"]]))
write_json(efd, file.path(OUTPUT_DIR, "europe_first_difference.json"),
           auto_unbox = TRUE, pretty = TRUE, digits = 6)

mean_row <- data.frame(
  age = mean(md$age), gender_male = mean(md$gender_male),
  econ_national = mean(md$econ_national), econ_household = mean(md$econ_household),
  blair = mean(md$blair), hague = mean(md$hague), kennedy = mean(md$kennedy),
  europe = NA, political_knowledge = NA)
grid <- expand.grid(europe = 1:11, political_knowledge = c(0, 1, 2, 3))
gdf <- mean_row[rep(1, nrow(grid)), ]
gdf$europe <- grid$europe; gdf$political_knowledge <- grid$political_knowledge
gp <- mnl_probs(B, build_mm(gdf))
prof <- data.frame(europe = rep(grid$europe, 3),
                   political_knowledge = factor(rep(grid$political_knowledge, 3)),
                   party = rep(PARTIES, each = nrow(grid)),
                   prob = as.vector(gp))
ggsave(file.path(OUTPUT_DIR, "effect_europe_by_knowledge.png"),
       ggplot(prof, aes(europe, prob, colour = party)) + geom_line(linewidth = 0.8) +
         facet_wrap(~ political_knowledge, labeller = label_both) +
         labs(title = "Predicted vote probability across Euroscepticism by political knowledge",
              x = "Europe scale", y = "Predicted probability") + theme_minimal(),
       width = 7, height = 5, dpi = 100)

amep <- me
amep$lo <- amep$ame - 1.96 * amep$ame_se; amep$hi <- amep$ame + 1.96 * amep$ame_se
ggsave(file.path(OUTPUT_DIR, "ame_forest.png"),
       ggplot(amep, aes(ame, predictor)) + geom_point(size = 1.8) +
         geom_errorbarh(aes(xmin = lo, xmax = hi), height = 0.25) +
         geom_vline(xintercept = 0, linetype = "dashed") + facet_wrap(~ outcome) +
         labs(title = "Average marginal effects by party",
              x = "AME on party probability", y = "Predictor") + theme_minimal(),
       width = 8, height = 5, dpi = 100)

vc <- as.data.frame(table(md$vote)); names(vc) <- c("party", "n")
ggsave(file.path(OUTPUT_DIR, "vote_shares.png"),
       ggplot(vc, aes(party, n, fill = party)) + geom_col() +
         labs(title = "Observed vote distribution", x = "Party", y = "Respondents") +
         theme_minimal() + theme(legend.position = "none"),
       width = 6, height = 4, dpi = 100)

cal_rows <- list()
for (k in seq_along(PARTIES)) {
  p <- P0[, k]; y <- as.integer(md$vote == PARTIES[k])
  br <- cut(p, breaks = seq(0, 1, 0.1), include.lowest = TRUE)
  for (lvl in levels(br)) {
    sel <- br == lvl
    if (sum(sel) > 0) cal_rows[[length(cal_rows) + 1]] <- data.frame(
      party = PARTIES[k], predicted = mean(p[sel]), observed = mean(y[sel]), stringsAsFactors = FALSE)
  }
}
cal <- do.call(rbind, cal_rows)
ggsave(file.path(OUTPUT_DIR, "calibration.png"),
       ggplot(cal, aes(predicted, observed, colour = party)) + geom_point(size = 1.8) +
         geom_line() + geom_abline(linetype = "dashed") +
         labs(title = "Calibration of predicted vote probabilities",
              x = "Mean predicted probability", y = "Observed frequency") + theme_minimal(),
       width = 6, height = 5, dpi = 100)

conf <- as.data.frame(table(predicted = factor(pred_class, levels = PARTIES),
                            actual = factor(as.character(md$vote), levels = PARTIES)))
ggsave(file.path(OUTPUT_DIR, "confusion_heatmap.png"),
       ggplot(conf, aes(actual, predicted, fill = Freq)) + geom_tile() +
         geom_text(aes(label = Freq)) + scale_fill_gradient(low = "white", high = "steelblue") +
         labs(title = "Predicted versus actual party", x = "Actual", y = "Predicted") + theme_minimal(),
       width = 6, height = 5, dpi = 100)
EOF_R

chmod +x /app/environment/analysis.R
Rscript /app/environment/analysis.R
