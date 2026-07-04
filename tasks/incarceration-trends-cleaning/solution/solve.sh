#!/usr/bin/env bash
set -euo pipefail

cd /app/environment

cat > /app/environment/analysis.R <<'EOF_R'
#!/usr/bin/env Rscript

DATA_DIR <- "/app/environment/data/states"
OUTPUT_DIR <- "/app/environment/outputs"
unlink(OUTPUT_DIR, recursive = TRUE)
dir.create(OUTPUT_DIR, showWarnings = FALSE, recursive = TRUE)

files <- sort(list.files(DATA_DIR, pattern = "\\.csv$", full.names = TRUE))
dat <- do.call(rbind, lapply(files, function(f)
  read.csv(f, stringsAsFactors = FALSE, colClasses = "character")))

num <- function(x) suppressWarnings(as.numeric(trimws(x)))
clean_fips <- sprintf("%05d", as.integer(round(num(dat$fips))))
year <- as.integer(trimws(dat$year))
key <- paste(clean_fips, year)

# One record per county and year, in first-appearance order.
ukey <- unique(key)
firstidx <- match(ukey, key)
fips_u <- clean_fips[firstidx]
year_u <- year[firstidx]

# Reconcile a raw column: for each county and year, take the value from the
# latest row (by file order) that is not blank; blank only if every row is.
reconcile <- function(v) {
  tv <- trimws(v)
  ne <- !is.na(tv) & tv != ""
  idx <- which(ne)
  o <- order(key[idx], idx)
  ki <- key[idx][o]
  vi <- v[idx][o]
  keep <- !duplicated(ki, fromLast = TRUE)
  out <- setNames(rep("", length(ukey)), ukey)
  out[ki[keep]] <- vi[keep]
  unname(out[ukey])
}

r_state <- reconcile(dat$state)
r_county <- reconcile(dat$county_name)
r_urb <- reconcile(dat$urbanicity)
r_region <- reconcile(dat$region)
r_pop <- reconcile(dat$total_pop_15to64)
r_jail <- reconcile(dat$total_jail_pop)
r_prison <- reconcile(dat$total_prison_pop)

pop64 <- num(r_pop)
jail <- num(r_jail)
prison <- num(r_prison)

rate <- function(count, denom) {
  r <- count / denom * 100000
  r[is.na(count) | is.na(denom) | denom <= 0] <- NA_real_
  round(r, 1)
}

# Each county's type is the label that appears most often across its years;
# ties resolve toward the order rural, small/mid, suburban, urban.
canon <- c("rural", "small/mid", "suburban", "urban")
urb_folded <- tolower(trimws(r_urb))
mode_label <- function(labs) {
  tab <- table(labs)
  top <- names(tab)[tab == max(tab)]
  top[order(match(top, canon))][1]
}
fips_mode <- tapply(urb_folded, fips_u, mode_label)
urb_final <- unname(fips_mode[as.character(fips_u)])

full <- data.frame(
  fips = fips_u,
  state = trimws(r_state),
  county_name = r_county,
  year = year_u,
  urbanicity = urb_final,
  region = trimws(r_region),
  total_pop_15to64 = as.integer(pop64),
  total_jail_pop = as.integer(jail),
  total_prison_pop = as.integer(prison),
  jail_rate_per_100k = rate(jail, pop64),
  prison_rate_per_100k = rate(prison, pop64),
  stringsAsFactors = FALSE
)

clean <- full[order(full$fips, full$year), ]
rownames(clean) <- NULL
write.csv(clean, file.path(OUTPUT_DIR, "county_year_clean.csv"),
          row.names = FALSE, na = "")

groups <- sort(unique(clean$urbanicity))
weight <- as.integer(clean$total_pop_15to64)
MIN_YEARS <- 3L

# One study per state: population-weighted state rate y and its study variance v,
# the weighted variance of the state's yearly rates divided by the row count.
study_stats <- function(x, w) {
  W <- sum(w)
  y <- sum(w * x) / W
  S2 <- sum(w * (x - y)^2) / W
  list(y = y, v = S2 / length(x), S2 = S2)
}

# DerSimonian-Laird random-effects pool of a group's states for one rate.
dlpool <- function(rate, w, st) {
  ok <- !is.na(rate) & !is.na(w) & w > 0
  rate <- rate[ok]; w <- w[ok]; st <- st[ok]
  ys <- numeric(0); vs <- numeric(0)
  for (s in sort(unique(st))) {
    m <- st == s
    if (sum(m) >= MIN_YEARS) {
      ss <- study_stats(rate[m], w[m])
      if (ss$S2 > 0) { ys <- c(ys, ss$y); vs <- c(vs, ss$v) }
    }
  }
  k <- length(ys)
  if (k == 0) return(list(rate = NA_real_, k = 0L))
  if (k == 1) return(list(rate = ys[1], k = 1L))
  a <- 1 / vs
  ybar <- sum(a * ys) / sum(a)
  Q <- sum(a * (ys - ybar)^2)
  C <- sum(a) - sum(a^2) / sum(a)
  tau2 <- max(0, (Q - (k - 1)) / C)
  b <- 1 / (vs + tau2)
  list(rate = sum(b * ys) / sum(b), k = k)
}
jail_fit <- lapply(groups, function(g) {
  m <- clean$urbanicity == g
  dlpool(clean$jail_rate_per_100k[m], weight[m], clean$state[m])
})
prison_fit <- lapply(groups, function(g) {
  m <- clean$urbanicity == g
  dlpool(clean$prison_rate_per_100k[m], weight[m], clean$state[m])
})
r2 <- function(x) if (is.na(x)) NA_real_ else round(x, 2)
summary <- data.frame(
  urbanicity = groups,
  n_county_years = as.integer(sapply(groups, function(g) sum(clean$urbanicity == g))),
  n_jail_states = as.integer(sapply(jail_fit, function(f) f$k)),
  n_prison_states = as.integer(sapply(prison_fit, function(f) f$k)),
  re_jail_rate_per_100k = sapply(jail_fit, function(f) r2(f$rate)),
  re_prison_rate_per_100k = sapply(prison_fit, function(f) r2(f$rate)),
  stringsAsFactors = FALSE
)
write.csv(summary, file.path(OUTPUT_DIR, "urbanicity_summary.csv"),
          row.names = FALSE, na = "")
EOF_R

chmod +x /app/environment/analysis.R
Rscript /app/environment/analysis.R
